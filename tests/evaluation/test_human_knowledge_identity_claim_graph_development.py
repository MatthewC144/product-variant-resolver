import hashlib
import json
from pathlib import Path
from uuid import UUID

import pytest

from product_variant_resolver import human_knowledge_identity_claim_graph_development as claim_graph
from product_variant_resolver.human_knowledge import ReviewFamilyKnowledgeDocument
from product_variant_resolver.human_knowledge_admission_development import _catalog
from product_variant_resolver.human_knowledge_identity_claim_graph_development import (
    CALIBRATION_JSON,
    CALIBRATION_MANIFEST,
    CALIBRATION_MARKDOWN,
    CONTEXT_TOKENS,
    DECLARATIONS_PATH,
    HISTORICAL_DENOMINATORS,
    NON_REFERENCE_POLICIES,
    POLICIES,
    PROTOCOL_DIRECTORY,
    RAW_DIRECTORY,
    REPORT_DIRECTORY,
    SOURCE,
    UPSTREAM_FIXED_HASHES,
    CandidatePolicyInput,
    IdentityClaimGrammar,
    _contains_forbidden_raw_key,
    _negative_holdout_cases,
    apply_policy,
    build_pack,
    candidate_claim_evidence,
    candidate_decision,
    collect,
    evaluate_candidates_in_source_order,
    freeze_protocol,
    policy_definitions,
    policy_selection_key,
    validate_candidate_evidence,
    verify_historical_inputs,
)

ROOT = Path(__file__).resolve().parents[2]


def document(number: int, casting: str, aliases: tuple[str, ...] = ()):
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
def grammar():
    return IdentityClaimGrammar(
        (
            document(1, "2020 Ram 1500 Rebel"),
            document(2, "1988 Jeep Wagoneer"),
            document(3, "Mercedes Benz 500 E"),
            document(4, "Fiat 500e"),
            document(5, "94 Audi Avant RS2"),
            document(6, "Deora III"),
            document(7, "Super Twin Mill"),
            document(8, "Morgan Super 3"),
            document(9, "Custom 53 Chevy"),
            document(10, "Bloc"),
            document(11, "Tesla Model S Plaid", ("Model S Plaid",)),
            document(12, "Nissan Skyline GT-R BNR34", ("Nissan Skyline GT-R",)),
            document(13, "Honda Prelude"),
            document(14, "Honda Civic EG"),
            document(15, "Bugatti Veyron"),
            document(16, "Honda Veyron"),
        )
    )


def _atoms(graph):
    return {atom.text: atom for atom in graph.atoms}


def test_grammar_uses_only_public_casting_and_approved_alias_text(grammar):
    assert {form.kind for form in grammar.forms} == {"casting", "alias"}
    assert "model s plaid" in {form.normalized for form in grammar.forms}
    assert all("hot wheels" not in form.normalized for form in grammar.forms)
    assert all("knowledge" not in field for form in grammar.forms for field in form.__slots__)


def test_grammar_requires_unique_public_document_identity():
    duplicate = document(1, "Another Casting")

    with pytest.raises(ValueError, match="unique knowledge IDs"):
        IdentityClaimGrammar((document(1, "Bloc"), duplicate))


def test_committed_142_document_public_corpus_builds_without_private_inputs():
    catalog = _catalog(ROOT)
    public_grammar = IdentityClaimGrammar(catalog.documents)
    year_and_model = public_grammar.graph("20 Ram 1500 Rebel")
    conflict_probe = public_grammar.graph("Nissan Skyline GT-R R33 carded model")

    assert len(catalog.documents) == 142
    assert len(public_grammar.forms) == 240
    assert year_and_model.hypothesis.public_form == "2020 ram 1500 rebel"
    assert [frame.digit_runs for frame in year_and_model.frames] == [("20",), ("1500",)]
    assert _atoms(conflict_probe)["r33"].role == "unresolved_discriminative"
    assert any(frame.digit_runs == ("33",) for frame in conflict_probe.frames)


