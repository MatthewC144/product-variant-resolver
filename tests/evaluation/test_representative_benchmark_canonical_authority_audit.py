from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from pydantic import ValidationError

from product_variant_resolver.canonical_authority_packet import (
    reconstruct_frozen_parent_catalog,
)
from product_variant_resolver.representative_benchmark import (
    ContractError,
    canonical_record_sha256,
    validate_canonical_authority,
    validate_canonical_authority_manifest,
    validate_source_decisions,
    validate_t1_inventory_files,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "evaluation" / "representative-hard-benchmark-v1"
SCRIPT = ROOT / "scripts" / "build_representative_hard_benchmark_canonical_authority.py"


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rhb_canonical_authority", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validated_dependencies() -> tuple[Any, Any]:
    inventory_payload = _load(OUTPUT_DIR / "source-inventory.json")
    inventory_manifest = _load(OUTPUT_DIR / "source-inventory-manifest.json")
    inventory, _ = validate_t1_inventory_files(inventory_payload, inventory_manifest)
    decisions = validate_source_decisions(
        _load(OUTPUT_DIR / "source-decisions.json"),
        inventory_payload=inventory_payload,
        wiki_source_payload=_load(
            ROOT / "data/external/hot-wheels-wiki/pilot-2025/normalized.json"
        ),
    )
    return inventory, decisions


def _validate(
    manifest: dict[str, Any],
    authority: dict[str, Any],
    *,
    catalog: dict[str, Any] | None = None,
) -> None:
    inventory, decisions = _validated_dependencies()
    validate_canonical_authority_manifest(
        manifest,
        authority_payload=authority,
        catalog_payload=catalog or _load(ROOT / "data/catalog.json"),
        human_catalog_payload=_load(ROOT / "data/human_backed_catalog.json"),
        inventory=inventory,
        source_decisions=decisions,
        input_sha256={item["path"]: item["sha256"] for item in manifest["input_artifacts"]},
    )


def test_checked_in_authority_audit_records_the_honest_blocked_gate() -> None:
    authority = _load(OUTPUT_DIR / "canonical-authority.json")
    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    _validate(manifest, authority)

    assert authority == {
        "authority_version": "representative-hard-benchmark-canonical-authority-v1",
        "publication_scope": "public",
        "records": [],
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
    }
    assert manifest["status"] == "complete"
    assert manifest["network_requests"] == 0
    assert manifest["resolver_output_consulted"] is False
    assert manifest["benchmark_labels_consulted"] is False
    assert manifest["canonical_catalog"] == {
        "catalog_path": "data/catalog.json",
        "catalog_sha256": "0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261",
        "catalog_version": "fixture-v1",
        "independently_supported_exact_count": 0,
        "product_count": 120,
        "synthetic_regression_only_excluded_count": 120,
    }
    assert manifest["supporting_human_catalog"]["casting_count"] == 97
    assert manifest["supporting_human_catalog"]["provisional_variant_count"] == 100
    assert manifest["supporting_human_catalog"]["exact_variant_count"] == 0
    assert manifest["current_source_count"] == 11
    assert manifest["current_source_exact_authority_rejected_count"] == 11
    assert manifest["eligible_exact_variant_count"] == 0
    assert manifest["pilot_usable_exact_variant_count"] == 0
    assert manifest["same_casting_multi_release_family_count"] == 0
    assert manifest["thresholds"] == {
        "exact_variant_shortfall": 20,
        "family_shortfall": 4,
        "minimum_pilot_usable_exact_variants": 20,
        "minimum_same_casting_multi_release_families": 4,
        "observed_pilot_usable_exact_variants": 0,
        "observed_same_casting_multi_release_families": 0,
    }
    assert manifest["gate_result"] == "blocked_insufficient_exact_authority"
    assert manifest["next_allowed_step"] == "obtain_new_authorized_exact_variant_evidence"
    assert all(source["eligible_exact_variant_count"] == 0 for source in manifest["source_audit"])
    assert all(
        source["exact_authority_decision"] == "rejected" for source in manifest["source_audit"]
    )


def test_builder_is_deterministic_and_checked_in_outputs_are_unchanged() -> None:
    module = _load_builder()
    first = module.build_audit(ROOT)
    second = module.build_audit(ROOT)
    assert first == second
    assert (
        module.stable_json_bytes(first[0]) == (OUTPUT_DIR / "canonical-authority.json").read_bytes()
    )
    assert (
        module.stable_json_bytes(first[1])
        == (OUTPUT_DIR / "canonical-authority-manifest.json").read_bytes()
    )
    completed = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(SCRIPT), "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "unchanged"


def test_manifest_rejects_partial_status_and_unknown_fields() -> None:
    authority = _load(OUTPUT_DIR / "canonical-authority.json")
    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["status"] = "partial"
    with pytest.raises(ValidationError, match="status"):
        _validate(manifest, authority)

    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["undeclared_override"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _validate(manifest, authority)


def test_manifest_rejects_stale_authority_catalog_and_input_hashes() -> None:
    authority = _load(OUTPUT_DIR / "canonical-authority.json")
    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["authority_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="authority checksum"):
        _validate(manifest, authority)

    catalog = _load(ROOT / "data/catalog.json")
    catalog["products"][0]["color"] = "tampered"
    with pytest.raises(ContractError, match="catalog checksum"):
        _validate(
            _load(OUTPUT_DIR / "canonical-authority-manifest.json"), authority, catalog=catalog
        )

    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["input_artifacts"][0]["sha256"] = "f" * 64
    inventory, decisions = _validated_dependencies()
    expected_inputs = {
        item["path"]: item["sha256"]
        for item in _load(OUTPUT_DIR / "canonical-authority-manifest.json")["input_artifacts"]
    }
    with pytest.raises(ContractError, match="input set or checksum is stale"):
        validate_canonical_authority_manifest(
            manifest,
            authority_payload=authority,
            catalog_payload=_load(ROOT / "data/catalog.json"),
            human_catalog_payload=_load(ROOT / "data/human_backed_catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
            input_sha256=expected_inputs,
        )


def test_source_audit_rejects_missing_reordered_or_promoted_sources() -> None:
    authority = _load(OUTPUT_DIR / "canonical-authority.json")
    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["source_audit"] = manifest["source_audit"][:-1]
    manifest["current_source_count"] -= 1
    manifest["current_source_exact_authority_rejected_count"] -= 1
    with pytest.raises(ContractError, match="cover every owner-confirmed source"):
        _validate(manifest, authority)

    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["source_audit"] = list(reversed(manifest["source_audit"]))
    with pytest.raises(ContractError, match="stable source-id ordering"):
        _validate(manifest, authority)

    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    manifest["source_audit"][0]["authority_eligibility"] = "exact_variant_authority_candidate"
    with pytest.raises(ContractError, match="eligibility changed"):
        _validate(manifest, authority)


def test_fixture_uuid_cannot_be_inferred_into_exact_authority() -> None:
    catalog = reconstruct_frozen_parent_catalog(ROOT)[0].model_dump(mode="json")
    product = catalog["products"][0]
    authority = {
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
        "authority_version": "forged-authority-v1",
        "publication_scope": "public",
        "records": [
            {
                "authority_id": "forged-fixture-authority",
                "canonical_uuid": product["canonical_uuid"],
                "canonical_catalog_version": catalog["catalog_version"],
                "catalog_record_sha256": canonical_record_sha256(product),
                "variant_fields_verified": [
                    "casting",
                    "release_year",
                    "series",
                    "color",
                    "collector_number",
                    "series_position",
                    "identifiers",
                ],
                "independent_evidence_refs": ["fixture-is-not-independent-evidence"],
                "evidence_source_ids": ["fixture-v1-catalog"],
                "resolver_output_consulted": False,
                "reviewed_by": "project_owner",
                "reviewed_at": "2026-09-27T02:00:00Z",
                "review_reason": "Negative test: fixture UUID must remain regression-only.",
                "status": "approved_exact",
            }
        ],
    }
    inventory, decisions = _validated_dependencies()
    with pytest.raises(ContractError, match="lacks typed canonical_authority permission"):
        validate_canonical_authority(
            authority,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )


def test_authority_artifact_and_manifest_have_stable_raw_sha256_binding() -> None:
    authority_path = OUTPUT_DIR / "canonical-authority.json"
    manifest = _load(OUTPUT_DIR / "canonical-authority-manifest.json")
    assert hashlib.sha256(authority_path.read_bytes()).hexdigest() == manifest["authority_sha256"]
    paths = [item["path"] for item in manifest["input_artifacts"]]
    assert paths == sorted(paths)
    frozen_catalog_sha = hashlib.sha256(reconstruct_frozen_parent_catalog(ROOT)[1]).hexdigest()
    builder = _load_builder()
    for item in manifest["input_artifacts"]:
        expected = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        if item["path"] == "data/catalog.json":
            expected = frozen_catalog_sha
        elif item["path"] == "scripts/build_representative_hard_benchmark_canonical_authority.py":
            expected = builder.FROZEN_GENERATOR_SHA256
        assert expected == item["sha256"]
