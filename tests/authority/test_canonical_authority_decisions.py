from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

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
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "record_canonical_authority_review_decision.py"
REVIEWED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
SYNTHETIC_OWNER_RESPONSE = (
    "TEST-ONLY T5-G1 Batch 2：審閱測試項目 α、β、γ；三筆皆標記 reviewed，"
    "測試欄位維持 null。此合成句僅測 staged→reviewed 與 approved\\_exact 的 Unicode/escape，"
    "不代表任何真實 owner 決策。"
)
SYNTHETIC_BATCH_THREE_RESPONSE = (
    "TEST-ONLY T5-G1 Batch 3：審閱測試項目 δ、ε、ζ；三筆皆標記 reviewed，"
    "測試欄位維持 null。此合成句只測第二個 staged→reviewed 批次，"
    "不代表任何真實 owner 決策。"
)
SYNTHETIC_BATCH_FOUR_RESPONSE = (
    "TEST-ONLY T5-G1 Batch 4：審閱測試項目 η、θ、ι；三筆皆標記 reviewed，"
    "測試欄位維持 null。此合成句只測第三個 staged→reviewed 批次，"
    "不代表任何真實 owner 決策。"
)
SYNTHETIC_BATCH_FIVE_RESPONSE = (
    "TEST-ONLY T5-G1 Batch 5：審閱測試項目 κ、λ、μ；三筆皆標記 reviewed，"
    "測試欄位維持 null。此合成句只測第四個 staged→reviewed 批次，"
    "不代表任何真實 owner 決策。"
)
EXPECTED_ORDINALS = {2, 11, 18}
EXPECTED_BATCH_THREE_ORDINALS = {3, 8, 14}
EXPECTED_BATCH_FOUR_ORDINALS = {4, 13, 20}
EXPECTED_BATCH_FIVE_ORDINALS = {5, 7, 17}
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
    return cast(
        dict[str, Any],
        json.loads((root / reference).read_text(encoding="utf-8")),
    )


def _record(root: Path, **overrides: Any) -> str:
    arguments: dict[str, Any] = {
        "owner_response_verbatim": SYNTHETIC_OWNER_RESPONSE,
        "authorized_exact_owner_response": SYNTHETIC_OWNER_RESPONSE,
        "reviewed_at": REVIEWED_AT,
    }
    arguments.update(overrides)
    return record_t5_g1_batch_review(root, **arguments)


def _record_batch_three(root: Path, **overrides: Any) -> str:
    arguments: dict[str, Any] = {
        "owner_response_verbatim": SYNTHETIC_BATCH_THREE_RESPONSE,
        "authorized_exact_owner_response": SYNTHETIC_BATCH_THREE_RESPONSE,
        "reviewed_at": datetime(2026, 10, 1, 12, 1, tzinfo=UTC),
        "batch_ordinal": 3,
    }
    arguments.update(overrides)
    return record_t5_g1_batch_review(root, **arguments)


def _record_batch_four(root: Path, **overrides: Any) -> str:
    arguments: dict[str, Any] = {
        "owner_response_verbatim": SYNTHETIC_BATCH_FOUR_RESPONSE,
        "authorized_exact_owner_response": SYNTHETIC_BATCH_FOUR_RESPONSE,
        "reviewed_at": datetime(2026, 10, 1, 12, 2, tzinfo=UTC),
        "batch_ordinal": 4,
    }
    arguments.update(overrides)
    return record_t5_g1_batch_review(root, **arguments)


