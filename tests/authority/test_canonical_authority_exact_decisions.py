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
EXACT_RESPONSES = {
    1: (
        "TEST-ONLY T5-G2 Batch 1：明確批准測試項目 σ、τ、υ 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
    2: (
        "TEST-ONLY T5-G2 Batch 2：明確批准測試項目 φ、χ、ψ 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
    3: (
        "TEST-ONLY T5-G2 Batch 3：明確批准測試項目 α、β、γ 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
    4: (
        "TEST-ONLY T5-G2 Batch 4：明確批准測試項目 δ、ε、ζ 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
    5: (
        "TEST-ONLY T5-G2 Batch 5：明確批准測試項目 η、θ、ι 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
    6: (
        "TEST-ONLY T5-G2 Batch 6：明確批准測試項目 κ、λ、μ 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
    7: (
        "TEST-ONLY T5-G2 Batch 7：明確批准測試項目 ν、ξ 為 approved_exact；"
        "測試欄位維持 null，且不授權後續 Gate。"
    ),
}
EXACT_RESPONSE = EXACT_RESPONSES[1]
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
        exact.FORBIDDEN_AUTHORITY_REFERENCE,
        exact.FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE,
        exact.PRIVATE_DIRECTORY / "car-t5f-owner-authorization.json",
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
    batch_ordinal = cast(int, overrides.get("batch_ordinal", 1))
    response = EXACT_RESPONSES.get(batch_ordinal, EXACT_RESPONSE)
    arguments: dict[str, Any] = {
        "owner_response_verbatim": response,
        "authorized_exact_owner_response": response,
        "reviewed_at": datetime(2026, 10, 2, 13, 0, tzinfo=UTC)
        + timedelta(hours=batch_ordinal - 1),
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


def test_appends_batch_two_and_preserves_complete_batch_one(isolated_root: Path) -> None:
    assert _record(isolated_root, batch_ordinal=1) == "created"
    before_authorizations = _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)[
        "authorizations"
    ]
    before_attestations = _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = {
        item["event_id"]: item
        for item in _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
        if item["event_id"].startswith("car-t5-g2-")
    }
    before_candidates = {
        item["candidate_id"]: item
        for item in _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    }
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root, batch_ordinal=2) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root, batch_ordinal=2) == "unchanged"
    assert _record(isolated_root, batch_ordinal=2, check=True) == "unchanged"
    assert _record(isolated_root, batch_ordinal=1, check=True) == "unchanged"
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

    assert [item.batch_ordinal for item in authorizations.authorizations] == [1, 2]
    assert authorizations.authorizations[0].model_dump(mode="json") == before_authorizations[0]
    batch_two = authorizations.authorizations[1]
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 2)
    assert batch_two.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert batch_two.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 6
    after_attestations = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    for previous in before_attestations:
        assert after_attestations[previous["candidate_id"]] == previous
    assert candidates.status_counts == {"staged": 0, "reviewed": 14, "approved_exact": 6}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == {1, 2, 10, 11, 16, 18}
    assert events.batch_authorization_count == 9
    assert events.owner_attestation_count == 26
    assert events.review_event_count == 26
    assert events.status_counts == {"reviewed": 14, "approved_exact": 6}
    after_events = {item.event_id: item.model_dump(mode="json") for item in events.events}
    for event_id, previous in before_events.items():
        assert after_events[event_id] == previous
    batch_two_events = [
        item for item in events.events if item.event_id.startswith("car-t5-g2-batch-2-")
    ]
    assert len(batch_two_events) == 3
    assert all(
        {evidence.field for evidence in item.variant_field_evidence}
        == {
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        }
        for item in batch_two_events
    )
    after_candidates = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_candidates.items():
        if previous["ordinal"] not in {2, 11, 18}:
            assert after_candidates[candidate_id].model_dump(mode="json") == previous
    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    for response in (*EXACT_RESPONSES.values(), *G1_RESPONSES.values()):
        assert response.encode("utf-8") not in public


def test_batch_two_requires_complete_batch_one_prefix(isolated_root: Path) -> None:
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]}
    with pytest.raises(AuthorityContractError, match="prefix order"):
        _record(isolated_root, batch_ordinal=2)
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in TARGETS[2:]
    } == before
    assert not (isolated_root / EXACT_AUTHORIZATION_LEDGER_REFERENCE).exists()


