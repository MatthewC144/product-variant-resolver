from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_raw() -> dict:
    human = {
        "candidates": [],
        "work": {"query_forms": 0},
        "character_index": {},
        "retrieval_artifact_version": "v4",
        "retrieval_artifact_sha256": "a" * 64,
        "model_version": "human-knowledge-hybrid-v4",
    }
    body = {
        "status": "no_match",
        "canonical_uuid": None,
        "canonical_id": None,
        "confidence": 0.0,
        "reason": "insufficient_evidence",
        "product": None,
        "policy_version": "fixture-v1-rrf-trained-v2",
    }
    rows = []
    types = (
        ["positive_family"] * 168
        + ["merge_control"] * 4
        + ["hold_control"] * 7
        + ["unrelated_control"] * 20
    )
    for index, case_type in enumerate(types):
        request_id = f"hsp3-{index:03d}-0123456789ab"
        view = {"status": 200, "request_id": request_id, "canonical_body": body, "human": human}
        rows.append(
            {
                "case_id": f"case-{index}",
                "case_type": case_type,
                "request_id": request_id,
                "file": copy.deepcopy(view),
                "postgres": copy.deepcopy(view),
                "default": {"status": 200, "request_id": request_id, "canonical_body": body},
            }
        )
    startup = [
        {"case": str(index), "health_status": 503, "resolve_status": 503} for index in range(10)
    ]
    post = [
        {
            "case": str(index),
            "first_status": 503,
            "after_restore_health": 503,
            "after_restore_resolve": 503,
        }
        for index in range(4)
    ]
    invalid = [
        {"case": name, "status": status, "storage_probes": 0}
        for name, status in {
            "malformed_json": 400,
            "wrong_content_type": 415,
            "blank_title": 422,
            "title_501": 422,
            "debug_disabled": 422,
        }.items()
    ]
    return {
        "schema_version": "pvr-human-storage-hsp3-raw-v1",
        "publication_status": "raw_unscored",
        "cleanup": {"errors": [], "remaining_owned_resources": []},
        "runner_result": {
            "correctness_rows": rows,
            "reader_role": {
                "attributes": {
                    "rolsuper": False,
                    "rolinherit": False,
                    "rolcreaterole": False,
                    "rolcreatedb": False,
                    "rolcanlogin": True,
                },
                "table_privileges": {"hk_document": ["SELECT"], "hk_snapshot": ["SELECT"]},
                "write_denials": [{"denied": True, "sqlstate": "42501"} for _ in range(4)],
            },
            "startup_failures": startup,
            "poststartup_failures": post,
            "invalid_http": invalid,
            "canonical_before_sha256": "b" * 64,
            "canonical_after_sha256": "b" * 64,
            "source_and_image_binding": True,
        },
    }


def test_run_profiles_are_runtime_ready_and_keep_database_url_external() -> None:
    module = load_script("freeze_human_storage_hsp3_run.py")
    template = json.loads(module.TEMPLATE.read_bytes())
    database = "pvr_t49_2_0123456789ab"
    file_profile = module.profile(template, mode="file_snapshot_reference", database=database)
    db_profile = module.profile(template, mode="postgres_snapshot_experiment", database=database)
    assert file_profile["ready_for_real_outputs"] is True
    assert file_profile["status"] == "source_and_runtime_frozen_for_authorized_isolated_run"
    assert file_profile["database"] is None
    assert db_profile["database"] == {
        "url_environment": "PVR_HUMAN_STORAGE_TEST_DATABASE_URL",
        "expected_database": database,
    }
    assert len(db_profile["runtime_image_ids"]) == 2
    assert set(db_profile["database"]) == {"url_environment", "expected_database"}
    assert "postgresql+" not in json.dumps(db_profile["database"])


def test_scorer_accepts_exact199_and_never_runs_retrieval(tmp_path: Path) -> None:
    module = load_script("score_human_storage_profile_sql.py")
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(synthetic_raw()), encoding="utf-8")
    result = module.score(raw)
    assert result["verdict"] == "PASS"
    assert result["exact_parity_cases"] == 199
    assert result["case_type_counts"] == {
        "positive_family": 168,
        "merge_control": 4,
        "hold_control": 7,
        "unrelated_control": 20,
    }


def test_scorer_rejects_one_candidate_mismatch(tmp_path: Path) -> None:
    module = load_script("score_human_storage_profile_sql.py")
    payload = synthetic_raw()
    payload["runner_result"]["correctness_rows"][17]["postgres"]["human"]["candidates"] = [
        {"knowledge_type": "review_family", "review_family_id": "changed"}
    ]
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="parity"):
        module.score(raw)


def test_supervisor_has_strict_owned_cleanup_and_no_compose_or_volume_path() -> None:
    source = (ROOT / "scripts/run_human_storage_profile_sql.py").read_text()
    verifier = (ROOT / "scripts/verify_human_storage_profile_sql.py").read_text()
    assert 'LABEL = "pvr.t49-3.owner"' in source
    assert '"--internal"' in source and '"--read-only"' in source
    assert '"--tmpfs"' in source and '"--force"' in source
    assert "docker-compose" not in source and "volume create" not in source
    assert "pvr-hsp3-bootstrap-only" not in source
    assert "PASSWORD :password" not in verifier
    assert "remaining_owned_resources" in source
