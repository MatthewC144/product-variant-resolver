"""Fail-closed validation for the CAR v1 source-decision Gate.

This module intentionally validates only the two CAR-T1 decision artifacts and their frozen
parents.  It is not the broader candidate/review contract planned for CAR-T2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any, NoReturn, cast

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]

SOURCE_ID = "fandom-hot-wheels-2025-pilot-r790665-v1"
WORKBOOK_ID = "owner-local-release-snapshot-2023-2026-v1"
PAGE_TITLE = "List of 2025 Hot Wheels"
PAGE_URL = "https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665"
REVISION_ID = 790665
REVISION_TIMESTAMP = "2026-07-17T05:50:26Z"
LICENSE_URL = "https://www.fandom.com/licensing"
NORMALIZED_PATH = "data/external/hot-wheels-wiki/pilot-2025/normalized.json"
SOURCE_MANIFEST_PATH = "data/external/hot-wheels-wiki/pilot-2025/manifest.json"
DECISIONS_PATH = "data/authority-review/canonical-authority-review-v1/source-decisions.json"
NORMALIZED_SHA256 = "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6"
SOURCE_MANIFEST_SHA256 = "960c639765759d3ab7b610718c026fa784e1995844f4acc9587718d94218f111"
SOURCE_RECORD_IDS_SHA256 = "c2412a8e9fa8fe78a2e8f6c932636e5d2a965131f0561843d179d13cdd8adba7"
SHA_PATTERN = re.compile(r"[0-9a-f]{64}")


class SourceGateValidationError(ValueError):
    """Raised when a CAR-T1 artifact violates the frozen source Gate."""


def _fail(path: str, message: str) -> NoReturn:
    raise SourceGateValidationError(f"{path}: {message}")


def _object(value: JsonValue, path: str) -> dict[str, JsonValue]:
    if type(value) is not dict:
        _fail(path, "must be an object")
    return value


def _array(value: JsonValue, path: str) -> list[JsonValue]:
    if type(value) is not list:
        _fail(path, "must be an array")
    return value


def _string(value: JsonValue, path: str, *, nonblank: bool = True) -> str:
    if type(value) is not str:
        _fail(path, "must be a string")
    result = value
    if nonblank and not result.strip():
        _fail(path, "must not be blank")
    return result


def _integer(value: JsonValue, path: str) -> int:
    if type(value) is not int:
        _fail(path, "must be an integer")
    return value


def _boolean(value: JsonValue, path: str) -> bool:
    if type(value) is not bool:
        _fail(path, "must be a boolean")
    return value


def _keys(value: JsonValue, path: str, expected: set[str]) -> dict[str, JsonValue]:
    result = _object(value, path)
    actual = set(result)
    if actual != expected:
        extra = sorted(actual - expected)
        missing = sorted(expected - actual)
        _fail(path, f"keys differ; extra={extra}, missing={missing}")
    return result


def _exact(value: JsonValue, expected: object, path: str) -> None:
    if type(value) is not type(expected) or value != expected:
        _fail(path, f"must equal {expected!r}")


def _sha(value: JsonValue, path: str) -> str:
    result = _string(value, path)
    if SHA_PATTERN.fullmatch(result) is None:
        _fail(path, "must be a lowercase SHA-256")
    return result


def _stable_json(value: JsonValue) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SourceGateValidationError(f"JSON: duplicate key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> JsonValue:
    """Load JSON while rejecting duplicate keys and non-standard constants."""

    def reject_constant(value: str) -> NoReturn:
        raise SourceGateValidationError(f"{path}: invalid JSON constant {value}")

    try:
        parsed: Any = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceGateValidationError(f"{path}: cannot load JSON") from exc
    return cast(JsonValue, parsed)


def _validate_iso_timestamp(value: JsonValue, path: str, expected: str) -> None:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SourceGateValidationError(f"{path}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or text != expected:
        _fail(path, f"must equal frozen timestamp {expected}")


def _validate_approval_date(value: JsonValue, path: str) -> None:
    text = _string(value, path)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise SourceGateValidationError(f"{path}: invalid ISO date") from exc
    if parsed.isoformat() != "2026-09-28":
        _fail(path, "must equal owner approval date 2026-09-28")


def _validate_decisions(payload: JsonValue) -> dict[str, JsonValue]:
    decisions = _keys(
        payload,
        "decisions",
        {
            "authority_state",
            "decision_version",
            "default_source_policy",
            "gate_result",
            "network_and_collection_policy",
            "next_allowed_task",
            "owner_decision",
            "prohibited_next_steps",
            "schema_version",
            "sources",
        },
    )
    _exact(
        decisions["schema_version"],
        "pvr-canonical-authority-review-source-decisions-v1",
        "decisions.schema_version",
    )
    _exact(
        decisions["decision_version"],
        "canonical-authority-review-source-decisions-owner-approved-v1",
        "decisions.decision_version",
    )
    _exact(
        decisions["gate_result"],
        "passed_for_single_existing_snapshot_review",
        "decisions.gate_result",
    )
    _exact(decisions["next_allowed_task"], "CAR-T2-strict-contracts", "decisions.next_allowed_task")

    authority = _keys(
        decisions["authority_state"],
        "decisions.authority_state",
        {
            "approved_exact_count",
            "canonical_uuids_approved",
            "exact_authority_rows_created",
            "minimum_composition_passed",
            "rhb_t5_authorized",
        },
    )
    _exact(authority["approved_exact_count"], 0, "decisions.authority_state.approved_exact_count")
    for field in (
        "canonical_uuids_approved",
        "exact_authority_rows_created",
        "minimum_composition_passed",
        "rhb_t5_authorized",
    ):
        _exact(authority[field], False, f"decisions.authority_state.{field}")

    default = _keys(
        decisions["default_source_policy"],
        "decisions.default_source_policy",
        {"applies_to", "authority_use", "collection_authorized", "publication_authorized"},
    )
    _exact(default["applies_to"], "every_other_existing_or_future_source", "default.applies_to")
    _exact(
        default["authority_use"], "held_pending_separate_owner_decision", "default.authority_use"
    )
    _exact(default["collection_authorized"], False, "default.collection_authorized")
    _exact(default["publication_authorized"], False, "default.publication_authorized")

    network_fields = {
        "api_collection_authorized",
        "browser_collection_authorized",
        "historical_access_authorized_by_fandom_claimed",
        "historical_automated_access_permission_established",
        "image_collection_authorized",
        "media_collection_authorized",
        "network_collection_authorized",
        "new_page_collection_authorized",
        "ocr_authorized",
        "raw_page_collection_authorized",
        "selenium_or_crawler_authorized",
        "terms_reference",
    }
    network = _keys(
        decisions["network_and_collection_policy"],
        "decisions.network_and_collection_policy",
        network_fields,
    )
    for field in network_fields - {"terms_reference"}:
        _exact(network[field], False, f"network_and_collection_policy.{field}")
    _exact(
        network["terms_reference"], "https://www.fandom.com/terms-of-use", "network.terms_reference"
    )

    owner = _keys(
        decisions["owner_decision"],
        "decisions.owner_decision",
        {
            "approval_date",
            "confirmation_method_for_later_row_review",
            "decision_reason",
            "reviewer_role",
            "reviewer_role_only_publication",
        },
    )
    _validate_approval_date(owner["approval_date"], "owner_decision.approval_date")
    _exact(
        owner["confirmation_method_for_later_row_review"],
        "owner_attestation",
        "owner_decision.confirmation_method_for_later_row_review",
    )
    _string(owner["decision_reason"], "owner_decision.decision_reason")
    _exact(owner["reviewer_role"], "project_owner", "owner_decision.reviewer_role")
    _exact(
        owner["reviewer_role_only_publication"],
        True,
        "owner_decision.reviewer_role_only_publication",
    )

    prohibited = [
        _string(item, "decisions.prohibited_next_steps[]")
        for item in _array(decisions["prohibited_next_steps"], "decisions.prohibited_next_steps")
    ]
    expected_prohibited = [
        "authority_row_creation_in_CAR-T1",
        "automatic_canonical_uuid_inference",
        "automatic_approved_exact_promotion",
        "benchmark_query_or_label_authoring",
        "new_network_or_browser_collection",
        "RHB-T5",
    ]
    if prohibited != expected_prohibited:
        _fail("decisions.prohibited_next_steps", "must equal the frozen prohibition list")

    sources = _array(decisions["sources"], "decisions.sources")
    if len(sources) != 2:
        _fail("decisions.sources", "must contain exactly the snapshot and workbook decisions")
    snapshot = _validate_snapshot_source(sources[0])
    _validate_workbook_source(sources[1])
    if snapshot["source_id"] == _object(sources[1], "decisions.sources[1]")["source_id"]:
        _fail("decisions.sources", "source IDs must be unique")
    return decisions


def _validate_snapshot_source(value: JsonValue) -> dict[str, JsonValue]:
    path = "decisions.sources[0]"
    source = _keys(
        value,
        path,
        {
            "access_limitation",
            "acquisition_method",
            "allowed_field_mappings",
            "authority_use",
            "claim_boundary",
            "claim_tier",
            "decision_status",
            "eligible_record_set",
            "field_inference_policy",
            "license_and_attribution",
            "normalized_artifact",
            "privacy_policy",
            "publication_and_retention",
            "publication_scope",
            "retention_scope",
            "review_policy",
            "source_id",
            "source_kind",
            "source_owner_or_controller",
            "source_page",
        },
    )
    constants: Mapping[str, object] = {
        "source_id": SOURCE_ID,
        "source_kind": "licensed_community_snapshot",
        "claim_tier": "community_reference_snapshot_exact",
        "decision_status": "approved",
        "authority_use": "approved_for_human_exact_review_only",
        "acquisition_method": "reuse_existing_checked_in_normalized_text_snapshot_without_new_collection",
        "source_owner_or_controller": "Hot Wheels Wiki community contributors; hosted by Fandom",
        "publication_scope": "public_existing_normalized_text_snapshot_and_safe_metadata_only",
        "retention_scope": "public_existing_normalized_text_snapshot_only",
    }
    for field, expected in constants.items():
        _exact(source[field], expected, f"{path}.{field}")

    access = _keys(
        source["access_limitation"],
        f"{path}.access_limitation",
        {
            "approved_artifact_only",
            "historical_automated_access_permission_established",
            "new_collection_authorized",
            "note",
            "raw_json_is_car_input",
        },
    )
    _exact(
        access["approved_artifact_only"], NORMALIZED_PATH, f"{path}.access.approved_artifact_only"
    )
    for field in (
        "historical_automated_access_permission_established",
        "new_collection_authorized",
        "raw_json_is_car_input",
    ):
        _exact(access[field], False, f"{path}.access_limitation.{field}")
    note = _string(access["note"], f"{path}.access_limitation.note").lower()
    if "does not claim" not in note or "historical" not in note:
        _fail(f"{path}.access_limitation.note", "must preserve the historical-access disclaimer")

    expected_mappings = [
        ("casting_name", "casting"),
        ("collector_number", "collector_number"),
        ("release_year", "release_year"),
        ("series", "series"),
        ("series_position", "series_position"),
        ("toy_number", "identifiers"),
        ("variant_note", "review_context_only"),
    ]
    mappings: list[tuple[str, str]] = []
    for index, item in enumerate(
        _array(source["allowed_field_mappings"], f"{path}.allowed_field_mappings")
    ):
        mapping = _keys(
            item, f"{path}.allowed_field_mappings[{index}]", {"source_field", "target_field"}
        )
        mappings.append(
            (
                _string(mapping["source_field"], f"mapping[{index}].source_field"),
                _string(mapping["target_field"], f"mapping[{index}].target_field"),
            )
        )
    if mappings != expected_mappings:
        _fail(f"{path}.allowed_field_mappings", "must equal the approved ordered mapping")

    claim = _keys(
        source["claim_boundary"],
        f"{path}.claim_boundary",
        {
            "canonical_uuid_approved",
            "exact_relative_to",
            "manufacturer_certified",
            "mattel_certified",
            "source_gate_establishes_approved_exact",
        },
    )
    for field in (
        "canonical_uuid_approved",
        "manufacturer_certified",
        "mattel_certified",
        "source_gate_establishes_approved_exact",
    ):
        _exact(claim[field], False, f"{path}.claim_boundary.{field}")
    _exact(
        claim["exact_relative_to"],
        "frozen_community_reference_revision_790665_after_later_owner_review",
        f"{path}.claim_boundary.exact_relative_to",
    )

    eligible = _keys(
        source["eligible_record_set"],
        f"{path}.eligible_record_set",
        {
            "record_count",
            "source_record_ids_canonicalization",
            "source_record_ids_sha256",
            "unique_source_record_id_count",
        },
    )
    _exact(eligible["record_count"], 100, f"{path}.eligible_record_set.record_count")
    _exact(
        eligible["unique_source_record_id_count"], 100, f"{path}.eligible_record_set.unique_count"
    )
    _exact(
        eligible["source_record_ids_canonicalization"],
        "UTF-8 JSON array sorted lexicographically with sorted keys, two-space indentation and trailing newline",
        f"{path}.eligible_record_set.canonicalization",
    )
    _exact(
        eligible["source_record_ids_sha256"],
        SOURCE_RECORD_IDS_SHA256,
        f"{path}.eligible_record_set.sha256",
    )

    inference = _keys(
        source["field_inference_policy"],
        f"{path}.field_inference_policy",
        {"color", "edition", "second_color_note", "variant_note"},
    )
    _exact(
        inference["color"],
        "must_remain_null_without_separately_approved_explicit_evidence",
        f"{path}.inference.color",
    )
    _exact(
        inference["second_color_note"],
        "cannot_infer_color_name",
        f"{path}.inference.second_color_note",
    )
    _exact(
        inference["variant_note"],
        "context_only_cannot_fill_another_field",
        f"{path}.inference.variant_note",
    )
    _exact(
        inference["edition"],
        "allowed_only_with_explicit_nonempty_evidence_from_an_approved_source; current snapshot supplies none",
        f"{path}.inference.edition",
    )

    license_data = _keys(
        source["license_and_attribution"],
        f"{path}.license_and_attribution",
        {
            "attribution_text",
            "license_name",
            "license_url",
            "row_binding_required",
            "share_alike_required",
        },
    )
    attribution = _string(
        license_data["attribution_text"], f"{path}.license_and_attribution.attribution_text"
    )
    for required in (
        "Hot Wheels Wiki contributors",
        PAGE_TITLE,
        "revision 790665",
        "normalized derivative",
    ):
        if required not in attribution:
            _fail(f"{path}.license_and_attribution.attribution_text", f"must contain {required!r}")
    _exact(license_data["license_name"], "CC-BY-SA", f"{path}.license_and_attribution.license_name")
    _exact(license_data["license_url"], LICENSE_URL, f"{path}.license_and_attribution.license_url")
    _exact(
        license_data["share_alike_required"],
        True,
        f"{path}.license_and_attribution.share_alike_required",
    )
    row_bindings = [
        _string(item, f"{path}.row_binding_required[]")
        for item in _array(license_data["row_binding_required"], f"{path}.row_binding_required")
    ]
    expected_row_bindings = [
        "source_page_title",
        "source_page_url",
        "source_revision_id",
        "source_revision_timestamp",
        "source_record_id",
        "normalized_snapshot_sha256",
        "license_url",
    ]
    if row_bindings != expected_row_bindings:
        _fail(f"{path}.row_binding_required", "must equal required row bindings")

    artifact = _keys(
        source["normalized_artifact"],
        f"{path}.normalized_artifact",
        {"path", "record_count", "sha256"},
    )
    _exact(artifact["path"], NORMALIZED_PATH, f"{path}.normalized_artifact.path")
    _exact(artifact["record_count"], 100, f"{path}.normalized_artifact.record_count")
    _exact(artifact["sha256"], NORMALIZED_SHA256, f"{path}.normalized_artifact.sha256")

    privacy = _keys(
        source["privacy_policy"],
        f"{path}.privacy_policy",
        {
            "contact_or_account_data_allowed",
            "personal_identity_allowed",
            "public_reviewer_identity",
            "status",
        },
    )
    _exact(privacy["contact_or_account_data_allowed"], False, f"{path}.privacy.contact")
    _exact(privacy["personal_identity_allowed"], False, f"{path}.privacy.personal")
    _exact(privacy["public_reviewer_identity"], "project_owner", f"{path}.privacy.reviewer")
    _exact(privacy["status"], "approved_role_only", f"{path}.privacy.status")

    publication = _keys(
        source["publication_and_retention"],
        f"{path}.publication_and_retention",
        {
            "detailed_owner_packets",
            "existing_normalized_text_snapshot",
            "new_image_media_or_raw_page",
            "public_safe_artifacts",
        },
    )
    _exact(
        publication["detailed_owner_packets"],
        "local_only_git_ignored",
        f"{path}.publication.packets",
    )
    _exact(
        publication["existing_normalized_text_snapshot"],
        "public_existing_artifact_only",
        f"{path}.publication.snapshot",
    )
    _exact(
        publication["new_image_media_or_raw_page"], "prohibited", f"{path}.publication.new_media"
    )
    safe_artifacts = [
        _string(item, f"{path}.publication.public_safe_artifacts[]")
        for item in _array(
            publication["public_safe_artifacts"], f"{path}.publication.public_safe_artifacts"
        )
    ]
    if safe_artifacts != [
        "approved_non_sensitive_decision_metadata",
        "attribution_and_license_metadata",
        "counts_and_aggregates",
        "irreversible_sha256_values",
        "schemas_and_tests",
    ]:
        _fail(
            f"{path}.publication.public_safe_artifacts", "must equal the approved publication list"
        )

    review = _keys(
        source["review_policy"],
        f"{path}.review_policy",
        {
            "confirmation_method",
            "resolver_output_consulted",
            "resolver_output_must_remain_hidden",
            "reviewer_role",
        },
    )
    _exact(review["confirmation_method"], "owner_attestation", f"{path}.review.confirmation_method")
    _exact(review["resolver_output_consulted"], False, f"{path}.review.resolver_output_consulted")
    _exact(review["resolver_output_must_remain_hidden"], True, f"{path}.review.hidden")
    _exact(review["reviewer_role"], "project_owner", f"{path}.review.reviewer_role")

    page = _keys(
        source["source_page"],
        f"{path}.source_page",
        {"revision_id", "revision_timestamp", "title", "url"},
    )
    _exact(page["revision_id"], REVISION_ID, f"{path}.source_page.revision_id")
    _validate_iso_timestamp(
        page["revision_timestamp"], f"{path}.source_page.revision_timestamp", REVISION_TIMESTAMP
    )
    _exact(page["title"], PAGE_TITLE, f"{path}.source_page.title")
    _exact(page["url"], PAGE_URL, f"{path}.source_page.url")
    return source


def _validate_workbook_source(value: JsonValue) -> None:
    path = "decisions.sources[1]"
    source = _keys(
        value,
        path,
        {
            "allowed_uses",
            "authority_use",
            "claim_tier",
            "decision_reason",
            "decision_status",
            "exact_field_evidence_allowed",
            "record_count",
            "source_id",
            "source_kind",
        },
    )
    expected: Mapping[str, object] = {
        "source_id": WORKBOOK_ID,
        "source_kind": "third_party_derived_workbook_context",
        "claim_tier": "context_only",
        "decision_status": "rejected_for_exact_authority",
        "authority_use": "rejected",
        "exact_field_evidence_allowed": False,
        "record_count": 1763,
    }
    for field, expected_value in expected.items():
        _exact(source[field], expected_value, f"{path}.{field}")
    allowed = [
        _string(item, f"{path}.allowed_uses[]")
        for item in _array(source["allowed_uses"], f"{path}.allowed_uses")
    ]
    if allowed != ["family_context", "candidate_selection_only"]:
        _fail(f"{path}.allowed_uses", "must remain context-only")
    reason = _string(source["decision_reason"], f"{path}.decision_reason").lower()
    for phrase in ("not individually bound", "cannot establish exact", "canonical uuid"):
        if phrase not in reason:
            _fail(f"{path}.decision_reason", f"must retain {phrase!r}")


def _validate_source_manifest(payload: JsonValue, normalized_sha: str) -> None:
    manifest = _keys(
        payload,
        "source_manifest",
        {
            "dataset_version",
            "files",
            "license",
            "record_count",
            "schema_version",
            "source_revision_id",
            "usage_limits",
        },
    )
    _exact(manifest["dataset_version"], SOURCE_ID, "source_manifest.dataset_version")
    _exact(manifest["schema_version"], "fandom-pilot-manifest-v1", "source_manifest.schema_version")
    _exact(manifest["record_count"], 100, "source_manifest.record_count")
    _exact(manifest["source_revision_id"], REVISION_ID, "source_manifest.source_revision_id")
    files = _keys(manifest["files"], "source_manifest.files", {"normalized.json", "raw.json"})
    for name in ("normalized.json", "raw.json"):
        entry = _keys(files[name], f"source_manifest.files.{name}", {"sha256"})
        _sha(entry["sha256"], f"source_manifest.files.{name}.sha256")
    _exact(
        _object(files["normalized.json"], "source_manifest.files.normalized")["sha256"],
        normalized_sha,
        "source_manifest.files.normalized.sha256",
    )
    license_data = _keys(manifest["license"], "source_manifest.license", {"name", "url"})
    _exact(license_data["name"], "CC-BY-SA", "source_manifest.license.name")
    _exact(license_data["url"], LICENSE_URL, "source_manifest.license.url")
    limits = [
        _string(item, "source_manifest.usage_limits[]")
        for item in _array(manifest["usage_limits"], "source_manifest.usage_limits")
    ]
    if limits != [
        "needs_canonical_review",
        "not_canonical_ground_truth",
        "not_evaluation_or_threshold_training",
        "text_only_no_images_downloaded",
    ]:
        _fail("source_manifest.usage_limits", "must preserve the frozen source limits")


def _validate_normalized(payload: JsonValue) -> dict[str, int | str]:
    normalized = _keys(
        payload,
        "normalized",
        {"dataset_version", "record_count", "records", "schema_version", "scope", "source"},
    )
    _exact(normalized["dataset_version"], SOURCE_ID, "normalized.dataset_version")
    _exact(
        normalized["schema_version"], "fandom-hot-wheels-staging-v1", "normalized.schema_version"
    )
    _exact(
        normalized["scope"],
        "review-only catalog candidates; excluded from canonical API and evaluation",
        "normalized.scope",
    )
    root_source = _keys(
        normalized["source"],
        "normalized.source",
        {
            "license",
            "license_url",
            "page_id",
            "page_title",
            "page_url",
            "revision_id",
            "revision_timestamp",
            "wiki",
        },
    )
    _exact(root_source["license"], "CC-BY-SA", "normalized.source.license")
    _exact(root_source["license_url"], LICENSE_URL, "normalized.source.license_url")
    _exact(root_source["page_id"], 161422, "normalized.source.page_id")
    _exact(root_source["page_title"], PAGE_TITLE, "normalized.source.page_title")
    _exact(root_source["page_url"], PAGE_URL, "normalized.source.page_url")
    _exact(root_source["revision_id"], REVISION_ID, "normalized.source.revision_id")
    _validate_iso_timestamp(
        root_source["revision_timestamp"],
        "normalized.source.revision_timestamp",
        REVISION_TIMESTAMP,
    )
    _exact(root_source["wiki"], "Hot Wheels Wiki", "normalized.source.wiki")
    records = _array(normalized["records"], "normalized.records")
    _exact(normalized["record_count"], len(records), "normalized.record_count")
    if len(records) != 100:
        _fail("normalized.records", "must contain exactly 100 rows")

    ids: list[str] = []
    castings: list[str] = []
    missing_fields = {
        "toy_number": 0,
        "casting_name": 0,
        "release_year": 0,
        "series": 0,
        "collector_number": 0,
        "series_position": 0,
        "color": 0,
        "edition": 0,
        "variant_note": 0,
    }
    for index, item in enumerate(records):
        path = f"normalized.records[{index}]"
        row = _keys(
            item,
            path,
            {
                "brand",
                "canonical_uuid",
                "casting_name",
                "collector_number",
                "color",
                "release_year",
                "review_status",
                "series",
                "series_position",
                "source",
                "source_markers",
                "source_model_label",
                "source_record_id",
                "source_row",
                "toy_number",
                "usage",
                "variant_note",
            },
        )
        for field in (
            "toy_number",
            "casting_name",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "color",
            "variant_note",
        ):
            if field not in row or row[field] is None or row[field] == "":
                missing_fields[field] += 1
        if "edition" not in row or row["edition"] is None or row["edition"] == "":
            missing_fields["edition"] += 1
        ids.append(_string(row.get("source_record_id"), f"{path}.source_record_id"))
        castings.append(_string(row.get("casting_name"), f"{path}.casting_name"))
        _exact(row["brand"], "Hot Wheels", f"{path}.brand")
        _string(row["collector_number"], f"{path}.collector_number")
        _exact(row["release_year"], 2025, f"{path}.release_year")
        _string(row["series"], f"{path}.series")
        _string(row["series_position"], f"{path}.series_position")
        _string(row["source_model_label"], f"{path}.source_model_label")
        _exact(row["source_row"], index + 1, f"{path}.source_row")
        _string(row["toy_number"], f"{path}.toy_number")
        _exact(row["review_status"], "needs_canonical_review", f"{path}.review_status")
        _exact(
            row["usage"],
            "staging_only_not_evaluation_or_canonical",
            f"{path}.usage",
        )
        markers = _array(row["source_markers"], f"{path}.source_markers")
        for marker_index, marker in enumerate(markers):
            _string(marker, f"{path}.source_markers[{marker_index}]")
        if row["variant_note"] is not None:
            _string(row["variant_note"], f"{path}.variant_note")
        _exact(row.get("canonical_uuid"), None, f"{path}.canonical_uuid")
        _exact(row.get("color"), None, f"{path}.color")
        row_source = _keys(
            row.get("source"),
            f"{path}.source",
            {
                "license",
                "license_url",
                "page_title",
                "page_url",
                "revision_id",
                "revision_timestamp",
            },
        )
        _exact(row_source["license"], "CC-BY-SA", f"{path}.source.license")
        _exact(row_source["license_url"], LICENSE_URL, f"{path}.source.license_url")
        _exact(row_source["page_title"], PAGE_TITLE, f"{path}.source.page_title")
        _exact(row_source["page_url"], PAGE_URL, f"{path}.source.page_url")
        _exact(row_source["revision_id"], REVISION_ID, f"{path}.source.revision_id")
        _validate_iso_timestamp(
            row_source["revision_timestamp"],
            f"{path}.source.revision_timestamp",
            REVISION_TIMESTAMP,
        )

    if len(ids) != len(set(ids)):
        _fail("normalized.records.source_record_id", "must be unique")
    if sorted(
        _integer(_object(item, "normalized.record")["source_row"], "source_row") for item in records
    ) != list(range(1, 101)):
        _fail("normalized.records.source_row", "must contain each row number from 1 through 100")
    family_counts = Counter(castings)
    multi_family_count = sum(count >= 2 for count in family_counts.values())
    rows_in_multi = sum(count for count in family_counts.values() if count >= 2)
    return {
        "record_count": len(records),
        "unique_record_count": len(set(ids)),
        "record_ids_sha256": _digest(_stable_json(cast(list[JsonValue], sorted(ids)))),
        "multi_release_family_count": multi_family_count,
        "rows_in_multi_release_families": rows_in_multi,
        **missing_fields,
    }


def _validate_manifest(
    payload: JsonValue,
    *,
    root: Path,
    decisions: JsonValue,
    normalized: JsonValue,
    source_manifest: JsonValue,
    facts: Mapping[str, int | str],
) -> None:
    manifest = _keys(
        payload,
        "manifest",
        {
            "artifact_bindings",
            "authority_state",
            "candidate_feasibility",
            "collection_telemetry",
            "decision_version",
            "gate_result",
            "manifest_version",
            "schema_version",
            "source_binding",
        },
    )
    expected_constants: Mapping[str, str] = {
        "schema_version": "pvr-canonical-authority-review-source-decisions-manifest-v1",
        "manifest_version": "canonical-authority-review-source-decisions-manifest-v1",
        "decision_version": "canonical-authority-review-source-decisions-owner-approved-v1",
        "gate_result": "passed_for_single_existing_snapshot_review",
    }
    for field, expected in expected_constants.items():
        _exact(manifest[field], expected, f"manifest.{field}")

    bindings: dict[str, tuple[str, str]] = {}
    binding_items = _array(manifest["artifact_bindings"], "manifest.artifact_bindings")
    for index, item in enumerate(binding_items):
        binding = _keys(
            item, f"manifest.artifact_bindings[{index}]", {"hash_encoding", "path", "sha256"}
        )
        path = _string(binding["path"], f"manifest.artifact_bindings[{index}].path")
        encoding = _string(
            binding["hash_encoding"], f"manifest.artifact_bindings[{index}].hash_encoding"
        )
        sha = _sha(binding["sha256"], f"manifest.artifact_bindings[{index}].sha256")
        if path in bindings:
            _fail("manifest.artifact_bindings", f"duplicate path {path}")
        bindings[path] = (encoding, sha)
    expected_paths = {
        DECISIONS_PATH,
        SOURCE_MANIFEST_PATH,
        NORMALIZED_PATH,
        "specs/canonical-authority-review-v1/design.md",
        "specs/canonical-authority-review-v1/requirements.md",
        "specs/canonical-authority-review-v1/source-approval.md",
        "specs/canonical-authority-review-v1/tasks.md",
    }
    if set(bindings) != expected_paths or list(bindings) != sorted(bindings):
        _fail("manifest.artifact_bindings", "must contain the exact stable-ordered parent set")
    json_payloads: Mapping[str, JsonValue] = {
        DECISIONS_PATH: decisions,
        SOURCE_MANIFEST_PATH: source_manifest,
        NORMALIZED_PATH: normalized,
    }
    for path, (encoding, declared_sha) in bindings.items():
        if path in json_payloads:
            if encoding != "canonical_json_utf8_sorted_keys_indent_2_trailing_newline":
                _fail(
                    f"manifest.artifact_bindings.{path}", "JSON parent requires canonical encoding"
                )
            actual_sha = _digest(_stable_json(json_payloads[path]))
        else:
            if encoding != "raw_file_bytes":
                _fail(
                    f"manifest.artifact_bindings.{path}", "spec parent requires raw-file encoding"
                )
            try:
                actual_sha = _digest((root / path).read_bytes())
            except OSError as exc:
                raise SourceGateValidationError(f"manifest artifact missing: {path}") from exc
        if actual_sha != declared_sha:
            _fail(f"manifest.artifact_bindings.{path}.sha256", "does not match current parent")

    authority = _keys(
        manifest["authority_state"],
        "manifest.authority_state",
        {
            "approved_exact_count",
            "authority_rows_created",
            "canonical_uuids_approved",
            "minimum_composition_passed",
        },
    )
    for field in ("approved_exact_count", "authority_rows_created", "canonical_uuids_approved"):
        _exact(authority[field], 0, f"manifest.authority_state.{field}")
    _exact(
        authority["minimum_composition_passed"],
        False,
        "manifest.authority_state.minimum_composition_passed",
    )

    feasibility = _keys(
        manifest["candidate_feasibility"],
        "manifest.candidate_feasibility",
        {
            "interpretation",
            "missing_field_counts",
            "multi_release_family_count",
            "record_count",
            "rows_in_multi_release_families",
            "target_claimed_passed",
        },
    )
    _exact(
        feasibility["interpretation"],
        "candidate_feasibility_not_authority",
        "manifest.feasibility.interpretation",
    )
    _exact(feasibility["record_count"], facts["record_count"], "manifest.feasibility.record_count")
    _exact(
        feasibility["multi_release_family_count"],
        facts["multi_release_family_count"],
        "manifest.feasibility.multi_release_family_count",
    )
    _exact(
        feasibility["rows_in_multi_release_families"],
        facts["rows_in_multi_release_families"],
        "manifest.feasibility.rows_in_multi_release_families",
    )
    _exact(
        feasibility["target_claimed_passed"], False, "manifest.feasibility.target_claimed_passed"
    )
    missing = _keys(
        feasibility["missing_field_counts"],
        "manifest.candidate_feasibility.missing_field_counts",
        {
            "casting_name",
            "collector_number",
            "color",
            "edition",
            "release_year",
            "series",
            "series_position",
            "toy_number",
            "variant_note",
        },
    )
    for field in missing:
        _exact(missing[field], facts[field], f"manifest.feasibility.missing_field_counts.{field}")

    telemetry = _keys(
        manifest["collection_telemetry"],
        "manifest.collection_telemetry",
        {
            "api_requests",
            "browser_sessions",
            "images_or_media_acquired",
            "network_requests",
            "new_pages_acquired",
            "raw_pages_acquired",
        },
    )
    for field in telemetry:
        _exact(telemetry[field], 0, f"manifest.collection_telemetry.{field}")

    source_binding = _keys(
        manifest["source_binding"],
        "manifest.source_binding",
        {
            "claim_tier",
            "normalized_snapshot_sha256",
            "revision_id",
            "source_id",
            "source_kind",
            "source_record_id_count",
            "source_record_ids_canonicalization",
            "source_record_ids_sha256",
            "unique_source_record_id_count",
        },
    )
    _exact(source_binding["source_id"], SOURCE_ID, "manifest.source_binding.source_id")
    _exact(
        source_binding["source_kind"],
        "licensed_community_snapshot",
        "manifest.source_binding.source_kind",
    )
    _exact(
        source_binding["claim_tier"],
        "community_reference_snapshot_exact",
        "manifest.source_binding.claim_tier",
    )
    _exact(source_binding["revision_id"], REVISION_ID, "manifest.source_binding.revision_id")
    _exact(
        source_binding["source_record_id_count"],
        facts["record_count"],
        "manifest.source_binding.record_count",
    )
    _exact(
        source_binding["unique_source_record_id_count"],
        facts["unique_record_count"],
        "manifest.source_binding.unique_count",
    )
    _exact(
        source_binding["source_record_ids_sha256"],
        facts["record_ids_sha256"],
        "manifest.source_binding.record_ids_sha256",
    )
    _exact(
        source_binding["source_record_ids_canonicalization"],
        "UTF-8 JSON array sorted lexicographically with sorted keys, two-space indentation and trailing newline",
        "manifest.source_binding.source_record_ids_canonicalization",
    )
    _exact(
        source_binding["normalized_snapshot_sha256"],
        _digest(_stable_json(normalized)),
        "manifest.source_binding.normalized_sha256",
    )

    snapshot = _object(
        _array(_object(decisions, "decisions")["sources"], "decisions.sources")[0],
        "decisions.sources[0]",
    )
    eligible = _object(snapshot["eligible_record_set"], "decisions.sources[0].eligible_record_set")
    artifact = _object(snapshot["normalized_artifact"], "decisions.sources[0].normalized_artifact")
    _exact(
        eligible["source_record_ids_sha256"],
        facts["record_ids_sha256"],
        "decisions.eligible_record_set.sha256",
    )
    _exact(
        eligible["record_count"],
        facts["record_count"],
        "decisions.eligible_record_set.record_count",
    )
    _exact(
        eligible["unique_source_record_id_count"],
        facts["unique_record_count"],
        "decisions.eligible_record_set.unique_count",
    )
    _exact(
        artifact["sha256"],
        _digest(_stable_json(normalized)),
        "decisions.normalized_artifact.sha256",
    )
    source_manifest_obj = _object(source_manifest, "source_manifest")
    files = _object(source_manifest_obj["files"], "source_manifest.files")
    normalized_file = _object(files["normalized.json"], "source_manifest.files.normalized.json")
    _exact(
        normalized_file["sha256"],
        _digest(_stable_json(normalized)),
        "source_manifest.normalized.sha256",
    )


def validate_source_gate_payloads(
    *,
    root: Path,
    decisions: JsonValue,
    manifest: JsonValue,
    normalized: JsonValue,
    source_manifest: JsonValue,
) -> None:
    """Validate T1 semantics before accepting any manifest checksum."""

    validated_decisions = _validate_decisions(decisions)
    normalized_sha = _digest(_stable_json(normalized))
    _validate_source_manifest(source_manifest, normalized_sha)
    facts = _validate_normalized(normalized)
    if normalized_sha != NORMALIZED_SHA256:
        _fail("normalized", "content SHA-256 differs from the owner-approved snapshot")
    if _digest(_stable_json(source_manifest)) != SOURCE_MANIFEST_SHA256:
        _fail("source_manifest", "content SHA-256 differs from the frozen source manifest")
    if facts["record_ids_sha256"] != SOURCE_RECORD_IDS_SHA256:
        _fail("normalized.records.source_record_id", "membership differs from the approved set")
    _validate_manifest(
        manifest,
        root=root,
        decisions=validated_decisions,
        normalized=normalized,
        source_manifest=source_manifest,
        facts=facts,
    )


def validate_source_gate_paths(root: Path) -> None:
    """Load and validate the repository's CAR-T1 artifacts and frozen parents."""

    validate_source_gate_payloads(
        root=root,
        decisions=load_json(root / DECISIONS_PATH),
        manifest=load_json(
            root
            / "data"
            / "authority-review"
            / "canonical-authority-review-v1"
            / "source-decisions-manifest.json"
        ),
        normalized=load_json(root / NORMALIZED_PATH),
        source_manifest=load_json(root / SOURCE_MANIFEST_PATH),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the offline CAR-T1 source Gate")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    validate_source_gate_paths(args.root.resolve())
    print("CAR-T1 source Gate: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
