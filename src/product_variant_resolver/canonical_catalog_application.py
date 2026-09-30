"""Deterministic CAR-T4A catalog-v2 batch application.

The application Gate is deliberately separate from catalog-proposal review and exact-authority
review.  It appends the twenty approved namespace records, preserves the frozen 120-row parent
byte-semantically, and publishes only safe aggregate/hash metadata.  The exact owner authorization
event remains in the existing Git-ignored local review directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_packet import (
    CATALOG_REFERENCE,
    EXPECTED_RAW_CATALOG_SHA256,
    AppliedCatalogParentLineage,
    CatalogProposalPacketEntry,
    WorkspaceArtifacts,
    build_catalog_projection,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)
from product_variant_resolver.canonical_catalog_decisions import (
    CATALOG_APPLICATION_EVENT_NAME,
    LEDGER_REFERENCE,
    CatalogDecision,
    CatalogDecisionLedger,
    _validate_car_t4_inputs,
    _validate_ledger,
    check_catalog_decisions,
)
from product_variant_resolver.identity import natural_key, slugify

APPLICATION_VERSION = "canonical-catalog-application-car-t4a-v1"
APPLICATION_DECISION = "apply_all_approved_catalog_proposals"
APPLICATION_REASON = (
    "Project owner explicitly authorized the complete 20-record catalog namespace batch; "
    "color=null and edition=null remain required, and exact authority remains unapproved."
)
PUBLIC_MANIFEST_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/catalog-application-manifest.json"
)
LOCAL_DIRECTORY = LEDGER_REFERENCE.parent
PRIVATE_EVENT_REFERENCE = LOCAL_DIRECTORY / CATALOG_APPLICATION_EVENT_NAME
TRANSACTION_JOURNAL_REFERENCE = LOCAL_DIRECTORY / "catalog-application-transaction.json"
TRANSACTION_DIRECTORY_REFERENCE = LOCAL_DIRECTORY / ".catalog-application-transaction-v1"
DATA_MANIFEST_REFERENCE = Path("data/manifest.json")
EXPECTED_PARENT_DATA_MANIFEST_SHA256 = (
    "d9480603280fb7db49d1ecb6046d7c3e61946658c1cdfe40a72ed50f63518360"
)
PARENT_PRODUCT_COUNT = 120
APPENDED_PRODUCT_COUNT = 20
TOTAL_PRODUCT_COUNT = 140
PARENT_SOURCE_NOTE = (
    "Deterministic synthetic records for architecture and test validation only; not an "
    "authoritative Hot Wheels catalog."
)
CHILD_SOURCE_NOTE = (
    "Catalog contains 120 synthetic regression rows plus 20 owner-approved community-snapshot "
    "catalog rows; catalog inclusion is not exact authority."
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class ApplicationContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class AppliedRecordBinding(ApplicationContract):
    ordinal: int = Field(ge=1, le=20)
    candidate_id: NonBlank
    proposal_id: NonBlank
    canonical_uuid: NonBlank
    canonical_id: NonBlank
    release_key: NonBlank
    toy_identifier: NonBlank
    proposal_sha256: Sha256
    product_record_sha256: Sha256
    decision_event_sha256: Sha256
    output_row_sha256: Sha256


class CatalogApplicationAuthorizationEvent(ApplicationContract):
    schema_version: Literal["pvr-canonical-catalog-application-authorization-event-v1"]
    application_version: Literal["canonical-catalog-application-car-t4a-v1"]
    status: Literal["authorized_catalog_application_only"]
    authorization_contract_version: Literal["exact-external-catalog-application-v1"]
    decision: Literal["apply_all_approved_catalog_proposals"]
    owner_response_verbatim: NonBlank
    authorized_exact_owner_response: NonBlank
    reviewed_by_role: Literal["project_owner"]
    confirmation_method: Literal["owner_attestation"]
    authorized_at: AwareDatetime
    review_reason: Literal[
        "Project owner explicitly authorized the complete 20-record catalog namespace batch; "
        "color=null and edition=null remain required, and exact authority remains unapproved."
    ]
    packet_sha256: Sha256
    proposal_bundle_sha256: Sha256
    decision_ledger_sha256: Sha256
    cumulative_decision_events_sha256: Sha256
    decision_event_head_sha256: Sha256
    parent_catalog_version: Literal["fixture-v1"]
    parent_raw_catalog_sha256: Literal[
        "0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261"
    ]
    parent_data_manifest_sha256: Literal[
        "d9480603280fb7db49d1ecb6046d7c3e61946658c1cdfe40a72ed50f63518360"
    ]
    approved_proposal_count: Literal[20]
    planned_child_catalog_sha256: Sha256
    output_data_manifest_sha256: Sha256
    ordered_record_bindings: list[AppliedRecordBinding] = Field(min_length=20, max_length=20)
    constraints: tuple[
        Literal["catalog_application_only"],
        Literal["exact_authority_not_approved"],
        Literal["rhb_t5_not_authorized"],
        Literal["color_must_remain_null"],
        Literal["edition_must_remain_null"],
    ]
    authorization_contract_sha256: Sha256
    catalog_applied_count: Literal[20]
    exact_authority_count: Literal[0]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    event_sha256: Sha256

    @model_validator(mode="after")
    def exact_authorization_and_hash(self) -> CatalogApplicationAuthorizationEvent:
        response = _normalize(self.owner_response_verbatim)
        authorized = _normalize(self.authorized_exact_owner_response)
        if (
            response != self.owner_response_verbatim
            or authorized != self.authorized_exact_owner_response
        ):
            raise ValueError("application authorization text must already be normalized")
        if response != authorized:
            raise ValueError("application response differs from exact external authorization")
        if self.authorized_at.utcoffset() != UTC.utcoffset(self.authorized_at):
            raise ValueError("application authorization timestamp must be UTC")
        if self.authorized_at.microsecond:
            raise ValueError("application authorization timestamp must use whole-second precision")
        if [item.ordinal for item in self.ordered_record_bindings] != list(range(1, 21)):
            raise ValueError("application record bindings must be contiguous in packet order")
        authorization_body = {
            "authorization_contract_version": self.authorization_contract_version,
            "decision": self.decision,
            "authorized_exact_owner_response": self.authorized_exact_owner_response,
            "reviewed_by_role": self.reviewed_by_role,
            "confirmation_method": self.confirmation_method,
            "review_reason": self.review_reason,
            "packet_sha256": self.packet_sha256,
            "proposal_bundle_sha256": self.proposal_bundle_sha256,
            "decision_ledger_sha256": self.decision_ledger_sha256,
            "cumulative_decision_events_sha256": self.cumulative_decision_events_sha256,
            "decision_event_head_sha256": self.decision_event_head_sha256,
            "parent_raw_catalog_sha256": self.parent_raw_catalog_sha256,
            "approved_proposal_count": self.approved_proposal_count,
            "planned_child_catalog_sha256": self.planned_child_catalog_sha256,
            "ordered_record_bindings": [
                item.model_dump(mode="json") for item in self.ordered_record_bindings
            ],
            "constraints": list(self.constraints),
        }
        if self.authorization_contract_sha256 != content_sha256(authorization_body):
            raise ValueError("application authorization contract checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"event_sha256"}))
        if self.event_sha256 != expected:
            raise ValueError("application authorization event checksum is stale")
        return self


class CatalogApplicationManifest(ApplicationContract):
    schema_version: Literal["pvr-canonical-catalog-application-manifest-v1"]
    application_version: Literal["canonical-catalog-application-car-t4a-v1"]
    publication_scope: Literal[
        "safe_hash_count_and_lineage_metadata_only_no_owner_response_or_product_rows"
    ]
    status: Literal["catalog_namespace_batch_applied_exact_authority_pending"]
    authorization_event_sha256: Sha256
    authorization_contract_sha256: Sha256
    packet_sha256: Sha256
    proposal_bundle_sha256: Sha256
    decision_ledger_sha256: Sha256
    parent_catalog_version: Literal["fixture-v1"]
    child_catalog_version: Literal["catalog-v2"]
    parent_raw_catalog_sha256: Literal[
        "0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261"
    ]
    parent_data_manifest_sha256: Literal[
        "d9480603280fb7db49d1ecb6046d7c3e61946658c1cdfe40a72ed50f63518360"
    ]
    parent_product_count: Literal[120]
    parent_ordered_product_sha256: Sha256
    appended_product_count: Literal[20]
    total_product_count: Literal[140]
    output_catalog_sha256: Sha256
    output_data_manifest_sha256: Sha256
    preserved_parent_order: Literal[True]
    appended_in_packet_order: Literal[True]
    null_color_count: Literal[20]
    null_edition_count: Literal[20]
    ordered_applied_record_sha256: Sha256
    catalog_record_applied_count: Literal[20]
    catalog_product_count: Literal[140]
    synthetic_product_count: Literal[120]
    nonsynthetic_product_count: Literal[20]
    exact_authority_count: Literal[0]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    encoding_policy: Literal["utf8_sorted_keys_two_space_indent_one_trailing_newline"]
    source_id: Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]
    license_name: Literal["CC-BY-SA"]
    license_url: Literal["https://www.fandom.com/licensing"]
    share_alike_required: Literal[True]
    attribution: Literal[
        "Source: Hot Wheels Wiki contributors, List of 2025 Hot Wheels, revision 790665; normalized derivative."
    ]
    next_gate: Literal["separate_exact_authority_review_gate"]


class TransactionEntry(ApplicationContract):
    target: NonBlank
    staged: NonBlank
    backup: str | None
    previous_sha256: Sha256 | None
    next_sha256: Sha256


class TransactionJournal(ApplicationContract):
    schema_version: Literal["pvr-canonical-catalog-application-transaction-v1"]
    application_version: Literal["canonical-catalog-application-car-t4a-v1"]
    status: Literal["prepared"]
    entries: list[TransactionEntry] = Field(min_length=4, max_length=4)


@dataclass(frozen=True)
class ApplicationOutputs:
    catalog: bytes
    data_manifest: bytes
    private_event: bytes
    public_manifest: bytes


APPLICATION_TARGET_REFERENCES = (
    Path(CATALOG_REFERENCE),
    DATA_MANIFEST_REFERENCE,
    PRIVATE_EVENT_REFERENCE,
    PUBLIC_MANIFEST_REFERENCE,
)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _lexical_root(root: Path) -> Path:
    lexical = Path(os.path.abspath(os.fspath(root)))
    try:
        metadata = lexical.lstat()
    except OSError as error:
        raise AuthorityContractError("repository root is unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise AuthorityContractError("repository root must be a real directory")
    return lexical


def _safe_path(root: Path, reference: Path, *, allow_missing: bool) -> Path:
    if reference.is_absolute() or any(part in {"", ".", ".."} for part in reference.parts):
        raise AuthorityContractError("application artifact reference is unsafe")
    target = root / reference
    current = root
    for index, part in enumerate(reference.parts):
        current = current / part
        leaf = index == len(reference.parts) - 1
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if leaf and allow_missing:
                continue
            raise AuthorityContractError("application artifact has a missing ancestor") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise AuthorityContractError("application artifact path contains a symlink")
        if leaf and not stat.S_ISREG(metadata.st_mode):
            raise AuthorityContractError("application artifact target is not a regular file")
    try:
        target.parent.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise AuthorityContractError("application artifact escapes repository root") from error
    return target


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise AuthorityContractError(
            f"required application input is not a regular file: {path.name}"
        )
    raw = path.read_bytes()
    try:
        payload = json.loads(raw, object_pairs_hook=_duplicate_rejecting_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AuthorityContractError(f"invalid application JSON artifact: {path.name}") from error
    if not isinstance(payload, dict):
        raise AuthorityContractError(f"application JSON root must be an object: {path.name}")
    return cast(dict[str, Any], payload), raw


def _canonical_id(casting: str, release_year: int, toy_identifier: str) -> str:
    value = slugify(f"Hot Wheels {casting} {release_year} {toy_identifier}")
    if not value:
        raise AuthorityContractError("proposal identity cannot create a canonical ID")
    return value


def _typed_identifier_keys(product: Mapping[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    identifiers = product.get("identifiers", [])
    if not isinstance(identifiers, list):
        raise AuthorityContractError("catalog product identifiers must be a list")
    for item in identifiers:
        if not isinstance(item, Mapping):
            continue
        kind = str(item.get("identifier_type", "")).strip().casefold()
        value = str(item.get("identifier_value", "")).strip().casefold()
        if kind and value:
            key = (kind, value)
            if key in keys:
                raise AuthorityContractError("catalog product repeats a typed identifier")
            keys.add(key)
    return keys


def _provenance(entry: CatalogProposalPacketEntry) -> list[dict[str, Any]]:
    binding = entry.candidate.source_binding
    license_note = (
        f"{binding.license_name}; {binding.license_url}; {binding.attribution}; "
        "share-alike required"
    )
    rows: list[dict[str, Any]] = []
    for evidence in entry.proposal.pending_field_evidence:
        rows.append(
            {
                "confidence_note": (
                    "Owner-approved catalog namespace mapping only; not exact authority; "
                    f"normalized snapshot sha256={binding.normalized_snapshot_sha256}."
                ),
                "field_name": evidence.field.value,
                "license_note": license_note,
                "retrieved_at": binding.source_revision_timestamp,
                "source_name": binding.source_id,
                "source_reference": f"{binding.source_page_url}#{binding.source_record_id}",
                "value_snapshot": json.dumps(
                    evidence.proposed_value,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )
    return rows


def _catalog_row(entry: CatalogProposalPacketEntry) -> dict[str, Any]:
    proposal = entry.proposal
    product = proposal.proposed_product_record
    if product.color is not None or product.edition is not None:
        raise AuthorityContractError("catalog application cannot infer color or edition")
    if len(product.identifiers) != 1:
        raise AuthorityContractError("catalog application requires one exact toy identifier")
    if (
        product.family_group_key != entry.candidate.family_group_key
        or product.release_key != entry.candidate.proposed_release_key
    ):
        raise AuthorityContractError("proposal family or release key differs from frozen candidate")
    toy_identifier = product.identifiers[0]
    identifier_evidence = entry.proposal.pending_field_evidence[-1]
    if identifier_evidence.field.value != "identifiers":
        raise AuthorityContractError("proposal identifier evidence is out of order")
    evidence_reference = identifier_evidence.evidence_refs[0]
    return {
        "aliases": [],
        "brand": "Hot Wheels",
        "canonical_id": _canonical_id(product.casting, product.release_year, toy_identifier),
        "canonical_uuid": str(product.canonical_uuid),
        "casting": product.casting,
        "collector_number": product.collector_number,
        "color": None,
        "edition": None,
        "identifiers": [
            {
                "identifier_type": "toy_number",
                "identifier_value": toy_identifier,
                "source_id": evidence_reference,
            }
        ],
        "near_duplicate_group": product.family_group_key,
        "provenance": _provenance(entry),
        "rarity_tier": None,
        "release_key": product.release_key,
        "release_year": product.release_year,
        "series": product.series,
        "series_position": product.series_position,
    }


def _parent_catalog_payload(catalog_payload: Mapping[str, Any]) -> dict[str, Any]:
    products = catalog_payload.get("products")
    if not isinstance(products, list):
        raise AuthorityContractError("catalog products are unavailable")
    if catalog_payload.get("catalog_version") == "fixture-v1":
        parent = dict(catalog_payload)
    elif catalog_payload.get("catalog_version") == "catalog-v2":
        if catalog_payload.get("source_note") != CHILD_SOURCE_NOTE:
            raise AuthorityContractError(
                "catalog-v2 source note differs from mixed-source contract"
            )
        lineage = AppliedCatalogParentLineage.model_validate(catalog_payload.get("catalog_lineage"))
        if len(products) != lineage.parent_product_count + lineage.appended_product_count:
            raise AuthorityContractError("applied catalog count differs from lineage")
        parent = {
            "catalog_version": lineage.parent_catalog_version,
            "dataset_version": lineage.parent_dataset_version,
            "products": products[: lineage.parent_product_count],
            "source_note": PARENT_SOURCE_NOTE,
        }
    else:
        raise AuthorityContractError("catalog version is unsupported by the application Gate")
    parent_raw = stable_json_bytes(parent)
    if _sha256(parent_raw) != EXPECTED_RAW_CATALOG_SHA256:
        raise AuthorityContractError("catalog parent bytes differ from frozen CAR-T4 input")
    if len(cast(list[Any], parent["products"])) != PARENT_PRODUCT_COUNT:
        raise AuthorityContractError("catalog parent count differs from 120")
    return parent


def _parent_product_digest(products: Sequence[Any]) -> str:
    return content_sha256([content_sha256(item) for item in products])


def _validate_complete_ledger(
    root: Path,
) -> tuple[WorkspaceArtifacts, str, CatalogDecisionLedger]:
    artifacts, packet_sha = _validate_car_t4_inputs(root)
    anchored_ledger = check_catalog_decisions(root)
    ledger_payload, _ = _read_json(_safe_path(root, LEDGER_REFERENCE, allow_missing=False))
    ledger = _validate_ledger(artifacts, packet_sha, ledger_payload)
    if ledger != anchored_ledger:
        raise AuthorityContractError("decision ledger differs from its immutable Git anchor")
    if (
        ledger.status != "complete_awaiting_batch_application_gate"
        or len(ledger.events) != APPENDED_PRODUCT_COUNT
        or ledger.next_pending_ordinal is not None
        or ledger.decision_counts.approved != APPENDED_PRODUCT_COUNT
        or ledger.decision_counts.pending != 0
        or ledger.decision_counts.held != 0
        or ledger.decision_counts.rejected != 0
    ):
        raise AuthorityContractError("catalog application requires twenty approved decisions")
    for entry, event in zip(artifacts.review_packet.entries, ledger.events, strict=True):
        if (
            event.decision != CatalogDecision.approve_catalog_record
            or event.candidate_id != entry.candidate.candidate_id
            or event.proposal_id != entry.proposal.proposal_id
            or event.proposal_sha256 != entry.proposal_sha256
            or event.product_record_sha256 != entry.proposal.product_record_sha256
            or event.catalog_applied is not False
            or event.authority_approved is not False
            or event.rhb_t5_authorized is not False
        ):
            raise AuthorityContractError("approved decision differs from the frozen proposal order")
    return artifacts, packet_sha, ledger


def _validate_collisions(parent_products: list[Any], appended: list[dict[str, Any]]) -> None:
    parent_natural_keys = {
        natural_key(cast(Mapping[str, Any], item))
        for item in parent_products
        if isinstance(item, Mapping)
    }
    for product in appended:
        if natural_key(product) in parent_natural_keys:
            raise AuthorityContractError("proposal collides with a legacy parent natural key")
    all_products = [*parent_products, *appended]
    uuids: set[str] = set()
    canonical_ids: set[str] = set()
    release_keys: set[str] = set()
    identifier_keys: set[tuple[str, str]] = set()
    for product in all_products:
        if not isinstance(product, Mapping):
            raise AuthorityContractError("catalog product must be an object")
        uuid = str(product.get("canonical_uuid", ""))
        canonical_id = str(product.get("canonical_id", ""))
        if not uuid or uuid in uuids or not canonical_id or canonical_id in canonical_ids:
            raise AuthorityContractError("catalog UUID or canonical_id collision")
        uuids.add(uuid)
        canonical_ids.add(canonical_id)
        release_key = product.get("release_key")
        if release_key is not None:
            normalized_release = str(release_key).strip().casefold()
            if not normalized_release or normalized_release in release_keys:
                raise AuthorityContractError("catalog release_key collision")
            release_keys.add(normalized_release)
        for key in _typed_identifier_keys(product):
            if key in identifier_keys:
                raise AuthorityContractError("catalog typed identifier collision")
            identifier_keys.add(key)


def _build_catalog(
    parent: Mapping[str, Any], artifacts: WorkspaceArtifacts
) -> tuple[dict[str, Any], str]:
    parent_products = cast(list[Any], parent["products"])
    appended = [_catalog_row(entry) for entry in artifacts.review_packet.entries]
    _validate_collisions(parent_products, appended)
    ordered_parent_sha = _parent_product_digest(parent_products)
    lineage = AppliedCatalogParentLineage.model_validate(
        {
            "schema_version": "pvr-catalog-lineage-v1",
            "parent_catalog_version": "fixture-v1",
            "parent_dataset_version": "fixture-v1",
            "parent_raw_catalog_sha256": EXPECTED_RAW_CATALOG_SHA256,
            "parent_product_count": PARENT_PRODUCT_COUNT,
            "parent_ordered_product_sha256": ordered_parent_sha,
            "application_version": APPLICATION_VERSION,
            "appended_product_count": APPENDED_PRODUCT_COUNT,
        }
    )
    result: dict[str, Any] = {
        "catalog_lineage": lineage.model_dump(mode="json"),
        "catalog_version": "catalog-v2",
        "dataset_version": "fixture-v1",
        "products": [*parent_products, *appended],
        "source_note": CHILD_SOURCE_NOTE,
    }
    if result["products"][:PARENT_PRODUCT_COUNT] != parent_products:
        raise AuthorityContractError("catalog application changed parent order or content")
    return result, ordered_parent_sha


def _base_data_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    base = dict(payload)
    for key in (
        "catalog_application_version",
        "catalog_version",
        "parent_catalog_sha256",
        "parent_catalog_version",
        "parent_product_count",
    ):
        base.pop(key, None)
    base["catalog_sha256"] = EXPECTED_RAW_CATALOG_SHA256
    base["product_count"] = PARENT_PRODUCT_COUNT
    if _sha256(stable_json_bytes(base)) != EXPECTED_PARENT_DATA_MANIFEST_SHA256:
        raise AuthorityContractError("data manifest differs from frozen application parent")
    return base


def _build_data_manifest(parent: Mapping[str, Any], catalog_sha256: str) -> dict[str, Any]:
    result = dict(parent)
    result.update(
        {
            "catalog_application_version": APPLICATION_VERSION,
            "catalog_sha256": catalog_sha256,
            "catalog_version": "catalog-v2",
            "parent_catalog_sha256": EXPECTED_RAW_CATALOG_SHA256,
            "parent_catalog_version": "fixture-v1",
            "parent_product_count": PARENT_PRODUCT_COUNT,
            "product_count": TOTAL_PRODUCT_COUNT,
        }
    )
    return result


def _build_event(
    *,
    owner_response: str,
    authorized_exact_owner_response: str,
    authorized_at: datetime,
    packet_sha256: str,
    proposal_bundle_sha256: str,
    ledger_sha256: str,
    cumulative_decision_events_sha256: str,
    decision_event_head_sha256: str,
    ordered_record_bindings: Sequence[AppliedRecordBinding],
    output_catalog_sha256: str,
    output_data_manifest_sha256: str,
) -> CatalogApplicationAuthorizationEvent:
    response = _normalize(owner_response)
    authorized = _normalize(authorized_exact_owner_response)
    if not response or response != authorized:
        raise AuthorityContractError("application requires the exact external owner authorization")
    if authorized_at.tzinfo is None or authorized_at.utcoffset() is None:
        raise AuthorityContractError("application authorization timestamp must be aware UTC")
    timestamp = authorized_at.astimezone(UTC).replace(microsecond=0)
    body = {
        "schema_version": "pvr-canonical-catalog-application-authorization-event-v1",
        "application_version": APPLICATION_VERSION,
        "status": "authorized_catalog_application_only",
        "authorization_contract_version": "exact-external-catalog-application-v1",
        "decision": APPLICATION_DECISION,
        "owner_response_verbatim": response,
        "authorized_exact_owner_response": authorized,
        "reviewed_by_role": "project_owner",
        "confirmation_method": "owner_attestation",
        "authorized_at": timestamp.isoformat().replace("+00:00", "Z"),
        "review_reason": APPLICATION_REASON,
        "packet_sha256": packet_sha256,
        "proposal_bundle_sha256": proposal_bundle_sha256,
        "decision_ledger_sha256": ledger_sha256,
        "cumulative_decision_events_sha256": cumulative_decision_events_sha256,
        "decision_event_head_sha256": decision_event_head_sha256,
        "parent_catalog_version": "fixture-v1",
        "parent_raw_catalog_sha256": EXPECTED_RAW_CATALOG_SHA256,
        "parent_data_manifest_sha256": EXPECTED_PARENT_DATA_MANIFEST_SHA256,
        "approved_proposal_count": APPENDED_PRODUCT_COUNT,
        "planned_child_catalog_sha256": output_catalog_sha256,
        "output_data_manifest_sha256": output_data_manifest_sha256,
        "ordered_record_bindings": [
            item.model_dump(mode="json") for item in ordered_record_bindings
        ],
        "constraints": [
            "catalog_application_only",
            "exact_authority_not_approved",
            "rhb_t5_not_authorized",
            "color_must_remain_null",
            "edition_must_remain_null",
        ],
        "catalog_applied_count": APPENDED_PRODUCT_COUNT,
        "exact_authority_count": 0,
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    authorization_body = {
        key: body[key]
        for key in (
            "authorization_contract_version",
            "decision",
            "authorized_exact_owner_response",
            "reviewed_by_role",
            "confirmation_method",
            "review_reason",
            "packet_sha256",
            "proposal_bundle_sha256",
            "decision_ledger_sha256",
            "cumulative_decision_events_sha256",
            "decision_event_head_sha256",
            "parent_raw_catalog_sha256",
            "approved_proposal_count",
            "planned_child_catalog_sha256",
            "ordered_record_bindings",
            "constraints",
        )
    }
    body["authorization_contract_sha256"] = content_sha256(authorization_body)
    return CatalogApplicationAuthorizationEvent.model_validate(
        {**body, "event_sha256": content_sha256(body)}
    )


def _build_public_manifest(
    event: CatalogApplicationAuthorizationEvent,
    *,
    parent_ordered_product_sha256: str,
) -> CatalogApplicationManifest:
    return CatalogApplicationManifest.model_validate(
        {
            "schema_version": "pvr-canonical-catalog-application-manifest-v1",
            "application_version": APPLICATION_VERSION,
            "publication_scope": (
                "safe_hash_count_and_lineage_metadata_only_no_owner_response_or_product_rows"
            ),
            "status": "catalog_namespace_batch_applied_exact_authority_pending",
            "authorization_event_sha256": event.event_sha256,
            "authorization_contract_sha256": event.authorization_contract_sha256,
            "packet_sha256": event.packet_sha256,
            "proposal_bundle_sha256": event.proposal_bundle_sha256,
            "decision_ledger_sha256": event.decision_ledger_sha256,
            "parent_catalog_version": "fixture-v1",
            "child_catalog_version": "catalog-v2",
            "parent_raw_catalog_sha256": EXPECTED_RAW_CATALOG_SHA256,
            "parent_data_manifest_sha256": EXPECTED_PARENT_DATA_MANIFEST_SHA256,
            "parent_product_count": PARENT_PRODUCT_COUNT,
            "parent_ordered_product_sha256": parent_ordered_product_sha256,
            "appended_product_count": APPENDED_PRODUCT_COUNT,
            "total_product_count": TOTAL_PRODUCT_COUNT,
            "output_catalog_sha256": event.planned_child_catalog_sha256,
            "output_data_manifest_sha256": event.output_data_manifest_sha256,
            "preserved_parent_order": True,
            "appended_in_packet_order": True,
            "null_color_count": APPENDED_PRODUCT_COUNT,
            "null_edition_count": APPENDED_PRODUCT_COUNT,
            "ordered_applied_record_sha256": content_sha256(
                [item.output_row_sha256 for item in event.ordered_record_bindings]
            ),
            "catalog_record_applied_count": APPENDED_PRODUCT_COUNT,
            "catalog_product_count": TOTAL_PRODUCT_COUNT,
            "synthetic_product_count": PARENT_PRODUCT_COUNT,
            "nonsynthetic_product_count": APPENDED_PRODUCT_COUNT,
            "exact_authority_count": 0,
            "resolver_output_consulted": False,
            "network_requests": 0,
            "rhb_t5_authorized": False,
            "encoding_policy": "utf8_sorted_keys_two_space_indent_one_trailing_newline",
            "source_id": "fandom-hot-wheels-2025-pilot-r790665-v1",
            "license_name": "CC-BY-SA",
            "license_url": "https://www.fandom.com/licensing",
            "share_alike_required": True,
            "attribution": (
                "Source: Hot Wheels Wiki contributors, List of 2025 Hot Wheels, revision 790665; "
                "normalized derivative."
            ),
            "next_gate": "separate_exact_authority_review_gate",
        }
    )


def _record_bindings(
    artifacts: WorkspaceArtifacts,
    ledger: CatalogDecisionLedger,
    output_catalog: Mapping[str, Any],
) -> list[AppliedRecordBinding]:
    products = cast(list[dict[str, Any]], output_catalog["products"])
    appended = products[PARENT_PRODUCT_COUNT:]
    if len(appended) != APPENDED_PRODUCT_COUNT:
        raise AuthorityContractError("catalog application output lacks twenty appended rows")
    bindings: list[AppliedRecordBinding] = []
    for ordinal, (entry, decision, row) in enumerate(
        zip(artifacts.review_packet.entries, ledger.events, appended, strict=True), start=1
    ):
        product = entry.proposal.proposed_product_record
        identifier = cast(list[dict[str, str]], row["identifiers"])[0]["identifier_value"]
        binding = AppliedRecordBinding(
            ordinal=ordinal,
            candidate_id=entry.candidate.candidate_id,
            proposal_id=entry.proposal.proposal_id,
            canonical_uuid=str(product.canonical_uuid),
            canonical_id=str(row["canonical_id"]),
            release_key=product.release_key,
            toy_identifier=identifier,
            proposal_sha256=entry.proposal_sha256,
            product_record_sha256=entry.proposal.product_record_sha256,
            decision_event_sha256=decision.event_sha256,
            output_row_sha256=content_sha256(row),
        )
        if (
            row["canonical_uuid"] != binding.canonical_uuid
            or row["release_key"] != binding.release_key
            or identifier != product.identifiers[0]
        ):
            raise AuthorityContractError("output row differs from proposal binding")
        bindings.append(binding)
    return bindings


def _expected_outputs(
    root: Path,
    *,
    owner_response: str,
    authorized_exact_owner_response: str,
    authorized_at: datetime,
) -> tuple[ApplicationOutputs, CatalogApplicationManifest]:
    artifacts, packet_sha, ledger = _validate_complete_ledger(root)
    catalog_payload, _ = _read_json(_safe_path(root, Path(CATALOG_REFERENCE), allow_missing=False))
    parent_catalog = _parent_catalog_payload(catalog_payload)
    _, parent_catalog_model = build_catalog_projection(root)
    if len(parent_catalog_model.products) != PARENT_PRODUCT_COUNT:
        raise AuthorityContractError("reconstructed catalog parent is incomplete")
    data_manifest_payload, _ = _read_json(
        _safe_path(root, DATA_MANIFEST_REFERENCE, allow_missing=False)
    )
    parent_data_manifest = _base_data_manifest(data_manifest_payload)
    output_catalog, parent_ordered_sha = _build_catalog(parent_catalog, artifacts)
    bindings = _record_bindings(artifacts, ledger, output_catalog)
    catalog_bytes = stable_json_bytes(output_catalog)
    output_data_manifest = _build_data_manifest(parent_data_manifest, _sha256(catalog_bytes))
    data_manifest_bytes = stable_json_bytes(output_data_manifest)
    event = _build_event(
        owner_response=owner_response,
        authorized_exact_owner_response=authorized_exact_owner_response,
        authorized_at=authorized_at,
        packet_sha256=packet_sha,
        proposal_bundle_sha256=content_sha256(artifacts.proposal_bundle.model_dump(mode="json")),
        ledger_sha256=ledger.ledger_sha256,
        cumulative_decision_events_sha256=ledger.cumulative_events_sha256,
        decision_event_head_sha256=ledger.events[-1].event_sha256,
        ordered_record_bindings=bindings,
        output_catalog_sha256=_sha256(catalog_bytes),
        output_data_manifest_sha256=_sha256(data_manifest_bytes),
    )
    public = _build_public_manifest(event, parent_ordered_product_sha256=parent_ordered_sha)
    return (
        ApplicationOutputs(
            catalog=catalog_bytes,
            data_manifest=data_manifest_bytes,
            private_event=stable_json_bytes(event.model_dump(mode="json")),
            public_manifest=stable_json_bytes(public.model_dump(mode="json")),
        ),
        public,
    )


def _write_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cleanup_transaction(root: Path) -> None:
    journal = root / TRANSACTION_JOURNAL_REFERENCE
    directory = root / TRANSACTION_DIRECTORY_REFERENCE
    if directory.exists() or directory.is_symlink():
        if directory.is_symlink() or not directory.is_dir():
            raise AuthorityContractError("application transaction directory is unsafe")
        shutil.rmtree(directory)
        _fsync_directory(root / LOCAL_DIRECTORY)
    journal.unlink(missing_ok=True)
    _fsync_directory(root / LOCAL_DIRECTORY)


def _validate_transaction_entries(
    root: Path, journal: TransactionJournal
) -> list[tuple[TransactionEntry, Path, Path, Path | None]]:
    expected_targets = [reference.as_posix() for reference in APPLICATION_TARGET_REFERENCES]
    supplied_targets = [entry.target for entry in journal.entries]
    if supplied_targets != expected_targets or len(set(supplied_targets)) != len(expected_targets):
        raise AuthorityContractError(
            "application transaction targets differ from the canonical four-output set"
        )
    validated: list[tuple[TransactionEntry, Path, Path, Path | None]] = []
    for index, entry in enumerate(journal.entries):
        expected_staged = TRANSACTION_DIRECTORY_REFERENCE / f"staged-{index}.json"
        expected_backup = TRANSACTION_DIRECTORY_REFERENCE / f"backup-{index}.json"
        if entry.staged != expected_staged.as_posix():
            raise AuthorityContractError("application transaction staged reference is not owned")
        if (entry.previous_sha256 is None) != (entry.backup is None):
            raise AuthorityContractError("application transaction backup contract is inconsistent")
        if entry.backup is not None and entry.backup != expected_backup.as_posix():
            raise AuthorityContractError("application transaction backup reference is not owned")
        if index < 2 and entry.previous_sha256 is None:
            raise AuthorityContractError("application parent output lacks its rollback checksum")
        if index >= 2 and entry.previous_sha256 is not None:
            raise AuthorityContractError("new application artifact falsely claims a parent")
        target = _safe_path(root, APPLICATION_TARGET_REFERENCES[index], allow_missing=True)
        staged = root / expected_staged
        backup = root / expected_backup if entry.backup is not None else None
        validated.append((entry, target, staged, backup))
    return validated


def recover_catalog_application(root: Path) -> Literal["absent", "completed", "rolled_back"]:
    root = _lexical_root(root)
    journal_path = root / TRANSACTION_JOURNAL_REFERENCE
    if not journal_path.exists() and not journal_path.is_symlink():
        return "absent"
    journal_payload, _ = _read_json(journal_path)
    journal = TransactionJournal.model_validate(journal_payload)
    entries = _validate_transaction_entries(root, journal)
    target_states: list[str | None] = []
    for entry, target, staged, backup in entries:
        target_sha = _sha256(target.read_bytes()) if target.is_file() else None
        if target_sha not in {entry.previous_sha256, entry.next_sha256}:
            raise AuthorityContractError("application target state is ambiguous")
        target_states.append(target_sha)
    if all(
        target_sha == entry.next_sha256
        for target_sha, (entry, _, _, _) in zip(target_states, entries, strict=True)
    ):
        _cleanup_transaction(root)
        return "completed"
    if all(
        target_sha == entry.previous_sha256
        for target_sha, (entry, _, _, _) in zip(target_states, entries, strict=True)
    ):
        _cleanup_transaction(root)
        return "rolled_back"
    transaction_directory = root / TRANSACTION_DIRECTORY_REFERENCE
    if transaction_directory.is_symlink() or not transaction_directory.is_dir():
        raise AuthorityContractError(
            "partial application transaction lacks its owned recovery directory"
        )
    for entry, target, staged_reference, backup_reference in entries:
        staged = _safe_path(root, staged_reference.relative_to(root), allow_missing=True)
        backup = (
            _safe_path(root, backup_reference.relative_to(root), allow_missing=False)
            if backup_reference is not None
            else None
        )
        target_sha = _sha256(target.read_bytes()) if target.is_file() else None
        staged_sha = _sha256(staged.read_bytes()) if staged.is_file() else None
        backup_sha = _sha256(backup.read_bytes()) if backup is not None else None
        if backup is not None and backup_sha != entry.previous_sha256:
            raise AuthorityContractError("application rollback backup is stale or missing")
        if staged_sha is not None and staged_sha != entry.next_sha256:
            raise AuthorityContractError("application staged output checksum is stale")
        if target_sha != entry.next_sha256 and staged_sha != entry.next_sha256:
            raise AuthorityContractError("application next output is unavailable")
    for entry, target, _, backup in entries:
        if entry.previous_sha256 is None:
            target.unlink(missing_ok=True)
        else:
            if backup is None:
                raise AuthorityContractError("application rollback backup is missing")
            restore = target.with_name(f".{target.name}.rollback-{os.getpid()}")
            _write_file(restore, backup.read_bytes())
            os.replace(restore, target)
            _fsync_directory(target.parent)
    _cleanup_transaction(root)
    return "rolled_back"


def _publish_atomically(root: Path, files: Mapping[Path, bytes]) -> None:
    if recover_catalog_application(root) not in {"absent", "completed", "rolled_back"}:
        raise AuthorityContractError("application recovery returned an unknown state")
    txn_dir = root / TRANSACTION_DIRECTORY_REFERENCE
    if txn_dir.exists() or txn_dir.is_symlink():
        raise AuthorityContractError("application transaction directory already exists")
    if tuple(files) != APPLICATION_TARGET_REFERENCES:
        raise AuthorityContractError("application publication set is not canonical")
    txn_dir.mkdir(mode=0o700)
    entries: list[TransactionEntry] = []
    journal_path = root / TRANSACTION_JOURNAL_REFERENCE
    try:
        for index, (reference, payload) in enumerate(files.items()):
            target = _safe_path(root, reference, allow_missing=True)
            staged_reference = TRANSACTION_DIRECTORY_REFERENCE / f"staged-{index}.json"
            staged = root / staged_reference
            _write_file(staged, payload)
            if target.exists():
                previous = target.read_bytes()
                backup_reference = TRANSACTION_DIRECTORY_REFERENCE / f"backup-{index}.json"
                backup = root / backup_reference
                _write_file(backup, previous)
                previous_sha: str | None = _sha256(previous)
            else:
                backup_reference = None
                previous_sha = None
            entries.append(
                TransactionEntry(
                    target=reference.as_posix(),
                    staged=staged_reference.as_posix(),
                    backup=backup_reference.as_posix() if backup_reference else None,
                    previous_sha256=previous_sha,
                    next_sha256=_sha256(payload),
                )
            )
        journal = TransactionJournal.model_validate(
            {
                "schema_version": "pvr-canonical-catalog-application-transaction-v1",
                "application_version": APPLICATION_VERSION,
                "status": "prepared",
                "entries": [item.model_dump(mode="json") for item in entries],
            }
        )
        _validate_transaction_entries(root, journal)
        journal_temp = txn_dir / "journal.json"
        _write_file(journal_temp, stable_json_bytes(journal.model_dump(mode="json")))
        os.replace(journal_temp, journal_path)
        _fsync_directory(journal_path.parent)
        for entry in entries:
            staged = root / entry.staged
            target = root / entry.target
            os.replace(staged, target)
            _fsync_directory(target.parent)
    except BaseException as error:
        if journal_path.exists() or journal_path.is_symlink():
            if isinstance(error, Exception):
                recover_catalog_application(root)
        elif txn_dir.exists() and txn_dir.is_dir() and not txn_dir.is_symlink():
            shutil.rmtree(txn_dir)
            _fsync_directory(root / LOCAL_DIRECTORY)
        raise
    _cleanup_transaction(root)


def _validate_installed_outputs(
    root: Path,
    *,
    expected_owner_response: str,
) -> CatalogApplicationManifest:
    expected_response = _normalize(expected_owner_response)
    if not expected_response:
        raise AuthorityContractError("application check requires an exact external owner response")
    artifacts, packet_sha, ledger = _validate_complete_ledger(root)
    event_payload, event_raw = _read_json(
        _safe_path(root, PRIVATE_EVENT_REFERENCE, allow_missing=False)
    )
    public_payload, public_raw = _read_json(
        _safe_path(root, PUBLIC_MANIFEST_REFERENCE, allow_missing=False)
    )
    event = CatalogApplicationAuthorizationEvent.model_validate(event_payload)
    public = CatalogApplicationManifest.model_validate(public_payload)
    if (
        event.owner_response_verbatim != expected_response
        or event.authorized_exact_owner_response != expected_response
    ):
        raise AuthorityContractError("application event differs from external exact authorization")
    catalog_payload, catalog_raw = _read_json(
        _safe_path(root, Path(CATALOG_REFERENCE), allow_missing=False)
    )
    parent_catalog = _parent_catalog_payload(catalog_payload)
    expected_catalog, parent_ordered_sha = _build_catalog(parent_catalog, artifacts)
    bindings = _record_bindings(artifacts, ledger, expected_catalog)
    expected_catalog_raw = stable_json_bytes(expected_catalog)
    if catalog_raw != expected_catalog_raw:
        raise AuthorityContractError(
            "applied catalog differs from deterministic packet-order output"
        )
    data_manifest_payload, data_manifest_raw = _read_json(
        _safe_path(root, DATA_MANIFEST_REFERENCE, allow_missing=False)
    )
    parent_data_manifest = _base_data_manifest(data_manifest_payload)
    expected_data_manifest = _build_data_manifest(parent_data_manifest, _sha256(catalog_raw))
    expected_data_manifest_raw = stable_json_bytes(expected_data_manifest)
    if data_manifest_raw != expected_data_manifest_raw:
        raise AuthorityContractError("applied data manifest differs from catalog-v2 output")
    expected_event = _build_event(
        owner_response=expected_response,
        authorized_exact_owner_response=expected_response,
        authorized_at=event.authorized_at,
        packet_sha256=packet_sha,
        proposal_bundle_sha256=content_sha256(artifacts.proposal_bundle.model_dump(mode="json")),
        ledger_sha256=ledger.ledger_sha256,
        cumulative_decision_events_sha256=ledger.cumulative_events_sha256,
        decision_event_head_sha256=ledger.events[-1].event_sha256,
        ordered_record_bindings=bindings,
        output_catalog_sha256=_sha256(catalog_raw),
        output_data_manifest_sha256=_sha256(data_manifest_raw),
    )
    if event != expected_event or event_raw != stable_json_bytes(event.model_dump(mode="json")):
        raise AuthorityContractError(
            "private application authorization event differs from contract"
        )
    expected_public = _build_public_manifest(
        expected_event, parent_ordered_product_sha256=parent_ordered_sha
    )
    if public != expected_public or public_raw != stable_json_bytes(public.model_dump(mode="json")):
        raise AuthorityContractError("public application manifest differs from safe contract")
    public_text = public_raw.decode("utf-8")
    if expected_response in public_text:
        raise AuthorityContractError("public application manifest contains owner verbatim")
    return public


def check_catalog_application(
    root: Path, *, expected_owner_response: str
) -> CatalogApplicationManifest:
    root = _lexical_root(root)
    if (root / TRANSACTION_JOURNAL_REFERENCE).exists():
        raise AuthorityContractError("catalog application transaction requires recovery")
    return _validate_installed_outputs(root, expected_owner_response=expected_owner_response)


def apply_catalog_application(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    authorized_at: datetime | None = None,
) -> tuple[Literal["created", "unchanged"], CatalogApplicationManifest]:
    root = _lexical_root(root)
    recover_catalog_application(root)
    event_exists = (root / PRIVATE_EVENT_REFERENCE).exists() or (
        root / PRIVATE_EVENT_REFERENCE
    ).is_symlink()
    public_exists = (root / PUBLIC_MANIFEST_REFERENCE).exists() or (
        root / PUBLIC_MANIFEST_REFERENCE
    ).is_symlink()
    if (root / PRIVATE_EVENT_REFERENCE).is_symlink() or (
        root / PUBLIC_MANIFEST_REFERENCE
    ).is_symlink():
        raise AuthorityContractError("catalog application artifact path contains a symlink")
    if event_exists != public_exists:
        raise AuthorityContractError("partial private/public catalog application state")
    if event_exists:
        manifest = _validate_installed_outputs(
            root, expected_owner_response=authorized_exact_owner_response
        )
        if _normalize(owner_response_verbatim) != _normalize(authorized_exact_owner_response):
            raise AuthorityContractError("conflicting retry for catalog application authorization")
        return "unchanged", manifest
    catalog_payload, catalog_raw = _read_json(
        _safe_path(root, Path(CATALOG_REFERENCE), allow_missing=False)
    )
    if catalog_payload.get("catalog_version") != "fixture-v1":
        raise AuthorityContractError("unrecorded catalog-v2 state is not eligible for application")
    if _sha256(catalog_raw) != EXPECTED_RAW_CATALOG_SHA256:
        raise AuthorityContractError("catalog application parent checksum is stale")
    _, data_manifest_raw = _read_json(
        _safe_path(root, DATA_MANIFEST_REFERENCE, allow_missing=False)
    )
    if _sha256(data_manifest_raw) != EXPECTED_PARENT_DATA_MANIFEST_SHA256:
        raise AuthorityContractError("data manifest application parent checksum is stale")
    timestamp = authorized_at or datetime.now(UTC).replace(microsecond=0)
    outputs, _ = _expected_outputs(
        root,
        owner_response=owner_response_verbatim,
        authorized_exact_owner_response=authorized_exact_owner_response,
        authorized_at=timestamp,
    )
    _publish_atomically(
        root,
        {
            Path(CATALOG_REFERENCE): outputs.catalog,
            DATA_MANIFEST_REFERENCE: outputs.data_manifest,
            PRIVATE_EVENT_REFERENCE: outputs.private_event,
            PUBLIC_MANIFEST_REFERENCE: outputs.public_manifest,
        },
    )
    manifest = _validate_installed_outputs(
        root, expected_owner_response=authorized_exact_owner_response
    )
    return "created", manifest
