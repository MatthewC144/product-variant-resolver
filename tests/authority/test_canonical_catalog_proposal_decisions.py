from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from product_variant_resolver.canonical_authority_packet import (
    publish_workspace,
    reconstruct_frozen_parent_catalog,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
)
from product_variant_resolver.canonical_catalog_decisions import (
    APPROVAL_REASON,
    BASE_CAR_T4_COMMIT,
    CATALOG_APPLICATION_EVENT_NAME,
    CATALOG_BATCH_APPLICATION_GATE,
    CONTINUE_OWNER_REVIEW_GATE,
    LEDGER_REFERENCE,
    PUBLIC_METHOD_REFERENCE,
    PUBLIC_PROGRESS_REFERENCE,
    CatalogDecision,
    CommittedProgressAnchor,
    ExpectedOwnerAuthorization,
    ProgressCommitment,
    PublicCatalogDecisionProgress,
    _build_public_progress,
    _render_public_method,
    check_catalog_decisions,
    record_catalog_decision,
)

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_ID = "car-t3-fandom-row-0b280377b913e854"
PROPOSAL_ID = "car-t4-proposal-0b280377b913e854"
OWNER_RESPONSE = "批准，color 與 edition 保持 null。"
SECOND_CANDIDATE_ID = "car-t3-fandom-row-20f16ad2c5417006"
SECOND_PROPOSAL_ID = "car-t4-proposal-20f16ad2c5417006"
SECOND_OWNER_RESPONSE = "批准第 2 筆，color 與 edition 保持 null。"
REVIEWED_AT = datetime(2026, 9, 29, 15, 30, tzinfo=UTC)

