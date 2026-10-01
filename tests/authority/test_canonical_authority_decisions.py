from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import product_variant_resolver.canonical_authority_decisions as decisions
from product_variant_resolver.canonical_authority_decisions import (
    ATTESTATION_LEDGER_REFERENCE,
    AUTHORITY_CANDIDATES_REFERENCE,
    AUTHORIZATION_LEDGER_REFERENCE,
    REVIEW_EVENTS_REFERENCE,
    AuthorityCandidateStateFile,
    AuthorityReviewEventFile,
    BatchAuthorizationLedger,
    OwnerAttestationLedger,
    record_t5_g1_batch_review,
)
from product_variant_resolver.canonical_authority_preparation import (
    PRIVATE_DIRECTORY,
    PRIVATE_PACKET_REFERENCE,
)
from product_variant_resolver.canonical_authority_review import AuthorityContractError

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "record_canonical_authority_review_decision.py"
REVIEWED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
SYNTHETIC_OWNER_RESPONSE = (
    "TEST-ONLY T5-G1 Batch 2：審閱測試項目 α、β、γ；三筆皆標記 reviewed，"
    "測試欄位維持 null。此合成句僅測 staged→reviewed 與 approved\\_exact 的 Unicode/escape，"
    "不代表任何真實 owner 決策。"
)
EXPECTED_ORDINALS = {2, 11, 18}
TARGETS = (
    AUTHORIZATION_LEDGER_REFERENCE,
    ATTESTATION_LEDGER_REFERENCE,
    AUTHORITY_CANDIDATES_REFERENCE,
    REVIEW_EVENTS_REFERENCE,
)


@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "specs", root / "specs")
    shutil.copyfile(ROOT / ".gitignore", root / ".gitignore")
    for reference in TARGETS:
        path = root / reference
        path.unlink(missing_ok=True)
    for forbidden in (
        decisions.FORBIDDEN_AUTHORITY_REFERENCE,
        decisions.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE,
    ):
        (root / forbidden).unlink(missing_ok=True)
    return root


def _read(root: Path, reference: Path) -> dict[str, Any]:
    return json.loads((root / reference).read_text(encoding="utf-8"))


def _record(root: Path, **overrides: Any) -> str:
    arguments: dict[str, Any] = {
        "owner_response_verbatim": SYNTHETIC_OWNER_RESPONSE,
        "authorized_exact_owner_response": SYNTHETIC_OWNER_RESPONSE,
        "reviewed_at": REVIEWED_AT,
    }
    arguments.update(overrides)
    return record_t5_g1_batch_review(root, **arguments)


def test_records_only_batch_two_and_replays_idempotently(isolated_root: Path) -> None:
    assert _record(isolated_root) == "created"
    assert _record(isolated_root) == "unchanged"
    assert _record(isolated_root, check=True) == "unchanged"

    authorization = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )
    attestations = OwnerAttestationLedger.model_validate(
        _read(isolated_root, ATTESTATION_LEDGER_REFERENCE)
    )
    candidates = AuthorityCandidateStateFile.model_validate(
        _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)
    )
    events = AuthorityReviewEventFile.model_validate(_read(isolated_root, REVIEW_EVENTS_REFERENCE))

    assert len(authorization.authorizations) == 1
    stored = authorization.authorizations[0]
    assert stored.owner_response_verbatim == SYNTHETIC_OWNER_RESPONSE
    assert stored.batch_ordinal == 2
    assert stored.family_batch_sha256 == (
        "11adcabde3fd8594a8bca8e3a50c0e6b757ed87f714d5c3dd74e3534dad03d39"
    )
    assert len(attestations.attestations) == 3
    assert candidates.status_counts == {"staged": 17, "reviewed": 3, "approved_exact": 0}
    assert {
        candidate.ordinal
        for candidate in candidates.candidates
        if candidate.status.value == "reviewed"
    } == EXPECTED_ORDINALS
    assert events.status_counts == {"reviewed": 3, "approved_exact": 0}
    assert {event.to_status.value for event in events.events} == {"reviewed"}
    assert {event.batch_authorization_sha256 for event in events.events} == {
        stored.authorization_sha256
    }
    assert all(len(event.variant_field_evidence) == 6 for event in events.events)
    assert not candidates.rhb_t5_authorized
    assert not events.rhb_t5_authorized


