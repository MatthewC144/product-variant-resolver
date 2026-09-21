import json
from pathlib import Path
from uuid import UUID

import pytest

from product_variant_resolver import release_casting_review_anchor_evaluation as evaluation
from product_variant_resolver.human_knowledge import (
    HumanKnowledgeCatalog,
    ReviewFamilyKnowledgeDocument,
)

ROOT = Path(__file__).resolve().parents[2]


def document(index: int, casting: str):
    return ReviewFamilyKnowledgeDocument(
        UUID(f"00000000-0000-0000-0000-{index:012d}"),
        f"family-{index}",
        "Hot Wheels",
        casting,
        (),
        (f"source-{index}",),
        "fixture",
    )


def catalog():
    return HumanKnowledgeCatalog(
        "fixture", "fixture", [document(1, "Alpha One"), document(2, "Beta Two")]
    )


def row(query="collector alpha one", candidates=None, case_type="positive_family"):
    values = (
        [
            {
                "knowledge_id": "family-1",
                "knowledge_uuid": "00000000-0000-0000-0000-000000000001",
                "knowledge_type": "review_family",
                "rrf_rank": 1,
            }
        ]
        if candidates is None
        else candidates
    )
    return {
        "case_id": "case-1",
        "case_type": case_type,
        "query_text": query,
        "candidates": values,
        "work": {},
        "error": None,
    }


def test_rank_one_anchor_survives_low_coverage():
    value = row(query="unrelated wording")
    admitted, abstained = evaluation._admit_row(value, catalog())
    assert [item["rrf_rank"] for item in admitted] == [1]
    assert abstained == []


def test_secondary_candidate_requires_frozen_coverage():
    candidates = [
        row()["candidates"][0],
        {
            "knowledge_id": "family-2",
            "knowledge_uuid": "00000000-0000-0000-0000-000000000002",
            "knowledge_type": "review_family",
            "rrf_rank": 2,
        },
    ]
    admitted, abstained = evaluation._admit_row(
        row(query="collector alpha one", candidates=candidates), catalog()
    )
    assert [item["knowledge_id"] for item in admitted] == ["family-1"]
    assert [item["knowledge_id"] for item in abstained] == ["family-2"]


def test_candidate_not_in_catalog_fails_closed():
    value = row()
    value["candidates"][0]["knowledge_uuid"] = "00000000-0000-0000-0000-999999999999"
    with pytest.raises(ValueError, match="validated shadow catalog"):
        evaluation._admit_row(value, catalog())


def private_fixture():
    rows = []
    cases = []
    for family in range(1, 6):
        for variation in range(3):
            case_id = f"positive-{family}-{variation}"
            rows.append(
                {
                    **row(
                        query=f"collector family {family}",
                        candidates=[
                            {
                                "knowledge_id": f"family-{family}",
                                "knowledge_uuid": f"00000000-0000-0000-0000-{family:012d}",
                                "knowledge_type": "review_family",
                                "rrf_rank": 1,
                            }
                        ],
                    ),
                    "case_id": case_id,
                }
            )
            cases.append(
                {
                    "case_id": case_id,
                    "expected": {
                        "review_family_id": f"family-{family}",
                        "review_family_uuid": f"00000000-0000-0000-0000-{family:012d}",
                    },
                }
            )
    for family in range(1, 6):
        case_id = f"negative-{family}"
        rows.append(
            {**row(query="unrelated", candidates=[], case_type="hard_negative"), "case_id": case_id}
        )
        cases.append(
            {
                "case_id": case_id,
                "expected": {
                    "forbidden_review_family_id": f"family-{family}",
                    "forbidden_review_family_uuid": f"00000000-0000-0000-0000-{family:012d}",
                },
            }
        )
    documents = [document(index, f"Family {index}") for index in range(1, 6)]
    return {"rows": rows}, {"cases": cases}, HumanKnowledgeCatalog("fixture", "fixture", documents)


def test_perfect_private_policy_score_passes_all_gates():
    raw, benchmark, shadow = private_fixture()
    result = evaluation.score(raw, benchmark, shadow)
    assert result["verdict"] == "PASS"
    assert result["metrics"] == {
        "positive_recall_at_5": 1.0,
        "positive_recall_at_1": 1.0,
        "family_coverage_at_5": 1.0,
        "hard_negative_forbidden_hits": 0,
        "hard_negative_forbidden_rank1_hits": 0,
        "retrieval_errors": 0,
        "admission_errors": 0,
    }
    assert all(gate["passed"] for gate in result["gates"])


