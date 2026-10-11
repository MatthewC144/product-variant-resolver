from __future__ import annotations

from pathlib import Path

import pytest

from product_variant_resolver.image_search_evaluation import ExpectedFullIdentity
from product_variant_resolver.image_search_result_set_dataset import (
    CATALOG_SHA256,
    DATASET,
    FROZEN_DATASET_SHA256,
    ResultSetDataset,
    SearchResultText,
    _expected_membership,
    check,
    validate_membership,
)
from product_variant_resolver.serper_dual_source_evaluation import (
    FROZEN_DATASET_SHA256 as POSITIVE_DATASET_SHA256,
)
from product_variant_resolver.serper_dual_source_policy_calibration import (
    POLICY_DATASET_SHA256,
)

ROOT = Path(__file__).resolve().parents[2]


def _payload() -> dict[str, object]:
    records = []
    for index, expected in enumerate(_expected_membership(ROOT), start=1):
        record = dict(expected)
        identity = record["expected_full_identity"]
        assert isinstance(identity, ExpectedFullIdentity)
        record["expected_full_identity"] = identity.model_dump(mode="json")
        records.append(
            {
                "id": f"isrs-{index:04d}",
                **record,
                "results": [],
            }
        )
    return {
        "dataset_version": "image-search-result-set-query-v1",
        "catalog_sha256": CATALOG_SHA256,
        "positive_parent_dataset_sha256": POSITIVE_DATASET_SHA256,
        "policy_parent_dataset_sha256": POLICY_DATASET_SHA256,
        "record_count": 140,
        "result_count": 0,
        "records": records,
    }


def test_frozen_membership_has_exact_development_counts_and_no_holdout() -> None:
    dataset = ResultSetDataset.model_validate(_payload())
    validate_membership(dataset, ROOT)
    assert sum(row.development_role == "positive_development" for row in dataset.records) == 100
    assert sum(row.development_role == "no_match_development" for row in dataset.records) == 40
    assert all(
        row.parent_target_id.startswith(("sds-target-", "sdsp-target-")) for row in dataset.records
    )


def test_empty_result_sets_are_preserved_as_valid_provider_outcomes() -> None:
    dataset = ResultSetDataset.model_validate(_payload())
    assert dataset.result_count == 0
    assert all(not row.results for row in dataset.records)


def test_raw_and_cleaned_text_reject_urls() -> None:
    with pytest.raises(ValueError, match="URL-free"):
        SearchResultText(raw="https://example.com/item", cleaned="example item")
    with pytest.raises(ValueError, match="URL-free"):
        SearchResultText(raw="example item", cleaned="http://example.com/item")


def test_result_set_rejects_duplicate_raw_titles() -> None:
    payload = _payload()
    records = payload["records"]
    assert isinstance(records, list)
    records[0]["results"] = [
        {"raw": "Hot Wheels Alpha", "cleaned": "Hot Wheels Alpha"},
        {"raw": "hot wheels alpha", "cleaned": "hot wheels alpha"},
    ]
    payload["result_count"] = 2
    with pytest.raises(ValueError, match="unique"):
        ResultSetDataset.model_validate(payload)


def test_membership_rejects_replacing_a_hard_target() -> None:
    payload = _payload()
    records = payload["records"]
    assert isinstance(records, list)
    records[0]["expected_casting"] = records[1]["expected_casting"]
    records[0]["expected_full_identity"] = records[1]["expected_full_identity"]
    dataset = ResultSetDataset.model_validate(payload)
    with pytest.raises(ValueError, match="frozen parent field"):
        validate_membership(dataset, ROOT)


def test_schema_rejects_secret_or_provider_metadata_fields() -> None:
    payload = _payload()
    records = payload["records"]
    assert isinstance(records, list)
    records[0]["api_key"] = "forbidden"
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ResultSetDataset.model_validate(payload)


def test_frozen_result_set_dataset_is_minimal_and_valid() -> None:
    dataset = check(ROOT)
    assert dataset.record_count == 140
    assert dataset.result_count == 1_108
    assert sum(not row.results for row in dataset.records) == 23
    assert sorted(path.name for path in (ROOT / DATASET).parent.iterdir()) == ["dataset.json"]
    import hashlib

    assert hashlib.sha256((ROOT / DATASET).read_bytes()).hexdigest() == FROZEN_DATASET_SHA256
