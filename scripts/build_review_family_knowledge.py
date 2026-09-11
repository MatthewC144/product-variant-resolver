#!/usr/bin/env python3
"""Build the debug-only runtime projection for accepted review families."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "pvr-review-family-knowledge-v1"
KNOWLEDGE_VERSION = "review-family-knowledge-fandom-2025-r790665-v1"
MANIFEST_SCHEMA_VERSION = "pvr-review-family-knowledge-manifest-v1"
REGISTRY_SCHEMA_VERSION = "pvr-review-family-registry-v1"
REGISTRY_VERSION = "fandom-2025-review-families-r790665-v1"
REGISTRY_MANIFEST_SCHEMA_VERSION = "pvr-review-family-registry-manifest-v1"
IDENTITY_NAMESPACE = "product-variant-resolver:review-family:fandom-hot-wheels-wiki"

REGISTRY_ELIGIBLE_FOR = ["family_review", "future_human_knowledge_index"]
REGISTRY_EXCLUDED_FROM = [
    "runtime_retrieval",
    "canonical_variant_response",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "postgresql_ingestion",
]
PROJECTION_ELIGIBLE_FOR = ["human_knowledge_debug_retrieval"]
PROJECTION_EXCLUDED_FROM = [
    "canonical_variant_response",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "evaluation_ground_truth",
    "variant_identity",
    "postgresql_ingestion",
]
SEARCHABLE_FIELDS = ["brand", "casting", "aliases"]
DOCUMENT_FIELDS = [
    "knowledge_type",
    "review_family_id",
    "review_family_uuid",
    "identity_level",
    "identity_status",
    "brand",
    "casting",
    "aliases",
    "source_record_ids",
]
EXPECTED_COUNTS = {
    "new_family_count": 42,
    "merge_link_count": 4,
    "hold_exclusion_count": 7,
    "new_family_source_row_count": 79,
    "merge_source_row_count": 9,
    "hold_source_row_count": 12,
    "held_release_reference_count": 100,
}


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name}: could not read valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _required_string(value: Any, *, field: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {field} must be a non-empty string")
    return value


def _string_list(value: Any, *, field: str, context: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError(f"{context}: {field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{context}: {field} contains duplicates")
    return list(value)


def _normalize(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _validate_registry_manifest(
    *,
    registry_path: Path,
    registry: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ValueError("review-family registry has an unsupported schema")
    if registry.get("registry_version") != REGISTRY_VERSION:
        raise ValueError("review-family registry has an unsupported version")
    if registry.get("status") != "review_family_only":
        raise ValueError("review-family registry has an unsupported status")
    if registry.get("identity_namespace") != IDENTITY_NAMESPACE:
        raise ValueError("review-family registry identity namespace differs from contract")
    if registry.get("eligible_for") != REGISTRY_ELIGIBLE_FOR:
        raise ValueError("review-family registry eligibility boundary was widened or changed")
    if registry.get("excluded_from") != REGISTRY_EXCLUDED_FROM:
        raise ValueError("review-family registry exclusion boundary was widened or changed")

    if manifest.get("schema_version") != REGISTRY_MANIFEST_SCHEMA_VERSION:
        raise ValueError("review-family registry manifest has an unsupported schema")
    if manifest.get("registry_version") != REGISTRY_VERSION:
        raise ValueError("review-family registry manifest has an unsupported version")
    if manifest.get("registry_file") != registry_path.name:
        raise ValueError("review-family registry filename differs from its manifest")
    if manifest.get("registry_sha256") != _sha256(registry_path):
        raise ValueError("review-family registry checksum differs from its manifest")
    if manifest.get("identity_namespace") != IDENTITY_NAMESPACE:
        raise ValueError("review-family manifest identity namespace differs from contract")
    if not manifest_path.is_file():
        raise ValueError("review-family registry manifest is missing")
    for field, expected in EXPECTED_COUNTS.items():
        if manifest.get(field) != expected:
            raise ValueError(f"review-family registry manifest {field} differs from contract")
    for field in (
        "provisional_variant_count",
        "canonical_promotion_count",
        "runtime_indexed_family_count",
        "postgresql_row_count",
    ):
        if manifest.get(field) != 0:
            raise ValueError(f"review-family registry manifest unexpectedly widens {field}")


def _registry_counts(registry: dict[str, Any]) -> dict[str, int]:
    sections = {
        "new_families": registry.get("new_families"),
        "merge_links": registry.get("merge_links"),
        "hold_exclusions": registry.get("hold_exclusions"),
    }
    expected_lengths = {"new_families": 42, "merge_links": 4, "hold_exclusions": 7}
    seen_source_ids: set[str] = set()
    source_counts: dict[str, int] = {}
    for section_name, items in sections.items():
        if not isinstance(items, list) or len(items) != expected_lengths[section_name]:
            raise ValueError(f"review-family registry {section_name} count differs from contract")
        count = 0
        for index, item in enumerate(items):
            context = f"{section_name}[{index}]"
            if not isinstance(item, dict):
                raise ValueError(f"{context}: item must be an object")
            references = item.get("held_release_references")
            if not isinstance(references, list) or not references:
                raise ValueError(f"{context}: held release references are missing")
            for reference in references:
                if not isinstance(reference, dict):
                    raise ValueError(f"{context}: held release reference must be an object")
                source_id = _required_string(
                    reference.get("source_record_id"),
                    field="source_record_id",
                    context=context,
                )
                if reference.get("review_status") != "held_for_variant_review":
                    raise ValueError(f"{context}: release reference bypasses variant review")
                if source_id in seen_source_ids:
                    raise ValueError("review-family registry contains duplicate source records")
                seen_source_ids.add(source_id)
                count += 1
        source_counts[section_name] = count
    counts = {
        "new_family_count": len(sections["new_families"]),
        "merge_link_count": len(sections["merge_links"]),
        "hold_exclusion_count": len(sections["hold_exclusions"]),
        "new_family_source_row_count": source_counts["new_families"],
        "merge_source_row_count": source_counts["merge_links"],
        "hold_source_row_count": source_counts["hold_exclusions"],
        "held_release_reference_count": len(seen_source_ids),
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"review-family registry accounting differs from contract: {counts}")
    return counts


def _build_document(family: dict[str, Any], *, index: int) -> dict[str, Any]:
    context = f"new_families[{index}]"
    family_id = _required_string(
        family.get("review_family_id"), field="review_family_id", context=context
    )
    family_uuid = _required_string(
        family.get("review_family_uuid"), field="review_family_uuid", context=family_id
    )
    try:
        uuid.UUID(family_uuid)
    except ValueError as error:
        raise ValueError(f"{family_id}: review_family_uuid is invalid") from error
    expected_uuid = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"{IDENTITY_NAMESPACE}:{family_id}")
    )
    if family_uuid != expected_uuid:
        raise ValueError(f"{family_id}: review_family_uuid is not source-stable")
    if family.get("identity_level") != "casting_family_only":
        raise ValueError(f"{family_id}: identity level differs from contract")
    if family.get("identity_status") != "family_accepted_variants_unreviewed":
        raise ValueError(f"{family_id}: identity status differs from contract")

    brand = _required_string(family.get("brand"), field="brand", context=family_id)
    casting = _required_string(
        family.get("display_name"), field="display_name", context=family_id
    )
    aliases = _string_list(family.get("aliases"), field="aliases", context=family_id)
    if aliases != [casting]:
        raise ValueError(f"{family_id}: approved aliases differ from the frozen v1 contract")
    expected_key = {"brand": _normalize(brand), "casting": _normalize(casting)}
    if family.get("normalized_family_key") != expected_key:
        raise ValueError(f"{family_id}: normalized family key differs from display identity")

    decision = family.get("decision")
    if not isinstance(decision, dict):
        raise ValueError(f"{family_id}: decision metadata is missing")
    if (
        decision.get("decision") != "create_new_casting"
        or decision.get("scope") != "casting_family_only"
        or decision.get("variant_decision") != "hold"
        or decision.get("target_family_id") is not None
    ):
        raise ValueError(f"{family_id}: decision is not eligible for family projection")

    references = family.get("held_release_references")
    if not isinstance(references, list) or not references:
        raise ValueError(f"{family_id}: source record references are missing")
    source_record_ids = sorted(
        _required_string(
            reference.get("source_record_id") if isinstance(reference, dict) else None,
            field="source_record_id",
            context=family_id,
        )
        for reference in references
    )
    if len(source_record_ids) != len(set(source_record_ids)):
        raise ValueError(f"{family_id}: source record references contain duplicates")

    return {
        "knowledge_type": "review_family",
        "review_family_id": family_id,
        "review_family_uuid": family_uuid,
        "identity_level": "casting_family_only",
        "identity_status": "family_accepted_variants_unreviewed",
        "brand": brand,
        "casting": casting,
        "aliases": sorted(aliases, key=lambda value: (value.casefold(), value)),
        "source_record_ids": source_record_ids,
    }


def build_projection(
    registry_path: Path, registry_manifest_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = _load(registry_path)
    registry_manifest = _load(registry_manifest_path)
    _validate_registry_manifest(
        registry_path=registry_path,
        registry=registry,
        manifest_path=registry_manifest_path,
        manifest=registry_manifest,
    )
    counts = _registry_counts(registry)

    documents = [
        _build_document(family, index=index)
        for index, family in enumerate(registry["new_families"])
    ]
    documents.sort(key=lambda item: item["review_family_id"])
    document_ids = [item["review_family_id"] for item in documents]
    document_uuids = [item["review_family_uuid"] for item in documents]
    normalized_keys = [
        (_normalize(item["brand"]), _normalize(item["casting"])) for item in documents
    ]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("review-family projection contains duplicate knowledge IDs")
    if len(document_uuids) != len(set(document_uuids)):
        raise ValueError("review-family projection contains duplicate knowledge UUIDs")
    if len(normalized_keys) != len(set(normalized_keys)):
        raise ValueError("review-family projection contains duplicate family identities")

    source = registry.get("source")
    if not isinstance(source, dict):
        raise ValueError("review-family registry source metadata is missing")
    projection_source = {
        "dataset_version": _required_string(
            source.get("dataset_version"), field="dataset_version", context="source"
        ),
        "license": _required_string(source.get("license"), field="license", context="source"),
        "license_url": _required_string(
            source.get("license_url"), field="license_url", context="source"
        ),
        "page_title": _required_string(
            source.get("page_title"), field="page_title", context="source"
        ),
        "page_url": _required_string(
            source.get("page_url"), field="page_url", context="source"
        ),
        "revision_id": source.get("revision_id"),
        "revision_timestamp": _required_string(
            source.get("revision_timestamp"), field="revision_timestamp", context="source"
        ),
        "registry_version": REGISTRY_VERSION,
    }
    if not isinstance(projection_source["revision_id"], int):
        raise ValueError("source: revision_id must be an integer")

    projection = {
        "schema_version": SCHEMA_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "status": "debug_retrieval_only",
        "eligible_for": PROJECTION_ELIGIBLE_FOR,
        "excluded_from": PROJECTION_EXCLUDED_FROM,
        "searchable_fields": SEARCHABLE_FIELDS,
        "source": projection_source,
        "documents": documents,
    }
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "inputs": {
            "review_family_registry": {
                "file": registry_path.name,
                "sha256": _sha256(registry_path),
                "version": REGISTRY_VERSION,
            },
            "review_family_registry_manifest": {
                "file": registry_manifest_path.name,
                "sha256": _sha256(registry_manifest_path),
            },
        },
        "document_count": len(documents),
        "knowledge_type_counts": {"review_family": len(documents)},
        "document_fields": DOCUMENT_FIELDS,
        "searchable_fields": SEARCHABLE_FIELDS,
        "eligible_for": PROJECTION_ELIGIBLE_FOR,
        "excluded_from": PROJECTION_EXCLUDED_FROM,
        "accepted_source_record_count": counts["new_family_source_row_count"],
        "skipped_merge_link_count": counts["merge_link_count"],
        "skipped_merge_source_record_count": counts["merge_source_row_count"],
        "skipped_hold_exclusion_count": counts["hold_exclusion_count"],
        "skipped_hold_source_record_count": counts["hold_source_row_count"],
        "source_held_release_reference_count": counts["held_release_reference_count"],
        "provisional_variant_document_count": 0,
        "canonical_promotion_count": 0,
        "postgresql_row_count": 0,
    }
    return projection, manifest


def expected_outputs(
    projection: dict[str, Any],
    manifest: dict[str, Any],
    *,
    projection_file_name: str = "review_family_knowledge.json",
) -> tuple[str, str]:
    projection_text = _stable_json(projection)
    frozen_manifest = dict(manifest)
    frozen_manifest["projection_file"] = projection_file_name
    frozen_manifest["projection_sha256"] = hashlib.sha256(
        projection_text.encode("utf-8")
    ).hexdigest()
    return projection_text, _stable_json(frozen_manifest)


def _write_atomically(outputs: list[tuple[Path, str]]) -> None:
    temporary: list[tuple[Path, Path]] = []
    try:
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary.append((Path(handle.name), path))
        for temporary_path, final_path in temporary:
            os.replace(temporary_path, final_path)
    finally:
        for temporary_path, _ in temporary:
            temporary_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or verify the debug-only review-family knowledge projection"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "data" / "review_family_registry.json",
    )
    parser.add_argument(
        "--registry-manifest",
        type=Path,
        default=ROOT / "data" / "review_family_registry_manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "review_family_knowledge.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "review_family_knowledge_manifest.json",
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        built = build_projection(arguments.registry, arguments.registry_manifest)
        expected = expected_outputs(*built, projection_file_name=arguments.output.name)
        outputs = (arguments.output, arguments.manifest)
        inputs = (arguments.registry, arguments.registry_manifest)
        resolved_outputs = {path.resolve() for path in outputs}
        if len(resolved_outputs) != len(outputs):
            raise ValueError("review-family knowledge output paths must be distinct")
        if resolved_outputs & {path.resolve() for path in inputs}:
            raise ValueError("review-family knowledge outputs must not overwrite inputs")
        if arguments.check:
            if any(not path.is_file() for path in outputs):
                raise ValueError("review-family knowledge outputs are missing")
            actual = tuple(path.read_text(encoding="utf-8") for path in outputs)
            if actual != expected:
                raise ValueError("review-family knowledge outputs are stale")
            print("verified review-family knowledge projection: 42 families; variants=0")
            return 0
        _write_atomically(list(zip(outputs, expected, strict=True)))
        print("built review-family knowledge projection: 42 families; variants=0")
        return 0
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
