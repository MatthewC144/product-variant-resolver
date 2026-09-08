#!/usr/bin/env python3
"""Build evidence packets for priority-one Fandom family adjudication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA_VERSION = "pvr-fandom-priority-one-evidence-v1"
PACKET_VERSION = "fandom-2025-priority-one-family-evidence-v1"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _normalize(value: str | None) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _shared_variant_tokens(
    wiki_rows: list[dict[str, Any]], human_variants: list[dict[str, Any]]
) -> list[str]:
    wiki_tokens = {
        token
        for row in wiki_rows
        for token in _normalize(row.get("variant_note")).split()
    }
    human_tokens = {
        token
        for variant in human_variants
        for token in _normalize(variant.get("variant_label")).split()
    }
    ignored = {"1st", "2nd", "3rd", "4th", "color", "colour"}
    return sorted((wiki_tokens & human_tokens) - ignored)


def build_packets(
    queue_path: Path,
    queue_manifest_path: Path,
    human_catalog_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    queue = _load(queue_path)
    queue_manifest = _load(queue_manifest_path)
    human_catalog = _load(human_catalog_path)
    if queue_manifest.get("queue_sha256") != hashlib.sha256(
        queue_path.read_bytes()
    ).hexdigest():
        raise ValueError("queue checksum differs from its manifest")
    families = queue.get("families")
    human_castings = human_catalog.get("castings")
    if not isinstance(families, list) or not isinstance(human_castings, list):
        raise ValueError("queue and human catalog must contain family arrays")
    human_by_id = {item["casting_id"]: item for item in human_castings}

    packets: list[dict[str, Any]] = []
    for family in families:
        if family.get("priority") != 1:
            continue
        decision = family.get("reviewer_decision", {})
        if decision.get("status") != "pending" or family.get("promotion_eligible") is not False:
            raise ValueError("priority-one family has crossed the pending review boundary")
        candidate_ids = family["pre_review"]["human_casting_candidate_ids"]
        if len(candidate_ids) != 1:
            raise ValueError("priority-one packet requires one exact human family candidate")
        human = human_by_id.get(candidate_ids[0])
        if human is None:
            raise ValueError("priority-one human family candidate is missing")
        if _normalize(human["brand"]) != family["normalized_family_key"]["brand"]:
            raise ValueError("priority-one candidate brand no longer matches")
        if _normalize(human["casting"]) != family["normalized_family_key"]["casting"]:
            raise ValueError("priority-one candidate casting no longer matches")
        wiki_rows = family["source_rows"]
        human_variants = human["provisional_variants"]
        wiki_series = sorted({row["series"] for row in wiki_rows})
        human_series = sorted(
            {item["series_label"] for item in human_variants if item["series_label"]}
        )
        shared_tokens = _shared_variant_tokens(wiki_rows, human_variants)
        packets.append(
            {
                "family_review_id": family["family_review_id"],
                "brand": family["brand"],
                "casting_name": family["casting_name"],
                "target_human_casting_id": human["casting_id"],
                "target_human_casting_uuid": human["casting_uuid"],
                "family_name_match": "exact_normalized_brand_and_casting",
                "wiki_evidence": {
                    "source_rows": wiki_rows,
                    "release_years": sorted({row["release_year"] for row in wiki_rows}),
                    "series_labels": wiki_series,
                },
                "human_evidence": {
                    "source_case_ids": human["source_case_ids"],
                    "variants": [
                        {
                            "provisional_variant_id": item["provisional_variant_id"],
                            "source_case_ids": item["source_case_ids"],
                            "human_label_names": item["human_label_names"],
                            "initial_names": item["initial_names"],
                            "series_label": item["series_label"],
                            "variant_label": item["variant_label"],
                            "failure_categories": item["failure_categories"],
                        }
                        for item in human_variants
                    ],
                    "series_labels": human_series,
                },
                "comparison": {
                    "family_name_exact": True,
                    "series_labels_exact": {
                        _normalize(value) for value in wiki_series
                    }
                    == {_normalize(value) for value in human_series},
                    "shared_explicit_variant_tokens": shared_tokens,
                    "variant_identity_verified": False,
                },
                "machine_recommendation": {
                    "family_decision": "merge_existing_family",
                    "target_family_id": human["casting_id"],
                    "reason": (
                        "brand and casting match exactly after normalization across the frozen "
                        "Wiki review and confirmed-label human catalog"
                    ),
                    "scope": "casting_family_only",
                    "variant_decision": "hold",
                    "variant_reason": (
                        "year, series, color, edition, and release identity are not "
                        "jointly verified"
                    ),
                },
                "reviewer_confirmation": {
                    "status": "pending",
                    "accept_family_recommendation": None,
                    "decided_by": None,
                    "decided_at": None,
                    "reason": None,
                    "evidence_references": [],
                },
                "promotion_eligible": False,
            }
        )

    packets.sort(key=lambda item: item["casting_name"].casefold())
    payload = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_version": PACKET_VERSION,
        "status": "awaiting_reviewer_confirmation",
        "scope": "priority-one casting-family decisions only; variants remain held",
        "packet_count": len(packets),
        "wiki_source_row_count": sum(
            len(item["wiki_evidence"]["source_rows"]) for item in packets
        ),
        "confirmed_reviewer_decisions": 0,
        "promotion_eligible_families": 0,
        "packets": packets,
    }
    manifest = {
        "schema_version": "pvr-fandom-priority-one-evidence-manifest-v1",
        "packet_version": PACKET_VERSION,
        "inputs": {
            "adjudication_queue": {
                "file": queue_path.name,
                "sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
            },
            "adjudication_queue_manifest": {
                "file": queue_manifest_path.name,
                "sha256": hashlib.sha256(
                    queue_manifest_path.read_bytes()
                ).hexdigest(),
            },
            "human_catalog": {
                "file": human_catalog_path.name,
                "sha256": hashlib.sha256(human_catalog_path.read_bytes()).hexdigest(),
            },
        },
        "packet_count": payload["packet_count"],
        "wiki_source_row_count": payload["wiki_source_row_count"],
        "confirmed_reviewer_decisions": 0,
        "promotion_eligible_families": 0,
    }
    return payload, manifest, build_markdown(payload)


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Priority 1 Family Review Evidence",
        "",
        "> Machine recommendation only. Reviewer confirmation is still pending. The recommendation",
        "> applies to casting family identity; every release/variant remains held.",
        "",
        "## Summary",
        "",
        f"- Family packets: `{payload['packet_count']}`",
        f"- Wiki release rows represented: `{payload['wiki_source_row_count']}`",
        "- Proposed family decision: `merge_existing_family` for all four exact-name candidates",
        "- Proposed variant decision: `hold` for every packet",
        "- Confirmed reviewer decisions: `0`",
        "- Promotion-eligible families: `0`",
        "",
    ]
    for packet in payload["packets"]:
        lines.extend(
            [
                f"## {_markdown_escape(packet['casting_name'])}",
                "",
                f"- Queue ID: `{packet['family_review_id']}`",
                f"- Proposed target: `{packet['target_human_casting_id']}`",
                "- Family evidence: exact normalized brand and casting in both sources",
                (
                    "- Wiki series: "
                    + ", ".join(
                        f"`{_markdown_escape(value)}`"
                        for value in packet["wiki_evidence"]["series_labels"]
                    )
                ),
                (
                    "- Human series: "
                    + ", ".join(
                        f"`{_markdown_escape(value)}`"
                        for value in packet["human_evidence"]["series_labels"]
                    )
                ),
                (
                    "- Shared explicit variant tokens: "
                    + (
                        ", ".join(
                            f"`{value}`"
                            for value in packet["comparison"][
                                "shared_explicit_variant_tokens"
                            ]
                        )
                        or "none"
                    )
                ),
                "- Recommendation: merge casting family only; hold every release/variant",
                "- Reviewer confirmation: **pending**",
                "",
                "| Wiki row | Toy # | Collector # | Year | Series | Variant note |",
                "|---:|---|---|---:|---|---|",
            ]
        )
        for row in packet["wiki_evidence"]["source_rows"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["source_row"]),
                        _markdown_escape(row["toy_number"]),
                        _markdown_escape(row["collector_number"] or ""),
                        str(row["release_year"]),
                        _markdown_escape(row["series"]),
                        _markdown_escape(row["variant_note"] or "—"),
                    ]
                )
                + " |"
            )
        lines.extend(["", "Human-backed evidence:", ""])
        for variant in packet["human_evidence"]["variants"]:
            lines.append(
                f"- Variant candidate: `{variant['provisional_variant_id']}`"
            )
            lines.append(
                "  - Human label: "
                + _markdown_escape("; ".join(variant["human_label_names"]) or "not retained")
            )
            lines.append(
                "  - Initial source name: "
                + _markdown_escape("; ".join(variant["initial_names"]) or "not retained")
            )
            lines.append(
                "  - Structured fields: series "
                f"`{_markdown_escape(variant['series_label'] or 'unknown')}`; variant "
                f"`{_markdown_escape(variant['variant_label'] or 'unknown')}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Reviewer decision boundary",
            "",
            "Accepting a packet means only that both sources refer to the same casting family. It",
            "does not approve a color, year, series, toy number, edition, rarity, or canonical",
            "release UUID. Those variant-level decisions remain `hold` until separately verified.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_outputs(
    payload: dict[str, Any],
    manifest: dict[str, Any],
    markdown: str,
    *,
    packet_file_name: str = "priority-1-evidence.json",
    report_file_name: str = "priority-1-evidence.md",
) -> tuple[str, str, str]:
    packet_text = _stable_json(payload)
    frozen_manifest = dict(manifest)
    frozen_manifest["packet_file"] = packet_file_name
    frozen_manifest["packet_sha256"] = hashlib.sha256(
        packet_text.encode("utf-8")
    ).hexdigest()
    frozen_manifest["report_file"] = report_file_name
    frozen_manifest["report_sha256"] = hashlib.sha256(
        markdown.encode("utf-8")
    ).hexdigest()
    return packet_text, _stable_json(frozen_manifest), markdown


def parse_args() -> argparse.Namespace:
    directory = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
    parser = argparse.ArgumentParser(
        description="Build or verify evidence packets for priority-one Fandom families"
    )
    parser.add_argument(
        "--queue", type=Path, default=directory / "adjudication-queue.json"
    )
    parser.add_argument(
        "--queue-manifest",
        type=Path,
        default=directory / "adjudication-queue-manifest.json",
    )
    parser.add_argument(
        "--human", type=Path, default=ROOT / "data" / "human_backed_catalog.json"
    )
    parser.add_argument(
        "--output", type=Path, default=directory / "priority-1-evidence.json"
    )
    parser.add_argument(
        "--report", type=Path, default=directory / "priority-1-evidence.md"
    )
    parser.add_argument(
        "--manifest", type=Path, default=directory / "priority-1-evidence-manifest.json"
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, manifest, markdown = build_packets(
        args.queue, args.queue_manifest, args.human
    )
    packet_text, manifest_text, report_text = expected_outputs(
        payload,
        manifest,
        markdown,
        packet_file_name=args.output.name,
        report_file_name=args.report.name,
    )
    if args.check:
        for path, expected in (
            (args.output, packet_text),
            (args.manifest, manifest_text),
            (args.report, report_text),
        ):
            if path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"{path.name} differs from a deterministic rebuild")
        status = "verified"
    else:
        for path in (args.output, args.manifest, args.report):
            path.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(packet_text, encoding="utf-8")
        args.manifest.write_text(manifest_text, encoding="utf-8")
        args.report.write_text(report_text, encoding="utf-8")
        status = "built"
    print(
        f"{status} {payload['packet_count']} priority-one family packets; "
        "reviewer confirmations=0, promotion eligible=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
