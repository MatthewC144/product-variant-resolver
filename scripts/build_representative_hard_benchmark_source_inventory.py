"""Freeze the RHB-v1 source baseline without reading network or private source rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from product_variant_resolver.canonical_authority_packet import (
    EXPECTED_RAW_CATALOG_SHA256,
    reconstruct_frozen_parent_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "evaluation" / "representative-hard-benchmark-v1"
INVENTORY_PATH = OUTPUT_DIR / "source-inventory.json"
MANIFEST_PATH = OUTPUT_DIR / "source-inventory-manifest.json"
EVIDENCE_PATH = ROOT / "docs" / "evidence" / "representative-hard-benchmark-source-baseline.md"

INVENTORY_SCHEMA = "pvr-representative-hard-benchmark-source-inventory-v1"
MANIFEST_SCHEMA = "pvr-representative-hard-benchmark-source-inventory-manifest-v1"
INVENTORY_VERSION = "representative-hard-benchmark-source-baseline-v1"
BASELINE_DATE = "2026-09-26"
GENERATOR = "scripts/build_representative_hard_benchmark_source_inventory.py"
FROZEN_GENERATOR_SHA256 = "a0b4ac376358ae1a7e261547ada6bae66936eee4b97d668e136e09bb29973a72"
TRACKED_PUBLIC_ARTIFACTS = (
    "data/benchmark.json",
    "data/catalog.json",
    "data/human_labeled_names.json",
    "data/human_labeled_catalog_alignment.json",
    "reports/local-release-staging-v1/manifest.json",
    "data/external/hot-wheels-wiki/pilot-2025/manifest.json",
    "data/external/hot-wheels-wiki/pilot-2025/normalized.json",
    "data/external/hot-wheels-wiki/pilot-2025/raw.json",
)


class BaselineError(ValueError):
    """Raised when a frozen source no longer matches its declared evidence."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BaselineError(f"{path}: could not read valid JSON") from error
    if not isinstance(value, dict):
        raise BaselineError(f"{path}: root must be an object")
    return value


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise BaselineError(f"{path}: could not compute SHA-256") from error


def _stable_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise BaselineError(message)


def _require_list(value: Any, message: str) -> list[Any]:
    if not isinstance(value, list):
        raise BaselineError(message)
    return value


