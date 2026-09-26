"""Regression locks for the measured neural reranker comparison v1 result."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from product_variant_resolver.neural_reranking import validate_raw_test_payload

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "data/evaluation/neural-reranker-comparison-v1"
REPORT = ROOT / "reports/neural-reranker-comparison-v1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_measured_report_is_hash_bound_and_selects_no_winner() -> None:
    report = _load(REPORT / "comparison.json")
    manifest = _load(REPORT / "comparison-manifest.json")

    assert manifest == {
        "accuracy_latency_svg_sha256": (
            "3a3156f3ba9f866c68afd435a1054ead2b29543c76cc452439df182a5f0dfe7c"
        ),
        "comparison_sha256": "f0493fc5d7b30b5e57ee382cf14e06e4fddbcebc62228b9f4b5a0dcec45b3dd2",
        "experiment_id": "neural-reranker-comparison-v1",
        "markdown_sha256": "0a90e7803db1497584ef2ee2e6b78cd47e95f750db3b9697b447a7016a7ae0fb",
        "raw_sha256": "948582264e67ad6d686a4409a41100149118d12b6e4548bbdc1265d778756884",
        "reranker_comparison_svg_sha256": (
            "028f88117af4962d4d1d25a6c765e23b9143d84cf280641f6b6f78d4d54d87c6"
        ),
        "schema_version": "pvr-neural-reranker-comparison-report-manifest-v1",
        "winner": None,
    }
    assert _sha256(REPORT / "comparison.json") == manifest["comparison_sha256"]
    assert _sha256(REPORT / "comparison.md") == manifest["markdown_sha256"]
    assert _sha256(REPORT / "accuracy-latency.svg") == manifest["accuracy_latency_svg_sha256"]
    assert _sha256(REPORT / "reranker-comparison.svg") == manifest["reranker_comparison_svg_sha256"]
    assert _sha256(EXPERIMENT / "raw/test-raw.json") == manifest["raw_sha256"]

    assert report["winner"] is None
    assert report["default_runtime_arm"] == "rrf"
    assert report["test_case_count"] == 21
    assert report["matched_test_denominator"] == 12
    assert report["collection_error_count"] == 0
    assert report["one_case_top1_increment"] == 1 / 12


def test_all_arms_tie_on_quality_and_neural_arms_fail_only_improvement_gate() -> None:
    report = _load(REPORT / "comparison.json")
    expected_metrics = {
        "top1_accuracy": (12.0, 12, 1.0),
        "mrr_at_10": (12.0, 12, 1.0),
        "recall_at_10": (12.0, 12, 1.0),
        "recall_at_25": (12.0, 12, 1.0),
        "hard_negative_accuracy": (4.0, 4, 1.0),
    }
    for arm_name in ("rrf", "neural_pointwise", "neural_listwise"):
        metrics = report["arms"][arm_name]["metrics"]
        for metric_name, (numerator, denominator, value) in expected_metrics.items():
            assert metrics[metric_name] == {
                "numerator": numerator,
                "denominator": denominator,
                "value": value,
            }

    for arm_name in ("neural_pointwise", "neural_listwise"):
        gates = report["arms"][arm_name]["gates"]
        failed = [gate for gate in gates if not gate["passed"]]
        assert [gate["name"] for gate in failed] == ["top1_absolute_gain_at_least_0_05"]
        assert failed[0]["actual"] == 0.0
        assert failed[0]["threshold"] == 0.05
        transitions = report["paired_transitions"][arm_name]
        assert len(transitions) == 12
        assert all(
            item["baseline_rank"] == item["compared_rank"] == 1 and item["direction"] == "unchanged"
            for item in transitions
        )

    assert report["arms"]["rrf"]["latency_ms"]["resolver_p95"] < 2.0
    assert report["arms"]["neural_pointwise"]["latency_ms"]["resolver_p95"] < 1_500.0
    assert report["arms"]["neural_listwise"]["latency_ms"]["resolver_p95"] < 1_500.0


def test_frozen_raw_remains_label_blind_and_candidate_sets_are_shared() -> None:
    raw = _load(EXPERIMENT / "raw/test-raw.json")
    raw_manifest = _load(EXPERIMENT / "raw/test-raw-manifest.json")

    validate_raw_test_payload(raw)
    assert raw_manifest["label_blind"] is True
    assert raw_manifest["retrieval_call_count"] == 21
    assert raw_manifest["retrieval_error_count"] == 0
    assert raw_manifest["raw_sha256"] == _sha256(EXPERIMENT / "raw/test-raw.json")
    assert len(raw["rows"]) == len({row["case_id"] for row in raw["rows"]}) == 21

    for row in raw["rows"]:
        assert row["error"] is None
        candidate_ids = [candidate["canonical_uuid"] for candidate in row["candidates"]]
        assert len(candidate_ids) == len(set(candidate_ids)) == 25
        assert candidate_ids == [item["canonical_uuid"] for item in row["arms"]["rrf"]]
        assert set(candidate_ids) == {
            item["canonical_uuid"] for item in row["arms"]["neural_pointwise"]
        }
        assert set(candidate_ids) == {
            item["canonical_uuid"] for item in row["arms"]["neural_listwise"]
        }


def test_readme_publishes_the_same_null_result_without_inflated_claims() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "**100-case synthetic/curated fixture benchmark**" in readme
    assert "The formal result is **`winner: null`**" in readme
    assert "| RRF | `12/12` | `12/12` | `4/4` | `12/12` | `1.398 ms` | Runtime baseline |" in readme
    assert "| Neural pointwise | `12/12` | `12/12` | `4/4` | `12/12` | `89.164 ms`" in readme
    assert "| Neural listwise | `12/12` | `12/12` | `4/4` | `12/12` | `89.583 ms`" in readme
    assert "does not establish production" in readme
    assert "accuracy or statistical generality" in readme