def test_one_query_has_one_reproducible_graph_and_checksum(grammar):
    query = "warehouse find '88 Jeep Wagoneer unboxed collector sale"
    first = grammar.graph(query)
    second = grammar.graph(query)

    assert first == second
    assert first.as_dict() == second.as_dict()
    assert len(first.checksum) == 64
    assert first.hypothesis.public_form == "1988 jeep wagoneer"
    assert _atoms(first)["88"].role == "numeric_frame"
    assert _atoms(first)["88"].relation == "leading_year_suffix"
    assert _atoms(first)["jeep"].raw_source_token == "Jeep"
    assert _atoms(first)["jeep"].raw_start == query.index("Jeep")
    assert _atoms(first)["jeep"].start == first.normalized_query.index("jeep")
    assert {atom.text for atom in first.atoms if atom.role == "context"} == {
        "warehouse",
        "find",
        "unboxed",
        "collector",
        "sale",
    }


def test_context_vocabulary_yields_to_public_identity_participation(grammar):
    graph = grammar.graph("listing Tesla Model S Plaid display vehicle")
    atoms = _atoms(graph)

    assert "model" in CONTEXT_TOKENS
    assert atoms["model"].role == "identity_model"
    assert atoms["listing"].role == "context"
    assert atoms["display"].role == "context"
    assert atoms["vehicle"].role == "context"


def test_compact_segmentation_conserves_identity_and_digit_runs(grammar):
    compact = grammar.graph("2020ram1500rebel")
    prefixed = grammar.graph("carded smallbloc miniature")

    assert [atom.text for atom in compact.atoms] == ["2020", "ram", "1500", "rebel"]
    assert all(atom.relation == "compact_exact" for atom in compact.atoms)
    assert [(frame.kind, frame.digit_runs) for frame in compact.frames] == [
        ("leading_year", ("2020",)),
        ("compact_model", ("1500",)),
    ]
    assert [(atom.text, atom.role) for atom in prefixed.atoms] == [
        ("carded", "context"),
        ("small", "context"),
        ("bloc", "identity_anchor"),
        ("miniature", "context"),
    ]


@pytest.mark.parametrize(
    ("query", "public_form", "query_atom", "relation"),
    (
        ("de iii", "deora iii", "de", "unique_prefix_abbreviation"),
        ("su twin mill", "super twin mill", "su", "unique_prefix_abbreviation"),
        ("suer twin mill", "super twin mill", "suer", "unique_alpha_edit_1"),
        ("moran super 3", "morgan super 3", "moran", "unique_alpha_edit_1"),
        ("cusom 53 chevy", "custom 53 chevy", "cusom", "unique_alpha_edit_1"),
    ),
)
def test_bounded_abbreviation_and_edit_relations_are_public_and_auditable(
    grammar, query, public_form, query_atom, relation
):
    graph = grammar.graph(query)

    assert graph.hypothesis.public_form == public_form
    assert _atoms(graph)[query_atom].relation == relation
    assert _atoms(graph)[query_atom].public_form_atom is not None


def test_ambiguous_prefix_is_not_recorded_as_equivalent():
    ambiguous = IdentityClaimGrammar(
        (
            document(1, "Super Twin Mill"),
            document(2, "Subaru Twin Mill"),
        )
    ).graph("su twin mill")

    assert _atoms(ambiguous)["su"].role == "unresolved_discriminative"
    assert _atoms(ambiguous)["su"].relation is None
    assert all(
        relation.relation != "unique_prefix_abbreviation"
        for relation in ambiguous.hypothesis.relations
    )


@pytest.mark.parametrize(
    ("query", "public_form", "atom", "relation"),
    (
        ("20 Ram 1500 Rebel", "2020 ram 1500 rebel", "20", "leading_year_suffix"),
        ("Mercedes Benz 5o0 E", "mercedes benz 500 e", "5o0", "ocr_o_zero"),
        ("Fiat 50e", "fiat 500e", "50e", "ocr_repeated_digit_restore"),
        ("94x Audi Avant RS2", "94 audi avant rs2", "94x", "leading_year_uncertainty_x"),
    ),
)
def test_numeric_equivalences_are_bounded_and_recorded(grammar, query, public_form, atom, relation):
    graph = grammar.graph(query)

    assert graph.hypothesis.public_form == public_form
    assert _atoms(graph)[atom].relation == relation
    assert any(frame.equivalence_rule == relation for frame in graph.frames)


