from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from product_variant_resolver import human_knowledge_identity_contradiction_development as module
from product_variant_resolver.human_knowledge import ReviewFamilyKnowledgeDocument
from product_variant_resolver.human_knowledge_admission_development import _catalog
from product_variant_resolver.human_knowledge_anchor_confidence_development import (
    validate_pack as validate_anchor_pack,
)
from product_variant_resolver.identity import normalize_text

ROOT = Path(__file__).resolve().parents[2]


def test_pack_constructor_is_balanced_unique_and_labelled():
    pack, manifest = module.build_pack(ROOT)

    assert pack["case_counts"] == {
        "positive_preservation": 12,
        "absent_identity_contradiction": 12,
    }
    assert len(pack["cases"]) == len({case["case_id"] for case in pack["cases"]}) == 24
    assert manifest["case_counts"] == pack["case_counts"]
    assert pack["private_local_artifacts_read"] is False
    assert pack["retrieval_executed"] is False


def test_positives_exclude_v4_sources_cover_styles_and_span_documents():
    pack, _ = module.build_pack(ROOT)
    positives = [case for case in pack["cases"] if case["case_type"] == "positive_preservation"]
    anchor = validate_anchor_pack(ROOT)
    used = {
        case["source_case_id"] for case in anchor["cases"] if case["source_case_id"] is not None
    }

    assert all(case["source_case_id"] not in used for case in positives)
    assert len({case["expected"]["knowledge_id"] for case in positives}) == 12
    assert Counter(case["challenge_type"] for case in positives) == {
        "abbreviation_numeric": 3,
        "contextual_noise": 3,
        "single_edit": 3,
        "spacing_punctuation": 3,
    }


def test_negatives_are_new_absent_identities_with_declared_challenge_balance():
    pack, _ = module.build_pack(ROOT)
    negatives = [
        case for case in pack["cases"] if case["case_type"] == "absent_identity_contradiction"
    ]
    catalog_identities = {
        normalize_text(identity)
        for document in _catalog(ROOT).documents
        for identity in document.character_identity_texts
    }
    anchor = validate_anchor_pack(ROOT)
    prior_identities = {
        normalize_text(case["expected"]["absent_identity"])
        for case in anchor["cases"]
        if case["case_type"] == "missing_identity_hard_negative"
    }

    assert all(
        normalize_text(case["expected"]["absent_identity"])
        not in catalog_identities | prior_identities
        for case in negatives
    )
    assert Counter(case["challenge_type"] for case in negatives) == {
        "same_maker_model_substitution": 3,
        "same_stem_numeric_conflict": 3,
        "compact_or_punctuated_conflict": 3,
        "cross_maker_descriptor_overlap": 3,
    }


def document(number: int, casting: str, aliases=()):
    return ReviewFamilyKnowledgeDocument(
        UUID(int=number),
        f"family-{number}",
        "Hot Wheels",
        casting,
        aliases,
        (),
        "family_accepted_variants_unreviewed",
    )


def test_constructor_is_deterministic_without_retrieval_or_private_paths(monkeypatch):
    class ForbiddenRetriever:
        def __init__(self, *args, **kwargs):
            raise AssertionError("pack construction must not instantiate a retriever")

    monkeypatch.setattr(module, "HumanKnowledgeIdentityRetriever", ForbiddenRetriever)
    first = module.build_pack(ROOT)
    second = module.build_pack(ROOT)
    source = (ROOT / module.SOURCE).read_text(encoding="utf-8")

    assert first == second
    assert "local-release-review-family-retrieval-evaluation-v1" not in source
    assert "local-release-review-family-anchor-admission-evaluation-v2" not in source
    assert "local-release-casting-review-family-knowledge-v1" not in source


def test_atomization_retains_order_offsets_and_alphanumeric_frames():
    core, atoms = module.atomize("boxed Nissan Skyline GT-R R32 miniature")

    assert core == "nissan skyline gt r r32"
    assert [atom.text for atom in atoms] == ["nissan", "skyline", "gt", "r", "r", "32"]
    assert core[atoms[-1].start : atoms[-1].end] == "32"
    assert atoms[-1].source_token == "r32"


def test_alignment_detects_same_frame_numeric_conflict():
    target = document(1, "Nissan Skyline GT-R R34")
    index = module.IdentityEvidenceIndex((target,))

    evidence = module.alignment_evidence("Nissan Skyline GT-R R32 carded", target, index)

    assert evidence["numeric_conflict"] is True
    assert evidence["bilateral_residual"] > 0
    admitted, reasons = module._decision(
        {"source_rank": 1, "identity_token_coverage": 0.75}, evidence, "numeric", None
    )
    assert admitted is False
    assert reasons == ["numeric_model_conflict"]


