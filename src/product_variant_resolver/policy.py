from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .calibration import decision_score
from .retrieval import Candidate
from .schemas import ResolutionStatus


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    version: str = "fixture-v1-rrf-trained-v2"
    match_threshold: float = 0.67
    no_match_threshold: float = 0.32
    margin_threshold: float = 0.08
    max_conflicts: int = 2

    @classmethod
    def load(cls, path: Path) -> "DecisionPolicy":
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = {field: payload[field] for field in cls.__dataclass_fields__ if field in payload}
        policy = cls(**values)
        if not 0 <= policy.no_match_threshold <= policy.match_threshold <= 1:
            raise ValueError("invalid policy thresholds")
        if not 0 <= policy.margin_threshold <= 1 or policy.max_conflicts < 0:
            raise ValueError("invalid policy margin/conflict limits")
        return policy

    def decide(self, candidates: list[Candidate], confidence: float) -> tuple[ResolutionStatus, str]:
        if not math.isfinite(confidence):
            raise ValueError("non-finite confidence")
        if not candidates:
            return ResolutionStatus.no_match, "no_candidates"
        top_score = decision_score(candidates[0])
        second = decision_score(candidates[1]) if len(candidates) > 1 else 0.0
        margin = top_score - second
        if confidence < self.no_match_threshold or top_score <= 0:
            return ResolutionStatus.no_match, "no_candidate_above_threshold"
        if len(candidates[0].conflicts) > self.max_conflicts:
            return ResolutionStatus.ambiguous, "too_many_attribute_conflicts"
        if confidence < self.match_threshold:
            return ResolutionStatus.ambiguous, "confidence_below_match_threshold"
        if len(candidates) > 1 and margin < self.margin_threshold:
            return ResolutionStatus.ambiguous, "top1_top2_margin_too_small"
        return ResolutionStatus.matched, "score_and_margin_above_threshold"


def select_policy(
    dev_rows: list[tuple[float, float, int]], *, split: str, version: str = "fixture-v1",
) -> DecisionPolicy:
    """Select the highest-coverage threshold with >=90% precision on dev only."""
    if split != "dev":
        raise ValueError("threshold selection may read dev labels only")
    best = 0.99
    for threshold in [value / 100 for value in range(30, 100)]:
        selected = [label for confidence, _margin, label in dev_rows if confidence >= threshold]
        precision = sum(selected) / len(selected) if selected else 1.0
        if selected and precision >= 0.90:
            best = threshold
            break
    return DecisionPolicy(version=version, match_threshold=best)
