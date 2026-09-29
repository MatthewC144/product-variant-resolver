"""Append-only owner decisions for CAR-T4 catalog-record proposals.

This module records one output-blind catalog decision at a time.  A catalog decision is deliberately
not a catalog write and not an exact-authority decision.  The private ledger stays in the existing
Git-ignored CAR-T4 directory; only aggregate progress and integrity hashes are public.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_packet import (
    MANIFEST_REFERENCE,
    BlankCatalogDecisionTemplate,
    CatalogProposalPacketEntry,
    derive_workspace,
    validate_catalog_proposal_manifest,
    validate_proposal_bundle,
    validate_proposal_review_packet,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)

LOCAL_DIRECTORY = Path(
    "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1"
)
LEDGER_REFERENCE = LOCAL_DIRECTORY / "catalog-decision-ledger.json"
PUBLIC_PROGRESS_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/catalog-proposal-review-progress.json"
)
PUBLIC_METHOD_REFERENCE = Path("specs/canonical-authority-review-v1/catalog-proposal-review.md")

EVENT_SCHEMA_VERSION = "pvr-canonical-catalog-owner-decision-event-v1"
LEDGER_SCHEMA_VERSION = "pvr-canonical-catalog-owner-decision-ledger-v1"
LEDGER_VERSION = "canonical-catalog-owner-decisions-car-t4-v1"
BASE_CAR_T4_COMMIT = "c3e37eeb5bdeaa7367912424036e8cad008af193"
AUTHORIZATION_CONTRACT_VERSION = "explicit-exact-owner-response-v1"

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OpaqueId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:#-]{0,199}$")]
NonBlank = Annotated[str, Field(min_length=1)]
GitCommit = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]

EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ().-]{7,}\d)(?!\d)")
CREDENTIAL_RE = re.compile(
    r"\b(?:password|passwd|api[_ -]?key|access[_ -]?token|bearer[_ -]?token|"
    r"client[_ -]?secret|private[_ -]?key)\b\s*(?::|=|#)?\s*\S+",
    re.IGNORECASE,
)
ADDRESS_RE = re.compile(
    r"\b\d{1,6}[A-Za-z]?\s+[A-Za-z0-9.' -]{2,}\s+"
    r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct)\b",
    re.IGNORECASE,
)

APPROVAL_REASON = (
    "Project owner accepted all six frozen source-to-proposal mappings for this catalog record; "
    "color=null and edition=null remain explicit constraints."
)
EVENT_01_EXACT_RESPONSE = "批准，color 與 edition 保持 null。"
APPROVAL_FIELDS = (
    "casting",
    "release_year",
    "series",
    "collector_number",
    "series_position",
    "identifiers",
)
APPROVAL_CONSTRAINTS = (
    "authority_approval_not_granted",
    "catalog_application_deferred",
    "color_must_remain_null",
    "edition_must_remain_null",
    "six_source_to_proposal_mappings_accepted",
)
NON_APPROVAL_CONSTRAINTS = (
    "authority_approval_not_granted",
    "catalog_application_deferred",
)
BASE_LOCAL_FILES = {
    "OWNER-REVIEW.md",
    "catalog-decision-template.json",
    "catalog-proposal-review-packet.json",
    "catalog-proposals.json",
}


class DecisionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class CatalogDecision(str, Enum):
    approve_catalog_record = "approve_catalog_record"
    hold = "hold"
    reject = "reject"


class ExpectedOwnerAuthorization(DecisionContract):
    """Trusted caller input for exactly one not-yet-committed append."""

    ordinal: int = Field(ge=1, le=20)
    candidate_id: OpaqueId
    proposal_id: OpaqueId
    decision: CatalogDecision
    exact_owner_response: NonBlank
    review_reason: NonBlank

    @model_validator(mode="after")
    def values_are_exact_and_safe(self) -> ExpectedOwnerAuthorization:
        normalized = _normalize_owner_response(self.exact_owner_response)
        if self.exact_owner_response != normalized:
            raise ValueError("expected owner response must already be normalized")
        _reject_sensitive_text(self.exact_owner_response, "expected owner response")
        _reject_sensitive_text(self.review_reason, "expected review reason")
        return self


@dataclass(frozen=True)
class CommittedProgressAnchor:
    """The current Git HEAD and the public progress bytes committed at that revision."""

    commit_sha: str
    first_parent_sha: str | None
    progress_bytes: bytes | None


@dataclass(frozen=True)
class ProgressCommitment:
    """The immutable public predecessor to which a new working progress file points."""

    anchor_commit_sha: str
    previous_progress_sha256: str | None
    previous_private_ledger_sha256: str | None
    previous_committed_event_count: int


HeadAnchorProvider = Callable[[Path], CommittedProgressAnchor]
ProgressAtCommitProvider = Callable[[Path, str], bytes | None]
FirstParentAtCommitProvider = Callable[[Path, str], str | None]


class CatalogDecisionEvent(DecisionContract):
    schema_version: Literal["pvr-canonical-catalog-owner-decision-event-v1"]
    ordinal: int = Field(ge=1, le=20)
    candidate_id: OpaqueId
    proposal_id: OpaqueId
    packet_sha256: Sha256
    proposal_sha256: Sha256
    product_record_sha256: Sha256
    parent_catalog_reference: Literal["data/catalog.json"]
    parent_catalog_version: Literal["fixture-v1"]
    parent_raw_catalog_sha256: Sha256
    parent_projection_sha256: Sha256
    decision: CatalogDecision
    owner_response_verbatim: NonBlank
    authorization_contract_version: Literal["explicit-exact-owner-response-v1"]
    authorized_exact_owner_response: NonBlank
    authorization_contract_sha256: Sha256
    reviewed_by_role: Literal["project_owner"]
    confirmation_method: Literal["owner_attestation"]
    reviewed_at: AwareDatetime
    review_reason: NonBlank
    accepted_field_mappings: list[
        Literal[
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        ]
    ]
    constraints: list[
        Literal[
            "authority_approval_not_granted",
            "catalog_application_deferred",
            "color_must_remain_null",
            "edition_must_remain_null",
            "six_source_to_proposal_mappings_accepted",
        ]
    ]
    resolver_output_consulted: Literal[False]
    catalog_applied: Literal[False]
    authority_approved: Literal[False]
    rhb_t5_authorized: Literal[False]
    previous_event_sha256: Sha256 | None
    event_sha256: Sha256

    @model_validator(mode="after")
    def decision_semantics_are_explicit(self) -> CatalogDecisionEvent:
        offset = self.reviewed_at.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("reviewed_at must be an aware UTC timestamp")
        if self.reviewed_at.microsecond:
            raise ValueError("reviewed_at must use whole-second precision")
        _reject_sensitive_text(self.owner_response_verbatim, "owner response")
        _reject_sensitive_text(
            self.authorized_exact_owner_response, "authorized exact owner response"
        )
        _reject_sensitive_text(self.review_reason, "review reason")
        normalized = _normalize_owner_response(self.owner_response_verbatim)
        authorized = _normalize_owner_response(self.authorized_exact_owner_response)
        if self.owner_response_verbatim != normalized:
            raise ValueError("owner response must already use the exact normalized literal")
        if self.authorized_exact_owner_response != authorized:
            raise ValueError("authorized owner response must already be normalized")
        if normalized != authorized:
            raise ValueError("owner response differs from the explicit exact authorization")
        authorization_body = {
            "authorization_contract_version": self.authorization_contract_version,
            "candidate_id": self.candidate_id,
            "proposal_id": self.proposal_id,
            "decision": self.decision.value,
            "authorized_exact_owner_response": authorized,
            "review_reason": self.review_reason,
        }
        if self.authorization_contract_sha256 != content_sha256(authorization_body):
            raise ValueError("explicit owner authorization checksum is stale")
        if self.decision == CatalogDecision.approve_catalog_record:
            if self.review_reason != APPROVAL_REASON:
                raise ValueError("approval reason differs from the bounded owner decision")
            if self.accepted_field_mappings != list(APPROVAL_FIELDS):
                raise ValueError("approval must accept exactly the six frozen field mappings")
            if self.constraints != list(APPROVAL_CONSTRAINTS):
                raise ValueError("approval constraints differ from the fail-closed contract")
        else:
            if self.accepted_field_mappings:
                raise ValueError("a held or rejected proposal cannot accept field mappings")
            if self.constraints != list(NON_APPROVAL_CONSTRAINTS):
                raise ValueError("non-approval constraints differ from the contract")
        expected = content_sha256(self.model_dump(mode="json", exclude={"event_sha256"}))
        if self.event_sha256 != expected:
            raise ValueError("decision event checksum is stale")
        return self


class DecisionCounts(DecisionContract):
    approved: int = Field(ge=0, le=20)
    held: int = Field(ge=0, le=20)
    rejected: int = Field(ge=0, le=20)
    pending: int = Field(ge=0, le=20)


class CatalogDecisionLedger(DecisionContract):
    schema_version: Literal["pvr-canonical-catalog-owner-decision-ledger-v1"]
    ledger_version: Literal["canonical-catalog-owner-decisions-car-t4-v1"]
    status: Literal["in_progress_awaiting_owner", "complete_awaiting_batch_application_gate"]
    packet_sha256: Sha256
    proposal_bundle_sha256: Sha256
    candidate_plan_sha256: Sha256
    source_decisions_sha256: Sha256
    parent_catalog_version: Literal["fixture-v1"]
    parent_raw_catalog_sha256: Sha256
    parent_projection_sha256: Sha256
    total_proposal_count: Literal[20]
    events: list[CatalogDecisionEvent] = Field(max_length=20)
    decision_counts: DecisionCounts
    next_pending_ordinal: int | None
    cumulative_events_sha256: Sha256
    catalog_applied_count: Literal[0]
    authority_approved_count: Literal[0]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    ledger_sha256: Sha256


class PublicCatalogDecisionProgress(DecisionContract):
    schema_version: Literal["pvr-canonical-catalog-owner-decision-progress-v1"]
    progress_version: Literal["canonical-catalog-owner-decision-progress-car-t4-v1"]
    publication_scope: Literal[
        "safe_aggregate_and_hash_metadata_only_no_candidate_names_ids_questions_or_verbatim"
    ]
    status: Literal["in_progress_awaiting_owner", "complete_awaiting_batch_application_gate"]
    packet_sha256: Sha256
    private_ledger_sha256: Sha256
    cumulative_events_sha256: Sha256
    event_head_sha256: Sha256
    recorded_event_count: int = Field(ge=1, le=20)
    anchor_commit_sha: GitCommit
    previous_committed_progress_sha256: Sha256 | None
    previous_committed_ledger_sha256: Sha256 | None
    previous_committed_event_count: int = Field(ge=0, le=19)
    total_proposal_count: Literal[20]
    owner_decision_approved_count: int = Field(ge=0, le=20)
    owner_decision_held_count: int = Field(ge=0, le=20)
    owner_decision_rejected_count: int = Field(ge=0, le=20)
    pending_owner_decision_count: int = Field(ge=0, le=20)
    proposal_artifact_review_status: Literal["staged"]
    staged_proposal_artifact_count: Literal[20]
    catalog_applied_count: Literal[0]
    exact_authority_count: Literal[0]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    next_gate: Literal["continue_sequential_owner_review_before_batch_application"]

    @model_validator(mode="after")
    def counts_cover_all_proposals(self) -> PublicCatalogDecisionProgress:
        if (
            self.owner_decision_approved_count
            + self.owner_decision_held_count
            + self.owner_decision_rejected_count
            + self.pending_owner_decision_count
            != self.total_proposal_count
        ):
            raise ValueError("public progress counts do not cover all proposals")
        if (
            self.recorded_event_count
            != self.total_proposal_count - self.pending_owner_decision_count
        ):
            raise ValueError("recorded event count differs from decision counts")
        has_predecessor = self.previous_committed_progress_sha256 is not None
        if has_predecessor != (self.previous_committed_ledger_sha256 is not None):
            raise ValueError("public predecessor progress and ledger commitments must be paired")
        if has_predecessor:
            if self.previous_committed_event_count < 1:
                raise ValueError("a committed predecessor must contain at least one event")
            if self.recorded_event_count != self.previous_committed_event_count + 1:
                raise ValueError("working progress must extend its committed predecessor by one")
        elif self.previous_committed_event_count != 0 or self.recorded_event_count != 1:
            raise ValueError("the first event must point to an empty committed predecessor")
        return self


def _normalize_owner_response(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _reject_sensitive_text(value: str, context: str) -> None:
    if EMAIL_RE.search(value):
        raise AuthorityContractError(f"{context} contains email-like personal information")
    if PHONE_RE.search(value):
        raise AuthorityContractError(f"{context} contains phone-like personal information")
    if CREDENTIAL_RE.search(value):
        raise AuthorityContractError(f"{context} contains credential-like information")
    if ADDRESS_RE.search(value):
        raise AuthorityContractError(f"{context} contains address-like personal information")


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_strict_json(path: Path) -> tuple[Any, bytes]:
    _validate_existing_regular_file(path)
    raw = path.read_bytes()
    try:
        value = json.loads(raw, object_pairs_hook=_duplicate_rejecting_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AuthorityContractError(f"invalid JSON artifact: {path.name}") from error
    return value, raw


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _run_git(root: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise AuthorityContractError(
            "Git is unavailable for decision-prefix verification"
        ) from error


def _git_progress_at(root: Path, commit_sha: str) -> bytes | None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise AuthorityContractError("committed anchor is not a full Git commit SHA")
    result = _run_git(root, ["show", f"{commit_sha}:{PUBLIC_PROGRESS_REFERENCE.as_posix()}"])
    if result.returncode == 0:
        return result.stdout
    missing = b"does not exist" in result.stderr or b"exists on disk, but not in" in result.stderr
    if missing:
        return None
    raise AuthorityContractError("Git could not read the committed public progress anchor")


def _git_first_parent_at(root: Path, commit_sha: str) -> str | None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise AuthorityContractError("first-parent lookup requires a full Git commit SHA")
    result = _run_git(root, ["rev-list", "--parents", "-n", "1", commit_sha])
    if result.returncode != 0:
        raise AuthorityContractError("Git could not resolve a commit's first parent")
    tokens = result.stdout.decode("ascii", errors="strict").strip().split()
    if not tokens or tokens[0] != commit_sha:
        raise AuthorityContractError("Git first-parent metadata is malformed")
    # Merge commits are handled explicitly through Git's first-parent ordering: tokens[1] is the
    # first parent and later parent tokens are intentionally outside this append-only lineage.
    first_parent_sha = tokens[1] if len(tokens) >= 2 else None
    if first_parent_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", first_parent_sha):
        raise AuthorityContractError("Git first parent is not a full commit SHA")
    return first_parent_sha


def _git_head_anchor(root: Path) -> CommittedProgressAnchor:
    result = _run_git(root, ["rev-parse", "--verify", "HEAD"])
    if result.returncode != 0:
        raise AuthorityContractError("catalog decisions require a Git HEAD anchor")
    commit_sha = result.stdout.decode("ascii", errors="strict").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise AuthorityContractError("Git HEAD did not resolve to a full commit SHA")
    return CommittedProgressAnchor(
        commit_sha=commit_sha,
        first_parent_sha=_git_first_parent_at(root, commit_sha),
        progress_bytes=_git_progress_at(root, commit_sha),
    )


def _parse_public_progress(raw: bytes) -> PublicCatalogDecisionProgress:
    try:
        payload = json.loads(raw, object_pairs_hook=_duplicate_rejecting_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AuthorityContractError("committed public progress is invalid JSON") from error
    return PublicCatalogDecisionProgress.model_validate(payload)


def _fresh[T: BaseModel](model: type[T], value: T | Mapping[str, Any]) -> T:
    payload: Any = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return model.model_validate(payload)


def _lexical_root(root: Path) -> Path:
    lexical = Path(os.path.abspath(os.fspath(root)))
    try:
        metadata = lexical.lstat()
    except OSError as error:
        raise AuthorityContractError("repository root is unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise AuthorityContractError("repository root must be a real directory, not a symlink")
    return lexical


def _path_under_root(root: Path, reference: Path, *, leaf_may_be_missing: bool) -> Path:
    if reference.is_absolute() or any(part in {"", ".", ".."} for part in reference.parts):
        raise AuthorityContractError("artifact reference is absolute or contains path traversal")
    target = root / reference
    current = root
    for index, part in enumerate(reference.parts):
        current = current / part
        is_leaf = index == len(reference.parts) - 1
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if is_leaf and leaf_may_be_missing:
                continue
            raise AuthorityContractError("artifact path has a missing ancestor") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise AuthorityContractError("artifact path contains a symlink ancestor")
    try:
        target.parent.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise AuthorityContractError("resolved artifact path escapes repository root") from error
    return target


def _validate_existing_regular_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise AuthorityContractError(f"required artifact is missing: {path.name}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AuthorityContractError(f"required artifact is not a regular file: {path.name}")


def _expected_base_files(artifacts: Any) -> dict[str, bytes]:
    return {
        "catalog-proposals.json": stable_json_bytes(
            artifacts.proposal_bundle.model_dump(mode="json")
        ),
        "catalog-proposal-review-packet.json": stable_json_bytes(
            artifacts.review_packet.model_dump(mode="json")
        ),
        "OWNER-REVIEW.md": artifacts.owner_markdown.encode("utf-8"),
        "catalog-decision-template.json": stable_json_bytes(
            artifacts.decision_template.model_dump(mode="json")
        ),
    }


def _validate_car_t4_inputs(root: Path) -> tuple[Any, str]:
    """Rebuild every CAR-T4 parent and compare every published/local byte before recording."""

    root = _lexical_root(root)
    artifacts = derive_workspace(root)
    local_dir = _path_under_root(root, LOCAL_DIRECTORY, leaf_may_be_missing=False)
    if not local_dir.is_dir():
        raise AuthorityContractError("CAR-T4 local review directory is unavailable")
    names = {item.name for item in local_dir.iterdir()}
    allowed = BASE_LOCAL_FILES | {LEDGER_REFERENCE.name}
    if names not in (BASE_LOCAL_FILES, allowed):
        raise AuthorityContractError(
            "CAR-T4 local review directory contains drift or partial files"
        )
    for name, expected in _expected_base_files(artifacts).items():
        path = local_dir / name
        _validate_existing_regular_file(path)
        if path.read_bytes() != expected:
            raise AuthorityContractError(f"CAR-T4 base artifact changed: {name}")

    bundle_payload, bundle_raw = _read_strict_json(local_dir / "catalog-proposals.json")
    packet_payload, packet_raw = _read_strict_json(
        local_dir / "catalog-proposal-review-packet.json"
    )
    template_payload, template_raw = _read_strict_json(local_dir / "catalog-decision-template.json")
    manifest_payload, manifest_raw = _read_strict_json(root / MANIFEST_REFERENCE)
    validate_proposal_bundle(root, cast(Mapping[str, Any], bundle_payload))
    validate_proposal_review_packet(root, cast(Mapping[str, Any], packet_payload))
    validate_catalog_proposal_manifest(root, cast(Mapping[str, Any], manifest_payload))
    template = BlankCatalogDecisionTemplate.model_validate(template_payload)
    if template != artifacts.decision_template:
        raise AuthorityContractError("blank decision template differs from CAR-T4 inputs")
    if any(
        (
            bundle_raw != stable_json_bytes(artifacts.proposal_bundle.model_dump(mode="json")),
            packet_raw != stable_json_bytes(artifacts.review_packet.model_dump(mode="json")),
            template_raw != stable_json_bytes(artifacts.decision_template.model_dump(mode="json")),
            manifest_raw != stable_json_bytes(artifacts.manifest.model_dump(mode="json")),
        )
    ):
        raise AuthorityContractError("CAR-T4 parent encoding or bytes differ from contract")
    packet_sha = content_sha256(artifacts.review_packet.model_dump(mode="json"))
    if packet_sha != artifacts.decision_template.packet_sha256:
        raise AuthorityContractError("CAR-T4 packet checksum differs from the blank template")
    return artifacts, packet_sha


def _build_event(
    entry: CatalogProposalPacketEntry,
    *,
    ordinal: int,
    packet_sha256: str,
    decision: CatalogDecision,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    reviewed_at: datetime,
    review_reason: str,
    previous_event_sha256: str | None,
) -> CatalogDecisionEvent:
    accepted_fields: Sequence[str]
    constraints: Sequence[str]
    if decision == CatalogDecision.approve_catalog_record:
        accepted_fields = APPROVAL_FIELDS
        constraints = APPROVAL_CONSTRAINTS
    else:
        accepted_fields = ()
        constraints = NON_APPROVAL_CONSTRAINTS
    normalized_authorization = _normalize_owner_response(authorized_exact_owner_response)
    authorization_body = {
        "authorization_contract_version": AUTHORIZATION_CONTRACT_VERSION,
        "candidate_id": entry.candidate.candidate_id,
        "proposal_id": entry.proposal.proposal_id,
        "decision": decision.value,
        "authorized_exact_owner_response": normalized_authorization,
        "review_reason": review_reason,
    }
    body: dict[str, Any] = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "ordinal": ordinal,
        "candidate_id": entry.candidate.candidate_id,
        "proposal_id": entry.proposal.proposal_id,
        "packet_sha256": packet_sha256,
        "proposal_sha256": entry.proposal_sha256,
        "product_record_sha256": entry.proposal.product_record_sha256,
        "parent_catalog_reference": entry.proposal.parent_catalog_reference,
        "parent_catalog_version": entry.proposal.parent_catalog_version,
        "parent_raw_catalog_sha256": entry.proposal.parent_raw_catalog_sha256,
        "parent_projection_sha256": entry.proposal.parent_projection_sha256,
        "decision": decision.value,
        "owner_response_verbatim": _normalize_owner_response(owner_response_verbatim),
        "authorization_contract_version": AUTHORIZATION_CONTRACT_VERSION,
        "authorized_exact_owner_response": normalized_authorization,
        "authorization_contract_sha256": content_sha256(authorization_body),
        "reviewed_by_role": "project_owner",
        "confirmation_method": "owner_attestation",
        "reviewed_at": reviewed_at.isoformat().replace("+00:00", "Z"),
        "review_reason": review_reason,
        "accepted_field_mappings": list(accepted_fields),
        "constraints": list(constraints),
        "resolver_output_consulted": False,
        "catalog_applied": False,
        "authority_approved": False,
        "rhb_t5_authorized": False,
        "previous_event_sha256": previous_event_sha256,
    }
    return CatalogDecisionEvent.model_validate({**body, "event_sha256": content_sha256(body)})


def _build_ledger(
    artifacts: Any,
    packet_sha256: str,
    events: Sequence[CatalogDecisionEvent],
) -> CatalogDecisionLedger:
    counts = Counter(event.decision for event in events)
    decision_counts = {
        "approved": counts[CatalogDecision.approve_catalog_record],
        "held": counts[CatalogDecision.hold],
        "rejected": counts[CatalogDecision.reject],
        "pending": 20 - len(events),
    }
    body: dict[str, Any] = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "ledger_version": LEDGER_VERSION,
        "status": (
            "complete_awaiting_batch_application_gate"
            if len(events) == 20
            else "in_progress_awaiting_owner"
        ),
        "packet_sha256": packet_sha256,
        "proposal_bundle_sha256": content_sha256(artifacts.proposal_bundle.model_dump(mode="json")),
        "candidate_plan_sha256": artifacts.review_packet.candidate_plan_sha256,
        "source_decisions_sha256": artifacts.review_packet.source_decisions_sha256,
        "parent_catalog_version": artifacts.review_packet.raw_catalog_version,
        "parent_raw_catalog_sha256": artifacts.review_packet.raw_catalog_sha256,
        "parent_projection_sha256": artifacts.review_packet.catalog_projection_sha256,
        "total_proposal_count": 20,
        "events": [event.model_dump(mode="json") for event in events],
        "decision_counts": decision_counts,
        "next_pending_ordinal": len(events) + 1 if len(events) < 20 else None,
        "cumulative_events_sha256": content_sha256([event.event_sha256 for event in events]),
        "catalog_applied_count": 0,
        "authority_approved_count": 0,
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    return CatalogDecisionLedger.model_validate({**body, "ledger_sha256": content_sha256(body)})


def _validate_ledger(
    artifacts: Any,
    packet_sha256: str,
    ledger: CatalogDecisionLedger | Mapping[str, Any],
) -> CatalogDecisionLedger:
    supplied = _fresh(CatalogDecisionLedger, ledger)
    entries = artifacts.review_packet.entries
    if len(supplied.events) > len(entries):
        raise AuthorityContractError("decision ledger contains too many events")
    previous: str | None = None
    validated: list[CatalogDecisionEvent] = []
    for ordinal, event in enumerate(supplied.events, start=1):
        entry = entries[ordinal - 1]
        if event.ordinal != ordinal:
            raise AuthorityContractError("decision ordinals must be contiguous")
        if event.candidate_id != entry.candidate.candidate_id:
            raise AuthorityContractError("decision candidate order differs from the frozen packet")
        if event.proposal_id != entry.proposal.proposal_id:
            raise AuthorityContractError("decision proposal differs from the frozen packet")
        if event.packet_sha256 != packet_sha256:
            raise AuthorityContractError("decision packet checksum is stale")
        if event.previous_event_sha256 != previous:
            raise AuthorityContractError("decision previous-event checksum is stale")
        if ordinal == 1 and (
            event.decision != CatalogDecision.approve_catalog_record
            or event.authorized_exact_owner_response != EVENT_01_EXACT_RESPONSE
            or event.owner_response_verbatim != EVENT_01_EXACT_RESPONSE
            or event.review_reason != APPROVAL_REASON
        ):
            raise AuthorityContractError("event 1 differs from the explicit owner authorization")
        expected = _build_event(
            entry,
            ordinal=ordinal,
            packet_sha256=packet_sha256,
            decision=event.decision,
            owner_response_verbatim=event.owner_response_verbatim,
            authorized_exact_owner_response=event.authorized_exact_owner_response,
            reviewed_at=event.reviewed_at,
            review_reason=event.review_reason,
            previous_event_sha256=previous,
        )
        if event != expected:
            raise AuthorityContractError("decision event differs from its deterministic contract")
        validated.append(event)
        previous = event.event_sha256
    expected_ledger = _build_ledger(artifacts, packet_sha256, validated)
    if supplied != expected_ledger:
        raise AuthorityContractError("decision ledger summary or checksum differs from events")
    return supplied


def _build_public_progress(
    ledger: CatalogDecisionLedger, commitment: ProgressCommitment
) -> PublicCatalogDecisionProgress:
    return PublicCatalogDecisionProgress(
        schema_version="pvr-canonical-catalog-owner-decision-progress-v1",
        progress_version="canonical-catalog-owner-decision-progress-car-t4-v1",
        publication_scope=(
            "safe_aggregate_and_hash_metadata_only_no_candidate_names_ids_questions_or_verbatim"
        ),
        status=ledger.status,
        packet_sha256=ledger.packet_sha256,
        private_ledger_sha256=ledger.ledger_sha256,
        cumulative_events_sha256=ledger.cumulative_events_sha256,
        event_head_sha256=ledger.events[-1].event_sha256,
        recorded_event_count=len(ledger.events),
        anchor_commit_sha=commitment.anchor_commit_sha,
        previous_committed_progress_sha256=commitment.previous_progress_sha256,
        previous_committed_ledger_sha256=commitment.previous_private_ledger_sha256,
        previous_committed_event_count=commitment.previous_committed_event_count,
        total_proposal_count=20,
        owner_decision_approved_count=ledger.decision_counts.approved,
        owner_decision_held_count=ledger.decision_counts.held,
        owner_decision_rejected_count=ledger.decision_counts.rejected,
        pending_owner_decision_count=ledger.decision_counts.pending,
        proposal_artifact_review_status="staged",
        staged_proposal_artifact_count=20,
        catalog_applied_count=0,
        exact_authority_count=0,
        resolver_output_consulted=False,
        network_requests=0,
        rhb_t5_authorized=False,
        next_gate="continue_sequential_owner_review_before_batch_application",
    )


def _render_public_method(progress: PublicCatalogDecisionProgress) -> str:
    return "\n".join(
        [
            "# CAR catalog proposal review — public method and progress",
            "",
            "Catalog proposals are reviewed one at a time in the canonical packet order. The",
            "project owner uses explicit owner attestation while resolver/model output remains",
            "hidden. The private append-only ledger binds each answer to the frozen packet, proposal,",
            "product-record and parent-catalog checksums.",
            "Git commits are the external immutable prefix anchor: a later event must extend the",
            "progress committed at HEAD by exactly one canonical event. Rehashing mutable JSON alone",
            "cannot prove append-only history and is rejected.",
            "Before a new event is committed, precommit verification also requires the caller's",
            "external expected ordinal, row identities, decision, exact owner response and bounded",
            "reason; the mutable ledger cannot authorize its own wording.",
            "The verifier walks first-parent history through every commit carrying identical progress",
            "bytes. The commit that introduced those bytes must name its own first parent as the",
            "predecessor; later code-only commits cannot launder a rewritten history.",
            "",
            "## Current progress",
            "",
            f"- Recorded decisions: **{20 - progress.pending_owner_decision_count} / 20**",
            f"- Approved for a later catalog batch gate: **{progress.owner_decision_approved_count}**",
            f"- Held: **{progress.owner_decision_held_count}**",
            f"- Rejected: **{progress.owner_decision_rejected_count}**",
            f"- Pending: **{progress.pending_owner_decision_count}**",
            "- Proposal artifacts remain `staged`: **20**",
            "- Catalog records applied: **0**",
            "- Exact-authority records approved: **0**",
            "- Resolver output consulted: **false**",
            "- Network requests: **0**",
            "- RHB-T5 authorized: **false**",
            "",
            "An owner approval here records only a catalog-proposal decision. It does not edit",
            "`data/catalog.json`, change the staged proposal artifact, approve exact authority, or",
            "authorize RHB-T5. Catalog application waits for a separate batch application Gate after",
            "all 20 proposals have been reviewed.",
            "",
            f"Private ledger SHA-256: `{progress.private_ledger_sha256}`.",
            f"Event head SHA-256: `{progress.event_head_sha256}`.",
            f"Git predecessor commit: `{progress.anchor_commit_sha}`.",
            "",
        ]
    )


def _load_existing_state(
    root: Path, artifacts: Any, packet_sha256: str
) -> tuple[CatalogDecisionLedger | None, PublicCatalogDecisionProgress | None]:
    paths = [
        root / LEDGER_REFERENCE,
        root / PUBLIC_PROGRESS_REFERENCE,
        root / PUBLIC_METHOD_REFERENCE,
    ]
    existence = [path.exists() or path.is_symlink() for path in paths]
    if any(existence) and not all(existence):
        raise AuthorityContractError("partial local/public decision publication detected")
    if not any(existence):
        return None, None
    ledger_payload, _ = _read_strict_json(paths[0])
    progress_payload, progress_raw = _read_strict_json(paths[1])
    _validate_existing_regular_file(paths[2])
    ledger = _validate_ledger(artifacts, packet_sha256, cast(Mapping[str, Any], ledger_payload))
    progress = PublicCatalogDecisionProgress.model_validate(progress_payload)
    commitment = ProgressCommitment(
        anchor_commit_sha=progress.anchor_commit_sha,
        previous_progress_sha256=progress.previous_committed_progress_sha256,
        previous_private_ledger_sha256=progress.previous_committed_ledger_sha256,
        previous_committed_event_count=progress.previous_committed_event_count,
    )
    expected = _build_public_progress(ledger, commitment)
    if progress != expected:
        raise AuthorityContractError("public progress differs from the private ledger")
    if progress_raw != stable_json_bytes(expected.model_dump(mode="json")):
        raise AuthorityContractError("public progress encoding differs from contract")
    if paths[2].read_text(encoding="utf-8") != _render_public_method(expected):
        raise AuthorityContractError("public method/progress document differs from the ledger")
    return ledger, progress


def _validate_progress_history(
    root: Path,
    artifacts: Any,
    packet_sha256: str,
    progress: PublicCatalogDecisionProgress,
    ledger: CatalogDecisionLedger,
    *,
    progress_at_commit_provider: ProgressAtCommitProvider,
    expected_base_commit: str,
) -> None:
    current = progress
    visited: set[str] = set()
    while True:
        count = current.recorded_event_count
        if count > len(ledger.events):
            raise AuthorityContractError(
                "public progress commits more events than the private ledger"
            )
        prefix = _build_ledger(artifacts, packet_sha256, ledger.events[:count])
        if current.private_ledger_sha256 != prefix.ledger_sha256:
            raise AuthorityContractError(
                "committed progress does not bind the private ledger prefix"
            )
        if current.event_head_sha256 != prefix.events[-1].event_sha256:
            raise AuthorityContractError(
                "committed progress event head differs from the ledger prefix"
            )
        predecessor_sha = current.previous_committed_progress_sha256
        if predecessor_sha is None:
            if current.anchor_commit_sha != expected_base_commit:
                raise AuthorityContractError(
                    "first progress is not anchored to the approved CAR-T4 commit"
                )
            if current.previous_committed_event_count != 0:
                raise AuthorityContractError("first progress falsely claims a predecessor event")
            if progress_at_commit_provider(root, current.anchor_commit_sha) is not None:
                raise AuthorityContractError("first progress anchor unexpectedly contains progress")
            return
        if current.anchor_commit_sha in visited:
            raise AuthorityContractError("public progress anchor history contains a cycle")
        visited.add(current.anchor_commit_sha)
        predecessor_raw = progress_at_commit_provider(root, current.anchor_commit_sha)
        if predecessor_raw is None:
            raise AuthorityContractError("committed predecessor progress is missing")
        if _sha256_bytes(predecessor_raw) != predecessor_sha:
            raise AuthorityContractError("committed predecessor progress checksum is stale")
        predecessor = _parse_public_progress(predecessor_raw)
        if (
            predecessor.recorded_event_count != current.previous_committed_event_count
            or predecessor.private_ledger_sha256 != current.previous_committed_ledger_sha256
        ):
            raise AuthorityContractError(
                "committed predecessor summary differs from its commitment"
            )
        current = predecessor


def _validate_git_commitment(
    root: Path,
    artifacts: Any,
    packet_sha256: str,
    ledger: CatalogDecisionLedger,
    progress: PublicCatalogDecisionProgress,
    *,
    allow_uncommitted_current: bool,
    head_anchor_provider: HeadAnchorProvider,
    progress_at_commit_provider: ProgressAtCommitProvider,
    first_parent_at_commit_provider: FirstParentAtCommitProvider,
    expected_base_commit: str,
    expected_uncommitted_authorization: ExpectedOwnerAuthorization | None,
) -> tuple[Literal["committed", "uncommitted_extension"], CommittedProgressAnchor]:
    head = head_anchor_provider(root)
    if not re.fullmatch(r"[0-9a-f]{40}", head.commit_sha):
        raise AuthorityContractError("Git anchor provider returned an invalid commit SHA")
    working_raw = stable_json_bytes(progress.model_dump(mode="json"))
    if head.progress_bytes == working_raw:
        current_commit = head.commit_sha
        first_parent = head.first_parent_sha
        visited = {current_commit}
        depth = 0
        while first_parent is not None:
            depth += 1
            if depth > 10_000:
                raise AuthorityContractError(
                    "Git first-parent progress history is excessively deep"
                )
            if first_parent in visited:
                raise AuthorityContractError("Git first-parent progress history contains a cycle")
            visited.add(first_parent)
            parent_progress = progress_at_commit_provider(root, first_parent)
            if parent_progress != working_raw:
                break
            current_commit = first_parent
            first_parent = first_parent_at_commit_provider(root, current_commit)
            if first_parent is not None and not re.fullmatch(r"[0-9a-f]{40}", first_parent):
                raise AuthorityContractError(
                    "Git first-parent provider returned an invalid commit SHA"
                )
        if first_parent is None:
            raise AuthorityContractError(
                "committed public progress cannot be introduced at a root commit"
            )
        if progress.anchor_commit_sha != first_parent:
            raise AuthorityContractError(
                "committed public progress must name the introduction commit's first parent as "
                "its predecessor"
            )
        _validate_progress_history(
            root,
            artifacts,
            packet_sha256,
            progress,
            ledger,
            progress_at_commit_provider=progress_at_commit_provider,
            expected_base_commit=expected_base_commit,
        )
        return "committed", head
    if not allow_uncommitted_current:
        raise AuthorityContractError(
            "working public progress is not the Git-committed HEAD anchor; commit it first or use "
            "--allow-uncommitted-current only for precommit verification"
        )
    if head.progress_bytes is None:
        if (
            head.commit_sha != expected_base_commit
            or progress.anchor_commit_sha != head.commit_sha
            or progress.previous_committed_progress_sha256 is not None
            or progress.previous_committed_ledger_sha256 is not None
            or progress.recorded_event_count != 1
        ):
            raise AuthorityContractError("uncommitted event 1 does not strictly extend CAR-T4 HEAD")
    else:
        predecessor = _parse_public_progress(head.progress_bytes)
        if (
            progress.anchor_commit_sha != head.commit_sha
            or progress.previous_committed_progress_sha256 != _sha256_bytes(head.progress_bytes)
            or progress.previous_committed_ledger_sha256 != predecessor.private_ledger_sha256
            or progress.previous_committed_event_count != predecessor.recorded_event_count
            or progress.recorded_event_count != predecessor.recorded_event_count + 1
        ):
            raise AuthorityContractError(
                "working progress is not exactly one event beyond committed HEAD"
            )
        _validate_progress_history(
            root,
            artifacts,
            packet_sha256,
            predecessor,
            ledger,
            progress_at_commit_provider=progress_at_commit_provider,
            expected_base_commit=expected_base_commit,
        )
    _validate_progress_history(
        root,
        artifacts,
        packet_sha256,
        progress,
        ledger,
        progress_at_commit_provider=progress_at_commit_provider,
        expected_base_commit=expected_base_commit,
    )
    if expected_uncommitted_authorization is None:
        raise AuthorityContractError(
            "precommit verification requires an external expected owner authorization"
        )
    appended = ledger.events[-1]
    expected = expected_uncommitted_authorization
    if (
        appended.ordinal != expected.ordinal
        or appended.candidate_id != expected.candidate_id
        or appended.proposal_id != expected.proposal_id
        or appended.decision != expected.decision
        or appended.owner_response_verbatim != expected.exact_owner_response
        or appended.authorized_exact_owner_response != expected.exact_owner_response
        or appended.review_reason != expected.review_reason
    ):
        raise AuthorityContractError(
            "uncommitted event differs from the external expected owner authorization"
        )
    return "uncommitted_extension", head


def _write_staged(path: Path, payload: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _publish_atomically(files: Mapping[Path, bytes]) -> None:
    originals = {path: path.read_bytes() if path.exists() else None for path in files}
    staged = {path: _write_staged(path, payload) for path, payload in files.items()}
    replaced: list[Path] = []
    try:
        for path in files:
            os.replace(staged[path], path)
            replaced.append(path)
        for parent in {path.parent for path in files}:
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                restore = _write_staged(path, original)
                os.replace(restore, path)
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)


def _publication_bytes(
    ledger: CatalogDecisionLedger, commitment: ProgressCommitment
) -> dict[Path, bytes]:
    progress = _build_public_progress(ledger, commitment)
    return {
        LEDGER_REFERENCE: stable_json_bytes(ledger.model_dump(mode="json")),
        PUBLIC_PROGRESS_REFERENCE: stable_json_bytes(progress.model_dump(mode="json")),
        PUBLIC_METHOD_REFERENCE: _render_public_method(progress).encode("utf-8"),
    }


def check_catalog_decisions(
    root: Path,
    *,
    allow_uncommitted_current: bool = False,
    head_anchor_provider: HeadAnchorProvider = _git_head_anchor,
    progress_at_commit_provider: ProgressAtCommitProvider = _git_progress_at,
    first_parent_at_commit_provider: FirstParentAtCommitProvider = _git_first_parent_at,
    expected_base_commit: str = BASE_CAR_T4_COMMIT,
    expected_uncommitted_authorization: ExpectedOwnerAuthorization | None = None,
) -> CatalogDecisionLedger:
    root = _lexical_root(root)
    artifacts, packet_sha = _validate_car_t4_inputs(root)
    ledger, progress = _load_existing_state(root, artifacts, packet_sha)
    if ledger is None or progress is None:
        raise AuthorityContractError("catalog decision ledger is missing; --check never writes")
    _validate_git_commitment(
        root,
        artifacts,
        packet_sha,
        ledger,
        progress,
        allow_uncommitted_current=allow_uncommitted_current,
        head_anchor_provider=head_anchor_provider,
        progress_at_commit_provider=progress_at_commit_provider,
        first_parent_at_commit_provider=first_parent_at_commit_provider,
        expected_base_commit=expected_base_commit,
        expected_uncommitted_authorization=expected_uncommitted_authorization,
    )
    return ledger


def record_catalog_decision(
    root: Path,
    *,
    candidate_id: str,
    proposal_id: str,
    decision: CatalogDecision | str,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str | None = None,
    review_reason: str | None = None,
    reviewed_at: datetime | None = None,
    head_anchor_provider: HeadAnchorProvider = _git_head_anchor,
    progress_at_commit_provider: ProgressAtCommitProvider = _git_progress_at,
    first_parent_at_commit_provider: FirstParentAtCommitProvider = _git_first_parent_at,
    expected_base_commit: str = BASE_CAR_T4_COMMIT,
) -> tuple[Literal["recorded", "unchanged"], CatalogDecisionLedger]:
    root = _lexical_root(root)
    artifacts, packet_sha = _validate_car_t4_inputs(root)
    ledger, progress = _load_existing_state(root, artifacts, packet_sha)
    parsed_decision = CatalogDecision(decision)
    normalized_response = _normalize_owner_response(owner_response_verbatim)
    if not normalized_response:
        raise AuthorityContractError("owner response cannot be blank")
    _reject_sensitive_text(normalized_response, "owner response")
    existing_events = list(ledger.events) if ledger is not None else []
    existing_match = next(
        (
            event
            for event in existing_events
            if event.candidate_id == candidate_id or event.proposal_id == proposal_id
        ),
        None,
    )
    if existing_match is not None and (
        existing_match.decision != parsed_decision
        or existing_match.owner_response_verbatim != normalized_response
    ):
        raise AuthorityContractError("conflicting retry for an already recorded proposal")
    ordinal = existing_match.ordinal if existing_match is not None else len(existing_events) + 1
    if ordinal == 1:
        effective_authorized_response = EVENT_01_EXACT_RESPONSE
        if authorized_exact_owner_response is not None and (
            _normalize_owner_response(authorized_exact_owner_response) != EVENT_01_EXACT_RESPONSE
        ):
            raise AuthorityContractError("event 1 authorization literal is fixed by the owner")
        if parsed_decision != CatalogDecision.approve_catalog_record:
            raise AuthorityContractError(
                "event 1 decision differs from explicit owner authorization"
            )
    else:
        effective_authorized_response = _normalize_owner_response(
            authorized_exact_owner_response or ""
        )
        if not effective_authorized_response:
            raise AuthorityContractError(
                "future decisions require an explicit authorized exact owner response"
            )
    if normalized_response != effective_authorized_response:
        raise AuthorityContractError(
            "owner response differs from the explicit exact authorization literal"
        )
    if parsed_decision == CatalogDecision.approve_catalog_record:
        if review_reason is not None and review_reason.strip() != APPROVAL_REASON:
            raise AuthorityContractError("approval reason cannot broaden the owner decision")
        effective_reason = APPROVAL_REASON
    else:
        effective_reason = (review_reason or "").strip()
        if not effective_reason:
            raise AuthorityContractError("held or rejected decisions require a review reason")
    _reject_sensitive_text(effective_authorized_response, "authorized exact owner response")
    _reject_sensitive_text(effective_reason, "review reason")
    external_expectation = ExpectedOwnerAuthorization(
        ordinal=ordinal,
        candidate_id=candidate_id,
        proposal_id=proposal_id,
        decision=parsed_decision,
        exact_owner_response=effective_authorized_response,
        review_reason=effective_reason,
    )

    head: CommittedProgressAnchor
    state: Literal["committed", "uncommitted_extension"]
    if ledger is None or progress is None:
        head = head_anchor_provider(root)
        if head.commit_sha != expected_base_commit or head.progress_bytes is not None:
            raise AuthorityContractError(
                "event 1 requires the exact approved CAR-T4 Git HEAD with no progress artifact"
            )
        state = "committed"
    else:
        state, head = _validate_git_commitment(
            root,
            artifacts,
            packet_sha,
            ledger,
            progress,
            allow_uncommitted_current=True,
            head_anchor_provider=head_anchor_provider,
            progress_at_commit_provider=progress_at_commit_provider,
            first_parent_at_commit_provider=first_parent_at_commit_provider,
            expected_base_commit=expected_base_commit,
            expected_uncommitted_authorization=external_expectation,
        )
    for event in existing_events:
        if event.candidate_id == candidate_id or event.proposal_id == proposal_id:
            if (
                event.candidate_id == candidate_id
                and event.proposal_id == proposal_id
                and event.decision == parsed_decision
                and event.owner_response_verbatim == normalized_response
                and event.authorized_exact_owner_response == effective_authorized_response
                and event.review_reason == effective_reason
            ):
                return "unchanged", cast(CatalogDecisionLedger, ledger)
            raise AuthorityContractError("conflicting retry for an already recorded proposal")

    if state == "uncommitted_extension":
        raise AuthorityContractError(
            "cannot append another event until the current public progress is committed"
        )
    if ordinal > len(artifacts.review_packet.entries):
        raise AuthorityContractError("all catalog proposals already have owner decisions")
    entry = artifacts.review_packet.entries[ordinal - 1]
    if candidate_id != entry.candidate.candidate_id or proposal_id != entry.proposal.proposal_id:
        raise AuthorityContractError(f"next pending canonical proposal is ordinal {ordinal}")
    timestamp = reviewed_at or datetime.now(UTC).replace(microsecond=0)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise AuthorityContractError("reviewed_at must be an aware UTC timestamp")
    timestamp = timestamp.astimezone(UTC).replace(microsecond=0)
    previous = existing_events[-1].event_sha256 if existing_events else None
    event = _build_event(
        entry,
        ordinal=ordinal,
        packet_sha256=packet_sha,
        decision=parsed_decision,
        owner_response_verbatim=normalized_response,
        authorized_exact_owner_response=effective_authorized_response,
        reviewed_at=timestamp,
        review_reason=effective_reason,
        previous_event_sha256=previous,
    )
    result = _build_ledger(artifacts, packet_sha, [*existing_events, event])
    _validate_ledger(artifacts, packet_sha, result)

    commitment = ProgressCommitment(
        anchor_commit_sha=head.commit_sha,
        previous_progress_sha256=(
            _sha256_bytes(head.progress_bytes) if head.progress_bytes is not None else None
        ),
        previous_private_ledger_sha256=(
            ledger.ledger_sha256 if head.progress_bytes is not None and ledger is not None else None
        ),
        previous_committed_event_count=(
            len(existing_events) if head.progress_bytes is not None else 0
        ),
    )

    absolute_files = {
        _path_under_root(root, reference, leaf_may_be_missing=True): payload
        for reference, payload in _publication_bytes(result, commitment).items()
    }
    _publish_atomically(absolute_files)
    checked = check_catalog_decisions(
        root,
        allow_uncommitted_current=True,
        head_anchor_provider=head_anchor_provider,
        progress_at_commit_provider=progress_at_commit_provider,
        first_parent_at_commit_provider=first_parent_at_commit_provider,
        expected_base_commit=expected_base_commit,
        expected_uncommitted_authorization=external_expectation,
    )
    if checked != result:
        raise AuthorityContractError("published catalog decision ledger failed verification")
    return "recorded", result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record/check one ordered CAR catalog-proposal owner decision"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--candidate-id")
    parser.add_argument("--proposal-id")
    parser.add_argument("--decision", choices=[item.value for item in CatalogDecision])
    parser.add_argument("--owner-response")
    parser.add_argument("--authorized-exact-owner-response")
    parser.add_argument("--review-reason")
    parser.add_argument("--allow-uncommitted-current", action="store_true")
    parser.add_argument("--expected-ordinal", type=int)
    parser.add_argument("--expected-candidate-id")
    parser.add_argument("--expected-proposal-id")
    parser.add_argument("--expected-decision", choices=[item.value for item in CatalogDecision])
    parser.add_argument("--expected-owner-response")
    parser.add_argument("--expected-review-reason")
    args = parser.parse_args(argv)
    try:
        if args.check:
            if any(
                value is not None
                for value in (
                    args.candidate_id,
                    args.proposal_id,
                    args.decision,
                    args.owner_response,
                    args.authorized_exact_owner_response,
                    args.review_reason,
                )
            ):
                raise AuthorityContractError("--check cannot be combined with recording arguments")
            expected_values = (
                args.expected_ordinal,
                args.expected_candidate_id,
                args.expected_proposal_id,
                args.expected_decision,
                args.expected_owner_response,
                args.expected_review_reason,
            )
            if args.allow_uncommitted_current:
                if None in expected_values:
                    raise AuthorityContractError(
                        "precommit --check requires every --expected-* authorization field"
                    )
                expected_authorization = ExpectedOwnerAuthorization(
                    ordinal=args.expected_ordinal,
                    candidate_id=args.expected_candidate_id,
                    proposal_id=args.expected_proposal_id,
                    decision=args.expected_decision,
                    exact_owner_response=args.expected_owner_response,
                    review_reason=args.expected_review_reason,
                )
            else:
                if any(value is not None for value in expected_values):
                    raise AuthorityContractError(
                        "--expected-* fields require --allow-uncommitted-current"
                    )
                expected_authorization = None
            ledger = check_catalog_decisions(
                args.root,
                allow_uncommitted_current=args.allow_uncommitted_current,
                expected_uncommitted_authorization=expected_authorization,
            )
            status = "valid"
        else:
            if args.allow_uncommitted_current:
                raise AuthorityContractError(
                    "--allow-uncommitted-current is only valid with --check"
                )
            if any(
                value is not None
                for value in (
                    args.expected_ordinal,
                    args.expected_candidate_id,
                    args.expected_proposal_id,
                    args.expected_decision,
                    args.expected_owner_response,
                    args.expected_review_reason,
                )
            ):
                raise AuthorityContractError("--expected-* fields are only valid with --check")
            if None in (
                args.candidate_id,
                args.proposal_id,
                args.decision,
                args.owner_response,
            ):
                parser.error(
                    "recording requires --candidate-id, --proposal-id, --decision and "
                    "--owner-response"
                )
            status, ledger = record_catalog_decision(
                args.root,
                candidate_id=args.candidate_id,
                proposal_id=args.proposal_id,
                decision=args.decision,
                owner_response_verbatim=args.owner_response,
                authorized_exact_owner_response=args.authorized_exact_owner_response,
                review_reason=args.review_reason,
            )
        print(
            json.dumps(
                {
                    "status": status,
                    "recorded": len(ledger.events),
                    "pending": ledger.decision_counts.pending,
                    "approved_for_later_batch_gate": ledger.decision_counts.approved,
                    "catalog_applied": 0,
                    "exact_authority_approved": 0,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (AuthorityContractError, OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
