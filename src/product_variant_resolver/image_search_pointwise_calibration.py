"""Development-only confidence calibration for the frozen image-search Pointwise ranker."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from .calibration import (
    FEATURE_SCHEMA,
    CalibrationArtifact,
    features,
    train_logistic,
)
from .config import Settings
from .human_knowledge import load_human_knowledge_catalog
from .image_search_evaluation import (
    AUTHORITY_NOTE,
    DATASET,
    FROZEN_DATASET_SHA256,
    FROZEN_DEVELOPMENT_COUNT,
    FROZEN_SPLIT_SHA256,
    SOURCE,
    SOURCE_COUNT,
    bind_dataset_to_source,
    build_evaluation_catalog,
    load_frozen_split,
    load_image_search_dataset,
    load_source_records,
)
from .image_search_ranking_development import (
    POINTWISE_CONFIG,
    POINTWISE_MODEL,
    SELECTION,
    check_development_selection,
)
from .neural_reranking import LocalPointwiseScorer, load_pointwise_model_config
from .policy import DecisionPolicy
from .rerank import NeuralPointwiseReranker
from .service import ResolverService
from .signals import extract_signals

VERSION = "image-search-pointwise-calibration-v1"
SCHEMA_VERSION = "pvr-image-search-pointwise-calibration-selection-v1"
INNER_SPLIT_VERSION = "image-search-pointwise-calibration-inner-split-v1"
INNER_SPLIT_SALT = "pvr:image-search-pointwise-calibration:fit-selection:v1"
FROZEN_INNER_SPLIT_SHA256 = "a676eb2713bfea3c46576486685535b3f7358c048b220eda876ce3bdb150635e"
FIT_COUNT = 70
SELECTION_COUNT = 30
MIN_ACCEPTED = 5
MIN_PRECISION = 0.90
CANDIDATE_LIMIT = 25
FROZEN_SOURCE_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
DIRECTORY = Path("data/evaluation/image-search-pointwise-calibration-v1")
CALIBRATION_PATH = DIRECTORY / "calibration.json"
POLICY_PATH = DIRECTORY / "policy.json"
SELECTION_PATH = DIRECTORY / "selection.json"

Partition = Literal["calibration_fit", "threshold_selection"]


@dataclass(frozen=True, slots=True)
class CalibrationRow:
    case_id: str
    partition: Partition
    vector: tuple[float, ...]
    exact_top1_correct: int


@dataclass(frozen=True, slots=True)
class ThresholdSelection:
    threshold: float
    accepted_count: int
    accepted_correct: int
    precision: float
    coverage: float


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _inner_assignment(case_ids: tuple[str, ...]) -> tuple[dict[str, Partition], str]:
    if len(case_ids) != FROZEN_DEVELOPMENT_COUNT or len(set(case_ids)) != len(case_ids):
        raise ValueError("inner split requires exactly 100 unique development case IDs")
    ordered = sorted(
        case_ids,
        key=lambda case_id: hashlib.sha256(f"{INNER_SPLIT_SALT}\n{case_id}".encode()).hexdigest(),
    )
    fit = set(ordered[:FIT_COUNT])
    assignment: dict[str, Partition] = {
        case_id: "calibration_fit" if case_id in fit else "threshold_selection"
        for case_id in sorted(case_ids)
    }
    digest = hashlib.sha256(
        _canonical_bytes([[case_id, assignment[case_id]] for case_id in sorted(assignment)])
    ).hexdigest()
    return assignment, digest


def _probability(artifact: CalibrationArtifact, vector: tuple[float, ...]) -> float:
    if len(vector) != len(artifact.weights):
        raise ValueError("calibration vector differs from artifact feature count")
    value = artifact.intercept + sum(
        weight * feature for weight, feature in zip(artifact.weights, vector, strict=True)
    )
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value))))


def select_threshold(
    rows: list[tuple[float, int]],
    *,
    minimum_precision: float = MIN_PRECISION,
    minimum_accepted: int = MIN_ACCEPTED,
) -> ThresholdSelection:
    if not rows or any(label not in {0, 1} for _confidence, label in rows):
        raise ValueError("threshold selection requires labeled confidence rows")
    if not 0 < minimum_precision <= 1 or minimum_accepted < 1:
        raise ValueError("threshold selection constraints are invalid")
    if any(not 0 <= confidence <= 1 for confidence, _label in rows):
        raise ValueError("threshold selection confidence must be between zero and one")
    for threshold in sorted({confidence for confidence, _label in rows}):
        accepted = [label for confidence, label in rows if confidence >= threshold]
        correct = sum(accepted)
        precision = correct / len(accepted)
        if len(accepted) >= minimum_accepted and precision >= minimum_precision:
            return ThresholdSelection(
                threshold=threshold,
                accepted_count=len(accepted),
                accepted_correct=correct,
                precision=precision,
                coverage=len(accepted) / len(rows),
            )
    raise ValueError("development selection cannot meet the frozen precision/coverage gate")


def collect_development_rows(root: Path) -> tuple[list[CalibrationRow], str]:
    dataset_path = root / DATASET
    source_path = root / SOURCE
    if _sha256(dataset_path) != FROZEN_DATASET_SHA256:
        raise ValueError("calibration dataset bytes differ from the frozen benchmark")
    if _sha256(source_path) != FROZEN_SOURCE_SHA256:
        raise ValueError("calibration source bytes differ from the frozen source snapshot")
    dataset = load_image_search_dataset(dataset_path)
    split = load_frozen_split(dataset, dataset_path)
    if split.assignment_sha256 != FROZEN_SPLIT_SHA256:
        raise ValueError("calibration outer split differs from the frozen contract")
    assignment, assignment_sha256 = _inner_assignment(split.development_case_ids)
    development_ids = set(split.development_case_ids)
    cases = [case for case in dataset.records if case.id in development_ids]
    records = load_source_records(source_path, expected_count=SOURCE_COUNT)
    bindings = bind_dataset_to_source(dataset, records)
    target_by_case = {binding.case_id: binding.evaluation_uuid for binding in bindings}
    catalog = build_evaluation_catalog(records)
    settings = Settings(
        human_catalog_path=root / "data/human_backed_catalog.json",
        review_family_knowledge_path=root / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=(root / "data/review_family_knowledge_manifest.json"),
        candidate_limit=CANDIDATE_LIMIT,
    )
    human_catalog = load_human_knowledge_catalog(
        settings.human_catalog_path,
        settings.review_family_knowledge_path,
        settings.review_family_knowledge_manifest_path,
    )
    service = ResolverService(settings, catalog, human_catalog)
    config = load_pointwise_model_config(root / POINTWISE_CONFIG)
    scorer = LocalPointwiseScorer.load(config, root / POINTWISE_MODEL)
    reranker = NeuralPointwiseReranker(scorer)

    rows = []
    for case in cases:
        signals = extract_signals(case.query, service.color_vocabulary, service.series_vocabulary)
        candidates = service.retrieval.retrieve(signals, CANDIDATE_LIMIT)
        candidates = reranker.rerank(signals, candidates, query=case.query)
        target: UUID = target_by_case[case.id]
        rows.append(
            CalibrationRow(
                case_id=case.id,
                partition=assignment[case.id],
                vector=features(candidates),
                exact_top1_correct=int(
                    bool(candidates) and candidates[0].product.canonical_uuid == target
                ),
            )
        )
    if len(rows) != FROZEN_DEVELOPMENT_COUNT:
        raise ValueError("calibration did not collect exactly 100 development rows")
    return rows, assignment_sha256


def fit_development_calibration(
    rows: list[CalibrationRow],
    assignment_sha256: str,
) -> tuple[CalibrationArtifact, DecisionPolicy, dict[str, Any]]:
    fit_rows = [row for row in rows if row.partition == "calibration_fit"]
    selection_rows = [row for row in rows if row.partition == "threshold_selection"]
    if len(fit_rows) != FIT_COUNT or len(selection_rows) != SELECTION_COUNT:
        raise ValueError("calibration nested split has the wrong partition counts")
    if len({row.case_id for row in rows}) != len(rows):
        raise ValueError("calibration rows contain duplicate case IDs")
    artifact = train_logistic(
        [(row.vector, row.exact_top1_correct) for row in fit_rows],
        VERSION,
        split="train",
        iterations=2_000,
        learning_rate=0.01,
    )
    artifact = replace(
        artifact,
        model_version="logistic-python-v1+neural-pointwise-v1",
        artifact_version=VERSION,
    )
    confidence_rows = [
        (_probability(artifact, row.vector), row.exact_top1_correct) for row in selection_rows
    ]
    threshold = select_threshold(confidence_rows)
    policy = DecisionPolicy(
        version="image-search-development-neural-pointwise-v1",
        match_threshold=threshold.threshold,
        no_match_threshold=0.0,
        margin_threshold=0.0,
        max_conflicts=5,
        require_positive_top_score=False,
        runtime_eligible=False,
    )
    fit_correct = sum(row.exact_top1_correct for row in fit_rows)
    selection_correct = sum(row.exact_top1_correct for row in selection_rows)
    brier = sum((confidence - label) ** 2 for confidence, label in confidence_rows) / len(
        confidence_rows
    )
    metrics: dict[str, Any] = {
        "inner_split_assignment_sha256": assignment_sha256,
        "fit": {
            "sample_count": len(fit_rows),
            "exact_top1_correct": fit_correct,
            "exact_top1_incorrect": len(fit_rows) - fit_correct,
        },
        "threshold_selection": {
            "sample_count": len(selection_rows),
            "exact_top1_correct": selection_correct,
            "exact_top1_incorrect": len(selection_rows) - selection_correct,
            "accepted_count": threshold.accepted_count,
            "accepted_correct": threshold.accepted_correct,
            "match_threshold": threshold.threshold,
            "precision": threshold.precision,
            "coverage": threshold.coverage,
            "ambiguous_count": len(selection_rows) - threshold.accepted_count,
            "no_match_count": 0,
            "brier_score": brier,
        },
    }
    return artifact, policy, metrics


def _artifact_payload(artifact: CalibrationArtifact) -> dict[str, Any]:
    return asdict(artifact)


def _policy_payload(policy: DecisionPolicy) -> dict[str, Any]:
    return asdict(policy)


def materialize(root: Path) -> dict[str, Any]:
    directory = root / DIRECTORY
    paths = (root / CALIBRATION_PATH, root / POLICY_PATH, root / SELECTION_PATH)
    if any(path.exists() for path in paths):
        raise FileExistsError("pointwise calibration artifacts already exist")
    selection = check_development_selection(root)
    if selection.winner != "neural_pointwise":
        raise ValueError("development ranking selection is not neural_pointwise")
    rows, assignment_sha256 = collect_development_rows(root)
    if assignment_sha256 != FROZEN_INNER_SPLIT_SHA256:
        raise ValueError("calibration inner split differs from the frozen assignment")
    artifact, policy, metrics = fit_development_calibration(rows, assignment_sha256)
    directory.mkdir(parents=True, exist_ok=False)
    calibration_bytes = _canonical_bytes(_artifact_payload(artifact))
    policy_bytes = _canonical_bytes(_policy_payload(policy))
    (root / CALIBRATION_PATH).write_bytes(calibration_bytes)
    (root / POLICY_PATH).write_bytes(policy_bytes)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "development_calibrated_not_runtime_eligible",
        "dataset": {
            "path": str(DATASET),
            "sha256": FROZEN_DATASET_SHA256,
            "outer_split_assignment_sha256": FROZEN_SPLIT_SHA256,
            "development_count": FROZEN_DEVELOPMENT_COUNT,
        },
        "source": {
            "path": str(SOURCE),
            "sha256": FROZEN_SOURCE_SHA256,
            "record_count": SOURCE_COUNT,
        },
        "nested_split": {
            "version": INNER_SPLIT_VERSION,
            "salt": INNER_SPLIT_SALT,
            "fit_count": FIT_COUNT,
            "selection_count": SELECTION_COUNT,
            "assignment_sha256": assignment_sha256,
        },
        "ranking": {
            "provider": "neural-pointwise-v1",
            "candidate_limit": CANDIDATE_LIMIT,
            "development_selection_sha256": _sha256(root / SELECTION),
            "model_manifest_sha256": _sha256(root / POINTWISE_MODEL / "manifest.json"),
        },
        "artifacts": {
            "calibration_path": str(CALIBRATION_PATH),
            "calibration_sha256": hashlib.sha256(calibration_bytes).hexdigest(),
            "policy_path": str(POLICY_PATH),
            "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
        },
        "selection_rule": {
            "minimum_empirical_precision": MIN_PRECISION,
            "minimum_accepted": MIN_ACCEPTED,
            "tie_break": "lowest_confidence_threshold_for_highest_coverage",
        },
        "metrics": metrics,
        "guardrails": {
            "test_cases_scored": 0,
            "row_level_output_persisted": False,
            "no_match_labels_available": False,
            "no_match_threshold_selected": False,
            "runtime_eligible": False,
            "runtime_default_changed": False,
        },
        "authority_note": AUTHORITY_NOTE,
    }
    (root / SELECTION_PATH).write_bytes(_canonical_bytes(payload))
    return payload


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
    }
    if isinstance(value, dict):
        return any(
            (isinstance(key, str) and key in forbidden) or _contains_row_level_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def _require_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{name} keys differ from the frozen contract")


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def check(root: Path, *, require_local_source: bool = True) -> dict[str, Any]:
    payload = json.loads((root / SELECTION_PATH).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("pointwise calibration selection must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("pointwise calibration selection schema differs from v1")
    if payload.get("status") != "development_calibrated_not_runtime_eligible":
        raise ValueError("pointwise calibration selection status differs from v1")
    _require_keys(
        payload,
        {
            "schema_version",
            "status",
            "dataset",
            "source",
            "nested_split",
            "ranking",
            "artifacts",
            "selection_rule",
            "metrics",
            "guardrails",
            "authority_note",
        },
        "pointwise calibration selection",
    )
    if _contains_row_level_key(payload):
        raise ValueError("pointwise calibration selection contains row-level output")
    dataset = payload.get("dataset")
    source = payload.get("source")
    nested = payload.get("nested_split")
    ranking = payload.get("ranking")
    artifacts = payload.get("artifacts")
    metrics = payload.get("metrics")
    guardrails = payload.get("guardrails")
    if not all(
        isinstance(value, dict)
        for value in (
            dataset,
            source,
            nested,
            ranking,
            artifacts,
            metrics,
            guardrails,
        )
    ):
        raise TypeError("pointwise calibration selection contains an invalid section")
    assert isinstance(dataset, dict) and isinstance(source, dict)
    assert isinstance(nested, dict) and isinstance(ranking, dict)
    assert isinstance(artifacts, dict) and isinstance(metrics, dict)
    assert isinstance(guardrails, dict)
    _require_keys(
        dataset,
        {
            "path",
            "sha256",
            "outer_split_assignment_sha256",
            "development_count",
        },
        "pointwise calibration dataset",
    )
    _require_keys(source, {"path", "sha256", "record_count"}, "pointwise calibration source")
    _require_keys(
        nested,
        {
            "version",
            "salt",
            "fit_count",
            "selection_count",
            "assignment_sha256",
        },
        "pointwise calibration nested split",
    )
    _require_keys(
        ranking,
        {
            "provider",
            "candidate_limit",
            "development_selection_sha256",
            "model_manifest_sha256",
        },
        "pointwise calibration ranking",
    )
    _require_keys(
        artifacts,
        {
            "calibration_path",
            "calibration_sha256",
            "policy_path",
            "policy_sha256",
        },
        "pointwise calibration artifacts",
    )
    if (
        dataset.get("path") != str(DATASET)
        or dataset.get("sha256") != FROZEN_DATASET_SHA256
        or dataset.get("outer_split_assignment_sha256") != FROZEN_SPLIT_SHA256
        or dataset.get("development_count") != FROZEN_DEVELOPMENT_COUNT
        or _sha256(root / DATASET) != FROZEN_DATASET_SHA256
    ):
        raise ValueError("pointwise calibration dataset binding changed")
    if (
        source.get("path") != str(SOURCE)
        or source.get("sha256") != FROZEN_SOURCE_SHA256
        or source.get("record_count") != SOURCE_COUNT
        or (require_local_source and _sha256(root / SOURCE) != FROZEN_SOURCE_SHA256)
    ):
        raise ValueError("pointwise calibration source binding changed")
    if nested != {
        "version": INNER_SPLIT_VERSION,
        "salt": INNER_SPLIT_SALT,
        "fit_count": FIT_COUNT,
        "selection_count": SELECTION_COUNT,
        "assignment_sha256": FROZEN_INNER_SPLIT_SHA256,
    }:
        raise ValueError("pointwise calibration nested split contract changed")
    frozen_split = load_frozen_split(
        load_image_search_dataset(root / DATASET),
        root / DATASET,
    )
    _assignment, expected_inner_sha256 = _inner_assignment(frozen_split.development_case_ids)
    if (
        expected_inner_sha256 != FROZEN_INNER_SPLIT_SHA256
        or nested.get("assignment_sha256") != FROZEN_INNER_SPLIT_SHA256
    ):
        raise ValueError("pointwise calibration nested split assignment changed")
    if ranking.get("provider") != "neural-pointwise-v1" or ranking.get("candidate_limit") != 25:
        raise ValueError("pointwise calibration ranking contract changed")
    if ranking.get("development_selection_sha256") != _sha256(root / SELECTION) or ranking.get(
        "model_manifest_sha256"
    ) != _sha256(root / POINTWISE_MODEL / "manifest.json"):
        raise ValueError("pointwise calibration ranking binding changed")
    calibration_path = root / str(artifacts.get("calibration_path"))
    policy_path = root / str(artifacts.get("policy_path"))
    if artifacts.get("calibration_sha256") != _sha256(calibration_path) or artifacts.get(
        "policy_sha256"
    ) != _sha256(policy_path):
        raise ValueError("pointwise calibration artifact hash changed")
    calibration_payload = json.loads(calibration_path.read_text(encoding="utf-8"))
    policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(calibration_payload, dict) or not isinstance(policy_payload, dict):
        raise TypeError("pointwise calibration artifacts must be JSON objects")
    _require_keys(
        calibration_payload,
        {
            "dataset_version",
            "model_version",
            "artifact_version",
            "feature_schema",
            "weights",
            "intercept",
        },
        "pointwise calibration artifact",
    )
    _require_keys(
        policy_payload,
        {
            "version",
            "match_threshold",
            "no_match_threshold",
            "margin_threshold",
            "max_conflicts",
            "require_positive_top_score",
            "runtime_eligible",
        },
        "pointwise calibration policy",
    )
    if _contains_row_level_key(calibration_payload) or _contains_row_level_key(policy_payload):
        raise ValueError("pointwise calibration artifact contains row-level output")
    artifact = CalibrationArtifact.load(calibration_path)
    policy = DecisionPolicy.load(policy_path)
    if (
        artifact.dataset_version != VERSION
        or artifact.model_version != "logistic-python-v1+neural-pointwise-v1"
        or artifact.artifact_version != VERSION
        or artifact.feature_schema != FEATURE_SCHEMA
        or policy.runtime_eligible
        or policy.require_positive_top_score
        or policy.no_match_threshold != 0.0
        or policy.margin_threshold != 0.0
    ):
        raise ValueError("pointwise calibration artifact policy boundary changed")
    threshold_metrics = metrics.get("threshold_selection")
    fit_metrics = metrics.get("fit")
    if not isinstance(fit_metrics, dict) or not isinstance(threshold_metrics, dict):
        raise TypeError("pointwise calibration threshold metrics must be an object")
    _require_keys(
        metrics,
        {
            "inner_split_assignment_sha256",
            "fit",
            "threshold_selection",
        },
        "pointwise calibration metrics",
    )
    _require_keys(
        fit_metrics,
        {
            "sample_count",
            "exact_top1_correct",
            "exact_top1_incorrect",
        },
        "pointwise calibration fit metrics",
    )
    _require_keys(
        threshold_metrics,
        {
            "sample_count",
            "exact_top1_correct",
            "exact_top1_incorrect",
            "accepted_count",
            "accepted_correct",
            "match_threshold",
            "precision",
            "coverage",
            "ambiguous_count",
            "no_match_count",
            "brier_score",
        },
        "pointwise calibration threshold metrics",
    )
    fit_sample = _integer(fit_metrics.get("sample_count"), "fit sample_count")
    fit_correct = _integer(fit_metrics.get("exact_top1_correct"), "fit exact correct")
    fit_incorrect = _integer(fit_metrics.get("exact_top1_incorrect"), "fit exact incorrect")
    selection_sample = _integer(threshold_metrics.get("sample_count"), "selection sample_count")
    selection_correct = _integer(
        threshold_metrics.get("exact_top1_correct"), "selection exact correct"
    )
    selection_incorrect = _integer(
        threshold_metrics.get("exact_top1_incorrect"), "selection exact incorrect"
    )
    accepted = _integer(threshold_metrics.get("accepted_count"), "accepted_count")
    correct = _integer(threshold_metrics.get("accepted_correct"), "accepted_correct")
    ambiguous = _integer(threshold_metrics.get("ambiguous_count"), "ambiguous_count")
    no_match = _integer(threshold_metrics.get("no_match_count"), "no_match_count")
    precision = _number(threshold_metrics.get("precision"), "selection precision")
    coverage = _number(threshold_metrics.get("coverage"), "selection coverage")
    match_threshold = _number(threshold_metrics.get("match_threshold"), "selection match_threshold")
    brier = _number(threshold_metrics.get("brier_score"), "selection brier_score")
    if (
        metrics.get("inner_split_assignment_sha256") != FROZEN_INNER_SPLIT_SHA256
        or fit_sample != FIT_COUNT
        or fit_correct + fit_incorrect != FIT_COUNT
        or selection_sample != SELECTION_COUNT
        or selection_correct + selection_incorrect != SELECTION_COUNT
        or not 0 <= correct <= accepted <= SELECTION_COUNT
        or ambiguous != SELECTION_COUNT - accepted
        or no_match != 0
        or accepted < MIN_ACCEPTED
        or correct / accepted < MIN_PRECISION
        or not math.isclose(precision, correct / accepted, rel_tol=0.0, abs_tol=1e-15)
        or not math.isclose(coverage, accepted / SELECTION_COUNT, rel_tol=0.0, abs_tol=1e-15)
        or not math.isclose(policy.match_threshold, match_threshold, rel_tol=0.0, abs_tol=1e-15)
        or not 0 <= brier <= 1
    ):
        raise ValueError("pointwise calibration threshold gate failed")
    if payload.get("selection_rule") != {
        "minimum_empirical_precision": MIN_PRECISION,
        "minimum_accepted": MIN_ACCEPTED,
        "tie_break": "lowest_confidence_threshold_for_highest_coverage",
    }:
        raise ValueError("pointwise calibration selection rule changed")
    if guardrails != {
        "test_cases_scored": 0,
        "row_level_output_persisted": False,
        "no_match_labels_available": False,
        "no_match_threshold_selected": False,
        "runtime_eligible": False,
        "runtime_default_changed": False,
    }:
        raise ValueError("pointwise calibration guardrails changed")
    if payload.get("authority_note") != AUTHORITY_NOTE:
        raise ValueError("pointwise calibration authority note changed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate Pointwise on development only")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--acknowledge-development-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.check:
        check(root)
        print("valid")
        return
    if not arguments.run or not arguments.acknowledge_development_only:
        parser.error("--run requires --acknowledge-development-only")
    print(json.dumps(materialize(root), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
