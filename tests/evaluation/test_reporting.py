from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from product_variant_resolver.config import Settings
from product_variant_resolver.reporting import (
    NON_PRODUCTION_NOTICE,
    REPORT_SCHEMA_VERSION,
    generate_report,
    validate_report_payload,
)


ROOT = Path(__file__).resolve().parents[2]


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = Settings(
            catalog_path=ROOT / "data/catalog.json",
            benchmark_path=ROOT / "data/benchmark.json",
            ui_path=ROOT / "ui",
        )

    def test_versioned_report_schema_disclosures_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = generate_report(self.settings, Path(directory))
            self.assertEqual(paths["json"].parent.name, "fixture-v1")
            self.assertEqual(paths["json"].name, "evaluation-fixture-v1-test.json")
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            validate_report_payload(payload)
            self.assertEqual(payload["report_schema_version"], REPORT_SCHEMA_VERSION)
            self.assertEqual(payload["disclosure"]["notice"], NON_PRODUCTION_NOTICE)
            self.assertEqual(payload["dataset"]["sample_count"], 21)
            self.assertEqual(len(payload["latency_evidence"]["pipeline"]["samples_ms"]), 21)
            self.assertEqual(len(payload["latency_evidence"]["http"]["samples_ms"]), 21)
            self.assertGreaterEqual(payload["latency_evidence"]["http"]["warmup_requests"], 1)
            self.assertFalse(payload["latency_evidence"]["container"]["measured"])
            self.assertFalse(payload["r13_http_smoke"]["container_latency_validated"])
            self.assertEqual(payload["runtime_ranker_decision"]["selected_default"], "rrf")
            self.assertFalse(
                payload["runtime_ranker_decision"]["heuristic_reranker_runtime_enabled"],
            )
            self.assertFalse(
                payload["runtime_ranker_decision"]["external_cross_encoder_evaluated"],
            )

            markdown = paths["markdown"].read_text(encoding="utf-8")
            self.assertIn("21 synthetic fixture test cases", markdown)
            self.assertIn("does not establish production accuracy", markdown)
            self.assertIn("Raw derivation", markdown)
            self.assertIn("Warmed HTTP `/resolve`", markdown)
            self.assertIn("Container latency measured: **false**", markdown)
            self.assertIn("does not validate Docker/container", markdown)
            self.assertIn("R11 alternative decision", markdown)
            self.assertIn("No external cross-encoder was evaluated", markdown)
            self.assertIn(payload["configuration"]["benchmark_sha256"], markdown)
            for name in (
                "retrieval_ablation", "reranker_comparison", "precision_coverage", "latency",
            ):
                content = paths[name].read_text(encoding="utf-8")
                self.assertIn("<svg", content)
                self.assertIn("<title>", content)

    def test_schema_rejects_untraceable_metric_and_missing_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = generate_report(self.settings, Path(directory))
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))
        broken_metric = copy.deepcopy(payload)
        broken_metric["headline_metrics"]["precision"] = .123
        with self.assertRaisesRegex(ValueError, "traceable"):
            validate_report_payload(broken_metric)
        broken_ablation = copy.deepcopy(payload)
        broken_ablation["ablations"]["rrf"]["top1_accuracy"] = .123
        with self.assertRaisesRegex(ValueError, "raw ranks"):
            validate_report_payload(broken_ablation)
        broken_latency = copy.deepcopy(payload)
        broken_latency["headline_metrics"]["http_p95_latency_ms"] = 0
        with self.assertRaisesRegex(ValueError, "http p95"):
            validate_report_payload(broken_latency)
        hidden_container_gap = copy.deepcopy(payload)
        hidden_container_gap["latency_evidence"]["container"]["measured"] = True
        with self.assertRaisesRegex(ValueError, "container latency"):
            validate_report_payload(hidden_container_gap)
        false_external_claim = copy.deepcopy(payload)
        false_external_claim["runtime_ranker_decision"]["external_cross_encoder_evaluated"] = True
        with self.assertRaisesRegex(ValueError, "cross-encoder"):
            validate_report_payload(false_external_claim)
        broken_disclosure = copy.deepcopy(payload)
        broken_disclosure["disclosure"]["notice"] = "benchmark"
        with self.assertRaisesRegex(ValueError, "disclosure"):
            validate_report_payload(broken_disclosure)


if __name__ == "__main__":
    unittest.main()