def test_alignment_preserves_ocr_substitution_and_exact_alias_span():
    fiat = document(1, "Fiat 500e")
    tesla = document(2, "08 Tesla Roadster", ("Tesla Roadster",))
    index = module.IdentityEvidenceIndex((fiat, tesla))

    fiat_evidence = module.alignment_evidence("Fiat 5o0e diecast", fiat, index)
    tesla_evidence = module.alignment_evidence(
        "greetings from space Tesla Roadster loose car", tesla, index
    )

    assert any(
        alignment["mode"] == "ocr_numeric_substitution" for alignment in fiat_evidence["alignments"]
    )
    assert fiat_evidence["numeric_conflict"] is False
    assert fiat_evidence["bilateral_residual"] == 0
    assert tesla_evidence["candidate_identity_kind"] == "alias"
    assert tesla_evidence["query_span_text"] == "tesla roadster"
    assert tesla_evidence["bilateral_residual"] == 0


def test_bilateral_residual_requires_identity_evidence_on_both_sides():
    civic = document(1, "Honda Civic EG")
    index = module.IdentityEvidenceIndex((civic,))

    evidence = module.alignment_evidence("Honda Prelude coupe model", civic, index)

    assert evidence["query_residual"] > 0
    assert evidence["candidate_residual"] > 0
    assert evidence["bilateral_residual"] > 0
    admitted, reasons = module._decision(
        {"source_rank": 1, "identity_token_coverage": 1 / 3},
        evidence,
        "contradiction",
        0.5,
    )
    assert admitted is False
    assert reasons == ["bilateral_identity_residual"]


def test_secondary_candidate_keeps_frozen_coverage_gate():
    evidence = {"numeric_conflict": False, "bilateral_residual": 0.0}

    assert module._decision(
        {"source_rank": 2, "identity_token_coverage": 0.75}, evidence, "contradiction", 0.5
    ) == (True, ["no_contradiction"])
    assert module._decision(
        {"source_rank": 2, "identity_token_coverage": 0.749}, evidence, "contradiction", 0.5
    ) == (False, ["secondary_coverage_below_075"])


def test_protocol_declares_frozen_grid_and_label_blind_phases(monkeypatch):
    monkeypatch.setattr(module, "validate_pack", lambda root: {"cases": [{}] * 24})
    monkeypatch.setattr(module, "_source_hashes", lambda root: {})
    monkeypatch.setattr(module, "_sha", lambda path: "a" * 64)

    protocol = module.build_protocol(ROOT)

    assert [item["configuration_id"] for item in protocol["policies"]] == [
        "baseline-anchor",
        "numeric-only",
        "contradiction-050",
        "contradiction-075",
        "contradiction-100",
        "contradiction-125",
        "contradiction-150",
    ]
    assert protocol["secondary_minimum_identity_token_coverage"] == 0.75
    assert protocol["retrieval_executed"] is False


def test_collection_calls_each_query_once_and_never_copies_expected(monkeypatch):
    pack, _ = module.build_pack(ROOT)
    calls = []

    class FakeRetriever:
        def __init__(self, *args):
            pass

        def retrieve_with_work(self, signals, limit):
            calls.append((signals.normalized_title, limit))
            return [], SimpleNamespace(as_dict=dict)

    monkeypatch.setattr(module, "validate_protocol", lambda root: {"base_retriever": {}})
    monkeypatch.setattr(module, "validate_pack", lambda root: pack)
    monkeypatch.setattr(module, "_catalog", lambda root: object())
    monkeypatch.setattr(module, "_sha", lambda path: "a" * 64)
    monkeypatch.setattr(module, "HumanKnowledgeIdentityRetriever", FakeRetriever)

    raw = module.collect_payload(ROOT)

    assert len(calls) == raw["retrieval_calls"] == len(raw["rows"]) == 24
    assert all(limit == 5 for _, limit in calls)
    assert module._contains_expected_key(raw) is False


def test_freeze_directory_is_create_once_and_byte_idempotent(tmp_path):
    directory = tmp_path / "artifact"
    outputs = {"one.json": "{}\n", "two.json": "[]\n"}

    assert module._freeze_directory(directory, outputs, "fixture") == "created"
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert module._freeze_directory(directory, outputs, "fixture") == "unchanged"
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}


def test_alignment_is_ordered_one_to_one_with_valid_offsets():
    target = document(1, "80 El Camino")
    index = module.IdentityEvidenceIndex((target,))

    evidence = module.alignment_evidence("carded 80elcamino miniature", target, index)

    candidate_positions = []
    query_positions = []
    for alignment in evidence["alignments"]:
        candidate_positions.extend(range(alignment["candidate_start"], alignment["candidate_end"]))
        query_positions.extend(range(alignment["query_start"], alignment["query_end"]))
    assert candidate_positions == sorted(set(candidate_positions))
    assert query_positions == sorted(set(query_positions))
    assert (
        evidence["query_core"][evidence["query_span_start"] : evidence["query_span_end"]]
        == evidence["query_span_text"]
    )