COPY_PATHS = (
    ".gitignore",
    "data/catalog.json",
    "data/authority-review/canonical-authority-review-v1/candidate-plan.json",
    "data/authority-review/canonical-authority-review-v1/catalog-proposal-manifest.json",
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
    local = Path("data/authority-review/canonical-authority-review-v1/local-catalog-review-v1")
    shutil.copytree(ROOT / local, tmp_path / local)
    _, parent_catalog_raw = reconstruct_frozen_parent_catalog(tmp_path)
    (tmp_path / "data/catalog.json").write_bytes(parent_catalog_raw)
    (tmp_path / LEDGER_REFERENCE).unlink(missing_ok=True)
    (tmp_path / LEDGER_REFERENCE.parent / CATALOG_APPLICATION_EVENT_NAME).unlink(missing_ok=True)
    (
        tmp_path
        / "data/authority-review/canonical-authority-review-v1/catalog-application-manifest.json"
    ).unlink(missing_ok=True)
    return tmp_path


def _record(root: Path) -> tuple[str, Any]:
    return record_catalog_decision(
        root,
        candidate_id=CANDIDATE_ID,
        proposal_id=PROPOSAL_ID,
        decision=CatalogDecision.approve_catalog_record,
        owner_response_verbatim=OWNER_RESPONSE,
        reviewed_at=REVIEWED_AT,
        head_anchor_provider=_base_head,
        progress_at_commit_provider=_no_progress,
    )


def _base_head(_root: Path) -> CommittedProgressAnchor:
    return CommittedProgressAnchor(BASE_CAR_T4_COMMIT, None, None)


def _no_progress(_root: Path, _commit: str) -> bytes | None:
    return None


def _check(root: Path) -> Any:
    return check_catalog_decisions(
        root,
        allow_uncommitted_current=True,
        head_anchor_provider=_base_head,
        progress_at_commit_provider=_no_progress,
        expected_uncommitted_authorization=ExpectedOwnerAuthorization(
            ordinal=1,
            candidate_id=CANDIDATE_ID,
            proposal_id=PROPOSAL_ID,
            decision=CatalogDecision.approve_catalog_record,
            exact_owner_response=OWNER_RESPONSE,
            review_reason=APPROVAL_REASON,
        ),
    )


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_applied_workspace_preserves_completed_historical_decision_ledger() -> None:
    current = _load(ROOT / "data/catalog.json")
    assert current["catalog_version"] == "catalog-v2"
    assert len(current["products"]) == 140

    ledger = check_catalog_decisions(ROOT)
    assert len(ledger.events) == 20
    assert ledger.decision_counts.approved == 20
    assert ledger.catalog_applied_count == 0


def test_records_only_first_canonical_decision_and_preserves_all_base_artifacts(
    isolated_root: Path,
) -> None:
    protected = [
        isolated_root / "data/catalog.json",
        isolated_root
        / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposals.json",
        isolated_root
        / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposal-review-packet.json",
        isolated_root
        / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-decision-template.json",
        isolated_root
        / "data/authority-review/canonical-authority-review-v1/catalog-proposal-manifest.json",
    ]
    before = {path: path.read_bytes() for path in protected}

    status, ledger = _record(isolated_root)

    assert status == "recorded"
    assert len(ledger.events) == 1
    event = ledger.events[0]
    assert event.ordinal == 1
    assert event.candidate_id == CANDIDATE_ID
    assert event.proposal_id == PROPOSAL_ID
    assert event.owner_response_verbatim == OWNER_RESPONSE
    assert event.review_reason == APPROVAL_REASON
    assert event.accepted_field_mappings == [
        "casting",
        "release_year",
        "series",
        "collector_number",
        "series_position",
        "identifiers",
    ]
    assert event.resolver_output_consulted is False
    assert event.catalog_applied is False
    assert event.authority_approved is False
    assert ledger.decision_counts.model_dump() == {
        "approved": 1,
        "held": 0,
        "rejected": 0,
        "pending": 19,
    }
    assert all(path.read_bytes() == payload for path, payload in before.items())
    assert _check(isolated_root) == ledger
    assert publish_workspace(isolated_root, check=True) == "unchanged"


def test_identical_retry_is_unchanged_but_conflicting_retry_fails(isolated_root: Path) -> None:
    _, first = _record(isolated_root)
    status, second = _record(isolated_root)
    assert status == "unchanged"
    assert second == first

    with pytest.raises(AuthorityContractError, match="conflicting retry"):
        record_catalog_decision(
            isolated_root,
            candidate_id=CANDIDATE_ID,
            proposal_id=PROPOSAL_ID,
            decision=CatalogDecision.hold,
            owner_response_verbatim="暫緩",
            review_reason="Evidence needs another owner review.",
            reviewed_at=REVIEWED_AT,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )


def test_precommit_check_requires_external_expected_authorization(isolated_root: Path) -> None:
    _record(isolated_root)
    with pytest.raises(AuthorityContractError, match="external expected owner authorization"):
        check_catalog_decisions(
            isolated_root,
            allow_uncommitted_current=True,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )


def test_rejects_out_of_order_candidate_or_proposal(isolated_root: Path) -> None:
    with pytest.raises(AuthorityContractError, match="ordinal 1"):
        record_catalog_decision(
            isolated_root,
            candidate_id="car-t3-fandom-row-20f16ad2c5417006",
            proposal_id="car-t4-proposal-20f16ad2c5417006",
            decision=CatalogDecision.approve_catalog_record,
            owner_response_verbatim=OWNER_RESPONSE,
            reviewed_at=REVIEWED_AT,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )

    with pytest.raises(AuthorityContractError, match="ordinal 1"):
        record_catalog_decision(
            isolated_root,
            candidate_id=CANDIDATE_ID,
            proposal_id="car-t4-proposal-wrong",
            decision=CatalogDecision.approve_catalog_record,
            owner_response_verbatim=OWNER_RESPONSE,
            reviewed_at=REVIEWED_AT,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )


@pytest.mark.parametrize(
    "response",
    [
        "不批准，color 與 edition 保持 null。",
        "批准，color 及 edition 保持 null。",
        "批准，color 與 edition 都維持 null。",
        "Approve with color and edition null.",
    ],
)
def test_event_one_requires_the_exact_normalized_owner_literal(
    isolated_root: Path, response: str
) -> None:
    with pytest.raises(AuthorityContractError, match="explicit exact authorization literal"):
        record_catalog_decision(
            isolated_root,
            candidate_id=CANDIDATE_ID,
            proposal_id=PROPOSAL_ID,
            decision=CatalogDecision.approve_catalog_record,
            owner_response_verbatim=response,
            reviewed_at=REVIEWED_AT,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )


@pytest.mark.parametrize(
    ("reference", "mutation"),
    [
        (
            "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposal-review-packet.json",
            lambda value: value.update({"network_requests": 1}),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposals.json",
            lambda value: value.update({"approved_count": 1}),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/catalog-proposal-manifest.json",
            lambda value: value.update({"catalog_mutated": True}),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/candidate-plan.json",
            lambda value: value.update({"approval_status": "held"}),
        ),
        (
            "data/authority-review/canonical-authority-review-v1/source-decisions.json",
            lambda value: value.update({"unexpected": True}),
        ),
        (
            "data/catalog.json",
            lambda value: value.update({"catalog_version": "stale"}),
        ),
    ],
)
def test_rejects_stale_or_tampered_parent_artifacts(
    isolated_root: Path,
    reference: str,
    mutation: Any,
) -> None:
    path = isolated_root / reference
    payload = _load(path)
    mutation(payload)
    _write(path, payload)
    with pytest.raises((AuthorityContractError, ValidationError, ValueError)):
        _record(isolated_root)


def test_rejects_unknown_nested_fields_pii_and_broadened_approval(isolated_root: Path) -> None:
    _record(isolated_root)
    ledger_path = isolated_root / LEDGER_REFERENCE
    payload = _load(ledger_path)
    payload["events"][0]["hidden_prediction"] = "x"
    _write(ledger_path, payload)
    with pytest.raises(ValidationError):
        _check(isolated_root)

    second_root = isolated_root.parent / "second"
    shutil.copytree(isolated_root, second_root)
    (second_root / LEDGER_REFERENCE).unlink()
    (second_root / PUBLIC_PROGRESS_REFERENCE).unlink()
    (second_root / PUBLIC_METHOD_REFERENCE).unlink()
    with pytest.raises(AuthorityContractError, match="personal information"):
        record_catalog_decision(
            second_root,
            candidate_id=CANDIDATE_ID,
            proposal_id=PROPOSAL_ID,
            decision=CatalogDecision.approve_catalog_record,
            owner_response_verbatim="批准，color 與 edition 保持 null。 owner@example.com",
            reviewed_at=REVIEWED_AT,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )
    with pytest.raises(AuthorityContractError, match="broaden"):
        record_catalog_decision(
            second_root,
            candidate_id=CANDIDATE_ID,
            proposal_id=PROPOSAL_ID,
            decision=CatalogDecision.approve_catalog_record,
            owner_response_verbatim=OWNER_RESPONSE,
            review_reason="Also approve exact authority.",
            reviewed_at=REVIEWED_AT,
            head_anchor_provider=_base_head,
            progress_at_commit_provider=_no_progress,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["events"][0].update({"ordinal": 2}),
        lambda value: value["events"][0].update({"previous_event_sha256": "a" * 64}),
        lambda value: value["events"][0].update({"owner_response_verbatim": "拒絕"}),
        lambda value: value["events"][0].update({"resolver_output_consulted": True}),
        lambda value: value["events"][0].update({"catalog_applied": True}),
        lambda value: value["events"][0].update({"authority_approved": True}),
        lambda value: value["events"][0].update({"event_sha256": "b" * 64}),
        lambda value: value["decision_counts"].update({"approved": 0, "pending": 20}),
        lambda value: value.update({"ledger_sha256": "c" * 64}),
    ],
)
def test_rejects_private_ledger_tampering(isolated_root: Path, mutation: Any) -> None:
    _record(isolated_root)
    path = isolated_root / LEDGER_REFERENCE
    payload = _load(path)
    mutation(payload)
    _write(path, payload)
    with pytest.raises((AuthorityContractError, ValidationError, ValueError)):
        _check(isolated_root)


