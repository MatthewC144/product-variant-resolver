#!/usr/bin/env python3
"""Validate one owner decision event against the frozen batch01 packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = ROOT / "reports/release-field-review-batch-01/packet.json"
MANIFEST_PATH = ROOT / "reports/release-field-review-batch-01/manifest.json"
PHYSICAL_FIELDS = {"color","wheel_type","tampo_description","edition","packaging_variant"}
FIELD_DECISIONS = {"confirmed","unknown","conflicted","rejected"}
RELATIONSHIP_DECISIONS = {"same_release","different_release","unresolved"}


def _reject_duplicate_keys(pairs: list[tuple[str,Any]]) -> dict[str,Any]:
    result: dict[str,Any] = {}
    for key,value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str,Any]:
    value = json.loads(path.read_text(),object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value,dict):
        raise ValueError(f"{path}: expected object")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_event(path: Path) -> dict[str,Any]:
    packet = _load(PACKET_PATH)
    manifest = _load(MANIFEST_PATH)
    event = _load(path)
    if event.get("schema_version") != "pvr-release-field-review-decision-event-v1":
        raise ValueError("unexpected event schema")
    if event.get("packet_sha256") != _sha(PACKET_PATH):
        raise ValueError("event packet SHA mismatch")
    if manifest["artifact_sha256"]["packet.json"] != _sha(PACKET_PATH):
        raise ValueError("manifest packet SHA mismatch")
    if event.get("canonical_promotion_authorized") is not False:
        raise ValueError("decision event cannot authorize canonical promotion")

    authorization = event.get("owner_authorization")
    if not isinstance(authorization,dict):
        raise ValueError("owner authorization missing")
    for field in ("question","response","interpreted_scope","recorded_at_utc"):
        if not isinstance(authorization.get(field),str) or not authorization[field].strip():
            raise ValueError(f"owner authorization {field} missing")
    if authorization["response"] != "繼續下一步":
        raise ValueError("unexpected owner response")

    family_id = event.get("family_review_id")
    families = [family for family in packet["families"] if family["family_review_id"] == family_id]
    if len(families) != 1:
        raise ValueError("event family is not uniquely present in packet")
    family = families[0]
    rows = {row["source_record_id"]: row for row in family["rows"]}

    candidate_fields: dict[tuple[str,str],Any] = {}
    for source_id,row in rows.items():
        for claim in row["candidate_secondary_claims"]:
            for field,value in claim["candidate_fields"].items():
                key = (source_id,field)
                if key in candidate_fields and candidate_fields[key] != value:
                    raise ValueError(f"conflicting packet candidates for {source_id}/{field}")
                candidate_fields[key] = value

    required_fields = {
        (source_id,field)
        for source_id in rows
        for field in PHYSICAL_FIELDS
    } | set(candidate_fields)
    decisions = event.get("field_decisions")
    if not isinstance(decisions,list):
        raise ValueError("field decisions missing")
    seen_fields: set[tuple[str,str]] = set()
    calculated = {"confirmed":0,"unknown":0,"conflicted":0,"rejected":0}
    for decision in decisions:
        source_id = decision.get("source_record_id")
        field = decision.get("field")
        if source_id not in rows or not isinstance(field,str):
            raise ValueError("field decision references an unknown row/field")
        allowed_fields = set(rows[source_id]["raw_fields"]) | {
            candidate_field
            for candidate_source,candidate_field in candidate_fields
            if candidate_source == source_id
        }
        if field not in allowed_fields:
            raise ValueError(f"field decision is outside packet: {source_id}/{field}")
        key = (source_id,field)
        if key in seen_fields:
            raise ValueError(f"duplicate field decision: {source_id}/{field}")
        seen_fields.add(key)
        outcome = decision.get("decision")
        if outcome not in FIELD_DECISIONS:
            raise ValueError(f"invalid field decision: {outcome}")
        if not isinstance(decision.get("reason"),str) or not decision["reason"].strip():
            raise ValueError(f"field decision reason missing: {source_id}/{field}")
        references = decision.get("evidence_references")
        if not isinstance(references,list) or not references or not all(
            isinstance(reference,str) and reference for reference in references
        ):
            raise ValueError(f"field evidence missing: {source_id}/{field}")
        reviewed_value = decision.get("reviewed_value")
        if outcome == "confirmed":
            allowed_values = {json.dumps(rows[source_id]["raw_fields"].get(field),sort_keys=True)}
            if key in candidate_fields:
                allowed_values.add(json.dumps(candidate_fields[key],sort_keys=True))
            if reviewed_value is None or json.dumps(reviewed_value,sort_keys=True) not in allowed_values:
                raise ValueError(f"confirmed value is not grounded: {source_id}/{field}")
        elif outcome == "unknown" and reviewed_value is not None:
            raise ValueError(f"unknown decision must keep null: {source_id}/{field}")
        if field in PHYSICAL_FIELDS and key not in candidate_fields and outcome != "unknown":
            raise ValueError(f"unsupported physical field must remain unknown: {source_id}/{field}")
        calculated[outcome] += 1
    if seen_fields != required_fields:
        missing = sorted(required_fields - seen_fields)
        extra = sorted(seen_fields - required_fields)
        raise ValueError(f"required field decisions differ;missing={missing},extra={extra}")

    packet_pairs = {
        tuple(sorted((pair["left_source_record_id"],pair["right_source_record_id"])))
        for pair in family["relationship_pairs"]
    }
    relationship_decisions = event.get("relationship_decisions")
    if not isinstance(relationship_decisions,list):
        raise ValueError("relationship decisions missing")
    seen_pairs: set[tuple[str,str]] = set()
    relationship_counts = {outcome:0 for outcome in RELATIONSHIP_DECISIONS}
    for decision in relationship_decisions:
        pair = tuple(sorted((decision.get("left_source_record_id"),decision.get("right_source_record_id"))))
        if pair not in packet_pairs or pair in seen_pairs:
            raise ValueError(f"invalid/duplicate relationship pair: {pair}")
        seen_pairs.add(pair)
        outcome = decision.get("decision")
        if outcome not in RELATIONSHIP_DECISIONS:
            raise ValueError(f"invalid relationship decision: {outcome}")
        if not isinstance(decision.get("reason"),str) or not decision["reason"].strip():
            raise ValueError(f"relationship reason missing: {pair}")
        references = decision.get("evidence_references")
        if not isinstance(references,list) or not references:
            raise ValueError(f"relationship evidence missing: {pair}")
        relationship_counts[outcome] += 1
    if seen_pairs != packet_pairs:
        raise ValueError("event does not decide every family relationship pair")

    expected_summary = {
        "required_field_decisions":len(required_fields),
        "confirmed_fields":calculated["confirmed"],
        "unknown_fields":calculated["unknown"],
        "conflicted_fields":calculated["conflicted"],
        "rejected_fields":calculated["rejected"],
        "relationship_pairs":len(packet_pairs),
        "same_release":relationship_counts["same_release"],
        "different_release":relationship_counts["different_release"],
        "unresolved":relationship_counts["unresolved"],
        "canonical_changes":0,
    }
    if event.get("summary") != expected_summary:
        raise ValueError(f"event summary mismatch;expected {expected_summary}")
    if event.get("review_scope_complete") is not True:
        raise ValueError("family review scope must be explicitly complete")
    return event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",type=Path,required=True)
    args = parser.parse_args()
    try:
        event = validate_event(args.check)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(f"decision event rejected: {error}",file=sys.stderr)
        return 1
    print(
        f"PASS owner event: family={event['family_review_id']};"
        f"fields={event['summary']['required_field_decisions']};"
        f"pairs={event['summary']['relationship_pairs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
