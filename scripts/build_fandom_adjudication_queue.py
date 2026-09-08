#!/usr/bin/env python3
"""Group the Fandom row review into a human-adjudication queue."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCHEMA_VERSION = "pvr-fandom-adjudication-queue-v1"
QUEUE_VERSION = "fandom-2025-pilot-adjudication-queue-v1"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _family_id(brand_key: str, casting_key: str) -> str:
    digest = hashlib.sha256(f"{brand_key}|{casting_key}".encode()).hexdigest()[:16]
    return f"fandom-family-{digest}"


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def build_queue(
    review_path: Path,
    review_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    review = _load(review_path)
    review_manifest = _load(review_manifest_path)
    rows = review.get("reviews")
    if not isinstance(rows, list) or not rows:
        raise ValueError("review input must contain non-empty reviews[]")
    if review_manifest.get("review_sha256") != hashlib.sha256(
        review_path.read_bytes()
    ).hexdigest():
        raise ValueError("review checksum differs from its manifest")
    if review_manifest.get("review_row_count") != len(rows):
        raise ValueError("review row count differs from its manifest")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    seen_record_ids: set[str] = set()
    for row in rows:
        record_id = row.get("source_record_id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("review row has no source record ID")
        if record_id in seen_record_ids:
            raise ValueError(f"duplicate source record ID: {record_id}")
        seen_record_ids.add(record_id)
        if row.get("promotion_eligible") is not False:
            raise ValueError("pre-review row is unexpectedly promotion eligible")
        if row.get("promotion_decision") != "hold_for_human_review":
            raise ValueError("pre-review row is not held for human review")
        family_key = row.get("normalized_family_key")
        if not isinstance(family_key, dict):
            raise ValueError("review row has no normalized family key")
        key = (family_key.get("brand"), family_key.get("casting"))
        if not all(isinstance(value, str) and value for value in key):
            raise ValueError("review row has an invalid normalized family key")
        grouped.setdefault(key, []).append(row)

    families: list[dict[str, Any]] = []
    for key, family_rows in grouped.items():
        statuses = {row["match_status"] for row in family_rows}
        if len(statuses) != 1:
            raise ValueError("one family has inconsistent row match statuses")
        match_status = statuses.pop()
        canonical_candidates = sorted(
            {
                candidate
                for row in family_rows
                for candidate in row["canonical_family_candidate_ids"]
            }
        )
        human_casting_candidates = sorted(
            {
                candidate
                for row in family_rows
                for candidate in row["human_casting_candidate_ids"]
            }
        )
        human_variant_candidates = sorted(
            {
                candidate
                for row in family_rows
                for candidate in row["human_variant_candidate_ids"]
            }
        )
        has_existing_candidate = bool(canonical_candidates or human_casting_candidates)
        priority = 1 if has_existing_candidate else 2
        suggested_action = (
            "merge_existing_family_candidate"
            if has_existing_candidate
            else "research_possible_new_casting_family"
        )
        suggested_reason = (
            "exact normalized family candidate exists; verify release-level differences"
            if has_existing_candidate
            else "no exact family candidate exists; confirm name and casting before creation"
        )
        ordered_rows = sorted(family_rows, key=lambda item: item["source_row"])
        families.append(
            {
                "family_review_id": _family_id(*key),
                "priority": priority,
                "brand": ordered_rows[0]["brand"],
                "casting_name": ordered_rows[0]["casting_name"],
                "normalized_family_key": {"brand": key[0], "casting": key[1]},
                "source_row_count": len(ordered_rows),
                "source_rows": [
                    {
                        "source_record_id": row["source_record_id"],
                        "source_row": row["source_row"],
                        "toy_number": row["toy_number"],
                        "collector_number": row["collector_number"],
                        "release_year": row["release_year"],
                        "series": row["series"],
                        "variant_note": row["variant_note"],
                    }
                    for row in ordered_rows
                ],
                "pre_review": {
                    "match_status": match_status,
                    "canonical_family_candidate_ids": canonical_candidates,
                    "human_casting_candidate_ids": human_casting_candidates,
                    "human_variant_candidate_ids": human_variant_candidates,
                    "suggested_action": suggested_action,
                    "suggested_reason": suggested_reason,
                },
                "reviewer_decision": {
                    "status": "pending",
                    "decision": None,
                    "target_family_id": None,
                    "reason": None,
                    "decided_by": None,
                    "decided_at": None,
                    "evidence_references": [],
                },
                "promotion_eligible": False,
            }
        )

    families.sort(
        key=lambda item: (
            item["priority"],
            item["normalized_family_key"]["casting"],
            item["family_review_id"],
        )
    )
    priority_counts = Counter(item["priority"] for item in families)
    queue = {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "queue_version": QUEUE_VERSION,
        "status": "awaiting_human_adjudication",
        "source_review_version": review.get("review_version"),
        "decision_contract": {
            "allowed_decisions": [
                "merge_existing_family",
                "create_new_casting",
                "hold",
                "reject",
            ],
            "merge_existing_family": (
                "requires target_family_id from an exact candidate and a written reason"
            ),
            "create_new_casting": (
                "requires independent source confirmation and a written reason"
            ),
            "hold": "requires a written reason describing missing evidence",
            "reject": "requires a written reason describing duplication or invalid source data",
            "completed_decision_requires": [
                "decided_by",
                "decided_at",
                "reason",
                "evidence_references",
            ],
            "pending_items_are_promotion_eligible": False,
        },
        "summary": {
            "source_row_count": len(rows),
            "family_count": len(families),
            "priority_1_existing_candidate_families": priority_counts[1],
            "priority_2_possible_new_families": priority_counts[2],
            "completed_decisions": 0,
            "pending_decisions": len(families),
            "promotion_eligible_families": 0,
        },
        "families": families,
    }
    markdown = build_markdown(queue)
    manifest = {
        "schema_version": "pvr-fandom-adjudication-queue-manifest-v1",
        "queue_version": QUEUE_VERSION,
        "inputs": {
            "review": {
                "file": review_path.name,
                "sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
            },
            "review_manifest": {
                "file": review_manifest_path.name,
                "sha256": hashlib.sha256(
                    review_manifest_path.read_bytes()
                ).hexdigest(),
            },
        },
        **queue["summary"],
    }
    return queue, manifest, markdown


def build_markdown(queue: dict[str, Any]) -> str:
    summary = queue["summary"]
    lines = [
        "# Fandom 2025 Pilot — Human Adjudication Queue",
        "",
        "> This is a review worksheet, not a promotion file. All decisions are pending, and no",
        "> family is eligible for canonical or PostgreSQL ingestion.",
        "",
        "## Queue summary",
        "",
        "| Item | Count |",
        "|---|---:|",
        f"| Source rows | `{summary['source_row_count']}` |",
        f"| Distinct casting families | `{summary['family_count']}` |",
        (
            "| Priority 1: exact existing-family candidate | "
            f"`{summary['priority_1_existing_candidate_families']}` |"
        ),
        (
            "| Priority 2: possible new family, research required | "
            f"`{summary['priority_2_possible_new_families']}` |"
        ),
        f"| Completed decisions | `{summary['completed_decisions']}` |",
        f"| Promotion-eligible families | `{summary['promotion_eligible_families']}` |",
        "",
        "Allowed reviewer decisions are `merge_existing_family`, `create_new_casting`, `hold`,",
        "and `reject`. A real decision must record reviewer, timestamp, reason, and supporting",
        "evidence. Suggested actions below are machine pre-review only.",
        "",
        "## Priority 1 — exact existing-family candidates",
        "",
        "| Family | Wiki rows | Existing candidate | Suggested action | Decision |",
        "|---|---:|---|---|---|",
    ]
    priority_one = [item for item in queue["families"] if item["priority"] == 1]
    for item in priority_one:
        candidates = item["pre_review"]["canonical_family_candidate_ids"] + item[
            "pre_review"
        ]["human_casting_candidate_ids"]
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_escape(item["casting_name"]),
                    str(item["source_row_count"]),
                    _markdown_escape(", ".join(candidates)),
                    item["pre_review"]["suggested_action"],
                    "pending",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Priority 2 — possible new families requiring research",
            "",
            "| Family | Wiki rows | Suggested action | Decision |",
            "|---|---:|---|---|",
        ]
    )
    priority_two = [item for item in queue["families"] if item["priority"] == 2]
    for item in priority_two:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_escape(item["casting_name"]),
                    str(item["source_row_count"]),
                    item["pre_review"]["suggested_action"],
                    "pending",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Review boundary",
            "",
            "A family-level merge does not establish a release variant. Color, series, edition,",
            "rarity, and toy-number identity must be reviewed separately. Do not ingest this queue",
            "directly; only a later validated promotion artifact may write canonical records.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_outputs(
    queue: dict[str, Any],
    manifest: dict[str, Any],
    markdown: str,
    *,
    queue_file_name: str = "adjudication-queue.json",
    worksheet_file_name: str = "adjudication-queue.md",
) -> tuple[str, str, str]:
    queue_text = _stable_json(queue)
    frozen_manifest = dict(manifest)
    frozen_manifest["queue_file"] = queue_file_name
    frozen_manifest["queue_sha256"] = hashlib.sha256(
        queue_text.encode("utf-8")
    ).hexdigest()
    frozen_manifest["worksheet_file"] = worksheet_file_name
    frozen_manifest["worksheet_sha256"] = hashlib.sha256(
        markdown.encode("utf-8")
    ).hexdigest()
    return queue_text, _stable_json(frozen_manifest), markdown


def parse_args() -> argparse.Namespace:
    directory = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
    parser = argparse.ArgumentParser(
        description="Build or verify the grouped Fandom human-adjudication queue"
    )
    parser.add_argument("--review", type=Path, default=directory / "review.json")
    parser.add_argument(
        "--review-manifest", type=Path, default=directory / "review-manifest.json"
    )
    parser.add_argument(
        "--output", type=Path, default=directory / "adjudication-queue.json"
    )
    parser.add_argument(
        "--worksheet", type=Path, default=directory / "adjudication-queue.md"
    )
    parser.add_argument(
        "--manifest", type=Path, default=directory / "adjudication-queue-manifest.json"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare checked-in outputs with a fresh in-memory build without writing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue, manifest, markdown = build_queue(args.review, args.review_manifest)
    queue_text, manifest_text, worksheet_text = expected_outputs(
        queue,
        manifest,
        markdown,
        queue_file_name=args.output.name,
        worksheet_file_name=args.worksheet.name,
    )
    if args.check:
        comparisons = (
            (args.output, queue_text),
            (args.manifest, manifest_text),
            (args.worksheet, worksheet_text),
        )
        for path, expected in comparisons:
            if path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"{path.name} differs from a deterministic rebuild")
        status = "verified"
    else:
        for path in (args.output, args.manifest, args.worksheet):
            path.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(queue_text, encoding="utf-8")
        args.manifest.write_text(manifest_text, encoding="utf-8")
        args.worksheet.write_text(worksheet_text, encoding="utf-8")
        status = "built"
    summary = queue["summary"]
    print(
        f"{status} {summary['family_count']} pending family decisions from "
        f"{summary['source_row_count']} rows; promotion eligible=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