def _require_dict(value: Any, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BaselineError(message)
    return value


def _require_sha256(value: Any, message: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise BaselineError(message)
    return value


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _artifact(path: Path, root: Path, *, effective_sha256: str | None = None) -> dict[str, str]:
    return {
        "path": _relative(path, root),
        "sha256": effective_sha256 or _sha256(path),
    }


def _frozen_fixture_manifest(payload: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    """Reconstruct the fixture-v1 manifest after an explicitly linked catalog-v2 apply."""

    if "catalog_application_version" not in payload:
        parent = payload
    else:
        _expect(
            payload.get("parent_catalog_sha256") == EXPECTED_RAW_CATALOG_SHA256,
            "fixture manifest parent catalog drift",
        )
        _expect(payload.get("parent_catalog_version") == "fixture-v1", "fixture parent changed")
        _expect(payload.get("parent_product_count") == 120, "fixture parent count changed")
        parent = dict(payload)
        for key in (
            "catalog_application_version",
            "catalog_version",
            "parent_catalog_sha256",
            "parent_catalog_version",
            "parent_product_count",
        ):
            parent.pop(key, None)
        parent["catalog_sha256"] = EXPECTED_RAW_CATALOG_SHA256
        parent["product_count"] = 120
    parent_raw = _stable_json(parent)
    return parent, parent_raw


def _entry(
    *,
    source_id: str,
    source_kind: str,
    origin_reference: str,
    acquisition_method: str,
    local_sha256: str,
    access_permission_status: str,
    content_license_status: str,
    retention_scope: str,
    redistribution_scope: str,
    privacy_review_status: str,
    benchmark_uses: list[str],
    evidence_refs: list[str],
    current_repository_state: str,
    current_publication_state: str,
    known_rights_evidence: dict[str, Any],
    prospective_benchmark_use_status: str,
    prospective_redistribution_status: str,
    owner_decision: str,
    owner_decision_metadata: dict[str, Any],
    record_count: int,
    record_count_kind: str,
    authority_eligibility: str,
    authority_evidence_level: str,
    authority_boundary: str,
) -> dict[str, Any]:
    return {
        "access_permission_status": access_permission_status,
        "acquisition_method": acquisition_method,
        "authority_boundary": authority_boundary,
        "authority_eligibility": authority_eligibility,
        "authority_evidence_level": authority_evidence_level,
        "benchmark_uses": benchmark_uses,
        "content_license_status": content_license_status,
        "current_publication_state": current_publication_state,
        "current_repository_state": current_repository_state,
        "evidence_refs": evidence_refs,
        "known_rights_evidence": known_rights_evidence,
        "local_sha256": local_sha256,
        "origin_reference": origin_reference,
        "owner_decision": owner_decision,
        "owner_decision_metadata": owner_decision_metadata,
        "privacy_review_status": privacy_review_status,
        "prospective_benchmark_use_status": prospective_benchmark_use_status,
        "prospective_redistribution_status": prospective_redistribution_status,
        "record_count": record_count,
        "record_count_kind": record_count_kind,
        "redistribution_scope": redistribution_scope,
        "retention_scope": retention_scope,
        "source_id": source_id,
        "source_kind": source_kind,
    }


def build_baseline(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Build and validate all T1 outputs from repository-safe source evidence."""

    data = root / "data"
    fixture_manifest_path = data / "manifest.json"
    benchmark_path = data / "benchmark.json"
    catalog_path = data / "catalog.json"
    human_path = data / "human_labeled_names.json"
    human_manifest_path = data / "human_labeled_names_manifest.json"
    alignment_path = data / "human_labeled_catalog_alignment.json"
    alignment_manifest_path = data / "human_labeled_catalog_alignment_manifest.json"
    local_summary_path = root / "reports" / "local-release-staging-v1" / "manifest.json"
    wiki_dir = data / "external" / "hot-wheels-wiki" / "pilot-2025"
    wiki_manifest_path = wiki_dir / "manifest.json"
    wiki_normalized_path = wiki_dir / "normalized.json"
    wiki_raw_path = wiki_dir / "raw.json"

    tracked_public_paths = [root / relative for relative in TRACKED_PUBLIC_ARTIFACTS]
    for path in tracked_public_paths:
        _expect(path.is_file(), f"checked-in artifact contract is missing {_relative(path, root)}")

    fixture_manifest, fixture_manifest_raw = _frozen_fixture_manifest(_load(fixture_manifest_path))
    benchmark = _load(benchmark_path)
    catalog_model, catalog_raw = reconstruct_frozen_parent_catalog(root)
    catalog = catalog_model.model_dump(mode="json")
    human = _load(human_path)
    human_manifest = _load(human_manifest_path)
    alignment = _load(alignment_path)
    alignment_manifest = _load(alignment_manifest_path)
    local_summary = _load(local_summary_path)
    wiki_manifest = _load(wiki_manifest_path)
    wiki_normalized = _load(wiki_normalized_path)

    benchmark_cases = _require_list(
        benchmark.get("cases"), "fixture benchmark: records must be an array"
    )
    catalog_products = _require_list(
        catalog.get("products"), "fixture catalog: records must be an array"
    )
    human_records = _require_list(
        human.get("records"), "human-labeled scans: records must be an array"
    )
    alignments = _require_list(
        alignment.get("alignments"), "catalog alignment: records must be an array"
    )
    wiki_records = _require_list(
        wiki_normalized.get("records"), "Wiki pilot: records must be an array"
    )

    _expect(len(benchmark_cases) == 100, "fixture benchmark count must be 100")
    _expect(len(catalog_products) == 120, "fixture catalog count must be 120")
    _expect(len(human_records) == 101, "human-labeled scan count must be 101")
    _expect(len(alignments) == 101, "catalog alignment count must be 101")
    _expect(len(wiki_records) == 100, "Wiki pilot count must be 100")

    benchmark_sha = _sha256(benchmark_path)
    catalog_sha = hashlib.sha256(catalog_raw).hexdigest()
    human_sha = _sha256(human_path)
    alignment_sha = _sha256(alignment_path)
    wiki_normalized_sha = _sha256(wiki_normalized_path)
    wiki_raw_sha = _sha256(wiki_raw_path)
    _expect(fixture_manifest.get("benchmark_sha256") == benchmark_sha, "fixture benchmark drift")
    _expect(fixture_manifest.get("catalog_sha256") == catalog_sha, "fixture catalog drift")
    _expect(fixture_manifest.get("benchmark_case_count") == 100, "fixture manifest count drift")
    _expect(fixture_manifest.get("product_count") == 120, "fixture manifest count drift")
    _expect(human_manifest.get("dataset_sha256") == human_sha, "human scan dataset drift")
    _expect(human_manifest.get("record_count") == 101, "human scan manifest count drift")
    _expect(alignment_manifest.get("alignment_sha256") == alignment_sha, "alignment drift")
    _expect(
        alignment_manifest.get("human_dataset_sha256") == human_sha, "alignment human parent drift"
    )
    _expect(
        alignment_manifest.get("catalog_sha256") == catalog_sha, "alignment catalog parent drift"
    )

    status_counts = Counter(row.get("status") for row in alignments if isinstance(row, dict))
    expected_alignment = {"casting_family_only": 2, "mapped": 0, "unmapped": 99}
    observed_alignment = {key: status_counts.get(key, 0) for key in expected_alignment}
    _expect(observed_alignment == expected_alignment, "real-scan alignment counts changed")
    _expect(
        alignment_manifest.get("status_counts") == expected_alignment,
        "alignment manifest status counts changed",
    )
    _expect(
        all(
            isinstance(row, dict)
            and row.get("canonical_id") is None
            and row.get("canonical_uuid") is None
            for row in alignments
        ),
        "real-scan alignment must not assert canonical identity",
    )

    local_counts = _require_dict(
        local_summary.get("counts"), "local release public summary is missing"
    )
    _expect(local_counts.get("staged_observations") == 1763, "local release count must be 1,763")
    _expect(local_counts.get("canonical_products") == 0, "local releases gained canonical products")
    _expect(local_counts.get("reviewed_variants") == 0, "local releases gained reviewed variants")
    _expect(local_counts.get("parse_errors") == 0, "local release snapshot contains parse errors")
    _expect(
        local_summary.get("public_scope") == "summary_and_checksums_only_no_source_rows",
        "local release public scope changed",
    )
    _expect(
        local_summary.get("source_rights_state")
        == "access_permission_and_republication_rights_not_provided",
        "local release rights state changed",
    )
    _expect("records" not in local_summary, "local release public summary contains private rows")
    local_content_sha = _require_sha256(
        local_summary.get("content_sha256"),
        "local release source digest is missing",
    )

    wiki_files = _require_dict(wiki_manifest.get("files"), "Wiki pilot file manifest is missing")
    wiki_normalized_reference = _require_dict(
        wiki_files.get("normalized.json"), "Wiki normalized file reference is missing"
    )
    wiki_raw_reference = _require_dict(
        wiki_files.get("raw.json"), "Wiki raw file reference is missing"
    )
    _expect(wiki_manifest.get("record_count") == 100, "Wiki pilot manifest count drift")
    _expect(wiki_normalized.get("record_count") == 100, "Wiki pilot dataset count drift")
    _expect(
        wiki_normalized_reference.get("sha256") == wiki_normalized_sha,
        "Wiki normalized dataset drift",
    )
    _expect(
        wiki_raw_reference.get("sha256") == wiki_raw_sha,
        "Wiki raw dataset drift",
    )
    _expect(
        all(
            isinstance(row, dict)
            and row.get("canonical_uuid") is None
            and row.get("usage") == "staging_only_not_evaluation_or_canonical"
            for row in wiki_records
        ),
        "Wiki pilot crossed its staging-only authority boundary",
    )

    entries = [
        _entry(
            source_id="fixture-v1-benchmark",
            source_kind="synthetic_fixture",
            origin_reference="data/benchmark.json",
            acquisition_method="deterministic repository fixture generation",
            local_sha256=benchmark_sha,
            access_permission_status="not_applicable",
            content_license_status="approved",
            retention_scope="public",
            redistribution_scope="public_rows",
            privacy_review_status="approved",
            benchmark_uses=["negative_control"],
            evidence_refs=["data/manifest.json", "data/benchmark.json"],
            current_repository_state="tracked_public_repository",
            current_publication_state="row_level_public",
            known_rights_evidence={
                "status": "approved",
                "evidence": [
                    "specs/representative-hard-benchmark-v1/design.md#gate-a--inventoryprovenance-readiness"
                ],
                "limitations": ["synthetic_fixture_only"],
            },
            prospective_benchmark_use_status="pending_RHB_T3_owner_selection",
            prospective_redistribution_status="pending_RHB_T3_owner_selection",
            owner_decision="pending",
            owner_decision_metadata={
                "current_use": "regression_and_tooling_only",
                "privacy_risk": "none_synthetic",
                "representative_pilot_use": "requires_RHB_T3_owner_decision",
                "unresolved_conditions": ["owner_selection_for_representative_pilot"],
            },
            record_count=100,
            record_count_kind="synthetic_benchmark_cases",
            authority_eligibility="synthetic_regression_only",
            authority_evidence_level="synthetic_only",
            authority_boundary="Not eligible for the non-synthetic representative-pilot quota.",
        ),
        _entry(
            source_id="fixture-v1-catalog",
            source_kind="synthetic_fixture",
            origin_reference="data/catalog.json",
            acquisition_method="deterministic repository fixture generation",
            local_sha256=catalog_sha,
            access_permission_status="not_applicable",
            content_license_status="approved",
            retention_scope="public",
            redistribution_scope="public_rows",
            privacy_review_status="approved",
            benchmark_uses=["negative_control"],
            evidence_refs=["data/manifest.json", "data/catalog.json"],
            current_repository_state="tracked_public_repository",
            current_publication_state="row_level_public",
            known_rights_evidence={
                "status": "approved",
                "evidence": [
                    "specs/representative-hard-benchmark-v1/design.md#gate-a--inventoryprovenance-readiness"
                ],
                "limitations": ["synthetic_fixture_only"],
            },
            prospective_benchmark_use_status="pending_RHB_T3_owner_selection",
            prospective_redistribution_status="pending_RHB_T3_owner_selection",
            owner_decision="pending",
            owner_decision_metadata={
                "current_use": "synthetic_catalog_regression_only",
                "privacy_risk": "none_synthetic",
                "representative_pilot_use": "requires_RHB_T3_owner_decision",
                "unresolved_conditions": ["owner_selection_for_representative_pilot"],
            },
            record_count=120,
            record_count_kind="synthetic_catalog_products",
            authority_eligibility="synthetic_regression_only",
            authority_evidence_level="synthetic_only",
            authority_boundary="Synthetic canonical IDs do not establish real release truth.",
        ),
        _entry(
            source_id="human-labeled-real-noisy-v1",
            source_kind="owner_scan",
            origin_reference="data/human_labeled_names.json",
            acquisition_method="owner-supplied human-reviewed scan export",
            local_sha256=human_sha,
            access_permission_status="approved",
            content_license_status="unknown",
            retention_scope="public",
            redistribution_scope="public_rows",
            privacy_review_status="pending",
            benchmark_uses=["none"],
            evidence_refs=[
                "data/human_labeled_names_manifest.json",
                "docs/decisions/product-variant-resolver.md#d8--keep-reviewed-real-names-separate-until-catalog-alignment",
            ],
            current_repository_state="tracked_public_repository",
            current_publication_state="row_level_public",
            known_rights_evidence={
                "status": "unknown_for_benchmark_reuse_and_republication",
                "evidence": [
                    "docs/decisions/product-variant-resolver.md#d8--keep-reviewed-real-names-separate-until-catalog-alignment"
                ],
                "limitations": [
                    "existing_publication_does_not_authorize_future_benchmark_reuse",
                    "privacy_review_pending",
                ],
            },
            prospective_benchmark_use_status="blocked_pending_RHB_T3_rights_and_privacy_decision",
            prospective_redistribution_status="blocked_pending_RHB_T3_rights_and_privacy_decision",
            owner_decision="pending",
            owner_decision_metadata={
                "current_use": "auxiliary_name_pair_audit",
                "benchmark_use": "blocked_until_RHB_T3_owner_rights_and_privacy_decision",
                "privacy_risk": "pending_review_of_listing_derived_text",
                "unresolved_conditions": [
                    "content_reuse_rights",
                    "public_redistribution",
                    "allowed_fields",
                    "privacy_review",
                ],
            },
            record_count=101,
            record_count_kind="human_labeled_scans",
            authority_eligibility="prohibited",
            authority_evidence_level="none",
            authority_boundary="No row is exact canonical variant authority.",
        ),
        _entry(
            source_id="human-labeled-to-fixture-alignment-v1",
            source_kind="other",
            origin_reference="data/human_labeled_catalog_alignment.json",
            acquisition_method="offline exact normalized family alignment",
            local_sha256=alignment_sha,
            access_permission_status="not_applicable",
            content_license_status="unknown",
            retention_scope="public",
            redistribution_scope="public_rows",
            privacy_review_status="pending",
            benchmark_uses=["family_context"],
            evidence_refs=[
                "data/human_labeled_catalog_alignment_manifest.json",
                "docs/decisions/product-variant-resolver.md#d9--prefer-explicit-non-matches-over-fuzzy-catalog-assignments",
            ],
            current_repository_state="tracked_public_repository",
            current_publication_state="row_level_public",
            known_rights_evidence={
                "status": "inherits_unknown_human_scan_rights",
                "evidence": ["data/human_labeled_catalog_alignment_manifest.json"],
                "limitations": [
                    "derived_artifact_inherits_parent_source_rights",
                    "existing_publication_does_not_authorize_future_benchmark_reuse",
                ],
            },
            prospective_benchmark_use_status="blocked_pending_RHB_T3_parent_rights_decision",
            prospective_redistribution_status="blocked_pending_RHB_T3_parent_rights_decision",
            owner_decision="pending",
            owner_decision_metadata={
                "current_use": "coverage_audit_only",
                "benchmark_use": "requires_RHB_T3_owner_decision",
                "privacy_risk": "inherits_human_scan_review",
                "unresolved_conditions": [
                    "parent_source_rights",
                    "public_redistribution",
                    "benchmark_use",
                ],
            },
            record_count=101,
            record_count_kind="alignment_rows",
            authority_eligibility="prohibited",
            authority_evidence_level="family_only",
            authority_boundary="0 exact canonical mappings; family-only rows cannot create UUID labels.",
        ),
        _entry(
            source_id="owner-local-release-snapshot-2023-2026-v1",
            source_kind="owner_export",
            origin_reference="owner-local HW data workbooks; raw rows intentionally not referenced publicly",
            acquisition_method="owner-supplied XLSX files normalized offline with openpyxl",
            local_sha256=local_content_sha,
            access_permission_status="approved",
            content_license_status="unknown",
            retention_scope="local_only",
            redistribution_scope="aggregate_only",
            privacy_review_status="pending",
            benchmark_uses=["family_context"],
            evidence_refs=[
                "reports/local-release-staging-v1/manifest.json",
                "docs/evidence/local-release-staging-ingestion.md",
            ],
            current_repository_state="private_rows_untracked_with_tracked_public_aggregate",
            current_publication_state="aggregate_only_public_private_rows_unpublished",
            known_rights_evidence={
                "status": "owner_access_approved_republication_unknown",
                "evidence": [
                    "reports/local-release-staging-v1/manifest.json",
                    "docs/evidence/local-release-staging-ingestion.md",
                ],
                "limitations": [
                    "raw_workbooks_and_normalized_rows_unpublished",
                    "republication_rights_not_provided",
                ],
            },
            prospective_benchmark_use_status="blocked_pending_RHB_T3_rights_fields_and_privacy_decision",
            prospective_redistribution_status="blocked_pending_RHB_T3_republication_decision",
            owner_decision="pending",
            owner_decision_metadata={
                "current_use": "review_only_local_staging",
                "benchmark_use": "requires_RHB_T3_owner_rights_and_fields_decision",
                "privacy_risk": "pending_owner_export_field_review",
                "unresolved_conditions": [
                    "content_reuse_rights",
                    "allowed_fields",
                    "public_redistribution",
                    "privacy_review",
                ],
            },
            record_count=1763,
            record_count_kind="staged_release_observations",
            authority_eligibility="prohibited",
            authority_evidence_level="staging_only",
            authority_boundary="Review-only observations; zero canonical links or promotions.",
        ),
        _entry(
            source_id="fandom-hot-wheels-2025-pilot-r790665-v1",
            source_kind="licensed_text_derivative",
            origin_reference="data/external/hot-wheels-wiki/pilot-2025",
            acquisition_method="checked-in revision-bound text derivative; no new collection in RHB-v1",
            local_sha256=wiki_normalized_sha,
            access_permission_status="unknown",
            content_license_status="approved",
            retention_scope="public",
            redistribution_scope="public_rows",
            privacy_review_status="approved",
            benchmark_uses=["family_context"],
            evidence_refs=[
                "data/external/hot-wheels-wiki/pilot-2025/manifest.json",
                "data/external/hot-wheels-wiki/README.md",
            ],
            current_repository_state="tracked_public_repository",
            current_publication_state="row_level_public_with_attribution",
            known_rights_evidence={
                "status": "CC_BY_SA_text_derivative_recorded_access_permission_unknown",
                "evidence": ["data/external/hot-wheels-wiki/pilot-2025/manifest.json"],
                "limitations": [
                    "not_canonical_or_evaluation_truth",
                    "no_new_collection_without_source_specific_permission",
                ],
            },
            prospective_benchmark_use_status="pending_RHB_T3_existing_derivative_only",
            prospective_redistribution_status="pending_RHB_T3_attribution_and_use_decision",
            owner_decision="pending",
            owner_decision_metadata={
                "current_use": "family_and_release_review_questions_only",
                "benchmark_use": "requires_RHB_T3_owner_decision",
                "new_collection": "blocked_without_source_specific_permission",
                "privacy_risk": "none_known_in_checked_in_text_rows",
                "unresolved_conditions": [
                    "owner_selection_for_benchmark_use",
                    "source_specific_permission_for_any_new_collection",
                ],
            },
            record_count=100,
            record_count_kind="staged_release_rows",
            authority_eligibility="prohibited",
            authority_evidence_level="staging_only",
            authority_boundary="CC-BY-SA text derivative; not canonical truth or evaluation labels.",
        ),
    ]

    inventory = {
        "alignment_summary": {
            "exact_canonical": observed_alignment["mapped"],
            "family_only": observed_alignment["casting_family_only"],
            "unmapped": observed_alignment["unmapped"],
        },
        "baseline_date": BASELINE_DATE,
        "entries": entries,
        "inventory_version": INVENTORY_VERSION,
        "network_collection_performed": False,
        "owner_source_gate": "pending_RHB_T3",
        "private_source_rows_copied": False,
        "schema_version": INVENTORY_SCHEMA,
    }
    inventory_bytes = _stable_json(inventory)
    inventory_sha = hashlib.sha256(inventory_bytes).hexdigest()

    input_paths = [
        root / GENERATOR,
        fixture_manifest_path,
        benchmark_path,
        catalog_path,
        human_path,
        human_manifest_path,
        alignment_path,
        alignment_manifest_path,
        local_summary_path,
        wiki_manifest_path,
        wiki_normalized_path,
        wiki_raw_path,
    ]
    historical_hashes = {
        root / GENERATOR: FROZEN_GENERATOR_SHA256,
        fixture_manifest_path: hashlib.sha256(fixture_manifest_raw).hexdigest(),
        catalog_path: catalog_sha,
    }
    manifest = {
        "alignment_summary": inventory["alignment_summary"],
        "baseline_date": BASELINE_DATE,
        "external_content_digests": {
            "owner_local_release_snapshot_content_sha256": local_content_sha,
        },
        "generator": GENERATOR,
        "input_artifacts": [
            _artifact(path, root, effective_sha256=historical_hashes.get(path))
            for path in input_paths
        ],
        "inventory_file": "source-inventory.json",
        "inventory_sha256": inventory_sha,
        "inventory_version": INVENTORY_VERSION,
        "network_requests": 0,
        "private_source_rows_copied": False,
        "repository_tracking_contract": {
            "state": "tracked_public_repository",
            "artifacts": [
                _artifact(path, root, effective_sha256=historical_hashes.get(path))
                for path in tracked_public_paths
            ],
            "owner_private_rows": "untracked_and_not_copied",
        },
        "record_counts": {
            "fixture_benchmark_cases": 100,
            "fixture_catalog_products": 120,
            "human_labeled_scans": 101,
            "human_scan_alignments": 101,
            "owner_local_release_observations": 1763,
            "wiki_pilot_rows": 100,
        },
        "schema_version": MANIFEST_SCHEMA,
        "source_entry_count": len(entries),
    }

    evidence = f"""# Representative hard benchmark v1 — source baseline

Date: {BASELINE_DATE}. Mode: Lite / Lean Industrial. Scope: **RHB-T1 only**.

## Outcome

The current source evidence is now checksum-bound and machine-checkable without network access. This
baseline records availability and authority boundaries; it does **not** approve sources for the
representative pilot, publish private owner rows, create benchmark labels, or promote any row into
canonical identity. The owner source Gate remains pending for RHB-T3.

| Evidence source | Count | Current publication reality | Prospective RHB-v1 use / redistribution | Exact authority |
|---|---:|---|---|---|
| `fixture-v1` benchmark | 100 | row-level public | both pending T3 selection | synthetic only |
| `fixture-v1` catalog | 120 | row-level public | both pending T3 selection | synthetic only |
| Human-labeled scans | 101 | **row-level public and Git-tracked** | both blocked pending T3 rights/privacy decision | none |
| Human alignment | 101 | **row-level public and Git-tracked** | both blocked pending parent-rights decision | **0 exact**, 2 family-only, 99 unmapped |
| Owner release snapshot | 1,763 | public aggregate only; private rows unpublished | use and redistribution blocked pending T3 | staging only; exact authority prohibited |
| Checked-in Wiki pilot | 100 | attributed row-level public | both pending T3; new collection blocked | staging only; exact authority prohibited |

## Why these boundaries exist

- A human-confirmed casting name does not prove an exact release variant, year, color, series, or
  collector number. The alignment therefore preserves `0 exact / 2 family-only / 99 unmapped`.
- Typed `authority_eligibility` and `authority_evidence_level` fields enforce this boundary. Every
  current real source is `prohibited`; synthetic fixtures are `synthetic_regression_only`. Only a
  future, separately inventoried `authorized_export` may be an
  `exact_variant_authority_candidate`, and it still requires the T3/T4 Gates.
- The human-label JSON and its derived alignment are already Git-tracked in the public repository.
  The inventory records that existing publication as fact while separately keeping future benchmark
  reuse and republication blocked until the T3 rights/privacy decision. Existing publication is not
  interpreted as permission for a new use.
- The 1,763 owner rows have an unpublished, gitignored raw source. This public baseline uses only the
  Git-tracked `reports/local-release-staging-v1/manifest.json` aggregate and its non-reversible
  source-content digest; it neither requires the ignored local review summary nor copies any row or
  casting label. A clean checkout can therefore reproduce this baseline.
- The Wiki pilot is attributed text under its recorded license, but every row remains outside
  canonical truth and evaluation labels. Its presence does not authorize a new crawl.
- Every owner decision is still `pending` until RHB-T3; affected prospective uses are explicitly
  blocked while that decision and its required rights/privacy evidence are absent.

## Reproduction

```bash
python3 scripts/build_representative_hard_benchmark_source_inventory.py --check
```

The command reads repository-local files only. A successful check prints `unchanged`; any changed
count, parent checksum, alignment authority, staging boundary, or stored output fails closed.

## Frozen artifacts

- Inventory SHA-256: `{inventory_sha}`
- Fixture benchmark SHA-256: `{benchmark_sha}`
- Fixture catalog SHA-256: `{catalog_sha}`
- Human scan dataset SHA-256: `{human_sha}`
- Alignment SHA-256: `{alignment_sha}`
- Owner private snapshot content SHA-256: `{local_content_sha}`
- Wiki normalized SHA-256: `{wiki_normalized_sha}`
- Network requests: `0`
- Private source rows copied: `false`
"""
    return inventory, manifest, evidence


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def materialize(*, root: Path = ROOT, check: bool = False) -> str:
    inventory, manifest, evidence = build_baseline(root)
    outputs = {
        root
        / "data"
        / "evaluation"
        / "representative-hard-benchmark-v1"
        / "source-inventory.json": _stable_json(inventory),
        root
        / "data"
        / "evaluation"
        / "representative-hard-benchmark-v1"
        / "source-inventory-manifest.json": _stable_json(manifest),
        root
        / "docs"
        / "evidence"
        / "representative-hard-benchmark-source-baseline.md": evidence.encode(),
    }
    unchanged = all(
        path.is_file() and path.read_bytes() == content for path, content in outputs.items()
    )
    if check:
        if not unchanged:
            raise BaselineError(
                "stored source baseline is missing or differs from deterministic output"
            )
        return "unchanged"
    if unchanged:
        return "unchanged"
    for path, content in outputs.items():
        _write_atomic(path, content)
    return "written"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="verify stored outputs without writing"
    )
    args = parser.parse_args(argv)
    try:
        result = materialize(check=args.check)
    except BaselineError as error:
        print(f"source baseline error: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