def test_appends_batch_three_and_preserves_complete_two_batch_prefix(
    isolated_root: Path,
) -> None:
    assert _record(isolated_root, batch_ordinal=1) == "created"
    assert _record(isolated_root, batch_ordinal=2) == "created"
    before_authorizations = _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)[
        "authorizations"
    ]
    before_attestations = _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = {
        item["event_id"]: item
        for item in _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
        if item["event_id"].startswith("car-t5-g2-")
    }
    before_candidates = {
        item["candidate_id"]: item
        for item in _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    }
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root, batch_ordinal=3) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root, batch_ordinal=3) == "unchanged"
    assert _record(isolated_root, batch_ordinal=3, check=True) == "unchanged"
    assert _record(isolated_root, batch_ordinal=2, check=True) == "unchanged"
    assert _record(isolated_root, batch_ordinal=1, check=True) == "unchanged"
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

    assert [item.batch_ordinal for item in authorizations.authorizations] == [1, 2, 3]
    assert [
        item.model_dump(mode="json") for item in authorizations.authorizations[:2]
    ] == before_authorizations
    batch_three = authorizations.authorizations[2]
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 3)
    assert batch_three.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert batch_three.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 9
    after_attestations = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    for previous in before_attestations:
        assert after_attestations[previous["candidate_id"]] == previous
    assert candidates.status_counts == {"staged": 0, "reviewed": 11, "approved_exact": 9}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == {1, 2, 3, 8, 10, 11, 14, 16, 18}
    assert events.batch_authorization_count == 10
    assert events.owner_attestation_count == 29
    assert events.review_event_count == 29
    assert events.status_counts == {"reviewed": 11, "approved_exact": 9}
    after_events = {item.event_id: item.model_dump(mode="json") for item in events.events}
    for event_id, previous in before_events.items():
        assert after_events[event_id] == previous
    batch_three_events = [
        item for item in events.events if item.event_id.startswith("car-t5-g2-batch-3-")
    ]
    assert len(batch_three_events) == 3
    expected_values = {
        "casting": "Subaru BRZ",
        "release_year": 2025,
        "series": "HW J-Imports",
        "collector_number": "048",
        "series_position": "3/5",
    }
    observed_identifiers = set()
    for event in batch_three_events:
        evidence = {item.field: item for item in event.variant_field_evidence}
        assert set(evidence) == {
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        }
        assert all(
            evidence[field].reviewed_value == value for field, value in expected_values.items()
        )
        observed_identifiers.add(evidence["identifiers"].reviewed_value)
    assert observed_identifiers == {"JBB55", "HYY12", "HYW99"}
    after_candidates = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_candidates.items():
        if previous["ordinal"] not in {3, 8, 14}:
            assert after_candidates[candidate_id].model_dump(mode="json") == previous
    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    for response in (*EXACT_RESPONSES.values(), *G1_RESPONSES.values()):
        assert response.encode("utf-8") not in public


