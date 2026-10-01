"""Prepare the local, output-blind CAR-T5 exact-authority owner packet.

Preparation reconciles frozen CAR-T4 proposals to the applied catalog-v2 rows.  It never records
an owner outcome, creates authority, consults the resolver, or authorizes RHB-T5.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_review import (
    AuthorityCandidate,
    AuthorityContractError,
    CanonicalProductRecord,
    CatalogResolutionBinding,
    EvidenceAgreement,
    VariantField,
    VariantFieldEvidence,
    content_sha256,
    stable_json_bytes,
)
from product_variant_resolver.canonical_catalog_application import (
    CatalogApplicationAuthorizationEvent,
    CatalogApplicationManifest,
)
from product_variant_resolver.canonical_catalog_decisions import (
    CatalogDecision,
    _read_strict_json,
    _validate_car_t4_inputs,
    _validate_ledger,
)

PREPARATION_VERSION: Literal["canonical-authority-review-car-t5p-v1"] = (
    "canonical-authority-review-car-t5p-v1"
)
PRIVATE_DIRECTORY = Path(
    "data/authority-review/canonical-authority-review-v1/local-authority-review-v1"
)
PRIVATE_PACKET_REFERENCE = PRIVATE_DIRECTORY / "authority-review-packet.json"
OWNER_REVIEW_REFERENCE = PRIVATE_DIRECTORY / "OWNER-REVIEW.md"
PUBLIC_MANIFEST_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/authority-review-packet-manifest.json"
)
CAR_T4_LOCAL_DIRECTORY = Path(
    "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1"
)
CAR_T4_LEDGER_REFERENCE = CAR_T4_LOCAL_DIRECTORY / "catalog-decision-ledger.json"
APPLICATION_EVENT_REFERENCE = CAR_T4_LOCAL_DIRECTORY / "catalog-application-event.json"
APPLICATION_MANIFEST_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/catalog-application-manifest.json"
)
CATALOG_REFERENCE = Path("data/catalog.json")
IGNORE_RULE = "/data/authority-review/canonical-authority-review-v1/local-authority-review-v1/"

EXPECTED_PACKET_SHA256 = "8997392511b1eb7a55abab3573f9773a57cb3501df5ed01d124952fc6df70ddd"
EXPECTED_PROPOSAL_BUNDLE_SHA256 = "cd7da71b0635d2fdec3531aa4b5cdbf84df925448e1ae4cdef1a765676779898"
EXPECTED_LEDGER_SHA256 = "c1fe895d5fa525b49c9115ffc4883e0b6d54bc172a3af7dc2fcb73ab9bc39b85"
EXPECTED_APPLICATION_MANIFEST_SHA256 = (
    "cf1c95ec8985f80f9ee48c2d8af8b297f5e7d771eff3bb07990034643e4b37b4"
)
EXPECTED_CATALOG_SHA256 = "e763c8739a76ab4cc9b66169aecd4aea241ee810d8a27cdfb7d05bcacd98562e"
SUPPORTED_FIELDS = (
    VariantField.casting,
    VariantField.release_year,
    VariantField.series,
    VariantField.collector_number,
    VariantField.series_position,
    VariantField.identifiers,
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OpaqueId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:#-]{0,199}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class PreparationContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class AuthorityReviewPreparationEntry(PreparationContract):
    ordinal: int = Field(ge=1, le=20)
    candidate: AuthorityCandidate
    resolution_binding: CatalogResolutionBinding
    catalog_record: CanonicalProductRecord
    catalog_record_sha256: Sha256
    field_evidence: list[VariantFieldEvidence] = Field(min_length=6, max_length=6)
    variant_note_context: str | None
    variant_note_role: Literal["context_only_not_color_or_edition_evidence"]
    explicit_color: None
    explicit_edition: None
    missing_or_conflicting_items: list[OpaqueId]
    publication_limits: tuple[
        Literal["community_snapshot_exact_only"],
        Literal["catalog_inclusion_is_not_exact_authority"],
        Literal["rhb_t5_not_authorized"],
    ]
    owner_questions: list[NonBlank] = Field(min_length=1)
    entry_sha256: Sha256

    @model_validator(mode="after")
    def entry_is_staged_complete_and_output_blind(self) -> AuthorityReviewPreparationEntry:
        if self.ordinal != self.resolution_binding.ordinal:
            raise ValueError("entry ordinal differs from its catalog resolution")
        if self.candidate.candidate_id != self.resolution_binding.candidate_id:
            raise ValueError("entry candidate differs from its catalog resolution")
        if self.candidate.canonical_uuid != self.resolution_binding.applied_canonical_uuid:
            raise ValueError("entry UUID differs from its catalog resolution")
        if (
            self.candidate.family_group_key != self.resolution_binding.family_group_key
            or self.candidate.proposed_release_key != self.resolution_binding.release_key
        ):
            raise ValueError("entry family or release differs from its catalog resolution")
        if self.catalog_record.canonical_uuid != self.candidate.canonical_uuid:
            raise ValueError("catalog record differs from the derived candidate UUID")
        if (
            self.catalog_record.family_group_key != self.candidate.family_group_key
            or self.catalog_record.release_key != self.candidate.proposed_release_key
        ):
            raise ValueError("catalog record family or release differs from the candidate")
        if self.catalog_record.color is not None or self.catalog_record.edition is not None:
            raise ValueError("CAR-T5P must preserve null color and edition")
        if [row.field for row in self.field_evidence] != list(SUPPORTED_FIELDS):
            raise ValueError("entry requires six ordered supported evidence rows")
        if any(row.agreement != EvidenceAgreement.agrees for row in self.field_evidence):
            raise ValueError("preparation requires six complete agreeing evidence rows")
        if self.missing_or_conflicting_items:
            raise ValueError("resolved preparation entries cannot retain conflicts or shortfalls")
        expected = content_sha256(self.model_dump(mode="json", exclude={"entry_sha256"}))
        if self.entry_sha256 != expected:
            raise ValueError("preparation entry checksum is stale")
        return self


class AuthorityReviewFamilyBatch(PreparationContract):
    batch_ordinal: int = Field(ge=1, le=7)
    family_group_key: OpaqueId
    entry_ordinals: list[int] = Field(min_length=2, max_length=3)
    candidate_ids: list[OpaqueId] = Field(min_length=2, max_length=3)
    entry_sha256s: list[Sha256] = Field(min_length=2, max_length=3)
    batch_sha256: Sha256

    @model_validator(mode="after")
    def family_batch_is_ordered_and_bound(self) -> AuthorityReviewFamilyBatch:
        if len({len(self.entry_ordinals), len(self.candidate_ids), len(self.entry_sha256s)}) != 1:
            raise ValueError("family batch vectors must have equal length")
        if self.entry_ordinals != sorted(set(self.entry_ordinals)):
            raise ValueError("family batch ordinals must be unique and ordered")
        expected = content_sha256(self.model_dump(mode="json", exclude={"batch_sha256"}))
        if self.batch_sha256 != expected:
            raise ValueError("family batch checksum is stale")
        return self


class AuthorityReviewPreparationPacket(PreparationContract):
    schema_version: Literal["pvr-canonical-authority-review-packet-v1"]
    packet_version: Literal["canonical-authority-review-car-t5p-v1"]
    packet_purpose: Literal["output_blind_exact_authority_preparation_only_no_owner_decision"]
    publication_scope: Literal["local_only_git_ignored"]
    car_t4_packet_sha256: Sha256
    proposal_bundle_sha256: Sha256
    catalog_decision_ledger_sha256: Sha256
    catalog_application_manifest_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    entries: list[AuthorityReviewPreparationEntry] = Field(min_length=20, max_length=20)
    family_batches: list[AuthorityReviewFamilyBatch] = Field(min_length=7, max_length=7)
    review_event_count: Literal[0]
    owner_attestation_count: Literal[0]
    approved_exact_count: Literal[0]
    authority_bundle_record_count: Literal[0]
    resolver_output_consulted: Literal[False]
    resolver_output_included: Literal[False]
    predicted_uuid_included: Literal[False]
    model_scores_included: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    status: Literal["awaiting_owner_review_gate"]

    @model_validator(mode="after")
    def packet_is_complete_and_undecided(self) -> AuthorityReviewPreparationPacket:
        if [entry.ordinal for entry in self.entries] != list(range(1, 21)):
            raise ValueError("packet entries must preserve contiguous CAR-T4 packet order")
        candidate_ids = [entry.candidate.candidate_id for entry in self.entries]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("packet candidate IDs must be distinct")
        bindings = [entry.resolution_binding for entry in self.entries]
        for values, label in (
            ([str(item.applied_canonical_uuid) for item in bindings], "catalog UUIDs"),
            ([item.applied_canonical_id for item in bindings], "canonical IDs"),
            ([item.release_key for item in bindings], "release keys"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"packet {label} must be distinct")
        if [batch.batch_ordinal for batch in self.family_batches] != list(range(1, 8)):
            raise ValueError("family batches must be contiguous")
        covered = [ordinal for batch in self.family_batches for ordinal in batch.entry_ordinals]
        if sorted(covered) != list(range(1, 21)) or len(covered) != len(set(covered)):
            raise ValueError("family batches must cover every entry exactly once")
        by_ordinal = {entry.ordinal: entry for entry in self.entries}
        for batch in self.family_batches:
            selected = [by_ordinal[ordinal] for ordinal in batch.entry_ordinals]
            if any(
                entry.candidate.family_group_key != batch.family_group_key for entry in selected
            ):
                raise ValueError("family batch mixes candidate families")
            if batch.candidate_ids != [entry.candidate.candidate_id for entry in selected]:
                raise ValueError("family batch candidate order is stale")
            if batch.entry_sha256s != [entry.entry_sha256 for entry in selected]:
                raise ValueError("family batch entry hashes are stale")
        return self


class AuthorityReviewPacketManifest(PreparationContract):
    schema_version: Literal["pvr-canonical-authority-review-packet-manifest-v1"]
    manifest_version: Literal["canonical-authority-review-car-t5p-v1"]
    publication_scope: Literal[
        "safe_hash_count_and_attribution_only_no_product_rows_questions_or_owner_responses"
    ]
    status: Literal["awaiting_owner_review_gate"]
    car_t4_packet_sha256: Sha256
    proposal_bundle_sha256: Sha256
    catalog_decision_ledger_sha256: Sha256
    catalog_application_manifest_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    private_packet_sha256: Sha256
    private_owner_review_sha256: Sha256
    ordered_entry_sha256s: list[Sha256] = Field(min_length=20, max_length=20)
    entry_count: Literal[20]
    family_count: Literal[7]
    family_batch_sizes: list[int] = Field(min_length=7, max_length=7)
    evidence_row_count: Literal[120]
    evidence_rows_per_entry: Literal[6]
    null_color_count: Literal[20]
    null_edition_count: Literal[20]
    review_event_count: Literal[0]
    owner_attestation_count: Literal[0]
    approved_exact_count: Literal[0]
    authority_bundle_record_count: Literal[0]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    reviewed_by_role: Literal["project_owner"]
    source_id: Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]
    license_name: Literal["CC-BY-SA"]
    license_url: Literal["https://www.fandom.com/licensing"]
    share_alike_required: Literal[True]
    attribution: Literal[
        "Source: Hot Wheels Wiki contributors, List of 2025 Hot Wheels, revision 790665; normalized derivative."
    ]
    next_gate: Literal["owner_gate_t5_g1_explicit_staged_to_reviewed_outcomes_required"]

    @model_validator(mode="after")
    def aggregate_counts_are_exact(self) -> AuthorityReviewPacketManifest:
        if sorted(self.family_batch_sizes) != [2, 3, 3, 3, 3, 3, 3]:
            raise ValueError("manifest requires six three-entry and one two-entry family batches")
        if len(set(self.ordered_entry_sha256s)) != 20:
            raise ValueError("manifest entry hashes must be distinct")
        return self


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _root(root: Path) -> Path:
    lexical = root.absolute()
    try:
        metadata = lexical.lstat()
    except OSError as error:
        raise AuthorityContractError("repository root is unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise AuthorityContractError("repository root must be a real directory")
    return lexical


def _safe_path(root: Path, reference: Path, *, allow_missing_leaf: bool) -> Path:
    if reference.is_absolute() or any(part in {"", ".", ".."} for part in reference.parts):
        raise AuthorityContractError("artifact reference is unsafe")
    current = root
    for index, part in enumerate(reference.parts):
        current = current / part
        if not current.exists() and not current.is_symlink():
            if allow_missing_leaf:
                continue
            raise AuthorityContractError("artifact path is missing")
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise AuthorityContractError("artifact path contains a symlink")
        if index < len(reference.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise AuthorityContractError("artifact path ancestor is not a directory")
    try:
        current.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise AuthorityContractError("artifact path escapes repository root") from error
    return current


def _strict_json(path: Path) -> tuple[dict[str, Any], bytes]:
    payload, raw = _read_strict_json(path)
    if not isinstance(payload, dict):
        raise AuthorityContractError(f"{path.name} root must be an object")
    return cast(dict[str, Any], payload), raw


def _require_ignore_rule(root: Path) -> None:
    path = _safe_path(root, Path(".gitignore"), allow_missing_leaf=False)
    if not path.is_file():
        raise AuthorityContractError(".gitignore is unavailable")
    rules = path.read_text(encoding="utf-8").splitlines()
    if rules.count(IGNORE_RULE) != 1:
        raise AuthorityContractError("exact CAR-T5 private workspace ignore rule is required")


def _catalog_value(row: Mapping[str, Any], field: VariantField) -> Any:
    if field != VariantField.identifiers:
        return row.get(field.value)
    identifiers = row.get("identifiers")
    if not isinstance(identifiers, list) or len(identifiers) != 1:
        raise AuthorityContractError("applied catalog row requires one typed toy identifier")
    identifier = identifiers[0]
    if not isinstance(identifier, Mapping) or identifier.get("identifier_type") != "toy_number":
        raise AuthorityContractError("applied catalog row lacks the typed toy identifier")
    value = identifier.get("identifier_value")
    if not isinstance(value, str) or not value:
        raise AuthorityContractError("applied catalog toy identifier is invalid")
    return value


def _build_evidence(entry: Any, row: Mapping[str, Any]) -> list[VariantFieldEvidence]:
    evidence: list[VariantFieldEvidence] = []
    for pending in entry.proposal.pending_field_evidence:
        catalog_value = _catalog_value(row, pending.field)
        expected_proposal_value = (
            [catalog_value] if pending.field == VariantField.identifiers else catalog_value
        )
        if expected_proposal_value != pending.proposed_value:
            raise AuthorityContractError("applied catalog value differs from the frozen proposal")
        evidence.append(
            VariantFieldEvidence(
                schema_version="pvr-canonical-authority-field-evidence-v1",
                field=pending.field,
                source_field=pending.source_field,
                catalog_value=catalog_value,
                reviewed_value=pending.source_value,
                evidence_refs=pending.evidence_refs,
                source_bindings=[pending.source_binding],
                agreement=EvidenceAgreement.agrees,
                notes="Frozen source-to-catalog comparison; owner review is still pending.",
            )
        )
    return evidence


def _entry_hash_body(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "entry_sha256": content_sha256(value)}


def _batch_hash_body(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "batch_sha256": content_sha256(value)}


def _load_inputs(root: Path) -> tuple[Any, str, Any, CatalogApplicationManifest, Any, list[Any]]:
    artifacts, packet_sha = _validate_car_t4_inputs(root)
    if packet_sha != EXPECTED_PACKET_SHA256:
        raise AuthorityContractError("CAR-T4 packet checksum is stale")
    proposal_sha = content_sha256(artifacts.proposal_bundle.model_dump(mode="json"))
    if proposal_sha != EXPECTED_PROPOSAL_BUNDLE_SHA256:
        raise AuthorityContractError("CAR-T4 proposal bundle checksum is stale")

    ledger_payload, ledger_raw = _strict_json(
        _safe_path(root, CAR_T4_LEDGER_REFERENCE, allow_missing_leaf=False)
    )
    ledger = _validate_ledger(artifacts, packet_sha, ledger_payload)
    if (
        ledger.ledger_sha256 != EXPECTED_LEDGER_SHA256
        or _sha256(ledger_raw) != _sha256(stable_json_bytes(ledger.model_dump(mode="json")))
        or len(ledger.events) != 20
        or ledger.decision_counts.approved != 20
        or any(event.decision != CatalogDecision.approve_catalog_record for event in ledger.events)
    ):
        raise AuthorityContractError("catalog decision ledger is not the frozen approved 20/20 set")

    application_payload, application_raw = _strict_json(
        _safe_path(root, APPLICATION_MANIFEST_REFERENCE, allow_missing_leaf=False)
    )
    if _sha256(application_raw) != EXPECTED_APPLICATION_MANIFEST_SHA256:
        raise AuthorityContractError("catalog application manifest checksum is stale")
    application = CatalogApplicationManifest.model_validate(application_payload)
    if (
        application.packet_sha256 != packet_sha
        or application.proposal_bundle_sha256 != proposal_sha
    ):
        raise AuthorityContractError("catalog application manifest differs from CAR-T4 parents")
    if application.decision_ledger_sha256 != ledger.ledger_sha256:
        raise AuthorityContractError("catalog application manifest differs from decision ledger")
    if (
        application.output_catalog_sha256 != EXPECTED_CATALOG_SHA256
        or application.catalog_product_count != 140
        or application.catalog_record_applied_count != 20
        or application.exact_authority_count != 0
        or application.rhb_t5_authorized is not False
    ):
        raise AuthorityContractError("catalog application manifest is outside CAR-T5P scope")

    event_payload, event_raw = _strict_json(
        _safe_path(root, APPLICATION_EVENT_REFERENCE, allow_missing_leaf=False)
    )
    event = CatalogApplicationAuthorizationEvent.model_validate(event_payload)
    if event_raw != stable_json_bytes(event.model_dump(mode="json")):
        raise AuthorityContractError("catalog application event encoding is stale")
    if event.event_sha256 != application.authorization_event_sha256:
        raise AuthorityContractError("catalog application event differs from its public manifest")

    catalog_payload, catalog_raw = _strict_json(
        _safe_path(root, CATALOG_REFERENCE, allow_missing_leaf=False)
    )
    if _sha256(catalog_raw) != EXPECTED_CATALOG_SHA256:
        raise AuthorityContractError("catalog-v2 checksum is stale")
    if catalog_payload.get("catalog_version") != "catalog-v2":
        raise AuthorityContractError("CAR-T5P requires catalog-v2")
    products = catalog_payload.get("products")
    if not isinstance(products, list) or len(products) != 140:
        raise AuthorityContractError("CAR-T5P requires exactly 140 catalog rows")
    appended = products[120:]
    if len(appended) != 20 or any(not isinstance(row, Mapping) for row in appended):
        raise AuthorityContractError("catalog-v2 lacks the exact 20 applied rows")
    return artifacts, packet_sha, ledger, application, event, appended


def build_authority_review_preparation(
    root: Path,
) -> tuple[AuthorityReviewPreparationPacket, str, AuthorityReviewPacketManifest]:
    """Build deterministic CAR-T5P outputs in memory without recording a human decision."""

    root = _root(root)
    _require_ignore_rule(root)
    artifacts, packet_sha, ledger, _application, application_event, appended = _load_inputs(root)
    application_raw = (root / APPLICATION_MANIFEST_REFERENCE).read_bytes()
    entries: list[AuthorityReviewPreparationEntry] = []
    seen_uuids: set[str] = set()
    seen_ids: set[str] = set()
    seen_releases: set[str] = set()
    for ordinal, (source_entry, decision, binding, row) in enumerate(
        zip(
            artifacts.review_packet.entries,
            ledger.events,
            application_event.ordered_record_bindings,
            appended,
            strict=True,
        ),
        start=1,
    ):
        if not isinstance(row, Mapping):
            raise AuthorityContractError("applied catalog row must be an object")
        proposal = source_entry.proposal
        candidate = source_entry.candidate
        uuid = str(row.get("canonical_uuid", ""))
        canonical_id = str(row.get("canonical_id", ""))
        release_key = str(row.get("release_key", ""))
        if (
            binding.ordinal != ordinal
            or binding.candidate_id != candidate.candidate_id
            or binding.proposal_id != proposal.proposal_id
            or binding.proposal_sha256 != source_entry.proposal_sha256
            or binding.product_record_sha256 != proposal.product_record_sha256
            or binding.decision_event_sha256 != decision.event_sha256
            or binding.canonical_uuid != uuid
            or binding.canonical_id != canonical_id
            or binding.release_key != release_key
            or binding.output_row_sha256 != content_sha256(row)
            or str(proposal.proposed_canonical_uuid) != binding.canonical_uuid
            or proposal.proposed_product_record.release_key != release_key
        ):
            raise AuthorityContractError(
                "historical proposal does not resolve one-to-one to catalog-v2"
            )
        if uuid in seen_uuids or canonical_id in seen_ids or release_key in seen_releases:
            raise AuthorityContractError("duplicate catalog UUID, canonical ID or release key")
        seen_uuids.add(uuid)
        seen_ids.add(canonical_id)
        seen_releases.add(release_key)
        catalog_record = proposal.proposed_product_record
        if catalog_record.color is not None or catalog_record.edition is not None:
            raise AuthorityContractError("color and edition must remain null")
        evidence = _build_evidence(source_entry, row)
        resolution = CatalogResolutionBinding(
            schema_version="pvr-canonical-authority-catalog-resolution-binding-v1",
            ordinal=ordinal,
            candidate_id=candidate.candidate_id,
            candidate_sha256=content_sha256(candidate.model_dump(mode="json")),
            proposal_id=proposal.proposal_id,
            proposal_sha256=source_entry.proposal_sha256,
            proposal_product_record_sha256=proposal.product_record_sha256,
            catalog_application_manifest_sha256=_sha256(application_raw),
            catalog_version="catalog-v2",
            catalog_sha256=EXPECTED_CATALOG_SHA256,
            family_group_key=candidate.family_group_key,
            release_key=release_key,
            applied_canonical_uuid=UUID(uuid),
            applied_canonical_id=canonical_id,
            applied_catalog_record_sha256=content_sha256(row),
        )
        derived = AuthorityCandidate(
            **{
                **candidate.model_dump(mode="json"),
                "catalog_lookup_state": "existing_uuid",
                "canonical_uuid": uuid,
                "status": "staged",
            }
        )
        body = {
            "ordinal": ordinal,
            "candidate": derived.model_dump(mode="json"),
            "resolution_binding": resolution.model_dump(mode="json"),
            "catalog_record": catalog_record.model_dump(mode="json"),
            "catalog_record_sha256": content_sha256(row),
            "field_evidence": [item.model_dump(mode="json") for item in evidence],
            "variant_note_context": source_entry.variant_note_context,
            "variant_note_role": "context_only_not_color_or_edition_evidence",
            "explicit_color": None,
            "explicit_edition": None,
            "missing_or_conflicting_items": [],
            "publication_limits": [
                "community_snapshot_exact_only",
                "catalog_inclusion_is_not_exact_authority",
                "rhb_t5_not_authorized",
            ],
            "owner_questions": [
                "Does this source-to-catalog reconciliation identify one exact release with all six evidence rows agreeing?"
            ],
        }
        entries.append(AuthorityReviewPreparationEntry.model_validate(_entry_hash_body(body)))

    grouped: dict[str, list[AuthorityReviewPreparationEntry]] = defaultdict(list)
    family_order: list[str] = []
    for entry in entries:
        family = entry.candidate.family_group_key
        if family not in grouped:
            family_order.append(family)
        grouped[family].append(entry)
    batches: list[AuthorityReviewFamilyBatch] = []
    for batch_ordinal, family in enumerate(family_order, start=1):
        selected = grouped[family]
        body = {
            "batch_ordinal": batch_ordinal,
            "family_group_key": family,
            "entry_ordinals": [entry.ordinal for entry in selected],
            "candidate_ids": [entry.candidate.candidate_id for entry in selected],
            "entry_sha256s": [entry.entry_sha256 for entry in selected],
        }
        batches.append(AuthorityReviewFamilyBatch.model_validate(_batch_hash_body(body)))

    packet = AuthorityReviewPreparationPacket(
        schema_version="pvr-canonical-authority-review-packet-v1",
        packet_version=PREPARATION_VERSION,
        packet_purpose="output_blind_exact_authority_preparation_only_no_owner_decision",
        publication_scope="local_only_git_ignored",
        car_t4_packet_sha256=packet_sha,
        proposal_bundle_sha256=EXPECTED_PROPOSAL_BUNDLE_SHA256,
        catalog_decision_ledger_sha256=ledger.ledger_sha256,
        catalog_application_manifest_sha256=_sha256(application_raw),
        catalog_version="catalog-v2",
        catalog_sha256=EXPECTED_CATALOG_SHA256,
        entries=entries,
        family_batches=batches,
        review_event_count=0,
        owner_attestation_count=0,
        approved_exact_count=0,
        authority_bundle_record_count=0,
        resolver_output_consulted=False,
        resolver_output_included=False,
        predicted_uuid_included=False,
        model_scores_included=False,
        network_requests=0,
        rhb_t5_authorized=False,
        status="awaiting_owner_review_gate",
    )
    owner_markdown = render_owner_review(packet)
    manifest = AuthorityReviewPacketManifest(
        schema_version="pvr-canonical-authority-review-packet-manifest-v1",
        manifest_version=PREPARATION_VERSION,
        publication_scope=(
            "safe_hash_count_and_attribution_only_no_product_rows_questions_or_owner_responses"
        ),
        status="awaiting_owner_review_gate",
        car_t4_packet_sha256=packet_sha,
        proposal_bundle_sha256=EXPECTED_PROPOSAL_BUNDLE_SHA256,
        catalog_decision_ledger_sha256=ledger.ledger_sha256,
        catalog_application_manifest_sha256=_sha256(application_raw),
        catalog_version="catalog-v2",
        catalog_sha256=EXPECTED_CATALOG_SHA256,
        private_packet_sha256=content_sha256(packet.model_dump(mode="json")),
        private_owner_review_sha256=_sha256(owner_markdown.encode("utf-8")),
        ordered_entry_sha256s=[entry.entry_sha256 for entry in entries],
        entry_count=20,
        family_count=7,
        family_batch_sizes=[len(batch.entry_ordinals) for batch in batches],
        evidence_row_count=120,
        evidence_rows_per_entry=6,
        null_color_count=20,
        null_edition_count=20,
        review_event_count=0,
        owner_attestation_count=0,
        approved_exact_count=0,
        authority_bundle_record_count=0,
        resolver_output_consulted=False,
        network_requests=0,
        rhb_t5_authorized=False,
        reviewed_by_role="project_owner",
        source_id="fandom-hot-wheels-2025-pilot-r790665-v1",
        license_name="CC-BY-SA",
        license_url="https://www.fandom.com/licensing",
        share_alike_required=True,
        attribution=(
            "Source: Hot Wheels Wiki contributors, List of 2025 Hot Wheels, revision 790665; "
            "normalized derivative."
        ),
        next_gate="owner_gate_t5_g1_explicit_staged_to_reviewed_outcomes_required",
    )
    _validate_public_privacy(stable_json_bytes(manifest.model_dump(mode="json")))
    return packet, owner_markdown, manifest


def render_owner_review(packet: AuthorityReviewPreparationPacket) -> str:
    lines = [
        "# CAR-T5P output-blind exact-authority review",
        "",
        "Status: awaiting Owner Gate T5-G1. This packet records no review outcome or exact authority.",
        "Resolver output, predicted UUIDs, model scores and benchmark labels were not consulted.",
        "",
    ]
    by_ordinal = {entry.ordinal: entry for entry in packet.entries}
    for batch in packet.family_batches:
        lines.extend(
            [
                f"## Family batch {batch.batch_ordinal}: {batch.family_group_key}",
                "",
                f"Batch SHA-256: `{batch.batch_sha256}`",
                "",
            ]
        )
        for ordinal in batch.entry_ordinals:
            entry = by_ordinal[ordinal]
            record = entry.catalog_record
            lines.extend(
                [
                    f"### {ordinal}. {record.casting} — {entry.candidate.proposed_release_key}",
                    "",
                    f"- Candidate: `{entry.candidate.candidate_id}`",
                    f"- Catalog UUID: `{record.canonical_uuid}`",
                    f"- Catalog record SHA-256: `{entry.catalog_record_sha256}`",
                    f"- Color: `{record.color}` (must remain null)",
                    f"- Edition: `{record.edition}` (must remain null)",
                    f"- Variant note: `{entry.variant_note_context}` (context only)",
                    "- Evidence: casting, release year, series, collector number, series position and toy identifier all agree.",
                    f"- T5-G1 question: {entry.owner_questions[0]}",
                    "",
                ]
            )
    lines.extend(
        [
            "Catalog inclusion is not exact authority. A fresh explicit response is required for T5-G1.",
            "T5-G2 exact-authority approval and RHB-T5 remain separate and unauthorized.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_public_privacy(raw: bytes) -> None:
    text = raw.decode("utf-8")
    forbidden = (
        "candidate_id",
        "canonical_uuid",
        "canonical_id",
        "release_key",
        "casting",
        "owner_questions",
        '"owner_response_verbatim"',
        '"authorized_exact_owner_response"',
    )
    if any(token in text for token in forbidden):
        raise AuthorityContractError("public preparation manifest contains private row metadata")
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        raise AuthorityContractError("public preparation manifest contains email-like PII")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_temp(path: Path, payload: bytes, mode: int) -> Path:
    temp = path.with_name(f".{path.name}.car-t5p.tmp")
    if temp.exists() or temp.is_symlink():
        raise AuthorityContractError("stale CAR-T5P temporary file exists")
    try:
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temp.read_bytes() != payload:
            raise AuthorityContractError("CAR-T5P temporary artifact failed validation")
    except BaseException:
        if temp.exists() and not temp.is_symlink():
            temp.unlink()
        raise
    return temp


def _expected_output_bytes(
    packet: AuthorityReviewPreparationPacket,
    owner_markdown: str,
    manifest: AuthorityReviewPacketManifest,
) -> dict[Path, bytes]:
    return {
        PRIVATE_PACKET_REFERENCE: stable_json_bytes(packet.model_dump(mode="json")),
        OWNER_REVIEW_REFERENCE: owner_markdown.encode("utf-8"),
        PUBLIC_MANIFEST_REFERENCE: stable_json_bytes(manifest.model_dump(mode="json")),
    }


def prepare_authority_review(root: Path, *, check: bool = False) -> Literal["created", "unchanged"]:
    root = _root(root)
    packet, owner_markdown, manifest = build_authority_review_preparation(root)
    expected = _expected_output_bytes(packet, owner_markdown, manifest)
    targets = {
        reference: _safe_path(root, reference, allow_missing_leaf=True) for reference in expected
    }
    states = {reference: path.exists() or path.is_symlink() for reference, path in targets.items()}
    if any(states.values()):
        if not all(states.values()):
            raise AuthorityContractError("partial CAR-T5P output state")
        private_dir = root / PRIVATE_DIRECTORY
        if stat.S_IMODE(private_dir.stat().st_mode) != 0o700:
            raise AuthorityContractError("CAR-T5P private workspace permissions are unsafe")
        for reference, path in targets.items():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != expected[reference]:
                raise AuthorityContractError(
                    "existing CAR-T5P output differs from deterministic replay"
                )
            if reference.parent == PRIVATE_DIRECTORY and stat.S_IMODE(path.stat().st_mode) != 0o600:
                raise AuthorityContractError("CAR-T5P private artifact permissions are unsafe")
        return "unchanged"
    if check:
        raise AuthorityContractError("CAR-T5P outputs are not materialized")

    private_dir = _safe_path(root, PRIVATE_DIRECTORY, allow_missing_leaf=True)
    created_private = False
    if private_dir.exists() or private_dir.is_symlink():
        if private_dir.is_symlink() or not private_dir.is_dir():
            raise AuthorityContractError("CAR-T5P private workspace is unsafe")
    else:
        private_dir.mkdir(mode=0o700)
        created_private = True
        _fsync_directory(private_dir.parent)
    os.chmod(private_dir, 0o700)

    temps: list[Path] = []
    installed: list[Path] = []
    try:
        for reference, payload in expected.items():
            path = targets[reference]
            mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
            temps.append(_write_temp(path, payload, mode))
        for (reference, path), temp in zip(targets.items(), temps, strict=True):
            os.replace(temp, path)
            installed.append(path)
            if reference.parent == PRIVATE_DIRECTORY:
                os.chmod(path, 0o600)
            _fsync_directory(path.parent)
    except BaseException:
        for temp in temps:
            if temp.exists() and not temp.is_symlink():
                temp.unlink()
        for path in installed:
            if path.exists() and not path.is_symlink():
                path.unlink()
                _fsync_directory(path.parent)
        if created_private and private_dir.exists() and not any(private_dir.iterdir()):
            private_dir.rmdir()
            _fsync_directory(private_dir.parent)
        raise
    return "created"


__all__ = [
    "AuthorityReviewFamilyBatch",
    "AuthorityReviewPacketManifest",
    "AuthorityReviewPreparationEntry",
    "AuthorityReviewPreparationPacket",
    "build_authority_review_preparation",
    "prepare_authority_review",
    "render_owner_review",
]