def test_forbidden_rank_one_anchor_fails_both_negative_gates():
    raw, benchmark, shadow = private_fixture()
    negative = raw["rows"][-1]
    negative["candidates"] = [
        {
            "knowledge_id": "family-5",
            "knowledge_uuid": "00000000-0000-0000-0000-000000000005",
            "knowledge_type": "review_family",
            "rrf_rank": 1,
        }
    ]
    result = evaluation.score(raw, benchmark, shadow)
    assert result["metrics"]["hard_negative_forbidden_hits"] == 1
    assert result["metrics"]["hard_negative_forbidden_rank1_hits"] == 1
    assert result["verdict"] == "FAIL"


def test_public_manifest_excludes_private_case_evidence():
    raw, benchmark, shadow = private_fixture()
    result = evaluation.score(raw, benchmark, shadow)
    result.update(
        protocol_sha256="protocol",
        upstream={
            "raw_results_sha256": "raw",
            "benchmark_sha256": "benchmark",
            "query_pack_sha256": "query",
            "projection_sha256": "projection",
        },
        limitations=[],
    )
    manifest = evaluation._public_manifest(result)
    serialized = evaluation._stable_json(manifest)
    assert "case_results" not in manifest
    assert '"case_id"' not in serialized
    assert manifest["downstream_effects"] == {
        "runtime_documents_added": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "api_changes": 0,
        "network_requests": 0,
    }


def test_protocol_freeze_is_create_once_and_byte_idempotent(tmp_path, monkeypatch):
    protocol = {
        "source_sha256": {},
        "upstream": {"raw_results_sha256": "raw"},
        "schema_version": "fixture",
    }
    monkeypatch.setattr(evaluation, "build_protocol", lambda root: protocol)
    (tmp_path / "data/evaluation").mkdir(parents=True)
    assert evaluation.freeze_protocol(tmp_path) == "created"
    before = {
        path.name: path.read_bytes()
        for path in (tmp_path / evaluation.PROTOCOL_DIRECTORY).iterdir()
    }
    assert evaluation.freeze_protocol(tmp_path) == "unchanged"
    assert before == {
        path.name: path.read_bytes()
        for path in (tmp_path / evaluation.PROTOCOL_DIRECTORY).iterdir()
    }


def test_protocol_freeze_rejects_partial_directory(tmp_path, monkeypatch):
    protocol = {"source_sha256": {}, "upstream": {"raw_results_sha256": "raw"}}
    monkeypatch.setattr(evaluation, "build_protocol", lambda root: protocol)
    directory = tmp_path / evaluation.PROTOCOL_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "protocol.json").write_text("{}")
    with pytest.raises(ValueError, match="partial or conflicting"):
        evaluation.freeze_protocol(tmp_path)


def test_public_artifact_preserves_private_fail_without_case_details():
    path = ROOT / "reports" / evaluation.PUBLIC_DIRECTORY_NAME / "manifest.json"
    manifest = json.loads(path.read_text())
    serialized = json.dumps(manifest)
    assert manifest["verdict"] == "FAIL"
    assert manifest["counts"]["positive_hits_at_5"] == 15
    assert manifest["counts"]["hard_negative_forbidden_hits"] == 2
    assert manifest["counts"]["hard_negative_forbidden_rank1_hits"] == 2
    assert manifest["new_retrieval_calls"] == 0
    assert "case_results" not in manifest
    assert '"case_id"' not in serialized


def test_real_check_never_retrieves_again(monkeypatch):
    private = ROOT / "data/external/hot-wheels-wiki" / evaluation.PRIVATE_DIRECTORY_NAME
    if not (private / "result.json").is_file():
        pytest.skip("owner-private evaluation artifact is not present")
    from product_variant_resolver import release_casting_review_evaluation as upstream

    monkeypatch.setattr(
        upstream,
        "collect",
        lambda root: (_ for _ in ()).throw(AssertionError("retrieval reran")),
    )
    result = evaluation.check(ROOT)
    assert result["verdict"] == "FAIL"
    assert result["new_retrieval_calls"] == 0
