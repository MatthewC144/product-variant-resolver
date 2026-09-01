#!/usr/bin/env python3
"""Generate the frozen synthetic fixture catalog and grouped benchmark.

The generated records are intentionally synthetic and are suitable only for
testing the resolver architecture. Running this script twice produces the same
bytes (including UUIDs and checksums once written by the validator).
"""

from __future__ import annotations

import json
import hashlib
import re
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
NAMESPACE = uuid.UUID("2f49c7c2-6f48-5df2-b86f-19977788bb2c")
DATASET_VERSION = "fixture-v1"

FAMILIES = (
    ("Chevy Nomad", "Nomad"),
    ("Twin Mill", "Twinmill"),
    ("Bone Shaker", "Boneshaker"),
    ("Custom Camaro", "Camaro"),
    ("Volkswagen Beetle", "VW Beetle"),
    ("Ford Mustang GT", "Mustang"),
    ("Porsche 911 GT3", "911 GT3"),
    ("Nissan Skyline GT-R", "Skyline GTR"),
    ("Dodge Charger", "Charger"),
    ("Toyota Supra", "Supra"),
)
YEARS = (2022, 2023, 2024)
COLORS = ("Red", "Blue", "Black", "Silver")
SERIES = ("Mainline", "HW Dream Garage", "Then and Now")
SPLIT_BY_FAMILY = {
    **{name: "train" for name, _ in FAMILIES[:6]},
    **{name: "dev" for name, _ in FAMILIES[6:8]},
    **{name: "test" for name, _ in FAMILIES[8:]},
    "Mazda RX-7": "train",
    "Lamborghini Miura": "train",
    "Honda S2000": "dev",
    "McLaren F1": "test",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def canonical_identity(casting: str, year: int, series: str, color: str, number: str) -> tuple[str, str]:
    canonical_id = "-".join(
        ("hot-wheels", slugify(casting), str(year), slugify(series), slugify(color), number)
    )
    return str(uuid.uuid5(NAMESPACE, canonical_id)), canonical_id


def build_catalog() -> dict[str, object]:
    products: list[dict[str, object]] = []
    number = 101
    for family_index, (casting, short_alias) in enumerate(FAMILIES):
        for year_index, year in enumerate(YEARS):
            series = SERIES[(family_index + year_index) % len(SERIES)]
            for color_index, color in enumerate(COLORS):
                collector_number = str(number)
                canonical_uuid, canonical_id = canonical_identity(
                    casting, year, series, color, collector_number
                )
                source_reference = f"synthetic://fixture-v1/{canonical_id}"
                products.append(
                    {
                        "canonical_uuid": canonical_uuid,
                        "canonical_id": canonical_id,
                        "brand": "Hot Wheels",
                        "casting": casting,
                        "release_year": year,
                        "series": series,
                        "color": color,
                        "collector_number": collector_number,
                        "series_position": f"{color_index + 1}/10",
                        "rarity_tier": "mainline",
                        "edition": None,
                        "near_duplicate_group": f"{slugify(casting)}-{year}",
                        "aliases": [
                            {
                                "alias_text": short_alias,
                                "alias_type": "casting_alias",
                                "source_id": source_reference,
                            },
                            {
                                "alias_text": f"{year} {short_alias} {color} #{collector_number}",
                                "alias_type": "listing_form",
                                "source_id": source_reference,
                            },
                        ],
                        "identifiers": [
                            {
                                "identifier_type": "collector_number",
                                "identifier_value": collector_number,
                                "source_id": source_reference,
                            }
                        ],
                        "provenance": [
                            {
                                "field_name": None,
                                "value_snapshot": canonical_id,
                                "source_name": "synthetic_fixture",
                                "source_reference": source_reference,
                                "retrieved_at": "2026-09-01T00:00:00Z",
                                "license_note": "CC0 synthetic test data generated for this repository",
                                "confidence_note": "Not a claim about a real-world release",
                            }
                        ],
                    }
                )
                number += 1
    return {
        "dataset_version": DATASET_VERSION,
        "catalog_version": DATASET_VERSION,
        "source_note": (
            "Deterministic synthetic records for architecture and test validation only; "
            "not an authoritative Hot Wheels catalog."
        ),
        "products": products,
    }


def build_benchmark(catalog: dict[str, object]) -> dict[str, object]:
    products = catalog["products"]
    assert isinstance(products, list)
    by_family: dict[str, list[dict[str, object]]] = {}
    for product in products:
        assert isinstance(product, dict)
        by_family.setdefault(str(product["casting"]), []).append(product)

    cases: list[dict[str, object]] = []
    case_number = 1

    def add_case(
        query: str,
        status: str,
        family: str,
        category: str,
        product: dict[str, object] | None = None,
        hard_negative: bool = False,
    ) -> None:
        nonlocal case_number
        cases.append(
            {
                "case_id": f"case-{case_number:03d}",
                "query": query,
                "expected_status": status,
                "expected_canonical_uuid": product["canonical_uuid"] if product else None,
                "expected_canonical_id": product["canonical_id"] if product else None,
                "failure_category": category,
                "casting_family": family,
                "split": SPLIT_BY_FAMILY[family],
                "source_type": "synthetic_fixture",
                "label_notes": "Deterministic synthetic architecture benchmark",
                "dataset_version": DATASET_VERSION,
                "hard_negative": hard_negative,
            }
        )
        case_number += 1

    # Six exact-but-noisy matches per catalog family: 60 total.
    templates = (
        "HOT WHEELS {year} {casting} {color} #{number} NEW IN BOX",
        "hw {casting} / {series} / {color} / {number}",
        "{year} {alias} diecast color {color} collector no {number}",
        "LOT OF 3 -- {casting} {color} {year} #{number}",
        "Hot-Wheels::{casting}::{series}::{color}::{number}",
        "{casting} {year} {color} {position} carded #{number}",
    )
    for family, family_products in by_family.items():
        for index, template in enumerate(templates):
            product = family_products[index]
            alias = product["aliases"][0]["alias_text"]
            add_case(
                template.format(
                    year=product["release_year"],
                    casting=family,
                    alias=alias,
                    series=product["series"],
                    color=product["color"],
                    number=product["collector_number"],
                    position=product["series_position"],
                ),
                "matched",
                family,
                ("identifier_noise" if index % 2 == 0 else "marketplace_noise"),
                product,
                hard_negative=index in (1, 5),
            )

        # Two titles omit the distinguishing color/collector number: 20 ambiguous total.
        first = family_products[0]
        second = family_products[1]
        add_case(
            f"Hot Wheels {first['release_year']} {family} {first['series']} carded",
            "ambiguous",
            family,
            "missing_variant_attribute",
            hard_negative=True,
        )
        add_case(
            f"{family} {second['release_year']} diecast choose color",
            "ambiguous",
            family,
            "near_duplicate_variants",
            hard_negative=True,
        )

    # Four entities absent from the catalog, each with five noisy variants: 20 total.
    unknowns = (
        ("Mazda RX-7", 2024, "Green"),
        ("Lamborghini Miura", 2021, "Yellow"),
        ("Honda S2000", 2025, "White"),
        ("McLaren F1", 2020, "Orange"),
    )
    unknown_templates = (
        "Hot Wheels {year} {family} {color} #999 sealed",
        "HW {family} premium {color}",
        "rare {family} {year} die cast toy",
        "lot of 2 {color} {family} carded",
        "{family} unknown edition collector 999",
    )
    for family, year, color in unknowns:
        for template in unknown_templates:
            add_case(
                template.format(year=year, family=family, color=color),
                "no_match",
                family,
                "entity_absent_from_catalog",
                hard_negative=True,
            )

    return {
        "dataset_version": DATASET_VERSION,
        "split_seed": 240901,
        "split_strategy": "fixed mapping by casting_family; a family occurs in exactly one split",
        "source_note": "Synthetic noisy titles; test labels must not be used for fitting or threshold selection.",
        "cases": cases,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    benchmark = build_benchmark(catalog)
    catalog_path = DATA_DIR / "catalog.json"
    benchmark_path = DATA_DIR / "benchmark.json"
    write_json(catalog_path, catalog)
    write_json(benchmark_path, benchmark)
    split_counts: dict[str, int] = {}
    for case in benchmark["cases"]:
        split = str(case["split"])
        split_counts[split] = split_counts.get(split, 0) + 1
    write_json(
        DATA_DIR / "manifest.json",
        {
            "dataset_version": DATASET_VERSION,
            "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
            "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
            "product_count": len(catalog["products"]),
            "benchmark_case_count": len(benchmark["cases"]),
            "benchmark_split_counts": split_counts,
            "generator": "scripts/generate_fixture_data.py",
        },
    )
    print(f"wrote {len(catalog['products'])} products and {len(benchmark['cases'])} benchmark cases")


if __name__ == "__main__":
    main()
