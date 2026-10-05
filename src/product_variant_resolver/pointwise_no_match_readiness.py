"""Read-only readiness audit for real catalog-relative no-match development evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .identity import normalize_text

VERSION = "pointwise-no-match-readiness-v1"
SCHEMA_VERSION = "pvr-pointwise-no-match-readiness-v1"
HUMAN_DATASET = Path("data/human_labeled_names.json")
SOURCE = Path("data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json")
OUTPUT = Path("data/evaluation/image-search-pointwise-no-match-readiness-v1/readiness.json")
HUMAN_DATASET_SHA256 = "68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188"
SOURCE_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
HUMAN_RECORD_COUNT = 101
SOURCE_RECORD_COUNT = 1763
FIT_COUNT = 32
SELECTION_COUNT = 20
SPLIT_SALT = "pvr:pointwise-no-match-development:fit-selection:v1"
REQUIRED_EXCLUSIONS = ("calibration_training", "threshold_selection")

Partition = Literal["calibration_fit", "threshold_selection"]


@dataclass(frozen=True, slots=True)
class NoMatchCandidate:
    case_id: str
    query: str
    brand: str
    casting: str


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    return value


def classify_candidates(
    human_records: Sequence[object], source_records: Sequence[object]
) -> tuple[list[NoMatchCandidate], dict[str, int]]:
    source_families: set[tuple[str, str]] = set()
    source_brands: set[str] = set()
    for index, raw in enumerate(source_records):
        if not isinstance(raw, dict):
            raise TypeError(f"source record {index} must be an object")
        if raw.get("parse_status") != "parsed":
            raise ValueError(f"source record {index} is not parsed")
        brand = normalize_text(_string(raw.get("brand"), "source brand"))
        casting = normalize_text(_string(raw.get("casting_name"), "source casting"))
        if not brand or not casting:
            raise ValueError(f"source record {index} has an empty family key")
        source_brands.add(brand)
        source_families.add((brand, casting))

    candidates: list[NoMatchCandidate] = []
    case_ids: set[str] = set()
    paired_confirmed_count = 0
    present_count = 0
    missing_query_count = 0
    same_brand_absent_count = 0
    other_brand_absent_count = 0
    for index, raw in enumerate(human_records):
        if not isinstance(raw, dict):
            raise TypeError(f"human record {index} must be an object")
        case_id = _string(raw.get("case_id"), "human case_id")
        if not case_id or case_id in case_ids:
            raise ValueError("human case IDs must be non-empty and unique")
        case_ids.add(case_id)
        query = normalize_text(_string(raw.get("initial_name") or "", "initial_name"))
        if not query:
            missing_query_count += 1
            continue
        if raw.get("human_label_confidence") != "confirmed":
            continue
        brand = normalize_text(_string(raw.get("human_label_brand"), "human label brand"))
        casting = normalize_text(_string(raw.get("human_label_casting"), "human label casting"))
        if not brand or not casting:
            raise ValueError(f"human record {case_id} has an empty family key")
        paired_confirmed_count += 1
        if (brand, casting) in source_families:
            present_count += 1
            continue
        if brand in source_brands:
            same_brand_absent_count += 1
        else:
            other_brand_absent_count += 1
        candidates.append(NoMatchCandidate(case_id, query, brand, casting))

    if len({candidate.query for candidate in candidates}) != len(candidates):
        raise ValueError("no-match candidate queries must be unique")
    if len({(candidate.brand, candidate.casting) for candidate in candidates}) != len(candidates):
        raise ValueError("no-match candidate identities must be unique")
    counts = {
        "paired_confirmed_count": paired_confirmed_count,
        "exact_family_present_count": present_count,
        "exact_family_absent_count": len(candidates),
        "same_brand_absent_count": same_brand_absent_count,
        "other_brand_absent_count": other_brand_absent_count,
        "missing_query_count": missing_query_count,
        "source_family_count": len(source_families),
    }
    return candidates, counts


def _candidate_digest(candidates: list[NoMatchCandidate]) -> str:
    rows = [
        [candidate.case_id, candidate.query, candidate.brand, candidate.casting]
        for candidate in sorted(candidates, key=lambda item: item.case_id)
    ]
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest()


def _prospective_split(candidates: list[NoMatchCandidate]) -> tuple[dict[str, Partition], str]:
    if len(candidates) != FIT_COUNT + SELECTION_COUNT:
        raise ValueError("prospective no-match split requires exactly 52 candidates")
    ordered = sorted(
        candidates,
        key=lambda item: hashlib.sha256(f"{SPLIT_SALT}\n{item.case_id}".encode()).hexdigest(),
    )
    fit_ids = {candidate.case_id for candidate in ordered[:FIT_COUNT]}
    assignment: dict[str, Partition] = {
        candidate.case_id: (
            "calibration_fit" if candidate.case_id in fit_ids else "threshold_selection"
        )
        for candidate in sorted(candidates, key=lambda item: item.case_id)
    }
    digest = hashlib.sha256(
        _canonical_bytes([[case_id, assignment[case_id]] for case_id in sorted(assignment)])
    ).hexdigest()
    return assignment, digest


def build_readiness(root: Path) -> dict[str, Any]:
    human_path = root / HUMAN_DATASET
    source_path = root / SOURCE
    if _sha256(human_path) != HUMAN_DATASET_SHA256:
        raise ValueError("human noisy-name dataset differs from the frozen input")
    if _sha256(source_path) != SOURCE_SHA256:
        raise ValueError("catalog snapshot differs from the frozen input")
    human = _load_object(human_path)
    source = _load_object(source_path)
    if human.get("dataset_version") != "human-labeled-real-noisy-v1":
        raise ValueError("unexpected human dataset version")
    records = human.get("records")
    source_records = source.get("records")
    if not isinstance(records, list) or len(records) != HUMAN_RECORD_COUNT:
        raise ValueError("human dataset record count changed")
    if not isinstance(source_records, list) or len(source_records) != SOURCE_RECORD_COUNT:
        raise ValueError("catalog snapshot record count changed")
    usage_scope = human.get("usage_scope")
    excluded_from = human.get("excluded_from")
    if not isinstance(usage_scope, list) or "future_catalog_alignment" not in usage_scope:
        raise ValueError("human dataset no longer permits future catalog alignment")
    if not isinstance(excluded_from, list) or not all(
        exclusion in excluded_from for exclusion in REQUIRED_EXCLUSIONS
    ):
        raise ValueError("human dataset calibration exclusions changed")

    candidates, counts = classify_candidates(records, source_records)
    if counts != {
        "paired_confirmed_count": 91,
        "exact_family_present_count": 39,
        "exact_family_absent_count": 52,
        "same_brand_absent_count": 46,
        "other_brand_absent_count": 6,
        "missing_query_count": 10,
        "source_family_count": 677,
    }:
        raise ValueError("no-match readiness counts changed")
    assignment, split_sha256 = _prospective_split(candidates)
    if sum(value == "calibration_fit" for value in assignment.values()) != FIT_COUNT:
        raise ValueError("prospective calibration-fit count changed")
    if sum(value == "threshold_selection" for value in assignment.values()) != SELECTION_COUNT:
        raise ValueError("prospective threshold-selection count changed")

    return {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "status": "owner_authorization_required",
        "inputs": {
            "human_dataset": {
                "path": str(HUMAN_DATASET),
                "sha256": HUMAN_DATASET_SHA256,
                "record_count": HUMAN_RECORD_COUNT,
                "dataset_version": "human-labeled-real-noisy-v1",
            },
            "catalog_snapshot": {
                "path": str(SOURCE),
                "sha256": SOURCE_SHA256,
                "record_count": SOURCE_RECORD_COUNT,
            },
        },
        "candidate_rule": {
            "query_field": "initial_name",
            "required_human_label_confidence": "confirmed",
            "absence_definition": "normalized_exact_brand_and_casting_family_absent_from_frozen_catalog",
            "normalizer": "identity.normalize_text-v1",
        },
        "audit": {
            **counts,
            "candidate_set_sha256": _candidate_digest(candidates),
        },
        "prospective_split": {
            "salt": SPLIT_SALT,
            "fit_count": FIT_COUNT,
            "selection_count": SELECTION_COUNT,
            "assignment_sha256": split_sha256,
        },
        "permission": {
            "current_usage_allows_alignment_audit": True,
            "current_usage_allows_calibration_training": False,
            "current_usage_allows_threshold_selection": False,
            "permission_changed": False,
            "blockers": [
                "human_dataset_excludes_calibration_training",
                "human_dataset_excludes_threshold_selection",
            ],
        },
        "guardrails": {
            "row_level_output_persisted": False,
            "resolver_loaded": False,
            "neural_model_loaded": False,
            "development_cases_scored": 0,
            "final_test_cases_read": 0,
            "final_test_cases_scored": 0,
            "calibration_artifact_written": False,
            "policy_artifact_written": False,
            "runtime_default_changed": False,
        },
        "authority_note": (
            "Candidate labels are human-confirmed but absence is relative only to the frozen "
            "1,763-record third-party catalog snapshot; it is not manufacturer/global truth."
        ),
        "next_allowed_action": (
            "request_owner_authorization_for_hash_bound_no_match_development_overlay"
        ),
    }


def _contains_row_level_key(value: object) -> bool:
    forbidden = {
        "case",
        "case_id",
        "case_ids",
        "cases",
        "query",
        "queries",
        "records",
        "labels",
        "assignment",
    }
    if isinstance(value, dict):
        return any(key in forbidden or _contains_row_level_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def check(root: Path, *, require_local_inputs: bool = False) -> dict[str, Any]:
    path = root / OUTPUT
    payload = _load_object(path)
    if _contains_row_level_key(payload):
        raise ValueError("readiness artifact contains row-level output")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("version") != VERSION:
        raise ValueError("readiness artifact version changed")
    if payload.get("status") != "owner_authorization_required":
        raise ValueError("readiness artifact status changed")
    audit = payload.get("audit")
    permission = payload.get("permission")
    guardrails = payload.get("guardrails")
    split = payload.get("prospective_split")
    if not all(isinstance(item, dict) for item in (audit, permission, guardrails, split)):
        raise TypeError("readiness artifact sections must be objects")
    assert isinstance(audit, dict)
    assert isinstance(permission, dict)
    assert isinstance(guardrails, dict)
    assert isinstance(split, dict)
    if audit.get("exact_family_absent_count") != FIT_COUNT + SELECTION_COUNT:
        raise ValueError("readiness candidate count changed")
    if split.get("fit_count") != FIT_COUNT or split.get("selection_count") != SELECTION_COUNT:
        raise ValueError("readiness split counts changed")
    if permission.get("blockers") != [
        "human_dataset_excludes_calibration_training",
        "human_dataset_excludes_threshold_selection",
    ]:
        raise ValueError("readiness permission blockers changed")
    if permission.get("permission_changed") is not False:
        raise ValueError("readiness must not change source permission")
    expected_guardrails = {
        "row_level_output_persisted": False,
        "resolver_loaded": False,
        "neural_model_loaded": False,
        "development_cases_scored": 0,
        "final_test_cases_read": 0,
        "final_test_cases_scored": 0,
        "calibration_artifact_written": False,
        "policy_artifact_written": False,
        "runtime_default_changed": False,
    }
    if guardrails != expected_guardrails:
        raise ValueError("readiness negative guardrails changed")
    if require_local_inputs:
        expected = build_readiness(root)
        if _canonical_bytes(payload) != _canonical_bytes(expected):
            raise ValueError("readiness artifact differs from frozen inputs")
    return payload


def materialize(root: Path) -> dict[str, Any]:
    path = root / OUTPUT
    if path.exists():
        raise FileExistsError("no-match readiness artifact already exists")
    payload = build_readiness(root)
    path.parent.mkdir(parents=True, exist_ok=False)
    path.write_bytes(_canonical_bytes(payload))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit real no-match development readiness")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-readiness-only", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if not args.acknowledge_readiness_only:
            parser.error("--run requires --acknowledge-readiness-only")
        payload = materialize(root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if args.check:
        check(root, require_local_inputs=(root / SOURCE).exists())
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
