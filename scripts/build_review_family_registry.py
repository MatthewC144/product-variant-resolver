#!/usr/bin/env python3
"""Materialize adjudicated family decisions without fabricating release variants."""

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
PILOT = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
SCHEMA_VERSION = "pvr-review-family-registry-v1"
REGISTRY_VERSION = "fandom-2025-review-families-r790665-v1"
MANIFEST_SCHEMA_VERSION = "pvr-review-family-registry-manifest-v1"
QUEUE_SCHEMA_VERSION = "pvr-fandom-priority-two-adjudicated-queue-v1"
QUEUE_VERSION = "fandom-2025-priority-two-batch-05-adjudicated-v1"
QUEUE_MANIFEST_SCHEMA_VERSION = "pvr-fandom-priority-two-adjudicated-manifest-v1"
STAGING_SCHEMA_VERSION = "fandom-hot-wheels-staging-v1"
STAGING_VERSION = "fandom-hot-wheels-2025-pilot-r790665-v1"
STAGING_MANIFEST_SCHEMA_VERSION = "fandom-pilot-manifest-v1"
HUMAN_SCHEMA_VERSION = "pvr-human-backed-catalog-v1"
HUMAN_MANIFEST_SCHEMA_VERSION = "pvr-human-backed-catalog-manifest-v1"
IDENTITY_NAMESPACE = "product-variant-resolver:review-family:fandom-hot-wheels-wiki"
ALLOWED_DECISIONS = {"create_new_casting", "merge_existing_family", "hold"}
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


def _file_reference(path: Path) -> dict[str, str]:
    return {"file": path.name, "sha256": _sha256(path)}


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
    return list(value)


def normalize(value: str | None) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _review_uuid(family_review_id: str) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{IDENTITY_NAMESPACE}:{family_review_id}",
        )
    )


def _validate_input_manifests(
    *,
    queue_path: Path,
    queue: dict[str, Any],
    queue_manifest_path: Path,
    queue_manifest: dict[str, Any],
    staging_path: Path,
    staging: dict[str, Any],
    staging_manifest_path: Path,
    staging_manifest: dict[str, Any],
    human_path: Path,
    human: dict[str, Any],
    human_manifest_path: Path,
    human_manifest: dict[str, Any],
) -> None:
    if queue.get("schema_version") != QUEUE_SCHEMA_VERSION:
        raise ValueError("final queue has an unsupported schema")
    if queue.get("queue_version") != QUEUE_VERSION:
        raise ValueError("final queue has an unsupported version")
    if queue_manifest.get("schema_version") != QUEUE_MANIFEST_SCHEMA_VERSION:
        raise ValueError("final queue manifest has an unsupported schema")
    if queue_manifest.get("result_file") != queue_path.name:
        raise ValueError("final queue filename differs from its manifest")
    if queue_manifest.get("result_sha256") != _sha256(queue_path):
        raise ValueError("final queue checksum differs from its manifest")
    if queue_manifest.get("result_version") != queue.get("queue_version"):
        raise ValueError("final queue version differs from its manifest")

    normalized_reference = staging_manifest.get("files", {}).get(staging_path.name, {})
    if normalized_reference.get("sha256") != _sha256(staging_path):
        raise ValueError("staging checksum differs from its manifest")
    if staging_manifest.get("dataset_version") != STAGING_VERSION:
        raise ValueError("staging manifest has an unsupported version")
    if staging_manifest.get("schema_version") != STAGING_MANIFEST_SCHEMA_VERSION:
        raise ValueError("staging manifest has an unsupported schema")
    if staging.get("schema_version") != STAGING_SCHEMA_VERSION:
        raise ValueError("staging dataset has an unsupported schema")
    if staging.get("dataset_version") != staging_manifest.get("dataset_version"):
        raise ValueError("staging dataset version differs from its manifest")

    if human.get("schema_version") != HUMAN_SCHEMA_VERSION:
        raise ValueError("human-backed catalog has an unsupported schema")
    if human_manifest.get("schema_version") != HUMAN_MANIFEST_SCHEMA_VERSION:
        raise ValueError("human-backed catalog manifest has an unsupported schema")
    if human.get("status") != "human_review_draft":
        raise ValueError("human-backed catalog has an unsupported status")
    if human_manifest.get("catalog_version") != human.get("catalog_version"):
        raise ValueError("human-backed catalog version differs from its manifest")
    if human_manifest.get("catalog_file") != human_path.name:
        raise ValueError("human-backed catalog filename differs from its manifest")
    if human_manifest.get("catalog_sha256") != _sha256(human_path):
        raise ValueError("human-backed catalog checksum differs from its manifest")

    for path in (queue_manifest_path, staging_manifest_path, human_manifest_path):
        if not path.is_file():
            raise ValueError(f"{path.name}: manifest is missing")


