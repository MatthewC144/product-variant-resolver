#!/usr/bin/env python3
"""Build a bounded, source-backed research packet for priority-two families."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "pvr-fandom-priority-two-research-v1"
BATCH_VERSION = "fandom-2025-priority-two-research-batch-01-v1"
SOURCE_SCHEMA_VERSION = "pvr-fandom-priority-two-source-notes-v1"
BATCH_SIZE = 10


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


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("research sources must use an absolute HTTPS URL")
    return parsed.netloc.casefold()


def _validate_source_note(note: dict[str, Any], family: dict[str, Any]) -> None:
    if note.get("family_review_id") != family["family_review_id"]:
        raise ValueError("source notes are not in the selected queue order")
    if note.get("casting_name") != family["casting_name"]:
        raise ValueError("source-note casting name differs from the queue")
    wiki = note.get("wiki_casting_page")
    independent = note.get("independent_sources")
    if not isinstance(wiki, dict) or not isinstance(independent, list):
        raise ValueError("each family requires Wiki and independent source sections")
    if _host(str(wiki.get("url", ""))) != "hotwheels.fandom.com":
        raise ValueError("Wiki casting evidence must come from hotwheels.fandom.com")
    if wiki.get("page_classification") not in {
        "single_casting",
        "disambiguation",
        "homonymous_castings",
    }:
        raise ValueError("Wiki page classification is unsupported")
    if not isinstance(wiki.get("observed_claim"), str) or not wiki["observed_claim"].strip():
        raise ValueError("Wiki evidence requires a concise observed claim")
    related_pages = wiki.get("related_casting_pages", [])
    if not isinstance(related_pages, list):
        raise ValueError("related casting pages must be a list")
    for related in related_pages:
        if not isinstance(related, dict):
            raise ValueError("each related casting page must be an object")
        _host(str(related.get("url", "")))
        if not isinstance(related.get("distinction"), str) or not related[
            "distinction"
        ].strip():
            raise ValueError("related casting evidence requires an explicit distinction")
    if wiki.get("page_classification") == "homonymous_castings" and not related_pages:
        raise ValueError("homonymous casting evidence requires the conflicting tool page")
    if not independent:
        raise ValueError("each family requires at least one independent source")
    for source in independent:
        if _host(str(source.get("url", ""))) == "hotwheels.fandom.com":
            raise ValueError("independent evidence cannot use the Wiki host")
        if source.get("confirms_exact_casting_name") is not True:
            raise ValueError("independent source must confirm the exact casting name")
        if not isinstance(source.get("observed_claim"), str) or not source[
            "observed_claim"
        ].strip():
            raise ValueError("independent evidence requires a concise observed claim")


def build_research(
    adjudicated_queue_path: Path,
    adjudicated_manifest_path: Path,
    source_notes_path: Path,
    *,
    batch_version: str = BATCH_VERSION,
    batch_label: str = "01",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    queue = _load(adjudicated_queue_path)
    queue_manifest = _load(adjudicated_manifest_path)
    source_notes = _load(source_notes_path)
    if queue_manifest.get("result_sha256") != hashlib.sha256(
        adjudicated_queue_path.read_bytes()
    ).hexdigest():
        raise ValueError("adjudicated queue checksum differs from its manifest")
    if source_notes.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise ValueError("source-note file has an unsupported schema")

    families = queue.get("families")
    notes = source_notes.get("families")
    if not isinstance(families, list) or not isinstance(notes, list):
        raise ValueError("queue and source notes must contain families[]")
    selected = [
        family
        for family in families
        if family.get("priority") == 2
        and family.get("reviewer_decision", {}).get("status") == "pending"
    ][:BATCH_SIZE]
    if len(selected) != BATCH_SIZE or len(notes) != BATCH_SIZE:
        raise ValueError(
            f"batch {batch_label} requires exactly {BATCH_SIZE} pending families"
        )

    packets: list[dict[str, Any]] = []
    for family, note in zip(selected, notes, strict=True):
        _validate_source_note(note, family)
        wiki = note["wiki_casting_page"]
        independent = note["independent_sources"]
        page_classification = wiki["page_classification"]
        if page_classification == "single_casting":
            proposed_decision = "create_new_casting"
            decision_reason = (
                "the queue name resolves to one dedicated Wiki casting page and at least one "
                "separate publisher confirms the exact Hot Wheels casting name"
            )
        elif page_classification == "disambiguation":
            proposed_decision = "hold"
            decision_reason = (
                "the queue name resolves to a disambiguation page covering multiple casting "
                "tools, so the 2025 row must be mapped to one lineage before family creation"
            )
        else:
            proposed_decision = "hold"
            decision_reason = (
                "the queued display name is also used by a separate casting tool, so the source "
                "rows need a tool-specific identity before family creation"
            )
        packets.append(
            {
                "family_review_id": family["family_review_id"],
                "brand": family["brand"],
                "casting_name": family["casting_name"],
                "source_row_count": family["source_row_count"],
                "source_rows": family["source_rows"],
                "research_evidence": {
                    "wiki_casting_page": wiki,
                    "independent_sources": independent,
                    "independent_source_count": len(independent),
                    "distinct_source_hosts": sorted(
                        {_host(wiki["url"]), *(_host(item["url"]) for item in independent)}
                    ),
                },
                "machine_recommendation": {
                    "family_decision": proposed_decision,
                    "reason": decision_reason,
                    "scope": "casting_family_only",
                    "variant_decision": "hold",
                },
                "reviewer_confirmation": {
                    "status": "pending",
                    "decided_by": None,
                    "decided_at": None,
                    "reason": None,
                    "evidence_references": [],
                },
                "promotion_eligible": False,
            }
        )

    create_count = sum(
        packet["machine_recommendation"]["family_decision"]
        == "create_new_casting"
        for packet in packets
    )
    hold_count = len(packets) - create_count
    payload = {
        "schema_version": SCHEMA_VERSION,
        "batch_version": batch_version,
        "status": "awaiting_reviewer_confirmation",
        "selection_rule": "first 10 pending priority-2 families in adjudicated queue order",
        "decision_policy": {
            "create_new_casting": (
                "one dedicated Wiki casting page plus at least one non-Fandom publisher that "
                "confirms the exact Hot Wheels casting name"
            ),
            "hold": "ambiguous/disambiguated identity or insufficient independent evidence",
            "variant_boundary": "every release variant remains held",
        },
        "summary": {
            "researched_families": len(packets),
            "represented_wiki_rows": sum(item["source_row_count"] for item in packets),
            "proposed_new_castings": create_count,
            "proposed_holds": hold_count,
            "confirmed_reviewer_decisions": 0,
            "promotion_eligible_families": 0,
        },
        "packets": packets,
    }
    manifest = {
        "schema_version": "pvr-fandom-priority-two-research-manifest-v1",
        "batch_version": batch_version,
        "inputs": {
            "adjudicated_queue": _file_reference(adjudicated_queue_path),
            "adjudicated_queue_manifest": _file_reference(adjudicated_manifest_path),
            "source_notes": _file_reference(source_notes_path),
        },
        **payload["summary"],
    }
    return payload, manifest, build_markdown(payload, batch_label=batch_label)


def build_markdown(payload: dict[str, Any], *, batch_label: str = "01") -> str:
    summary = payload["summary"]
    lines = [
        f"# Priority 2 Family Research — Batch {batch_label}",
        "",
        "> Source-backed machine recommendations only. Reviewer confirmation remains pending,",
        "> every release variant stays held, and no canonical or PostgreSQL record is created.",
        "",
        "## Summary",
        "",
        "| State | Count |",
        "|---|---:|",
        f"| Researched families | `{summary['researched_families']}` |",
        f"| Wiki release rows represented | `{summary['represented_wiki_rows']}` |",
        f"| Proposed `create_new_casting` | `{summary['proposed_new_castings']}` |",
        f"| Proposed `hold` | `{summary['proposed_holds']}` |",
        f"| Confirmed reviewer decisions | `{summary['confirmed_reviewer_decisions']}` |",
        f"| Promotion-eligible families | `{summary['promotion_eligible_families']}` |",
        "",
        "## Recommendations",
        "",
        "| Casting family | Wiki page | Independent source(s) | Recommendation | Why |",
        "|---|---|---:|---|---|",
    ]
    for packet in payload["packets"]:
        wiki = packet["research_evidence"]["wiki_casting_page"]
        recommendation = packet["machine_recommendation"]
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_escape(packet["casting_name"]),
                    wiki["page_classification"],
                    str(packet["research_evidence"]["independent_source_count"]),
                    recommendation["family_decision"],
                    _markdown_escape(recommendation["reason"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Evidence details", ""])
    for packet in payload["packets"]:
        evidence = packet["research_evidence"]
        wiki = evidence["wiki_casting_page"]
        lines.extend(
            [
                f"### {_markdown_escape(packet['casting_name'])}",
                "",
                f"- Queue ID: `{packet['family_review_id']}`",
                f"- Wiki evidence: [{wiki['publisher']}]({wiki['url']}) — "
                f"{_markdown_escape(wiki['observed_claim'])}",
            ]
        )
        for source in evidence["independent_sources"]:
            lines.append(
                f"- Independent evidence: [{source['publisher']}]({source['url']}) — "
                f"{_markdown_escape(source['observed_claim'])}"
            )
        lines.extend(
            [
                "- Machine recommendation: "
                f"`{packet['machine_recommendation']['family_decision']}` at family scope; "
                "variant remains `hold`.",
                "- Reviewer confirmation: **pending**",
                "",
            ]
        )
    return "\n".join(lines)


def expected_outputs(
    payload: dict[str, Any],
    manifest: dict[str, Any],
    markdown: str,
    *,
    research_file_name: str = "priority-2-batch-01-research.json",
    report_file_name: str = "priority-2-batch-01-research.md",
) -> tuple[str, str, str]:
    research_text = _stable_json(payload)
    frozen_manifest = dict(manifest)
    frozen_manifest["research_file"] = research_file_name
    frozen_manifest["research_sha256"] = hashlib.sha256(
        research_text.encode("utf-8")
    ).hexdigest()
    frozen_manifest["report_file"] = report_file_name
    frozen_manifest["report_sha256"] = hashlib.sha256(
        markdown.encode("utf-8")
    ).hexdigest()
    return research_text, _stable_json(frozen_manifest), markdown


def main() -> None:
    directory = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
    parser = argparse.ArgumentParser(
        description="Build or verify a priority-two source-research batch"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--batch", choices=("1", "2", "3", "4"), default="1")
    parser.add_argument("--directory", type=Path, default=directory)
    arguments = parser.parse_args()
    output = arguments.directory
    if arguments.batch == "1":
        batch_label = "01"
        batch_version = BATCH_VERSION
        queue_name = "adjudicated-queue.json"
        queue_manifest_name = "adjudicated-queue-manifest.json"
    elif arguments.batch == "2":
        batch_label = "02"
        batch_version = "fandom-2025-priority-two-research-batch-02-v1"
        queue_name = "priority-2-batch-01-adjudicated-queue.json"
        queue_manifest_name = "priority-2-batch-01-adjudicated-queue-manifest.json"
    elif arguments.batch == "3":
        batch_label = "03"
        batch_version = "fandom-2025-priority-two-research-batch-03-v1"
        queue_name = "priority-2-batch-02-adjudicated-queue.json"
        queue_manifest_name = "priority-2-batch-02-adjudicated-queue-manifest.json"
    else:
        batch_label = "04"
        batch_version = "fandom-2025-priority-two-research-batch-04-v1"
        queue_name = "priority-2-batch-03-adjudicated-queue.json"
        queue_manifest_name = "priority-2-batch-03-adjudicated-queue-manifest.json"
    prefix = f"priority-2-batch-{batch_label}"
    built = build_research(
        output / queue_name,
        output / queue_manifest_name,
        output / f"{prefix}-source-notes.json",
        batch_version=batch_version,
        batch_label=batch_label,
    )
    expected = expected_outputs(
        *built,
        research_file_name=f"{prefix}-research.json",
        report_file_name=f"{prefix}-research.md",
    )
    paths = (
        output / f"{prefix}-research.json",
        output / f"{prefix}-research-manifest.json",
        output / f"{prefix}-research.md",
    )
    if arguments.check:
        if any(not path.exists() for path in paths):
            raise ValueError("priority-two research outputs are missing")
        actual = tuple(path.read_text(encoding="utf-8") for path in paths)
        if actual != expected:
            raise ValueError("priority-two research outputs are stale")
        print(f"priority-two research batch {batch_label} is deterministic and current")
        return
    output.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, expected, strict=True):
        path.write_text(content, encoding="utf-8")
    print(_stable_json(built[0]["summary"]), end="")


if __name__ == "__main__":
    main()
