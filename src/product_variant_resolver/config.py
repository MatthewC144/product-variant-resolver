from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    catalog_path: Path = Path("data/catalog.json")
    benchmark_path: Path = Path("data/benchmark.json")
    ui_path: Path = Path("ui")
    database_url: str = "postgresql+psycopg://pvr:pvr@localhost:5432/pvr"
    backend: str = "offline"
    dense_provider: str = "hashing-v1"
    dense_dimensions: int = 192
    reranker_provider: str = "heuristic-v1"
    reranker_enabled: bool = False
    calibration_artifact: Path | None = None
    policy_artifact: Path | None = None
    policy_version: str = "fixture-v1-rrf-trained-v2"
    candidate_limit: int = 25
    debug_enabled: bool = True
    tracing_enabled: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        artifact = os.getenv("PVR_CALIBRATION_ARTIFACT", "").strip()
        policy_artifact = os.getenv("PVR_POLICY_ARTIFACT", "").strip()
        result = cls(
            catalog_path=Path(os.getenv("PVR_CATALOG_PATH", "data/catalog.json")),
            benchmark_path=Path(os.getenv("PVR_BENCHMARK_PATH", "data/benchmark.json")),
            ui_path=Path(os.getenv("PVR_UI_PATH", "ui")),
            database_url=os.getenv("PVR_DATABASE_URL", "postgresql+psycopg://pvr:pvr@localhost:5432/pvr"),
            backend=os.getenv("PVR_BACKEND", "offline"),
            dense_provider=os.getenv("PVR_DENSE_PROVIDER", "hashing-v1"),
            dense_dimensions=int(os.getenv("PVR_DENSE_DIMENSIONS", "192")),
            reranker_provider=os.getenv("PVR_RERANKER_PROVIDER", "heuristic-v1"),
            reranker_enabled=_bool("PVR_RERANKER_ENABLED", False),
            calibration_artifact=Path(artifact) if artifact else None,
            policy_artifact=Path(policy_artifact) if policy_artifact else None,
            policy_version=os.getenv("PVR_POLICY_VERSION", "fixture-v1-rrf-trained-v2"),
            candidate_limit=int(os.getenv("PVR_CANDIDATE_LIMIT", "25")),
            debug_enabled=_bool("PVR_DEBUG_ENABLED", True),
            tracing_enabled=_bool("PVR_TRACING_ENABLED", False),
        )
        result.validate()
        return result

    def validate(self) -> None:
        if self.backend not in {"offline", "postgres"}:
            raise ValueError("PVR_BACKEND must be offline or postgres")
        if not 32 <= self.dense_dimensions <= 4096:
            raise ValueError("PVR_DENSE_DIMENSIONS must be between 32 and 4096")
        if not 1 <= self.candidate_limit <= 25:
            raise ValueError("PVR_CANDIDATE_LIMIT must be between 1 and 25")
