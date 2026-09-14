"""One-shot final-v2 collection, then label scoring; --check never retrieves."""
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from . import family_retrieval_final_v2_labels as labels
from .human_knowledge import load_human_knowledge_catalog
from .human_knowledge_identity import HumanKnowledgeIdentityRetriever, HumanKnowledgeV4Config
from .human_knowledge_identity_artifact import _check_candidates, load_human_knowledge_v4_config
from .human_knowledge_identity_selection import publish_new, serialize
from .human_knowledge_selection import load_object, sha
from .retrieval import HashingEmbedding
from .signals import extract_signals

ROOT = labels.ROOT
DIRECTORY = Path("reports/family-retrieval-v2")
SOURCES = ("src/product_variant_resolver/family_retrieval_final_v2_evaluation.py",
    "scripts/generate_family_retrieval_report_v2.py")
LIMITATIONS = ["synthetic_same_family_questions_not_population_or_unseen_casting_accuracy",
    "prior_development_known_not_independent_author", "family_truth_not_release_variant_truth",
    "human_debug_only_canonical_authority_unchanged", "single_process_non_isolated_host",
    "hashing_v1_not_neural", "final_cost_diagnostic_not_fitted_gate_or_http_sql_latency"]


def now() -> str:
    return datetime.now(UTC).isoformat()


def corpus(root: Path) -> Any:
    return load_human_knowledge_catalog(root / "data/human_backed_catalog.json",
        root / "data/review_family_knowledge.json", root / "data/review_family_knowledge_manifest.json")


def collect(root: Path = ROOT) -> dict[str, Any]:
    """No approved benchmark/owner decisions are opened here; all105 raw results precede scoring."""
    pack_path = root / labels.questions.DIRECTORY / "query-pack.json"
    if sha(pack_path) != labels.QUERY_SHA:
        raise ValueError("final query pack changed")
    pack = load_object(pack_path)
    config = load_human_knowledge_v4_config(root / labels.questions.ARTIFACT, root=root,
        human_catalog_path=root / "data/human_backed_catalog.json",
        review_family_path=root / "data/review_family_knowledge.json",
        development_pack_path=root / "data/evaluation/family-retrieval-development-v1/development-pack.json",
        development_manifest_path=root / "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json",
        dense_dimensions=192)
    service = HumanKnowledgeIdentityRetriever(corpus(root), HashingEmbedding(192), config)
    started = now()
    rows = []
    for case in pack["cases"]:
        signals = extract_signals(case["query_text"])
        tick = time.perf_counter_ns()
        try:
            candidates, work = service.retrieve_with_work(signals, 5)
            row = {"candidates": [serialize(item) for item in candidates],
                "work": work.as_dict(), "error": None}
        except Exception as error:  # noqa: BLE001 - preserve every failed case; never retry it
            row = {"candidates": [], "work": None,
                "error": {"type": type(error).__name__, "message": str(error)}}
        rows.append({"case_id": case["case_id"], "query_text": case["query_text"], **row,
            "latency_ms": (time.perf_counter_ns() - tick) / 1e6})
    return {"schema_version": "pvr-family-retrieval-raw-v2", "query_pack_sha256": labels.QUERY_SHA,
        "artifact_sha256": labels.questions.ARTIFACT_SHA, "configuration": pack["winner"]["configuration"],
        "started_at": started, "completed_at": now(), "candidate_k": 5, "warmup_count": 0,
        "runtime": {"python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "process_count": 1, "host_isolated": False,
            "measured_boundary": "extraction_excluded_retrieval_and_serialization_included"},
        "index": service.character_index_metadata, "rows": rows}


