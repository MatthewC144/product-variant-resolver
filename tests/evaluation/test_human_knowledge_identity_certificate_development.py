import hashlib
import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

from product_variant_resolver import human_knowledge_identity_certificate_development as certificate
from product_variant_resolver.human_knowledge import (
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
)
from product_variant_resolver.human_knowledge_admission_development import _catalog
from product_variant_resolver.human_knowledge_identity_certificate_development import (
    CONTEXT_TOKENS,
    EXPECTED_AUTHORITY_COUNTS,
    EXPECTED_DOCUMENT_COUNTS,
    NON_REFERENCE_PROFILES,
    PROFILES,
    UPSTREAM_FIXED_HASHES,
    AliasBridge,
    CandidateCertificateInput,
    CertificateClaim,
    CertificateInventory,
    ClaimAlignment,
    IdentityAuthority,
    PublicInputBinding,
    build_authority_inventory,
    build_certificate_inventory,
    build_public_authority_inventory,
    build_public_certificate_inventory,
    build_query_support,
    candidate_decision,
    evaluate_candidates_in_source_order,
    profile_definitions,
    validate_candidate_decision,
    validate_certificate_inventory,
    validate_public_inventory,
    validate_query_support,
    verify_upstream_bindings,
)

ROOT = Path(__file__).resolve().parents[2]


def variant(
    number: int,
    casting_id: str,
    casting: str,
    *,
    aliases: tuple[str, ...] = (),
    casting_uuid: UUID | None = None,
) -> HumanVariantKnowledgeDocument:
    return HumanVariantKnowledgeDocument(
        casting_uuid=casting_uuid or UUID(int=10_000 + number),
        casting_id=casting_id,
        provisional_variant_uuid=UUID(int=number),
        provisional_variant_id=f"variant-{number}",
        brand="Hot Wheels",
        casting=casting,
        series_label="Forbidden Series",
        variant_label="Forbidden Color",
        identity_status="needs_canonical_review",
        human_label_names=aliases,
        pricing_keywords=("Forbidden Price",),
        initial_names=("Forbidden Initial",),
        source_case_ids=(f"case-{number}",),
    )


def family(
    number: int, casting: str, aliases: tuple[str, ...] = ()
) -> ReviewFamilyKnowledgeDocument:
    return ReviewFamilyKnowledgeDocument(
        review_family_uuid=UUID(int=20_000 + number),
        review_family_id=f"family-{number}",
        brand="Hot Wheels",
        casting=casting,
        aliases=aliases,
        source_record_ids=(f"source-{number}",),
        identity_status="family_accepted_variants_unreviewed",
    )


def test_all_immutable_upstream_bindings_match_committed_bytes():
    bindings = verify_upstream_bindings(ROOT)

    assert len(bindings) == 9
    assert {binding.file: binding.sha256 for binding in bindings} == UPSTREAM_FIXED_HASHES


def test_upstream_mismatch_fails_before_inventory_construction(tmp_path, monkeypatch):
    relative = next(iter(UPSTREAM_FIXED_HASHES))
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text("changed", encoding="utf-8")
    monkeypatch.setattr(
        certificate,
        "UPSTREAM_FIXED_HASHES",
        {relative: UPSTREAM_FIXED_HASHES[relative]},
    )

    with pytest.raises(ValueError, match="immutable upstream binding mismatch"):
        verify_upstream_bindings(tmp_path)


def test_committed_public_corpus_builds_142_documents_into_139_authorities():
    inventory = build_public_authority_inventory(ROOT)

    assert {
        "documents": inventory.documents,
        "provisional_variant": inventory.provisional_variant_documents,
        "review_family": inventory.review_family_documents,
    } == EXPECTED_DOCUMENT_COUNTS
    assert {
        "authorities": len(inventory.authorities),
        "casting": inventory.casting_authorities,
        "review_family": inventory.review_family_authorities,
        "duplicate_document_excess": inventory.duplicate_document_excess,
    } == EXPECTED_AUTHORITY_COUNTS
    assert len(inventory.upstream_bindings) == 9
    assert len(inventory.corpus_bindings) == 3
    assert len(inventory.checksum) == 64


def test_only_expected_castings_have_multiple_source_documents():
    inventory = build_public_authority_inventory(ROOT)
    duplicated = {
        authority.primary_casting: len(authority.member_knowledge_ids)
        for authority in inventory.authorities
        if len(authority.member_knowledge_ids) > 1
    }

    assert duplicated == {"83 Chevy Silverado": 3, "Toyota Supra": 2}
    assert all(authority.status == "certifiable" for authority in inventory.authorities)


def test_member_order_and_inventory_checksum_are_deterministic():
    first = build_public_authority_inventory(ROOT)
    second = build_public_authority_inventory(ROOT)

    assert first == second
    assert first.as_dict() == second.as_dict()
    assert [item.authority_key for item in first.authorities] == sorted(
        item.authority_key for item in first.authorities
    )
    assert all(
        item.member_knowledge_ids == tuple(sorted(item.member_knowledge_ids))
        for item in first.authorities
    )


def test_authority_contract_excludes_variant_and_source_metadata_fields():
    assert set(IdentityAuthority.__slots__) == {
        "authority_key",
        "authority_kind",
        "primary_casting",
        "normalized_primary_casting",
        "member_knowledge_ids",
        "member_knowledge_uuids",
        "approved_aliases",
        "status",
    }
    forbidden = {
        "brand",
        "series_label",
        "variant_label",
        "pricing_keywords",
        "initial_names",
        "source_case_ids",
        "source_record_ids",
        "color",
        "wheel",
        "tampo",
        "edition",
        "packaging",
    }
    assert forbidden.isdisjoint(IdentityAuthority.__slots__)


