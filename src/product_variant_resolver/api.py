from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import Settings
from .retrieval import RetrievalUnavailable
from .schemas import (
    DependencyHealth, ErrorBody, ErrorResponse, HealthResponse, ResolveRequest, ResolveResponse,
)
from .service import DependencyUnavailable, ResolverService

LOGGER = logging.getLogger("product_variant_resolver")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _request_id(value: str | None) -> str:
    return value if value and REQUEST_ID_RE.fullmatch(value) else str(uuid.uuid4())


def _error(status: int, code: str, message: str, request_id: str, details: list[object] | None = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(
        code=code, message=message, request_id=request_id, details=details or [],
    ))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def create_app(
    settings: Settings | None = None,
    service_factory: Callable[[Settings], ResolverService] = ResolverService.from_settings,
) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Product Variant Resolver", version="0.1.0")
    app.state.settings = settings
    app.state.service = None
    app.state.readiness_error = None
    try:
        app.state.service = service_factory(settings)
    except Exception as error:
        app.state.readiness_error = f"{type(error).__name__}: dependency unavailable"

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = _request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        content_type = request.headers.get("content-type", "")
        if request.method == "POST" and request.url.path == "/resolve" and content_type and "application/json" not in content_type:
            return _error(415, "unsupported_content_type", "content type must be application/json", request_id)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        errors = error.errors()
        malformed = any(item.get("type") == "json_invalid" for item in errors)
        details = [{"type": item.get("type"), "loc": list(item.get("loc", ())),
                    "msg": item.get("msg")} for item in errors]
        return _error(400 if malformed else 422, "malformed_json" if malformed else "invalid_request",
                      "request body is malformed" if malformed else "request validation failed",
                      request_id, details)

    @app.exception_handler(ValidationError)
    async def pydantic_error(request: Request, error: ValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        details = [{"type": item.get("type"), "loc": list(item.get("loc", ())),
                    "msg": item.get("msg")} for item in error.errors()]
        return _error(422, "invalid_request", "request validation failed", request_id, details)

    @app.post(
        "/resolve", response_model=ResolveResponse,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def resolve(payload: ResolveRequest, request: Request) -> ResolveResponse | JSONResponse:
        if payload.debug and not settings.debug_enabled:
            return _error(422, "debug_disabled", "debug output is disabled", request.state.request_id)
        service: ResolverService | None = app.state.service
        if service is None:
            return _error(503, "resolver_not_ready", "resolver dependencies are unavailable", request.state.request_id)
        try:
            return service.resolve(payload, request_id=request.state.request_id)
        except (DependencyUnavailable, RetrievalUnavailable):
            return _error(503, "dependency_unavailable", "a required dependency is unavailable", request.state.request_id)
        except Exception:
            LOGGER.exception("resolve_failed request_id=%s title_length=%d", request.state.request_id, len(payload.title))
            return _error(500, "internal_error", "an unexpected error occurred", request.state.request_id)

    @app.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
    async def health() -> HealthResponse | JSONResponse:
        service: ResolverService | None = app.state.service
        ready = service is not None
        catalog = DependencyHealth(
            ready=ready, version=service.catalog.version if service else None,
            detail=None if ready else app.state.readiness_error,
        )
        dependencies = {
            "catalog": catalog,
            "human_catalog": DependencyHealth(
                ready=ready,
                version=service.human_catalog.version if service else None,
                detail=(
                    "human-reviewed draft; retrieval evidence only, not canonical identity"
                    if ready else app.state.readiness_error
                ),
            ),
            "human_knowledge_index": DependencyHealth(
                ready=ready,
                version=service.human_knowledge.version if service else None,
            ),
            "sparse_index": DependencyHealth(
                ready=ready,
                version=service.sparse_retriever.version if service else None,
            ),
            "dense_index": DependencyHealth(
                ready=ready,
                version=service.dense_retriever.version if service else None,
            ),
            "reranker": DependencyHealth(
                ready=ready,
                version=(settings.reranker_provider if settings.reranker_enabled else "disabled")
                if ready else None,
                detail=(None if settings.reranker_enabled
                        else "heuristic-v1 is available for offline ablation but not the default path"),
            ),
            "calibrator": DependencyHealth(
                ready=ready,
                version=service.calibrator.artifact.artifact_version if service else None,
            ),
            "database": DependencyHealth(
                ready=ready,
                version=service.database_version if service else None,
                detail=(
                    "canonical sparse and exact dense retrieval use PostgreSQL"
                    if ready and settings.backend == "postgres" else None
                ),
            ),
        }
        result = HealthResponse(alive=True, ready=ready and all(item.ready for item in dependencies.values()),
                                dependencies=dependencies)
        return result if result.ready else JSONResponse(status_code=503, content=result.model_dump(mode="json"))

    # Register the catch-all static mount after every API/OpenAPI route so the
    # diagnostic UI cannot shadow `/resolve`, `/health`, `/docs`, or `/openapi.json`.
    # Missing UI assets do not make the resolver unavailable; this keeps the API
    # usable in minimal library installations while the container always copies UI.
    if settings.ui_path.is_dir() and (settings.ui_path / "index.html").is_file():
        app.mount("/", StaticFiles(directory=settings.ui_path, html=True), name="debug-ui")

    return app


app = create_app()
