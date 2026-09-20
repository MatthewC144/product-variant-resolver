import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from product_variant_resolver import release_casting_review_evaluation as evaluation


def projection():
    documents = []
    for index in range(5):
        documents.append(
            {
                "knowledge_type": "review_family",
                "review_family_id": f"family-{index}",
                "review_family_uuid": f"00000000-0000-0000-0000-{index:012d}",
                "knowledge_version": "fixture",
                "brand": "Hot Wheels",
                "casting": f"Fixture Family {index}",
                "aliases": [f"Fixture Family {index}"],
                "source_record_ids": [f"source-{index}"],
                "identity_status": "owner_confirmed_variants_unreviewed",
            }
        )
    return {
        "projection_sha256": "projection-sha",
        "knowledge_version": "fixture-v1",
        "documents": documents,
    }


def query_pack():
    cases = []
    for index in range(5):
        for variation in range(3):
            cases.append(
                {
                    "case_id": f"positive-{index}-{variation}",
                    "case_type": "positive_family",
                    "query_text": f"loose fixture family {index} variation {variation}",
                }
            )
    for index in range(5):
        cases.append(
            {
                "case_id": f"negative-{index}",
                "case_type": "hard_negative",
                "query_text": f"unrelated nearby model {index}",
            }
        )
    return {
        "schema_version": evaluation.QUERY_SCHEMA_VERSION,
        "evaluation_version": evaluation.EVALUATION_VERSION,
        "projection_sha256": "projection-sha",
        "cases": cases,
    }


def benchmark():
    rows = []
    for index in range(5):
        for variation in range(3):
            rows.append(
                {
                    "case_id": f"positive-{index}-{variation}",
                    "expected": {
                        "review_family_id": f"family-{index}",
                        "review_family_uuid": f"00000000-0000-0000-0000-{index:012d}",
                    },
                }
            )
    for index in range(5):
        rows.append(
            {
                "case_id": f"negative-{index}",
                "expected": {
                    "forbidden_review_family_id": f"family-{index}",
                    "forbidden_review_family_uuid": f"00000000-0000-0000-0000-{index:012d}",
                },
            }
        )
    return {
        "schema_version": evaluation.BENCHMARK_SCHEMA_VERSION,
        "evaluation_version": evaluation.EVALUATION_VERSION,
        "projection_sha256": "projection-sha",
        "query_pack_sha256": "query-sha",
        "gates": evaluation.FIXED_GATES,
        "cases": rows,
    }


def perfect_raw():
    rows = []
    for query, label in zip(query_pack()["cases"], benchmark()["cases"], strict=True):
        candidates = []
        if query["case_type"] == "positive_family":
            expected = label["expected"]
            candidates = [
                {
                    "knowledge_type": "review_family",
                    "knowledge_id": expected["review_family_id"],
                    "knowledge_uuid": expected["review_family_uuid"],
                    "rrf_rank": 1,
                }
            ]
        rows.append(
            {
                **query,
                "candidates": candidates,
                "work": {},
                "error": None,
            }
        )
    return {"rows": rows}


def test_private_contract_has_three_nonexact_positives_and_one_negative_per_family():
    pack = query_pack()
    evaluation._validate_query_pack(pack, projection())
    evaluation._validate_benchmark(benchmark(), pack, projection(), "query-sha")


def test_private_contract_rejects_exact_positive_identity():
    pack = query_pack()
    pack["cases"][0]["query_text"] = "Fixture Family 0"
    with pytest.raises(ValueError, match="must not equal"):
        evaluation._validate_benchmark(benchmark(), pack, projection(), "query-sha")


def test_private_contract_rejects_changed_precommitted_gate():
    value = benchmark()
    value["gates"] = {**evaluation.FIXED_GATES, "positive_recall_at_1": 0.5}
    with pytest.raises(ValueError, match="gates differ"):
        evaluation._validate_benchmark(value, query_pack(), projection(), "query-sha")