def test_grouping_uses_casting_lineage_and_deduplicates_alias_surfaces():
    shared_casting_uuid = UUID(int=99_999)
    inventory = build_authority_inventory(
        (
            variant(
                1,
                "shared-casting",
                "Toyota Supra",
                aliases=("Toyota Supra Premium", "Toyota-Supra Premium"),
                casting_uuid=shared_casting_uuid,
            ),
            variant(
                2,
                "shared-casting",
                "Toyota Supra",
                aliases=("Toyota Supra", "Toyota Supra Premium"),
                casting_uuid=shared_casting_uuid,
            ),
        )
    )
    authority = inventory.authorities[0]

    assert authority.authority_key == "casting:shared-casting"
    assert authority.member_knowledge_ids == ("variant-1", "variant-2")
    assert authority.approved_aliases == ("Toyota Supra Premium",)
    assert "Forbidden Series" not in authority.as_dict().values()
    assert "Forbidden Color" not in authority.as_dict().values()


def test_review_family_uses_its_own_authority_namespace():
    inventory = build_authority_inventory((family(1, "Max Steel", ("Maximum Steel",)),))
    authority = inventory.authorities[0]

    assert authority.authority_key == "review_family:family-1"
    assert authority.authority_kind == "review_family"
    assert authority.primary_casting == "Max Steel"
    assert authority.approved_aliases == ("Maximum Steel",)


def test_primary_casting_collision_is_explicitly_unresolved():
    inventory = build_authority_inventory(
        (
            family(1, "Mercedes-Benz 500 E"),
            family(2, "Mercedes Benz 500 E"),
        )
    )

    assert {item.normalized_primary_casting for item in inventory.authorities} == {
        "mercedes benz 500 e"
    }
    assert {item.status for item in inventory.authorities} == {"unresolved_collision"}


def test_conflicting_documents_under_one_casting_authority_fail_closed():
    shared_casting_uuid = UUID(int=77_777)
    documents = (
        variant(1, "same", "Toyota Supra", casting_uuid=shared_casting_uuid),
        variant(2, "same", "Toyota Soarer", casting_uuid=shared_casting_uuid),
    )

    with pytest.raises(ValueError, match="conflicting primary castings"):
        build_authority_inventory(documents)


def test_duplicate_document_membership_fails_closed():
    document = family(1, "Max Steel")

    with pytest.raises(ValueError, match="unique knowledge IDs"):
        build_authority_inventory((document, document))


def test_public_inventory_validator_rejects_checksum_tampering():
    inventory = build_public_authority_inventory(ROOT)

    with pytest.raises(ValueError, match="checksum is not reproducible"):
        validate_public_inventory(replace(inventory, checksum="0" * 64))


def test_public_inventory_validator_rejects_count_drift():
    inventory = build_public_authority_inventory(ROOT)

    with pytest.raises(ValueError, match="document counts differ"):
        validate_public_inventory(replace(inventory, documents=141))


def test_input_binding_contains_only_public_file_and_hash_fields():
    assert set(PublicInputBinding.__slots__) == {"file", "sha256"}


def certificate_inventory(*documents):
    authority_inventory = build_authority_inventory(tuple(documents))
    return authority_inventory, build_certificate_inventory(authority_inventory)


def test_committed_primary_castings_produce_minimal_certificate_inventory():
    authority_inventory = build_public_authority_inventory(ROOT)
    inventory = build_public_certificate_inventory(ROOT)

    assert inventory.authority_inventory_checksum == authority_inventory.checksum
    assert len(inventory.authorities) == 139
    assert sum(item.status == "unresolved_collision" for item in inventory.authorities) == 7
    assert len(inventory.claims) == 460
    assert len(inventory.certificates) == 401
    assert len(inventory.alias_bridges) == 101
    assert len(inventory.checksum) == 64
    assert (
        max(
            sum(claim.authority_key == authority.authority_key for claim in inventory.claims)
            for authority in inventory.authorities
        )
        == 8
    )


def test_primary_claims_preserve_local_numeric_frame_owners_and_digits():
    inventory = build_public_certificate_inventory(ROOT)
    authority = next(
        item for item in inventory.authorities if item.primary_casting == "2020 Ford F-150 Lariat"
    )
    claims = tuple(
        claim for claim in inventory.claims if claim.authority_key == authority.authority_key
    )

    assert [(claim.kind, claim.normalized_value) for claim in claims] == [
        ("numeric_frame", "2020"),
        ("alphabetic", "ford"),
        ("alphabetic", "f"),
        ("numeric_frame", "150"),
        ("alphabetic", "lariat"),
    ]
    assert (claims[0].frame_kind, claims[0].owner_before, claims[0].owner_after) == (
        "leading_year",
        None,
        "ford",
    )
    assert (claims[3].frame_kind, claims[3].owner_before, claims[3].owner_after) == (
        "standalone_model",
        "f",
        "lariat",
    )
    assert claims[0].digit_runs == ("2020",)
    assert claims[3].digit_runs == ("150",)


