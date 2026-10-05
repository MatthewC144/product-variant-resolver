"""Read-only RHB-T5 readiness validation.

This module deliberately stops before query-pack authoring.  It validates the frozen
upstream Gates, proves that enough real query text exists, and reports the controls
that must be repaired before a fresh output-blind authoring session can begin.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    AuthorityStatus,
    BenchmarkQuery,
    CanonicalAuthorityArtifact,
    SourceDecisionScope,
    SourceDecisionStatus,
    SourceDecisionUse,
    SourceDownstreamPermission,
    content_sha256,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_query_projection import (
    IGNORE_RULE,
    PRIVATE_AUTHORING_DIRECTORY,
    validate_materialized_projection,
)
from product_variant_resolver.representative_benchmark_query_projection import (
    MANIFEST_REFERENCE as PROJECTION_MANIFEST_REFERENCE,
)
from product_variant_resolver.representative_benchmark_query_projection import (
    PROJECTION_REFERENCE as OUTPUT_BLIND_PROJECTION_REFERENCE,
)
from product_variant_resolver.representative_benchmark_reaudit import CarT6ReauditManifest

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
INVENTORY_REFERENCE = RHB_DIRECTORY / "source-inventory.json"
INVENTORY_MANIFEST_REFERENCE = RHB_DIRECTORY / "source-inventory-manifest.json"
SOURCE_DECISIONS_REFERENCE = RHB_DIRECTORY / "source-decisions.json"
HUMAN_SOURCE_REFERENCE = Path("data/human_labeled_names.json")
WIKI_SOURCE_REFERENCE = Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json")
HISTORICAL_AUTHORITY_REFERENCE = RHB_DIRECTORY / "canonical-authority.json"
HISTORICAL_MANIFEST_REFERENCE = RHB_DIRECTORY / "canonical-authority-manifest.json"
REAUDIT_AUTHORITY_REFERENCE = RHB_DIRECTORY / "canonical-authority-reaudit-v1.json"
REAUDIT_MANIFEST_REFERENCE = RHB_DIRECTORY / "canonical-authority-reaudit-manifest-v1.json"
PUBLIC_QUERY_PACK_REFERENCE = RHB_DIRECTORY / "query-pack.json"
PRIVATE_QUERY_PACK_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "query-pack.json"
QUERY_PACK_MANIFEST_REFERENCE = RHB_DIRECTORY / "query-pack-manifest.json"
LABEL_REFERENCES = (
    PRIVATE_AUTHORING_DIRECTORY / "labels.json",
    PRIVATE_AUTHORING_DIRECTORY / "held-labels.json",
    RHB_DIRECTORY / "labels.json",
    RHB_DIRECTORY / "held-labels.json",
    RHB_DIRECTORY / "labels-manifest.json",
)
OWNER_AUTHORIZATION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "rhb-t5-owner-authorization.json"

HUMAN_SOURCE_ID = "human-labeled-real-noisy-v1"
TARGET_CASE_COUNT = 60
REQUIRED_BLOCKERS = [
    "fresh_output_blind_authoring_context_required",
    "rhb_t5_owner_gate_required",
]


class QueryReadinessError(ValueError):
    """Raised when an upstream artifact is stale, malformed, or unsafe."""


class QueryAuthoringReadiness(BaseModel):
    """Machine-checkable, non-authorizing RHB-T5 readiness result."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["pvr-rhb-t5-query-authoring-readiness-v2"]
    gate: Literal["RHB-T5"]
    status: Literal["ready_for_separate_owner_authorization"]
    target_case_count: Literal[60]
    source_id: Literal["human-labeled-real-noisy-v1"]
    source_record_count: int = Field(ge=0)
    nonblank_query_count: int = Field(ge=0)
    unique_nonblank_query_count: int = Field(ge=0)
    duplicate_nonblank_query_count: int = Field(ge=0)
    candidate_shortfall: int = Field(ge=0)
    source_rows_with_pipeline_outputs: int = Field(ge=0)
    source_rows_with_human_labels: int = Field(ge=0)
    source_rows_with_failure_categories: int = Field(ge=0)
    source_query_scope: Literal["local_only"]
    public_raw_query_pack_authorized: Literal[False]
    public_aggregate_metadata_authorized: Literal[True]
    output_blind_projection_present: Literal[True]
    output_blind_projection_valid: Literal[True]
    output_blind_projection_record_count: Literal[91]
    output_blind_projection_required: Literal[True]
    private_authoring_path_ignored: Literal[True]
    query_contract_requires_split: Literal[False]
    family_safe_split_phase: Literal["RHB-T7"]
    query_contract_split_phase_alignment_required: Literal[False]
    car_t6_gate_result: Literal["passed_exact_authority_gate"]
    approved_exact_variant_count: Literal[20]
    qualifying_family_count: int = Field(ge=4)
    exact_variant_shortfall: Literal[0]
    qualifying_family_shortfall: Literal[0]
    public_query_pack_present: bool
    private_query_pack_present: bool
    query_pack_manifest_present: bool
    label_artifact_count: int = Field(ge=0)
    owner_gate_present: bool
    challenge_coverage_verified: Literal[False]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    network_requests: Literal[0]
    current_session_eligible_for_authoring: Literal[False]
    rhb_t5_authorized: Literal[False]
    blockers: list[str]
    next_allowed_action: Literal[
        "request_separate_owner_gate_then_author_in_fresh_output_blind_context"
    ]
    readiness_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def readiness_is_coherent_and_hash_bound(self) -> QueryAuthoringReadiness:
        if self.unique_nonblank_query_count + self.candidate_shortfall < self.target_case_count:
            raise ValueError("candidate shortfall is inconsistent")
        expected_shortfall = max(0, self.target_case_count - self.unique_nonblank_query_count)
        if self.candidate_shortfall != expected_shortfall:
            raise ValueError("candidate shortfall is inconsistent")
        if self.duplicate_nonblank_query_count != (
            self.nonblank_query_count - self.unique_nonblank_query_count
        ):
            raise ValueError("duplicate query count is inconsistent")
        if self.blockers != REQUIRED_BLOCKERS:
            raise ValueError("RHB-T5 readiness blockers changed or are out of order")
        expected = content_sha256(self.model_dump(mode="json", exclude={"readiness_sha256"}))
        if self.readiness_sha256 != expected:
            raise ValueError("RHB-T5 readiness checksum is stale")
        return self


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QueryReadinessError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise QueryReadinessError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise QueryReadinessError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise QueryReadinessError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise QueryReadinessError(message)


