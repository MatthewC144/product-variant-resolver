from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import product_variant_resolver.canonical_authority_preparation as preparation
from product_variant_resolver.canonical_authority_preparation import (
    AuthorityReviewPreparationPacket,
    build_authority_review_preparation,
    prepare_authority_review,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    AuthorityReviewEventV2,
    BatchOwnerAuthorization,
    ExpectedBatchOwnerAuthorization,
    OwnerAttestationV2,
    VariantFieldEvidence,
    content_sha256,
    stable_json_bytes,
    validate_batch_owner_authorization,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "prepare_canonical_authority_review.py"


@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "specs", root / "specs")
    shutil.copyfile(ROOT / ".gitignore", root / ".gitignore")
    # Every isolated test starts immediately before CAR-T5P.  The real workspace may already have
    # the materialized packet, but CAR-T4/catalog/application parents must remain exact copies.
    private_output = root / preparation.PRIVATE_DIRECTORY
    if private_output.exists():
        shutil.rmtree(private_output)
    public_output = root / preparation.PUBLIC_MANIFEST_REFERENCE
    public_output.unlink(missing_ok=True)
    for reference in (
        Path("data/authority-review/canonical-authority-review-v1/approved-authority.json"),
        Path("data/authority-review/canonical-authority-review-v1/authority-manifest.json"),
    ):
        (root / reference).unlink(missing_ok=True)
    return root


def _rewrite(path: Path, payload: Any) -> None:
    path.write_bytes(stable_json_bytes(payload))


def _private_packet(root: Path) -> Path:
    return root / preparation.PRIVATE_PACKET_REFERENCE


def _public_manifest(root: Path) -> Path:
    return root / preparation.PUBLIC_MANIFEST_REFERENCE


G1_RESPONSE = "I explicitly authorize T5-G1 review outcomes for every covered entry."
G2_RESPONSE = "I explicitly authorize T5-G2 exact-authority outcomes for every covered entry."
REVIEW_ONLY_RESPONSE = "I explicitly authorize review-only outcomes for the covered entries."


def _response_sha256(response: str) -> str:
    return hashlib.sha256(response.encode("utf-8")).hexdigest()


def _valid_batch_authorization(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-batch-owner-authorization-v1",
        "gate": "T5-G1",
        "authorization_scope": "staged_to_reviewed",
        "authorization_declaration": (
            "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry"
        ),
        "packet_sha256": "1" * 64,
        "batch_ordinal": 1,
        "family_batch_sha256": "4" * 64,
        "catalog_application_manifest_sha256": "5" * 64,
        "catalog_version": "catalog-v2",
        "catalog_sha256": "2" * 64,
        "ordered_candidate_ids": ["candidate-a"],
        "ordered_entry_sha256s": ["3" * 64],
        "declared_outcome": "reviewed",
        "owner_response_verbatim": G1_RESPONSE,
        "authorized_exact_owner_response": G1_RESPONSE,
        "response_verbatim_sha256": _response_sha256(G1_RESPONSE),
        "prior_gate_response_sha256s": [],
        "confirmation_method": "owner_attestation",
        "reviewed_by_role": "project_owner",
        "authorized_at": "2026-09-30T12:00:00Z",
        "resolver_output_consulted": False,
    }
    body.update(overrides)
    body["response_verbatim_sha256"] = _response_sha256(body["owner_response_verbatim"])
    body["authorization_sha256"] = content_sha256(body)
    return body


def _expected_batch(
    *, gate: str = "T5-G1", response: str = G1_RESPONSE, prior: list[str] | None = None
) -> ExpectedBatchOwnerAuthorization:
    is_g1 = gate == "T5-G1"
    return ExpectedBatchOwnerAuthorization.model_validate(
        {
            "gate": gate,
            "authorization_scope": (
                "staged_to_reviewed" if is_g1 else "reviewed_to_approved_exact"
            ),
            "authorization_declaration": (
                "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry"
                if is_g1
                else "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
            ),
            "expected_outcome": "reviewed" if is_g1 else "approved_exact",
            "batch_ordinal": 1,
            "family_batch_sha256": "4" * 64,
            "catalog_application_manifest_sha256": "5" * 64,
            "exact_external_response": response,
            "exact_external_response_sha256": _response_sha256(response),
            "prior_gate_response_sha256s": prior or [],
        }
    )