def test_multiword_authority_cannot_use_one_alphabetic_claim_as_certificate():
    _, inventory = certificate_inventory(
        family(1, "Honda Civic EG"),
        family(2, "Honda Prelude"),
        family(3, "Toyota Supra"),
    )
    target = next(
        item for item in inventory.authorities if item.primary_casting == "Honda Civic EG"
    )
    certificates = tuple(
        item for item in inventory.certificates if item.authority_key == target.authority_key
    )
    claim_by_id = {item.claim_id: item for item in inventory.claims}

    assert certificates
    assert all(
        not (len(item.claim_ids) == 1 and claim_by_id[item.claim_ids[0]].kind == "alphabetic")
        for item in certificates
    )
    assert any(
        proof.deletion_status == "single_alphabetic_forbidden"
        for item in certificates
        for proof in item.minimality_proof
    )


def test_true_one_word_primary_casting_can_use_one_alphabetic_certificate():
    _, inventory = certificate_inventory(
        family(1, "Bloc"),
        family(2, "Honda Prelude"),
    )
    target = next(item for item in inventory.authorities if item.primary_casting == "Bloc")
    certificates = tuple(
        item for item in inventory.certificates if item.authority_key == target.authority_key
    )

    assert len(certificates) == 1
    assert len(certificates[0].claim_ids) == 1
    assert certificates[0].remaining_after == (target.authority_key,)
    assert certificates[0].minimality_proof[0].deletion_status == "empty_subset"


def test_complete_primary_subsequence_collision_remains_unresolved():
    _, inventory = certificate_inventory(
        family(1, "Dodge Challenger"),
        family(2, "2018 Dodge Challenger SRT Demon"),
    )
    short = next(
        item for item in inventory.authorities if item.primary_casting == "Dodge Challenger"
    )
    long = next(
        item
        for item in inventory.authorities
        if item.primary_casting == "2018 Dodge Challenger SRT Demon"
    )

    assert short.status == "unresolved_collision"
    assert long.status == "certifiable"
    assert not any(item.authority_key == short.authority_key for item in inventory.certificates)
    assert any(item.authority_key == long.authority_key for item in inventory.certificates)


def test_numeric_single_claim_certificate_keeps_owner_proof():
    _, inventory = certificate_inventory(
        family(1, "2020 Ford F-150 Lariat"),
        family(2, "2020 Ford F-150 Raptor"),
    )
    target = next(item for item in inventory.authorities if item.primary_casting.endswith("Lariat"))
    claims = {
        item.claim_id: item
        for item in inventory.claims
        if item.authority_key == target.authority_key
    }
    numeric_singletons = [
        claims[item.claim_ids[0]]
        for item in inventory.certificates
        if item.authority_key == target.authority_key and len(item.claim_ids) == 1
    ]

    assert any(
        item.normalized_value == "150"
        and item.owner_before == "f"
        and item.owner_after == "lariat"
        and item.digit_runs == ("150",)
        for item in numeric_singletons
    )


def test_alias_bridge_maps_only_to_existing_claims_and_retains_unmapped_atoms():
    _, inventory = certificate_inventory(
        family(1, "Mercedes Benz 500 E", ("Premium MercedesBenz 5o0 E",)),
        family(2, "Fiat 500e"),
    )
    bridge = inventory.alias_bridges[0]
    target_claim_ids = {
        item.claim_id for item in inventory.claims if item.authority_key == bridge.authority_key
    }

    assert [item.relation for item in bridge.mappings] == [
        "compact_segmentation",
        "ocr_o_zero",
        "exact",
    ]
    assert {item.text for item in bridge.unmapped_alias_atoms} == {"premium"}
    assert {
        claim_id for mapping in bridge.mappings for claim_id in mapping.target_claim_ids
    }.issubset(target_claim_ids)
    assert len(target_claim_ids) == 4
    assert len(inventory.claims) == 6


def test_alias_bridge_and_certificate_contract_exclude_variant_fields():
    assert set(CertificateClaim.__slots__) == {
        "claim_id",
        "authority_key",
        "kind",
        "normalized_value",
        "source_atom_indices",
        "frame_kind",
        "owner_before",
        "owner_after",
        "digit_runs",
    }
    assert set(AliasBridge.__slots__) == {
        "authority_key",
        "alias",
        "normalized_alias",
        "mappings",
        "unmapped_alias_atoms",
        "checksum",
    }
    forbidden = {
        "series_label",
        "variant_label",
        "pricing_keywords",
        "initial_names",
        "source_case_ids",
        "source_record_ids",
        "color",
        "wheel",
        "tampo",
        "edition",
        "packaging",
        "source_rank",
    }
    assert forbidden.isdisjoint(CertificateClaim.__slots__)
    assert forbidden.isdisjoint(AliasBridge.__slots__)


def test_more_than_twelve_primary_claims_fail_closed():
    authority_inventory = build_authority_inventory(
        (family(1, "one two three four five six seven eight nine ten eleven twelve thirteen"),)
    )

    with pytest.raises(ValueError, match="exceeds 12 primary claims"):
        build_certificate_inventory(authority_inventory)


def test_certificate_inventory_is_deterministic_and_independently_validated():
    authority_inventory = build_public_authority_inventory(ROOT)
    first = build_certificate_inventory(authority_inventory)
    second = build_certificate_inventory(authority_inventory)

    assert first == second
    assert first.as_dict() == second.as_dict()
    validate_certificate_inventory(first, authority_inventory)


def test_certificate_proof_tampering_fails_closed():
    authority_inventory, inventory = certificate_inventory(
        family(1, "Bloc"),
        family(2, "Honda Prelude"),
    )
    changed_certificate = replace(inventory.certificates[0], remaining_after=("wrong",))
    changed = replace(inventory, certificates=(changed_certificate, *inventory.certificates[1:]))
    changed = replace(changed, checksum=certificate._certificate_inventory_checksum(changed))

    with pytest.raises(ValueError, match="proof or checksum is not reproducible"):
        validate_certificate_inventory(changed, authority_inventory)