def test_batch_three_requires_complete_two_batch_prefix(isolated_root: Path) -> None:
    assert _record(isolated_root, batch_ordinal=1) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="prefix order"):
        _record(isolated_root, batch_ordinal=3)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_appends_batch_four_and_preserves_complete_three_batch_prefix(
    isolated_root: Path,
) -> None:
    for batch_ordinal in (1, 2, 3):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before_authorizations = _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)[
        "authorizations"
    ]
    before_attestations = _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = {
        item["event_id"]: item
        for item in _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
        if item["event_id"].startswith("car-t5-g2-")
    }
    before_candidates = {
        item["candidate_id"]: item
        for item in _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    }
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root, batch_ordinal=4) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root, batch_ordinal=4) == "unchanged"
    for batch_ordinal in (1, 2, 3, 4):
        assert _record(isolated_root, batch_ordinal=batch_ordinal, check=True) == "unchanged"
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

    assert [item.batch_ordinal for item in authorizations.authorizations] == [1, 2, 3, 4]
    assert [
        item.model_dump(mode="json") for item in authorizations.authorizations[:3]
    ] == before_authorizations
    batch_four = authorizations.authorizations[3]
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 4)
    assert batch_four.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert batch_four.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 12
    after_attestations = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    for previous in before_attestations:
        assert after_attestations[previous["candidate_id"]] == previous
    assert candidates.status_counts == {"staged": 0, "reviewed": 8, "approved_exact": 12}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == {1, 2, 3, 4, 8, 10, 11, 13, 14, 16, 18, 20}
    assert events.batch_authorization_count == 11
    assert events.owner_attestation_count == 32
    assert events.review_event_count == 32
    assert events.status_counts == {"reviewed": 8, "approved_exact": 12}
    after_events = {item.event_id: item.model_dump(mode="json") for item in events.events}
    for event_id, previous in before_events.items():
        assert after_events[event_id] == previous
    batch_four_events = [
        item for item in events.events if item.event_id.startswith("car-t5-g2-batch-4-")
    ]
    assert len(batch_four_events) == 3
    expected_values = {
        "casting": "Nissan Skyline 2000GT-R LBWK",
        "release_year": 2025,
        "series": "HW J-Imports",
        "collector_number": "026",
        "series_position": "1/5",
    }
    observed_identifiers = set()
    for event in batch_four_events:
        evidence = {item.field: item for item in event.variant_field_evidence}
        assert set(evidence) == {
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        }
        assert all(
            evidence[field].reviewed_value == value for field, value in expected_values.items()
        )
        observed_identifiers.add(evidence["identifiers"].reviewed_value)
    assert observed_identifiers == {"HYX54", "HYW79", "HYY30"}
    after_candidates = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_candidates.items():
        if previous["ordinal"] not in {4, 13, 20}:
            assert after_candidates[candidate_id].model_dump(mode="json") == previous
    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    for response in (*EXACT_RESPONSES.values(), *G1_RESPONSES.values()):
        assert response.encode("utf-8") not in public


def test_batch_four_requires_complete_three_batch_prefix(isolated_root: Path) -> None:
    for batch_ordinal in (1, 2):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="prefix order"):
        _record(isolated_root, batch_ordinal=4)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_appends_batch_five_and_preserves_complete_four_batch_prefix(
    isolated_root: Path,
) -> None:
    for batch_ordinal in (1, 2, 3, 4):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before_authorizations = _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)[
        "authorizations"
    ]
    before_attestations = _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = {
        item["event_id"]: item
        for item in _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
        if item["event_id"].startswith("car-t5-g2-")
    }
    before_candidates = {
        item["candidate_id"]: item
        for item in _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    }
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root, batch_ordinal=5) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root, batch_ordinal=5) == "unchanged"
    for batch_ordinal in (1, 2, 3, 4, 5):
        assert _record(isolated_root, batch_ordinal=batch_ordinal, check=True) == "unchanged"
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

    assert [item.batch_ordinal for item in authorizations.authorizations] == [1, 2, 3, 4, 5]
    assert [
        item.model_dump(mode="json") for item in authorizations.authorizations[:4]
    ] == before_authorizations
    batch_five = authorizations.authorizations[4]
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 5)
    assert batch_five.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert batch_five.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 15
    after_attestations = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    for previous in before_attestations:
        assert after_attestations[previous["candidate_id"]] == previous
    assert candidates.status_counts == {"staged": 0, "reviewed": 5, "approved_exact": 15}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == {1, 2, 3, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 18, 20}
    assert events.batch_authorization_count == 12
    assert events.owner_attestation_count == 35
    assert events.review_event_count == 35
    assert events.status_counts == {"reviewed": 5, "approved_exact": 15}
    after_events = {item.event_id: item.model_dump(mode="json") for item in events.events}
    for event_id, previous in before_events.items():
        assert after_events[event_id] == previous
    batch_five_events = [
        item for item in events.events if item.event_id.startswith("car-t5-g2-batch-5-")
    ]
    assert len(batch_five_events) == 3
    expected_values = {
        "casting": "'21 Ford Bronco",
        "release_year": 2025,
        "series": "HW Hot Trucks",
        "collector_number": "020",
        "series_position": "1/10",
    }
    observed_identifiers = set()
    for event in batch_five_events:
        evidence = {item.field: item for item in event.variant_field_evidence}
        assert set(evidence) == {
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        }
        assert all(
            evidence[field].reviewed_value == value for field, value in expected_values.items()
        )
        observed_identifiers.add(evidence["identifiers"].reviewed_value)
    assert observed_identifiers == {"HYY32", "HYW73", "HYX50"}
    after_candidates = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_candidates.items():
        if previous["ordinal"] not in {5, 7, 17}:
            assert after_candidates[candidate_id].model_dump(mode="json") == previous
    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    for response in (*EXACT_RESPONSES.values(), *G1_RESPONSES.values()):
        assert response.encode("utf-8") not in public


