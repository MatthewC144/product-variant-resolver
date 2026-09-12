import json
import unittest
from pathlib import Path

from product_variant_resolver.catalog import Catalog, catalog_checksum, load_catalog
from product_variant_resolver.config import Settings
from product_variant_resolver.human_knowledge import (
    HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
    HumanKnowledgeV3Config,
    ReviewFamilyKnowledgeDocument,
)
from product_variant_resolver.ingestion import InMemoryCatalogRepository, ingest_catalog
from product_variant_resolver.retrieval import (
    CandidateRetrievalService,
    RetrievalUnavailable,
    StructuredRetriever,
)
from product_variant_resolver.schemas import ResolveRequest
from product_variant_resolver.service import ResolverService
from product_variant_resolver.signals import extract_signals

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

    def test_catalog_checksum_changes_when_searchable_content_changes(self):
        original = catalog_checksum(self.catalog)
        first = self.catalog.products[0]
        changed = first.product.model_copy(update={"color": "Checksum Test"})
        modified = Catalog(self.catalog.version, [
            type(first)(
                canonical_uuid=first.canonical_uuid,
                canonical_id=first.canonical_id,
                product=changed,
                aliases=first.aliases,
                identifiers=first.identifiers,
                provenance=first.provenance,
                alias_records=first.alias_records,
                identifier_records=first.identifier_records,
            ),
            *self.catalog.products[1:],
        ])
        self.assertNotEqual(original, catalog_checksum(modified))
        reordered = Catalog(self.catalog.version, list(reversed(self.catalog.products)))
        self.assertEqual(original, catalog_checksum(reordered))

    def test_failed_ingestion_rolls_back_every_prior_change(self):
        repository = InMemoryCatalogRepository()
        ingest_catalog(self.catalog, repository)
        snapshot = (dict(repository.rows), repository.version, repository.checksum)
        first, second = self.catalog.products[:2]
        invalid_second = type(second)(
            canonical_uuid=second.canonical_uuid,
            canonical_id=first.canonical_id,
            product=second.product,
            aliases=second.aliases,
            identifiers=second.identifiers,
            provenance=second.provenance,
            alias_records=second.alias_records,
            identifier_records=second.identifier_records,
        )
        invalid = Catalog("invalid", [first, invalid_second])
        with self.assertRaises(ValueError):
            ingest_catalog(invalid, repository)
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
                "signal_extraction", "human_knowledge_retrieval", "sparse", "dense",
                "structured", "fusion", "rerank", "calibration", "total",
            })

    def test_human_catalog_is_a_second_noncanonical_retrieval_source(self):
        result = self.service.resolve(ResolveRequest(
            title="Hot Wheels BMW M3 GT2 Neon Speeders",
            debug=True,
            debug_candidate_limit=3,
        ))
        self.assertTrue(result.debug.human_knowledge_candidates)
        top = result.debug.human_knowledge_candidates[0]
        self.assertEqual(top.casting, "BMW M3 GT2")
        self.assertEqual(top.identity_status, "needs_canonical_review")
        self.assertGreater(len(top.matched_tokens), 2)
        self.assertIsNone(result.canonical_uuid)
        self.assertIsNone(result.canonical_id)

    def test_review_family_is_retrieved_internally_but_never_becomes_canonical(self):
        query = "Hot Wheels Proton Saga"
        human_candidates = self.service.human_knowledge.retrieve(
            extract_signals(query), 5
        )
        family = next(
            item
            for item in human_candidates
            if isinstance(item.document, ReviewFamilyKnowledgeDocument)
            and item.document.casting == "Proton Saga"
        )
        self.assertLessEqual(family.rrf_rank, 5)

        result = self.service.resolve(ResolveRequest(title=query, debug=False))
        self.assertEqual(result.status.value, "no_match")
        self.assertIsNone(result.canonical_uuid)
        self.assertIsNone(result.canonical_id)
        self.assertIsNone(result.product)

    def test_v3_character_evidence_remains_noncanonical_and_debug_off_is_compatible(self):
        config = HumanKnowledgeV3Config(
            artifact_version="human-knowledge-retrieval-v3-test-fixture",
            artifact_sha256="a" * 64,
            character_score_floor=0.25,
            character_rrf_weight=1.0,
            sparse_rrf_weight=1.0,
            dense_rrf_weight=1.0,
            dense_dimensions=192,
            rrf_k=60,
            source_candidate_limit=25,
            index_version=HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
        )
        v3_service = ResolverService(
            self.settings,
            self.catalog,
            self.service.human_catalog,
            human_knowledge_v3_config=config,
        )

        typo = v3_service.resolve(
            ResolveRequest(title="Protn Sagx", debug=True, debug_candidate_limit=5)
        )
        family = next(
            item
            for item in typo.debug.human_knowledge_candidates
            if item.casting == "Proton Saga"
        )
        self.assertEqual(typo.status.value, "no_match")
        self.assertIsNone(typo.canonical_uuid)
        self.assertIsNone(typo.canonical_id)
        self.assertIsNone(family.sparse_rank)
        self.assertEqual(family.character_rank, 1)
        self.assertGreater(family.character_score or 0, 0.7)
        self.assertEqual(
            typo.debug.model_versions["human_knowledge"],
            "human-knowledge-hybrid-v3",
        )
        self.assertEqual(
            typo.debug.human_knowledge_retrieval_artifact_version,
            "human-knowledge-retrieval-v3-test-fixture",
        )
        self.assertEqual(
            typo.debug.human_knowledge_character_index.document_count, 142
        )

        request = ResolveRequest(title="2022 Chevy Nomad Red #101", debug=False)
        v2_response = self.service.resolve(request).model_dump(mode="json", exclude_none=True)
        v3_response = v3_service.resolve(request).model_dump(mode="json", exclude_none=True)
        self.assertEqual(v3_response, v2_response)
        self.assertNotIn("debug", v3_response)

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