def test_duplicate_json_keys_and_partial_publication_fail_closed(isolated_root: Path) -> None:
    _record(isolated_root)
    ledger_path = isolated_root / LEDGER_REFERENCE
    text = ledger_path.read_text(encoding="utf-8")
    ledger_path.write_text(text.replace("{", '{"schema_version":"duplicate",', 1))
    with pytest.raises(AuthorityContractError, match="duplicate JSON key"):
        _check(isolated_root)

    other = isolated_root.parent / "partial"
    shutil.copytree(isolated_root, other)
    (other / LEDGER_REFERENCE).unlink()
    with pytest.raises(AuthorityContractError, match="partial"):
        _check(other)


def test_public_progress_has_only_safe_aggregates(isolated_root: Path) -> None:
    _record(isolated_root)
    progress_text = (isolated_root / PUBLIC_PROGRESS_REFERENCE).read_text(encoding="utf-8")
    method_text = (isolated_root / PUBLIC_METHOD_REFERENCE).read_text(encoding="utf-8")
    combined = progress_text + method_text
    assert CANDIDATE_ID not in combined
    assert PROPOSAL_ID not in combined
    assert "Mazda" not in combined
    assert "HYX45" not in combined
    assert OWNER_RESPONSE not in combined
    assert "owner@example.com" not in combined
    progress = PublicCatalogDecisionProgress.model_validate(json.loads(progress_text))
    assert progress.owner_decision_approved_count == 1
    assert progress.pending_owner_decision_count == 19
    assert progress.proposal_artifact_review_status == "staged"
    assert progress.catalog_applied_count == 0
    assert progress.exact_authority_count == 0