def test_alias_bridge_tampering_fails_closed():
    authority_inventory, inventory = certificate_inventory(
        family(1, "Mercedes Benz 500 E", ("Premium MercedesBenz 5o0 E",)),
        family(2, "Fiat 500e"),
    )
    changed_bridge = replace(inventory.alias_bridges[0], checksum="0" * 64)
    changed = replace(inventory, alias_bridges=(changed_bridge, *inventory.alias_bridges[1:]))
    changed = replace(changed, checksum=certificate._certificate_inventory_checksum(changed))

    with pytest.raises(ValueError, match="mapping or checksum is not reproducible"):
        validate_certificate_inventory(changed, authority_inventory)


def test_certificate_inventory_contract_has_no_runtime_or_candidate_state():
    assert set(CertificateInventory.__slots__) == {
        "version",
        "authority_inventory_checksum",
        "authorities",
        "claims",
        "certificates",
        "alias_bridges",
        "checksum",
    }


def test_profile_definitions_are_categorical_and_reference_is_comparison_only():
    definitions = profile_definitions()

    assert tuple(item["profile_id"] for item in definitions) == PROFILES
    assert definitions[0] == {
        "profile_id": "reference-anchor",
        "certificate_matching": False,
        "survivor_eligible": False,
        "relations": [],
        "scalar_threshold": None,
    }
    assert tuple(item["profile_id"] for item in definitions[1:]) == NON_REFERENCE_PROFILES
    assert all(item["scalar_threshold"] is None for item in definitions)


def test_reference_profile_cannot_create_certificate_support():
    inventory = build_public_certificate_inventory(ROOT)

    with pytest.raises(ValueError, match="comparison-only"):
        build_query_support("55 Chevy", inventory, "reference-anchor")


def test_exact_partial_certificate_preserves_context_and_omitted_candidate_claims():
    inventory = build_public_certificate_inventory(ROOT)
    evidence = build_query_support("unverified 55 Chevy listing", inventory, "certificate-exact")

    assert evidence.status == "singleton"
    assert evidence.support_authority_keys == ("casting:human-hot-wheels-55-chevy-bel-air-gasser",)
    assert {(item.text, item.reason_code) for item in evidence.context_atoms} == {
        ("unverified", "frozen_context_wrapper"),
        ("listing", "frozen_context_wrapper"),
    }
    complete = [item for item in evidence.certificate_matches if item.complete]
    assert complete
    assert any(item.omitted_primary_claim_ids for item in complete)
    assert not evidence.unresolved_discriminative_atoms
    assert len(evidence.checksum) == 64


@pytest.mark.parametrize(
    ("query", "unresolved"),
    (
        ("Honda Accord", "accord"),
        ("BMW M4", "m4"),
        ("Bugatti Divo", "divo"),
    ),
)
def test_shared_maker_or_generic_token_does_not_create_support(query, unresolved):
    evidence = build_query_support(
        query,
        build_public_certificate_inventory(ROOT),
        "certificate-bounded",
    )

    assert evidence.status == "empty"
    assert not evidence.support_authority_keys
    assert unresolved in {item.text for item in evidence.unresolved_discriminative_atoms}


def test_compact_segmentation_conserves_digit_runs_and_requires_structural_profile():
    inventory = build_public_certificate_inventory(ROOT)
    exact = build_query_support("2020fordf150lariat", inventory, "certificate-exact")
    structural = build_query_support("2020fordf150lariat", inventory, "certificate-structural")

    assert [item.text for item in structural.query_atoms] == [
        "2020",
        "ford",
        "f",
        "150",
        "lariat",
    ]
    assert exact.status == "empty"
    assert structural.status == "singleton"
    assert structural.support_authority_keys == ("casting:human-auto-world-2020-ford-f-150-lariat",)
    assert all(
        relation.relation == "compact_segmentation"
        for match in structural.certificate_matches
        if match.complete
        for relation in match.claim_alignments
    )


def test_unknown_alphanumeric_digit_run_is_not_split_or_silently_discarded():
    inventory = build_public_certificate_inventory(ROOT)
    evidence = build_query_support("Nissan Skyline GTR R33", inventory, "certificate-bounded")

    assert "r33" in {item.text for item in evidence.query_atoms}
    assert not {"3"}.intersection(item.text for item in evidence.query_atoms)
    assert evidence.status == "empty"
    assert any(
        conflict.query_value == "r33" and conflict.public_value == "bnr34"
        for conflict in evidence.numeric_conflicts
    )


def test_year_shorthand_requires_structural_profile_and_keeps_local_frame():
    inventory = build_public_certificate_inventory(ROOT)
    exact = build_query_support("20 Ford F 150 Lariat", inventory, "certificate-exact")
    structural = build_query_support("20 Ford F 150 Lariat", inventory, "certificate-structural")

    assert exact.status == "empty"
    assert structural.status == "singleton"
    assert any(
        alignment.relation == "leading_year_suffix"
        for match in structural.certificate_matches
        if match.complete
        for alignment in match.claim_alignments
    )


def test_ocr_equivalence_requires_bounded_profile():
    inventory = build_public_certificate_inventory(ROOT)
    structural = build_query_support("Mercedes Benz 5o0 E", inventory, "certificate-structural")
    bounded = build_query_support("Mercedes Benz 5o0 E", inventory, "certificate-bounded")

    assert structural.status == "empty"
    assert bounded.status == "singleton"
    assert any(
        alignment.relation == "ocr_o_zero"
        for match in bounded.certificate_matches
        if match.complete
        for alignment in match.claim_alignments
    )


