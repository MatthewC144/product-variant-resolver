from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

import product_variant_resolver.representative_benchmark_query_projection as projection_module
from product_variant_resolver.representative_benchmark_query_projection import (
    IGNORE_RULE,
    MANIFEST_REFERENCE,
    PROJECTION_REFERENCE,
    OutputBlindSourceProjection,
    ProjectionError,
    build_output_blind_projection,
    materialize_output_blind_projection,
    validate_materialized_projection,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/build_representative_hard_benchmark_query_projection.py"


@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copyfile(ROOT / ".gitignore", root / ".gitignore")
    (root / PROJECTION_REFERENCE).unlink(missing_ok=True)
    (root / MANIFEST_REFERENCE).unlink(missing_ok=True)
    return root


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_projection_is_query_only_deterministic_and_aggregate_public() -> None:
    first_projection, first_manifest = build_output_blind_projection(ROOT)
    second_projection, second_manifest = build_output_blind_projection(ROOT)

    assert first_projection == second_projection
    assert first_manifest == second_manifest
    assert len(first_projection.records) == 91
    assert first_projection.excluded_blank_query_count == 10
    assert first_projection.field_allowlist == ["source_record_ref", "query"]
    assert all(
        set(record.model_dump()) == {"source_record_ref", "query"}
        for record in first_projection.records
    )
    assert not first_projection.resolver_output_viewed
    assert not first_projection.benchmark_labels_loaded
    assert first_manifest.record_count == 91
    assert set(first_manifest.model_dump(by_alias=True)) == {
        "schema",
        "sha256",
        "record_count",
        "non_sensitive_aggregate",
        "non_sensitive_summary",
    }
    aggregate = first_manifest.non_sensitive_aggregate
    assert not aggregate.contains_pipeline_outputs
    assert not aggregate.contains_human_labels
    assert not aggregate.contains_failure_categories
    public_text = json.dumps(
        first_manifest.model_dump(mode="json", by_alias=True), ensure_ascii=False
    )
    assert all(record.query not in public_text for record in first_projection.records)


def test_projection_contract_rejects_adjacent_output_or_label_fields() -> None:
    projection, _manifest = build_output_blind_projection(ROOT)
    payload = projection.model_dump(mode="json")
    payload["records"][0]["pipeline_outputs"] = {"candidate": "leak"}
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        OutputBlindSourceProjection.model_validate(payload)

    payload = projection.model_dump(mode="json")
    payload["records"][0]["human_label_casting"] = "leak"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        OutputBlindSourceProjection.model_validate(payload)


def test_materialization_is_private_atomic_and_reproducible(isolated_root: Path) -> None:
    assert materialize_output_blind_projection(isolated_root) == "created"
    private_path = isolated_root / PROJECTION_REFERENCE
    public_path = isolated_root / MANIFEST_REFERENCE
    assert stat.S_IMODE(private_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(private_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(public_path.stat().st_mode) == 0o644
    projection, manifest = validate_materialized_projection(isolated_root)
    assert manifest.record_count == len(projection.records) == 91
    assert materialize_output_blind_projection(isolated_root) == "unchanged"
    assert materialize_output_blind_projection(isolated_root, check=True) == "unchanged"


def test_missing_ignore_rule_and_private_only_partial_output_fail_closed(
    isolated_root: Path,
) -> None:
    ignore_path = isolated_root / ".gitignore"
    rules = [
        line for line in ignore_path.read_text(encoding="utf-8").splitlines() if line != IGNORE_RULE
    ]
    ignore_path.write_text("\n".join(rules) + "\n", encoding="utf-8")
    with pytest.raises(ProjectionError, match="gitignore"):
        materialize_output_blind_projection(isolated_root)

    ignore_path.write_text((ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    private_path = isolated_root / PROJECTION_REFERENCE
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ProjectionError, match="without its public manifest"):
        materialize_output_blind_projection(isolated_root)


def test_tracked_public_manifest_can_rebuild_ignored_private_projection(
    isolated_root: Path,
) -> None:
    assert materialize_output_blind_projection(isolated_root) == "created"
    private_path = isolated_root / PROJECTION_REFERENCE
    public_path = isolated_root / MANIFEST_REFERENCE
    public_bytes = public_path.read_bytes()
    private_path.unlink()

    with pytest.raises(ProjectionError, match="not materialized"):
        materialize_output_blind_projection(isolated_root, check=True)
    assert materialize_output_blind_projection(isolated_root) == "created"
    assert public_path.read_bytes() == public_bytes
    assert validate_materialized_projection(isolated_root)[1].record_count == 91


def test_second_replace_failure_rolls_back_new_outputs(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected projection failure")
        real_replace(source, target)

    monkeypatch.setattr(projection_module.os, "replace", fail_second)
    with pytest.raises(OSError, match="injected projection"):
        materialize_output_blind_projection(isolated_root)
    assert not (isolated_root / PROJECTION_REFERENCE).exists()
    assert not (isolated_root / MANIFEST_REFERENCE).exists()


def test_source_drift_and_cli_check_fail_closed(isolated_root: Path) -> None:
    source_path = isolated_root / "data/human_labeled_names.json"
    payload = _read(source_path)
    payload["records"][0]["initial_name"] = "tampered"
    source_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProjectionError, match="checksum drift"):
        build_output_blind_projection(isolated_root)

    clean_root = isolated_root.parent / "clean-repo"
    clean_root.mkdir()
    shutil.copytree(ROOT / "data", clean_root / "data")
    shutil.copyfile(ROOT / ".gitignore", clean_root / ".gitignore")
    (clean_root / PROJECTION_REFERENCE).unlink(missing_ok=True)
    (clean_root / MANIFEST_REFERENCE).unlink(missing_ok=True)
    command = [sys.executable, str(CLI), "--root", str(clean_root)]
    created = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert created.returncode == 0, created.stderr
    assert created.stdout.strip() == "created"
    checked = subprocess.run(
        [*command, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout.strip() == "unchanged"


def test_projection_module_has_no_runtime_or_network_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_query_projection.py"
    ).read_text(encoding="utf-8")
    forbidden = ("import requests", "import selenium", "import fastapi", "ResolverService")
    assert all(token not in source for token in forbidden)
