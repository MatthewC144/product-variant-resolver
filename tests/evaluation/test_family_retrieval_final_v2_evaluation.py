"""Fake retrieval only: no real final query is executed by regression tests."""
import shutil
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from product_variant_resolver import family_retrieval_final_v2_evaluation as evaluation
from product_variant_resolver.human_knowledge_identity import IdentityRetrievalWork


@pytest.fixture(scope="module")
def benchmark():
    return evaluation.labels.validate()


def empty_raw(benchmark):
    return {"schema_version": "pvr-family-retrieval-raw-v2",
        "query_pack_sha256": evaluation.labels.QUERY_SHA,
        "artifact_sha256": evaluation.labels.questions.ARTIFACT_SHA,
        "configuration": benchmark["winner"]["configuration"],
        "started_at": evaluation.now(), "completed_at": evaluation.now(),
        "candidate_k": 5, "warmup_count": 0,
        "runtime": {"python": "3.12.test", "system": "fixture", "machine": "fixture",
            "process_count": 1, "host_isolated": False,
            "measured_boundary": "extraction_excluded_retrieval_and_serialization_included"},
        "index": evaluation.HumanKnowledgeIdentityRetriever(evaluation.corpus(evaluation.ROOT),
            evaluation.HashingEmbedding(192), evaluation.HumanKnowledgeV4Config(.5, 1)).character_index_metadata,
        "rows": [{"case_id": case["case_id"], "query_text": case["query_text"], "candidates": [],
            "work": IdentityRetrievalWork().as_dict(), "error": None, "latency_ms": 1.0}
            for case in benchmark["cases"]]}


def perfect_score_rows(benchmark):
    raw = empty_raw(benchmark)
    for case, row in zip(benchmark["cases"], raw["rows"], strict=True):
        expected = case["expected"]
        if case["case_type"] == "positive_family":
            row["candidates"] = [{"knowledge_type": "review_family",
                "knowledge_id": expected["review_family_id"], "knowledge_uuid": expected["review_family_uuid"]}]
        elif case["case_type"] == "merge_control":
            row["candidates"] = [{"knowledge_type": "provisional_variant", "casting_id": expected["casting_id"],
                "knowledge_id": "fake-provisional", "knowledge_uuid": "fake-uuid"}]
    return raw