@pytest.mark.parametrize(
    ("casting", "query", "relation"),
    (
        ("Deora III", "de iii", "unique_prefix_abbreviation"),
        ("Morgan Super 3", "moran super 3", "unique_alpha_edit_1"),
        ("Fiat 500e", "fiat 50e", "ocr_repeated_digit_restore"),
        ("94 Audi Avant RS2", "94x audi avant rs2", "leading_year_uncertainty_x"),
    ),
)
def test_each_bounded_relation_is_reason_coded_and_not_structural(casting, query, relation):
    _, inventory = certificate_inventory(
        family(1, casting),
        family(2, "Honda Prelude"),
    )
    structural = build_query_support(query, inventory, "certificate-structural")
    bounded = build_query_support(query, inventory, "certificate-bounded")

    assert structural.status == "empty"
    assert bounded.status == "singleton"
    assert any(
        alignment.relation == relation
        for match in bounded.certificate_matches
        if match.complete
        for alignment in match.claim_alignments
    )


def test_identity_participation_takes_precedence_over_context_vocabulary():
    assert "model" in CONTEXT_TOKENS
    _, inventory = certificate_inventory(
        family(1, "Tesla Model S Plaid"),
        family(2, "Honda Prelude"),
    )
    evidence = build_query_support("listing Tesla Model S Plaid", inventory, "certificate-exact")

    assert evidence.status == "singleton"
    assert {item.text for item in evidence.context_atoms} == {"listing"}
    assert "model" not in {item.text for item in evidence.context_atoms}


def test_structural_year_equivalence_can_remain_ambiguous_without_tie_break():
    _, inventory = certificate_inventory(
        family(1, "2020 Honda Civic"),
        family(2, "20 Honda Civic"),
        family(3, "Toyota Supra"),
    )
    evidence = build_query_support("20 Honda Civic", inventory, "certificate-structural")

    assert evidence.status == "ambiguous"
    assert len(evidence.support_authority_keys) == 2
    assert evidence.ambiguous_authority_keys == evidence.support_authority_keys


def test_same_casting_authority_members_remain_in_source_order_without_variant_resolution():
    shared_casting_uuid = UUID(int=44_444)
    first = variant(1, "toyota-supra", "Toyota Supra", casting_uuid=shared_casting_uuid)
    second = variant(2, "toyota-supra", "Toyota Supra", casting_uuid=shared_casting_uuid)
    other = family(9, "Toyota Soarer")
    _, inventory = certificate_inventory(first, second, other)
    support = build_query_support("Toyota Supra", inventory, "certificate-exact")
    decisions = evaluate_candidates_in_source_order(
        (
            CandidateCertificateInput(other, 1),
            CandidateCertificateInput(first, 2),
            CandidateCertificateInput(second, 4),
        ),
        support,
        inventory,
    )

    assert support.status == "singleton"
    assert [item.source_rank for item in decisions] == [1, 2, 4]
    assert [item.decision for item in decisions] == ["abstain", "admit", "admit"]
    assert all(item.query_support_checksum == support.checksum for item in decisions)
    assert all(
        {"casting_authority_only", "variant_not_resolved"}.issubset(item.reason_codes)
        for item in decisions[1:]
    )


def test_empty_support_cannot_be_bypassed_at_rank_one_or_five():
    inventory = build_public_certificate_inventory(ROOT)
    support = build_query_support("Nissan Skyline GTR R33", inventory, "certificate-bounded")
    document = next(
        item
        for item in _catalog(ROOT).documents
        if item.knowledge_id
        == "human-hot-wheels-nissan-skyline-gtr-bnr34-mainline-blue-2026-k-case"
    )
    decisions = evaluate_candidates_in_source_order(
        (
            CandidateCertificateInput(document, 1),
            CandidateCertificateInput(document, 5),
        ),
        support,
        inventory,
    )

    assert support.status == "empty"
    assert [item.decision for item in decisions] == ["abstain", "abstain"]
    assert all(item.reason_codes == ("query_support_not_singleton",) for item in decisions)


def test_real_partial_certificate_admits_member_without_claiming_variant():
    inventory = build_public_certificate_inventory(ROOT)
    support = build_query_support("55 Chevy", inventory, "certificate-exact")
    document = next(
        item for item in _catalog(ROOT).documents if item.casting == "55 CHEVY BEL AIR GASSER"
    )
    evidence = candidate_decision(CandidateCertificateInput(document, 3), support, inventory)

    assert evidence.decision == "admit"
    assert evidence.authority_membership
    assert evidence.primary_conflict_result == "pass"
    assert "casting_authority_only" in evidence.reason_codes
    assert "variant_not_resolved" in evidence.reason_codes


def test_query_support_overlap_tampering_fails_closed():
    _, inventory = certificate_inventory(
        family(1, "Honda Civic EG"),
        family(2, "Honda Prelude"),
    )
    evidence = build_query_support("Honda Civic EG", inventory, "certificate-exact")
    match_index = next(
        index
        for index, match in enumerate(evidence.certificate_matches)
        if match.complete and len(match.claim_alignments) >= 2
    )
    original_match = evidence.certificate_matches[match_index]
    first_alignment = original_match.claim_alignments[0]
    second_alignment = original_match.claim_alignments[1]
    overlapping = replace(
        second_alignment,
        query_atom_indices=first_alignment.query_atom_indices,
        query_values=first_alignment.query_values,
    )
    changed_match = replace(
        original_match,
        claim_alignments=(first_alignment, overlapping, *original_match.claim_alignments[2:]),
    )
    changed_matches = list(evidence.certificate_matches)
    changed_matches[match_index] = changed_match
    changed = replace(evidence, certificate_matches=tuple(changed_matches))
    changed = replace(changed, checksum=certificate._query_support_checksum(changed))

    with pytest.raises(ValueError, match="reuses one query span"):
        validate_query_support(changed, inventory)


