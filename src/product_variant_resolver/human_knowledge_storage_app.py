"""Explicit T49.3 experimental app; the original ``api:app`` remains unchanged."""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api import create_app as create_base_app
from .catalog import load_catalog
from .config import Settings
from .human_knowledge_identity_artifact import load_human_knowledge_v4_config
from .human_knowledge_storage_profile import (
    HumanStorageHydration,
    HumanStorageProfile,
    RepositoryFactory,
    StorageIntegrityError,
    default_repository_factory,
    load_profile,
)
from .schemas import ResolveRequest, ResolveResponse
from .service import DependencyUnavailable, ResolverService

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ENVIRONMENT = "PVR_HUMAN_STORAGE_PROFILE_PATH"


def _inside(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("service input path must remain inside project")
    return resolved


def _absolute_settings(settings: Settings, root: Path) -> Settings:
    return replace(settings,
        catalog_path=_inside(root, settings.catalog_path),
        human_catalog_path=_inside(root, settings.human_catalog_path),
        review_family_knowledge_path=_inside(root, settings.review_family_knowledge_path),
        review_family_knowledge_manifest_path=_inside(root, settings.review_family_knowledge_manifest_path),
        human_knowledge_development_path=_inside(root, settings.human_knowledge_development_path),
        human_knowledge_development_manifest_path=_inside(
            root, settings.human_knowledge_development_manifest_path),
        ui_path=_inside(root, settings.ui_path),
        calibration_artifact=(
            _inside(root, settings.calibration_artifact) if settings.calibration_artifact else None),
        policy_artifact=_inside(root, settings.policy_artifact) if settings.policy_artifact else None,
    )


class HumanStorageResolverService(ResolverService):  # type: ignore[misc]
    def __init__(self, *args: Any, storage: HumanStorageHydration,
                 profile: HumanStorageProfile, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.storage = storage
        self.storage_profile = profile
        self._unavailable_callback: Any = None

    def bind_unavailable_callback(self, callback: Any) -> None:
        self._unavailable_callback = callback

    def probe_storage(self) -> float:
        try:
            return self.storage.probe()
        except StorageIntegrityError as error:
            if self._unavailable_callback is not None:
                self._unavailable_callback(error)
            raise DependencyUnavailable("human storage is unavailable") from error

    def resolve(self, request: ResolveRequest, *, request_id: str | None = None) -> ResolveResponse:
        integrity_ms = self.probe_storage()
        response = super().resolve(request, request_id=request_id)
        if response.debug is None:
            return response
        debug = response.debug.model_copy(update={
            "timings_ms": {**response.debug.timings_ms,
                           "human_storage_integrity": integrity_ms},
            "model_versions": {**response.debug.model_versions,
                "human_knowledge_storage": self.storage_profile.artifact_version,
                "human_knowledge_storage_sha256": self.storage_profile.artifact_sha256},
        })
        return response.model_copy(update={"debug": debug})


def build_service(settings: Settings, *, profile_path: Path, root: Path = ROOT,
                  environ: Mapping[str, str] | None = None,
                  repository_factory: RepositoryFactory = default_repository_factory,
                  allow_private_mock: bool = False) -> HumanStorageResolverService:
    if settings.backend != "offline":
        raise ValueError("experimental canonical backend must remain offline")
    if (settings.human_knowledge_retrieval_artifact_path is not None
            or settings.human_knowledge_identity_artifact_path is not None):
        raise ValueError("legacy human knowledge switches conflict with storage profile")
    absolute = _absolute_settings(settings, root)
    absolute.validate()
    profile = load_profile(profile_path, root=root, environ=environ,
                           allow_private_mock=allow_private_mock)
    storage = HumanStorageHydration(profile, environ=environ,
                                    repository_factory=repository_factory)
    math = load_human_knowledge_v4_config(profile.math_artifact_path,
        human_catalog_path=absolute.human_catalog_path,
        review_family_path=absolute.review_family_knowledge_path,
        development_pack_path=absolute.human_knowledge_development_path,
        development_manifest_path=absolute.human_knowledge_development_manifest_path,
        dense_dimensions=absolute.dense_dimensions, root=root)
    return HumanStorageResolverService(absolute, load_catalog(absolute.catalog_path), storage.catalog,
        human_knowledge_v4_config=math, storage=storage, profile=profile)


def create_app(settings: Settings | None = None, *, profile_path: Path | None = None,
               root: Path = ROOT, environ: Mapping[str, str] | None = None,
               repository_factory: RepositoryFactory = default_repository_factory,
               allow_private_mock: bool = False) -> FastAPI:
    environment = os.environ if environ is None else environ
    configured_path = environment.get(PROFILE_ENVIRONMENT, "").strip()
    selected = profile_path if profile_path is not None else (
        Path(configured_path) if configured_path else None)
    base_settings = settings or Settings.from_env()

    def factory(config: Settings) -> ResolverService:
        if selected is None:
            raise ValueError("explicit human storage profile path is required")
        return build_service(config, profile_path=selected, root=root, environ=environment,
            repository_factory=repository_factory, allow_private_mock=allow_private_mock)

    app = create_base_app(base_settings, service_factory=factory)

    def unavailable(error: Exception) -> None:
        app.state.service = None
        app.state.readiness_error = f"{type(error).__name__}: dependency unavailable"

    service = app.state.service
    if isinstance(service, HumanStorageResolverService):
        service.bind_unavailable_callback(unavailable)

    @app.middleware("http")  # type: ignore[untyped-decorator]
    async def storage_health_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        current = app.state.service
        if request.method == "GET" and request.url.path == "/health" \
                and isinstance(current, HumanStorageResolverService):
            try:
                current.probe_storage()
            except DependencyUnavailable:
                pass  # Callback latched app.state.service=None; base health emits safe 503.
        response = await call_next(request)
        if request.method != "GET" or request.url.path != "/health":
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        payload = json.loads(body)
        active = app.state.service
        profile = current.storage_profile if isinstance(current, HumanStorageResolverService) else None
        payload["dependencies"]["human_knowledge_storage"] = {
            "ready": isinstance(active, HumanStorageResolverService),
            "version": profile.artifact_version if profile else None,
            "detail": (
                f"{profile.mode}; immutable142 snapshot; complete integrity gate"
                if isinstance(active, HumanStorageResolverService) and profile else
                "configured human storage is unavailable"
            ),
        }
        headers = {key: value for key, value in response.headers.items()
                   if key.lower() not in {"content-length", "content-type"}}
        return JSONResponse(status_code=response.status_code, content=payload, headers=headers)

    return app


# Importing the explicit module is safe: without a profile it exposes a not-ready app, no fallback.
app = create_app()