def _record_batch_five(root: Path, **overrides: Any) -> str:
    arguments: dict[str, Any] = {
        "owner_response_verbatim": SYNTHETIC_BATCH_FIVE_RESPONSE,
        "authorized_exact_owner_response": SYNTHETIC_BATCH_FIVE_RESPONSE,
        "reviewed_at": datetime(2026, 10, 1, 12, 3, tzinfo=UTC),
        "batch_ordinal": 5,
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


def test_appends_batch_three_to_batch_two_and_replays_idempotently(
    isolated_root: Path,
) -> None:
    assert _record(isolated_root) == "created"
    assert _record_batch_three(isolated_root) == "created"
    assert _record_batch_three(isolated_root) == "unchanged"
    assert _record_batch_three(isolated_root, check=True) == "unchanged"

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

    assert [item.batch_ordinal for item in authorization.authorizations] == [2, 3]
    assert len({item.authorization_sha256 for item in authorization.authorizations}) == 2
    assert attestations.batch_authorization_sha256s == [
        item.authorization_sha256 for item in authorization.authorizations
    ]
    assert len(attestations.attestations) == 6
    assert candidates.status_counts == {"staged": 14, "reviewed": 6, "approved_exact": 0}
    assert {
        candidate.ordinal
        for candidate in candidates.candidates
        if candidate.status.value == "reviewed"
    } == EXPECTED_ORDINALS | EXPECTED_BATCH_THREE_ORDINALS
    assert events.batch_authorization_count == 2
    assert events.owner_attestation_count == 6
    assert events.review_event_count == 6
    assert events.status_counts == {"reviewed": 6, "approved_exact": 0}
    assert {event.to_status.value for event in events.events} == {"reviewed"}
    assert not candidates.rhb_t5_authorized
    assert not events.rhb_t5_authorized
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_REFERENCE).exists()
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE).exists()

    public_raw = b"".join(
        (isolated_root / reference).read_bytes()
        for reference in (AUTHORITY_CANDIDATES_REFERENCE, REVIEW_EVENTS_REFERENCE)
    )
    assert SYNTHETIC_OWNER_RESPONSE.encode("utf-8") not in public_raw
    assert SYNTHETIC_BATCH_THREE_RESPONSE.encode("utf-8") not in public_raw


def test_appends_batch_four_to_complete_prefix_without_rewriting_prior_objects(
    isolated_root: Path,
) -> None:
    assert _record(isolated_root) == "created"
    assert _record_batch_three(isolated_root) == "created"
    before_authorizations = _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)["authorizations"]
    before_attestations = _read(isolated_root, ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]

    assert _record_batch_four(isolated_root) == "created"
    first_materialization = {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS
    }
    assert _record_batch_four(isolated_root) == "unchanged"
    assert _record_batch_four(isolated_root, check=True) == "unchanged"
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS
    } == first_materialization

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

    assert [item.batch_ordinal for item in authorization.authorizations] == [2, 3, 4]
    assert [item.model_dump(mode="json") for item in authorization.authorizations[:2]] == (
        before_authorizations
    )
    assert len(attestations.attestations) == 9
    attestation_by_candidate = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    event_by_candidate = {item.candidate_id: item.model_dump(mode="json") for item in events.events}
    assert {
        item["candidate_id"]: attestation_by_candidate[item["candidate_id"]]
        for item in before_attestations
    } == {item["candidate_id"]: item for item in before_attestations}
    assert {
        item["candidate_id"]: event_by_candidate[item["candidate_id"]] for item in before_events
    } == {item["candidate_id"]: item for item in before_events}
    assert candidates.status_counts == {"staged": 11, "reviewed": 9, "approved_exact": 0}
    assert {
        candidate.ordinal
        for candidate in candidates.candidates
        if candidate.status.value == "reviewed"
    } == EXPECTED_ORDINALS | EXPECTED_BATCH_THREE_ORDINALS | EXPECTED_BATCH_FOUR_ORDINALS
    assert events.batch_authorization_count == 3
    assert events.owner_attestation_count == 9
    assert events.review_event_count == 9
    assert events.status_counts == {"reviewed": 9, "approved_exact": 0}
    assert {event.to_status.value for event in events.events} == {"reviewed"}
    assert not candidates.rhb_t5_authorized
    assert not events.rhb_t5_authorized
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_REFERENCE).exists()
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE).exists()

    public_raw = b"".join(
        (isolated_root / reference).read_bytes()
        for reference in (AUTHORITY_CANDIDATES_REFERENCE, REVIEW_EVENTS_REFERENCE)
    )
    for private_response in (
        SYNTHETIC_OWNER_RESPONSE,
        SYNTHETIC_BATCH_THREE_RESPONSE,
        SYNTHETIC_BATCH_FOUR_RESPONSE,
    ):
        assert private_response.encode("utf-8") not in public_raw