def test_local_frames_keep_year_and_model_number_separate(grammar):
    graph = grammar.graph("20 Ram 1500 Rebel")

    assert [
        (frame.kind, frame.digit_runs, frame.owner_before, frame.owner_after)
        for frame in graph.frames
    ] == [
        ("leading_year", ("20",), None, "ram"),
        ("standalone_model", ("1500",), "ram", "rebel"),
    ]
    assert sum(edge.relation == "belongs_to_frame" for edge in graph.edges) == 2
    assert sum(edge.relation == "same_identity_slot" for edge in graph.edges) == 2


def test_unequal_model_digits_remain_unresolved_and_conserved(grammar):
    graph = grammar.graph("Nissan Skyline GT-R R33 carded model")
    r33 = _atoms(graph)["r33"]

    assert graph.hypothesis.public_form == "nissan skyline gt r bnr34"
    assert r33.role == "unresolved_discriminative"
    assert r33.relation is None
    assert any(frame.digit_runs == ("33",) and frame.owner_before == "r" for frame in graph.frames)


def test_unanchored_query_keeps_unknown_claims_and_frames(grammar):
    graph = grammar.graph("Aurora Phantom X9")

    assert graph.status == "unanchored"
    assert graph.hypothesis.public_form is None
    assert all(atom.role == "unresolved_discriminative" for atom in graph.atoms)
    assert any(frame.digit_runs == ("9",) for frame in graph.frames)


def test_source_has_no_private_dependency():
    source = ROOT / SOURCE
    text = source.read_text(encoding="utf-8")

    assert "local-release-review-family" not in text
    assert "private_projection" not in text.casefold()
    assert "owner_only" not in text.casefold()
    assert "requests" not in text


def test_t2_policy_family_and_order_match_the_confirmed_design():
    assert POLICIES == (
        "reference-anchor",
        "claim-conflict-veto",
        "claim-bilateral",
        "claim-query-conservation",
        "claim-decision-list",
    )
    definitions = policy_definitions()

    assert tuple(value["configuration_id"] for value in definitions) == POLICIES
    assert definitions[0]["eligible_as_survivor"] is False
    assert all(value["eligible_as_survivor"] is True for value in definitions[1:])
    assert definitions[1]["ordered_rules"][0] == "all_rank_hard_conflict_veto"


def test_primary_casting_conflict_cannot_be_hidden_by_alias():
    wrong = document(
        101,
        "Nissan Skyline GT-R BNR34",
        ("Nissan Skyline GT-R",),
    )
    local_grammar = IdentityClaimGrammar((wrong, document(102, "Nissan Skyline GT-R R33")))
    graph = local_grammar.graph("Nissan Skyline GT-R R33 carded model")
    evidence = candidate_claim_evidence(graph, wrong, local_grammar, source_rank=4)

    assert evidence["candidate_identity_kind"] == "alias"
    assert evidence["candidate_identity"] == "nissan skyline gt r"
    assert evidence["numeric_relation"] == "query_only"
    assert evidence["primary_numeric_relation"] == "conflict"
    assert evidence["hard_conflict"] == "fail"
    assert evidence["primary_frame_comparisons"][0]["candidate_source_token"] == "bnr34"
    assert "knowledge_id" not in str(evidence)


@pytest.mark.parametrize("rank", (1, 4))
def test_all_non_reference_policies_veto_numeric_conflict_before_rank_or_coverage(rank):
    wrong = document(
        101,
        "Nissan Skyline GT-R BNR34",
        ("Nissan Skyline GT-R",),
    )
    local_grammar = IdentityClaimGrammar((wrong, document(102, "Nissan Skyline GT-R R33")))
    graph = local_grammar.graph("Nissan Skyline GT-R R33 carded model")
    evidence = candidate_claim_evidence(graph, wrong, local_grammar, source_rank=rank)

    for configuration in NON_REFERENCE_POLICIES:
        assert candidate_decision(
            evidence,
            configuration,
            identity_token_coverage=1.0,
        ) == ("abstain", ("hard_numeric_model_conflict",))
    assert (
        candidate_decision(
            evidence,
            "reference-anchor",
            identity_token_coverage=1.0,
        )[0]
        == "admit"
    )


