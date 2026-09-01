from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from .calibration import LogisticCalibrator, features, train_logistic
from .config import Settings
from .policy import select_policy
from .service import ResolverService
from .signals import extract_signals


def _cases(payload: dict[str, Any], split: str) -> list[dict[str, Any]]:
    if split not in {"train", "dev"}:
        raise ValueError("training pipeline may access train or dev cases only")
    return [case for case in payload.get("cases", []) if case.get("split") == split]


def _rank(service: ResolverService, query: str):  # type: ignore[no-untyped-def]
    signals = extract_signals(query, service.color_vocabulary, service.series_vocabulary)
    candidates = service.retrieval.retrieve(signals, service.settings.candidate_limit)
    return (service.reranker.rerank(signals, candidates)
            if service.settings.reranker_enabled else candidates)


def train_and_select(settings: Settings, output_directory: Path) -> tuple[Path, Path]:
    """Fit on train, select thresholds on dev, and never select or report on test."""
    payload = json.loads(settings.benchmark_path.read_text(encoding="utf-8"))
    dataset_version = str(payload.get("dataset_version", "unknown"))
    ranker_version = "heuristic" if settings.reranker_enabled else "rrf"
    service = ResolverService.from_settings(settings)
    train_rows = []
    for case in _cases(payload, "train"):
        candidates = _rank(service, case["query"])
        label = int(bool(candidates) and case.get("expected_status") == "matched"
                    and str(candidates[0].product.canonical_uuid) == str(case.get("expected_canonical_uuid")))
        train_rows.append((features(candidates), label))
    artifact = train_logistic(train_rows, dataset_version, split="train")
    artifact = replace(
        artifact,
        model_version=f"logistic-python-v1+{ranker_version}",
        artifact_version=f"{dataset_version}-{ranker_version}-logistic-v2",
    )
    calibrator = LogisticCalibrator(artifact)
    dev_rows = []
    for case in _cases(payload, "dev"):
        candidates = _rank(service, case["query"])
        confidence = calibrator.probability(candidates)
        vector = features(candidates)
        label = int(bool(candidates) and case.get("expected_status") == "matched"
                    and str(candidates[0].product.canonical_uuid) == str(case.get("expected_canonical_uuid")))
        dev_rows.append((confidence, vector[1], label))
    policy = select_policy(
        dev_rows, split="dev", version=f"{dataset_version}-{ranker_version}-trained-v2",
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    artifact_path = output_directory / f"calibration-{dataset_version}.json"
    policy_path = output_directory / f"policy-{dataset_version}.json"
    artifact.save(artifact_path)
    policy_path.write_text(json.dumps({
        **asdict(policy), "dataset_version": dataset_version,
        "selection_split": "dev", "calibration_split": "train",
        "test_labels_accessed": False,
    }, indent=2) + "\n", encoding="utf-8")
    return artifact_path, policy_path
