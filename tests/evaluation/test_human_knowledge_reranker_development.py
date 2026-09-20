from pathlib import Path
from types import SimpleNamespace

import pytest

from product_variant_resolver import human_knowledge_reranker_development as reranker

ROOT = Path(__file__).resolve().parents[2]


def raw_candidate(identifier: str, rank: int, score: float, coverage: float):
    return {
        "knowledge_id": identifier,
        "knowledge_uuid": f"00000000-0000-0000-0000-{rank:012d}",
        "knowledge_type": "review_family",
        "casting_id": None,
        "source_rank": rank,
        "source_rrf_score": score,
        "sparse_rank": None,
        "sparse_score": None,
        "dense_rank": rank,
        "dense_score": score,
        "character_rank": None,
        "character_score": None,
        "matched_tokens": [],
        "identity_token_coverage": coverage,
    }


def test_zero_weight_preserves_source_top_five():
    row = {
        "candidates": [
            raw_candidate(f"family-{rank}", rank, 1 / (60 + rank), 0) for rank in range(1, 7)
        ]
    }
    result = reranker.rerank_candidates(row, 0)
    assert [candidate["source_rank"] for candidate in result] == [1, 2, 3, 4, 5]


def test_relative_penalty_demotes_unsupported_candidate_without_mutating_pool():
    candidates = [
        raw_candidate("unsupported", 1, 0.05, 0),
        raw_candidate("supported", 2, 0.049, 1),
        raw_candidate("third", 3, 0.03, 1),
    ]
    row = {"candidates": candidates}
    result = reranker.rerank_candidates(row, 1)
    assert [candidate["knowledge_id"] for candidate in result][:2] == ["supported", "third"]
    assert [candidate["knowledge_id"] for candidate in row["candidates"]] == [
        "unsupported",
        "supported",
        "third",
    ]


@pytest.mark.parametrize("weight", [-1, float("inf"), float("nan")])
def test_penalty_weight_must_be_finite_and_nonnegative(weight):
    with pytest.raises(ValueError, match="penalty weight"):
        reranker.rerank_candidates({"candidates": []}, weight)


def test_protocol_freezes_candidate_pool_formula_and_public_denominators():
    protocol = reranker.build_protocol(ROOT)
    assert protocol["query_counts"] == {
        "existing_development": 199,
        "false_positive_development": 24,
    }
    assert protocol["candidate_pool_limit"] == 25
    assert protocol["output_limit"] == 5
    assert protocol["reranker"]["hard_deletion"] is False
    assert [item["unmatched_token_penalty_weight"] for item in protocol["configurations"]] == [
        0,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2,
    ]
    assert protocol["private_local_artifacts_read"] is False


def test_source_contract_has_no_private_local_artifact_path():
    source = (ROOT / reranker.SOURCE).read_text()
    assert "local-release-review-family-retrieval-evaluation-v1" not in source
    assert "local-release-casting-review-family-knowledge-v1" not in source


def test_collection_retrieves_each_query_once_at_25(monkeypatch):
    cases = reranker._cases(ROOT)
    monkeypatch.setattr(reranker, "validate_protocol", lambda root: {"base_retriever": {}})
    monkeypatch.setattr(reranker, "_catalog", lambda root: object())
    monkeypatch.setattr(reranker, "_cases", lambda root: cases)
    monkeypatch.setattr(reranker, "_sha", lambda path: "protocol-sha")
    calls = []

    class FakeRetriever:
        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], SimpleNamespace(as_dict=dict)

    monkeypatch.setattr(reranker, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    raw = reranker.collect(ROOT)
    assert len(calls) == len(raw["rows"]) == 223
    assert raw["retrieval_calls"] == 223
    assert all(limit == 25 for _, limit in calls)


def test_selection_uses_gates_then_safety_rank_quality_and_lowest_weight(monkeypatch):
    monkeypatch.setattr(reranker, "_cases", lambda root: [])

    def fake_summary(cases, rows, weight):
        forbidden = {0: 8, 0.05: 3, 0.1: 1, 0.25: 1}.get(weight, 0)
        eligible = weight in {0.05, 0.1, 0.25}
        rank1 = {0.05: 160, 0.1: 161, 0.25: 161}.get(weight, 150)
        counts = {
            **reranker.GATES,
            "existing_positive_hits_at_1": rank1,
            "new_required_hits_at_1": 24,
            "new_forbidden_hit_cases_at_5": forbidden,
            "new_forbidden_candidates_at_5": forbidden,
        }
        return {
            "counts": counts,
            "metrics": {},
            "gates": [],
            "eligible": eligible,
            "case_results": [],
        }

    monkeypatch.setattr(reranker, "summarize", fake_summary)
    result = reranker.score(ROOT, {"rows": []})
    assert result["winner"]["configuration_id"] == "penalty-010"
    assert result["winner"]["improves_over_baseline"] is True


def test_protocol_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    protocol = {"sources": {}, "schema_version": "fixture"}
    monkeypatch.setattr(reranker, "build_protocol", lambda root: protocol)
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert reranker.freeze_protocol(tmp_path) == "created"
    before = {
        path.name: path.read_bytes() for path in (tmp_path / reranker.DATA_DIRECTORY).iterdir()
    }
    assert reranker.freeze_protocol(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes() for path in (tmp_path / reranker.DATA_DIRECTORY).iterdir()
    }


def test_protocol_freeze_rejects_partial_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(reranker, "build_protocol", lambda root: {"sources": {}})
    directory = tmp_path / reranker.DATA_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "protocol.json").write_text("{}")
    with pytest.raises(ValueError, match="partial or conflicting"):
        reranker.freeze_protocol(tmp_path)


def test_real_grid_preserves_no_effect_result_and_sparse_pool_evidence():
    reranker.validate_protocol(ROOT)
    report = reranker.check(ROOT)
    summaries = report["summaries"]
    assert report["winner"]["configuration_id"] == "baseline"
    assert report["winner"]["improves_over_baseline"] is False
    assert all(summary["eligible"] for summary in summaries)
    assert {summary["counts"]["new_forbidden_hit_cases_at_5"] for summary in summaries} == {18}
    assert {summary["counts"]["existing_positive_hits_at_5"] for summary in summaries} == {168}
    assert sum(len(row["candidates"]) > 5 for row in report["raw"]["rows"]) == 5


def test_check_never_collects_or_retrieves(monkeypatch):
    monkeypatch.setattr(
        reranker,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval reran")),
    )
    assert reranker.check(ROOT)["status"] == "development_selection_complete_not_runtime"
