from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from product_variant_resolver.identity import normalize_text

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/evaluation/image-search-pointwise-no-match-holdout-v1/dataset.json"
CATALOG = ROOT / "data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json"
CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
DATASET_SHA256 = "b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_owner_reviewed_holdout_is_frozen_and_not_authorized_for_scoring() -> None:
    payload = _load(DATASET)

    assert _sha256(DATASET) == DATASET_SHA256
    assert payload["dataset_version"] == "image-search-pointwise-no-match-holdout-v1"
    assert payload["status"] == "owner_reviewed_frozen_not_scored"
    assert payload["authority_scope"] == (
        "frozen_third_party_catalog_relative_not_manufacturer_or_global_truth"
    )
    assert payload["frozen_catalog_sha256"] == CATALOG_SHA256
    assert payload["approval"] == {
        "approved_by": "project_owner",
        "approved_record_count": 20,
        "model_retuning_authorized": False,
        "resolver_scoring_authorized": False,
        "runtime_activation_authorized": False,
        "threshold_retuning_authorized": False,
    }


def test_records_are_minimal_unique_and_identity_complete() -> None:
    records = _load(DATASET)["records"]
    assert isinstance(records, list)
    assert len(records) == 20
    assert [record["id"] for record in records] == [f"hnm-{index:03d}" for index in range(1, 21)]
    assert len({record["query"] for record in records}) == 20
    assert len({normalize_text(record["expected_casting"]) for record in records}) == 20

    identity_fields = {
        "brand",
        "casting",
        "collector_number",
        "release_year",
        "series",
        "series_position",
        "toy_number",
    }
    for record in records:
        assert set(record) == {"id", "query", "expected_casting", "expected_full_identity"}
        identity = record["expected_full_identity"]
        assert set(identity) == identity_fields
        assert identity["brand"] == "Hot Wheels"
        assert identity["release_year"] == "2022"
        assert record["expected_casting"] == identity["casting"]


def test_every_expected_family_is_absent_from_the_bound_frozen_catalog() -> None:
    assert _sha256(CATALOG) == CATALOG_SHA256
    catalog_records = _load(CATALOG)["records"]
    catalog_families = {
        (normalize_text(record["brand"]), normalize_text(record["casting_name"]))
        for record in catalog_records
    }

    for record in _load(DATASET)["records"]:
        identity = record["expected_full_identity"]
        expected_family = (
            normalize_text(identity["brand"]),
            normalize_text(record["expected_casting"]),
        )
        assert expected_family not in catalog_families


def test_dataset_contains_no_collection_metadata_or_urls() -> None:
    payload = _load(DATASET)
    forbidden_keys = {
        "color",
        "edition",
        "image",
        "image_sha256",
        "image_url",
        "raw_response",
        "search_time",
        "source_url",
        "variant_note",
    }

    for record in payload["records"]:
        assert forbidden_keys.isdisjoint(record)
        assert forbidden_keys.isdisjoint(record["expected_full_identity"])
        query = record["query"].casefold()
        assert "http://" not in query
        assert "https://" not in query
