from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from product_variant_resolver import human_knowledge_admission_development as admission
from product_variant_resolver.human_knowledge import ReviewFamilyKnowledgeDocument

ROOT = Path(__file__).resolve().parents[2]


def document(casting="Porsche 911 GT3", aliases=()):
    return ReviewFamilyKnowledgeDocument(
        UUID(int=1),
        "family-1",
        "Hot Wheels",
        casting,
        tuple(aliases),
        ("source-1",),
        "fixture",
    )


@pytest.mark.parametrize(
    "identity,query",
    [
        ("supra", "supra"),
        ("supra", "supera"),
        ("steel", "st"),
        ("90", "1990"),
        ("coupe", "coupeclip"),
    ],
)
def test_frozen_token_match_modes(identity, query):
    assert admission._token_matches(identity, query)


def test_identity_coverage_requires_distinctive_model_tokens():
    target = document()
    assert admission.identity_token_coverage("Porsche 911 GT3 loose", target) == 1
    assert admission.identity_token_coverage("Porsche 911 Carrera RS", target) == 2 / 3


def test_identity_coverage_accepts_alias_and_misspelling():
    target = document("Max Steel", ("Maximum Steel",))
    assert admission.identity_token_coverage("max stel loose", target) == 1
    assert admission.identity_token_coverage("maximum steel boxed", target) == 1


def test_protocol_freezes_five_configs_and_both_dev_denominators():
    protocol = admission.build_protocol(ROOT)
    assert protocol["query_counts"] == {
        "existing_development": 199,
        "false_positive_development": 24,
    }
    assert [item["minimum_identity_token_coverage"] for item in protocol["configurations"]] == [
        0.0,
        0.5,
        2 / 3,
        0.75,
        1.0,
    ]
    assert protocol["private_local_artifacts_read"] is False
    assert protocol["retrieval_executed"] is False


def test_source_contract_has_no_private_local_artifact_path():
    source = (ROOT / admission.SOURCE).read_text()
    assert "local-release-review-family-retrieval-evaluation-v1" not in source
    assert "local-release-casting-review-family-knowledge-v1" not in source


def test_collection_retrieves_each_of_223_queries_once(monkeypatch):
    protocol = admission.build_protocol(ROOT)
    cases = admission._cases(ROOT)
    monkeypatch.setattr(admission, "validate_protocol", lambda root: protocol)
    monkeypatch.setattr(admission, "_catalog", lambda root: object())
    monkeypatch.setattr(admission, "_cases", lambda root: cases)
    monkeypatch.setattr(admission, "_sha", lambda path: "protocol-sha")
    calls = []

    class FakeRetriever:
        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], SimpleNamespace(as_dict=dict)

    monkeypatch.setattr(admission, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    raw = admission.collect(ROOT)
    assert len(calls) == len(raw["rows"]) == 223
    assert raw["retrieval_calls"] == 223
    assert all(limit == 5 for _, limit in calls)


def test_selection_requires_all_gates_then_minimizes_forbidden(monkeypatch):
    monkeypatch.setattr(admission, "_cases", lambda root: [])

    def fake_summary(cases, rows, threshold):
        eligible = threshold in {0.5, 0.75, 1.0}
        forbidden = {0.5: 4, 0.75: 1, 1.0: 1}.get(threshold, 10)
        counts = {
            **admission.GATES,
            "existing_positive_hits_at_1": 168,
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

    monkeypatch.setattr(admission, "summarize", fake_summary)
    result = admission.score(ROOT, {"rows": []})
    assert result["winner"]["configuration_id"] == "coverage-075"
    assert result["winner"]["minimum_identity_token_coverage"] == 0.75


def test_protocol_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    protocol = {"sources": {}, "schema_version": "fixture"}
    monkeypatch.setattr(admission, "build_protocol", lambda root: protocol)
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert admission.freeze_protocol(tmp_path) == "created"
    before = {
        path.name: path.read_bytes() for path in (tmp_path / admission.DATA_DIRECTORY).iterdir()
    }
    assert admission.freeze_protocol(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes() for path in (tmp_path / admission.DATA_DIRECTORY).iterdir()
    }


def test_protocol_freeze_rejects_partial_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(admission, "build_protocol", lambda root: {"sources": {}})
    directory = tmp_path / admission.DATA_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "protocol.json").write_text("{}")
    with pytest.raises(ValueError, match="partial or conflicting"):
        admission.freeze_protocol(tmp_path)


def test_real_grid_preserves_failed_mitigation_tradeoff():
    admission.validate_protocol(ROOT)
    report = admission.check(ROOT)
    summaries = {item["configuration_id"]: item for item in report["summaries"]}
    assert report["winner"]["configuration_id"] == "baseline"
    assert summaries["baseline"]["counts"]["new_forbidden_hit_cases_at_5"] == 18
    assert summaries["coverage-050"]["counts"]["new_forbidden_hit_cases_at_5"] == 7
    assert summaries["coverage-050"]["counts"]["existing_positive_hits_at_5"] == 167
    assert summaries["coverage-075"]["counts"]["new_forbidden_hit_cases_at_5"] == 0
    assert summaries["coverage-075"]["counts"]["new_required_hits_at_5"] == 23
    assert all(not summaries[name]["eligible"] for name in summaries if name != "baseline")


def test_check_never_collects_or_retrieves(monkeypatch):
    monkeypatch.setattr(
        admission,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval reran")),
    )
    assert admission.check(ROOT)["status"] == "development_selection_complete_not_runtime"