def test_batch_five_requires_complete_four_batch_prefix(isolated_root: Path) -> None:
    for batch_ordinal in (1, 2, 3):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="prefix order"):
        _record(isolated_root, batch_ordinal=5)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_appends_batch_six_and_preserves_complete_five_batch_prefix(
    isolated_root: Path,
) -> None:
    for batch_ordinal in (1, 2, 3, 4, 5):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before_authorizations = _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)[
        "authorizations"
    ]
    before_attestations = _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = {
        item["event_id"]: item
        for item in _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
        if item["event_id"].startswith("car-t5-g2-")
    }
    before_candidates = {
        item["candidate_id"]: item
        for item in _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    }
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root, batch_ordinal=6) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root, batch_ordinal=6) == "unchanged"
    for batch_ordinal in (1, 2, 3, 4, 5, 6):
        assert _record(isolated_root, batch_ordinal=batch_ordinal, check=True) == "unchanged"
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

    assert [item.batch_ordinal for item in authorizations.authorizations] == [1, 2, 3, 4, 5, 6]
    assert [
        item.model_dump(mode="json") for item in authorizations.authorizations[:5]
    ] == before_authorizations
    batch_six = authorizations.authorizations[5]
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 6)
    assert batch_six.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert batch_six.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 18
    after_attestations = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    for previous in before_attestations:
        assert after_attestations[previous["candidate_id"]] == previous
    assert candidates.status_counts == {"staged": 0, "reviewed": 2, "approved_exact": 18}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == {1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20}
    assert events.batch_authorization_count == 13
    assert events.owner_attestation_count == 38
    assert events.review_event_count == 38
    assert events.status_counts == {"reviewed": 2, "approved_exact": 18}
    after_events = {item.event_id: item.model_dump(mode="json") for item in events.events}
    for event_id, previous in before_events.items():
        assert after_events[event_id] == previous
    batch_six_events = [
        item for item in events.events if item.event_id.startswith("car-t5-g2-batch-6-")
    ]
    assert len(batch_six_events) == 3
    expected_values = {
        "casting": "Morgan Super 3",
        "release_year": 2025,
        "series": "Factory Fresh",
        "collector_number": "015",
        "series_position": "1/5",
    }
    observed_identifiers = set()
    for event in batch_six_events:
        evidence = {item.field: item for item in event.variant_field_evidence}
        assert set(evidence) == {
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        }
        assert all(
            evidence[field].reviewed_value == value for field, value in expected_values.items()
        )
        observed_identifiers.add(evidence["identifiers"].reviewed_value)
    assert observed_identifiers == {"HYX48", "HYW13", "HYY33"}
    after_candidates = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_candidates.items():
        if previous["ordinal"] not in {6, 12, 19}:
            assert after_candidates[candidate_id].model_dump(mode="json") == previous
    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    for response in (*EXACT_RESPONSES.values(), *G1_RESPONSES.values()):
        assert response.encode("utf-8") not in public