@pytest.mark.parametrize(
    ("query", "candidate", "numeric_relation"),
    (
        ("20 Ram 1500 Rebel", "2020 Ram 1500 Rebel", "year_suffix"),
        ("Mercedes Benz 5o0 E", "Mercedes Benz 500 E", "ocr_equivalent"),
        ("Fiat 50e", "Fiat 500e", "ocr_equivalent"),
        ("94x Audi Avant RS2", "94 Audi Avant RS2", "year_suffix"),
    ),
)
def test_bounded_numeric_equivalence_passes_preflight_and_every_policy(
    grammar, query, candidate, numeric_relation
):
    graph = grammar.graph(query)
    evidence = candidate_claim_evidence(
        graph,
        document(200, candidate),
        grammar,
        source_rank=1,
    )

    assert evidence["hard_conflict"] == "pass"
    assert evidence["numeric_relation"] == numeric_relation
    assert evidence["form_completion"] == "complete"
    for configuration in POLICIES:
        assert (
            candidate_decision(
                evidence,
                configuration,
                identity_token_coverage=1.0,
            )[0]
            == "admit"
        )


def test_bounded_abbreviation_is_selected_as_auditable_candidate_evidence(grammar):
    graph = grammar.graph("su twin mill")
    evidence = candidate_claim_evidence(
        graph,
        document(201, "Super Twin Mill"),
        grammar,
        source_rank=1,
    )

    assert evidence["anchor_relation"] == "bounded_equivalent"
    assert evidence["query_claim_residual"] == "none"
    assert evidence["candidate_claim_residual"] == "none"
    assert evidence["query_graph"]["checksum"] == graph.checksum
    assert candidate_decision(
        evidence,
        "claim-decision-list",
        identity_token_coverage=1.0,
    ) == ("admit", ("complete_claim_form",))


def test_policy_layers_distinguish_bilateral_and_query_only_residuals(grammar):
    graph = grammar.graph("Honda Prelude coupe")
    wrong = candidate_claim_evidence(
        graph,
        document(202, "Honda Civic EG"),
        grammar,
        source_rank=1,
    )
    incomplete = candidate_claim_evidence(
        graph,
        document(203, "Honda Prelude"),
        grammar,
        source_rank=1,
    )

    assert wrong["query_claim_residual"] == "present"
    assert wrong["candidate_claim_residual"] == "present"
    assert (
        candidate_decision(
            wrong,
            "claim-conflict-veto",
            identity_token_coverage=1.0,
        )[0]
        == "admit"
    )
    assert candidate_decision(
        wrong,
        "claim-bilateral",
        identity_token_coverage=1.0,
    ) == ("abstain", ("bilateral_claim_residual",))

    assert incomplete["query_claim_residual"] == "present"
    assert incomplete["candidate_claim_residual"] == "none"
    assert (
        candidate_decision(
            incomplete,
            "claim-bilateral",
            identity_token_coverage=1.0,
        )[0]
        == "admit"
    )
    assert candidate_decision(
        incomplete,
        "claim-query-conservation",
        identity_token_coverage=1.0,
    ) == ("abstain", ("query_claim_not_conserved",))
    assert candidate_decision(
        incomplete,
        "claim-decision-list",
        identity_token_coverage=1.0,
    ) == ("abstain", ("ambiguous_claim_form",))


def test_anchor_mismatch_is_structural_for_stricter_policies(grammar):
    graph = grammar.graph("Bugatti Veyron")
    evidence = candidate_claim_evidence(
        graph,
        document(204, "Honda Veyron"),
        grammar,
        source_rank=1,
    )

    assert evidence["anchor_relation"] == "different"
    assert (
        candidate_decision(
            evidence,
            "claim-conflict-veto",
            identity_token_coverage=1.0,
        )[0]
        == "admit"
    )
    for configuration in (
        "claim-bilateral",
        "claim-query-conservation",
        "claim-decision-list",
    ):
        assert candidate_decision(
            evidence,
            configuration,
            identity_token_coverage=1.0,
        ) == ("abstain", ("anchor_mismatch",))


def test_secondary_coverage_runs_only_after_structural_rules(grammar):
    graph = grammar.graph("20 Ram 1500 Rebel")
    evidence = candidate_claim_evidence(
        graph,
        document(205, "2020 Ram 1500 Rebel"),
        grammar,
        source_rank=4,
    )

    assert (
        candidate_decision(
            evidence,
            "claim-bilateral",
            identity_token_coverage=0.749,
        )[-1][-1]
        == "secondary_coverage_below_075"
    )
    assert candidate_decision(
        evidence,
        "claim-bilateral",
        identity_token_coverage=0.75,
    ) == (
        "admit",
        ("structurally_compatible", "secondary_coverage_at_least_075"),
    )


