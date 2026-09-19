"""Materialize completed local casting decisions into a private review-layer registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .release_casting_review_batch import check_batch
from .release_casting_review_decisions import check_decisions, validate_ledger
from .release_staging import digest

SCHEMA_VERSION = "pvr-local-release-casting-review-family-registry-v1"
REGISTRY_VERSION = "local-release-casting-review-family-materialization-v1"
PUBLIC_SCHEMA_VERSION = "pvr-local-release-casting-review-family-public-summary-v1"
PRIVATE_DIRECTORY_NAME = "local-release-casting-review-family-materialization-v1"
PUBLIC_DIRECTORY_NAME = "local-release-casting-review-family-materialization-v1"
EXCLUDED_EFFECTS = (
    "release_variant_approval",
    "physical_color_inference",
    "candidate_identity_selection",
    "canonical_uuid_creation",
    "postgresql_write",
    "evaluation_label_creation",
    "dual_rag_runtime_change",
)


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"blank or invalid {field}")
    return value.strip()


def _objects(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError(f"{field} must be a list of objects")
    return value


def _source_references(question: dict[str, Any], seen_source_ids: set[str]) -> list[dict[str, Any]]:
    observations = _objects(question.get("source_observations"), "source observations")
    if not observations:
        raise ValueError("review question has no source observations")
    references: list[dict[str, Any]] = []
    for observation in observations:
        source_id = _required_text(observation.get("source_record_id"), "source_record_id")
        if source_id in seen_source_ids:
            raise ValueError("source record is assigned to more than one review relationship")
        seen_source_ids.add(source_id)
        references.append(
            {
                "source_record_id": source_id,
                "release_year": observation.get("release_year"),
                "toy_number": observation.get("toy_number"),
                "collector_number": observation.get("collector_number"),
                "source_model_label": observation.get("source_model_label"),
                "casting_name": observation.get("casting_name"),
                "series": observation.get("series"),
                "series_position": observation.get("series_position"),
                "variant_note": observation.get("variant_note"),
                "release_variant_status": "held_for_variant_review",
                "canonical_uuid": None,
                "color": None,
            }
        )
    references.sort(
        key=lambda item: (
            str(item["release_year"]),
            str(item["toy_number"]),
            item["source_record_id"],
        )
    )
    return references


def _relationship_id(packet_sha256: str, review_cluster_id: str) -> str:
    identity = digest(
        {
            "identity_scope": "local_release_casting_review_relationship",
            "packet_sha256": packet_sha256,
            "review_cluster_id": review_cluster_id,
        }
    )
    return f"local-review-family-{identity[:20]}"


def _decision_item(
    packet: dict[str, Any],
    question: dict[str, Any],
    event: dict[str, Any],
    seen_source_ids: set[str],
) -> tuple[str, dict[str, Any]]:
    ordinal = question.get("ordinal")
    if event.get("question_ordinal") != ordinal:
        raise ValueError("decision event differs from packet question ordinal")
    cluster_id = _required_text(question.get("review_cluster_id"), "review_cluster_id")
    if event.get("review_cluster_id") != cluster_id:
        raise ValueError("decision event differs from packet review cluster")
    if question.get("canonical_uuid") is not None or question.get("color_decision") is not None:
        raise ValueError("review question unexpectedly contains canonical or color authority")
    labels = question.get("observed_casting_labels")
    if (
        not isinstance(labels, list)
        or not labels
        or not all(isinstance(item, str) for item in labels)
    ):
        raise ValueError("review question has invalid observed labels")
    references = _source_references(question, seen_source_ids)
    decision = _required_text(event.get("decision"), "decision")
    common = {
        "question_ordinal": ordinal,
        "review_cluster_id": cluster_id,
        "decision": decision,
        "decision_event_sha256": event.get("event_sha256"),
        "observed_casting_labels": labels,
        "normalized_key": question.get("normalized_key"),
        "candidate_evidence_sha256": digest(question.get("candidate_evidence")),
        "candidate_evidence_status": "context_only_not_selected",
        "source_references": references,
        "source_reference_count": len(references),
        "canonical_uuid": None,
        "color_decision": None,
        "excluded_effects": list(EXCLUDED_EFFECTS),
    }
    if decision == "same_review_family":
        relationship_id = _relationship_id(str(packet["packet_sha256"]), cluster_id)
        body = {
            **common,
            "relationship_id": relationship_id,
            "identity_level": "review_family_only",
            "relationship_status": "owner_confirmed_variants_held",
        }
        return "relationship", {**body, "relationship_sha256": digest(body)}
    if decision not in {"keep_separate", "unknown"}:
        raise ValueError("decision is unsupported for review-family materialization")
    body = {
        **common,
        "exclusion_status": (
            "owner_rejected_relationship"
            if decision == "keep_separate"
            else "owner_relationship_unresolved"
        ),
        "materialized": False,
    }
    return "exclusion", {**body, "exclusion_sha256": digest(body)}


def build_registry(packet: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    validate_ledger(packet, ledger)
    questions = _objects(packet.get("questions"), "packet questions")
    events = _objects(ledger.get("events"), "decision events")
    if ledger.get("status") != "complete" or len(events) != len(questions):
        raise ValueError("decision ledger must be complete before materialization")
    if packet.get("packet_sha256") != ledger.get("packet_sha256"):
        raise ValueError("packet and decision ledger checksums differ")

    relationships: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    seen_cluster_ids: set[str] = set()
    for question, event in zip(questions, events, strict=True):
        cluster_id = _required_text(question.get("review_cluster_id"), "review_cluster_id")
        if cluster_id in seen_cluster_ids:
            raise ValueError("review cluster is assigned more than once")
        seen_cluster_ids.add(cluster_id)
        kind, item = _decision_item(packet, question, event, seen_source_ids)
        if kind == "relationship":
            relationships.append(item)
        else:
            exclusions.append(item)
    relationships.sort(key=lambda item: int(item["question_ordinal"]))
    exclusions.sort(key=lambda item: int(item["question_ordinal"]))
    decisions = Counter(str(event["decision"]) for event in events)
    summary = {
        "review_questions": len(questions),
        "materialized_review_relationships": len(relationships),
        "decision_exclusions": len(exclusions),
        "held_source_references": len(seen_source_ids),
        "decision_counts": {
            "same_review_family": decisions["same_review_family"],
            "keep_separate": decisions["keep_separate"],
            "unknown": decisions["unknown"],
        },
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "evaluation_labels": 0,
        "runtime_indexed_relationships": 0,
        "network_requests": 0,
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "registry_version": REGISTRY_VERSION,
        "status": "complete_review_layer_only",
        "source_packet_sha256": packet.get("packet_sha256"),
        "source_packet_batch_id": packet.get("batch_id"),
        "source_decision_ledger_sha256": ledger.get("ledger_sha256"),
        "policy": {
            "identity_level": "review_family_only",
            "release_variants": "held_for_variant_review",
            "candidate_evidence": "context_only_not_selected",
            "canonical_promotion": False,
            "color_inference": False,
            "postgresql_write": False,
            "evaluation_label_creation": False,
            "runtime_indexing": False,
        },
        "relationships": relationships,
        "decision_exclusions": exclusions,
        "summary": summary,
    }
    return {**body, "registry_sha256": digest(body)}


def validate_registry(
    packet: dict[str, Any], ledger: dict[str, Any], registry: dict[str, Any]
) -> None:
    if registry != build_registry(packet, ledger):
        raise ValueError("review-family registry differs from deterministic materialization")


def build_public_manifest(registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "registry_version": REGISTRY_VERSION,
        "status": registry["status"],
        "public_scope": "aggregate_counts_and_hashes_only_no_labels_clusters_source_rows_or_answers",
        "source_packet_sha256": registry["source_packet_sha256"],
        "source_packet_batch_id": registry["source_packet_batch_id"],
        "source_decision_ledger_sha256": registry["source_decision_ledger_sha256"],
        "private_registry_sha256": registry["registry_sha256"],
        "summary": registry["summary"],
    }


def render_public_report(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    return "\n".join(
        [
            "# Local release casting review-family materialization — public summary",
            "",
            "A complete owner-decision batch was materialized into a private review-layer registry.",
            "The registry remains local; this report exposes aggregate counts and hashes only.",
            "",
            f"- Review questions: {summary['review_questions']}",
            f"- Materialized review relationships: {summary['materialized_review_relationships']}",
            f"- Decision exclusions: {summary['decision_exclusions']}",
            f"- Held source references: {summary['held_source_references']}",
            f"- `same_review_family`: {summary['decision_counts']['same_review_family']}",
            f"- `keep_separate`: {summary['decision_counts']['keep_separate']}",
            f"- `unknown`: {summary['decision_counts']['unknown']}",
            "- Canonical promotions: 0",
            "- Reviewed colors: 0",
            "- PostgreSQL writes: 0",
            "- Evaluation labels: 0",
            "- Runtime-indexed relationships: 0",
            "- Network requests: 0",
            "",
            "All source releases remain distinct and held for variant review.",
            "Candidate evidence is context-only and no candidate identity is selected.",
            "",
        ]
    )


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


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
        raise ValueError(f"{label} files differ from materialization contract")
    for name, content in outputs.items():
        if (directory / name).read_text(encoding="utf-8") != content:
            raise ValueError(f"{label}/{name} differs from deterministic materialization")


def build_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = check_batch(
        root,
        root / "data/external/hot-wheels-wiki/local-release-casting-review-batch-01",
        root / "reports/local-release-casting-review-batch-01",
    )
    ledger = check_decisions(root)
    registry = build_registry(packet, ledger)
    return registry, build_public_manifest(registry)


def _expected_outputs(
    registry: dict[str, Any], manifest: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {"registry.json": _stable_json(registry)},
        {
            "manifest.json": _stable_json(manifest),
            "report.md": render_public_report(manifest),
        },
    )


def publish_outputs(root: Path, registry: dict[str, Any], manifest: dict[str, Any]) -> str:
    private_directory, public_directory = _paths(root)
    _safe_directory(
        private_directory, root / "data/external/hot-wheels-wiki", "private materialization"
    )
    _safe_directory(public_directory, root / "reports", "public materialization")
    private_outputs, public_outputs = _expected_outputs(registry, manifest)
    if private_directory.exists() and public_directory.exists():
        _assert_outputs(private_directory, private_outputs, "private materialization")
        _assert_outputs(public_directory, public_outputs, "public materialization")
        return "unchanged"
    if private_directory.exists() or public_directory.exists():
        raise ValueError("partial materialization exists; refusing to overwrite")

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


def publish_materialization(root: Path) -> tuple[dict[str, Any], str]:
    registry, manifest = build_artifacts(root)
    operation = publish_outputs(root, registry, manifest)
    check_materialization(root)
    return registry, operation


def check_materialization(root: Path) -> dict[str, Any]:
    registry, manifest = build_artifacts(root)
    private_directory, public_directory = _paths(root)
    private_outputs, public_outputs = _expected_outputs(registry, manifest)
    _assert_outputs(private_directory, private_outputs, "private materialization")
    _assert_outputs(public_directory, public_outputs, "public materialization")
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize completed local casting decisions at review-family scope"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.check:
        registry = check_materialization(root)
        operation = "valid"
    else:
        registry, operation = publish_materialization(root)
    print(
        json.dumps(
            {
                "operation": operation,
                "registry_sha256": registry["registry_sha256"],
                "status": registry["status"],
                "summary": registry["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
