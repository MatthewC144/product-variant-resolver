import hashlib
from pathlib import Path
from uuid import UUID

import pytest

from product_variant_resolver.human_knowledge import ReviewFamilyKnowledgeDocument
from product_variant_resolver.human_knowledge_identity_contradiction_development import (
    IdentityEvidenceIndex,
)
from product_variant_resolver.human_knowledge_identity_envelope_development import (
    POLICIES,
    RAW_DIRECTORY,
    REPORT_DIRECTORY,
    SOURCE,
    IdentityEnvelopeIndex,
    _contains_expected_key,
    _decision,
    _policy_definitions,
    build_pack,
    build_protocol,
    check,
    envelope_alignment_evidence,
    freeze_protocol,
    historical_calibration,
    numeric_evidence,
    validate_calibration_failure,
)

ROOT = Path(__file__).resolve().parents[2]


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


@pytest.fixture
def index():
    return IdentityEnvelopeIndex(
        (
            document(1, "1988 Jeep Wagoneer"),
            document(2, "08 Tesla Roadster", ("Tesla Roadster",)),
            document(3, "Nissan Skyline GT-R R34"),
            document(4, "Nissan Skyline GT-R BNR34"),
            document(5, "BMW M4"),
            document(6, "Honda Civic EG"),
        )
    )


def test_anchor_index_uses_only_casting_and_approved_aliases(index):
    assert {form.identity_kind for form in index.forms} == {"casting", "alias"}
    assert {form.anchor for form in index.forms} == {
        "bmw",
        "honda",
        "jeep",
        "nissan",
        "tesla",
    }
    assert all("hot wheels" not in form.core for form in index.forms)


def test_envelope_drops_leading_context_and_is_candidate_independent(index):
    envelope = index.envelope("greetings from space Tesla Roadster loose car")
    before = envelope.as_dict()

    tesla = numeric_evidence(envelope, "08 Tesla Roadster")
    bmw = numeric_evidence(envelope, "BMW M4")

    assert envelope.status == "anchored"
    assert envelope.anchor == "tesla"
    assert envelope.text == "tesla roadster"
    assert envelope.as_dict() == before
    assert tesla.query_digit_runs == bmw.query_digit_runs == ()


def test_envelope_retains_adjacent_leading_identity_year(index):
    envelope = index.envelope("boxed 88 Jeep Wagoneer collector model")

    assert envelope.anchor == "jeep"
    assert envelope.anchor_atom_index == 1
    assert envelope.text == "88 jeep wagoneer"
    assert [atom.text for atom in envelope.atoms] == ["88", "jeep", "wagoneer"]


def test_year_suffix_equivalence_is_structural_and_auditable(index):
    envelope = index.envelope("88 Jeep Wagoneer")
    evidence = numeric_evidence(envelope, "1988 Jeep Wagoneer")

    assert evidence.relation == "year_suffix_equivalent"
    assert evidence.anchor_relation == "equal"
    assert evidence.shorthand_rule == "leading_year_suffix"
    assert evidence.compact_digit_guard == "pass"


@pytest.mark.parametrize(
    ("query", "candidate", "expected_query_frame", "expected_candidate_frame"),
    (
        ("Nissan Skyline GT-R R33", "Nissan Skyline GT-R R34", "r33", "r34"),
        ("Nissan Skyline GT-R R33", "Nissan Skyline GT-R BNR34", "r33", "bnr34"),
        ("BMW M2", "BMW M4", "m2", "m4"),
    ),
)
def test_conserved_model_digits_cannot_be_hidden(
    index, query, candidate, expected_query_frame, expected_candidate_frame
):
    envelope = index.envelope(query)
    evidence = numeric_evidence(envelope, candidate)

    assert evidence.relation == "conflict"
    assert evidence.compact_digit_guard == "fail"
    assert expected_query_frame in {frame.source_token for frame in evidence.query_frames}
    assert expected_candidate_frame in {frame.source_token for frame in evidence.candidate_frames}


