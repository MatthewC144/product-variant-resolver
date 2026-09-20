import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from product_variant_resolver import human_knowledge_false_positive_development as development

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pack_and_manifest():
    return development.build_pack(ROOT)


def test_pack_contains_24_distinct_development_only_pairs(pack_and_manifest):
    pack, manifest = pack_and_manifest
    assert pack["case_count"] == len(pack["cases"]) == 24
    assert pack["split"] == "dev"
    assert pack["authorship"] == {
        "method": "manual_related_identity_pairs_before_pack_baseline",
        "retriever_output_viewed_for_this_pack": False,
        "private_local_evaluation_loaded": False,
        "eligible_for_final_accuracy": False,
        "eligible_for_development": True,
    }
    assert manifest["retrieval_executed"] is False
    assert manifest["private_local_artifacts_read"] is False
    assert len({case["case_id"] for case in pack["cases"]}) == 24
    assert len({case["query_text"] for case in pack["cases"]}) == 24


def test_each_pair_is_nonexact_distinct_and_shares_identity_core(pack_and_manifest):
    pack, _ = pack_and_manifest
    for case in pack["cases"]:
        assert case["case_type"] == "required_plus_forbidden"
        assert case["shared_identity_core_tokens"]
        assert (
            case["expected"]["required"]["knowledge_id"]
            != case["expected"]["forbidden"]["knowledge_id"]
        )
        assert (
            case["expected"]["required"]["knowledge_uuid"]
            != case["expected"]["forbidden"]["knowledge_uuid"]
        )


def test_pack_manifest_binds_current_public_sources(pack_and_manifest):
    pack, manifest = pack_and_manifest
    assert manifest["source_sha256"] == development._sources(ROOT)
    assert (
        manifest["pack_sha256"]
        == development.hashlib.sha256(development._json(pack).encode()).hexdigest()
    )
    assert set(manifest["source_sha256"]) == {*development.INPUTS, development.SOURCE}


def test_module_has_no_private_local_evaluation_path_reference():
    source = (ROOT / development.SOURCE).read_text()
    assert "local-release-review-family-retrieval-evaluation-v1" not in source
    assert "local-release-casting-review-family-knowledge-v1" not in source


def test_collector_calls_each_dev_query_once_and_never_reads_expected_output(
    pack_and_manifest, monkeypatch
):
    pack, _ = pack_and_manifest
    monkeypatch.setattr(development, "validate_pack", lambda root: pack)
    monkeypatch.setattr(development, "_catalog", lambda root: object())
    calls = []

    class FakeRetriever:
        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], SimpleNamespace(as_dict=dict)

    monkeypatch.setattr(development, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    monkeypatch.setattr(development, "_sha", lambda path: "pack-sha")
    baseline = development.collect(ROOT)
    assert len(calls) == len(baseline["rows"]) == 24
    assert all(limit == 5 for _, limit in calls)
    assert all("expected" not in row for row in baseline["rows"])


def test_collector_preserves_each_exception_without_retry(pack_and_manifest, monkeypatch):
    pack, _ = pack_and_manifest
    monkeypatch.setattr(development, "validate_pack", lambda root: pack)
    monkeypatch.setattr(development, "_catalog", lambda root: object())
    calls = []

    class FailingRetriever:
        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append(signals.normalized_title)
            raise RuntimeError("fixture failure")

    monkeypatch.setattr(development, "HumanKnowledgeIdentityRetriever", FailingRetriever)
    monkeypatch.setattr(development, "_sha", lambda path: "pack-sha")
    baseline = development.collect(ROOT)
    assert len(calls) == 24
    assert all(row["error"]["type"] == "RuntimeError" for row in baseline["rows"])


def perfect_baseline(pack):
    rows = []
    for case in pack["cases"]:
        target = case["expected"]["required"]
        rows.append(
            {
                "case_id": case["case_id"],
                "query_text": case["query_text"],
                "candidates": [{**target, "rank": 1}],
                "work": {},
                "error": None,
            }
        )
    return {"rows": rows}


def test_score_reports_required_recall_and_forbidden_safety_separately(pack_and_manifest):
    pack, _ = pack_and_manifest
    result = development.score(pack, perfect_baseline(pack))
    assert result["counts"] == {
        "cases": 24,
        "required_hits_at_5": 24,
        "forbidden_hit_cases_at_5": 0,
        "forbidden_candidates_at_5": 0,
        "retrieval_errors": 0,
    }
    assert result["metrics"] == {
        "required_recall_at_5": 1,
        "forbidden_case_rate_at_5": 0,
        "safety_accuracy_at_5": 1,
    }


def test_score_keeps_forbidden_denominator_when_required_target_is_present(pack_and_manifest):
    pack, _ = pack_and_manifest
    baseline = perfect_baseline(pack)
    forbidden = pack["cases"][0]["expected"]["forbidden"]
    baseline["rows"][0]["candidates"].append({**forbidden, "rank": 2})
    result = development.score(pack, baseline)
    assert result["counts"]["required_hits_at_5"] == 24
    assert result["counts"]["forbidden_hit_cases_at_5"] == 1
    assert result["metrics"]["safety_accuracy_at_5"] == 23 / 24


def test_pack_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    pack = {"schema_version": "fixture", "cases": []}
    manifest = {"schema_version": "fixture-manifest"}
    monkeypatch.setattr(development, "build_pack", lambda root: (pack, manifest))
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert development.freeze_pack(tmp_path) == "created"
    before = {
        path.name: path.read_bytes() for path in (tmp_path / development.DATA_DIRECTORY).iterdir()
    }
    assert development.freeze_pack(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes() for path in (tmp_path / development.DATA_DIRECTORY).iterdir()
    }


def test_pack_freeze_rejects_partial_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(development, "build_pack", lambda root: ({}, {}))
    directory = tmp_path / development.DATA_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "development-pack.json").write_text(json.dumps({}))
    with pytest.raises(ValueError, match="partial or conflicting"):
        development.freeze_pack(tmp_path)


def test_real_frozen_pack_and_baseline_are_valid():
    assert development.validate_pack(ROOT)["case_count"] == 24
    report = development.check(ROOT)
    assert report["counts"] == {
        "cases": 24,
        "required_hits_at_5": 24,
        "forbidden_hit_cases_at_5": 18,
        "forbidden_candidates_at_5": 18,
        "retrieval_errors": 0,
    }
    assert report["metrics"] == {
        "required_recall_at_5": 1.0,
        "forbidden_case_rate_at_5": 0.75,
        "safety_accuracy_at_5": 0.25,
    }


def test_check_recomputes_evidence_without_retrieval(monkeypatch):
    monkeypatch.setattr(
        development,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval reran")),
    )
    assert development.check(ROOT)["status"] == "baseline_recorded_no_mitigation_selected"
