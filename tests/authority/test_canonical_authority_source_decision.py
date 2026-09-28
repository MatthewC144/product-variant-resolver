from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest

from product_variant_resolver.canonical_authority_source_gate import (
    SourceGateValidationError,
    validate_source_gate_paths,
    validate_source_gate_payloads,
)

ROOT = Path(__file__).resolve().parents[2]
CAR_DIR = ROOT / "data" / "authority-review" / "canonical-authority-review-v1"
WIKI_DIR = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
DECISIONS_PATH = CAR_DIR / "source-decisions.json"
DECISIONS_MANIFEST_PATH = CAR_DIR / "source-decisions-manifest.json"
NORMALIZED_PATH = WIKI_DIR / "normalized.json"
SOURCE_MANIFEST_PATH = WIKI_DIR / "manifest.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_strings(child)]
    return []


def _approved_snapshot(decisions: dict[str, Any]) -> dict[str, Any]:
    approved = [
        source for source in decisions["sources"] if source["decision_status"] == "approved"
    ]
    assert len(approved) == 1
    return cast(dict[str, Any], approved[0])


def test_source_gate_approves_only_the_frozen_normalized_snapshot() -> None:
    decisions = _load(DECISIONS_PATH)
    source = _approved_snapshot(decisions)

    assert decisions["gate_result"] == "passed_for_single_existing_snapshot_review"
    assert source["source_id"] == "fandom-hot-wheels-2025-pilot-r790665-v1"
    assert source["source_kind"] == "licensed_community_snapshot"
    assert source["claim_tier"] == "community_reference_snapshot_exact"
    assert (
        source["acquisition_method"]
        == "reuse_existing_checked_in_normalized_text_snapshot_without_new_collection"
    )
    assert (
        source["source_owner_or_controller"]
        == "Hot Wheels Wiki community contributors; hosted by Fandom"
    )
    assert source["source_page"] == {
        "revision_id": 790665,
        "revision_timestamp": "2026-07-17T05:50:26Z",
        "title": "List of 2025 Hot Wheels",
        "url": "https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665",
    }
    assert source["normalized_artifact"] == {
        "path": "data/external/hot-wheels-wiki/pilot-2025/normalized.json",
        "record_count": 100,
        "sha256": "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6",
    }
    assert source["access_limitation"]["raw_json_is_car_input"] is False
    assert source["retention_scope"] == "public_existing_normalized_text_snapshot_only"
    assert (
        source["publication_scope"]
        == "public_existing_normalized_text_snapshot_and_safe_metadata_only"
    )
    assert source["claim_boundary"]["mattel_certified"] is False
    assert source["claim_boundary"]["manufacturer_certified"] is False
    assert source["claim_boundary"]["source_gate_establishes_approved_exact"] is False


def test_snapshot_hash_record_membership_and_row_source_binding_are_frozen() -> None:
    decisions = _load(DECISIONS_PATH)
    source = _approved_snapshot(decisions)
    normalized = _load(NORMALIZED_PATH)
    source_manifest = _load(SOURCE_MANIFEST_PATH)

    assert _sha256(NORMALIZED_PATH.read_bytes()) == source["normalized_artifact"]["sha256"]
    assert (
        source_manifest["files"]["normalized.json"]["sha256"]
        == source["normalized_artifact"]["sha256"]
    )
    assert normalized["record_count"] == len(normalized["records"]) == 100

    record_ids = sorted(row["source_record_id"] for row in normalized["records"])
    binding = source["eligible_record_set"]
    assert len(record_ids) == len(set(record_ids)) == binding["record_count"] == 100
    assert _sha256(_stable_json(record_ids)) == binding["source_record_ids_sha256"]

    expected_row_source = source["source_page"] | {
        "license": "CC-BY-SA",
        "license_url": "https://www.fandom.com/licensing",
        "page_title": source["source_page"]["title"],
        "page_url": source["source_page"]["url"],
    }
    expected_row_source.pop("title")
    expected_row_source.pop("url")
    expected_row_source["revision_id"] = 790665
    expected_row_source["revision_timestamp"] = "2026-07-17T05:50:26Z"
    for row in normalized["records"]:
        assert row["source"] == expected_row_source
        assert row["source_record_id"] in set(record_ids)


