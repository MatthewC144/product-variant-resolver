from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

import product_variant_resolver.canonical_authority_packet as packet_module
from product_variant_resolver.canonical_authority_packet import (
    CANDIDATE_PLAN_REFERENCE,
    DEFAULT_LOCAL_NAME,
    LOCAL_PARENT_REFERENCE,
    MANIFEST_REFERENCE,
    CatalogProposalBundle,
    FrozenCatalogProjectionV2,
    build_catalog_projection,
    derive_workspace,
    publish_workspace,
    validate_catalog_projection,
    validate_proposal_bundle,
    validate_proposal_review_packet,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    CanonicalProductRecord,
    content_sha256,
    stable_json_bytes,
)

ROOT = Path(__file__).resolve().parents[2]
COPY_PATHS = (
    ".gitignore",
    "data/catalog.json",
    "data/authority-review/canonical-authority-review-v1/candidate-plan.json",
    "data/authority-review/canonical-authority-review-v1/source-decisions.json",
    "data/authority-review/canonical-authority-review-v1/source-decisions-manifest.json",
    "data/external/hot-wheels-wiki/pilot-2025/normalized.json",
    "data/external/hot-wheels-wiki/pilot-2025/manifest.json",
    "specs/canonical-authority-review-v1/design.md",
    "specs/canonical-authority-review-v1/requirements.md",
    "specs/canonical-authority-review-v1/source-approval.md",
    "specs/canonical-authority-review-v1/tasks.md",
)


@pytest.fixture
def isolated_root(tmp_path: Path) -> Path:
    for reference in COPY_PATHS:
        source = ROOT / reference
        target = tmp_path / reference
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def test_projection_rebuilds_raw_catalog_and_excludes_every_synthetic_fixture() -> None:
    projection, catalog = build_catalog_projection(ROOT)

    assert projection.raw_catalog_sha256 == (
        "0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261"
    )
    assert projection.raw_catalog_version == "fixture-v1"
    assert projection.raw_product_count == len(catalog.products) == 120
    assert projection.eligible_product_count == 0
    assert projection.excluded_synthetic_product_count == 120
    assert projection.eligible_products == []


def test_workspace_contains_twenty_staged_deterministic_proposals_only() -> None:
    first = derive_workspace(ROOT)
    second = derive_workspace(ROOT)

    assert first == second
    proposals = first.proposal_bundle.proposals
    assert len(proposals) == 20
    assert len({item.proposed_canonical_uuid for item in proposals}) == 20
    assert all(item.review_status == "staged" for item in proposals)
    assert all(item.reviewed_by_role is None for item in proposals)
    assert all(item.reviewed_at is None for item in proposals)
    assert all(item.review_reason is None for item in proposals)
    assert all(item.authority_approved is False for item in proposals)
    assert all(item.catalog_record_applied is False for item in proposals)
    assert all(item.proposed_product_record.color is None for item in proposals)
    assert all(item.proposed_product_record.edition is None for item in proposals)
    assert all(len(item.pending_field_evidence) == 6 for item in proposals)
    assert all(
        [row.field.value for row in item.pending_field_evidence]
        == [
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        ]
        for item in proposals
    )
    assert first.review_packet.pending_owner_question_count == 20
    assert first.manifest.surplus_excluded_count == 9
    assert first.manifest.existing_eligible_exact_match_count == 0
    assert first.manifest.exact_authority_count == 0
    assert first.manifest.rhb_t5_authorized is False


def test_pending_mapping_language_does_not_claim_owner_agreement() -> None:
    artifacts = derive_workspace(ROOT)
    for proposal in artifacts.proposal_bundle.proposals:
        for evidence in proposal.pending_field_evidence:
            assert evidence.owner_reviewed is False
            assert evidence.authority_approved is False
            assert evidence.mapping_status.endswith("pending_owner_review")
            assert "not owner approval" in evidence.notes


