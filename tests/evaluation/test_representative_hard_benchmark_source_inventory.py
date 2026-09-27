from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_representative_hard_benchmark_source_inventory.py"
OUTPUT_DIR = ROOT / "data" / "evaluation" / "representative-hard-benchmark-v1"


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rhb_source_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_baseline_reproduces_counts_and_authority_boundaries() -> None:
    module = _load_builder()
    inventory, manifest, _ = module.build_baseline(ROOT)

    assert manifest["record_counts"] == {
        "fixture_benchmark_cases": 100,
        "fixture_catalog_products": 120,
        "human_labeled_scans": 101,
        "human_scan_alignments": 101,
        "owner_local_release_observations": 1763,
        "wiki_pilot_rows": 100,
    }
    assert inventory["alignment_summary"] == {
        "exact_canonical": 0,
        "family_only": 2,
        "unmapped": 99,
    }
    assert inventory["network_collection_performed"] is False
    assert inventory["private_source_rows_copied"] is False
    assert inventory["owner_source_gate"] == "pending_RHB_T3"

    by_id = {entry["source_id"]: entry for entry in inventory["entries"]}
    assert set(by_id) == {
        "fixture-v1-benchmark",
        "fixture-v1-catalog",
        "human-labeled-real-noisy-v1",
        "human-labeled-to-fixture-alignment-v1",
        "owner-local-release-snapshot-2023-2026-v1",
        "fandom-hot-wheels-2025-pilot-r790665-v1",
    }
    assert all(entry["owner_decision"] == "pending" for entry in by_id.values())
    required_state_fields = {
        "current_publication_state",
        "current_repository_state",
        "known_rights_evidence",
        "prospective_benchmark_use_status",
        "prospective_redistribution_status",
    }
    assert all(required_state_fields <= set(entry) for entry in by_id.values())
    assert all(
        {"authority_eligibility", "authority_evidence_level"} <= set(entry)
        for entry in by_id.values()
    )
    assert by_id["human-labeled-real-noisy-v1"]["benchmark_uses"] == ["none"]
    assert (
        by_id["owner-local-release-snapshot-2023-2026-v1"]["redistribution_scope"]
        == "aggregate_only"
    )
    assert "exact_variant_authority" not in {
        use for entry in by_id.values() for use in entry["benchmark_uses"]
    }
    assert by_id["fixture-v1-catalog"]["authority_eligibility"] == ("synthetic_regression_only")
    assert by_id["human-labeled-real-noisy-v1"]["authority_eligibility"] == "prohibited"
    assert by_id["human-labeled-to-fixture-alignment-v1"]["authority_evidence_level"] == (
        "family_only"
    )
    assert (
        by_id["owner-local-release-snapshot-2023-2026-v1"]["authority_evidence_level"]
        == "staging_only"
    )
    assert (
        by_id["fandom-hot-wheels-2025-pilot-r790665-v1"]["authority_evidence_level"]
        == "staging_only"
    )


def test_human_artifacts_separate_current_publication_from_future_permission() -> None:
    module = _load_builder()
    inventory, manifest, _ = module.build_baseline(ROOT)
    by_id = {entry["source_id"]: entry for entry in inventory["entries"]}

    for source_id, path in (
        ("human-labeled-real-noisy-v1", "data/human_labeled_names.json"),
        (
            "human-labeled-to-fixture-alignment-v1",
            "data/human_labeled_catalog_alignment.json",
        ),
    ):
        entry = by_id[source_id]
        assert entry["current_repository_state"] == "tracked_public_repository"
        assert entry["current_publication_state"] == "row_level_public"
        assert entry["retention_scope"] == "public"
        assert entry["redistribution_scope"] == "public_rows"
        assert entry["known_rights_evidence"]["status"] != "approved"
        assert entry["prospective_benchmark_use_status"].startswith("blocked_pending_RHB_T3")
        assert entry["prospective_redistribution_status"].startswith("blocked_pending_RHB_T3")
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    tracked_contract = {
        item["path"] for item in manifest["repository_tracking_contract"]["artifacts"]
    }
    assert "data/human_labeled_names.json" in tracked_contract
    assert "data/human_labeled_catalog_alignment.json" in tracked_contract


