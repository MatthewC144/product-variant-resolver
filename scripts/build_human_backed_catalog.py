#!/usr/bin/env python3
"""Build a deterministic casting catalog with provisional variants from human labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "pvr-human-backed-catalog-v1"
CATALOG_VERSION = "human-backed-catalog-v1"
CATALOG_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "product-variant-resolver:human-backed-catalog")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        raise ValueError("human-labeled dataset must contain a records array")
    return value


def normalize(value: str | None) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def slug(value: str) -> str:
    return normalize(value).replace(" ", "-") or "unknown"


def display_from_normalized(value: str) -> str:
    return " ".join(
        token.upper() if any(char.isdigit() for char in token) else token.title()
        for token in value.split()
    )


def _stable_uuid(kind: str, key: tuple[str, ...]) -> str:
    return str(uuid.uuid5(CATALOG_NAMESPACE, f"{CATALOG_VERSION}:{kind}:{'|'.join(key)}"))


def _unique(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _preferred_label(values: list[str | None]) -> str | None:
    available = [value for value in values if value]
    if not available:
        return None
    counts = Counter(available)
    return sorted(counts, key=lambda value: (-counts[value], value.casefold(), value))[0]


def build_catalog(human_dataset_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source = _load(human_dataset_path)
    records = source["records"]
    casting_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        brand_key = normalize(record.get("human_label_brand"))
        casting_key = normalize(record.get("human_label_casting"))
        if not brand_key or not casting_key:
            raise ValueError(f"{record.get('case_id')}: missing brand or casting label")
        if record.get("human_label_confidence") != "confirmed":
            raise ValueError(f"{record.get('case_id')}: label is not confirmed")
        casting_groups[(brand_key, casting_key)].append(record)

    castings: list[dict[str, Any]] = []
    merged_duplicate_count = 0
    for casting_key in sorted(casting_groups):
        casting_records = casting_groups[casting_key]
        brand = display_from_normalized(casting_key[0])
        casting = _preferred_label(
            [record.get("human_label_casting") for record in casting_records]
        )
        assert casting is not None
        casting_uuid = _stable_uuid("casting", casting_key)
        casting_id = f"human-{slug(brand)}-{slug(casting)}"

        variant_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for record in casting_records:
            variant_groups[
                (
                    normalize(record.get("human_label_series")),
                    normalize(record.get("human_label_variant")),
                )
            ].append(record)

        variants: list[dict[str, Any]] = []
        for variant_key in sorted(variant_groups):
            variant_records = variant_groups[variant_key]
            merged_duplicate_count += len(variant_records) - 1
            identity_key = (*casting_key, *variant_key)
            variant_suffix = "-".join(
                part for part in (slug(variant_key[0]), slug(variant_key[1])) if part != "unknown"
            ) or "unclassified"
            variants.append(
                {
                    "provisional_variant_uuid": _stable_uuid("variant", identity_key),
                    "provisional_variant_id": f"{casting_id}-{variant_suffix}",
                    "identity_status": "needs_canonical_review",
                    "series_label": _preferred_label(
                        [record.get("human_label_series") for record in variant_records]
                    ),
                    "variant_label": _preferred_label(
                        [record.get("human_label_variant") for record in variant_records]
                    ),
                    "human_label_names": _unique(
                        [record.get("human_label_name") for record in variant_records]
                    ),
                    "pricing_keywords": _unique(
                        [record.get("human_label_pricing_keyword") for record in variant_records]
                    ),
                    "initial_names": _unique(
                        [record.get("initial_name") for record in variant_records]
                    ),
                    "source_case_ids": sorted(record["case_id"] for record in variant_records),
                    "failure_categories": sorted(
                        {
                            category
                            for record in variant_records
                            for category in record.get("failure_categories", [])
                        }
                    ),
                }
            )

        castings.append(
            {
                "casting_uuid": casting_uuid,
                "casting_id": casting_id,
                "identity_level": "casting",
                "brand": brand,
                "casting": casting,
                "source_case_ids": sorted(record["case_id"] for record in casting_records),
                "provisional_variants": variants,
            }
        )

    variant_count = sum(len(item["provisional_variants"]) for item in castings)
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "status": "human_review_draft",
        "identity_level": "casting_with_provisional_variants",
        "eligible_for": [
            "sparse_candidate_retrieval",
            "dense_candidate_retrieval",
            "human_catalog_review",
        ],
        "excluded_from": [
            "canonical_variant_response",
            "canonical_resolution_accuracy",
            "calibration_training",
            "threshold_selection",
        ],
        "castings": castings,
    }
    manifest = {
        "schema_version": "pvr-human-backed-catalog-manifest-v1",
        "catalog_version": CATALOG_VERSION,
        "source_dataset_file": human_dataset_path.name,
        "source_dataset_sha256": hashlib.sha256(human_dataset_path.read_bytes()).hexdigest(),
        "source_record_count": len(records),
        "casting_count": len(castings),
        "provisional_variant_count": variant_count,
        "provisional_variants_needing_review": variant_count,
        "merged_duplicate_record_count": merged_duplicate_count,
    }
    return catalog, manifest


def write_outputs(
    catalog: dict[str, Any],
    manifest: dict[str, Any],
    *,
    output_path: Path,
    manifest_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_text = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path.write_text(catalog_text, encoding="utf-8")
    manifest["catalog_file"] = output_path.name
    manifest["catalog_sha256"] = hashlib.sha256(catalog_text.encode("utf-8")).hexdigest()
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
        "--output",
        type=Path,
        default=ROOT / "data" / "human_backed_catalog.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "human_backed_catalog_manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog, manifest = build_catalog(args.human_dataset)
    write_outputs(catalog, manifest, output_path=args.output, manifest_path=args.manifest)
    print(
        f"built {manifest['casting_count']} human-backed castings with "
        f"{manifest['provisional_variant_count']} provisional variants from "
        f"{manifest['source_record_count']} reviewed records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
