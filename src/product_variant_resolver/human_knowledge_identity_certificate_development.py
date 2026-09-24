"""Public authority-inventory primitives for identity-certificate development v4."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from functools import cache
from itertools import combinations
from pathlib import Path
from typing import Any, Literal

from .human_knowledge import (
    HumanKnowledgeDocument,
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
)
from .human_knowledge_admission_development import (
    CHARACTER_RRF_WEIGHT,
    CHARACTER_SCORE_FLOOR,
    DIMENSIONS,
    EXISTING_MANIFEST,
    EXISTING_PACK,
    _cases,
    _catalog,
)
from .human_knowledge_anchor_admission_development import summarize as summarize_existing
from .human_knowledge_anchor_confidence_development import (
    PACK_DIRECTORY as ANCHOR_PACK_DIRECTORY,
)
from .human_knowledge_anchor_confidence_development import (
    REPORT_DIRECTORY as ANCHOR_REPORT_DIRECTORY,
)
from .human_knowledge_anchor_confidence_development import _score_anchor
from .human_knowledge_anchor_confidence_development import check as check_anchor
from .human_knowledge_anchor_confidence_development import validate_pack as validate_anchor_pack
from .human_knowledge_identity import NOISE, HumanKnowledgeIdentityRetriever, HumanKnowledgeV4Config
from .human_knowledge_identity_claim_graph_development import (
    CONTEXT_TOKENS as HICG_CONTEXT_TOKENS,
)
from .human_knowledge_identity_claim_graph_development import (
    IdentityClaimGrammar,
    _base_relation,
    _known_secondary_conflicts_abstained,
)
from .human_knowledge_identity_claim_graph_development import (
    apply_policy as apply_reference_policy,
)
from .human_knowledge_identity_contradiction_development import (
    PACK_DIRECTORY as HIC_PACK_DIRECTORY,
)
from .human_knowledge_identity_contradiction_development import (
    PROTOCOL_DIRECTORY as HIC_PROTOCOL_DIRECTORY,
)
from .human_knowledge_identity_contradiction_development import RAW_DIRECTORY as HIC_RAW_DIRECTORY
from .human_knowledge_identity_contradiction_development import (
    _candidate as _upstream_candidate,
)
from .human_knowledge_identity_contradiction_development import (
    _summarize_new as summarize_hic,
)
from .human_knowledge_identity_contradiction_development import validate_pack as validate_hic_pack
from .human_knowledge_identity_contradiction_development import validate_raw as validate_hic_raw
from .human_knowledge_reranker_development import REPORT_DIRECTORY as UPSTREAM_REPORT_DIRECTORY
from .human_knowledge_reranker_development import check as check_upstream
from .identity import normalize_text
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-identity-certificate-development-v4"
SOURCE = "src/product_variant_resolver/human_knowledge_identity_certificate_development.py"
CORPUS_INPUTS = (
    Path("data/human_backed_catalog.json"),
    Path("data/review_family_knowledge.json"),
    Path("data/review_family_knowledge_manifest.json"),
)
EXPECTED_DOCUMENT_COUNTS = {
    "documents": 142,
    "provisional_variant": 100,
    "review_family": 42,
}
EXPECTED_AUTHORITY_COUNTS = {
    "authorities": 139,
    "casting": 97,
    "review_family": 42,
    "duplicate_document_excess": 3,
}
UPSTREAM_FIXED_HASHES = {
    "src/product_variant_resolver/human_knowledge_identity_contradiction_development.py": (
        "167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f"
    ),
    "src/product_variant_resolver/human_knowledge_identity_envelope_development.py": (
        "c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e"
    ),
    "reports/human-knowledge-identity-envelope-development-v2/historical-calibration.json": (
        "fbdc5171f3b1bfbe3f07b207acb56bd9608e2a3136bdff1acb9175e99f1557ce"
    ),
    "reports/human-knowledge-identity-envelope-development-v2/"
    "historical-calibration-manifest.json": (
        "03eee815b2cb4110e158f2ff02bf51d8b582282c1f050358c3be117ee238eeb5"
    ),
    "reports/human-knowledge-identity-envelope-development-v2/historical-calibration.md": (
        "7e0fbd7e1f92cf0d043949e0c0fdee69bd4d53f0a9f40fe1a41d466f6b5039be"
    ),
    "src/product_variant_resolver/human_knowledge_identity_claim_graph_development.py": (
        "998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173"
    ),
    "reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration.json": (
        "d2d94334d311c84e17c98b2f7d38876674ecf9def1c0dda6c889fbc822a7b1c2"
    ),
    "reports/human-knowledge-identity-claim-graph-development-v3/"
    "historical-calibration-manifest.json": (
        "9666ff2b5c63677fbc6f74daf9f4490e191c9a209151c798e44e75cccb2cac5f"
    ),
    "reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration.md": (
        "16f5b425c6c3e4f7947f868112663a1e024c0270484ebea34fcfe7f583b460a5"
    ),
}

AuthorityKind = Literal["casting", "review_family"]
AuthorityStatus = Literal["certifiable", "unresolved_collision"]
ClaimKind = Literal["alphabetic", "numeric_frame", "alphanumeric_frame"]
FrameKind = Literal["leading_year", "standalone_model", "alphanumeric_model", "compact_model"]
MAX_PRIMARY_CLAIMS = 12
BRIDGE_RELATIONS = frozenset(
    {
        "exact",
        "compact_segmentation",
        "unique_prefix_abbreviation",
        "unique_alpha_edit_1",
        "leading_year_suffix",
        "ocr_o_zero",
        "ocr_repeated_digit_restore",
        "leading_year_uncertainty_x",
    }
)
CONTEXT_TOKENS = (
    HICG_CONTEXT_TOKENS
    | NOISE
    | frozenset(
        {
            "unverified",
            "greetings",
            "space",
            "premium",
            "performance",
            "hypercar",
            "sedan",
            "coupe",
            "roadster",
            "electric",
            "crossover",
            "wagon",
            "touring",
        }
    )
)
PROFILES = (
    "reference-anchor",
    "certificate-exact",
    "certificate-structural",
    "certificate-bounded",
)
NON_REFERENCE_PROFILES = PROFILES[1:]
PROFILE_RELATIONS = {
    "certificate-exact": frozenset({"exact"}),
    "certificate-structural": frozenset({"exact", "compact_segmentation", "leading_year_suffix"}),
    "certificate-bounded": BRIDGE_RELATIONS,
}
QUERY_SUPPORT_STATUSES = frozenset({"singleton", "empty", "ambiguous", "error"})
CANDIDATE_DECISIONS = frozenset({"admit", "abstain"})
PROFILE_PREFERENCE = {
    "certificate-exact": 0,
    "certificate-structural": 1,
    "certificate-bounded": 2,
    "reference-anchor": 3,
}
CANDIDATE_LIMIT = 5
DATA_DIRECTORY = Path("data/evaluation") / VERSION
PROTOCOL_DIRECTORY = DATA_DIRECTORY / "protocol"
INVENTORY_DIRECTORY = DATA_DIRECTORY / "inventory"
PACK_DIRECTORY = DATA_DIRECTORY / "pack"
RAW_DIRECTORY = DATA_DIRECTORY / "raw"
REPORT_DIRECTORY = Path("reports") / VERSION
DECLARATIONS_PATH = (
    Path("specs/human-knowledge-identity-certificate-development")
    / "holdout-negative-declarations.json"
)
CALIBRATION_JSON = "historical-calibration.json"
CALIBRATION_MANIFEST = "historical-calibration-manifest.json"
CALIBRATION_MARKDOWN = "historical-calibration.md"
SELECTION_JSON = "selection.json"
SELECTION_MARKDOWN = "selection.md"
CALIBRATION_SCHEMA = "pvr-human-knowledge-identity-certificate-calibration-v4"
PROTOCOL_SCHEMA = "pvr-human-knowledge-identity-certificate-protocol-v4"
INVENTORY_SCHEMA = "pvr-human-knowledge-identity-certificate-inventory-v4"
PACK_SCHEMA = "pvr-human-knowledge-identity-certificate-pack-v4"
RAW_SCHEMA = "pvr-human-knowledge-identity-certificate-raw-v4"
REPORT_SCHEMA = "pvr-human-knowledge-identity-certificate-selection-v4"
HISTORICAL_DENOMINATORS = {
    "existing_public": 223,
    "anchor_confidence_v4": 22,
    "hic_v1": 24,
}
HISTORICAL_GATE_TARGETS = {
    "existing_positive_hits_at_5": 168,
    "merge_hits_at_5": 4,
    "existing_forbidden_candidates": 0,
    "unrelated_nonempty": 0,
    "new_required_hits_at_5": 24,
    "anchor_valid_low_coverage_hits": 10,
    "anchor_missing_identity_nonempty": 0,
    "hic_positive_preservation_hits": 12,
    "hic_absent_identity_nonempty": 0,
    "secondary_numeric_conflicts_abstained": 2,
    "retrieval_errors": 0,
    "certificate_construction_errors": 0,
    "query_support_errors": 0,
    "alias_alignment_errors": 0,
    "frame_comparison_errors": 0,
    "decision_errors": 0,
}
POSITIVE_CHALLENGES = {
    "unique_partial_certificate": 4,
    "punctuation_compact_certificate": 4,
    "bounded_edit_abbreviation_certificate": 4,
    "year_numeric_certificate": 4,
}
NEGATIVE_CHALLENGES = {
    "shared_maker_incomplete_certificate": 4,
    "same_maker_model_substitution": 4,
    "numeric_alphanumeric_frame_conflict": 4,
    "ambiguous_certificate_context_overlap": 4,
}


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"cannot read required public input: {path}") from error


@dataclass(frozen=True, slots=True)
class PublicInputBinding:
    file: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        return {"file": self.file, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class IdentityAuthority:
    authority_key: str
    authority_kind: AuthorityKind
    primary_casting: str
    normalized_primary_casting: str
    member_knowledge_ids: tuple[str, ...]
    member_knowledge_uuids: tuple[str, ...]
    approved_aliases: tuple[str, ...]
    status: AuthorityStatus

    def as_dict(self) -> dict[str, Any]:
        return {
            "authority_key": self.authority_key,
            "authority_kind": self.authority_kind,
            "primary_casting": self.primary_casting,
            "normalized_primary_casting": self.normalized_primary_casting,
            "member_knowledge_ids": list(self.member_knowledge_ids),
            "member_knowledge_uuids": list(self.member_knowledge_uuids),
            "approved_aliases": list(self.approved_aliases),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class AuthorityInventory:
    version: str
    documents: int
    provisional_variant_documents: int
    review_family_documents: int
    authorities: tuple[IdentityAuthority, ...]
    upstream_bindings: tuple[PublicInputBinding, ...]
    corpus_bindings: tuple[PublicInputBinding, ...]
    checksum: str

    @property
    def casting_authorities(self) -> int:
        return sum(item.authority_kind == "casting" for item in self.authorities)

    @property
    def review_family_authorities(self) -> int:
        return sum(item.authority_kind == "review_family" for item in self.authorities)

    @property
    def duplicate_document_excess(self) -> int:
        return self.documents - len(self.authorities)

    def payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "counts": {
                "documents": self.documents,
                "provisional_variant_documents": self.provisional_variant_documents,
                "review_family_documents": self.review_family_documents,
                "authorities": len(self.authorities),
                "casting_authorities": self.casting_authorities,
                "review_family_authorities": self.review_family_authorities,
                "duplicate_document_excess": self.duplicate_document_excess,
            },
            "upstream_bindings": [item.as_dict() for item in self.upstream_bindings],
            "corpus_bindings": [item.as_dict() for item in self.corpus_bindings],
            "authorities": [item.as_dict() for item in self.authorities],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "checksum": self.checksum}


@dataclass(frozen=True, slots=True)
class CertificateClaim:
    claim_id: str
    authority_key: str
    kind: ClaimKind
    normalized_value: str
    source_atom_indices: tuple[int, ...]
    frame_kind: FrameKind | None
    owner_before: str | None
    owner_after: str | None
    digit_runs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "authority_key": self.authority_key,
            "kind": self.kind,
            "normalized_value": self.normalized_value,
            "source_atom_indices": list(self.source_atom_indices),
            "frame_kind": self.frame_kind,
            "owner_before": self.owner_before,
            "owner_after": self.owner_after,
            "digit_runs": list(self.digit_runs),
        }


@dataclass(frozen=True, slots=True)
class CertificateEliminationStep:
    claim_id: str
    remaining_authority_keys: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "remaining_authority_keys": list(self.remaining_authority_keys),
        }


@dataclass(frozen=True, slots=True)
class CertificateMinimalityProof:
    removed_claim_id: str
    remaining_authority_keys: tuple[str, ...]
    deletion_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "removed_claim_id": self.removed_claim_id,
            "remaining_authority_keys": list(self.remaining_authority_keys),
            "deletion_status": self.deletion_status,
        }


@dataclass(frozen=True, slots=True)
class IdentityCertificate:
    certificate_id: str
    authority_key: str
    claim_ids: tuple[str, ...]
    primary_casting: str
    member_knowledge_ids: tuple[str, ...]
    competing_before: tuple[str, ...]
    elimination_steps: tuple[CertificateEliminationStep, ...]
    remaining_after: tuple[str, ...]
    minimality_proof: tuple[CertificateMinimalityProof, ...]
    checksum: str

    def payload(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "authority_key": self.authority_key,
            "claim_ids": list(self.claim_ids),
            "primary_casting": self.primary_casting,
            "member_knowledge_ids": list(self.member_knowledge_ids),
            "competing_before": list(self.competing_before),
            "elimination_steps": [item.as_dict() for item in self.elimination_steps],
            "remaining_after": list(self.remaining_after),
            "minimality_proof": [item.as_dict() for item in self.minimality_proof],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "checksum": self.checksum}


@dataclass(frozen=True, slots=True)
class AliasClaimMapping:
    alias_atom_indices: tuple[int, ...]
    alias_start: int
    alias_end: int
    target_claim_ids: tuple[str, ...]
    relation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "alias_atom_indices": list(self.alias_atom_indices),
            "alias_start": self.alias_start,
            "alias_end": self.alias_end,
            "target_claim_ids": list(self.target_claim_ids),
            "relation": self.relation,
        }


@dataclass(frozen=True, slots=True)
class AliasUnmappedAtom:
    atom_index: int
    text: str
    start: int
    end: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "text": self.text,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True, slots=True)
class AliasBridge:
    authority_key: str
    alias: str
    normalized_alias: str
    mappings: tuple[AliasClaimMapping, ...]
    unmapped_alias_atoms: tuple[AliasUnmappedAtom, ...]
    checksum: str

    def payload(self) -> dict[str, Any]:
        return {
            "authority_key": self.authority_key,
            "alias": self.alias,
            "normalized_alias": self.normalized_alias,
            "mappings": [item.as_dict() for item in self.mappings],
            "unmapped_alias_atoms": [item.as_dict() for item in self.unmapped_alias_atoms],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "checksum": self.checksum}


@dataclass(frozen=True, slots=True)
class CertificateInventory:
    version: str
    authority_inventory_checksum: str
    authorities: tuple[IdentityAuthority, ...]
    claims: tuple[CertificateClaim, ...]
    certificates: tuple[IdentityCertificate, ...]
    alias_bridges: tuple[AliasBridge, ...]
    checksum: str

    def payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "authority_inventory_checksum": self.authority_inventory_checksum,
            "counts": {
                "authorities": len(self.authorities),
                "unresolved_authorities": sum(
                    item.status == "unresolved_collision" for item in self.authorities
                ),
                "claims": len(self.claims),
                "certificates": len(self.certificates),
                "alias_bridges": len(self.alias_bridges),
            },
            "authorities": [item.as_dict() for item in self.authorities],
            "claims": [item.as_dict() for item in self.claims],
            "certificates": [item.as_dict() for item in self.certificates],
            "alias_bridges": [item.as_dict() for item in self.alias_bridges],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "checksum": self.checksum}


@dataclass(frozen=True, slots=True)
class _AliasAtom:
    atom_index: int
    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class QueryAtom:
    atom_index: int
    text: str
    raw_source_token: str
    normalized_start: int
    normalized_end: int
    raw_start: int
    raw_end: int
    source_token_index: int
    segment_index: int
    segment_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "text": self.text,
            "raw_source_token": self.raw_source_token,
            "normalized_start": self.normalized_start,
            "normalized_end": self.normalized_end,
            "raw_start": self.raw_start,
            "raw_end": self.raw_end,
            "source_token_index": self.source_token_index,
            "segment_index": self.segment_index,
            "segment_count": self.segment_count,
        }


@dataclass(frozen=True, slots=True)
class ContextAtomDecision:
    atom_index: int
    text: str
    reason_code: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "text": self.text,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class UnresolvedAtomDecision:
    atom_index: int
    text: str
    reason_code: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "text": self.text,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class ClaimAlignment:
    claim_id: str
    query_atom_indices: tuple[int, ...]
    query_values: tuple[str, ...]
    public_value: str
    relation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "query_atom_indices": list(self.query_atom_indices),
            "query_values": list(self.query_values),
            "public_value": self.public_value,
            "relation": self.relation,
        }


@dataclass(frozen=True, slots=True)
class NumericConflict:
    claim_id: str
    query_atom_index: int
    query_value: str
    public_value: str
    frame_kind: str
    owner_before: str | None
    owner_after: str | None
    reason_code: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "query_atom_index": self.query_atom_index,
            "query_value": self.query_value,
            "public_value": self.public_value,
            "frame_kind": self.frame_kind,
            "owner_before": self.owner_before,
            "owner_after": self.owner_after,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class CertificateMatch:
    certificate_id: str
    authority_key: str
    claim_alignments: tuple[ClaimAlignment, ...]
    missing_claim_ids: tuple[str, ...]
    omitted_primary_claim_ids: tuple[str, ...]
    context_atom_indices: tuple[int, ...]
    unresolved_atom_indices: tuple[int, ...]
    numeric_conflicts: tuple[NumericConflict, ...]
    complete: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "authority_key": self.authority_key,
            "claim_alignments": [item.as_dict() for item in self.claim_alignments],
            "missing_claim_ids": list(self.missing_claim_ids),
            "omitted_primary_claim_ids": list(self.omitted_primary_claim_ids),
            "context_atom_indices": list(self.context_atom_indices),
            "unresolved_atom_indices": list(self.unresolved_atom_indices),
            "numeric_conflicts": [item.as_dict() for item in self.numeric_conflicts],
            "complete": self.complete,
        }


@dataclass(frozen=True, slots=True)
class QuerySupportEvidence:
    normalized_query: str
    inventory_checksum: str
    profile_id: str
    query_atoms: tuple[QueryAtom, ...]
    context_atoms: tuple[ContextAtomDecision, ...]
    certificate_matches: tuple[CertificateMatch, ...]
    support_authority_keys: tuple[str, ...]
    ambiguous_authority_keys: tuple[str, ...]
    unresolved_discriminative_atoms: tuple[UnresolvedAtomDecision, ...]
    numeric_conflicts: tuple[NumericConflict, ...]
    status: str
    checksum: str

    def payload(self) -> dict[str, Any]:
        return {
            "normalized_query": self.normalized_query,
            "inventory_checksum": self.inventory_checksum,
            "profile_id": self.profile_id,
            "query_atoms": [item.as_dict() for item in self.query_atoms],
            "context_atoms": [item.as_dict() for item in self.context_atoms],
            "certificate_matches": [item.as_dict() for item in self.certificate_matches],
            "support_authority_keys": list(self.support_authority_keys),
            "ambiguous_authority_keys": list(self.ambiguous_authority_keys),
            "unresolved_discriminative_atoms": [
                item.as_dict() for item in self.unresolved_discriminative_atoms
            ],
            "numeric_conflicts": [item.as_dict() for item in self.numeric_conflicts],
            "status": self.status,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "checksum": self.checksum}


@dataclass(frozen=True, slots=True)
class CandidateCertificateInput:
    document: HumanKnowledgeDocument
    source_rank: int


@dataclass(frozen=True, slots=True)
class CandidateFrameComparison:
    claim_id: str | None
    query_atom_index: int | None
    relation: str
    query_value: str | None
    candidate_value: str | None
    owner_before: str | None
    owner_after: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "query_atom_index": self.query_atom_index,
            "relation": self.relation,
            "query_value": self.query_value,
            "candidate_value": self.candidate_value,
            "owner_before": self.owner_before,
            "owner_after": self.owner_after,
        }


@dataclass(frozen=True, slots=True)
class CandidateDecisionEvidence:
    query_support_checksum: str
    inventory_checksum: str
    profile_id: str
    candidate_authority_key: str
    member_knowledge_id: str
    source_rank: int
    authority_membership: bool
    frame_comparisons: tuple[CandidateFrameComparison, ...]
    primary_conflict_result: str
    decision: str
    reason_codes: tuple[str, ...]
    checksum: str

    def payload(self) -> dict[str, Any]:
        return {
            "query_support_checksum": self.query_support_checksum,
            "inventory_checksum": self.inventory_checksum,
            "profile_id": self.profile_id,
            "candidate_authority_key": self.candidate_authority_key,
            "member_knowledge_id": self.member_knowledge_id,
            "source_rank": self.source_rank,
            "authority_membership": self.authority_membership,
            "frame_comparisons": [item.as_dict() for item in self.frame_comparisons],
            "primary_conflict_result": self.primary_conflict_result,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "checksum": self.checksum}


def verify_upstream_bindings(root: Path) -> tuple[PublicInputBinding, ...]:
    bindings: list[PublicInputBinding] = []
    for relative_path, expected_hash in sorted(UPSTREAM_FIXED_HASHES.items()):
        actual_hash = _sha256(root / relative_path)
        if actual_hash != expected_hash:
            raise ValueError(f"immutable upstream binding mismatch: {relative_path}")
        bindings.append(PublicInputBinding(relative_path, actual_hash))
    return tuple(bindings)


def bind_corpus_inputs(root: Path) -> tuple[PublicInputBinding, ...]:
    return tuple(
        PublicInputBinding(str(relative_path), _sha256(root / relative_path))
        for relative_path in CORPUS_INPUTS
    )


def _authority_identity(document: HumanKnowledgeDocument) -> tuple[str, AuthorityKind]:
    if isinstance(document, HumanVariantKnowledgeDocument):
        return f"casting:{document.casting_id}", "casting"
    if isinstance(document, ReviewFamilyKnowledgeDocument):
        return f"review_family:{document.review_family_id}", "review_family"
    raise TypeError("unsupported public knowledge document")


def _aliases(
    documents: tuple[HumanKnowledgeDocument, ...], primary_casting: str
) -> tuple[str, ...]:
    by_normalized: dict[str, str] = {}
    primary_normalized = normalize_text(primary_casting)
    for document in documents:
        values = (
            document.human_label_names
            if isinstance(document, HumanVariantKnowledgeDocument)
            else document.aliases
        )
        for value in values:
            normalized = normalize_text(value)
            if not normalized or normalized == primary_normalized:
                continue
            previous = by_normalized.get(normalized)
            if previous is None or value < previous:
                by_normalized[normalized] = value
    return tuple(by_normalized[key] for key in sorted(by_normalized))


def _validate_group(
    authority_key: str,
    authority_kind: AuthorityKind,
    documents: tuple[HumanKnowledgeDocument, ...],
) -> None:
    if not documents:
        raise ValueError(f"empty authority group: {authority_key}")
    if any(
        _authority_identity(document) != (authority_key, authority_kind) for document in documents
    ):
        raise ValueError(f"authority group contains a foreign document: {authority_key}")
    if len({document.casting for document in documents}) != 1:
        raise ValueError(f"authority group has conflicting primary castings: {authority_key}")
    if authority_kind == "casting":
        variants = tuple(
            document
            for document in documents
            if isinstance(document, HumanVariantKnowledgeDocument)
        )
        if len(variants) != len(documents) or len({item.casting_uuid for item in variants}) != 1:
            raise ValueError(f"casting authority has inconsistent lineage: {authority_key}")
    elif len(documents) != 1:
        raise ValueError(f"review-family authority must contain one document: {authority_key}")


def build_authority_inventory(
    documents: tuple[HumanKnowledgeDocument, ...],
    *,
    upstream_bindings: tuple[PublicInputBinding, ...] = (),
    corpus_bindings: tuple[PublicInputBinding, ...] = (),
) -> AuthorityInventory:
    if not documents:
        raise ValueError("authority inventory requires public documents")
    if len({document.knowledge_id for document in documents}) != len(documents):
        raise ValueError("authority inventory requires unique knowledge IDs")
    if len({document.knowledge_uuid for document in documents}) != len(documents):
        raise ValueError("authority inventory requires unique knowledge UUIDs")

    grouped: dict[tuple[str, AuthorityKind], list[HumanKnowledgeDocument]] = defaultdict(list)
    for document in documents:
        grouped[_authority_identity(document)].append(document)

    provisional: list[IdentityAuthority] = []
    for (authority_key, authority_kind), members in sorted(grouped.items()):
        ordered = tuple(sorted(members, key=lambda item: item.knowledge_id))
        _validate_group(authority_key, authority_kind, ordered)
        primary_casting = ordered[0].casting
        normalized_primary = normalize_text(primary_casting)
        if not normalized_primary:
            raise ValueError(f"authority has empty normalized primary casting: {authority_key}")
        provisional.append(
            IdentityAuthority(
                authority_key=authority_key,
                authority_kind=authority_kind,
                primary_casting=primary_casting,
                normalized_primary_casting=normalized_primary,
                member_knowledge_ids=tuple(item.knowledge_id for item in ordered),
                member_knowledge_uuids=tuple(str(item.knowledge_uuid) for item in ordered),
                approved_aliases=_aliases(ordered, primary_casting),
                status="certifiable",
            )
        )

    primary_owners: dict[str, list[str]] = defaultdict(list)
    for authority in provisional:
        primary_owners[authority.normalized_primary_casting].append(authority.authority_key)
    colliding_keys = {
        authority_key
        for authority_keys in primary_owners.values()
        if len(authority_keys) > 1
        for authority_key in authority_keys
    }
    authorities = tuple(
        replace(authority, status="unresolved_collision")
        if authority.authority_key in colliding_keys
        else authority
        for authority in provisional
    )

    inventory = AuthorityInventory(
        version=VERSION,
        documents=len(documents),
        provisional_variant_documents=sum(
            isinstance(document, HumanVariantKnowledgeDocument) for document in documents
        ),
        review_family_documents=sum(
            isinstance(document, ReviewFamilyKnowledgeDocument) for document in documents
        ),
        authorities=authorities,
        upstream_bindings=tuple(sorted(upstream_bindings, key=lambda item: item.file)),
        corpus_bindings=tuple(sorted(corpus_bindings, key=lambda item: item.file)),
        checksum="",
    )
    checksum = hashlib.sha256(_canonical_json(inventory.payload()).encode()).hexdigest()
    return replace(inventory, checksum=checksum)


def _digit_runs(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\d+", value))


def _claim_id(authority_key: str, atom_index: int) -> str:
    authority_digest = hashlib.sha256(authority_key.encode()).hexdigest()[:16]
    return f"claim-{authority_digest}-{atom_index:02d}"


def _claims_for_authority(authority: IdentityAuthority) -> tuple[CertificateClaim, ...]:
    atoms = tuple(authority.normalized_primary_casting.split())
    if not atoms:
        raise ValueError(f"authority has no primary claims: {authority.authority_key}")
    if len(atoms) > MAX_PRIMARY_CLAIMS:
        raise ValueError(
            f"authority exceeds {MAX_PRIMARY_CLAIMS} primary claims: {authority.authority_key}"
        )
    alphabetic_indices = tuple(
        index for index, atom in enumerate(atoms) if any(character.isalpha() for character in atom)
    )
    first_alphabetic = alphabetic_indices[0] if alphabetic_indices else None
    claims: list[CertificateClaim] = []
    for atom_index, atom in enumerate(atoms):
        digits = _digit_runs(atom)
        if not digits:
            kind: ClaimKind = "alphabetic"
            frame_kind: FrameKind | None = None
            before = None
            after = None
        else:
            kind = "numeric_frame" if atom.isdigit() else "alphanumeric_frame"
            before = next(
                (atoms[index] for index in reversed(alphabetic_indices) if index < atom_index),
                None,
            )
            after = next(
                (atoms[index] for index in alphabetic_indices if index > atom_index),
                None,
            )
            if (
                atom.isdigit()
                and first_alphabetic is not None
                and atom_index < first_alphabetic
                and len(digits) == 1
                and len(digits[0]) in {2, 4}
            ):
                frame_kind = "leading_year"
            elif atom.isdigit():
                frame_kind = "standalone_model"
            else:
                frame_kind = "alphanumeric_model"
        claims.append(
            CertificateClaim(
                claim_id=_claim_id(authority.authority_key, atom_index),
                authority_key=authority.authority_key,
                kind=kind,
                normalized_value=atom,
                source_atom_indices=(atom_index,),
                frame_kind=frame_kind,
                owner_before=before,
                owner_after=after,
                digit_runs=digits,
            )
        )
    return tuple(claims)


def _claim_signature(claim: CertificateClaim) -> tuple[Any, ...]:
    return (
        claim.kind,
        claim.normalized_value,
        claim.frame_kind,
        claim.owner_before,
        claim.owner_after,
        claim.digit_runs,
    )


def _contains_ordered_claims(
    candidate: tuple[CertificateClaim, ...], subset: tuple[CertificateClaim, ...]
) -> bool:
    if not subset:
        return True
    subset_position = 0
    for claim in candidate:
        if _claim_signature(claim) != _claim_signature(subset[subset_position]):
            continue
        subset_position += 1
        if subset_position == len(subset):
            return True
    return False


def _matching_authorities(
    subset: tuple[CertificateClaim, ...],
    claims_by_authority: dict[str, tuple[CertificateClaim, ...]],
) -> tuple[str, ...]:
    return tuple(
        authority_key
        for authority_key, candidate in sorted(claims_by_authority.items())
        if _contains_ordered_claims(candidate, subset)
    )


def _eligible_unique_subset(
    authority_key: str,
    authority_claims: tuple[CertificateClaim, ...],
    subset: tuple[CertificateClaim, ...],
    matches: tuple[str, ...],
) -> bool:
    if matches != (authority_key,):
        return False
    return not (len(subset) == 1 and subset[0].kind == "alphabetic" and len(authority_claims) != 1)


def _deletion_status(
    authority_key: str,
    authority_claims: tuple[CertificateClaim, ...],
    subset: tuple[CertificateClaim, ...],
    matches: tuple[str, ...],
) -> str:
    if not subset:
        return "empty_subset"
    if (
        len(subset) == 1
        and subset[0].kind == "alphabetic"
        and len(authority_claims) != 1
        and matches == (authority_key,)
    ):
        return "single_alphabetic_forbidden"
    if matches != (authority_key,):
        return "non_unique"
    return "still_unique"


def _certificate(
    authority: IdentityAuthority,
    authority_claims: tuple[CertificateClaim, ...],
    subset: tuple[CertificateClaim, ...],
    claims_by_authority: dict[str, tuple[CertificateClaim, ...]],
) -> IdentityCertificate:
    all_authority_keys = tuple(sorted(claims_by_authority))
    elimination_steps = tuple(
        CertificateEliminationStep(
            claim_id=subset[index].claim_id,
            remaining_authority_keys=_matching_authorities(
                subset[: index + 1], claims_by_authority
            ),
        )
        for index in range(len(subset))
    )
    minimality: list[CertificateMinimalityProof] = []
    for index, removed in enumerate(subset):
        deletion = subset[:index] + subset[index + 1 :]
        matches = _matching_authorities(deletion, claims_by_authority)
        minimality.append(
            CertificateMinimalityProof(
                removed_claim_id=removed.claim_id,
                remaining_authority_keys=matches,
                deletion_status=_deletion_status(
                    authority.authority_key, authority_claims, deletion, matches
                ),
            )
        )
    identity_payload = {
        "authority_key": authority.authority_key,
        "claim_ids": [claim.claim_id for claim in subset],
    }
    certificate_id = (
        f"certificate-{hashlib.sha256(_canonical_json(identity_payload).encode()).hexdigest()[:24]}"
    )
    partial = IdentityCertificate(
        certificate_id=certificate_id,
        authority_key=authority.authority_key,
        claim_ids=tuple(claim.claim_id for claim in subset),
        primary_casting=authority.primary_casting,
        member_knowledge_ids=authority.member_knowledge_ids,
        competing_before=tuple(key for key in all_authority_keys if key != authority.authority_key),
        elimination_steps=elimination_steps,
        remaining_after=(authority.authority_key,),
        minimality_proof=tuple(minimality),
        checksum="",
    )
    return replace(
        partial,
        checksum=hashlib.sha256(_canonical_json(partial.payload()).encode()).hexdigest(),
    )


def _certificates_for_authority(
    authority: IdentityAuthority,
    authority_claims: tuple[CertificateClaim, ...],
    claims_by_authority: dict[str, tuple[CertificateClaim, ...]],
) -> tuple[IdentityCertificate, ...]:
    if authority.status == "unresolved_collision":
        return ()
    certificates: list[IdentityCertificate] = []
    for size in range(1, len(authority_claims) + 1):
        for indices in combinations(range(len(authority_claims)), size):
            subset = tuple(authority_claims[index] for index in indices)
            matches = _matching_authorities(subset, claims_by_authority)
            if not _eligible_unique_subset(
                authority.authority_key, authority_claims, subset, matches
            ):
                continue
            deletions = tuple(subset[:index] + subset[index + 1 :] for index in range(len(subset)))
            if any(
                _eligible_unique_subset(
                    authority.authority_key,
                    authority_claims,
                    deletion,
                    _matching_authorities(deletion, claims_by_authority),
                )
                for deletion in deletions
            ):
                continue
            certificates.append(
                _certificate(authority, authority_claims, subset, claims_by_authority)
            )
    return tuple(
        sorted(
            certificates,
            key=lambda item: (
                len(item.claim_ids),
                sum(
                    claim.kind != "alphabetic"
                    for claim in authority_claims
                    if claim.claim_id in item.claim_ids
                ),
                tuple(
                    claim.normalized_value
                    for claim in authority_claims
                    if claim.claim_id in item.claim_ids
                ),
                item.certificate_id,
            ),
        )
    )


def _alias_atoms(alias: str) -> tuple[str, tuple[_AliasAtom, ...]]:
    normalized = normalize_text(alias)
    atoms = tuple(normalized.split())
    cursor = 0
    result: list[_AliasAtom] = []
    for atom_index, atom in enumerate(atoms):
        start = normalized.find(atom, cursor)
        if start < 0:
            raise ValueError("alias normalization offsets are inconsistent")
        end = start + len(atom)
        result.append(_AliasAtom(atom_index, atom, start, end))
        cursor = end
    return normalized, tuple(result)


def _bridge_relation(
    alias_atom: str,
    claim: CertificateClaim,
    primary_values: frozenset[str],
) -> str | None:
    relation_value: object = _base_relation(alias_atom, claim.normalized_value)
    if relation_value is None:
        return None
    if not isinstance(relation_value, str):
        raise TypeError("frozen structural relation must be a string or null")
    relation = relation_value
    if relation in {"unique_prefix_abbreviation", "unique_alpha_edit_1"}:
        expansions = {
            value for value in primary_values if _base_relation(alias_atom, value) == relation
        }
        if expansions != {claim.normalized_value}:
            return None
    return relation


def _alignment_key(mappings: tuple[AliasClaimMapping, ...]) -> tuple[Any, ...]:
    target_count = sum(len(item.target_claim_ids) for item in mappings)
    alias_count = sum(len(item.alias_atom_indices) for item in mappings)
    exact_count = sum(item.relation == "exact" for item in mappings)
    nonexact_count = sum(item.relation != "exact" for item in mappings)
    stable = tuple(
        (item.alias_atom_indices, item.target_claim_ids, item.relation) for item in mappings
    )
    return target_count, alias_count, exact_count, -nonexact_count, -len(mappings), stable


def _alias_mappings(
    alias_atoms: tuple[_AliasAtom, ...],
    claims: tuple[CertificateClaim, ...],
    primary_values: frozenset[str],
) -> tuple[AliasClaimMapping, ...]:
    memo: dict[tuple[int, int], tuple[AliasClaimMapping, ...]] = {}

    def solve(alias_position: int, claim_position: int) -> tuple[AliasClaimMapping, ...]:
        key = (alias_position, claim_position)
        if key in memo:
            return memo[key]
        if alias_position >= len(alias_atoms) or claim_position >= len(claims):
            return ()
        options = [
            solve(alias_position + 1, claim_position),
            solve(alias_position, claim_position + 1),
        ]
        atom = alias_atoms[alias_position]
        claim = claims[claim_position]
        relation = _bridge_relation(atom.text, claim, primary_values)
        if relation is not None:
            options.append(
                (
                    AliasClaimMapping(
                        alias_atom_indices=(atom.atom_index,),
                        alias_start=atom.start,
                        alias_end=atom.end,
                        target_claim_ids=(claim.claim_id,),
                        relation=relation,
                    ),
                    *solve(alias_position + 1, claim_position + 1),
                )
            )
        for claim_end in range(claim_position + 2, len(claims) + 1):
            targets = claims[claim_position:claim_end]
            if atom.text != "".join(item.normalized_value for item in targets):
                continue
            options.append(
                (
                    AliasClaimMapping(
                        alias_atom_indices=(atom.atom_index,),
                        alias_start=atom.start,
                        alias_end=atom.end,
                        target_claim_ids=tuple(item.claim_id for item in targets),
                        relation="compact_segmentation",
                    ),
                    *solve(alias_position + 1, claim_end),
                )
            )
        for alias_end in range(alias_position + 2, len(alias_atoms) + 1):
            sources = alias_atoms[alias_position:alias_end]
            if "".join(item.text for item in sources) != claim.normalized_value:
                continue
            options.append(
                (
                    AliasClaimMapping(
                        alias_atom_indices=tuple(item.atom_index for item in sources),
                        alias_start=sources[0].start,
                        alias_end=sources[-1].end,
                        target_claim_ids=(claim.claim_id,),
                        relation="compact_segmentation",
                    ),
                    *solve(alias_end, claim_position + 1),
                )
            )
        result = max(options, key=_alignment_key)
        memo[key] = result
        return result

    return solve(0, 0)


def _alias_bridge(
    authority: IdentityAuthority,
    alias: str,
    claims: tuple[CertificateClaim, ...],
    primary_values: frozenset[str],
) -> AliasBridge:
    normalized, atoms = _alias_atoms(alias)
    mappings = _alias_mappings(atoms, claims, primary_values)
    mapped_indices = {
        atom_index for mapping in mappings for atom_index in mapping.alias_atom_indices
    }
    unmapped = tuple(
        AliasUnmappedAtom(atom.atom_index, atom.text, atom.start, atom.end)
        for atom in atoms
        if atom.atom_index not in mapped_indices
    )
    partial = AliasBridge(
        authority_key=authority.authority_key,
        alias=alias,
        normalized_alias=normalized,
        mappings=mappings,
        unmapped_alias_atoms=unmapped,
        checksum="",
    )
    return replace(
        partial,
        checksum=hashlib.sha256(_canonical_json(partial.payload()).encode()).hexdigest(),
    )


def _certificate_inventory_checksum(inventory: CertificateInventory) -> str:
    return hashlib.sha256(_canonical_json(inventory.payload()).encode()).hexdigest()


def build_certificate_inventory(authority_inventory: AuthorityInventory) -> CertificateInventory:
    expected_authority_checksum = hashlib.sha256(
        _canonical_json(authority_inventory.payload()).encode()
    ).hexdigest()
    if authority_inventory.checksum != expected_authority_checksum:
        raise ValueError("authority inventory checksum is not reproducible")

    initial_claims = {
        authority.authority_key: _claims_for_authority(authority)
        for authority in authority_inventory.authorities
    }
    statuses: dict[str, AuthorityStatus] = {}
    for authority in authority_inventory.authorities:
        complete_matches = _matching_authorities(
            initial_claims[authority.authority_key], initial_claims
        )
        statuses[authority.authority_key] = (
            "certifiable"
            if complete_matches == (authority.authority_key,)
            else "unresolved_collision"
        )
    authorities = tuple(
        replace(authority, status=statuses[authority.authority_key])
        for authority in authority_inventory.authorities
    )
    claims_by_authority = {
        authority.authority_key: initial_claims[authority.authority_key]
        for authority in authorities
    }
    claims = tuple(
        claim for authority in authorities for claim in claims_by_authority[authority.authority_key]
    )
    certificates = tuple(
        certificate
        for authority in authorities
        for certificate in _certificates_for_authority(
            authority,
            claims_by_authority[authority.authority_key],
            claims_by_authority,
        )
    )
    certificate_authorities = {item.authority_key for item in certificates}
    missing = {
        authority.authority_key
        for authority in authorities
        if authority.status == "certifiable"
        and authority.authority_key not in certificate_authorities
    }
    if missing:
        raise ValueError(f"certifiable authorities have no minimal certificate: {sorted(missing)}")

    primary_values = frozenset(claim.normalized_value for claim in claims)
    bridges = tuple(
        _alias_bridge(
            authority,
            alias,
            claims_by_authority[authority.authority_key],
            primary_values,
        )
        for authority in authorities
        for alias in authority.approved_aliases
    )
    partial = CertificateInventory(
        version=VERSION,
        authority_inventory_checksum=authority_inventory.checksum,
        authorities=authorities,
        claims=claims,
        certificates=certificates,
        alias_bridges=bridges,
        checksum="",
    )
    inventory = replace(partial, checksum=_certificate_inventory_checksum(partial))
    validate_certificate_inventory(inventory, authority_inventory)
    return inventory


def validate_certificate_inventory(
    inventory: CertificateInventory, authority_inventory: AuthorityInventory
) -> None:
    if inventory.version != VERSION:
        raise ValueError("certificate inventory version differs from contract")
    if inventory.authority_inventory_checksum != authority_inventory.checksum:
        raise ValueError("certificate inventory authority binding is stale")
    if inventory.checksum != _certificate_inventory_checksum(inventory):
        raise ValueError("certificate inventory checksum is not reproducible")
    authority_by_key = {item.authority_key: item for item in inventory.authorities}
    if len(authority_by_key) != len(inventory.authorities):
        raise ValueError("certificate inventory contains duplicate authorities")
    if set(authority_by_key) != {item.authority_key for item in authority_inventory.authorities}:
        raise ValueError("certificate inventory authority set differs from source inventory")

    claims_by_authority: dict[str, tuple[CertificateClaim, ...]] = {}
    for authority in inventory.authorities:
        actual = tuple(
            claim for claim in inventory.claims if claim.authority_key == authority.authority_key
        )
        expected = _claims_for_authority(authority)
        if actual != expected:
            raise ValueError(
                f"certificate claims differ from primary casting: {authority.authority_key}"
            )
        claims_by_authority[authority.authority_key] = actual
    if len({claim.claim_id for claim in inventory.claims}) != len(inventory.claims):
        raise ValueError("certificate inventory contains duplicate claim IDs")

    expected_statuses = {
        authority_key: (
            "certifiable"
            if _matching_authorities(claims, claims_by_authority) == (authority_key,)
            else "unresolved_collision"
        )
        for authority_key, claims in claims_by_authority.items()
    }
    if any(
        authority.status != expected_statuses[authority.authority_key]
        for authority in inventory.authorities
    ):
        raise ValueError("authority collision status differs from complete primary claims")

    claim_by_id = {item.claim_id: item for item in inventory.claims}
    seen_certificate_ids: set[str] = set()
    certificate_authorities: set[str] = set()
    for certificate in inventory.certificates:
        resolved_authority = authority_by_key.get(certificate.authority_key)
        if resolved_authority is None or resolved_authority.status != "certifiable":
            raise ValueError("certificate targets an unknown or unresolved authority")
        if certificate.certificate_id in seen_certificate_ids:
            raise ValueError("certificate inventory contains duplicate certificate IDs")
        seen_certificate_ids.add(certificate.certificate_id)
        try:
            subset = tuple(claim_by_id[claim_id] for claim_id in certificate.claim_ids)
        except KeyError as error:
            raise ValueError("certificate references an unknown claim") from error
        authority_claims = claims_by_authority[certificate.authority_key]
        source_positions = tuple(claim.source_atom_indices[0] for claim in subset)
        if any(
            claim.authority_key != certificate.authority_key for claim in subset
        ) or source_positions != tuple(sorted(source_positions)):
            raise ValueError("certificate claims cross authority or source order")
        matches = _matching_authorities(subset, claims_by_authority)
        if not _eligible_unique_subset(
            certificate.authority_key, authority_claims, subset, matches
        ):
            raise ValueError("certificate does not uniquely identify its authority")
        expected_certificate = _certificate(
            resolved_authority, authority_claims, subset, claims_by_authority
        )
        if certificate != expected_certificate:
            raise ValueError("certificate proof or checksum is not reproducible")
        for index in range(len(subset)):
            deletion = subset[:index] + subset[index + 1 :]
            deletion_matches = _matching_authorities(deletion, claims_by_authority)
            if _eligible_unique_subset(
                certificate.authority_key,
                authority_claims,
                deletion,
                deletion_matches,
            ):
                raise ValueError("certificate is not minimal")
        certificate_authorities.add(certificate.authority_key)
    expected_certificate_authorities = {
        item.authority_key for item in inventory.authorities if item.status == "certifiable"
    }
    if certificate_authorities != expected_certificate_authorities:
        raise ValueError("certifiable authority certificate coverage is incomplete")

    bridges_by_identity = {
        (bridge.authority_key, bridge.alias): bridge for bridge in inventory.alias_bridges
    }
    if len(bridges_by_identity) != len(inventory.alias_bridges):
        raise ValueError("certificate inventory contains duplicate alias bridges")
    primary_values = frozenset(claim.normalized_value for claim in inventory.claims)
    for bridge in inventory.alias_bridges:
        bridge_authority = authority_by_key.get(bridge.authority_key)
        if bridge_authority is None or bridge.alias not in bridge_authority.approved_aliases:
            raise ValueError("alias bridge is not approved by its authority")
        expected_bridge = _alias_bridge(
            bridge_authority,
            bridge.alias,
            claims_by_authority[bridge_authority.authority_key],
            primary_values,
        )
        if bridge != expected_bridge:
            raise ValueError("alias bridge mapping or checksum is not reproducible")
        mapped_alias_indices = [
            atom_index for mapping in bridge.mappings for atom_index in mapping.alias_atom_indices
        ]
        mapped_claim_ids = [
            claim_id for mapping in bridge.mappings for claim_id in mapping.target_claim_ids
        ]
        unmapped_alias_indices = [item.atom_index for item in bridge.unmapped_alias_atoms]
        if (
            len(mapped_alias_indices) != len(set(mapped_alias_indices))
            or len(mapped_claim_ids) != len(set(mapped_claim_ids))
            or set(mapped_alias_indices).intersection(unmapped_alias_indices)
            or any(mapping.relation not in BRIDGE_RELATIONS for mapping in bridge.mappings)
            or any(
                claim_id
                not in {
                    claim.claim_id for claim in claims_by_authority[bridge_authority.authority_key]
                }
                for claim_id in mapped_claim_ids
            )
        ):
            raise ValueError("alias bridge crosses claim or source boundaries")
    expected_bridges = {
        (authority.authority_key, alias)
        for authority in inventory.authorities
        for alias in authority.approved_aliases
    }
    if set(bridges_by_identity) != expected_bridges:
        raise ValueError("approved alias bridge coverage is incomplete")


def build_public_certificate_inventory(root: Path) -> CertificateInventory:
    authority_inventory = build_public_authority_inventory(root)
    return build_certificate_inventory(authority_inventory)


def profile_definitions() -> tuple[dict[str, Any], ...]:
    return (
        {
            "profile_id": "reference-anchor",
            "certificate_matching": False,
            "survivor_eligible": False,
            "relations": [],
            "scalar_threshold": None,
        },
        *(
            {
                "profile_id": profile_id,
                "certificate_matching": True,
                "survivor_eligible": True,
                "relations": sorted(PROFILE_RELATIONS[profile_id]),
                "scalar_threshold": None,
            }
            for profile_id in NON_REFERENCE_PROFILES
        ),
    )


def _segment_token(token: str, terms: frozenset[str]) -> tuple[str, ...]:
    if token in terms:
        return (token,)

    @cache
    def solve(position: int) -> tuple[tuple[str, ...], ...]:
        if position == len(token):
            return ((),)
        options: list[tuple[str, ...]] = []
        for term in terms:
            if len(term) == 1 and term.isalpha() and not _digit_runs(token):
                continue
            if not token.startswith(term, position):
                continue
            for suffix in solve(position + len(term)):
                options.append((term, *suffix))
        return tuple(options)

    token_digit_runs = _digit_runs(token)
    candidates = tuple(
        value
        for value in solve(0)
        if len(value) > 1
        and tuple(run for term in value for run in _digit_runs(term)) == token_digit_runs
    )
    if not candidates:
        return (token,)

    def score(value: tuple[str, ...]) -> tuple[int, int, int, int]:
        identity_weight = sum(len(term) ** 2 for term in value if term not in CONTEXT_TOKENS)
        numeric_count = sum(any(character.isdigit() for character in term) for term in value)
        return identity_weight, numeric_count, sum(map(len, value)), -len(value)

    best = max(score(value) for value in candidates)
    return min(value for value in candidates if score(value) == best)


def _query_atoms(
    query_text: str, inventory: CertificateInventory
) -> tuple[str, tuple[QueryAtom, ...]]:
    normalized_source = unicodedata.normalize("NFKC", query_text)
    primary_terms = {claim.normalized_value for claim in inventory.claims}
    alias_terms = {
        atom for bridge in inventory.alias_bridges for atom in bridge.normalized_alias.split()
    }
    segment_terms = frozenset(primary_terms | alias_terms | set(CONTEXT_TOKENS))
    raw_parts: list[tuple[str, str, int, int, int]] = []
    source_token_index = 0
    for match in re.finditer(r"[\w]+", normalized_source, flags=re.UNICODE):
        normalized = normalize_text(match.group())
        for part in normalized.split():
            raw_parts.append((part, match.group(), match.start(), match.end(), source_token_index))
            source_token_index += 1
    normalized_query = " ".join(item[0] for item in raw_parts)
    atoms: list[QueryAtom] = []
    normalized_cursor = 0
    for token, raw_token, raw_start, raw_end, token_index in raw_parts:
        segments = _segment_token(token, segment_terms)
        token_start = normalized_cursor
        relative = 0
        for segment_index, segment in enumerate(segments):
            start = token_start + relative
            atoms.append(
                QueryAtom(
                    atom_index=len(atoms),
                    text=segment,
                    raw_source_token=raw_token,
                    normalized_start=start,
                    normalized_end=start + len(segment),
                    raw_start=raw_start,
                    raw_end=raw_end,
                    source_token_index=token_index,
                    segment_index=segment_index,
                    segment_count=len(segments),
                )
            )
            relative += len(segment)
        normalized_cursor += len(token) + 1
    if not atoms:
        raise ValueError("query has no normalized atoms")
    return normalized_query, tuple(atoms)


def _text_relation(
    query_value: str,
    public_value: str,
    profile_id: str,
    primary_values: frozenset[str],
    *,
    segmented: bool = False,
) -> str | None:
    relation_value: object = _base_relation(query_value, public_value)
    if relation_value is None:
        return None
    if not isinstance(relation_value, str):
        raise TypeError("frozen structural relation must be a string or null")
    relation = "compact_segmentation" if segmented and relation_value == "exact" else relation_value
    if relation not in PROFILE_RELATIONS[profile_id]:
        return None
    if relation in {"unique_prefix_abbreviation", "unique_alpha_edit_1"}:
        expansions = {
            value for value in primary_values if _base_relation(query_value, value) == relation
        }
        if expansions != {public_value}:
            return None
    return relation


def _identity_capable_indices(
    atoms: tuple[QueryAtom, ...],
    inventory: CertificateInventory,
    profile_id: str,
) -> frozenset[int]:
    primary_values = frozenset(claim.normalized_value for claim in inventory.claims)
    return frozenset(
        atom.atom_index
        for atom in atoms
        if any(
            _text_relation(
                atom.text,
                public_value,
                profile_id,
                primary_values,
                segmented=atom.segment_count > 1,
            )
            is not None
            for public_value in primary_values
        )
    )


def _context_indices(
    atoms: tuple[QueryAtom, ...], identity_capable: frozenset[int]
) -> frozenset[int]:
    return frozenset(
        atom.atom_index
        for atom in atoms
        if atom.text in CONTEXT_TOKENS and atom.atom_index not in identity_capable
    )


def _query_frame(
    atoms: tuple[QueryAtom, ...],
    atom_indices: tuple[int, ...],
    context_indices: frozenset[int],
) -> tuple[str, str | None, str | None, tuple[str, ...]]:
    selected = tuple(atoms[index] for index in atom_indices)
    value = "".join(atom.text for atom in selected)
    digits = _digit_runs(value)
    uncertainty = re.fullmatch(r"(\d{2}|\d{4})x", value)
    if uncertainty:
        digits = (uncertainty.group(1),)
    if not digits:
        raise ValueError("query frame requires conserved digit runs")
    selected_indices = set(atom_indices)
    alphabetic_indices = tuple(
        atom.atom_index
        for atom in atoms
        if atom.atom_index not in context_indices
        and any(character.isalpha() for character in atom.text)
        and not _digit_runs(atom.text)
    )
    first_alphabetic = alphabetic_indices[0] if alphabetic_indices else None
    start = atom_indices[0]
    end = atom_indices[-1]
    before = next(
        (
            atoms[index].text
            for index in reversed(alphabetic_indices)
            if index < start and index not in selected_indices
        ),
        None,
    )
    after = next(
        (
            atoms[index].text
            for index in alphabetic_indices
            if index > end and index not in selected_indices
        ),
        None,
    )
    if (
        (value.isdigit() or uncertainty is not None)
        and first_alphabetic is not None
        and end < first_alphabetic
        and len(digits) == 1
        and len(digits[0]) in {2, 4}
    ):
        kind = "leading_year"
    elif value.isdigit():
        kind = "standalone_model"
    else:
        kind = "alphanumeric_model"
    return kind, before, after, digits


def _owner_matches(
    query_owner: str | None,
    public_owner: str | None,
    profile_id: str,
    primary_values: frozenset[str],
) -> bool:
    if query_owner is None or public_owner is None:
        return query_owner == public_owner
    return _text_relation(query_owner, public_owner, profile_id, primary_values) is not None


def _frame_matches(
    atoms: tuple[QueryAtom, ...],
    atom_indices: tuple[int, ...],
    claim: CertificateClaim,
    profile_id: str,
    primary_values: frozenset[str],
    context_indices: frozenset[int],
) -> bool:
    if claim.kind == "alphabetic":
        return True
    query_kind, before, after, _ = _query_frame(atoms, atom_indices, context_indices)
    if claim.frame_kind == "leading_year" or query_kind == "leading_year":
        return bool(
            claim.frame_kind == query_kind
            and _owner_matches(after, claim.owner_after, profile_id, primary_values)
        )
    return bool(
        _owner_matches(before, claim.owner_before, profile_id, primary_values)
        and _owner_matches(after, claim.owner_after, profile_id, primary_values)
    )


def _alignment_score(alignments: tuple[ClaimAlignment, ...]) -> tuple[Any, ...]:
    claim_count = len(alignments)
    atom_count = sum(len(item.query_atom_indices) for item in alignments)
    exact_count = sum(item.relation == "exact" for item in alignments)
    nonexact_count = sum(item.relation != "exact" for item in alignments)
    stable = tuple((item.claim_id, item.query_atom_indices, item.relation) for item in alignments)
    return claim_count, atom_count, exact_count, -nonexact_count, stable


def _align_authority_claims(
    atoms: tuple[QueryAtom, ...],
    claims: tuple[CertificateClaim, ...],
    profile_id: str,
    primary_values: frozenset[str],
    context_indices: frozenset[int],
) -> tuple[ClaimAlignment, ...]:
    memo: dict[tuple[int, int], tuple[ClaimAlignment, ...]] = {}

    def solve(query_position: int, claim_position: int) -> tuple[ClaimAlignment, ...]:
        key = (query_position, claim_position)
        if key in memo:
            return memo[key]
        if query_position >= len(atoms) or claim_position >= len(claims):
            return ()
        options = [
            solve(query_position + 1, claim_position),
            solve(query_position, claim_position + 1),
        ]
        atom = atoms[query_position]
        claim = claims[claim_position]
        relation = _text_relation(
            atom.text,
            claim.normalized_value,
            profile_id,
            primary_values,
            segmented=atom.segment_count > 1,
        )
        if relation is not None and _frame_matches(
            atoms,
            (query_position,),
            claim,
            profile_id,
            primary_values,
            context_indices,
        ):
            options.append(
                (
                    ClaimAlignment(
                        claim.claim_id,
                        (query_position,),
                        (atom.text,),
                        claim.normalized_value,
                        relation,
                    ),
                    *solve(query_position + 1, claim_position + 1),
                )
            )
        if "compact_segmentation" in PROFILE_RELATIONS[profile_id]:
            for query_end in range(query_position + 2, len(atoms) + 1):
                query_slice = atoms[query_position:query_end]
                query_value = "".join(item.text for item in query_slice)
                if query_value != claim.normalized_value:
                    continue
                indices = tuple(item.atom_index for item in query_slice)
                if not _frame_matches(
                    atoms,
                    indices,
                    claim,
                    profile_id,
                    primary_values,
                    context_indices,
                ):
                    continue
                options.append(
                    (
                        ClaimAlignment(
                            claim.claim_id,
                            indices,
                            tuple(item.text for item in query_slice),
                            claim.normalized_value,
                            "compact_segmentation",
                        ),
                        *solve(query_end, claim_position + 1),
                    )
                )
        result = max(options, key=_alignment_score)
        memo[key] = result
        return result

    return solve(0, 0)


def _frames_comparable(
    atoms: tuple[QueryAtom, ...],
    query_index: int,
    claim: CertificateClaim,
    profile_id: str,
    primary_values: frozenset[str],
    context_indices: frozenset[int],
) -> bool:
    if claim.kind == "alphabetic" or not _digit_runs(atoms[query_index].text):
        return False
    query_kind, before, after, _ = _query_frame(atoms, (query_index,), context_indices)
    if claim.frame_kind == "leading_year" or query_kind == "leading_year":
        return bool(
            claim.frame_kind == query_kind
            and _owner_matches(after, claim.owner_after, profile_id, primary_values)
        )
    return bool(
        _owner_matches(before, claim.owner_before, profile_id, primary_values)
        and _owner_matches(after, claim.owner_after, profile_id, primary_values)
    )


def _numeric_conflicts(
    atoms: tuple[QueryAtom, ...],
    claims: tuple[CertificateClaim, ...],
    alignments: tuple[ClaimAlignment, ...],
    profile_id: str,
    primary_values: frozenset[str],
    context_indices: frozenset[int],
) -> tuple[NumericConflict, ...]:
    aligned_query_indices = {
        index for alignment in alignments for index in alignment.query_atom_indices
    }
    conflicts: list[NumericConflict] = []
    for atom in atoms:
        if atom.atom_index in aligned_query_indices or not _digit_runs(atom.text):
            continue
        for claim in claims:
            if not _frames_comparable(
                atoms,
                atom.atom_index,
                claim,
                profile_id,
                primary_values,
                context_indices,
            ):
                continue
            relation = _text_relation(
                atom.text,
                claim.normalized_value,
                profile_id,
                primary_values,
                segmented=atom.segment_count > 1,
            )
            if relation is not None:
                continue
            conflicts.append(
                NumericConflict(
                    claim_id=claim.claim_id,
                    query_atom_index=atom.atom_index,
                    query_value=atom.text,
                    public_value=claim.normalized_value,
                    frame_kind=claim.frame_kind or "unknown",
                    owner_before=claim.owner_before,
                    owner_after=claim.owner_after,
                    reason_code="primary_numeric_frame_conflict",
                )
            )
    return tuple(
        sorted(
            conflicts,
            key=lambda item: (item.query_atom_index, item.claim_id, item.public_value),
        )
    )


def _query_support_checksum(evidence: QuerySupportEvidence) -> str:
    return hashlib.sha256(_canonical_json(evidence.payload()).encode()).hexdigest()


def build_query_support(
    query_text: str,
    inventory: CertificateInventory,
    profile_id: str,
) -> QuerySupportEvidence:
    if profile_id == "reference-anchor":
        raise ValueError("reference-anchor is comparison-only and has no certificate support set")
    if profile_id not in NON_REFERENCE_PROFILES:
        raise ValueError("unknown certificate profile")
    normalized_query, atoms = _query_atoms(query_text, inventory)
    identity_capable = _identity_capable_indices(atoms, inventory, profile_id)
    context_indices = _context_indices(atoms, identity_capable)
    primary_values = frozenset(claim.normalized_value for claim in inventory.claims)
    claims_by_authority = {
        authority.authority_key: tuple(
            claim for claim in inventory.claims if claim.authority_key == authority.authority_key
        )
        for authority in inventory.authorities
    }
    authority_alignments = {
        authority.authority_key: _align_authority_claims(
            atoms,
            claims_by_authority[authority.authority_key],
            profile_id,
            primary_values,
            context_indices,
        )
        for authority in inventory.authorities
        if authority.status == "certifiable"
    }
    authority_conflicts = {
        authority_key: _numeric_conflicts(
            atoms,
            claims_by_authority[authority_key],
            alignments,
            profile_id,
            primary_values,
            context_indices,
        )
        for authority_key, alignments in authority_alignments.items()
    }

    matches: list[CertificateMatch] = []
    for certificate in inventory.certificates:
        alignments = authority_alignments[certificate.authority_key]
        aligned_claim_ids = {item.claim_id for item in alignments}
        aligned_atom_indices = {
            index for alignment in alignments for index in alignment.query_atom_indices
        }
        missing = tuple(
            claim_id for claim_id in certificate.claim_ids if claim_id not in aligned_claim_ids
        )
        omitted = tuple(
            claim.claim_id
            for claim in claims_by_authority[certificate.authority_key]
            if claim.claim_id not in aligned_claim_ids
        )
        unresolved = tuple(
            atom.atom_index
            for atom in atoms
            if atom.atom_index not in aligned_atom_indices
            and atom.atom_index not in context_indices
        )
        conflicts = authority_conflicts[certificate.authority_key]
        complete = not missing and not unresolved and not conflicts
        if (
            complete
            or any(claim_id in certificate.claim_ids for claim_id in aligned_claim_ids)
            or conflicts
        ):
            matches.append(
                CertificateMatch(
                    certificate_id=certificate.certificate_id,
                    authority_key=certificate.authority_key,
                    claim_alignments=alignments,
                    missing_claim_ids=missing,
                    omitted_primary_claim_ids=omitted,
                    context_atom_indices=tuple(sorted(context_indices)),
                    unresolved_atom_indices=unresolved,
                    numeric_conflicts=conflicts,
                    complete=complete,
                )
            )
    support_keys = tuple(sorted({item.authority_key for item in matches if item.complete}))
    if len(support_keys) == 1:
        status = "singleton"
        ambiguous_keys: tuple[str, ...] = ()
    elif support_keys:
        status = "ambiguous"
        ambiguous_keys = support_keys
    else:
        status = "empty"
        ambiguous_keys = ()

    if support_keys:
        unresolved_indices: set[int] = set()
        conflicts = ()
    else:
        unresolved_indices = {index for item in matches for index in item.unresolved_atom_indices}
        conflicts = tuple(
            sorted(
                {
                    (
                        conflict.claim_id,
                        conflict.query_atom_index,
                        conflict.query_value,
                        conflict.public_value,
                        conflict.frame_kind,
                        conflict.owner_before,
                        conflict.owner_after,
                        conflict.reason_code,
                    ): conflict
                    for item in matches
                    for conflict in item.numeric_conflicts
                }.values(),
                key=lambda item: (item.query_atom_index, item.claim_id),
            )
        )
    partial = QuerySupportEvidence(
        normalized_query=normalized_query,
        inventory_checksum=inventory.checksum,
        profile_id=profile_id,
        query_atoms=atoms,
        context_atoms=tuple(
            ContextAtomDecision(index, atoms[index].text, "frozen_context_wrapper")
            for index in sorted(context_indices)
        ),
        certificate_matches=tuple(matches),
        support_authority_keys=support_keys,
        ambiguous_authority_keys=ambiguous_keys,
        unresolved_discriminative_atoms=tuple(
            UnresolvedAtomDecision(index, atoms[index].text, "unresolved_discriminative_query_atom")
            for index in sorted(unresolved_indices)
        ),
        numeric_conflicts=conflicts,
        status=status,
        checksum="",
    )
    evidence = replace(partial, checksum=_query_support_checksum(partial))
    validate_query_support(evidence, inventory)
    return evidence


def validate_query_support(evidence: QuerySupportEvidence, inventory: CertificateInventory) -> None:
    if evidence.inventory_checksum != inventory.checksum:
        raise ValueError("query support inventory binding is stale")
    if evidence.profile_id not in NON_REFERENCE_PROFILES:
        raise ValueError("query support uses an invalid certificate profile")
    if evidence.status not in QUERY_SUPPORT_STATUSES or evidence.status == "error":
        raise ValueError("query support status differs from contract")
    if evidence.checksum != _query_support_checksum(evidence):
        raise ValueError("query support checksum is not reproducible")
    if tuple(item.atom_index for item in evidence.query_atoms) != tuple(
        range(len(evidence.query_atoms))
    ):
        raise ValueError("query atom order differs from contract")
    certificate_by_id = {item.certificate_id: item for item in inventory.certificates}
    claim_by_id = {item.claim_id: item for item in inventory.claims}
    complete_keys: set[str] = set()
    for match in evidence.certificate_matches:
        certificate = certificate_by_id.get(match.certificate_id)
        if certificate is None or certificate.authority_key != match.authority_key:
            raise ValueError("query support references an unknown certificate")
        used_indices = [
            index for alignment in match.claim_alignments for index in alignment.query_atom_indices
        ]
        if len(used_indices) != len(set(used_indices)):
            raise ValueError("query support reuses one query span for multiple claims")
        for alignment in match.claim_alignments:
            claim = claim_by_id.get(alignment.claim_id)
            if claim is None or claim.authority_key != match.authority_key:
                raise ValueError("query support alignment crosses authority")
            if alignment.relation not in PROFILE_RELATIONS[evidence.profile_id]:
                raise ValueError("query support uses a relation outside its profile")
            if any(index >= len(evidence.query_atoms) for index in alignment.query_atom_indices):
                raise ValueError("query support alignment references an unknown atom")
        aligned_claim_ids = {item.claim_id for item in match.claim_alignments}
        expected_missing = tuple(
            claim_id for claim_id in certificate.claim_ids if claim_id not in aligned_claim_ids
        )
        expected_complete = bool(
            not expected_missing
            and not match.unresolved_atom_indices
            and not match.numeric_conflicts
        )
        if match.missing_claim_ids != expected_missing or match.complete != expected_complete:
            raise ValueError("query support completeness proof is inconsistent")
        if match.complete:
            complete_keys.add(match.authority_key)
    expected_support = tuple(sorted(complete_keys))
    if evidence.support_authority_keys != expected_support:
        raise ValueError("query support authority set is inconsistent")
    expected_status = (
        "singleton" if len(expected_support) == 1 else "ambiguous" if expected_support else "empty"
    )
    if evidence.status != expected_status:
        raise ValueError("query support status is inconsistent")
    expected_ambiguous = expected_support if expected_status == "ambiguous" else ()
    if evidence.ambiguous_authority_keys != expected_ambiguous:
        raise ValueError("query support ambiguity evidence is inconsistent")


def _candidate_decision_checksum(evidence: CandidateDecisionEvidence) -> str:
    return hashlib.sha256(_canonical_json(evidence.payload()).encode()).hexdigest()


def _candidate_frame_comparisons(
    support: QuerySupportEvidence,
    candidate_claims: tuple[CertificateClaim, ...],
    profile_id: str,
    inventory: CertificateInventory,
) -> tuple[CandidateFrameComparison, ...]:
    atoms = support.query_atoms
    context_indices = frozenset(item.atom_index for item in support.context_atoms)
    primary_values = frozenset(claim.normalized_value for claim in inventory.claims)
    comparisons: list[CandidateFrameComparison] = []
    used_query_indices: set[int] = set()
    for claim in candidate_claims:
        if claim.kind == "alphabetic":
            continue
        comparable = tuple(
            atom
            for atom in atoms
            if atom.atom_index not in used_query_indices
            and _frames_comparable(
                atoms,
                atom.atom_index,
                claim,
                profile_id,
                primary_values,
                context_indices,
            )
        )
        if not comparable:
            comparisons.append(
                CandidateFrameComparison(
                    claim.claim_id,
                    None,
                    "candidate_only",
                    None,
                    claim.normalized_value,
                    claim.owner_before,
                    claim.owner_after,
                )
            )
            continue
        atom = min(comparable, key=lambda item: item.atom_index)
        used_query_indices.add(atom.atom_index)
        relation = _text_relation(
            atom.text,
            claim.normalized_value,
            profile_id,
            primary_values,
            segmented=atom.segment_count > 1,
        )
        comparisons.append(
            CandidateFrameComparison(
                claim.claim_id,
                atom.atom_index,
                relation or "conflict",
                atom.text,
                claim.normalized_value,
                claim.owner_before,
                claim.owner_after,
            )
        )
    for atom in atoms:
        if (
            atom.atom_index not in used_query_indices
            and atom.atom_index not in context_indices
            and _digit_runs(atom.text)
        ):
            comparisons.append(
                CandidateFrameComparison(
                    None,
                    atom.atom_index,
                    "query_only",
                    atom.text,
                    None,
                    None,
                    None,
                )
            )
    return tuple(comparisons)


def candidate_decision(
    candidate: CandidateCertificateInput,
    support: QuerySupportEvidence,
    inventory: CertificateInventory,
) -> CandidateDecisionEvidence:
    validate_query_support(support, inventory)
    if candidate.source_rank not in range(1, 6):
        raise ValueError("candidate source rank must be between one and five")
    authority_key, _ = _authority_identity(candidate.document)
    authority = next(
        (item for item in inventory.authorities if item.authority_key == authority_key),
        None,
    )
    membership = bool(
        authority is not None
        and candidate.document.knowledge_id in authority.member_knowledge_ids
        and support.status == "singleton"
        and support.support_authority_keys == (authority_key,)
    )
    candidate_claims = tuple(
        claim for claim in inventory.claims if claim.authority_key == authority_key
    )
    comparisons = (
        _candidate_frame_comparisons(support, candidate_claims, support.profile_id, inventory)
        if membership
        else ()
    )
    conflict = any(item.relation == "conflict" for item in comparisons)
    reason_codes: tuple[str, ...]
    if support.status != "singleton":
        decision = "abstain"
        reason_codes = ("query_support_not_singleton",)
    elif not membership:
        decision = "abstain"
        reason_codes = ("candidate_authority_mismatch",)
    elif conflict:
        decision = "abstain"
        reason_codes = ("primary_numeric_frame_conflict",)
    else:
        decision = "admit"
        admitted_reasons = ["singleton_authority_member"]
        if authority is not None and authority.authority_kind == "casting":
            admitted_reasons.extend(("casting_authority_only", "variant_not_resolved"))
        else:
            admitted_reasons.append("review_family_authority")
        reason_codes = tuple(admitted_reasons)
    partial = CandidateDecisionEvidence(
        query_support_checksum=support.checksum,
        inventory_checksum=inventory.checksum,
        profile_id=support.profile_id,
        candidate_authority_key=authority_key,
        member_knowledge_id=candidate.document.knowledge_id,
        source_rank=candidate.source_rank,
        authority_membership=membership,
        frame_comparisons=comparisons,
        primary_conflict_result="fail" if conflict else "pass",
        decision=decision,
        reason_codes=reason_codes,
        checksum="",
    )
    evidence = replace(partial, checksum=_candidate_decision_checksum(partial))
    validate_candidate_decision(evidence, support, inventory)
    return evidence


def validate_candidate_decision(
    evidence: CandidateDecisionEvidence,
    support: QuerySupportEvidence,
    inventory: CertificateInventory,
) -> None:
    if (
        evidence.query_support_checksum != support.checksum
        or evidence.inventory_checksum != inventory.checksum
        or evidence.profile_id != support.profile_id
    ):
        raise ValueError("candidate decision bindings are stale")
    if evidence.source_rank not in range(1, 6):
        raise ValueError("candidate decision source rank differs from contract")
    if evidence.decision not in CANDIDATE_DECISIONS:
        raise ValueError("candidate decision differs from contract")
    if evidence.primary_conflict_result not in {"pass", "fail"}:
        raise ValueError("candidate conflict result differs from contract")
    if evidence.checksum != _candidate_decision_checksum(evidence):
        raise ValueError("candidate decision checksum is not reproducible")
    if evidence.decision == "admit" and (
        support.status != "singleton"
        or not evidence.authority_membership
        or evidence.primary_conflict_result != "pass"
        or support.support_authority_keys != (evidence.candidate_authority_key,)
    ):
        raise ValueError("candidate admission bypasses singleton membership or conflict veto")
    if evidence.primary_conflict_result == "fail" and not any(
        item.relation == "conflict" for item in evidence.frame_comparisons
    ):
        raise ValueError("candidate conflict result has no frame evidence")


def evaluate_candidates_in_source_order(
    candidates: tuple[CandidateCertificateInput, ...],
    support: QuerySupportEvidence,
    inventory: CertificateInventory,
) -> tuple[CandidateDecisionEvidence, ...]:
    source_ranks = tuple(item.source_rank for item in candidates)
    if source_ranks != tuple(sorted(source_ranks)) or len(source_ranks) != len(set(source_ranks)):
        raise ValueError("candidate inputs must preserve unique source-rank order")
    decisions = tuple(candidate_decision(candidate, support, inventory) for candidate in candidates)
    if tuple(item.source_rank for item in decisions) != source_ranks:
        raise ValueError("candidate decisions changed source order")
    if any(item.query_support_checksum != support.checksum for item in decisions):
        raise ValueError("candidate decisions changed query support evidence")
    return decisions


def validate_public_inventory(inventory: AuthorityInventory) -> None:
    actual_document_counts = {
        "documents": inventory.documents,
        "provisional_variant": inventory.provisional_variant_documents,
        "review_family": inventory.review_family_documents,
    }
    if actual_document_counts != EXPECTED_DOCUMENT_COUNTS:
        raise ValueError("public authority inventory document counts differ from contract")
    actual_authority_counts = {
        "authorities": len(inventory.authorities),
        "casting": inventory.casting_authorities,
        "review_family": inventory.review_family_authorities,
        "duplicate_document_excess": inventory.duplicate_document_excess,
    }
    if actual_authority_counts != EXPECTED_AUTHORITY_COUNTS:
        raise ValueError("public authority inventory authority counts differ from contract")
    if len({item.authority_key for item in inventory.authorities}) != len(inventory.authorities):
        raise ValueError("public authority inventory contains duplicate authority keys")
    knowledge_ids = [
        knowledge_id
        for authority in inventory.authorities
        for knowledge_id in authority.member_knowledge_ids
    ]
    knowledge_uuids = [
        knowledge_uuid
        for authority in inventory.authorities
        for knowledge_uuid in authority.member_knowledge_uuids
    ]
    if len(knowledge_ids) != len(set(knowledge_ids)) or len(knowledge_ids) != inventory.documents:
        raise ValueError("public knowledge ID membership is incomplete or duplicated")
    if (
        len(knowledge_uuids) != len(set(knowledge_uuids))
        or len(knowledge_uuids) != inventory.documents
    ):
        raise ValueError("public knowledge UUID membership is incomplete or duplicated")
    expected_checksum = hashlib.sha256(_canonical_json(inventory.payload()).encode()).hexdigest()
    if inventory.checksum != expected_checksum:
        raise ValueError("public authority inventory checksum is not reproducible")


def build_public_authority_inventory(root: Path) -> AuthorityInventory:
    upstream_bindings = verify_upstream_bindings(root)
    corpus_bindings = bind_corpus_inputs(root)
    catalog = load_human_knowledge_catalog(*(root / path for path in CORPUS_INPUTS))
    inventory = build_authority_inventory(
        catalog.documents,
        upstream_bindings=upstream_bindings,
        corpus_bindings=corpus_bindings,
    )
    validate_public_inventory(inventory)
    return inventory


# The functions below implement the isolated development lifecycle.  They intentionally live in
# this module rather than the runtime retriever so a measured null result cannot alter production.


def _artifact_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read deterministic artifact: {path}") from error
    if not isinstance(value, dict):
        raise TypeError(f"deterministic artifact must be an object: {path}")
    return value


def _assert_file(path: Path, expected: str) -> None:
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"missing deterministic artifact: {path}") from error
    if actual != expected:
        raise ValueError(f"deterministic artifact differs from recomputation: {path}")


def _freeze_directory(directory: Path, outputs: dict[str, str], label: str) -> str:
    if directory.exists():
        if not directory.is_dir() or {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError(f"{label} artifacts are partial or contain extra files")
        for name, content in outputs.items():
            _assert_file(directory / name, content)
        return "unchanged"
    directory.mkdir(parents=True, exist_ok=False)
    try:
        for name, content in outputs.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except BaseException:
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()
        raise
    return "created"


def _freeze_report_files(directory: Path, outputs: dict[str, str], label: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    allowed = {
        CALIBRATION_JSON,
        CALIBRATION_MANIFEST,
        CALIBRATION_MARKDOWN,
        SELECTION_JSON,
        SELECTION_MARKDOWN,
    }
    current = {path.name for path in directory.iterdir()}
    if not current <= allowed:
        raise ValueError(f"{label} directory contains conflicting files")
    existing = current & set(outputs)
    if existing and existing != set(outputs):
        raise ValueError(f"{label} artifacts are partial")
    if existing:
        for name, content in outputs.items():
            _assert_file(directory / name, content)
        return "unchanged"
    try:
        for name, content in outputs.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except BaseException:
        for name in outputs:
            path = directory / name
            if path.exists():
                path.unlink()
        raise
    return "created"


def _historical_input_paths() -> tuple[Path, ...]:
    return (
        *CORPUS_INPUTS,
        EXISTING_PACK,
        EXISTING_MANIFEST,
        UPSTREAM_REPORT_DIRECTORY / "selection.json",
        ANCHOR_PACK_DIRECTORY / "development-pack.json",
        ANCHOR_PACK_DIRECTORY / "development-pack-manifest.json",
        ANCHOR_REPORT_DIRECTORY / "selection.json",
        HIC_PACK_DIRECTORY / "development-pack.json",
        HIC_PACK_DIRECTORY / "development-pack-manifest.json",
        HIC_PROTOCOL_DIRECTORY / "protocol.json",
        HIC_PROTOCOL_DIRECTORY / "protocol-manifest.json",
        HIC_RAW_DIRECTORY / "raw.json",
        HIC_RAW_DIRECTORY / "raw-manifest.json",
        *(Path(name) for name in UPSTREAM_FIXED_HASHES),
    )


def verify_historical_inputs(root: Path) -> dict[str, str]:
    """Bind every public calibration input without reading private evidence."""

    paths = tuple(dict.fromkeys(_historical_input_paths()))
    hashes = {str(path): _sha256(root / path) for path in paths}
    for name, expected in UPSTREAM_FIXED_HASHES.items():
        if hashes.get(name) != expected:
            raise ValueError(f"immutable upstream hash mismatch: {name}")
    hashes[SOURCE] = _sha256(root / SOURCE)
    return dict(sorted(hashes.items()))


def _non_exact_support_operations(support: QuerySupportEvidence) -> int:
    return sum(
        alignment.relation != "exact"
        for match in support.certificate_matches
        if match.complete and match.authority_key in support.support_authority_keys
        for alignment in match.claim_alignments
    )


def apply_certificate_profile(
    rows: list[dict[str, Any]],
    documents: dict[str, HumanKnowledgeDocument],
    inventory: CertificateInventory,
    profile_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Apply one certificate profile offline while preserving rows and source ranks."""

    if profile_id not in NON_REFERENCE_PROFILES:
        raise ValueError("certificate scoring requires a non-reference profile")
    metrics = {
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
        "non_exact_equivalence_operations": 0,
        "retrieval_errors": 0,
        "certificate_construction_errors": 0,
        "query_support_errors": 0,
        "alias_alignment_errors": 0,
        "frame_comparison_errors": 0,
        "decision_errors": 0,
    }
    filtered_rows: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    for row in rows:
        metrics["retrieval_errors"] += row.get("error") is not None
        source_candidates = row.get("candidates", [])[:CANDIDATE_LIMIT]
        ranks = tuple(candidate.get("source_rank") for candidate in source_candidates)
        if ranks != tuple(range(1, len(source_candidates) + 1)):
            raise ValueError("historical candidates differ from source-rank order")
        metrics["source_candidates"] += len(source_candidates)
        try:
            support = build_query_support(row["query_text"], inventory, profile_id)
        except Exception as error:  # noqa: BLE001 - a measured computation failure is a failed gate
            metrics["query_support_errors"] += 1
            metrics["abstained_candidates"] += len(source_candidates)
            filtered_rows.append({**row, "candidates": []})
            evaluations.append(
                {
                    "case_id": row["case_id"],
                    "query_support": None,
                    "candidates": [],
                    "error": {"type": type(error).__name__, "message": str(error)},
                }
            )
            continue
        metrics["non_exact_equivalence_operations"] += _non_exact_support_operations(support)
        inputs: list[CandidateCertificateInput] = []
        candidate_errors: dict[int, dict[str, Any]] = {}
        for candidate in source_candidates:
            document = documents.get(candidate["knowledge_uuid"])
            if document is None or document.knowledge_id != candidate["knowledge_id"]:
                metrics["alias_alignment_errors"] += 1
                metrics["abstained_candidates"] += 1
                candidate_errors[candidate["source_rank"]] = {
                    "knowledge_id": candidate.get("knowledge_id"),
                    "source_rank": candidate.get("source_rank"),
                    "decision": "abstain",
                    "error": {"type": "ValueError", "message": "candidate absent from corpus"},
                }
                continue
            inputs.append(CandidateCertificateInput(document, candidate["source_rank"]))
        decisions: tuple[CandidateDecisionEvidence, ...]
        try:
            decisions = evaluate_candidates_in_source_order(tuple(inputs), support, inventory)
        except Exception as error:  # noqa: BLE001 - preserve the failed gate, never retry retrieval
            metrics["decision_errors"] += 1
            metrics["abstained_candidates"] += len(inputs)
            decisions = ()
            candidate_errors.update(
                {
                    item.source_rank: {
                        "knowledge_id": item.document.knowledge_id,
                        "source_rank": item.source_rank,
                        "decision": "abstain",
                        "error": {"type": type(error).__name__, "message": str(error)},
                    }
                    for item in inputs
                }
            )
        decision_by_rank = {item.source_rank: item for item in decisions}
        admitted: list[dict[str, Any]] = []
        decision_rows: list[dict[str, Any]] = []
        for candidate in source_candidates:
            decision = decision_by_rank.get(candidate["source_rank"])
            if decision is None:
                decision_rows.append(candidate_errors[candidate["source_rank"]])
                continue
            if decision.decision == "admit":
                admitted.append(candidate)
                metrics["admitted_candidates"] += 1
                metrics["non_exact_equivalence_operations"] += sum(
                    item.relation not in {"exact", "candidate_only", "query_only"}
                    for item in decision.frame_comparisons
                )
            else:
                metrics["abstained_candidates"] += 1
            decision_rows.append({**decision.as_dict(), "error": None})
        filtered_rows.append({**row, "candidates": admitted})
        evaluations.append(
            {
                "case_id": row["case_id"],
                "query_support": support.as_dict(),
                "candidates": decision_rows,
                "error": None,
            }
        )
    return filtered_rows, evaluations, metrics


