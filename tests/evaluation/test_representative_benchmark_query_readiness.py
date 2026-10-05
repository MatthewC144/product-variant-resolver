from __future__ import annotations

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
    private_directory = root / RHB / "local-query-authoring-v1"
    for filename in (
        "rhb-t5-owner-authorization.json",
        "query-pack-authoring-input.json",
        "query-pack.json",
    ):
        (private_directory / filename).unlink(missing_ok=True)
    (root / RHB / "query-pack-manifest.json").unlink(missing_ok=True)
    return root


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_real_readiness_closes_after_owner_gate_without_writing() -> None:
    watched = [
        ROOT / RHB / "query-pack.json",
        ROOT / RHB / "query-pack-manifest.json",
        ROOT / RHB / "labels.json",
        ROOT / RHB / "held-labels.json",
        ROOT / RHB / "labels-manifest.json",
    ]
    before = {path: path.exists() for path in watched}

    for _ in range(2):
        with pytest.raises(
            QueryReadinessError,
            match="owner authorization already exists; pre-authoring readiness is closed",
        ):
            build_rhb_t5_query_readiness(ROOT)
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


def test_existing_private_label_artifact_fails_closed(isolated_root: Path) -> None:
    label_path = isolated_root / RHB / "local-query-authoring-v1/labels.json"
    label_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(QueryReadinessError, match="artifacts already exist"):
        build_rhb_t5_query_readiness(isolated_root)


def test_car_t6_authority_tamper_fails_closed(isolated_root: Path) -> None:
    authority_path = isolated_root / RHB / "canonical-authority-reaudit-v1.json"
    payload = _read(authority_path)
    payload["records"][0]["review_reason"] = "tampered"
    authority_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryReadinessError, match="authority checksum drift"):
        build_rhb_t5_query_readiness(isolated_root)


def test_cli_closes_after_owner_gate() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "owner authorization already exists; pre-authoring readiness is closed" in result.stderr


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