def test_candidate_admission_tampering_fails_closed():
    inventory = build_public_certificate_inventory(ROOT)
    support = build_query_support("55 Chevy", inventory, "certificate-exact")
    document = next(
        item for item in _catalog(ROOT).documents if item.casting == "55 CHEVY BEL AIR GASSER"
    )
    evidence = candidate_decision(CandidateCertificateInput(document, 2), support, inventory)
    changed = replace(evidence, candidate_authority_key="casting:wrong")
    changed = replace(changed, checksum=certificate._candidate_decision_checksum(changed))

    with pytest.raises(ValueError, match="bypasses singleton membership"):
        validate_candidate_decision(changed, support, inventory)


def test_query_support_contract_contains_no_candidate_rank_score_or_uuid():
    forbidden = {"candidate", "source_rank", "score", "knowledge_uuid"}
    assert forbidden.isdisjoint(certificate.QuerySupportEvidence.__slots__)
    assert set(ClaimAlignment.__slots__) == {
        "claim_id",
        "query_atom_indices",
        "query_values",
        "public_value",
        "relation",
    }


def _zero_lifecycle_metrics():
    return {
        "source_candidates": 0,
        "admitted_candidates": 0,
        "abstained_candidates": 0,
        "non_exact_equivalence_operations": 0,
        "retrieval_errors": 0,
        "certificate_construction_errors": 0,
        "query_support_errors": 0,
        "alias_alignment_errors": 0,
        "frame_comparison_errors": 0,
        "decision_errors": 0,
    }


def _synthetic_calibration(inventory, survivors=()):
    return {
        "schema_version": certificate.CALIBRATION_SCHEMA,
        "version": certificate.VERSION,
        "status": "historical_calibration_pass" if survivors else "historical_calibration_fail",
        "denominators": certificate.HISTORICAL_DENOMINATORS,
        "retrieval_calls_executed": 0,
        "private_local_artifacts_read": False,
        "sources": {certificate.SOURCE: "synthetic-source-hash"},
        "inventory_checksum": inventory.checksum,
        "profile_definitions": list(profile_definitions()),
        "summaries": [],
        "eligible_non_reference_profile_ids": list(survivors),
        "winner": None,
    }


def test_hics_t4_historical_contract_uses_223_22_24_without_retrieval(monkeypatch):
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
            "case_type": (
                "valid_low_coverage_anchor" if index < 10 else "missing_identity_hard_negative"
            ),
        }
        for index, row in enumerate(anchor_rows)
    ]
    hic_cases = [
        {
            "case_id": row["case_id"],
            "case_type": (
                "positive_preservation" if index < 12 else "absent_identity_contradiction"
            ),
        }
        for index, row in enumerate(hic_rows)
    ]
    document = family(900, "Honda Prelude")
    inventory = certificate_inventory(document)[1]
    monkeypatch.setattr(
        certificate, "verify_historical_inputs", lambda root: {certificate.SOURCE: "hash"}
    )
    monkeypatch.setattr(
        certificate, "check_upstream", lambda root: {"raw": {"rows": existing_rows}}
    )
    monkeypatch.setattr(certificate, "check_anchor", lambda root: {"raw": {"rows": anchor_rows}})
    monkeypatch.setattr(certificate, "validate_anchor_pack", lambda root: {"cases": anchor_cases})
    monkeypatch.setattr(certificate, "validate_hic_raw", lambda root: {"rows": hic_rows})
    monkeypatch.setattr(certificate, "validate_hic_pack", lambda root: {"cases": hic_cases})
    monkeypatch.setattr(
        certificate, "_catalog", lambda root: type("C", (), {"documents": (document,)})()
    )
    monkeypatch.setattr(certificate, "_cases", lambda root: existing_cases)
    monkeypatch.setattr(certificate, "build_public_certificate_inventory", lambda root: inventory)
    monkeypatch.setattr(
        certificate,
        "_reference_profile",
        lambda source_rows, documents, grammar: (source_rows, [], _zero_lifecycle_metrics()),
    )
    monkeypatch.setattr(
        certificate,
        "apply_certificate_profile",
        lambda source_rows, documents, current_inventory, profile_id: (
            source_rows,
            [],
            _zero_lifecycle_metrics(),
        ),
    )
    monkeypatch.setattr(
        certificate,
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
        certificate,
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
        certificate,
        "summarize_hic",
        lambda pack, original, filtered, errors: {
            "counts": {
                "positive_preservation_hits": 12,
                "absent_identity_nonempty": 0,
                "retrieval_errors": 0,
            }
        },
    )
    monkeypatch.setattr(certificate, "_known_secondary_conflicts_abstained", lambda *args: 2)
    monkeypatch.setattr(
        certificate.HumanKnowledgeIdentityRetriever,
        "retrieve_with_work",
        lambda *args, **kwargs: pytest.fail("historical scoring must never retrieve"),
    )

    report = certificate.historical_calibration(Path("synthetic"))

    assert report["denominators"] == certificate.HISTORICAL_DENOMINATORS
    assert report["retrieval_calls_executed"] == 0
    assert [item["profile_id"] for item in report["summaries"]] == list(PROFILES)
    assert all(len(item["historical_gates"]) == 16 for item in report["summaries"])
    assert report["eligible_non_reference_profile_ids"] == list(NON_REFERENCE_PROFILES)
    assert "reference-anchor" not in report["eligible_non_reference_profile_ids"]