def test_candidate_sequence_preserves_source_order(grammar):
    graph = grammar.graph("20 Ram 1500 Rebel")
    ram = document(206, "2020 Ram 1500 Rebel")
    candidates = (
        CandidatePolicyInput(ram, 1, 1.0),
        CandidatePolicyInput(ram, 4, 0.75),
    )
    results = evaluate_candidates_in_source_order(
        graph,
        candidates,
        grammar,
        "claim-bilateral",
    )

    assert [result["source_rank"] for result in results] == [1, 4]
    assert [result["decision"] for result in results] == ["admit", "admit"]
    with pytest.raises(ValueError, match="source-rank order"):
        evaluate_candidates_in_source_order(
            graph,
            tuple(reversed(candidates)),
            grammar,
            "claim-bilateral",
        )


def test_evidence_and_decision_validation_fail_closed(grammar):
    graph = grammar.graph("20 Ram 1500 Rebel")
    evidence = candidate_claim_evidence(
        graph,
        document(207, "2020 Ram 1500 Rebel"),
        grammar,
        source_rank=1,
    )
    evidence["query_graph"]["checksum"] = "tampered"

    with pytest.raises(ValueError, match="different query graph"):
        validate_candidate_evidence(evidence, graph.checksum)
    with pytest.raises(ValueError, match="finite"):
        candidate_decision(evidence, "claim-bilateral", identity_token_coverage=float("nan"))


def _calibration(survivors=()):
    return {
        "schema_version": claim_graph.CALIBRATION_SCHEMA,
        "version": claim_graph.VERSION,
        "status": "historical_calibration_pass" if survivors else "historical_calibration_fail",
        "denominators": HISTORICAL_DENOMINATORS,
        "retrieval_calls_executed": 0,
        "private_local_artifacts_read": False,
        "sources": {},
        "summaries": [],
        "eligible_non_reference_configuration_ids": list(survivors),
        "winner": None,
    }


def test_t3_verifies_all_public_inputs_and_five_frozen_upstream_hashes():
    hashes = verify_historical_inputs(ROOT)

    assert all(hashes[name] == expected for name, expected in UPSTREAM_FIXED_HASHES.items())
    assert hashes[SOURCE] == claim_graph._sha(ROOT / SOURCE)
    assert len(hashes) > len(UPSTREAM_FIXED_HASHES)


def test_offline_policy_application_preserves_rows_and_never_calls_retrieval(monkeypatch):
    wrong = document(101, "Nissan Skyline GT-R BNR34", ("Nissan Skyline GT-R",))
    local_grammar = IdentityClaimGrammar((wrong, document(102, "Nissan Skyline GT-R R33")))
    row = {
        "case_id": "offline-r33",
        "query_text": "Nissan Skyline GT-R R33 carded model",
        "error": None,
        "candidates": [
            {
                "knowledge_id": wrong.knowledge_id,
                "knowledge_uuid": str(wrong.knowledge_uuid),
                "source_rank": 1,
                "identity_token_coverage": 1.0,
            }
        ],
    }
    monkeypatch.setattr(
        claim_graph.HumanKnowledgeIdentityRetriever,
        "retrieve_with_work",
        lambda *args, **kwargs: pytest.fail("historical scoring must not retrieve"),
    )

    filtered, evaluations, metrics = apply_policy(
        [row],
        {str(wrong.knowledge_uuid): wrong},
        local_grammar,
        "claim-bilateral",
    )

    assert filtered[0]["case_id"] == row["case_id"]
    assert filtered[0]["candidates"] == []
    assert evaluations[0]["candidates"][0]["decision"] == "abstain"
    assert evaluations[0]["candidates"][0]["reason_codes"] == ["hard_numeric_model_conflict"]
    assert metrics["source_candidates"] == metrics["abstained_candidates"] == 1
    assert metrics["graph_errors"] == metrics["alignment_errors"] == 0