def test_local_markdown_exposes_all_pending_fields_issues_questions_and_variant_notes() -> None:
    artifacts = derive_workspace(ROOT)
    markdown = artifacts.owner_markdown
    entries = artifacts.review_packet.entries

    assert markdown.count("## car-t3-") == 20
    assert markdown.count("- Pending field `") == 120
    assert markdown.count("evidence refs:") == 120
    assert markdown.count("- Missing/conflicting items:") == 20
    assert markdown.count("- Pending owner question:") == 20
    noted = [entry for entry in entries if entry.variant_note_context is not None]
    assert len(noted) == 13
    assert markdown.count("`context_only_not_color_or_edition_evidence`") == 13
    for entry in entries:
        assert len(entry.proposal.pending_field_evidence) == 6
        assert all(
            evidence.field.value not in {"color", "edition"}
            for evidence in entry.proposal.pending_field_evidence
        )
        if entry.variant_note_context is not None:
            assert f"Variant note: `{entry.variant_note_context}`" in markdown


def test_public_manifest_contains_aggregates_and_hashes_but_no_private_rows() -> None:
    text = json.dumps(derive_workspace(ROOT).manifest.model_dump(mode="json"), ensure_ascii=False)

    assert "fandom-row-" not in text
    assert "Subaru BRZ" not in text
    assert "Mazda" not in text
    assert "@" not in text
    assert "local_only_git_ignored" in text
    assert "safe_aggregate_and_hash_metadata_only" in text


def test_projection_rejects_unknown_fields_stale_hash_and_preconstructed_extras() -> None:
    projection, _ = build_catalog_projection(ROOT)
    unknown = projection.model_dump(mode="json")
    unknown["trusted_by_caller"] = True
    with pytest.raises(ValidationError):
        validate_catalog_projection(ROOT, unknown)

    stale = projection.model_dump(mode="json")
    stale["raw_catalog_sha256"] = "a" * 64
    stale["projection_sha256"] = content_sha256(
        {key: value for key, value in stale.items() if key != "projection_sha256"}
    )
    with pytest.raises(AuthorityContractError, match="differs from strict raw-catalog rebuild"):
        validate_catalog_projection(ROOT, stale)

    constructed = FrozenCatalogProjectionV2.model_construct(**projection.model_dump())
    constructed.__dict__["trusted_by_caller"] = True
    with pytest.raises(AuthorityContractError, match="undeclared fields"):
        validate_catalog_projection(ROOT, constructed)


def test_bundle_rejects_tampered_candidate_parent_product_evidence_uuid_and_order() -> None:
    bundle = derive_workspace(ROOT).proposal_bundle.model_dump(mode="json")
    mutations: list[dict[str, Any]] = []

    candidate = copy.deepcopy(bundle)
    candidate["proposals"][0]["candidate_id"] = "candidate-tampered"
    mutations.append(candidate)

    parent = copy.deepcopy(bundle)
    parent["proposals"][0]["parent_raw_catalog_sha256"] = "a" * 64
    mutations.append(parent)

    product = copy.deepcopy(bundle)
    product["proposals"][0]["proposed_product_record"]["casting"] = "Wrong casting"
    product["proposals"][0]["product_record_sha256"] = content_sha256(
        product["proposals"][0]["proposed_product_record"]
    )
    mutations.append(product)

    evidence = copy.deepcopy(bundle)
    evidence["proposals"][0]["pending_field_evidence"][0]["source_value"] = "Wrong casting"
    evidence["proposals"][0]["pending_field_evidence"][0]["proposed_value"] = "Wrong casting"
    mutations.append(evidence)

    uuid = copy.deepcopy(bundle)
    uuid["proposals"][0]["proposed_canonical_uuid"] = uuid["proposals"][1][
        "proposed_canonical_uuid"
    ]
    mutations.append(uuid)

    reordered = copy.deepcopy(bundle)
    reordered["proposals"] = list(reversed(reordered["proposals"]))
    mutations.append(reordered)

    for mutation in mutations:
        with pytest.raises((AuthorityContractError, ValidationError)):
            validate_proposal_bundle(ROOT, mutation)


