from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

import product_variant_resolver.canonical_authority_exact_decisions as exact
from product_variant_resolver.canonical_authority_decisions import (
    ATTESTATION_LEDGER_REFERENCE,
    AUTHORITY_CANDIDATES_REFERENCE,
    AUTHORIZATION_LEDGER_REFERENCE,
    REVIEW_EVENTS_REFERENCE,
    AuthorityCandidateStateFile,
    AuthorityReviewEventFile,
    BatchAuthorizationLedger,
    record_t5_g1_batch_review,
)
from product_variant_resolver.canonical_authority_exact_decisions import (
    EXACT_ATTESTATION_LEDGER_REFERENCE,
    EXACT_AUTHORIZATION_LEDGER_REFERENCE,
    ExactBatchAuthorizationLedger,
    ExactOwnerAttestationLedger,
    record_t5_g2_batch_exact,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "record_canonical_exact_authority_decision.py"
EXACT_RESPONSE = (
    "TEST-ONLY T5-G2 Batch 1：明確批准測試項目 σ、τ、υ 為 approved_exact；"
    "測試欄位維持 null，且不授權後續 Gate。"
)
G1_RESPONSES = {
    ordinal: (
        f"TEST-ONLY T5-G1 Batch {ordinal}：明確審閱本批測試項目為 reviewed；"
        "測試欄位維持 null，且不代表真實 owner 決策。"
    )
    for ordinal in range(1, 8)
}
TARGETS = (
    EXACT_AUTHORIZATION_LEDGER_REFERENCE,
    EXACT_ATTESTATION_LEDGER_REFERENCE,
    AUTHORITY_CANDIDATES_REFERENCE,
    REVIEW_EVENTS_REFERENCE,
)


def _read(root: Path, reference: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((root / reference).read_text(encoding="utf-8")),
    )


@pytest.fixture(scope="module")
def g1_baseline(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("exact-g1-baseline") / "repo"
    root.mkdir()
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "specs", root / "specs")
    shutil.copyfile(ROOT / ".gitignore", root / ".gitignore")
    for reference in (
        AUTHORIZATION_LEDGER_REFERENCE,
        ATTESTATION_LEDGER_REFERENCE,
        AUTHORITY_CANDIDATES_REFERENCE,
        REVIEW_EVENTS_REFERENCE,
        EXACT_AUTHORIZATION_LEDGER_REFERENCE,
        EXACT_ATTESTATION_LEDGER_REFERENCE,
    ):
        (root / reference).unlink(missing_ok=True)
    base_time = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
    for offset, batch_ordinal in enumerate((2, 3, 4, 5, 6, 7, 1)):
        response = G1_RESPONSES[batch_ordinal]
        assert (
            record_t5_g1_batch_review(
                root,
                owner_response_verbatim=response,
                authorized_exact_owner_response=response,
                batch_ordinal=batch_ordinal,
                reviewed_at=base_time + timedelta(minutes=offset),
            )
            == "created"
        )
    return root


@pytest.fixture()
def isolated_root(tmp_path: Path, g1_baseline: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(g1_baseline, root)
    return root


def _record(root: Path, **overrides: Any) -> str:
    arguments: dict[str, Any] = {
        "owner_response_verbatim": EXACT_RESPONSE,
        "authorized_exact_owner_response": EXACT_RESPONSE,
        "reviewed_at": datetime(2026, 10, 2, 13, 0, tzinfo=UTC),
    }
    arguments.update(overrides)
    return record_t5_g2_batch_exact(root, **arguments)


def test_records_exact_batch_one_and_replays_without_rewriting_g1(
    isolated_root: Path,
) -> None:
    before_candidates = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    before_events = _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root) == "unchanged"
    assert _record(isolated_root, check=True) == "unchanged"
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == first

    authorizations = ExactBatchAuthorizationLedger.model_validate(
        _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)
    )
    attestations = ExactOwnerAttestationLedger.model_validate(
        _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)
    )
    candidates = AuthorityCandidateStateFile.model_validate(
        _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)
    )
    events = AuthorityReviewEventFile.model_validate(_read(isolated_root, REVIEW_EVENTS_REFERENCE))

    assert len(authorizations.authorizations) == 1
    authorization = authorizations.authorizations[0]
    assert authorization.gate == "T5-G2"
    assert authorization.declared_outcome.value == "approved_exact"
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 1)
    assert authorization.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert authorization.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 3
    assert candidates.status_counts == {"staged": 0, "reviewed": 17, "approved_exact": 3}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == {1, 10, 16}
    assert events.batch_authorization_count == 8
    assert events.owner_attestation_count == 23
    assert events.review_event_count == 23
    assert events.status_counts == {"reviewed": 17, "approved_exact": 3}
    assert [
        item.model_dump(mode="json")
        for item in events.events
        if item.event_id.startswith("car-t5-g1-")
    ] == before_events
    before_reviewed = {item["candidate_id"]: item for item in before_candidates}
    after = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_reviewed.items():
        if previous["ordinal"] not in {1, 10, 16}:
            assert after[candidate_id].model_dump(mode="json") == previous
    assert not candidates.rhb_t5_authorized and not events.rhb_t5_authorized
    assert not (isolated_root / exact.FORBIDDEN_AUTHORITY_REFERENCE).exists()
    assert not (isolated_root / exact.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE).exists()

    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    assert EXACT_RESPONSE.encode("utf-8") not in public
    for response in G1_RESPONSES.values():
        assert response.encode("utf-8") not in public