def test_policy_preserves_source_order_and_emits_reason_codes():
    civic = document(1, "Honda Civic EG")
    accord = document(2, "Honda Accord")
    documents = {str(item.knowledge_uuid): item for item in (civic, accord)}
    index = module.IdentityEvidenceIndex((civic, accord))
    row = {
        "case_id": "fixture",
        "query_text": "Honda Prelude coupe",
        "candidates": [
            {
                "knowledge_id": civic.knowledge_id,
                "knowledge_uuid": str(civic.knowledge_uuid),
                "source_rank": 1,
                "identity_token_coverage": 1 / 3,
            },
            {
                "knowledge_id": accord.knowledge_id,
                "knowledge_uuid": str(accord.knowledge_uuid),
                "source_rank": 2,
                "identity_token_coverage": 0.75,
            },
        ],
    }

    filtered, evaluations, metrics = module.apply_policy(
        [row], documents, index, "contradiction-050"
    )

    assert [item["source_rank"] for item in filtered[0]["candidates"]] == [2]
    assert [item["decision"] for item in evaluations[0]["candidates"]] == [
        "abstain",
        "admit",
    ]
    assert evaluations[0]["candidates"][0]["reason_codes"] == ["bilateral_identity_residual"]
    assert metrics == {
        "source_candidates": 2,
        "admitted_candidates": 1,
        "abstained_candidates": 1,
        "contradiction_errors": 0,
    }


def test_raw_candidate_validator_rejects_nonfinite_or_wrong_rank():
    target = document(1, "Honda Civic EG")
    query = "Honda Civic EG"
    candidate = {
        "knowledge_id": target.knowledge_id,
        "knowledge_uuid": str(target.knowledge_uuid),
        "knowledge_type": target.knowledge_type,
        "casting_id": None,
        "source_rank": 1,
        "source_rrf_score": 0.03,
        "sparse_score": None,
        "dense_score": 0.4,
        "character_score": 1.0,
        "identity_token_coverage": 1.0,
    }

    module._validate_raw_candidate(candidate, target, query, 1)
    candidate["source_rrf_score"] = float("inf")
    with pytest.raises(ValueError, match="numeric contract"):
        module._validate_raw_candidate(candidate, target, query, 1)


def test_cli_contract_is_installed_with_five_explicit_phases():
    source = (ROOT / module.SOURCE).read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for phase in ("--freeze-pack", "--freeze-protocol", "--collect", "--score", "--check"):
        assert phase in source
    assert (
        "pvr-develop-human-knowledge-identity-contradiction = "
        '"product_variant_resolver.human_knowledge_identity_contradiction_development:main"'
        in pyproject
    )


def test_new_summary_requires_all_twelve_hits_and_zero_negative_output():
    pack, _ = module.build_pack(ROOT)
    original_rows = []
    filtered_rows = []
    for case in pack["cases"]:
        if case["case_type"] == "positive_preservation":
            candidate = {
                "knowledge_id": case["expected"]["knowledge_id"],
                "knowledge_uuid": case["expected"]["knowledge_uuid"],
            }
            candidates = [candidate]
        else:
            candidates = []
        row = {"case_id": case["case_id"], "candidates": candidates, "error": None}
        original_rows.append(row)
        filtered_rows.append({**row, "candidates": list(candidates)})

    summary = module._summarize_new(pack, original_rows, filtered_rows, 0)

    assert summary["eligible"] is True
    assert summary["counts"]["positive_preservation_hits"] == 12
    assert summary["counts"]["absent_identity_nonempty"] == 0
    filtered_rows[-1]["candidates"] = [{"knowledge_id": "wrong", "knowledge_uuid": "wrong"}]
    assert module._summarize_new(pack, original_rows, filtered_rows, 0)["eligible"] is False


def test_frozen_real_artifacts_recompute_to_null_winner_with_measured_counts():
    report = module.check(ROOT)
    measured = {
        summary["configuration_id"]: (
            summary["existing"]["counts"]["existing_positive_hits_at_5"],
            summary["anchor_v4"]["counts"]["valid_low_coverage_anchor_hits"],
            summary["anchor_v4"]["counts"]["missing_identity_nonempty"],
            summary["new"]["counts"]["positive_preservation_hits"],
            summary["new"]["counts"]["absent_identity_nonempty"],
            summary["new"]["counts"]["contradiction_errors"],
        )
        for summary in report["summaries"]
    }

    assert measured == {
        "baseline-anchor": (168, 10, 11, 12, 10, 0),
        "numeric-only": (167, 10, 10, 12, 10, 0),
        "contradiction-050": (164, 9, 1, 11, 1, 0),
        "contradiction-075": (165, 9, 1, 11, 2, 0),
        "contradiction-100": (167, 10, 6, 12, 5, 0),
        "contradiction-125": (167, 10, 6, 12, 5, 0),
        "contradiction-150": (167, 10, 7, 12, 5, 0),
    }
    assert all(summary["eligible"] is False for summary in report["summaries"])
    assert report["winner"] is None
    assert report["private_local_artifacts_read"] is False