def test_historical_calibration_contract_uses_exact_denominators_and_all_gates(monkeypatch):
    def rows(prefix, count):
        return [
            {
                "case_id": f"{prefix}-{index}",
                "query_text": "Honda Prelude",
                "candidates": [],
                "error": None,
            }
            for index in range(count)
        ]

    existing_rows = rows("existing", 223)
    anchor_rows = rows("anchor", 22)
    hic_rows = rows("hic", 24)
    existing_cases = [
        {"case_id": row["case_id"], "dataset": "false_positive"} for row in existing_rows
    ]
    anchor_cases = [
        {
            "case_id": row["case_id"],
            "case_type": "valid_low_coverage_anchor"
            if index < 10
            else "missing_identity_hard_negative",
        }
        for index, row in enumerate(anchor_rows)
    ]
    hic_cases = [
        {
            "case_id": row["case_id"],
            "case_type": "positive_preservation" if index < 12 else "absent_identity_contradiction",
        }
        for index, row in enumerate(hic_rows)
    ]
    zero_metrics = {
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
        "non_exact_equivalence_operations": 0,
        "retrieval_errors": 0,
        "graph_errors": 0,
        "alignment_errors": 0,
        "decision_errors": 0,
    }
    monkeypatch.setattr(claim_graph, "verify_historical_inputs", lambda root: {SOURCE: "hash"})
    monkeypatch.setattr(
        claim_graph,
        "check_upstream",
        lambda root: {"raw": {"rows": existing_rows}},
    )
    monkeypatch.setattr(
        claim_graph,
        "check_anchor",
        lambda root: {"raw": {"rows": anchor_rows}},
    )
    monkeypatch.setattr(claim_graph, "validate_anchor_pack", lambda root: {"cases": anchor_cases})
    monkeypatch.setattr(claim_graph, "validate_hic_raw", lambda root: {"rows": hic_rows})
    monkeypatch.setattr(claim_graph, "validate_hic_pack", lambda root: {"cases": hic_cases})
    monkeypatch.setattr(
        claim_graph,
        "_catalog",
        lambda root: type("C", (), {"documents": (document(500, "Honda Prelude"),)})(),
    )
    monkeypatch.setattr(claim_graph, "_cases", lambda root: existing_cases)
    monkeypatch.setattr(
        claim_graph,
        "apply_policy",
        lambda source_rows, documents, grammar, configuration: (
            source_rows,
            [],
            dict(zero_metrics),
        ),
    )
    monkeypatch.setattr(
        claim_graph,
        "summarize_existing",
        lambda cases, filtered, threshold: {
            "counts": {
                "existing_positive_hits_at_5": 168,
                "merge_hits_at_5": 4,
                "existing_forbidden_candidates": 0,
                "unrelated_nonempty": 0,
                "new_required_hits_at_5": 24,
                "retrieval_errors": 0,
            }
        },
    )
    monkeypatch.setattr(
        claim_graph,
        "_score_anchor",
        lambda pack, raw, threshold: {
            "counts": {
                "valid_low_coverage_anchor_hits": 10,
                "missing_identity_nonempty": 0,
                "anchor_retrieval_errors": 0,
            }
        },
    )
    monkeypatch.setattr(
        claim_graph,
        "_summarize_hic",
        lambda pack, original, filtered, errors: {
            "counts": {
                "positive_preservation_hits": 12,
                "absent_identity_nonempty": 0,
                "retrieval_errors": 0,
            }
        },
    )
    monkeypatch.setattr(claim_graph, "_known_secondary_conflicts_abstained", lambda *args: 2)

    report = claim_graph.historical_calibration(Path("unused"))

    assert report["denominators"] == HISTORICAL_DENOMINATORS
    assert report["retrieval_calls_executed"] == 0
    assert [summary["configuration_id"] for summary in report["summaries"]] == list(POLICIES)
    assert all(len(summary["historical_gates"]) == 14 for summary in report["summaries"])
    assert report["eligible_non_reference_configuration_ids"] == list(NON_REFERENCE_POLICIES)


def test_policy_selection_key_uses_the_exact_frozen_order():
    base = {
        "negative_admitted_candidates": 0,
        "positive_abstained_candidates": 0,
        "non_exact_equivalence_operations": 0,
    }
    summaries = [
        {"configuration_id": policy, "selection_metrics": dict(base)}
        for policy in reversed(NON_REFERENCE_POLICIES)
    ]

    assert min(summaries, key=policy_selection_key)["configuration_id"] == ("claim-conflict-veto")
    summaries[-1]["selection_metrics"]["negative_admitted_candidates"] = 1
    assert min(summaries, key=policy_selection_key)["configuration_id"] == "claim-bilateral"


