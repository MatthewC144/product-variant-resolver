import copy
import json
import tempfile
import unittest
from pathlib import Path

from product_variant_resolver.evaluation import (
    evaluate, load_benchmark, percentile, recall_at_k, reciprocal_rank, safe_divide,
)
from product_variant_resolver.config import Settings

ROOT = Path(__file__).resolve().parents[2]


class MetricTests(unittest.TestCase):
    def test_zero_denominators_and_bounds(self):
        self.assertEqual(safe_divide(1, 0), 0)
        self.assertEqual(recall_at_k([], 25), 0)
        self.assertEqual(reciprocal_rank([]), 0)
        self.assertEqual(percentile([], .95), 0)
        self.assertLessEqual(recall_at_k([1, None, 25], 25), 1)

    def test_actual_benchmark_has_grouped_splits(self):
        benchmark = load_benchmark(ROOT / "data/benchmark.json")
        self.assertGreaterEqual(len(benchmark["cases"]), 90)

    def test_frozen_runner_metrics_and_ablations_are_bounded(self):
        report = evaluate(Settings(
            catalog_path=ROOT / "data/catalog.json", benchmark_path=ROOT / "data/benchmark.json",
        ))
        for metric in (report.recall_at_25, report.top1_accuracy, report.precision,
                       report.coverage, report.false_match_rate, report.abstention_rate):
            self.assertGreaterEqual(metric, 0)
            self.assertLessEqual(metric, 1)
        self.assertEqual(set(report.ablations), {"sparse", "dense", "rrf", "reranker"})
        self.assertEqual(report.metadata["default_ranker"], "rrf")
        self.assertFalse(report.metadata["reranker_runtime_enabled"])
        self.assertFalse(report.metadata["external_cross_encoder_evaluated"])
        self.assertEqual(
            report.ablations["reranker"]["top1_accuracy"],
            report.ablations["rrf"]["top1_accuracy"],
        )

    def test_family_leakage_is_rejected(self):
        payload = json.loads((ROOT / "data/benchmark.json").read_text())
        payload = copy.deepcopy(payload)
        payload["cases"][1]["casting_family"] = payload["cases"][0]["casting_family"]
        payload["cases"][1]["split"] = "dev" if payload["cases"][0]["split"] != "dev" else "test"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.json"
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                load_benchmark(path)


if __name__ == "__main__":
    unittest.main()