def test_collector_never_reads_approved_labels_and_calls_each_query_once(monkeypatch):
    calls = []
    class FakeRetriever:
        def __init__(self, *args):
            self.character_index_metadata = {}
        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], IdentityRetrievalWork()
    monkeypatch.setattr(evaluation, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        if "/approved/" in str(path) or "/reports/family-retrieval-" in str(path):
            raise AssertionError("collection must be final-label/result blind")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    raw = evaluation.collect()
    assert len(calls) == len(raw["rows"]) == 105
    assert all(limit == 5 for _, limit in calls) and raw["warmup_count"] == 0
    assert all("expected" not in row for row in raw["rows"])


def test_collector_preserves_exception_and_never_retries(monkeypatch):
    calls = []
    class FakeRetriever:
        def __init__(self, *args):
            self.character_index_metadata = {}
        def retrieve_with_work(self, signals, limit):
            calls.append(signals)
            raise RuntimeError("fake dependency failure")
    monkeypatch.setattr(evaluation, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    raw = evaluation.collect()
    assert len(calls) == 105
    assert all(row["error"]["type"] == "RuntimeError" and row["work"] is None for row in raw["rows"])


def test_fixed_gates_and_counts_perfect_artificial_rows(benchmark):
    result = evaluation.score(perfect_score_rows(benchmark), benchmark)
    assert result["verdict"] == "PASS" and len(result["gates"]) == 9
    assert result["raw_counts"]["positive_hits_at_5"] == 84
    assert result["raw_counts"]["merge_hits_at_5"] == 4
    assert result["metrics"]["mrr_at_5"] == 1
    assert result["failures"] == []


def test_family_coverage_uses_any_pair_hit_and42_groups_not84_queries(benchmark):
    raw = perfect_score_rows(benchmark)
    for case, row in zip(benchmark["cases"], raw["rows"], strict=True):
        if case["challenge_style"] == "lexical_variation":
            row["candidates"] = []
    result = evaluation.score(raw, benchmark)
    assert result["metrics"]["positive_recall_at_5"] == .5
    assert result["metrics"]["family_coverage_at_5"] == 1.0
    assert result["verdict"] == "FAIL" and len(result["failures"]) == 42


def test_mrr_top1_and_budget_misses_keep_denominators(benchmark):
    raw = perfect_score_rows(benchmark)
    rows = [row for case, row in zip(benchmark["cases"], raw["rows"], strict=True) if case["case_type"] == "positive_family"]
    rows[0]["candidates"].insert(0, {"knowledge_type": "review_family", "knowledge_id": "fake-wrong", "knowledge_uuid": "fake-uuid"})
    rows[1]["candidates"] = []
    rows[1]["work"]["abstention_reason"] = "posting_limit"
    result = evaluation.score(raw, benchmark)
    assert result["raw_counts"]["positive_total"] == 84
    assert result["raw_counts"]["positive_hits_at_1"] == 82
    assert result["raw_counts"]["positive_hits_at_5"] == 83
    assert result["metrics"]["mrr_at_5"] == 82.5 / 84
    assert result["abstentions"] == {"posting_limit": 1}


@pytest.mark.parametrize("kind", ["hold_control", "merge_control", "unrelated_control", "retrieval_error"])
def test_safety_and_error_fail_even_with_high_positive_recall(benchmark, kind):
    raw = perfect_score_rows(benchmark)
    if kind == "retrieval_error":
        row = raw["rows"][0]
        row["error"] = {"type": "FakeError", "message": "failed"}
        row["work"] = None
    else:
        case, row = next((case, row) for case, row in zip(benchmark["cases"], raw["rows"], strict=True) if case["case_type"] == kind)
        row["candidates"].append({"knowledge_type": "review_family", "knowledge_id": case["expected"].get("forbidden_review_family_id", "fake-wrong"), "knowledge_uuid": "fake-uuid"})
    assert evaluation.score(raw, benchmark)["verdict"] == "FAIL"


def test_held_control_allows_other_valid_evidence(benchmark):
    raw = perfect_score_rows(benchmark)
    row = next(row for case, row in zip(benchmark["cases"], raw["rows"], strict=True) if case["case_type"] == "hold_control")
    row["candidates"] = [{"knowledge_type": "review_family", "knowledge_id": "fake-other", "knowledge_uuid": "fake-uuid"}]
    assert evaluation.score(raw, benchmark)["verdict"] == "PASS"


@pytest.mark.parametrize("mutation", ["partial", "order", "query"])
def test_changed_query_or_missing_rows_cannot_score(benchmark, mutation):
    raw = empty_raw(benchmark)
    if mutation == "partial":
        raw["rows"].pop()
    elif mutation == "order":
        raw["rows"].reverse()
    else:
        raw["rows"][0]["query_text"] += " rewritten"
    with pytest.raises(ValueError):
        evaluation.score(raw, benchmark)


@pytest.fixture
def workspace(tmp_path, monkeypatch, benchmark):
    for name in evaluation.hashes(evaluation.ROOT):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(evaluation.ROOT / name, path)
    monkeypatch.setattr(evaluation, "preflight", lambda root: "fake-commit")
    monkeypatch.setattr(evaluation, "collect", lambda root: empty_raw(benchmark))
    def validate(root):
        # Integrity preflight is separate; actual labels cannot be parsed until raw outputs exist.
        assert (root / evaluation.DIRECTORY / "raw-results.json").exists()
        return benchmark
    monkeypatch.setattr(evaluation.labels, "validate", validate)
    def fake_git(root, *args):
        if args[0] == "merge-base":
            return CompletedProcess([], 0, "", "")
        name = args[-1].split(":", 1)[1]
        return CompletedProcess([], 0, (root / name).read_text(), "")
    monkeypatch.setattr(evaluation.labels.questions, "git", fake_git)
    return tmp_path


def test_raw_before_label_access_one_shot_and_pure_check(workspace, monkeypatch):
    evaluation.run(workspace)
    def forbidden(root):
        raise AssertionError("no final rerun/check retrieval")
    monkeypatch.setattr(evaluation, "collect", forbidden)
    report = evaluation.check(workspace)
    assert report["verdict"] == "FAIL" and report["raw_published_before_label_scoring"] is True
    paths = list((workspace / evaluation.DIRECTORY).iterdir())
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
    with pytest.raises(ValueError, match="already reserved"):
        evaluation.run(workspace)
    assert before == [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]


def test_interrupted_collection_keeps_reservation_and_blocks_retry(workspace, monkeypatch):
    def failure(root):
        raise RuntimeError("fake interruption")
    monkeypatch.setattr(evaluation, "collect", failure)
    with pytest.raises(RuntimeError):
        evaluation.run(workspace)
    assert (workspace / evaluation.DIRECTORY / "run-start.json").exists()
    with pytest.raises(ValueError, match="already reserved"):
        evaluation.run(workspace)


@pytest.mark.parametrize("mutation", ["metric", "gate", "verdict", "sample", "rank", "work", "source", "markdown", "time", "runtime", "index"])
def test_report_or_raw_tampering_rejects_without_retrieval(workspace, mutation):
    evaluation.run(workspace)
    directory = workspace / evaluation.DIRECTORY
    if mutation == "markdown":
        (directory / "evaluation.md").write_text("changed")
    elif mutation == "source":
        path = workspace / evaluation.SOURCES[0]
        path.write_text(path.read_text() + "# changed\n")
    else:
        name = "raw-results.json" if mutation in {"sample", "rank", "work", "runtime", "index"} else "evaluation.json"
        path = directory / name
        doc = evaluation.load_object(path)
        if mutation == "metric":
            doc["metrics"]["positive_recall_at_5"] = 1
        elif mutation == "gate":
            doc["gates"][0]["passed"] = True
        elif mutation == "verdict":
            doc["verdict"] = "PASS"
        elif mutation == "sample":
            doc["rows"][0]["latency_ms"] = -1
        elif mutation == "rank":
            doc["rows"][0]["candidates"] = [{"knowledge_uuid": "fake-unknown"}]
        elif mutation == "work":
            doc["rows"][0]["work"]["dense_union"] = 100
        elif mutation == "runtime":
            doc["runtime"]["host_isolated"] = True
        elif mutation == "index":
            doc["index"]["form_count"] = 999
        else:
            doc["scored_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(evaluation.labels.questions.json_text(doc))
    with pytest.raises((ValueError, KeyError)):
        evaluation.check(workspace)


@pytest.mark.parametrize("kind", ["benchmark", "source"])
def test_preflight_rejects_before_run_reservation(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(evaluation, "preflight", evaluation.preflight)
    if kind == "benchmark":
        monkeypatch.setattr(evaluation.subprocess, "run", lambda *args, **kwargs: CompletedProcess([], 1, "", "invalid benchmark"))
    else:
        monkeypatch.setattr(evaluation.subprocess, "run", lambda *args, **kwargs: CompletedProcess([], 0, "", ""))
        for name in evaluation.SOURCES:
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(evaluation.ROOT / name, path)
    with pytest.raises(ValueError):
        evaluation.run(tmp_path)
    assert not (tmp_path / evaluation.DIRECTORY).exists()