def test_allowed_fields_preserve_missing_color_and_forbid_inference() -> None:
    decisions = _load(DECISIONS_PATH)
    source = _approved_snapshot(decisions)
    normalized = _load(NORMALIZED_PATH)

    mappings = {
        item["source_field"]: item["target_field"] for item in source["allowed_field_mappings"]
    }
    assert mappings == {
        "casting_name": "casting",
        "collector_number": "collector_number",
        "release_year": "release_year",
        "series": "series",
        "series_position": "series_position",
        "toy_number": "identifiers",
        "variant_note": "review_context_only",
    }
    assert all(row["color"] is None for row in normalized["records"])
    assert any(row["variant_note"] == "2nd Color" for row in normalized["records"])
    inference = source["field_inference_policy"]
    assert inference["color"].startswith("must_remain_null")
    assert inference["second_color_note"] == "cannot_infer_color_name"
    assert "current snapshot supplies none" in inference["edition"]


def test_license_review_blindness_and_collection_limits_fail_closed() -> None:
    decisions = _load(DECISIONS_PATH)
    source = _approved_snapshot(decisions)

    license_policy = source["license_and_attribution"]
    assert license_policy["license_name"] == "CC-BY-SA"
    assert license_policy["share_alike_required"] is True
    assert {
        "source_page_title",
        "source_page_url",
        "source_revision_id",
        "source_revision_timestamp",
        "source_record_id",
        "normalized_snapshot_sha256",
        "license_url",
    } == set(license_policy["row_binding_required"])
    assert source["review_policy"] == {
        "confirmation_method": "owner_attestation",
        "resolver_output_consulted": False,
        "resolver_output_must_remain_hidden": True,
        "reviewer_role": "project_owner",
    }

    collection = decisions["network_and_collection_policy"]
    boolean_flags = [value for value in collection.values() if isinstance(value, bool)]
    assert boolean_flags and all(value is False for value in boolean_flags)
    assert (
        source["access_limitation"]["historical_automated_access_permission_established"] is False
    )
    assert decisions["authority_state"] == {
        "approved_exact_count": 0,
        "canonical_uuids_approved": False,
        "exact_authority_rows_created": False,
        "minimum_composition_passed": False,
        "rhb_t5_authorized": False,
    }


def test_workbook_is_context_only_and_other_sources_default_to_held() -> None:
    decisions = _load(DECISIONS_PATH)
    workbook = next(
        source
        for source in decisions["sources"]
        if source["source_id"] == "owner-local-release-snapshot-2023-2026-v1"
    )

    assert workbook["record_count"] == 1763
    assert workbook["decision_status"] == "rejected_for_exact_authority"
    assert workbook["authority_use"] == "rejected"
    assert workbook["exact_field_evidence_allowed"] is False
    assert workbook["allowed_uses"] == ["family_context", "candidate_selection_only"]
    assert decisions["default_source_policy"] == {
        "applies_to": "every_other_existing_or_future_source",
        "authority_use": "held_pending_separate_owner_decision",
        "collection_authorized": False,
        "publication_authorized": False,
    }


