from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .retrieval import Candidate

FEATURE_SCHEMA = ("top1_score", "margin", "source_support", "match_count", "conflict_count")


def decision_score(candidate: Candidate) -> float:
    """Return the score used by calibration/policy for the active ranking path.

    A pointwise score takes precedence only when an opt-in reranker populated it.
    The default path maps RRF and structured evidence to the same stable feature
    scale without changing RRF candidate order.
    """

    if candidate.reranker_score is not None:
        return float(candidate.reranker_score)
    return (
        candidate.rrf_score * 20.0
        + 0.10 * len(candidate.matches)
        - 0.12 * len(candidate.conflicts)
    )


def features(candidates: list[Candidate]) -> tuple[float, ...]:
    if not candidates:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    top = candidates[0]
    first = decision_score(top)
    second = decision_score(candidates[1]) if len(candidates) > 1 else 0.0
    return (first, first - second, len(top.source_ranks) / 3.0,
            float(len(top.matches)), float(len(top.conflicts)))


@dataclass(frozen=True, slots=True)
class CalibrationArtifact:
    dataset_version: str
    model_version: str
    artifact_version: str
    feature_schema: tuple[str, ...]
    weights: tuple[float, ...]
    intercept: float

    def validate(self) -> None:
        if self.feature_schema != FEATURE_SCHEMA or len(self.weights) != len(FEATURE_SCHEMA):
            raise ValueError("calibration feature schema mismatch")
        if not all(math.isfinite(value) for value in (*self.weights, self.intercept)):
            raise ValueError("calibration artifact contains non-finite values")

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CalibrationArtifact":
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact = cls(
            dataset_version=payload["dataset_version"], model_version=payload["model_version"],
            artifact_version=payload["artifact_version"], feature_schema=tuple(payload["feature_schema"]),
            weights=tuple(float(item) for item in payload["weights"]),
            intercept=float(payload["intercept"]),
        )
        artifact.validate()
        return artifact


DEFAULT_HEURISTIC_ARTIFACT = CalibrationArtifact(
    dataset_version="fixture-v1", model_version="heuristic-v1",
    artifact_version="builtin-heuristic-v1",
    feature_schema=FEATURE_SCHEMA, weights=(2.2, 3.0, 0.7, 0.55, -0.9), intercept=-2.0,
)

# Deterministically fit by scripts/train_calibration.py on fixture-v1 train families;
# the 0.67 decision threshold was selected on fixture-v1 dev families. Test labels
# were not used to fit these weights or select the threshold.
DEFAULT_RRF_ARTIFACT = CalibrationArtifact(
    dataset_version="fixture-v1",
    model_version="logistic-python-v1+rrf",
    artifact_version="fixture-v1-rrf-logistic-v2",
    feature_schema=FEATURE_SCHEMA,
    weights=(-0.5943875578013758, 0.5522925612468645, -0.8914878659948483,
             1.7670971762445122, -0.4187180582858896),
    intercept=-1.2868156995143227,
)

DEFAULT_ARTIFACT = DEFAULT_RRF_ARTIFACT


class LogisticCalibrator:
    def __init__(self, artifact: CalibrationArtifact = DEFAULT_ARTIFACT) -> None:
        artifact.validate()
        self.artifact = artifact

    def probability(self, candidates: list[Candidate]) -> float:
        vector = features(candidates)
        value = self.artifact.intercept + sum(w * x for w, x in zip(self.artifact.weights, vector, strict=True))
        value = max(-40.0, min(40.0, value))
        result = 1.0 / (1.0 + math.exp(-value))
        if not math.isfinite(result):
            raise ValueError("non-finite calibrated probability")
        return result


def train_logistic(
    rows: list[tuple[tuple[float, ...], int]], dataset_version: str,
    *, split: str, iterations: int = 500, learning_rate: float = 0.05,
) -> CalibrationArtifact:
    """Small deterministic trainer for offline use. It rejects dev/test label access."""
    if split != "train":
        raise ValueError("calibration fitting may read train labels only")
    if not rows:
        raise ValueError("training rows are empty")
    weights = [0.0] * len(FEATURE_SCHEMA)
    intercept = 0.0
    for _ in range(iterations):
        gradient = [0.0] * len(weights)
        intercept_gradient = 0.0
        for vector, label in rows:
            if len(vector) != len(weights) or label not in {0, 1}:
                raise ValueError("invalid training row")
            value = intercept + sum(w * x for w, x in zip(weights, vector, strict=True))
            probability = 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value))))
            error = probability - label
            intercept_gradient += error
            for index, feature in enumerate(vector):
                gradient[index] += error * feature
        scale = learning_rate / len(rows)
        intercept -= scale * intercept_gradient
        weights = [weight - scale * gradient[index] for index, weight in enumerate(weights)]
    return CalibrationArtifact(
        dataset_version=dataset_version, model_version="logistic-python-v1",
        artifact_version=f"{dataset_version}-logistic-v1", feature_schema=FEATURE_SCHEMA,
        weights=tuple(weights), intercept=intercept,
    )


def train_with_sklearn(
    rows: list[tuple[tuple[float, ...], int]], dataset_version: str, *, split: str,
) -> CalibrationArtifact:
    """Optional sklearn adapter. Import is lazy so the offline baseline needs no sklearn install."""
    if split != "train":
        raise ValueError("calibration fitting may read train labels only")
    if not rows:
        raise ValueError("training rows are empty")
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError as error:  # pragma: no cover - optional dependency
        raise RuntimeError("install the 'ml' optional dependency to use sklearn") from error
    vectors, labels = zip(*rows, strict=True)
    model = LogisticRegression(random_state=0, solver="liblinear").fit(vectors, labels)
    artifact = CalibrationArtifact(
        dataset_version=dataset_version, model_version="sklearn-logistic-regression",
        artifact_version=f"{dataset_version}-sklearn-logistic-v1", feature_schema=FEATURE_SCHEMA,
        weights=tuple(float(value) for value in model.coef_[0]),
        intercept=float(model.intercept_[0]),
    )
    artifact.validate()
    return artifact