def test_unknown_model_atom_remains_inside_envelope(index):
    envelope = index.envelope("loose Honda Prelude coupe model")

    assert envelope.anchor == "honda"
    assert envelope.text == "honda prelude coupe"
    assert "prelude" in [atom.text for atom in envelope.atoms]


def test_unanchored_query_uses_the_whole_identity_core(index):
    envelope = index.envelope("unlisted Aurora Phantom X9 collector model")

    assert envelope.status == "unanchored"
    assert envelope.anchor is None
    assert envelope.text == "unlisted aurora phantom x9"
    assert envelope.anchor_atom_index is None


def test_multiple_anchor_candidates_choose_the_best_corpus_wide_form(index):
    envelope = index.envelope("Honda note Nissan Skyline GT-R R33")

    assert envelope.anchor == "nissan"
    assert envelope.text == "nissan skyline gt r r33"


def test_t1_source_has_no_private_dependency_or_retrieval_artifact():
    source = ROOT / "src/product_variant_resolver/human_knowledge_identity_envelope_development.py"
    text = source.read_text(encoding="utf-8")

    assert "local-release-review-family-retrieval-evaluation-v1" not in text
    assert "local-release-review-family-anchor-admission-evaluation-v2" not in text
    assert "local-release-casting-review-family-knowledge-v1" not in text
    assert not (ROOT / "data/evaluation/human-knowledge-identity-envelope-development-v2").exists()


def _rank_1_candidate(coverage=1.0):
    return {"source_rank": 1, "identity_token_coverage": coverage}


def _evidence(**overrides):
    value = {
        "numeric_relation": "none",
        "compact_digit_guard": "pass",
        "anchor_relation": "equal",
        "query_model_residual": "none",
        "candidate_model_residual": "none",
        "form_completion": "complete",
        "alignment_strength": "exact",
    }
    value.update(overrides)
    return value


def test_five_ordered_policies_match_the_confirmed_design():
    assert POLICIES == (
        "reference-anchor",
        "envelope-numeric",
        "envelope-bilateral",
        "envelope-safe-form",
        "envelope-decision-list",
    )
    assert [item["configuration_id"] for item in _policy_definitions()] == list(POLICIES)


def test_numeric_policy_rejects_conflict_before_other_rules():
    admitted, reasons = _decision(
        _rank_1_candidate(),
        _evidence(numeric_relation="conflict", compact_digit_guard="fail"),
        "envelope-numeric",
    )

    assert admitted is False
    assert reasons == ["numeric_conflict"]


def test_bilateral_policy_rejects_two_sided_model_residual():
    admitted, reasons = _decision(
        _rank_1_candidate(),
        _evidence(query_model_residual="present", candidate_model_residual="present"),
        "envelope-bilateral",
    )

    assert admitted is False
    assert reasons == ["bilateral_model_residual"]


def test_safe_form_admits_structural_year_shorthand(index):
    envelope = index.envelope("88 Jeep Wagoneer")
    target = document(1, "1988 Jeep Wagoneer")
    evidence = envelope_alignment_evidence(
        envelope,
        target,
        IdentityEvidenceIndex((target,)),
    )
    admitted, reasons = _decision(_rank_1_candidate(), evidence, "envelope-safe-form")

    assert evidence["numeric_relation"] == "year_suffix_equivalent"
    assert evidence["alignment_strength"] == "shorthand"
    assert admitted is True
    assert reasons == ["complete_safe_form"]


def test_decision_list_rejects_ambiguous_partial_identity():
    admitted, reasons = _decision(
        _rank_1_candidate(),
        _evidence(
            form_completion="partial",
            alignment_strength="weak",
            candidate_model_residual="present",
        ),
        "envelope-decision-list",
    )

    assert admitted is False
    assert reasons == ["ambiguous_identity"]


@pytest.mark.parametrize(
    ("coverage", "admitted"),
    ((0.75, True), (0.749, False)),
)
def test_secondary_candidates_keep_the_frozen_coverage_gate(coverage, admitted):
    result, _ = _decision(
        {"source_rank": 2, "identity_token_coverage": coverage},
        _evidence(),
        "envelope-decision-list",
    )

    assert result is admitted


