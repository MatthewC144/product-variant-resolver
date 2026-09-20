"""Select anchored secondary-candidate admission using public development evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .human_knowledge_admission_development import GATES, _cases
from .human_knowledge_reranker_development import (
    DATA_DIRECTORY as UPSTREAM_DATA_DIRECTORY,
)
from .human_knowledge_reranker_development import (
    REPORT_DIRECTORY as UPSTREAM_REPORT_DIRECTORY,
)
from .human_knowledge_reranker_development import (
    SOURCE as UPSTREAM_SOURCE,
)
from .human_knowledge_reranker_development import (
    VERSION as UPSTREAM_VERSION,
)
from .human_knowledge_reranker_development import check as check_upstream

VERSION = "human-knowledge-anchor-admission-development-v3"
PROTOCOL_SCHEMA = "pvr-human-knowledge-anchor-admission-protocol-v3"
REPORT_SCHEMA = "pvr-human-knowledge-anchor-admission-selection-v3"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
REPORT_DIRECTORY = Path("reports") / VERSION
SOURCE = "src/product_variant_resolver/human_knowledge_anchor_admission_development.py"
SOURCE_OUTPUT_LIMIT = 5
THRESHOLD_CONFIGURATIONS = (
    ("baseline", 0.0),
    ("secondary-033", 1 / 3),
    ("secondary-040", 0.4),
    ("secondary-050", 0.5),
    ("secondary-060", 0.6),
    ("secondary-067", 2 / 3),
    ("secondary-075", 0.75),
    ("secondary-100", 1.0),
)
UPSTREAM_FILES = (
    UPSTREAM_DATA_DIRECTORY / "protocol.json",
    UPSTREAM_DATA_DIRECTORY / "protocol-manifest.json",
    UPSTREAM_REPORT_DIRECTORY / "selection.json",
    UPSTREAM_REPORT_DIRECTORY / "selection.md",
    Path(UPSTREAM_SOURCE),
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
    names = (*UPSTREAM_FILES, Path(SOURCE))
    return {str(name): _sha(root / name) for name in names}


def build_protocol(root: Path) -> dict[str, Any]:
    upstream = check_upstream(root)
    raw = upstream["raw"]
    if raw["query_count"] != 223 or raw["retrieval_calls"] != 223:
        raise ValueError("upstream development denominator differs from contract")
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_v3_scoring",
        "sources": _sources(root),
        "upstream": {
            "version": UPSTREAM_VERSION,
            "selection_sha256": _sha(root / UPSTREAM_REPORT_DIRECTORY / "selection.json"),
            "query_count": 223,
            "existing_development": 199,
            "false_positive_development": 24,
            "retrieval_reused": True,
        },
        "source_output_limit": SOURCE_OUTPUT_LIMIT,
        "admission": {
            "rank_1": "always_admit_anchor",
            "ranks_2_through_5": "identity_token_coverage_gte_threshold",
            "source_order_preserved": True,
            "candidates_beyond_source_rank_5": "not_output_eligible",
            "hard_delete_rank_1": False,
        },
        "configurations": [
            {"configuration_id": name, "secondary_minimum_identity_token_coverage": threshold}
            for name, threshold in THRESHOLD_CONFIGURATIONS
        ],
        "gates": GATES,
        "winner_order": [
            "eligible_only",
            "minimum_new_forbidden_hit_cases",
            "minimum_secondary_identity_token_coverage",
        ],
        "eligible_for": ["new_versioned_private_shadow_evaluation_only"],
        "excluded_from": [
            "runtime_activation",
            "final_accuracy",
            "canonical_truth",
            "release_variant_truth",
            "color_truth",
            "postgresql_query_behavior",
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
        "schema_version": "pvr-human-knowledge-anchor-admission-manifest-v3",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "upstream_selection_sha256": protocol["upstream"]["selection_sha256"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    outputs = {"protocol.json": _json(protocol), "protocol-manifest.json": _json(manifest)}
    directory = root / DATA_DIRECTORY
    if directory.exists():
        if {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError("anchor-admission protocol directory is partial or conflicting")
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
        "schema_version": "pvr-human-knowledge-anchor-admission-manifest-v3",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(expected).encode()).hexdigest(),
        "source_sha256": expected["sources"],
        "upstream_selection_sha256": expected["upstream"]["selection_sha256"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    directory = root / DATA_DIRECTORY
    _assert_file(directory / "protocol.json", _json(expected))
    _assert_file(directory / "protocol-manifest.json", _json(manifest))
    return expected


def admit_candidates(row: dict[str, Any], secondary_threshold: float) -> list[dict[str, Any]]:
    if not 0 <= secondary_threshold <= 1:
        raise ValueError("secondary threshold must be in [0,1]")
    admitted = []
    for candidate in row["candidates"][:SOURCE_OUTPUT_LIMIT]:
        coverage = candidate["identity_token_coverage"]
        if not 0 <= coverage <= 1:
            raise ValueError("identity-token coverage must be in [0,1]")
        if candidate["source_rank"] == 1 or coverage + 1e-12 >= secondary_threshold:
            admitted.append(candidate)
    return admitted


def summarize(
    cases: list[dict[str, Any]], rows: list[dict[str, Any]], threshold: float
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
        "source_top5_candidates": 0,
        "admitted_candidates": 0,
        "abstained_secondary_candidates": 0,
    }
    case_results = []
    for case, row in zip(cases, rows, strict=True):
        if (
            row["dataset"] != case["dataset"]
            or row["case_id"] != case["case_id"]
            or row["query_text"] != case["query_text"]
        ):
            raise ValueError("upstream row differs from ordered development case")
        source = row["candidates"][:SOURCE_OUTPUT_LIMIT]
        candidates = admit_candidates(row, threshold)
        counts["retrieval_errors"] += row["error"] is not None
        counts["source_top5_candidates"] += len(source)
        counts["admitted_candidates"] += len(candidates)
        counts["abstained_secondary_candidates"] += len(source) - len(candidates)
        result: dict[str, Any] = {
            "dataset": case["dataset"],
            "case_id": case["case_id"],
            "source_candidate_count": len(source),
            "admitted_source_ranks": [candidate["source_rank"] for candidate in candidates],
            "abstained_source_ranks": [
                candidate["source_rank"] for candidate in source if candidate not in candidates
            ],
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
            "secondary_abstention_rate": (
                counts["abstained_secondary_candidates"] / counts["source_top5_candidates"]
                if counts["source_top5_candidates"]
                else 0.0
            ),
        },
        "gates": gate_results,
        "eligible": all(gate["passed"] for gate in gate_results),
        "case_results": case_results,
    }


def score(root: Path, upstream: dict[str, Any]) -> dict[str, Any]:
    cases = _cases(root)
    rows = upstream["raw"]["rows"]
    summaries = [
        {
            "configuration_id": configuration_id,
            "secondary_minimum_identity_token_coverage": threshold,
            **summarize(cases, rows, threshold),
        }
        for configuration_id, threshold in THRESHOLD_CONFIGURATIONS
    ]
    eligible = [summary for summary in summaries if summary["eligible"]]
    winner = min(
        eligible,
        key=lambda summary: (
            summary["counts"]["new_forbidden_hit_cases_at_5"],
            summary["secondary_minimum_identity_token_coverage"],
        ),
        default=None,
    )
    return {
        "summaries": summaries,
        "winner": (
            {
                "configuration_id": winner["configuration_id"],
                "secondary_minimum_identity_token_coverage": winner[
                    "secondary_minimum_identity_token_coverage"
                ],
                "counts": winner["counts"],
                "metrics": winner["metrics"],
                "selection_rule": "eligible_min_forbidden_then_lowest_secondary_threshold",
                "improves_over_baseline": (
                    winner["counts"]["new_forbidden_hit_cases_at_5"]
                    < summaries[0]["counts"]["new_forbidden_hit_cases_at_5"]
                ),
                "status": "qualified_for_new_private_shadow_evaluation_only",
            }
            if winner is not None
            else None
        ),
    }


def _report(root: Path, upstream: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "version": VERSION,
        "status": "development_selection_complete_not_runtime",
        "protocol_sha256": _sha(root / DATA_DIRECTORY / "protocol.json"),
        "protocol_manifest_sha256": _sha(root / DATA_DIRECTORY / "protocol-manifest.json"),
        "sources": _sources(root),
        "upstream": {
            "version": UPSTREAM_VERSION,
            "selection_file": str(UPSTREAM_REPORT_DIRECTORY / "selection.json"),
            "selection_sha256": _sha(root / UPSTREAM_REPORT_DIRECTORY / "selection.json"),
            "raw_query_count": upstream["raw"]["query_count"],
            "new_retrieval_calls": 0,
        },
        "limitations": [
            "development_only_not_final_accuracy",
            "rank1_anchor_may_admit_wrong_top1_on_unseen_queries",
            "identity_derived_existing_pack_and_manual_related_pairs",
            "no_private_local_evaluation",
            "selected_policy_not_runtime_activated",
        ],
        **score(root, upstream),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Knowledge anchored compatibility admission selection",
        "",
        "Public-development selection only; private evaluation and runtime are unchanged.",
        "",
        "| Configuration | Secondary coverage | Eligible | Old R@5 | New required | Forbidden cases | Admitted | Abstained |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        counts = summary["counts"]
        lines.append(
            f"| {summary['configuration_id']} | "
            f"{summary['secondary_minimum_identity_token_coverage']:.4f} | "
            f"{'yes' if summary['eligible'] else 'no'} | "
            f"{counts['existing_positive_hits_at_5']}/168 | "
            f"{counts['new_required_hits_at_5']}/24 | "
            f"{counts['new_forbidden_hit_cases_at_5']}/24 | "
            f"{counts['admitted_candidates']} | "
            f"{counts['abstained_secondary_candidates']} |"
        )
    lines.extend(["", "## Selection", ""])
    winner = report["winner"]
    if winner is None:
        lines.append("No configuration passed every frozen recall and governance gate.")
    elif not winner["improves_over_baseline"]:
        lines.append(
            f"The frozen rule returned **{winner['configuration_id']}**, but it does not improve "
            "forbidden-case safety; no mitigation qualified."
        )
    else:
        lines.append(
            f"Selected **{winner['configuration_id']}** with secondary coverage "
            f"`{winner['secondary_minimum_identity_token_coverage']}` for a new versioned private "
            "shadow evaluation only."
        )
    lines.extend(["", "The selection is not active in the API or Dual RAG runtime.", ""])
    return "\n".join(lines)


def run(root: Path) -> tuple[dict[str, Any], str]:
    directory = root / REPORT_DIRECTORY
    if directory.exists():
        return check(root), "unchanged"
    validate_protocol(root)
    report = _report(root, check_upstream(root))
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


def check(root: Path) -> dict[str, Any]:
    validate_protocol(root)
    upstream = check_upstream(root)
    directory = root / REPORT_DIRECTORY
    report = _load(directory / "selection.json")
    expected_upstream = {
        "version": UPSTREAM_VERSION,
        "selection_file": str(UPSTREAM_REPORT_DIRECTORY / "selection.json"),
        "selection_sha256": _sha(root / UPSTREAM_REPORT_DIRECTORY / "selection.json"),
        "raw_query_count": 223,
        "new_retrieval_calls": 0,
    }
    if (
        report.get("schema_version") != REPORT_SCHEMA
        or report.get("protocol_sha256") != _sha(root / DATA_DIRECTORY / "protocol.json")
        or report.get("sources") != _sources(root)
        or report.get("upstream") != expected_upstream
    ):
        raise ValueError("anchor-admission selection metadata differs from contract")
    rescored = score(root, upstream)
    if (
        report.get("summaries") != rescored["summaries"]
        or report.get("winner") != rescored["winner"]
    ):
        raise ValueError("anchor-admission selection differs from deterministic scoring")
    _assert_file(directory / "selection.md", _markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Select anchored Human Knowledge admission")
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
            "configurations": len(THRESHOLD_CONFIGURATIONS),
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