def _reference_profile(
    rows: list[dict[str, Any]],
    documents: dict[str, HumanKnowledgeDocument],
    grammar: IdentityClaimGrammar,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    filtered, evaluations, old = apply_reference_policy(
        rows, documents, grammar, "reference-anchor"
    )
    metrics = {
        "source_candidates": old["source_candidates"],
        "admitted_candidates": old["admitted_candidates"],
        "abstained_candidates": old["abstained_candidates"],
        "non_exact_equivalence_operations": old["non_exact_equivalence_operations"],
        "retrieval_errors": old["retrieval_errors"],
        "certificate_construction_errors": 0,
        "query_support_errors": old["graph_errors"],
        "alias_alignment_errors": old["alignment_errors"],
        "frame_comparison_errors": 0,
        "decision_errors": old["decision_errors"],
    }
    return filtered, evaluations, metrics


def _gate(name: str, actual: int) -> dict[str, Any]:
    threshold = HISTORICAL_GATE_TARGETS[name]
    return {
        "name": name,
        "operator": "=",
        "threshold": threshold,
        "actual": actual,
        "passed": actual == threshold,
    }


def profile_selection_key(summary: dict[str, Any]) -> tuple[int, int, int, int]:
    metrics = summary["selection_metrics"]
    return (
        metrics["negative_admitted_candidates"],
        metrics["positive_abstained_candidates"],
        metrics["non_exact_equivalence_operations"],
        PROFILE_PREFERENCE[summary["profile_id"]],
    )


def historical_calibration(root: Path) -> dict[str, Any]:
    """Recompute the immutable 223 + 22 + 24 rows with exactly zero retrieval."""

    sources = verify_historical_inputs(root)
    upstream = check_upstream(root)
    anchor_report = check_anchor(root)
    anchor_pack = validate_anchor_pack(root)
    hic_raw = validate_hic_raw(root)
    hic_pack = validate_hic_pack(root)
    historical_rows = upstream["raw"]["rows"]
    anchor_rows = anchor_report["raw"]["rows"]
    hic_rows = hic_raw["rows"]
    if (len(historical_rows), len(anchor_rows), len(hic_rows)) != (223, 22, 24):
        raise ValueError("historical calibration denominator drift")
    catalog = _catalog(root)
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    inventory = build_public_certificate_inventory(root)
    grammar = IdentityClaimGrammar(catalog.documents)
    cases = _cases(root)
    positive_existing = {
        case["case_id"]
        for case in cases
        if case["dataset"] == "false_positive"
        or case.get("case_type") in {"positive_family", "merge_control"}
    }
    anchor_positive = {
        case["case_id"]
        for case in anchor_pack["cases"]
        if case["case_type"] == "valid_low_coverage_anchor"
    }
    hic_positive = {
        case["case_id"]
        for case in hic_pack["cases"]
        if case["case_type"] == "positive_preservation"
    }
    summaries: list[dict[str, Any]] = []
    for profile_id in PROFILES:
        if profile_id == "reference-anchor":
            filtered_existing, evaluations_existing, metrics_existing = _reference_profile(
                historical_rows, documents, grammar
            )
            filtered_anchor, evaluations_anchor, metrics_anchor = _reference_profile(
                anchor_rows, documents, grammar
            )
            filtered_hic, evaluations_hic, metrics_hic = _reference_profile(
                hic_rows, documents, grammar
            )
        else:
            filtered_existing, evaluations_existing, metrics_existing = apply_certificate_profile(
                historical_rows, documents, inventory, profile_id
            )
            filtered_anchor, evaluations_anchor, metrics_anchor = apply_certificate_profile(
                anchor_rows, documents, inventory, profile_id
            )
            filtered_hic, evaluations_hic, metrics_hic = apply_certificate_profile(
                hic_rows, documents, inventory, profile_id
            )
        existing = summarize_existing(cases, filtered_existing, 0.0)
        anchor = _score_anchor(anchor_pack, {**anchor_report["raw"], "rows": filtered_anchor}, 0.0)
        computation_errors = {
            name: sum(metrics[name] for metrics in (metrics_existing, metrics_anchor, metrics_hic))
            for name in (
                "certificate_construction_errors",
                "query_support_errors",
                "alias_alignment_errors",
                "frame_comparison_errors",
                "decision_errors",
            )
        }
        hic = summarize_hic(
            hic_pack,
            hic_rows,
            filtered_hic,
            sum(computation_errors.values()),
        )
        existing_counts = existing["counts"]
        anchor_counts = anchor["counts"]
        hic_counts = hic["counts"]
        actuals = {
            "existing_positive_hits_at_5": existing_counts["existing_positive_hits_at_5"],
            "merge_hits_at_5": existing_counts["merge_hits_at_5"],
            "existing_forbidden_candidates": existing_counts["existing_forbidden_candidates"],
            "unrelated_nonempty": existing_counts["unrelated_nonempty"],
            "new_required_hits_at_5": existing_counts["new_required_hits_at_5"],
            "anchor_valid_low_coverage_hits": anchor_counts["valid_low_coverage_anchor_hits"],
            "anchor_missing_identity_nonempty": anchor_counts["missing_identity_nonempty"],
            "hic_positive_preservation_hits": hic_counts["positive_preservation_hits"],
            "hic_absent_identity_nonempty": hic_counts["absent_identity_nonempty"],
            "secondary_numeric_conflicts_abstained": _known_secondary_conflicts_abstained(
                (anchor_rows, hic_rows), (filtered_anchor, filtered_hic)
            ),
            "retrieval_errors": (
                existing_counts["retrieval_errors"]
                + anchor_counts["anchor_retrieval_errors"]
                + hic_counts["retrieval_errors"]
            ),
            **computation_errors,
        }
        gates = [_gate(name, actuals[name]) for name in HISTORICAL_GATE_TARGETS]
        evaluation_sets = (
            (historical_rows, filtered_existing, positive_existing),
            (anchor_rows, filtered_anchor, anchor_positive),
            (hic_rows, filtered_hic, hic_positive),
        )
        positive_abstained = sum(
            len(source["candidates"]) - len(admitted["candidates"])
            for source_rows, admitted_rows, positive_ids in evaluation_sets
            for source, admitted in zip(source_rows, admitted_rows, strict=True)
            if source["case_id"] in positive_ids
        )
        negative_admitted = sum(
            len(row["candidates"])
            for case, row in zip(anchor_pack["cases"], filtered_anchor, strict=True)
            if case["case_type"] == "missing_identity_hard_negative"
        ) + sum(
            len(row["candidates"])
            for case, row in zip(hic_pack["cases"], filtered_hic, strict=True)
            if case["case_type"] == "absent_identity_contradiction"
        )
        summaries.append(
            {
                "profile_id": profile_id,
                "eligible_as_survivor": profile_id in NON_REFERENCE_PROFILES,
                "existing_223": existing,
                "anchor_v4_22": anchor,
                "hic_v1_24": hic,
                "historical_gates": gates,
                "selection_metrics": {
                    "negative_admitted_candidates": negative_admitted,
                    "positive_abstained_candidates": positive_abstained,
                    "non_exact_equivalence_operations": sum(
                        metrics["non_exact_equivalence_operations"]
                        for metrics in (metrics_existing, metrics_anchor, metrics_hic)
                    ),
                    **computation_errors,
                },
                "candidate_metrics": {
                    "existing_223": metrics_existing,
                    "anchor_v4_22": metrics_anchor,
                    "hic_v1_24": metrics_hic,
                },
                "evaluations": {
                    "existing_223": evaluations_existing,
                    "anchor_v4_22": evaluations_anchor,
                    "hic_v1_24": evaluations_hic,
                },
                "eligible": all(gate["passed"] for gate in gates),
            }
        )
    survivors = [
        summary for summary in summaries if summary["eligible_as_survivor"] and summary["eligible"]
    ]
    winner = min(survivors, key=profile_selection_key, default=None)
    return {
        "schema_version": CALIBRATION_SCHEMA,
        "version": VERSION,
        "status": "historical_calibration_pass" if survivors else "historical_calibration_fail",
        "denominators": HISTORICAL_DENOMINATORS,
        "retrieval_calls_executed": 0,
        "private_local_artifacts_read": False,
        "sources": sources,
        "inventory_checksum": inventory.checksum,
        "profile_definitions": list(profile_definitions()),
        "summaries": summaries,
        "eligible_non_reference_profile_ids": [item["profile_id"] for item in survivors],
        "winner": (
            None
            if winner is None
            else {
                "profile_id": winner["profile_id"],
                "status": "historical_survivor_only_not_holdout_qualified",
            }
        ),
    }


def _calibration_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-certificate-calibration-manifest-v4",
        "version": VERSION,
        "calibration_sha256": hashlib.sha256(_artifact_json(report).encode()).hexdigest(),
        "source_sha256": report["sources"],
        "inventory_checksum": report["inventory_checksum"],
        "denominators": report["denominators"],
        "eligible_non_reference_profile_ids": report["eligible_non_reference_profile_ids"],
        "retrieval_calls_executed": 0,
        "protocol_authorized": bool(report["eligible_non_reference_profile_ids"]),
        "private_local_artifacts_read": False,
    }


