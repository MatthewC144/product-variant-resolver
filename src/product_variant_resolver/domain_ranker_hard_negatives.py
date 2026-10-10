"""DRSP-T3 deterministic, one-shot, train-only hard-negative mining.

The miner consumes the already frozen T2 Top-25 pools.  It never retrieves,
scores, trains, selects a model, calibrates, evaluates a final set, or changes
runtime behavior.  A minimized row-level package is emitted only when every
release-gate check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .domain_ranker_governance import (
    CATALOG_PATH,
    CATALOG_SHA256,
    GOVERNANCE_V2_PATH,
    NEGATIVE_HOLDOUT_COUNT,
    NEGATIVE_HOLDOUT_PATH,
    NEGATIVE_HOLDOUT_SHA256,
    POSITIVE_DATASET_PATH,
    POSITIVE_DATASET_SHA256,
    POSITIVE_SPLIT_SHA256,
    POSITIVE_TEST_COUNT,
    check_publication_amendment,
)
from .domain_ranker_partitions import (
    AUTHORIZATION_PATH as T2_AUTHORIZATION_PATH,
)
from .domain_ranker_partitions import (
    LOCAL_PARTITIONS_PATH,
    LOCAL_POOLS_PATH,
    POOL_MANIFEST_PATH,
    RANKER_TRAIN_TARGET,
    SPLIT_MANIFEST_PATH,
)
from .identity import normalize_text
from .image_search_evaluation import (
    load_frozen_split,
    load_image_search_dataset,
    load_source_records,
)

VERSION = "domain-ranker-selective-prediction-development-v1"
SCHEMA_AUTHORIZATION = "pvr-drsp-t3-owner-authorization-v1"
SCHEMA_PAIR = "pvr-drsp-t3-binary-hard-negative-pair-v1"
SCHEMA_MANIFEST = "pvr-drsp-t3-public-hard-negative-pairs-manifest-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-selective-prediction-development-v1")
PACKAGE_DIRECTORY = DIRECTORY / "public-hard-negative-pairs-v1"
AUTHORIZATION_OUTPUT_PATH = PACKAGE_DIRECTORY / "owner-authorization.json"
PAIR_PATH = PACKAGE_DIRECTORY / "pairs.jsonl"
MANIFEST_PATH = PACKAGE_DIRECTORY / "manifest.json"
DATA_CARD_PATH = PACKAGE_DIRECTORY / "DATA_CARD.md"
NOTICE_PATH = PACKAGE_DIRECTORY / "NOTICE.md"

FROZEN_GOVERNANCE_V2_FILE_SHA256 = (
    "2ce83d6790f05ad4c580f835b2b749809ce906860c37f4f385b8512a60937302"
)
FROZEN_T2_AUTHORIZATION_FILE_SHA256 = (
    "c94cd201a0705ce7fed26cb21b66fa2a45e9944fe4c740bc6b4ed85e6e6be928"
)
FROZEN_T2_SPLIT_MANIFEST_FILE_SHA256 = (
    "3555b8177def3347200f82319b390cd8b702a1ee780b3e57f118ab10f091e60c"
)
FROZEN_T2_POOL_MANIFEST_FILE_SHA256 = (
    "ec27f7608865bef5983ae90a780b8779fa6a715bc8253d9dfa4ce046f79e4ac3"
)
FROZEN_T2_LOCAL_PARTITIONS_FILE_SHA256 = (
    "43f3a327f31785a175d0d6b02af2c40b504ad6f8670befaaad4789041a015b1b"
)
FROZEN_T2_LOCAL_POOLS_FILE_SHA256 = (
    "a54172a409e759dff89175aefc6a82a7de4c8828b5a7da5c119072bb8d9fa9a1"
)
FROZEN_T2_PARTITION_MODULE_SHA256 = (
    "e7be4b7dfbebd1b37b363a67a5f45d3f983ee03d2b2028e1bd68fa7405304e8b"
)
OWNER_STATEMENT_SHA256 = "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"
MINER_ORDER_SALT = "pvr:drsp-t3:package-local-order:v1"
MAX_NEGATIVES_PER_QUERY = 5
MIN_NEGATIVES_PER_QUERY = 2
GENERIC_RANK_CATEGORY_CUTOFF = 10

_CATEGORY_PRIORITY = {
    "same_casting_wrong_exact_release": 1,
    "adjacent_year_wrong_series_or_identifier": 2,
    "explicit_wrong_color": 3,
    "high_generic_minilm_score": 4,
    "high_rrf_rank": 5,
}
_IDENTITY_FIELDS = (
    "toy_number",
    "release_year",
    "series",
    "collector_number",
    "series_position",
    "color",
)
_PUBLIC_PAIR_FIELDS = frozenset(
    {
        "schema_version",
        "pair_id",
        "query_id",
        "query_text",
        "positive_text",
        "positive_label",
        "negative_text",
        "negative_label",
        "negative_category",
    }
)
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_.-]+")
_SELLER_OR_PLATFORM_RE = re.compile(
    r"(?i)\b(?:amazon(?:\.[a-z]{2,3})?|poshmark|etsy|mercari|wallapop|mercadolivre|"
    r"todocoleccion|youtube|penguen diecast|klas car keeper|alikhlasdiecast|"
    r"ministry of diecast|carolinasdiecast)\b"
)
_UNSAFE_RELEASE_PATTERNS = {
    "url": re.compile(r"(?i)\b(?:https?://|www\.|file://)"),
    "email": _EMAIL_RE,
    "contact_handle": _HANDLE_RE,
    "local_path": re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\\\Users\\\\)"),
    "secret": re.compile(
        r"(?i)(?:-----BEGIN [A-Z ]+PRIVATE KEY-----|\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}|(?:api[_ -]?key|token|secret)\s*[:=])"
    ),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "authorization_credential": re.compile(
        r"(?i)\bauthorization\s*:\s*(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"
    ),
    "secret_file_or_traversal_path": re.compile(
        r"(?i)(?:\.\.[/\\]|(?:^|[/\\])\.env(?:\.[A-Za-z0-9_-]+)?(?:$|[/\\\s\"'])|"
        r"(?:^|[/\\])(?:id_rsa|id_ed25519|credentials\.json|service-account\.json)(?:$|[/\\\s\"'])|"
        r"\.aws[/\\]credentials|\.ssh[/\\])"
    ),
    # Formatted contact numbers only: pure digit product barcodes (including
    # 11-digit UPC-like values) deliberately do not match this expression.
    "formatted_phone_contact": re.compile(
        r"(?i)(?<![A-Za-z0-9])(?:"
        r"\+\d{1,3}[ .-](?:\(?\d{2,3}\)?[ .-]){2,4}\d{3,4}|"
        r"(?:phone|tel(?:ephone)?|mobile|contact)\s*[:=]?\s*"
        r"(?:\+\d{1,3}[ .-])?(?:\(?\d{2,3}\)?[ .-]){2,4}\d{3,4}"
        r")(?![A-Za-z0-9])"
    ),
    "private_case_id": re.compile(r"\bisr-\d{4}\b"),
    "private_source_id": re.compile(r"\bselenium-row-[0-9a-f]+\b"),
}


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _content_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{path}: required regular file is absent or unsafe")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if _file_sha256(path) != expected_sha256:
        raise ValueError(f"{label} differs from the frozen SHA-256 binding")


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


def _validate_digest(payload: Mapping[str, Any], field: str, label: str) -> None:
    body = {key: value for key, value in payload.items() if key != field}
    if payload.get(field) != _content_sha256(body):
        raise ValueError(f"{label} checksum is stale")


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_t2_chain(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _require_file(
        root / GOVERNANCE_V2_PATH,
        FROZEN_GOVERNANCE_V2_FILE_SHA256,
        "DRSP-T1A effective governance",
    )
    effective = check_publication_amendment(root, require_local_catalog=True)
    permissions = effective.get("permissions")
    if not isinstance(permissions, dict) or (
        permissions.get("positive_local_hard_negative_mining") is not True
        or permissions.get("public_hard_negative_pairs_after_release_gate") is not True
        or permissions.get("runtime_activation") is not False
    ):
        raise ValueError("DRSP-T1A does not authorize the bounded T3 mining/release Gate")

    bindings = (
        (T2_AUTHORIZATION_PATH, FROZEN_T2_AUTHORIZATION_FILE_SHA256, "T2 authorization"),
        (SPLIT_MANIFEST_PATH, FROZEN_T2_SPLIT_MANIFEST_FILE_SHA256, "T2 split manifest"),
        (POOL_MANIFEST_PATH, FROZEN_T2_POOL_MANIFEST_FILE_SHA256, "T2 pool manifest"),
        (
            LOCAL_PARTITIONS_PATH,
            FROZEN_T2_LOCAL_PARTITIONS_FILE_SHA256,
            "T2 private partitions",
        ),
        (LOCAL_POOLS_PATH, FROZEN_T2_LOCAL_POOLS_FILE_SHA256, "T2 private pools"),
        (
            Path("src/product_variant_resolver/domain_ranker_partitions.py"),
            FROZEN_T2_PARTITION_MODULE_SHA256,
            "T2 implementation",
        ),
    )
    for relative, digest, label in bindings:
        _require_file(root / relative, digest, label)
    for relative in (LOCAL_PARTITIONS_PATH, LOCAL_POOLS_PATH):
        if stat.S_IMODE((root / relative).stat().st_mode) != 0o600:
            raise ValueError(f"{relative}: private T2 artifact must use mode 0600")

    split = _load_object(root / SPLIT_MANIFEST_PATH)
    pools = _load_object(root / POOL_MANIFEST_PATH)
    local_partitions = _load_object(root / LOCAL_PARTITIONS_PATH)
    local_pools = _load_object(root / LOCAL_POOLS_PATH)
    _validate_digest(split, "manifest_sha256", "T2 split manifest")
    _validate_digest(pools, "manifest_sha256", "T2 pool manifest")
    _validate_digest(local_partitions, "content_sha256", "T2 private partitions")
    _validate_digest(local_pools, "content_sha256", "T2 private pools")
    counts = split.get("aggregate_counts")
    pool_counts = pools.get("aggregate_counts")
    if not isinstance(counts, dict) or not isinstance(pool_counts, dict):
        raise TypeError("T2 aggregate counts are absent")
    if counts.get("ranker_train") != 70 or counts.get("ranker_selection") != 30:
        raise ValueError("T2 70/30 partition binding changed")
    if (
        pool_counts.get("ranker_train_pool_count") != 70
        or pool_counts.get("ranker_selection_pool_count") != 30
        or pool_counts.get("positive_test_scored") != 0
        or pool_counts.get("negative_holdout_scored") != 0
        or pool_counts.get("no_match_ranker_scored") != 0
        or pool_counts.get("target_injection_count") != 0
    ):
        raise ValueError("T2 frozen-pool guardrails changed")
    if pools.get("private_pool_artifact_sha256") != _content_sha256(local_pools):
        raise ValueError("T2 private-pool binding changed")
    if split.get("private_partition_artifact_sha256") != _content_sha256(local_partitions):
        raise ValueError("T2 private-partition binding changed")
    return local_partitions, local_pools, pools


def build_authorization(root: Path) -> dict[str, Any]:
    _local_partitions, _local_pools, pool_manifest = _validate_t2_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRSP-T3",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "execute_one_shot_train_only_mining_and_publish_only_after_pair_release_gate",
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_third_party_catalog_relative_not_manufacturer_or_global_truth",
        "parent_bindings": {
            "governance_v2_file_sha256": FROZEN_GOVERNANCE_V2_FILE_SHA256,
            "t2_authorization_file_sha256": FROZEN_T2_AUTHORIZATION_FILE_SHA256,
            "t2_split_manifest_file_sha256": FROZEN_T2_SPLIT_MANIFEST_FILE_SHA256,
            "t2_pool_manifest_file_sha256": FROZEN_T2_POOL_MANIFEST_FILE_SHA256,
            "t2_private_partitions_file_sha256": FROZEN_T2_LOCAL_PARTITIONS_FILE_SHA256,
            "t2_private_pools_file_sha256": FROZEN_T2_LOCAL_POOLS_FILE_SHA256,
            "t2_pool_manifest_content_sha256": pool_manifest["manifest_sha256"],
        },
        "authorized_actions": [
            "mine_once_from_70_ranker_train_frozen_top25_pools",
            "hold_evidence_insufficient_same_family_siblings",
            "publish_minimized_binary_pair_package_after_release_gate_passes",
        ],
        "publication_boundary": {
            "row_level_minimized_training_pairs": True,
            "package_local_ids_and_sanitized_query_projection": True,
            "private_case_or_source_ids": False,
            "selection_or_holdout_membership": False,
            "source_image_or_api_metadata": False,
            "contact_pii_secrets_or_local_paths": False,
        },
        "prohibited_actions": [
            "mine_or_score_30_ranker_selection_rows",
            "mine_or_score_53_positive_test_rows",
            "mine_or_score_20_negative_holdout_rows",
            "mine_or_score_52_no_match_development_rows",
            "retrieve_rebuild_rescore_or_mutate_t2_candidate_pools",
            "model_training_or_fine_tuning",
            "model_selection",
            "calibration_or_threshold_selection",
            "fresh_final_read_or_evaluation",
            "runtime_change_or_activation",
        ],
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def _identity_signature(identity: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(normalize_text(str(identity.get(field, ""))) for field in _IDENTITY_FIELDS)


def _uuid_for_source_record(record: Mapping[str, Any]) -> str:
    source_id = _string(record.get("source_record_id"), "catalog source_record_id")
    return str(uuid5(NAMESPACE_URL, f"pvr:image-search-evaluation:{source_id}"))


def _query_mentions(query: str, value: object) -> bool:
    if value is None:
        return False
    needle = normalize_text(str(value))
    if not needle:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", query) is not None


def _sanitize_query(query: str) -> str:
    without_contacts = _SELLER_OR_PLATFORM_RE.sub(
        " ", _HANDLE_RE.sub(" ", _EMAIL_RE.sub(" ", _URL_RE.sub(" ", query)))
    )
    projected_value: object = normalize_text(without_contacts)
    if not isinstance(projected_value, str):
        raise TypeError("normalized training query must be a string")
    projected = projected_value
    if not projected:
        raise ValueError("sanitized training query is empty")
    return projected[:512].strip()


def _candidate_category(
    query: str,
    target: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    generic_rank: int,
    rrf_rank: int,
) -> tuple[str | None, str | None]:
    target_casting = normalize_text(_string(target.get("casting"), "target casting"))
    candidate_casting = normalize_text(
        _string(candidate.get("casting_name"), "candidate casting")
    )
    target_brand = normalize_text(_string(target.get("brand"), "target brand"))
    candidate_brand = normalize_text(_string(candidate.get("brand"), "candidate brand"))
    same_family = target_casting == candidate_casting and target_brand == candidate_brand
    explicit_fields = {
        field for field in _IDENTITY_FIELDS if _query_mentions(query, target.get(field))
    }
    differing_fields = {
        field
        for field in _IDENTITY_FIELDS
        if normalize_text(str(target.get(field, "")))
        != normalize_text(str(candidate.get(field, "")))
    }
    explicit_differences = explicit_fields & differing_fields

    if same_family:
        if not explicit_differences:
            return None, "same_family_without_query_supported_release_discriminator"
        return "same_casting_wrong_exact_release", None

    if not _query_mentions(query, target.get("casting")):
        return None, "target_casting_not_explicit_in_query"

    target_year = target.get("release_year")
    candidate_year = candidate.get("release_year")
    adjacent_year = False
    try:
        adjacent_year = abs(int(str(target_year)) - int(str(candidate_year))) <= 1
    except ValueError:
        adjacent_year = False
    release_fields = {
        "release_year",
        "series",
        "toy_number",
        "collector_number",
        "series_position",
    }
    if adjacent_year and explicit_differences & release_fields:
        return "adjacent_year_wrong_series_or_identifier", None
    if "color" in explicit_differences:
        return "explicit_wrong_color", None
    if generic_rank <= GENERIC_RANK_CATEGORY_CUTOFF:
        return "high_generic_minilm_score", None
    if rrf_rank > 0:
        return "high_rrf_rank", None
    return None, "candidate_has_no_supported_hardness_signal"


def _denylist(root: Path, catalog_by_toy: Mapping[str, Mapping[str, Any]]) -> dict[str, set[Any]]:
    _require_file(root / POSITIVE_DATASET_PATH, POSITIVE_DATASET_SHA256, "positive dataset")
    dataset = load_image_search_dataset(root / POSITIVE_DATASET_PATH)
    frozen = load_frozen_split(dataset, root / POSITIVE_DATASET_PATH)
    if frozen.assignment_sha256 != POSITIVE_SPLIT_SHA256:
        raise ValueError("positive development/test assignment changed")
    test_ids = set(frozen.test_case_ids)
    test_queries: set[str] = set()
    test_identity_signatures: set[tuple[str, ...]] = set()
    test_uuids: set[str] = set()
    for case in dataset.records:
        if case.id not in test_ids:
            continue
        identity = case.expected_full_identity.model_dump(mode="python")
        test_queries.add(normalize_text(case.query))
        test_identity_signatures.add(_identity_signature(identity))
        source = catalog_by_toy.get(case.expected_full_identity.toy_number)
        if source is not None:
            test_uuids.add(_uuid_for_source_record(source))
    if len(test_queries) != POSITIVE_TEST_COUNT:
        raise ValueError("positive test denylist count changed")

    _require_file(root / NEGATIVE_HOLDOUT_PATH, NEGATIVE_HOLDOUT_SHA256, "negative holdout")
    holdout = _load_object(root / NEGATIVE_HOLDOUT_PATH)
    records = holdout.get("records")
    if not isinstance(records, list) or len(records) != NEGATIVE_HOLDOUT_COUNT:
        raise ValueError("negative holdout count changed")
    holdout_queries: set[str] = set()
    holdout_identity_signatures: set[tuple[str, ...]] = set()
    for raw in records:
        if not isinstance(raw, dict) or not isinstance(raw.get("expected_full_identity"), dict):
            raise TypeError("negative holdout record is invalid")
        holdout_queries.add(normalize_text(_string(raw.get("query"), "holdout query")))
        holdout_identity_signatures.add(_identity_signature(raw["expected_full_identity"]))
    return {
        "queries": test_queries | holdout_queries,
        "public_query_projections": {
            _sanitize_query(query) for query in test_queries | holdout_queries
        },
        "identity_signatures": test_identity_signatures | holdout_identity_signatures,
        "positive_test_uuids": test_uuids,
    }


def _pair_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical_bytes(dict(row)) for row in rows)


def _scan_release_files(files: Mapping[str, bytes]) -> dict[str, Any]:
    findings: Counter[str] = Counter()
    for name, payload in files.items():
        if Path(name).suffix.lower() not in {".json", ".jsonl", ".md"}:
            findings["executable_or_unapproved_format"] += 1
        if b"\x00" in payload or payload.startswith(b"#!"):
            findings["executable_or_binary_payload"] += 1
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            findings["non_utf8_payload"] += 1
            continue
        for finding_name, pattern in _UNSAFE_RELEASE_PATTERNS.items():
            findings[finding_name] += len(pattern.findall(text))
    return {
        "passed": not any(findings.values()),
        "finding_counts": dict(sorted(findings.items())),
        "scanned_files": sorted(files),
    }


def _validate_pair_projection(rows: Sequence[Mapping[str, Any]]) -> None:
    pair_ids: set[str] = set()
    query_ids: set[str] = set()
    query_text_by_id: dict[str, str] = {}
    for row in rows:
        if set(row) != _PUBLIC_PAIR_FIELDS:
            raise ValueError("public pair projection contains missing or unrelated fields")
        if row.get("schema_version") != SCHEMA_PAIR:
            raise ValueError("public pair schema changed")
        pair_id = _string(row.get("pair_id"), "pair_id")
        query_id = _string(row.get("query_id"), "query_id")
        query_text = _string(row.get("query_text"), "query_text")
        if pair_id in pair_ids:
            raise ValueError("public pair IDs must be unique")
        if query_id in query_text_by_id and query_text_by_id[query_id] != query_text:
            raise ValueError("one package query ID maps to multiple projections")
        if row.get("positive_label") != 1 or row.get("negative_label") != 0:
            raise ValueError("public pair labels must be binary 1/0")
        if row.get("positive_text") == row.get("negative_text"):
            raise ValueError("positive and negative texts must differ")
        if row.get("negative_category") not in _CATEGORY_PRIORITY:
            raise ValueError("public pair category is invalid")
        pair_ids.add(pair_id)
        query_ids.add(query_id)
        query_text_by_id[query_id] = query_text
    if not rows or not query_ids:
        raise ValueError("public pair package is empty")


def _data_card(counts: Mapping[str, Any]) -> bytes:
    text = f"""# Public hard-negative pairs v1 — Data Card