def test_safe_manifest_binds_inputs_and_records_feasibility_not_authority() -> None:
    manifest = _load(DECISIONS_MANIFEST_PATH)
    normalized = _load(NORMALIZED_PATH)
    bindings = manifest["artifact_bindings"]

    assert [item["path"] for item in bindings] == sorted(item["path"] for item in bindings)
    for binding in bindings:
        path = ROOT / binding["path"]
        if binding["hash_encoding"].startswith("canonical_json"):
            actual = _sha256(_stable_json(_load(path)))
        else:
            actual = _sha256(path.read_bytes())
        assert actual == binding["sha256"]

    record_ids = sorted(row["source_record_id"] for row in normalized["records"])
    source_binding = manifest["source_binding"]
    assert len(record_ids) == len(set(record_ids)) == source_binding["source_record_id_count"]
    assert _sha256(_stable_json(record_ids)) == source_binding["source_record_ids_sha256"]

    family_counts = Counter(row["casting_name"] for row in normalized["records"])
    feasibility = manifest["candidate_feasibility"]
    assert feasibility["record_count"] == len(normalized["records"]) == 100
    assert (
        feasibility["multi_release_family_count"]
        == sum(count >= 2 for count in family_counts.values())
        == 38
    )
    assert (
        feasibility["rows_in_multi_release_families"]
        == sum(count for count in family_counts.values() if count >= 2)
        == 85
    )
    assert feasibility["interpretation"] == "candidate_feasibility_not_authority"
    assert feasibility["target_claimed_passed"] is False
    assert manifest["authority_state"]["authority_rows_created"] == 0
    assert all(value == 0 for value in manifest["collection_telemetry"].values())


def test_public_decision_metadata_contains_no_obvious_pii() -> None:
    payload = {
        "decisions": _load(DECISIONS_PATH),
        "manifest": _load(DECISIONS_MANIFEST_PATH),
    }
    text = "\n".join(_walk_strings(payload))

    assert not re.search(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])", text)
    assert not re.search(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)", text)


def _validator_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        cast(dict[str, Any], _load(DECISIONS_PATH)),
        cast(dict[str, Any], _load(DECISIONS_MANIFEST_PATH)),
        cast(dict[str, Any], _load(NORMALIZED_PATH)),
        cast(dict[str, Any], _load(SOURCE_MANIFEST_PATH)),
    )


def _rebind_decisions(decisions: dict[str, Any], manifest: dict[str, Any]) -> None:
    binding = next(
        item
        for item in manifest["artifact_bindings"]
        if item["path"].endswith("source-decisions.json")
    )
    binding["sha256"] = _sha256(_stable_json(decisions))


def _validate_mutated(
    decisions: dict[str, Any],
    manifest: dict[str, Any],
    normalized: dict[str, Any],
    source_manifest: dict[str, Any],
) -> None:
    validate_source_gate_payloads(
        root=ROOT,
        decisions=decisions,
        manifest=manifest,
        normalized=normalized,
        source_manifest=source_manifest,
    )


def test_production_validator_accepts_current_t1_artifacts() -> None:
    validate_source_gate_paths(ROOT)


@pytest.mark.parametrize(
    ("target", "nested"),
    [
        ("decisions", False),
        ("decisions", True),
        ("manifest", False),
        ("manifest", True),
    ],
)
def test_validator_rejects_unknown_fields_even_when_decisions_are_rehashed(
    target: str, nested: bool
) -> None:
    decisions, manifest, normalized, source_manifest = _validator_payloads()
    if target == "decisions":
        container = decisions["sources"][0]["license_and_attribution"] if nested else decisions
    else:
        container = manifest["source_binding"] if nested else manifest
    container["unexpected_field"] = "must fail closed"
    if target == "decisions":
        _rebind_decisions(decisions, manifest)

    with pytest.raises(SourceGateValidationError, match="keys differ"):
        _validate_mutated(decisions, manifest, normalized, source_manifest)


