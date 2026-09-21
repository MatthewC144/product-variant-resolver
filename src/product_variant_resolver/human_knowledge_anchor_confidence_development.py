"""Develop public-only rank-1 confidence for Human Knowledge admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    FALSE_POSITIVE_DATA_DIRECTORY,
    FALSE_POSITIVE_SOURCE,
    GATES,
    _cases,
    _catalog,
    identity_token_coverage,
)
from .human_knowledge_anchor_admission_development import summarize as summarize_existing
from .human_knowledge_identity import HumanKnowledgeIdentityRetriever, HumanKnowledgeV4Config
from .human_knowledge_reranker_development import (
    REPORT_DIRECTORY as UPSTREAM_REPORT_DIRECTORY,
)
from .human_knowledge_reranker_development import SOURCE as UPSTREAM_SOURCE
from .human_knowledge_reranker_development import check as check_upstream
from .identity import normalize_text
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-anchor-confidence-development-v4"
PACK_SCHEMA = "pvr-human-knowledge-anchor-confidence-pack-v4"
PROTOCOL_SCHEMA = "pvr-human-knowledge-anchor-confidence-protocol-v4"
REPORT_SCHEMA = "pvr-human-knowledge-anchor-confidence-selection-v4"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
PACK_DIRECTORY = DATA_DIRECTORY / "pack"
PROTOCOL_DIRECTORY = DATA_DIRECTORY / "protocol"
REPORT_DIRECTORY = Path("reports") / VERSION
SOURCE = "src/product_variant_resolver/human_knowledge_anchor_confidence_development.py"
CANDIDATE_LIMIT = 5
SECONDARY_THRESHOLD = 0.75
POSITIVE_SOURCE_CASE_IDS = (
    "frd-positive-356e4ef63275a661-spacing-punctuation",
    "frd-positive-526b697937fde7cc-abbreviation-numeric",
    "frd-positive-526b697937fde7cc-spacing-punctuation",
    "frd-positive-7e221ec8ecd02815-spacing-punctuation",
    "frd-positive-85226ac5ac0d3f77-abbreviation-numeric",
    "frd-positive-89930c384be2e8bf-spacing-punctuation",
    "frd-positive-aaafff57ac4d4daa-abbreviation-numeric",
    "frd-positive-aaafff57ac4d4daa-spacing-punctuation",
    "frd-positive-fd96307f2dc8b421-spacing-punctuation",
    "fpdev-16-tesla",
)
MISSING_IDENTITY_SPECS = (
    ("anchor-neg-01-honda-accord", "loose 2020 Honda Accord touring diecast", "Honda Accord"),
    (
        "anchor-neg-02-mercedes-c300",
        "boxed Mercedes Benz C300 sedan miniature",
        "Mercedes-Benz C300",
    ),
    (
        "anchor-neg-03-lamborghini-aventador",
        "Lamborghini Aventador SVJ collector car",
        "Lamborghini Aventador SVJ",
    ),
    ("anchor-neg-04-mazda-miata", "carded Mazda MX-5 Miata roadster model", "Mazda MX-5 Miata"),
    ("anchor-neg-05-bmw-m4", "premium BMW M4 competition coupe", "BMW M4 Competition"),
    ("anchor-neg-06-tesla-model3", "Tesla Model 3 performance miniature", "Tesla Model 3"),
    ("anchor-neg-07-nissan-r32", "Nissan Skyline GT-R R32 loose model", "Nissan Skyline GT-R R32"),
    ("anchor-neg-08-ford-fiesta", "Ford Fiesta RS rally diecast vehicle", "Ford Fiesta RS"),
    (
        "anchor-neg-09-chevrolet-impala",
        "1964 Chevrolet Impala collector car",
        "1964 Chevrolet Impala",
    ),
    (
        "anchor-neg-10-toyota-land-cruiser",
        "Toyota Land Cruiser off road miniature",
        "Toyota Land Cruiser",
    ),
    (
        "anchor-neg-11-subaru-impreza",
        "Subaru Impreza WRX STI boxed model",
        "Subaru Impreza WRX STI",
    ),
    ("anchor-neg-12-bugatti-divo", "Bugatti Divo hypercar display piece", "Bugatti Divo"),
)
CONFIGURATIONS = (
    ("baseline", 0.0),
    ("anchor-050", 0.5),
    ("anchor-055", 0.55),
    ("anchor-0575", 0.575),
    ("anchor-060", 0.6),
    ("anchor-061", 0.61),
    ("anchor-0625", 0.625),
    ("anchor-065", 0.65),
    ("anchor-070", 0.7),
    ("anchor-075", 0.75),
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


def _base_sources(root: Path) -> dict[str, str]:
    names = (
        *CORPUS_INPUTS,
        EXISTING_PACK,
        EXISTING_MANIFEST,
        FALSE_POSITIVE_DATA_DIRECTORY / "development-pack.json",
        FALSE_POSITIVE_DATA_DIRECTORY / "development-pack-manifest.json",
        Path(FALSE_POSITIVE_SOURCE),
        Path(UPSTREAM_SOURCE),
        UPSTREAM_REPORT_DIRECTORY / "selection.json",
        Path(SOURCE),
    )
    return {str(name): _sha(root / name) for name in names}


def build_pack(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = _catalog(root)
    documents = {document.knowledge_id: document for document in catalog.documents}
    cases = {case["case_id"]: case for case in _cases(root)}
    upstream = check_upstream(root)
    upstream_rows = {row["case_id"]: row for row in upstream["raw"]["rows"]}
    rows: list[dict[str, Any]] = []
    for case_id in POSITIVE_SOURCE_CASE_IDS:
        case = cases.get(case_id)
        raw = upstream_rows.get(case_id)
        if case is None or raw is None or not raw["candidates"]:
            raise ValueError("anchor-positive source case is unavailable")
        if case["dataset"] == "false_positive":
            expected = case["expected"]["required"]
        else:
            target_id = case["expected"]["review_family_id"]
            target = documents[target_id]
            expected = {
                "knowledge_id": target.knowledge_id,
                "knowledge_uuid": str(target.knowledge_uuid),
            }
        top = raw["candidates"][0]
        if (
            top["knowledge_id"] != expected["knowledge_id"]
            or top["knowledge_uuid"] != expected["knowledge_uuid"]
            or not top["identity_token_coverage"] < SECONDARY_THRESHOLD
        ):
            raise ValueError("anchor-positive source no longer has valid low-coverage rank 1")
        rows.append(
            {
                "case_id": f"anchor-pos-{len(rows) + 1:02d}",
                "case_type": "valid_low_coverage_anchor",
                "source_case_id": case_id,
                "query_text": case["query_text"],
                "expected": expected,
            }
        )
    identities = {
        normalize_text(value)
        for document in catalog.documents
        for value in document.character_identity_texts
    }
    for case_id, query, absent_identity in MISSING_IDENTITY_SPECS:
        normalized_absent = normalize_text(absent_identity)
        if normalized_absent in identities or normalized_absent not in normalize_text(query):
            raise ValueError("missing-identity case is present in corpus or absent from query")
        rows.append(
            {
                "case_id": case_id,
                "case_type": "missing_identity_hard_negative",
                "source_case_id": None,
                "query_text": query,
                "expected": {"absent_identity": absent_identity, "must_abstain_all": True},
            }
        )
    if len(rows) != 22 or len({row["case_id"] for row in rows}) != 22:
        raise ValueError("anchor-confidence pack must contain 22 unique cases")
    pack = {
        "schema_version": PACK_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_anchor_retrieval",
        "sources": _base_sources(root),
        "case_counts": {"valid_low_coverage_anchor": 10, "missing_identity_hard_negative": 12},
        "cases": rows,
        "eligible_for": ["public_anchor_confidence_development_only"],
        "excluded_from": ["private_evaluation", "runtime_activation", "canonical_truth"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    manifest = {
        "schema_version": "pvr-human-knowledge-anchor-confidence-pack-manifest-v4",
        "version": VERSION,
        "pack_sha256": hashlib.sha256(_json(pack).encode()).hexdigest(),
        "source_sha256": pack["sources"],
        "case_counts": pack["case_counts"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    return pack, manifest


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
        "anchor-confidence pack",
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
        **_base_sources(root),
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
        "status": "frozen_before_anchor_grid_retrieval",
        "sources": dict(sorted(sources.items())),
        "query_counts": {"existing_public": 223, "anchor_confidence": len(pack["cases"])},
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "policy": {
            "rank_1_confidence": "max(identity_token_coverage,bounded_character_score)",
            "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
            "source_order_preserved": True,
        },
        "configurations": [
            {"configuration_id": name, "rank_1_minimum_confidence": threshold}
            for name, threshold in CONFIGURATIONS
        ],
        "existing_gates": GATES,
        "anchor_gates": {
            "valid_low_coverage_anchor_hits": 10,
            "missing_identity_nonempty": 0,
            "anchor_retrieval_errors": 0,
        },
        "winner_order": [
            "eligible_only",
            "minimum_missing_identity_nonempty",
            "minimum_rank_1_confidence_threshold",
        ],
        "eligible_for": ["new_versioned_private_shadow_evaluation_only"],
        "excluded_from": ["runtime_activation", "canonical_truth", "private_tuning"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def freeze_protocol(root: Path) -> str:
    protocol = build_protocol(root)
    manifest = {
        "schema_version": "pvr-human-knowledge-anchor-confidence-protocol-manifest-v4",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    return _freeze_directory(
        root / PROTOCOL_DIRECTORY,
        {"protocol.json": _json(protocol), "protocol-manifest.json": _json(manifest)},
        "anchor-confidence protocol",
    )


def validate_protocol(root: Path) -> dict[str, Any]:
    expected = build_protocol(root)
    manifest = {
        "schema_version": "pvr-human-knowledge-anchor-confidence-protocol-manifest-v4",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(expected).encode()).hexdigest(),
        "source_sha256": expected["sources"],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }
    directory = root / PROTOCOL_DIRECTORY
    _assert_file(directory / "protocol.json", _json(expected))
    _assert_file(directory / "protocol-manifest.json", _json(manifest))
    return expected


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


def collect(root: Path) -> dict[str, Any]:
    protocol = validate_protocol(root)
    pack = validate_pack(root)
    catalog = _catalog(root)
    retriever = HumanKnowledgeIdentityRetriever(
        catalog,
        HashingEmbedding(DIMENSIONS),
        HumanKnowledgeV4Config(
            CHARACTER_SCORE_FLOOR,
            CHARACTER_RRF_WEIGHT,
            artifact_version=f"{VERSION}-grid",
            artifact_sha256=_sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        ),
    )
    rows = []
    for case in pack["cases"]:
        query = case["query_text"]
        try:
            candidates, work = retriever.retrieve_with_work(extract_signals(query), CANDIDATE_LIMIT)
            payload = {
                "candidates": [_candidate(candidate, query) for candidate in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - preserve each public dev error once
            payload = {
                "candidates": [],
                "work": None,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        rows.append(
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "query_text": query,
                **payload,
            }
        )
    if len(rows) != 22:
        raise ValueError("anchor-confidence collection must contain exactly 22 rows")
    return {
        "schema_version": "pvr-human-knowledge-anchor-confidence-raw-v4",
        "version": VERSION,
        "protocol_sha256": _sha(root / PROTOCOL_DIRECTORY / "protocol.json"),
        "retrieval_calls": 22,
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": protocol["base_retriever"],
        "rows": rows,
    }


def anchor_confidence(candidate: dict[str, Any]) -> float:
    character = candidate["character_score"]
    character_value = float(character) if character is not None else 0.0
    if not math.isfinite(character_value):
        raise ValueError("character score must be finite")
    return min(1.0, max(float(candidate["identity_token_coverage"]), character_value))


def admit_candidates(row: dict[str, Any], anchor_threshold: float) -> list[dict[str, Any]]:
    if not 0 <= anchor_threshold <= 1:
        raise ValueError("anchor threshold must be in [0,1]")
    admitted = []
    for candidate in row["candidates"][:CANDIDATE_LIMIT]:
        if candidate["source_rank"] == 1:
            if anchor_confidence(candidate) + 1e-12 >= anchor_threshold:
                admitted.append(candidate)
        elif candidate["identity_token_coverage"] + 1e-12 >= SECONDARY_THRESHOLD:
            admitted.append(candidate)
    return admitted


def _score_existing(root: Path, upstream: dict[str, Any], threshold: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in upstream["raw"]["rows"]:
        rows.append({**row, "candidates": admit_candidates(row, threshold)})
    summary: dict[str, Any] = summarize_existing(_cases(root), rows, 0.0)
    return summary


def _score_anchor(pack: dict[str, Any], raw: dict[str, Any], threshold: float) -> dict[str, Any]:
    counts = {
        "valid_low_coverage_anchor_hits": 0,
        "valid_low_coverage_anchor_hits_at_1": 0,
        "missing_identity_nonempty": 0,
        "anchor_retrieval_errors": 0,
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
    }
    case_results = []
    for case, row in zip(pack["cases"], raw["rows"], strict=True):
        if row["case_id"] != case["case_id"] or row["query_text"] != case["query_text"]:
            raise ValueError("anchor raw row differs from frozen pack")
        admitted = admit_candidates(row, threshold)
        counts["anchor_retrieval_errors"] += row["error"] is not None
        counts["source_candidates"] += len(row["candidates"])
        counts["admitted_candidates"] += len(admitted)
        counts["abstained_candidates"] += len(row["candidates"]) - len(admitted)
        result: dict[str, Any] = {"case_id": case["case_id"], "case_type": case["case_type"]}
        if case["case_type"] == "valid_low_coverage_anchor":
            expected = case["expected"]
            rank = next(
                (
                    index
                    for index, candidate in enumerate(admitted, 1)
                    if candidate["knowledge_id"] == expected["knowledge_id"]
                    and candidate["knowledge_uuid"] == expected["knowledge_uuid"]
                ),
                None,
            )
            counts["valid_low_coverage_anchor_hits"] += rank is not None
            counts["valid_low_coverage_anchor_hits_at_1"] += rank == 1
            result["target_rank"] = rank
        elif case["case_type"] == "missing_identity_hard_negative":
            counts["missing_identity_nonempty"] += bool(admitted)
            result["admitted_candidate_count"] = len(admitted)
        else:
            raise ValueError("unexpected anchor-confidence case type")
        case_results.append(result)
    gates = [
        {
            "name": name,
            "operator": "=",
            "threshold": expected,
            "actual": counts[name],
            "passed": counts[name] == expected,
        }
        for name, expected in {
            "valid_low_coverage_anchor_hits": 10,
            "missing_identity_nonempty": 0,
            "anchor_retrieval_errors": 0,
        }.items()
    ]
    return {
        "counts": counts,
        "gates": gates,
        "eligible": all(gate["passed"] for gate in gates),
        "case_results": case_results,
    }


def score(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    upstream = check_upstream(root)
    pack = validate_pack(root)
    summaries = []
    for configuration_id, threshold in CONFIGURATIONS:
        existing = _score_existing(root, upstream, threshold)
        anchor = _score_anchor(pack, raw, threshold)
        summaries.append(
            {
                "configuration_id": configuration_id,
                "rank_1_minimum_confidence": threshold,
                "existing": existing,
                "anchor": anchor,
                "eligible": existing["eligible"] and anchor["eligible"],
            }
        )
    eligible = [summary for summary in summaries if summary["eligible"]]
    winner = min(
        eligible,
        key=lambda summary: (
            summary["anchor"]["counts"]["missing_identity_nonempty"],
            summary["rank_1_minimum_confidence"],
        ),
        default=None,
    )
    return {
        "summaries": summaries,
        "winner": (
            {
                "configuration_id": winner["configuration_id"],
                "rank_1_minimum_confidence": winner["rank_1_minimum_confidence"],
                "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
                "existing_counts": winner["existing"]["counts"],
                "anchor_counts": winner["anchor"]["counts"],
                "selection_rule": "eligible_min_missing_identity_nonempty_then_lowest_threshold",
                "status": "qualified_for_new_private_shadow_evaluation_only",
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
        "protocol_manifest_sha256": _sha(root / PROTOCOL_DIRECTORY / "protocol-manifest.json"),
        "sources": build_protocol(root)["sources"],
        "raw": raw,
        "limitations": [
            "public_curated_development_only_not_final_accuracy",
            "twelve_missing_identity_cases_not_population_safety",
            "max_coverage_character_score_is_deterministic_not_neural",
            "no_private_local_evaluation",
            "winner_not_runtime_activated",
        ],
        **score(root, raw),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge rank-1 anchor-confidence selection",
        "",
        "Public-development selection only; private evaluation and runtime are unchanged.",
        "",
        "| Configuration | Anchor threshold | Eligible | Existing R@5 | Prior required | Anchor positives | Missing nonempty |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        existing = summary["existing"]["counts"]
        anchor = summary["anchor"]["counts"]
        lines.append(
            f"| {summary['configuration_id']} | {summary['rank_1_minimum_confidence']:.3f} | "
            f"{'yes' if summary['eligible'] else 'no'} | "
            f"{existing['existing_positive_hits_at_5']}/168 | "
            f"{existing['new_required_hits_at_5']}/24 | "
            f"{anchor['valid_low_coverage_anchor_hits']}/10 | "
            f"{anchor['missing_identity_nonempty']}/12 |"
        )
    lines.extend(["", "## Selection", ""])
    winner = report["winner"]
    if winner is None:
        lines.append("No configuration passed every frozen recall and anchor-safety gate.")
    else:
        lines.append(
            f"Selected **{winner['configuration_id']}** with rank-1 confidence threshold "
            f"`{winner['rank_1_minimum_confidence']}` for a new private shadow evaluation only."
        )
    lines.extend(["", "The selection is not active in the API or Dual RAG runtime.", ""])
    return "\n".join(lines)


def run(root: Path) -> tuple[dict[str, Any], str]:
    directory = root / REPORT_DIRECTORY
    if directory.exists():
        return check(root), "unchanged"
    report = _report(root, collect(root))
    outputs = {"selection.json": _json(report), "selection.md": _markdown(report)}
    directory.mkdir()
    try:
        for name, content in outputs.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except BaseException:
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()
        raise
    return check(root), "created"


def _validate_raw_candidate(
    candidate: dict[str, Any], document: HumanKnowledgeDocument, query: str, rank: int
) -> None:
    values = (candidate["source_rrf_score"], candidate["dense_score"])
    if (
        candidate["knowledge_id"] != document.knowledge_id
        or candidate["knowledge_type"] != document.knowledge_type
        or candidate["source_rank"] != rank
        or not all(type(value) in {int, float} and math.isfinite(value) for value in values)
        or candidate["identity_token_coverage"] != identity_token_coverage(query, document)
    ):
        raise ValueError("anchor raw candidate differs from public corpus")
    anchor_confidence(candidate)


def check(root: Path) -> dict[str, Any]:
    validate_protocol(root)
    directory = root / REPORT_DIRECTORY
    report = _load(directory / "selection.json")
    raw = report.get("raw")
    if (
        not isinstance(raw, dict)
        or report.get("schema_version") != REPORT_SCHEMA
        or raw.get("retrieval_calls") != 22
        or raw.get("candidate_limit") != CANDIDATE_LIMIT
        or raw.get("protocol_sha256") != _sha(root / PROTOCOL_DIRECTORY / "protocol.json")
        or report.get("sources") != build_protocol(root)["sources"]
    ):
        raise ValueError("anchor-confidence selection metadata differs from contract")
    pack = validate_pack(root)
    catalog = {str(document.knowledge_uuid): document for document in _catalog(root).documents}
    if len(raw.get("rows", [])) != 22:
        raise ValueError("anchor-confidence raw row count differs from contract")
    for case, row in zip(pack["cases"], raw["rows"], strict=True):
        if row["case_id"] != case["case_id"] or row["query_text"] != case["query_text"]:
            raise ValueError("anchor-confidence raw row differs from pack")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = catalog.get(candidate["knowledge_uuid"])
            if document is None:
                raise ValueError("anchor-confidence candidate is absent from corpus")
            _validate_raw_candidate(candidate, document, row["query_text"], rank)
    rescored = score(root, raw)
    if (
        report.get("summaries") != rescored["summaries"]
        or report.get("winner") != rescored["winner"]
    ):
        raise ValueError("anchor-confidence selection differs from deterministic scoring")
    _assert_file(directory / "selection.md", _markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Develop public rank-1 anchor confidence")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--freeze-pack", action="store_true")
    parser.add_argument("--freeze-protocol", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_pack:
        output = {"operation": freeze_pack(root), "retrieval_executed": False, "cases": 22}
    elif arguments.freeze_protocol:
        output = {
            "operation": freeze_protocol(root),
            "retrieval_executed": False,
            "configurations": len(CONFIGURATIONS),
        }
    elif arguments.check:
        report = check(root)
        output = {"operation": "valid", "winner": report["winner"]}
    else:
        report, operation = run(root)
        output = {"operation": operation, "winner": report["winner"]}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