def test_builds_exact_twenty_staged_entries_in_seven_output_blind_batches(
    isolated_root: Path,
) -> None:
    packet, owner_markdown, manifest = build_authority_review_preparation(isolated_root)

    assert len(packet.entries) == 20
    assert [entry.ordinal for entry in packet.entries] == list(range(1, 21))
    assert len(packet.family_batches) == 7
    assert sorted(len(batch.entry_ordinals) for batch in packet.family_batches) == [
        2,
        3,
        3,
        3,
        3,
        3,
        3,
    ]
    assert all(
        entry.candidate.catalog_lookup_state.value == "existing_uuid" for entry in packet.entries
    )
    assert all(entry.candidate.status.value == "staged" for entry in packet.entries)
    assert all(len(entry.field_evidence) == 6 for entry in packet.entries)
    assert all(
        entry.explicit_color is None and entry.explicit_edition is None for entry in packet.entries
    )
    assert packet.review_event_count == packet.owner_attestation_count == 0
    assert packet.approved_exact_count == packet.authority_bundle_record_count == 0
    assert packet.resolver_output_consulted is False
    assert packet.network_requests == 0
    assert manifest.entry_count == 20
    assert manifest.evidence_row_count == 120
    assert manifest.approved_exact_count == 0
    assert "awaiting Owner Gate T5-G1" in owner_markdown
    assert "Catalog inclusion is not exact authority" in owner_markdown


def test_resolution_bindings_preserve_all_immutable_parents(isolated_root: Path) -> None:
    packet, _, manifest = build_authority_review_preparation(isolated_root)
    assert packet.car_t4_packet_sha256 == preparation.EXPECTED_PACKET_SHA256
    assert packet.proposal_bundle_sha256 == preparation.EXPECTED_PROPOSAL_BUNDLE_SHA256
    assert packet.catalog_decision_ledger_sha256 == preparation.EXPECTED_LEDGER_SHA256
    assert packet.catalog_application_manifest_sha256 == (
        preparation.EXPECTED_APPLICATION_MANIFEST_SHA256
    )
    assert packet.catalog_sha256 == preparation.EXPECTED_CATALOG_SHA256
    assert manifest.ordered_entry_sha256s == [entry.entry_sha256 for entry in packet.entries]
    assert len({str(entry.candidate.canonical_uuid) for entry in packet.entries}) == 20
    assert len({entry.resolution_binding.applied_canonical_id for entry in packet.entries}) == 20
    assert len({entry.resolution_binding.release_key for entry in packet.entries}) == 20


def test_create_retry_and_two_checks_are_deterministic_and_private(isolated_root: Path) -> None:
    before_catalog = (isolated_root / "data/catalog.json").read_bytes()
    before_car_t4 = {
        path.relative_to(isolated_root).as_posix(): path.read_bytes()
        for path in (
            isolated_root
            / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1"
        ).iterdir()
        if path.is_file()
    }
    assert prepare_authority_review(isolated_root) == "created"
    assert prepare_authority_review(isolated_root) == "unchanged"
    assert prepare_authority_review(isolated_root, check=True) == "unchanged"
    assert prepare_authority_review(isolated_root, check=True) == "unchanged"
    assert stat_mode(isolated_root / preparation.PRIVATE_DIRECTORY) == 0o700
    assert stat_mode(_private_packet(isolated_root)) == 0o600
    assert stat_mode(isolated_root / preparation.OWNER_REVIEW_REFERENCE) == 0o600
    assert (isolated_root / "data/catalog.json").read_bytes() == before_catalog
    assert before_car_t4 == {
        path.relative_to(isolated_root).as_posix(): path.read_bytes()
        for path in (
            isolated_root
            / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1"
        ).iterdir()
        if path.is_file()
    }


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_safe_manifest_has_no_rows_questions_verbatim_or_pii(isolated_root: Path) -> None:
    packet, owner_markdown, _ = build_authority_review_preparation(isolated_root)
    prepare_authority_review(isolated_root)
    public = _public_manifest(isolated_root).read_text(encoding="utf-8")
    private = _private_packet(isolated_root).read_text(encoding="utf-8")
    assert packet.entries[0].candidate.candidate_id in private
    assert packet.entries[0].catalog_record.casting in owner_markdown
    for forbidden in (
        packet.entries[0].candidate.candidate_id,
        packet.entries[0].catalog_record.casting,
        "owner_questions",
        "canonical_uuid",
        "owner_response_verbatim",
        "@example.com",
    ):
        assert forbidden not in public


