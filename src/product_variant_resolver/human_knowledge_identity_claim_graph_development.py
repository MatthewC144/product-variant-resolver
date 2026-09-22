"""Public candidate-independent identity-claim graph development primitives."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any

from .human_knowledge import HumanKnowledgeDocument
from .human_knowledge_admission_development import (
    CHARACTER_RRF_WEIGHT,
    CHARACTER_SCORE_FLOOR,
    CORPUS_INPUTS,
    DIMENSIONS,
    EXISTING_MANIFEST,
    EXISTING_PACK,
    _cases,
    _catalog,
    identity_token_coverage,
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
from .human_knowledge_identity import (
    NOISE,
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
)
from .human_knowledge_identity_contradiction_development import (
    PACK_DIRECTORY as HIC_PACK_DIRECTORY,
)
from .human_knowledge_identity_contradiction_development import (
    PROTOCOL_DIRECTORY as HIC_PROTOCOL_DIRECTORY,
)
from .human_knowledge_identity_contradiction_development import (
    RAW_DIRECTORY as HIC_RAW_DIRECTORY,
)
from .human_knowledge_identity_contradiction_development import SOURCE as HIC_SOURCE
from .human_knowledge_identity_contradiction_development import _candidate as _upstream_candidate
from .human_knowledge_identity_contradiction_development import (
    _summarize_new as _summarize_hic,
)
from .human_knowledge_identity_contradiction_development import (
    validate_pack as validate_hic_pack,
)
from .human_knowledge_identity_contradiction_development import (
    validate_raw as validate_hic_raw,
)
from .human_knowledge_identity_envelope_development import (
    REPORT_DIRECTORY as HIE_REPORT_DIRECTORY,
)
from .human_knowledge_identity_envelope_development import SOURCE as HIE_SOURCE
from .human_knowledge_reranker_development import (
    REPORT_DIRECTORY as UPSTREAM_REPORT_DIRECTORY,
)
from .human_knowledge_reranker_development import check as check_upstream
from .identity import normalize_text
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-identity-claim-graph-development-v3"
SOURCE = "src/product_variant_resolver/human_knowledge_identity_claim_graph_development.py"
CANDIDATE_LIMIT = 5
PACK_SCHEMA = "pvr-human-knowledge-identity-claim-graph-pack-v3"
PROTOCOL_SCHEMA = "pvr-human-knowledge-identity-claim-graph-protocol-v3"
RAW_SCHEMA = "pvr-human-knowledge-identity-claim-graph-raw-v3"
REPORT_SCHEMA = "pvr-human-knowledge-identity-claim-graph-selection-v3"
CALIBRATION_SCHEMA = "pvr-human-knowledge-identity-claim-graph-calibration-v3"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
PROTOCOL_DIRECTORY = DATA_DIRECTORY / "protocol"
PACK_DIRECTORY = DATA_DIRECTORY / "pack"
RAW_DIRECTORY = DATA_DIRECTORY / "raw"
REPORT_DIRECTORY = Path("reports") / VERSION
CALIBRATION_JSON = "historical-calibration.json"
CALIBRATION_MARKDOWN = "historical-calibration.md"
CALIBRATION_MANIFEST = "historical-calibration-manifest.json"
SELECTION_JSON = "selection.json"
SELECTION_MARKDOWN = "selection.md"
DECLARATIONS_PATH = (
    Path("specs/human-knowledge-identity-claim-graph-development")
    / "holdout-negative-declarations.json"
)
UPSTREAM_FIXED_HASHES = {
    HIC_SOURCE: "167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f",
    HIE_SOURCE: "c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e",
    str(HIE_REPORT_DIRECTORY / CALIBRATION_JSON): (
        "fbdc5171f3b1bfbe3f07b207acb56bd9608e2a3136bdff1acb9175e99f1557ce"
    ),
    str(HIE_REPORT_DIRECTORY / CALIBRATION_MANIFEST): (
        "03eee815b2cb4110e158f2ff02bf51d8b582282c1f050358c3be117ee238eeb5"
    ),
    str(HIE_REPORT_DIRECTORY / CALIBRATION_MARKDOWN): (
        "7e0fbd7e1f92cf0d043949e0c0fdee69bd4d53f0a9f40fe1a41d466f6b5039be"
    ),
}
CONTEXT_EXTENSION = frozenset(
    {
        "lineage",
        "listing",
        "matchbox",
        "mile",
        "preowned",
        "quarter",
        "racers",
        "sale",
        "street",
        "unboxed",
        "unclear",
        "warehouse",
        "without",
    }
)
CONTEXT_TOKENS = NOISE | CONTEXT_EXTENSION
RELATIONS = frozenset(
    {
        "exact",
        "compact_exact",
        "unique_prefix_abbreviation",
        "unique_alpha_edit_1",
        "leading_year_suffix",
        "ocr_o_zero",
        "ocr_repeated_digit_restore",
        "leading_year_uncertainty_x",
    }
)
ATOM_ROLES = frozenset(
    {
        "identity_anchor",
        "identity_model",
        "numeric_frame",
        "context",
        "unresolved_discriminative",
    }
)
FRAME_KINDS = frozenset({"leading_year", "standalone_model", "alphanumeric_model", "compact_model"})
SECONDARY_THRESHOLD = 0.75
POLICIES = (
    "reference-anchor",
    "claim-conflict-veto",
    "claim-bilateral",
    "claim-query-conservation",
    "claim-decision-list",
)
NON_REFERENCE_POLICIES = POLICIES[1:]
POLICY_PREFERENCE = {
    "claim-conflict-veto": 0,
    "claim-bilateral": 1,
    "claim-query-conservation": 2,
    "claim-decision-list": 3,
    "reference-anchor": 4,
}
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
    "graph_errors": 0,
    "alignment_errors": 0,
    "decision_errors": 0,
}
KNOWN_SECONDARY_CONFLICTS = {
    "anchor-neg-07-nissan-r32": (
        "human-hot-wheels-nissan-skyline-gtr-bnr34-mainline-blue-2026-k-case"
    ),
    "hic-neg-04-nissan-r33": (
        "human-hot-wheels-nissan-skyline-gtr-bnr34-mainline-blue-2026-k-case"
    ),
}
ANCHOR_RELATIONS = frozenset(
    {"exact", "alias_equivalent", "bounded_equivalent", "different", "unavailable"}
)
NUMERIC_RELATIONS = frozenset(
    {"none", "equal", "year_suffix", "ocr_equivalent", "conflict", "query_only", "candidate_only"}
)
CONTEXT_RELATIONS = frozenset({"separated", "none"})
RESIDUAL_STATES = frozenset({"none", "present"})
FORM_COMPLETIONS = frozenset({"complete", "partial"})
HARD_CONFLICT_STATES = frozenset({"pass", "fail"})
DECISIONS = frozenset({"admit", "abstain"})
REASON_CODES = frozenset(
    {
        "reference_rank_1",
        "hard_numeric_model_conflict",
        "anchor_mismatch",
        "bilateral_claim_residual",
        "query_claim_not_conserved",
        "complete_claim_form",
        "unique_bounded_claim_form",
        "ambiguous_claim_form",
        "structurally_compatible",
        "secondary_coverage_at_least_075",
        "secondary_coverage_below_075",
    }
)


@dataclass(frozen=True, slots=True)
class PublicIdentityForm:
    normalized: str
    kind: str
    atoms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _RawToken:
    text: str
    raw_text: str
    start: int
    end: int
    raw_start: int
    raw_end: int
    token_index: int


@dataclass(frozen=True, slots=True)
class _WorkingAtom:
    text: str
    source_token: str
    raw_source_token: str
    start: int
    end: int
    raw_start: int
    raw_end: int
    source_token_index: int
    segment_index: int
    segment_count: int


@dataclass(frozen=True, slots=True)
class AtomRelation:
    query_atom_index: int
    form_atom_index: int
    relation: str
    query_atom: str
    form_atom: str


@dataclass(frozen=True, slots=True)
class IdentityHypothesis:
    status: str
    public_form: str | None
    public_form_kind: str | None
    relations: tuple[AtomRelation, ...]


@dataclass(frozen=True, slots=True)
class ClaimAtom:
    text: str
    role: str
    relation: str | None
    public_form_atom: str | None
    start: int
    end: int
    raw_start: int
    raw_end: int
    source_token: str
    raw_source_token: str
    source_token_index: int
    segment_index: int
    segment_count: int


@dataclass(frozen=True, slots=True)
class ClaimFrame:
    frame_id: str
    kind: str
    atom_indices: tuple[int, ...]
    owner_before: str | None
    owner_after: str | None
    ordinal: int
    source_token: str
    alphabetic_skeleton: str
    digit_runs: tuple[str, ...]
    equivalence_rule: str | None


@dataclass(frozen=True, slots=True)
class ClaimEdge:
    source_atom_index: int
    target: str
    relation: str


@dataclass(frozen=True, slots=True)
class QueryClaimGraph:
    status: str
    normalized_query: str
    atoms: tuple[ClaimAtom, ...]
    frames: tuple[ClaimFrame, ...]
    edges: tuple[ClaimEdge, ...]
    hypothesis: IdentityHypothesis
    checksum: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "normalized_query": self.normalized_query,
            "atoms": [asdict(atom) for atom in self.atoms],
            "frames": [asdict(frame) for frame in self.frames],
            "edges": [asdict(edge) for edge in self.edges],
            "hypothesis": {
                "status": self.hypothesis.status,
                "public_form": self.hypothesis.public_form,
                "public_form_kind": self.hypothesis.public_form_kind,
                "relations": [asdict(relation) for relation in self.hypothesis.relations],
            },
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class CandidateFrame:
    frame_id: str
    kind: str
    atom_index: int
    owner_before: str | None
    owner_after: str | None
    ordinal: int
    source_token: str
    alphabetic_skeleton: str
    digit_runs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FrameComparison:
    query_frame_id: str | None
    candidate_frame_id: str | None
    relation: str
    query_source_token: str | None
    candidate_source_token: str | None
    query_digit_runs: tuple[str, ...]
    candidate_digit_runs: tuple[str, ...]
    owner_before: str | None
    owner_after: str | None


@dataclass(frozen=True, slots=True)
class CandidatePolicyInput:
    document: HumanKnowledgeDocument
    source_rank: int
    identity_token_coverage: float


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _checksum(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _form_atoms(text: str) -> tuple[str, ...]:
    return tuple(normalize_text(text).split())


def _raw_tokens(text: str) -> tuple[str, tuple[_RawToken, ...]]:
    normalized_source = unicodedata.normalize("NFKC", text)
    values: list[tuple[str, str, int, int]] = []
    for match in re.finditer(r"[\w]+", normalized_source, flags=re.UNICODE):
        normalized = normalize_text(match.group())
        for part in normalized.split():
            values.append((part, match.group(), match.start(), match.end()))
    normalized_query = " ".join(value[0] for value in values)
    result: list[_RawToken] = []
    cursor = 0
    for token_index, (token, raw_token, raw_start, raw_end) in enumerate(values):
        start = cursor
        end = start + len(token)
        result.append(
            _RawToken(
                text=token,
                raw_text=raw_token,
                start=start,
                end=end,
                raw_start=raw_start,
                raw_end=raw_end,
                token_index=token_index,
            )
        )
        cursor = end + 1
    return normalized_query, tuple(result)


def _has_letter(value: str) -> bool:
    return any(character.isalpha() for character in value)


def _has_digit(value: str) -> bool:
    return any(character.isdigit() for character in value)


def _alpha_skeleton(value: str) -> str:
    return "".join(character for character in value if character.isalpha())


def _digit_runs(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\d+", value))


def _one_alpha_edit(left: str, right: str) -> bool:
    if left == right or not left.isalpha() or not right.isalpha():
        return False
    if min(len(left), len(right)) < 4 or abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        differences = [index for index, pair in enumerate(zip(left, right)) if pair[0] != pair[1]]
        if len(differences) == 1:
            return True
        return bool(
            len(differences) == 2
            and differences[1] == differences[0] + 1
            and left[differences[0]] == right[differences[1]]
            and left[differences[1]] == right[differences[0]]
        )
    shorter, longer = sorted((left, right), key=len)
    for index in range(len(longer)):
        if longer[:index] + longer[index + 1 :] == shorter:
            return True
    return False


def _year_suffix(left: str, right: str) -> bool:
    shorter, longer = sorted((left, right), key=len)
    return bool(
        shorter.isdigit()
        and longer.isdigit()
        and len(shorter) == 2
        and len(longer) == 4
        and longer[:2] in {"19", "20"}
        and longer[-2:] == shorter
    )


def _ocr_o_zero(left: str, right: str) -> bool:
    if len(left) != len(right) or left == right:
        return False
    if not (_has_digit(left) or _has_digit(right)) or "o" not in left + right:
        return False
    return left.replace("o", "0") == right.replace("o", "0")


def _remove_one_repeated_digit(value: str) -> set[str]:
    results: set[str] = set()
    for index, character in enumerate(value):
        if not character.isdigit():
            continue
        previous_same = index > 0 and value[index - 1] == character
        next_same = index + 1 < len(value) and value[index + 1] == character
        if previous_same or next_same:
            results.add(value[:index] + value[index + 1 :])
    return results


def _repeated_digit_restore(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) != 1 or _alpha_skeleton(left) != _alpha_skeleton(right):
        return False
    shorter, longer = sorted((left, right), key=len)
    return shorter in _remove_one_repeated_digit(longer)


def _base_relation(query: str, public: str) -> str | None:
    if query == public:
        return "exact"
    if _year_suffix(query, public):
        return "leading_year_suffix"
    uncertainty = re.fullmatch(r"(\d{2}|\d{4})x", query)
    if uncertainty and uncertainty.group(1) == public:
        return "leading_year_uncertainty_x"
    if _ocr_o_zero(query, public):
        return "ocr_o_zero"
    if _repeated_digit_restore(query, public):
        return "ocr_repeated_digit_restore"
    if (
        query.isalpha()
        and public.isalpha()
        and len(query) >= 2
        and len(public) >= 5
        and public.startswith(query)
    ):
        return "unique_prefix_abbreviation"
    if _one_alpha_edit(query, public):
        return "unique_alpha_edit_1"
    return None


class IdentityClaimGrammar:
    """Build one query claim graph from the whole public identity corpus."""

    def __init__(self, documents: tuple[HumanKnowledgeDocument, ...]) -> None:
        if not documents:
            raise ValueError("identity claim grammar requires public documents")
        if len({document.knowledge_id for document in documents}) != len(documents):
            raise ValueError("identity claim grammar requires unique knowledge IDs")
        if len({document.knowledge_uuid for document in documents}) != len(documents):
            raise ValueError("identity claim grammar requires unique knowledge UUIDs")

        forms_by_text: dict[str, PublicIdentityForm] = {}
        for document in documents:
            for identity_index, identity in enumerate(document.character_identity_texts):
                normalized = normalize_text(identity)
                atoms = _form_atoms(identity)
                if not normalized or not atoms:
                    raise ValueError("public identity form must contain normalized atoms")
                kind = "casting" if identity_index == 0 else "alias"
                current = forms_by_text.get(normalized)
                if current is None or (current.kind == "alias" and kind == "casting"):
                    forms_by_text[normalized] = PublicIdentityForm(normalized, kind, atoms)
        self.forms = tuple(forms_by_text[key] for key in sorted(forms_by_text))
        if not self.forms:
            raise ValueError("identity claim grammar has no public forms")

        identity_atoms = {atom for form in self.forms for atom in form.atoms}
        self.identity_atoms = frozenset(identity_atoms)
        self.segment_terms = frozenset(
            term
            for term in identity_atoms | set(CONTEXT_TOKENS)
            if term.isdigit() or len(term) >= 2
        )
        frequencies = Counter(atom for form in self.forms for atom in set(form.atoms))
        self.atom_idf = {
            atom: math.log((len(self.forms) + 1) / (frequency + 1)) + 1
            for atom, frequency in frequencies.items()
        }
        self.maximum_idf = math.log(len(self.forms) + 1) + 1

    def _weight(self, atom: str) -> float:
        return self.atom_idf.get(atom, self.maximum_idf) / self.maximum_idf

    def _segment(self, token: str) -> tuple[str, ...]:
        if token in self.identity_atoms or token in CONTEXT_TOKENS:
            return (token,)

        @cache
        def solve(position: int) -> tuple[tuple[str, ...], ...]:
            if position == len(token):
                return ((),)
            candidates: list[tuple[str, ...]] = []
            for term in self.segment_terms:
                if not token.startswith(term, position):
                    continue
                for suffix in solve(position + len(term)):
                    candidates.append((term, *suffix))
            return tuple(candidates)

        candidates = tuple(value for value in solve(0) if len(value) > 1)
        if not candidates:
            return (token,)

        def numeric_key(value: tuple[str, ...]) -> tuple[int, int, int, int]:
            identity_count = sum(term in self.identity_atoms for term in value)
            digit_count = sum(_has_digit(term) for term in value)
            return identity_count, digit_count, sum(map(len, value)), -len(value)

        best_key = max(numeric_key(value) for value in candidates)
        return min(value for value in candidates if numeric_key(value) == best_key)

    def _atoms(self, query_text: str) -> tuple[str, tuple[_WorkingAtom, ...]]:
        normalized, tokens = _raw_tokens(query_text)
        atoms: list[_WorkingAtom] = []
        for token in tokens:
            segments = self._segment(token.text)
            relative = 0
            for segment_index, segment in enumerate(segments):
                segment_start = token.start + relative
                atoms.append(
                    _WorkingAtom(
                        text=segment,
                        source_token=token.text,
                        raw_source_token=token.raw_text,
                        start=segment_start,
                        end=segment_start + len(segment),
                        raw_start=token.raw_start,
                        raw_end=token.raw_end,
                        source_token_index=token.token_index,
                        segment_index=segment_index,
                        segment_count=len(segments),
                    )
                )
                relative += len(segment)
        return normalized, tuple(atoms)

    def _alignment_key(
        self,
        relations: tuple[AtomRelation, ...],
        query_atoms: tuple[_WorkingAtom, ...],
    ) -> tuple[int, int, int, float, int, int]:
        exact = sum(relation.relation in {"exact", "compact_exact"} for relation in relations)
        numeric = sum(_has_digit(relation.query_atom) for relation in relations)
        weight = sum(self._weight(relation.form_atom) for relation in relations)
        nonexact = len(relations) - exact
        later_start = min(
            (query_atoms[relation.query_atom_index].source_token_index for relation in relations),
            default=-1,
        )
        return exact, numeric, len(relations), weight, -nonexact, later_start

    def _align(
        self, query_atoms: tuple[_WorkingAtom, ...], form: PublicIdentityForm
    ) -> tuple[AtomRelation, ...]:
        @cache
        def solve(query_position: int, form_position: int) -> tuple[AtomRelation, ...]:
            if query_position >= len(query_atoms) or form_position >= len(form.atoms):
                return ()
            options = [
                solve(query_position + 1, form_position),
                solve(query_position, form_position + 1),
            ]
            relation = _base_relation(query_atoms[query_position].text, form.atoms[form_position])
            if relation is not None:
                if relation == "exact" and query_atoms[query_position].segment_count > 1:
                    relation = "compact_exact"
                options.append(
                    (
                        AtomRelation(
                            query_position,
                            form_position,
                            relation,
                            query_atoms[query_position].text,
                            form.atoms[form_position],
                        ),
                        *solve(query_position + 1, form_position + 1),
                    )
                )
            return max(options, key=lambda value: self._alignment_key(value, query_atoms))

        return solve(0, 0)

    def _bounded_relations_are_unique(self, relations: tuple[AtomRelation, ...]) -> bool:
        bounded = tuple(
            relation
            for relation in relations
            if relation.relation in {"unique_prefix_abbreviation", "unique_alpha_edit_1"}
        )
        if not bounded:
            return True
        support = {
            relation.form_atom
            for relation in relations
            if relation.relation in {"exact", "compact_exact"}
        }
        if not support:
            return False
        for relation in bounded:
            expansions: set[str] = set()
            for form in self.forms:
                if not support.issubset(form.atoms):
                    continue
                for atom in form.atoms:
                    if _base_relation(relation.query_atom, atom) == relation.relation:
                        expansions.add(atom)
            if expansions != {relation.form_atom}:
                return False
        return True

    def _hypothesis(self, query_atoms: tuple[_WorkingAtom, ...]) -> IdentityHypothesis:
        choices: list[
            tuple[
                tuple[int, int, int, float, int, int, int],
                PublicIdentityForm,
                tuple[AtomRelation, ...],
            ]
        ] = []
        for form in self.forms:
            relations = self._align(query_atoms, form)
            if not relations or not self._bounded_relations_are_unique(relations):
                continue
            key = (*self._alignment_key(relations, query_atoms), len(form.atoms))
            choices.append((key, form, relations))
        if not choices:
            return IdentityHypothesis("unanchored", None, None, ())
        best_key = max(choice[0] for choice in choices)
        _, form, relations = min(
            (choice for choice in choices if choice[0] == best_key),
            key=lambda choice: choice[1].normalized,
        )
        return IdentityHypothesis("anchored", form.normalized, form.kind, relations)

    def _claim_atoms(
        self,
        working: tuple[_WorkingAtom, ...],
        hypothesis: IdentityHypothesis,
    ) -> tuple[ClaimAtom, ...]:
        matched = {relation.query_atom_index: relation for relation in hypothesis.relations}
        first_alphabetic = next(
            (
                index
                for index in sorted(matched)
                if _has_letter(working[index].text) and not _has_digit(working[index].text)
            ),
            None,
        )
        atoms: list[ClaimAtom] = []
        for index, atom in enumerate(working):
            relation = matched.get(index)
            if relation is not None and _has_digit(atom.text):
                role = "numeric_frame"
            elif relation is not None and index == first_alphabetic:
                role = "identity_anchor"
            elif relation is not None:
                role = "identity_model"
            elif atom.text in CONTEXT_TOKENS:
                role = "context"
            else:
                role = "unresolved_discriminative"
            atoms.append(
                ClaimAtom(
                    text=atom.text,
                    role=role,
                    relation=None if relation is None else relation.relation,
                    public_form_atom=None if relation is None else relation.form_atom,
                    start=atom.start,
                    end=atom.end,
                    raw_start=atom.raw_start,
                    raw_end=atom.raw_end,
                    source_token=atom.source_token,
                    raw_source_token=atom.raw_source_token,
                    source_token_index=atom.source_token_index,
                    segment_index=atom.segment_index,
                    segment_count=atom.segment_count,
                )
            )
        if any(atom.role not in ATOM_ROLES for atom in atoms):
            raise ValueError("query atom role differs from claim-graph contract")
        return tuple(atoms)

    def _frames(self, atoms: tuple[ClaimAtom, ...]) -> tuple[ClaimFrame, ...]:
        identity_indices = tuple(
            index
            for index, atom in enumerate(atoms)
            if atom.role in {"identity_anchor", "identity_model"}
        )
        first_identity = identity_indices[0] if identity_indices else None
        frames: list[ClaimFrame] = []
        for atom_index, atom in enumerate(atoms):
            digits = _digit_runs(atom.text)
            uncertainty = re.fullmatch(r"(\d{2}|\d{4})x", atom.text)
            if uncertainty:
                digits = (uncertainty.group(1),)
            if not digits:
                continue
            before = next(
                (
                    atoms[index].public_form_atom or atoms[index].text
                    for index in reversed(identity_indices)
                    if index < atom_index
                ),
                None,
            )
            after = next(
                (
                    atoms[index].public_form_atom or atoms[index].text
                    for index in identity_indices
                    if index > atom_index
                ),
                None,
            )
            if (
                first_identity is not None
                and atom_index < first_identity
                and len(digits) == 1
                and len(digits[0]) in {2, 4}
            ):
                kind = "leading_year"
            elif atom.segment_count > 1:
                kind = "compact_model"
            elif atom.text.isdigit():
                kind = "standalone_model"
            else:
                kind = "alphanumeric_model"
            rule = atom.relation if atom.relation not in {None, "exact", "compact_exact"} else None
            frame_id = f"frame-{len(frames)}"
            frames.append(
                ClaimFrame(
                    frame_id=frame_id,
                    kind=kind,
                    atom_indices=(atom_index,),
                    owner_before=before,
                    owner_after=after,
                    ordinal=len(frames),
                    source_token=atom.source_token,
                    alphabetic_skeleton=_alpha_skeleton(atom.text),
                    digit_runs=digits,
                    equivalence_rule=rule,
                )
            )
        if any(frame.kind not in FRAME_KINDS for frame in frames):
            raise ValueError("query frame kind differs from claim-graph contract")
        return tuple(frames)

    @staticmethod
    def _edges(
        atoms: tuple[ClaimAtom, ...], frames: tuple[ClaimFrame, ...]
    ) -> tuple[ClaimEdge, ...]:
        edges = [
            ClaimEdge(index, f"atom-{index + 1}", "ordered_before")
            for index in range(len(atoms) - 1)
        ]
        anchor = next(
            (index for index, atom in enumerate(atoms) if atom.role == "identity_anchor"),
            None,
        )
        for frame in frames:
            atom_index = frame.atom_indices[0]
            edges.append(ClaimEdge(atom_index, frame.frame_id, "belongs_to_frame"))
            slot = f"slot:{frame.owner_before or '^'}:{frame.owner_after or '$'}:{frame.ordinal}"
            edges.append(ClaimEdge(atom_index, slot, "same_identity_slot"))
            if frame.kind == "leading_year" and anchor is not None:
                edges.append(ClaimEdge(atom_index, f"atom-{anchor}", "modifies_anchor"))
        return tuple(edges)

    def graph(self, query_text: str) -> QueryClaimGraph:
        normalized_query, working = self._atoms(query_text)
        if not working:
            raise ValueError("query has no normalized atoms")
        hypothesis = self._hypothesis(working)
        atoms = self._claim_atoms(working, hypothesis)
        frames = self._frames(atoms)
        edges = self._edges(atoms, frames)
        payload = {
            "status": hypothesis.status,
            "normalized_query": normalized_query,
            "atoms": [asdict(atom) for atom in atoms],
            "frames": [asdict(frame) for frame in frames],
            "edges": [asdict(edge) for edge in edges],
            "hypothesis": {
                "status": hypothesis.status,
                "public_form": hypothesis.public_form,
                "public_form_kind": hypothesis.public_form_kind,
                "relations": [asdict(relation) for relation in hypothesis.relations],
            },
        }
        graph = QueryClaimGraph(
            status=hypothesis.status,
            normalized_query=normalized_query,
            atoms=atoms,
            frames=frames,
            edges=edges,
            hypothesis=hypothesis,
            checksum=_checksum(payload),
        )
        if (
            _checksum({key: value for key, value in graph.as_dict().items() if key != "checksum"})
            != graph.checksum
        ):
            raise ValueError("query claim graph checksum is not reproducible")
        return graph


def _identity_atoms(grammar: IdentityClaimGrammar, identity: str) -> tuple[str, ...]:
    atoms: list[str] = []
    for token in normalize_text(identity).split():
        atoms.extend(grammar._segment(token))
    if not atoms:
        raise ValueError("candidate identity form has no normalized atoms")
    return tuple(atoms)


def _candidate_frames(atoms: tuple[str, ...]) -> tuple[CandidateFrame, ...]:
    identity_indices = tuple(index for index, atom in enumerate(atoms) if _has_letter(atom))
    first_identity = identity_indices[0] if identity_indices else None
    frames: list[CandidateFrame] = []
    for atom_index, atom in enumerate(atoms):
        digits = _digit_runs(atom)
        if not digits:
            continue
        before = next(
            (atoms[index] for index in reversed(identity_indices) if index < atom_index),
            None,
        )
        after = next((atoms[index] for index in identity_indices if index > atom_index), None)
        if (
            first_identity is not None
            and atom_index < first_identity
            and len(digits) == 1
            and len(digits[0]) in {2, 4}
        ):
            kind = "leading_year"
        elif atom.isdigit():
            kind = "standalone_model"
        else:
            kind = "alphanumeric_model"
        frames.append(
            CandidateFrame(
                frame_id=f"candidate-frame-{len(frames)}",
                kind=kind,
                atom_index=atom_index,
                owner_before=before,
                owner_after=after,
                ordinal=len(frames),
                source_token=atom,
                alphabetic_skeleton=_alpha_skeleton(atom),
                digit_runs=digits,
            )
        )
    return tuple(frames)


def _frames_are_comparable(query: ClaimFrame, candidate: CandidateFrame) -> bool:
    if query.kind == "leading_year" or candidate.kind == "leading_year":
        return query.kind == candidate.kind and query.owner_after == candidate.owner_after
    return bool(
        (query.owner_before is not None or query.owner_after is not None)
        and query.owner_before == candidate.owner_before
        and query.owner_after == candidate.owner_after
    )


def _frame_relation(query: ClaimFrame, candidate: CandidateFrame) -> str:
    relation = _base_relation(query.source_token, candidate.source_token)
    if relation == "leading_year_uncertainty_x" and query.kind == candidate.kind == "leading_year":
        return "year_suffix"
    if query.digit_runs == candidate.digit_runs:
        return "equal"
    if relation == "leading_year_suffix" and query.kind == candidate.kind == "leading_year":
        return "year_suffix"
    if relation in {"ocr_o_zero", "ocr_repeated_digit_restore"}:
        return "ocr_equivalent"
    return "conflict"


def _compare_frames(
    query_frames: tuple[ClaimFrame, ...], candidate_frames: tuple[CandidateFrame, ...]
) -> tuple[FrameComparison, ...]:
    comparisons: list[FrameComparison] = []
    used_candidates: set[int] = set()
    for query in query_frames:
        matches = tuple(
            (index, candidate)
            for index, candidate in enumerate(candidate_frames)
            if index not in used_candidates and _frames_are_comparable(query, candidate)
        )
        if not matches:
            comparisons.append(
                FrameComparison(
                    query.frame_id,
                    None,
                    "query_only",
                    query.source_token,
                    None,
                    query.digit_runs,
                    (),
                    query.owner_before,
                    query.owner_after,
                )
            )
            continue
        candidate_index, candidate = min(
            matches,
            key=lambda item: (
                item[1].kind != query.kind,
                abs(item[1].ordinal - query.ordinal),
                item[1].frame_id,
            ),
        )
        used_candidates.add(candidate_index)
        comparisons.append(
            FrameComparison(
                query.frame_id,
                candidate.frame_id,
                _frame_relation(query, candidate),
                query.source_token,
                candidate.source_token,
                query.digit_runs,
                candidate.digit_runs,
                query.owner_before,
                query.owner_after,
            )
        )
    for candidate_index, candidate in enumerate(candidate_frames):
        if candidate_index in used_candidates:
            continue
        comparisons.append(
            FrameComparison(
                None,
                candidate.frame_id,
                "candidate_only",
                None,
                candidate.source_token,
                (),
                candidate.digit_runs,
                candidate.owner_before,
                candidate.owner_after,
            )
        )
    return tuple(comparisons)


def _numeric_relation(comparisons: tuple[FrameComparison, ...]) -> str:
    relations = {comparison.relation for comparison in comparisons}
    if "conflict" in relations:
        return "conflict"
    if "ocr_equivalent" in relations:
        return "ocr_equivalent"
    if "year_suffix" in relations:
        return "year_suffix"
    if "query_only" in relations:
        return "query_only"
    if "candidate_only" in relations:
        return "candidate_only"
    if comparisons:
        return "equal"
    return "none"


def _claim_value(atom: ClaimAtom) -> str:
    return atom.public_form_atom or atom.text


def _candidate_alignment(
    graph: QueryClaimGraph,
    candidate_atoms: tuple[str, ...],
    grammar: IdentityClaimGrammar,
) -> tuple[AtomRelation, ...]:
    query_claims = tuple(
        (index, atom) for index, atom in enumerate(graph.atoms) if atom.role != "context"
    )

    def alignment_key(relations: tuple[AtomRelation, ...]) -> tuple[int, int, float, int]:
        exact = sum(relation.relation in {"exact", "compact_exact"} for relation in relations)
        weight = sum(grammar._weight(relation.form_atom) for relation in relations)
        return (
            len(relations),
            exact,
            weight,
            -sum(relation.relation not in {"exact", "compact_exact"} for relation in relations),
        )

    @cache
    def solve(query_position: int, candidate_position: int) -> tuple[AtomRelation, ...]:
        if query_position >= len(query_claims) or candidate_position >= len(candidate_atoms):
            return ()
        options = [
            solve(query_position + 1, candidate_position),
            solve(query_position, candidate_position + 1),
        ]
        graph_index, query_atom = query_claims[query_position]
        query_value = _claim_value(query_atom)
        relation = _base_relation(query_value, candidate_atoms[candidate_position])
        if relation in {
            "exact",
            "leading_year_suffix",
            "ocr_o_zero",
            "ocr_repeated_digit_restore",
            "leading_year_uncertainty_x",
        }:
            options.append(
                (
                    AtomRelation(
                        graph_index,
                        candidate_position,
                        relation,
                        query_atom.text,
                        candidate_atoms[candidate_position],
                    ),
                    *solve(query_position + 1, candidate_position + 1),
                )
            )
        return max(options, key=alignment_key)

    return solve(0, 0)


def _form_evidence(
    graph: QueryClaimGraph,
    identity: str,
    identity_kind: str,
    grammar: IdentityClaimGrammar,
) -> dict[str, Any]:
    candidate_atoms = _identity_atoms(grammar, identity)
    alignments = _candidate_alignment(graph, candidate_atoms, grammar)
    matched_query = {alignment.query_atom_index for alignment in alignments}
    matched_candidate = {alignment.form_atom_index for alignment in alignments}
    query_claim_indices = {
        index for index, atom in enumerate(graph.atoms) if atom.role != "context"
    }
    unmatched_query = tuple(
        asdict(graph.atoms[index]) for index in sorted(query_claim_indices - matched_query)
    )
    unmatched_candidate = tuple(
        candidate_atoms[index]
        for index in range(len(candidate_atoms))
        if index not in matched_candidate
    )
    anchor_index = next(
        (index for index, atom in enumerate(graph.atoms) if atom.role == "identity_anchor"),
        None,
    )
    anchor_alignment = next(
        (alignment for alignment in alignments if alignment.query_atom_index == anchor_index),
        None,
    )
    if graph.status == "unanchored" or anchor_index is None:
        anchor_relation = "unavailable"
    elif anchor_alignment is None:
        anchor_relation = "different"
    elif identity_kind == "alias":
        anchor_relation = "alias_equivalent"
    elif graph.atoms[anchor_index].relation in {
        "unique_prefix_abbreviation",
        "unique_alpha_edit_1",
    }:
        anchor_relation = "bounded_equivalent"
    else:
        anchor_relation = "exact"
    candidate_frames = _candidate_frames(candidate_atoms)
    frame_comparisons = _compare_frames(graph.frames, candidate_frames)
    numeric_relation = _numeric_relation(frame_comparisons)
    query_residual = "present" if unmatched_query else "none"
    candidate_residual = "present" if unmatched_candidate else "none"
    completion = "complete" if query_residual == candidate_residual == "none" else "partial"
    return {
        "candidate_identity": normalize_text(identity),
        "candidate_identity_kind": identity_kind,
        "candidate_atoms": list(candidate_atoms),
        "candidate_frames": [asdict(frame) for frame in candidate_frames],
        "alignments": [asdict(alignment) for alignment in alignments],
        "frame_comparisons": [asdict(comparison) for comparison in frame_comparisons],
        "anchor_relation": anchor_relation,
        "numeric_relation": numeric_relation,
        "query_claim_residual": query_residual,
        "candidate_claim_residual": candidate_residual,
        "form_completion": completion,
        "unmatched_query_claims": list(unmatched_query),
        "unmatched_candidate_atoms": list(unmatched_candidate),
    }


def _form_choice_key(evidence: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        evidence["numeric_relation"] != "conflict",
        evidence["anchor_relation"] != "different",
        evidence["form_completion"] == "complete",
        -len(evidence["unmatched_query_claims"]),
        -len(evidence["unmatched_candidate_atoms"]),
    )


def candidate_claim_evidence(
    graph: QueryClaimGraph,
    document: HumanKnowledgeDocument,
    grammar: IdentityClaimGrammar,
    *,
    source_rank: int,
) -> dict[str, Any]:
    """Compare a candidate with one immutable graph without changing the graph."""

    if source_rank not in range(1, 6):
        raise ValueError("candidate source rank must be between one and five")
    before = graph.as_dict()
    identities = tuple(dict.fromkeys(document.character_identity_texts))
    if not identities or normalize_text(identities[0]) != normalize_text(document.casting):
        raise ValueError("candidate primary identity must be its casting")
    form_evidence = tuple(
        _form_evidence(graph, identity, "casting" if index == 0 else "alias", grammar)
        for index, identity in enumerate(identities)
    )
    primary = form_evidence[0]
    best_form_key = max(_form_choice_key(value) for value in form_evidence)
    selected = min(
        (value for value in form_evidence if _form_choice_key(value) == best_form_key),
        key=lambda value: value["candidate_identity"],
    )
    hard_conflict = "fail" if primary["numeric_relation"] == "conflict" else "pass"
    evidence = {
        "query_graph": graph.as_dict(),
        "candidate_identity": selected["candidate_identity"],
        "candidate_identity_kind": selected["candidate_identity_kind"],
        "primary_casting_identity": primary["candidate_identity"],
        "primary_numeric_relation": primary["numeric_relation"],
        "primary_frame_comparisons": primary["frame_comparisons"],
        "approved_form_evidence": list(form_evidence),
        "alignments": selected["alignments"],
        "candidate_frames": selected["candidate_frames"],
        "frame_comparisons": selected["frame_comparisons"],
        "graph_status": graph.status,
        "anchor_relation": selected["anchor_relation"],
        "numeric_relation": selected["numeric_relation"],
        "context_relation": (
            "separated" if any(atom.role == "context" for atom in graph.atoms) else "none"
        ),
        "query_claim_residual": selected["query_claim_residual"],
        "candidate_claim_residual": selected["candidate_claim_residual"],
        "form_completion": selected["form_completion"],
        "hard_conflict": hard_conflict,
        "source_rank": source_rank,
        "unmatched_query_claims": selected["unmatched_query_claims"],
        "unmatched_candidate_atoms": selected["unmatched_candidate_atoms"],
    }
    validate_candidate_evidence(evidence, graph.checksum)
    if graph.as_dict() != before:
        raise ValueError("candidate comparison changed the immutable query graph")
    return evidence


def validate_candidate_evidence(evidence: dict[str, Any], graph_checksum: str) -> None:
    if evidence.get("query_graph", {}).get("checksum") != graph_checksum:
        raise ValueError("candidate evidence uses a different query graph")
    if evidence.get("graph_status") not in {"anchored", "unanchored"}:
        raise ValueError("candidate evidence has an unknown graph state")
    if evidence.get("anchor_relation") not in ANCHOR_RELATIONS:
        raise ValueError("candidate evidence has an unknown anchor relation")
    if evidence.get("numeric_relation") not in NUMERIC_RELATIONS:
        raise ValueError("candidate evidence has an unknown numeric relation")
    if evidence.get("primary_numeric_relation") not in NUMERIC_RELATIONS:
        raise ValueError("candidate evidence has an unknown primary numeric relation")
    if evidence.get("context_relation") not in CONTEXT_RELATIONS:
        raise ValueError("candidate evidence has an unknown context relation")
    if (
        evidence.get("query_claim_residual") not in RESIDUAL_STATES
        or evidence.get("candidate_claim_residual") not in RESIDUAL_STATES
    ):
        raise ValueError("candidate evidence has an unknown residual state")
    if evidence.get("form_completion") not in FORM_COMPLETIONS:
        raise ValueError("candidate evidence has an unknown form completion")
    if evidence.get("hard_conflict") not in HARD_CONFLICT_STATES:
        raise ValueError("candidate evidence has an unknown hard-conflict state")
    if evidence.get("source_rank") not in range(1, 6):
        raise ValueError("candidate evidence has an invalid source rank")
    for comparison in (
        *evidence.get("primary_frame_comparisons", []),
        *evidence.get("frame_comparisons", []),
    ):
        if comparison.get("relation") not in NUMERIC_RELATIONS - {"none"}:
            raise ValueError("candidate evidence has an unknown frame relation")


def policy_definitions() -> tuple[dict[str, Any], ...]:
    return (
        {
            "configuration_id": "reference-anchor",
            "eligible_as_survivor": False,
            "ordered_rules": ["rank_1_admit", "secondary_coverage_075"],
        },
        {
            "configuration_id": "claim-conflict-veto",
            "eligible_as_survivor": True,
            "ordered_rules": ["all_rank_hard_conflict_veto", "rank_policy"],
        },
        {
            "configuration_id": "claim-bilateral",
            "eligible_as_survivor": True,
            "ordered_rules": [
                "all_rank_hard_conflict_veto",
                "reject_anchor_mismatch",
                "reject_bilateral_residual",
                "rank_policy",
            ],
        },
        {
            "configuration_id": "claim-query-conservation",
            "eligible_as_survivor": True,
            "ordered_rules": [
                "all_rank_hard_conflict_veto",
                "reject_anchor_mismatch",
                "reject_bilateral_residual",
                "reject_unconserved_query_claim",
                "rank_policy",
            ],
        },
        {
            "configuration_id": "claim-decision-list",
            "eligible_as_survivor": True,
            "ordered_rules": [
                "all_rank_hard_conflict_veto",
                "admit_complete_claim_form",
                "reject_anchor_mismatch",
                "admit_unique_bounded_claim_form",
                "otherwise_abstain",
                "rank_policy",
            ],
        },
    )


def candidate_decision(
    evidence: dict[str, Any],
    configuration_id: str,
    *,
    identity_token_coverage: float,
) -> tuple[str, tuple[str, ...]]:
    if configuration_id not in POLICIES:
        raise ValueError("unknown identity-claim configuration")
    if (
        type(identity_token_coverage) not in {int, float}
        or not math.isfinite(identity_token_coverage)
        or not 0 <= identity_token_coverage <= 1
    ):
        raise ValueError("identity token coverage must be finite and between zero and one")
    graph_checksum = evidence.get("query_graph", {}).get("checksum")
    if not isinstance(graph_checksum, str):
        raise TypeError("candidate evidence has no query graph checksum")
    validate_candidate_evidence(evidence, graph_checksum)
    rank = evidence["source_rank"]

    if configuration_id == "reference-anchor":
        if rank == 1:
            return "admit", ("reference_rank_1",)
        if identity_token_coverage + 1e-12 >= SECONDARY_THRESHOLD:
            return "admit", ("secondary_coverage_at_least_075",)
        return "abstain", ("secondary_coverage_below_075",)

    if evidence["hard_conflict"] == "fail":
        return "abstain", ("hard_numeric_model_conflict",)

    reasons: list[str] = []
    if (
        configuration_id
        in {
            "claim-bilateral",
            "claim-query-conservation",
            "claim-decision-list",
        }
        and evidence["anchor_relation"] == "different"
    ):
        return "abstain", ("anchor_mismatch",)

    bilateral = (
        evidence["query_claim_residual"] == "present"
        and evidence["candidate_claim_residual"] == "present"
    )
    if configuration_id in {"claim-bilateral", "claim-query-conservation"} and bilateral:
        return "abstain", ("bilateral_claim_residual",)

    if configuration_id == "claim-query-conservation" and (
        evidence["query_claim_residual"] == "present"
        or evidence["numeric_relation"] == "query_only"
    ):
        return "abstain", ("query_claim_not_conserved",)

    if configuration_id == "claim-decision-list":
        if evidence["form_completion"] == "complete":
            reasons.append("complete_claim_form")
        elif (
            evidence["anchor_relation"] == "bounded_equivalent"
            and evidence["query_claim_residual"] == "none"
            and evidence["candidate_claim_residual"] == "none"
        ):
            reasons.append("unique_bounded_claim_form")
        else:
            return "abstain", ("ambiguous_claim_form",)
    else:
        reasons.append("structurally_compatible")

    if rank != 1:
        if identity_token_coverage + 1e-12 < SECONDARY_THRESHOLD:
            return "abstain", (*reasons, "secondary_coverage_below_075")
        reasons.append("secondary_coverage_at_least_075")
    if any(reason not in REASON_CODES for reason in reasons):
        raise ValueError("candidate decision emitted an unknown reason code")
    return "admit", tuple(reasons)


def evaluate_candidates_in_source_order(
    graph: QueryClaimGraph,
    candidates: tuple[CandidatePolicyInput, ...],
    grammar: IdentityClaimGrammar,
    configuration_id: str,
) -> tuple[dict[str, Any], ...]:
    if tuple(candidate.source_rank for candidate in candidates) != tuple(
        sorted(candidate.source_rank for candidate in candidates)
    ):
        raise ValueError("candidate inputs must retain source-rank order")
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        evidence = candidate_claim_evidence(
            graph,
            candidate.document,
            grammar,
            source_rank=candidate.source_rank,
        )
        decision, reasons = candidate_decision(
            evidence,
            configuration_id,
            identity_token_coverage=candidate.identity_token_coverage,
        )
        results.append(
            {
                **evidence,
                "identity_token_coverage": candidate.identity_token_coverage,
                "decision": decision,
                "reason_codes": list(reasons),
            }
        )
    if any(result["decision"] not in DECISIONS for result in results):
        raise ValueError("candidate sequence emitted an unknown decision")
    return tuple(results)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required public input is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return value


def _assert_file(path: Path, content: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != content:
        raise ValueError(f"{path} differs from deterministic artifact")


def _freeze_directory(directory: Path, outputs: dict[str, str], label: str) -> str:
    if directory.exists():
        if not directory.is_dir() or {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError(f"{label} directory is partial or conflicting")
        for name, content in outputs.items():
            _assert_file(directory / name, content)
        return "unchanged"
    directory.mkdir(parents=True)
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
    current = {path.name for path in directory.iterdir()}
    allowed = {
        CALIBRATION_JSON,
        CALIBRATION_MANIFEST,
        CALIBRATION_MARKDOWN,
        SELECTION_JSON,
        SELECTION_MARKDOWN,
    }
    if not current <= allowed:
        raise ValueError(f"{label} directory contains conflicting files")
    existing = current & set(outputs)
    if existing and existing != set(outputs):
        raise ValueError(f"{label} files are partial")
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
        Path(HIC_SOURCE),
        Path(HIE_SOURCE),
        HIE_REPORT_DIRECTORY / CALIBRATION_JSON,
        HIE_REPORT_DIRECTORY / CALIBRATION_MANIFEST,
        HIE_REPORT_DIRECTORY / CALIBRATION_MARKDOWN,
    )


def verify_historical_inputs(root: Path) -> dict[str, str]:
    """Hash every public input and enforce the five immutable upstream bindings."""

    hashes = {str(path): _sha(root / path) for path in _historical_input_paths()}
    for name, expected in UPSTREAM_FIXED_HASHES.items():
        if hashes.get(name) != expected:
            raise ValueError(f"immutable upstream hash mismatch: {name}")
    hashes[SOURCE] = _sha(root / SOURCE)
    return dict(sorted(hashes.items()))


def _non_exact_equivalence_count(evidence: dict[str, Any]) -> int:
    return sum(
        alignment["relation"] not in {"exact", "compact_exact"}
        for alignment in evidence["alignments"]
    )


def apply_policy(
    rows: list[dict[str, Any]],
    documents: dict[str, HumanKnowledgeDocument],
    grammar: IdentityClaimGrammar,
    configuration_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Apply one frozen policy offline while preserving row and candidate order."""

    if configuration_id not in POLICIES:
        raise ValueError("unknown identity-claim configuration")
    filtered_rows: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    metrics = {
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
        "non_exact_equivalence_operations": 0,
        "retrieval_errors": 0,
        "graph_errors": 0,
        "alignment_errors": 0,
        "decision_errors": 0,
    }
    for row in rows:
        metrics["retrieval_errors"] += row.get("error") is not None
        source_candidates = row.get("candidates", [])[:CANDIDATE_LIMIT]
        ranks = tuple(candidate.get("source_rank") for candidate in source_candidates)
        if ranks != tuple(range(1, len(source_candidates) + 1)):
            raise ValueError("historical candidates differ from source-rank order")
        try:
            graph = grammar.graph(row["query_text"])
        except Exception as error:  # noqa: BLE001 - graph failures are failed gates
            metrics["source_candidates"] += len(source_candidates)
            metrics["abstained_candidates"] += len(source_candidates)
            metrics["graph_errors"] += 1
            filtered_rows.append({**row, "candidates": []})
            evaluations.append(
                {
                    "case_id": row["case_id"],
                    "query_graph": None,
                    "candidates": [],
                    "error": {"type": type(error).__name__, "message": str(error)},
                }
            )
            continue
        admitted_candidates: list[dict[str, Any]] = []
        candidate_results: list[dict[str, Any]] = []
        for candidate in source_candidates:
            metrics["source_candidates"] += 1
            document = documents.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("policy candidate is absent from public corpus")
            try:
                evidence = candidate_claim_evidence(
                    graph,
                    document,
                    grammar,
                    source_rank=candidate["source_rank"],
                )
            except Exception as error:  # noqa: BLE001 - alignment failures are failed gates
                metrics["alignment_errors"] += 1
                metrics["abstained_candidates"] += 1
                candidate_results.append(
                    {
                        "knowledge_id": candidate["knowledge_id"],
                        "knowledge_uuid": candidate["knowledge_uuid"],
                        "source_rank": candidate["source_rank"],
                        "query_graph": graph.as_dict(),
                        "reason_codes": [],
                        "decision": "abstain",
                        "error": {"type": type(error).__name__, "message": str(error)},
                    }
                )
                continue
            try:
                decision, reasons = candidate_decision(
                    evidence,
                    configuration_id,
                    identity_token_coverage=candidate["identity_token_coverage"],
                )
            except Exception as error:  # noqa: BLE001 - decision failures are failed gates
                metrics["decision_errors"] += 1
                metrics["abstained_candidates"] += 1
                candidate_results.append(
                    {
                        "knowledge_id": candidate["knowledge_id"],
                        "knowledge_uuid": candidate["knowledge_uuid"],
                        "source_rank": candidate["source_rank"],
                        **evidence,
                        "reason_codes": [],
                        "decision": "abstain",
                        "error": {"type": type(error).__name__, "message": str(error)},
                    }
                )
                continue
            result = {
                "knowledge_id": candidate["knowledge_id"],
                "knowledge_uuid": candidate["knowledge_uuid"],
                "source_rank": candidate["source_rank"],
                **evidence,
                "reason_codes": list(reasons),
                "decision": decision,
                "error": None,
            }
            if decision == "admit":
                admitted_candidates.append(candidate)
                metrics["admitted_candidates"] += 1
                metrics["non_exact_equivalence_operations"] += _non_exact_equivalence_count(
                    evidence
                )
            else:
                metrics["abstained_candidates"] += 1
            candidate_results.append(result)
        if any(result["query_graph"]["checksum"] != graph.checksum for result in candidate_results):
            raise ValueError("candidate evaluations disagree on immutable query graph")
        filtered_rows.append({**row, "candidates": admitted_candidates})
        evaluations.append(
            {
                "case_id": row["case_id"],
                "query_graph": graph.as_dict(),
                "candidates": candidate_results,
                "error": None,
            }
        )
    return filtered_rows, evaluations, metrics