def test_verbatim_is_private_once_and_no_entry_utterances_are_fabricated(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    authorization_raw = (isolated_root / AUTHORIZATION_LEDGER_REFERENCE).read_text(encoding="utf-8")
    attestation_raw = (isolated_root / ATTESTATION_LEDGER_REFERENCE).read_text(encoding="utf-8")
    public_raw = b"".join(
        (isolated_root / reference).read_bytes()
        for reference in (AUTHORITY_CANDIDATES_REFERENCE, REVIEW_EVENTS_REFERENCE)
    )
    # One authorization intentionally stores both the received and independently authorized
    # exact fields. JSON escapes the literal backslash, while decoding restores the exact bytes.
    authorization_payload = json.loads(authorization_raw)["authorizations"][0]
    assert authorization_payload["owner_response_verbatim"] == SYNTHETIC_OWNER_RESPONSE
    assert authorization_payload["authorized_exact_owner_response"] == SYNTHETIC_OWNER_RESPONSE
    assert SYNTHETIC_OWNER_RESPONSE not in attestation_raw
    assert SYNTHETIC_OWNER_RESPONSE.encode("utf-8") not in public_raw
    assert b"owner_response_verbatim" not in public_raw
    assert b"authorized_exact_owner_response" not in public_raw


@pytest.mark.parametrize(
    ("owner_response", "expected_response"),
    [
        ("Please continue with the next step.", SYNTHETIC_OWNER_RESPONSE),
        ("可以繼續下一步。", SYNTHETIC_OWNER_RESPONSE),
        ("I authorize catalog application.", SYNTHETIC_OWNER_RESPONSE),
        ("I approve exact authority for Batch 2.", SYNTHETIC_OWNER_RESPONSE),
        (
            SYNTHETIC_OWNER_RESPONSE.replace("Batch 2", "Batch Two"),
            SYNTHETIC_OWNER_RESPONSE,
        ),
    ],
)
def test_requires_the_independently_supplied_exact_g1_response(
    isolated_root: Path,
    owner_response: str,
    expected_response: str,
) -> None:
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record(
            isolated_root,
            owner_response_verbatim=owner_response,
            authorized_exact_owner_response=expected_response,
        )
    assert not any((isolated_root / reference).exists() for reference in TARGETS)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"batch_ordinal": 1}, "Batch 2"),
        ({"expected_outcome": "approved_exact"}, "staged to reviewed"),
        ({"expected_outcome": "held"}, "staged to reviewed"),
    ],
)
def test_rejects_wrong_batch_or_direct_exact_outcome(
    isolated_root: Path,
    overrides: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(AuthorityContractError, match=message):
        _record(isolated_root, **overrides)


def test_stale_preparation_binding_fails_before_decision_write(isolated_root: Path) -> None:
    packet_path = isolated_root / PRIVATE_PACKET_REFERENCE
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["entries"][1]["catalog_record_sha256"] = "0" * 64
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    with pytest.raises((AuthorityContractError, ValueError)):
        _record(isolated_root)
    assert not any((isolated_root / reference).exists() for reference in TARGETS)


def test_conflicting_retry_and_partial_state_fail_closed(isolated_root: Path) -> None:
    _record(isolated_root)
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record(
            isolated_root,
            owner_response_verbatim=SYNTHETIC_OWNER_RESPONSE + " extra",
        )

    (isolated_root / REVIEW_EVENTS_REFERENCE).unlink()
    with pytest.raises(AuthorityContractError, match="partial"):
        _record(isolated_root)


def test_atomic_failure_removes_every_decision_output_and_retry_succeeds(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = decisions.os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        real_replace(source, target)

    monkeypatch.setattr(decisions.os, "replace", fail_second)
    with pytest.raises(OSError, match="injected"):
        _record(isolated_root)
    assert not any((isolated_root / reference).exists() for reference in TARGETS)

    monkeypatch.setattr(decisions.os, "replace", real_replace)
    assert _record(isolated_root) == "created"


def test_symlink_and_unsafe_private_permissions_are_rejected(
    isolated_root: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    target = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    target.symlink_to(outside)
    with pytest.raises(AuthorityContractError, match="symbolic|symlink"):
        _record(isolated_root)
    target.unlink()

    _record(isolated_root)
    private_dir = isolated_root / PRIVATE_DIRECTORY
    assert stat.S_IMODE(private_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE((isolated_root / AUTHORIZATION_LEDGER_REFERENCE).stat().st_mode) == 0o600
    os.chmod(private_dir, 0o755)
    with pytest.raises(AuthorityContractError, match="permissions"):
        _record(isolated_root)


def test_cli_records_and_checks_an_isolated_root(isolated_root: Path) -> None:
    command = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--owner-response",
        SYNTHETIC_OWNER_RESPONSE,
        "--authorized-exact-owner-response",
        SYNTHETIC_OWNER_RESPONSE,
        "--reviewed-at",
        "2026-10-01T12:00:00Z",
    ]
    created = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert created.returncode == 0, created.stderr
    assert created.stdout.strip() == "created"

    checked = subprocess.run(
        [*command, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout.strip() == "unchanged"


def test_catalog_and_preparation_inputs_are_not_mutated(isolated_root: Path) -> None:
    protected = [
        Path("data/catalog.json"),
        Path("data/manifest.json"),
        PRIVATE_PACKET_REFERENCE,
        Path(
            "data/authority-review/canonical-authority-review-v1/"
            "authority-review-packet-manifest.json"
        ),
    ]
    before = {reference: (isolated_root / reference).read_bytes() for reference in protected}
    _record(isolated_root)
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in protected
    } == before
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_REFERENCE).exists()
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE).exists()
