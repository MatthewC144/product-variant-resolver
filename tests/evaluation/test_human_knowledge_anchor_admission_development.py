from pathlib import Path

import pytest

from product_variant_resolver import human_knowledge_anchor_admission_development as anchor

ROOT = Path(__file__).resolve().parents[2]


def candidate(rank: int, coverage: float):
    return {
        "knowledge_id": f"family-{rank}",
        "knowledge_uuid": f"00000000-0000-0000-0000-{rank:012d}",
        "source_rank": rank,
        "identity_token_coverage": coverage,
    }


def test_rank_one_anchor_is_admitted_even_with_zero_coverage():
    row = {"candidates": [candidate(1, 0), candidate(2, 0.7)]}
    admitted = anchor.admit_candidates(row, 0.75)
    assert [item["source_rank"] for item in admitted] == [1]


def test_secondary_candidate_requires_configured_coverage():
    row = {
        "candidates": [
            candidate(1, 0),
            candidate(2, 0.75),
            candidate(3, 0.749),
            candidate(4, 1),
        ]
    }
    admitted = anchor.admit_candidates(row, 0.75)
    assert [item["source_rank"] for item in admitted] == [1, 2, 4]


def test_admission_preserves_source_order_and_never_promotes_beyond_rank_five():
    row = {"candidates": [candidate(rank, 1) for rank in range(1, 8)]}
    admitted = anchor.admit_candidates(row, 0.75)
    assert [item["source_rank"] for item in admitted] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_secondary_threshold_must_be_bounded(threshold):
    with pytest.raises(ValueError, match="secondary threshold"):
        anchor.admit_candidates({"candidates": []}, threshold)


def test_protocol_freezes_upstream_and_eight_configurations():
    protocol = anchor.build_protocol(ROOT)
    assert protocol["upstream"]["query_count"] == 223
    assert protocol["upstream"]["retrieval_reused"] is True
    assert protocol["retrieval_executed"] is False
    assert protocol["private_local_artifacts_read"] is False
    assert len(protocol["configurations"]) == 8
    assert protocol["admission"]["rank_1"] == "always_admit_anchor"


def test_source_contract_has_no_private_local_artifact_path():
    source = (ROOT / anchor.SOURCE).read_text()
    assert "local-release-review-family-retrieval-evaluation-v1" not in source
    assert "local-release-casting-review-family-knowledge-v1" not in source


def test_selection_requires_gates_then_minimizes_forbidden_and_threshold(monkeypatch):
    monkeypatch.setattr(anchor, "_cases", lambda root: [])

    def fake_summary(cases, rows, threshold):
        forbidden = {0: 8, 1 / 3: 3, 0.4: 1, 0.5: 1}.get(threshold, 0)
        eligible = threshold <= 0.5
        counts = {
            **anchor.GATES,
            "existing_positive_hits_at_1": 168,
            "new_required_hits_at_1": 24,
            "new_forbidden_hit_cases_at_5": forbidden,
            "new_forbidden_candidates_at_5": forbidden,
            "source_top5_candidates": 10,
            "admitted_candidates": 5,
            "abstained_secondary_candidates": 5,
        }
        return {
            "counts": counts,
            "metrics": {},
            "gates": [],
            "eligible": eligible,
            "case_results": [],
        }

    monkeypatch.setattr(anchor, "summarize", fake_summary)
    upstream = {"raw": {"rows": []}}
    result = anchor.score(ROOT, upstream)
    assert result["winner"]["configuration_id"] == "secondary-040"
    assert result["winner"]["improves_over_baseline"] is True


def test_protocol_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    protocol = {
        "sources": {},
        "upstream": {"selection_sha256": "upstream"},
        "schema_version": "fixture",
    }
    monkeypatch.setattr(anchor, "build_protocol", lambda root: protocol)
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert anchor.freeze_protocol(tmp_path) == "created"
    before = {path.name: path.read_bytes() for path in (tmp_path / anchor.DATA_DIRECTORY).iterdir()}
    assert anchor.freeze_protocol(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes() for path in (tmp_path / anchor.DATA_DIRECTORY).iterdir()
    }


def test_protocol_freeze_rejects_partial_directory(tmp_path, monkeypatch):
    protocol = {"sources": {}, "upstream": {"selection_sha256": "upstream"}}
    monkeypatch.setattr(anchor, "build_protocol", lambda root: protocol)
    directory = tmp_path / anchor.DATA_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "protocol.json").write_text("{}")
    with pytest.raises(ValueError, match="partial or conflicting"):
        anchor.freeze_protocol(tmp_path)


def test_real_grid_selects_secondary_075_for_private_shadow_gate_only():
    anchor.validate_protocol(ROOT)
    report = anchor.check(ROOT)
    summaries = {item["configuration_id"]: item for item in report["summaries"]}
    winner = report["winner"]
    assert winner["configuration_id"] == "secondary-075"
    assert winner["secondary_minimum_identity_token_coverage"] == 0.75
    assert winner["improves_over_baseline"] is True
    assert winner["status"] == "qualified_for_new_private_shadow_evaluation_only"
    assert winner["counts"]["existing_positive_hits_at_5"] == 168
    assert winner["counts"]["new_required_hits_at_5"] == 24
    assert winner["counts"]["new_forbidden_hit_cases_at_5"] == 0
    assert summaries["secondary-100"]["eligible"] is False
    assert summaries["secondary-100"]["counts"]["existing_positive_hits_at_5"] == 167


def test_check_never_runs_upstream_retrieval(monkeypatch):
    from product_variant_resolver import human_knowledge_reranker_development as upstream

    monkeypatch.setattr(
        upstream,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval reran")),
    )
    assert anchor.check(ROOT)["status"] == "development_selection_complete_not_runtime"