def _known_secondary_conflicts_abstained(
    original_sets: tuple[list[dict[str, Any]], ...],
    filtered_sets: tuple[list[dict[str, Any]], ...],
) -> int:
    originals = {
        row["case_id"]: row
        for rows in original_sets
        for row in rows
        if row["case_id"] in KNOWN_SECONDARY_CONFLICTS
    }
    filtered = {
        row["case_id"]: row
        for rows in filtered_sets
        for row in rows
        if row["case_id"] in KNOWN_SECONDARY_CONFLICTS
    }
    if set(originals) != set(KNOWN_SECONDARY_CONFLICTS) or set(filtered) != set(
        KNOWN_SECONDARY_CONFLICTS
    ):
        raise ValueError("known secondary numeric-conflict rows are missing")
    abstained = 0
    for case_id, target_id in KNOWN_SECONDARY_CONFLICTS.items():
        source = [
            candidate
            for candidate in originals[case_id]["candidates"]
            if candidate["knowledge_id"] == target_id
        ]
        if len(source) != 1 or source[0]["source_rank"] == 1:
            raise ValueError("known numeric-conflict candidate differs from frozen evidence")
        admitted_ids = {candidate["knowledge_id"] for candidate in filtered[case_id]["candidates"]}
        abstained += target_id not in admitted_ids
    return abstained


