from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from product_variant_resolver.human_knowledge import (
    HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
    HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS,
    HUMAN_KNOWLEDGE_V3_ARTIFACT_SCHEMA,
    HUMAN_KNOWLEDGE_V3_ELIGIBLE_FOR,
    HUMAN_KNOWLEDGE_V3_EXCLUDED_FROM,
    HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION,
    CharacterIdentityIndex,
    HumanKnowledgeCatalog,
    HumanKnowledgeRetriever,
    HumanKnowledgeV3Config,
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
    load_human_knowledge_v3_config,
)
from product_variant_resolver.retrieval import HashingEmbedding
from product_variant_resolver.signals import extract_signals

ROOT = Path(__file__).resolve().parents[2]
HUMAN_CATALOG = ROOT / "data/human_backed_catalog.json"
FAMILY_PROJECTION = ROOT / "data/review_family_knowledge.json"
FAMILY_MANIFEST = ROOT / "data/review_family_knowledge_manifest.json"
DEVELOPMENT_PACK = (
    ROOT
    / "data/evaluation/family-retrieval-development-v1/development-pack.json"
)
DEVELOPMENT_MANIFEST = (
    ROOT
    / "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _v3_config(*, floor: float = 0.25, weight: float = 1.0) -> HumanKnowledgeV3Config:
    return HumanKnowledgeV3Config(
        artifact_version="human-knowledge-retrieval-v3-test-fixture",
        artifact_sha256="0" * 64,
        character_score_floor=floor,
        character_rrf_weight=weight,
        sparse_rrf_weight=1.0,
        dense_rrf_weight=1.0,
        dense_dimensions=192,
        rrf_k=60,
        source_candidate_limit=25,
        index_version=HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
    )


def _reference(path: Path, version: str) -> dict[str, str]:
    return {"file": path.name, "sha256": _sha256(path), "version": version}


def _v3_artifact() -> dict:
    import product_variant_resolver.human_knowledge as implementation

    implementation_path = Path(implementation.__file__)
    return {
        "artifact_version": "human-knowledge-retrieval-v3-test-fixture",
        "character_index": {
            "allowed_fields": HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS,
            "gram_sizes": [2, 3],
            "modes": ["spaced", "compact"],
            "stable_tie_break": "knowledge_uuid",
            "version": HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
            "window_token_radius": 1,
        },
        "configuration": {
            "character_rrf_weight": 1.0,
            "character_score_floor": 0.25,
            "dense_dimensions": 192,
            "dense_rrf_weight": 1.0,
            "rrf_k": 60,
            "selection_candidate_limit": 5,
            "source_candidate_limit": 25,
            "sparse_rrf_weight": 1.0,
        },
        "eligible_for": HUMAN_KNOWLEDGE_V3_ELIGIBLE_FOR,
        "excluded_from": HUMAN_KNOWLEDGE_V3_EXCLUDED_FROM,
        "implementation": {
            "file": implementation_path.name,
            "sha256": _sha256(implementation_path),
        },
        "retriever_version": HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION,
        "schema_version": HUMAN_KNOWLEDGE_V3_ARTIFACT_SCHEMA,
        "sources": {
            "development_manifest": _reference(
                DEVELOPMENT_MANIFEST, "family-retrieval-development-v1"
            ),
            "development_pack": _reference(
                DEVELOPMENT_PACK, "family-retrieval-development-v1"
            ),
            "human_catalog": _reference(HUMAN_CATALOG, "human-backed-catalog-v1"),
            "review_family_knowledge": _reference(
                FAMILY_PROJECTION,
                "review-family-knowledge-fandom-2025-r790665-v1",
            ),
        },
        "status": "selected_development_configuration",
    }


def _tiny_variant() -> HumanVariantKnowledgeDocument:
    return HumanVariantKnowledgeDocument(
        casting_uuid=UUID(int=1),
        casting_id="casting-alpha",
        provisional_variant_uuid=UUID(int=2),
        provisional_variant_id="variant-alpha",
        brand="Brandonly",
        casting="Alpha",
        series_label="RareSeries",
        variant_label="RedVariant",
        identity_status="needs_canonical_review",
        human_label_names=("Alpha",),
        pricing_keywords=("SecretPricing",),
        initial_names=("RawRecognition",),
        source_case_ids=("case-1",),
    )


class HumanKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_human_knowledge_catalog(
            HUMAN_CATALOG, FAMILY_PROJECTION, FAMILY_MANIFEST
        )
        cls.retriever = HumanKnowledgeRetriever(cls.catalog, HashingEmbedding())

    def test_catalog_loads_typed_review_gated_documents(self) -> None:
        self.assertEqual(self.catalog.version, "human-backed-catalog-v1")
        self.assertEqual(
            self.catalog.review_family_version,
            "review-family-knowledge-fandom-2025-r790665-v1",
        )
        self.assertEqual(len(self.catalog.documents), 142)
        self.assertEqual(self.catalog.variant_document_count, 100)
        self.assertEqual(self.catalog.review_family_document_count, 42)
        self.assertTrue(
            all(
                item.identity_status == "needs_canonical_review"
                for item in self.catalog.documents
                if isinstance(item, HumanVariantKnowledgeDocument)
            )
        )
        self.assertTrue(
            all(
                item.identity_status == "family_accepted_variants_unreviewed"
                for item in self.catalog.documents
                if isinstance(item, ReviewFamilyKnowledgeDocument)
            )
        )
        self.assertEqual(
            len({item.knowledge_id for item in self.catalog.documents}), 142
        )
        self.assertEqual(
            len({item.knowledge_uuid for item in self.catalog.documents}), 142
        )

    def test_hybrid_retrieval_returns_matching_human_evidence(self) -> None:
        signals = extract_signals("Hot Wheels BMW M3 GT2 Neon Speeders")
        candidates = self.retriever.retrieve(signals, 3)
        self.assertEqual(candidates[0].document.casting, "BMW M3 GT2")
        self.assertEqual(candidates[0].document.knowledge_type, "provisional_variant")
        self.assertIsInstance(candidates[0].document, HumanVariantKnowledgeDocument)
        self.assertEqual(candidates[0].document.variant_label, "Neon Speeders")
        self.assertEqual(candidates[0].sparse_rank, 1)
        self.assertEqual(candidates[0].dense_rank, 1)
        self.assertIn("m3", candidates[0].matched_tokens)
        self.assertIn("gt2", candidates[0].matched_tokens)
        self.assertIsNone(candidates[0].character_rank)
        self.assertIsNone(candidates[0].character_score)

    def test_character_identity_fields_are_strictly_allowlisted(self) -> None:
        variant = _tiny_variant()
        self.assertEqual(variant.character_identity_texts, ("Alpha", "Alpha"))
        prohibited = {
            variant.brand,
            variant.series_label,
            variant.variant_label,
            *variant.pricing_keywords,
            *variant.initial_names,
            *variant.source_case_ids,
        }
        self.assertTrue(prohibited.isdisjoint(variant.character_identity_texts))
        family = next(
            item
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        )
        self.assertEqual(
            family.character_identity_texts, (family.casting, *family.aliases)
        )
        self.assertTrue(set(family.source_record_ids).isdisjoint(family.character_identity_texts))

    def test_character_index_uses_postings_and_frozen_metadata(self) -> None:
        index = CharacterIdentityIndex(self.catalog.documents)
        metadata = index.metadata.as_dict()
        self.assertEqual(metadata["document_count"], 142)
        self.assertGreater(metadata["posting_count"], 0)
        self.assertGreater(metadata["posting_entry_count"], metadata["posting_count"])
        self.assertEqual(metadata["gram_sizes"], [2, 3])
        self.assertEqual(metadata["modes"], ["spaced", "compact"])
        self.assertEqual(metadata["allowed_fields"], HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS)

    def test_character_only_candidate_enters_union_without_sparse_rank(self) -> None:
        retriever = HumanKnowledgeRetriever(
            self.catalog, HashingEmbedding(), _v3_config()
        )
        candidates = retriever.retrieve(extract_signals("Protn Sagx"), 5)
        target = next(item for item in candidates if item.document.casting == "Proton Saga")
        self.assertEqual(target.rrf_rank, 1)
        self.assertIsNone(target.sparse_rank)
        self.assertIsNone(target.sparse_score)
        self.assertEqual(target.character_rank, 1)
        self.assertGreater(target.character_score or 0, 0.7)
        self.assertIsNotNone(target.dense_rank)

    def test_missing_source_ranks_contribute_zero_to_weighted_rrf(self) -> None:
        catalog = HumanKnowledgeCatalog("tiny-v1", "none", [_tiny_variant()])
        retriever = HumanKnowledgeRetriever(catalog, HashingEmbedding(), _v3_config())

        sparse_only = retriever.retrieve(extract_signals("RareSeries"), 1)[0]
        self.assertEqual(sparse_only.sparse_rank, 1)
        self.assertIsNone(sparse_only.character_rank)
        self.assertAlmostEqual(sparse_only.rrf_score, 2 / 61)

        character_only = retriever.retrieve(extract_signals("Alphx"), 1)[0]
        self.assertIsNone(character_only.sparse_rank)
        self.assertEqual(character_only.character_rank, 1)
        self.assertAlmostEqual(character_only.rrf_score, 2 / 61)

    def test_compact_form_and_stable_uuid_tie_break(self) -> None:
        first = ReviewFamilyKnowledgeDocument(
            review_family_uuid=UUID(int=1),
            review_family_id="family-1",
            brand="Brand",
            casting="Alpha Beta",
            aliases=("Alpha Beta",),
            source_record_ids=("row-1",),
            identity_status="family_accepted_variants_unreviewed",
        )
        second = ReviewFamilyKnowledgeDocument(
            review_family_uuid=UUID(int=2),
            review_family_id="family-2",
            brand="Brand",
            casting="Alpha Beta",
            aliases=("Alpha Beta",),
            source_record_ids=("row-2",),
            identity_status="family_accepted_variants_unreviewed",
        )
        ranked = CharacterIdentityIndex((second, first)).rank(
            "AlphaBeta", score_floor=0.25
        )
        self.assertEqual([item.knowledge_id for item, _ in ranked], ["family-1", "family-2"])
        self.assertAlmostEqual(ranked[0][1], 1.0)

    def test_character_index_rejects_empty_short_and_invalid_floor(self) -> None:
        short = ReviewFamilyKnowledgeDocument(
            review_family_uuid=UUID(int=3),
            review_family_id="family-short",
            brand="Brand",
            casting="A",
            aliases=("A",),
            source_record_ids=("row-3",),
            identity_status="family_accepted_variants_unreviewed",
        )
        with self.assertRaisesRegex(ValueError, "too short"):
            CharacterIdentityIndex((short,))
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            CharacterIdentityIndex((_tiny_variant(),)).rank("Alpha", score_floor=float("nan"))

    def test_v3_artifact_is_strict_checksum_bound_and_rejects_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "v3.json"
            artifact = _v3_artifact()
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            config = load_human_knowledge_v3_config(
                artifact_path,
                human_catalog_path=HUMAN_CATALOG,
                review_family_path=FAMILY_PROJECTION,
                development_pack_path=DEVELOPMENT_PACK,
                development_manifest_path=DEVELOPMENT_MANIFEST,
                dense_dimensions=192,
            )
            self.assertEqual(config.character_score_floor, 0.25)
            self.assertEqual(config.character_rrf_weight, 1.0)
            self.assertEqual(config.artifact_sha256, _sha256(artifact_path))

            invalid_evidence = json.loads(json.dumps(artifact))
            invalid_evidence["selection_evidence"] = {
                "file": "../external.json", "sha256": "0" * 64, "configurations": []}
            artifact_path.write_text(json.dumps(invalid_evidence), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside development reports"):
                load_human_knowledge_v3_config(
                    artifact_path, human_catalog_path=HUMAN_CATALOG,
                    review_family_path=FAMILY_PROJECTION,
                    development_pack_path=DEVELOPMENT_PACK,
                    development_manifest_path=DEVELOPMENT_MANIFEST,
                    dense_dimensions=192,
                )

            invalid = json.loads(json.dumps(artifact))
            invalid["configuration"]["character_score_floor"] = 0.24
            artifact_path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported or mismatched"):
                load_human_knowledge_v3_config(
                    artifact_path,
                    human_catalog_path=HUMAN_CATALOG,
                    review_family_path=FAMILY_PROJECTION,
                    development_pack_path=DEVELOPMENT_PACK,
                    development_manifest_path=DEVELOPMENT_MANIFEST,
                    dense_dimensions=192,
                )

            stale = json.loads(json.dumps(artifact))
            stale["implementation"]["sha256"] = "0" * 64
            artifact_path.write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "implementation reference is stale"):
                load_human_knowledge_v3_config(
                    artifact_path,
                    human_catalog_path=HUMAN_CATALOG,
                    review_family_path=FAMILY_PROJECTION,
                    development_pack_path=DEVELOPMENT_PACK,
                    development_manifest_path=DEVELOPMENT_MANIFEST,
                    dense_dimensions=192,
                )

    def test_no_shared_tokens_returns_no_suggestion(self) -> None:
        signals = extract_signals("qzxv completely unknown")
        self.assertEqual(self.retriever.retrieve(signals, 5), [])

    def test_limit_is_enforced(self) -> None:
        signals = extract_signals("Hot Wheels")
        self.assertEqual(len(self.retriever.retrieve(signals, 2)), 2)
        with self.assertRaisesRegex(ValueError, "between 1 and 25"):
            self.retriever.retrieve(signals, 26)

    def test_all_42_family_names_retrieve_the_expected_document_within_top_five(self) -> None:
        family_documents = [
            item
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        ]
        self.assertEqual(len(family_documents), 42)
        worst_rank = 0
        for document in family_documents:
            candidates = self.retriever.retrieve(
                extract_signals(f"{document.brand} {document.casting}"), 5
            )
            matching = next(
                item
                for item in candidates
                if item.document.knowledge_id == document.review_family_id
            )
            worst_rank = max(worst_rank, matching.rrf_rank)
        self.assertLessEqual(worst_rank, 5)

    def test_family_searchable_text_uses_only_approved_name_fields(self) -> None:
        family = next(
            item
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        )
        self.assertEqual(
            family.searchable_text,
            " ".join((family.brand, family.casting, *family.aliases)),
        )
        self.assertFalse(
            set(family.source_record_ids) & set(family.searchable_text.split())
        )

    def test_merge_and_hold_families_create_no_review_family_document(self) -> None:
        registry = json.loads(
            (ROOT / "data/review_family_registry.json").read_text(encoding="utf-8")
        )
        projected_ids = {
            item.review_family_id
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        }
        merge_ids = {item["source_family_review_id"] for item in registry["merge_links"]}
        hold_ids = {item["review_family_id"] for item in registry["hold_exclusions"]}
        self.assertTrue(projected_ids.isdisjoint(merge_ids | hold_ids))
        for merge in registry["merge_links"]:
            candidates = self.retriever.retrieve(
                extract_signals(f"{merge['brand']} {merge['display_name']}"), 5
            )
            self.assertTrue(
                any(
                    isinstance(item.document, HumanVariantKnowledgeDocument)
                    and item.document.casting == merge["target_casting"]
                    for item in candidates
                )
            )
        for hold in registry["hold_exclusions"]:
            candidates = self.retriever.retrieve(
                extract_signals(f"{hold['brand']} {hold['display_name']}"), 5
            )
            self.assertFalse(
                any(
                    isinstance(item.document, ReviewFamilyKnowledgeDocument)
                    and item.document.casting == hold["display_name"]
                    for item in candidates
                )
            )

    def test_loader_rejects_a_variant_that_bypasses_canonical_review(self) -> None:
        source = HUMAN_CATALOG
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["castings"][0]["provisional_variants"][0]["identity_status"] = "canonical"

        with tempfile.TemporaryDirectory() as directory:
            invalid_path = Path(directory) / "invalid-human-catalog.json"
            invalid_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid provisional variant"):
                load_human_knowledge_catalog(
                    invalid_path, FAMILY_PROJECTION, FAMILY_MANIFEST
                )

    def test_family_loader_rejects_checksum_field_scope_and_count_changes(self) -> None:
        source_projection = json.loads(FAMILY_PROJECTION.read_text(encoding="utf-8"))
        source_manifest = json.loads(FAMILY_MANIFEST.read_text(encoding="utf-8"))

        mutations = (
            (
                lambda payload: payload["documents"][0].update(
                    {"decision_reason": "must never become searchable"}
                ),
                "fields differ",
            ),
            (
                lambda payload: payload["eligible_for"].append("canonical_retrieval"),
                "eligibility boundary",
            ),
            (lambda payload: payload["documents"].pop(), "exactly 42"),
        )
        for mutate, expected_error in mutations:
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as directory:
                    projection = json.loads(json.dumps(source_projection))
                    mutate(projection)
                    projection_path = Path(directory) / FAMILY_PROJECTION.name
                    projection_path.write_text(json.dumps(projection), encoding="utf-8")
                    manifest = json.loads(json.dumps(source_manifest))
                    manifest["projection_sha256"] = hashlib.sha256(
                        projection_path.read_bytes()
                    ).hexdigest()
                    manifest_path = Path(directory) / FAMILY_MANIFEST.name
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, expected_error):
                        load_human_knowledge_catalog(
                            HUMAN_CATALOG, projection_path, manifest_path
                        )

        with tempfile.TemporaryDirectory() as directory:
            projection_path = Path(directory) / FAMILY_PROJECTION.name
            projection_path.write_bytes(FAMILY_PROJECTION.read_bytes())
            manifest_path = Path(directory) / FAMILY_MANIFEST.name
            manifest_path.write_bytes(FAMILY_MANIFEST.read_bytes())
            projection_path.write_text(
                FAMILY_PROJECTION.read_text(encoding="utf-8") + " ",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                load_human_knowledge_catalog(
                    HUMAN_CATALOG, projection_path, manifest_path
                )


if __name__ == "__main__":
    unittest.main()