def score(raw: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    if len(raw["rows"]) != 105 or [row["case_id"] for row in raw["rows"]] != [case["case_id"] for case in benchmark["cases"]]:
        raise ValueError("final rows must cover all105 ordered cases")
    positive_ranks, merge_ranks, failures = [], [], []
    styles: dict[str, list[int | None]] = defaultdict(list)
    groups: set[str] = set()
    forbidden = unrelated = errors = 0
    case_results = []
    for row, case in zip(raw["rows"], benchmark["cases"], strict=True):
        if row["query_text"] != case["query_text"]:
            raise ValueError("final query was rewritten")
        expected = case["expected"]
        candidates = row["candidates"]
        kind = case["case_type"]
        rank = None
        violations = []
        if row["error"] is not None:
            errors += 1
            violations.append("retrieval_error")
        if kind == "positive_family":
            rank = next((index for index, candidate in enumerate(candidates, 1)
                if candidate["knowledge_type"] == "review_family"
                and candidate["knowledge_id"] == expected["review_family_id"]
                and candidate["knowledge_uuid"] == expected["review_family_uuid"]), None)
            positive_ranks.append(rank)
            styles[case["challenge_style"]].append(rank)
            if rank is not None:
                groups.add(case["casting_group_id"])
            else:
                violations.append("positive_target_missed_at_5")
        elif kind == "merge_control":
            rank = next((index for index, candidate in enumerate(candidates, 1)
                if candidate["knowledge_type"] == "provisional_variant"
                and candidate["casting_id"] == expected["casting_id"]), None)
            merge_ranks.append(rank)
            if rank is None:
                violations.append("merge_target_missed_at_5")
        if kind in {"merge_control", "hold_control"}:
            hits = sum(candidate["knowledge_type"] == "review_family"
                and candidate["knowledge_id"] == expected["forbidden_review_family_id"] for candidate in candidates)
            forbidden += hits
            if hits:
                violations.append("forbidden_family_materialized")
        elif kind == "unrelated_control" and candidates:
            unrelated += 1
            violations.append("unrelated_nonempty")
        result = {"case_id": case["case_id"], "case_type": kind, "target_rank": rank,
            "violations": violations}
        case_results.append(result)
        if violations:
            failures.append({**result, "query_text": case["query_text"], "expected": expected,
                "returned_knowledge_ids": [candidate["knowledge_id"] for candidate in candidates]})
    if len(positive_ranks) != 84 or len(merge_ranks) != 4 or any(len(styles[style]) != 42 for style in ("marketplace_noise", "lexical_variation")):
        raise ValueError("final denominators changed")
    counts: dict[str, Any] = {"positive_total": 84, "positive_hits_at_5": sum(rank is not None for rank in positive_ranks),
        "positive_hits_at_1": sum(rank == 1 for rank in positive_ranks),
        "positive_reciprocal_rank_sum": sum(1 / rank for rank in positive_ranks if rank is not None),
        "covered_families": len(groups), "family_total": 42,
        "merge_total": 4, "merge_hits_at_5": sum(rank is not None for rank in merge_ranks),
        "forbidden_family_candidates": forbidden, "unrelated_total": 10, "unrelated_nonempty": unrelated,
        "retrieval_errors": errors, "positive_styles": {style: {"total": 42,
            "hits_at_5": sum(rank is not None for rank in ranks)} for style, ranks in sorted(styles.items())}}
    metrics: dict[str, Any] = {"positive_recall_at_5": counts["positive_hits_at_5"] / 84,
        "positive_recall_at_1": counts["positive_hits_at_1"] / 84,
        "mrr_at_5": counts["positive_reciprocal_rank_sum"] / 84,
        "family_coverage_at_5": len(groups) / 42,
        "merge_recall_at_5": counts["merge_hits_at_5"] / 4,
        "forbidden_family_candidates": forbidden, "unrelated_nonempty": unrelated,
        "positive_style_recall_at_5": {style: count["hits_at_5"] / 42 for style, count in counts["positive_styles"].items()}}
    gates = []
    for name, threshold in benchmark["final_gates"].items():
        values = metrics[name] if name == "positive_style_recall_at_5" else {name: metrics[name]}
        equality = name in {"merge_recall_at_5", "forbidden_family_candidates", "unrelated_nonempty"}
        for label, value in values.items():
            gates.append({"name": label, "operator": "=" if equality else ">=", "threshold": threshold,
                "actual": value, "passed": value == threshold if equality else value >= threshold})
    samples = sorted(row["latency_ms"] for row in raw["rows"])
    cost = {"sample_count": 105, "percentile_method": "nearest_rank",
        "p50_ms": samples[math.ceil(.50 * 105) - 1], "p95_ms": samples[math.ceil(.95 * 105) - 1],
        "final_latency_has_no_new_acceptance_threshold": True}
    return {"raw_counts": counts, "metrics": metrics, "gates": gates,
        "verdict": "PASS" if all(gate["passed"] for gate in gates) and not errors else "FAIL",
        "case_results": case_results, "failures": failures, "cost_diagnostic": cost,
        "abstentions": dict(Counter(row["work"]["abstention_reason"] for row in raw["rows"]
            if row["work"] and row["work"]["abstention_reason"]))}


def hashes(root: Path) -> dict[str, str]:
    names = (*SOURCES, *labels.source_hashes(root), *(str(labels.DIRECTORY / name) for name in labels.FILES))
    return {name: sha(root / name) for name in names}


def preflight(root: Path) -> str:
    # Isolated integrity process may validate labels; collector/runner never parse them before raw publish.
    process = subprocess.run([sys.executable, str(root / labels.SOURCES[1]), "--check-committed"],
        cwd=root, capture_output=True, text=True, check=False)
    if process.returncode:
        raise ValueError("committed benchmark preflight failed: " + process.stderr)
    commit = labels.questions.git(root, "rev-parse", "HEAD").stdout.strip()
    for name in SOURCES:
        result = labels.questions.git(root, "show", f"{commit}:{name}")
        if result.returncode or result.stdout.encode() != (root / name).read_bytes():
            raise ValueError("final evaluation code must be committed unchanged before collection")
    return cast(str, commit)


def run(root: Path = ROOT) -> None:
    directory = root / DIRECTORY
    if directory.exists():
        raise ValueError("final run already reserved; no retry, replacement or tuning allowed")
    commit = preflight(root)
    before = {name: sha(root / name) for name in SOURCES}
    directory.mkdir(parents=True, exist_ok=False)
    # Durable reservation survives errors/interruption; never erase it to permit another final run.
    start = {"schema_version": "pvr-family-retrieval-run-start-v2", "started_at": now(),
        "code_commit": commit, "source_sha256": before,
        "query_pack_sha256": labels.QUERY_SHA, "one_shot": True}
    publish_new(directory / "run-start.json", start)
    raw = collect(root)
    publish_new(directory / "raw-results.json", raw)
    # All105 outputs are now durable. Only now may this process parse new-final labels.
    benchmark = labels.validate(root)
    report = {"schema_version": "pvr-family-retrieval-evaluation-v2", "scored_at": now(),
        "benchmark_version": benchmark["benchmark_version"], "code_commit": commit,
        "raw_results_sha256": sha(directory / "raw-results.json"), "source_sha256": hashes(root),
        "raw_published_before_label_scoring": True, "limitations": LIMITATIONS, **score(raw, benchmark)}
    if before != {name: sha(root / name) for name in SOURCES}:
        raise ValueError("evaluation source changed; retain raw evidence and stop")
    publish_new(directory / "evaluation.json", report)
    with (directory / "evaluation.md").open("x", encoding="utf-8") as handle:
        handle.write(markdown(report))
    print("Final-v2:", report["verdict"], report["metrics"], flush=True)


def check(root: Path = ROOT) -> dict[str, Any]:
    directory = root / DIRECTORY
    start = load_object(directory / "run-start.json")
    raw = load_object(directory / "raw-results.json")
    report = load_object(directory / "evaluation.json")
    benchmark = labels.validate(root)
    pack = load_object(root / labels.questions.DIRECTORY / "query-pack.json")
    if (raw["schema_version"] != "pvr-family-retrieval-raw-v2" or raw["query_pack_sha256"] != labels.QUERY_SHA
            or raw["artifact_sha256"] != labels.questions.ARTIFACT_SHA
            or raw["configuration"] != pack["winner"]["configuration"]
            or type(raw["candidate_k"]) is not int or raw["candidate_k"] != 5 or raw["warmup_count"] != 0
            or len(raw["rows"]) != 105 or start["one_shot"] is not True
            or start["source_sha256"] != {name: sha(root / name) for name in SOURCES}
            or start["query_pack_sha256"] != labels.QUERY_SHA):
        raise ValueError("final raw/start metadata changed")
    if not (datetime.fromisoformat(start["started_at"]) <= datetime.fromisoformat(raw["started_at"])
            <= datetime.fromisoformat(raw["completed_at"]) <= datetime.fromisoformat(report["scored_at"])):
        raise ValueError("retrieval/scoring event order invalid")
    catalog = corpus(root)
    expected_index = HumanKnowledgeIdentityRetriever(catalog, HashingEmbedding(192),
        HumanKnowledgeV4Config(**raw["configuration"])).character_index_metadata
    runtime = raw["runtime"]
    if (labels.questions.json_text(raw["index"]) != labels.questions.json_text(expected_index)
            or set(runtime) != {"python", "system", "machine", "process_count", "host_isolated", "measured_boundary"}
            or any(not isinstance(runtime[name], str) or not runtime[name] for name in ("python", "system", "machine"))
            or type(runtime["process_count"]) is not int or runtime["process_count"] != 1
            or runtime["host_isolated"] is not False
            or runtime["measured_boundary"] != "extraction_excluded_retrieval_and_serialization_included"):
        raise ValueError("final runtime/index metadata changed")
    documents = {str(item.knowledge_uuid): item for item in catalog.documents}
    for row in raw["rows"]:
        if (set(row) != {"case_id", "query_text", "candidates", "work", "error", "latency_ms"}
                or type(row["latency_ms"]) not in {int, float}
                or not math.isfinite(row["latency_ms"]) or row["latency_ms"] < 0):
            raise ValueError("invalid final raw case/sample")
        if row["error"] is None:
            _check_candidates(row, documents, raw["configuration"])
        elif (row["candidates"] or row["work"] is not None
                or set(row["error"]) != {"type", "message"}
                or not all(isinstance(value, str) for value in row["error"].values())):
            raise ValueError("retrieval error has partial or invalid evidence")
    commit = start["code_commit"]
    if labels.questions.git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode:
        raise ValueError("evaluation code commit not an ancestor")
    for name in SOURCES:
        result = labels.questions.git(root, "show", f"{commit}:{name}")
        if result.returncode or result.stdout.encode() != (root / name).read_bytes():
            raise ValueError("evaluation source differs from run commit")
    expected = {"schema_version": "pvr-family-retrieval-evaluation-v2", "scored_at": report["scored_at"],
        "benchmark_version": benchmark["benchmark_version"], "code_commit": commit,
        "raw_results_sha256": sha(directory / "raw-results.json"), "source_sha256": hashes(root),
        "raw_published_before_label_scoring": True, "limitations": LIMITATIONS, **score(raw, benchmark)}
    if labels.questions.json_text(report) != labels.questions.json_text(expected):
        raise ValueError("final evaluation does not reproduce from raw ranks")
    if (directory / "evaluation.md").read_text() != markdown(report):
        raise ValueError("final Markdown does not reproduce")
    return cast(dict[str, Any], report)


def markdown(report: dict[str, Any]) -> str:
    lines = ["# Final-v2 family retrieval", "", f"Verdict: **{report['verdict']}** (family retrieval only).",
        "No final-set tuning/default deployment/canonical or release-variant claim.", "",
        "| Gate | Actual | Required | Result |", "|---|---:|---:|---|"]
    for gate in report["gates"]:
        lines.append(f"| {gate['name']} | {gate['actual']:.6f} | {gate['operator']}{gate['threshold']} | {'PASS' if gate['passed'] else 'FAIL'} |")
    lines += ["", f"Counts: `{json.dumps(report['raw_counts'], sort_keys=True)}`",
        "", f"Diagnostic cost: `{json.dumps(report['cost_diagnostic'], sort_keys=True)}`",
        "", f"Abstentions: `{json.dumps(report['abstentions'], sort_keys=True)}`", "", "## Case errors/misses", ""]
    if not report["failures"]:
        lines.append("None.")
    for failure in report["failures"]:
        query = failure["query_text"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"- `{failure['case_id']}`: {query}; target rank={failure['target_rank']}; {', '.join(failure['violations'])}; returned={failure['returned_knowledge_ids']}")
    lines += ["", "## Limitations", "", *[f"- {value}" for value in report["limitations"]], ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.run:
        run()
    else:
        report = check()
        print("Final-v2 raw/Markdown reproduced without retrieval:", report["verdict"])


if __name__ == "__main__":
    main()