def test_next_gate_changes_only_after_all_twenty_decisions(isolated_root: Path) -> None:
    _, in_progress_ledger = _record(isolated_root)
    in_progress = PublicCatalogDecisionProgress.model_validate(
        json.loads((isolated_root / PUBLIC_PROGRESS_REFERENCE).read_text(encoding="utf-8"))
    )
    before = (isolated_root / PUBLIC_PROGRESS_REFERENCE).read_bytes()
    assert in_progress.status == "in_progress_awaiting_owner"
    assert in_progress.next_gate == CONTINUE_OWNER_REVIEW_GATE
    assert _check(isolated_root) == in_progress_ledger
    assert (isolated_root / PUBLIC_PROGRESS_REFERENCE).read_bytes() == before

    final_ledger = in_progress_ledger.model_copy(
        update={
            "status": "complete_awaiting_batch_application_gate",
            "events": [in_progress_ledger.events[-1]] * 20,
            "decision_counts": in_progress_ledger.decision_counts.model_copy(
                update={"approved": 20, "pending": 0}
            ),
            "next_pending_ordinal": None,
        }
    )
    final_progress = _build_public_progress(
        final_ledger,
        ProgressCommitment(
            anchor_commit_sha=BASE_CAR_T4_COMMIT,
            previous_progress_sha256="a" * 64,
            previous_private_ledger_sha256="b" * 64,
            previous_committed_event_count=19,
        ),
    )
    assert final_progress.status == "complete_awaiting_batch_application_gate"
    assert final_progress.recorded_event_count == 20
    assert final_progress.pending_owner_decision_count == 0
    assert final_progress.next_gate == CATALOG_BATCH_APPLICATION_GATE
    rendered = _render_public_method(final_progress)
    assert "All 20 owner decisions are recorded" in rendered
    assert "separate catalog\nbatch application owner Gate" in rendered
    assert "does not apply catalog records" in rendered

    stale_final = final_progress.model_dump(mode="json")
    stale_final["next_gate"] = CONTINUE_OWNER_REVIEW_GATE
    with pytest.raises(ValidationError, match="next Gate differs"):
        PublicCatalogDecisionProgress.model_validate(stale_final)

    premature_final = in_progress.model_dump(mode="json")
    premature_final["next_gate"] = CATALOG_BATCH_APPLICATION_GATE
    with pytest.raises(ValidationError, match="next Gate differs"):
        PublicCatalogDecisionProgress.model_validate(premature_final)


def test_partial_atomic_write_rolls_back_all_new_outputs(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated publication failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="simulated"):
        _record(isolated_root)
    assert not (isolated_root / LEDGER_REFERENCE).exists()
    assert not (isolated_root / PUBLIC_PROGRESS_REFERENCE).exists()
    assert not (isolated_root / PUBLIC_METHOD_REFERENCE).exists()


