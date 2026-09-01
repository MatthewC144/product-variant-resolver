#!/usr/bin/env python3
"""Validate fixture integrity and print a stable manifest checksum."""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    catalog = load("catalog.json")
    benchmark = load("benchmark.json")
    manifest = load("manifest.json")
    products = catalog.get("products", [])
    cases = benchmark.get("cases", [])
    if len(products) < 120:
        errors.append(f"catalog has {len(products)} products; expected >=120")

    ids: set[str] = set()
    uuids: set[str] = set()
    groups: set[str] = set()
    families: set[str] = set()
    for product in products:
        try:
            uuid.UUID(product["canonical_uuid"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"invalid UUID in {product!r}")
            continue
        canonical_id = product.get("canonical_id")
        canonical_uuid = product.get("canonical_uuid")
        if canonical_id in ids:
            errors.append(f"duplicate canonical_id: {canonical_id}")
        if canonical_uuid in uuids:
            errors.append(f"duplicate canonical_uuid: {canonical_uuid}")
        ids.add(canonical_id)
        uuids.add(canonical_uuid)
        families.add(product.get("casting"))
        groups.add(product.get("near_duplicate_group"))
        if not product.get("provenance"):
            errors.append(f"missing provenance: {canonical_id}")

    if len(families) < 8:
        errors.append(f"catalog has {len(families)} families; expected >=8")
    if len(groups) < 20:
        errors.append(f"catalog has {len(groups)} near-duplicate groups; expected >=20")

    counts = Counter(case.get("expected_status") for case in cases)
    minima = {"matched": 50, "ambiguous": 20, "no_match": 20}
    for status, minimum in minima.items():
        if counts[status] < minimum:
            errors.append(f"benchmark has {counts[status]} {status}; expected >={minimum}")
    if len(cases) < 90:
        errors.append(f"benchmark has {len(cases)} cases; expected >=90")

    family_splits: dict[str, set[str]] = defaultdict(set)
    for case in cases:
        family_splits[case.get("casting_family")].add(case.get("split"))
        if case.get("dataset_version") != benchmark.get("dataset_version"):
            errors.append(f"dataset version mismatch: {case.get('case_id')}")
        if case.get("expected_status") == "matched":
            if case.get("expected_canonical_uuid") not in uuids:
                errors.append(f"unknown expected UUID: {case.get('case_id')}")
            if case.get("expected_canonical_id") not in ids:
                errors.append(f"unknown expected ID: {case.get('case_id')}")
        elif case.get("expected_canonical_uuid") is not None or case.get("expected_canonical_id") is not None:
            errors.append(f"abstention has asserted identity: {case.get('case_id')}")
    overlaps = {family: splits for family, splits in family_splits.items() if len(splits) != 1}
    if overlaps:
        errors.append(f"casting families cross splits: {overlaps}")

    catalog_digest = hashlib.sha256((ROOT / "data" / "catalog.json").read_bytes()).hexdigest()
    benchmark_digest = hashlib.sha256((ROOT / "data" / "benchmark.json").read_bytes()).hexdigest()
    if manifest.get("catalog_sha256") != catalog_digest:
        errors.append("catalog checksum differs from frozen manifest")
    if manifest.get("benchmark_sha256") != benchmark_digest:
        errors.append("benchmark checksum differs from frozen manifest")
    if manifest.get("product_count") != len(products):
        errors.append("manifest product count mismatch")
    if manifest.get("benchmark_case_count") != len(cases):
        errors.append("manifest benchmark count mismatch")

    return errors


def manifest_checksum() -> str:
    digest = hashlib.sha256()
    for name in ("catalog.json", "benchmark.json", "manifest.json"):
        digest.update((ROOT / "data" / name).read_bytes())
    return digest.hexdigest()


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"fixture manifest sha256={manifest_checksum()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