@pytest.mark.parametrize("replacement", [None, "", "   "])
def test_validator_requires_nonblank_attribution_even_after_rehash(
    replacement: str | None,
) -> None:
    decisions, manifest, normalized, source_manifest = _validator_payloads()
    license_data = decisions["sources"][0]["license_and_attribution"]
    if replacement is None:
        del license_data["attribution_text"]
    else:
        license_data["attribution_text"] = replacement
    _rebind_decisions(decisions, manifest)

    with pytest.raises(SourceGateValidationError, match="attribution|keys differ|blank"):
        _validate_mutated(decisions, manifest, normalized, source_manifest)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("network_and_collection_policy", "network_collection_authorized"), True),
        (("network_and_collection_policy", "historical_access_authorized_by_fandom_claimed"), True),
        (("authority_state", "approved_exact_count"), 1),
        (("authority_state", "canonical_uuids_approved"), True),
        (("authority_state", "minimum_composition_passed"), True),
        (("authority_state", "rhb_t5_authorized"), True),
    ],
)
def test_validator_rejects_self_consistent_rehashed_semantic_escalation(
    path: tuple[str, str], value: object
) -> None:
    decisions, manifest, normalized, source_manifest = _validator_payloads()
    decisions[path[0]][path[1]] = value
    _rebind_decisions(decisions, manifest)

    with pytest.raises(SourceGateValidationError):
        _validate_mutated(decisions, manifest, normalized, source_manifest)


@pytest.mark.parametrize(
    ("field", "stale_value"),
    [
        ("toy_number", 1),
        ("casting_name", 1),
        ("release_year", 1),
        ("series", 1),
        ("collector_number", 1),
        ("series_position", 1),
        ("color", 99),
        ("edition", 99),
    ],
)
def test_validator_recomputes_every_required_missing_count(field: str, stale_value: int) -> None:
    decisions, manifest, normalized, source_manifest = _validator_payloads()
    manifest["candidate_feasibility"]["missing_field_counts"][field] = stale_value

    with pytest.raises(SourceGateValidationError, match="missing_field_counts"):
        _validate_mutated(decisions, manifest, normalized, source_manifest)


def test_validator_rejects_stale_parent_hashes_and_id_membership() -> None:
    decisions, manifest, normalized, source_manifest = _validator_payloads()
    normalized["records"][0]["source_record_id"] = normalized["records"][1]["source_record_id"]
    source_manifest["files"]["normalized.json"]["sha256"] = _sha256(_stable_json(normalized))

    with pytest.raises(SourceGateValidationError, match="unique"):
        _validate_mutated(decisions, manifest, normalized, source_manifest)


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("license_name", "proprietary"),
        ("license_url", "https://example.invalid/license"),
        ("share_alike_required", False),
        ("manufacturer_certified", True),
        ("mattel_certified", True),
        ("workbook_authority_use", "approved_for_human_exact_review_only"),
        ("workbook_exact_field", True),
        ("color_inference", "may_infer_from_second_color_note"),
        ("revision_id", 790666),
        ("source_id", "another-source"),
        ("gate_result", "partially_approved"),
    ],
)
def test_validator_rejects_qa_boundary_mutations_after_rehash(mutation: str, value: object) -> None:
    decisions, manifest, normalized, source_manifest = _validator_payloads()
    snapshot = decisions["sources"][0]
    workbook = decisions["sources"][1]
    if mutation in {"license_name", "license_url", "share_alike_required"}:
        snapshot["license_and_attribution"][mutation] = value
    elif mutation in {"manufacturer_certified", "mattel_certified"}:
        snapshot["claim_boundary"][mutation] = value
    elif mutation == "workbook_authority_use":
        workbook["authority_use"] = value
    elif mutation == "workbook_exact_field":
        workbook["exact_field_evidence_allowed"] = value
    elif mutation == "color_inference":
        snapshot["field_inference_policy"]["color"] = value
    elif mutation == "revision_id":
        snapshot["source_page"]["revision_id"] = value
    elif mutation == "source_id":
        snapshot["source_id"] = value
    elif mutation == "gate_result":
        decisions["gate_result"] = value
    _rebind_decisions(decisions, manifest)

    with pytest.raises(SourceGateValidationError):
        _validate_mutated(decisions, manifest, normalized, source_manifest)
