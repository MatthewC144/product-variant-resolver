from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from product_variant_resolver.representative_benchmark_query_readiness import (
    QueryReadinessError,
    build_rhb_t5_query_readiness,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/validate_representative_hard_benchmark_query_readiness.py"
RHB = Path("data/evaluation/representative-hard-benchmark-v1")


@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(ROOT / "data", root / "data")
    return root


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_real_readiness_is_deterministic_read_only_and_honestly_blocked() -> None:
    watched = [
        ROOT / RHB / "query-pack.json",
        ROOT / RHB / "query-pack-manifest.json",
        ROOT / RHB / "labels.json",
        ROOT / RHB / "held-labels.json",
        ROOT / RHB / "labels-manifest.json",
    ]
    before = {path: path.exists() for path in watched}

    first = build_rhb_t5_query_readiness(ROOT)
    second = build_rhb_t5_query_readiness(ROOT)

    assert first == second
    assert first.status == "blocked_pending_pre_authoring_repairs_and_owner_gate"
    assert first.source_record_count == 101
    assert first.nonblank_query_count == 91
    assert first.unique_nonblank_query_count == 91
    assert first.duplicate_nonblank_query_count == 0
    assert first.candidate_shortfall == 0
    assert first.source_rows_with_pipeline_outputs == 101
    assert first.source_rows_with_human_labels == 101
    assert first.source_rows_with_failure_categories == 99
    assert first.approved_exact_variant_count == 20
    assert first.qualifying_family_count == 7
    assert not first.public_raw_query_pack_authorized
    assert first.public_aggregate_metadata_authorized
    assert first.output_blind_projection_required
    assert first.query_contract_split_phase_alignment_required
    assert not first.current_session_eligible_for_authoring
    assert not first.rhb_t5_authorized
    assert {path: path.exists() for path in watched} == before


def test_human_source_checksum_drift_fails_closed(isolated_root: Path) -> None:
    source_path = isolated_root / "data/human_labeled_names.json"
    payload = _read(source_path)
    payload["records"][0]["initial_name"] = "tampered query"
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryReadinessError, match="checksum drift"):
        build_rhb_t5_query_readiness(isolated_root)


def test_existing_query_or_label_artifact_fails_closed(isolated_root: Path) -> None:
    query_path = isolated_root / RHB / "query-pack.json"
    query_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(QueryReadinessError, match="artifacts already exist"):
        build_rhb_t5_query_readiness(isolated_root)


def test_car_t6_authority_tamper_fails_closed(isolated_root: Path) -> None:
    authority_path = isolated_root / RHB / "canonical-authority-reaudit-v1.json"
    payload = _read(authority_path)
    payload["records"][0]["review_reason"] = "tampered"
    authority_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryReadinessError, match="authority checksum drift"):
        build_rhb_t5_query_readiness(isolated_root)


def test_cli_emits_the_same_hash_bound_report() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    expected = build_rhb_t5_query_readiness(ROOT)
    assert payload == expected.model_dump(mode="json")
    unhashed = dict(payload)
    digest = unhashed.pop("readiness_sha256")
    canonical = json.dumps(
        unhashed, ensure_ascii=False, indent=2, sort_keys=True, separators=(",", ": ")
    )
    assert digest == hashlib.sha256(f"{canonical}\n".encode()).hexdigest()


def test_readiness_module_has_no_runtime_or_network_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_query_readiness.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import selenium",
        "import fastapi",
        "ResolverService",
        ".resolve(",
    )
    assert all(token not in source for token in forbidden)