def _gate(name: str, actual: int) -> dict[str, Any]:
    threshold = HISTORICAL_GATE_TARGETS[name]
    return {
        "name": name,
        "operator": "=",
        "threshold": threshold,
        "actual": actual,
        "passed": actual == threshold,
    }


def policy_selection_key(summary: dict[str, Any]) -> tuple[int, int, int, int]:
    metrics = summary["selection_metrics"]
    return (
        metrics["negative_admitted_candidates"],
        metrics["positive_abstained_candidates"],
        metrics["non_exact_equivalence_operations"],
        POLICY_PREFERENCE[summary["configuration_id"]],
    )


def historical_calibration(root: Path) -> dict[str, Any]:
    """Rescore the frozen 223 + 22 + 24 public rows without retrieval."""

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
    for configuration_id in POLICIES:
        filtered_existing, evaluations_existing, metrics_existing = apply_policy(
            historical_rows,
            documents,
            grammar,
            configuration_id,
        )
        existing = summarize_existing(cases, filtered_existing, 0.0)
        filtered_anchor, evaluations_anchor, metrics_anchor = apply_policy(
            anchor_rows,
            documents,
            grammar,
            configuration_id,
        )
        anchor = _score_anchor(anchor_pack, {**anchor_report["raw"], "rows": filtered_anchor}, 0.0)
        filtered_hic, evaluations_hic, metrics_hic = apply_policy(
            hic_rows,
            documents,
            grammar,
            configuration_id,
        )
        computation_errors = {
            name: sum(metrics[name] for metrics in (metrics_existing, metrics_anchor, metrics_hic))
            for name in ("graph_errors", "alignment_errors", "decision_errors")
        }
        hic = _summarize_hic(
            hic_pack,
            hic_rows,
            filtered_hic,
            sum(computation_errors.values()),
        )
        existing_counts = existing["counts"]
        anchor_counts = anchor["counts"]
        hic_counts = hic["counts"]
        secondary_conflicts = _known_secondary_conflicts_abstained(
            (anchor_rows, hic_rows),
            (filtered_anchor, filtered_hic),
        )
        retrieval_errors = (
            existing_counts["retrieval_errors"]
            + anchor_counts["anchor_retrieval_errors"]
            + hic_counts["retrieval_errors"]
        )
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
            "secondary_numeric_conflicts_abstained": secondary_conflicts,
            "retrieval_errors": retrieval_errors,
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
                "configuration_id": configuration_id,
                "eligible_as_survivor": configuration_id in NON_REFERENCE_POLICIES,
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
    preferred = min(
        survivors,
        key=policy_selection_key,
        default=None,
    )
    return {
        "schema_version": CALIBRATION_SCHEMA,
        "version": VERSION,
        "status": "historical_calibration_pass" if survivors else "historical_calibration_fail",
        "denominators": HISTORICAL_DENOMINATORS,
        "retrieval_calls_executed": 0,
        "private_local_artifacts_read": False,
        "sources": sources,
        "summaries": summaries,
        "eligible_non_reference_configuration_ids": [
            summary["configuration_id"] for summary in survivors
        ],
        "winner": (
            None
            if preferred is None
            else {
                "configuration_id": preferred["configuration_id"],
                "status": "historical_survivor_only_not_holdout_qualified",
            }
        ),
    }


