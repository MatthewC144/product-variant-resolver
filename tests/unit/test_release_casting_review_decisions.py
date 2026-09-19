from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from product_variant_resolver.release_casting_review_decisions import (
    append_event,
    build_public_manifest,
    validate_ledger,
)

ROOT = Path(__file__).resolve().parents[2]


def packet() -> dict[str, Any]:
    questions = []
    for ordinal in range(1, 6):
        questions.append(
            {
                "ordinal": ordinal,
                "review_cluster_id": f"cluster-{ordinal}",
                "allowed_decisions": [
                    "same_review_family",
                    "keep_separate",
                    "unknown",
                ],
            }
        )
    return {
        "packet_sha256": "a" * 64,
        "batch_id": "batch-01-" + "a" * 64,
        "questions": questions,
    }


def first_ledger() -> dict[str, Any]:
    return append_event(
        packet(),
        None,
        question_ordinal=1,
        decision="same_review_family",
        owner_response_verbatim="`same_review_family`",
        decided_at="2026-09-18T02:10:49Z",
    )


def test_first_owner_event_is_verbatim_packet_bound_and_narrow() -> None:
    current_packet = packet()
    ledger = first_ledger()
    validate_ledger(current_packet, ledger)
    event = ledger["events"][0]
    assert event["question_ordinal"] == 1
    assert event["review_cluster_id"] == "cluster-1"
    assert event["owner_response_verbatim"] == "`same_review_family`"
    assert event["decision"] == "same_review_family"
    assert event["authorized_effect"] == "review_family_relationship_confirmed"
    assert event["canonical_uuid"] is None
    assert event["color_decision"] is None
    assert "canonical_uuid_creation" in event["excluded_effects"]
    assert ledger["summary"]["recorded_owner_decisions"] == 1
    assert ledger["summary"]["pending_owner_decisions"] == 4


def test_response_must_normalize_to_recorded_decision() -> None:
    with pytest.raises(ValueError, match="owner response differs"):
        append_event(
            packet(),
            None,
            question_ordinal=1,
            decision="same_review_family",
            owner_response_verbatim="unknown",
            decided_at="2026-09-18T02:10:49Z",
        )


def test_matching_question_prefix_is_accepted_and_preserved_verbatim() -> None:
    second = append_event(
        packet(),
        first_ledger(),
        question_ordinal=2,
        decision="same_review_family",
        owner_response_verbatim="2. `same_review_family`",
        decided_at="2026-09-18T02:27:29Z",
    )
    assert second["events"][1]["owner_response_verbatim"] == "2. `same_review_family`"
    assert second["events"][1]["decision"] == "same_review_family"


def test_mismatched_question_prefix_is_rejected() -> None:
    with pytest.raises(ValueError, match="question prefix differs"):
        append_event(
            packet(),
            first_ledger(),
            question_ordinal=2,
            decision="same_review_family",
            owner_response_verbatim="3. `same_review_family`",
            decided_at="2026-09-18T02:27:29Z",
        )


def test_decisions_must_be_contiguous_and_cannot_skip_question_one() -> None:
    with pytest.raises(ValueError, match="next unanswered question is 1"):
        append_event(
            packet(),
            None,
            question_ordinal=2,
            decision="unknown",
            owner_response_verbatim="unknown",
            decided_at="2026-09-18T02:10:49Z",
        )


def test_decision_cannot_be_recorded_twice() -> None:
    with pytest.raises(ValueError, match="next unanswered question is 2"):
        append_event(
            packet(),
            first_ledger(),
            question_ordinal=1,
            decision="same_review_family",
            owner_response_verbatim="same_review_family",
            decided_at="2026-09-18T02:11:49Z",
        )


def test_append_preserves_prior_event_exactly() -> None:
    current_packet = packet()
    first = first_ledger()
    prior = copy.deepcopy(first["events"][0])
    second = append_event(
        current_packet,
        first,
        question_ordinal=2,
        decision="keep_separate",
        owner_response_verbatim="`keep_separate`",
        decided_at="2026-09-18T02:11:49Z",
    )
    assert second["events"][0] == prior
    assert second["events"][1]["event_sequence"] == 2
    assert second["summary"]["decision_counts"]["keep_separate"] == 1


def test_tampered_event_or_summary_fails_validation() -> None:
    current_packet = packet()
    ledger = first_ledger()
    ledger["events"][0]["decision"] = "unknown"
    with pytest.raises(ValueError, match="owner response differs"):
        validate_ledger(current_packet, ledger)
    ledger = first_ledger()
    ledger["summary"]["canonical_promotions"] = 1
    with pytest.raises(ValueError, match="summary, status, or checksum"):
        validate_ledger(current_packet, ledger)


def test_public_manifest_contains_progress_but_not_answer_or_question_identity() -> None:
    manifest = build_public_manifest(first_ledger())
    text = json.dumps(manifest, sort_keys=True)
    assert manifest["summary"]["recorded_owner_decisions"] == 1
    assert manifest["summary"]["review_family_relationships_confirmed"] == 1
    assert "events" not in manifest
    assert "owner_response_verbatim" not in text
    assert "cluster-1" not in text


def test_current_private_ledger_records_all_questions_when_present() -> None:
    path = (
        ROOT / "data/external/hot-wheels-wiki/local-release-casting-review-decisions-v1/ledger.json"
    )
    if not path.is_file():
        pytest.skip(
            "private decision ledger is local and created after the owner answer is recorded"
        )
    ledger = json.loads(path.read_text(encoding="utf-8"))
    assert len(ledger["events"]) == 5
    assert ledger["events"][0]["question_ordinal"] == 1
    assert ledger["events"][0]["decision"] == "same_review_family"
    assert ledger["events"][1]["question_ordinal"] == 2
    assert ledger["events"][1]["decision"] == "same_review_family"
    assert ledger["events"][1]["owner_response_verbatim"] == "2. `same_review_family`"
    assert ledger["events"][2]["question_ordinal"] == 3
    assert ledger["events"][2]["decision"] == "same_review_family"
    assert ledger["events"][2]["owner_response_verbatim"] == "same_review_family"
    assert ledger["events"][3]["question_ordinal"] == 4
    assert ledger["events"][3]["decision"] == "same_review_family"
    assert ledger["events"][3]["owner_response_verbatim"] == "same_review_family"
    assert ledger["events"][4]["question_ordinal"] == 5
    assert ledger["events"][4]["decision"] == "same_review_family"
    assert ledger["events"][4]["owner_response_verbatim"] == "same_review_family"
    assert ledger["status"] == "complete"
    assert ledger["summary"]["pending_owner_decisions"] == 0
    assert ledger["summary"]["canonical_promotions"] == 0


def test_committed_public_progress_is_privacy_bounded() -> None:
    path = ROOT / "reports/local-release-casting-review-decisions-v1/manifest.json"
    if not path.is_file():
        pytest.skip("public aggregate is created after owner decisions are recorded")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["summary"]["recorded_owner_decisions"] == 5
    assert manifest["summary"]["pending_owner_decisions"] == 0
    assert manifest["summary"]["canonical_promotions"] == 0
    assert "events" not in manifest
