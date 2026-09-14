"""Frozen closure evidence validation; no real final retrieval or Docker startup in tests."""
from product_variant_resolver import family_retrieval_final_v2_evaluation as evaluation
from product_variant_resolver.human_knowledge_identity import HumanKnowledgeIdentityRetriever
from product_variant_resolver.human_knowledge_selection import load_object, sha


def test_docker_source_root_and_nonroot_evidence_contract():
    root = evaluation.ROOT
    text = (root / "Dockerfile").read_text()
    assert "PYTHONPATH=/app/src" in text
    assert "COPY src/ ./src/" in text and "COPY data/ ./data/" in text
    assert "USER pvr" in text and "chmod -R a+rX" in text
    assert "!scripts/build_human_knowledge_identity_protocol.py" in (root / ".dockerignore").read_text()


def test_real_final_report_reproduces_without_query_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("closure may only check stored ranks, never rerun final queries")
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve", forbidden)
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve_with_work", forbidden)
    report = evaluation.check()
    assert report["verdict"] == "PASS"
    assert len(report["case_results"]) == 105 and len(report["failures"]) == 4
    assert report["raw_counts"]["positive_hits_at_5"] == 80
    assert report["raw_counts"]["positive_hits_at_1"] == 77
    assert report["raw_counts"]["covered_families"] == 42


def test_runtime_report_image_sources_health_and_canonical_invariants():
    root = evaluation.ROOT
    report = load_object(root / "reports/runtime-validation/human-knowledge-v4-ibr-t5.json")
    assert report["verdict"] == "PASS" and report["uid"] > 0
    assert report["python"] == "3.12.14" and report["read_only_container"] is True
    assert report["new_final_queries_executed"] is False
    assert report["image_id"].startswith("sha256:")
    for name, value in report["source_sha256"].items():
        assert sha(root / name) == value
    for name, value in report["packaging_sha256"].items():
        assert sha(root / name) == value
    assert report["verifier_sha256"] == sha(root / "scripts/verify_human_knowledge_v4_runtime.py")
    outputs = report["outputs"]
    assert outputs["default"]["responses"] == outputs["v4"]["responses"]
    assert outputs["default"]["health_status"] == outputs["v4"]["health_status"] == 200
    for name in ("missing", "malformed", "stale"):
        assert outputs[name]["health_status"] == outputs[name]["resolve_status"] == 503


def test_runtime_failures_and_unmodified_final_evidence_are_preserved():
    root = evaluation.ROOT
    first = load_object(root / "reports/runtime-validation/human-knowledge-v4-ibr-t5-failed-01.json")
    second = load_object(root / "reports/runtime-validation/human-knowledge-v4-ibr-t5-failed-02.json")
    assert first["verdict"] == second["verdict"] == "FAIL"
    assert first["v4_http_health_status"] == 503 and first["missing_path"].startswith("/usr/local/lib/python3.12/data/")
    assert second["failure_scope"] == "runtime_verifier_fixture_not_product_or_final_quality"
    assert first["new_final_retrieval_rerun"] is second["new_final_retrieval_rerun"] is False
    assert sha(root / evaluation.DIRECTORY / "raw-results.json") == "61264a33bdb98e609c868cae59fbba8d067e13d47ff965919bd6a9adb4da4f32"