def test_check_is_read_only_and_missing_or_partial_state_fails(isolated_root: Path) -> None:
    with pytest.raises(AuthorityContractError, match="not materialized"):
        prepare_authority_review(isolated_root, check=True)
    public = _public_manifest(isolated_root)
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text("{}\n", encoding="utf-8")
    with pytest.raises(AuthorityContractError, match="partial"):
        prepare_authority_review(isolated_root)


def test_replay_rejects_unsafe_private_permissions(isolated_root: Path) -> None:
    prepare_authority_review(isolated_root)
    _private_packet(isolated_root).chmod(0o644)
    with pytest.raises(AuthorityContractError, match="permissions"):
        prepare_authority_review(isolated_root, check=True)


def test_missing_ignore_rule_and_symlink_workspace_fail_before_write(
    isolated_root: Path, tmp_path: Path
) -> None:
    ignore = isolated_root / ".gitignore"
    ignore.write_text(
        ignore.read_text(encoding="utf-8").replace(preparation.IGNORE_RULE + "\n", ""),
        encoding="utf-8",
    )
    with pytest.raises(AuthorityContractError, match="ignore rule"):
        prepare_authority_review(isolated_root)
    assert not _private_packet(isolated_root).exists()

    shutil.copyfile(ROOT / ".gitignore", ignore)
    outside = tmp_path / "outside"
    outside.mkdir()
    private = isolated_root / preparation.PRIVATE_DIRECTORY
    private.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AuthorityContractError, match="symlink"):
        prepare_authority_review(isolated_root)
    assert not any(outside.iterdir())