def test_batch_six_requires_complete_five_batch_prefix(isolated_root: Path) -> None:
    for batch_ordinal in (1, 2, 3, 4):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="prefix order"):
        _record(isolated_root, batch_ordinal=6)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_appends_batch_seven_and_preserves_complete_six_batch_prefix(
    isolated_root: Path,
) -> None:
    for batch_ordinal in (1, 2, 3, 4, 5, 6):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before_authorizations = _read(isolated_root, EXACT_AUTHORIZATION_LEDGER_REFERENCE)[
        "authorizations"
    ]
    before_attestations = _read(isolated_root, EXACT_ATTESTATION_LEDGER_REFERENCE)["attestations"]
    before_events = {
        item["event_id"]: item
        for item in _read(isolated_root, REVIEW_EVENTS_REFERENCE)["events"]
        if item["event_id"].startswith("car-t5-g2-")
    }
    before_candidates = {
        item["candidate_id"]: item
        for item in _read(isolated_root, AUTHORITY_CANDIDATES_REFERENCE)["candidates"]
    }
    g1_authorizations = BatchAuthorizationLedger.model_validate(
        _read(isolated_root, AUTHORIZATION_LEDGER_REFERENCE)
    )

    assert _record(isolated_root, batch_ordinal=7) == "created"
    first = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    assert _record(isolated_root, batch_ordinal=7) == "unchanged"
    for batch_ordinal in (1, 2, 3, 4, 5, 6, 7):
        assert _record(isolated_root, batch_ordinal=batch_ordinal, check=True) == "unchanged"
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

    assert [item.batch_ordinal for item in authorizations.authorizations] == [1, 2, 3, 4, 5, 6, 7]
    assert [
        item.model_dump(mode="json") for item in authorizations.authorizations[:6]
    ] == before_authorizations
    batch_seven = authorizations.authorizations[6]
    prior = next(item for item in g1_authorizations.authorizations if item.batch_ordinal == 7)
    assert batch_seven.prior_gate_response_sha256s == [prior.response_verbatim_sha256]
    assert batch_seven.response_verbatim_sha256 != prior.response_verbatim_sha256
    assert len(attestations.attestations) == 20
    after_attestations = {
        item.candidate_id: item.model_dump(mode="json") for item in attestations.attestations
    }
    for previous in before_attestations:
        assert after_attestations[previous["candidate_id"]] == previous
    assert candidates.status_counts == {"staged": 0, "reviewed": 0, "approved_exact": 20}
    assert {
        item.ordinal for item in candidates.candidates if item.status.value == "approved_exact"
    } == set(range(1, 21))
    assert events.batch_authorization_count == 14
    assert events.owner_attestation_count == 40
    assert events.review_event_count == 40
    assert events.status_counts == {"reviewed": 0, "approved_exact": 20}
    after_events = {item.event_id: item.model_dump(mode="json") for item in events.events}
    for event_id, previous in before_events.items():
        assert after_events[event_id] == previous
    batch_seven_events = [
        item for item in events.events if item.event_id.startswith("car-t5-g2-batch-7-")
    ]
    assert len(batch_seven_events) == 2
    expected_values = {
        "casting": "Mazda MX-5 Miata",
        "release_year": 2025,
        "series": "HW Dream Garage",
        "collector_number": "001",
        "series_position": "2/5",
    }
    observed_identifiers = set()
    for event in batch_seven_events:
        evidence = {item.field: item for item in event.variant_field_evidence}
        assert set(evidence) == {
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "identifiers",
        }
        assert all(
            evidence[field].reviewed_value == value for field, value in expected_values.items()
        )
        observed_identifiers.add(evidence["identifiers"].reviewed_value)
    assert observed_identifiers == {"HYW18", "HYX57"}
    after_candidates = {item.candidate_id: item for item in candidates.candidates}
    for candidate_id, previous in before_candidates.items():
        if previous["ordinal"] not in {9, 15}:
            assert after_candidates[candidate_id].model_dump(mode="json") == previous
    public = (isolated_root / AUTHORITY_CANDIDATES_REFERENCE).read_bytes() + (
        isolated_root / REVIEW_EVENTS_REFERENCE
    ).read_bytes()
    for response in (*EXACT_RESPONSES.values(), *G1_RESPONSES.values()):
        assert response.encode("utf-8") not in public


def test_batch_seven_requires_complete_six_batch_prefix(isolated_root: Path) -> None:
    for batch_ordinal in (1, 2, 3, 4, 5):
        assert _record(isolated_root, batch_ordinal=batch_ordinal) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    with pytest.raises(AuthorityContractError, match="prefix order"):
        _record(isolated_root, batch_ordinal=7)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


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


def test_batch_two_requires_its_own_fresh_response(isolated_root: Path) -> None:
    assert _record(isolated_root, batch_ordinal=1) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    response = G1_RESPONSES[2]
    with pytest.raises((AuthorityContractError, ValueError), match="response|Gate"):
        record_t5_g2_batch_exact(
            isolated_root,
            owner_response_verbatim=response,
            authorized_exact_owner_response=response,
            batch_ordinal=2,
            reviewed_at=datetime(2026, 10, 2, 14, 0, tzinfo=UTC),
        )
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before


def test_requires_independently_supplied_exact_response(isolated_root: Path) -> None:
    with pytest.raises((AuthorityContractError, ValueError), match="exact|external|differs"):
        _record(isolated_root, owner_response_verbatim="TEST-ONLY generic continuation")
    assert not (isolated_root / EXACT_AUTHORIZATION_LEDGER_REFERENCE).exists()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"batch_ordinal": 8}, "Batches 1-7"),
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


