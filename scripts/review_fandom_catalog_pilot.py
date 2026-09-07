#!/usr/bin/env python3
"""Build or verify a conservative cross-catalog review of the Fandom pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCHEMA_VERSION = "pvr-fandom-catalog-review-v1"
REVIEW_VERSION = "fandom-2025-pilot-cross-catalog-review-v1"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def normalize(value: str | None) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _status_and_action(
    canonical_candidates: list[dict[str, Any]],
    human_candidates: list[dict[str, Any]],
) -> tuple[str, str, str]:
    if canonical_candidates and human_candidates:
        return (
            "exact_both_casting_families",
            "exact normalized brand and casting exist in both review sources",
            "review_existing_cross_source_family",
        )
    if canonical_candidates:
        return (
            "exact_canonical_casting_family",
            "exact normalized brand and casting exist in the canonical fixture",
            "review_existing_canonical_family",
        )
    if human_candidates:
        return (
            "exact_human_casting_family",
            "exact normalized brand and casting exist in the human-backed draft",
            "review_existing_human_family",
        )
    return (
        "no_exact_casting_family",
        "no exact normalized brand and casting exist in either reviewed catalog",
        "review_possible_new_casting_family",
    )


def build_review(
    staging_path: Path,
    canonical_catalog_path: Path,
    human_catalog_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    staging = _load(staging_path)
    canonical_catalog = _load(canonical_catalog_path)
    human_catalog = _load(human_catalog_path)
    records = staging.get("records")
    products = canonical_catalog.get("products")
    human_castings = human_catalog.get("castings")
    if not isinstance(records, list):
        raise ValueError("staging input must contain records[]")
    if not isinstance(products, list):
        raise ValueError("canonical catalog must contain products[]")
    if not isinstance(human_castings, list):
        raise ValueError("human-backed catalog must contain castings[]")

    canonical_families: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for product in products:
        key = (normalize(product.get("brand")), normalize(product.get("casting")))
        canonical_families.setdefault(key, []).append(product)

    human_families: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for casting in human_castings:
        key = (normalize(casting.get("brand")), normalize(casting.get("casting")))
        human_families.setdefault(key, []).append(casting)

    reviews: list[dict[str, Any]] = []
    for record in records:
        if record.get("canonical_uuid") is not None:
            raise ValueError("staging record already asserts a canonical UUID")
        if record.get("review_status") != "needs_canonical_review":
            raise ValueError("staging record bypasses the review boundary")
        key = (normalize(record.get("brand")), normalize(record.get("casting_name")))
        if not all(key):
            raise ValueError("staging record has no normalized brand/casting key")
        canonical_candidates = sorted(
            canonical_families.get(key, []), key=lambda item: item["canonical_id"]
        )
        human_candidates = sorted(
            human_families.get(key, []), key=lambda item: item["casting_id"]
        )
        status, reason, action = _status_and_action(
            canonical_candidates, human_candidates
        )
        human_variant_ids = sorted(
            variant["provisional_variant_id"]
            for casting in human_candidates
            for variant in casting["provisional_variants"]
        )
        reviews.append(
            {
                "source_record_id": record["source_record_id"],
                "source_row": record["source_row"],
                "brand": record["brand"],
                "casting_name": record["casting_name"],
                "release_year": record["release_year"],
                "toy_number": record["toy_number"],
                "collector_number": record["collector_number"],
                "series": record["series"],
                "variant_note": record["variant_note"],
                "normalized_family_key": {
                    "brand": key[0],
                    "casting": key[1],
                },
                "match_status": status,
                "match_reason": reason,
                "canonical_family_candidate_ids": [
                    item["canonical_id"] for item in canonical_candidates
                ],
                "human_casting_candidate_ids": [
                    item["casting_id"] for item in human_candidates
                ],
                "human_variant_candidate_ids": human_variant_ids,
                "recommended_action": action,
                "promotion_decision": "hold_for_human_review",
                "promotion_eligible": False,
                "canonical_uuid": None,
                "canonical_id": None,
                "review_requirements": [
                    "confirm_casting_identity",
                    "classify_release_or_variant",
                    "resolve_color_without_image_inference",
                ],
            }
        )

    row_counts = Counter(item["match_status"] for item in reviews)
    family_statuses: dict[tuple[str, str], str] = {}
    for item in reviews:
        key = (
            item["normalized_family_key"]["brand"],
            item["normalized_family_key"]["casting"],
        )
        family_statuses[key] = item["match_status"]
    family_counts = Counter(family_statuses.values())
    review = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "review_version": REVIEW_VERSION,
        "status": "human_review_required",
        "policy": {
            "family_match": "exact normalized brand and casting only",
            "normalization": "NFKD ASCII, casefold, alphanumeric tokens",
            "fuzzy_matching": False,
            "identifier_only_matching": False,
            "automatic_promotion": False,
            "meaning_of_match": "candidate casting-family relationship only",
        },
        "source_dataset_version": staging.get("dataset_version"),
        "reviews": reviews,
    }
    manifest = {
        "schema_version": "pvr-fandom-catalog-review-manifest-v1",
        "review_version": REVIEW_VERSION,
        "inputs": {
            "staging": {
                "file": staging_path.name,
                "sha256": hashlib.sha256(staging_path.read_bytes()).hexdigest(),
            },
            "canonical_catalog": {
                "file": canonical_catalog_path.name,
                "sha256": hashlib.sha256(
                    canonical_catalog_path.read_bytes()
                ).hexdigest(),
            },
            "human_catalog": {
                "file": human_catalog_path.name,
                "sha256": hashlib.sha256(human_catalog_path.read_bytes()).hexdigest(),
            },
        },
        "review_row_count": len(reviews),
        "unique_staging_casting_family_count": len(family_statuses),
        "row_match_status_counts": dict(sorted(row_counts.items())),
        "family_match_status_counts": dict(sorted(family_counts.items())),
        "promotion_decision_counts": {"hold_for_human_review": len(reviews)},
        "canonical_promotion_count": 0,
    }
    return review, manifest


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def expected_outputs(
    review: dict[str, Any],
    manifest: dict[str, Any],
    *,
    review_file_name: str = "review.json",
) -> tuple[str, str]:
    review_text = _stable_json(review)
    frozen_manifest = dict(manifest)
    frozen_manifest["review_file"] = review_file_name
    frozen_manifest["review_sha256"] = hashlib.sha256(
        review_text.encode("utf-8")
    ).hexdigest()
    return review_text, _stable_json(frozen_manifest)


def parse_args() -> argparse.Namespace:
    directory = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
    parser = argparse.ArgumentParser(
        description="Build or verify the review-only cross-catalog Fandom report"
    )
    parser.add_argument("--staging", type=Path, default=directory / "normalized.json")
    parser.add_argument("--canonical", type=Path, default=ROOT / "data" / "catalog.json")
    parser.add_argument(
        "--human", type=Path, default=ROOT / "data" / "human_backed_catalog.json"
    )
    parser.add_argument("--output", type=Path, default=directory / "review.json")
    parser.add_argument("--manifest", type=Path, default=directory / "review-manifest.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare checked-in outputs with a fresh in-memory build without writing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review, manifest = build_review(args.staging, args.canonical, args.human)
    review_text, manifest_text = expected_outputs(
        review, manifest, review_file_name=args.output.name
    )
    if args.check:
        if args.output.read_text(encoding="utf-8") != review_text:
            raise ValueError("review.json differs from a fresh deterministic build")
        if args.manifest.read_text(encoding="utf-8") != manifest_text:
            raise ValueError("review-manifest.json differs from a fresh deterministic build")
        status = "verified"
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(review_text, encoding="utf-8")
        args.manifest.write_text(manifest_text, encoding="utf-8")
        status = "built"
    print(
        f"{status} {manifest['review_row_count']} rows across "
        f"{manifest['unique_staging_casting_family_count']} casting families; "
        f"canonical promotions={manifest['canonical_promotion_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