def test_hics_t4_winner_order_is_negative_positive_nonexact_then_profile():
    base = {
        "negative_admitted_candidates": 0,
        "positive_abstained_candidates": 0,
        "non_exact_equivalence_operations": 0,
    }
    summaries = [
        {"profile_id": profile, "selection_metrics": dict(base)}
        for profile in reversed(NON_REFERENCE_PROFILES)
    ]

    assert min(summaries, key=certificate.profile_selection_key)["profile_id"] == (
        "certificate-exact"
    )
    summaries[-1]["selection_metrics"]["negative_admitted_candidates"] = 1
    assert min(summaries, key=certificate.profile_selection_key)["profile_id"] == (
        "certificate-structural"
    )


def test_hics_t4_failed_freeze_writes_only_three_null_calibration_files(tmp_path, monkeypatch):
    inventory = certificate_inventory(family(901, "Honda Prelude"))[1]
    report = _synthetic_calibration(inventory)
    monkeypatch.setattr(certificate, "historical_calibration", lambda root: report)

    assert certificate.freeze_protocol(tmp_path) == "calibration_failed_created"
    assert certificate.freeze_protocol(tmp_path) == "calibration_failed_unchanged"
    report_directory = tmp_path / certificate.REPORT_DIRECTORY
    assert {path.name for path in report_directory.iterdir()} == {
        certificate.CALIBRATION_JSON,
        certificate.CALIBRATION_MANIFEST,
        certificate.CALIBRATION_MARKDOWN,
    }
    assert (
        json.loads((report_directory / certificate.CALIBRATION_JSON).read_text())["winner"] is None
    )
    assert not (tmp_path / certificate.DATA_DIRECTORY).exists()


def test_hics_t4_successful_freeze_binds_protocol_and_inventory_once(tmp_path, monkeypatch):
    inventory = certificate_inventory(family(902, "Honda Prelude"))[1]
    report = _synthetic_calibration(inventory, ("certificate-exact",))
    monkeypatch.setattr(certificate, "historical_calibration", lambda root: report)
    monkeypatch.setattr(certificate, "build_public_certificate_inventory", lambda root: inventory)

    assert certificate.freeze_protocol(tmp_path) == "created"
    assert certificate.freeze_protocol(tmp_path) == "unchanged"
    assert (tmp_path / certificate.PROTOCOL_DIRECTORY / "protocol.json").is_file()
    assert (tmp_path / certificate.INVENTORY_DIRECTORY / "inventory.json").is_file()
    assert not (tmp_path / certificate.PACK_DIRECTORY).exists()


def test_hics_t4_freeze_rejects_changed_bytes_and_partial_phase_state(tmp_path, monkeypatch):
    inventory = certificate_inventory(family(903, "Honda Prelude"))[1]
    report = _synthetic_calibration(inventory, ("certificate-exact",))
    monkeypatch.setattr(certificate, "historical_calibration", lambda root: report)
    monkeypatch.setattr(certificate, "build_public_certificate_inventory", lambda root: inventory)
    changed_root = tmp_path / "changed"
    partial_root = tmp_path / "partial"

    assert certificate.freeze_protocol(changed_root) == "created"
    protocol_path = changed_root / certificate.PROTOCOL_DIRECTORY / "protocol.json"
    protocol_path.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from recomputation"):
        certificate.freeze_protocol(changed_root)

    (partial_root / certificate.PROTOCOL_DIRECTORY).mkdir(parents=True)
    with pytest.raises(ValueError, match="protocol and inventory artifacts are partial"):
        certificate.freeze_protocol(partial_root)
    assert not (partial_root / certificate.REPORT_DIRECTORY).exists()


def test_hics_t4_raw_schema_rejects_labels_profiles_gates_and_winner_at_any_depth():
    assert certificate._contains_forbidden_raw_key({"rows": [{"expected": {"id": "x"}}]})
    assert certificate._contains_forbidden_raw_key({"rows": [{"profile_id": "exact"}]})
    assert certificate._contains_forbidden_raw_key({"rows": [{"gates": []}]})
    assert certificate._contains_forbidden_raw_key({"winner": None})
    assert not certificate._contains_forbidden_raw_key(
        {"rows": [{"case_id": "x", "query_text": "Honda Civic", "candidates": []}]}
    )


def test_hics_t4_repeated_collection_never_retries_existing_error_rows(tmp_path, monkeypatch):
    (tmp_path / certificate.RAW_DIRECTORY).mkdir(parents=True)
    marker = {"retrieval_calls": 32, "rows": [{"error": {"type": "Timeout"}}]}
    monkeypatch.setattr(certificate, "validate_raw", lambda root: marker)
    monkeypatch.setattr(
        certificate,
        "collect_payload",
        lambda root: pytest.fail("repeat collection must not retrieve"),
    )

    assert certificate.collect(tmp_path) == (marker, "unchanged")


def test_hics_t4_cli_declares_only_the_five_phase_actions():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    source = (ROOT / certificate.SOURCE).read_text(encoding="utf-8")

    assert "pvr-develop-human-knowledge-identity-certificate" in pyproject
    for phase in ("--freeze-protocol", "--freeze-pack", "--collect", "--score", "--check"):
        assert phase in source


