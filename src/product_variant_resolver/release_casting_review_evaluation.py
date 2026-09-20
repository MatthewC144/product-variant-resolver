"""Evaluate private local review families without changing the Dual RAG runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from .human_knowledge import (
    HumanKnowledgeCatalog,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
)
from .human_knowledge_identity import HumanKnowledgeIdentityRetriever, HumanKnowledgeV4Config
from .release_casting_review_knowledge import check_projection
from .retrieval import HashingEmbedding
from .signals import extract_signals

SCHEMA_VERSION = "pvr-local-release-review-family-retrieval-evaluation-v1"
QUERY_SCHEMA_VERSION = "pvr-local-release-review-family-query-pack-v1"
BENCHMARK_SCHEMA_VERSION = "pvr-local-release-review-family-benchmark-v1"
RAW_SCHEMA_VERSION = "pvr-local-release-review-family-raw-results-v1"
PUBLIC_SCHEMA_VERSION = "pvr-local-release-review-family-evaluation-public-v1"
EVALUATION_VERSION = "local-release-review-family-retrieval-evaluation-v1"
PRIVATE_DIRECTORY_NAME = EVALUATION_VERSION
PUBLIC_DIRECTORY_NAME = EVALUATION_VERSION
CANDIDATE_LIMIT = 5
DIMENSIONS = 192
CHARACTER_SCORE_FLOOR = 0.5
CHARACTER_RRF_WEIGHT = 1.0
FIXED_GATES: dict[str, float | int] = {
    "positive_recall_at_5": 1.0,
    "positive_recall_at_1": 0.8,
    "family_coverage_at_5": 1.0,
    "hard_negative_forbidden_hits": 0,
    "retrieval_errors": 0,
}
LIMITATIONS = (
    "twenty_owner_project_cases_not_population_accuracy",
    "five_local_families_only",
    "casting_family_truth_not_release_variant_or_color_truth",
    "hashing_v1_not_neural",
    "in_process_offline_retrieval_only",
    "pass_does_not_authorize_runtime_integration",
)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return payload


def _private_directory(root: Path) -> Path:
    return root / "data/external/hot-wheels-wiki" / PRIVATE_DIRECTORY_NAME


def _public_directory(root: Path) -> Path:
    return root / "reports" / PUBLIC_DIRECTORY_NAME


def _validate_query_pack(pack: dict[str, Any], projection: dict[str, Any]) -> list[dict[str, Any]]:
    if pack.get("schema_version") != QUERY_SCHEMA_VERSION:
        raise ValueError("private query-pack schema differs from contract")
    if pack.get("evaluation_version") != EVALUATION_VERSION:
        raise ValueError("private query-pack version differs from contract")
    if pack.get("projection_sha256") != projection.get("projection_sha256"):
        raise ValueError("private query pack is not bound to the current projection")
    cases = pack.get("cases")
    if not isinstance(cases, list) or len(cases) != 20:
        raise ValueError("private query pack must contain exactly 20 cases")
    expected_fields = {"case_id", "case_type", "query_text"}
    positive = 0
    hard_negative = 0
    case_ids: set[str] = set()
    queries: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != expected_fields:
            raise ValueError("private query case fields differ from contract")
        case_id = case.get("case_id")
        case_type = case.get("case_type")
        query = case.get("query_text")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("private query case contains a blank case ID")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("private query case contains blank text")
        if case_type == "positive_family":
            positive += 1
        elif case_type == "hard_negative":
            hard_negative += 1
        else:
            raise ValueError("private query case type differs from contract")
        normalized_query = extract_signals(query).normalized_title
        if case_id in case_ids or normalized_query in queries:
            raise ValueError("private query case IDs and normalized queries must be unique")
        case_ids.add(case_id)
        queries.add(normalized_query)
    if (positive, hard_negative) != (15, 5):
        raise ValueError("private query pack must contain 15 positives and five hard negatives")
    return cases


def _local_documents(projection: dict[str, Any]) -> list[ReviewFamilyKnowledgeDocument]:
    rows = projection.get("documents")
    if not isinstance(rows, list) or len(rows) != 5:
        raise ValueError("local projection must contain exactly five documents")
    documents: list[ReviewFamilyKnowledgeDocument] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("knowledge_type") != "review_family":
            raise ValueError("local projection contains an invalid document")
        aliases = row.get("aliases")
        source_ids = row.get("source_record_ids")
        if not isinstance(aliases, list) or not isinstance(source_ids, list):
            raise TypeError("local projection aliases or source IDs are invalid")
        documents.append(
            ReviewFamilyKnowledgeDocument(
                review_family_uuid=UUID(str(row["review_family_uuid"])),
                review_family_id=str(row["review_family_id"]),
                brand=str(row["brand"]),
                casting=str(row["casting"]),
                aliases=tuple(str(value) for value in aliases),
                source_record_ids=tuple(str(value) for value in source_ids),
                identity_status=str(row["identity_status"]),
            )
        )
    return documents


def _shadow_catalog(root: Path, projection: dict[str, Any]) -> HumanKnowledgeCatalog:
    base = load_human_knowledge_catalog(
        root / "data/human_backed_catalog.json",
        root / "data/review_family_knowledge.json",
        root / "data/review_family_knowledge_manifest.json",
    )
    local = _local_documents(projection)
    catalog = HumanKnowledgeCatalog(
        base.version,
        f"{base.review_family_version}+{projection['knowledge_version']}",
        [*base.documents, *local],
    )
    if len(catalog.documents) != 147 or catalog.review_family_document_count != 47:
        raise ValueError("shadow catalog must contain 147 documents and 47 review families")
    return catalog


def _serialize_candidate(candidate: Any) -> dict[str, Any]:
    return {
        "knowledge_id": candidate.document.knowledge_id,
        "knowledge_uuid": str(candidate.document.knowledge_uuid),
        "knowledge_type": candidate.document.knowledge_type,
        "rrf_rank": candidate.rrf_rank,
    }


def collect(root: Path | None = None) -> dict[str, Any]:
    """Retrieve each unlabeled private query once; this function never opens the benchmark."""
    root = root or Path.cwd()
    projection = check_projection(root)
    private = _private_directory(root)
    query_path = private / "query-pack.json"
    pack = _load_object(query_path)
    cases = _validate_query_pack(pack, projection)
    catalog = _shadow_catalog(root, projection)
    config = HumanKnowledgeV4Config(
        CHARACTER_SCORE_FLOOR,
        CHARACTER_RRF_WEIGHT,
        artifact_version="local-release-review-family-shadow-v1",
        artifact_sha256=str(projection["projection_sha256"]),
    )
    retriever = HumanKnowledgeIdentityRetriever(catalog, HashingEmbedding(DIMENSIONS), config)
    rows: list[dict[str, Any]] = []
    for case in cases:
        try:
            candidates, work = retriever.retrieve_with_work(
                extract_signals(str(case["query_text"])), CANDIDATE_LIMIT
            )
            row = {
                "candidates": [_serialize_candidate(candidate) for candidate in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - preserve a one-shot case failure
            row = {
                "candidates": [],
                "work": None,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        rows.append(
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "query_text": case["query_text"],
                **row,
            }
        )
    return {
        "schema_version": RAW_SCHEMA_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "query_pack_sha256": _sha256_path(query_path),
        "projection_sha256": projection["projection_sha256"],
        "candidate_limit": CANDIDATE_LIMIT,
        "retriever": {
            "version": retriever.version,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
        },
        "corpus": {
            "base_documents": 142,
            "local_documents": 5,
            "total_documents": 147,
            "review_family_documents": 47,
        },
        "rows": rows,
    }


def _validate_benchmark(
    benchmark: dict[str, Any], pack: dict[str, Any], projection: dict[str, Any], query_sha: str
) -> list[dict[str, Any]]:
    if benchmark.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
        raise ValueError("private benchmark schema differs from contract")
    if benchmark.get("evaluation_version") != EVALUATION_VERSION:
        raise ValueError("private benchmark version differs from contract")
    if benchmark.get("query_pack_sha256") != query_sha:
        raise ValueError("private benchmark is not bound to the query pack")
    if benchmark.get("projection_sha256") != projection.get("projection_sha256"):
        raise ValueError("private benchmark is not bound to the current projection")
    if benchmark.get("gates") != FIXED_GATES:
        raise ValueError("private benchmark gates differ from the precommitted contract")
    cases = benchmark.get("cases")
    query_cases = pack.get("cases")
    if not isinstance(cases, list) or not isinstance(query_cases, list) or len(cases) != 20:
        raise ValueError("private benchmark must contain exactly 20 cases")
    documents = {row["review_family_id"]: row for row in projection["documents"]}
    positive_counts = {family_id: 0 for family_id in documents}
    negative_counts = {family_id: 0 for family_id in documents}
    for query_case, case in zip(query_cases, cases, strict=True):
        if not isinstance(case, dict) or case.get("case_id") != query_case.get("case_id"):
            raise ValueError("private benchmark order differs from the query pack")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise TypeError("private benchmark case has no expected label")
        if query_case["case_type"] == "positive_family":
            if set(case) != {"case_id", "expected"} or set(expected) != {
                "review_family_id",
                "review_family_uuid",
            }:
                raise ValueError("positive benchmark label fields differ from contract")
            family_id = expected.get("review_family_id")
            document = documents.get(family_id)
            if (
                document is None
                or expected.get("review_family_uuid") != document["review_family_uuid"]
            ):
                raise ValueError("positive benchmark target differs from local projection")
            identities = {document["casting"], *document["aliases"]}
            normalized_query = extract_signals(query_case["query_text"]).normalized_title
            if normalized_query in {
                extract_signals(str(identity)).normalized_title for identity in identities
            }:
                raise ValueError("positive query must not equal a target identity")
            positive_counts[str(family_id)] += 1
        else:
            if set(case) != {"case_id", "expected"} or set(expected) != {
                "forbidden_review_family_id",
                "forbidden_review_family_uuid",
            }:
                raise ValueError("hard-negative benchmark label fields differ from contract")
            family_id = expected.get("forbidden_review_family_id")
            document = documents.get(family_id)
            if (
                document is None
                or expected.get("forbidden_review_family_uuid") != document["review_family_uuid"]
            ):
                raise ValueError("hard-negative target differs from local projection")
            negative_counts[str(family_id)] += 1
    if set(positive_counts.values()) != {3} or set(negative_counts.values()) != {1}:
        raise ValueError("benchmark must contain three positives and one hard negative per family")
    return cases


def _validate_raw(
    raw: dict[str, Any],
    pack: dict[str, Any],
    projection: dict[str, Any],
    catalog: HumanKnowledgeCatalog | None = None,
) -> None:
    expected_retriever = {
        "version": "human-knowledge-hybrid-v4",
        "dense_embedding": "hashing-v1",
        "dense_dimensions": DIMENSIONS,
        "character_score_floor": CHARACTER_SCORE_FLOOR,
        "character_rrf_weight": CHARACTER_RRF_WEIGHT,
    }
    expected_corpus = {
        "base_documents": 142,
        "local_documents": 5,
        "total_documents": 147,
        "review_family_documents": 47,
    }
    if (
        raw.get("schema_version") != RAW_SCHEMA_VERSION
        or raw.get("evaluation_version") != EVALUATION_VERSION
        or raw.get("projection_sha256") != projection.get("projection_sha256")
        or raw.get("candidate_limit") != CANDIDATE_LIMIT
        or raw.get("retriever") != expected_retriever
        or raw.get("corpus") != expected_corpus
    ):
        raise ValueError("private raw-result metadata differs from the frozen evaluation")
    rows = raw.get("rows")
    cases = pack.get("cases")
    known_documents = (
        {str(document.knowledge_uuid): document for document in catalog.documents}
        if catalog is not None
        else None
    )
    if not isinstance(rows, list) or not isinstance(cases, list) or len(rows) != len(cases):
        raise ValueError("private raw results do not cover the frozen query pack")
    for row, case in zip(rows, cases, strict=True):
        if not isinstance(row, dict) or set(row) != {
            "case_id",
            "case_type",
            "query_text",
            "candidates",
            "work",
            "error",
        }:
            raise ValueError("private raw-result case fields differ from contract")
        if any(row[field] != case[field] for field in ("case_id", "case_type", "query_text")):
            raise ValueError("private raw-result case differs from the frozen query")
        candidates = row["candidates"]
        if not isinstance(candidates, list) or len(candidates) > CANDIDATE_LIMIT:
            raise TypeError("private raw-result candidate list is invalid")
        if row["error"] is None:
            if not isinstance(row["work"], dict):
                raise TypeError("successful raw-result case must contain work counters")
        elif (
            candidates
            or row["work"] is not None
            or not isinstance(row["error"], dict)
            or set(row["error"]) != {"type", "message"}
            or not all(isinstance(value, str) for value in row["error"].values())
        ):
            raise ValueError("failed raw-result case contains partial or invalid evidence")
        seen: set[str] = set()
        for rank, candidate in enumerate(candidates, 1):
            if not isinstance(candidate, dict) or set(candidate) != {
                "knowledge_id",
                "knowledge_uuid",
                "knowledge_type",
                "rrf_rank",
            }:
                raise ValueError("private raw-result candidate fields differ from contract")
            if (
                not all(
                    isinstance(candidate[field], str) and candidate[field]
                    for field in ("knowledge_id", "knowledge_uuid", "knowledge_type")
                )
                or candidate["rrf_rank"] != rank
                or candidate["knowledge_uuid"] in seen
            ):
                raise ValueError("private raw-result candidate identity or rank is invalid")
            if known_documents is not None:
                document = known_documents.get(candidate["knowledge_uuid"])
                if (
                    document is None
                    or document.knowledge_id != candidate["knowledge_id"]
                    or document.knowledge_type != candidate["knowledge_type"]
                ):
                    raise ValueError("private raw-result candidate differs from the shadow corpus")
            seen.add(candidate["knowledge_uuid"])


def score(raw: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    cases = benchmark["cases"]
    rows = raw.get("rows")
    if not isinstance(rows, list) or len(rows) != len(cases):
        raise ValueError("raw results do not cover the complete benchmark")
    positive_ranks: list[int | None] = []
    covered: set[str] = set()
    forbidden_hits = 0
    errors = 0
    case_results: list[dict[str, Any]] = []
    for row, case in zip(rows, cases, strict=True):
        if row.get("case_id") != case.get("case_id"):
            raise ValueError("raw result order differs from the benchmark")
        expected = case["expected"]
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            raise TypeError("raw result candidates are invalid")
        if row.get("error") is not None:
            errors += 1
        if row.get("case_type") == "positive_family":
            target_id = expected["review_family_id"]
            target_uuid = expected["review_family_uuid"]
            rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate.get("knowledge_type") == "review_family"
                    and candidate.get("knowledge_id") == target_id
                    and candidate.get("knowledge_uuid") == target_uuid
                ),
                None,
            )
            positive_ranks.append(rank)
            if rank is not None:
                covered.add(target_id)
            case_results.append({"case_id": row["case_id"], "target_rank": rank})
        elif row.get("case_type") == "hard_negative":
            forbidden_id = expected["forbidden_review_family_id"]
            hits = sum(candidate.get("knowledge_id") == forbidden_id for candidate in candidates)
            forbidden_hits += hits
            case_results.append({"case_id": row["case_id"], "forbidden_hits": hits})
        else:
            raise ValueError("raw result case type differs from the benchmark")
    if len(positive_ranks) != 15:
        raise ValueError("positive denominator differs from the frozen benchmark")
    metrics: dict[str, float | int] = {
        "positive_recall_at_5": sum(rank is not None for rank in positive_ranks) / 15,
        "positive_recall_at_1": sum(rank == 1 for rank in positive_ranks) / 15,
        "family_coverage_at_5": len(covered) / 5,
        "hard_negative_forbidden_hits": forbidden_hits,
        "retrieval_errors": errors,
    }
    gates: list[dict[str, Any]] = []
    for name, threshold in FIXED_GATES.items():
        actual = metrics[name]
        operator = "=" if name in {"hard_negative_forbidden_hits", "retrieval_errors"} else ">="
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
        "counts": {
            "positive_cases": 15,
            "hard_negative_cases": 5,
            "positive_hits_at_5": sum(rank is not None for rank in positive_ranks),
            "positive_hits_at_1": sum(rank == 1 for rank in positive_ranks),
            "covered_local_families": len(covered),
            "hard_negative_forbidden_hits": forbidden_hits,
            "retrieval_errors": errors,
        },
        "metrics": metrics,
        "gates": gates,
        "verdict": "PASS" if all(gate["passed"] for gate in gates) else "FAIL",
        "case_results": case_results,
    }


def _result(raw: dict[str, Any], benchmark: dict[str, Any], benchmark_sha: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "query_pack_sha256": raw["query_pack_sha256"],
        "benchmark_sha256": benchmark_sha,
        "projection_sha256": raw["projection_sha256"],
        "raw_results_sha256": _sha256_bytes(_stable_json(raw).encode()),
        "raw_published_before_label_scoring": True,
        "limitations": list(LIMITATIONS),
        **score(raw, benchmark),
    }


def _public_manifest(raw: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "status": "offline_shadow_evaluation_complete_not_runtime",
        "public_scope": "aggregate_counts_metrics_gates_hashes_and_configuration_only",
        "verdict": result["verdict"],
        "hashes": {
            "projection_sha256": result["projection_sha256"],
            "query_pack_sha256": result["query_pack_sha256"],
            "benchmark_sha256": result["benchmark_sha256"],
            "raw_results_sha256": result["raw_results_sha256"],
            "private_result_sha256": _sha256_bytes(_stable_json(result).encode()),
        },
        "corpus": raw["corpus"],
        "retriever": raw["retriever"],
        "counts": result["counts"],
        "metrics": result["metrics"],
        "gates": result["gates"],
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
            "# Local release review-family retrieval evaluation — public summary",
            "",
            f"Verdict: **{manifest['verdict']}** for the bounded offline shadow evaluation.",
            "",
            (
                f"- Shadow corpus: {manifest['corpus']['total_documents']} documents "
                f"({manifest['corpus']['local_documents']} local candidates)"
            ),
            (
                f"- Private cases: {counts['positive_cases']} positives and "
                f"{counts['hard_negative_cases']} hard negatives"
            ),
            f"- Positive Recall@5: {metrics['positive_recall_at_5']:.4f}",
            f"- Positive Recall@1: {metrics['positive_recall_at_1']:.4f}",
            f"- Local-family coverage@5: {metrics['family_coverage_at_5']:.4f}",
            f"- Hard-negative forbidden hits: {metrics['hard_negative_forbidden_hits']}",
            f"- Retrieval errors: {metrics['retrieval_errors']}",
            "",
            "Queries, expected labels, candidate IDs, ranks, and case results remain private.",
            "This result does not load the five documents into the API, establish release/color",
            "truth, or authorize canonical promotion.",
            "",
        ]
    )


def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def run(root: Path | None = None) -> tuple[dict[str, Any], str]:
    root = root or Path.cwd()
    private = _private_directory(root)
    public = _public_directory(root)
    raw_path = private / "raw-results.json"
    if raw_path.exists():
        return check(root), "unchanged"
    if public.exists() or (private / "result.json").exists():
        raise ValueError("partial evaluation outputs exist; refusing to retrieve")
    raw = collect(root)
    _write_new(raw_path, _stable_json(raw))
    projection = check_projection(root)
    pack = _load_object(private / "query-pack.json")
    benchmark_path = private / "benchmark.json"
    benchmark = _load_object(benchmark_path)
    _validate_benchmark(benchmark, pack, projection, raw["query_pack_sha256"])
    result = _result(raw, benchmark, _sha256_path(benchmark_path))
    _write_new(private / "result.json", _stable_json(result))
    manifest = _public_manifest(raw, result)
    public.mkdir()
    _write_new(public / "manifest.json", _stable_json(manifest))
    _write_new(public / "report.md", _render_report(manifest))
    return check(root), "created"


def check(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    private = _private_directory(root)
    public = _public_directory(root)
    projection = check_projection(root)
    query_path = private / "query-pack.json"
    benchmark_path = private / "benchmark.json"
    raw_path = private / "raw-results.json"
    pack = _load_object(query_path)
    _validate_query_pack(pack, projection)
    benchmark = _load_object(benchmark_path)
    _validate_benchmark(benchmark, pack, projection, _sha256_path(query_path))
    raw = _load_object(raw_path)
    if (
        raw.get("query_pack_sha256") != _sha256_path(query_path)
        or raw.get("projection_sha256") != projection["projection_sha256"]
    ):
        raise ValueError("private raw results differ from current frozen inputs")
    _validate_raw(raw, pack, projection, _shadow_catalog(root, projection))
    result = _load_object(private / "result.json")
    expected_result = _result(raw, benchmark, _sha256_path(benchmark_path))
    if result != expected_result:
        raise ValueError("private evaluation result differs from deterministic scoring")
    manifest = _load_object(public / "manifest.json")
    expected_manifest = _public_manifest(raw, result)
    if manifest != expected_manifest:
        raise ValueError("public evaluation manifest differs from private aggregate result")
    if (public / "report.md").read_text(encoding="utf-8") != _render_report(manifest):
        raise ValueError("public evaluation report differs from manifest")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate private local review-family candidates")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.check:
        result, operation = check(root), "valid"
    else:
        result, operation = run(root)
    print(
        json.dumps(
            {
                "operation": operation,
                "verdict": result["verdict"],
                "counts": result["counts"],
                "metrics": result["metrics"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