def test_batch_two_atomic_failure_restores_complete_batch_one(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _record(isolated_root, batch_ordinal=1) == "created"
    before = {reference: (isolated_root / reference).read_bytes() for reference in TARGETS}
    real_replace = os.replace
    calls = 0

    def fail_third(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected Batch 2 exact append failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_third)
    with pytest.raises(OSError, match="Batch 2"):
        _record(isolated_root, batch_ordinal=2)
    assert {reference: (isolated_root / reference).read_bytes() for reference in TARGETS} == before

    monkeypatch.setattr(os, "replace", real_replace)
    assert _record(isolated_root, batch_ordinal=2) == "created"


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

    batch_two = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--batch-ordinal",
        "2",
        "--owner-response",
        EXACT_RESPONSES[2],
        "--authorized-exact-owner-response",
        EXACT_RESPONSES[2],
        "--reviewed-at",
        "2026-10-02T14:00:00Z",
    ]
    appended = subprocess.run(batch_two, cwd=ROOT, text=True, capture_output=True, check=False)
    assert appended.returncode == 0, appended.stderr
    assert appended.stdout.strip() == "created"
    checked_two = subprocess.run(
        [*batch_two, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked_two.returncode == 0, checked_two.stderr
    assert checked_two.stdout.strip() == "unchanged"

    batch_three = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--batch-ordinal",
        "3",
        "--owner-response",
        EXACT_RESPONSES[3],
        "--authorized-exact-owner-response",
        EXACT_RESPONSES[3],
        "--reviewed-at",
        "2026-10-02T15:00:00Z",
    ]
    appended_three = subprocess.run(
        batch_three, cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert appended_three.returncode == 0, appended_three.stderr
    assert appended_three.stdout.strip() == "created"
    checked_three = subprocess.run(
        [*batch_three, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked_three.returncode == 0, checked_three.stderr
    assert checked_three.stdout.strip() == "unchanged"

    batch_four = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--batch-ordinal",
        "4",
        "--owner-response",
        EXACT_RESPONSES[4],
        "--authorized-exact-owner-response",
        EXACT_RESPONSES[4],
        "--reviewed-at",
        "2026-10-02T16:00:00Z",
    ]
    appended_four = subprocess.run(
        batch_four, cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert appended_four.returncode == 0, appended_four.stderr
    assert appended_four.stdout.strip() == "created"
    checked_four = subprocess.run(
        [*batch_four, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked_four.returncode == 0, checked_four.stderr
    assert checked_four.stdout.strip() == "unchanged"

    batch_five = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--batch-ordinal",
        "5",
        "--owner-response",
        EXACT_RESPONSES[5],
        "--authorized-exact-owner-response",
        EXACT_RESPONSES[5],
        "--reviewed-at",
        "2026-10-02T17:00:00Z",
    ]
    appended_five = subprocess.run(
        batch_five, cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert appended_five.returncode == 0, appended_five.stderr
    assert appended_five.stdout.strip() == "created"
    checked_five = subprocess.run(
        [*batch_five, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked_five.returncode == 0, checked_five.stderr
    assert checked_five.stdout.strip() == "unchanged"

    batch_six = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--batch-ordinal",
        "6",
        "--owner-response",
        EXACT_RESPONSES[6],
        "--authorized-exact-owner-response",
        EXACT_RESPONSES[6],
        "--reviewed-at",
        "2026-10-02T18:00:00Z",
    ]
    appended_six = subprocess.run(batch_six, cwd=ROOT, text=True, capture_output=True, check=False)
    assert appended_six.returncode == 0, appended_six.stderr
    assert appended_six.stdout.strip() == "created"
    checked_six = subprocess.run(
        [*batch_six, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked_six.returncode == 0, checked_six.stderr
    assert checked_six.stdout.strip() == "unchanged"

    batch_seven = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--batch-ordinal",
        "7",
        "--owner-response",
        EXACT_RESPONSES[7],
        "--authorized-exact-owner-response",
        EXACT_RESPONSES[7],
        "--reviewed-at",
        "2026-10-02T19:00:00Z",
    ]
    appended_seven = subprocess.run(
        batch_seven, cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert appended_seven.returncode == 0, appended_seven.stderr
    assert appended_seven.stdout.strip() == "created"
    checked_seven = subprocess.run(
        [*batch_seven, "--check"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert checked_seven.returncode == 0, checked_seven.stderr
    assert checked_seven.stdout.strip() == "unchanged"
