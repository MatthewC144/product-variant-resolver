from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from product_variant_resolver.catalog import catalog_checksum, load_catalog


def _row(
    number: int,
    *,
    canonical_id: str,
    release_key: str | None,
    toy_number: str,
    casting: str = "Repeated Casting",
    identifier_type: str = "toy_number",
) -> dict[str, object]:
    row: dict[str, object] = {
        "canonical_uuid": str(UUID(int=number)),
        "canonical_id": canonical_id,
        "brand": "Hot Wheels",
        "casting": casting,
        "release_year": 2025,
        "series": "Mainline",
        "color": None,
        "collector_number": "001",
        "series_position": "1/10",
        "rarity_tier": None,
        "edition": None,
        "aliases": [],
        "identifiers": [
            {
                "identifier_type": identifier_type,
                "identifier_value": toy_number,
                "source_id": f"source://{toy_number}",
            }
        ],
        "provenance": [
            {
                "field_name": None,
                "value_snapshot": toy_number,
                "source_name": "test_source",
                "source_reference": f"source://{toy_number}",
                "retrieved_at": "2026-09-30T00:00:00Z",
                "license_note": "test license",
                "confidence_note": "catalog inclusion is not exact authority",
            }
        ],
    }
    if release_key is not None:
        row["release_key"] = release_key
    return row


def _write_catalog(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"catalog_version": "catalog-v2", "products": rows}),
        encoding="utf-8",
    )


def test_loader_exposes_release_key_and_allows_disambiguated_natural_duplicates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "catalog.json"
    _write_catalog(
        path,
        [
            _row(
                1,
                canonical_id="repeated-casting-hyx45",
                release_key="release-2025-hyx45",
                toy_number="HYX45",
            ),
            _row(
                2,
                canonical_id="repeated-casting-hyy10",
                release_key="release-2025-hyy10",
                toy_number="HYY10",
            ),
        ],
    )

    catalog = load_catalog(path)

    assert [product.release_key for product in catalog.products] == [
        "release-2025-hyx45",
        "release-2025-hyy10",
    ]
    assert catalog.by_release_key["release-2025-hyx45"].canonical_id == ("repeated-casting-hyx45")
    assert "release_key" not in catalog.products[0].product.model_dump()


def test_release_key_changes_catalog_checksum(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    row = _row(
        1,
        canonical_id="one",
        release_key="release-2025-hyx45",
        toy_number="HYX45",
    )
    _write_catalog(path, [row])
    first = catalog_checksum(load_catalog(path))
    row["release_key"] = "release-2025-hyx45-revised"
    _write_catalog(path, [row])

    assert catalog_checksum(load_catalog(path)) != first


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda rows: rows[1].__setitem__("release_key", "RELEASE 2025 HYX45"),
            "release_key collision",
        ),
        (
            lambda rows: rows[1]["identifiers"][0].__setitem__("identifier_value", "hyx45"),
            "normalized identifier collision",
        ),
    ],
)
def test_loader_rejects_normalized_release_and_identifier_collisions(
    tmp_path: Path, mutate: object, message: str
) -> None:
    rows = [
        _row(
            1,
            canonical_id="one",
            release_key="release-2025-hyx45",
            toy_number="HYX45",
            casting="One",
        ),
        _row(
            2,
            canonical_id="two",
            release_key="release-2025-hyy10",
            toy_number="HYY10",
            casting="Two",
        ),
    ]
    assert callable(mutate)
    mutate(rows)
    path = tmp_path / "catalog.json"
    _write_catalog(path, rows)

    with pytest.raises(ValueError, match=message):
        load_catalog(path)


@pytest.mark.parametrize(
    ("release_key", "identifier_type", "message"),
    [
        (None, "toy_number", "natural-key collision without release_key"),
        (
            "release-2025-hyy10",
            "catalog_identifier",
            "requires a typed toy_number identifier",
        ),
    ],
)
def test_natural_duplicates_fail_closed_without_application_disambiguators(
    tmp_path: Path,
    release_key: str | None,
    identifier_type: str,
    message: str,
) -> None:
    path = tmp_path / "catalog.json"
    _write_catalog(
        path,
        [
            _row(
                1,
                canonical_id="one",
                release_key="release-2025-hyx45",
                toy_number="HYX45",
            ),
            _row(
                2,
                canonical_id="two",
                release_key=release_key,
                toy_number="HYY10",
                identifier_type=identifier_type,
            ),
        ],
    )

    with pytest.raises(ValueError, match=message):
        load_catalog(path)
