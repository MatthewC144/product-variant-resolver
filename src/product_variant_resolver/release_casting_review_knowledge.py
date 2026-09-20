"""Project local review-family relationships into private offline-evaluation documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from .release_casting_review_materialization import (
    REGISTRY_VERSION as SOURCE_REGISTRY_VERSION,
)
from .release_casting_review_materialization import (
    SCHEMA_VERSION as SOURCE_REGISTRY_SCHEMA_VERSION,
)
from .release_casting_review_materialization import check_materialization
from .release_staging import digest

SCHEMA_VERSION = "pvr-local-release-review-family-knowledge-v1"
KNOWLEDGE_VERSION = "local-release-review-family-knowledge-v1"
PUBLIC_SCHEMA_VERSION = "pvr-local-release-review-family-knowledge-public-summary-v1"
EXISTING_SCHEMA_VERSION = "pvr-review-family-knowledge-v1"
EXISTING_KNOWLEDGE_VERSION = "review-family-knowledge-fandom-2025-r790665-v1"
PRIVATE_DIRECTORY_NAME = "local-release-casting-review-family-knowledge-v1"
PUBLIC_DIRECTORY_NAME = "local-release-casting-review-family-knowledge-v1"
IDENTITY_NAMESPACE = "product-variant-resolver:local-release-review-family-knowledge"
SEARCHABLE_FIELDS = ("brand", "casting", "aliases")
DOCUMENT_FIELDS = (
    "knowledge_type",
    "review_family_id",
    "review_family_uuid",
    "identity_level",
    "identity_status",
    "brand",
    "casting",
    "aliases",
    "source_record_ids",
)
ELIGIBLE_FOR = ("offline_retrieval_evaluation",)
EXCLUDED_FROM = (
    "runtime_retrieval",
    "canonical_variant_response",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "evaluation_ground_truth",
    "variant_identity",
    "postgresql_ingestion",
)


def _normalize(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"blank or invalid {field}")
    return value.strip()


def _objects(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError(f"{field} must be a list of objects")
    return value


def _strings(value: Any, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError(f"{field} must contain non-empty strings")
    stripped = [item.strip() for item in value]
    if len(stripped) != len(set(stripped)):
        raise ValueError(f"{field} contains duplicates")
    return stripped


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    if registry.get("schema_version") != SOURCE_REGISTRY_SCHEMA_VERSION:
        raise ValueError("local review-family registry schema differs from contract")
    if registry.get("registry_version") != SOURCE_REGISTRY_VERSION:
        raise ValueError("local review-family registry version differs from contract")
    if registry.get("status") != "complete_review_layer_only":
        raise ValueError("local review-family registry is not complete")
    checksum = registry.get("registry_sha256")
    body = {key: value for key, value in registry.items() if key != "registry_sha256"}
    if checksum != digest(body):
        raise ValueError("local review-family registry checksum differs from content")
    relationships = _objects(registry.get("relationships"), "review relationships")
    exclusions = _objects(registry.get("decision_exclusions"), "decision exclusions")
    if exclusions:
        raise ValueError("current knowledge projection does not accept decision exclusions")
    summary = registry.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("local review-family registry summary is missing")
    if summary.get("materialized_review_relationships") != len(relationships):
        raise ValueError("local review-family relationship count differs from summary")
    for field in (
        "canonical_promotions",
        "reviewed_colors",
        "postgresql_writes",
        "evaluation_labels",
        "runtime_indexed_relationships",
        "network_requests",
    ):
        if summary.get(field) != 0:
            raise ValueError(f"local review-family registry unexpectedly widens {field}")
    return relationships


def _validate_existing_projection(
    projection: dict[str, Any],
    manifest: dict[str, Any],
    *,
    projection_sha256: str,
) -> list[dict[str, Any]]:
    if projection.get("schema_version") != EXISTING_SCHEMA_VERSION:
        raise ValueError("existing review-family projection schema differs from contract")
    if projection.get("knowledge_version") != EXISTING_KNOWLEDGE_VERSION:
        raise ValueError("existing review-family projection version differs from contract")
    if projection.get("status") != "debug_retrieval_only":
        raise ValueError("existing review-family projection status differs from contract")
    documents = _objects(projection.get("documents"), "existing review-family documents")
    if len(documents) != 42:
        raise ValueError("existing review-family projection must contain exactly 42 documents")
    if manifest.get("knowledge_version") != EXISTING_KNOWLEDGE_VERSION:
        raise ValueError("existing review-family manifest version differs from contract")
    if manifest.get("document_count") != len(documents):
        raise ValueError("existing review-family manifest count differs from documents")
    if manifest.get("projection_sha256") != projection_sha256:
        raise ValueError("existing review-family projection checksum differs from manifest")
    return documents


def _identity_keys(document: dict[str, Any]) -> set[tuple[str, str]]:
    brand = _normalize(_required_text(document.get("brand"), "brand"))
    casting = _required_text(document.get("casting"), "casting")
    aliases = _strings(document.get("aliases"), "aliases")
    return {(brand, _normalize(value)) for value in (casting, *aliases)}


def _existing_identity_sets(
    documents: list[dict[str, Any]],
) -> tuple[set[str], set[str], set[tuple[str, str]]]:
    ids: set[str] = set()
    uuids: set[str] = set()
    identities: set[tuple[str, str]] = set()
    for document in documents:
        if document.get("knowledge_type") != "review_family":
            raise ValueError("existing projection contains a non-family document")
        family_id = _required_text(document.get("review_family_id"), "review_family_id")
        family_uuid = _required_text(document.get("review_family_uuid"), "review_family_uuid")
        try:
            uuid.UUID(family_uuid)
        except ValueError as error:
            raise ValueError("existing projection contains an invalid UUID") from error
        keys = _identity_keys(document)
        if family_id in ids or family_uuid in uuids or identities.intersection(keys):
            raise ValueError("existing projection contains duplicate family identity")
        ids.add(family_id)
        uuids.add(family_uuid)
        identities.update(keys)
    return ids, uuids, identities


def _build_document(relationship: dict[str, Any]) -> dict[str, Any]:
    relationship_id = _required_text(relationship.get("relationship_id"), "relationship_id")
    if relationship.get("identity_level") != "review_family_only":
        raise ValueError("relationship identity level differs from contract")
    if relationship.get("relationship_status") != "owner_confirmed_variants_held":
        raise ValueError("relationship status differs from contract")
    if relationship.get("decision") != "same_review_family":
        raise ValueError("only affirmative review relationships can be projected")
    if relationship.get("candidate_evidence_status") != "context_only_not_selected":
        raise ValueError("candidate evidence selection boundary was widened")
    if (
        relationship.get("canonical_uuid") is not None
        or relationship.get("color_decision") is not None
    ):
        raise ValueError("relationship unexpectedly contains canonical or color authority")
    relationship_checksum = relationship.get("relationship_sha256")
    relationship_body = {
        key: value for key, value in relationship.items() if key != "relationship_sha256"
    }
    if relationship_checksum != digest(relationship_body):
        raise ValueError("review relationship checksum differs from content")

    key = relationship.get("normalized_key")
    if not isinstance(key, dict):
        raise ValueError("relationship normalized key is missing")
    brand_key = _required_text(key.get("brand"), "normalized brand")
    casting_key = _required_text(key.get("casting"), "normalized casting")
    if brand_key != "hot wheels":
        raise ValueError("local projection supports only the Hot Wheels brand")
    aliases = sorted(
        _strings(relationship.get("observed_casting_labels"), "observed_casting_labels"),
        key=lambda value: (value.casefold(), value),
    )
    if any(_normalize(alias) != casting_key for alias in aliases):
        raise ValueError("owner-confirmed aliases differ from the frozen normalized family key")
    references = _objects(relationship.get("source_references"), "source references")
    source_ids = sorted(
        _required_text(reference.get("source_record_id"), "source_record_id")
        for reference in references
    )
    if not source_ids or len(source_ids) != len(set(source_ids)):
        raise ValueError("relationship source references are empty or duplicated")
    if any(
        reference.get("release_variant_status") != "held_for_variant_review"
        for reference in references
    ):
        raise ValueError("relationship source reference bypasses variant review")
    family_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{IDENTITY_NAMESPACE}:{relationship_id}"))
    return {
        "knowledge_type": "review_family",
        "review_family_id": relationship_id,
        "review_family_uuid": family_uuid,
        "identity_level": "casting_family_only",
        "identity_status": "owner_confirmed_variants_unreviewed",
        "brand": "Hot Wheels",
        "casting": aliases[0],
        "aliases": aliases,
        "source_record_ids": source_ids,
    }


def build_projection(
    registry: dict[str, Any],
    existing_projection: dict[str, Any],
    existing_manifest: dict[str, Any],
    *,
    existing_projection_sha256: str,
    existing_manifest_sha256: str,
) -> dict[str, Any]:
    relationships = _validate_registry(registry)
    existing_documents = _validate_existing_projection(
        existing_projection,
        existing_manifest,
        projection_sha256=existing_projection_sha256,
    )
    existing_ids, existing_uuids, existing_identities = _existing_identity_sets(existing_documents)
    documents = [_build_document(relationship) for relationship in relationships]
    documents.sort(key=lambda item: item["review_family_id"])

    local_ids: set[str] = set()
    local_uuids: set[str] = set()
    local_identities: set[tuple[str, str]] = set()
    source_ids: set[str] = set()
    for document in documents:
        family_id = str(document["review_family_id"])
        family_uuid = str(document["review_family_uuid"])
        identities = _identity_keys(document)
        document_sources = set(str(value) for value in document["source_record_ids"])
        if family_id in local_ids or family_id in existing_ids:
            raise ValueError("review-family knowledge ID collides with another document")
        if family_uuid in local_uuids or family_uuid in existing_uuids:
            raise ValueError("review-family knowledge UUID collides with another document")
        if local_identities.intersection(identities) or existing_identities.intersection(
            identities
        ):
            raise ValueError("normalized review-family identity collides with another document")
        if source_ids.intersection(document_sources):
            raise ValueError("source record is assigned to more than one knowledge document")
        local_ids.add(family_id)
        local_uuids.add(family_uuid)
        local_identities.update(identities)
        source_ids.update(document_sources)

    summary = {
        "document_count": len(documents),
        "knowledge_type_counts": {"review_family": len(documents)},
        "source_record_reference_count": len(source_ids),
        "existing_corpus_document_count": len(existing_documents),
        "id_collisions": 0,
        "uuid_collisions": 0,
        "normalized_identity_collisions": 0,
        "runtime_indexed_documents": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "evaluation_labels": 0,
        "network_requests": 0,
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "status": "offline_evaluation_candidate_not_runtime",
        "eligible_for": list(ELIGIBLE_FOR),
        "excluded_from": list(EXCLUDED_FROM),
        "searchable_fields": list(SEARCHABLE_FIELDS),
        "document_fields": list(DOCUMENT_FIELDS),
        "source": {
            "local_registry_version": registry.get("registry_version"),
            "local_registry_sha256": registry.get("registry_sha256"),
            "source_decision_ledger_sha256": registry.get("source_decision_ledger_sha256"),
            "existing_projection_version": existing_projection.get("knowledge_version"),
            "existing_projection_sha256": existing_projection_sha256,
            "existing_manifest_sha256": existing_manifest_sha256,
            "publication_authority": "local_owner_supplied_no_redistribution_authority",
        },
        "documents": documents,
        "summary": summary,
    }
    return {**body, "projection_sha256": digest(body)}


def validate_projection(
    registry: dict[str, Any],
    existing_projection: dict[str, Any],
    existing_manifest: dict[str, Any],
    projection: dict[str, Any],
    *,
    existing_projection_sha256: str,
    existing_manifest_sha256: str,
) -> None:
    expected = build_projection(
        registry,
        existing_projection,
        existing_manifest,
        existing_projection_sha256=existing_projection_sha256,
        existing_manifest_sha256=existing_manifest_sha256,
    )
    if projection != expected:
        raise ValueError("local review-family knowledge differs from deterministic projection")


def build_public_manifest(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "status": projection["status"],
        "public_scope": "aggregate_counts_hashes_and_allowlists_only_no_documents_labels_ids_or_rows",
        "eligible_for": projection["eligible_for"],
        "excluded_from": projection["excluded_from"],
        "searchable_fields": projection["searchable_fields"],
        "document_fields": projection["document_fields"],
        "source_hashes": {
            "local_registry_sha256": projection["source"]["local_registry_sha256"],
            "source_decision_ledger_sha256": projection["source"]["source_decision_ledger_sha256"],
            "existing_projection_sha256": projection["source"]["existing_projection_sha256"],
            "existing_manifest_sha256": projection["source"]["existing_manifest_sha256"],
        },
        "private_projection_sha256": projection["projection_sha256"],
        "summary": projection["summary"],
    }


def render_public_report(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    return "\n".join(
        [
            "# Local release review-family knowledge projection — public summary",
            "",
            "Five private review-family documents were prepared for offline evaluation only.",
            "No document is loaded into the API or Dual RAG runtime by this feature.",
            "",
            f"- Projected documents: {summary['document_count']}",
            f"- Source record references: {summary['source_record_reference_count']}",
            f"- Existing-corpus documents checked: {summary['existing_corpus_document_count']}",
            f"- ID collisions: {summary['id_collisions']}",
            f"- UUID collisions: {summary['uuid_collisions']}",
            f"- Normalized identity collisions: {summary['normalized_identity_collisions']}",
            "- Runtime-indexed documents: 0",
            "- Canonical promotions: 0",
            "- Reviewed colors: 0",
            "- PostgreSQL writes: 0",
            "- Evaluation labels: 0",
            "- Network requests: 0",
            "",
            "Searchable-field candidate allowlist: `brand`, `casting`, `aliases`.",
            "The next gate is an independently specified offline retrieval evaluation.",
            "",
        ]
    )


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return payload


def _paths(root: Path) -> tuple[Path, Path]:
    return (
        root / "data/external/hot-wheels-wiki" / PRIVATE_DIRECTORY_NAME,
        root / "reports" / PUBLIC_DIRECTORY_NAME,
    )


def _safe_directory(directory: Path, expected_parent: Path, label: str) -> None:
    if directory.absolute().parent != expected_parent.absolute():
        raise ValueError(f"{label} must be a direct child of {expected_parent}")
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError(f"symlink {label} is not allowed")


def _write_directory(directory: Path, outputs: dict[str, str]) -> None:
    directory.mkdir()
    try:
        for name, content in outputs.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except BaseException:
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()
        raise


def _remove_created_directory(directory: Path) -> None:
    if directory.is_dir():
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()


def _assert_outputs(directory: Path, outputs: dict[str, str], label: str) -> None:
    if not directory.is_dir() or {path.name for path in directory.iterdir()} != set(outputs):
        raise ValueError(f"{label} files differ from projection contract")
    for name, content in outputs.items():
        if (directory / name).read_text(encoding="utf-8") != content:
            raise ValueError(f"{label}/{name} differs from deterministic projection")


def build_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = check_materialization(root)
    existing_path = root / "data/review_family_knowledge.json"
    existing_manifest_path = root / "data/review_family_knowledge_manifest.json"
    existing_bytes = existing_path.read_bytes()
    existing_manifest_bytes = existing_manifest_path.read_bytes()
    existing_projection = _load_object(existing_path)
    existing_manifest = _load_object(existing_manifest_path)
    projection = build_projection(
        registry,
        existing_projection,
        existing_manifest,
        existing_projection_sha256=_sha256_bytes(existing_bytes),
        existing_manifest_sha256=_sha256_bytes(existing_manifest_bytes),
    )
    return projection, build_public_manifest(projection)


def _expected_outputs(
    projection: dict[str, Any], manifest: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {"projection.json": _stable_json(projection)},
        {
            "manifest.json": _stable_json(manifest),
            "report.md": render_public_report(manifest),
        },
    )


def publish_outputs(root: Path, projection: dict[str, Any], manifest: dict[str, Any]) -> str:
    private_directory, public_directory = _paths(root)
    _safe_directory(private_directory, root / "data/external/hot-wheels-wiki", "private projection")
    _safe_directory(public_directory, root / "reports", "public projection")
    private_outputs, public_outputs = _expected_outputs(projection, manifest)
    if private_directory.exists() and public_directory.exists():
        _assert_outputs(private_directory, private_outputs, "private projection")
        _assert_outputs(public_directory, public_outputs, "public projection")
        return "unchanged"
    if private_directory.exists() or public_directory.exists():
        raise ValueError("partial knowledge projection exists; refusing to overwrite")
    created: list[Path] = []
    try:
        _write_directory(private_directory, private_outputs)
        created.append(private_directory)
        _write_directory(public_directory, public_outputs)
        created.append(public_directory)
    except BaseException:
        for directory in reversed(created):
            _remove_created_directory(directory)
        raise
    return "created"


def publish_projection(root: Path) -> tuple[dict[str, Any], str]:
    projection, manifest = build_artifacts(root)
    operation = publish_outputs(root, projection, manifest)
    check_projection(root)
    return projection, operation


def check_projection(root: Path) -> dict[str, Any]:
    projection, manifest = build_artifacts(root)
    private_directory, public_directory = _paths(root)
    private_outputs, public_outputs = _expected_outputs(projection, manifest)
    _assert_outputs(private_directory, private_outputs, "private projection")
    _assert_outputs(public_directory, public_outputs, "public projection")
    return projection


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project local review families into private offline-evaluation knowledge"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.check:
        projection = check_projection(root)
        operation = "valid"
    else:
        projection, operation = publish_projection(root)
    print(
        json.dumps(
            {
                "operation": operation,
                "projection_sha256": projection["projection_sha256"],
                "status": projection["status"],
                "summary": projection["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