def test_bundle_rejects_pii_and_preconstructed_nested_extras() -> None:
    artifacts = derive_workspace(ROOT)
    pii = artifacts.proposal_bundle.model_dump(mode="json")
    pii["proposals"][0]["proposed_product_record"]["casting"] = "owner@example.com"
    pii["proposals"][0]["product_record_sha256"] = content_sha256(
        pii["proposals"][0]["proposed_product_record"]
    )
    with pytest.raises(ValidationError):
        validate_proposal_bundle(ROOT, pii)

    proposal = artifacts.proposal_bundle.proposals[0]
    product = CanonicalProductRecord.model_construct(
        **proposal.proposed_product_record.model_dump()
    )
    product.__dict__["hidden_prediction"] = "secret"
    bad_proposal = proposal.model_copy(update={"proposed_product_record": product})
    bad_bundle = CatalogProposalBundle.model_construct(
        **artifacts.proposal_bundle.model_dump(exclude={"proposals"}),
        proposals=[bad_proposal, *artifacts.proposal_bundle.proposals[1:]],
    )
    with pytest.raises(AuthorityContractError, match="undeclared fields"):
        validate_proposal_bundle(ROOT, bad_bundle)


def test_candidate_source_and_catalog_tampering_fail_before_output(isolated_root: Path) -> None:
    candidate_path = isolated_root / (
        "data/authority-review/canonical-authority-review-v1/candidate-plan.json"
    )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["primary_queue"]["families"][0]["candidates"][0]["source_record_id"] = (
        "fandom-row-not-approved"
    )
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    with pytest.raises(AuthorityContractError, match="candidate plan checksum"):
        derive_workspace(isolated_root)

    shutil.copy2(ROOT / CANDIDATE_PLAN_REFERENCE, candidate_path)
    catalog_path = isolated_root / "data/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["catalog_version"] = "changed"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises((AuthorityContractError, ValidationError)):
        derive_workspace(isolated_root)


def test_raw_uuid_collision_is_checked_against_all_120_catalog_rows(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = json.loads((isolated_root / "data/catalog.json").read_text(encoding="utf-8"))
    colliding = UUID(raw["products"][0]["canonical_uuid"])
    monkeypatch.setattr(packet_module, "uuid5", lambda *_args: colliding)

    with pytest.raises(AuthorityContractError, match="collides with the raw catalog"):
        derive_workspace(isolated_root)


def test_first_build_repeat_and_check_are_deterministic_and_do_not_mutate_catalog(
    isolated_root: Path,
) -> None:
    catalog_path = isolated_root / "data/catalog.json"
    before = catalog_path.read_bytes()

    assert publish_workspace(isolated_root) == "created"
    assert publish_workspace(isolated_root) == "unchanged"
    assert publish_workspace(isolated_root, check=True) == "unchanged"
    assert catalog_path.read_bytes() == before

    output = isolated_root / LOCAL_PARENT_REFERENCE / DEFAULT_LOCAL_NAME
    assert {item.name for item in output.iterdir()} == {
        "catalog-proposals.json",
        "catalog-proposal-review-packet.json",
        "OWNER-REVIEW.md",
        "catalog-decision-template.json",
    }
    template = json.loads((output / "catalog-decision-template.json").read_text())
    assert len(template["decisions"]) == 20
    assert all(row["catalog_decision"] is None for row in template["decisions"])
    manifest = json.loads((isolated_root / MANIFEST_REFERENCE).read_text(encoding="utf-8"))
    expected_hashes = {
        "local_proposal_bundle_sha256": "catalog-proposals.json",
        "local_review_packet_sha256": "catalog-proposal-review-packet.json",
        "local_owner_markdown_sha256": "OWNER-REVIEW.md",
        "local_blank_decision_template_sha256": "catalog-decision-template.json",
    }
    for field, filename in expected_hashes.items():
        assert manifest[field] == hashlib.sha256((output / filename).read_bytes()).hexdigest()


def test_check_never_writes_and_partial_or_drifted_output_fails_closed(
    isolated_root: Path,
) -> None:
    with pytest.raises(AuthorityContractError, match="--check never writes"):
        publish_workspace(isolated_root, check=True)
    assert not (isolated_root / MANIFEST_REFERENCE).exists()

    output = isolated_root / LOCAL_PARENT_REFERENCE / DEFAULT_LOCAL_NAME
    output.mkdir()
    (output / "partial.json").write_text("{}", encoding="utf-8")
    with pytest.raises(AuthorityContractError, match="asymmetric partial"):
        publish_workspace(isolated_root)
    assert not (isolated_root / MANIFEST_REFERENCE).exists()


def test_manifest_only_partial_state_fails_closed_without_creating_local_output(
    isolated_root: Path,
) -> None:
    manifest_path = isolated_root / MANIFEST_REFERENCE
    manifest_path.write_bytes(
        stable_json_bytes(derive_workspace(isolated_root).manifest.model_dump(mode="json"))
    )

    with pytest.raises(AuthorityContractError, match="asymmetric partial"):
        publish_workspace(isolated_root)

    assert manifest_path.is_file()
    assert not (isolated_root / LOCAL_PARENT_REFERENCE / DEFAULT_LOCAL_NAME).exists()


def test_symlink_and_path_traversal_outputs_are_rejected(isolated_root: Path) -> None:
    parent = isolated_root / LOCAL_PARENT_REFERENCE
    outside = isolated_root / "outside"
    outside.mkdir()
    symlink = parent / DEFAULT_LOCAL_NAME
    symlink.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AuthorityContractError, match="symlink"):
        publish_workspace(isolated_root)

    symlink.unlink()
    with pytest.raises(AuthorityContractError, match="repository-relative"):
        publish_workspace(isolated_root, output_dir=parent / DEFAULT_LOCAL_NAME)
    with pytest.raises(AuthorityContractError, match="safe direct child"):
        publish_workspace(
            isolated_root,
            output_dir=Path(LOCAL_PARENT_REFERENCE) / ".." / "escaped",
        )