def test_historical_calibration_reuses_all_public_rows_without_retrieval(monkeypatch):
    def forbidden_retrieval(*args, **kwargs):
        raise AssertionError("historical calibration must not execute retrieval")

    monkeypatch.setattr(
        "product_variant_resolver.human_knowledge_identity.HumanKnowledgeIdentityRetriever.retrieve_with_work",
        forbidden_retrieval,
    )
    report = historical_calibration(ROOT)

    assert report["denominators"] == {
        "existing_public": 223,
        "anchor_confidence_v4": 22,
        "hic_v1": 24,
    }
    assert report["retrieval_calls_executed"] == 0
    assert [summary["configuration_id"] for summary in report["summaries"]] == list(POLICIES)
    assert all("eligible" in summary for summary in report["summaries"])


def test_protocol_freeze_refuses_when_no_non_reference_policy_survives(monkeypatch):
    monkeypatch.setattr(
        "product_variant_resolver.human_knowledge_identity_envelope_development.historical_calibration",
        lambda root: {
            "eligible_non_reference_configuration_ids": [],
        },
    )

    with pytest.raises(ValueError, match="no non-reference"):
        build_protocol(ROOT)


def test_pack_builder_requires_the_protocol_phase_first():
    with pytest.raises(ValueError):
        build_pack(ROOT)


def test_raw_label_guard_rejects_expected_fields_at_any_depth():
    assert _contains_expected_key({"rows": [{"expected": {"knowledge_id": "x"}}]}) is True
    assert _contains_expected_key({"rows": [{"query_text": "Honda Civic"}]}) is False


def test_installed_cli_is_declared_and_t3_creates_no_retrieval_artifacts():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    source = (
        ROOT / "src/product_variant_resolver/human_knowledge_identity_envelope_development.py"
    ).read_text(encoding="utf-8")

    assert "pvr-develop-human-knowledge-identity-envelope" in pyproject
    for phase in ("--freeze-protocol", "--freeze-pack", "--collect", "--score", "--check"):
        assert phase in source
    assert not (ROOT / "data/evaluation/human-knowledge-identity-envelope-development-v2").exists()


def test_t3_preserves_deterministic_fail_without_protocol_pack_or_raw():
    report = validate_calibration_failure(ROOT)
    repeated = freeze_protocol(ROOT)
    checked = check(ROOT)

    assert report["status"] == "historical_calibration_fail"
    assert report["eligible_non_reference_configuration_ids"] == []
    assert report["retrieval_calls_executed"] == 0
    assert repeated == "calibration_failed_unchanged"
    assert checked == report
    assert {path.name for path in (ROOT / REPORT_DIRECTORY).iterdir()} == {
        "historical-calibration.json",
        "historical-calibration.md",
        "historical-calibration-manifest.json",
    }
    assert not (
        ROOT / "data/evaluation/human-knowledge-identity-envelope-development-v2/protocol"
    ).exists()
    assert not (
        ROOT / "data/evaluation/human-knowledge-identity-envelope-development-v2/pack"
    ).exists()
    assert not (ROOT / RAW_DIRECTORY).exists()


def test_t3_locks_measured_failure_and_public_source_hash():
    report = validate_calibration_failure(ROOT)
    summaries = {item["configuration_id"]: item for item in report["summaries"]}

    assert (
        summaries["reference-anchor"]["anchor_v4_22"]["counts"]["missing_identity_nonempty"] == 11
    )
    assert summaries["reference-anchor"]["hic_v1_24"]["counts"]["absent_identity_nonempty"] == 10
    assert (
        summaries["envelope-bilateral"]["existing_223"]["counts"]["existing_positive_hits_at_5"]
        == 146
    )
    assert (
        summaries["envelope-bilateral"]["anchor_v4_22"]["counts"]["missing_identity_nonempty"] == 1
    )
    assert summaries["envelope-bilateral"]["hic_v1_24"]["counts"]["absent_identity_nonempty"] == 1
    assert report["sources"][SOURCE] == hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest()