def _calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-certificate v4 historical calibration",
        "",
        f"Status: `{report['status']}`.",
        "",
        "This report recomputes the immutable 223 + 22 + 24 public rows with zero retrieval calls.",
        "",
        "| profile | survivor eligible | all gates | existing positives | anchor positives | HIC positives | secondary vetoes | computation errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    error_names = (
        "certificate_construction_errors",
        "query_support_errors",
        "alias_alignment_errors",
        "frame_comparison_errors",
        "decision_errors",
    )
    for summary in report["summaries"]:
        gates = {gate["name"]: gate["actual"] for gate in summary["historical_gates"]}
        lines.append(
            "| {profile} | {survivor} | {eligible} | {existing}/168 | {anchor}/10 | {hic}/12 | {veto}/2 | {errors} |".format(
                profile=summary["profile_id"],
                survivor=summary["eligible_as_survivor"],
                eligible=summary["eligible"],
                existing=gates["existing_positive_hits_at_5"],
                anchor=gates["anchor_valid_low_coverage_hits"],
                hic=gates["hic_positive_preservation_hits"],
                veto=gates["secondary_numeric_conflicts_abstained"],
                errors=sum(gates[name] for name in error_names),
            )
        )
    survivors = report["eligible_non_reference_profile_ids"]
    lines.extend(
        [
            "",
            "Eligible non-reference profiles: "
            + (", ".join(survivors) if survivors else "none")
            + ".",
            "",
            (
                "A protocol and certificate inventory may now be frozen; no holdout or runtime change is yet authorized."
                if survivors
                else "No protocol, inventory, holdout pack, raw retrieval, selection, private evaluation, or runtime change is authorized."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _calibration_outputs(report: dict[str, Any]) -> dict[str, str]:
    return {
        CALIBRATION_JSON: _artifact_json(report),
        CALIBRATION_MANIFEST: _artifact_json(_calibration_manifest(report)),
        CALIBRATION_MARKDOWN: _calibration_markdown(report),
    }


def _build_protocol(report: dict[str, Any], inventory: CertificateInventory) -> dict[str, Any]:
    survivors = report["eligible_non_reference_profile_ids"]
    if not survivors:
        raise ValueError("no non-reference certificate profile passed historical calibration")
    definitions = list(profile_definitions())
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "source_inventory_and_protocol_frozen_before_new_holdout",
        "sources": report["sources"],
        "source_sha256": report["sources"][SOURCE],
        "inventory_checksum": inventory.checksum,
        "inventory_sha256": hashlib.sha256(
            _artifact_json(inventory.as_dict()).encode()
        ).hexdigest(),
        "profile_definitions": definitions,
        "profile_definitions_sha256": hashlib.sha256(
            _canonical_json({"profiles": definitions}).encode()
        ).hexdigest(),
        "historical_calibration_sha256": hashlib.sha256(
            _artifact_json(report).encode()
        ).hexdigest(),
        "historical_denominators": HISTORICAL_DENOMINATORS,
        "historical_gates": HISTORICAL_GATE_TARGETS,
        "historical_eligible_profile_ids": survivors,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "holdout": {
            "positive_count": 16,
            "negative_count": 16,
            "positive_challenges": POSITIVE_CHALLENGES,
            "negative_challenges": NEGATIVE_CHALLENGES,
            "negative_declarations_path": str(DECLARATIONS_PATH),
            "negative_declarations_schema": (
                "pvr-human-knowledge-identity-certificate-negative-declarations-v4"
            ),
            "family_disjoint": True,
        },
        "winner_order": [
            "eligible_only",
            "minimum_negative_admitted_candidates",
            "minimum_positive_abstained_candidates",
            "minimum_non_exact_equivalence_operations",
            "certificate-exact_before-structural-before-bounded",
        ],
        "new_holdout_gates": {
            "positive_preservation_hits": 16,
            "absent_identity_nonempty": 0,
            "retrieval_errors": 0,
            "query_support_errors": 0,
            "alias_alignment_errors": 0,
            "frame_comparison_errors": 0,
            "decision_errors": 0,
        },
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }


def _protocol_manifest(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-certificate-protocol-manifest-v4",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_artifact_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "inventory_checksum": protocol["inventory_checksum"],
        "profile_definitions_sha256": protocol["profile_definitions_sha256"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }


def _inventory_artifacts(inventory: CertificateInventory) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "schema_version": INVENTORY_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_new_holdout",
        "certificate_inventory": inventory.as_dict(),
        "private_local_artifacts_read": False,
    }
    manifest = {
        "schema_version": "pvr-human-knowledge-identity-certificate-inventory-manifest-v4",
        "version": VERSION,
        "inventory_sha256": hashlib.sha256(_artifact_json(payload).encode()).hexdigest(),
        "certificate_inventory_checksum": inventory.checksum,
        "authority_inventory_checksum": inventory.authority_inventory_checksum,
        "private_local_artifacts_read": False,
    }
    return payload, manifest


def freeze_protocol(root: Path) -> str:
    report = historical_calibration(root)
    downstream = (PROTOCOL_DIRECTORY, INVENTORY_DIRECTORY, PACK_DIRECTORY, RAW_DIRECTORY)
    if not report["eligible_non_reference_profile_ids"]:
        if any((root / path).exists() for path in downstream) or any(
            (root / REPORT_DIRECTORY / name).exists()
            for name in (SELECTION_JSON, SELECTION_MARKDOWN)
        ):
            raise ValueError("failed calibration contains unauthorized downstream artifacts")
        calibration_operation = _freeze_report_files(
            root / REPORT_DIRECTORY,
            _calibration_outputs(report),
            "identity-certificate historical calibration",
        )
        return f"calibration_failed_{calibration_operation}"
    inventory = build_public_certificate_inventory(root)
    if inventory.checksum != report["inventory_checksum"]:
        raise ValueError("certificate inventory drifted after calibration")
    protocol_exists = (root / PROTOCOL_DIRECTORY).exists()
    inventory_exists = (root / INVENTORY_DIRECTORY).exists()
    if protocol_exists != inventory_exists:
        raise ValueError("protocol and inventory artifacts are partial")
    calibration_operation = _freeze_report_files(
        root / REPORT_DIRECTORY,
        _calibration_outputs(report),
        "identity-certificate historical calibration",
    )
    if calibration_operation not in {"created", "unchanged"}:
        raise ValueError("unexpected calibration freeze operation")
    protocol = _build_protocol(report, inventory)
    inventory_payload, inventory_manifest = _inventory_artifacts(inventory)
    protocol_operation = _freeze_directory(
        root / PROTOCOL_DIRECTORY,
        {
            "protocol.json": _artifact_json(protocol),
            "protocol-manifest.json": _artifact_json(_protocol_manifest(protocol)),
        },
        "identity-certificate protocol",
    )
    inventory_operation = _freeze_directory(
        root / INVENTORY_DIRECTORY,
        {
            "inventory.json": _artifact_json(inventory_payload),
            "inventory-manifest.json": _artifact_json(inventory_manifest),
        },
        "identity-certificate inventory",
    )
    if protocol_operation != inventory_operation:
        raise ValueError("protocol and inventory freeze states differ")
    return protocol_operation


def validate_calibration(root: Path) -> dict[str, Any]:
    expected = historical_calibration(root)
    for name, content in _calibration_outputs(expected).items():
        _assert_file(root / REPORT_DIRECTORY / name, content)
    if not expected["eligible_non_reference_profile_ids"] and (
        {path.name for path in (root / REPORT_DIRECTORY).iterdir()}
        != set(_calibration_outputs(expected))
        or any(
            (root / path).exists()
            for path in (PROTOCOL_DIRECTORY, INVENTORY_DIRECTORY, PACK_DIRECTORY, RAW_DIRECTORY)
        )
    ):
        raise ValueError("failed calibration contains unauthorized downstream artifacts")
    return expected


def validate_protocol(root: Path) -> dict[str, Any]:
    report = validate_calibration(root)
    inventory = build_public_certificate_inventory(root)
    if inventory.checksum != report["inventory_checksum"]:
        raise ValueError("certificate inventory differs from calibration")
    expected = _build_protocol(report, inventory)
    _assert_file(root / PROTOCOL_DIRECTORY / "protocol.json", _artifact_json(expected))
    _assert_file(
        root / PROTOCOL_DIRECTORY / "protocol-manifest.json",
        _artifact_json(_protocol_manifest(expected)),
    )
    inventory_payload, inventory_manifest = _inventory_artifacts(inventory)
    _assert_file(root / INVENTORY_DIRECTORY / "inventory.json", _artifact_json(inventory_payload))
    _assert_file(
        root / INVENTORY_DIRECTORY / "inventory-manifest.json",
        _artifact_json(inventory_manifest),
    )
    return expected


def _positive_challenge(support: QuerySupportEvidence) -> str | None:
    complete = [
        match
        for match in support.certificate_matches
        if match.complete and match.authority_key in support.support_authority_keys
    ]
    relations = {alignment.relation for match in complete for alignment in match.claim_alignments}
    if relations & {
        "leading_year_suffix",
        "ocr_o_zero",
        "ocr_repeated_digit_restore",
        "leading_year_uncertainty_x",
    }:
        return "year_numeric_certificate"
    if relations & {"unique_prefix_abbreviation", "unique_alpha_edit_1"}:
        return "bounded_edit_abbreviation_certificate"
    if "compact_segmentation" in relations:
        return "punctuation_compact_certificate"
    if any(match.omitted_primary_claim_ids for match in complete):
        return "unique_partial_certificate"
    return None


def _positive_holdout_cases(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = build_public_certificate_inventory(root)
    catalog = _catalog(root)
    documents = {document.knowledge_id: document for document in catalog.documents}
    upstream_rows = {row["case_id"]: row for row in check_upstream(root)["raw"]["rows"]}
    anchor_pack = validate_anchor_pack(root)
    hic_pack = validate_hic_pack(root)
    used_documents = {
        case["expected"]["knowledge_id"]
        for pack in (anchor_pack, hic_pack)
        for case in pack["cases"]
        if case["case_type"] in {"valid_low_coverage_anchor", "positive_preservation"}
    }
    used_authorities = {
        _authority_identity(documents[knowledge_id])[0]
        for knowledge_id in used_documents
        if knowledge_id in documents
    }
    candidates: dict[str, list[tuple[str, dict[str, Any], dict[str, Any], str]]] = defaultdict(list)
    protocol_hash = _sha256(root / PROTOCOL_DIRECTORY / "protocol.json")
    for case in _cases(root):
        row = upstream_rows.get(case["case_id"])
        if case.get("case_type") != "positive_family" or row is None or not row["candidates"]:
            continue
        top = row["candidates"][0]
        document = documents.get(top["knowledge_id"])
        if document is None or top["source_rank"] != 1 or top["knowledge_id"] in used_documents:
            continue
        authority_key, _ = _authority_identity(document)
        if authority_key in used_authorities:
            continue
        try:
            support = build_query_support(case["query_text"], inventory, "certificate-bounded")
        except ValueError:
            continue
        if support.status != "singleton" or support.support_authority_keys != (authority_key,):
            continue
        challenge = _positive_challenge(support)
        if challenge is None:
            continue
        key = hashlib.sha256(f"{protocol_hash}:{challenge}:{case['case_id']}".encode()).hexdigest()
        candidates[challenge].append((key, case, top, authority_key))
    selected: list[dict[str, Any]] = []
    selected_documents: set[str] = set()
    selected_authorities: set[str] = set()
    for challenge, expected_count in protocol["holdout"]["positive_challenges"].items():
        count = 0
        for _, case, top, authority_key in sorted(candidates[challenge]):
            if top["knowledge_id"] in selected_documents or authority_key in selected_authorities:
                continue
            selected_documents.add(top["knowledge_id"])
            selected_authorities.add(authority_key)
            count += 1
            selected.append(
                {
                    "case_id": f"hics-pos-{len(selected) + 1:02d}",
                    "case_type": "positive_preservation",
                    "challenge_type": challenge,
                    "source_case_id": case["case_id"],
                    "query_text": case["query_text"],
                    "authority_key": authority_key,
                    "expected": {
                        "knowledge_id": top["knowledge_id"],
                        "knowledge_uuid": top["knowledge_uuid"],
                        "knowledge_type": top["knowledge_type"],
                        "authority_key": authority_key,
                    },
                }
            )
            if count == expected_count:
                break
        if count != expected_count:
            raise ValueError(f"insufficient family-disjoint positive cases for {challenge}")
    if len(selected) != 16 or len(selected_documents) != 16 or len(selected_authorities) != 16:
        raise ValueError("certificate positives must use sixteen documents and authorities")
    return selected


def _negative_holdout_cases(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    declarations = _load_json(root / DECLARATIONS_PATH)
    if (
        declarations.get("schema_version") != protocol["holdout"]["negative_declarations_schema"]
        or declarations.get("version") != VERSION
        or len(declarations.get("cases", [])) != 16
    ):
        raise ValueError("negative declarations differ from frozen schema or count")
    catalog = _catalog(root)
    public_identities = {
        normalize_text(identity)
        for document in catalog.documents
        for identity in document.character_identity_texts
    }
    prior_packs = (validate_anchor_pack(root), validate_hic_pack(root))
    prior_queries = {
        normalize_text(case["query_text"])
        for pack in prior_packs
        for case in pack["cases"]
        if case["case_type"] in {"missing_identity_hard_negative", "absent_identity_contradiction"}
    }
    prior_identities = {
        normalize_text(case["expected"]["absent_identity"])
        for pack in prior_packs
        for case in pack["cases"]
        if case["case_type"] in {"missing_identity_hard_negative", "absent_identity_contradiction"}
    }
    categories: Counter[str] = Counter()
    identities: set[str] = set()
    queries: set[str] = set()
    rows: list[dict[str, Any]] = []
    for declaration in sorted(
        declarations["cases"],
        key=lambda item: (item.get("challenge_type", ""), item.get("case_id", "")),
    ):
        required = {
            "case_id",
            "challenge_type",
            "query_text",
            "absent_identity",
            "expected_reason",
            "family_key",
        }
        if set(declaration) != required:
            raise ValueError("negative declaration fields differ from contract")
        normalized_identity = normalize_text(declaration["absent_identity"])
        normalized_query = normalize_text(declaration["query_text"])
        if (
            declaration["challenge_type"] not in NEGATIVE_CHALLENGES
            or declaration["expected_reason"] not in {"empty", "ambiguous", "conflict"}
            or not isinstance(declaration["family_key"], str)
            or not declaration["family_key"]
            or not normalized_identity
            or normalized_identity in public_identities
            or normalized_identity in prior_identities
            or normalized_identity in identities
            or normalized_query in prior_queries
            or normalized_query in queries
            or normalized_identity.replace(" ", "") not in normalized_query.replace(" ", "")
        ):
            raise ValueError("negative identity/query is reused, corpus-present, or malformed")
        identities.add(normalized_identity)
        queries.add(normalized_query)
        categories[declaration["challenge_type"]] += 1
        rows.append(
            {
                "case_id": declaration["case_id"],
                "case_type": "absent_identity_contradiction",
                "challenge_type": declaration["challenge_type"],
                "source_case_id": None,
                "query_text": declaration["query_text"],
                "authority_key": None,
                "family_key": declaration["family_key"],
                "expected": {
                    "absent_identity": declaration["absent_identity"],
                    "expected_reason": declaration["expected_reason"],
                    "must_abstain_all": True,
                },
            }
        )
    if dict(categories) != protocol["holdout"]["negative_challenges"]:
        raise ValueError("negative declaration categories differ from four-by-four contract")
    return rows


def build_pack(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = validate_protocol(root)
    positives = _positive_holdout_cases(root, protocol)
    negatives = _negative_holdout_cases(root, protocol)
    cases = [*positives, *negatives]
    if len(cases) != 32 or len({case["case_id"] for case in cases}) != 32:
        raise ValueError("certificate pack must contain thirty-two unique cases")
    positive_authorities = {case["authority_key"] for case in positives}
    negative_families = {case["family_key"] for case in negatives}
    if (
        len(positives) != 16
        or len(negatives) != 16
        or len(positive_authorities) != 16
        or len(negative_families) != 16
        or positive_authorities & negative_families
        or dict(Counter(case["challenge_type"] for case in positives))
        != protocol["holdout"]["positive_challenges"]
        or dict(Counter(case["challenge_type"] for case in negatives))
        != protocol["holdout"]["negative_challenges"]
    ):
        raise ValueError("holdout balance or family-disjoint contract failed")
    sources = {
        str(PROTOCOL_DIRECTORY / "protocol.json"): _sha256(
            root / PROTOCOL_DIRECTORY / "protocol.json"
        ),
        str(PROTOCOL_DIRECTORY / "protocol-manifest.json"): _sha256(
            root / PROTOCOL_DIRECTORY / "protocol-manifest.json"
        ),
        str(INVENTORY_DIRECTORY / "inventory.json"): _sha256(
            root / INVENTORY_DIRECTORY / "inventory.json"
        ),
        str(INVENTORY_DIRECTORY / "inventory-manifest.json"): _sha256(
            root / INVENTORY_DIRECTORY / "inventory-manifest.json"
        ),
        str(DECLARATIONS_PATH): _sha256(root / DECLARATIONS_PATH),
    }
    pack = {
        "schema_version": PACK_SCHEMA,
        "version": VERSION,
        "status": "frozen_after_protocol_before_retrieval",
        "sources": dict(sorted(sources.items())),
        "case_counts": {"positive_preservation": 16, "absent_identity_contradiction": 16},
        "positive_challenge_counts": dict(
            sorted(Counter(case["challenge_type"] for case in positives).items())
        ),
        "negative_challenge_counts": dict(
            sorted(Counter(case["challenge_type"] for case in negatives).items())
        ),
        "family_disjoint": True,
        "cases": cases,
        "eligible_for": ["public_identity_certificate_development_only"],
        "excluded_from": [
            "private_evaluation",
            "runtime_activation",
            "canonical_truth",
            "release_variant_truth",
            "color_truth",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    manifest = {
        "schema_version": "pvr-human-knowledge-identity-certificate-pack-manifest-v4",
        "version": VERSION,
        "pack_sha256": hashlib.sha256(_artifact_json(pack).encode()).hexdigest(),
        "source_sha256": pack["sources"],
        "case_counts": pack["case_counts"],
        "family_disjoint": True,
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    return pack, manifest


def freeze_pack(root: Path) -> str:
    pack, manifest = build_pack(root)
    return _freeze_directory(
        root / PACK_DIRECTORY,
        {
            "development-pack.json": _artifact_json(pack),
            "development-pack-manifest.json": _artifact_json(manifest),
        },
        "identity-certificate pack",
    )


def validate_pack(root: Path) -> dict[str, Any]:
    pack, manifest = build_pack(root)
    _assert_file(root / PACK_DIRECTORY / "development-pack.json", _artifact_json(pack))
    _assert_file(root / PACK_DIRECTORY / "development-pack-manifest.json", _artifact_json(manifest))
    return pack


def collect_payload(root: Path) -> dict[str, Any]:
    protocol = validate_protocol(root)
    pack = validate_pack(root)
    catalog = _catalog(root)
    retriever = HumanKnowledgeIdentityRetriever(
        catalog,
        HashingEmbedding(DIMENSIONS),
        HumanKnowledgeV4Config(
            CHARACTER_SCORE_FLOOR,
            CHARACTER_RRF_WEIGHT,
            artifact_version=f"{VERSION}-collection",
            artifact_sha256=_sha256(root / PROTOCOL_DIRECTORY / "protocol.json"),
        ),
    )
    rows: list[dict[str, Any]] = []
    for case in pack["cases"]:
        query = case["query_text"]
        try:
            candidates, work = retriever.retrieve_with_work(extract_signals(query), CANDIDATE_LIMIT)
            payload = {
                "candidates": [_upstream_candidate(item, query) for item in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - exactly-once evidence retains the error
            payload = {
                "candidates": [],
                "work": None,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        rows.append(
            {
                "case_id": case["case_id"],
                "query_text": query,
                **payload,
            }
        )
    if len(rows) != 32:
        raise ValueError("certificate collection must contain thirty-two rows")
    return {
        "schema_version": RAW_SCHEMA,
        "version": VERSION,
        "status": "label_blind_raw_retrieval_complete",
        "protocol_sha256": _sha256(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "inventory_sha256": _sha256(root / INVENTORY_DIRECTORY / "inventory.json"),
        "pack_sha256": _sha256(root / PACK_DIRECTORY / "development-pack.json"),
        "retrieval_calls": 32,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": protocol["base_retriever"],
        "private_local_artifacts_read": False,
        "rows": rows,
    }


def _raw_manifest(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-certificate-raw-manifest-v4",
        "version": VERSION,
        "raw_sha256": hashlib.sha256(_artifact_json(raw).encode()).hexdigest(),
        "protocol_sha256": _sha256(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "inventory_sha256": _sha256(root / INVENTORY_DIRECTORY / "inventory.json"),
        "pack_sha256": _sha256(root / PACK_DIRECTORY / "development-pack.json"),
        "retrieval_calls": 32,
        "expected_labels_present": False,
        "private_local_artifacts_read": False,
    }


def collect(root: Path) -> tuple[dict[str, Any], str]:
    if (root / RAW_DIRECTORY).exists():
        return validate_raw(root), "unchanged"
    raw = collect_payload(root)
    operation = _freeze_directory(
        root / RAW_DIRECTORY,
        {
            "raw.json": _artifact_json(raw),
            "raw-manifest.json": _artifact_json(_raw_manifest(root, raw)),
        },
        "identity-certificate raw",
    )
    return validate_raw(root), operation


RAW_FORBIDDEN_KEYS = frozenset(
    {
        "absent_identity",
        "authority_key",
        "case_type",
        "challenge_type",
        "decision",
        "eligibility",
        "eligible",
        "expected",
        "expected_label",
        "expected_labels",
        "expected_reason",
        "gates",
        "label",
        "labels",
        "must_abstain_all",
        "policy",
        "profile",
        "profile_id",
        "winner",
    }
)


def _contains_forbidden_raw_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in RAW_FORBIDDEN_KEYS or _contains_forbidden_raw_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_raw_key(item) for item in value)
    return False


def _validate_raw_candidate(
    candidate: dict[str, Any], document: HumanKnowledgeDocument, rank: int
) -> None:
    numeric_required = (candidate.get("source_rrf_score"), candidate.get("identity_token_coverage"))
    numeric_optional = (
        candidate.get("sparse_score"),
        candidate.get("dense_score"),
        candidate.get("character_score"),
    )
    if (
        candidate.get("knowledge_id") != document.knowledge_id
        or candidate.get("knowledge_uuid") != str(document.knowledge_uuid)
        or candidate.get("knowledge_type") != document.knowledge_type
        or candidate.get("casting_id") != getattr(document, "casting_id", None)
        or candidate.get("source_rank") != rank
        or not all(_finite_number(value) for value in numeric_required)
        or not all(value is None or _finite_number(value) for value in numeric_optional)
    ):
        raise ValueError("raw candidate differs from public corpus or numeric contract")


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_raw(root: Path) -> dict[str, Any]:
    protocol = validate_protocol(root)
    pack = validate_pack(root)
    raw = _load_json(root / RAW_DIRECTORY / "raw.json")
    if (
        raw.get("schema_version") != RAW_SCHEMA
        or raw.get("version") != VERSION
        or raw.get("retrieval_calls") != 32
        or raw.get("candidate_limit") != CANDIDATE_LIMIT
        or raw.get("protocol_sha256") != _sha256(root / PROTOCOL_DIRECTORY / "protocol.json")
        or raw.get("inventory_sha256") != _sha256(root / INVENTORY_DIRECTORY / "inventory.json")
        or raw.get("pack_sha256") != _sha256(root / PACK_DIRECTORY / "development-pack.json")
        or raw.get("base_retriever") != protocol["base_retriever"]
        or raw.get("private_local_artifacts_read") is not False
        or _contains_forbidden_raw_key(raw)
        or len(raw.get("rows", [])) != 32
    ):
        raise ValueError("raw identity-certificate metadata differs from contract")
    documents = {str(document.knowledge_uuid): document for document in _catalog(root).documents}
    for case, row in zip(pack["cases"], raw["rows"], strict=True):
        if set(row) != {"case_id", "query_text", "candidates", "work", "error"} or any(
            row.get(name) != case[name] for name in ("case_id", "query_text")
        ):
            raise ValueError("raw identity-certificate row differs from frozen pack")
        if row["error"] is not None:
            if row["candidates"] or row["work"] is not None:
                raise ValueError("errored raw row must preserve empty candidate/work evidence")
        elif row["work"] is None:
            raise ValueError("successful raw row must preserve retrieval work")
        if len(row["candidates"]) > CANDIDATE_LIMIT:
            raise ValueError("raw row exceeds frozen candidate limit")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = documents.get(candidate.get("knowledge_uuid"))
            if document is None:
                raise ValueError("raw candidate is absent from public corpus")
            _validate_raw_candidate(candidate, document, rank)
    _assert_file(
        root / RAW_DIRECTORY / "raw-manifest.json",
        _artifact_json(_raw_manifest(root, raw)),
    )
    return raw


def _summarize_holdout(
    pack: dict[str, Any],
    original_rows: list[dict[str, Any]],
    filtered_rows: list[dict[str, Any]],
    metrics: dict[str, int],
) -> dict[str, Any]:
    counts = {
        "positive_preservation_hits": 0,
        "positive_preservation_hits_at_1": 0,
        "absent_identity_nonempty": 0,
        "retrieval_errors": sum(row["error"] is not None for row in original_rows),
        "query_support_errors": metrics["query_support_errors"],
        "alias_alignment_errors": metrics["alias_alignment_errors"],
        "frame_comparison_errors": metrics["frame_comparison_errors"],
        "decision_errors": metrics["decision_errors"],
        "source_candidates": 0,
        "admitted_candidates": 0,
    }
    case_results: list[dict[str, Any]] = []
    for case, original, filtered in zip(pack["cases"], original_rows, filtered_rows, strict=True):
        if case["case_id"] != original["case_id"] or case["case_id"] != filtered["case_id"]:
            raise ValueError("holdout scoring rows differ from frozen pack")
        counts["source_candidates"] += len(original["candidates"])
        counts["admitted_candidates"] += len(filtered["candidates"])
        result: dict[str, Any] = {"case_id": case["case_id"], "case_type": case["case_type"]}
        if case["case_type"] == "positive_preservation":
            expected = case["expected"]
            rank = next(
                (
                    position
                    for position, candidate in enumerate(filtered["candidates"], 1)
                    if candidate["knowledge_id"] == expected["knowledge_id"]
                    and candidate["knowledge_uuid"] == expected["knowledge_uuid"]
                ),
                None,
            )
            counts["positive_preservation_hits"] += rank is not None
            counts["positive_preservation_hits_at_1"] += rank == 1
            result["target_rank"] = rank
        elif case["case_type"] == "absent_identity_contradiction":
            counts["absent_identity_nonempty"] += bool(filtered["candidates"])
            result["admitted_candidate_count"] = len(filtered["candidates"])
        else:
            raise ValueError("unexpected identity-certificate holdout case type")
        case_results.append(result)
    targets = {
        "positive_preservation_hits": 16,
        "absent_identity_nonempty": 0,
        "retrieval_errors": 0,
        "query_support_errors": 0,
        "alias_alignment_errors": 0,
        "frame_comparison_errors": 0,
        "decision_errors": 0,
    }
    gates = [
        {
            "name": name,
            "operator": "=",
            "threshold": threshold,
            "actual": counts[name],
            "passed": counts[name] == threshold,
        }
        for name, threshold in targets.items()
    ]
    return {
        "counts": counts,
        "gates": gates,
        "eligible": all(gate["passed"] for gate in gates),
        "case_results": case_results,
    }


def score(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    protocol = validate_protocol(root)
    pack = validate_pack(root)
    calibration = validate_calibration(root)
    catalog = _catalog(root)
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    inventory = build_public_certificate_inventory(root)
    calibration_by_id = {item["profile_id"]: item for item in calibration["summaries"]}
    positive_ids = {
        case["case_id"] for case in pack["cases"] if case["case_type"] == "positive_preservation"
    }
    summaries: list[dict[str, Any]] = []
    for profile_id in NON_REFERENCE_PROFILES:
        filtered, evaluations, metrics = apply_certificate_profile(
            raw["rows"], documents, inventory, profile_id
        )
        holdout = _summarize_holdout(pack, raw["rows"], filtered, metrics)
        historical = calibration_by_id[profile_id]
        positive_abstained = historical["selection_metrics"]["positive_abstained_candidates"] + sum(
            len(source["candidates"]) - len(admitted["candidates"])
            for source, admitted in zip(raw["rows"], filtered, strict=True)
            if source["case_id"] in positive_ids
        )
        negative_admitted = historical["selection_metrics"]["negative_admitted_candidates"] + sum(
            len(row["candidates"])
            for case, row in zip(pack["cases"], filtered, strict=True)
            if case["case_type"] == "absent_identity_contradiction"
        )
        eligible = (
            profile_id in protocol["historical_eligible_profile_ids"]
            and historical["eligible"]
            and holdout["eligible"]
        )
        summaries.append(
            {
                "profile_id": profile_id,
                "historical": {
                    "eligible": historical["eligible"],
                    "historical_gates": historical["historical_gates"],
                },
                "new_holdout_32": holdout,
                "selection_metrics": {
                    "negative_admitted_candidates": negative_admitted,
                    "positive_abstained_candidates": positive_abstained,
                    "non_exact_equivalence_operations": historical["selection_metrics"][
                        "non_exact_equivalence_operations"
                    ]
                    + metrics["non_exact_equivalence_operations"],
                },
                "candidate_metrics": metrics,
                "evaluations": evaluations,
                "eligible": eligible,
            }
        )
    eligible = [item for item in summaries if item["eligible"]]
    winner = min(eligible, key=profile_selection_key, default=None)
    return {
        "summaries": summaries,
        "winner": (
            None
            if winner is None
            else {
                "profile_id": winner["profile_id"],
                "selection_metrics": winner["selection_metrics"],
                "historical_eligible_profile_ids": protocol["historical_eligible_profile_ids"],
                "new_holdout_counts": winner["new_holdout_32"]["counts"],
                "status": "qualified_for_new_private_shadow_evaluation_design_only",
            }
        ),
    }


def _selection_sources(root: Path) -> dict[str, str]:
    paths = (
        REPORT_DIRECTORY / CALIBRATION_JSON,
        REPORT_DIRECTORY / CALIBRATION_MANIFEST,
        REPORT_DIRECTORY / CALIBRATION_MARKDOWN,
        PROTOCOL_DIRECTORY / "protocol.json",
        PROTOCOL_DIRECTORY / "protocol-manifest.json",
        INVENTORY_DIRECTORY / "inventory.json",
        INVENTORY_DIRECTORY / "inventory-manifest.json",
        PACK_DIRECTORY / "development-pack.json",
        PACK_DIRECTORY / "development-pack-manifest.json",
        RAW_DIRECTORY / "raw.json",
        RAW_DIRECTORY / "raw-manifest.json",
    )
    return {str(path): _sha256(root / path) for path in paths}


def _report(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "version": VERSION,
        "status": "public_development_selection_complete_not_runtime",
        "protocol_sha256": raw["protocol_sha256"],
        "inventory_sha256": raw["inventory_sha256"],
        "pack_sha256": raw["pack_sha256"],
        "raw_sha256": _sha256(root / RAW_DIRECTORY / "raw.json"),
        "sources": _selection_sources(root),
        "private_local_artifacts_read": False,
        "limitations": [
            "public development evidence is not a private final evaluation",
            "an eligible winner does not authorize runtime activation",
            "casting authority does not resolve color or release variant",
        ],
        **score(root, raw),
    }


def _selection_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-certificate v4 selection",
        "",
        f"Status: `{report['status']}`.",
        "",
        "| profile | historical | new holdout | eligible | negatives admitted | positives abstained | non-exact operations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        lines.append(
            "| {profile} | {historical} | {holdout} | {eligible} | {negative} | {positive} | {nonexact} |".format(
                profile=summary["profile_id"],
                historical=summary["historical"]["eligible"],
                holdout=summary["new_holdout_32"]["eligible"],
                eligible=summary["eligible"],
                negative=summary["selection_metrics"]["negative_admitted_candidates"],
                positive=summary["selection_metrics"]["positive_abstained_candidates"],
                nonexact=summary["selection_metrics"]["non_exact_equivalence_operations"],
            )
        )
    lines.extend(
        [
            "",
            f"Winner: `{None if report['winner'] is None else report['winner']['profile_id']}`.",
            "",
            "This public result does not activate API, Dual RAG, PostgreSQL, canonical, release, or color behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def write_selection(root: Path) -> tuple[dict[str, Any], str]:
    raw = validate_raw(root)
    report = _report(root, raw)
    operation = _freeze_report_files(
        root / REPORT_DIRECTORY,
        {
            SELECTION_JSON: _artifact_json(report),
            SELECTION_MARKDOWN: _selection_markdown(report),
        },
        "identity-certificate selection",
    )
    return check(root), operation


def check(root: Path) -> dict[str, Any]:
    calibration = validate_calibration(root)
    if not calibration["eligible_non_reference_profile_ids"]:
        return calibration
    protocol = validate_protocol(root)
    if not (root / PACK_DIRECTORY).exists():
        if (root / RAW_DIRECTORY).exists():
            raise ValueError("raw artifacts exist before the frozen pack")
        return protocol
    pack = validate_pack(root)
    if not (root / RAW_DIRECTORY).exists():
        if (root / REPORT_DIRECTORY / SELECTION_JSON).exists():
            raise ValueError("selection exists before label-blind raw evidence")
        return pack
    raw = validate_raw(root)
    paths = (
        root / REPORT_DIRECTORY / SELECTION_JSON,
        root / REPORT_DIRECTORY / SELECTION_MARKDOWN,
    )
    if not any(path.exists() for path in paths):
        return raw
    if not all(path.exists() for path in paths):
        raise ValueError("selection artifacts are partial")
    expected = _report(root, raw)
    _assert_file(paths[0], _artifact_json(expected))
    _assert_file(paths[1], _selection_markdown(expected))
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Develop public candidate-independent identity certificates"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    phases = parser.add_mutually_exclusive_group(required=True)
    phases.add_argument("--freeze-protocol", action="store_true")
    phases.add_argument("--freeze-pack", action="store_true")
    phases.add_argument("--collect", action="store_true")
    phases.add_argument("--score", action="store_true")
    phases.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_protocol:
        operation = freeze_protocol(root)
        output = {
            "operation": operation,
            "retrieval_executed": False,
            "profiles": len(PROFILES),
            "protocol_created": operation in {"created", "unchanged"},
        }
    elif arguments.freeze_pack:
        output = {"operation": freeze_pack(root), "retrieval_executed": False, "cases": 32}
    elif arguments.collect:
        raw, operation = collect(root)
        output = {"operation": operation, "retrieval_calls": raw["retrieval_calls"]}
    elif arguments.score:
        report, operation = write_selection(root)
        output = {"operation": operation, "winner": report["winner"]}
    else:
        report = check(root)
        output = {
            "operation": "valid",
            "status": report["status"],
            "winner": report.get("winner"),
        }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