def test_failed_protocol_freeze_writes_only_deterministic_null_calibration(tmp_path, monkeypatch):
    report = _calibration()
    monkeypatch.setattr(claim_graph, "historical_calibration", lambda root: report)

    assert freeze_protocol(tmp_path) == "calibration_failed_created"
    assert freeze_protocol(tmp_path) == "calibration_failed_unchanged"
    report_directory = tmp_path / REPORT_DIRECTORY
    assert {path.name for path in report_directory.iterdir()} == {
        CALIBRATION_JSON,
        CALIBRATION_MANIFEST,
        CALIBRATION_MARKDOWN,
    }
    assert json.loads((report_directory / CALIBRATION_JSON).read_text()) == report
    assert not (tmp_path / PROTOCOL_DIRECTORY).exists()
    assert not (tmp_path / RAW_DIRECTORY).exists()


def test_successful_protocol_freeze_requires_a_survivor_and_freezes_both_phases(
    tmp_path, monkeypatch
):
    report = _calibration(("claim-bilateral",))
    protocol = {
        "schema_version": claim_graph.PROTOCOL_SCHEMA,
        "version": claim_graph.VERSION,
        "sources": {},
    }
    monkeypatch.setattr(claim_graph, "historical_calibration", lambda root: report)
    monkeypatch.setattr(
        claim_graph,
        "_build_protocol_from_calibration",
        lambda root, calibration: protocol,
    )

    assert freeze_protocol(tmp_path) == "created"
    assert freeze_protocol(tmp_path) == "unchanged"
    assert (tmp_path / REPORT_DIRECTORY / CALIBRATION_JSON).is_file()
    assert (tmp_path / PROTOCOL_DIRECTORY / "protocol.json").is_file()
    assert not (tmp_path / claim_graph.PACK_DIRECTORY).exists()


def test_pack_builder_fails_closed_before_protocol_phase(tmp_path, monkeypatch):
    monkeypatch.setattr(
        claim_graph,
        "historical_calibration",
        lambda root: _calibration(("claim-bilateral",)),
    )

    with pytest.raises(ValueError, match="deterministic artifact"):
        build_pack(tmp_path)