def test_collection_never_opens_benchmark_and_executes_each_query_once(tmp_path, monkeypatch):
    private = tmp_path / "data/external/hot-wheels-wiki" / evaluation.PRIVATE_DIRECTORY_NAME
    private.mkdir(parents=True)
    (private / "query-pack.json").write_text(json.dumps(query_pack()))
    monkeypatch.setattr(evaluation, "check_projection", lambda root: projection())
    monkeypatch.setattr(evaluation, "_shadow_catalog", lambda root, value: object())
    original_load = evaluation._load_object

    def guarded_load(path: Path):
        if path.name == "benchmark.json":
            raise AssertionError("collection cannot read labels")
        return original_load(path)

    monkeypatch.setattr(evaluation, "_load_object", guarded_load)
    calls = []

    class FakeRetriever:
        version = "fake-retriever"

        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], SimpleNamespace(as_dict=dict)

    monkeypatch.setattr(evaluation, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    raw = evaluation.collect(tmp_path)
    assert len(calls) == len(raw["rows"]) == 20
    assert all(limit == 5 for _, limit in calls)
    assert all("expected" not in row for row in raw["rows"])


def test_collection_preserves_failure_without_retry(tmp_path, monkeypatch):
    private = tmp_path / "data/external/hot-wheels-wiki" / evaluation.PRIVATE_DIRECTORY_NAME
    private.mkdir(parents=True)
    (private / "query-pack.json").write_text(json.dumps(query_pack()))
    monkeypatch.setattr(evaluation, "check_projection", lambda root: projection())
    monkeypatch.setattr(evaluation, "_shadow_catalog", lambda root, value: object())
    calls = []

    class FailingRetriever:
        version = "fake-retriever"

        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append(signals.normalized_title)
            raise RuntimeError("fixture failure")

    monkeypatch.setattr(evaluation, "HumanKnowledgeIdentityRetriever", FailingRetriever)
    raw = evaluation.collect(tmp_path)
    assert len(calls) == 20
    assert all(row["error"]["type"] == "RuntimeError" for row in raw["rows"])


def test_perfect_score_passes_all_precommitted_gates():
    result = evaluation.score(perfect_raw(), benchmark())
    assert result["verdict"] == "PASS"
    assert result["metrics"] == {
        "positive_recall_at_5": 1.0,
        "positive_recall_at_1": 1.0,
        "family_coverage_at_5": 1.0,
        "hard_negative_forbidden_hits": 0,
        "retrieval_errors": 0,
    }
    assert all(gate["passed"] for gate in result["gates"])


def test_top_one_gate_has_fixed_denominator():
    raw = perfect_raw()
    for row in raw["rows"][:4]:
        row["candidates"].insert(0, {"knowledge_id": "other", "knowledge_type": "review_family"})
    result = evaluation.score(raw, benchmark())
    assert result["metrics"]["positive_recall_at_5"] == 1
    assert result["metrics"]["positive_recall_at_1"] == 11 / 15
    assert result["verdict"] == "FAIL"


def test_forbidden_local_family_hit_fails_hard_negative_gate():
    raw = perfect_raw()
    row = raw["rows"][-1]
    expected = benchmark()["cases"][-1]["expected"]
    row["candidates"] = [{"knowledge_id": expected["forbidden_review_family_id"]}]
    result = evaluation.score(raw, benchmark())
    assert result["metrics"]["hard_negative_forbidden_hits"] == 1
    assert result["verdict"] == "FAIL"


def test_retrieval_error_fails_even_when_target_is_returned():
    raw = perfect_raw()
    raw["rows"][0]["error"] = {"type": "FixtureError", "message": "failed"}
    result = evaluation.score(raw, benchmark())
    assert result["metrics"]["retrieval_errors"] == 1
    assert result["verdict"] == "FAIL"


def test_public_manifest_excludes_private_case_details():
    raw = {
        "query_pack_sha256": "query",
        "projection_sha256": "projection",
        "corpus": {"total_documents": 147, "local_documents": 5},
        "retriever": {"version": "fixture"},
    }
    result = {
        "verdict": "PASS",
        "projection_sha256": "projection",
        "query_pack_sha256": "query",
        "benchmark_sha256": "benchmark",
        "raw_results_sha256": "raw",
        "counts": {},
        "metrics": {},
        "gates": [],
        "limitations": [],
        "case_results": [{"case_id": "private"}],
    }
    public = evaluation._public_manifest(raw, result)
    serialized = json.dumps(public)
    assert "case_results" not in public
    assert '"case_id"' not in serialized
    assert public["downstream_effects"] == {
        "runtime_documents_added": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "api_changes": 0,
        "network_requests": 0,
    }


def test_existing_raw_result_never_retrieves_again(tmp_path, monkeypatch):
    private = tmp_path / "data/external/hot-wheels-wiki" / evaluation.PRIVATE_DIRECTORY_NAME
    private.mkdir(parents=True)
    (private / "raw-results.json").write_text("{}")
    monkeypatch.setattr(evaluation, "check", lambda root: {"verdict": "FAIL"})
    monkeypatch.setattr(
        evaluation,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval reran")),
    )
    result, operation = evaluation.run(tmp_path)
    assert result == {"verdict": "FAIL"}
    assert operation == "unchanged"


def test_partial_public_output_without_raw_fails_before_retrieval(tmp_path, monkeypatch):
    (tmp_path / "reports" / evaluation.PUBLIC_DIRECTORY_NAME).mkdir(parents=True)
    monkeypatch.setattr(
        evaluation,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval started")),
    )
    with pytest.raises(ValueError, match="partial evaluation"):
        evaluation.run(tmp_path)


def test_raw_validator_rejects_changed_candidate_rank():
    pack = query_pack()
    raw = perfect_raw()
    raw.update(
        {
            "schema_version": evaluation.RAW_SCHEMA_VERSION,
            "evaluation_version": evaluation.EVALUATION_VERSION,
            "projection_sha256": "projection-sha",
            "candidate_limit": 5,
            "retriever": {
                "version": "human-knowledge-hybrid-v4",
                "dense_embedding": "hashing-v1",
                "dense_dimensions": 192,
                "character_score_floor": 0.5,
                "character_rrf_weight": 1.0,
            },
            "corpus": {
                "base_documents": 142,
                "local_documents": 5,
                "total_documents": 147,
                "review_family_documents": 47,
            },
        }
    )
    raw["rows"][0]["candidates"][0]["rrf_rank"] = 2
    with pytest.raises(ValueError, match="identity or rank"):
        evaluation._validate_raw(raw, pack, projection())
