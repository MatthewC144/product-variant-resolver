"""Materialize the PNMR-G1 owner authorization and narrow development-use overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from . import pointwise_no_match_readiness as readiness

FIT_COUNT = readiness.FIT_COUNT
HUMAN_DATASET_SHA256 = readiness.HUMAN_DATASET_SHA256
READINESS_PATH = readiness.OUTPUT
SELECTION_COUNT = readiness.SELECTION_COUNT
SOURCE_SHA256 = readiness.SOURCE_SHA256

DIRECTORY = Path("data/evaluation/image-search-pointwise-no-match-readiness-v1")
AUTHORIZATION_PATH = DIRECTORY / "pnmr-g1-owner-authorization.json"
OVERLAY_PATH = DIRECTORY / "governance-overlay.json"
AUTHORIZATION_SCHEMA = "pvr-pnmr-g1-owner-authorization-v1"
OVERLAY_SCHEMA = "pvr-pointwise-no-match-governance-overlay-v1"
CANDIDATE_SET_SHA256 = "08d08e668dfd56f82e638fe27f876285af8dd5300da2b34103ffe636416b5c53"
SPLIT_ASSIGNMENT_SHA256 = "e16475d94435d69dfb188c8c38374997633d18167f04086abb1127cbb27f4817"
OWNER_AUTHORIZATION_TEXT = (
    "我批准 PNMR-G1：僅針對 human dataset SHA-256 "
    "`68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188` 中的 "
    "no-match candidate set SHA-256 "
    "`08d08e668dfd56f82e638fe27f876285af8dd5300da2b34103ffe636416b5c53`，綁定 "
    "frozen catalog SHA-256 "
    "`b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4`，允許建立 "
    "versioned governance overlay，並依 frozen 32/20 split 用於 Pointwise development "
    "calibration-fit 與 threshold-selection。此批准不授權 final-test retuning、runtime "
    "activation、公開逐筆查詢資料或宣稱 manufacturer/global no-match truth。"
)
ALLOWED_ACTIONS = [
    "materialize_versioned_governance_overlay",
    "pointwise_development_calibration_fit",
    "pointwise_development_threshold_selection",
]
PROHIBITED_ACTIONS = [
    "final_test_retuning",
    "runtime_activation",
    "public_row_level_query_data",
    "manufacturer_or_global_no_match_claim",
]


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


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _content_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_authorization(root: Path) -> dict[str, Any]:
    readiness_payload = readiness.check(root, require_local_inputs=True)
    if readiness_payload != readiness.build_readiness(root):
        raise ValueError("PNMR-G1 readiness is stale")
    audit = readiness_payload["audit"]
    split = readiness_payload["prospective_split"]
    if (
        audit.get("candidate_set_sha256") != CANDIDATE_SET_SHA256
        or split.get("assignment_sha256") != SPLIT_ASSIGNMENT_SHA256
    ):
        raise ValueError("PNMR-G1 approved candidate set or split differs from readiness")
    body: dict[str, Any] = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "gate": "PNMR-G1",
        "authorized_by": "project_owner",
        "authorization_date": "2026-10-05",
        "authorization_text": OWNER_AUTHORIZATION_TEXT,
        "authorization_text_sha256": hashlib.sha256(OWNER_AUTHORIZATION_TEXT.encode()).hexdigest(),
        "readiness_path": str(READINESS_PATH),
        "readiness_sha256": _file_sha256(root / READINESS_PATH),
        "human_dataset_sha256": HUMAN_DATASET_SHA256,
        "candidate_set_sha256": CANDIDATE_SET_SHA256,
        "catalog_snapshot_sha256": SOURCE_SHA256,
        "split_assignment_sha256": SPLIT_ASSIGNMENT_SHA256,
        "fit_count": FIT_COUNT,
        "selection_count": SELECTION_COUNT,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "prohibited_actions": list(PROHIBITED_ACTIONS),
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def _validate_authorization(payload: dict[str, Any], root: Path) -> None:
    expected = build_authorization(root)
    if payload != expected:
        raise ValueError("PNMR-G1 owner authorization is stale, generic, or out of scope")
    body = {key: value for key, value in payload.items() if key != "authorization_sha256"}
    if payload.get("authorization_sha256") != _content_sha256(body):
        raise ValueError("PNMR-G1 owner authorization checksum is stale")


def build_overlay(root: Path, authorization: dict[str, Any]) -> dict[str, Any]:
    _validate_authorization(authorization, root)
    body: dict[str, Any] = {
        "schema_version": OVERLAY_SCHEMA,
        "overlay_version": "pointwise-no-match-governance-overlay-v1",
        "status": "active_for_bound_development_only",
        "materialization_date": "2026-10-05",
        "materialized_by": "product_variant_resolver.pointwise_no_match_governance",
        "owner_authorization_sha256": authorization["authorization_sha256"],
        "owner_response_sha256": authorization["authorization_text_sha256"],
        "readiness_sha256": authorization["readiness_sha256"],
        "bindings": {
            "human_dataset_sha256": HUMAN_DATASET_SHA256,
            "candidate_set_sha256": CANDIDATE_SET_SHA256,
            "catalog_snapshot_sha256": SOURCE_SHA256,
            "split_assignment_sha256": SPLIT_ASSIGNMENT_SHA256,
            "fit_count": FIT_COUNT,
            "selection_count": SELECTION_COUNT,
        },
        "permissions": {
            "pointwise_development_calibration_fit": True,
            "pointwise_development_threshold_selection": True,
            "final_test_retuning": False,
            "runtime_activation": False,
            "public_row_level_query_data": False,
            "manufacturer_or_global_no_match_claim": False,
        },
        "scope": {
            "label": "catalog_relative_no_match",
            "publication": "aggregate_only",
            "source_contract_overwritten": False,
            "source_wide_permission_promotion": False,
        },
        "guardrails": {
            "resolver_output_consulted_before_split": False,
            "neural_output_consulted_before_split": False,
            "final_test_cases_read": 0,
            "final_test_cases_scored": 0,
            "runtime_default_changed": False,
        },
        "next_allowed_action": "run_pointwise_no_match_development_calibration",
    }
    return {**body, "overlay_sha256": _content_sha256(body)}


def _validate_overlay(payload: dict[str, Any], root: Path, authorization: dict[str, Any]) -> None:
    expected = build_overlay(root, authorization)
    if payload != expected:
        raise ValueError("PNMR-G1 governance overlay is stale or out of scope")
    body = {key: value for key, value in payload.items() if key != "overlay_sha256"}
    if payload.get("overlay_sha256") != _content_sha256(body):
        raise ValueError("PNMR-G1 governance overlay checksum is stale")


def materialize(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    authorization_path = root / AUTHORIZATION_PATH
    overlay_path = root / OVERLAY_PATH
    if authorization_path.exists() or overlay_path.exists():
        raise FileExistsError("PNMR-G1 authorization or overlay already exists")
    authorization = build_authorization(root)
    overlay = build_overlay(root, authorization)
    authorization_path.write_bytes(_canonical_bytes(authorization))
    overlay_path.write_bytes(_canonical_bytes(overlay))
    return authorization, overlay


def check(root: Path) -> dict[str, Any]:
    authorization = _load_object(root / AUTHORIZATION_PATH)
    overlay = _load_object(root / OVERLAY_PATH)
    _validate_authorization(authorization, root)
    _validate_overlay(overlay, root, authorization)
    return overlay


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize or validate PNMR-G1 governance")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if not args.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        _authorization, overlay = materialize(root)
        print(json.dumps(overlay, indent=2, sort_keys=True))
        return
    if args.check:
        check(root)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