def _decision_for_use(source: Any, use: SourceDecisionUse) -> Any:
    return next(decision for decision in source.decisions if decision.use == use)


def build_rhb_t5_query_readiness(root: Path) -> QueryAuthoringReadiness:
    """Validate RHB-T5 prerequisites without writing files or invoking the resolver."""

    root = root.absolute()
    rhb_directory = root / RHB_DIRECTORY
    inventory_payload = _load_object(root / INVENTORY_REFERENCE)
    inventory_manifest_payload = _load_object(root / INVENTORY_MANIFEST_REFERENCE)
    decisions_payload = _load_object(root / SOURCE_DECISIONS_REFERENCE)
    wiki_payload = _load_object(root / WIKI_SOURCE_REFERENCE)
    human_payload = _load_object(root / HUMAN_SOURCE_REFERENCE)

    inventory, _inventory_manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )
    human_inventory = next(
        (entry for entry in inventory.entries if entry.source_id == HUMAN_SOURCE_ID), None
    )
    human_decision = next(
        (source for source in decisions.sources if source.source_id == HUMAN_SOURCE_ID), None
    )
    _expect(human_inventory is not None, "human query source is missing from the inventory")
    _expect(human_decision is not None, "human query source is missing from source decisions")
    assert human_inventory is not None
    assert human_decision is not None
    _expect(
        human_inventory.local_sha256 == _raw_sha256(root / HUMAN_SOURCE_REFERENCE),
        "human query source checksum drift",
    )
    _expect(
        SourceDownstreamPermission.query_pack in human_decision.downstream_permissions,
        "human source no longer grants query-pack use",
    )
    query_decision = _decision_for_use(human_decision, SourceDecisionUse.query_text)
    local_decision = _decision_for_use(human_decision, SourceDecisionUse.local_only_benchmark_use)
    public_decision = _decision_for_use(human_decision, SourceDecisionUse.public_git_artifacts)
    _expect(
        query_decision.status == SourceDecisionStatus.approved
        and query_decision.effective_publication_scope == SourceDecisionScope.local_only,
        "human query text must remain approved local-only",
    )
    _expect(
        local_decision.status == SourceDecisionStatus.approved
        and local_decision.effective_publication_scope == SourceDecisionScope.local_only,
        "human benchmark use must remain approved local-only",
    )
    _expect(
        public_decision.status == SourceDecisionStatus.approved
        and public_decision.effective_publication_scope == SourceDecisionScope.aggregate_only,
        "human source Git output must remain aggregate-only",
    )

    authority_payload = _load_object(root / REAUDIT_AUTHORITY_REFERENCE)
    manifest_payload = _load_object(root / REAUDIT_MANIFEST_REFERENCE)
    authority = CanonicalAuthorityArtifact.model_validate(authority_payload)
    manifest = CarT6ReauditManifest.model_validate(manifest_payload)
    _expect(
        manifest.authority_sha256 == content_sha256(authority.model_dump(mode="json")),
        "CAR-T6 authority checksum drift",
    )
    _expect(len(authority.records) == 20, "CAR-T6 authority must contain 20 records")
    _expect(
        len({record.canonical_uuid for record in authority.records}) == 20,
        "CAR-T6 authority UUIDs must be unique",
    )
    _expect(
        all(
            record.status == AuthorityStatus.approved_exact and not record.resolver_output_consulted
            for record in authority.records
        ),
        "CAR-T6 authority contains a non-exact or output-contaminated record",
    )
    _expect(
        manifest.gate_result == "passed_exact_authority_gate"
        and manifest.approved_exact_variant_count == 20
        and manifest.thresholds.exact_variant_shortfall == 0
        and manifest.thresholds.qualifying_family_shortfall == 0,
        "CAR-T6 authority Gate no longer passes 20/4",
    )
    _expect(
        _raw_sha256(root / HISTORICAL_AUTHORITY_REFERENCE)
        == manifest.historical_rhb_t4.authority_sha256
        and _raw_sha256(root / HISTORICAL_MANIFEST_REFERENCE)
        == manifest.historical_rhb_t4.manifest_sha256,
        "historical RHB-T4 checkpoint drift",
    )
    _expect(
        not manifest.rhb_t5_authorized
        and {"RHB_T5", "query_pack_authoring", "label_authoring"}
        == set(manifest.prohibited_next_steps),
        "CAR-T6 must retain the separate RHB-T5 owner Gate",
    )

    records = human_payload.get("records")
    _expect(isinstance(records, list), "human query source must contain records[]")
    assert isinstance(records, list)
    _expect(
        human_payload.get("dataset_version") == HUMAN_SOURCE_ID,
        "human query dataset version drift",
    )
    _expect(
        len(records) == human_inventory.record_count,
        "human query source count differs from inventory",
    )
    case_ids: list[str] = []
    nonblank_queries: list[str] = []
    rows_with_pipeline_outputs = 0
    rows_with_human_labels = 0
    rows_with_failure_categories = 0
    for index, record in enumerate(records):
        _expect(isinstance(record, Mapping), f"human query row {index} must be an object")
        assert isinstance(record, Mapping)
        case_id = record.get("case_id")
        _expect(isinstance(case_id, str) and bool(case_id.strip()), f"row {index} lacks case_id")
        assert isinstance(case_id, str)
        case_ids.append(case_id)
        query = record.get("initial_name")
        if isinstance(query, str) and query.strip():
            nonblank_queries.append(query.strip())
        rows_with_pipeline_outputs += "pipeline_outputs" in record
        rows_with_human_labels += any(str(key).startswith("human_label_") for key in record)
        failure_categories = record.get("failure_categories")
        rows_with_failure_categories += isinstance(failure_categories, list) and bool(
            failure_categories
        )
    _expect(len(case_ids) == len(set(case_ids)), "human query source contains duplicate case IDs")
    normalized_queries = [query.casefold() for query in nonblank_queries]
    unique_query_count = len(set(normalized_queries))
    _expect(
        unique_query_count >= TARGET_CASE_COUNT,
        "human source does not contain 60 unique nonblank query candidates",
    )
    _expect(
        rows_with_pipeline_outputs > 0 and rows_with_human_labels > 0,
        "readiness expected adjacent output/label fields requiring a blind projection",
    )

    projection, projection_manifest = validate_materialized_projection(root)
    output_blind_projection_present = (root / OUTPUT_BLIND_PROJECTION_REFERENCE).exists()
    owner_gate_present = (root / OWNER_AUTHORIZATION_REFERENCE).exists()
    public_query_pack_present = (root / PUBLIC_QUERY_PACK_REFERENCE).exists()
    private_query_pack_present = (root / PRIVATE_QUERY_PACK_REFERENCE).exists()
    query_pack_manifest_present = (rhb_directory / QUERY_PACK_MANIFEST_REFERENCE.name).exists()
    label_artifact_count = sum((root / reference).exists() for reference in LABEL_REFERENCES)
    _expect(
        output_blind_projection_present
        and (root / PROJECTION_MANIFEST_REFERENCE).exists()
        and len(projection.records) == projection_manifest.record_count == 91,
        "validated output-blind projection is incomplete",
    )
    _expect(not owner_gate_present, "an unvalidated RHB-T5 owner authorization already exists")
    _expect(
        not public_query_pack_present
        and not private_query_pack_present
        and not query_pack_manifest_present
        and label_artifact_count == 0,
        "RHB-T5/T6 artifacts already exist despite the closed owner Gate",
    )
    split_field = BenchmarkQuery.model_fields.get("split")
    split_required = split_field is not None and split_field.is_required()
    _expect(not split_required, "BenchmarkQuery must defer split assignment to RHB-T7")
    try:
        ignore_rules = root.joinpath(".gitignore").read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise QueryReadinessError("could not read .gitignore") from error
    _expect(IGNORE_RULE in ignore_rules, "private authoring path is not ignored")

    body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t5-query-authoring-readiness-v2",
        "gate": "RHB-T5",
        "status": "ready_for_separate_owner_authorization",
        "target_case_count": TARGET_CASE_COUNT,
        "source_id": HUMAN_SOURCE_ID,
        "source_record_count": len(records),
        "nonblank_query_count": len(nonblank_queries),
        "unique_nonblank_query_count": unique_query_count,
        "duplicate_nonblank_query_count": len(nonblank_queries) - unique_query_count,
        "candidate_shortfall": max(0, TARGET_CASE_COUNT - unique_query_count),
        "source_rows_with_pipeline_outputs": rows_with_pipeline_outputs,
        "source_rows_with_human_labels": rows_with_human_labels,
        "source_rows_with_failure_categories": rows_with_failure_categories,
        "source_query_scope": "local_only",
        "public_raw_query_pack_authorized": False,
        "public_aggregate_metadata_authorized": True,
        "output_blind_projection_present": output_blind_projection_present,
        "output_blind_projection_valid": True,
        "output_blind_projection_record_count": len(projection.records),
        "output_blind_projection_required": True,
        "private_authoring_path_ignored": True,
        "query_contract_requires_split": split_required,
        "family_safe_split_phase": "RHB-T7",
        "query_contract_split_phase_alignment_required": False,
        "car_t6_gate_result": manifest.gate_result,
        "approved_exact_variant_count": manifest.approved_exact_variant_count,
        "qualifying_family_count": manifest.qualifying_family_count,
        "exact_variant_shortfall": manifest.thresholds.exact_variant_shortfall,
        "qualifying_family_shortfall": manifest.thresholds.qualifying_family_shortfall,
        "public_query_pack_present": public_query_pack_present,
        "private_query_pack_present": private_query_pack_present,
        "query_pack_manifest_present": query_pack_manifest_present,
        "label_artifact_count": label_artifact_count,
        "owner_gate_present": owner_gate_present,
        "challenge_coverage_verified": False,
        "resolver_output_consulted": False,
        "benchmark_labels_consulted": False,
        "network_requests": 0,
        "current_session_eligible_for_authoring": False,
        "rhb_t5_authorized": False,
        "blockers": REQUIRED_BLOCKERS,
        "next_allowed_action": (
            "request_separate_owner_gate_then_author_in_fresh_output_blind_context"
        ),
    }
    return QueryAuthoringReadiness.model_validate(
        {**body, "readiness_sha256": content_sha256(body)}
    )


__all__ = [
    "OUTPUT_BLIND_PROJECTION_REFERENCE",
    "OWNER_AUTHORIZATION_REFERENCE",
    "QueryAuthoringReadiness",
    "QueryReadinessError",
    "build_rhb_t5_query_readiness",
]
