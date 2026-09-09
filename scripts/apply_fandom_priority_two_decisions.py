#!/usr/bin/env python3
"""Validate and apply a source-backed priority-two family-decision batch."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT_SCHEMA_VERSION = "pvr-fandom-priority-two-adjudicated-queue-v1"
RESULT_VERSION = "fandom-2025-priority-two-batch-01-adjudicated-v1"
DECISION_SCHEMA_VERSION = "pvr-fandom-family-decisions-v1"
ALLOWED_OUTCOMES = {"create_new_casting", "hold"}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _file_reference(path: Path) -> dict[str, str]:
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_batch(decisions: dict[str, Any]) -> None:
    if decisions.get("schema_version") != DECISION_SCHEMA_VERSION:
        raise ValueError("decision file has an unsupported schema")
    if not isinstance(decisions.get("batch_id"), str) or not decisions["batch_id"]:
        raise ValueError("decision batch requires a batch ID")
    if not isinstance(decisions.get("decided_by"), str) or not decisions["decided_by"]:
        raise ValueError("decision batch requires decided_by")
    if not _valid_timestamp(decisions.get("decided_at")):
        raise ValueError("decision batch requires an ISO-8601 UTC decided_at")
    provenance = decisions.get("decision_provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("decision batch requires provenance")
    items = decisions.get("decisions")
    if not isinstance(items, list) or not items:
        raise ValueError("decision batch requires decisions[]")


def _validate_decision(
    decision: dict[str, Any],
    family: dict[str, Any],
    research: dict[str, Any],
    research_file_name: str,
) -> None:
    outcome = decision.get("decision")
    recommendation = research["machine_recommendation"]["family_decision"]
    if outcome not in ALLOWED_OUTCOMES:
        raise ValueError("priority-two batch outcome is not permitted")
    if outcome != recommendation:
        raise ValueError("decision differs from the approved research recommendation")
    if decision.get("scope") != "casting_family_only":
        raise ValueError("priority-two decisions only permit casting-family scope")
    if decision.get("variant_decision") != "hold":
        raise ValueError("release variants must remain held")
    if decision.get("target_family_id") is not None:
        raise ValueError("create/hold decisions cannot target an existing family")
    if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
        raise ValueError("completed decision requires a written reason")
    references = decision.get("evidence_references")
    expected_packet = research_file_name + "#" + family["family_review_id"]
    if not isinstance(references, list) or expected_packet not in references:
        raise ValueError("completed decision must reference its research packet")
    if not all(isinstance(reference, str) and reference.strip() for reference in references):
        raise ValueError("completed decision has an invalid evidence reference")
    if family["priority"] != 2 or family["reviewer_decision"]["status"] != "pending":
        raise ValueError("decision does not target a pending priority-two family")
    if outcome == "create_new_casting":
        evidence = research["research_evidence"]
        if evidence["wiki_casting_page"]["page_classification"] != "single_casting":
            raise ValueError("new casting requires a dedicated casting page")
        if evidence["independent_source_count"] < 1:
            raise ValueError("new casting requires independent exact-name evidence")
        if len(evidence["distinct_source_hosts"]) < 2:
            raise ValueError("new casting evidence must span at least two hosts")
        if family["pre_review"]["canonical_family_candidate_ids"]:
            raise ValueError("new casting conflicts with an existing canonical family")
        if family["pre_review"]["human_casting_candidate_ids"]:
            raise ValueError("new casting conflicts with an existing human family")


def apply_priority_two_decisions(
    adjudicated_queue_path: Path,
    adjudicated_manifest_path: Path,
    research_path: Path,
    research_manifest_path: Path,
    decisions_path: Path,
    *,
    result_version: str = RESULT_VERSION,
    batch_label: str = "01",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    queue = _load(adjudicated_queue_path)
    queue_manifest = _load(adjudicated_manifest_path)
    research = _load(research_path)
    research_manifest = _load(research_manifest_path)
    decisions = _load(decisions_path)
    if queue_manifest.get("result_sha256") != hashlib.sha256(
        adjudicated_queue_path.read_bytes()
    ).hexdigest():
        raise ValueError("adjudicated queue checksum differs from its manifest")
    if research_manifest.get("research_sha256") != hashlib.sha256(
        research_path.read_bytes()
    ).hexdigest():
        raise ValueError("research checksum differs from its manifest")
    if research.get("status") != "awaiting_reviewer_confirmation":
        raise ValueError("research packet is not awaiting reviewer confirmation")
    _validate_batch(decisions)

    result = copy.deepcopy(queue)
    result["schema_version"] = RESULT_SCHEMA_VERSION
    result["queue_version"] = result_version
    result["status"] = "partially_adjudicated"
    families = result.get("families")
    packets = research.get("packets")
    if not isinstance(families, list) or not isinstance(packets, list):
        raise ValueError("queue and research must contain family/packet arrays")
    families_by_id = {family["family_review_id"]: family for family in families}
    packets_by_id = {packet["family_review_id"]: packet for packet in packets}
    if len(packets_by_id) != len(packets):
        raise ValueError("research packet contains duplicate family IDs")

    decision_items = decisions["decisions"]
    decision_ids = [item.get("family_review_id") for item in decision_items]
    if len(set(decision_ids)) != len(decision_ids):
        raise ValueError("decision family IDs are missing or duplicated")
    if set(decision_ids) != set(packets_by_id):
        raise ValueError("decision batch must cover every research packet exactly once")

    for decision in decision_items:
        family_id = decision["family_review_id"]
        family = families_by_id.get(family_id)
        packet = packets_by_id[family_id]
        if family is None:
            raise ValueError("decision references an unknown family")
        if family["casting_name"] != packet["casting_name"]:
            raise ValueError("research packet name differs from the queue")
        _validate_decision(decision, family, packet, research_path.name)
        family["reviewer_decision"] = {
            "status": "completed",
            "decision": decision["decision"],
            "target_family_id": None,
            "scope": decision["scope"],
            "variant_decision": decision["variant_decision"],
            "reason": decision["reason"],
            "decided_by": decisions["decided_by"],
            "decided_at": decisions["decided_at"],
            "evidence_references": decision["evidence_references"],
            "decision_batch_id": decisions["batch_id"],
        }
        family["promotion_eligible"] = False

    completed = [
        family
        for family in families
        if family["reviewer_decision"]["status"] == "completed"
    ]
    pending = [
        family
        for family in families
        if family["reviewer_decision"]["status"] == "pending"
    ]
    result["status"] = "adjudicated" if not pending else "partially_adjudicated"
    result["summary"] = {
        **result["summary"],
        "completed_decisions": len(completed),
        "pending_decisions": len(pending),
        "accepted_family_merges": sum(
            family["reviewer_decision"]["decision"] == "merge_existing_family"
            for family in completed
        ),
        "accepted_new_casting_families": sum(
            family["reviewer_decision"]["decision"] == "create_new_casting"
            for family in completed
        ),
        "held_family_decisions": sum(
            family["reviewer_decision"]["decision"] == "hold"
            for family in completed
        ),
        "held_release_variants": sum(family["source_row_count"] for family in completed),
        "promotion_eligible_families": 0,
    }
    previous_batch = result.pop("decision_batch", None)
    previous_batches = result.pop("decision_batches", [])
    if not isinstance(previous_batches, list):
        raise ValueError("prior decision batch history must be a list")
    batch_history = [
        *previous_batches,
        *([previous_batch] if isinstance(previous_batch, dict) else []),
    ]
    if not all(isinstance(item, dict) for item in batch_history):
        raise ValueError("prior decision batch history contains an invalid item")
    if decisions["batch_id"] in {
        item.get("batch_id") for item in batch_history
    }:
        raise ValueError("decision batch ID already exists in prior history")
    current_batch = {
        "batch_id": decisions["batch_id"],
        "decided_by": decisions["decided_by"],
        "decided_at": decisions["decided_at"],
        "decision_provenance": decisions["decision_provenance"],
        "decision_file_sha256": hashlib.sha256(decisions_path.read_bytes()).hexdigest(),
    }
    result["decision_batches"] = [
        *batch_history,
        current_batch,
    ]
    manifest = {
        "schema_version": "pvr-fandom-priority-two-adjudicated-manifest-v1",
        "result_version": result_version,
        "inputs": {
            "adjudicated_queue": _file_reference(adjudicated_queue_path),
            "adjudicated_queue_manifest": _file_reference(adjudicated_manifest_path),
            "research": _file_reference(research_path),
            "research_manifest": _file_reference(research_manifest_path),
            "decisions": _file_reference(decisions_path),
        },
        **result["summary"],
    }
    return result, manifest, build_markdown(
        result,
        decisions["batch_id"],
        batch_label=batch_label,
    )


def build_markdown(
    result: dict[str, Any],
    batch_id: str,
    *,
    batch_label: str = "01",
) -> str:
    summary = result["summary"]
    current = [
        family
        for family in result["families"]
        if family["reviewer_decision"].get("decision_batch_id") == batch_id
    ]
    if batch_label == "03":
        overview_lines = [
            "> Ten casting families are accepted as new review-layer families. Every release",
            "> variant stays held; canonical and PostgreSQL data remain unchanged.",
        ]
    elif batch_label == "04":
        overview_lines = [
            "> Eight casting families are accepted as new review-layer families and two same-name",
            "> tool ambiguities remain held. Every release variant stays held; canonical and",
            "> PostgreSQL data remain unchanged.",
        ]
    elif batch_label == "05":
        overview_lines = [
            "> Six casting families are accepted as new review-layer families and three identity",
            "> conflicts remain held. The 53-family queue is fully adjudicated, but every release",
            "> variant stays held; canonical and PostgreSQL data remain unchanged.",
        ]
    else:
        overview_lines = [
            "> Nine casting families are accepted as new review-layer families and one ambiguous",
            "> name remains held. Every release variant stays held; canonical and PostgreSQL data",
            "> remain unchanged.",
        ]
    lines = [
        f"# Priority 2 Batch {batch_label} — Adjudication Result",
        "",
        *overview_lines,
        "",
        "## Cumulative queue state",
        "",
        "| State | Count |",
        "|---|---:|",
        f"| Completed family decisions | `{summary['completed_decisions']}` |",
        f"| Accepted existing-family merges | `{summary['accepted_family_merges']}` |",
        f"| Accepted new casting families | `{summary['accepted_new_casting_families']}` |",
        f"| Held family decisions | `{summary['held_family_decisions']}` |",
        f"| Pending family decisions | `{summary['pending_decisions']}` |",
        f"| Held Wiki release variants | `{summary['held_release_variants']}` |",
        f"| Promotion-eligible families | `{summary['promotion_eligible_families']}` |",
        "",
        f"## Batch {batch_label} decisions",
        "",
        "| Casting family | Family decision | Scope | Variant state | Reviewer | Time |",
        "|---|---|---|---|---|---|",
    ]
    for family in current:
        decision = family["reviewer_decision"]
        lines.append(
            "| "
            + " | ".join(
                [
                    family["casting_name"],
                    decision["decision"],
                    decision["scope"],
                    decision["variant_decision"],
                    decision["decided_by"],
                    decision["decided_at"],
                ]
            )
            + " |"
        )
    if batch_label == "01":
        hold_lines = [
            "UUID, no verified release/color identity, and no PostgreSQL row. `'55 Chevy` remains",
            "held until the 2025 rows can be linked to one of its distinct casting tools.",
        ]
        new_family_count = "nine"
    elif batch_label == "02":
        hold_lines = [
            "UUID, no verified release/color identity, and no PostgreSQL row. `Batman and Robin",
            "Batmobile` remains held until HYW60/HYX61 can be linked to one specific casting tool.",
        ]
        new_family_count = "nine"
    elif batch_label == "03":
        hold_lines = [
            "UUID, no verified release/color identity, and no PostgreSQL row. Batch 03 has no",
            "family-level hold, but all eighteen release variants remain held.",
        ]
        new_family_count = "ten"
    elif batch_label == "04":
        hold_lines = [
            "UUID, no verified release/color identity, and no PostgreSQL row. Mazda MX-5 Miata",
            "and Nissan Skyline 2000GT-R LBWK remain held until their 2025 rows can be linked to",
            "one tool-specific family without relying on their shared display names.",
        ]
        new_family_count = "eight"
    else:
        hold_lines = [
            "UUID, no verified release/color identity, and no PostgreSQL row. Nissan Skyline GT-R",
            "(BNR32), Power Wheels Dune Racer, and Standard Kart remain held for same-scale-tool,",
            "renamed-lineage, and multi-tool-page conflicts respectively.",
        ]
        new_family_count = "six"
    lines.extend(
        [
            "",
            f"The {new_family_count} new families exist only as accepted review decisions. They have no canonical",
            *hold_lines,
            "",
        ]
    )
    return "\n".join(lines)


def expected_outputs(
    result: dict[str, Any],
    manifest: dict[str, Any],
    markdown: str,
    *,
    result_file_name: str = "priority-2-batch-01-adjudicated-queue.json",
    report_file_name: str = "priority-2-batch-01-adjudication-result.md",
) -> tuple[str, str, str]:
    result_text = _stable_json(result)
    frozen_manifest = dict(manifest)
    frozen_manifest["result_file"] = result_file_name
    frozen_manifest["result_sha256"] = hashlib.sha256(
        result_text.encode("utf-8")
    ).hexdigest()
    frozen_manifest["report_file"] = report_file_name
    frozen_manifest["report_sha256"] = hashlib.sha256(
        markdown.encode("utf-8")
    ).hexdigest()
    return result_text, _stable_json(frozen_manifest), markdown


def main() -> None:
    directory = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
    parser = argparse.ArgumentParser(
        description="Apply or verify a priority-two family-decision batch"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--batch", choices=("1", "2", "3", "4", "5"), default="1")
    parser.add_argument("--directory", type=Path, default=directory)
    arguments = parser.parse_args()
    output = arguments.directory
    if arguments.batch == "1":
        batch_label = "01"
        result_version = RESULT_VERSION
        queue_prefix = ""
    elif arguments.batch == "2":
        batch_label = "02"
        result_version = "fandom-2025-priority-two-batch-02-adjudicated-v1"
        queue_prefix = "priority-2-batch-01-"
    elif arguments.batch == "3":
        batch_label = "03"
        result_version = "fandom-2025-priority-two-batch-03-adjudicated-v1"
        queue_prefix = "priority-2-batch-02-"
    elif arguments.batch == "4":
        batch_label = "04"
        result_version = "fandom-2025-priority-two-batch-04-adjudicated-v1"
        queue_prefix = "priority-2-batch-03-"
    else:
        batch_label = "05"
        result_version = "fandom-2025-priority-two-batch-05-adjudicated-v1"
        queue_prefix = "priority-2-batch-04-"
    prefix = f"priority-2-batch-{batch_label}"
    built = apply_priority_two_decisions(
        output / f"{queue_prefix}adjudicated-queue.json",
        output / f"{queue_prefix}adjudicated-queue-manifest.json",
        output / f"{prefix}-research.json",
        output / f"{prefix}-research-manifest.json",
        output / f"{prefix}-decisions.json",
        result_version=result_version,
        batch_label=batch_label,
    )
    expected = expected_outputs(
        *built,
        result_file_name=f"{prefix}-adjudicated-queue.json",
        report_file_name=f"{prefix}-adjudication-result.md",
    )
    paths = (
        output / f"{prefix}-adjudicated-queue.json",
        output / f"{prefix}-adjudicated-queue-manifest.json",
        output / f"{prefix}-adjudication-result.md",
    )
    if arguments.check:
        if any(not path.exists() for path in paths):
            raise ValueError("priority-two adjudication outputs are missing")
        actual = tuple(path.read_text(encoding="utf-8") for path in paths)
        if actual != expected:
            raise ValueError("priority-two adjudication outputs are stale")
        summary = built[0]["summary"]
        print(
            f"verified {summary['completed_decisions']} completed family decisions; "
            f"{summary['pending_decisions']} pending; promotion eligible=0"
        )
        return
    output.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, expected, strict=True):
        path.write_text(content, encoding="utf-8")
    print(_stable_json(built[0]["summary"]), end="")


if __name__ == "__main__":
    main()
