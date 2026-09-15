from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_payload(duration: float = 1.0) -> dict:
    startup = {
        name: [{"sample": index, "duration_ms": duration, "error": None} for index in range(5)]
        for name in ("file", "postgres")
    }
    http_value = {
        "duration_ms": duration,
        "status": 200,
        "error": None,
        "integrity_ms": duration,
        "abstention": "no_match",
    }
    core_value = {"duration_ms": duration, "status": "ok", "error": None, "abstention": None}
    http = [
        {"case_id": str(index), "file": dict(http_value), "postgres": dict(http_value)}
        for index in range(199)
    ]
    core = [
        {"case_id": str(index), "file": dict(core_value), "postgres": dict(core_value)}
        for index in range(199)
    ]
    http_warmups = {
        name: [{"warmup": True, "status": 200, "error": None} for _ in range(3)]
        for name in ("file", "postgres")
    }
    core_warmups = {
        name: [{"warmup": True, "status": "ok", "error": None} for _ in range(3)]
        for name in ("file", "postgres")
    }
    contract = {
        "fresh_startup_samples_per_profile": 5,
        "http_samples_per_profile": 199,
        "core_samples_per_profile": 199,
        "warmups_before_http_per_profile": 3,
        "warmups_before_core_per_profile": 3,
        "startup_p95_max_ms": 5000,
        "http_p95_max_ms": 250,
        "integrity_p95_max_ms": 150,
        "core_p95_max_ms": 25,
        "percentile_method": "nearest_rank",
        "http_transport": "real_Uvicorn_loopback_not_TestClient",
        "concurrency": 1,
        "worker_count": 1,
        "timed_retries_or_budget_reruns": 0,
    }
    return {
        "schema_version": "pvr-human-storage-hsp4-raw-v1",
        "publication_status": "raw_unscored",
        "cleanup": {"errors": [], "remaining_owned_resources": []},
        "runner_result": {
            "measurement_contract": contract,
            "startup_samples": startup,
            "http_samples": http,
            "core_samples": core,
            "http_warmups": http_warmups,
            "core_warmups": core_warmups,
            "timed_retries": 0,
            "old_final_105_used": False,
            "real_3000_claim": False,
        },
    }


def test_nearest_rank_uses_ceiling_rank() -> None:
    module = load_script("score_human_storage_profile_cost.py")
    assert module.nearest_rank(list(range(1, 101)), 0.95) == 95
    assert module.nearest_rank([5, 1, 3, 2, 4], 0.95) == 5


def test_cost_scorer_requires_all_fixed_samples_and_budgets(tmp_path: Path) -> None:
    module = load_script("score_human_storage_profile_cost.py")
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(raw_payload()), encoding="utf-8")
    result = module.score(path)
    assert result["verdict"] == "PASS"
    assert result["metrics"]["startup"]["file"]["samples"] == 5
    assert result["metrics"]["http"]["postgres"]["samples"] == 199


def test_cost_scorer_keeps_fixed_budget_failure(tmp_path: Path) -> None:
    module = load_script("score_human_storage_profile_cost.py")
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(raw_payload(duration=300.0)), encoding="utf-8")
    result = module.score(path)
    assert result["verdict"] == "FAIL"
    assert result["metrics"]["http"]["file"]["pass"] is False
    assert result["metrics"]["core"]["postgres"]["pass"] is False


def test_hsp4_supervisor_is_isolated_and_credentials_are_generated() -> None:
    supervisor = (ROOT / "scripts/run_human_storage_profile_cost.py").read_text()
    verifier = (ROOT / "scripts/verify_human_storage_profile_cost.py").read_text()
    assert 'LABEL = "pvr.t49-4.owner"' in supervisor
    assert '"--internal"' in supervisor and '"--read-only"' in supervisor
    assert '"--tmpfs"' in supervisor and "secrets.token_hex(24)" in supervisor
    assert "docker-compose" not in supervisor and "volume create" not in supervisor
    assert "PASSWORD :password" not in verifier
    assert "timed_retries" in verifier
