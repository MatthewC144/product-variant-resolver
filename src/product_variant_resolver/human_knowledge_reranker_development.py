"""Select a candidate-relative Human Knowledge reranker on public development data."""

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
from .human_knowledge_identity import HumanKnowledgeIdentityRetriever, HumanKnowledgeV4Config
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-reranker-development-v2"
PROTOCOL_SCHEMA = "pvr-human-knowledge-reranker-development-protocol-v2"
REPORT_SCHEMA = "pvr-human-knowledge-reranker-development-selection-v2"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
REPORT_DIRECTORY = Path("reports") / VERSION
SOURCE = "src/product_variant_resolver/human_knowledge_reranker_development.py"
ADMISSION_SOURCE = "src/product_variant_resolver/human_knowledge_admission_development.py"
CANDIDATE_POOL_LIMIT = 25
OUTPUT_LIMIT = 5
RRF_K = 60
PENALTY_CONFIGURATIONS = (
    ("baseline", 0.0),
    ("penalty-005", 0.05),
    ("penalty-010", 0.1),
    ("penalty-025", 0.25),
    ("penalty-050", 0.5),
    ("penalty-100", 1.0),
    ("penalty-200", 2.0),
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


def _sources(root: Path) -> dict[str, str]:
    names = (
        *CORPUS_INPUTS,
        EXISTING_PACK,
        EXISTING_MANIFEST,
        FALSE_POSITIVE_DATA_DIRECTORY / "development-pack.json",
        FALSE_POSITIVE_DATA_DIRECTORY / "development-pack-manifest.json",
        Path(ADMISSION_SOURCE),
        Path(FALSE_POSITIVE_SOURCE),
        Path(SOURCE),
    )
    return {str(name): _sha(root / name) for name in names}


def build_protocol(root: Path) -> dict[str, Any]:
    cases = _cases(root)
    if len(cases) != 223:
        raise ValueError("development input denominator differs from contract")
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_grid_execution",
        "sources": _sources(root),
        "corpus_document_count": 142,
        "query_counts": {"existing_development": 199, "false_positive_development": 24},
        "candidate_pool_limit": CANDIDATE_POOL_LIMIT,
        "output_limit": OUTPUT_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
            "rrf_k": RRF_K,
        },
        "reranker": {
            "formula": "rrf_score / (1 + weight * (1 - identity_token_coverage))",
            "coverage_range": [0.0, 1.0],
            "hard_deletion": False,
            "stable_tie_break": ["source_rank", "knowledge_uuid"],
        },
        "configurations": [
            {"configuration_id": name, "unmatched_token_penalty_weight": weight}
            for name, weight in PENALTY_CONFIGURATIONS
        ],
        "gates": GATES,
        "winner_order": [
            "eligible_only",
            "minimum_new_forbidden_hit_cases",
            "maximum_existing_positive_hits_at_1",
            "maximum_new_required_hits_at_1",
            "minimum_unmatched_token_penalty_weight",
        ],
        "eligible_for": ["development_selection_only"],
        "excluded_from": [
            "runtime_activation",
            "final_accuracy",
            "private_local_evaluation",
            "canonical_truth",
            "release_variant_truth",
            "color_truth",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def _assert_file(path: Path, content: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != content:
        raise ValueError(f"{path} differs from deterministic artifact")


def freeze_protocol(root: Path) -> str:
    protocol = build_protocol(root)
    manifest = {
        "schema_version": "pvr-human-knowledge-reranker-development-manifest-v2",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    outputs = {"protocol.json": _json(protocol), "protocol-manifest.json": _json(manifest)}
    directory = root / DATA_DIRECTORY
    if directory.exists():
        if {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError("reranker protocol directory is partial or conflicting")
        for name, content in outputs.items():
            _assert_file(directory / name, content)
        return "unchanged"
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
    return "created"


def validate_protocol(root: Path) -> dict[str, Any]:
    expected = build_protocol(root)
    manifest = {
        "schema_version": "pvr-human-knowledge-reranker-development-manifest-v2",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(expected).encode()).hexdigest(),
        "source_sha256": expected["sources"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    directory = root / DATA_DIRECTORY
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
    catalog = _catalog(root)
    retriever = HumanKnowledgeIdentityRetriever(
        catalog,
        HashingEmbedding(DIMENSIONS),
        HumanKnowledgeV4Config(
            CHARACTER_SCORE_FLOOR,
            CHARACTER_RRF_WEIGHT,
            artifact_version=f"{VERSION}-grid",
            artifact_sha256=_sha(root / DATA_DIRECTORY / "protocol.json"),
        ),
    )
    rows = []
    for case in _cases(root):
        query = case["query_text"]
        try:
            candidates, work = retriever.retrieve_with_work(
                extract_signals(query), CANDIDATE_POOL_LIMIT
            )
            row = {
                "candidates": [_candidate(candidate, query) for candidate in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - preserve each development error once
            row = {
                "candidates": [],
                "work": None,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        rows.append(
            {
                "dataset": case["dataset"],
                "case_id": case["case_id"],
                "query_text": query,
                **row,
            }
        )
    if len(rows) != 223:
        raise ValueError("reranker collection must contain exactly 223 rows")
    return {
        "schema_version": "pvr-human-knowledge-reranker-development-raw-v2",
        "version": VERSION,
        "protocol_sha256": _sha(root / DATA_DIRECTORY / "protocol.json"),
        "configuration_count": len(PENALTY_CONFIGURATIONS),
        "query_count": 223,
        "retrieval_calls": 223,
        "candidate_pool_limit": CANDIDATE_POOL_LIMIT,
        "output_limit": OUTPUT_LIMIT,
        "corpus_document_count": 142,
        "base_retriever": protocol["base_retriever"],
        "rows": rows,
    }


def rerank_candidates(row: dict[str, Any], weight: float) -> list[dict[str, Any]]:
    if not math.isfinite(weight) or weight < 0:
        raise ValueError("penalty weight must be finite and nonnegative")
    reranked = []
    for candidate in row["candidates"]:
        coverage = candidate["identity_token_coverage"]
        if not 0 <= coverage <= 1:
            raise ValueError("identity-token coverage must be in [0,1]")
        penalty = 1 + weight * (1 - coverage)
        reranked.append(
            {
                **candidate,
                "unmatched_identity_fraction": 1 - coverage,
                "rerank_score": candidate["source_rrf_score"] / penalty,
            }
        )
    return sorted(
        reranked,
        key=lambda item: (-item["rerank_score"], item["source_rank"], item["knowledge_uuid"]),
    )[:OUTPUT_LIMIT]


def summarize(
    cases: list[dict[str, Any]], rows: list[dict[str, Any]], weight: float
) -> dict[str, Any]:
    counts = {
        "existing_positive_hits_at_5": 0,
        "existing_positive_hits_at_1": 0,
        "merge_hits_at_5": 0,
        "existing_forbidden_candidates": 0,
        "unrelated_nonempty": 0,
        "new_required_hits_at_5": 0,
        "new_required_hits_at_1": 0,
        "new_forbidden_hit_cases_at_5": 0,
        "new_forbidden_candidates_at_5": 0,
        "retrieval_errors": 0,
    }
    case_results = []
    for case, row in zip(cases, rows, strict=True):
        if (
            row["dataset"] != case["dataset"]
            or row["case_id"] != case["case_id"]
            or row["query_text"] != case["query_text"]
        ):
            raise ValueError("raw row differs from ordered development case")
        candidates = rerank_candidates(row, weight)
        counts["retrieval_errors"] += row["error"] is not None
        result: dict[str, Any] = {
            "dataset": case["dataset"],
            "case_id": case["case_id"],
            "candidate_ranks": [candidate["knowledge_id"] for candidate in candidates],
        }
        if case["dataset"] == "false_positive":
            required = case["expected"]["required"]
            forbidden = case["expected"]["forbidden"]
            required_rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate["knowledge_id"] == required["knowledge_id"]
                    and candidate["knowledge_uuid"] == required["knowledge_uuid"]
                ),
                None,
            )
            forbidden_ranks = [
                index
                for index, candidate in enumerate(candidates, 1)
                if candidate["knowledge_id"] == forbidden["knowledge_id"]
                and candidate["knowledge_uuid"] == forbidden["knowledge_uuid"]
            ]
            counts["new_required_hits_at_5"] += required_rank is not None
            counts["new_required_hits_at_1"] += required_rank == 1
            counts["new_forbidden_hit_cases_at_5"] += bool(forbidden_ranks)
            counts["new_forbidden_candidates_at_5"] += len(forbidden_ranks)
            result.update(required_rank=required_rank, forbidden_ranks=forbidden_ranks)
        elif case["case_type"] == "positive_family":
            target = case["expected"]["review_family_id"]
            rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate["knowledge_type"] == "review_family"
                    and candidate["knowledge_id"] == target
                ),
                None,
            )
            counts["existing_positive_hits_at_5"] += rank is not None
            counts["existing_positive_hits_at_1"] += rank == 1
            result["target_rank"] = rank
        elif case["case_type"] == "merge_control":
            target = case["expected"]["casting_id"]
            rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate["knowledge_type"] == "provisional_variant"
                    and candidate["casting_id"] == target
                ),
                None,
            )
            counts["merge_hits_at_5"] += rank is not None
            forbidden = case["expected"]["forbidden_review_family_id"]
            violations = sum(candidate["knowledge_id"] == forbidden for candidate in candidates)
            counts["existing_forbidden_candidates"] += violations
            result.update(target_rank=rank, forbidden_candidates=violations)
        elif case["case_type"] == "hold_control":
            forbidden = case["expected"]["forbidden_review_family_id"]
            violations = sum(candidate["knowledge_id"] == forbidden for candidate in candidates)
            counts["existing_forbidden_candidates"] += violations
            result["forbidden_candidates"] = violations
        elif case["case_type"] == "unrelated_control":
            counts["unrelated_nonempty"] += bool(candidates)
            result["candidate_count"] = len(candidates)
        else:
            raise ValueError("unexpected development case type")
        case_results.append(result)
    gate_results = [
        {
            "name": name,
            "operator": "=",
            "threshold": expected,
            "actual": counts[name],
            "passed": counts[name] == expected,
        }
        for name, expected in GATES.items()
    ]
    return {
        "counts": counts,
        "metrics": {
            "existing_positive_recall_at_5": counts["existing_positive_hits_at_5"] / 168,
            "existing_positive_recall_at_1": counts["existing_positive_hits_at_1"] / 168,
            "new_required_recall_at_5": counts["new_required_hits_at_5"] / 24,
            "new_required_recall_at_1": counts["new_required_hits_at_1"] / 24,
            "new_forbidden_case_rate_at_5": counts["new_forbidden_hit_cases_at_5"] / 24,
            "new_safety_accuracy_at_5": (24 - counts["new_forbidden_hit_cases_at_5"]) / 24,
        },
        "gates": gate_results,
        "eligible": all(gate["passed"] for gate in gate_results),
        "case_results": case_results,
    }


def score(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    cases = _cases(root)
    summaries = [
        {
            "configuration_id": configuration_id,
            "unmatched_token_penalty_weight": weight,
            **summarize(cases, raw["rows"], weight),
        }
        for configuration_id, weight in PENALTY_CONFIGURATIONS
    ]
    eligible = [summary for summary in summaries if summary["eligible"]]
    winner = min(
        eligible,
        key=lambda summary: (
            summary["counts"]["new_forbidden_hit_cases_at_5"],
            -summary["counts"]["existing_positive_hits_at_1"],
            -summary["counts"]["new_required_hits_at_1"],
            summary["unmatched_token_penalty_weight"],
        ),
        default=None,
    )
    return {
        "summaries": summaries,
        "winner": (
            {
                "configuration_id": winner["configuration_id"],
                "unmatched_token_penalty_weight": winner["unmatched_token_penalty_weight"],
                "counts": winner["counts"],
                "metrics": winner["metrics"],
                "selection_rule": (
                    "eligible_min_forbidden_max_old_rank1_max_new_rank1_lowest_weight"
                ),
                "improves_over_baseline": (
                    winner["counts"]["new_forbidden_hit_cases_at_5"]
                    < summaries[0]["counts"]["new_forbidden_hit_cases_at_5"]
                ),
                "status": "selected_development_only_not_runtime",
            }
            if winner is not None
            else None
        ),
    }


def _report(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "version": VERSION,
        "status": "development_selection_complete_not_runtime",
        "protocol_sha256": raw["protocol_sha256"],
        "protocol_manifest_sha256": _sha(root / DATA_DIRECTORY / "protocol-manifest.json"),
        "sources": _sources(root),
        "raw": raw,
        "limitations": [
            "development_only_not_final_accuracy",
            "identity_derived_existing_pack_and_manual_related_pairs",
            "candidate_relative_reranking_not_new_retrieval_model",
            "no_private_local_evaluation",
            "selected_policy_not_runtime_activated",
        ],
        **score(root, raw),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge candidate-relative reranker selection",
        "",
        "Development selection only; runtime and private final evaluation are unchanged.",
        "",
        "| Configuration | Weight | Eligible | Existing R@5 | Existing R@1 | New required | Forbidden cases | Safety |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        counts = summary["counts"]
        lines.append(
            f"| {summary['configuration_id']} | "
            f"{summary['unmatched_token_penalty_weight']:.2f} | "
            f"{'yes' if summary['eligible'] else 'no'} | "
            f"{counts['existing_positive_hits_at_5']}/168 | "
            f"{counts['existing_positive_hits_at_1']}/168 | "
            f"{counts['new_required_hits_at_5']}/24 | "
            f"{counts['new_forbidden_hit_cases_at_5']}/24 | "
            f"{summary['metrics']['new_safety_accuracy_at_5']:.4f} |"
        )
    lines.extend(["", "## Selection", ""])
    winner = report["winner"]
    if winner is None:
        lines.append("No configuration passed every frozen recall and governance gate.")
    elif not winner["improves_over_baseline"]:
        lines.append(
            f"The frozen rule returned **{winner['configuration_id']}**, but it does not improve "
            "forbidden-case safety over baseline; no mitigation qualified."
        )
    else:
        lines.append(
            f"Selected experimental configuration: **{winner['configuration_id']}** with weight "
            f"`{winner['unmatched_token_penalty_weight']}`."
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


def _expected_rrf(candidate: dict[str, Any]) -> float:
    ranks = (candidate["sparse_rank"], candidate["dense_rank"], candidate["character_rank"])
    return float(sum(1 / (RRF_K + rank) for rank in ranks if rank is not None))


def _validate_raw_candidate(
    candidate: dict[str, Any], document: HumanKnowledgeDocument, query: str, rank: int
) -> None:
    numeric = (
        candidate["source_rrf_score"],
        candidate["dense_score"],
        candidate["identity_token_coverage"],
    )
    optional_numeric = (candidate["sparse_score"], candidate["character_score"])
    if (
        candidate["knowledge_id"] != document.knowledge_id
        or candidate["knowledge_type"] != document.knowledge_type
        or candidate["casting_id"] != getattr(document, "casting_id", None)
        or candidate["source_rank"] != rank
        or not all(type(value) in {int, float} and math.isfinite(value) for value in numeric)
        or not all(
            value is None or (type(value) in {int, float} and math.isfinite(value))
            for value in optional_numeric
        )
        or not math.isclose(candidate["source_rrf_score"], _expected_rrf(candidate), abs_tol=1e-15)
        or candidate["identity_token_coverage"] != identity_token_coverage(query, document)
    ):
        raise ValueError("reranker raw candidate differs from corpus or frozen scoring")


def check(root: Path) -> dict[str, Any]:
    validate_protocol(root)
    directory = root / REPORT_DIRECTORY
    report = _load(directory / "selection.json")
    raw = report.get("raw")
    if (
        not isinstance(raw, dict)
        or report.get("schema_version") != REPORT_SCHEMA
        or raw.get("query_count") != 223
        or raw.get("retrieval_calls") != 223
        or raw.get("candidate_pool_limit") != CANDIDATE_POOL_LIMIT
        or raw.get("output_limit") != OUTPUT_LIMIT
        or raw.get("protocol_sha256") != _sha(root / DATA_DIRECTORY / "protocol.json")
        or report.get("sources") != _sources(root)
    ):
        raise ValueError("reranker selection metadata differs from contract")
    catalog = {str(item.knowledge_uuid): item for item in _catalog(root).documents}
    cases = _cases(root)
    if len(raw.get("rows", [])) != len(cases):
        raise ValueError("reranker raw row count differs from contract")
    for case, row in zip(cases, raw["rows"], strict=True):
        if (
            row["dataset"] != case["dataset"]
            or row["case_id"] != case["case_id"]
            or row["query_text"] != case["query_text"]
            or len(row["candidates"]) > CANDIDATE_POOL_LIMIT
        ):
            raise ValueError("reranker raw row differs from frozen case")
        seen = set()
        for rank, candidate in enumerate(row["candidates"], 1):
            document = catalog.get(candidate["knowledge_uuid"])
            if document is None or candidate["knowledge_uuid"] in seen:
                raise ValueError("reranker candidate is missing or duplicated")
            seen.add(candidate["knowledge_uuid"])
            _validate_raw_candidate(candidate, document, row["query_text"], rank)
        baseline = rerank_candidates(row, 0.0)
        if [item["source_rank"] for item in baseline] != list(range(1, len(baseline) + 1)):
            raise ValueError("weight-zero reranker differs from source Top 5")
    rescored = score(root, raw)
    if (
        report.get("summaries") != rescored["summaries"]
        or report.get("winner") != rescored["winner"]
    ):
        raise ValueError("reranker selection differs from deterministic scoring")
    _assert_file(directory / "selection.md", _markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select a development-only Human Knowledge reranker"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--freeze-protocol", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_protocol:
        operation = freeze_protocol(root)
        output = {
            "operation": operation,
            "retrieval_executed": False,
            "configurations": len(PENALTY_CONFIGURATIONS),
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
