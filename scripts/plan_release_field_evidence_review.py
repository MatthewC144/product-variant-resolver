#!/usr/bin/env python3
"""Build/check the offline VAR-PLAN1 field-evidence review plan."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = Path("data/external/hot-wheels-wiki/pilot-2025")
NORMALIZED_PATH = PILOT / "normalized.json"
REVIEW_PATH = PILOT / "review.json"
QUEUE_PATH = PILOT / "priority-2-batch-05-adjudicated-queue.json"
DEFAULT_OUTPUT = ROOT / "reports/release-field-evidence-review-v1"

FIELD_NAMES = (
    "brand",
    "casting_name",
    "release_year",
    "series",
    "series_position",
    "collector_number",
    "toy_number",
    "variant_note",
    "color",
    "wheel_type",
    "tampo_description",
    "edition",
    "packaging_variant",
)
ALLOWED_FAMILY_DECISIONS = {"hold", "merge_existing_family", "create_new_casting"}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    source = "\x1f".join(str(part) for part in parts).encode()
    return f"{prefix}-{hashlib.sha256(source).hexdigest()[:20]}"


def _index_unique(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        source_id = row.get("source_record_id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(f"{label}: missing source_record_id")
        if source_id in result:
            raise ValueError(f"{label}: duplicate source_record_id {source_id}")
        result[source_id] = row
    return result


def _family_features(records: Sequence[Mapping[str, Any]], decision: str) -> list[str]:
    notes = [str(record.get("variant_note") or "").casefold() for record in records]
    series = {record.get("series") for record in records}
    features = {f"family_decision:{decision}"}
    if any("2nd color" in note for note in notes):
        features.add("second_color_marker")
    if any("3rd color" in note for note in notes):
        features.add("third_color_marker")
    if any("zamac" in note for note in notes):
        features.add("zamac_marker_without_verified_color")
    if len(series) > 1:
        features.add("series_divergence")
    if len(records) >= 3:
        features.add("three_source_rows")
    if len(records) > 1 and sum(record.get("variant_note") is None for record in records) > 1:
        features.add("multiple_rows_without_variant_note")
    return sorted(features)


def _select_first_batch(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for family in families:
        records = family["records"]
        features = _family_features(records, str(family["family_decision"]))
        information_score = (
            len(features) * 10
            + len(records) * 3
            + sum(record.get("variant_note") is not None for record in records)
        )
        candidates.append(
            {
                "family_review_id": family["family_review_id"],
                "casting_name": family["casting_name"],
                "family_decision": family["family_decision"],
                "source_record_ids": [record["source_record_id"] for record in records],
                "source_row_count": len(records),
                "coverage_features": features,
                "information_score": information_score,
            }
        )

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    covered: set[str] = set()
    row_count = 0
    while len(selected) < 5:
        eligible = [
            candidate
            for candidate in candidates
            if candidate["family_review_id"] not in selected_ids
            and row_count + candidate["source_row_count"] <= 15
        ]
        if not eligible:
            break
        eligible.sort(
            key=lambda candidate: (
                -len(set(candidate["coverage_features"]) - covered),
                -candidate["information_score"],
                -candidate["source_row_count"],
                candidate["family_review_id"],
            )
        )
        chosen = dict(eligible[0])
        new_coverage = set(chosen["coverage_features"]) - covered
        if not new_coverage and {
            item["family_decision"] for item in selected
        } == ALLOWED_FAMILY_DECISIONS:
            break
        chosen["new_coverage_at_selection"] = sorted(new_coverage)
        selected.append(chosen)
        selected_ids.add(str(chosen["family_review_id"]))
        covered.update(chosen["coverage_features"])
        row_count += int(chosen["source_row_count"])

    decisions = {item["family_decision"] for item in selected}
    if decisions != ALLOWED_FAMILY_DECISIONS:
        raise ValueError(f"first batch does not cover family decisions: {sorted(decisions)}")
    if not 1 <= len(selected) <= 5 or not 1 <= row_count <= 15:
        raise ValueError("first batch bounds not satisfied")
    return {
        "batch_id": "release-field-review-batch-01-proposal-v1",
        "status": "proposal_only_owner_review_not_started",
        "selection_method": "greedy whole-family new-pattern coverage; stable family-ID tie-break",
        "family_limit": 5,
        "source_row_limit": 15,
        "family_count": len(selected),
        "source_row_count": row_count,
        "covered_features": sorted(covered),
        "families": selected,
        "review_questions": [
            "Which exact source text supports each non-null field value?",
            "Are color, wheel, tampo, edition and packaging still unknown, or is attributable text evidence available?",
            "Do same-casting observations represent the same release, different releases, or an unresolved relationship?",
            "Does any field conflict across independent sources, and must the release remain held?",
        ],
        "completion_rule": (
            "append owner decisions bound to exact field values and evidence; unknown/conflicted fields "
            "never create variant equivalence or canonical identity"
        ),
    }


def build_plan(root: Path = ROOT) -> dict[str, Any]:
    normalized_path = root / NORMALIZED_PATH
    review_path = root / REVIEW_PATH
    queue_path = root / QUEUE_PATH
    normalized = _load_json(normalized_path)
    review = _load_json(review_path)
    queue = _load_json(queue_path)

    if normalized.get("schema_version") != "fandom-hot-wheels-staging-v1":
        raise ValueError("unexpected normalized schema")
    if review.get("schema_version") != "pvr-fandom-catalog-review-v1":
        raise ValueError("unexpected review schema")
    if queue.get("schema_version") != "pvr-fandom-priority-two-adjudicated-queue-v1":
        raise ValueError("unexpected queue schema")

    normalized_rows = normalized.get("records")
    review_rows = review.get("reviews")
    queue_families = queue.get("families")
    if not isinstance(normalized_rows, list) or len(normalized_rows) != 100:
        raise ValueError("normalized input must contain exactly 100 records")
    if not isinstance(review_rows, list) or len(review_rows) != 100:
        raise ValueError("review input must contain exactly 100 records")
    if not isinstance(queue_families, list) or len(queue_families) != 53:
        raise ValueError("queue input must contain exactly 53 families")

    normalized_by_id = _index_unique(normalized_rows, "normalized")
    review_by_id = _index_unique(review_rows, "review")
    queue_by_id: dict[str, Mapping[str, Any]] = {}
    family_by_source: dict[str, Mapping[str, Any]] = {}
    for family in queue_families:
        family_id = family.get("family_review_id")
        if not isinstance(family_id, str) or family_id in queue_by_id:
            raise ValueError("invalid or duplicate family_review_id")
        queue_by_id[family_id] = family
        decision = family.get("reviewer_decision")
        if not isinstance(decision, dict):
            raise ValueError(f"{family_id}: missing reviewer decision")
        if decision.get("decision") not in ALLOWED_FAMILY_DECISIONS:
            raise ValueError(f"{family_id}: unexpected family decision")
        if decision.get("variant_decision") != "hold" or family.get("promotion_eligible") is not False:
            raise ValueError(f"{family_id}: release variant is not held")
        source_rows = family.get("source_rows")
        if not isinstance(source_rows, list) or len(source_rows) != family.get("source_row_count"):
            raise ValueError(f"{family_id}: invalid source-row count")
        for row in source_rows:
            source_id = row.get("source_record_id")
            if not isinstance(source_id, str) or source_id in family_by_source:
                raise ValueError(f"{family_id}: invalid or duplicate queue source row")
            family_by_source[source_id] = family

    expected_ids = set(normalized_by_id)
    if set(review_by_id) != expected_ids or set(family_by_source) != expected_ids:
        raise ValueError("source-record membership differs across the three inputs")
    summary = queue.get("summary")
    if not isinstance(summary, dict) or summary.get("held_release_variants") != 100:
        raise ValueError("queue does not preserve all 100 held releases")
    if summary.get("promotion_eligible_families") != 0:
        raise ValueError("queue unexpectedly permits promotion")

    records: list[dict[str, Any]] = []
    family_records: dict[str, list[Mapping[str, Any]]] = {}
    for source_id in sorted(expected_ids, key=lambda item: normalized_by_id[item]["source_row"]):
        raw = normalized_by_id[source_id]
        prior_review = review_by_id[source_id]
        family = family_by_source[source_id]
        if raw.get("source_row") != prior_review.get("source_row"):
            raise ValueError(f"{source_id}: source row mismatch")
        if raw.get("canonical_uuid") is not None or prior_review.get("canonical_uuid") is not None:
            raise ValueError(f"{source_id}: canonical UUID must remain null")
        if prior_review.get("promotion_decision") != "hold_for_human_review":
            raise ValueError(f"{source_id}: prior release hold changed")
        if prior_review.get("promotion_eligible") is not False:
            raise ValueError(f"{source_id}: prior release became promotion eligible")

        family_id = str(family["family_review_id"])
        decision = family["reviewer_decision"]
        if raw.get("casting_name") != family.get("casting_name"):
            raise ValueError(f"{source_id}: casting differs from final queue")
        evidence_fields: dict[str, Any] = {}
        for field in FIELD_NAMES:
            value = raw.get(field)
            evidence_fields[field] = {
                "raw_value": value,
                "state": "unknown" if value is None else "observed_unverified",
                "evidence_pointer": f"{NORMALIZED_PATH.as_posix()}#/records/{raw['source_row'] - 1}/{field}",
                "allowed_human_states": ["confirmed", "conflicted", "rejected", "unknown"],
            }
        observation_id = _stable_id(
            "release-observation",
            normalized["source"]["revision_id"],
            source_id,
        )
        item = {
            "source_record_id": source_id,
            "observation_id": observation_id,
            "family_review_id": family_id,
            "source_row": raw["source_row"],
            "source_revision_id": raw["source"]["revision_id"],
            "family_context": {
                "casting_name": raw["casting_name"],
                "decision": decision["decision"],
                "decision_scope": decision.get("scope"),
                "target_family_id": decision.get("target_family_id"),
            },
            "field_evidence": evidence_fields,
            "release_review": {
                "status": "held_pending_field_review",
                "promotion_eligible": False,
                "variant_equivalence_id": None,
                "canonical_uuid": None,
                "owner_field_decision_id": None,
            },
            "inference_prohibitions": [
                "do_not_parse_variant_note_into_physical_color",
                "do_not_infer_wheel_or_tampo_from_missing_fields_or_image_names",
                "do_not_treat_equal_nulls_or_casting_name_as_variant_equivalence",
                "do_not_use_toy_number_as_canonical_identity",
            ],
        }
        if observation_id == source_id:
            raise ValueError("observation and source IDs must differ")
        records.append(item)
        family_records.setdefault(family_id, []).append(raw)

    batch_families = [
        {
            "family_review_id": family_id,
            "casting_name": queue_by_id[family_id]["casting_name"],
            "family_decision": queue_by_id[family_id]["reviewer_decision"]["decision"],
            "records": sorted(family_records[family_id], key=lambda item: item["source_row"]),
        }
        for family_id in sorted(family_records)
    ]
    first_batch = _select_first_batch(batch_families)

    return {
        "schema_version": "pvr-release-field-evidence-review-plan-v1",
        "plan_version": "release-field-evidence-review-plan-v1",
        "status": "plan_only_no_field_or_variant_decisions",
        "source_bindings": {
            NORMALIZED_PATH.as_posix(): _sha256(normalized_path),
            REVIEW_PATH.as_posix(): _sha256(review_path),
            QUEUE_PATH.as_posix(): _sha256(queue_path),
        },
        "historical_source": normalized["source"],
        "rights_status": (
            "historical metadata retained; current source-specific access/rights not revalidated; "
            "no collection authorized"
        ),
        "authority": {
            "canonical_catalog_changed": False,
            "canonical_uuid_count": 0,
            "variant_equivalence_count": 0,
            "owner_field_decision_count": 0,
            "held_release_count": 100,
        },
        "counts": {
            "source_records": len(records),
            "observation_ids": len({item["observation_id"] for item in records}),
            "families": len(family_records),
            "color_unknown": sum(item["field_evidence"]["color"]["state"] == "unknown" for item in records),
            "wheel_unknown": sum(item["field_evidence"]["wheel_type"]["state"] == "unknown" for item in records),
            "tampo_unknown": sum(item["field_evidence"]["tampo_description"]["state"] == "unknown" for item in records),
            "edition_unknown": sum(item["field_evidence"]["edition"]["state"] == "unknown" for item in records),
            "packaging_unknown": sum(item["field_evidence"]["packaging_variant"]["state"] == "unknown" for item in records),
            "variant_note_observed": sum(item["field_evidence"]["variant_note"]["raw_value"] is not None for item in records),
        },
        "field_contract": {
            "fields": list(FIELD_NAMES),
            "planner_states": ["observed_unverified", "unknown"],
            "future_human_states": ["confirmed", "conflicted", "rejected", "unknown"],
            "null_rule": "unknown is not equality and cannot support release grouping",
            "variant_note_rule": "retain literal text only; it is not a verified physical attribute",
        },
        "records": records,
        "first_review_batch": first_batch,
        "next_gates": [
            "owner reviews batch-01 exact field values/evidence and records append-only outcomes",
            "VAR-PLAN2 separately verifies current source access/rights and collection budget",
            "VAR-PLAN3 separately specifies identity-v2 and an output-blind variant evaluation",
        ],
        "exclusions": [
            "network or image/OCR collection",
            "database or runtime changes",
            "field inference or owner decisions",
            "variant equivalence or canonical promotion",
            "claiming 100 verified variants or 3,000 approved products",
        ],
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    counts = plan["counts"]
    batch = plan["first_review_batch"]
    lines = [
        "# Release field-evidence review plan v1",
        "",
        "This is an offline review workload,not a verified variant dataset. All100 source releases",
        "remain held and canonical UUID/variant-equivalence fields remain null.",
        "",
        "## Current evidence gap",
        "",
        f"The plan covers {counts['source_records']} source rows across {counts['families']} casting families.",
        f"Color/wheel/tampo are unknown for {counts['color_unknown']}/{counts['wheel_unknown']}/"
        f"{counts['tampo_unknown']} rows. {counts['variant_note_observed']} rows have a literal variant note,",
        "but notes such as `2nd Color` or `Zamac` do not reveal the actual physical color.",
        "",
        "## Proposed first manual batch",
        "",
        f"Review {batch['family_count']} complete families / {batch['source_row_count']} rows (limits5/15).",
        "The selection maximizes different evidence problems; it is not an accuracy sample.",
        "",
        "| Family | Casting | Family context | Rows | Why included |",
        "|---|---|---|---:|---|",
    ]
    for family in batch["families"]:
        reasons = ", ".join(family["new_coverage_at_selection"] or family["coverage_features"])
        lines.append(
            f"| `{family['family_review_id']}` | {family['casting_name']} | "
            f"{family['family_decision']} | {family['source_row_count']} | {reasons} |"
        )
    lines.extend(
        [
            "",
            "## Human review rules",
            "",
            "For every row,open the exact evidence pointer and confirm fields independently. Preserve null as",
            "unknown; record disagreements as conflicted. Compare same-casting siblings together,but choose",
            "same release,different release,or unresolved only from attributable evidence. A family merge/new",
            "casting decision never approves color,wheel,tampo or release equivalence.",
            "",
            "No new source access was performed. Historical licensing metadata is retained but current rights",
            "remain unverified. New collection belongs to VAR-PLAN2; identity and evaluation belong to VAR-PLAN3.",
            "",
        ]
    )
    return "\n".join(lines)


def _serialized(plan: Mapping[str, Any]) -> tuple[bytes, bytes]:
    json_bytes = (json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    markdown_bytes = render_markdown(plan).encode()
    return json_bytes, markdown_bytes


def publish(output: Path, root: Path = ROOT) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"exclusive output already exists: {output}")
    plan = build_plan(root)
    json_bytes, markdown_bytes = _serialized(plan)
    output.mkdir(parents=True)
    (output / "plan.json").write_bytes(json_bytes)
    (output / "plan.md").write_bytes(markdown_bytes)
    return plan


def check(output: Path, root: Path = ROOT) -> dict[str, Any]:
    if not output.is_dir():
        raise ValueError(f"missing output directory: {output}")
    expected = {"plan.json", "plan.md"}
    actual = {path.name for path in output.iterdir() if path.is_file()}
    if actual != expected:
        raise ValueError(f"output files differ: expected {sorted(expected)}, got {sorted(actual)}")
    plan = build_plan(root)
    json_bytes, markdown_bytes = _serialized(plan)
    if (output / "plan.json").read_bytes() != json_bytes:
        raise ValueError("plan.json drift")
    if (output / "plan.md").read_bytes() != markdown_bytes:
        raise ValueError("plan.md drift")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        plan = publish(args.output) if args.run else check(args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"release field-evidence plan rejected: {error}", file=sys.stderr)
        return 1
    batch = plan["first_review_batch"]
    print(
        f"PASS offline PLAN: 100 held rows; batch={batch['family_count']} families/"
        f"{batch['source_row_count']} rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