def test_atomic_replace_failure_rolls_back_and_retry_succeeds(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path | str, target: Path | str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replacement failure")
        real_replace(source, target)

    monkeypatch.setattr(preparation.os, "replace", fail_second)
    with pytest.raises(OSError, match="injected"):
        prepare_authority_review(isolated_root)
    assert not _private_packet(isolated_root).exists()
    assert not (isolated_root / preparation.OWNER_REVIEW_REFERENCE).exists()
    assert not _public_manifest(isolated_root).exists()

    monkeypatch.setattr(preparation.os, "replace", real_replace)
    assert prepare_authority_review(isolated_root) == "created"


@pytest.mark.parametrize(
    ("relative", "mutation"),
    [
        (
            "data/catalog.json",
            lambda value: value["products"][120].__setitem__("color", "inferred"),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/catalog-application-manifest.json",
            lambda value: value.__setitem__("output_catalog_sha256", "0" * 64),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposal-review-packet.json",
            lambda value: value["entries"].reverse(),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposals.json",
            lambda value: value.__setitem__("resolver_output_consulted", True),
        ),
    ],
)
def test_stale_catalog_application_packet_or_resolver_inputs_fail_closed(
    isolated_root: Path, relative: str, mutation: Any
) -> None:
    path = isolated_root / relative
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutation(payload)
    _rewrite(path, payload)
    with pytest.raises((AuthorityContractError, ValidationError)):
        build_authority_review_preparation(isolated_root)


def test_packet_contract_rejects_missing_extra_reordered_and_duplicate_identities(
    isolated_root: Path,
) -> None:
    packet = build_authority_review_preparation(isolated_root)[0]
    original = packet.model_dump(mode="json")
    for mutate in (
        lambda value: value["entries"].pop(),
        lambda value: value["entries"].append(copy.deepcopy(value["entries"][0])),
        lambda value: value["family_batches"][0]["entry_ordinals"].reverse(),
    ):
        payload = copy.deepcopy(original)
        mutate(payload)
        with pytest.raises(ValidationError):
            AuthorityReviewPreparationPacket.model_validate(payload)

    for identity in ("applied_canonical_uuid", "applied_canonical_id", "release_key"):
        payload = copy.deepcopy(original)
        payload["entries"][1]["resolution_binding"][identity] = payload["entries"][0][
            "resolution_binding"
        ][identity]
        if identity == "applied_canonical_uuid":
            payload["entries"][1]["candidate"]["canonical_uuid"] = payload["entries"][0][
                "candidate"
            ]["canonical_uuid"]
            payload["entries"][1]["catalog_record"]["canonical_uuid"] = payload["entries"][0][
                "catalog_record"
            ]["canonical_uuid"]
        elif identity == "release_key":
            release_key = payload["entries"][0]["resolution_binding"]["release_key"]
            payload["entries"][1]["candidate"]["proposed_release_key"] = release_key
            payload["entries"][1]["catalog_record"]["release_key"] = release_key
        body = dict(payload["entries"][1])
        body.pop("entry_sha256")
        payload["entries"][1]["entry_sha256"] = content_sha256(body)
        with pytest.raises(ValidationError, match="distinct"):
            AuthorityReviewPreparationPacket.model_validate(payload)


def test_non_null_or_variant_note_evidence_cannot_be_promoted(isolated_root: Path) -> None:
    packet = build_authority_review_preparation(isolated_root)[0]
    payload = packet.entries[0].model_dump(mode="json")
    payload["catalog_record"]["color"] = payload["variant_note_context"] or "3rd Color"
    body = dict(payload)
    body.pop("entry_sha256")
    payload["entry_sha256"] = content_sha256(body)
    with pytest.raises(ValidationError, match="null color"):
        preparation.AuthorityReviewPreparationEntry.model_validate(payload)

    evidence = packet.entries[0].field_evidence[0].model_dump(mode="json")
    evidence.update(
        {
            "field": "color",
            "source_field": "casting_name",
            "catalog_value": "3rd Color",
            "reviewed_value": "3rd Color",
        }
    )
    with pytest.raises(ValidationError):
        VariantFieldEvidence.model_validate(evidence)


def test_missing_or_conflicting_evidence_is_not_preparable(isolated_root: Path) -> None:
    packet = build_authority_review_preparation(isolated_root)[0]
    for mutation in ("missing", "conflicting"):
        payload = packet.entries[0].model_dump(mode="json")
        if mutation == "missing":
            payload["field_evidence"].pop()
        else:
            payload["field_evidence"][0]["agreement"] = "conflicts"
        body = dict(payload)
        body.pop("entry_sha256")
        payload["entry_sha256"] = content_sha256(body)
        with pytest.raises(ValidationError):
            preparation.AuthorityReviewPreparationEntry.model_validate(payload)


def test_future_gate_requires_independent_exact_external_authorization() -> None:
    expected_g1 = _expected_batch()
    valid = _valid_batch_authorization()
    assert validate_batch_owner_authorization(valid, expected=expected_g1)

    rewritten_outcome = _valid_batch_authorization(declared_outcome="held")
    assert BatchOwnerAuthorization.model_validate(rewritten_outcome)
    with pytest.raises(AuthorityContractError, match="external Gate expectation"):
        validate_batch_owner_authorization(rewritten_outcome, expected=expected_g1)

    for response in (
        "Please continue with the next step.",
        "可以繼續下一步。",
        "Please proceed with the review.",
        "請繼續進行審查。",
        "批准將 20 筆已審 catalog proposals 批次套用至 data/catalog.json。",
        G2_RESPONSE,
    ):
        stored = _valid_batch_authorization(
            owner_response_verbatim=response,
            authorized_exact_owner_response=response,
        )
        # The artifact is only a data container; qualification requires the external contract.
        assert BatchOwnerAuthorization.model_validate(stored)
        with pytest.raises(AuthorityContractError, match="external Gate expectation"):
            validate_batch_owner_authorization(stored, expected=expected_g1)


def test_review_only_sentence_cannot_qualify_for_t5_g2() -> None:
    g1_sha = _response_sha256(G1_RESPONSE)
    expected_g2 = _expected_batch(gate="T5-G2", response=G2_RESPONSE, prior=[g1_sha])
    stored = _valid_batch_authorization(
        gate="T5-G2",
        authorization_scope="reviewed_to_approved_exact",
        authorization_declaration=(
            "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
        ),
        declared_outcome="approved_exact",
        owner_response_verbatim=REVIEW_ONLY_RESPONSE,
        authorized_exact_owner_response=REVIEW_ONLY_RESPONSE,
        prior_gate_response_sha256s=[g1_sha],
    )
    assert BatchOwnerAuthorization.model_validate(stored)
    with pytest.raises(AuthorityContractError, match="external Gate expectation"):
        validate_batch_owner_authorization(stored, expected=expected_g2)


def test_identical_verbatim_cannot_be_rehashed_across_gates() -> None:
    g1 = BatchOwnerAuthorization.model_validate(_valid_batch_authorization())
    g1_response_sha = g1.response_verbatim_sha256
    with pytest.raises(ValidationError, match="cannot authorize both Gates"):
        _expected_batch(gate="T5-G2", response=G1_RESPONSE, prior=[g1_response_sha])

    reused = _valid_batch_authorization(
        gate="T5-G2",
        authorization_scope="reviewed_to_approved_exact",
        authorization_declaration=(
            "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
        ),
        declared_outcome="approved_exact",
        owner_response_verbatim=G1_RESPONSE,
        authorized_exact_owner_response=G1_RESPONSE,
        prior_gate_response_sha256s=[g1_response_sha],
    )
    with pytest.raises(ValidationError, match="cannot authorize both Gates"):
        BatchOwnerAuthorization.model_validate(reused)


def test_v2_event_rejects_direct_staged_to_exact_and_false_reviewer(
    isolated_root: Path,
) -> None:
    entry = build_authority_review_preparation(isolated_root)[0].entries[0]
    event: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-review-event-v2",
        "event_id": "event-1",
        "candidate_id": entry.candidate.candidate_id,
        "from_status": "staged",
        "to_status": "approved_exact",
        "packet_sha256": "1" * 64,
        "catalog_version": "catalog-v2",
        "catalog_sha256": "2" * 64,
        "canonical_uuid": str(entry.candidate.canonical_uuid),
        "catalog_record_sha256": entry.catalog_record_sha256,
        "variant_field_evidence": [row.model_dump(mode="json") for row in entry.field_evidence],
        "source_decision_ids": ["fandom-hot-wheels-2025-pilot-r790665-v1"],
        "confirmation_method": "owner_attestation",
        "attestation_sha256": "3" * 64,
        "batch_authorization_sha256": "4" * 64,
        "resolver_output_consulted": False,
        "reviewed_by_role": "project_owner",
        "reviewed_at": "2026-09-30T12:00:00Z",
        "review_reason": "Explicit exact-authority decision.",
        "remediation_note": None,
    }
    event["event_sha256"] = content_sha256(event)
    with pytest.raises(ValidationError, match="invalid authority transition|separate reviewed"):
        AuthorityReviewEventV2.model_validate(event)

    attestation = {
        "schema_version": "pvr-canonical-authority-owner-attestation-v2",
        "candidate_id": entry.candidate.candidate_id,
        "packet_sha256": "1" * 64,
        "catalog_version": "catalog-v2",
        "catalog_sha256": "2" * 64,
        "catalog_record_sha256": entry.catalog_record_sha256,
        "outcome": "reviewed",
        "confirmation_method": "owner_attestation",
        "resolver_output_consulted": False,
        "reviewed_by_role": "second_reviewer",
        "reviewed_at": datetime(2026, 9, 30, 12, tzinfo=UTC),
        "review_reason": "Review complete.",
        "batch_authorization_sha256": "4" * 64,
    }
    with pytest.raises(ValidationError, match="project_owner"):
        OwnerAttestationV2.model_validate(attestation)


