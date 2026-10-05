"""Governed development-only three-class calibration for the Pointwise resolver."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

from .calibration import CalibrationArtifact, features, train_logistic
from .image_search_evaluation import (
    AUTHORITY_NOTE,
    DATASET,
    FROZEN_DATASET_SHA256,
    FROZEN_SPLIT_SHA256,
)
from .image_search_pointwise_calibration import (
    FROZEN_INNER_SPLIT_SHA256,
    CalibrationRow,
    PointwiseScoringContext,
    ThresholdSelection,
    _probability,
    collect_development_rows,
    load_pointwise_scoring_context,
    score_pointwise_query,
    select_threshold,
)
from .image_search_ranking_development import (
    POINTWISE_MODEL,
)
from .image_search_ranking_development import (
    SELECTION as POSITIVE_DEVELOPMENT_SELECTION,
)
from .pointwise_no_match_governance import (
    AUTHORIZATION_PATH,
    CANDIDATE_SET_SHA256,
    OVERLAY_PATH,
    SPLIT_ASSIGNMENT_SHA256,
)
from .pointwise_no_match_governance import (
    check as check_governance,
)
from .pointwise_no_match_readiness import (
    FIT_COUNT as NEGATIVE_FIT_COUNT,
)
from .pointwise_no_match_readiness import (
    HUMAN_DATASET,
    HUMAN_DATASET_SHA256,
    SOURCE,
    SOURCE_SHA256,
    _load_object,
    _prospective_split,
    classify_candidates,
)
from .pointwise_no_match_readiness import (
    OUTPUT as READINESS_PATH,
)
from .pointwise_no_match_readiness import (
    SELECTION_COUNT as NEGATIVE_SELECTION_COUNT,
)
from .policy import DecisionPolicy

VERSION = "image-search-pointwise-calibration-v2"
SCHEMA_VERSION = "pvr-image-search-pointwise-three-class-selection-v1"
DIRECTORY = Path("data/evaluation/image-search-pointwise-calibration-v2")
CALIBRATION_PATH = DIRECTORY / "calibration.json"
POLICY_PATH = DIRECTORY / "policy.json"
SELECTION_PATH = DIRECTORY / "selection.json"
POSITIVE_FIT_COUNT = 70
POSITIVE_SELECTION_COUNT = 30
MATCH_MINIMUM_ACCEPTED = 5
MATCH_MINIMUM_PRECISION = 0.90
NO_MATCH_MINIMUM_ACCEPTED = 5
NO_MATCH_MINIMUM_PRECISION = 0.90
MAXIMUM_FALSE_NO_MATCH_RATE = 0.10

Truth = Literal["catalog_present", "catalog_relative_no_match"]
Partition = Literal["calibration_fit", "threshold_selection"]


@dataclass(frozen=True, slots=True)
class ThreeClassRow:
    case_id: str
    partition: Partition
    truth: Truth
    vector: tuple[float, ...]
    exact_top1_correct: int


@dataclass(frozen=True, slots=True)
class NoMatchThresholdSelection:
    threshold: float
    predicted_count: int
    correct_count: int
    precision: float
    recall: float
    catalog_present_false_count: int
    catalog_present_false_rate: float


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _positive_row(row: CalibrationRow) -> ThreeClassRow:
    return ThreeClassRow(
        case_id=row.case_id,
        partition=row.partition,
        truth="catalog_present",
        vector=row.vector,
        exact_top1_correct=row.exact_top1_correct,
    )


def collect_no_match_rows(root: Path, context: PointwiseScoringContext) -> list[ThreeClassRow]:
    check_governance(root)
    human = _load_object(root / HUMAN_DATASET)
    source = _load_object(root / SOURCE)
    human_records = human.get("records")
    source_records = source.get("records")
    if not isinstance(human_records, list) or not isinstance(source_records, list):
        raise TypeError("PNMR-G1 inputs must contain record arrays")
    candidates, _counts = classify_candidates(human_records, source_records)
    assignment, assignment_sha256 = _prospective_split(candidates)
    if assignment_sha256 != SPLIT_ASSIGNMENT_SHA256:
        raise ValueError("PNMR-G1 no-match split differs from the authorized split")
    raw_query_by_case: dict[str, str] = {}
    for raw in human_records:
        if not isinstance(raw, dict):
            raise TypeError("human record must be an object")
        case_id = raw.get("case_id")
        query = raw.get("initial_name")
        if isinstance(case_id, str) and isinstance(query, str) and query.strip():
            raw_query_by_case[case_id] = query.strip()

    rows = []
    for candidate in candidates:
        query = raw_query_by_case.get(candidate.case_id)
        if query is None:
            raise ValueError("authorized no-match candidate has no frozen raw query")
        ranked = score_pointwise_query(context, query)
        rows.append(
            ThreeClassRow(
                case_id=candidate.case_id,
                partition=assignment[candidate.case_id],
                truth="catalog_relative_no_match",
                vector=features(ranked),
                exact_top1_correct=0,
            )
        )
    if len(rows) != NEGATIVE_FIT_COUNT + NEGATIVE_SELECTION_COUNT:
        raise ValueError("PNMR-G1 no-match row count changed")
    return rows


def collect_combined_rows(root: Path) -> list[ThreeClassRow]:
    context = load_pointwise_scoring_context(root)
    positive_rows, positive_split_sha256 = collect_development_rows(root, context=context)
    if positive_split_sha256 != FROZEN_INNER_SPLIT_SHA256:
        raise ValueError("positive development split differs from the frozen assignment")
    negative_rows = collect_no_match_rows(root, context)
    rows = [_positive_row(row) for row in positive_rows] + negative_rows
    if len({row.case_id for row in rows}) != len(rows):
        raise ValueError("combined calibration rows contain duplicate case IDs")
    return rows


def select_no_match_threshold(
    rows: list[tuple[float, bool]],
    *,
    match_threshold: float,
    minimum_accepted: int = NO_MATCH_MINIMUM_ACCEPTED,
    minimum_precision: float = NO_MATCH_MINIMUM_PRECISION,
    maximum_false_no_match_rate: float = MAXIMUM_FALSE_NO_MATCH_RATE,
) -> NoMatchThresholdSelection:
    if not rows or not 0 < match_threshold <= 1:
        raise ValueError("no-match selection requires rows and a valid match threshold")
    if minimum_accepted < 1 or not 0 < minimum_precision <= 1:
        raise ValueError("no-match selection constraints are invalid")
    if not 0 <= maximum_false_no_match_rate <= 1:
        raise ValueError("false-no-match limit must be between zero and one")
    if any(not 0 <= confidence <= 1 for confidence, _is_no_match in rows):
        raise ValueError("no-match confidence must be between zero and one")
    no_match_total = sum(is_no_match for _confidence, is_no_match in rows)
    catalog_present_total = len(rows) - no_match_total
    if not no_match_total or not catalog_present_total:
        raise ValueError("no-match selection requires both truth classes")

    thresholds = {
        math.nextafter(confidence, 1.0)
        for confidence, _is_no_match in rows
        if confidence < match_threshold
    }
    eligible: list[NoMatchThresholdSelection] = []
    for threshold in sorted(thresholds):
        predicted = [is_no_match for confidence, is_no_match in rows if confidence < threshold]
        correct = sum(predicted)
        false_count = len(predicted) - correct
        precision = correct / len(predicted)
        recall = correct / no_match_total
        false_rate = false_count / catalog_present_total
        if (
            len(predicted) >= minimum_accepted
            and precision >= minimum_precision
            and false_rate <= maximum_false_no_match_rate
        ):
            eligible.append(
                NoMatchThresholdSelection(
                    threshold=threshold,
                    predicted_count=len(predicted),
                    correct_count=correct,
                    precision=precision,
                    recall=recall,
                    catalog_present_false_count=false_count,
                    catalog_present_false_rate=false_rate,
                )
            )
    if not eligible:
        raise ValueError("development selection cannot meet the frozen no-match gate")
    return max(
        eligible,
        key=lambda item: (
            item.recall,
            -item.catalog_present_false_count,
            item.precision,
            -item.threshold,
        ),
    )


def fit_three_class_calibration(
    rows: list[ThreeClassRow],
) -> tuple[CalibrationArtifact, DecisionPolicy | None, dict[str, Any], list[str]]:
    fit_rows = [row for row in rows if row.partition == "calibration_fit"]
    selection_rows = [row for row in rows if row.partition == "threshold_selection"]
    expected_fit = POSITIVE_FIT_COUNT + NEGATIVE_FIT_COUNT
    expected_selection = POSITIVE_SELECTION_COUNT + NEGATIVE_SELECTION_COUNT
    if len(fit_rows) != expected_fit or len(selection_rows) != expected_selection:
        raise ValueError("combined calibration partitions have the wrong counts")
    fit_truth_counts = {
        truth: sum(row.truth == truth for row in fit_rows)
        for truth in ("catalog_present", "catalog_relative_no_match")
    }
    selection_truth_counts = {
        truth: sum(row.truth == truth for row in selection_rows)
        for truth in ("catalog_present", "catalog_relative_no_match")
    }
    if fit_truth_counts != {
        "catalog_present": POSITIVE_FIT_COUNT,
        "catalog_relative_no_match": NEGATIVE_FIT_COUNT,
    } or selection_truth_counts != {
        "catalog_present": POSITIVE_SELECTION_COUNT,
        "catalog_relative_no_match": NEGATIVE_SELECTION_COUNT,
    }:
        raise ValueError("combined calibration truth composition changed")

    artifact = train_logistic(
        [(row.vector, row.exact_top1_correct) for row in fit_rows],
        VERSION,
        split="train",
        iterations=2_000,
        learning_rate=0.01,
    )
    artifact = replace(
        artifact,
        model_version="logistic-python-v2+neural-pointwise-v1+catalog-relative-no-match-v1",
        artifact_version=VERSION,
    )
    scored = [(_probability(artifact, row.vector), row) for row in selection_rows]
    shortfalls: list[str] = []
    match: ThresholdSelection | None = None
    no_match: NoMatchThresholdSelection | None = None
    try:
        match = select_threshold(
            [(confidence, row.exact_top1_correct) for confidence, row in scored],
            minimum_precision=MATCH_MINIMUM_PRECISION,
            minimum_accepted=MATCH_MINIMUM_ACCEPTED,
        )
    except ValueError:
        shortfalls.append("match_gate_unmet")
    if match is not None:
        try:
            no_match = select_no_match_threshold(
                [
                    (confidence, row.truth == "catalog_relative_no_match")
                    for confidence, row in scored
                ],
                match_threshold=match.threshold,
            )
        except ValueError:
            shortfalls.append("no_match_gate_unmet")
    else:
        shortfalls.append("no_match_gate_not_evaluated_without_match_threshold")

    policy = None
    if match is not None and no_match is not None:
        policy = DecisionPolicy(
            version="image-search-development-neural-pointwise-v2",
            match_threshold=match.threshold,
            no_match_threshold=no_match.threshold,
            margin_threshold=0.0,
            max_conflicts=5,
            require_positive_top_score=False,
            runtime_eligible=False,
        )
    match_predicted = 0 if match is None else match.accepted_count
    match_correct = 0 if match is None else match.accepted_correct
    no_match_predicted = 0 if no_match is None else no_match.predicted_count
    no_match_correct = 0 if no_match is None else no_match.correct_count
    brier = sum((confidence - row.exact_top1_correct) ** 2 for confidence, row in scored) / len(
        scored
    )
    metrics: dict[str, Any] = {
        "fit": {
            "sample_count": len(fit_rows),
            "catalog_present_count": fit_truth_counts["catalog_present"],
            "catalog_relative_no_match_count": fit_truth_counts["catalog_relative_no_match"],
            "exact_top1_correct": sum(row.exact_top1_correct for row in fit_rows),
        },
        "threshold_selection": {
            "sample_count": len(selection_rows),
            "catalog_present_count": selection_truth_counts["catalog_present"],
            "catalog_relative_no_match_count": selection_truth_counts["catalog_relative_no_match"],
            "exact_top1_correct": sum(row.exact_top1_correct for row in selection_rows),
            "match": None
            if match is None
            else {
                "threshold": match.threshold,
                "predicted_count": match_predicted,
                "correct_count": match_correct,
                "precision": match.precision,
                "coverage": match.coverage,
            },
            "no_match": None
            if no_match is None
            else {
                "threshold": no_match.threshold,
                "predicted_count": no_match_predicted,
                "correct_count": no_match_correct,
                "precision": no_match.precision,
                "recall": no_match.recall,
                "catalog_present_false_count": no_match.catalog_present_false_count,
                "catalog_present_false_rate": no_match.catalog_present_false_rate,
            },
            "ambiguous_count": len(selection_rows) - match_predicted - no_match_predicted,
            "brier_score": brier,
        },
    }
    return artifact, policy, metrics, shortfalls


def _contains_row_level_key(value: object) -> bool:
    forbidden = {
        "case",
        "case_id",
        "case_ids",
        "cases",
        "query",
        "queries",
        "prediction",
        "predictions",
        "records",
        "labels",
        "assignment",
    }
    if isinstance(value, dict):
        return any(key in forbidden or _contains_row_level_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def materialize(root: Path) -> dict[str, Any]:
    paths = (root / CALIBRATION_PATH, root / POLICY_PATH, root / SELECTION_PATH)
    if any(path.exists() for path in paths):
        raise FileExistsError("three-class calibration artifacts already exist")
    overlay = check_governance(root)
    rows = collect_combined_rows(root)
    artifact, policy, metrics, shortfalls = fit_three_class_calibration(rows)
    directory = root / DIRECTORY
    directory.mkdir(parents=True, exist_ok=False)
    calibration_bytes = _canonical_bytes(asdict(artifact))
    (root / CALIBRATION_PATH).write_bytes(calibration_bytes)
    policy_sha256: str | None = None
    if policy is not None:
        policy_bytes = _canonical_bytes(asdict(policy))
        (root / POLICY_PATH).write_bytes(policy_bytes)
        policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "development_three_class_calibrated_not_runtime_authorized"
            if policy is not None
            else "development_three_class_gate_shortfall"
        ),
        "inputs": {
            "positive_dataset_path": str(DATASET),
            "positive_dataset_sha256": FROZEN_DATASET_SHA256,
            "positive_outer_split_sha256": FROZEN_SPLIT_SHA256,
            "positive_inner_split_sha256": FROZEN_INNER_SPLIT_SHA256,
            "positive_development_selection_sha256": _sha256(root / POSITIVE_DEVELOPMENT_SELECTION),
            "human_dataset_path": str(HUMAN_DATASET),
            "human_dataset_sha256": HUMAN_DATASET_SHA256,
            "no_match_candidate_set_sha256": CANDIDATE_SET_SHA256,
            "no_match_split_assignment_sha256": SPLIT_ASSIGNMENT_SHA256,
            "catalog_snapshot_path": str(SOURCE),
            "catalog_snapshot_sha256": SOURCE_SHA256,
            "readiness_sha256": _sha256(root / READINESS_PATH),
            "owner_authorization_sha256": _sha256(root / AUTHORIZATION_PATH),
            "governance_overlay_sha256": _sha256(root / OVERLAY_PATH),
            "governance_overlay_content_sha256": overlay["overlay_sha256"],
            "pointwise_model_manifest_sha256": _sha256(root / POINTWISE_MODEL / "manifest.json"),
        },
        "composition": {
            "fit": {
                "catalog_present": POSITIVE_FIT_COUNT,
                "catalog_relative_no_match": NEGATIVE_FIT_COUNT,
            },
            "threshold_selection": {
                "catalog_present": POSITIVE_SELECTION_COUNT,
                "catalog_relative_no_match": NEGATIVE_SELECTION_COUNT,
            },
        },
        "gates": {
            "match_minimum_accepted": MATCH_MINIMUM_ACCEPTED,
            "match_minimum_precision": MATCH_MINIMUM_PRECISION,
            "no_match_minimum_accepted": NO_MATCH_MINIMUM_ACCEPTED,
            "no_match_minimum_precision": NO_MATCH_MINIMUM_PRECISION,
            "maximum_false_no_match_rate": MAXIMUM_FALSE_NO_MATCH_RATE,
        },
        "artifacts": {
            "calibration_path": str(CALIBRATION_PATH),
            "calibration_sha256": hashlib.sha256(calibration_bytes).hexdigest(),
            "policy_path": str(POLICY_PATH) if policy is not None else None,
            "policy_sha256": policy_sha256,
        },
        "metrics": metrics,
        "shortfalls": shortfalls,
        "guardrails": {
            "row_level_output_persisted": False,
            "final_test_cases_read": 0,
            "final_test_cases_scored": 0,
            "final_test_retuning_performed": False,
            "runtime_default_changed": False,
            "runtime_activation_authorized": False,
            "runtime_eligible": False,
        },
        "authority_note": AUTHORITY_NOTE,
        "next_allowed_action": (
            "review_development_three_class_metrics_before_any_runtime_gate"
            if policy is not None
            else "collect_or_revise_development_evidence_without_using_final_test"
        ),
    }
    (root / SELECTION_PATH).write_bytes(_canonical_bytes(payload))
    return payload


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def check(root: Path, *, require_local_inputs: bool = False) -> dict[str, Any]:
    payload = _load_object(root / SELECTION_PATH)
    if _contains_row_level_key(payload):
        raise ValueError("three-class calibration artifact contains row-level output")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("three-class calibration schema changed")
    if payload.get("status") not in {
        "development_three_class_calibrated_not_runtime_authorized",
        "development_three_class_gate_shortfall",
    }:
        raise ValueError("three-class calibration status changed")
    inputs = payload.get("inputs")
    artifacts = payload.get("artifacts")
    metrics = payload.get("metrics")
    guardrails = payload.get("guardrails")
    shortfalls = payload.get("shortfalls")
    composition = payload.get("composition")
    gates = payload.get("gates")
    if not all(
        isinstance(item, dict)
        for item in (inputs, artifacts, metrics, guardrails, composition, gates)
    ):
        raise TypeError("three-class calibration sections must be objects")
    if not isinstance(shortfalls, list) or any(not isinstance(item, str) for item in shortfalls):
        raise TypeError("three-class calibration shortfalls must be strings")
    assert isinstance(inputs, dict)
    assert isinstance(artifacts, dict)
    assert isinstance(metrics, dict)
    assert isinstance(guardrails, dict)
    assert isinstance(composition, dict)
    assert isinstance(gates, dict)
    expected_inputs = {
        "positive_dataset_sha256": FROZEN_DATASET_SHA256,
        "positive_outer_split_sha256": FROZEN_SPLIT_SHA256,
        "positive_inner_split_sha256": FROZEN_INNER_SPLIT_SHA256,
        "human_dataset_sha256": HUMAN_DATASET_SHA256,
        "no_match_candidate_set_sha256": CANDIDATE_SET_SHA256,
        "no_match_split_assignment_sha256": SPLIT_ASSIGNMENT_SHA256,
        "catalog_snapshot_sha256": SOURCE_SHA256,
    }
    if any(inputs.get(key) != value for key, value in expected_inputs.items()):
        raise ValueError("three-class calibration input binding changed")
    expected_file_bindings = {
        "positive_dataset_sha256": root / DATASET,
        "positive_development_selection_sha256": root / POSITIVE_DEVELOPMENT_SELECTION,
        "human_dataset_sha256": root / HUMAN_DATASET,
        "readiness_sha256": root / READINESS_PATH,
        "owner_authorization_sha256": root / AUTHORIZATION_PATH,
        "governance_overlay_sha256": root / OVERLAY_PATH,
    }
    if any(inputs.get(key) != _sha256(path) for key, path in expected_file_bindings.items()):
        raise ValueError("three-class calibration tracked parent hash changed")
    if composition != {
        "fit": {
            "catalog_present": POSITIVE_FIT_COUNT,
            "catalog_relative_no_match": NEGATIVE_FIT_COUNT,
        },
        "threshold_selection": {
            "catalog_present": POSITIVE_SELECTION_COUNT,
            "catalog_relative_no_match": NEGATIVE_SELECTION_COUNT,
        },
    }:
        raise ValueError("three-class calibration composition changed")
    if gates != {
        "match_minimum_accepted": MATCH_MINIMUM_ACCEPTED,
        "match_minimum_precision": MATCH_MINIMUM_PRECISION,
        "no_match_minimum_accepted": NO_MATCH_MINIMUM_ACCEPTED,
        "no_match_minimum_precision": NO_MATCH_MINIMUM_PRECISION,
        "maximum_false_no_match_rate": MAXIMUM_FALSE_NO_MATCH_RATE,
    }:
        raise ValueError("three-class calibration gates changed")
    calibration_path = root / str(artifacts.get("calibration_path"))
    if artifacts.get("calibration_sha256") != _sha256(calibration_path):
        raise ValueError("three-class calibration hash changed")
    calibration = CalibrationArtifact.load(calibration_path)
    if (
        calibration.artifact_version != VERSION
        or calibration.model_version
        != "logistic-python-v2+neural-pointwise-v1+catalog-relative-no-match-v1"
    ):
        raise ValueError("three-class calibration artifact binding changed")
    fit_metrics = metrics.get("fit")
    selection = metrics.get("threshold_selection")
    if not isinstance(fit_metrics, dict) or not isinstance(selection, dict):
        raise TypeError("three-class metrics must be objects")
    if (
        _integer(fit_metrics.get("sample_count"), "fit sample count")
        != POSITIVE_FIT_COUNT + NEGATIVE_FIT_COUNT
        or _integer(fit_metrics.get("catalog_present_count"), "fit present count")
        != POSITIVE_FIT_COUNT
        or _integer(fit_metrics.get("catalog_relative_no_match_count"), "fit no-match count")
        != NEGATIVE_FIT_COUNT
        or not 0
        <= _integer(fit_metrics.get("exact_top1_correct"), "fit exact count")
        <= POSITIVE_FIT_COUNT
    ):
        raise ValueError("three-class fit metrics are inconsistent")
    if (
        _integer(selection.get("sample_count"), "selection sample count")
        != POSITIVE_SELECTION_COUNT + NEGATIVE_SELECTION_COUNT
        or _integer(selection.get("catalog_present_count"), "selection present count")
        != POSITIVE_SELECTION_COUNT
        or _integer(selection.get("catalog_relative_no_match_count"), "selection no-match count")
        != NEGATIVE_SELECTION_COUNT
        or not 0
        <= _integer(selection.get("exact_top1_correct"), "selection exact count")
        <= POSITIVE_SELECTION_COUNT
        or not 0 <= _number(selection.get("brier_score"), "selection brier") <= 1
    ):
        raise ValueError("three-class selection metrics are inconsistent")
    match = selection.get("match")
    no_match = selection.get("no_match")
    success = payload["status"] == "development_three_class_calibrated_not_runtime_authorized"
    if success:
        if shortfalls or not isinstance(match, dict) or not isinstance(no_match, dict):
            raise ValueError("successful three-class calibration has missing gates")
        match_predicted = _integer(match.get("predicted_count"), "match count")
        match_correct = _integer(match.get("correct_count"), "match correct count")
        match_precision = _number(match.get("precision"), "match precision")
        match_coverage = _number(match.get("coverage"), "match coverage")
        no_match_predicted = _integer(no_match.get("predicted_count"), "no-match count")
        no_match_correct = _integer(no_match.get("correct_count"), "no-match correct count")
        no_match_precision = _number(no_match.get("precision"), "no-match precision")
        no_match_recall = _number(no_match.get("recall"), "no-match recall")
        false_count = _integer(no_match.get("catalog_present_false_count"), "false no-match count")
        false_rate = _number(no_match.get("catalog_present_false_rate"), "false no-match rate")
        ambiguous = _integer(selection.get("ambiguous_count"), "ambiguous count")
        if (
            match_predicted < MATCH_MINIMUM_ACCEPTED
            or not 0 <= match_correct <= match_predicted
            or match_precision < MATCH_MINIMUM_PRECISION
            or not math.isclose(
                match_precision,
                match_correct / match_predicted,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or not math.isclose(
                match_coverage,
                match_predicted / (POSITIVE_SELECTION_COUNT + NEGATIVE_SELECTION_COUNT),
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or no_match_predicted < NO_MATCH_MINIMUM_ACCEPTED
            or not 0 <= no_match_correct <= no_match_predicted
            or no_match_precision < NO_MATCH_MINIMUM_PRECISION
            or not math.isclose(
                no_match_precision,
                no_match_correct / no_match_predicted,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or not math.isclose(
                no_match_recall,
                no_match_correct / NEGATIVE_SELECTION_COUNT,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or false_count != no_match_predicted - no_match_correct
            or false_rate > MAXIMUM_FALSE_NO_MATCH_RATE
            or not math.isclose(
                false_rate,
                false_count / POSITIVE_SELECTION_COUNT,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or ambiguous
            != POSITIVE_SELECTION_COUNT
            + NEGATIVE_SELECTION_COUNT
            - match_predicted
            - no_match_predicted
        ):
            raise ValueError("three-class calibration gate metrics are below contract")
        policy_path_value = artifacts.get("policy_path")
        if not isinstance(policy_path_value, str):
            raise TypeError("successful three-class calibration must publish a policy")
        policy_path = root / policy_path_value
        if artifacts.get("policy_sha256") != _sha256(policy_path):
            raise ValueError("three-class policy hash changed")
        policy = DecisionPolicy.load(policy_path)
        if (
            policy.version != "image-search-development-neural-pointwise-v2"
            or policy.runtime_eligible
            or policy.no_match_threshold != _number(no_match.get("threshold"), "no-match threshold")
            or policy.match_threshold != _number(match.get("threshold"), "match threshold")
            or not policy.no_match_threshold < policy.match_threshold
        ):
            raise ValueError("three-class policy contract changed")
    elif not shortfalls or artifacts.get("policy_path") is not None:
        raise ValueError("three-class shortfall must omit the policy")
    expected_guardrails = {
        "row_level_output_persisted": False,
        "final_test_cases_read": 0,
        "final_test_cases_scored": 0,
        "final_test_retuning_performed": False,
        "runtime_default_changed": False,
        "runtime_activation_authorized": False,
        "runtime_eligible": False,
    }
    if guardrails != expected_guardrails:
        raise ValueError("three-class calibration guardrails changed")
    if require_local_inputs:
        check_governance(root)
        if _sha256(root / HUMAN_DATASET) != HUMAN_DATASET_SHA256:
            raise ValueError("three-class human dataset bytes changed")
        if _sha256(root / SOURCE) != SOURCE_SHA256:
            raise ValueError("three-class catalog snapshot bytes changed")
        model_manifest = root / POINTWISE_MODEL / "manifest.json"
        if inputs.get("pointwise_model_manifest_sha256") != _sha256(model_manifest):
            raise ValueError("three-class Pointwise model binding changed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calibrate governed three-class Pointwise decisions"
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-development-only", action="store_true")
    parser.add_argument("--acknowledge-no-runtime-activation", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if not args.acknowledge_development_only or not args.acknowledge_no_runtime_activation:
            parser.error(
                "--run requires --acknowledge-development-only and "
                "--acknowledge-no-runtime-activation"
            )
        payload = materialize(root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if args.check:
        check(root, require_local_inputs=(root / SOURCE).exists())
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
