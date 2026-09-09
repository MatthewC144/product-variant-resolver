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
    human_names = load("human_labeled_names.json")
    human_names_manifest = load("human_labeled_names_manifest.json")
    human_alignment = load("human_labeled_catalog_alignment.json")
    human_alignment_manifest = load("human_labeled_catalog_alignment_manifest.json")
    human_catalog = load("human_backed_catalog.json")
    human_catalog_manifest = load("human_backed_catalog_manifest.json")
    review_registry = load("review_family_registry.json")
    review_registry_manifest = load("review_family_registry_manifest.json")
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

    human_records = human_names.get("records", [])
    human_digest = hashlib.sha256(
        (ROOT / "data" / "human_labeled_names.json").read_bytes()
    ).hexdigest()
    if human_names_manifest.get("dataset_sha256") != human_digest:
        errors.append("human-labeled dataset checksum differs from frozen manifest")
    if human_names_manifest.get("record_count") != len(human_records):
        errors.append("human-labeled manifest record count mismatch")
    if len(human_records) != 101:
        errors.append(f"human-labeled corpus has {len(human_records)} records; expected 101")
    if len({record.get("case_id") for record in human_records}) != len(human_records):
        errors.append("human-labeled corpus has duplicate case IDs")
    for record in human_records:
        case_id = record.get("case_id")
        if not record.get("human_label_name") or not record.get("human_label_casting"):
            errors.append(f"human-labeled record is incomplete: {case_id}")
        if record.get("human_label_confidence") != "confirmed":
            errors.append(f"human-labeled record is not confirmed: {case_id}")
        expected_status = "candidate" if record.get("initial_name") else "no_candidate"
        if record.get("initial_output_status") != expected_status:
            errors.append(f"human-labeled initial status mismatch: {case_id}")

    alignment_records = human_alignment.get("alignments", [])
    alignment_digest = hashlib.sha256(
        (ROOT / "data" / "human_labeled_catalog_alignment.json").read_bytes()
    ).hexdigest()
    if human_alignment_manifest.get("alignment_sha256") != alignment_digest:
        errors.append("human catalog alignment checksum differs from frozen manifest")
    if human_alignment_manifest.get("human_dataset_sha256") != human_digest:
        errors.append("human catalog alignment references a different human dataset")
    if human_alignment_manifest.get("catalog_sha256") != catalog_digest:
        errors.append("human catalog alignment references a different catalog")
    if len(alignment_records) != len(human_records):
        errors.append("human catalog alignment count differs from human corpus")
    alignment_ids = {record.get("case_id") for record in alignment_records}
    human_ids = {record.get("case_id") for record in human_records}
    if alignment_ids != human_ids:
        errors.append("human catalog alignment case IDs differ from human corpus")
    catalog_by_uuid = {product.get("canonical_uuid"): product for product in products}
    for alignment in alignment_records:
        status = alignment.get("status")
        canonical_uuid = alignment.get("canonical_uuid")
        canonical_id = alignment.get("canonical_id")
        if status == "mapped":
            product = catalog_by_uuid.get(canonical_uuid)
            if product is None or product.get("canonical_id") != canonical_id:
                errors.append(f"invalid mapped catalog identity: {alignment.get('case_id')}")
        elif status in {"casting_family_only", "unmapped"}:
            if canonical_uuid is not None or canonical_id is not None:
                errors.append(f"non-mapped alignment asserts identity: {alignment.get('case_id')}")
        else:
            errors.append(f"invalid alignment status: {alignment.get('case_id')}")

    human_catalog_path = ROOT / "data" / "human_backed_catalog.json"
    human_catalog_digest = hashlib.sha256(human_catalog_path.read_bytes()).hexdigest()
    if human_catalog_manifest.get("catalog_sha256") != human_catalog_digest:
        errors.append("human-backed catalog checksum differs from frozen manifest")
    if human_catalog_manifest.get("source_dataset_sha256") != human_digest:
        errors.append("human-backed catalog references a different human dataset")
    human_castings = human_catalog.get("castings", [])
    human_variants = [
        variant
        for casting in human_castings
        for variant in casting.get("provisional_variants", [])
    ]
    if human_catalog_manifest.get("casting_count") != len(human_castings):
        errors.append("human-backed catalog casting count mismatch")
    if human_catalog_manifest.get("provisional_variant_count") != len(human_variants):
        errors.append("human-backed catalog variant count mismatch")
    if len({casting.get("casting_uuid") for casting in human_castings}) != len(human_castings):
        errors.append("human-backed catalog has duplicate casting UUIDs")
    if len({casting.get("casting_id") for casting in human_castings}) != len(human_castings):
        errors.append("human-backed catalog has duplicate casting IDs")
    if len({variant.get("provisional_variant_uuid") for variant in human_variants}) != len(
        human_variants
    ):
        errors.append("human-backed catalog has duplicate provisional variant UUIDs")
    catalog_source_ids = [
        case_id for variant in human_variants for case_id in variant.get("source_case_ids", [])
    ]
    if len(catalog_source_ids) != len(human_records) or set(catalog_source_ids) != human_ids:
        errors.append("human-backed catalog source coverage differs from human corpus")
    for variant in human_variants:
        if variant.get("identity_status") != "needs_canonical_review":
            errors.append(
                f"human-backed variant bypasses canonical review: "
                f"{variant.get('provisional_variant_id')}"
            )

    review_registry_path = ROOT / "data" / "review_family_registry.json"
    review_registry_digest = hashlib.sha256(review_registry_path.read_bytes()).hexdigest()
    if review_registry_manifest.get("registry_sha256") != review_registry_digest:
        errors.append("review-family registry checksum differs from frozen manifest")
    if review_registry.get("schema_version") != "pvr-review-family-registry-v1":
        errors.append("review-family registry has an unsupported schema")
    if review_registry.get("status") != "review_family_only":
        errors.append("review-family registry has an unsupported status")
    new_families = review_registry.get("new_families", [])
    merge_links = review_registry.get("merge_links", [])
    hold_exclusions = review_registry.get("hold_exclusions", [])
    expected_registry_counts = {
        "new_family_count": len(new_families),
        "merge_link_count": len(merge_links),
        "hold_exclusion_count": len(hold_exclusions),
    }
    if expected_registry_counts != {
        "new_family_count": 42,
        "merge_link_count": 4,
        "hold_exclusion_count": 7,
    }:
        errors.append(f"review-family registry count mismatch: {expected_registry_counts}")
    for field, value in expected_registry_counts.items():
        if review_registry_manifest.get(field) != value:
            errors.append(f"review-family manifest {field} mismatch")
    for field in (
        "provisional_variant_count",
        "canonical_promotion_count",
        "runtime_indexed_family_count",
        "postgresql_row_count",
    ):
        if review_registry_manifest.get(field) != 0:
            errors.append(f"review-family manifest {field} must remain zero")

    review_ids: set[str] = set()
    review_uuids: set[str] = set()
    for family in new_families:
        family_id = family.get("review_family_id")
        family_uuid = family.get("review_family_uuid")
        if family_id in review_ids:
            errors.append(f"duplicate review-family ID: {family_id}")
        review_ids.add(family_id)
        try:
            uuid.UUID(family_uuid)
        except (AttributeError, TypeError, ValueError):
            errors.append(f"invalid review-family UUID: {family_uuid}")
        if family_uuid in review_uuids:
            errors.append(f"duplicate review-family UUID: {family_uuid}")
        review_uuids.add(family_uuid)
        if family.get("aliases") != [family.get("display_name")]:
            errors.append(f"review-family aliases exceed approved display name: {family_id}")
        if family.get("identity_status") != "family_accepted_variants_unreviewed":
            errors.append(f"review-family has invalid identity status: {family_id}")

    human_by_id = {casting.get("casting_id"): casting for casting in human_castings}
    for link in merge_links:
        target = human_by_id.get(link.get("target_casting_id"))
        if target is None or target.get("casting_uuid") != link.get("target_casting_uuid"):
            errors.append(
                f"review-family merge has invalid target: {link.get('source_family_review_id')}"
            )
        if "review_family_uuid" in link:
            errors.append("review-family merge minted a duplicate family UUID")
    for hold in hold_exclusions:
        if hold.get("retrieval_eligible") is not False:
            errors.append(f"held family became retrieval eligible: {hold.get('review_family_id')}")
        if hold.get("identity_status") != "held_not_materialized":
            errors.append(f"held family has invalid status: {hold.get('review_family_id')}")

    review_release_references = [
        reference
        for section in (new_families, merge_links, hold_exclusions)
        for family in section
        for reference in family.get("held_release_references", [])
    ]
    review_source_ids = [
        reference.get("source_record_id") for reference in review_release_references
    ]
    if len(review_release_references) != 100 or len(set(review_source_ids)) != 100:
        errors.append("review-family registry does not cover 100 unique release references")
    if not all(
        reference.get("review_status") == "held_for_variant_review"
        for reference in review_release_references
    ):
        errors.append("review-family registry contains a release that bypasses variant review")
    if review_registry_manifest.get("held_release_reference_count") != len(
        review_release_references
    ):
        errors.append("review-family manifest held release count mismatch")
    if review_registry.get("source", {}).get("revision_id") != 790665:
        errors.append("review-family registry source revision mismatch")
    if review_registry.get("source", {}).get("license") != "CC-BY-SA":
        errors.append("review-family registry source license mismatch")
    serialized_registry = json.dumps(review_registry, ensure_ascii=False)
    if '"provisional_variants"' in serialized_registry:
        errors.append("review-family registry fabricated provisional variants")
    if '"canonical_uuid"' in serialized_registry:
        errors.append("review-family registry asserts canonical identity")

    return errors


def manifest_checksum() -> str:
    digest = hashlib.sha256()
    for name in (
        "catalog.json",
        "benchmark.json",
        "manifest.json",
        "human_labeled_names.json",
        "human_labeled_names_manifest.json",
        "human_labeled_catalog_alignment.json",
        "human_labeled_catalog_alignment_manifest.json",
        "human_backed_catalog.json",
        "human_backed_catalog_manifest.json",
        "review_family_registry.json",
        "review_family_registry_manifest.json",
    ):
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
