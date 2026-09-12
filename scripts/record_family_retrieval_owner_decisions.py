#!/usr/bin/env python3
"""Record the project owner's approval of the frozen T48 query/reference pairs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EVALUATION = DATA / "evaluation/family-retrieval-v1"
QUERY_PACK = EVALUATION / "query-pack.json"
QUERY_PACK_MANIFEST = EVALUATION / "query-pack-manifest.json"
OUTPUT = EVALUATION / "owner-decisions.json"
APPROVED_QUERY_PACK_SHA256 = (
    "26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733"
)
DECIDED_AT = "2026-09-12T16:50:40Z"


def _load_builder():
    path = ROOT / "scripts/build_family_retrieval_benchmark.py"
    spec = importlib.util.spec_from_file_location("family_retrieval_benchmark", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load family-retrieval benchmark contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_owner_decisions() -> tuple[dict[str, Any], Any]:
    contract = _load_builder()
    if _sha256(QUERY_PACK) != APPROVED_QUERY_PACK_SHA256:
        raise ValueError("query pack changed after project-owner confirmation")
    query_pack, expected_manifest = contract._load_and_validate_query_pack(
        query_pack_path=QUERY_PACK,
        registry_path=DATA / "review_family_registry.json",
        registry_manifest_path=DATA / "review_family_registry_manifest.json",
        projection_path=DATA / "review_family_knowledge.json",
        projection_manifest_path=DATA / "review_family_knowledge_manifest.json",
        human_path=DATA / "human_backed_catalog.json",
        human_manifest_path=DATA / "human_backed_catalog_manifest.json",
    )
    contract._validate_query_pack_manifest(
        contract._load(QUERY_PACK_MANIFEST), expected_manifest
    )
    registry = contract._load(DATA / "review_family_registry.json")
    merge_by_id = {
        item["source_family_review_id"]: item for item in registry["merge_links"]
    }
    decisions: list[dict[str, Any]] = []
    for case in query_pack["cases"]:
        reference = case["review_reference"]
        if case["case_type"] == "positive_family":
            family_id = reference["review_family_id"]
            expected = {
                "knowledge_type": "review_family",
                "review_family_id": family_id,
            }
            reason = (
                "Project owner confirmed this frozen "
                f"{case['challenge_style']} query as a fair relevance question for "
                f"review family {family_id}."
            )
        elif case["case_type"] == "merge_control":
            family_id = reference["source_family_review_id"]
            target_id = merge_by_id[family_id]["target_casting_id"]
            expected = {
                "casting_id": target_id,
                "forbidden_review_family_id": family_id,
                "knowledge_type": "provisional_variant",
            }
            reason = (
                f"Project owner confirmed this query should reuse existing casting {target_id} "
                f"and must not create duplicate review family {family_id}."
            )
        elif case["case_type"] == "hold_control":
            family_id = reference["review_family_id"]
            expected = {
                "expected_materialized": False,
                "forbidden_review_family_id": family_id,
            }
            reason = (
                f"Project owner confirmed held identity {family_id} must remain unmaterialized "
                "until its lineage ambiguity is separately resolved."
            )
        else:
            expected = {
                "expected_candidate_count": 0,
                "zero_token_overlap": True,
            }
            reason = (
                "Project owner confirmed this synthetic zero-overlap query is unrelated to the "
                "frozen Human Knowledge corpus and should return no candidates."
            )
        decisions.append(
            {
                "case_id": case["case_id"],
                "decided_at": DECIDED_AT,
                "decided_by": "project_owner",
                "decision": "approve",
                "expected": expected,
                "reason": reason,
            }
        )

    payload = {
        "benchmark_version": contract.BENCHMARK_VERSION,
        "decided_at": DECIDED_AT,
        "decided_by": "project_owner",
        "decision_version": contract.DECISIONS_VERSION,
        "decisions": decisions,
        "query_pack_file": QUERY_PACK.name,
        "query_pack_sha256": APPROVED_QUERY_PACK_SHA256,
        "schema_version": contract.DECISIONS_SCHEMA,
        "status": "approved_for_test_evaluation",
    }
    return payload, contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        payload, contract = build_owner_decisions()
        expected = contract._stable_json(payload)
        if arguments.check:
            contract._check_text(arguments.output, expected)
            print("family retrieval owner decisions are reproducible")
        else:
            contract._atomic_write(arguments.output, expected)
            print(f"wrote {arguments.output}")
        return 0
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
