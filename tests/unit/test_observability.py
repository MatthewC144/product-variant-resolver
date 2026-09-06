from __future__ import annotations

import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from product_variant_resolver.catalog import load_catalog
from product_variant_resolver.human_knowledge import load_human_knowledge_catalog
from product_variant_resolver.config import Settings
from product_variant_resolver.observability import NoOpTracer, get_tracer
from product_variant_resolver.schemas import ResolveRequest
from product_variant_resolver.service import ResolverService


ROOT = Path(__file__).resolve().parents[2]


class RecordingSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, object] = {}
        self.exceptions: list[str] = []

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, exception: BaseException) -> None:
        self.exceptions.append(type(exception).__name__)


class RecordingTracer:
    def __init__(self) -> None:
        self.spans: list[RecordingSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs):  # type: ignore[no-untyped-def]
        span = RecordingSpan(name)
        self.spans.append(span)
        yield span


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            catalog_path=ROOT / "data/catalog.json",
            benchmark_path=ROOT / "data/benchmark.json",
            ui_path=ROOT / "ui",
        )

    def test_disabled_tracing_is_dependency_free_noop(self) -> None:
        self.assertIsInstance(get_tracer(False), NoOpTracer)
        with patch.dict(sys.modules, {"opentelemetry": None}):
            self.assertIsInstance(get_tracer(True), NoOpTracer)

    def test_stage_spans_have_correlation_without_raw_title(self) -> None:
        tracer = RecordingTracer()
        service = ResolverService(
            self.settings,
            load_catalog(self.settings.catalog_path),
            load_human_knowledge_catalog(self.settings.human_catalog_path),
            tracer=tracer,
        )
        raw_title = "2022 Chevy Nomad Red #101 private-marker"
        with self.assertLogs("product_variant_resolver.resolver", level="INFO") as captured:
            response = service.resolve(
                ResolveRequest(title=raw_title, debug=True), request_id="request-test-19",
            )

        self.assertEqual(response.status.value, "matched")
        names = [span.name for span in tracer.spans]
        self.assertEqual(names, [
            "pvr.resolve", "pvr.signal_extraction", "pvr.human_knowledge_retrieval",
            "pvr.sparse", "pvr.dense",
            "pvr.structured", "pvr.fusion", "pvr.rerank", "pvr.calibration",
        ])
        attributes = repr([span.attributes for span in tracer.spans])
        logs = "\n".join(captured.output)
        self.assertIn("request-test-19", attributes)
        self.assertIn("request-test-19", logs)
        self.assertNotIn(raw_title, attributes)
        self.assertNotIn(raw_title, logs)
        self.assertEqual(set(response.debug.timings_ms), {
            "signal_extraction", "human_knowledge_retrieval", "sparse", "dense",
            "structured", "fusion", "rerank",
            "calibration", "total",
        })
        self.assertTrue(all(value >= 0 for value in response.debug.timings_ms.values()))


if __name__ == "__main__":
    unittest.main()
