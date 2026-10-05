"""Validate private owner review events and publish aggregate RHB-T6 progress."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import content_sha256, stable_json_bytes
from product_variant_resolver.representative_benchmark_label_review import (
    WORKSPACE_REFERENCE,
    StagedProposalFile,
    validate_materialized_label_review,
)

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
DECISIONS_DIRECTORY = WORKSPACE_REFERENCE / "owner-decisions"
PROGRESS_REFERENCE = RHB_DIRECTORY / "rhb-t6-label-review-progress-v1.json"

BATCH_01_REFERENCE = DECISIONS_DIRECTORY / "rhb-t6-review-batch-01.json"
BATCH_01_RAW_SHA256 = "278fe28661f490fa04268c0bfe5362f7466aa0cb1df0b79344ee5e990238cfa1"
BATCH_01_RESPONSE_SHA256 = "2374e622008d81e69d97b2c06ce0065f4504db989168eedb3d803cac1bc7e42e"
BATCH_02_REFERENCE = DECISIONS_DIRECTORY / "rhb-t6-review-batch-02.json"
BATCH_02_RAW_SHA256 = "5e3606523f31e59b732216a2936b9396a850aa0bc783fe9ff132e2b602f53b5f"
BATCH_02_RESPONSE_SHA256 = "f27dcc9c84729c96358ffa023cb7c511384658b9f134297f11d4534137d86d7d"
APPROVED_BATCHES = (
    (1, BATCH_01_REFERENCE, BATCH_01_RAW_SHA256, BATCH_01_RESPONSE_SHA256),
    (2, BATCH_02_REFERENCE, BATCH_02_RAW_SHA256, BATCH_02_RESPONSE_SHA256),
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class ReviewProgressError(ValueError):
    """Raised when owner decisions or aggregate progress are stale or unsafe."""


class StrictProgressModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OwnerCaseDecision(StrictProgressModel):
    case_id: NonBlank
    decision: Literal["approved_label", "held"]
    expected_status: Literal["matched", "ambiguous", "no_match"] | None
    verified_challenge_tags: list[NonBlank] = Field(max_length=0)
    review_reason_code: Literal[
        "owner_confirmed_frozen_catalog_relative_no_match",
        "owner_confirmed_insufficient_evidence_hold",
    ]

    @model_validator(mode="after")
    def decision_is_coherent(self) -> OwnerCaseDecision:
        if self.decision == "held":
            if self.expected_status is not None:
                raise ValueError("held decision cannot carry an expected status")
            if self.review_reason_code != "owner_confirmed_insufficient_evidence_hold":
                raise ValueError("held decision has the wrong reason")
        elif (
            self.expected_status != "no_match"
            or self.review_reason_code != "owner_confirmed_frozen_catalog_relative_no_match"
        ):
            raise ValueError("current approved decision must be catalog-relative no_match")
        return self


class OwnerReviewBatch(StrictProgressModel):
    schema_version: Literal["pvr-rhb-t6-owner-review-batch-v1"]
    batch_id: NonBlank
    batch_number: int = Field(ge=1)
    decision_date: Literal["2026-10-05"]
    reviewed_by: Literal["project_owner"]
    owner_response: NonBlank
    owner_response_sha256: Sha256
    parent_proposals_sha256: Sha256
    case_decisions: list[OwnerCaseDecision] = Field(min_length=1)
    matched_approved_count: Literal[0]
    provisional_challenge_tags_verified: Literal[False]
    labels_materialized: Literal[False]
    rhb_t7_authorized: Literal[False]
    split_authorized: Literal[False]
    scoring_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    batch_decision_sha256: Sha256

    @model_validator(mode="after")
    def batch_is_ordered_and_hash_bound(self) -> OwnerReviewBatch:
        case_ids = [decision.case_id for decision in self.case_decisions]
        if case_ids != sorted(set(case_ids)):
            raise ValueError("owner batch cases must be unique and ordered")
        response_sha256 = hashlib.sha256(self.owner_response.encode()).hexdigest()
        if response_sha256 != self.owner_response_sha256:
            raise ValueError("owner response checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"batch_decision_sha256"}))
        if expected != self.batch_decision_sha256:
            raise ValueError("owner batch decision checksum is stale")
        return self


class LabelReviewProgress(StrictProgressModel):
    schema_version: Literal["pvr-rhb-t6-label-review-progress-v1"]
    review_version: Literal["representative-hard-benchmark-rhb-t6-review-v1"]
    progress_date: Literal["2026-10-05"]
    status: Literal["owner_review_in_progress"]
    generated_by: Literal["scripts/build_representative_hard_benchmark_review_progress.py"]
    publication_scope: Literal["aggregate_only"]
    staging_manifest_sha256: Sha256
    private_batch_file_sha256s: list[Sha256]
    private_decision_ledger_sha256: Sha256
    decision_batch_count: int = Field(ge=1)
    latest_batch_number: int = Field(ge=1)
    total_record_count: Literal[60]
    owner_reviewed_case_count: int = Field(ge=0, le=60)
    owner_approved_decision_count: int = Field(ge=0, le=60)
    owner_held_decision_count: int = Field(ge=0, le=60)
    remaining_staged_count: int = Field(ge=0, le=60)
    approved_status_counts: dict[str, int]
    verified_challenge_tag_count: Literal[0]
    matched_approved_count: Literal[0]
    labels_materialized: Literal[False]
    row_level_data_public: Literal[False]
    rhb_t7_authorized: Literal[False]
    split_authorized: Literal[False]
    scoring_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    next_allowed_action: Literal[
        "present_rhb_t6_review_batch_02",
        "present_rhb_t6_review_batch_03",
        "present_rhb_t6_review_batch_04",
        "present_rhb_t6_review_batch_05",
        "present_rhb_t6_review_batch_06",
        "request_separate_label_materialization_gate",
    ]
    progress_sha256: Sha256

    @model_validator(mode="after")
    def progress_is_recomputable_and_hash_bound(self) -> LabelReviewProgress:
        if self.decision_batch_count != len(self.private_batch_file_sha256s):
            raise ValueError("progress batch count is inconsistent")
        if self.owner_reviewed_case_count != (
            self.owner_approved_decision_count + self.owner_held_decision_count
        ):
            raise ValueError("reviewed count is inconsistent")
        if self.owner_reviewed_case_count + self.remaining_staged_count != self.total_record_count:
            raise ValueError("progress counts do not cover all 60 cases")
        if set(self.approved_status_counts) != {"ambiguous", "matched", "no_match"}:
            raise ValueError("approved status-count keys changed")
        if sum(self.approved_status_counts.values()) != self.owner_approved_decision_count:
            raise ValueError("approved status counts are inconsistent")
        if self.approved_status_counts["matched"] != self.matched_approved_count:
            raise ValueError("matched approved count is inconsistent")
        expected = content_sha256(self.model_dump(mode="json", exclude={"progress_sha256"}))
        if expected != self.progress_sha256:
            raise ValueError("review progress checksum is stale")
        return self


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReviewProgressError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReviewProgressError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise ReviewProgressError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ReviewProgressError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewProgressError(message)


def _load_batches(root: Path, proposals: StagedProposalFile) -> list[OwnerReviewBatch]:
    decisions_directory = root / DECISIONS_DIRECTORY
    _expect(
        decisions_directory.is_dir()
        and not decisions_directory.is_symlink()
        and stat.S_IMODE(decisions_directory.stat().st_mode) == 0o700,
        "owner-decisions directory must remain a real 0700 directory",
    )
    proposal_ids = {proposal.case_id for proposal in proposals.proposals}
    batches: list[OwnerReviewBatch] = []
    seen_case_ids: set[str] = set()
    for number, reference, expected_raw_sha256, expected_response_sha256 in APPROVED_BATCHES:
        path = root / reference
        _expect(
            path.is_file() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o600,
            f"owner decision batch {number} must remain a real 0600 file",
        )
        _expect(_raw_sha256(path) == expected_raw_sha256, f"owner decision batch {number} drift")
        batch = OwnerReviewBatch.model_validate(_load_object(path))
        _expect(batch.batch_number == number, "owner decision batch number changed")
        _expect(
            batch.owner_response_sha256 == expected_response_sha256,
            f"owner decision batch {number} response is not authorized",
        )
        _expect(
            batch.parent_proposals_sha256 == proposals.proposals_sha256,
            f"owner decision batch {number} references different proposals",
        )
        case_ids = {decision.case_id for decision in batch.case_decisions}
        _expect(case_ids <= proposal_ids, f"owner decision batch {number} references unknown cases")
        _expect(not case_ids & seen_case_ids, "owner decision batches overlap")
        seen_case_ids.update(case_ids)
        batches.append(batch)
    return batches


def _build_review_progress(root: Path, *, batch_limit: int | None = None) -> LabelReviewProgress:
    root = root.absolute()
    _evidence, proposals, staging_manifest = validate_materialized_label_review(root)
    batches = _load_batches(root, proposals)
    private_hashes = [raw_sha256 for _, _, raw_sha256, _ in APPROVED_BATCHES]
    if batch_limit is not None:
        _expect(1 <= batch_limit <= len(batches), "review progress batch limit is invalid")
        batches = batches[:batch_limit]
        private_hashes = private_hashes[:batch_limit]
    decisions = [decision for batch in batches for decision in batch.case_decisions]
    approved = [decision for decision in decisions if decision.decision == "approved_label"]
    status_counts: Counter[str] = Counter(
        decision.expected_status for decision in approved if decision.expected_status is not None
    )
    ledger_sha256 = content_sha256(
        [
            {
                "batch_number": batch.batch_number,
                "batch_decision_sha256": batch.batch_decision_sha256,
                "raw_sha256": private_hashes[index],
            }
            for index, batch in enumerate(batches)
        ]
    )
    body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-label-review-progress-v1",
        "review_version": "representative-hard-benchmark-rhb-t6-review-v1",
        "progress_date": "2026-10-05",
        "status": "owner_review_in_progress",
        "generated_by": "scripts/build_representative_hard_benchmark_review_progress.py",
        "publication_scope": "aggregate_only",
        "staging_manifest_sha256": staging_manifest.manifest_sha256,
        "private_batch_file_sha256s": private_hashes,
        "private_decision_ledger_sha256": ledger_sha256,
        "decision_batch_count": len(batches),
        "latest_batch_number": batches[-1].batch_number,
        "total_record_count": 60,
        "owner_reviewed_case_count": len(decisions),
        "owner_approved_decision_count": len(approved),
        "owner_held_decision_count": sum(decision.decision == "held" for decision in decisions),
        "remaining_staged_count": 60 - len(decisions),
        "approved_status_counts": {
            status: status_counts.get(status, 0) for status in ("ambiguous", "matched", "no_match")
        },
        "verified_challenge_tag_count": 0,
        "matched_approved_count": 0,
        "labels_materialized": False,
        "row_level_data_public": False,
        "rhb_t7_authorized": False,
        "split_authorized": False,
        "scoring_authorized": False,
        "resolver_evaluation_authorized": False,
        "next_allowed_action": (
            f"present_rhb_t6_review_batch_{len(batches) + 1:02}"
            if len(decisions) < 60
            else "request_separate_label_materialization_gate"
        ),
    }
    return LabelReviewProgress.model_validate({**body, "progress_sha256": content_sha256(body)})


def build_review_progress(root: Path) -> LabelReviewProgress:
    """Build the aggregate-only progress artifact from exact private owner events."""

    return _build_review_progress(root)


def _load_materialized_progress(path: Path) -> LabelReviewProgress:
    _expect(path.is_file() and not path.is_symlink(), "review progress is absent or unsafe")
    _expect(stat.S_IMODE(path.stat().st_mode) == 0o644, "review progress must use mode 0644")
    actual = LabelReviewProgress.model_validate(_load_object(path))
    _expect(
        path.read_bytes() == stable_json_bytes(actual.model_dump(mode="json")),
        "review progress bytes are non-canonical",
    )
    return actual


def validate_materialized_review_progress(root: Path) -> LabelReviewProgress:
    """Validate public aggregate progress against all private decision parents."""

    root = root.absolute()
    expected = build_review_progress(root)
    path = root / PROGRESS_REFERENCE
    actual = _load_materialized_progress(path)
    _expect(actual == expected, "materialized review progress is stale or tampered")
    return actual


def materialize_review_progress(
    root: Path, *, check: bool = False
) -> Literal["created", "updated", "unchanged"]:
    """Create, append-update, or validate progress without materializing labels."""

    root = root.absolute()
    progress = build_review_progress(root)
    path = root / PROGRESS_REFERENCE
    expected = stable_json_bytes(progress.model_dump(mode="json"))
    outcome: Literal["created", "updated"] = "created"
    if path.exists():
        actual = _load_materialized_progress(path)
        if actual == progress:
            return "unchanged"
        if check:
            raise ReviewProgressError("review progress is stale")
        _expect(
            actual.decision_batch_count < progress.decision_batch_count,
            "review progress cannot be rewritten or reduced",
        )
        historical = _build_review_progress(root, batch_limit=actual.decision_batch_count)
        _expect(actual == historical, "existing review progress is not an append-only prefix")
        outcome = "updated"
    if check:
        raise ReviewProgressError("review progress is not materialized")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, path)
        os.chmod(path, 0o644)
        validate_materialized_review_progress(root)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return outcome


__all__ = [
    "BATCH_01_REFERENCE",
    "BATCH_02_REFERENCE",
    "DECISIONS_DIRECTORY",
    "PROGRESS_REFERENCE",
    "LabelReviewProgress",
    "OwnerReviewBatch",
    "ReviewProgressError",
    "build_review_progress",
    "materialize_review_progress",
    "validate_materialized_review_progress",
]
