from pathlib import Path
from types import SimpleNamespace

from product_variant_resolver import human_knowledge_anchor_confidence_development as confidence

ROOT = Path(__file__).resolve().parents[2]


def candidate(rank=1, coverage=0.2, character=0.8):
    return {
        "knowledge_id": f"candidate-{rank}",
        "knowledge_uuid": f"00000000-0000-0000-0000-{rank:012d}",
        "knowledge_type": "review_family",
        "casting_id": None,
        "source_rank": rank,
        "source_rrf_score": 0.05,
        "sparse_rank": None,
        "sparse_score": None,
        "dense_rank": rank,
        "dense_score": 0.4,
        "character_rank": rank,
        "character_score": character,
        "matched_tokens": [],
        "identity_token_coverage": coverage,
    }


def test_anchor_confidence_uses_best_bounded_public_signal():
    assert confidence.anchor_confidence(candidate(coverage=0.2, character=0.8)) == 0.8
    assert confidence.anchor_confidence(candidate(coverage=0.9, character=0.7)) == 0.9
    assert confidence.anchor_confidence(candidate(coverage=0.2, character=1.0000000002)) == 1


def test_anchor_and_secondary_apply_distinct_frozen_gates():
    row = {
        "candidates": [
            candidate(1, coverage=0.2, character=0.6),
            candidate(2, coverage=0.74, character=1),
            candidate(3, coverage=0.75, character=0),
        ]
    }
    assert [item["source_rank"] for item in confidence.admit_candidates(row, 0.6)] == [1, 3]
    assert [item["source_rank"] for item in confidence.admit_candidates(row, 0.61)] == [3]


def test_pack_has_ten_public_positives_and_twelve_absent_identities():
    pack, manifest = confidence.build_pack(ROOT)
    assert pack["case_counts"] == {
        "valid_low_coverage_anchor": 10,
        "missing_identity_hard_negative": 12,
    }
    assert len(pack["cases"]) == 22
    assert manifest["case_counts"] == pack["case_counts"]
    assert pack["private_local_artifacts_read"] is False
    assert pack["retrieval_executed"] is False


def test_source_contract_has_no_private_local_artifact_path():
    source = (ROOT / confidence.SOURCE).read_text()
    assert "local-release-review-family-retrieval-evaluation-v1" not in source
    assert "local-release-review-family-anchor-admission-evaluation-v2" not in source
    assert "local-release-casting-review-family-knowledge-v1" not in source


def test_collection_retrieves_each_frozen_query_once(monkeypatch):
    pack, _ = confidence.build_pack(ROOT)
    monkeypatch.setattr(confidence, "validate_protocol", lambda root: {"base_retriever": {}})
    monkeypatch.setattr(confidence, "validate_pack", lambda root: pack)
    monkeypatch.setattr(confidence, "_catalog", lambda root: object())
    monkeypatch.setattr(confidence, "_sha", lambda path: "protocol")
    calls = []

    class FakeRetriever:
        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], SimpleNamespace(as_dict=dict)

    monkeypatch.setattr(confidence, "HumanKnowledgeIdentityRetriever", FakeRetriever)
    raw = confidence.collect(ROOT)
    assert len(calls) == len(raw["rows"]) == 22
    assert raw["retrieval_calls"] == 22
    assert all(limit == 5 for _, limit in calls)


def test_pack_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(
        confidence,
        "build_pack",
        lambda root: ({"schema_version": "fixture"}, {"schema_version": "manifest"}),
    )
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert confidence.freeze_pack(tmp_path) == "created"
    before = {
        path.name: path.read_bytes() for path in (tmp_path / confidence.PACK_DIRECTORY).iterdir()
    }
    assert confidence.freeze_pack(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes() for path in (tmp_path / confidence.PACK_DIRECTORY).iterdir()
    }


def test_protocol_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    protocol = {"sources": {}, "schema_version": "fixture"}
    monkeypatch.setattr(confidence, "build_protocol", lambda root: protocol)
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert confidence.freeze_protocol(tmp_path) == "created"
    before = {
        path.name: path.read_bytes()
        for path in (tmp_path / confidence.PROTOCOL_DIRECTORY).iterdir()
    }
    assert confidence.freeze_protocol(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes()
        for path in (tmp_path / confidence.PROTOCOL_DIRECTORY).iterdir()
    }


def test_frozen_pack_protocol_and_selection_are_reproducible():
    pack = confidence.validate_pack(ROOT)
    protocol = confidence.validate_protocol(ROOT)
    report = confidence.check(ROOT)

    assert len(pack["cases"]) == 22
    assert protocol["query_counts"] == {"existing_public": 223, "anchor_confidence": 22}
    assert report["raw"]["retrieval_calls"] == 22
    assert report["winner"] is None


def test_public_grid_proves_scalar_confidence_cannot_meet_both_gates():
    report = confidence.check(ROOT)
    by_id = {item["configuration_id"]: item for item in report["summaries"]}

    assert by_id["anchor-061"]["existing"]["counts"]["existing_positive_hits_at_5"] == 168
    assert by_id["anchor-061"]["anchor"]["counts"]["valid_low_coverage_anchor_hits"] == 10
    assert by_id["anchor-061"]["anchor"]["counts"]["missing_identity_nonempty"] == 10
    assert by_id["anchor-0625"]["existing"]["counts"]["existing_positive_hits_at_5"] == 167
    assert by_id["anchor-0625"]["anchor"]["counts"]["valid_low_coverage_anchor_hits"] == 9
    assert by_id["anchor-075"]["anchor"]["counts"]["missing_identity_nonempty"] == 4
    assert all(item["eligible"] is False for item in report["summaries"])