def test_appends_batch_five_to_complete_prefix_without_rewriting_prior_objects(
    isolated_root: Path,
) -> None:
    assert _record(isolated_root) == "created"
    assert _record_batch_three(isolated_root) == "created"
    assert _record_batch_four(isolated_root) == "created"
    before_authorizations = _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)["authorizations"]
    before_attestations = _read(isolated_root, ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]

    assert _record_batch_five(isolated_root) == "created"
    first_materialization = {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS
    }
    assert _record_batch_five(isolated_root) == "unchanged"
    assert _record_batch_five(isolated_root, check=True) == "unchanged"
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS
    } == first_materialization

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

    assert [item.batch_ordinal for item in authorization.authorizations] == [2, 3, 4, 5]
    assert [item.model_dump(mode="json") for item in authorization.authorizations[:3]] == (
        before_authorizations
    )
    assert len(attestations.attestations) == 12
    attestation_by_candidate = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    event_by_candidate = {item.candidate_id: item.model_dump(mode="json") for item in events.events}
    assert {
        item["candidate_id"]: attestation_by_candidate[item["candidate_id"]]
        for item in before_attestations
    } == {item["candidate_id"]: item for item in before_attestations}
    assert {
        item["candidate_id"]: event_by_candidate[item["candidate_id"]] for item in before_events
    } == {item["candidate_id"]: item for item in before_events}
    assert candidates.status_counts == {"staged": 8, "reviewed": 12, "approved_exact": 0}
    assert {
        candidate.ordinal
        for candidate in candidates.candidates
        if candidate.status.value == "reviewed"
    } == (
        EXPECTED_ORDINALS
        | EXPECTED_BATCH_THREE_ORDINALS
        | EXPECTED_BATCH_FOUR_ORDINALS
        | EXPECTED_BATCH_FIVE_ORDINALS
    )
    assert events.batch_authorization_count == 4
    assert events.owner_attestation_count == 12
    assert events.review_event_count == 12
    assert events.status_counts == {"reviewed": 12, "approved_exact": 0}
    assert {event.to_status.value for event in events.events} == {"reviewed"}
    assert not candidates.rhb_t5_authorized
    assert not events.rhb_t5_authorized
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_REFERENCE).exists()
    assert not (isolated_root / decisions.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE).exists()

    public_raw = b"".join(
        (isolated_root / reference).read_bytes()
        for reference in (AUTHORITY_CANDIDATES_REFERENCE, REVIEW_EVENTS_REFERENCE)
    )
    for private_response in (
        SYNTHETIC_OWNER_RESPONSE,
        SYNTHETIC_BATCH_THREE_RESPONSE,
        SYNTHETIC_BATCH_FOUR_RESPONSE,
        SYNTHETIC_BATCH_FIVE_RESPONSE,
    ):
        assert private_response.encode("utf-8") not in public_raw


def test_batch_three_requires_complete_batch_two_state(isolated_root: Path) -> None:
    with pytest.raises(AuthorityContractError, match="requires the complete Batch 2"):
        _record_batch_three(isolated_root)
    assert not any((isolated_root / reference).exists() for reference in TARGETS)


@pytest.mark.parametrize("prefix_length", [0, 1])
def test_batch_four_requires_complete_batch_two_and_three_prefix(
    isolated_root: Path, prefix_length: int
) -> None:
    if prefix_length == 1:
        _record(isolated_root)
    before = {
        reference: (isolated_root / reference).read_bytes()
        for reference in TARGETS
        if (isolated_root / reference).exists()
    }

    with pytest.raises(AuthorityContractError, match="requires the complete Batch 2 and Batch 3"):
        _record_batch_four(isolated_root)

    assert {
        reference: (isolated_root / reference).read_bytes()
        for reference in TARGETS
        if (isolated_root / reference).exists()
    } == before


@pytest.mark.parametrize("prefix_length", [0, 1, 2])
def test_batch_five_requires_complete_batch_two_three_and_four_prefix(
    isolated_root: Path, prefix_length: int
) -> None:
    if prefix_length >= 1:
        _record(isolated_root)
    if prefix_length >= 2:
        _record_batch_three(isolated_root)
    before = {
        reference: (isolated_root / reference).read_bytes()
        for reference in TARGETS
        if (isolated_root / reference).exists()
    }

    with pytest.raises(
        AuthorityContractError,
        match="requires the complete Batch 2 and Batch 3 and Batch 4",
    ):
        _record_batch_five(isolated_root)

    assert {
        reference: (isolated_root / reference).read_bytes()
        for reference in TARGETS
        if (isolated_root / reference).exists()
    } == before