def test_symlink_leaf_and_root_are_rejected(isolated_root: Path) -> None:
    outside = isolated_root / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (isolated_root / PUBLIC_PROGRESS_REFERENCE).symlink_to(outside)
    with pytest.raises(AuthorityContractError, match="partial"):
        _record(isolated_root)

    root_link = isolated_root.parent / "root-link"
    root_link.symlink_to(isolated_root, target_is_directory=True)
    with pytest.raises(AuthorityContractError, match="symlink"):
        _record(root_link)


def test_git_head_anchor_rejects_rehashed_history_rewrite(isolated_root: Path) -> None:
    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(isolated_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    git("init", "-q")
    git("config", "user.name", "CAR Test")
    git("config", "user.email", "car-test@example.invalid")
    git("add", ".")
    git("commit", "-qm", "base CAR-T4 fixture")
    base_commit = git("rev-parse", "HEAD")
    record_catalog_decision(
        isolated_root,
        candidate_id=CANDIDATE_ID,
        proposal_id=PROPOSAL_ID,
        decision=CatalogDecision.approve_catalog_record,
        owner_response_verbatim=OWNER_RESPONSE,
        reviewed_at=REVIEWED_AT,
        expected_base_commit=base_commit,
    )
    git("add", str(PUBLIC_PROGRESS_REFERENCE), str(PUBLIC_METHOD_REFERENCE))
    git("commit", "-qm", "anchor event 1 progress")
    check_catalog_decisions(isolated_root, expected_base_commit=base_commit)

    harmless = isolated_root / "harmless.txt"
    harmless.write_text("code-only follow-up fixture\n", encoding="utf-8")
    git("add", "harmless.txt")
    git("commit", "-qm", "code-only follow-up")
    check_catalog_decisions(isolated_root, expected_base_commit=base_commit)
    harmless.write_text("second code-only follow-up fixture\n", encoding="utf-8")
    git("add", "harmless.txt")
    git("commit", "-qm", "second code-only follow-up")
    check_catalog_decisions(isolated_root, expected_base_commit=base_commit)

    ledger_path = isolated_root / LEDGER_REFERENCE
    progress_path = isolated_root / PUBLIC_PROGRESS_REFERENCE
    method_path = isolated_root / PUBLIC_METHOD_REFERENCE
    ledger = _load(ledger_path)
    progress = _load(progress_path)
    old_ledger_sha = ledger["ledger_sha256"]
    old_event_sha = ledger["events"][0]["event_sha256"]
    event = ledger["events"][0]
    event["reviewed_at"] = "2026-09-29T15:31:00Z"
    event["event_sha256"] = content_sha256(
        {key: value for key, value in event.items() if key != "event_sha256"}
    )
    ledger["cumulative_events_sha256"] = content_sha256([event["event_sha256"]])
    ledger["ledger_sha256"] = content_sha256(
        {key: value for key, value in ledger.items() if key != "ledger_sha256"}
    )
    progress["private_ledger_sha256"] = ledger["ledger_sha256"]
    progress["cumulative_events_sha256"] = ledger["cumulative_events_sha256"]
    progress["event_head_sha256"] = event["event_sha256"]
    _write(ledger_path, ledger)
    _write(progress_path, progress)
    method = method_path.read_text(encoding="utf-8")
    method = method.replace(old_ledger_sha, ledger["ledger_sha256"])
    method = method.replace(old_event_sha, event["event_sha256"])
    method_path.write_text(method, encoding="utf-8")

    git("add", str(PUBLIC_PROGRESS_REFERENCE), str(PUBLIC_METHOD_REFERENCE))
    git("commit", "-qm", "synchronized malicious rewrite")
    with pytest.raises(AuthorityContractError, match="introduction commit's first parent"):
        check_catalog_decisions(isolated_root, expected_base_commit=base_commit)

    harmless.write_text("child after malicious rewrite\n", encoding="utf-8")
    git("add", "harmless.txt")
    git("commit", "-qm", "unchanged child after malicious rewrite")
    with pytest.raises(AuthorityContractError, match="introduction commit's first parent"):
        check_catalog_decisions(isolated_root, expected_base_commit=base_commit)

    harmless.write_text("grandchild after malicious rewrite\n", encoding="utf-8")
    git("add", "harmless.txt")
    git("commit", "-qm", "unchanged grandchild after malicious rewrite")
    with pytest.raises(AuthorityContractError, match="introduction commit's first parent"):
        check_catalog_decisions(isolated_root, expected_base_commit=base_commit)


def test_event_two_precommit_requires_external_exact_authorization(
    isolated_root: Path,
) -> None:
    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(isolated_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    git("init", "-q")
    git("config", "user.name", "CAR Test")
    git("config", "user.email", "car-test@example.invalid")
    git("add", ".")
    git("commit", "-qm", "base CAR-T4 fixture")
    base_commit = git("rev-parse", "HEAD")
    record_catalog_decision(
        isolated_root,
        candidate_id=CANDIDATE_ID,
        proposal_id=PROPOSAL_ID,
        decision=CatalogDecision.approve_catalog_record,
        owner_response_verbatim=OWNER_RESPONSE,
        reviewed_at=REVIEWED_AT,
        expected_base_commit=base_commit,
    )
    git("add", str(PUBLIC_PROGRESS_REFERENCE), str(PUBLIC_METHOD_REFERENCE))
    git("commit", "-qm", "anchor event 1 progress")

    record_catalog_decision(
        isolated_root,
        candidate_id=SECOND_CANDIDATE_ID,
        proposal_id=SECOND_PROPOSAL_ID,
        decision=CatalogDecision.approve_catalog_record,
        owner_response_verbatim=SECOND_OWNER_RESPONSE,
        authorized_exact_owner_response=SECOND_OWNER_RESPONSE,
        reviewed_at=REVIEWED_AT.replace(minute=31),
        expected_base_commit=base_commit,
    )
    expected = ExpectedOwnerAuthorization(
        ordinal=2,
        candidate_id=SECOND_CANDIDATE_ID,
        proposal_id=SECOND_PROPOSAL_ID,
        decision=CatalogDecision.approve_catalog_record,
        exact_owner_response=SECOND_OWNER_RESPONSE,
        review_reason=APPROVAL_REASON,
    )
    check_catalog_decisions(
        isolated_root,
        allow_uncommitted_current=True,
        expected_base_commit=base_commit,
        expected_uncommitted_authorization=expected,
    )
    with pytest.raises(AuthorityContractError, match="external expected owner authorization"):
        check_catalog_decisions(
            isolated_root,
            allow_uncommitted_current=True,
            expected_base_commit=base_commit,
        )

    wrong_expectations = [
        expected.model_copy(update={"candidate_id": CANDIDATE_ID}),
        expected.model_copy(update={"proposal_id": PROPOSAL_ID}),
        expected.model_copy(update={"decision": CatalogDecision.hold}),
        expected.model_copy(update={"review_reason": "Wrong bounded reason."}),
    ]
    for wrong in wrong_expectations:
        with pytest.raises(AuthorityContractError, match="external expected"):
            check_catalog_decisions(
                isolated_root,
                allow_uncommitted_current=True,
                expected_base_commit=base_commit,
                expected_uncommitted_authorization=wrong,
            )

    ledger_path = isolated_root / LEDGER_REFERENCE
    progress_path = isolated_root / PUBLIC_PROGRESS_REFERENCE
    method_path = isolated_root / PUBLIC_METHOD_REFERENCE
    originals = {
        ledger_path: ledger_path.read_bytes(),
        progress_path: progress_path.read_bytes(),
        method_path: method_path.read_bytes(),
    }
    ledger = _load(ledger_path)
    ledger["events"] = ledger["events"][:1]
    _write(ledger_path, ledger)
    with pytest.raises((AuthorityContractError, ValidationError, ValueError)):
        check_catalog_decisions(
            isolated_root,
            allow_uncommitted_current=True,
            expected_base_commit=base_commit,
            expected_uncommitted_authorization=expected,
        )
    for path, raw in originals.items():
        path.write_bytes(raw)

    ledger = _load(ledger_path)
    ledger["events"] = list(reversed(ledger["events"]))
    _write(ledger_path, ledger)
    with pytest.raises((AuthorityContractError, ValidationError, ValueError)):
        check_catalog_decisions(
            isolated_root,
            allow_uncommitted_current=True,
            expected_base_commit=base_commit,
            expected_uncommitted_authorization=expected,
        )
    for path, raw in originals.items():
        path.write_bytes(raw)

    ledger = _load(ledger_path)
    progress = _load(progress_path)
    event = ledger["events"][1]
    old_event_sha = event["event_sha256"]
    old_ledger_sha = ledger["ledger_sha256"]
    paraphrase = "批准第二筆，color 與 edition 保持 null。"
    event["owner_response_verbatim"] = paraphrase
    event["authorized_exact_owner_response"] = paraphrase
    authorization_body = {
        "authorization_contract_version": event["authorization_contract_version"],
        "candidate_id": event["candidate_id"],
        "proposal_id": event["proposal_id"],
        "decision": event["decision"],
        "authorized_exact_owner_response": paraphrase,
        "review_reason": event["review_reason"],
    }
    event["authorization_contract_sha256"] = content_sha256(authorization_body)
    event["event_sha256"] = content_sha256(
        {key: value for key, value in event.items() if key != "event_sha256"}
    )
    ledger["cumulative_events_sha256"] = content_sha256(
        [item["event_sha256"] for item in ledger["events"]]
    )
    ledger["ledger_sha256"] = content_sha256(
        {key: value for key, value in ledger.items() if key != "ledger_sha256"}
    )
    progress["private_ledger_sha256"] = ledger["ledger_sha256"]
    progress["cumulative_events_sha256"] = ledger["cumulative_events_sha256"]
    progress["event_head_sha256"] = event["event_sha256"]
    _write(ledger_path, ledger)
    _write(progress_path, progress)
    method = method_path.read_text(encoding="utf-8")
    method = method.replace(old_ledger_sha, ledger["ledger_sha256"])
    method = method.replace(old_event_sha, event["event_sha256"])
    method_path.write_text(method, encoding="utf-8")
    with pytest.raises(AuthorityContractError, match="external expected"):
        check_catalog_decisions(
            isolated_root,
            allow_uncommitted_current=True,
            expected_base_commit=base_commit,
            expected_uncommitted_authorization=expected,
        )


def test_cli_records_from_repo_root_and_check_is_read_only(isolated_root: Path) -> None:
    fake_bin = isolated_root / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  *"rev-parse --verify HEAD"*) echo {BASE_CAR_T4_COMMIT}; exit 0;;\n'
        f'  *"rev-list --parents -n 1 "*) echo {BASE_CAR_T4_COMMIT}; exit 0;;\n'
        '  *"show "*) echo "fatal: path does not exist in HEAD" >&2; exit 128;;\n'
        "esac\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    command = [
        str(ROOT / ".venv/bin/python"),
        str(ROOT / "scripts/record_canonical_catalog_proposal_decision.py"),
        "--root",
        str(isolated_root),
        "--candidate-id",
        CANDIDATE_ID,
        "--proposal-id",
        PROPOSAL_ID,
        "--decision",
        "approve_catalog_record",
        "--owner-response",
        OWNER_RESPONSE,
    ]
    recorded = subprocess.run(command, check=True, capture_output=True, text=True, env=environment)
    assert '"recorded": 1' in recorded.stdout
    before = {
        reference: (isolated_root / reference).read_bytes()
        for reference in (LEDGER_REFERENCE, PUBLIC_PROGRESS_REFERENCE, PUBLIC_METHOD_REFERENCE)
    }
    checked = subprocess.run(
        [
            *command[:4],
            "--check",
            "--allow-uncommitted-current",
            "--expected-ordinal",
            "1",
            "--expected-candidate-id",
            CANDIDATE_ID,
            "--expected-proposal-id",
            PROPOSAL_ID,
            "--expected-decision",
            "approve_catalog_record",
            "--expected-owner-response",
            OWNER_RESPONSE,
            "--expected-review-reason",
            APPROVAL_REASON,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert '"status": "valid"' in checked.stdout
    assert all((isolated_root / path).read_bytes() == raw for path, raw in before.items())