def _validate_source(
    staging: dict[str, Any], staging_manifest: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    records = staging.get("records")
    if not isinstance(records, list) or len(records) != 100:
        raise ValueError("staging dataset must contain exactly 100 records")
    if staging.get("record_count") != len(records):
        raise ValueError("staging record count is inconsistent")
    if staging_manifest.get("record_count") != len(records):
        raise ValueError("staging manifest record count is inconsistent")
    source = staging.get("source")
    if not isinstance(source, dict):
        raise ValueError("staging source metadata is missing")
    revision_id = source.get("revision_id")
    license_name = source.get("license")
    license_url = source.get("license_url")
    for field in ("page_title", "page_url", "revision_timestamp"):
        _required_string(source.get(field), field=field, context="staging source")
    if revision_id != staging_manifest.get("source_revision_id"):
        raise ValueError("staging source revision differs from its manifest")
    manifest_license = staging_manifest.get("license")
    if not isinstance(manifest_license, dict) or (
        license_name != manifest_license.get("name")
        or license_url != manifest_license.get("url")
    ):
        raise ValueError("staging source license differs from its manifest")
    by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        context = f"staging record {index}"
        if not isinstance(record, dict):
            raise ValueError(f"{context}: record must be an object")
        record_id = _required_string(
            record.get("source_record_id"), field="source_record_id", context=context
        )
        if record_id in by_id:
            raise ValueError("staging dataset contains duplicate source record IDs")
        if record.get("review_status") != "needs_canonical_review":
            raise ValueError(f"{context}: record bypasses review")
        if record.get("canonical_uuid") is not None:
            raise ValueError(f"{context}: record asserts canonical identity")
        record_source = record.get("source")
        if not isinstance(record_source, dict) or (
            record_source.get("revision_id") != revision_id
            or record_source.get("license") != license_name
            or record_source.get("license_url") != license_url
        ):
            raise ValueError(f"{context}: source provenance is inconsistent")
        by_id[record_id] = record
    return by_id, {
        "dataset_version": staging["dataset_version"],
        "license": license_name,
        "license_url": license_url,
        "page_title": source.get("page_title"),
        "page_url": source.get("page_url"),
        "revision_id": revision_id,
        "revision_timestamp": source.get("revision_timestamp"),
    }


def _index_human_catalog(
    human: dict[str, Any], human_manifest: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    castings = human.get("castings")
    if not isinstance(castings, list) or not castings:
        raise ValueError("human-backed catalog contains no castings")
    if human_manifest.get("casting_count") != len(castings):
        raise ValueError("human-backed catalog count differs from its manifest")
    by_id: dict[str, dict[str, Any]] = {}
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    uuids: set[str] = set()
    for index, casting in enumerate(castings):
        context = f"human casting {index}"
        if not isinstance(casting, dict):
            raise ValueError(f"{context}: casting must be an object")
        casting_id = _required_string(
            casting.get("casting_id"), field="casting_id", context=context
        )
        casting_uuid = _required_string(
            casting.get("casting_uuid"), field="casting_uuid", context=context
        )
        try:
            uuid.UUID(casting_uuid)
        except ValueError as error:
            raise ValueError(f"{context}: casting_uuid is invalid") from error
        key = (normalize(casting.get("brand")), normalize(casting.get("casting")))
        if not all(key):
            raise ValueError(f"{context}: normalized family key is empty")
        if casting_id in by_id or casting_uuid in uuids or key in by_key:
            raise ValueError("human-backed catalog contains duplicate family identity")
        by_id[casting_id] = casting
        by_key[key] = casting
        uuids.add(casting_uuid)
    return by_id, by_key


def _decision_payload(family: dict[str, Any]) -> dict[str, Any]:
    decision = family.get("reviewer_decision")
    context = str(family.get("family_review_id") or "family")
    if not isinstance(decision, dict) or decision.get("status") != "completed":
        raise ValueError(f"{context}: family decision is not completed")
    outcome = decision.get("decision")
    if outcome not in ALLOWED_DECISIONS:
        raise ValueError(f"{context}: family decision is not permitted")
    if decision.get("scope") != "casting_family_only":
        raise ValueError(f"{context}: decision exceeds casting-family scope")
    if decision.get("variant_decision") != "hold":
        raise ValueError(f"{context}: release variants must remain held")
    payload = {
        "decision": outcome,
        "decision_batch_id": _required_string(
            decision.get("decision_batch_id"), field="decision_batch_id", context=context
        ),
        "decided_by": _required_string(
            decision.get("decided_by"), field="decided_by", context=context
        ),
        "decided_at": _required_string(
            decision.get("decided_at"), field="decided_at", context=context
        ),
        "reason": _required_string(
            decision.get("reason"), field="reason", context=context
        ),
        "evidence_references": _string_list(
            decision.get("evidence_references"),
            field="evidence_references",
            context=context,
        ),
        "scope": decision["scope"],
        "variant_decision": decision["variant_decision"],
    }
    target = decision.get("target_family_id")
    payload["target_family_id"] = target
    return payload


def _release_references(
    family: dict[str, Any],
    staging_by_id: dict[str, dict[str, Any]],
    seen_source_ids: set[str],
) -> list[dict[str, Any]]:
    family_id = family["family_review_id"]
    rows = family.get("source_rows")
    if not isinstance(rows, list) or family.get("source_row_count") != len(rows):
        raise ValueError(f"{family_id}: source-row count is inconsistent")
    references: list[dict[str, Any]] = []
    compared_fields = (
        "source_record_id",
        "source_row",
        "release_year",
        "toy_number",
        "collector_number",
        "series",
        "variant_note",
    )
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{family_id}: source row must be an object")
        source_id = row.get("source_record_id")
        staged = staging_by_id.get(source_id)
        if staged is None:
            raise ValueError(f"{family_id}: source row is absent from staging")
        if source_id in seen_source_ids:
            raise ValueError("source record is assigned to more than one family")
        if any(row.get(field) != staged.get(field) for field in compared_fields):
            raise ValueError(f"{family_id}: queue row differs from staging")
        if normalize(staged.get("brand")) != family["normalized_family_key"]["brand"]:
            raise ValueError(f"{family_id}: source brand differs from family key")
        if normalize(staged.get("casting_name")) != family["normalized_family_key"]["casting"]:
            raise ValueError(f"{family_id}: source casting differs from family key")
        seen_source_ids.add(source_id)
        references.append(
            {
                "collector_number": staged.get("collector_number"),
                "release_year": staged.get("release_year"),
                "review_status": "held_for_variant_review",
                "series": staged.get("series"),
                "series_position": staged.get("series_position"),
                "source_record_id": source_id,
                "source_row": staged.get("source_row"),
                "toy_number": staged.get("toy_number"),
                "variant_note": staged.get("variant_note"),
            }
        )
    return references


def _family_base(family: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
    family_id = _required_string(
        family.get("family_review_id"), field="family_review_id", context="family"
    )
    brand = _required_string(family.get("brand"), field="brand", context=family_id)
    name = _required_string(
        family.get("casting_name"), field="casting_name", context=family_id
    )
    key = family.get("normalized_family_key")
    expected = {"brand": normalize(brand), "casting": normalize(name)}
    if key != expected or not all(expected.values()):
        raise ValueError(f"{family_id}: normalized family key is inconsistent")
    return family_id, name, expected


def build_registry(
    queue_path: Path,
    queue_manifest_path: Path,
    staging_path: Path,
    staging_manifest_path: Path,
    human_path: Path,
    human_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    queue = _load(queue_path)
    queue_manifest = _load(queue_manifest_path)
    staging = _load(staging_path)
    staging_manifest = _load(staging_manifest_path)
    human = _load(human_path)
    human_manifest = _load(human_manifest_path)
    _validate_input_manifests(
        queue_path=queue_path,
        queue=queue,
        queue_manifest_path=queue_manifest_path,
        queue_manifest=queue_manifest,
        staging_path=staging_path,
        staging=staging,
        staging_manifest_path=staging_manifest_path,
        staging_manifest=staging_manifest,
        human_path=human_path,
        human=human,
        human_manifest_path=human_manifest_path,
        human_manifest=human_manifest,
    )
    if queue.get("status") != "adjudicated":
        raise ValueError("final queue is not fully adjudicated")
    summary = queue.get("summary")
    families = queue.get("families")
    if not isinstance(summary, dict) or not isinstance(families, list):
        raise ValueError("final queue is missing summary or families")
    if summary.get("pending_decisions") != 0:
        raise ValueError("final queue still contains pending decisions")
    if summary.get("completed_decisions") != len(families):
        raise ValueError("final queue completed count is inconsistent")
    if summary.get("family_count") != len(families):
        raise ValueError("final queue family count is inconsistent")
    for field, expected in (
        ("source_row_count", 100),
        ("held_release_variants", 100),
        ("promotion_eligible_families", 0),
    ):
        if summary.get(field) != expected or queue_manifest.get(field) != expected:
            raise ValueError(f"final queue {field} differs from its manifest or contract")
    if queue_manifest.get("family_count") != len(families):
        raise ValueError("final queue manifest family count is inconsistent")
    if queue_manifest.get("completed_decisions") != len(families):
        raise ValueError("final queue manifest completed count is inconsistent")
    if queue_manifest.get("pending_decisions") != 0:
        raise ValueError("final queue manifest still contains pending decisions")

    staging_by_id, source = _validate_source(staging, staging_manifest)
    human_by_id, human_by_key = _index_human_catalog(human, human_manifest)
    new_families: list[dict[str, Any]] = []
    merge_links: list[dict[str, Any]] = []
    hold_exclusions: list[dict[str, Any]] = []
    seen_family_ids: set[str] = set()
    seen_uuids: set[str] = set()
    seen_source_ids: set[str] = set()
    batch_ids = {
        item.get("batch_id")
        for item in queue.get("decision_batches", [])
        if isinstance(item, dict)
    }

    for family in families:
        if not isinstance(family, dict):
            raise ValueError("final queue family must be an object")
        family_id, name, key = _family_base(family)
        if family_id in seen_family_ids:
            raise ValueError("final queue contains duplicate family review IDs")
        seen_family_ids.add(family_id)
        if family.get("promotion_eligible") is not False:
            raise ValueError(f"{family_id}: family bypasses promotion hold")
        decision = _decision_payload(family)
        if decision["decision_batch_id"] not in batch_ids:
            raise ValueError(f"{family_id}: decision batch is absent from history")
        releases = _release_references(family, staging_by_id, seen_source_ids)
        common = {
            "brand": family["brand"],
            "decision": decision,
            "display_name": name,
            "held_release_references": releases,
            "normalized_family_key": key,
        }
        key_tuple = (key["brand"], key["casting"])
        outcome = decision["decision"]
        target_id = decision["target_family_id"]
        if outcome == "create_new_casting":
            if target_id is not None:
                raise ValueError(f"{family_id}: new family unexpectedly has a target")
            if key_tuple in human_by_key:
                raise ValueError(f"{family_id}: new family collides with human catalog")
            family_uuid = _review_uuid(family_id)
            if family_uuid in seen_uuids:
                raise ValueError("review-family UUID collision")
            seen_uuids.add(family_uuid)
            new_families.append(
                {
                    **common,
                    "aliases": [name],
                    "identity_level": "casting_family_only",
                    "identity_status": "family_accepted_variants_unreviewed",
                    "review_family_id": family_id,
                    "review_family_uuid": family_uuid,
                }
            )
        elif outcome == "merge_existing_family":
            if not isinstance(target_id, str) or not target_id:
                raise ValueError(f"{family_id}: merge target is missing")
            target = human_by_id.get(target_id)
            if target is None:
                raise ValueError(f"{family_id}: merge target is absent from human catalog")
            candidates = family.get("pre_review", {}).get("human_casting_candidate_ids")
            if not isinstance(candidates, list) or target_id not in candidates:
                raise ValueError(f"{family_id}: merge target lacks exact pre-review evidence")
            target_key = (normalize(target.get("brand")), normalize(target.get("casting")))
            if target_key != key_tuple:
                raise ValueError(f"{family_id}: merge target family key differs")
            merge_links.append(
                {
                    **common,
                    "identity_status": "family_merge_accepted_variants_unreviewed",
                    "source_family_review_id": family_id,
                    "target_casting": target["casting"],
                    "target_casting_id": target_id,
                    "target_casting_uuid": target["casting_uuid"],
                }
            )
        else:
            if target_id is not None:
                raise ValueError(f"{family_id}: hold unexpectedly has a target")
            hold_exclusions.append(
                {
                    **common,
                    "identity_status": "held_not_materialized",
                    "retrieval_eligible": False,
                    "review_family_id": family_id,
                    "source_row_count": len(releases),
                }
            )

    if seen_source_ids != set(staging_by_id):
        raise ValueError("queue source coverage differs from staging dataset")
    counts = {
        "new_family_count": len(new_families),
        "merge_link_count": len(merge_links),
        "hold_exclusion_count": len(hold_exclusions),
        "new_family_source_row_count": sum(
            len(item["held_release_references"]) for item in new_families
        ),
        "merge_source_row_count": sum(
            len(item["held_release_references"]) for item in merge_links
        ),
        "hold_source_row_count": sum(
            len(item["held_release_references"]) for item in hold_exclusions
        ),
        "held_release_reference_count": len(seen_source_ids),
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"materialization accounting differs from contract: {counts}")
    expected_summary = {
        "accepted_new_casting_families": counts["new_family_count"],
        "accepted_family_merges": counts["merge_link_count"],
        "held_family_decisions": counts["hold_exclusion_count"],
        "held_release_variants": counts["held_release_reference_count"],
        "promotion_eligible_families": 0,
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise ValueError("final queue summary differs from materialized accounting")
    if any(queue_manifest.get(key) != value for key, value in expected_summary.items()):
        raise ValueError("final queue manifest differs from materialized accounting")

    registry = {
        "schema_version": SCHEMA_VERSION,
        "registry_version": REGISTRY_VERSION,
        "status": "review_family_only",
        "identity_namespace": IDENTITY_NAMESPACE,
        "source": source,
        "eligible_for": ["family_review", "future_human_knowledge_index"],
        "excluded_from": [
            "runtime_retrieval",
            "canonical_variant_response",
            "canonical_resolution_accuracy",
            "calibration_training",
            "threshold_selection",
            "postgresql_ingestion",
        ],
        "new_families": new_families,
        "merge_links": merge_links,
        "hold_exclusions": hold_exclusions,
    }
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "registry_version": REGISTRY_VERSION,
        "identity_namespace": IDENTITY_NAMESPACE,
        "inputs": {
            "final_queue": _file_reference(queue_path),
            "final_queue_manifest": _file_reference(queue_manifest_path),
            "staging_dataset": _file_reference(staging_path),
            "staging_manifest": _file_reference(staging_manifest_path),
            "human_backed_catalog": _file_reference(human_path),
            "human_backed_catalog_manifest": _file_reference(human_manifest_path),
        },
        **counts,
        "provisional_variant_count": 0,
        "canonical_promotion_count": 0,
        "runtime_indexed_family_count": 0,
        "postgresql_row_count": 0,
    }
    return registry, manifest, build_report(registry, counts)


def _markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def build_report(registry: dict[str, Any], counts: dict[str, int]) -> str:
    lines = [
        "# Review-Family Materialization",
        "",
        "> Family decisions are materialized for review only. No release variant, canonical",
        "> identity, runtime candidate, or PostgreSQL row is created.",
        "",
        "## Accounting",
        "",
        "| State | Families | Held release references |",
        "|---|---:|---:|",
        f"| New review families | `{counts['new_family_count']}` | `{counts['new_family_source_row_count']}` |",
        f"| Existing-family merge links | `{counts['merge_link_count']}` | `{counts['merge_source_row_count']}` |",
        f"| Hold exclusions | `{counts['hold_exclusion_count']}` | `{counts['hold_source_row_count']}` |",
        f"| **Total** | `53` | `{counts['held_release_reference_count']}` |",
        "",
        "## New review families",
        "",
        "| Display name | Review family ID | UUID | Release references |",
        "|---|---|---|---:|",
    ]
    for family in registry["new_families"]:
        lines.append(
            f"| {_markdown(family['display_name'])} | `{family['review_family_id']}` | "
            f"`{family['review_family_uuid']}` | `{len(family['held_release_references'])}` |"
        )
    lines.extend(
        [
            "",
            "## Existing-family merge links",
            "",
            "| Source family | Existing human family | Release references |",
            "|---|---|---:|",
        ]
    )
    for link in registry["merge_links"]:
        lines.append(
            f"| {_markdown(link['display_name'])} | `{link['target_casting_id']}` | "
            f"`{len(link['held_release_references'])}` |"
        )
    lines.extend(
        [
            "",
            "## Hold exclusions",
            "",
            "| Family | Reason | Release references |",
            "|---|---|---:|",
        ]
    )
    for hold in registry["hold_exclusions"]:
        lines.append(
            f"| {_markdown(hold['display_name'])} | "
            f"{_markdown(hold['decision']['reason'])} | `{hold['source_row_count']}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Every source row remains `held_for_variant_review`. The registry is explicitly",
            "excluded from runtime retrieval, PostgreSQL ingestion, canonical responses, accuracy",
            "evaluation, calibration training, and threshold selection.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_outputs(
    registry: dict[str, Any],
    manifest: dict[str, Any],
    report: str,
    *,
    registry_file_name: str = "review_family_registry.json",
    report_file_name: str = "review-family-materialization.md",
) -> tuple[str, str, str]:
    registry_text = _stable_json(registry)
    frozen_manifest = dict(manifest)
    frozen_manifest["registry_file"] = registry_file_name
    frozen_manifest["registry_sha256"] = hashlib.sha256(
        registry_text.encode("utf-8")
    ).hexdigest()
    frozen_manifest["report_file"] = report_file_name
    frozen_manifest["report_sha256"] = hashlib.sha256(
        report.encode("utf-8")
    ).hexdigest()
    return registry_text, _stable_json(frozen_manifest), report


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
        description="Build or verify the review-only family registry"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--queue",
        type=Path,
        default=PILOT / "priority-2-batch-05-adjudicated-queue.json",
    )
    parser.add_argument(
        "--queue-manifest",
        type=Path,
        default=PILOT / "priority-2-batch-05-adjudicated-queue-manifest.json",
    )
    parser.add_argument("--staging", type=Path, default=PILOT / "normalized.json")
    parser.add_argument(
        "--staging-manifest", type=Path, default=PILOT / "manifest.json"
    )
    parser.add_argument(
        "--human-catalog", type=Path, default=ROOT / "data" / "human_backed_catalog.json"
    )
    parser.add_argument(
        "--human-manifest",
        type=Path,
        default=ROOT / "data" / "human_backed_catalog_manifest.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data" / "review_family_registry.json"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "review_family_registry_manifest.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports" / "review-family-materialization.md",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        built = build_registry(
            arguments.queue,
            arguments.queue_manifest,
            arguments.staging,
            arguments.staging_manifest,
            arguments.human_catalog,
            arguments.human_manifest,
        )
        expected = expected_outputs(
            *built,
            registry_file_name=arguments.output.name,
            report_file_name=arguments.report.name,
        )
        paths = (arguments.output, arguments.manifest, arguments.report)
        input_paths = (
            arguments.queue,
            arguments.queue_manifest,
            arguments.staging,
            arguments.staging_manifest,
            arguments.human_catalog,
            arguments.human_manifest,
        )
        resolved_outputs = {path.resolve() for path in paths}
        if len(resolved_outputs) != len(paths):
            raise ValueError("review-family output paths must be distinct")
        if resolved_outputs & {path.resolve() for path in input_paths}:
            raise ValueError("review-family output paths must not overwrite inputs")
        if arguments.check:
            if any(not path.is_file() for path in paths):
                raise ValueError("review-family registry outputs are missing")
            actual = tuple(path.read_text(encoding="utf-8") for path in paths)
            if actual != expected:
                raise ValueError("review-family registry outputs are stale")
            counts = built[1]
            print(
                "verified review-family registry: "
                f"{counts['new_family_count']} new, "
                f"{counts['merge_link_count']} merged, "
                f"{counts['hold_exclusion_count']} held; variants=0"
            )
            return 0
        _write_atomically(list(zip(paths, expected, strict=True)))
        counts = built[1]
        print(
            "built review-family registry: "
            f"{counts['new_family_count']} new, "
            f"{counts['merge_link_count']} merged, "
            f"{counts['hold_exclusion_count']} held; variants=0"
        )
        return 0
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
