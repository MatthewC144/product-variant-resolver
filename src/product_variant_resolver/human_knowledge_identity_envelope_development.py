"""Public query-global identity-envelope development primitives."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
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
    GATES,
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
from .human_knowledge_identity_contradiction_development import (
    SOURCE as HIC_SOURCE,
)
from .human_knowledge_identity_contradiction_development import (
    IdentityAtom,
    IdentityEvidenceIndex,
    _ordered_alignment,
    atomize,
)
from .human_knowledge_identity_contradiction_development import (
    _candidate as _upstream_candidate,
)
from .human_knowledge_identity_contradiction_development import (
    _summarize_new as _summarize_hic,
)
from .human_knowledge_identity_contradiction_development import (
    validate_pack as validate_hic_pack,
)
from .human_knowledge_identity_contradiction_development import (
    validate_raw as validate_hic_raw,
)
from .human_knowledge_reranker_development import (
    REPORT_DIRECTORY as UPSTREAM_REPORT_DIRECTORY,
)
from .human_knowledge_reranker_development import check as check_upstream
from .identity import normalize_text
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-identity-envelope-development-v2"
SOURCE = "src/product_variant_resolver/human_knowledge_identity_envelope_development.py"
ALLOWED_CENTURY_PREFIXES = frozenset({"19", "20"})
CANDIDATE_LIMIT = 5
SECONDARY_THRESHOLD = 0.75
PACK_SCHEMA = "pvr-human-knowledge-identity-envelope-pack-v2"
PROTOCOL_SCHEMA = "pvr-human-knowledge-identity-envelope-protocol-v2"
RAW_SCHEMA = "pvr-human-knowledge-identity-envelope-raw-v2"
REPORT_SCHEMA = "pvr-human-knowledge-identity-envelope-selection-v2"
CALIBRATION_SCHEMA = "pvr-human-knowledge-identity-envelope-calibration-v2"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
PROTOCOL_DIRECTORY = DATA_DIRECTORY / "protocol"
PACK_DIRECTORY = DATA_DIRECTORY / "pack"
RAW_DIRECTORY = DATA_DIRECTORY / "raw"
REPORT_DIRECTORY = Path("reports") / VERSION
CALIBRATION_JSON = "historical-calibration.json"
CALIBRATION_MARKDOWN = "historical-calibration.md"
CALIBRATION_MANIFEST = "historical-calibration-manifest.json"
DECLARATIONS_PATH = (
    Path("specs/human-knowledge-identity-envelope-development")
    / "holdout-negative-declarations.json"
)
POLICIES = (
    "reference-anchor",
    "envelope-numeric",
    "envelope-bilateral",
    "envelope-safe-form",
    "envelope-decision-list",
)
PREFERENCE = {
    "envelope-numeric": 0,
    "envelope-bilateral": 1,
    "envelope-safe-form": 2,
    "envelope-decision-list": 3,
    "reference-anchor": 4,
}
ENVELOPE_STATES = frozenset({"anchored", "unanchored"})
ANCHOR_RELATIONS = frozenset({"equal", "different", "unavailable"})
NUMERIC_RELATIONS = frozenset(
    {"none", "equal", "year_suffix_equivalent", "conflict", "query_only", "candidate_only"}
)
FORM_COMPLETIONS = frozenset({"complete", "partial"})
ALIGNMENT_STRENGTHS = frozenset({"exact", "shorthand", "fuzzy", "weak"})
MODEL_RESIDUALS = frozenset({"none", "present"})
COMPACT_DIGIT_GUARDS = frozenset({"pass", "fail"})
REASON_CODES = frozenset(
    {
        "reference_rank_1",
        "compatible_identity",
        "numeric_conflict",
        "compact_digit_guard_failed",
        "anchor_mismatch",
        "bilateral_model_residual",
        "query_model_residual",
        "complete_safe_form",
        "bounded_fuzzy_form",
        "ambiguous_identity",
        "secondary_coverage_below_075",
        "secondary_coverage_at_least_075",
    }
)


@dataclass(frozen=True, slots=True)
class AnchorForm:
    knowledge_id: str
    identity_kind: str
    core: str
    anchor: str
    anchor_atom_index: int
    atoms: tuple[IdentityAtom, ...]


@dataclass(frozen=True, slots=True)
class ModelFrame:
    source_token: str
    alphabetic_skeleton: str
    digit_runs: tuple[str, ...]
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class QueryEnvelope:
    status: str
    query_core: str
    anchor: str | None
    anchor_atom_index: int | None
    atom_start: int
    atom_end: int
    start: int
    end: int
    text: str
    atoms: tuple[IdentityAtom, ...]
    checksum: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query_core": self.query_core,
            "anchor": self.anchor,
            "anchor_atom_index": self.anchor_atom_index,
            "atom_start": self.atom_start,
            "atom_end": self.atom_end,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "atoms": [asdict(atom) for atom in self.atoms],
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class NumericEvidence:
    relation: str
    anchor_relation: str
    query_digit_runs: tuple[str, ...]
    candidate_digit_runs: tuple[str, ...]
    query_frames: tuple[ModelFrame, ...]
    candidate_frames: tuple[ModelFrame, ...]
    shorthand_rule: str | None
    compact_digit_guard: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "relation": self.relation,
            "anchor_relation": self.anchor_relation,
            "query_digit_runs": list(self.query_digit_runs),
            "candidate_digit_runs": list(self.candidate_digit_runs),
            "query_frames": [asdict(frame) for frame in self.query_frames],
            "candidate_frames": [asdict(frame) for frame in self.candidate_frames],
            "shorthand_rule": self.shorthand_rule,
            "compact_digit_guard": self.compact_digit_guard,
        }


def _first_alphabetic_atom(atoms: tuple[IdentityAtom, ...]) -> int | None:
    return next((position for position, atom in enumerate(atoms) if atom.text.isalpha()), None)


def _pure_leading_number(
    atoms: tuple[IdentityAtom, ...], anchor_position: int | None
) -> IdentityAtom | None:
    if anchor_position != 1:
        return None
    atom = atoms[0]
    if atom.text.isdigit() and atom.source_token == atom.text and len(atom.text) in {2, 4}:
        return atom
    return None


def _checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _model_frames(atoms: tuple[IdentityAtom, ...]) -> tuple[ModelFrame, ...]:
    frames: list[ModelFrame] = []
    position = 0
    while position < len(atoms):
        end = position + 1
        while end < len(atoms) and atoms[end].source_token == atoms[position].source_token:
            end += 1
        group = atoms[position:end]
        token = group[0].source_token
        if any(atom.text.isdigit() for atom in group) and any(
            atom.text.isalpha() for atom in group
        ):
            frames.append(
                ModelFrame(
                    source_token=token,
                    alphabetic_skeleton=re.sub(r"\d+", "#", token),
                    digit_runs=tuple(atom.text for atom in group if atom.text.isdigit()),
                    start=group[0].start,
                    end=group[-1].end,
                )
            )
        position = end
    return tuple(frames)


def _year_suffix_equivalent(query: str, candidate: str) -> bool:
    shorter, longer = sorted((query, candidate), key=len)
    return bool(
        len(shorter) == 2
        and len(longer) == 4
        and longer[:2] in ALLOWED_CENTURY_PREFIXES
        and longer[-2:] == shorter
    )


class IdentityEnvelopeIndex:
    """Corpus-wide anchor index that creates one candidate-independent query envelope."""

    def __init__(self, documents: tuple[HumanKnowledgeDocument, ...]) -> None:
        if not documents:
            raise ValueError("identity envelope index requires public documents")
        if len({document.knowledge_id for document in documents}) != len(documents):
            raise ValueError("identity envelope index requires unique knowledge IDs")
        if len({document.knowledge_uuid for document in documents}) != len(documents):
            raise ValueError("identity envelope index requires unique knowledge UUIDs")

        forms: list[AnchorForm] = []
        seen: set[tuple[str, str]] = set()
        for document in sorted(documents, key=lambda item: item.knowledge_id):
            for identity_number, identity in enumerate(
                dict.fromkeys(document.character_identity_texts)
            ):
                core, atoms = atomize(identity)
                anchor_position = _first_alphabetic_atom(atoms)
                if anchor_position is None:
                    raise ValueError("public identity form has no alphabetic anchor")
                key = (document.knowledge_id, core)
                if key in seen:
                    continue
                seen.add(key)
                forms.append(
                    AnchorForm(
                        knowledge_id=document.knowledge_id,
                        identity_kind="casting" if identity_number == 0 else "alias",
                        core=core,
                        anchor=atoms[anchor_position].text,
                        anchor_atom_index=anchor_position,
                        atoms=atoms,
                    )
                )
        self.forms = tuple(sorted(forms, key=lambda form: (form.core, form.knowledge_id)))
        self.evidence_index = IdentityEvidenceIndex(documents)
        by_anchor: dict[str, list[AnchorForm]] = {}
        for form in self.forms:
            by_anchor.setdefault(form.anchor, []).append(form)
        self.forms_by_anchor = {
            anchor: tuple(anchor_forms) for anchor, anchor_forms in sorted(by_anchor.items())
        }

    def _anchor_choice(self, query_atoms: tuple[IdentityAtom, ...]) -> tuple[int, str] | None:
        choices: list[tuple[tuple[float, float, float, int, int], int, str]] = []
        for query_position, query_atom in enumerate(query_atoms):
            for form_number, form in enumerate(self.forms_by_anchor.get(query_atom.text, ())):
                query_suffix = query_atoms[query_position:]
                candidate_suffix = form.atoms[form.anchor_atom_index :]
                alignments = _ordered_alignment(query_suffix, candidate_suffix, self.evidence_index)
                matched_candidate = {
                    position
                    for alignment in alignments
                    for position in range(alignment.candidate_start, alignment.candidate_end)
                }
                matched_weight = sum(
                    self.evidence_index.weight(candidate_suffix[position])
                    for position in matched_candidate
                )
                total_weight = sum(self.evidence_index.weight(atom) for atom in candidate_suffix)
                matched_ratio = matched_weight / total_weight if total_weight else 0.0
                choices.append(
                    (
                        (
                            matched_ratio,
                            matched_weight,
                            sum(alignment.similarity for alignment in alignments),
                            query_position,
                            -form_number,
                        ),
                        query_position,
                        form.anchor,
                    )
                )
        if not choices:
            return None
        _, query_position, anchor = max(choices, key=lambda choice: choice[0])
        return query_position, anchor

    def envelope(self, query_text: str) -> QueryEnvelope:
        core, atoms = atomize(query_text)
        if not atoms:
            raise ValueError("query has no identity atoms")
        choice = self._anchor_choice(atoms)
        if choice is None:
            status = "unanchored"
            anchor = None
            anchor_position = None
            start_position = 0
        else:
            status = "anchored"
            anchor_position, anchor = choice
            start_position = anchor_position
            if _pure_leading_number(atoms, anchor_position) is not None:
                start_position -= 1
        envelope_atoms = atoms[start_position:]
        relative_anchor = None if anchor_position is None else anchor_position - start_position
        payload = {
            "status": status,
            "query_core": core,
            "anchor": anchor,
            "anchor_atom_index": relative_anchor,
            "atom_start": start_position,
            "atom_end": len(atoms),
            "start": envelope_atoms[0].start,
            "end": envelope_atoms[-1].end,
            "text": core[envelope_atoms[0].start : envelope_atoms[-1].end],
            "atoms": [asdict(atom) for atom in envelope_atoms],
        }
        return QueryEnvelope(
            status=status,
            query_core=core,
            anchor=anchor,
            anchor_atom_index=relative_anchor,
            atom_start=start_position,
            atom_end=len(atoms),
            start=envelope_atoms[0].start,
            end=envelope_atoms[-1].end,
            text=payload["text"],
            atoms=envelope_atoms,
            checksum=_checksum(payload),
        )


def numeric_evidence(envelope: QueryEnvelope, candidate_identity: str) -> NumericEvidence:
    _, candidate_atoms = atomize(candidate_identity)
    if not candidate_atoms:
        raise ValueError("candidate identity has no atoms")
    candidate_anchor_position = _first_alphabetic_atom(candidate_atoms)
    candidate_anchor = (
        None
        if candidate_anchor_position is None
        else candidate_atoms[candidate_anchor_position].text
    )
    if envelope.anchor is None or candidate_anchor is None:
        anchor_relation = "unavailable"
    elif envelope.anchor == candidate_anchor:
        anchor_relation = "equal"
    else:
        anchor_relation = "different"

    query_runs = tuple(atom.text for atom in envelope.atoms if atom.text.isdigit())
    candidate_runs = tuple(atom.text for atom in candidate_atoms if atom.text.isdigit())
    query_leading = _pure_leading_number(envelope.atoms, envelope.anchor_atom_index)
    candidate_leading = _pure_leading_number(candidate_atoms, candidate_anchor_position)
    shorthand = bool(
        anchor_relation == "equal"
        and query_leading is not None
        and candidate_leading is not None
        and len(query_runs) == len(candidate_runs) == 1
        and _year_suffix_equivalent(query_leading.text, candidate_leading.text)
    )

    if not query_runs and not candidate_runs:
        relation = "none"
    elif query_runs == candidate_runs:
        relation = "equal"
    elif shorthand:
        relation = "year_suffix_equivalent"
    elif not query_runs:
        relation = "candidate_only"
    elif not candidate_runs:
        relation = "query_only"
    else:
        relation = "conflict"

    return NumericEvidence(
        relation=relation,
        anchor_relation=anchor_relation,
        query_digit_runs=query_runs,
        candidate_digit_runs=candidate_runs,
        query_frames=_model_frames(envelope.atoms),
        candidate_frames=_model_frames(candidate_atoms),
        shorthand_rule=("leading_year_suffix" if shorthand else None),
        compact_digit_guard="fail" if relation == "conflict" else "pass",
    )


def _atom_payload(atom: IdentityAtom, weight: float) -> dict[str, Any]:
    return {
        "atom": atom.text,
        "source_token": atom.source_token,
        "start": atom.start,
        "end": atom.end,
        "weight": weight,
    }


def _alignment_strength(
    form_completion: str,
    numeric: NumericEvidence,
    modes: tuple[str, ...],
) -> str:
    if numeric.relation == "year_suffix_equivalent" and form_completion == "complete":
        return "shorthand"
    if (
        form_completion == "complete"
        and modes
        and all(mode in {"exact", "compact_exact"} for mode in modes)
    ):
        return "exact"
    if modes:
        return "fuzzy"
    return "weak"


def envelope_alignment_evidence(
    envelope: QueryEnvelope,
    document: HumanKnowledgeDocument,
    index: IdentityEvidenceIndex,
) -> dict[str, Any]:
    """Compare one immutable query envelope with each approved identity form."""

    choices: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for identity_number, identity in enumerate(dict.fromkeys(document.character_identity_texts)):
        candidate_core, candidate_atoms = atomize(identity)
        if not candidate_atoms:
            raise ValueError("candidate identity has no atoms")
        numeric = numeric_evidence(envelope, identity)
        alignments = _ordered_alignment(envelope.atoms, candidate_atoms, index)
        matched_query = {
            position
            for alignment in alignments
            for position in range(alignment.query_start, alignment.query_end)
        }
        matched_candidate = {
            position
            for alignment in alignments
            for position in range(alignment.candidate_start, alignment.candidate_end)
        }
        if numeric.relation == "year_suffix_equivalent":
            matched_query.add(0)
            matched_candidate.add(0)
        unmatched_query = tuple(
            atom
            for position, atom in enumerate(envelope.atoms)
            if position not in matched_query and index.weight(atom) > 0
        )
        unmatched_candidate = tuple(
            atom
            for position, atom in enumerate(candidate_atoms)
            if position not in matched_candidate and index.weight(atom) > 0
        )
        completion = "complete" if not unmatched_query and not unmatched_candidate else "partial"
        modes = tuple(alignment.mode for alignment in alignments)
        strength = _alignment_strength(completion, numeric, modes)
        matched_weight = sum(
            index.weight(candidate_atoms[position]) for position in matched_candidate
        )
        total_weight = sum(index.weight(atom) for atom in candidate_atoms)
        payload = {
            "query_envelope": envelope.as_dict(),
            "candidate_identity": candidate_core,
            "candidate_identity_kind": "casting" if identity_number == 0 else "alias",
            "alignments": [
                {
                    "candidate_atoms": [
                        atom.text
                        for atom in candidate_atoms[
                            alignment.candidate_start : alignment.candidate_end
                        ]
                    ],
                    "query_atoms": [
                        atom.text
                        for atom in envelope.atoms[alignment.query_start : alignment.query_end]
                    ],
                    "candidate_start": alignment.candidate_start,
                    "candidate_end": alignment.candidate_end,
                    "query_start": envelope.atom_start + alignment.query_start,
                    "query_end": envelope.atom_start + alignment.query_end,
                    "mode": alignment.mode,
                    "similarity": alignment.similarity,
                }
                for alignment in alignments
            ],
            "unmatched_query_atoms": [
                _atom_payload(atom, index.weight(atom)) for atom in unmatched_query
            ],
            "unmatched_candidate_atoms": [
                _atom_payload(atom, index.weight(atom)) for atom in unmatched_candidate
            ],
            "envelope_status": envelope.status,
            "anchor_relation": numeric.anchor_relation,
            "numeric_relation": numeric.relation,
            "form_completion": completion,
            "alignment_strength": strength,
            "query_model_residual": "present" if unmatched_query else "none",
            "candidate_model_residual": "present" if unmatched_candidate else "none",
            "compact_digit_guard": numeric.compact_digit_guard,
            "numeric_evidence": numeric.as_dict(),
        }
        key = (
            completion == "complete",
            numeric.anchor_relation == "equal",
            numeric.compact_digit_guard == "pass",
            matched_weight / total_weight if total_weight else 0.0,
            matched_weight,
            sum(alignment.similarity for alignment in alignments),
            -identity_number,
            candidate_core,
        )
        choices.append((key, payload))
    if not choices:
        raise ValueError("candidate has no approved identity form")
    evidence = max(choices, key=lambda choice: choice[0])[1]
    _validate_evidence(evidence, envelope.checksum)
    return evidence


def _validate_evidence(evidence: dict[str, Any], envelope_checksum: str) -> None:
    if (
        evidence.get("query_envelope", {}).get("checksum") != envelope_checksum
        or evidence.get("envelope_status") not in ENVELOPE_STATES
        or evidence.get("anchor_relation") not in ANCHOR_RELATIONS
        or evidence.get("numeric_relation") not in NUMERIC_RELATIONS
        or evidence.get("form_completion") not in FORM_COMPLETIONS
        or evidence.get("alignment_strength") not in ALIGNMENT_STRENGTHS
        or evidence.get("query_model_residual") not in MODEL_RESIDUALS
        or evidence.get("candidate_model_residual") not in MODEL_RESIDUALS
        or evidence.get("compact_digit_guard") not in COMPACT_DIGIT_GUARDS
    ):
        raise ValueError("candidate envelope evidence differs from categorical contract")
    numeric = evidence.get("numeric_evidence", {})
    if (
        numeric.get("relation") != evidence["numeric_relation"]
        or numeric.get("anchor_relation") != evidence["anchor_relation"]
    ):
        raise ValueError("numeric evidence differs from categorical state")
    for group in (numeric.get("query_frames", []), numeric.get("candidate_frames", [])):
        for frame in group:
            if not frame.get("digit_runs"):
                raise ValueError("model frame omitted its conserved digit run")


def _decision(
    candidate: dict[str, Any], evidence: dict[str, Any], configuration_id: str
) -> tuple[bool, list[str]]:
    if configuration_id not in POLICIES:
        raise ValueError("unknown identity-envelope configuration")
    if candidate["source_rank"] != 1:
        admitted = candidate["identity_token_coverage"] + 1e-12 >= SECONDARY_THRESHOLD
        return admitted, [
            "secondary_coverage_at_least_075" if admitted else "secondary_coverage_below_075"
        ]
    if configuration_id == "reference-anchor":
        return True, ["reference_rank_1"]
    if evidence["numeric_relation"] == "conflict":
        return False, ["numeric_conflict"]
    if evidence["compact_digit_guard"] == "fail":
        return False, ["compact_digit_guard_failed"]
    if configuration_id == "envelope-numeric":
        return True, ["compatible_identity"]
    bilateral = (
        evidence["query_model_residual"] == "present"
        and evidence["candidate_model_residual"] == "present"
    )
    if configuration_id == "envelope-bilateral":
        if evidence["anchor_relation"] == "different":
            return False, ["anchor_mismatch"]
        if bilateral:
            return False, ["bilateral_model_residual"]
        return True, ["compatible_identity"]
    safe_form = evidence["form_completion"] == "complete" and evidence["alignment_strength"] in {
        "exact",
        "shorthand",
    }
    if configuration_id == "envelope-safe-form":
        if safe_form:
            return True, ["complete_safe_form"]
        if evidence["anchor_relation"] == "different":
            return False, ["anchor_mismatch"]
        if evidence["query_model_residual"] == "present":
            return False, ["query_model_residual"]
        return True, ["compatible_identity"]
    if configuration_id != "envelope-decision-list":
        raise ValueError("unknown identity-envelope policy branch")
    if safe_form:
        return True, ["complete_safe_form"]
    if evidence["anchor_relation"] == "different":
        return False, ["anchor_mismatch"]
    if (
        evidence["alignment_strength"] == "fuzzy"
        and evidence["query_model_residual"] == "none"
        and evidence["candidate_model_residual"] == "none"
    ):
        return True, ["bounded_fuzzy_form"]
    if bilateral:
        return False, ["bilateral_model_residual"]
    return False, ["ambiguous_identity"]


def apply_policy(
    rows: list[dict[str, Any]],
    documents: dict[str, HumanKnowledgeDocument],
    evidence_index: IdentityEvidenceIndex,
    envelope_index: IdentityEnvelopeIndex,
    configuration_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    if configuration_id not in POLICIES:
        raise ValueError("unknown identity-envelope configuration")
    filtered_rows: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    metrics = {
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
        "envelope_errors": 0,
    }
    for row in rows:
        if not row["candidates"]:
            filtered_rows.append({**row, "candidates": []})
            evaluations.append(
                {
                    "case_id": row["case_id"],
                    "query_envelope": None,
                    "candidates": [],
                    "error": None,
                }
            )
            continue
        try:
            envelope = envelope_index.envelope(row["query_text"])
        except Exception as error:  # noqa: BLE001 - row-level evidence failure is a failed gate
            candidate_count = len(row["candidates"][:CANDIDATE_LIMIT])
            metrics["source_candidates"] += candidate_count
            metrics["abstained_candidates"] += candidate_count
            metrics["envelope_errors"] += 1
            filtered_rows.append({**row, "candidates": []})
            evaluations.append(
                {
                    "case_id": row["case_id"],
                    "query_envelope": None,
                    "candidates": [],
                    "error": {"type": type(error).__name__, "message": str(error)},
                }
            )
            continue
        admitted_candidates: list[dict[str, Any]] = []
        candidate_results: list[dict[str, Any]] = []
        for candidate in row["candidates"][:CANDIDATE_LIMIT]:
            metrics["source_candidates"] += 1
            document = documents.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("policy candidate is absent from public corpus")
            try:
                evidence = envelope_alignment_evidence(envelope, document, evidence_index)
                admitted, reason_codes = _decision(candidate, evidence, configuration_id)
                if not set(reason_codes) <= REASON_CODES:
                    raise ValueError("unknown identity-envelope reason code")
                result = {
                    "knowledge_id": candidate["knowledge_id"],
                    "knowledge_uuid": candidate["knowledge_uuid"],
                    "source_rank": candidate["source_rank"],
                    **evidence,
                    "reason_codes": reason_codes,
                    "decision": "admit" if admitted else "abstain",
                    "error": None,
                }
            except Exception as error:  # noqa: BLE001 - failed evidence is an explicit failed gate
                admitted = False
                metrics["envelope_errors"] += 1
                result = {
                    "knowledge_id": candidate["knowledge_id"],
                    "knowledge_uuid": candidate["knowledge_uuid"],
                    "source_rank": candidate["source_rank"],
                    "query_envelope": envelope.as_dict(),
                    "reason_codes": [],
                    "decision": "abstain",
                    "error": {"type": type(error).__name__, "message": str(error)},
                }
            if admitted:
                admitted_candidates.append(candidate)
                metrics["admitted_candidates"] += 1
            else:
                metrics["abstained_candidates"] += 1
            candidate_results.append(result)
        if any(
            result["query_envelope"]["checksum"] != envelope.checksum
            for result in candidate_results
        ):
            raise ValueError("candidate evaluations disagree on query envelope")
        filtered_rows.append({**row, "candidates": admitted_candidates})
        evaluations.append(
            {
                "case_id": row["case_id"],
                "query_envelope": envelope.as_dict(),
                "candidates": candidate_results,
                "error": None,
            }
        )
    return filtered_rows, evaluations, metrics


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha(path: Path) -> str:
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
        if {path.name for path in directory.iterdir()} != set(outputs):
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


def _historical_source_hashes(root: Path) -> dict[str, str]:
    names = (
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
        Path(SOURCE),
    )
    return {str(path): _sha(root / path) for path in names}


def historical_calibration(root: Path) -> dict[str, Any]:
    """Rescore immutable public rows without invoking retrieval."""

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
    evidence_index = IdentityEvidenceIndex(catalog.documents)
    envelope_index = IdentityEnvelopeIndex(catalog.documents)
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
            historical_rows, documents, evidence_index, envelope_index, configuration_id
        )
        existing = summarize_existing(cases, filtered_existing, 0.0)
        filtered_anchor, evaluations_anchor, metrics_anchor = apply_policy(
            anchor_rows, documents, evidence_index, envelope_index, configuration_id
        )
        anchor = _score_anchor(anchor_pack, {**anchor_report["raw"], "rows": filtered_anchor}, 0.0)
        filtered_hic, evaluations_hic, metrics_hic = apply_policy(
            hic_rows, documents, evidence_index, envelope_index, configuration_id
        )
        hic = _summarize_hic(
            hic_pack,
            hic_rows,
            filtered_hic,
            metrics_hic["envelope_errors"],
        )
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
        envelope_errors = sum(
            metrics["envelope_errors"]
            for metrics in (metrics_existing, metrics_anchor, metrics_hic)
        )
        eligible = (
            existing["eligible"] and anchor["eligible"] and hic["eligible"] and envelope_errors == 0
        )
        summaries.append(
            {
                "configuration_id": configuration_id,
                "existing_223": existing,
                "anchor_v4_22": anchor,
                "hic_v1_24": hic,
                "selection_metrics": {
                    "negative_admitted_candidates": negative_admitted,
                    "positive_abstained_candidates": positive_abstained,
                    "envelope_errors": envelope_errors,
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
                "eligible": eligible,
            }
        )
    eligible_non_reference = [
        summary["configuration_id"]
        for summary in summaries
        if summary["configuration_id"] != "reference-anchor" and summary["eligible"]
    ]
    return {
        "schema_version": CALIBRATION_SCHEMA,
        "version": VERSION,
        "status": (
            "historical_calibration_pass"
            if eligible_non_reference
            else "historical_calibration_fail"
        ),
        "denominators": {"existing_public": 223, "anchor_confidence_v4": 22, "hic_v1": 24},
        "retrieval_calls_executed": 0,
        "sources": dict(sorted(_historical_source_hashes(root).items())),
        "summaries": summaries,
        "eligible_non_reference_configuration_ids": eligible_non_reference,
    }


def _policy_definitions() -> list[dict[str, Any]]:
    return [
        {
            "configuration_id": "reference-anchor",
            "ordered_rank_1_rules": ["admit_rank_1_for_comparison"],
        },
        {
            "configuration_id": "envelope-numeric",
            "ordered_rank_1_rules": ["reject_numeric_or_compact_guard", "otherwise_admit"],
        },
        {
            "configuration_id": "envelope-bilateral",
            "ordered_rank_1_rules": [
                "reject_numeric_or_compact_guard",
                "reject_different_anchor",
                "reject_bilateral_model_residual",
                "otherwise_admit",
            ],
        },
        {
            "configuration_id": "envelope-safe-form",
            "ordered_rank_1_rules": [
                "reject_numeric_or_compact_guard",
                "admit_complete_exact_or_shorthand",
                "reject_different_anchor_or_query_model_residual",
                "otherwise_admit",
            ],
        },
        {
            "configuration_id": "envelope-decision-list",
            "ordered_rank_1_rules": [
                "reject_numeric_or_compact_guard",
                "admit_complete_exact_or_year_equivalent",
                "reject_anchor_mismatch",
                "admit_bounded_fuzzy_without_model_residual",
                "reject_bilateral_model_residual",
                "otherwise_abstain_ambiguous",
            ],
        },
    ]


def build_protocol(root: Path) -> dict[str, Any]:
    calibration = historical_calibration(root)
    survivors = calibration["eligible_non_reference_configuration_ids"]
    if not survivors:
        raise ValueError("no non-reference identity-envelope policy passed historical calibration")
    calibration_summary = [
        {
            "configuration_id": summary["configuration_id"],
            "eligible": summary["eligible"],
            "selection_metrics": summary["selection_metrics"],
            "existing_counts": summary["existing_223"]["counts"],
            "anchor_v4_counts": summary["anchor_v4_22"]["counts"],
            "hic_v1_counts": summary["hic_v1_24"]["counts"],
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
        "historical_calibration": calibration_summary,
        "historical_eligible_configuration_ids": survivors,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "envelope": {
            "normalization": "identity-core-policy-v1",
            "anchor_fields": ["casting", "aliases"],
            "one_envelope_per_query": True,
            "allowed_century_prefixes": sorted(ALLOWED_CENTURY_PREFIXES),
            "conserve_alphanumeric_digit_runs": True,
            "categorical_states": {
                "envelope_status": sorted(ENVELOPE_STATES),
                "anchor_relation": sorted(ANCHOR_RELATIONS),
                "numeric_relation": sorted(NUMERIC_RELATIONS),
                "form_completion": sorted(FORM_COMPLETIONS),
                "alignment_strength": sorted(ALIGNMENT_STRENGTHS),
                "model_residual": sorted(MODEL_RESIDUALS),
                "compact_digit_guard": sorted(COMPACT_DIGIT_GUARDS),
            },
        },
        "policies": _policy_definitions(),
        "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
        "holdout": {
            "positive_count": 16,
            "negative_count": 16,
            "positive_styles": [
                "abbreviation_numeric",
                "contextual_noise",
                "single_edit",
                "spacing_punctuation",
            ],
            "negative_declarations_path": str(DECLARATIONS_PATH),
            "negative_declarations_schema": "pvr-human-knowledge-identity-envelope-negative-declarations-v2",
        },
        "gates": {
            "existing": GATES,
            "anchor_v4": {
                "valid_low_coverage_anchor_hits": 10,
                "missing_identity_nonempty": 0,
                "anchor_retrieval_errors": 0,
            },
            "hic_v1": {
                "positive_preservation_hits": 12,
                "absent_identity_nonempty": 0,
                "retrieval_errors": 0,
                "envelope_errors": 0,
            },
            "new": {
                "positive_preservation_hits": 16,
                "absent_identity_nonempty": 0,
                "retrieval_errors": 0,
                "envelope_errors": 0,
            },
        },
        "winner_order": [
            "eligible_only",
            "minimum_negative_admitted_candidates",
            "minimum_positive_abstained_candidates",
            "policy_preference",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def _protocol_manifest(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-envelope-protocol-manifest-v2",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }


def _calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-envelope v2 historical calibration",
        "",
        f"Status: `{report['status']}`.",
        "",
        "No new retrieval was executed. This report rescored the immutable 223 + 22 + 24 public rows.",
        "",
        "| configuration | eligible | existing positives | v4 positives | v4 negative nonempty | HIC positives | HIC negative nonempty | errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        existing = summary["existing_223"]["counts"]
        anchor = summary["anchor_v4_22"]["counts"]
        hic = summary["hic_v1_24"]["counts"]
        lines.append(
            "| {configuration_id} | {eligible} | {existing_hits}/168 | {anchor_hits}/10 | {anchor_negative} | {hic_hits}/12 | {hic_negative} | {errors} |".format(
                configuration_id=summary["configuration_id"],
                eligible=summary["eligible"],
                existing_hits=existing["existing_positive_hits_at_5"],
                anchor_hits=anchor["valid_low_coverage_anchor_hits"],
                anchor_negative=anchor["missing_identity_nonempty"],
                hic_hits=hic["positive_preservation_hits"],
                hic_negative=hic["absent_identity_nonempty"],
                errors=summary["selection_metrics"]["envelope_errors"],
            )
        )
    lines.extend(
        [
            "",
            "Eligible non-reference policies: "
            + (
                ", ".join(report["eligible_non_reference_configuration_ids"])
                if report["eligible_non_reference_configuration_ids"]
                else "none"
            )
            + ".",
            "",
            "Because no non-reference policy passed every historical gate, no protocol, holdout pack, raw retrieval, private evaluation, or runtime change is authorized.",
            "",
        ]
    )
    return "\n".join(lines)


def _calibration_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-envelope-calibration-manifest-v2",
        "version": VERSION,
        "calibration_sha256": hashlib.sha256(_json(report).encode()).hexdigest(),
        "source_sha256": report["sources"],
        "denominators": report["denominators"],
        "eligible_non_reference_configuration_ids": report[
            "eligible_non_reference_configuration_ids"
        ],
        "retrieval_calls_executed": report["retrieval_calls_executed"],
        "protocol_created": False,
        "pack_created": False,
        "raw_created": False,
        "private_local_artifacts_read": False,
    }


def _calibration_outputs(report: dict[str, Any]) -> dict[str, str]:
    return {
        CALIBRATION_JSON: _json(report),
        CALIBRATION_MARKDOWN: _calibration_markdown(report),
        CALIBRATION_MANIFEST: _json(_calibration_manifest(report)),
    }


def freeze_protocol(root: Path) -> str:
    calibration = historical_calibration(root)
    if not calibration["eligible_non_reference_configuration_ids"]:
        operation = _freeze_directory(
            root / REPORT_DIRECTORY,
            _calibration_outputs(calibration),
            "identity-envelope historical calibration failure",
        )
        return f"calibration_failed_{operation}"
    protocol = build_protocol(root)
    return _freeze_directory(
        root / PROTOCOL_DIRECTORY,
        {
            "protocol.json": _json(protocol),
            "protocol-manifest.json": _json(_protocol_manifest(protocol)),
        },
        "identity-envelope protocol",
    )


def validate_calibration_failure(root: Path) -> dict[str, Any]:
    report = historical_calibration(root)
    if report["eligible_non_reference_configuration_ids"]:
        raise ValueError("historical calibration is no longer a failure")
    if any((root / path).exists() for path in (PROTOCOL_DIRECTORY, PACK_DIRECTORY, RAW_DIRECTORY)):
        raise ValueError("failed calibration must not create protocol, pack, or raw artifacts")
    directory = root / REPORT_DIRECTORY
    if not directory.is_dir() or {path.name for path in directory.iterdir()} != set(
        _calibration_outputs(report)
    ):
        raise ValueError("historical calibration failure directory is partial or conflicting")
    for name, content in _calibration_outputs(report).items():
        _assert_file(directory / name, content)
    return report


def validate_protocol(root: Path) -> dict[str, Any]:
    expected = build_protocol(root)
    _assert_file(root / PROTOCOL_DIRECTORY / "protocol.json", _json(expected))
    _assert_file(
        root / PROTOCOL_DIRECTORY / "protocol-manifest.json",
        _json(_protocol_manifest(expected)),
    )
    return expected


def _positive_holdout_cases(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    cases = _cases(root)
    upstream_rows = {row["case_id"]: row for row in check_upstream(root)["raw"]["rows"]}
    anchor_pack = validate_anchor_pack(root)
    hic_pack = validate_hic_pack(root)
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
    by_style: dict[str, list[tuple[str, dict[str, Any], dict[str, Any]]]] = {}
    protocol_sha = _sha(root / PROTOCOL_DIRECTORY / "protocol.json")
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
        if (
            top["source_rank"] != 1
            or top["knowledge_id"] != expected_id
            or expected_id in used_documents
        ):
            continue
        style = case["challenge_style"]
        selection_key = hashlib.sha256(f"{protocol_sha}:{style}:{case_id}".encode()).hexdigest()
        by_style.setdefault(style, []).append((selection_key, case, top))

    selected: list[dict[str, Any]] = []
    selected_documents: set[str] = set()
    for style in protocol["holdout"]["positive_styles"]:
        style_selected = 0
        for _, case, top in sorted(by_style.get(style, []), key=lambda item: item[0]):
            if top["knowledge_id"] in selected_documents:
                continue
            selected_documents.add(top["knowledge_id"])
            style_selected += 1
            selected.append(
                {
                    "case_id": f"hie-pos-{len(selected) + 1:02d}",
                    "case_type": "positive_preservation",
                    "challenge_type": style,
                    "source_case_id": case["case_id"],
                    "query_text": case["query_text"],
                    "expected": {
                        "knowledge_id": top["knowledge_id"],
                        "knowledge_uuid": top["knowledge_uuid"],
                        "knowledge_type": top["knowledge_type"],
                    },
                }
            )
            if style_selected == 4:
                break
        if style_selected != 4:
            raise ValueError(f"insufficient family-disjoint positive cases for {style}")
    if len(selected) != 16 or len(selected_documents) != 16:
        raise ValueError("identity-envelope positives must use sixteen distinct documents")
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
    expected_categories = {
        "same_maker_different_model": 4,
        "conserved_numeric_or_alphanumeric_frame_conflict": 4,
        "compact_punctuation_digit_conservation": 4,
        "cross_maker_descriptor_overlap": 4,
    }
    category_counts: Counter[str] = Counter()
    identities: set[str] = set()
    queries: set[str] = set()
    rows: list[dict[str, Any]] = []
    for declaration in declarations["cases"]:
        required = {"case_id", "challenge_type", "query_text", "absent_identity"}
        if set(declaration) != required:
            raise ValueError("negative declaration fields differ from contract")
        normalized_identity = normalize_text(declaration["absent_identity"])
        normalized_query = normalize_text(declaration["query_text"])
        if (
            normalized_identity in public_identities
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
        raise ValueError("identity-envelope pack must contain thirty-two unique cases")
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
        "eligible_for": ["public_identity_envelope_development_only"],
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
        "schema_version": "pvr-human-knowledge-identity-envelope-pack-manifest-v2",
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
        "identity-envelope pack",
    )


def validate_pack(root: Path) -> dict[str, Any]:
    pack, manifest = build_pack(root)
    _assert_file(root / PACK_DIRECTORY / "development-pack.json", _json(pack))
    _assert_file(root / PACK_DIRECTORY / "development-pack-manifest.json", _json(manifest))
    return pack


def collect_payload(root: Path) -> dict[str, Any]:
    protocol = validate_protocol(root)
    pack = validate_pack(root)
    catalog = _catalog(root)
    envelope_index = IdentityEnvelopeIndex(catalog.documents)
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
        envelope = envelope_index.envelope(query)
        try:
            candidates, work = retriever.retrieve_with_work(extract_signals(query), CANDIDATE_LIMIT)
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
                "case_type": case["case_type"],
                "challenge_type": case["challenge_type"],
                "query_text": query,
                "query_envelope": envelope.as_dict(),
                **payload,
            }
        )
    if len(rows) != 32:
        raise ValueError("identity-envelope collection must contain thirty-two rows")
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
        "schema_version": "pvr-human-knowledge-identity-envelope-raw-manifest-v2",
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
        {"raw.json": _json(raw), "raw-manifest.json": _json(_raw_manifest(root, raw))},
        "identity-envelope raw",
    )
    return validate_raw(root), operation


def _contains_expected_key(value: Any) -> bool:
    if isinstance(value, dict):
        return "expected" in value or any(_contains_expected_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_expected_key(item) for item in value)
    return False


def _validate_raw_candidate(
    candidate: dict[str, Any], document: HumanKnowledgeDocument, query: str, rank: int
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
        or _contains_expected_key(raw)
        or len(raw.get("rows", [])) != 32
    ):
        raise ValueError("raw identity-envelope metadata differs from contract")
    catalog = _catalog(root)
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    envelope_index = IdentityEnvelopeIndex(catalog.documents)
    for case, row in zip(pack["cases"], raw["rows"], strict=True):
        if any(
            row.get(name) != case[name]
            for name in ("case_id", "case_type", "challenge_type", "query_text")
        ):
            raise ValueError("raw identity-envelope row differs from frozen pack")
        expected_envelope = envelope_index.envelope(row["query_text"])
        if row.get("query_envelope") != expected_envelope.as_dict():
            raise ValueError("raw query envelope differs from deterministic envelope")
        if row["error"] is not None and (row["candidates"] or row["work"] is not None):
            raise ValueError("errored raw row must not contain candidates or work")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = documents.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("raw candidate is absent from public corpus")
            _validate_raw_candidate(candidate, document, row["query_text"], rank)
    _assert_file(root / RAW_DIRECTORY / "raw-manifest.json", _json(_raw_manifest(root, raw)))
    return raw


def _summarize_new(
    pack: dict[str, Any],
    original_rows: list[dict[str, Any]],
    filtered_rows: list[dict[str, Any]],
    envelope_errors: int,
) -> dict[str, Any]:
    counts = {
        "positive_preservation_hits": 0,
        "positive_preservation_hits_at_1": 0,
        "absent_identity_nonempty": 0,
        "retrieval_errors": 0,
        "envelope_errors": envelope_errors,
        "source_candidates": 0,
        "admitted_candidates": 0,
    }
    case_results: list[dict[str, Any]] = []
    for case, original, filtered in zip(pack["cases"], original_rows, filtered_rows, strict=True):
        if case["case_id"] != original["case_id"] or case["case_id"] != filtered["case_id"]:
            raise ValueError("new scoring rows differ from frozen pack")
        counts["retrieval_errors"] += original["error"] is not None
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
            raise ValueError("unexpected identity-envelope holdout case type")
        case_results.append(result)
    expected_gates = {
        "positive_preservation_hits": 16,
        "absent_identity_nonempty": 0,
        "retrieval_errors": 0,
        "envelope_errors": 0,
    }
    gates = [
        {
            "name": name,
            "operator": "=",
            "threshold": expected,
            "actual": counts[name],
            "passed": counts[name] == expected,
        }
        for name, expected in expected_gates.items()
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
    calibration = historical_calibration(root)
    catalog = _catalog(root)
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    evidence_index = IdentityEvidenceIndex(catalog.documents)
    envelope_index = IdentityEnvelopeIndex(catalog.documents)
    positive_ids = {
        case["case_id"] for case in pack["cases"] if case["case_type"] == "positive_preservation"
    }
    calibration_by_id = {
        summary["configuration_id"]: summary for summary in calibration["summaries"]
    }
    summaries: list[dict[str, Any]] = []
    for configuration_id in POLICIES:
        filtered_rows, evaluations, metrics = apply_policy(
            raw["rows"], documents, evidence_index, envelope_index, configuration_id
        )
        holdout = _summarize_new(
            pack,
            raw["rows"],
            filtered_rows,
            metrics["envelope_errors"],
        )
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
        eligible = historical["eligible"] and holdout["eligible"]
        summaries.append(
            {
                "configuration_id": configuration_id,
                "historical": {
                    "eligible": historical["eligible"],
                    "existing_223": historical["existing_223"],
                    "anchor_v4_22": historical["anchor_v4_22"],
                    "hic_v1_24": historical["hic_v1_24"],
                },
                "new_holdout_32": holdout,
                "selection_metrics": {
                    "negative_admitted_candidates": negative_admitted,
                    "positive_abstained_candidates": positive_abstained,
                    "envelope_errors": historical["selection_metrics"]["envelope_errors"]
                    + metrics["envelope_errors"],
                },
                "candidate_metrics": metrics,
                "evaluations": evaluations,
                "eligible": eligible,
            }
        )
    eligible_summaries = [summary for summary in summaries if summary["eligible"]]
    winner = min(
        eligible_summaries,
        key=lambda summary: (
            summary["selection_metrics"]["negative_admitted_candidates"],
            summary["selection_metrics"]["positive_abstained_candidates"],
            PREFERENCE[summary["configuration_id"]],
        ),
        default=None,
    )
    return {
        "summaries": summaries,
        "winner": (
            {
                "configuration_id": winner["configuration_id"],
                "selection_metrics": winner["selection_metrics"],
                "historical_eligible_configuration_ids": protocol[
                    "historical_eligible_configuration_ids"
                ],
                "new_holdout_counts": winner["new_holdout_32"]["counts"],
                "status": "qualified_for_new_private_shadow_evaluation_design_only",
            }
            if winner is not None
            else None
        ),
    }


def _selection_sources(root: Path) -> dict[str, str]:
    paths = (
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


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-envelope v2 selection",
        "",
        f"Status: `{report['status']}`.",
        "",
        "| configuration | historical | new holdout | eligible | negatives admitted | positives abstained |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        lines.append(
            "| {configuration_id} | {historical} | {holdout} | {eligible} | {negative} | {positive} |".format(
                configuration_id=summary["configuration_id"],
                historical=summary["historical"]["eligible"],
                holdout=summary["new_holdout_32"]["eligible"],
                eligible=summary["eligible"],
                negative=summary["selection_metrics"]["negative_admitted_candidates"],
                positive=summary["selection_metrics"]["positive_abstained_candidates"],
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
    operation = _freeze_directory(
        root / REPORT_DIRECTORY,
        {"selection.json": _json(report), "selection.md": _markdown(report)},
        "identity-envelope selection",
    )
    return check(root), operation


def check(root: Path) -> dict[str, Any]:
    if not (root / PROTOCOL_DIRECTORY).exists():
        return validate_calibration_failure(root)
    raw = validate_raw(root)
    expected = _report(root, raw)
    _assert_file(root / REPORT_DIRECTORY / "selection.json", _json(expected))
    _assert_file(root / REPORT_DIRECTORY / "selection.md", _markdown(expected))
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description="Develop public query-global identity envelope")
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