def test_every_tracking_contract_artifact_is_actually_git_tracked() -> None:
    module = _load_builder()
    _, manifest, _ = module.build_baseline(ROOT)
    tracked_paths = [item["path"] for item in manifest["repository_tracking_contract"]["artifacts"]]

    for path in tracked_paths:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    public_owner_summary = "reports/local-release-staging-v1/manifest.json"
    ignored_owner_summary = (
        "data/external/hot-wheels-wiki/local-release-casting-review-v1/manifest.json"
    )
    input_paths = {item["path"] for item in manifest["input_artifacts"]}
    assert public_owner_summary in tracked_paths
    assert public_owner_summary in input_paths
    assert ignored_owner_summary not in tracked_paths
    assert ignored_owner_summary not in input_paths
    assert (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", ignored_owner_summary],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).returncode
        != 0
    )
    assert (
        subprocess.run(
            ["git", "check-ignore", "-q", ignored_owner_summary],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def test_checked_in_outputs_are_byte_identical_to_builder() -> None:
    module = _load_builder()
    inventory, manifest, evidence = module.build_baseline(ROOT)
    inventory_bytes = module._stable_json(inventory)
    manifest_bytes = module._stable_json(manifest)

    assert (OUTPUT_DIR / "source-inventory.json").read_bytes() == inventory_bytes
    assert (OUTPUT_DIR / "source-inventory-manifest.json").read_bytes() == manifest_bytes
    assert (
        ROOT / "docs" / "evidence" / "representative-hard-benchmark-source-baseline.md"
    ).read_text(encoding="utf-8") == evidence
    assert manifest["inventory_sha256"] == hashlib.sha256(inventory_bytes).hexdigest()
    assert module.materialize(root=ROOT, check=True) == "unchanged"
    assert module.materialize(root=ROOT, check=False) == "unchanged"


def test_private_owner_rows_are_not_copied_to_public_outputs() -> None:
    combined = (
        (OUTPUT_DIR / "source-inventory.json").read_text(encoding="utf-8")
        + (OUTPUT_DIR / "source-inventory-manifest.json").read_text(encoding="utf-8")
        + (
            ROOT / "docs" / "evidence" / "representative-hard-benchmark-source-baseline.md"
        ).read_text(encoding="utf-8")
    )
    assert '"records"' not in combined
    assert '"casting_name"' not in combined
    assert '"source_model_label"' not in combined
    assert "Volvo P1800 Gasser" not in combined


def test_drift_fails_closed_without_replacing_outputs(tmp_path: Path) -> None:
    module = _load_builder()
    root = tmp_path / "repo"
    for relative in (
        "scripts/build_representative_hard_benchmark_source_inventory.py",
        "data/manifest.json",
        "data/benchmark.json",
        "data/catalog.json",
        "data/human_labeled_names.json",
        "data/human_labeled_names_manifest.json",
        "data/human_labeled_catalog_alignment.json",
        "data/human_labeled_catalog_alignment_manifest.json",
        "reports/local-release-staging-v1/manifest.json",
        "data/external/hot-wheels-wiki/pilot-2025/manifest.json",
        "data/external/hot-wheels-wiki/pilot-2025/normalized.json",
        "data/external/hot-wheels-wiki/pilot-2025/raw.json",
    ):
        source = ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    # A fresh-clone-shaped directory containing only public inputs can build the baseline.
    module.build_baseline(root)

    alignment_path = root / "data" / "human_labeled_catalog_alignment.json"
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    alignment["alignments"][0]["canonical_uuid"] = "not-allowed"
    alignment_path.write_text(json.dumps(alignment), encoding="utf-8")

    with pytest.raises(module.BaselineError):
        module.build_baseline(root)


def test_builder_has_no_network_or_browser_dependency() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = ("requests", "httpx", "urllib", "socket", "selenium", "playwright")
    assert not any(f"import {name}" in source or f"from {name}" in source for name in forbidden)
