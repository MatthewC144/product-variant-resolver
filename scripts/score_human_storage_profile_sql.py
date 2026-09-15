#!/usr/bin/env python3
"""Score already-published HSP-3 raw evidence without rerunning retrieval or SQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports/human-storage-profile-hsp3-raw-v4.json"
OUTPUT = ROOT / "reports/human-storage-profile-hsp3-evaluation-v4.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def score(raw_path: Path) -> dict[str, Any]:
    raw = json.loads(raw_path.read_bytes())
    require(raw.get("schema_version") == "pvr-human-storage-hsp3-raw-v1", "raw schema differs")
    require(raw.get("publication_status") == "raw_unscored", "input is not raw unscored evidence")
    require(
        raw["cleanup"]["errors"] == [] and raw["cleanup"]["remaining_owned_resources"] == [],
        "isolated resources were not fully cleaned",
    )
    result = raw["runner_result"]
    rows = result["correctness_rows"]
    require(len(rows) == 199, "correctness row count differs")
    parity = []
    for row in rows:
        ok = (
            row["file"]["status"] == row["postgres"]["status"] == row["default"]["status"] == 200
            and row["file"]["human"] == row["postgres"]["human"]
            and row["file"]["canonical_body"]
            == row["postgres"]["canonical_body"]
            == row["default"]["canonical_body"]
            and row["file"]["request_id"]
            == row["postgres"]["request_id"]
            == row["default"]["request_id"]
            == row["request_id"]
        )
        parity.append(ok)
    require(all(parity), "file/PostgreSQL/default per-case parity failed")
    role = result["reader_role"]
    require(
        role["attributes"]
        == {
            "rolsuper": False,
            "rolinherit": False,
            "rolcreaterole": False,
            "rolcreatedb": False,
            "rolcanlogin": True,
        },
        "reader role attributes differ",
    )
    require(
        role["table_privileges"] == {"hk_document": ["SELECT"], "hk_snapshot": ["SELECT"]},
        "reader role is not SELECT-only",
    )
    require(
        all(item["denied"] and item["sqlstate"] == "42501" for item in role["write_denials"]),
        "reader write denial failed",
    )
    require(
        all(
            item["health_status"] == 503 and item["resolve_status"] == 503
            for item in result["startup_failures"]
        ),
        "startup failure matrix failed",
    )
    require(
        all(
            item["first_status"] == 503
            and item["after_restore_health"] == 503
            and item["after_restore_resolve"] == 503
            for item in result["poststartup_failures"]
        ),
        "post-start latch matrix failed",
    )
    expected_invalid = {
        "malformed_json": 400,
        "wrong_content_type": 415,
        "blank_title": 422,
        "title_501": 422,
        "debug_disabled": 422,
    }
    require(
        {item["case"]: item["status"] for item in result["invalid_http"]} == expected_invalid
        and all(item["storage_probes"] == 0 for item in result["invalid_http"]),
        "invalid HTTP contract/probe boundary failed",
    )
    require(
        result["canonical_before_sha256"] == result["canonical_after_sha256"],
        "canonical tables changed",
    )
    require(result["source_and_image_binding"] is True, "source/image binding failed")
    by_type: dict[str, int] = {}
    empty = 0
    for row in rows:
        by_type[row["case_type"]] = by_type.get(row["case_type"], 0) + 1
        empty += int(not row["file"]["human"]["candidates"])
    return {
        "schema_version": "pvr-human-storage-hsp3-evaluation-v1",
        "verdict": "PASS",
        "raw_file": str(raw_path.relative_to(ROOT) if raw_path.is_relative_to(ROOT) else raw_path),
        "raw_sha256": sha(raw_path),
        "raw_published_before_scoring": True,
        "exact_parity_cases": sum(parity),
        "required_parity_cases": 199,
        "case_type_counts": by_type,
        "empty_candidate_cases_retained": empty,
        "gates": {
            "rank_score_type_uuid_payload_work_parity": True,
            "canonical_body_unchanged": True,
            "select_only_reader": True,
            "startup_failure_matrix": True,
            "poststartup_latch_matrix": True,
            "invalid_http_no_storage_probe": True,
            "canonical_seven_tables_unchanged": True,
            "owned_resource_cleanup": True,
            "source_and_image_bound": True,
        },
        "scope": "HSP-3 fixed199 correctness and failure evidence only; no cost, final105, real3k, production or canonical promotion claim",
    }


def publish(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink() or path.parent != ROOT / "reports":
        raise ValueError("evaluation must be a new exclusive reports/ file")
    descriptor, name = tempfile.mkstemp(prefix=".hsp3-score-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(
                (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
            )
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = score(args.raw)
    publish(args.output, result)
    print(f"HSP-3 score: {result['verdict']}; exact parity={result['exact_parity_cases']}/199")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
