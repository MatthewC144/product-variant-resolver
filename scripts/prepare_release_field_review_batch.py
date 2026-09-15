#!/usr/bin/env python3
"""Prepare/check the frozen VAR-PLAN1 batch01 owner-review packet."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = Path("reports/release-field-evidence-review-v1/plan.json")
NORMALIZED_PATH = Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json")
EVIDENCE_PATHS = (
    Path("data/external/hot-wheels-wiki/pilot-2025/priority-1-evidence.json"),
    Path("data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-01-research.json"),
    Path("data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-04-research.json"),
)
DEFAULT_OUTPUT = ROOT / "reports/release-field-review-batch-01"

ROW_CLAIM_PROTOCOL: dict[str, dict[str, Any]] = {
    "fandom-row-65987b3eab315de1": {
        "source_artifact": EVIDENCE_PATHS[1].as_posix(),
        "publisher": "HW Treasure",
        "url": "https://www.hwtreasure.com/2025-super/87-audi-quattro/",
        "observed_claim": (
            "The guide identifies JBC35 as a 2025 Super Treasure Hunt using the '87 Audi "
            "quattro casting, which debuted in 2024."
        ),
        "candidate_fields": {
            "casting_name": "'87 Audi quattro",
            "toy_number": "JBC35",
            "release_year": 2025,
            "edition": "Super Treasure Hunt",
        },
    },
    "fandom-row-cd91a09d2fb2f780": {
        "source_artifact": EVIDENCE_PATHS[2].as_posix(),
        "publisher": "Hot Wheels Collectors News Catalog",
        "url": "https://catalog.hwcollectorsnews.com/Castings/Details/dc9e9612-131c-4191-9352-fddd4609402d",
        "observed_claim": (
            "The casting catalog records Lamborghini Huracán Sterrato and its HYW93 2025 "
            "release under the exact name."
        ),
        "candidate_fields": {
            "casting_name": "Lamborghini Huracán Sterrato",
            "toy_number": "HYW93",
            "release_year": 2025,
        },
    },
    "fandom-row-27fe2c9ab41942b8": {
        "source_artifact": EVIDENCE_PATHS[2].as_posix(),
        "publisher": "Diecast Radar",
        "url": (
            "https://diecastradar.app/product/"
            "hot-wheels-nissan-skyline-2000gt-r-lbwk-tooned-metalflake-blue-hyx54"
        ),
        "observed_claim": (
            "The collector record maps HYX54 to the Nissan Skyline 2000GT-R LBWK (Tooned) "
            "casting and its 2025 HW J-Imports release."
        ),
        "candidate_fields": {
            "casting_name": "Nissan Skyline 2000GT-R LBWK",
            "toy_number": "HYX54",
            "release_year": 2025,
            "series": "HW J-Imports",
            "tool_lineage_ref": "Tooned",
        },
        "explicit_non_claims": [
            "color is not accepted from the URL slug; the frozen observed claim does not state it"
        ],
    },
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _research_index(root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for relative in EVIDENCE_PATHS:
        payload = _load(root / relative)
        packets = payload.get("packets")
        if not isinstance(packets, list):
            raise ValueError(f"{relative}: packets missing")
        for packet in packets:
            family_id = packet.get("family_review_id")
            if not isinstance(family_id, str):
                raise ValueError(f"{relative}: family ID missing")
            if family_id in index:
                raise ValueError(f"duplicate research family: {family_id}")
            index[family_id] = {"source_artifact": relative.as_posix(), "packet": packet}
    return index


def _normalized_index(root: Path) -> dict[str, Mapping[str, Any]]:
    payload = _load(root / NORMALIZED_PATH)
    rows = payload.get("records")
    if not isinstance(rows, list) or len(rows) != 100:
        raise ValueError("normalized source must contain exactly 100 rows")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        source_id = row.get("source_record_id")
        if not isinstance(source_id, str) or source_id in result:
            raise ValueError("invalid/duplicate normalized source ID")
        result[source_id] = row
    return result


def _family_evidence(research: Mapping[str, Any]) -> dict[str, Any]:
    packet = research["packet"]
    recommendation = packet.get("machine_recommendation")
    if not isinstance(recommendation, dict) or recommendation.get("scope") != "casting_family_only":
        raise ValueError("research evidence is not casting-family scoped")
    if recommendation.get("variant_decision") != "hold":
        raise ValueError("research evidence does not hold the variant")
    evidence = packet.get("research_evidence")
    if evidence is None:
        evidence = {
            "comparison": packet.get("comparison"),
            "human_evidence": packet.get("human_evidence"),
            "wiki_evidence": packet.get("wiki_evidence"),
        }
    return {
        "source_artifact": research["source_artifact"],
        "approved_scope": "casting_family_only",
        "family_recommendation": recommendation,
        "frozen_evidence": evidence,
        "release_effect": "none_all_source_rows_remain_held",
    }


def _validate_row_claims(research_index: Mapping[str, Mapping[str, Any]]) -> None:
    independent_claims: dict[tuple[str, str], Mapping[str, Any]] = {}
    for research in research_index.values():
        evidence = research["packet"].get("research_evidence")
        if not isinstance(evidence, dict):
            continue
        for claim in evidence.get("independent_sources", []):
            independent_claims[(research["source_artifact"], claim["url"])] = claim
    for source_id, protocol in ROW_CLAIM_PROTOCOL.items():
        key = (protocol["source_artifact"], protocol["url"])
        frozen = independent_claims.get(key)
        if frozen is None:
            raise ValueError(f"{source_id}: row-specific evidence missing")
        if frozen.get("publisher") != protocol["publisher"]:
            raise ValueError(f"{source_id}: publisher drift")
        if frozen.get("observed_claim") != protocol["observed_claim"]:
            raise ValueError(f"{source_id}: observed claim drift")


def build_packet(root: Path = ROOT) -> dict[str, Any]:
    plan_path = root / PLAN_PATH
    plan = _load(plan_path)
    if plan.get("schema_version") != "pvr-release-field-evidence-review-plan-v1":
        raise ValueError("unexpected VAR-PLAN1 schema")
    batch = plan.get("first_review_batch")
    if not isinstance(batch, dict) or batch.get("family_count") != 4 or batch.get("source_row_count") != 11:
        raise ValueError("expected frozen four-family/11-row batch")
    selected = batch.get("families")
    if not isinstance(selected, list) or len(selected) != 4:
        raise ValueError("invalid selected families")

    plan_records = plan.get("records")
    if not isinstance(plan_records, list):
        raise ValueError("plan records missing")
    plan_by_id = {record["source_record_id"]: record for record in plan_records}
    normalized_by_id = _normalized_index(root)
    research_by_family = _research_index(root)
    _validate_row_claims(research_by_family)

    packet_families: list[dict[str, Any]] = []
    seen_rows: set[str] = set()
    seen_families: set[str] = set()
    for selected_family in selected:
        family_id = selected_family.get("family_review_id")
        if not isinstance(family_id, str) or family_id in seen_families:
            raise ValueError("duplicate/invalid selected family")
        seen_families.add(family_id)
        research = research_by_family.get(family_id)
        if research is None:
            raise ValueError(f"{family_id}: missing research evidence")
        source_ids = selected_family.get("source_record_ids")
        if not isinstance(source_ids, list) or len(source_ids) != selected_family.get("source_row_count"):
            raise ValueError(f"{family_id}: invalid selected source IDs")

        rows: list[dict[str, Any]] = []
        for source_id in source_ids:
            if not isinstance(source_id, str) or source_id in seen_rows:
                raise ValueError("duplicate/invalid selected source row")
            seen_rows.add(source_id)
            planned = plan_by_id.get(source_id)
            normalized = normalized_by_id.get(source_id)
            if planned is None or normalized is None or planned["family_review_id"] != family_id:
                raise ValueError(f"{source_id}: plan/source/family mismatch")
            release_review = planned.get("release_review")
            if not isinstance(release_review, dict) or release_review.get("status") != "held_pending_field_review":
                raise ValueError(f"{source_id}: release is not held")
            if release_review.get("canonical_uuid") is not None:
                raise ValueError(f"{source_id}: canonical UUID must be null")

            raw_fields = {
                field: planned["field_evidence"][field]["raw_value"]
                for field in planned["field_evidence"]
            }
            for field in ("color", "wheel_type", "tampo_description", "edition", "packaging_variant"):
                if raw_fields[field] is not None:
                    raise ValueError(f"{source_id}: expected unknown physical field {field}")
            protocol = ROW_CLAIM_PROTOCOL.get(source_id)
            candidate_claims = []
            if protocol is not None:
                candidate_claims.append(
                    {
                        "status": "candidate_pending_owner_review",
                        "publisher": protocol["publisher"],
                        "url": protocol["url"],
                        "observed_claim": protocol["observed_claim"],
                        "source_artifact": protocol["source_artifact"],
                        "candidate_fields": protocol["candidate_fields"],
                        "explicit_non_claims": protocol.get("explicit_non_claims", []),
                    }
                )
            rows.append(
                {
                    "source_record_id": source_id,
                    "observation_id": planned["observation_id"],
                    "source_row": planned["source_row"],
                    "raw_fields": raw_fields,
                    "source_markers": normalized.get("source_markers", []),
                    "candidate_secondary_claims": candidate_claims,
                    "review_state": {
                        "status": "held_pending_owner_review",
                        "canonical_uuid": None,
                        "variant_equivalence_id": None,
                        "field_decision_count": 0,
                    },
                }
            )
        rows.sort(key=lambda row: row["source_row"])
        packet_families.append(
            {
                "family_review_id": family_id,
                "casting_name": selected_family["casting_name"],
                "prior_family_decision": selected_family["family_decision"],
                "family_evidence": _family_evidence(research),
                "rows": rows,
                "relationship_pairs": [
                    {
                        "left_source_record_id": left["source_record_id"],
                        "right_source_record_id": right["source_record_id"],
                        "decision": None,
                        "allowed_decisions": ["same_release", "different_release", "unresolved"],
                    }
                    for left, right in itertools.combinations(rows, 2)
                ],
            }
        )

    if len(seen_rows) != 11:
        raise ValueError("packet must contain exactly 11 unique rows")
    pair_count = sum(len(family["relationship_pairs"]) for family in packet_families)
    if pair_count != 10:
        raise ValueError("packet must contain exactly 10 within-family pairs")

    bindings = {
        PLAN_PATH.as_posix(): _sha(plan_path),
        NORMALIZED_PATH.as_posix(): _sha(root / NORMALIZED_PATH),
    }
    bindings.update({relative.as_posix(): _sha(root / relative) for relative in EVIDENCE_PATHS})
    return {
        "schema_version": "pvr-release-field-review-packet-v1",
        "packet_version": "release-field-review-batch-01-packet-v1",
        "status": "awaiting_owner_review_no_decisions",
        "source_bindings": bindings,
        "counts": {
            "families": len(packet_families),
            "source_rows": len(seen_rows),
            "relationship_pairs": pair_count,
            "row_specific_candidate_claims": sum(
                len(row["candidate_secondary_claims"])
                for family in packet_families
                for row in family["rows"]
            ),
            "owner_field_decisions": 0,
            "owner_relationship_decisions": 0,
            "canonical_uuids": 0,
        },
        "authority": {
            "prior_family_decisions_are_release_decisions": False,
            "all_rows_held": True,
            "url_slug_inference_allowed": False,
            "unknown_values_imply_equality": False,
        },
        "families": packet_families,
        "owner_gate": (
            "review exact row fields and every within-family relationship; bind completed choices "
            "to this packet SHA in a new append-only decision artifact"
        ),
        "rights_status": "historical evidence only; no current access/rights revalidation or fetch",
    }


def build_decision_template(packet: Mapping[str, Any], packet_sha256: str) -> dict[str, Any]:
    row_decisions: list[dict[str, Any]] = []
    relationship_decisions: list[dict[str, Any]] = []
    for family in packet["families"]:
        for row in family["rows"]:
            row_decisions.append(
                {
                    "family_review_id": family["family_review_id"],
                    "source_record_id": row["source_record_id"],
                    "fields": {
                        field: {
                            "decision": None,
                            "allowed_decisions": ["confirmed", "conflicted", "rejected", "unknown"],
                            "reviewed_value": None,
                            "evidence_references": [],
                            "reason": None,
                        }
                        for field in row["raw_fields"]
                    },
                }
            )
        for pair in family["relationship_pairs"]:
            relationship_decisions.append(
                {
                    "family_review_id": family["family_review_id"],
                    "left_source_record_id": pair["left_source_record_id"],
                    "right_source_record_id": pair["right_source_record_id"],
                    "decision": None,
                    "allowed_decisions": ["same_release", "different_release", "unresolved"],
                    "evidence_references": [],
                    "reason": None,
                }
            )
    return {
        "schema_version": "pvr-release-field-review-owner-decisions-v1",
        "decision_version": None,
        "status": "template_all_decisions_pending",
        "packet_sha256": packet_sha256,
        "reviewer": None,
        "reviewed_at": None,
        "overall_reason": None,
        "row_field_decisions": row_decisions,
        "relationship_decisions": relationship_decisions,
        "canonical_promotion_authorized": False,
    }


def render_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# Batch01 — release field owner review",
        "",
        "This packet asks for human decisions;it contains none. All11 rows remain held and noncanonical.",
        "A prior family decision answers only “which casting family?”,not “which exact release?”.",
        "",
        "## How to review",
        "",
        "1. Read siblings in one family together.",
        "2. Confirm a field only when the frozen text explicitly supports that row/value.",
        "3. Keep missing physical fields unknown;do not decode URL slugs or `2nd Color` into a color.",
        "4. For every row pair choose same release,different release,or unresolved and explain why.",
        "",
    ]
    for family in packet["families"]:
        lines.extend(
            [
                f"## {family['casting_name']}",
                "",
                f"Prior family context:`{family['prior_family_decision']}`;release effect:none/held.",
                "",
                "| Row | Source ID | Toy | Year | Series / position | Variant note | Markers | Physical fields |",
                "|---:|---|---|---:|---|---|---|---|",
            ]
        )
        for row in family["rows"]:
            raw = row["raw_fields"]
            note = raw["variant_note"] or "—"
            markers = ",".join(row["source_markers"]) or "—"
            lines.append(
                f"| {row['source_row']} | `{row['source_record_id']}` | {raw['toy_number']} | "
                f"{raw['release_year']} | {raw['series']} / {raw['series_position']} | {note} | "
                f"{markers} | color/wheel/tampo/edition/packaging unknown |"
            )
        lines.extend(["", "Frozen secondary claims awaiting your decision:", ""])
        claims = [claim for row in family["rows"] for claim in row["candidate_secondary_claims"]]
        if not claims:
            lines.append("- None is safely row-specific;family-level evidence must not fill a release field.")
        for claim in claims:
            fields = ", ".join(f"{key}={value}" for key, value in claim["candidate_fields"].items())
            lines.append(
                f"- `{claim['status']}` — {claim['publisher']}: {claim['observed_claim']} "
                f"Candidate fields: {fields}. Source: {claim['url']}"
            )
            for non_claim in claim["explicit_non_claims"]:
                lines.append(f"  - Do not claim: {non_claim}.")
        lines.extend(["", "Required within-family relationship decisions:", ""])
        for pair in family["relationship_pairs"]:
            lines.append(
                f"- `{pair['left_source_record_id']}` vs `{pair['right_source_record_id']}`: "
                "same_release / different_release / unresolved — reason and evidence required."
            )
        lines.append("")
    lines.extend(
        [
            "## Stop condition",
            "",
            "Do not advance to collection or identity design from this packet alone. Completed owner choices",
            "must be stored as a new immutable decision artifact bound to the packet SHA. Current source rights",
            "were not revalidated and no remote page was fetched during preparation.",
            "",
        ]
    )
    return "\n".join(lines)


def payloads(root: Path = ROOT) -> dict[str, bytes]:
    packet = build_packet(root)
    packet_bytes = _json_bytes(packet)
    template = build_decision_template(packet, hashlib.sha256(packet_bytes).hexdigest())
    markdown_bytes = render_markdown(packet).encode()
    template_bytes = _json_bytes(template)
    manifest = {
        "schema_version": "pvr-release-field-review-batch-manifest-v1",
        "status": "frozen_before_owner_decisions",
        "source_sha256": packet["source_bindings"],
        "artifact_sha256": {
            "packet.json": hashlib.sha256(packet_bytes).hexdigest(),
            "owner-review.md": hashlib.sha256(markdown_bytes).hexdigest(),
            "decisions.template.json": hashlib.sha256(template_bytes).hexdigest(),
        },
        "constraints": {
            "owner_decisions": 0,
            "network_requests": 0,
            "canonical_changes": 0,
            "all_rows_held": True,
        },
    }
    return {
        "packet.json": packet_bytes,
        "owner-review.md": markdown_bytes,
        "decisions.template.json": template_bytes,
        "manifest.json": _json_bytes(manifest),
    }


def publish(output: Path, root: Path = ROOT) -> None:
    if output.exists():
        raise ValueError(f"exclusive output already exists: {output}")
    files = payloads(root)
    output.mkdir(parents=True)
    for name, content in files.items():
        (output / name).write_bytes(content)


def check(output: Path, root: Path = ROOT) -> None:
    files = payloads(root)
    if not output.is_dir():
        raise ValueError(f"missing output directory: {output}")
    actual = {path.name for path in output.iterdir() if path.is_file()}
    if actual != set(files):
        raise ValueError(f"artifact names differ: expected {sorted(files)},got {sorted(actual)}")
    for name, content in files.items():
        if (output / name).read_bytes() != content:
            raise ValueError(f"{name} drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        publish(args.output) if args.run else check(args.output)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(f"batch01 preparation rejected: {error}",file=sys.stderr)
        return 1
    print("PASS batch01 PREP: 4 families/11 rows/10 pairs; owner decisions=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