def test_public_privacy_guard_rejects_verbatim_and_pii() -> None:
    with pytest.raises(AuthorityContractError, match="private row"):
        preparation._validate_public_privacy(b'{"owner_response_verbatim":"yes"}\n')
    with pytest.raises(AuthorityContractError, match="PII"):
        preparation._validate_public_privacy(b'{"note":"person@example.com"}\n')


def test_cli_runs_from_repository_root_against_isolated_root(isolated_root: Path) -> None:
    created = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(CLI), "--root", str(isolated_root)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    checked = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(CLI), "--root", str(isolated_root), "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert created.stdout.strip() == "created"
    assert checked.stdout.strip() == "unchanged"


def test_real_post_materialized_workspace_check_is_unchanged() -> None:
    assert (ROOT / preparation.PRIVATE_PACKET_REFERENCE).is_file()
    assert (ROOT / preparation.OWNER_REVIEW_REFERENCE).is_file()
    assert (ROOT / preparation.PUBLIC_MANIFEST_REFERENCE).is_file()
    assert prepare_authority_review(ROOT, check=True) == "unchanged"


def test_preparation_does_not_mutate_rhb_t5_or_create_authority_state(isolated_root: Path) -> None:
    evaluation = isolated_root / "data/evaluation"
    before = {
        path.relative_to(isolated_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in evaluation.rglob("*")
        if path.is_file()
    }
    prepare_authority_review(isolated_root)
    after = {
        path.relative_to(isolated_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in evaluation.rglob("*")
        if path.is_file()
    }
    assert after == before
    public = json.loads(_public_manifest(isolated_root).read_text(encoding="utf-8"))
    assert public["review_event_count"] == 0
    assert public["owner_attestation_count"] == 0
    assert public["approved_exact_count"] == 0
    assert public["authority_bundle_record_count"] == 0
    assert public["rhb_t5_authorized"] is False
