import json
import unittest
from pathlib import Path

from product_variant_resolver.catalog import load_catalog
from product_variant_resolver.config import Settings
from product_variant_resolver.ingestion import InMemoryCatalogRepository, ingest_catalog
from product_variant_resolver.schemas import ResolveRequest
from product_variant_resolver.service import ResolverService
from product_variant_resolver.signals import extract_signals
from product_variant_resolver.retrieval import (
    CandidateRetrievalService, RetrievalUnavailable, StructuredRetriever,
)

ROOT = Path(__file__).resolve().parents[2]


class CatalogServiceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "data/catalog.json")
        cls.settings = Settings(
            catalog_path=ROOT / "data/catalog.json", benchmark_path=ROOT / "data/benchmark.json",
        )
        cls.service = ResolverService.from_settings(cls.settings)

    def test_actual_fixture_loads_and_idempotently_ingests(self):
        self.assertGreaterEqual(len(self.catalog.products), 120)
        repository = InMemoryCatalogRepository()
        ingest_catalog(self.catalog, repository)
        snapshot = (dict(repository.rows), repository.version, repository.checksum)
        ingest_catalog(self.catalog, repository)
        self.assertEqual(snapshot, (repository.rows, repository.version, repository.checksum))

    def test_fixture_known_cases_resolve_and_debug_is_bounded(self):
        cases = json.loads((ROOT / "data/benchmark.json").read_text())["cases"]
        for expected_status in ("matched", "ambiguous", "no_match"):
            case = next(item for item in cases if item["expected_status"] == expected_status)
            result = self.service.resolve(ResolveRequest(
                title=case["query"], debug=True, debug_candidate_limit=3,
            ))
            self.assertEqual(result.status.value, expected_status)
            self.assertLessEqual(len(result.debug.candidates), 3)
            self.assertEqual(set(result.debug.timings_ms), {
                "signal_extraction", "sparse", "dense", "structured", "fusion", "rerank",
                "calibration", "total",
            })

    def test_catalog_color_addition_needs_no_code_branch(self):
        color = next(item.product.color for item in self.catalog.products if item.product.color)
        result = self.service.resolve(ResolveRequest(title=f"Unknown casting {color}", debug=True))
        self.assertIn(color.casefold(), result.debug.signals.color_hints)

    def test_catalog_series_knowledge_needs_no_code_branch(self):
        series = next(item.product.series for item in self.catalog.products if item.product.series)
        result = self.service.resolve(ResolveRequest(title=f"Unknown casting {series}", debug=True))
        self.assertIn(series.casefold(), result.debug.signals.series_hints)

    def test_wrong_attributes_are_soft_conflicts_not_filters(self):
        target = next(item for item in self.catalog.products
                      if item.product.collector_number and item.product.color and item.product.release_year)
        wrong_color = next(item.product.color for item in self.catalog.products
                           if item.product.color and item.product.color != target.product.color)
        wrong_year = target.product.release_year - 1
        wrong_series = next(item.product.series for item in self.catalog.products
                            if item.product.series and item.product.series != target.product.series)
        query = (
            f"{target.product.casting} #{target.product.collector_number} "
            f"{wrong_color} {wrong_year} {wrong_series}"
        )
        signals = extract_signals(
            query, self.service.color_vocabulary, self.service.series_vocabulary,
        )
        candidates = self.service.retrieval.retrieve(signals, 25)
        retained = next(item for item in candidates if item.product.canonical_uuid == target.canonical_uuid)
        self.assertIn("year", retained.conflicts)
        self.assertIn("color", retained.conflicts)
        self.assertIn("series", retained.conflicts)

    def test_retriever_failure_fails_closed(self):
        class ThrowingRetriever:
            name = "throwing"

            def retrieve(self, signals, limit):
                raise TimeoutError("simulated")

        structured = StructuredRetriever(self.catalog)
        retrieval = CandidateRetrievalService([ThrowingRetriever()], structured)
        signals = extract_signals("Chevy Nomad", self.service.color_vocabulary)
        with self.assertRaises(RetrievalUnavailable):
            retrieval.retrieve(signals, 25)


if __name__ == "__main__":
    unittest.main()