def test_requires_fresh_exact_response_distinct_from_g1(isolated_root: Path) -> None:
    response = G1_RESPONSES[1]
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]}
    with pytest.raises((AuthorityContractError, ValueError), match="response|Gate"):
        record_t5_g2_batch_exact(
            isolated_root,
            owner_response_verbatim=response,
            authorized_exact_owner_response=response,
            reviewed_at=datetime(2026, 10, 2, 13, 0, tzinfo=UTC),
        )
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]
    } == before
    assert not (isolated_root / EXACT_AUTHORIZATION_LEDGER_REFERENCE).exists()


def test_requires_independently_supplied_exact_response(isolated_root: Path) -> None:
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record(isolated_root, owner_response_verbatim="TEST-ONLY generic continuation")
    assert not (isolated_root / EXACT_AUTHORIZATION_LEDGER_REFERENCE).exists()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"batch_ordinal": 2}, "Batch 1"),
        ({"expected_outcome": "reviewed"}, "approved_exact"),
        ({"expected_outcome": "held"}, "approved_exact"),
    ],
)
def test_rejects_unsupported_batch_or_non_exact_outcome(
    isolated_root: Path, overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(AuthorityContractError, match=message):
        _record(isolated_root, **overrides)


def test_check_requires_materialized_exact_state(isolated_root: Path) -> None:
    with pytest.raises(AuthorityContractError, match="not materialized"):
        _record(isolated_root, check=True)


def test_tampered_candidate_link_fails_without_writing(isolated_root: Path) -> None:
    path = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    payload = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)
    payload["candidates"][0]["latest_event_id"] = "tampered-test-only-event"
    payload["state_sha256"] = content_sha256(
        {key: value for key, value in payload.items() if key != "state_sha256"}
    )
    path.write_bytes(stable_json_bytes(payload))
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]}

    with pytest.raises(AuthorityContractError, match="latest review event"):
        _record(isolated_root)

    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]
    } == before
    assert not (isolated_root / EXACT_AUTHORIZATION_LEDGER_REFERENCE).exists()


def test_partial_exact_private_state_is_rejected(isolated_root: Path) -> None:
    assert _record(isolated_root) == "created"
    (isolated_root / EXACT_ATTESTATION_LEDGER_REFERENCE).unlink()
    with pytest.raises(AuthorityContractError, match="partial"):
        _record(isolated_root)


def test_atomic_failure_restores_g1_public_bytes(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]}
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected exact append failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected exact"):
        _record(isolated_root)
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]
    } == before
    assert not (isolated_root / EXACT_AUTHORIZATION_LEDGER_REFERENCE).exists()
    assert not (isolated_root / EXACT_ATTESTATION_LEDGER_REFERENCE).exists()

    monkeypatch.setattr(os, "replace", real_replace)
    assert _record(isolated_root) == "created"


def test_forbidden_bundle_blocks_exact_recording(isolated_root: Path) -> None:
    forbidden = isolated_root / exact.FORBIDDEN_AUTHORITY_REFERENCE
    forbidden.write_text("{}\n", encoding="utf-8")
    with pytest.raises(AuthorityContractError, match="frozen authority bundle"):
        _record(isolated_root)


def test_cli_records_and_checks_exact_batch_one(isolated_root: Path) -> None:
    command = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--owner-response",
        EXACT_RESPONSE,
        "--authorized-exact-owner-response",
        EXACT_RESPONSE,
        "--reviewed-at",
        "2026-10-02T13:00:00Z",
    ]
    created = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert created.returncode == 0, created.stderr
    assert created.stdout.strip() == "created"
    checked = subprocess.run(
        [*command, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout.strip() == "unchanged"