def test_middle_ancestor_symlink_escape_fails_before_local_or_manifest_write(
    isolated_root: Path,
) -> None:
    real_authority = isolated_root / "outside-authority"
    authority = isolated_root / "data/authority-review"
    authority.rename(real_authority)
    authority.symlink_to(real_authority, target_is_directory=True)

    with pytest.raises(AuthorityContractError, match="symlink ancestor"):
        publish_workspace(isolated_root)

    escaped_parent = real_authority / "canonical-authority-review-v1"
    assert not (escaped_parent / DEFAULT_LOCAL_NAME).exists()
    assert not (escaped_parent / "catalog-proposal-manifest.json").exists()


def test_relative_custom_exact_ignored_direct_child_succeeds(isolated_root: Path) -> None:
    custom_name = "local-owner-choice"
    with (isolated_root / ".gitignore").open("a", encoding="utf-8") as handle:
        handle.write(f"/{LOCAL_PARENT_REFERENCE}/{custom_name}/\n")
    relative = Path(LOCAL_PARENT_REFERENCE) / custom_name

    assert publish_workspace(isolated_root, output_dir=relative) == "created"
    assert publish_workspace(isolated_root, output_dir=relative, check=True) == "unchanged"
    assert (isolated_root / relative / "OWNER-REVIEW.md").is_file()


def test_atomic_manifest_failure_rolls_back_new_local_directory(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second_replace(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated manifest promotion failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="simulated"):
        publish_workspace(isolated_root)

    assert not (isolated_root / LOCAL_PARENT_REFERENCE / DEFAULT_LOCAL_NAME).exists()
    assert not (isolated_root / MANIFEST_REFERENCE).exists()


def test_review_packet_rejects_authority_promotion_and_output_consultation() -> None:
    packet = derive_workspace(ROOT).review_packet.model_dump(mode="json")
    promoted = copy.deepcopy(packet)
    promoted["authority_approved_count"] = 1
    with pytest.raises(ValidationError):
        validate_proposal_review_packet(ROOT, promoted)

    consulted = copy.deepcopy(packet)
    consulted["resolver_output_consulted"] = True
    with pytest.raises(ValidationError):
        validate_proposal_review_packet(ROOT, consulted)


def test_both_thin_scripts_support_build_and_check(isolated_root: Path) -> None:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    build = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/build_canonical_catalog_record_proposals.py"),
            "--root",
            str(isolated_root),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    check = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/build_canonical_authority_review_packet.py"),
            "--root",
            str(isolated_root),
            "--check",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert build.stdout.strip() == "created"
    assert check.stdout.strip() == "unchanged"