def test_appending_batch_three_migrates_the_original_private_ledger_shape(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    path = isolated_root / ATTESTATION_LEDGER_REFERENCE
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "batch_authorization_sha256" in payload
    assert "batch_authorization_sha256s" not in payload

    assert _record_batch_three(isolated_root) == "created"
    migrated = _read(isolated_root, ATTESTATION_LEDGER_REFERENCE)
    assert "batch_authorization_sha256" not in migrated
    assert len(migrated["batch_authorization_sha256s"]) == 2


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


def test_append_rejects_a_prior_owner_response_leaked_into_public_events(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    event_path = isolated_root / REVIEW_EVENTS_REFERENCE
    candidate_path = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    event_payload = _read(isolated_root, REVIEW_EVENTS_REFERENCE)
    candidate_payload = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)

    leaked_event = event_payload["events"][0]
    leaked_event["review_reason"] = SYNTHETIC_OWNER_RESPONSE
    leaked_event["event_sha256"] = content_sha256(
        {key: value for key, value in leaked_event.items() if key != "event_sha256"}
    )
    event_payload["cumulative_event_sha256"] = content_sha256(
        [event["event_sha256"] for event in event_payload["events"]]
    )
    event_payload["ledger_sha256"] = content_sha256(
        {key: value for key, value in event_payload.items() if key != "ledger_sha256"}
    )
    candidate = next(
        item
        for item in candidate_payload["candidates"]
        if item["candidate_id"] == leaked_event["candidate_id"]
    )
    candidate["latest_event_sha256"] = leaked_event["event_sha256"]
    candidate_payload["state_sha256"] = content_sha256(
        {key: value for key, value in candidate_payload.items() if key != "state_sha256"}
    )
    event_path.write_bytes(stable_json_bytes(event_payload))
    candidate_path.write_bytes(stable_json_bytes(candidate_payload))

    with pytest.raises(AuthorityContractError, match="public.*owner verbatim"):
        _record_batch_three(isolated_root)


def test_batch_four_rejects_prior_private_response_leaked_into_public_events(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    event_path = isolated_root / REVIEW_EVENTS_REFERENCE
    candidate_path = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    event_payload = _read(isolated_root, REVIEW_EVENTS_REFERENCE)
    candidate_payload = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)

    leaked_event = event_payload["events"][3]
    leaked_event["review_reason"] = SYNTHETIC_BATCH_THREE_RESPONSE
    leaked_event["event_sha256"] = content_sha256(
        {key: value for key, value in leaked_event.items() if key != "event_sha256"}
    )
    event_payload["cumulative_event_sha256"] = content_sha256(
        [event["event_sha256"] for event in event_payload["events"]]
    )
    event_payload["ledger_sha256"] = content_sha256(
        {key: value for key, value in event_payload.items() if key != "ledger_sha256"}
    )
    candidate = next(
        item
        for item in candidate_payload["candidates"]
        if item["candidate_id"] == leaked_event["candidate_id"]
    )
    candidate["latest_event_sha256"] = leaked_event["event_sha256"]
    candidate_payload["state_sha256"] = content_sha256(
        {key: value for key, value in candidate_payload.items() if key != "state_sha256"}
    )
    event_path.write_bytes(stable_json_bytes(event_payload))
    candidate_path.write_bytes(stable_json_bytes(candidate_payload))

    with pytest.raises(AuthorityContractError, match="public.*owner verbatim"):
        _record_batch_four(isolated_root)


def test_batch_five_rejects_prior_private_response_leaked_into_public_events(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    _record_batch_four(isolated_root)
    event_path = isolated_root / REVIEW_EVENTS_REFERENCE
    candidate_path = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    event_payload = _read(isolated_root, REVIEW_EVENTS_REFERENCE)
    candidate_payload = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)

    leaked_event = event_payload["events"][6]
    leaked_event["review_reason"] = SYNTHETIC_BATCH_FOUR_RESPONSE
    leaked_event["event_sha256"] = content_sha256(
        {key: value for key, value in leaked_event.items() if key != "event_sha256"}
    )
    event_payload["cumulative_event_sha256"] = content_sha256(
        [event["event_sha256"] for event in event_payload["events"]]
    )
    event_payload["ledger_sha256"] = content_sha256(
        {key: value for key, value in event_payload.items() if key != "ledger_sha256"}
    )
    candidate = next(
        item
        for item in candidate_payload["candidates"]
        if item["candidate_id"] == leaked_event["candidate_id"]
    )
    candidate["latest_event_sha256"] = leaked_event["event_sha256"]
    candidate_payload["state_sha256"] = content_sha256(
        {key: value for key, value in candidate_payload.items() if key != "state_sha256"}
    )
    event_path.write_bytes(stable_json_bytes(event_payload))
    candidate_path.write_bytes(stable_json_bytes(candidate_payload))

    with pytest.raises(AuthorityContractError, match="public.*owner verbatim"):
        _record_batch_five(isolated_root)


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


def test_conflicting_batch_three_retry_preserves_cumulative_state(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record_batch_three(
            isolated_root,
            owner_response_verbatim=SYNTHETIC_BATCH_THREE_RESPONSE + " extra",
        )
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_conflicting_batch_four_retry_preserves_cumulative_state(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    _record_batch_four(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record_batch_four(
            isolated_root,
            owner_response_verbatim=SYNTHETIC_BATCH_FOUR_RESPONSE + " extra",
        )
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_batch_five_wrong_response_and_conflicting_retry_preserve_cumulative_state(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    _record_batch_four(isolated_root)
    before_prefix = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record_batch_five(
            isolated_root,
            owner_response_verbatim="TEST-ONLY wrong Batch 5 response",
        )
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS
    } == before_prefix

    _record_batch_five(isolated_root)
    before_complete = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record_batch_five(
            isolated_root,
            owner_response_verbatim=SYNTHETIC_BATCH_FIVE_RESPONSE + " extra",
        )
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS
    } == before_complete


def test_batch_four_rejects_direct_exact_and_partial_state(isolated_root: Path) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="staged to reviewed"):
        _record_batch_four(isolated_root, expected_outcome="approved_exact")
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before

    (isolated_root / REVIEW_EVENTS_REFERENCE).unlink()
    with pytest.raises(AuthorityContractError, match="partial"):
        _record_batch_four(isolated_root)


def test_batch_five_rejects_direct_exact_and_partial_state(isolated_root: Path) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    _record_batch_four(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="staged to reviewed"):
        _record_batch_five(isolated_root, expected_outcome="approved_exact")
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before

    (isolated_root / REVIEW_EVENTS_REFERENCE).unlink()
    with pytest.raises(AuthorityContractError, match="partial"):
        _record_batch_five(isolated_root)


def test_batch_four_rejects_tampered_prefix_state_without_writing(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    candidate_path = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    candidate_payload = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)
    reviewed_candidate = next(
        item for item in candidate_payload["candidates"] if item["status"] == "reviewed"
    )
    reviewed_candidate["latest_event_id"] = "tampered-test-only-event"
    candidate_payload["state_sha256"] = content_sha256(
        {key: value for key, value in candidate_payload.items() if key != "state_sha256"}
    )
    candidate_path.write_bytes(stable_json_bytes(candidate_payload))
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}

    with pytest.raises(AuthorityContractError, match="candidate state differs"):
        _record_batch_four(isolated_root)

    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_batch_five_rejects_tampered_prefix_state_without_writing(
    isolated_root: Path,
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    _record_batch_four(isolated_root)
    candidate_path = isolated_root / AUTHORITY_CANDIDATES_REFERENCE
    candidate_payload = _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)
    reviewed_candidate = next(
        item for item in candidate_payload["candidates"] if item["status"] == "reviewed"
    )
    reviewed_candidate["latest_event_id"] = "tampered-test-only-event"
    candidate_payload["state_sha256"] = content_sha256(
        {key: value for key, value in candidate_payload.items() if key != "state_sha256"}
    )
    candidate_path.write_bytes(stable_json_bytes(candidate_payload))
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}

    with pytest.raises(AuthorityContractError, match="candidate state differs"):
        _record_batch_five(isolated_root)

    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_atomic_failure_removes_every_decision_output_and_retry_succeeds(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected"):
        _record(isolated_root)
    assert not any((isolated_root / reference).exists() for reference in TARGETS)

    monkeypatch.setattr(os, "replace", real_replace)
    assert _record(isolated_root) == "created"


def test_atomic_append_failure_restores_batch_two_bytes(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _record(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected append replace failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected append"):
        _record_batch_three(isolated_root)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before

    monkeypatch.setattr(os, "replace", real_replace)
    assert _record_batch_three(isolated_root) == "created"


def test_atomic_batch_four_append_failure_restores_complete_prefix_bytes(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected Batch 4 append replace failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected Batch 4"):
        _record_batch_four(isolated_root)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before

    monkeypatch.setattr(os, "replace", real_replace)
    assert _record_batch_four(isolated_root) == "created"


def test_atomic_batch_five_append_failure_restores_complete_prefix_bytes(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _record(isolated_root)
    _record_batch_three(isolated_root)
    _record_batch_four(isolated_root)
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected Batch 5 append replace failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected Batch 5"):
        _record_batch_five(isolated_root)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before

    monkeypatch.setattr(os, "replace", real_replace)
    assert _record_batch_five(isolated_root) == "created"


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
    assert stat.S_IMODE((isolated_root / AUTHORITY_CANDIDATES_REFERENCE).stat().st_mode) == 0o644
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
