#!/usr/bin/env python3
"""Validate and apply attributable family decisions without promoting variants."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT_SCHEMA_VERSION = "pvr-fandom-adjudicated-queue-v1"
RESULT_VERSION = "fandom-2025-pilot-adjudicated-queue-v1"
ALLOWED_DECISIONS = {
    "merge_existing_family",
    "create_new_casting",
    "hold",
    "reject",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_batch_header(decisions: dict[str, Any]) -> None:
    if decisions.get("schema_version") != "pvr-fandom-family-decisions-v1":
        raise ValueError("decision file has an unsupported schema")
    if not isinstance(decisions.get("batch_id"), str) or not decisions["batch_id"]:
        raise ValueError("decision batch requires a batch ID")
    if not isinstance(decisions.get("decided_by"), str) or not decisions["decided_by"]:
        raise ValueError("decision batch requires decided_by")
    if not _valid_timestamp(decisions.get("decided_at")):
        raise ValueError("decision batch requires an ISO-8601 UTC decided_at")
    if not isinstance(decisions.get("decision_provenance"), str) or not decisions[
        "decision_provenance"
    ].strip():
        raise ValueError("decision batch requires provenance")
    if not isinstance(decisions.get("decisions"), list) or not decisions["decisions"]:
        raise ValueError("decision batch requires decisions[]")


def _validate_decision(
    decision: dict[str, Any],
    family: dict[str, Any],
) -> None:
    outcome = decision.get("decision")
    if outcome not in ALLOWED_DECISIONS:
        raise ValueError("decision outcome is not permitted")
    if decision.get("scope") != "casting_family_only":
        raise ValueError("this decision batch only permits casting-family scope")
    if decision.get("variant_decision") != "hold":
        raise ValueError("release variants must remain held")
    if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
        raise ValueError("completed decision requires a written reason")
    references = decision.get("evidence_references")
    if not isinstance(references, list) or not references or not all(
        isinstance(reference, str) and reference.strip() for reference in references
    ):
        raise ValueError("completed decision requires evidence references")
    target = decision.get("target_family_id")
    exact_candidates = (
        family["pre_review"]["canonical_family_candidate_ids"]
        + family["pre_review"]["human_casting_candidate_ids"]
    )
    if outcome == "merge_existing_family" and target not in exact_candidates:
        raise ValueError("merge target is not an exact pre-review candidate")
    if outcome != "merge_existing_family" and target is not None:
        raise ValueError("only a merge decision may specify a target family")


def apply_decisions(
    queue_path: Path,
    queue_manifest_path: Path,
    evidence_path: Path,
    evidence_manifest_path: Path,
    decisions_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    queue = _load(queue_path)
    queue_manifest = _load(queue_manifest_path)
    evidence = _load(evidence_path)
    evidence_manifest = _load(evidence_manifest_path)
    decisions = _load(decisions_path)
    if queue_manifest.get("queue_sha256") != hashlib.sha256(
        queue_path.read_bytes()
    ).hexdigest():
        raise ValueError("queue checksum differs from its manifest")
    if evidence_manifest.get("packet_sha256") != hashlib.sha256(
        evidence_path.read_bytes()
    ).hexdigest():
        raise ValueError("priority-one evidence checksum differs from its manifest")
    _validate_batch_header(decisions)

    result = copy.deepcopy(queue)
    result["schema_version"] = RESULT_SCHEMA_VERSION
    result["queue_version"] = RESULT_VERSION
    result["status"] = "partially_adjudicated"
    families = result.get("families")
    if not isinstance(families, list):
        raise ValueError("queue must contain families[]")
    families_by_id = {family["family_review_id"]: family for family in families}
    evidence_ids = {packet["family_review_id"] for packet in evidence.get("packets", [])}
    seen_decision_ids: set[str] = set()
    for decision in decisions["decisions"]:
        family_id = decision.get("family_review_id")
        if not isinstance(family_id, str) or family_id in seen_decision_ids:
            raise ValueError("decision family ID is missing or duplicated")
        seen_decision_ids.add(family_id)
        family = families_by_id.get(family_id)
        if family is None:
            raise ValueError("decision references an unknown family")
        if family_id not in evidence_ids:
            raise ValueError("decision has no priority-one evidence packet")
        if family["reviewer_decision"]["status"] != "pending":
            raise ValueError("family has already been adjudicated")
        _validate_decision(decision, family)
        family["reviewer_decision"] = {
            "status": "completed",
            "decision": decision["decision"],
            "target_family_id": decision.get("target_family_id"),
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
    result["summary"] = {
        **result["summary"],
        "completed_decisions": len(completed),
        "pending_decisions": len(pending),
        "accepted_family_merges": sum(
            family["reviewer_decision"]["decision"] == "merge_existing_family"
            for family in completed
        ),
        "held_release_variants": sum(
            family["source_row_count"] for family in completed
        ),
        "promotion_eligible_families": 0,
    }
    result["decision_batch"] = {
        "batch_id": decisions["batch_id"],
        "decided_by": decisions["decided_by"],
        "decided_at": decisions["decided_at"],
        "decision_provenance": decisions["decision_provenance"],
        "decision_file_sha256": hashlib.sha256(decisions_path.read_bytes()).hexdigest(),
    }
    manifest = {
        "schema_version": "pvr-fandom-adjudicated-queue-manifest-v1",
        "result_version": RESULT_VERSION,
        "inputs": {
            "queue": _file_reference(queue_path),
            "queue_manifest": _file_reference(queue_manifest_path),
            "priority_one_evidence": _file_reference(evidence_path),
            "priority_one_evidence_manifest": _file_reference(evidence_manifest_path),
            "decisions": _file_reference(decisions_path),
        },
        **result["summary"],
    }
    return result, manifest, build_markdown(result)


def _file_reference(path: Path) -> dict[str, str]:
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    completed = [
        family
        for family in result["families"]
        if family["reviewer_decision"]["status"] == "completed"
    ]
    lines = [
        "# Fandom 2025 Pilot — Adjudication Result",
        "",
        "> Four casting-family relationships are accepted. Release variants remain held, and no",
        "> family is eligible for canonical or PostgreSQL promotion.",
        "",
        "## Summary",
        "",
        "| State | Count |",
        "|---|---:|",
        f"| Completed family decisions | `{summary['completed_decisions']}` |",
        f"| Accepted family merges | `{summary['accepted_family_merges']}` |",
        f"| Pending family decisions | `{summary['pending_decisions']}` |",
        f"| Held Wiki release variants | `{summary['held_release_variants']}` |",
        f"| Promotion-eligible families | `{summary['promotion_eligible_families']}` |",
        "",
        "## Completed decisions",
        "",
        "| Casting family | Decision | Target | Scope | Variant state | Reviewer | Time |",
        "|---|---|---|---|---|---|---|",
    ]
    for family in completed:
        decision = family["reviewer_decision"]
        lines.append(
            "| "
            + " | ".join(
                [
                    family["casting_name"],
                    decision["decision"],
                    decision["target_family_id"],
                    decision["scope"],
                    decision["variant_decision"],
                    decision["decided_by"],
                    decision["decided_at"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "These decisions connect Wiki rows to existing human-backed casting families only.",
            "They do not create canonical UUIDs or validate year, color, series, edition, rarity,",
            "collector number, or toy number identity. The remaining 49 family decisions are",
            "pending and require separate research.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_outputs(
    result: dict[str, Any],
    manifest: dict[str, Any],
    markdown: str,
    *,
    result_file_name: str = "adjudicated-queue.json",
    report_file_name: str = "adjudication-result.md",
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


def parse_args() -> argparse.Namespace:
    directory = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
    parser = argparse.ArgumentParser(
        description="Apply validated family decisions without promoting release variants"
    )
    parser.add_argument("--queue", type=Path, default=directory / "adjudication-queue.json")
    parser.add_argument(
        "--queue-manifest", type=Path, default=directory / "adjudication-queue-manifest.json"
    )
    parser.add_argument(
        "--evidence", type=Path, default=directory / "priority-1-evidence.json"
    )
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        default=directory / "priority-1-evidence-manifest.json",
    )
    parser.add_argument(
        "--decisions", type=Path, default=directory / "priority-1-decisions.json"
    )
    parser.add_argument(
        "--output", type=Path, default=directory / "adjudicated-queue.json"
    )
    parser.add_argument(
        "--report", type=Path, default=directory / "adjudication-result.md"
    )
    parser.add_argument(
        "--manifest", type=Path, default=directory / "adjudicated-queue-manifest.json"
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    built = apply_decisions(
        args.queue,
        args.queue_manifest,
        args.evidence,
        args.evidence_manifest,
        args.decisions,
    )
    result_text, manifest_text, report_text = expected_outputs(
        *built,
        result_file_name=args.output.name,
        report_file_name=args.report.name,
    )
    if args.check:
        for path, expected in (
            (args.output, result_text),
            (args.manifest, manifest_text),
            (args.report, report_text),
        ):
            if path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"{path.name} differs from a deterministic rebuild")
        status = "verified"
    else:
        for path in (args.output, args.manifest, args.report):
            path.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result_text, encoding="utf-8")
        args.manifest.write_text(manifest_text, encoding="utf-8")
        args.report.write_text(report_text, encoding="utf-8")
        status = "built"
    summary = built[0]["summary"]
    print(
        f"{status} {summary['completed_decisions']} completed family decisions; "
        f"{summary['pending_decisions']} pending; promotion eligible=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