def test_hics_t4_pack_contract_requires_16_plus_16_and_disjoint_families(tmp_path, monkeypatch):
    protocol = {
        "holdout": {
            "positive_challenges": certificate.POSITIVE_CHALLENGES,
            "negative_challenges": certificate.NEGATIVE_CHALLENGES,
        }
    }
    positives = [
        {
            "case_id": f"pos-{challenge}-{index}",
            "case_type": "positive_preservation",
            "challenge_type": challenge,
            "authority_key": f"casting:positive-{challenge}-{index}",
        }
        for challenge in certificate.POSITIVE_CHALLENGES
        for index in range(4)
    ]
    negatives = [
        {
            "case_id": f"neg-{challenge}-{index}",
            "case_type": "absent_identity_contradiction",
            "challenge_type": challenge,
            "family_key": f"absent:{challenge}:{index}",
        }
        for challenge in certificate.NEGATIVE_CHALLENGES
        for index in range(4)
    ]
    monkeypatch.setattr(certificate, "validate_protocol", lambda root: protocol)
    monkeypatch.setattr(certificate, "_positive_holdout_cases", lambda root, frozen: positives)
    monkeypatch.setattr(certificate, "_negative_holdout_cases", lambda root, frozen: negatives)
    monkeypatch.setattr(certificate, "_sha256", lambda path: "0" * 64)

    pack, manifest = certificate.build_pack(tmp_path)

    assert pack["case_counts"] == {
        "positive_preservation": 16,
        "absent_identity_contradiction": 16,
    }
    assert pack["family_disjoint"] is manifest["family_disjoint"] is True
    negatives[0]["family_key"] = positives[0]["authority_key"]
    with pytest.raises(ValueError, match="family-disjoint"):
        certificate.build_pack(tmp_path)


def test_hics_t5_locks_the_measured_null_calibration_and_branch_boundaries():
    report_path = ROOT / certificate.REPORT_DIRECTORY / certificate.CALIBRATION_JSON
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summaries = {item["profile_id"]: item for item in report["summaries"]}

    assert report["status"] == "historical_calibration_fail"
    assert report["winner"] is None
    assert report["eligible_non_reference_profile_ids"] == []
    assert report["denominators"] == certificate.HISTORICAL_DENOMINATORS
    assert report["retrieval_calls_executed"] == 0
    assert (
        report["sources"][certificate.SOURCE]
        == hashlib.sha256((ROOT / certificate.SOURCE).read_bytes()).hexdigest()
    )
    expected = {
        "reference-anchor": (168, 24, 10, 11, 12, 10, 0, 23, 123, 0),
        "certificate-exact": (42, 6, 0, 0, 3, 0, 2, 0, 294, 0),
        "certificate-structural": (82, 7, 4, 0, 7, 0, 2, 0, 245, 269),
        "certificate-bounded": (137, 5, 5, 0, 7, 0, 2, 0, 191, 363),
    }
    for profile_id, counts in expected.items():
        summary = summaries[profile_id]
        gates = {gate["name"]: gate["actual"] for gate in summary["historical_gates"]}
        metrics = summary["selection_metrics"]
        assert (
            gates["existing_positive_hits_at_5"],
            gates["new_required_hits_at_5"],
            gates["anchor_valid_low_coverage_hits"],
            gates["anchor_missing_identity_nonempty"],
            gates["hic_positive_preservation_hits"],
            gates["hic_absent_identity_nonempty"],
            gates["secondary_numeric_conflicts_abstained"],
            metrics["negative_admitted_candidates"],
            metrics["positive_abstained_candidates"],
            metrics["non_exact_equivalence_operations"],
        ) == counts
        assert gates["merge_hits_at_5"] == 4
        assert gates["existing_forbidden_candidates"] == gates["unrelated_nonempty"] == 0
        assert all(
            gates[name] == 0
            for name in (
                "retrieval_errors",
                "certificate_construction_errors",
                "query_support_errors",
                "alias_alignment_errors",
                "frame_comparison_errors",
                "decision_errors",
            )
        )

    assert not (ROOT / certificate.DATA_DIRECTORY).exists()
    assert {path.name for path in (ROOT / certificate.REPORT_DIRECTORY).iterdir()} == {
        certificate.CALIBRATION_JSON,
        certificate.CALIBRATION_MANIFEST,
        certificate.CALIBRATION_MARKDOWN,
    }


def test_hics_t5_manifest_and_markdown_bind_the_exact_failed_result():
    directory = ROOT / certificate.REPORT_DIRECTORY
    report_path = directory / certificate.CALIBRATION_JSON
    manifest_path = directory / certificate.CALIBRATION_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    markdown = (directory / certificate.CALIBRATION_MARKDOWN).read_text(encoding="utf-8")

    assert hashlib.sha256(report_path.read_bytes()).hexdigest() == (
        "d9ca782bd47252af0a1047776da3add97a5b40b2709b8a5d44bf4e6ecd78cf96"
    )
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == (
        "3bb89724f50f5a1229bf36023b84551fe7ee3cd27f5355f74d4fee1fd582ec95"
    )
    assert manifest["calibration_sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()
    assert manifest["eligible_non_reference_profile_ids"] == []
    assert manifest["retrieval_calls_executed"] == 0
    assert manifest["protocol_authorized"] is False
    assert "historical_calibration_fail" in markdown
    assert "No protocol, inventory, holdout pack, raw retrieval" in markdown