def test_negative_pack_contract_enforces_four_by_four_and_corpus_absence(tmp_path, monkeypatch):
    categories = (
        "numeric_model_conflict",
        "same_maker_model_substitution",
        "compact_digit_conflict",
        "context_overlap",
    )
    cases = [
        {
            "case_id": f"negative-{category}-{index}",
            "challenge_type": category,
            "query_text": f"Absent {category} Model {index}",
            "absent_identity": f"Absent {category} Model {index}",
        }
        for category in categories
        for index in range(4)
    ]
    path = tmp_path / DECLARATIONS_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": (
                    "pvr-human-knowledge-identity-claim-graph-negative-declarations-v3"
                ),
                "version": claim_graph.VERSION,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(claim_graph, "_catalog", lambda root: type("C", (), {"documents": ()})())
    monkeypatch.setattr(claim_graph, "validate_anchor_pack", lambda root: {"cases": []})
    monkeypatch.setattr(claim_graph, "validate_hic_pack", lambda root: {"cases": []})
    protocol = {
        "holdout": {
            "negative_declarations_schema": (
                "pvr-human-knowledge-identity-claim-graph-negative-declarations-v3"
            ),
            "negative_challenges": {category: 4 for category in categories},
        }
    }

    rows = _negative_holdout_cases(tmp_path, protocol)

    assert len(rows) == 16
    assert {row["case_type"] for row in rows} == {"absent_identity_contradiction"}
    cases[0]["absent_identity"] = ""
    path.write_text(
        json.dumps(
            {
                "schema_version": (
                    "pvr-human-knowledge-identity-claim-graph-negative-declarations-v3"
                ),
                "version": claim_graph.VERSION,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reused, corpus-present, or malformed"):
        _negative_holdout_cases(tmp_path, protocol)


@pytest.mark.parametrize(
    ("challenge", "query"),
    (
        ("leading_year_context", "warehouse find 1988 Jeep Wagoneer unboxed sale"),
        ("frame_local_ocr_numeric", "Mercedes Benz 5o0 E"),
        ("bounded_edit_abbreviation", "suer twin mill"),
        ("compact_spacing_punctuation", "carded 2020ram1500rebel miniature"),
    ),
)
def test_positive_pack_challenges_are_proven_from_graph_evidence(grammar, challenge, query):
    assert claim_graph._positive_challenge_valid(grammar, challenge, query)


def test_raw_schema_rejects_labels_policy_results_and_winner_fields():
    assert _contains_forbidden_raw_key({"rows": [{"expected": {"knowledge_id": "x"}}]})
    assert _contains_forbidden_raw_key({"rows": [{"decision": "admit"}]})
    assert _contains_forbidden_raw_key({"winner": None})
    assert not _contains_forbidden_raw_key(
        {"rows": [{"case_id": "x", "query_text": "Honda Civic", "candidates": []}]}
    )


def test_repeated_collection_validates_existing_raw_without_new_calls(tmp_path, monkeypatch):
    (tmp_path / RAW_DIRECTORY).mkdir(parents=True)
    marker = {"retrieval_calls": 32}
    monkeypatch.setattr(claim_graph, "validate_raw", lambda root: marker)
    monkeypatch.setattr(
        claim_graph,
        "collect_payload",
        lambda root: pytest.fail("repeat collection must not retrieve"),
    )

    assert collect(tmp_path) == (marker, "unchanged")


def test_t3_cli_declares_only_the_five_phase_actions():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    source = (ROOT / SOURCE).read_text(encoding="utf-8")

    assert "pvr-develop-human-knowledge-identity-claim-graph" in pyproject
    for phase in ("--freeze-protocol", "--freeze-pack", "--collect", "--score", "--check"):
        assert phase in source


def test_t4_locks_the_measured_null_calibration_and_branch_boundaries():
    report_path = ROOT / REPORT_DIRECTORY / CALIBRATION_JSON
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summaries = {summary["configuration_id"]: summary for summary in report["summaries"]}

    assert report["status"] == "historical_calibration_fail"
    assert report["winner"] is None
    assert report["eligible_non_reference_configuration_ids"] == []
    assert report["denominators"] == HISTORICAL_DENOMINATORS
    assert report["retrieval_calls_executed"] == 0
    assert report["sources"][SOURCE] == hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest()
    expected = {
        "reference-anchor": (168, 24, 10, 11, 12, 10, 0),
        "claim-conflict-veto": (166, 24, 9, 11, 12, 10, 0),
        "claim-bilateral": (134, 19, 4, 0, 8, 0, 2),
        "claim-query-conservation": (129, 8, 3, 0, 8, 0, 2),
        "claim-decision-list": (131, 3, 4, 0, 8, 0, 2),
    }
    for configuration, counts in expected.items():
        gates = {
            gate["name"]: gate["actual"] for gate in summaries[configuration]["historical_gates"]
        }
        assert (
            gates["existing_positive_hits_at_5"],
            gates["new_required_hits_at_5"],
            gates["anchor_valid_low_coverage_hits"],
            gates["anchor_missing_identity_nonempty"],
            gates["hic_positive_preservation_hits"],
            gates["hic_absent_identity_nonempty"],
            gates["secondary_numeric_conflicts_abstained"],
        ) == counts
        assert gates["retrieval_errors"] == 0
        assert gates["graph_errors"] == gates["alignment_errors"] == gates["decision_errors"] == 0

    assert not (ROOT / claim_graph.DATA_DIRECTORY).exists()
    assert {path.name for path in (ROOT / REPORT_DIRECTORY).iterdir()} == {
        CALIBRATION_JSON,
        CALIBRATION_MANIFEST,
        CALIBRATION_MARKDOWN,
    }


def test_t4_calibration_manifest_and_markdown_bind_the_exact_result():
    directory = ROOT / REPORT_DIRECTORY
    report_path = directory / CALIBRATION_JSON
    manifest = json.loads((directory / CALIBRATION_MANIFEST).read_text(encoding="utf-8"))
    markdown = (directory / CALIBRATION_MARKDOWN).read_text(encoding="utf-8")

    assert manifest["calibration_sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()
    assert manifest["eligible_non_reference_configuration_ids"] == []
    assert manifest["retrieval_calls_executed"] == 0
    assert manifest["protocol_authorized"] is False
    assert "historical_calibration_fail" in markdown
    assert "No protocol, holdout pack, raw retrieval" in markdown