def _grammar_definition(grammar: IdentityClaimGrammar) -> dict[str, Any]:
    forms = [asdict(form) for form in grammar.forms]
    return {
        "forms": forms,
        "forms_sha256": hashlib.sha256(_json(forms).encode()).hexdigest(),
        "form_count": len(forms),
        "identity_atom_count": len(grammar.identity_atoms),
        "context_tokens": sorted(CONTEXT_TOKENS),
        "relations": sorted(RELATIONS),
        "atom_roles": sorted(ATOM_ROLES),
        "frame_kinds": sorted(FRAME_KINDS),
        "candidate_independent": True,
    }


def _build_protocol_from_calibration(root: Path, calibration: dict[str, Any]) -> dict[str, Any]:
    survivors = calibration["eligible_non_reference_configuration_ids"]
    if not survivors:
        raise ValueError("no non-reference claim-graph policy passed historical calibration")
    catalog = _catalog(root)
    grammar = IdentityClaimGrammar(catalog.documents)
    summaries = [
        {
            "configuration_id": summary["configuration_id"],
            "eligible": summary["eligible"],
            "historical_gates": summary["historical_gates"],
            "selection_metrics": summary["selection_metrics"],
        }
        for summary in calibration["summaries"]
    ]
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "source_and_protocol_frozen_before_new_holdout",
        "sources": calibration["sources"],
        "historical_denominators": calibration["denominators"],
        "historical_calibration_sha256": hashlib.sha256(_json(calibration).encode()).hexdigest(),
        "historical_calibration": summaries,
        "historical_eligible_configuration_ids": survivors,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "claim_graph": _grammar_definition(grammar),
        "categorical_states": {
            "anchor_relation": sorted(ANCHOR_RELATIONS),
            "numeric_relation": sorted(NUMERIC_RELATIONS),
            "context_relation": sorted(CONTEXT_RELATIONS),
            "residual": sorted(RESIDUAL_STATES),
            "form_completion": sorted(FORM_COMPLETIONS),
            "hard_conflict": sorted(HARD_CONFLICT_STATES),
            "decision": sorted(DECISIONS),
        },
        "policies": list(policy_definitions()),
        "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
        "holdout": {
            "positive_count": 16,
            "negative_count": 16,
            "positive_challenges": {
                "leading_year_context": "contextual_noise",
                "frame_local_ocr_numeric": "abbreviation_numeric",
                "bounded_edit_abbreviation": "single_edit",
                "compact_spacing_punctuation": "spacing_punctuation",
            },
            "negative_challenges": {
                "numeric_model_conflict": 4,
                "same_maker_model_substitution": 4,
                "compact_digit_conflict": 4,
                "context_overlap": 4,
            },
            "negative_declarations_path": str(DECLARATIONS_PATH),
            "negative_declarations_schema": (
                "pvr-human-knowledge-identity-claim-graph-negative-declarations-v3"
            ),
        },
        "gates": {
            "historical": HISTORICAL_GATE_TARGETS,
            "new": {
                "positive_preservation_hits": 16,
                "absent_identity_nonempty": 0,
                "retrieval_errors": 0,
                "graph_errors": 0,
                "alignment_errors": 0,
                "decision_errors": 0,
            },
        },
        "winner_order": [
            "eligible_only",
            "minimum_negative_admitted_candidates",
            "minimum_positive_abstained_candidates",
            "minimum_non_exact_equivalence_operations",
            "least_restrictive_policy_preference",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def build_protocol(root: Path) -> dict[str, Any]:
    return _build_protocol_from_calibration(root, historical_calibration(root))


def _protocol_manifest(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-claim-graph-protocol-manifest-v3",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }


def _calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-claim graph v3 historical calibration",
        "",
        f"Status: `{report['status']}`.",
        "",
        "No new retrieval was executed. This report rescored the immutable 223 + 22 + 24 public rows.",
        "",
        "| configuration | eligible | existing positives | v4 positives | v4 negatives | HIC positives | HIC negatives | R32/R33 vetoes | computation errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        gates = {gate["name"]: gate["actual"] for gate in summary["historical_gates"]}
        errors = sum(
            gates[name] for name in ("graph_errors", "alignment_errors", "decision_errors")
        )
        lines.append(
            "| {configuration} | {eligible} | {existing}/168 | {anchor}/10 | {anchor_negative} | {hic}/12 | {hic_negative} | {conflicts}/2 | {errors} |".format(
                configuration=summary["configuration_id"],
                eligible=summary["eligible"],
                existing=gates["existing_positive_hits_at_5"],
                anchor=gates["anchor_valid_low_coverage_hits"],
                anchor_negative=gates["anchor_missing_identity_nonempty"],
                hic=gates["hic_positive_preservation_hits"],
                hic_negative=gates["hic_absent_identity_nonempty"],
                conflicts=gates["secondary_numeric_conflicts_abstained"],
                errors=errors,
            )
        )
    survivors = report["eligible_non_reference_configuration_ids"]
    lines.extend(
        [
            "",
            "Eligible non-reference policies: "
            + (", ".join(survivors) if survivors else "none")
            + ".",
            "",
            (
                "A protocol may now be frozen, but no holdout retrieval or runtime change is authorized."
                if survivors
                else "No protocol, holdout pack, raw retrieval, private evaluation, or runtime change is authorized."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _calibration_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-claim-graph-calibration-manifest-v3",
        "version": VERSION,
        "calibration_sha256": hashlib.sha256(_json(report).encode()).hexdigest(),
        "source_sha256": report["sources"],
        "denominators": report["denominators"],
        "eligible_non_reference_configuration_ids": report[
            "eligible_non_reference_configuration_ids"
        ],
        "retrieval_calls_executed": 0,
        "protocol_authorized": bool(report["eligible_non_reference_configuration_ids"]),
        "private_local_artifacts_read": False,
    }


def _calibration_outputs(report: dict[str, Any]) -> dict[str, str]:
    return {
        CALIBRATION_JSON: _json(report),
        CALIBRATION_MANIFEST: _json(_calibration_manifest(report)),
        CALIBRATION_MARKDOWN: _calibration_markdown(report),
    }


def freeze_protocol(root: Path) -> str:
    calibration = historical_calibration(root)
    calibration_operation = _freeze_report_files(
        root / REPORT_DIRECTORY,
        _calibration_outputs(calibration),
        "identity-claim historical calibration",
    )
    selection_exists = any(
        (root / REPORT_DIRECTORY / name).exists() for name in (SELECTION_JSON, SELECTION_MARKDOWN)
    )
    if selection_exists and not (root / PROTOCOL_DIRECTORY).exists():
        raise ValueError("selection artifacts exist before protocol freeze")
    if not calibration["eligible_non_reference_configuration_ids"]:
        if any(
            (root / path).exists() for path in (PROTOCOL_DIRECTORY, PACK_DIRECTORY, RAW_DIRECTORY)
        ):
            raise ValueError("failed calibration must not have downstream artifacts")
        return f"calibration_failed_{calibration_operation}"
    protocol = _build_protocol_from_calibration(root, calibration)
    return _freeze_directory(
        root / PROTOCOL_DIRECTORY,
        {
            "protocol.json": _json(protocol),
            "protocol-manifest.json": _json(_protocol_manifest(protocol)),
        },
        "identity-claim protocol",
    )


def validate_calibration(root: Path) -> dict[str, Any]:
    expected = historical_calibration(root)
    for name, content in _calibration_outputs(expected).items():
        _assert_file(root / REPORT_DIRECTORY / name, content)
    failed_calibration = not expected["eligible_non_reference_configuration_ids"]
    report_files = (
        {path.name for path in (root / REPORT_DIRECTORY).iterdir()} if failed_calibration else set()
    )
    if failed_calibration and (
        report_files != set(_calibration_outputs(expected))
        or any(
            (root / path).exists() for path in (PROTOCOL_DIRECTORY, PACK_DIRECTORY, RAW_DIRECTORY)
        )
    ):
        raise ValueError("failed calibration contains unauthorized downstream artifacts")
    return expected


def validate_protocol(root: Path) -> dict[str, Any]:
    calibration = validate_calibration(root)
    expected = _build_protocol_from_calibration(root, calibration)
    _assert_file(root / PROTOCOL_DIRECTORY / "protocol.json", _json(expected))
    _assert_file(
        root / PROTOCOL_DIRECTORY / "protocol-manifest.json",
        _json(_protocol_manifest(expected)),
    )
    return expected


def _document_family(document: HumanKnowledgeDocument) -> str:
    return str(getattr(document, "casting_id", None) or document.knowledge_id)


def _positive_challenge_valid(
    grammar: IdentityClaimGrammar,
    challenge: str,
    query_text: str,
) -> bool:
    graph = grammar.graph(query_text)
    if challenge == "leading_year_context":
        return any(atom.role == "context" for atom in graph.atoms)
    if challenge == "frame_local_ocr_numeric":
        return bool(graph.frames)
    if challenge == "bounded_edit_abbreviation":
        return any(
            atom.relation in {"unique_prefix_abbreviation", "unique_alpha_edit_1"}
            for atom in graph.atoms
        )
    if challenge == "compact_spacing_punctuation":
        return any(
            atom.relation == "compact_exact" or atom.segment_count > 1 for atom in graph.atoms
        )
    raise ValueError("unknown positive challenge family")


def _positive_holdout_cases(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    cases = _cases(root)
    upstream_rows = {row["case_id"]: row for row in check_upstream(root)["raw"]["rows"]}
    anchor_pack = validate_anchor_pack(root)
    hic_pack = validate_hic_pack(root)
    catalog = _catalog(root)
    documents = {document.knowledge_id: document for document in catalog.documents}
    grammar = IdentityClaimGrammar(catalog.documents)
    used_source_ids = {
        case["source_case_id"]
        for pack in (anchor_pack, hic_pack)
        for case in pack["cases"]
        if case.get("source_case_id") is not None
    }
    used_documents = {
        case["expected"]["knowledge_id"]
        for pack in (anchor_pack, hic_pack)
        for case in pack["cases"]
        if case["case_type"] in {"valid_low_coverage_anchor", "positive_preservation"}
    }
    used_families = {
        _document_family(documents[knowledge_id])
        for knowledge_id in used_documents
        if knowledge_id in documents
    }
    protocol_sha = _sha(root / PROTOCOL_DIRECTORY / "protocol.json")
    by_style: dict[str, list[tuple[str, dict[str, Any], dict[str, Any], str]]] = {}
    for case in cases:
        case_id = case["case_id"]
        row = upstream_rows.get(case_id)
        if (
            case.get("case_type") != "positive_family"
            or case_id in used_source_ids
            or row is None
            or not row["candidates"]
        ):
            continue
        expected_id = case["expected"]["review_family_id"]
        top = row["candidates"][0]
        document = documents.get(expected_id)
        if (
            document is None
            or top["source_rank"] != 1
            or top["knowledge_id"] != expected_id
            or expected_id in used_documents
        ):
            continue
        family = _document_family(document)
        if family in used_families:
            continue
        style = case["challenge_style"]
        key = hashlib.sha256(f"{protocol_sha}:{style}:{case_id}".encode()).hexdigest()
        by_style.setdefault(style, []).append((key, case, top, family))

    selected: list[dict[str, Any]] = []
    selected_documents: set[str] = set()
    selected_families: set[str] = set()
    for challenge, source_style in protocol["holdout"]["positive_challenges"].items():
        challenge_rows = 0
        for _, case, top, family in sorted(by_style.get(source_style, [])):
            if (
                top["knowledge_id"] in selected_documents
                or family in selected_families
                or not _positive_challenge_valid(grammar, challenge, case["query_text"])
            ):
                continue
            selected_documents.add(top["knowledge_id"])
            selected_families.add(family)
            challenge_rows += 1
            selected.append(
                {
                    "case_id": f"hicg-pos-{len(selected) + 1:02d}",
                    "case_type": "positive_preservation",
                    "challenge_type": challenge,
                    "source_case_id": case["case_id"],
                    "query_text": case["query_text"],
                    "expected": {
                        "knowledge_id": top["knowledge_id"],
                        "knowledge_uuid": top["knowledge_uuid"],
                        "knowledge_type": top["knowledge_type"],
                        "family_id": family,
                    },
                }
            )
            if challenge_rows == 4:
                break
        if challenge_rows != 4:
            raise ValueError(f"insufficient family-disjoint positive cases for {challenge}")
    if len(selected) != 16 or len(selected_documents) != 16 or len(selected_families) != 16:
        raise ValueError("claim-graph positives must use sixteen documents and families")
    return selected


def _negative_holdout_cases(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    declarations = _load(root / DECLARATIONS_PATH)
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
    expected_categories = protocol["holdout"]["negative_challenges"]
    category_counts: Counter[str] = Counter()
    identities: set[str] = set()
    queries: set[str] = set()
    rows: list[dict[str, Any]] = []
    declarations_rows = sorted(
        declarations["cases"],
        key=lambda item: (item.get("challenge_type", ""), item.get("case_id", "")),
    )
    for declaration in declarations_rows:
        required = {"case_id", "challenge_type", "query_text", "absent_identity"}
        if set(declaration) != required:
            raise ValueError("negative declaration fields differ from contract")
        normalized_identity = normalize_text(declaration["absent_identity"])
        normalized_query = normalize_text(declaration["query_text"])
        if (
            not normalized_identity
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
        category_counts[declaration["challenge_type"]] += 1
        rows.append(
            {
                "case_id": declaration["case_id"],
                "case_type": "absent_identity_contradiction",
                "challenge_type": declaration["challenge_type"],
                "source_case_id": None,
                "query_text": declaration["query_text"],
                "expected": {
                    "absent_identity": declaration["absent_identity"],
                    "must_abstain_all": True,
                },
            }
        )
    if dict(category_counts) != expected_categories:
        raise ValueError("negative declaration categories differ from four-by-four contract")
    return rows


def build_pack(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = validate_protocol(root)
    positive_cases = _positive_holdout_cases(root, protocol)
    negative_cases = _negative_holdout_cases(root, protocol)
    cases = [*positive_cases, *negative_cases]
    if len(cases) != 32 or len({case["case_id"] for case in cases}) != 32:
        raise ValueError("claim-graph pack must contain thirty-two unique cases")
    sources = {
        str(PROTOCOL_DIRECTORY / "protocol.json"): _sha(
            root / PROTOCOL_DIRECTORY / "protocol.json"
        ),
        str(PROTOCOL_DIRECTORY / "protocol-manifest.json"): _sha(
            root / PROTOCOL_DIRECTORY / "protocol-manifest.json"
        ),
        str(DECLARATIONS_PATH): _sha(root / DECLARATIONS_PATH),
    }
    pack = {
        "schema_version": PACK_SCHEMA,
        "version": VERSION,
        "status": "frozen_after_protocol_before_retrieval",
        "sources": dict(sorted(sources.items())),
        "case_counts": {"positive_preservation": 16, "absent_identity_contradiction": 16},
        "positive_challenge_counts": dict(
            sorted(Counter(case["challenge_type"] for case in positive_cases).items())
        ),
        "negative_challenge_counts": dict(
            sorted(Counter(case["challenge_type"] for case in negative_cases).items())
        ),
        "cases": cases,
        "eligible_for": ["public_identity_claim_graph_development_only"],
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
        "schema_version": "pvr-human-knowledge-identity-claim-graph-pack-manifest-v3",
        "version": VERSION,
        "pack_sha256": hashlib.sha256(_json(pack).encode()).hexdigest(),
        "source_sha256": pack["sources"],
        "case_counts": pack["case_counts"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    return pack, manifest


def freeze_pack(root: Path) -> str:
    pack, manifest = build_pack(root)
    return _freeze_directory(
        root / PACK_DIRECTORY,
        {
            "development-pack.json": _json(pack),
            "development-pack-manifest.json": _json(manifest),
        },
        "identity-claim pack",
    )


def validate_pack(root: Path) -> dict[str, Any]:
    pack, manifest = build_pack(root)
    _assert_file(root / PACK_DIRECTORY / "development-pack.json", _json(pack))
    _assert_file(
        root / PACK_DIRECTORY / "development-pack-manifest.json",
        _json(manifest),
    )
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
            artifact_sha256=_sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        ),
    )
    rows: list[dict[str, Any]] = []
    for case in pack["cases"]:
        query = case["query_text"]
        try:
            candidates, work = retriever.retrieve_with_work(
                extract_signals(query),
                CANDIDATE_LIMIT,
            )
            payload = {
                "candidates": [_upstream_candidate(candidate, query) for candidate in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - preserve one-shot public evidence
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
        raise ValueError("identity-claim collection must contain thirty-two rows")
    return {
        "schema_version": RAW_SCHEMA,
        "version": VERSION,
        "status": "label_blind_raw_retrieval_complete",
        "protocol_sha256": _sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "pack_sha256": _sha(root / PACK_DIRECTORY / "development-pack.json"),
        "retrieval_calls": 32,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": protocol["base_retriever"],
        "private_local_artifacts_read": False,
        "rows": rows,
    }


def _raw_manifest(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-claim-graph-raw-manifest-v3",
        "version": VERSION,
        "raw_sha256": hashlib.sha256(_json(raw).encode()).hexdigest(),
        "protocol_sha256": _sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "pack_sha256": _sha(root / PACK_DIRECTORY / "development-pack.json"),
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
            "raw.json": _json(raw),
            "raw-manifest.json": _json(_raw_manifest(root, raw)),
        },
        "identity-claim raw",
    )
    return validate_raw(root), operation


RAW_FORBIDDEN_KEYS = frozenset(
    {
        "absent_identity",
        "case_type",
        "challenge_type",
        "decision",
        "expected",
        "expected_label",
        "expected_labels",
        "gates",
        "label",
        "labels",
        "must_abstain_all",
        "policy",
        "policy_decisions",
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
    candidate: dict[str, Any],
    document: HumanKnowledgeDocument,
    query: str,
    rank: int,
) -> None:
    finite_required = (candidate["source_rrf_score"], candidate["identity_token_coverage"])
    finite_optional = (
        candidate["sparse_score"],
        candidate["dense_score"],
        candidate["character_score"],
    )
    if (
        candidate["knowledge_id"] != document.knowledge_id
        or candidate["knowledge_uuid"] != str(document.knowledge_uuid)
        or candidate["knowledge_type"] != document.knowledge_type
        or candidate["casting_id"] != getattr(document, "casting_id", None)
        or candidate["source_rank"] != rank
        or not all(
            type(value) in {int, float} and math.isfinite(value) for value in finite_required
        )
        or not all(
            value is None or (type(value) in {int, float} and math.isfinite(value))
            for value in finite_optional
        )
        or candidate["identity_token_coverage"] != identity_token_coverage(query, document)
    ):
        raise ValueError("raw candidate differs from public corpus or numeric contract")


def validate_raw(root: Path) -> dict[str, Any]:
    protocol = validate_protocol(root)
    pack = validate_pack(root)
    raw = _load(root / RAW_DIRECTORY / "raw.json")
    if (
        raw.get("schema_version") != RAW_SCHEMA
        or raw.get("retrieval_calls") != 32
        or raw.get("candidate_limit") != CANDIDATE_LIMIT
        or raw.get("protocol_sha256") != _sha(root / PROTOCOL_DIRECTORY / "protocol.json")
        or raw.get("pack_sha256") != _sha(root / PACK_DIRECTORY / "development-pack.json")
        or raw.get("base_retriever") != protocol["base_retriever"]
        or raw.get("private_local_artifacts_read") is not False
        or _contains_forbidden_raw_key(raw)
        or len(raw.get("rows", [])) != 32
    ):
        raise ValueError("raw identity-claim metadata differs from contract")
    catalog = _catalog(root)
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    for case, row in zip(pack["cases"], raw["rows"], strict=True):
        if set(row) != {"case_id", "query_text", "candidates", "work", "error"} or any(
            row.get(name) != case[name] for name in ("case_id", "query_text")
        ):
            raise ValueError("raw identity-claim row differs from frozen pack")
        if row["error"] is not None:
            if row["candidates"] or row["work"] is not None:
                raise ValueError("errored raw row must preserve an empty candidate/work result")
        elif row["work"] is None:
            raise ValueError("successful raw row must preserve retrieval work")
        if len(row["candidates"]) > CANDIDATE_LIMIT:
            raise ValueError("raw row exceeds frozen candidate limit")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = documents.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("raw candidate is absent from public corpus")
            _validate_raw_candidate(candidate, document, row["query_text"], rank)
    _assert_file(root / RAW_DIRECTORY / "raw-manifest.json", _json(_raw_manifest(root, raw)))
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
        "graph_errors": metrics["graph_errors"],
        "alignment_errors": metrics["alignment_errors"],
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
        result: dict[str, Any] = {
            "case_id": case["case_id"],
            "case_type": case["case_type"],
        }
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
            raise ValueError("unexpected identity-claim holdout case type")
        case_results.append(result)
    expected = {
        "positive_preservation_hits": 16,
        "absent_identity_nonempty": 0,
        "retrieval_errors": 0,
        "graph_errors": 0,
        "alignment_errors": 0,
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
        for name, threshold in expected.items()
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
    grammar = IdentityClaimGrammar(catalog.documents)
    calibration_by_id = {
        summary["configuration_id"]: summary for summary in calibration["summaries"]
    }
    positive_ids = {
        case["case_id"] for case in pack["cases"] if case["case_type"] == "positive_preservation"
    }
    summaries: list[dict[str, Any]] = []
    for configuration_id in POLICIES:
        filtered_rows, evaluations, metrics = apply_policy(
            raw["rows"],
            documents,
            grammar,
            configuration_id,
        )
        holdout = _summarize_holdout(pack, raw["rows"], filtered_rows, metrics)
        historical = calibration_by_id[configuration_id]
        positive_abstained = historical["selection_metrics"]["positive_abstained_candidates"] + sum(
            len(source["candidates"]) - len(admitted["candidates"])
            for source, admitted in zip(raw["rows"], filtered_rows, strict=True)
            if source["case_id"] in positive_ids
        )
        negative_admitted = historical["selection_metrics"]["negative_admitted_candidates"] + sum(
            len(row["candidates"])
            for case, row in zip(pack["cases"], filtered_rows, strict=True)
            if case["case_type"] == "absent_identity_contradiction"
        )
        eligible = (
            configuration_id in protocol["historical_eligible_configuration_ids"]
            and historical["eligible"]
            and holdout["eligible"]
        )
        summaries.append(
            {
                "configuration_id": configuration_id,
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
                    "graph_errors": historical["selection_metrics"]["graph_errors"]
                    + metrics["graph_errors"],
                    "alignment_errors": historical["selection_metrics"]["alignment_errors"]
                    + metrics["alignment_errors"],
                    "decision_errors": historical["selection_metrics"]["decision_errors"]
                    + metrics["decision_errors"],
                },
                "candidate_metrics": metrics,
                "evaluations": evaluations,
                "eligible": eligible,
            }
        )
    eligible = [summary for summary in summaries if summary["eligible"]]
    winner = min(
        eligible,
        key=policy_selection_key,
        default=None,
    )
    return {
        "summaries": summaries,
        "winner": (
            None
            if winner is None
            else {
                "configuration_id": winner["configuration_id"],
                "selection_metrics": winner["selection_metrics"],
                "historical_eligible_configuration_ids": protocol[
                    "historical_eligible_configuration_ids"
                ],
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
        PACK_DIRECTORY / "development-pack.json",
        PACK_DIRECTORY / "development-pack-manifest.json",
        RAW_DIRECTORY / "raw.json",
        RAW_DIRECTORY / "raw-manifest.json",
    )
    return {str(path): _sha(root / path) for path in paths}


def _report(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "version": VERSION,
        "status": "public_development_selection_complete_not_runtime",
        "protocol_sha256": raw["protocol_sha256"],
        "pack_sha256": raw["pack_sha256"],
        "raw_sha256": _sha(root / RAW_DIRECTORY / "raw.json"),
        "sources": _selection_sources(root),
        "private_local_artifacts_read": False,
        "limitations": [
            "public development evidence is not a private final evaluation",
            "an eligible winner does not authorize runtime activation",
            "variant-level color and release metadata remain out of scope",
        ],
        **score(root, raw),
    }


def _selection_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-claim graph v3 selection",
        "",
        f"Status: `{report['status']}`.",
        "",
        "| configuration | historical | new holdout | eligible | negatives admitted | positives abstained | non-exact operations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        lines.append(
            "| {configuration} | {historical} | {holdout} | {eligible} | {negative} | {positive} | {nonexact} |".format(
                configuration=summary["configuration_id"],
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
            f"Winner: `{None if report['winner'] is None else report['winner']['configuration_id']}`.",
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
            SELECTION_JSON: _json(report),
            SELECTION_MARKDOWN: _selection_markdown(report),
        },
        "identity-claim selection",
    )
    return check(root), operation


def check(root: Path) -> dict[str, Any]:
    calibration = validate_calibration(root)
    if not calibration["eligible_non_reference_configuration_ids"]:
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
    selection_paths = (
        root / REPORT_DIRECTORY / SELECTION_JSON,
        root / REPORT_DIRECTORY / SELECTION_MARKDOWN,
    )
    if not any(path.exists() for path in selection_paths):
        return raw
    if not all(path.exists() for path in selection_paths):
        raise ValueError("selection artifacts are partial")
    expected = _report(root, raw)
    _assert_file(selection_paths[0], _json(expected))
    _assert_file(selection_paths[1], _selection_markdown(expected))
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Develop public candidate-independent identity-claim graph"
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
            "configurations": len(POLICIES),
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
