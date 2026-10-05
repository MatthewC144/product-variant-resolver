"""Output-blind, local-only authoring for the RHB-T5 query pack.

This module consumes only the mechanically projected query source plus the frozen
T1/T3 governance artifacts.  It never imports the resolver, labels, split data,
or the mixed raw human source.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    ChallengeTag,
    QueryPack,
    SourceDecisionArtifact,
    SourceDecisionScope,
    SourceDecisionStatus,
    SourceDecisionUse,
    SourceDownstreamPermission,
    SourceInventory,
    content_sha256,
    stable_json_bytes,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_query_projection import (
    IGNORE_RULE,
    OutputBlindSourceManifest,
    OutputBlindSourceProjection,
)

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
PRIVATE_AUTHORING_DIRECTORY = RHB_DIRECTORY / "local-query-authoring-v1"
PROJECTION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "output-blind-source.json"
PROJECTION_MANIFEST_REFERENCE = RHB_DIRECTORY / "query-authoring-source-manifest.json"
OWNER_AUTHORIZATION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "rhb-t5-owner-authorization.json"
AUTHORING_INPUT_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "query-pack-authoring-input.json"
QUERY_PACK_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "query-pack.json"
QUERY_PACK_MANIFEST_REFERENCE = RHB_DIRECTORY / "query-pack-manifest.json"
INVENTORY_REFERENCE = RHB_DIRECTORY / "source-inventory.json"
INVENTORY_MANIFEST_REFERENCE = RHB_DIRECTORY / "source-inventory-manifest.json"
SOURCE_DECISIONS_REFERENCE = RHB_DIRECTORY / "source-decisions.json"
WIKI_SOURCE_REFERENCE = Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json")

HUMAN_SOURCE_ID = "human-labeled-real-noisy-v1"
TARGET_CASE_COUNT = 60
MINIMUM_PER_CHALLENGE = 4
OWNER_AUTHORIZATION_TEXT_SHA256 = "91eb10ee1c4fe78a80a689b2f449652be8f9e12854cec00b84d3cf8a2112e0ef"
ALLOWED_ACTIONS = [
    "author_output_blind_60_case_query_pack",
    "publish_aggregate_only_query_pack_manifest",
]
PROHIBITED_ACTIONS = [
    "RHB-T6",
    "RHB-T7",
    "resolver_evaluation",
    "label_authoring",
    "split_assignment",
]
CHALLENGE_ORDER = [tag.value for tag in ChallengeTag]

NonBlank = Annotated[str, Field(min_length=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
SourceRecordRef = Annotated[
    str,
    Field(pattern=r"^ui-scan-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
]


class QueryAuthoringError(ValueError):
    """Raised when an RHB-T5 authoring boundary or frozen artifact drifts."""


class AuthoringContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RhbT5OwnerAuthorization(AuthoringContract):
    schema_version: Literal["pvr-rhb-t5-owner-authorization-v1"]
    gate: Literal["RHB-T5"]
    authorized_by: Literal["project_owner"]
    authorized_at: AwareDatetime
    authorization_text: NonBlank
    authorization_text_sha256: Sha256
    authorization_sha256: Sha256
    source_id: Literal["human-labeled-real-noisy-v1"]
    source_projection_sha256: Sha256
    source_decisions_sha256: Sha256
    authoring_context: Literal["fresh_output_blind_independent_agent"]
    allowed_actions: list[NonBlank]
    prohibited_actions: list[NonBlank]
    resolver_output_viewed: Literal[False]
    human_labels_viewed: Literal[False]
    failure_categories_viewed: Literal[False]
    split_viewed_or_assigned: Literal[False]
    mixed_raw_source_viewed: Literal[False]
    network_requests: Literal[0]
    rhb_t6_authorized: Literal[False]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]

    @model_validator(mode="after")
    def authorization_is_exact_and_narrow(self) -> RhbT5OwnerAuthorization:
        actual_text_sha256 = hashlib.sha256(self.authorization_text.encode("utf-8")).hexdigest()
        if (
            actual_text_sha256 != OWNER_AUTHORIZATION_TEXT_SHA256
            or self.authorization_text_sha256 != OWNER_AUTHORIZATION_TEXT_SHA256
        ):
            raise ValueError("RHB-T5 owner authorization text is generic or mismatched")
        if self.allowed_actions != ALLOWED_ACTIONS:
            raise ValueError("RHB-T5 owner authorization changed its allowed actions")
        if self.prohibited_actions != PROHIBITED_ACTIONS:
            raise ValueError("RHB-T5 owner authorization changed its prohibited actions")
        expected_authorization_sha256 = content_sha256(
            self.model_dump(mode="json", exclude={"authorization_sha256"})
        )
        if self.authorization_sha256 != expected_authorization_sha256:
            raise ValueError("RHB-T5 owner authorization self-binding checksum is stale")
        return self


class QuerySelection(AuthoringContract):
    source_record_ref: SourceRecordRef
    family_group_key: Slug
    evidence_event_group_key: Slug
    challenge_tags: list[ChallengeTag] = Field(min_length=1)

    @model_validator(mode="after")
    def challenge_tags_are_unique_and_ordered(self) -> QuerySelection:
        values = [tag.value for tag in self.challenge_tags]
        if len(values) != len(set(values)):
            raise ValueError("challenge tags must be unique")
        if values != sorted(values, key=CHALLENGE_ORDER.index):
            raise ValueError("challenge tags must follow the contract order")
        return self


class QueryPackAuthoringInput(AuthoringContract):
    schema_version: Literal["pvr-rhb-t5-query-pack-authoring-input-v1"]
    dataset_version: Literal["representative-hard-benchmark-query-pack-v1"]
    source_id: Literal["human-labeled-real-noisy-v1"]
    source_projection_sha256: Sha256
    owner_authorization_sha256: Sha256
    authored_by: Literal["fresh_output_blind_independent_agent"]
    authored_at: AwareDatetime
    publication_scope: Literal["local_only"]
    resolver_output_viewed: Literal[False]
    human_labels_viewed: Literal[False]
    failure_categories_viewed: Literal[False]
    split_viewed_or_assigned: Literal[False]
    network_requests: Literal[0]
    selections: list[QuerySelection] = Field(
        min_length=TARGET_CASE_COUNT, max_length=TARGET_CASE_COUNT
    )

    @model_validator(mode="after")
    def selections_are_unique_and_stable(self) -> QueryPackAuthoringInput:
        refs = [selection.source_record_ref for selection in self.selections]
        if refs != sorted(refs):
            raise ValueError("authoring selections must be ordered by opaque source reference")
        if len(refs) != len(set(refs)):
            raise ValueError("authoring selections must use unique source records")
        events = [selection.evidence_event_group_key for selection in self.selections]
        if len(events) != len(set(events)):
            raise ValueError("one evidence event cannot count more than once toward the 60 cases")
        family_counts = Counter(selection.family_group_key for selection in self.selections)
        for selection in self.selections:
            tags = set(selection.challenge_tags)
            if ChallengeTag.unknown_to_catalog in tags:
                raise ValueError(
                    "unknown_to_catalog cannot be inferred during output-blind query authoring"
                )
            if (
                ChallengeTag.same_casting_different_release in tags
                and family_counts[selection.family_group_key] < 2
            ):
                raise ValueError(
                    "same_casting_different_release requires at least two selected family rows"
                )
        return self


class QueryPackPublicAggregate(AuthoringContract):
    dataset_version: Literal["representative-hard-benchmark-query-pack-v1"]
    source_id: Literal["human-labeled-real-noisy-v1"]
    source_projection_sha256: Sha256
    owner_authorization_sha256: Sha256
    publication_scope: Literal["local_only"]
    unique_query_count: Literal[60]
    unique_source_record_count: Literal[60]
    unique_evidence_event_count: Literal[60]
    family_group_count: int = Field(ge=1, le=60)
    provisional_challenge_tag_counts: dict[str, int]
    provisional_challenge_tag_shortfalls: dict[str, int]
    minimum_per_challenge: Literal[4]
    provisional_surface_coverage_complete: bool
    challenge_coverage_verified: Literal[False]
    authoring_status: Literal[
        "authoring_artifact_pending_owner_labels_with_declared_surface_shortfalls"
    ]
    contains_query_text: Literal[False]
    contains_source_record_refs: Literal[False]
    contains_expected_status_or_uuid: Literal[False]
    contains_resolver_output_or_rank: Literal[False]
    contains_human_labels: Literal[False]
    contains_failure_categories: Literal[False]
    contains_split: Literal[False]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t6_authorized: Literal[False]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]

    @model_validator(mode="after")
    def coverage_summary_is_recomputable(self) -> QueryPackPublicAggregate:
        if set(self.provisional_challenge_tag_counts) != set(CHALLENGE_ORDER):
            raise ValueError("challenge count keys changed")
        if set(self.provisional_challenge_tag_shortfalls) != set(CHALLENGE_ORDER):
            raise ValueError("challenge shortfall keys changed")
        expected_shortfalls = {
            tag: max(
                0,
                self.minimum_per_challenge - self.provisional_challenge_tag_counts[tag],
            )
            for tag in CHALLENGE_ORDER
        }
        if self.provisional_challenge_tag_shortfalls != expected_shortfalls:
            raise ValueError("challenge shortfalls are inconsistent")
        complete = all(value == 0 for value in expected_shortfalls.values())
        if self.provisional_surface_coverage_complete != complete:
            raise ValueError("challenge coverage result is inconsistent")
        return self


class QueryPackManifest(AuthoringContract):
    schema_name: Literal["pvr-rhb-t5-query-pack-manifest-v1"] = Field(alias="schema")
    sha256: Sha256
    record_count: Literal[60]
    non_sensitive_aggregate: QueryPackPublicAggregate
    non_sensitive_summary: NonBlank

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QueryAuthoringError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise QueryAuthoringError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise QueryAuthoringError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise QueryAuthoringError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise QueryAuthoringError(message)


def _require_private_file(path: Path) -> None:
    _expect(path.is_file() and not path.is_symlink(), f"private file is absent or unsafe: {path}")
    _expect(stat.S_IMODE(path.stat().st_mode) == 0o600, f"private file must use mode 0600: {path}")


def _decision_for_use(source: Any, use: SourceDecisionUse) -> Any:
    return next(decision for decision in source.decisions if decision.use == use)


def _validate_upstream(
    root: Path,
) -> tuple[
    SourceInventory,
    SourceDecisionArtifact,
    OutputBlindSourceProjection,
    OutputBlindSourceManifest,
    RhbT5OwnerAuthorization,
    QueryPackAuthoringInput,
]:
    private_directory = root / PRIVATE_AUTHORING_DIRECTORY
    _expect(
        private_directory.is_dir()
        and not private_directory.is_symlink()
        and stat.S_IMODE(private_directory.stat().st_mode) == 0o700,
        "private authoring directory must be a real 0700 directory",
    )
    try:
        ignore_rules = root.joinpath(".gitignore").read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise QueryAuthoringError("could not read .gitignore") from error
    _expect(IGNORE_RULE in ignore_rules, "private authoring directory is not Git-ignored")

    inventory_payload = _load_object(root / INVENTORY_REFERENCE)
    inventory_manifest_payload = _load_object(root / INVENTORY_MANIFEST_REFERENCE)
    decisions_path = root / SOURCE_DECISIONS_REFERENCE
    decisions_payload = _load_object(decisions_path)
    wiki_payload = _load_object(root / WIKI_SOURCE_REFERENCE)
    inventory, _inventory_manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )

    human_source = next(
        (source for source in decisions.sources if source.source_id == HUMAN_SOURCE_ID), None
    )
    _expect(human_source is not None, "approved human query source is absent from T3")
    assert human_source is not None
    _expect(
        SourceDownstreamPermission.query_pack in human_source.downstream_permissions,
        "T3 no longer permits a query pack for the human source",
    )
    query_decision = _decision_for_use(human_source, SourceDecisionUse.query_text)
    local_decision = _decision_for_use(human_source, SourceDecisionUse.local_only_benchmark_use)
    public_decision = _decision_for_use(human_source, SourceDecisionUse.public_git_artifacts)
    _expect(
        query_decision.status == SourceDecisionStatus.approved
        and query_decision.effective_publication_scope == SourceDecisionScope.local_only
        and query_decision.allowed_fields == ["query_text"],
        "T3 query permission must remain query-text-only and local-only",
    )
    _expect(
        local_decision.status == SourceDecisionStatus.approved
        and local_decision.effective_publication_scope == SourceDecisionScope.local_only,
        "T3 local benchmark permission changed",
    )
    _expect(
        public_decision.status == SourceDecisionStatus.approved
        and public_decision.effective_publication_scope == SourceDecisionScope.aggregate_only,
        "T3 public Git permission must remain aggregate-only",
    )

    projection_path = root / PROJECTION_REFERENCE
    projection_manifest_path = root / PROJECTION_MANIFEST_REFERENCE
    authorization_path = root / OWNER_AUTHORIZATION_REFERENCE
    authoring_input_path = root / AUTHORING_INPUT_REFERENCE
    for private_path in (projection_path, authorization_path, authoring_input_path):
        _require_private_file(private_path)
    _expect(
        projection_manifest_path.is_file() and not projection_manifest_path.is_symlink(),
        "projection manifest is absent or unsafe",
    )
    _expect(
        stat.S_IMODE(projection_manifest_path.stat().st_mode) == 0o644,
        "projection manifest must use mode 0644",
    )
    projection = OutputBlindSourceProjection.model_validate(_load_object(projection_path))
    projection_manifest = OutputBlindSourceManifest.model_validate(
        _load_object(projection_manifest_path)
    )
    projection_sha256 = _raw_sha256(projection_path)
    _expect(
        projection_manifest.sha256 == projection_sha256,
        "private projection checksum differs from its public manifest",
    )
    _expect(
        projection.source_id == HUMAN_SOURCE_ID
        and projection_manifest.record_count == len(projection.records) == 91,
        "output-blind projection capacity or source changed",
    )

    authorization = RhbT5OwnerAuthorization.model_validate(_load_object(authorization_path))
    _expect(
        authorization.source_projection_sha256 == projection_sha256,
        "owner authorization references a different source projection",
    )
    _expect(
        authorization.source_decisions_sha256 == _raw_sha256(decisions_path),
        "owner authorization references different T3 decisions",
    )
    authoring_input = QueryPackAuthoringInput.model_validate(_load_object(authoring_input_path))
    _expect(
        authoring_input.source_projection_sha256 == projection_sha256,
        "authoring input references a different source projection",
    )
    _expect(
        authoring_input.owner_authorization_sha256 == authorization.authorization_sha256,
        "authoring input references a different owner authorization",
    )
    _expect(
        authoring_input.authored_at >= authorization.authorized_at,
        "query authoring cannot predate its owner authorization",
    )
    return inventory, decisions, projection, projection_manifest, authorization, authoring_input


def build_query_pack(root: Path) -> tuple[QueryPack, QueryPackManifest]:
    """Build the deterministic local query pack and aggregate-only public manifest."""

    root = root.absolute()
    _inventory, _decisions, projection, _projection_manifest, _authorization, authoring_input = (
        _validate_upstream(root)
    )
    records = {record.source_record_ref: record for record in projection.records}
    selected_refs = {selection.source_record_ref for selection in authoring_input.selections}
    _expect(
        selected_refs <= set(records), "authoring input references a row outside the projection"
    )

    cases: list[dict[str, Any]] = []
    for index, selection in enumerate(authoring_input.selections, start=1):
        source_record = records[selection.source_record_ref]
        cases.append(
            {
                "case_id": f"rhb-t5-q{index:03d}",
                "query": source_record.query,
                "source_id": HUMAN_SOURCE_ID,
                "source_record_ref": selection.source_record_ref,
                "public_safe": False,
                "family_group_key": selection.family_group_key,
                "evidence_event_group_key": selection.evidence_event_group_key,
                "challenge_tags": [tag.value for tag in selection.challenge_tags],
                "authored_by": authoring_input.authored_by,
                "authored_at": authoring_input.authored_at,
                "resolver_output_viewed": False,
            }
        )

    counts = Counter(tag for case in cases for tag in case["challenge_tags"])
    challenge_counts = {tag: counts[tag] for tag in CHALLENGE_ORDER}
    shortfalls = {
        tag: max(0, MINIMUM_PER_CHALLENGE - challenge_counts[tag]) for tag in CHALLENGE_ORDER
    }
    provisional_surface_coverage_complete = all(value == 0 for value in shortfalls.values())
    query_pack = QueryPack.model_validate(
        {
            "schema_version": "pvr-representative-hard-benchmark-query-pack-v1",
            "dataset_version": authoring_input.dataset_version,
            "publication_scope": "local_only",
            "representative_pilot": False,
            "cases": cases,
        }
    )
    query_pack_raw = stable_json_bytes(query_pack.model_dump(mode="json"))
    aggregate = {
        "dataset_version": authoring_input.dataset_version,
        "source_id": HUMAN_SOURCE_ID,
        "source_projection_sha256": authoring_input.source_projection_sha256,
        "owner_authorization_sha256": authoring_input.owner_authorization_sha256,
        "publication_scope": "local_only",
        "unique_query_count": len({case.query.casefold() for case in query_pack.cases}),
        "unique_source_record_count": len({case.source_record_ref for case in query_pack.cases}),
        "unique_evidence_event_count": len(
            {case.evidence_event_group_key for case in query_pack.cases}
        ),
        "family_group_count": len({case.family_group_key for case in query_pack.cases}),
        "provisional_challenge_tag_counts": challenge_counts,
        "provisional_challenge_tag_shortfalls": shortfalls,
        "minimum_per_challenge": MINIMUM_PER_CHALLENGE,
        "provisional_surface_coverage_complete": (provisional_surface_coverage_complete),
        "challenge_coverage_verified": False,
        "authoring_status": (
            "authoring_artifact_pending_owner_labels_with_declared_surface_shortfalls"
        ),
        "contains_query_text": False,
        "contains_source_record_refs": False,
        "contains_expected_status_or_uuid": False,
        "contains_resolver_output_or_rank": False,
        "contains_human_labels": False,
        "contains_failure_categories": False,
        "contains_split": False,
        "resolver_output_consulted": False,
        "benchmark_labels_consulted": False,
        "network_requests": 0,
        "rhb_t6_authorized": False,
        "rhb_t7_authorized": False,
        "resolver_evaluation_authorized": False,
    }
    summary = (
        "Private 60-case output-blind authoring artifact created with provisional, unverified "
        "surface tags and declared shortfalls; public Git contains aggregate metadata only."
    )
    manifest = QueryPackManifest.model_validate(
        {
            "schema": "pvr-rhb-t5-query-pack-manifest-v1",
            "sha256": hashlib.sha256(query_pack_raw).hexdigest(),
            "record_count": len(query_pack.cases),
            "non_sensitive_aggregate": aggregate,
            "non_sensitive_summary": summary,
        }
    )
    return query_pack, manifest


def validate_materialized_query_pack(root: Path) -> tuple[QueryPack, QueryPackManifest]:
    """Validate private/public materialization against a fresh deterministic build."""

    root = root.absolute()
    expected_pack, expected_manifest = build_query_pack(root)
    pack_path = root / QUERY_PACK_REFERENCE
    manifest_path = root / QUERY_PACK_MANIFEST_REFERENCE
    _require_private_file(pack_path)
    _expect(manifest_path.is_file() and not manifest_path.is_symlink(), "manifest is absent")
    _expect(stat.S_IMODE(manifest_path.stat().st_mode) == 0o644, "manifest must use mode 0644")
    actual_pack = QueryPack.model_validate(_load_object(pack_path))
    actual_manifest = QueryPackManifest.model_validate(_load_object(manifest_path))
    _expect(actual_pack == expected_pack, "materialized query pack is stale or tampered")
    _expect(actual_manifest == expected_manifest, "query-pack manifest is stale or tampered")
    _expect(
        actual_manifest.sha256 == _raw_sha256(pack_path),
        "query-pack manifest checksum differs from private bytes",
    )
    return actual_pack, actual_manifest


def _write_temp(target: Path, raw: bytes, mode: int) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp


def materialize_query_pack(root: Path, *, check: bool = False) -> Literal["created", "unchanged"]:
    """Atomically install the private pack and aggregate-only public manifest."""

    root = root.absolute()
    query_pack, manifest = build_query_pack(root)
    targets = {
        QUERY_PACK_REFERENCE: root / QUERY_PACK_REFERENCE,
        QUERY_PACK_MANIFEST_REFERENCE: root / QUERY_PACK_MANIFEST_REFERENCE,
    }
    states = {reference: target.exists() for reference, target in targets.items()}
    if any(states.values()) and not all(states.values()):
        raise QueryAuthoringError("query-pack materialization is partial")
    expected = {
        QUERY_PACK_REFERENCE: stable_json_bytes(query_pack.model_dump(mode="json")),
        QUERY_PACK_MANIFEST_REFERENCE: stable_json_bytes(
            manifest.model_dump(mode="json", by_alias=True)
        ),
    }
    if all(states.values()):
        validate_materialized_query_pack(root)
        if all(targets[reference].read_bytes() == raw for reference, raw in expected.items()):
            return "unchanged"
        raise QueryAuthoringError("materialized query pack differs from canonical bytes")
    if check:
        raise QueryAuthoringError("private query pack is not materialized")

    temps: list[Path] = []
    installed: list[Path] = []
    try:
        for reference, target in targets.items():
            mode = 0o600 if reference == QUERY_PACK_REFERENCE else 0o644
            temps.append(_write_temp(target, expected[reference], mode))
        for (reference, target), temp in zip(targets.items(), temps, strict=True):
            os.replace(temp, target)
            os.chmod(target, 0o600 if reference == QUERY_PACK_REFERENCE else 0o644)
            installed.append(target)
        validate_materialized_query_pack(root)
    except BaseException:
        for temp in temps:
            temp.unlink(missing_ok=True)
        for target in reversed(installed):
            if target.exists() and not target.is_symlink():
                target.unlink()
        raise
    return "created"


__all__ = [
    "AUTHORING_INPUT_REFERENCE",
    "OWNER_AUTHORIZATION_REFERENCE",
    "OWNER_AUTHORIZATION_TEXT_SHA256",
    "QUERY_PACK_MANIFEST_REFERENCE",
    "QUERY_PACK_REFERENCE",
    "QueryAuthoringError",
    "QueryPackAuthoringInput",
    "QueryPackManifest",
    "RhbT5OwnerAuthorization",
    "build_query_pack",
    "materialize_query_pack",
    "validate_materialized_query_pack",
]