This package contains {counts['pair_count']} binary training pairs derived from
{counts['train_query_count']} frozen ranker-training queries. Each row has one sanitized query
projection, one positive rendered catalog text, one wrong-candidate rendered catalog text, binary
labels, a bounded negative category, and package-local IDs.

The examples reveal the training text and therefore reveal effective training membership. The
package removes direct private case/source IDs, URLs, contact handles, known seller/platform names,
secrets, local paths, image metadata, API responses, selection rows, calibration rows, and
final/holdout rows;
it does not claim that publication makes membership secret or anonymous.

Mining is deterministic and one-shot over the frozen T2 Top-25 pools. Evidence-insufficient
same-family siblings are held instead of being forced to label 0. The labels mean "wrong relative
to the frozen catalog identity for this query"; they are not manufacturer-certified or global
truth. No model training, model selection, calibration, final evaluation, or runtime activation
was performed by this package build.
"""
    return text.encode()


def _notice() -> bytes:
    return """# NOTICE — Public hard-negative pairs v1

The project owner authorized publication of this minimized package. Source and redistribution
rights were not independently verified. Repository code licensing, if any, must not be interpreted
as granting rights to third-party-derived training text or catalog facts in this package.

Use is limited by applicable law and the underlying sources' terms. This package provides frozen
catalog-relative development labels only and makes no Mattel, manufacturer, authenticity,
ownership, production-readiness, privacy, or global-truth representation.
""".encode()


def _miner_code_sha256(root: Path) -> str:
    return _file_sha256(root / "src/product_variant_resolver/domain_ranker_hard_negatives.py")


def build_package(
    root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]]:
    authorization = build_authorization(root)
    local_partitions, local_pools, pool_manifest = _validate_t2_chain(root)
    before_pool_digest = _content_sha256(local_pools)

    members_raw = local_partitions.get("members")
    pool_rows_raw = local_pools.get("rows")
    if not isinstance(members_raw, list) or not isinstance(pool_rows_raw, list):
        raise TypeError("T2 private artifacts are missing row lists")
    members = {
        _string(raw.get("case_id"), "partition case ID"): raw
        for raw in members_raw
        if isinstance(raw, dict)
    }
    pool_rows = {
        _string(raw.get("case_id"), "pool case ID"): raw
        for raw in pool_rows_raw
        if isinstance(raw, dict)
    }
    if len(members) != 100 or set(members) != set(pool_rows):
        raise ValueError("T2 partition/pool membership differs from frozen 100-row contract")
    train_ids = sorted(
        (case_id for case_id, row in members.items() if row.get("partition") == "ranker_train"),
        key=lambda value: hashlib.sha256(f"{MINER_ORDER_SALT}\0{value}".encode()).hexdigest(),
    )
    selection_ids = {
        case_id for case_id, row in members.items() if row.get("partition") == "ranker_selection"
    }
    if len(train_ids) != RANKER_TRAIN_TARGET or len(selection_ids) != 30:
        raise ValueError("T2 private 70/30 partition membership changed")

    _require_file(root / CATALOG_PATH, CATALOG_SHA256, "frozen catalog")
    source_records = load_source_records(root / CATALOG_PATH)
    catalog_by_uuid = {_uuid_for_source_record(record): record for record in source_records}
    catalog_by_toy = {
        _string(record.get("toy_number"), "catalog toy number"): record
        for record in source_records
    }
    if len(catalog_by_uuid) != len(source_records) or len(catalog_by_toy) != len(source_records):
        raise ValueError("catalog UUID/toy-number mapping is not unique")
    denylist = _denylist(root, catalog_by_toy)
    selection_target_uuids = {
        _string(members[case_id].get("target_uuid"), "selection target UUID")
        for case_id in selection_ids
    }

    output_rows: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    held_reasons: Counter[str] = Counter()
    queries_with_one = 0
    queries_with_two = 0
    pair_sequence = 0
    for query_sequence, case_id in enumerate(train_ids, start=1):
        member = members[case_id]
        pool = pool_rows[case_id]
        if pool.get("partition") != "ranker_train":
            raise ValueError("ranker-train membership and pool partition disagree")
        query = _string(member.get("query"), "ranker-train query")
        query_projection = _sanitize_query(query)
        if (
            normalize_text(query) in denylist["queries"]
            or query_projection in denylist["public_query_projections"]
        ):
            raise ValueError("ranker-train query intersects the permanent holdout denylist")
        target = member.get("exact_identity")
        if not isinstance(target, dict):
            raise TypeError("ranker-train exact identity is missing")
        target_uuid = _string(member.get("target_uuid"), "ranker-train target UUID")
        if (
            target_uuid in denylist["positive_test_uuids"]
            or _identity_signature(target) in denylist["identity_signatures"]
        ):
            raise ValueError("ranker-train target intersects the permanent holdout denylist")
        candidates = pool.get("candidates")
        if not isinstance(candidates, list) or len(candidates) > 25:
            raise ValueError("ranker-train frozen pool is invalid")
        target_candidates = [
            raw
            for raw in candidates
            if isinstance(raw, dict) and raw.get("canonical_uuid") == target_uuid
        ]
        if len(target_candidates) != 1:
            raise ValueError("ranker-train target must occur exactly once in the frozen pool")
        positive_text = _string(target_candidates[0].get("rendered_text"), "positive text")

        eligible: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []
        for raw_candidate in candidates:
            if not isinstance(raw_candidate, dict):
                raise TypeError("frozen candidate must be an object")
            candidate_uuid = _string(raw_candidate.get("canonical_uuid"), "candidate UUID")
            if candidate_uuid == target_uuid:
                continue
            if candidate_uuid in selection_target_uuids:
                held_reasons["selection_target_identity_excluded"] += 1
                continue
            candidate = catalog_by_uuid.get(candidate_uuid)
            if candidate is None:
                raise ValueError("frozen candidate UUID is absent from the bound catalog")
            if (
                candidate_uuid in denylist["positive_test_uuids"]
                or _identity_signature(candidate) in denylist["identity_signatures"]
            ):
                held_reasons["permanent_holdout_identity_excluded"] += 1
                continue
            generic_rank = raw_candidate.get("generic_pointwise_rank")
            rrf_rank = raw_candidate.get("rrf_rank")
            generic_score = raw_candidate.get("generic_pointwise_score")
            if (
                not isinstance(generic_rank, int)
                or not isinstance(rrf_rank, int)
                or not isinstance(generic_score, (int, float))
                or not math.isfinite(float(generic_score))
            ):
                raise ValueError("frozen candidate rank/score is invalid")
            category, held_reason = _candidate_category(
                normalize_text(query),
                target,
                candidate,
                generic_rank=generic_rank,
                rrf_rank=rrf_rank,
            )
            if category is None:
                held_reasons[held_reason or "unspecified_evidence_shortfall"] += 1
                continue
            eligible.append(
                (
                    (_CATEGORY_PRIORITY[category], generic_rank, rrf_rank, candidate_uuid),
                    {
                        "negative_text": _string(
                            raw_candidate.get("rendered_text"), "negative text"
                        ),
                        "negative_category": category,
                    },
                )
            )
        selected = [row for _key, row in sorted(eligible, key=lambda item: item[0])][
            :MAX_NEGATIVES_PER_QUERY
        ]
        if selected:
            queries_with_one += 1
        if len(selected) >= MIN_NEGATIVES_PER_QUERY:
            queries_with_two += 1
        query_id = f"pvr-query-{query_sequence:03d}"
        for selected_row in selected:
            pair_sequence += 1
            category = _string(selected_row["negative_category"], "negative category")
            category_counts[category] += 1
            output_rows.append(
                {
                    "schema_version": SCHEMA_PAIR,
                    "pair_id": f"pvr-pair-{pair_sequence:04d}",
                    "query_id": query_id,
                    "query_text": query_projection,
                    "positive_text": positive_text,
                    "positive_label": 1,
                    "negative_text": selected_row["negative_text"],
                    "negative_label": 0,
                    "negative_category": category,
                }
            )

    majority_minimum = len(train_ids) // 2 + 1
    if queries_with_two < majority_minimum:
        raise ValueError(
            "hard-negative shortfall: a strict majority of train queries lacks two defensible negatives"
        )
    _validate_pair_projection(output_rows)
    if _content_sha256(local_pools) != before_pool_digest:
        raise ValueError("T2 private candidate pool was mutated during mining")

    counts: dict[str, Any] = {
        "train_query_count": len(train_ids),
        "selection_query_count_untouched": len(selection_ids),
        "pair_count": len(output_rows),
        "maximum_negatives_per_query": MAX_NEGATIVES_PER_QUERY,
        "minimum_negatives_required_for_majority": MIN_NEGATIVES_PER_QUERY,
        "queries_with_at_least_one_defensible_negative": queries_with_one,
        "queries_with_at_least_two_defensible_negatives": queries_with_two,
        "queries_with_zero_defensible_negatives": len(train_ids) - queries_with_one,
        "strict_majority_gate_minimum": majority_minimum,
    }
    pair_payload = _pair_bytes(output_rows)
    data_card = _data_card(counts)
    notice = _notice()
    authorization_bytes = _canonical_bytes(authorization)
    release_files = {
        "owner-authorization.json": authorization_bytes,
        "pairs.jsonl": pair_payload,
        "DATA_CARD.md": data_card,
        "NOTICE.md": notice,
    }
    release_scan = _scan_release_files(release_files)
    if release_scan["passed"] is not True:
        raise ValueError(f"public pair release scan failed: {release_scan['finding_counts']}")
    files_sha256 = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(release_files.items())
    }
    package_sha256 = _content_sha256(files_sha256)
    manifest_body: dict[str, Any] = {
        "schema_version": SCHEMA_MANIFEST,
        "version": VERSION,
        "status": "published_release_gate_passed",
        "published": True,
        "release_gate_passed": True,
        "authorization_sha256": authorization["authorization_sha256"],
        "rights_state": "owner_attested_not_independently_verified",
        "label_semantics": "binary_wrong_release_relative_to_frozen_catalog_not_global_truth",
        "bindings": {
            "catalog_sha256": CATALOG_SHA256,
            "positive_dataset_sha256": POSITIVE_DATASET_SHA256,
            "positive_split_assignment_sha256": POSITIVE_SPLIT_SHA256,
            "t2_split_manifest_file_sha256": FROZEN_T2_SPLIT_MANIFEST_FILE_SHA256,
            "t2_candidate_pool_manifest_file_sha256": FROZEN_T2_POOL_MANIFEST_FILE_SHA256,
            "t2_private_pool_sha256": FROZEN_T2_LOCAL_POOLS_FILE_SHA256,
            "generic_model_id": pool_manifest["bindings"]["generic_model_id"],
            "generic_model_revision": pool_manifest["bindings"]["generic_model_revision"],
            "generic_model_config_sha256": pool_manifest["bindings"][
                "generic_model_config_sha256"
            ],
            "generic_model_manifest_sha256": pool_manifest["bindings"][
                "generic_model_manifest_sha256"
            ],
            "renderer": pool_manifest["bindings"]["renderer"],
            "renderer_module_sha256": pool_manifest["bindings"]["renderer_module_sha256"],
            "miner_module_sha256": _miner_code_sha256(root),
            "gitignore_sha256": _file_sha256(root / ".gitignore"),
        },
        "mining_contract": {
            "one_shot": True,
            "pool_retrieval_rebuild_or_rescore": False,
            "source_partition": "ranker_train_only",
            "candidate_source": "frozen_t2_top25_only",
            "maximum_negatives_per_query": MAX_NEGATIVES_PER_QUERY,
            "category_priority": list(_CATEGORY_PRIORITY),
            "ambiguous_same_family_action": "held_excluded_from_binary_pairs",
        },
        "aggregate_counts": counts,
        "negative_category_counts": dict(sorted(category_counts.items())),
        "held_candidate_counts_by_reason": dict(sorted(held_reasons.items())),
        "guardrails": {
            "ranker_selection_queries_mined": 0,
            "ranker_selection_queries_scored": 0,
            "positive_test_queries_mined": 0,
            "positive_test_queries_scored": 0,
            "negative_holdout_queries_mined": 0,
            "negative_holdout_queries_scored": 0,
            "no_match_development_queries_mined": 0,
            "no_match_development_queries_scored": 0,
            "target_injections": 0,
            "candidate_pool_mutations": 0,
            "model_training_runs": 0,
            "model_selection_runs": 0,
            "calibration_fits": 0,
            "fresh_final_evaluations": 0,
            "runtime_default_changed": False,
        },
        "release_gate": {
            "non_executable_utf8_formats_only": True,
            "strict_field_minimization_passed": True,
            "secret_pii_contact_and_local_path_scan": release_scan,
            "final_manifest_secondary_scan_passed": True,
            "permanent_denylist_query_or_identity_intersection": 0,
            "ranker_selection_identity_excluded_from_negatives": True,
            "license_notice_present": True,
            "training_rights_limitation_disclosed": True,
            "lineage_and_hashes_complete": True,
        },
        "files_sha256": files_sha256,
        "package_sha256": package_sha256,
        "limitations": [
            "public_training_text_reveals_effective_training_membership",
            "source_and_redistribution_rights_not_independently_verified",
            "catalog_relative_labels_are_not_manufacturer_or_global_truth",
            "no_training_selection_calibration_final_or_runtime_action_executed",
        ],
        "next_allowed_action": "DRSP-T4_requires_separate_owner_authorization_and_model_release_gate",
    }
    manifest = {**manifest_body, "manifest_sha256": _content_sha256(manifest_body)}
    final_manifest_scan = _scan_release_files({"manifest.json": _canonical_bytes(manifest)})
    if final_manifest_scan["passed"] is not True:
        raise ValueError(
            f"final public manifest release scan failed: {final_manifest_scan['finding_counts']}"
        )
    return authorization, output_rows, data_card, notice, manifest


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    path.chmod(0o644)


def materialize(root: Path) -> dict[str, Any]:
    if (root / PACKAGE_DIRECTORY).exists():
        raise FileExistsError("DRSP-T3 public pair package already exists")
    authorization, rows, data_card, notice, manifest = build_package(root)
    _write(root / AUTHORIZATION_OUTPUT_PATH, _canonical_bytes(authorization))
    _write(root / PAIR_PATH, _pair_bytes(rows))
    _write(root / DATA_CARD_PATH, data_card)
    _write(root / NOTICE_PATH, notice)
    _write(root / MANIFEST_PATH, _canonical_bytes(manifest))
    return manifest


def check(root: Path) -> dict[str, Any]:
    authorization, rows, data_card, notice, manifest = build_package(root)
    expected = {
        AUTHORIZATION_OUTPUT_PATH: _canonical_bytes(authorization),
        PAIR_PATH: _pair_bytes(rows),
        DATA_CARD_PATH: data_card,
        NOTICE_PATH: notice,
        MANIFEST_PATH: _canonical_bytes(manifest),
    }
    for relative, payload in expected.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{relative}: public package file is absent or unsafe")
        if path.read_bytes() != payload:
            raise ValueError(f"{relative}: deterministic regeneration mismatch")
        if stat.S_IMODE(path.stat().st_mode) != 0o644:
            raise ValueError(f"{relative}: public package file must use mode 0644")
        if stat.S_IMODE(path.stat().st_mode) & 0o111:
            raise ValueError(f"{relative}: public package file must not be executable")
    package_root = root / PACKAGE_DIRECTORY
    allowed_names = {path.name for path in expected}
    actual_entries: set[str] = set()
    for path in package_root.rglob("*"):
        entry_name = path.relative_to(package_root).as_posix()
        actual_entries.add(entry_name)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"public package contains unsafe extra entry: {entry_name}")
    if actual_entries != allowed_names:
        raise ValueError("public package contains unapproved extra or missing entries")
    stored_manifest = _load_object(root / MANIFEST_PATH)
    _validate_digest(stored_manifest, "manifest_sha256", "DRSP-T3 manifest")
    if stored_manifest != manifest:
        raise ValueError("DRSP-T3 manifest is stale or tampered")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize or validate DRSP-T3 train-only public hard-negative pairs"
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    arguments = parser.parse_args()
    root = Path.cwd()
    if arguments.run:
        if not arguments.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        print(json.dumps(materialize(root), indent=2, sort_keys=True))
        return
    if arguments.check:
        check(root)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
