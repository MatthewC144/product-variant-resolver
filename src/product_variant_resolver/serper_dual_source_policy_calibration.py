"""Development-only calibration for paired Image/Lens and Shopping queries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from .calibration import FEATURE_SCHEMA, CalibrationArtifact, features, train_logistic
from .identity import normalize_text
from .image_search_evaluation import (
    SOURCE,
    SOURCE_COUNT,
    ExpectedFullIdentity,
    ImageSearchCase,
    ImageSearchDataset,
    bind_dataset_to_source,
    load_source_records,
)
from .image_search_pointwise_calibration import (
    PointwiseScoringContext,
    load_pointwise_scoring_context,
    score_pointwise_query,
    select_threshold,
)
from .image_search_ranking_development import POINTWISE_MODEL
from .pointwise_three_class_calibration import select_no_match_threshold
from .policy import DecisionPolicy
from .schemas import StrictModel
from .serper_dual_source_evaluation import (
    DATASET as POSITIVE_DATASET,
)
from .serper_dual_source_evaluation import (
    FROZEN_DATASET_SHA256 as POSITIVE_DATASET_SHA256,
)
from .serper_dual_source_evaluation import (
    FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
    FROZEN_SPLIT_SHA256,
    RAW_POINTWISE_DEVELOPMENT,
    load_frozen_grouped_split,
    load_serper_dual_source_dataset,
)

VERSION = "serper-dual-source-policy-calibration-v1"
SCHEMA_VERSION = "pvr-serper-dual-source-policy-calibration-selection-v1"
POLICY_DATASET = Path("data/evaluation/serper-dual-source-policy-query-v1/dataset.json")
POLICY_DATASET_SHA256 = "7df621e277e5c702f2d1277daf84d883e6e98a50f9c2ad69b052594c18ecbbf1"
CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
POINTWISE_MODEL_MANIFEST_SHA256 = "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
DIRECTORY = Path("data/evaluation/serper-dual-source-policy-calibration-v1")
CALIBRATORS_PATH = DIRECTORY / "calibrators.json"
POLICY_PATH = DIRECTORY / "policy.json"
SELECTION_PATH = DIRECTORY / "selection.json"
SPLIT_VERSION = "serper-dual-source-policy-grouped-development-split-v1"
SPLIT_SALT = "pvr:serper-dual-source-policy-calibration:grouped:v1"
POSITIVE_FIT_TARGETS = 70
POSITIVE_SELECTION_TARGETS = 30
NEGATIVE_FIT_TARGETS = 28
NEGATIVE_SELECTION_TARGETS = 12
MATCH_MINIMUM_ACCEPTED = 5
MATCH_MINIMUM_PRECISION = 0.90
NO_MATCH_MINIMUM_ACCEPTED = 5
NO_MATCH_MINIMUM_PRECISION = 0.90
MAXIMUM_FALSE_NO_MATCH_RATE = 0.10

SourceType = Literal["image_search", "shopping"]
Truth = Literal["catalog_present", "catalog_relative_no_match"]
DatasetPartition = Literal["no_match_development", "policy_holdout"]
DevelopmentPartition = Literal["calibration_fit", "threshold_selection"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


class PolicyQueryCase(StrictModel):
    id: str = Field(pattern=r"^sdsp-[0-9]{4}$")
    target_id: str = Field(pattern=r"^sdsp-target-[0-9]{4}$")
    partition: DatasetPartition
    truth: Truth
    challenge_type: Literal["catalog_present", "same_casting_absent_release", "absent_casting"]
    source_type: SourceType
    query_raw: str = Field(min_length=1, max_length=512)
    expected_casting: str = Field(min_length=1)
    expected_full_identity: ExpectedFullIdentity

    @field_validator("query_raw", "expected_casting")
    @classmethod
    def strip_and_reject_urls(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or "http://" in stripped.casefold() or "https://" in stripped.casefold():
            raise ValueError("query/casting must be nonblank and URL-free")
        return stripped

    @model_validator(mode="after")
    def validate_semantics(self) -> PolicyQueryCase:
        if normalize_text(self.expected_casting) != normalize_text(
            self.expected_full_identity.casting
        ):
            raise ValueError("expected casting differs from full identity")
        if self.truth == "catalog_present" and self.challenge_type != "catalog_present":
            raise ValueError("catalog-present truth requires catalog-present challenge")
        if self.truth == "catalog_relative_no_match" and self.challenge_type == "catalog_present":
            raise ValueError("no-match truth cannot use catalog-present challenge")
        if self.partition == "no_match_development" and self.truth != "catalog_relative_no_match":
            raise ValueError("development additions must be no-match")
        return self


class PolicyQueryDataset(StrictModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: Literal["serper-dual-source-policy-query-v1"]
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_scope: Literal["frozen-community-catalog-relative-not-manufacturer-truth"]
    query_representation: Literal["raw"]
    target_count: Literal[80]
    record_count: Literal[160]
    records: list[PolicyQueryCase]

    @model_validator(mode="after")
    def validate_pairs(self) -> PolicyQueryDataset:
        if len(self.records) != self.record_count:
            raise ValueError("record count changed")
        if [row.id for row in self.records] != [f"sdsp-{index:04d}" for index in range(1, 161)]:
            raise ValueError("record IDs must be contiguous")
        grouped: dict[str, list[PolicyQueryCase]] = defaultdict(list)
        for row in self.records:
            grouped[row.target_id].append(row)
        if list(grouped) != [f"sdsp-target-{index:04d}" for index in range(1, 81)]:
            raise ValueError("target IDs must be contiguous")
        toy_numbers: list[str] = []
        for target_id, pair in grouped.items():
            if [row.source_type for row in pair] != ["image_search", "shopping"]:
                raise ValueError(f"{target_id} source pair changed")
            stable = (
                "partition",
                "truth",
                "challenge_type",
                "expected_casting",
                "expected_full_identity",
            )
            if any(getattr(pair[0], field) != getattr(pair[1], field) for field in stable):
                raise ValueError(f"{target_id} source truth differs")
            toy_numbers.append(pair[0].expected_full_identity.toy_number)
        if len(toy_numbers) != len(set(toy_numbers)):
            raise ValueError("target toy numbers must be unique")
        targets = [pair[0] for pair in grouped.values()]
        counts = {
            "development_no_match": sum(row.partition == "no_match_development" for row in targets),
            "holdout_positive": sum(
                row.partition == "policy_holdout" and row.truth == "catalog_present"
                for row in targets
            ),
            "holdout_no_match": sum(
                row.partition == "policy_holdout" and row.truth == "catalog_relative_no_match"
                for row in targets
            ),
        }
        if counts != {
            "development_no_match": 40,
            "holdout_positive": 20,
            "holdout_no_match": 20,
        }:
            raise ValueError("policy dataset partition counts changed")
        for source in ("image_search", "shopping"):
            queries = [
                normalize_text(row.query_raw) for row in self.records if row.source_type == source
            ]
            if len(queries) != len(set(queries)):
                raise ValueError(f"{source} queries must be unique")
        return self

    def target_pairs(self) -> tuple[tuple[PolicyQueryCase, PolicyQueryCase], ...]:
        return tuple(
            (self.records[index], self.records[index + 1])
            for index in range(0, len(self.records), 2)
        )


@dataclass(frozen=True, slots=True)
class CalibrationRow:
    target_id: str
    source_type: SourceType
    partition: DevelopmentPartition
    truth: Truth
    vector: tuple[float, ...]
    exact_top1_correct: int


@dataclass(frozen=True, slots=True)
class GroupedSplit:
    assignment: dict[str, DevelopmentPartition]
    assignment_sha256: str


def load_policy_dataset(path: Path) -> PolicyQueryDataset:
    return PolicyQueryDataset.model_validate(_read_object(path))


def _assign_group(
    target_ids: tuple[str, ...], *, fit_count: int, namespace: str
) -> dict[str, DevelopmentPartition]:
    if len(target_ids) != len(set(target_ids)) or not 0 < fit_count < len(target_ids):
        raise ValueError("grouped split input is invalid")
    ordered = sorted(
        target_ids,
        key=lambda target_id: hashlib.sha256(
            f"{SPLIT_SALT}\0{namespace}\0{target_id}".encode()
        ).hexdigest(),
    )
    fit = set(ordered[:fit_count])
    return {
        target_id: "calibration_fit" if target_id in fit else "threshold_selection"
        for target_id in sorted(target_ids)
    }


def build_grouped_split(
    positive_target_ids: tuple[str, ...], negative_target_ids: tuple[str, ...]
) -> GroupedSplit:
    if len(positive_target_ids) != 100 or len(negative_target_ids) != 40:
        raise ValueError("grouped calibration requires 100 positive and 40 negative identities")
    assignment = {
        **_assign_group(positive_target_ids, fit_count=POSITIVE_FIT_TARGETS, namespace="positive"),
        **_assign_group(negative_target_ids, fit_count=NEGATIVE_FIT_TARGETS, namespace="no-match"),
    }
    rows = [[target_id, assignment[target_id]] for target_id in sorted(assignment)]
    return GroupedSplit(
        assignment=assignment,
        assignment_sha256=hashlib.sha256(_canonical_bytes(rows)).hexdigest(),
    )


def _validate_no_match_truth(
    dataset: PolicyQueryDataset, source_records: list[dict[str, Any]]
) -> tuple[str, ...]:
    catalog_toys = {str(row["toy_number"]) for row in source_records}
    catalog_castings = {normalize_text(str(row["casting_name"])) for row in source_records}
    targets: list[str] = []
    for image, _shopping in dataset.target_pairs():
        if image.partition != "no_match_development":
            continue
        if image.expected_full_identity.toy_number in catalog_toys:
            raise ValueError("no-match development toy number exists in frozen catalog")
        casting_present = normalize_text(image.expected_casting) in catalog_castings
        if image.challenge_type == "same_casting_absent_release" and not casting_present:
            raise ValueError("same-casting no-match is absent from frozen catalog")
        if image.challenge_type == "absent_casting" and casting_present:
            raise ValueError("absent-casting no-match exists in frozen catalog")
        targets.append(image.target_id)
    if len(targets) != 40:
        raise ValueError("no-match development target count changed")
    return tuple(targets)


def _positive_targets_and_bindings(
    root: Path, source_records: list[dict[str, Any]]
) -> tuple[dict[str, UUID], dict[str, tuple[str, str]], tuple[str, ...]]:
    dataset = load_serper_dual_source_dataset(root / POSITIVE_DATASET)
    split = load_frozen_grouped_split(dataset, root / POSITIVE_DATASET)
    pairs = {pair[0].target_id: pair for pair in dataset.target_pairs()}
    cases: list[ImageSearchCase] = []
    queries: dict[str, tuple[str, str]] = {}
    for index, target_id in enumerate(split.development_target_ids, start=1):
        image, shopping = pairs[target_id]
        cases.append(
            ImageSearchCase(
                id=f"isr-{index:04d}",
                query=image.query_raw,
                expected_casting=image.expected_casting,
                expected_full_identity=image.expected_full_identity,
            )
        )
        queries[target_id] = (image.query_raw, shopping.query_raw)
    bindings = bind_dataset_to_source(
        ImageSearchDataset(dataset_version="image-search-resolver-v2", records=cases),
        source_records,
    )
    targets = {
        target_id: binding.evaluation_uuid
        for target_id, binding in zip(split.development_target_ids, bindings, strict=True)
    }
    return targets, queries, split.development_target_ids


def collect_development_rows(
    root: Path, context: PointwiseScoringContext | None = None
) -> tuple[list[CalibrationRow], GroupedSplit]:
    if _sha256(root / POLICY_DATASET) != POLICY_DATASET_SHA256:
        raise ValueError("policy dataset differs from the frozen contract")
    if _sha256(root / POSITIVE_DATASET) != POSITIVE_DATASET_SHA256:
        raise ValueError("positive dataset differs from the frozen contract")
    if _sha256(root / RAW_POINTWISE_DEVELOPMENT) != FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256:
        raise ValueError("positive development ranker selection differs from the frozen contract")
    if _sha256(root / SOURCE) != CATALOG_SHA256:
        raise ValueError("catalog differs from the frozen contract")
    if _sha256(root / POINTWISE_MODEL / "manifest.json") != POINTWISE_MODEL_MANIFEST_SHA256:
        raise ValueError("pointwise model manifest differs from the frozen contract")
    policy_dataset = load_policy_dataset(root / POLICY_DATASET)
    source_records = load_source_records(root / SOURCE, expected_count=SOURCE_COUNT)
    positive_targets, positive_queries, positive_ids = _positive_targets_and_bindings(
        root, source_records
    )
    negative_ids = _validate_no_match_truth(policy_dataset, source_records)
    split = build_grouped_split(positive_ids, negative_ids)
    context = context or load_pointwise_scoring_context(root)
    rows: list[CalibrationRow] = []
    for target_id in positive_ids:
        target = positive_targets[target_id]
        source_types: tuple[SourceType, SourceType] = ("image_search", "shopping")
        for source_type, query in zip(source_types, positive_queries[target_id], strict=True):
            ranked = score_pointwise_query(context, query)
            rows.append(
                CalibrationRow(
                    target_id=target_id,
                    source_type=source_type,
                    partition=split.assignment[target_id],
                    truth="catalog_present",
                    vector=features(ranked),
                    exact_top1_correct=int(
                        bool(ranked) and ranked[0].product.canonical_uuid == target
                    ),
                )
            )
    for image, shopping in policy_dataset.target_pairs():
        if image.partition != "no_match_development":
            continue
        for row in (image, shopping):
            ranked = score_pointwise_query(context, row.query_raw)
            rows.append(
                CalibrationRow(
                    target_id=row.target_id,
                    source_type=row.source_type,
                    partition=split.assignment[row.target_id],
                    truth="catalog_relative_no_match",
                    vector=features(ranked),
                    exact_top1_correct=0,
                )
            )
    fit = [row for row in rows if row.partition == "calibration_fit"]
    selection = [row for row in rows if row.partition == "threshold_selection"]
    if len(rows) != 280 or len(fit) != 196 or len(selection) != 84:
        raise ValueError("development observation composition changed")
    return rows, split


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value))))


def _logistic_probability(artifact: CalibrationArtifact, vector: tuple[float, ...]) -> float:
    return _sigmoid(
        artifact.intercept
        + sum(weight * item for weight, item in zip(artifact.weights, vector, strict=True))
    )


def _interpolate(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for index in range(1, len(xs)):
        if x <= xs[index]:
            left_x, right_x = xs[index - 1], xs[index]
            left_y, right_y = ys[index - 1], ys[index]
            if right_x == left_x:
                return right_y
            ratio = (x - left_x) / (right_x - left_x)
            return left_y + ratio * (right_y - left_y)
    raise AssertionError("isotonic interpolation failed")


def _calibration_metrics(confidences: list[float], labels: list[int]) -> dict[str, Any]:
    if not confidences or len(confidences) != len(labels):
        raise ValueError("calibration metrics require aligned rows")
    clipped = [min(1 - 1e-15, max(1e-15, value)) for value in confidences]
    brier = sum((value - label) ** 2 for value, label in zip(clipped, labels, strict=True)) / len(
        labels
    )
    nll = -sum(
        label * math.log(value) + (1 - label) * math.log(1 - value)
        for value, label in zip(clipped, labels, strict=True)
    ) / len(labels)
    bins: list[dict[str, int | float]] = []
    ece = 0.0
    for index in range(10):
        low, high = index / 10, (index + 1) / 10
        members = [
            (value, label)
            for value, label in zip(clipped, labels, strict=True)
            if low <= value < high or (index == 9 and value == 1.0)
        ]
        count = len(members)
        mean_confidence = sum(item[0] for item in members) / count if count else 0.0
        empirical_accuracy = sum(item[1] for item in members) / count if count else 0.0
        ece += count / len(labels) * abs(mean_confidence - empirical_accuracy)
        bins.append(
            {
                "bin": index,
                "count": count,
                "mean_confidence": mean_confidence,
                "empirical_accuracy": empirical_accuracy,
            }
        )
    ordered = sorted(zip(clipped, labels, strict=True), key=lambda item: item[0], reverse=True)
    cumulative_errors = 0
    cumulative_risks: list[float] = []
    for index, (_confidence, label) in enumerate(ordered, start=1):
        cumulative_errors += 1 - label
        cumulative_risks.append(cumulative_errors / index)
    risk_points = []
    for coverage in (0.10, 0.25, 0.50, 0.75, 1.0):
        count = max(1, math.ceil(len(ordered) * coverage))
        risk_points.append(
            {
                "coverage": count / len(ordered),
                "accepted_count": count,
                "risk": cumulative_risks[count - 1],
                "precision": 1.0 - cumulative_risks[count - 1],
            }
        )
    return {
        "sample_count": len(labels),
        "positive_count": sum(labels),
        "brier_score": brier,
        "negative_log_likelihood": nll,
        "ece_10_bin": ece,
        "reliability_bins": bins,
        "aurc": sum(cumulative_risks) / len(cumulative_risks),
        "risk_coverage": risk_points,
    }


def _fit_calibrators(
    fit_rows: list[CalibrationRow], selection_rows: list[CalibrationRow]
) -> tuple[dict[str, Any], dict[str, list[float]], dict[str, dict[str, Any]]]:
    logistic = train_logistic(
        [(row.vector, row.exact_top1_correct) for row in fit_rows],
        VERSION,
        split="train",
        iterations=2_000,
        learning_rate=0.01,
    )
    logistic = replace(
        logistic,
        model_version="logistic-python-v3+dual-source-neural-pointwise-v1",
        artifact_version=VERSION,
    )
    logistic_confidences = [_logistic_probability(logistic, row.vector) for row in selection_rows]

    try:
        from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
    except ImportError as error:  # pragma: no cover - optional dependency guard
        raise RuntimeError("install the ml optional dependency for isotonic calibration") from error
    isotonic = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    fit_scores = [row.vector[0] for row in fit_rows]
    fit_labels = [row.exact_top1_correct for row in fit_rows]
    isotonic.fit(fit_scores, fit_labels)
    iso_x = [float(value) for value in isotonic.X_thresholds_]
    iso_y = [float(value) for value in isotonic.y_thresholds_]
    isotonic_confidences = [_interpolate(row.vector[0], iso_x, iso_y) for row in selection_rows]

    best_temperature = 1.0
    best_nll = math.inf
    for step in range(-400, 401):
        temperature = math.exp(step / 100)
        probabilities = [_sigmoid(row.vector[0] / temperature) for row in fit_rows]
        metrics = _calibration_metrics(probabilities, fit_labels)
        nll = float(metrics["negative_log_likelihood"])
        if nll < best_nll:
            best_nll = nll
            best_temperature = temperature
    temperature_confidences = [_sigmoid(row.vector[0] / best_temperature) for row in selection_rows]

    confidences = {
        "five_feature_logistic": logistic_confidences,
        "top_score_isotonic": isotonic_confidences,
        "top_score_temperature": temperature_confidences,
    }
    parameters: dict[str, Any] = {
        "five_feature_logistic": {
            "type": "linear_logistic",
            "feature_schema": list(logistic.feature_schema),
            "weights": list(logistic.weights),
            "intercept": logistic.intercept,
            "model_version": logistic.model_version,
        },
        "top_score_isotonic": {
            "type": "isotonic_piecewise_linear",
            "feature": "top1_score",
            "x_thresholds": iso_x,
            "y_thresholds": iso_y,
        },
        "top_score_temperature": {
            "type": "temperature_scaling",
            "feature": "top1_score",
            "temperature": best_temperature,
            "fit_negative_log_likelihood": best_nll,
            "grid": {"log_temperature_min": -4.0, "max": 4.0, "step": 0.01},
        },
    }
    labels = [row.exact_top1_correct for row in selection_rows]
    metrics_by_method = {
        name: _calibration_metrics(values, labels) for name, values in confidences.items()
    }
    return parameters, confidences, metrics_by_method


def _source_metrics(
    rows: list[CalibrationRow], confidences: list[float]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for source in ("image_search", "shopping"):
        indices = [index for index, row in enumerate(rows) if row.source_type == source]
        result[source] = _calibration_metrics(
            [confidences[index] for index in indices],
            [rows[index].exact_top1_correct for index in indices],
        )
        result[source]["catalog_present_count"] = sum(
            rows[index].truth == "catalog_present" for index in indices
        )
        result[source]["catalog_relative_no_match_count"] = sum(
            rows[index].truth == "catalog_relative_no_match" for index in indices
        )
    return result


def fit_and_select(
    rows: list[CalibrationRow], split: GroupedSplit
) -> tuple[dict[str, Any], DecisionPolicy | None, dict[str, Any]]:
    fit_rows = [row for row in rows if row.partition == "calibration_fit"]
    selection_rows = [row for row in rows if row.partition == "threshold_selection"]
    parameters, confidences, metrics_by_method = _fit_calibrators(fit_rows, selection_rows)
    winner = min(
        metrics_by_method,
        key=lambda name: (
            metrics_by_method[name]["brier_score"],
            metrics_by_method[name]["negative_log_likelihood"],
            metrics_by_method[name]["ece_10_bin"],
            name,
        ),
    )
    selected = confidences[winner]
    shortfalls: list[str] = []
    match = None
    no_match = None
    try:
        match = select_threshold(
            list(zip(selected, [row.exact_top1_correct for row in selection_rows], strict=True)),
            minimum_precision=MATCH_MINIMUM_PRECISION,
            minimum_accepted=MATCH_MINIMUM_ACCEPTED,
        )
    except ValueError:
        shortfalls.append("match_gate_unmet")
    if match is not None:
        try:
            no_match = select_no_match_threshold(
                list(
                    zip(
                        selected,
                        [row.truth == "catalog_relative_no_match" for row in selection_rows],
                        strict=True,
                    )
                ),
                match_threshold=match.threshold,
                minimum_accepted=NO_MATCH_MINIMUM_ACCEPTED,
                minimum_precision=NO_MATCH_MINIMUM_PRECISION,
                maximum_false_no_match_rate=MAXIMUM_FALSE_NO_MATCH_RATE,
            )
        except ValueError:
            shortfalls.append("no_match_gate_unmet")
    else:
        shortfalls.append("no_match_gate_not_evaluated_without_match_threshold")
    policy = None
    if match is not None and no_match is not None:
        policy = DecisionPolicy(
            version=VERSION,
            match_threshold=match.threshold,
            no_match_threshold=no_match.threshold,
            margin_threshold=0.0,
            max_conflicts=5,
            require_positive_top_score=False,
            runtime_eligible=False,
        )
    thresholds: dict[str, Any] = {
        "match": None if match is None else asdict(match),
        "no_match": None if no_match is None else asdict(no_match),
        "ambiguous_count": (
            len(selection_rows)
            - (0 if match is None else match.accepted_count)
            - (0 if no_match is None else no_match.predicted_count)
        ),
        "shortfalls": shortfalls,
    }
    artifact = {
        "version": VERSION,
        "feature_schema": list(FEATURE_SCHEMA),
        "grouped_split_assignment_sha256": split.assignment_sha256,
        "fit_observation_count": len(fit_rows),
        "selection_observation_count": len(selection_rows),
        "selection_rule": "lowest_brier_then_nll_then_ece_then_method_name",
        "selected_method": winner,
        "methods": parameters,
    }
    metrics = {
        "methods": metrics_by_method,
        "selected_method": winner,
        "selected_source_metrics": _source_metrics(selection_rows, selected),
        "thresholds": thresholds,
    }
    return artifact, policy, metrics


def _contains_row_level_key(value: object) -> bool:
    forbidden = {
        "case_id",
        "case_ids",
        "query",
        "queries",
        "record",
        "records",
        "target_id",
        "target_ids",
        "prediction",
        "predictions",
        "labels",
        "assignment",
    }
    if isinstance(value, dict):
        return any(key in forbidden or _contains_row_level_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def materialize(root: Path) -> dict[str, Any]:
    paths = (root / CALIBRATORS_PATH, root / POLICY_PATH, root / SELECTION_PATH)
    if any(path.exists() for path in paths):
        raise FileExistsError("dual-source calibration artifacts already exist")
    rows, split = collect_development_rows(root)
    calibrators, policy, metrics = fit_and_select(rows, split)
    directory = root / DIRECTORY
    directory.mkdir(parents=True, exist_ok=False)
    calibrator_bytes = _canonical_bytes(calibrators)
    (root / CALIBRATORS_PATH).write_bytes(calibrator_bytes)
    policy_sha256 = None
    if policy is not None:
        policy_bytes = _canonical_bytes(asdict(policy))
        (root / POLICY_PATH).write_bytes(policy_bytes)
        policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "development_calibrated_not_runtime_authorized"
            if policy is not None
            else "development_calibration_gate_shortfall"
        ),
        "bindings": {
            "positive_dataset_sha256": POSITIVE_DATASET_SHA256,
            "positive_split_sha256": FROZEN_SPLIT_SHA256,
            "positive_development_ranking_sha256": FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
            "policy_dataset_sha256": POLICY_DATASET_SHA256,
            "catalog_sha256": CATALOG_SHA256,
            "pointwise_model_manifest_sha256": POINTWISE_MODEL_MANIFEST_SHA256,
        },
        "grouped_split": {
            "version": SPLIT_VERSION,
            "salt": SPLIT_SALT,
            "assignment_sha256": split.assignment_sha256,
            "fit_target_counts": {
                "catalog_present": POSITIVE_FIT_TARGETS,
                "catalog_relative_no_match": NEGATIVE_FIT_TARGETS,
            },
            "selection_target_counts": {
                "catalog_present": POSITIVE_SELECTION_TARGETS,
                "catalog_relative_no_match": NEGATIVE_SELECTION_TARGETS,
            },
            "fit_observation_count": 196,
            "selection_observation_count": 84,
        },
        "gates": {
            "match_minimum_accepted": MATCH_MINIMUM_ACCEPTED,
            "match_minimum_precision": MATCH_MINIMUM_PRECISION,
            "no_match_minimum_accepted": NO_MATCH_MINIMUM_ACCEPTED,
            "no_match_minimum_precision": NO_MATCH_MINIMUM_PRECISION,
            "maximum_false_no_match_rate": MAXIMUM_FALSE_NO_MATCH_RATE,
        },
        "artifacts": {
            "calibrators_path": str(CALIBRATORS_PATH),
            "calibrators_sha256": hashlib.sha256(calibrator_bytes).hexdigest(),
            "policy_path": str(POLICY_PATH) if policy is not None else None,
            "policy_sha256": policy_sha256,
        },
        "metrics": metrics,
        "guardrails": {
            "network_requests": 0,
            "row_level_output_persisted": False,
            "opened_50_target_ranking_final_reused": False,
            "fresh_holdout_target_count": 40,
            "fresh_holdout_observations_scored": 0,
            "model_refit": False,
            "runtime_default_changed": False,
            "runtime_activation_authorized": False,
            "runtime_eligible": False,
        },
        "next_allowed_action": (
            "review_development_metrics_then_authorize_one_shot_fresh_holdout"
            if policy is not None
            else "improve_development_evidence_without_opening_fresh_holdout"
        ),
        "authority_note": (
            "All truth is relative to the frozen third-party community catalog, not "
            "manufacturer-certified or global truth."
        ),
    }
    if _contains_row_level_key(payload) or _contains_row_level_key(calibrators):
        raise ValueError("tracked calibration artifact contains row-level output")
    (root / SELECTION_PATH).write_bytes(_canonical_bytes(payload))
    return payload


def check(root: Path) -> dict[str, Any]:
    payload = _read_object(root / SELECTION_PATH)
    if payload.get("schema_version") != SCHEMA_VERSION or _contains_row_level_key(payload):
        raise ValueError("dual-source calibration selection contract changed")
    if _sha256(root / POLICY_DATASET) != POLICY_DATASET_SHA256:
        raise ValueError("policy dataset binding changed")
    if _sha256(root / POSITIVE_DATASET) != POSITIVE_DATASET_SHA256:
        raise ValueError("positive dataset binding changed")
    if _sha256(root / RAW_POINTWISE_DEVELOPMENT) != FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256:
        raise ValueError("positive ranker binding changed")
    if _sha256(root / SOURCE) != CATALOG_SHA256:
        raise ValueError("catalog binding changed")
    if _sha256(root / POINTWISE_MODEL / "manifest.json") != POINTWISE_MODEL_MANIFEST_SHA256:
        raise ValueError("pointwise model binding changed")
    bindings = payload.get("bindings")
    artifacts = payload.get("artifacts")
    grouped = payload.get("grouped_split")
    guardrails = payload.get("guardrails")
    metrics = payload.get("metrics")
    if not all(
        isinstance(item, dict) for item in (bindings, artifacts, grouped, guardrails, metrics)
    ):
        raise TypeError("dual-source calibration sections must be objects")
    assert isinstance(bindings, dict)
    assert isinstance(artifacts, dict)
    assert isinstance(grouped, dict)
    assert isinstance(guardrails, dict)
    assert isinstance(metrics, dict)
    expected_bindings = {
        "positive_dataset_sha256": POSITIVE_DATASET_SHA256,
        "positive_split_sha256": FROZEN_SPLIT_SHA256,
        "positive_development_ranking_sha256": FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
        "policy_dataset_sha256": POLICY_DATASET_SHA256,
        "catalog_sha256": CATALOG_SHA256,
        "pointwise_model_manifest_sha256": POINTWISE_MODEL_MANIFEST_SHA256,
    }
    if bindings != expected_bindings:
        raise ValueError("dual-source calibration bindings changed")
    calibrator_path = root / str(artifacts.get("calibrators_path"))
    if artifacts.get("calibrators_sha256") != _sha256(calibrator_path):
        raise ValueError("calibrator artifact hash changed")
    calibrators = _read_object(calibrator_path)
    if _contains_row_level_key(calibrators):
        raise ValueError("calibrator artifact contains row-level output")
    if calibrators.get("selected_method") != metrics.get("selected_method"):
        raise ValueError("selected calibrator differs between artifacts")
    expected_guardrails = {
        "network_requests": 0,
        "row_level_output_persisted": False,
        "opened_50_target_ranking_final_reused": False,
        "fresh_holdout_target_count": 40,
        "fresh_holdout_observations_scored": 0,
        "model_refit": False,
        "runtime_default_changed": False,
        "runtime_activation_authorized": False,
        "runtime_eligible": False,
    }
    if guardrails != expected_guardrails:
        raise ValueError("runtime/final guardrails changed")
    if (
        grouped.get("fit_observation_count") != 196
        or grouped.get("selection_observation_count") != 84
    ):
        raise ValueError("grouped observation counts changed")
    success = payload.get("status") == "development_calibrated_not_runtime_authorized"
    if success:
        policy_value = artifacts.get("policy_path")
        if not isinstance(policy_value, str):
            raise TypeError("successful calibration must publish a policy")
        policy_path = root / policy_value
        if artifacts.get("policy_sha256") != _sha256(policy_path):
            raise ValueError("policy artifact hash changed")
        policy = DecisionPolicy.load(policy_path)
        if policy.runtime_eligible or policy.version != VERSION:
            raise ValueError("development policy crossed the runtime boundary")
    elif artifacts.get("policy_path") is not None:
        raise ValueError("shortfall must not publish a policy")
    methods = metrics.get("methods")
    if not isinstance(methods, dict) or set(methods) != {
        "five_feature_logistic",
        "top_score_isotonic",
        "top_score_temperature",
    }:
        raise ValueError("calibrator comparison changed")
    for method in methods.values():
        if not isinstance(method, dict):
            raise TypeError("method metrics must be objects")
        for key in ("brier_score", "negative_log_likelihood", "ece_10_bin", "aurc"):
            value = method.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("calibration metric must be finite")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate the paired Serper decision policy")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--acknowledge-development-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.check:
        check(root)
        print("valid")
        return
    if not args.run or not args.acknowledge_development_only:
        parser.error("--run requires --acknowledge-development-only")
    print(json.dumps(materialize(root), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
