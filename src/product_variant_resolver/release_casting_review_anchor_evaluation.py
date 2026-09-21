"""Evaluate the frozen anchored-admission policy on immutable private shadow evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from .human_knowledge import HumanKnowledgeCatalog
from .human_knowledge_admission_development import identity_token_coverage
from .human_knowledge_anchor_admission_development import (
    DATA_DIRECTORY as POLICY_DATA_DIRECTORY,
)
from .human_knowledge_anchor_admission_development import (
    REPORT_DIRECTORY as POLICY_REPORT_DIRECTORY,
)
from .human_knowledge_anchor_admission_development import SOURCE as POLICY_SOURCE
from .human_knowledge_anchor_admission_development import check as check_policy
from .release_casting_review_evaluation import (
    EVALUATION_VERSION as UPSTREAM_EVALUATION_VERSION,
)
from .release_casting_review_evaluation import (
    PRIVATE_DIRECTORY_NAME as UPSTREAM_PRIVATE_DIRECTORY_NAME,
)
from .release_casting_review_evaluation import (
    PUBLIC_DIRECTORY_NAME as UPSTREAM_PUBLIC_DIRECTORY_NAME,
)
from .release_casting_review_evaluation import (
    _load_object,
    _sha256_bytes,
    _sha256_path,
    _shadow_catalog,
    _stable_json,
)
from .release_casting_review_evaluation import (
    check as check_upstream,
)
from .release_casting_review_knowledge import check_projection

VERSION = "local-release-review-family-anchor-admission-evaluation-v2"
PROTOCOL_SCHEMA = "pvr-local-release-review-family-anchor-admission-protocol-v2"
RESULT_SCHEMA = "pvr-local-release-review-family-anchor-admission-result-v2"
PUBLIC_SCHEMA = "pvr-local-release-review-family-anchor-admission-public-v2"
SOURCE = "src/product_variant_resolver/release_casting_review_anchor_evaluation.py"
UPSTREAM_SOURCE = "src/product_variant_resolver/release_casting_review_evaluation.py"
PROTOCOL_DIRECTORY = Path("data/evaluation") / VERSION
PRIVATE_DIRECTORY_NAME = VERSION
PUBLIC_DIRECTORY_NAME = VERSION
SECONDARY_THRESHOLD = 0.75
FIXED_GATES: dict[str, float | int] = {
    "positive_recall_at_5": 1.0,
    "positive_recall_at_1": 0.8,
    "family_coverage_at_5": 1.0,
    "hard_negative_forbidden_hits": 0,
    "hard_negative_forbidden_rank1_hits": 0,
    "retrieval_errors": 0,
    "admission_errors": 0,
}
LIMITATIONS = (
    "same_twenty_owner_project_cases_as_v1_not_population_accuracy",
    "five_local_families_only",
    "rank1_anchor_may_preserve_unseen_wrong_top1",
    "casting_family_truth_not_release_variant_or_color_truth",
    "offline_post_retrieval_policy_scoring_only",
    "pass_does_not_activate_runtime",
)


def _protocol_directory(root: Path) -> Path:
    return root / PROTOCOL_DIRECTORY


def _upstream_private_directory(root: Path) -> Path:
    return root / "data/external/hot-wheels-wiki" / str(UPSTREAM_PRIVATE_DIRECTORY_NAME)


def _private_directory(root: Path) -> Path:
    return root / "data/external/hot-wheels-wiki" / PRIVATE_DIRECTORY_NAME


def _upstream_public_directory(root: Path) -> Path:
    return root / "reports" / str(UPSTREAM_PUBLIC_DIRECTORY_NAME)


def _public_directory(root: Path) -> Path:
    return root / "reports" / PUBLIC_DIRECTORY_NAME


def _policy_files() -> tuple[Path, ...]:
    return (
        POLICY_DATA_DIRECTORY / "protocol.json",
        POLICY_DATA_DIRECTORY / "protocol-manifest.json",
        POLICY_REPORT_DIRECTORY / "selection.json",
        POLICY_REPORT_DIRECTORY / "selection.md",
        Path(POLICY_SOURCE),
    )


def _upstream_private_files(root: Path) -> tuple[Path, ...]:
    directory = _upstream_private_directory(root)
    return tuple(
        directory / name
        for name in ("query-pack.json", "benchmark.json", "raw-results.json", "result.json")
    )


def _upstream_public_files(root: Path) -> tuple[Path, ...]:
    directory = _upstream_public_directory(root)
    return directory / "manifest.json", directory / "report.md"


def _source_hashes(root: Path) -> dict[str, str]:
    relative = (*_policy_files(), Path(UPSTREAM_SOURCE), Path(SOURCE))
    hashes = {str(path): _sha256_path(root / path) for path in relative}
    for path in (*_upstream_private_files(root), *_upstream_public_files(root)):
        hashes[str(path.relative_to(root))] = _sha256_path(path)
    return dict(sorted(hashes.items()))


def _selected_policy(root: Path) -> dict[str, Any]:
    selection = check_policy(root)
    winner = selection.get("winner")
    if (
        not isinstance(winner, dict)
        or winner.get("configuration_id") != "secondary-075"
        or winner.get("secondary_minimum_identity_token_coverage") != SECONDARY_THRESHOLD
        or winner.get("improves_over_baseline") is not True
        or winner.get("status") != "qualified_for_new_private_shadow_evaluation_only"
    ):
        raise ValueError("public development selection is not the frozen private-gate policy")
    return winner


def build_protocol(root: Path) -> dict[str, Any]:
    upstream = check_upstream(root)
    winner = _selected_policy(root)
    if upstream.get("verdict") != "FAIL" or upstream.get("counts", {}).get("positive_cases") != 15:
        raise ValueError("upstream private evaluation differs from the immutable v1 evidence")
    projection = check_projection(root)
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_private_policy_scoring",
        "source_sha256": _source_hashes(root),
        "upstream": {
            "evaluation_version": UPSTREAM_EVALUATION_VERSION,
            "verdict": "FAIL",
            "positive_cases": 15,
            "hard_negative_cases": 5,
            "raw_results_sha256": _sha256_path(
                _upstream_private_directory(root) / "raw-results.json"
            ),
            "projection_sha256": projection["projection_sha256"],
        },
        "policy": {
            "development_configuration_id": winner["configuration_id"],
            "development_protocol_sha256": _sha256_path(
                root / POLICY_DATA_DIRECTORY / "protocol.json"
            ),
            "development_selection_sha256": _sha256_path(
                root / POLICY_REPORT_DIRECTORY / "selection.json"
            ),
            "rank_1": "always_admit_anchor",
            "ranks_2_through_5": "identity_token_coverage_gte_threshold",
            "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
            "source_order_preserved": True,
        },
        "gates": FIXED_GATES,
        "private_result_directory": str(
            Path("data/external/hot-wheels-wiki") / PRIVATE_DIRECTORY_NAME
        ),
        "public_result_directory": str(Path("reports") / PUBLIC_DIRECTORY_NAME),
        "new_retrieval_calls": 0,
        "eligible_for": ["opt_in_runtime_planning_only_if_pass"],
        "excluded_from": [
            "automatic_runtime_activation",
            "canonical_truth",
            "release_variant_truth",
            "color_truth",
            "postgresql_writes",
        ],
    }


def _assert_file(path: Path, content: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != content:
        raise ValueError(f"{path} differs from deterministic artifact")


def freeze_protocol(root: Path) -> str:
    protocol = build_protocol(root)
    manifest = {
        "schema_version": "pvr-local-release-review-family-anchor-admission-manifest-v2",
        "version": VERSION,
        "protocol_sha256": _sha256_bytes(_stable_json(protocol).encode()),
        "source_sha256": protocol["source_sha256"],
        "upstream_raw_results_sha256": protocol["upstream"]["raw_results_sha256"],
        "new_retrieval_calls": 0,
    }
    outputs = {
        "protocol.json": _stable_json(protocol),
        "protocol-manifest.json": _stable_json(manifest),
    }
    directory = _protocol_directory(root)
    if directory.exists():
        if {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError("private-evaluation protocol directory is partial or conflicting")
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
        "schema_version": "pvr-local-release-review-family-anchor-admission-manifest-v2",
        "version": VERSION,
        "protocol_sha256": _sha256_bytes(_stable_json(expected).encode()),
        "source_sha256": expected["source_sha256"],
        "upstream_raw_results_sha256": expected["upstream"]["raw_results_sha256"],
        "new_retrieval_calls": 0,
    }
    directory = _protocol_directory(root)
    _assert_file(directory / "protocol.json", _stable_json(expected))
    _assert_file(directory / "protocol-manifest.json", _stable_json(manifest))
    return expected


def _admit_row(
    row: dict[str, Any], catalog: HumanKnowledgeCatalog
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    documents = {str(document.knowledge_uuid): document for document in catalog.documents}
    admitted = []
    abstained = []
    query = str(row["query_text"])
    for candidate in row["candidates"]:
        document = documents.get(candidate["knowledge_uuid"])
        if (
            document is None
            or document.knowledge_id != candidate["knowledge_id"]
            or document.knowledge_type != candidate["knowledge_type"]
        ):
            raise ValueError("private candidate differs from the validated shadow catalog")
        coverage = identity_token_coverage(query, document)
        enriched = {**candidate, "identity_token_coverage": coverage}
        if candidate["rrf_rank"] == 1 or coverage + 1e-12 >= SECONDARY_THRESHOLD:
            admitted.append(enriched)
        else:
            abstained.append(enriched)
    return admitted, abstained


def score(
    raw: dict[str, Any], benchmark: dict[str, Any], catalog: HumanKnowledgeCatalog
) -> dict[str, Any]:
    rows = raw.get("rows")
    cases = benchmark.get("cases")
    if (
        not isinstance(rows, list)
        or not isinstance(cases, list)
        or len(rows) != 20
        or len(cases) != 20
    ):
        raise ValueError("private evidence does not contain the frozen 20 cases")
    positive_ranks: list[int | None] = []
    covered: set[str] = set()
    forbidden_hits = 0
    forbidden_rank1_hits = 0
    retrieval_errors = 0
    admission_errors = 0
    source_candidates = 0
    admitted_candidates = 0
    abstained_candidates = 0
    case_results = []
    for row, case in zip(rows, cases, strict=True):
        if row.get("case_id") != case.get("case_id"):
            raise ValueError("private raw result order differs from frozen labels")
        retrieval_errors += row.get("error") is not None
        source_candidates += len(row["candidates"])
        try:
            admitted, abstained = _admit_row(row, catalog)
        except Exception as error:  # noqa: BLE001 - preserve admission failure in private result
            admission_errors += 1
            admitted, abstained = [], []
            if row.get("case_type") == "positive_family":
                positive_ranks.append(None)
            case_results.append(
                {
                    "case_id": row["case_id"],
                    "case_type": row["case_type"],
                    "admission_error": {"type": type(error).__name__, "message": str(error)},
                }
            )
            continue
        admitted_candidates += len(admitted)
        abstained_candidates += len(abstained)
        expected = case["expected"]
        result: dict[str, Any] = {
            "case_id": row["case_id"],
            "case_type": row["case_type"],
            "source_candidate_count": len(row["candidates"]),
            "admitted_source_ranks": [item["rrf_rank"] for item in admitted],
            "abstained_source_ranks": [item["rrf_rank"] for item in abstained],
            "admission_error": None,
        }
        if row["case_type"] == "positive_family":
            target_id = expected["review_family_id"]
            target_uuid = expected["review_family_uuid"]
            target = next(
                (
                    (index, candidate)
                    for index, candidate in enumerate(admitted, 1)
                    if candidate["knowledge_type"] == "review_family"
                    and candidate["knowledge_id"] == target_id
                    and candidate["knowledge_uuid"] == target_uuid
                ),
                None,
            )
            rank = target[0] if target else None
            positive_ranks.append(rank)
            if rank is not None:
                covered.add(target_id)
            result["target_admitted_rank"] = rank
            result["target_source_rank"] = target[1]["rrf_rank"] if target else None
        elif row["case_type"] == "hard_negative":
            forbidden_id = expected["forbidden_review_family_id"]
            hits = [item for item in admitted if item["knowledge_id"] == forbidden_id]
            forbidden_hits += len(hits)
            rank1_hits = sum(item["rrf_rank"] == 1 for item in hits)
            forbidden_rank1_hits += rank1_hits
            result["forbidden_hits"] = len(hits)
            result["forbidden_rank1_hits"] = rank1_hits
        else:
            raise ValueError("private raw result case type differs from benchmark")
        case_results.append(result)
    if len(positive_ranks) != 15:
        raise ValueError("positive denominator differs from frozen private benchmark")
    metrics: dict[str, float | int] = {
        "positive_recall_at_5": sum(rank is not None for rank in positive_ranks) / 15,
        "positive_recall_at_1": sum(rank == 1 for rank in positive_ranks) / 15,
        "family_coverage_at_5": len(covered) / 5,
        "hard_negative_forbidden_hits": forbidden_hits,
        "hard_negative_forbidden_rank1_hits": forbidden_rank1_hits,
        "retrieval_errors": retrieval_errors,
        "admission_errors": admission_errors,
    }
    gates = []
    for name, threshold in FIXED_GATES.items():
        actual = metrics[name]
        operator = (
            "="
            if name
            not in {
                "positive_recall_at_5",
                "positive_recall_at_1",
                "family_coverage_at_5",
            }
            else ">="
        )
        passed = actual == threshold if operator == "=" else actual >= threshold
        gates.append(
            {
                "name": name,
                "operator": operator,
                "threshold": threshold,
                "actual": actual,
                "passed": passed,
            }
        )
    return {
        "schema_version": RESULT_SCHEMA,
        "version": VERSION,
        "policy": {
            "configuration_id": "secondary-075",
            "secondary_minimum_identity_token_coverage": SECONDARY_THRESHOLD,
            "rank_1_anchor": True,
        },
        "counts": {
            "positive_cases": 15,
            "hard_negative_cases": 5,
            "positive_hits_at_5": sum(rank is not None for rank in positive_ranks),
            "positive_hits_at_1": sum(rank == 1 for rank in positive_ranks),
            "covered_local_families": len(covered),
            "hard_negative_forbidden_hits": forbidden_hits,
            "hard_negative_forbidden_rank1_hits": forbidden_rank1_hits,
            "retrieval_errors": retrieval_errors,
            "admission_errors": admission_errors,
            "source_candidates": source_candidates,
            "admitted_candidates": admitted_candidates,
            "abstained_candidates": abstained_candidates,
        },
        "metrics": metrics,
        "gates": gates,
        "verdict": "PASS" if all(gate["passed"] for gate in gates) else "FAIL",
        "case_results": case_results,
    }


def _private_result(root: Path) -> dict[str, Any]:
    upstream_private = _upstream_private_directory(root)
    raw = _load_object(upstream_private / "raw-results.json")
    benchmark = _load_object(upstream_private / "benchmark.json")
    projection = check_projection(root)
    catalog = _shadow_catalog(root, projection)
    result = score(raw, benchmark, catalog)
    return {
        **result,
        "protocol_sha256": _sha256_path(_protocol_directory(root) / "protocol.json"),
        "upstream": {
            "evaluation_version": UPSTREAM_EVALUATION_VERSION,
            "raw_results_sha256": _sha256_path(upstream_private / "raw-results.json"),
            "benchmark_sha256": _sha256_path(upstream_private / "benchmark.json"),
            "query_pack_sha256": _sha256_path(upstream_private / "query-pack.json"),
            "projection_sha256": projection["projection_sha256"],
        },
        "new_retrieval_calls": 0,
        "limitations": list(LIMITATIONS),
    }


def _public_manifest(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA,
        "version": VERSION,
        "status": "offline_shadow_policy_evaluation_complete_not_runtime",
        "verdict": result["verdict"],
        "public_scope": "aggregate_metrics_gates_hashes_policy_and_zero_effects_only",
        "hashes": {
            "protocol_sha256": result["protocol_sha256"],
            "upstream_raw_results_sha256": result["upstream"]["raw_results_sha256"],
            "upstream_benchmark_sha256": result["upstream"]["benchmark_sha256"],
            "upstream_query_pack_sha256": result["upstream"]["query_pack_sha256"],
            "projection_sha256": result["upstream"]["projection_sha256"],
            "private_result_sha256": _sha256_bytes(_stable_json(result).encode()),
        },
        "policy": result["policy"],
        "counts": result["counts"],
        "metrics": result["metrics"],
        "gates": result["gates"],
        "new_retrieval_calls": 0,
        "limitations": result["limitations"],
        "downstream_effects": {
            "runtime_documents_added": 0,
            "canonical_promotions": 0,
            "reviewed_colors": 0,
            "postgresql_writes": 0,
            "api_changes": 0,
            "network_requests": 0,
        },
    }


def _render_report(manifest: dict[str, Any]) -> str:
    metrics = manifest["metrics"]
    counts = manifest["counts"]
    return "\n".join(
        [
            "# Local review-family anchored admission — private shadow public summary",
            "",
            f"Verdict: **{manifest['verdict']}** for the versioned offline policy evaluation.",
            "",
            "- Frozen policy: rank-1 anchor; secondary identity coverage >= 0.75",
            "- New retrieval calls: 0 (immutable v1 raw evidence reused)",
            f"- Positive Recall@5: {metrics['positive_recall_at_5']:.4f}",
            f"- Positive Recall@1: {metrics['positive_recall_at_1']:.4f}",
            f"- Local-family coverage@5: {metrics['family_coverage_at_5']:.4f}",
            f"- Hard-negative forbidden hits: {metrics['hard_negative_forbidden_hits']}",
            (
                "- Hard-negative forbidden rank-1 hits: "
                f"{metrics['hard_negative_forbidden_rank1_hits']}"
            ),
            f"- Retrieval errors: {metrics['retrieval_errors']}",
            f"- Admission errors: {metrics['admission_errors']}",
            (
                f"- Candidates: {counts['admitted_candidates']} admitted / "
                f"{counts['source_candidates']} source; {counts['abstained_candidates']} abstained"
            ),
            "",
            "Queries, labels, candidate identities, coverage, ranks, and case results remain private.",
            "PASS authorizes only opt-in runtime planning; it does not activate Dual RAG, establish",
            "canonical/release/color truth, or write PostgreSQL.",
            "",
        ]
    )


def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def run(root: Path | None = None) -> tuple[dict[str, Any], str]:
    root = (root or Path.cwd()).resolve()
    validate_protocol(root)
    private = _private_directory(root)
    public = _public_directory(root)
    result_path = private / "result.json"
    if result_path.exists():
        return check(root), "unchanged"
    if private.exists() or public.exists():
        raise ValueError("partial v2 evaluation outputs exist; refusing to score")
    result = _private_result(root)
    manifest = _public_manifest(result)
    private.mkdir(parents=True)
    try:
        _write_new(result_path, _stable_json(result))
        public.mkdir(parents=True)
        _write_new(public / "manifest.json", _stable_json(manifest))
        _write_new(public / "report.md", _render_report(manifest))
    except BaseException:
        for directory in (public, private):
            if directory.exists():
                for path in directory.iterdir():
                    path.unlink()
                directory.rmdir()
        raise
    return check(root), "created"


def check(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path.cwd()).resolve()
    validate_protocol(root)
    check_upstream(root)
    expected = _private_result(root)
    private_path = _private_directory(root) / "result.json"
    actual = cast(dict[str, Any], _load_object(private_path))
    if actual != expected:
        raise ValueError("private v2 evaluation result differs from deterministic scoring")
    manifest = _load_object(_public_directory(root) / "manifest.json")
    if manifest != _public_manifest(actual):
        raise ValueError("public v2 manifest differs from private aggregate result")
    if (_public_directory(root) / "report.md").read_text(encoding="utf-8") != _render_report(
        manifest
    ):
        raise ValueError("public v2 report differs from manifest")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate frozen anchored admission privately")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--freeze-protocol", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_protocol:
        operation = freeze_protocol(root)
        output = {"operation": operation, "new_retrieval_calls": 0}
    elif arguments.check:
        result = check(root)
        output = {"operation": "valid", "verdict": result["verdict"], "counts": result["counts"]}
    else:
        result, operation = run(root)
        output = {"operation": operation, "verdict": result["verdict"], "counts": result["counts"]}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
