"""Develop public candidate-specific Human Knowledge identity contradiction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import cache
from pathlib import Path
from typing import Any

from .human_knowledge import HumanKnowledgeCandidate, HumanKnowledgeDocument
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
from .human_knowledge_anchor_confidence_development import SOURCE as ANCHOR_SOURCE
from .human_knowledge_anchor_confidence_development import _score_anchor
from .human_knowledge_anchor_confidence_development import check as check_anchor
from .human_knowledge_anchor_confidence_development import validate_pack as validate_anchor_pack
from .human_knowledge_identity import (
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
    IdentityCorePolicy,
)
from .human_knowledge_reranker_development import (
    REPORT_DIRECTORY as UPSTREAM_REPORT_DIRECTORY,
)
from .human_knowledge_reranker_development import SOURCE as UPSTREAM_SOURCE
from .human_knowledge_reranker_development import check as check_upstream
from .identity import normalize_text
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-identity-contradiction-development-v1"
PACK_SCHEMA = "pvr-human-knowledge-identity-contradiction-pack-v1"
PROTOCOL_SCHEMA = "pvr-human-knowledge-identity-contradiction-protocol-v1"
RAW_SCHEMA = "pvr-human-knowledge-identity-contradiction-raw-v1"
REPORT_SCHEMA = "pvr-human-knowledge-identity-contradiction-selection-v1"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
PACK_DIRECTORY = DATA_DIRECTORY / "pack"
PROTOCOL_DIRECTORY = DATA_DIRECTORY / "protocol"
RAW_DIRECTORY = DATA_DIRECTORY / "raw"
REPORT_DIRECTORY = Path("reports") / VERSION
SOURCE = "src/product_variant_resolver/human_knowledge_identity_contradiction_development.py"
CANDIDATE_LIMIT = 5
SECONDARY_THRESHOLD = 0.75
ATOMIC_SIMILARITY = 0.8
COMPACT_SIMILARITY = 0.85
MAX_GROUP_ATOMS = 4
POLICIES = (
    ("baseline-anchor", "baseline", None),
    ("numeric-only", "numeric", None),
    ("contradiction-050", "contradiction", 0.5),
    ("contradiction-075", "contradiction", 0.75),
    ("contradiction-100", "contradiction", 1.0),
    ("contradiction-125", "contradiction", 1.25),
    ("contradiction-150", "contradiction", 1.5),
)
PREFERENCE = {
    "baseline-anchor": 0,
    "numeric-only": 1,
    "contradiction-150": 2,
    "contradiction-125": 3,
    "contradiction-100": 4,
    "contradiction-075": 5,
    "contradiction-050": 6,
}
REASON_CODES = frozenset(
    {
        "no_contradiction",
        "numeric_model_conflict",
        "bilateral_identity_residual",
        "secondary_coverage_below_075",
    }
)

POSITIVE_SOURCE_CASE_IDS = (
    "frd-positive-0573861db69878eb-abbreviation-numeric",
    "frd-positive-08cb7fadb9fed12d-abbreviation-numeric",
    "frd-positive-1555c05ceeb491cb-abbreviation-numeric",
    "frd-positive-174efb9bce3a441e-contextual-noise",
    "frd-positive-18e55e067083dbd1-contextual-noise",
    "frd-positive-1b2a4227b4e5decd-contextual-noise",
    "frd-positive-356e4ef63275a661-single-edit",
    "frd-positive-39b248ce2f3723cd-single-edit",
    "frd-positive-3c9f928f085efaae-single-edit",
    "frd-positive-440103f8ef3c6b70-spacing-punctuation",
    "frd-positive-45af5b93f3f6650f-spacing-punctuation",
    "frd-positive-4bf5341a133d433b-spacing-punctuation",
)

NEGATIVE_CASE_SPECS = (
    (
        "hic-neg-01-honda-prelude",
        "same_maker_model_substitution",
        "loose Honda Prelude coupe collector model",
        "Honda Prelude",
    ),
    (
        "hic-neg-02-mazda-mx30",
        "same_maker_model_substitution",
        "Mazda MX-30 electric crossover miniature",
        "Mazda MX-30",
    ),
    (
        "hic-neg-03-bugatti-bolide",
        "same_maker_model_substitution",
        "Bugatti Bolide hypercar display model",
        "Bugatti Bolide",
    ),
    (
        "hic-neg-04-nissan-r33",
        "same_stem_numeric_conflict",
        "Nissan Skyline GT-R R33 carded model",
        "Nissan Skyline GT-R R33",
    ),
    (
        "hic-neg-05-bmw-m2",
        "same_stem_numeric_conflict",
        "premium BMW M2 competition coupe",
        "BMW M2",
    ),
    (
        "hic-neg-06-tesla-model-y",
        "same_stem_numeric_conflict",
        "Tesla Model Y performance diecast",
        "Tesla Model Y",
    ),
    (
        "hic-neg-07-mercedes-c63s",
        "compact_or_punctuated_conflict",
        "MercedesAMGC63S boxed miniature",
        "Mercedes-AMG C 63 S",
    ),
    (
        "hic-neg-08-toyota-gr86",
        "compact_or_punctuated_conflict",
        "ToyotaGR86 loose collector car",
        "Toyota GR86",
    ),
    (
        "hic-neg-09-audi-rs6",
        "compact_or_punctuated_conflict",
        "AudiRS6Avant premium wagon",
        "Audi RS 6 Avant",
    ),
    (
        "hic-neg-10-hyundai-ioniq5n",
        "cross_maker_descriptor_overlap",
        "Hyundai Ioniq 5 N performance miniature",
        "Hyundai Ioniq 5 N",
    ),
    (
        "hic-neg-11-dodge-viper",
        "cross_maker_descriptor_overlap",
        "Dodge Viper GTS performance coupe model",
        "Dodge Viper GTS",
    ),
    (
        "hic-neg-12-kia-ev6",
        "cross_maker_descriptor_overlap",
        "Kia EV6 GT performance diecast vehicle",
        "Kia EV6 GT",
    ),
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return value


def _source_hashes(root: Path) -> dict[str, str]:
    names = (
        *CORPUS_INPUTS,
        EXISTING_PACK,
        EXISTING_MANIFEST,
        ANCHOR_PACK_DIRECTORY / "development-pack.json",
        ANCHOR_PACK_DIRECTORY / "development-pack-manifest.json",
        UPSTREAM_REPORT_DIRECTORY / "selection.json",
        Path(ANCHOR_SOURCE),
        Path(UPSTREAM_SOURCE),
        Path(SOURCE),
    )
    return {str(path): _sha(root / path) for path in names}


def _positive_cases(root: Path) -> list[dict[str, Any]]:
    public_cases = {case["case_id"]: case for case in _load(root / EXISTING_PACK).get("cases", [])}
    upstream_rows = {row["case_id"]: row for row in check_upstream(root)["raw"]["rows"]}
    anchor_pack = validate_anchor_pack(root)
    used_source_ids = {
        case["source_case_id"]
        for case in anchor_pack["cases"]
        if case["source_case_id"] is not None
    }
    rows: list[dict[str, Any]] = []
    for source_case_id in POSITIVE_SOURCE_CASE_IDS:
        case = public_cases.get(source_case_id)
        raw = upstream_rows.get(source_case_id)
        if (
            case is None
            or raw is None
            or case.get("case_type") != "positive_family"
            or source_case_id in used_source_ids
            or not raw.get("candidates")
        ):
            raise ValueError("positive-preservation source case is unavailable")
        top = raw["candidates"][0]
        if (
            raw.get("dataset") != "existing"
            or top["source_rank"] != 1
            or top["knowledge_id"] != case["expected"]["review_family_id"]
            or top["knowledge_type"] != case["expected"]["knowledge_type"]
        ):
            raise ValueError("positive-preservation source is not a correct public rank 1")
        rows.append(
            {
                "case_id": f"hic-pos-{len(rows) + 1:02d}",
                "case_type": "positive_preservation",
                "challenge_type": case["challenge_style"],
                "source_case_id": source_case_id,
                "query_text": case["query_text"],
                "expected": {
                    "knowledge_id": top["knowledge_id"],
                    "knowledge_uuid": top["knowledge_uuid"],
                    "knowledge_type": top["knowledge_type"],
                },
            }
        )
    styles = Counter(row["challenge_type"] for row in rows)
    document_ids = {row["expected"]["knowledge_id"] for row in rows}
    if (
        styles
        != {
            "abbreviation_numeric": 3,
            "contextual_noise": 3,
            "single_edit": 3,
            "spacing_punctuation": 3,
        }
        or len(document_ids) < 10
    ):
        raise ValueError("positive-preservation balance differs from contract")
    return rows


def _negative_cases(root: Path) -> list[dict[str, Any]]:
    catalog = _catalog(root)
    public_identities = {
        normalize_text(identity)
        for document in catalog.documents
        for identity in document.character_identity_texts
    }
    anchor_pack = validate_anchor_pack(root)
    used_identities = {
        normalize_text(case["expected"]["absent_identity"])
        for case in anchor_pack["cases"]
        if case["case_type"] == "missing_identity_hard_negative"
    }
    used_queries = {normalize_text(case["query_text"]) for case in anchor_pack["cases"]}
    rows: list[dict[str, Any]] = []
    for case_id, challenge_type, query_text, absent_identity in NEGATIVE_CASE_SPECS:
        normalized_identity = normalize_text(absent_identity)
        normalized_query = normalize_text(query_text)
        if (
            normalized_identity in public_identities
            or normalized_identity in used_identities
            or normalized_query in used_queries
            or normalized_identity.replace(" ", "") not in normalized_query.replace(" ", "")
        ):
            raise ValueError("negative contradiction identity is not new and corpus-absent")
        rows.append(
            {
                "case_id": case_id,
                "case_type": "absent_identity_contradiction",
                "challenge_type": challenge_type,
                "source_case_id": None,
                "query_text": query_text,
                "expected": {"absent_identity": absent_identity, "must_abstain_all": True},
            }
        )
    challenges = Counter(row["challenge_type"] for row in rows)
    if challenges != {
        "same_maker_model_substitution": 3,
        "same_stem_numeric_conflict": 3,
        "compact_or_punctuated_conflict": 3,
        "cross_maker_descriptor_overlap": 3,
    }:
        raise ValueError("negative contradiction balance differs from contract")
    return rows


def build_pack(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    cases = [*_positive_cases(root), *_negative_cases(root)]
    if len(cases) != 24 or len({case["case_id"] for case in cases}) != 24:
        raise ValueError("identity-contradiction pack must contain 24 unique cases")
    pack = {
        "schema_version": PACK_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_retrieval",
        "sources": dict(sorted(_source_hashes(root).items())),
        "case_counts": {
            "positive_preservation": 12,
            "absent_identity_contradiction": 12,
        },
        "positive_challenge_counts": dict(
            sorted(Counter(case["challenge_type"] for case in cases[:12]).items())
        ),
        "negative_challenge_counts": dict(
            sorted(Counter(case["challenge_type"] for case in cases[12:]).items())
        ),
        "cases": cases,
        "eligible_for": ["public_identity_contradiction_development_only"],
        "excluded_from": [
            "private_evaluation",
            "runtime_activation",
            "canonical_truth",
            "release_variant_truth",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    manifest = {
        "schema_version": "pvr-human-knowledge-identity-contradiction-pack-manifest-v1",
        "version": VERSION,
        "pack_sha256": hashlib.sha256(_json(pack).encode()).hexdigest(),
        "source_sha256": pack["sources"],
        "case_counts": pack["case_counts"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    return pack, manifest


@dataclass(frozen=True, slots=True)
class IdentityAtom:
    text: str
    start: int
    end: int
    source_token: str


@dataclass(frozen=True, slots=True)
class AtomAlignment:
    candidate_start: int
    candidate_end: int
    query_start: int
    query_end: int
    mode: str
    similarity: float


class IdentityEvidenceIndex:
    def __init__(self, documents: tuple[HumanKnowledgeDocument, ...]) -> None:
        if not documents:
            raise ValueError("identity evidence index requires public documents")
        document_atoms: list[set[str]] = []
        for document in documents:
            values: set[str] = set()
            for identity in document.character_identity_texts:
                values.update(atom.text for atom in atomize(identity)[1])
            document_atoms.append(values)
        frequencies = Counter(atom for atoms in document_atoms for atom in atoms)
        count = len(documents)
        self.idf = {
            atom: math.log((count + 1) / (frequency + 1)) + 1
            for atom, frequency in frequencies.items()
        }
        self.maximum_idf = math.log(count + 1) + 1

    def weight(self, atom: IdentityAtom) -> float:
        if (
            atom.text.isalpha()
            and len(atom.text) == 1
            and not any(character.isdigit() for character in atom.source_token)
        ):
            return 0.0
        return self.idf.get(atom.text, self.maximum_idf) / self.maximum_idf


def atomize(text: str) -> tuple[str, tuple[IdentityAtom, ...]]:
    core = IdentityCorePolicy().core(text)
    atoms: list[IdentityAtom] = []
    for token_match in re.finditer(r"\S+", core):
        source_token = token_match.group()
        for atom_match in re.finditer(r"[a-z]+|\d+", source_token):
            atoms.append(
                IdentityAtom(
                    atom_match.group(),
                    token_match.start() + atom_match.start(),
                    token_match.start() + atom_match.end(),
                    source_token,
                )
            )
    return core, tuple(atoms)


def _compact(atoms: tuple[IdentityAtom, ...]) -> str:
    return "".join(atom.text for atom in atoms)


def _ocr_form(value: str) -> str:
    if not any(character.isdigit() for character in value):
        return value
    return value.translate(str.maketrans("oil", "011"))


def _model_frame(token: str) -> tuple[str, tuple[str, ...]] | None:
    if not re.fullmatch(r"[a-z]*\d+[a-z]*", token) or not any(
        character.isalpha() for character in token
    ):
        return None
    return re.sub(r"\d+", "#", token), tuple(re.findall(r"\d+", token))


def _same_frame_numeric_conflict(query: str, candidate: str) -> bool:
    query_frame = _model_frame(query)
    candidate_frame = _model_frame(candidate)
    return bool(
        query_frame
        and candidate_frame
        and query_frame[0] == candidate_frame[0]
        and query_frame[1] != candidate_frame[1]
        and _ocr_form(query) != _ocr_form(candidate)
    )


def _match_mode(
    query: tuple[IdentityAtom, ...], candidate: tuple[IdentityAtom, ...]
) -> tuple[str, float] | None:
    query_text = _compact(query)
    candidate_text = _compact(candidate)
    if _same_frame_numeric_conflict(query_text, candidate_text):
        return None
    if query_text == candidate_text:
        return ("exact" if len(query) == len(candidate) == 1 else "compact_exact", 1.0)
    if _ocr_form(query_text) == _ocr_form(candidate_text):
        return "ocr_numeric_substitution", 1.0
    if len(query) == len(candidate) == 1:
        shorter, longer = sorted((query_text, candidate_text), key=len)
        if shorter.isalpha() and len(shorter) >= 2 and longer.startswith(shorter):
            return "prefix_abbreviation", len(shorter) / len(longer)
        similarity = SequenceMatcher(None, query_text, candidate_text).ratio()
        if similarity >= ATOMIC_SIMILARITY:
            return "fuzzy_atom", similarity
        return None
    if re.findall(r"\d+", query_text) != re.findall(r"\d+", candidate_text):
        return None
    similarity = SequenceMatcher(None, query_text, candidate_text).ratio()
    if similarity >= COMPACT_SIMILARITY:
        return "compact_fuzzy", similarity
    return None


def _alignment_key(
    alignments: tuple[AtomAlignment, ...],
    query: tuple[IdentityAtom, ...],
    candidate: tuple[IdentityAtom, ...],
    index: IdentityEvidenceIndex,
) -> tuple[float, float, float, int]:
    candidate_indices = {
        position
        for alignment in alignments
        for position in range(alignment.candidate_start, alignment.candidate_end)
    }
    query_indices = {
        position
        for alignment in alignments
        for position in range(alignment.query_start, alignment.query_end)
    }
    return (
        sum(index.weight(candidate[position]) for position in candidate_indices),
        sum(index.weight(query[position]) for position in query_indices),
        sum(alignment.similarity for alignment in alignments),
        -len(alignments),
    )


def _ordered_alignment(
    query: tuple[IdentityAtom, ...],
    candidate: tuple[IdentityAtom, ...],
    index: IdentityEvidenceIndex,
) -> tuple[AtomAlignment, ...]:
    @cache
    def solve(candidate_position: int, query_position: int) -> tuple[AtomAlignment, ...]:
        if candidate_position >= len(candidate) or query_position >= len(query):
            return ()
        options = [
            solve(candidate_position + 1, query_position),
            solve(candidate_position, query_position + 1),
        ]
        for candidate_size in range(
            1, min(MAX_GROUP_ATOMS, len(candidate) - candidate_position) + 1
        ):
            for query_size in range(1, min(MAX_GROUP_ATOMS, len(query) - query_position) + 1):
                result = _match_mode(
                    query[query_position : query_position + query_size],
                    candidate[candidate_position : candidate_position + candidate_size],
                )
                if result is None:
                    continue
                mode, similarity = result
                options.append(
                    (
                        AtomAlignment(
                            candidate_position,
                            candidate_position + candidate_size,
                            query_position,
                            query_position + query_size,
                            mode,
                            similarity,
                        ),
                        *solve(candidate_position + candidate_size, query_position + query_size),
                    )
                )
        return max(
            options,
            key=lambda value: _alignment_key(value, query, candidate, index),
        )

    return solve(0, 0)


def _numeric_conflict(query: tuple[IdentityAtom, ...], candidate: tuple[IdentityAtom, ...]) -> bool:
    query_tokens = {atom.source_token for atom in query}
    candidate_tokens = {atom.source_token for atom in candidate}
    return any(
        _same_frame_numeric_conflict(query_token, candidate_token)
        for query_token in query_tokens
        for candidate_token in candidate_tokens
    )


def _atom_payload(atom: IdentityAtom, weight: float) -> dict[str, Any]:
    return {
        "atom": atom.text,
        "source_token": atom.source_token,
        "start": atom.start,
        "end": atom.end,
        "weight": weight,
    }


def alignment_evidence(
    query_text: str,
    document: HumanKnowledgeDocument,
    index: IdentityEvidenceIndex,
) -> dict[str, Any]:
    query_core, query_atoms = atomize(query_text)
    if not query_atoms:
        raise ValueError("query has no identity atoms")
    choices: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    identities = tuple(dict.fromkeys(document.character_identity_texts))
    for identity_number, identity in enumerate(identities):
        candidate_core, candidate_atoms = atomize(identity)
        if not candidate_atoms:
            raise ValueError("candidate identity has no atoms")
        minimum = min(len(query_atoms), max(1, len(candidate_atoms) - 2))
        maximum = min(len(query_atoms), len(candidate_atoms) + 2)
        for size in range(minimum, maximum + 1):
            for start in range(len(query_atoms) - size + 1):
                window = query_atoms[start : start + size]
                alignments = _ordered_alignment(window, candidate_atoms, index)
                matched_candidate = {
                    position
                    for alignment in alignments
                    for position in range(alignment.candidate_start, alignment.candidate_end)
                }
                matched_query = {
                    position
                    for alignment in alignments
                    for position in range(alignment.query_start, alignment.query_end)
                }
                unmatched_candidate = [
                    atom
                    for position, atom in enumerate(candidate_atoms)
                    if position not in matched_candidate
                ]
                unmatched_query = [
                    atom for position, atom in enumerate(window) if position not in matched_query
                ]
                query_residual = sum(index.weight(atom) for atom in unmatched_query)
                candidate_residual = sum(index.weight(atom) for atom in unmatched_candidate)
                bilateral = min(query_residual, candidate_residual)
                matched_weight = sum(
                    index.weight(candidate_atoms[position]) for position in matched_candidate
                )
                total_candidate_weight = sum(index.weight(atom) for atom in candidate_atoms)
                matched_ratio = (
                    matched_weight / total_candidate_weight if total_candidate_weight else 0.0
                )
                absolute_alignments = [
                    {
                        "candidate_atoms": [
                            atom.text
                            for atom in candidate_atoms[
                                alignment.candidate_start : alignment.candidate_end
                            ]
                        ],
                        "query_atoms": [
                            atom.text
                            for atom in window[alignment.query_start : alignment.query_end]
                        ],
                        "candidate_start": alignment.candidate_start,
                        "candidate_end": alignment.candidate_end,
                        "query_start": start + alignment.query_start,
                        "query_end": start + alignment.query_end,
                        "mode": alignment.mode,
                        "similarity": alignment.similarity,
                    }
                    for alignment in alignments
                ]
                payload = {
                    "candidate_identity": candidate_core,
                    "candidate_identity_kind": "casting" if identity_number == 0 else "alias",
                    "query_core": query_core,
                    "query_span_text": query_core[window[0].start : window[-1].end],
                    "query_span_start": window[0].start,
                    "query_span_end": window[-1].end,
                    "alignments": absolute_alignments,
                    "unmatched_query_atoms": [
                        _atom_payload(atom, index.weight(atom)) for atom in unmatched_query
                    ],
                    "unmatched_candidate_atoms": [
                        _atom_payload(atom, index.weight(atom)) for atom in unmatched_candidate
                    ],
                    "query_residual": query_residual,
                    "candidate_residual": candidate_residual,
                    "bilateral_residual": bilateral,
                    "numeric_conflict": _numeric_conflict(window, candidate_atoms),
                }
                key = (
                    matched_ratio,
                    matched_weight,
                    -abs(size - len(candidate_atoms)),
                    sum(alignment.similarity for alignment in alignments),
                    size,
                    -start,
                    -identity_number,
                    candidate_core,
                )
                choices.append((key, payload))
    if not choices:
        raise ValueError("no bounded query identity span exists")
    return max(choices, key=lambda choice: choice[0])[1]


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


def freeze_pack(root: Path) -> str:
    pack, manifest = build_pack(root)
    return _freeze_directory(
        root / PACK_DIRECTORY,
        {"development-pack.json": _json(pack), "development-pack-manifest.json": _json(manifest)},
        "identity-contradiction pack",
    )


def validate_pack(root: Path) -> dict[str, Any]:
    pack, manifest = build_pack(root)
    directory = root / PACK_DIRECTORY
    _assert_file(directory / "development-pack.json", _json(pack))
    _assert_file(directory / "development-pack-manifest.json", _json(manifest))
    return pack


def build_protocol(root: Path) -> dict[str, Any]:
    pack = validate_pack(root)
    sources = {
        **_source_hashes(root),
        str(PACK_DIRECTORY / "development-pack.json"): _sha(
            root / PACK_DIRECTORY / "development-pack.json"
        ),
        str(PACK_DIRECTORY / "development-pack-manifest.json"): _sha(
            root / PACK_DIRECTORY / "development-pack-manifest.json"
        ),
    }
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_retrieval",
        "sources": dict(sorted(sources.items())),
        "query_counts": {
            "existing_public": 223,
            "anchor_confidence_v4": 22,
            "new_identity_contradiction": len(pack["cases"]),
        },
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "alignment": {
            "normalization": "identity-core-policy-v1",
            "allowed_fields": ["casting", "aliases"],
            "atom_pattern": "[a-z]+|[0-9]+",
            "query_window_delta": 2,
            "maximum_group_atoms": MAX_GROUP_ATOMS,
            "atomic_similarity": ATOMIC_SIMILARITY,
            "compact_similarity": COMPACT_SIMILARITY,
            "ocr_substitutions": {"o": "0", "i": "1", "l": "1"},
            "residual_weight": "public_identity_atom_idf_divided_by_maximum_idf",
            "bilateral_residual": "min(query_residual,candidate_residual)",
            "same_frame_numeric_conflict": True,
        },
        "policies": [
            {"configuration_id": name, "mode": mode, "bilateral_threshold": threshold}
            for name, mode, threshold in POLICIES
        ],
        "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
        "gates": {
            "existing": GATES,
            "anchor_v4": {
                "valid_low_coverage_anchor_hits": 10,
                "missing_identity_nonempty": 0,
                "anchor_retrieval_errors": 0,
            },
            "new": {
                "positive_preservation_hits": 12,
                "absent_identity_nonempty": 0,
                "retrieval_errors": 0,
                "contradiction_errors": 0,
            },
        },
        "winner_order": [
            "eligible_only",
            "minimum_negative_admitted_candidates",
            "minimum_positive_abstained_candidates",
            "policy_preference",
        ],
        "eligible_for": ["new_versioned_private_shadow_evaluation_design_only"],
        "excluded_from": [
            "runtime_activation",
            "canonical_truth",
            "private_tuning",
            "release_variant_truth",
            "color_truth",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def _protocol_manifest(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-contradiction-protocol-manifest-v1",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def freeze_protocol(root: Path) -> str:
    protocol = build_protocol(root)
    return _freeze_directory(
        root / PROTOCOL_DIRECTORY,
        {
            "protocol.json": _json(protocol),
            "protocol-manifest.json": _json(_protocol_manifest(protocol)),
        },
        "identity-contradiction protocol",
    )


def validate_protocol(root: Path) -> dict[str, Any]:
    protocol = build_protocol(root)
    directory = root / PROTOCOL_DIRECTORY
    _assert_file(directory / "protocol.json", _json(protocol))
    _assert_file(directory / "protocol-manifest.json", _json(_protocol_manifest(protocol)))
    return protocol


def _candidate(candidate: HumanKnowledgeCandidate, query: str) -> dict[str, Any]:
    return {
        "knowledge_id": candidate.document.knowledge_id,
        "knowledge_uuid": str(candidate.document.knowledge_uuid),
        "knowledge_type": candidate.document.knowledge_type,
        "casting_id": getattr(candidate.document, "casting_id", None),
        "source_rank": candidate.rrf_rank,
        "source_rrf_score": candidate.rrf_score,
        "sparse_rank": candidate.sparse_rank,
        "sparse_score": candidate.sparse_score,
        "dense_rank": candidate.dense_rank,
        "dense_score": candidate.dense_score,
        "character_rank": candidate.character_rank,
        "character_score": candidate.character_score,
        "matched_tokens": list(candidate.matched_tokens),
        "identity_token_coverage": identity_token_coverage(query, candidate.document),
    }


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
            candidates, work = retriever.retrieve_with_work(extract_signals(query), CANDIDATE_LIMIT)
            payload = {
                "candidates": [_candidate(candidate, query) for candidate in candidates],
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
                **payload,
            }
        )
    if len(rows) != 24:
        raise ValueError("identity-contradiction collection must contain 24 rows")
    return {
        "schema_version": RAW_SCHEMA,
        "version": VERSION,
        "status": "label_blind_raw_retrieval_complete",
        "protocol_sha256": _sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "retrieval_calls": 24,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": protocol["base_retriever"],
        "private_local_artifacts_read": False,
        "rows": rows,
    }


def _raw_manifest(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-human-knowledge-identity-contradiction-raw-manifest-v1",
        "version": VERSION,
        "raw_sha256": hashlib.sha256(_json(raw).encode()).hexdigest(),
        "protocol_sha256": _sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "retrieval_calls": 24,
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
        "identity-contradiction raw",
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
        or raw.get("retrieval_calls") != 24
        or raw.get("candidate_limit") != CANDIDATE_LIMIT
        or raw.get("protocol_sha256") != _sha(root / PROTOCOL_DIRECTORY / "protocol.json")
        or raw.get("base_retriever") != protocol["base_retriever"]
        or raw.get("private_local_artifacts_read") is not False
        or _contains_expected_key(raw)
        or len(raw.get("rows", [])) != 24
    ):
        raise ValueError("raw identity-contradiction metadata differs from contract")
    documents = {str(document.knowledge_uuid): document for document in _catalog(root).documents}
    for case, row in zip(pack["cases"], raw["rows"], strict=True):
        if any(
            row.get(name) != case[name]
            for name in ("case_id", "case_type", "challenge_type", "query_text")
        ):
            raise ValueError("raw identity-contradiction row differs from frozen pack")
        if row["error"] is not None and (row["candidates"] or row["work"] is not None):
            raise ValueError("errored raw row must not contain candidates or work")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = documents.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("raw candidate is absent from public corpus")
            _validate_raw_candidate(candidate, document, row["query_text"], rank)
    _assert_file(root / RAW_DIRECTORY / "raw-manifest.json", _json(_raw_manifest(root, raw)))
    return raw


def _decision(
    candidate: dict[str, Any],
    evidence: dict[str, Any],
    mode: str,
    threshold: float | None,
) -> tuple[bool, list[str]]:
    if candidate["source_rank"] != 1:
        admitted = candidate["identity_token_coverage"] + 1e-12 >= SECONDARY_THRESHOLD
        return admitted, ["no_contradiction" if admitted else "secondary_coverage_below_075"]
    if mode == "baseline":
        return True, ["no_contradiction"]
    if evidence["numeric_conflict"]:
        return False, ["numeric_model_conflict"]
    if mode == "numeric":
        return True, ["no_contradiction"]
    if mode != "contradiction" or threshold is None:
        raise ValueError("unknown identity-contradiction policy")
    if evidence["bilateral_residual"] + 1e-12 >= threshold:
        return False, ["bilateral_identity_residual"]
    return True, ["no_contradiction"]


def apply_policy(
    rows: list[dict[str, Any]],
    documents: dict[str, HumanKnowledgeDocument],
    index: IdentityEvidenceIndex,
    configuration_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    policy = next((item for item in POLICIES if item[0] == configuration_id), None)
    if policy is None:
        raise ValueError("unknown identity-contradiction configuration")
    _, mode, threshold = policy
    filtered_rows: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    metrics = {
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
        "contradiction_errors": 0,
    }
    for row in rows:
        admitted_candidates = []
        candidate_results = []
        for candidate in row["candidates"][:CANDIDATE_LIMIT]:
            metrics["source_candidates"] += 1
            document = documents.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("policy candidate is absent from public corpus")
            try:
                evidence = alignment_evidence(row["query_text"], document, index)
                admitted, reason_codes = _decision(candidate, evidence, mode, threshold)
                if not set(reason_codes) <= REASON_CODES:
                    raise ValueError("unknown contradiction reason code")
                result = {
                    "knowledge_id": candidate["knowledge_id"],
                    "knowledge_uuid": candidate["knowledge_uuid"],
                    "source_rank": candidate["source_rank"],
                    **evidence,
                    "reason_codes": reason_codes,
                    "decision": "admit" if admitted else "abstain",
                    "error": None,
                }
            except Exception as error:  # noqa: BLE001 - score errors are explicit failed gates
                admitted = False
                metrics["contradiction_errors"] += 1
                result = {
                    "knowledge_id": candidate["knowledge_id"],
                    "knowledge_uuid": candidate["knowledge_uuid"],
                    "source_rank": candidate["source_rank"],
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
        filtered_rows.append({**row, "candidates": admitted_candidates})
        evaluations.append({"case_id": row["case_id"], "candidates": candidate_results})
    return filtered_rows, evaluations, metrics


def _summarize_new(
    pack: dict[str, Any],
    original_rows: list[dict[str, Any]],
    filtered_rows: list[dict[str, Any]],
    contradiction_errors: int,
) -> dict[str, Any]:
    counts = {
        "positive_preservation_hits": 0,
        "positive_preservation_hits_at_1": 0,
        "absent_identity_nonempty": 0,
        "retrieval_errors": 0,
        "contradiction_errors": contradiction_errors,
        "source_candidates": 0,
        "admitted_candidates": 0,
    }
    case_results = []
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
            raise ValueError("unexpected new identity-contradiction case type")
        case_results.append(result)
    expected_gates = {
        "positive_preservation_hits": 12,
        "absent_identity_nonempty": 0,
        "retrieval_errors": 0,
        "contradiction_errors": 0,
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


def _selection_sources(root: Path) -> dict[str, str]:
    protocol = build_protocol(root)
    return {
        **protocol["sources"],
        str(PROTOCOL_DIRECTORY / "protocol.json"): _sha(
            root / PROTOCOL_DIRECTORY / "protocol.json"
        ),
        str(PROTOCOL_DIRECTORY / "protocol-manifest.json"): _sha(
            root / PROTOCOL_DIRECTORY / "protocol-manifest.json"
        ),
        str(RAW_DIRECTORY / "raw.json"): _sha(root / RAW_DIRECTORY / "raw.json"),
        str(RAW_DIRECTORY / "raw-manifest.json"): _sha(root / RAW_DIRECTORY / "raw-manifest.json"),
    }


def score(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    upstream = check_upstream(root)
    anchor_report = check_anchor(root)
    anchor_pack = validate_anchor_pack(root)
    pack = validate_pack(root)
    catalog = _catalog(root)
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    index = IdentityEvidenceIndex(catalog.documents)
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
    new_positive = {
        case["case_id"] for case in pack["cases"] if case["case_type"] == "positive_preservation"
    }
    summaries = []
    for configuration_id, _, _ in POLICIES:
        existing_rows, existing_evaluations, existing_metrics = apply_policy(
            upstream["raw"]["rows"], documents, index, configuration_id
        )
        existing = summarize_existing(cases, existing_rows, 0.0)
        anchor_rows, anchor_evaluations, anchor_metrics = apply_policy(
            anchor_report["raw"]["rows"], documents, index, configuration_id
        )
        anchor = _score_anchor(anchor_pack, {**anchor_report["raw"], "rows": anchor_rows}, 0.0)
        new_rows, new_evaluations, new_metrics = apply_policy(
            raw["rows"], documents, index, configuration_id
        )
        new = _summarize_new(pack, raw["rows"], new_rows, new_metrics["contradiction_errors"])
        evaluation_sets = (
            (upstream["raw"]["rows"], existing_rows, positive_existing),
            (anchor_report["raw"]["rows"], anchor_rows, anchor_positive),
            (raw["rows"], new_rows, new_positive),
        )
        positive_abstained = sum(
            len(source["candidates"]) - len(admitted["candidates"])
            for source_rows, admitted_rows, positive_ids in evaluation_sets
            for source, admitted in zip(source_rows, admitted_rows, strict=True)
            if source["case_id"] in positive_ids
        )
        negative_admitted = sum(
            len(row["candidates"])
            for case, row in zip(anchor_pack["cases"], anchor_rows, strict=True)
            if case["case_type"] == "missing_identity_hard_negative"
        ) + sum(
            len(row["candidates"])
            for case, row in zip(pack["cases"], new_rows, strict=True)
            if case["case_type"] == "absent_identity_contradiction"
        )
        contradiction_errors = (
            existing_metrics["contradiction_errors"]
            + anchor_metrics["contradiction_errors"]
            + new_metrics["contradiction_errors"]
        )
        eligible = (
            existing["eligible"]
            and anchor["eligible"]
            and new["eligible"]
            and contradiction_errors == 0
        )
        summaries.append(
            {
                "configuration_id": configuration_id,
                "existing": existing,
                "anchor_v4": anchor,
                "new": new,
                "selection_metrics": {
                    "negative_admitted_candidates": negative_admitted,
                    "positive_abstained_candidates": positive_abstained,
                    "contradiction_errors": contradiction_errors,
                },
                "candidate_metrics": {
                    "existing": existing_metrics,
                    "anchor_v4": anchor_metrics,
                    "new": new_metrics,
                },
                "evaluations": {
                    "existing": existing_evaluations,
                    "anchor_v4": anchor_evaluations,
                    "new": new_evaluations,
                },
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
                "existing_counts": winner["existing"]["counts"],
                "anchor_v4_counts": winner["anchor_v4"]["counts"],
                "new_counts": winner["new"]["counts"],
                "status": "qualified_for_new_private_shadow_evaluation_design_only",
            }
            if winner is not None
            else None
        ),
    }


def _report(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "version": VERSION,
        "status": "public_development_selection_complete_not_runtime",
        "protocol_sha256": raw["protocol_sha256"],
        "raw_sha256": _sha(root / RAW_DIRECTORY / "raw.json"),
        "sources": dict(sorted(_selection_sources(root).items())),
        "private_local_artifacts_read": False,
        "limitations": [
            "public_curated_development_only",
            "deterministic_alignment_not_semantic_model",
            "no_private_local_evaluation",
            "winner_not_runtime_activated",
        ],
        **score(root, raw),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge identity-contradiction selection",
        "",
        "Public-development selection only; private evaluation and runtime are unchanged.",
        "",
        "| Configuration | Eligible | Existing R@5 | V4 anchors | V4 missing nonempty | New positives | New absent nonempty |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        existing = summary["existing"]["counts"]
        anchor = summary["anchor_v4"]["counts"]
        new = summary["new"]["counts"]
        lines.append(
            f"| {summary['configuration_id']} | {'yes' if summary['eligible'] else 'no'} | "
            f"{existing['existing_positive_hits_at_5']}/168 | "
            f"{anchor['valid_low_coverage_anchor_hits']}/10 | "
            f"{anchor['missing_identity_nonempty']}/12 | "
            f"{new['positive_preservation_hits']}/12 | "
            f"{new['absent_identity_nonempty']}/12 |"
        )
    lines.extend(["", "## Selection", ""])
    if report["winner"] is None:
        lines.append("No configuration passed every frozen recall and contradiction-safety gate.")
    else:
        lines.append(
            f"Selected **{report['winner']['configuration_id']}** for a new private shadow-evaluation "
            "design only."
        )
    lines.extend(["", "The selection is not active in the API or Dual RAG runtime.", ""])
    return "\n".join(lines)


def write_selection(root: Path) -> tuple[dict[str, Any], str]:
    if (root / REPORT_DIRECTORY).exists():
        return check(root), "unchanged"
    raw = validate_raw(root)
    report = _report(root, raw)
    operation = _freeze_directory(
        root / REPORT_DIRECTORY,
        {"selection.json": _json(report), "selection.md": _markdown(report)},
        "identity-contradiction selection",
    )
    return check(root), operation


def check(root: Path) -> dict[str, Any]:
    raw = validate_raw(root)
    report = _load(root / REPORT_DIRECTORY / "selection.json")
    if (
        report.get("schema_version") != REPORT_SCHEMA
        or report.get("protocol_sha256") != raw["protocol_sha256"]
        or report.get("raw_sha256") != _sha(root / RAW_DIRECTORY / "raw.json")
        or report.get("sources") != dict(sorted(_selection_sources(root).items()))
        or report.get("private_local_artifacts_read") is not False
    ):
        raise ValueError("identity-contradiction report metadata differs from contract")
    rescored = score(root, raw)
    if (
        report.get("summaries") != rescored["summaries"]
        or report.get("winner") != rescored["winner"]
    ):
        raise ValueError("identity-contradiction selection differs from deterministic scoring")
    _assert_file(root / REPORT_DIRECTORY / "selection.md", _markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Develop public identity-contradiction admission")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    phases = parser.add_mutually_exclusive_group(required=True)
    phases.add_argument("--freeze-pack", action="store_true")
    phases.add_argument("--freeze-protocol", action="store_true")
    phases.add_argument("--collect", action="store_true")
    phases.add_argument("--score", action="store_true")
    phases.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_pack:
        output = {"operation": freeze_pack(root), "retrieval_executed": False, "cases": 24}
    elif arguments.freeze_protocol:
        output = {
            "operation": freeze_protocol(root),
            "retrieval_executed": False,
            "configurations": len(POLICIES),
        }
    elif arguments.collect:
        raw, operation = collect(root)
        output = {"operation": operation, "retrieval_calls": raw["retrieval_calls"]}
    elif arguments.score:
        report, operation = write_selection(root)
        output = {"operation": operation, "winner": report["winner"]}
    else:
        report = check(root)
        output = {"operation": "valid", "winner": report["winner"]}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
