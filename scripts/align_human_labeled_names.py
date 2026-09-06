#!/usr/bin/env python3
"""Conservatively align reviewed names to the repository fixture catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "pvr-human-catalog-alignment-v1"
ALIGNMENT_VERSION = "human-labeled-real-noisy-to-fixture-v1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return value


def normalize(value: str | None) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _variant_matches(record: dict[str, Any], product: dict[str, Any]) -> bool:
    """Require both series and one variant discriminator for an automatic UUID link."""
    human_series = normalize(record.get("human_label_series"))
    human_variant = normalize(record.get("human_label_variant"))
    if not human_series or not human_variant:
        return False
    if human_series != normalize(product.get("series")):
        return False
    product_discriminators = {
        normalize(product.get("color")),
        normalize(product.get("edition")),
        normalize(product.get("rarity_tier")),
    }
    product_discriminators.discard("")
    return human_variant in product_discriminators


def build_alignment(
    human_dataset_path: Path,
    catalog_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    human_dataset = _load(human_dataset_path)
    catalog = _load(catalog_path)
    records = human_dataset.get("records")
    products = catalog.get("products")
    if not isinstance(records, list) or not isinstance(products, list):
        raise ValueError("dataset and catalog must contain record arrays")

    families: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for product in products:
        families[(normalize(product.get("brand")), normalize(product.get("casting")))].append(
            product
        )

    alignments: list[dict[str, Any]] = []
    for record in records:
        key = (
            normalize(record.get("human_label_brand")),
            normalize(record.get("human_label_casting")),
        )
        family_candidates = families.get(key, [])
        variant_candidates = [
            product for product in family_candidates if _variant_matches(record, product)
        ]

        if len(variant_candidates) == 1:
            product = variant_candidates[0]
            status = "mapped"
            reason = "unique_exact_brand_casting_series_and_variant"
            canonical_uuid = product["canonical_uuid"]
            canonical_id = product["canonical_id"]
        elif family_candidates:
            status = "casting_family_only"
            reason = "exact_brand_and_casting_but_no_unique_variant"
            canonical_uuid = None
            canonical_id = None
        else:
            status = "unmapped"
            reason = "no_exact_brand_and_casting_family"
            canonical_uuid = None
            canonical_id = None

        alignments.append(
            {
                "case_id": record["case_id"],
                "status": status,
                "reason": reason,
                "human_label_name": record["human_label_name"],
                "human_label_brand": record["human_label_brand"],
                "human_label_casting": record["human_label_casting"],
                "human_label_series": record["human_label_series"],
                "human_label_variant": record["human_label_variant"],
                "matched_casting_family": (
                    family_candidates[0]["casting"] if family_candidates else None
                ),
                "canonical_uuid": canonical_uuid,
                "canonical_id": canonical_id,
                "candidate_canonical_ids": [
                    product["canonical_id"] for product in family_candidates
                ],
            }
        )

    counts = Counter(item["status"] for item in alignments)
    alignment = {
        "schema_version": SCHEMA_VERSION,
        "alignment_version": ALIGNMENT_VERSION,
        "policy": {
            "family_alignment": "exact normalized brand and casting only",
            "canonical_variant_alignment": (
                "unique candidate after exact brand, casting, series, and one exact variant "
                "discriminator (color, edition, or rarity tier)"
            ),
            "fuzzy_matching": False,
        },
        "alignments": alignments,
    }
    manifest = {
        "schema_version": "pvr-human-catalog-alignment-manifest-v1",
        "alignment_version": ALIGNMENT_VERSION,
        "human_dataset_file": human_dataset_path.name,
        "human_dataset_sha256": hashlib.sha256(human_dataset_path.read_bytes()).hexdigest(),
        "catalog_file": catalog_path.name,
        "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "alignment_count": len(alignments),
        "status_counts": {
            "mapped": counts["mapped"],
            "casting_family_only": counts["casting_family_only"],
            "unmapped": counts["unmapped"],
        },
    }
    return alignment, manifest


def write_outputs(
    alignment: dict[str, Any],
    manifest: dict[str, Any],
    *,
    output_path: Path,
    manifest_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    alignment_text = json.dumps(alignment, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path.write_text(alignment_text, encoding="utf-8")
    manifest["alignment_file"] = output_path.name
    manifest["alignment_sha256"] = hashlib.sha256(
        alignment_text.encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--human-dataset",
        type=Path,
        default=ROOT / "data" / "human_labeled_names.json",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=ROOT / "data" / "catalog.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "human_labeled_catalog_alignment.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "human_labeled_catalog_alignment_manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    alignment, manifest = build_alignment(args.human_dataset, args.catalog)
    write_outputs(alignment, manifest, output_path=args.output, manifest_path=args.manifest)
    counts = manifest["status_counts"]
    print(
        f"aligned {manifest['alignment_count']} records: {counts['mapped']} mapped, "
        f"{counts['casting_family_only']} casting-family-only, {counts['unmapped']} unmapped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
