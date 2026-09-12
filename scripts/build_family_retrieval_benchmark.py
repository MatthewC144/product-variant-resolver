#!/usr/bin/env python3
"""Validate and freeze the output-blind family-retrieval benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "data" / "evaluation" / "family-retrieval-v1"

QUERY_PACK_SCHEMA = "pvr-family-retrieval-query-pack-v1"
QUERY_PACK_VERSION = "family-retrieval-query-pack-v1"
QUERY_PACK_MANIFEST_SCHEMA = "pvr-family-retrieval-query-pack-manifest-v1"
DECISIONS_SCHEMA = "pvr-family-retrieval-owner-decisions-v1"
DECISIONS_VERSION = "family-retrieval-owner-decisions-v1"
BENCHMARK_SCHEMA = "pvr-family-retrieval-benchmark-v1"
BENCHMARK_MANIFEST_SCHEMA = "pvr-family-retrieval-benchmark-manifest-v1"
BENCHMARK_VERSION = "family-retrieval-holdout-v1"

REGISTRY_SCHEMA = "pvr-review-family-registry-v1"
REGISTRY_VERSION = "fandom-2025-review-families-r790665-v1"
REGISTRY_MANIFEST_SCHEMA = "pvr-review-family-registry-manifest-v1"
PROJECTION_SCHEMA = "pvr-review-family-knowledge-v1"
PROJECTION_VERSION = "review-family-knowledge-fandom-2025-r790665-v1"
PROJECTION_MANIFEST_SCHEMA = "pvr-review-family-knowledge-manifest-v1"
HUMAN_SCHEMA = "pvr-human-backed-catalog-v1"
HUMAN_VERSION = "human-backed-catalog-v1"
HUMAN_MANIFEST_SCHEMA = "pvr-human-backed-catalog-manifest-v1"

REGISTRY_ELIGIBLE_FOR = ["family_review", "future_human_knowledge_index"]
REGISTRY_EXCLUDED_FROM = [
    "runtime_retrieval",
    "canonical_variant_response",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "postgresql_ingestion",
]
PROJECTION_ELIGIBLE_FOR = ["human_knowledge_debug_retrieval"]
PROJECTION_EXCLUDED_FROM = [
    "canonical_variant_response",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "evaluation_ground_truth",
    "variant_identity",
    "postgresql_ingestion",
]
HUMAN_ELIGIBLE_FOR = [
    "sparse_candidate_retrieval",
    "dense_candidate_retrieval",
    "human_catalog_review",
]
HUMAN_EXCLUDED_FROM = [
    "canonical_variant_response",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
]

EXPECTED_CASE_COUNTS = {
    "hold_control": 7,
    "merge_control": 4,
    "positive_family": 84,
    "unrelated_control": 10,
}
EXPECTED_STYLE_COUNTS = {
    "held_identity": 7,
    "lexical_variation": 42,
    "marketplace_noise": 42,
    "merge_existing_family": 4,
    "no_overlap": 10,
}
SPLIT_COUNTS = {"dev": 0, "test": 105, "train": 0}
ELIGIBLE_FOR = ["human_knowledge_retrieval_evaluation"]
EXCLUDED_FROM = [
    "calibration_training",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_variant_response",
    "postgresql_ingestion",
    "production_accuracy_claim",
    "query_rewriting",
    "release_variant_ground_truth",
    "retriever_tuning",
    "threshold_selection",
]
AUTHORING_POLICY = {
    "method": "independently_composed_synthetic_challenge-v1",
    "prohibited_query_sources": [
        "review_family_knowledge.searchable_text",
        "fandom_2025_staging_labels",
        "human_labeled_names.query_text",
    ],
    "retriever_output_viewed": False,
}
CASE_FIELDS = {
    "authored_at",
    "authored_by",
    "authoring_method",
    "case_id",
    "case_type",
    "casting_group_id",
    "challenge_style",
    "noise_tags",
    "query_text",
    "retriever_output_viewed",
    "review_reference",
    "split",
}
ALLOWED_NOISE_TAGS = {
    "abbreviation",
    "condition_noise",
    "identity_ambiguity",
    "marketplace_wrapper",
    "misspelling",
    "no_overlap",
    "punctuation",
    "seller_wrapper",
    "series_noise",
    "spacing",
    "year_noise",
}
LEXICAL_TAGS = {"abbreviation", "misspelling", "punctuation", "spacing"}
UTC_TIMESTAMP = re.compile(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
CASE_ID_PATTERN = re.compile(r"fre-(?:positive|merge|hold|unrelated)-[a-z0-9-]+")


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name}: could not read valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"{path.name}: could not read file for checksum") from error


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w]+", normalized, flags=re.UNICODE))


def _required_string(value: Any, *, field: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {field} must be a non-empty string")
    return value


def _exact_fields(value: Any, expected: set[str], *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{context}: fields differ from the frozen contract")
    return value


def _string_list(
    value: Any,
    *,
    field: str,
    context: str,
    allow_empty: bool = False,
) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or not all(isinstance(item, str) and item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"{context}: {field} must contain unique non-empty strings")
    return list(value)


def _validate_timestamp(value: Any, *, field: str, context: str) -> str:
    text = _required_string(value, field=field, context=context)
    if not UTC_TIMESTAMP.fullmatch(text):
        raise ValueError(f"{context}: {field} must be a second-precision UTC timestamp")
    return text


def _file_reference(path: Path, *, version: str | None = None) -> dict[str, str]:
    result = {"file": path.name, "sha256": _sha256(path)}
    if version is not None:
        result["version"] = version
    return result


def _system_under_test(
    *,
    human_path: Path,
    projection_path: Path,
) -> dict[str, Any]:
    return {
        "candidate_limit": 5,
        "dense_dimensions": 192,
        "dense_provider": "hashing-v1",
        "dense_source_file": "retrieval.py",
        "dense_source_sha256": _sha256(ROOT / "src/product_variant_resolver/retrieval.py"),
        "human_catalog_sha256": _sha256(human_path),
        "human_catalog_version": HUMAN_VERSION,
        "normalizer_source_file": "identity.py",
        "normalizer_source_sha256": _sha256(ROOT / "src/product_variant_resolver/identity.py"),
        "normalizer_version": "identity.normalize_text-v1",
        "retriever_source_file": "human_knowledge.py",
        "retriever_source_sha256": _sha256(
            ROOT / "src/product_variant_resolver/human_knowledge.py"
        ),
        "retriever_version": "human-knowledge-hybrid-v2",
        "review_family_knowledge_sha256": _sha256(projection_path),
        "review_family_knowledge_version": PROJECTION_VERSION,
        "rrf_k": 60,
    }


def _validate_sources(
    *,
    registry_path: Path,
    registry: dict[str, Any],
    registry_manifest_path: Path,
    registry_manifest: dict[str, Any],
    projection_path: Path,
    projection: dict[str, Any],
    projection_manifest_path: Path,
    projection_manifest: dict[str, Any],
    human_path: Path,
    human: dict[str, Any],
    human_manifest_path: Path,
    human_manifest: dict[str, Any],
) -> dict[str, Any]:
    if (
        registry.get("schema_version") != REGISTRY_SCHEMA
        or registry.get("registry_version") != REGISTRY_VERSION
        or registry.get("status") != "review_family_only"
        or registry.get("eligible_for") != REGISTRY_ELIGIBLE_FOR
        or registry.get("excluded_from") != REGISTRY_EXCLUDED_FROM
    ):
        raise ValueError("review-family registry identity differs from the frozen contract")
    if registry_manifest.get("schema_version") != REGISTRY_MANIFEST_SCHEMA:
        raise ValueError("review-family registry manifest schema differs from contract")
    if (
        registry_manifest.get("registry_file") != registry_path.name
        or registry_manifest.get("registry_sha256") != _sha256(registry_path)
        or registry_manifest.get("registry_version") != REGISTRY_VERSION
    ):
        raise ValueError("review-family registry manifest is stale or mismatched")

    sections = {
        "new_families": 42,
        "merge_links": 4,
        "hold_exclusions": 7,
    }
    for name, count in sections.items():
        if not isinstance(registry.get(name), list) or len(registry[name]) != count:
            raise ValueError(f"review-family registry {name} count differs from contract")

    if (
        projection.get("schema_version") != PROJECTION_SCHEMA
        or projection.get("knowledge_version") != PROJECTION_VERSION
        or projection.get("status") != "debug_retrieval_only"
        or projection.get("eligible_for") != PROJECTION_ELIGIBLE_FOR
        or projection.get("excluded_from") != PROJECTION_EXCLUDED_FROM
    ):
        raise ValueError("review-family projection identity differs from contract")
    if projection_manifest.get("schema_version") != PROJECTION_MANIFEST_SCHEMA:
        raise ValueError("review-family projection manifest schema differs from contract")
    if (
        projection_manifest.get("projection_file") != projection_path.name
        or projection_manifest.get("projection_sha256") != _sha256(projection_path)
        or projection_manifest.get("knowledge_version") != PROJECTION_VERSION
        or projection_manifest.get("document_count") != 42
    ):
        raise ValueError("review-family projection manifest is stale or mismatched")
    documents = projection.get("documents")
    if not isinstance(documents, list) or len(documents) != 42:
        raise ValueError("review-family projection must contain exactly 42 documents")
    family_ids = [item.get("review_family_id") for item in registry["new_families"]]
    projected_ids = [item.get("review_family_id") for item in documents]
    if len(set(family_ids)) != 42 or set(projected_ids) != set(family_ids):
        raise ValueError("review-family projection coverage differs from registry")

    if (
        human.get("schema_version") != HUMAN_SCHEMA
        or human.get("catalog_version") != HUMAN_VERSION
        or human.get("status") != "human_review_draft"
        or human.get("eligible_for") != HUMAN_ELIGIBLE_FOR
        or human.get("excluded_from") != HUMAN_EXCLUDED_FROM
    ):
        raise ValueError("human-backed catalog identity differs from contract")
    if human_manifest.get("schema_version") != HUMAN_MANIFEST_SCHEMA:
        raise ValueError("human-backed catalog manifest schema differs from contract")
    if (
        human_manifest.get("catalog_file") != human_path.name
        or human_manifest.get("catalog_sha256") != _sha256(human_path)
        or human_manifest.get("catalog_version") != HUMAN_VERSION
        or human_manifest.get("casting_count") != 97
        or human_manifest.get("provisional_variant_count") != 100
    ):
        raise ValueError("human-backed catalog manifest is stale or mismatched")
    castings = human.get("castings")
    if not isinstance(castings, list) or len(castings) != 97:
        raise ValueError("human-backed catalog must contain exactly 97 castings")
    variant_count = sum(
        len(item.get("provisional_variants", []))
        for item in castings
        if isinstance(item, dict)
    )
    if variant_count != 100:
        raise ValueError("human-backed catalog must contain exactly 100 variants")

    for path in (
        registry_manifest_path,
        projection_manifest_path,
        human_manifest_path,
    ):
        if not path.is_file():
            raise ValueError(f"{path.name}: required source manifest is missing")

    return _system_under_test(human_path=human_path, projection_path=projection_path)


def _forbidden_query_texts(
    registry: dict[str, Any], projection: dict[str, Any], human: dict[str, Any]
) -> set[str]:
    values: set[str] = set()
    for document in projection["documents"]:
        brand = document["brand"]
        casting = document["casting"]
        values.update((casting, f"{brand} {casting}", *document["aliases"]))
    for section in ("new_families", "merge_links", "hold_exclusions"):
        for item in registry[section]:
            display = item["display_name"]
            values.update((display, f"{item['brand']} {display}"))
    for casting in human["castings"]:
        values.update((casting["casting"], f"{casting['brand']} {casting['casting']}"))
        for variant in casting["provisional_variants"]:
            for field in ("human_label_names", "pricing_keywords", "initial_names"):
                values.update(variant[field])
    return {_normalize(value) for value in values if _normalize(value)}


def _knowledge_tokens(projection: dict[str, Any], human: dict[str, Any]) -> set[str]:
    values: list[str] = []
    for document in projection["documents"]:
        values.extend((document["brand"], document["casting"], *document["aliases"]))
    for casting in human["castings"]:
        values.extend((casting["brand"], casting["casting"]))
        for variant in casting["provisional_variants"]:
            for field in ("human_label_names", "pricing_keywords", "initial_names"):
                values.extend(variant[field])
            for field in ("series_label", "variant_label"):
                if variant[field]:
                    values.append(variant[field])
    return set(_normalize(" ".join(values)).split())


def _validate_case_common(case: Any, *, index: int) -> dict[str, Any]:
    context = f"query case {index}"
    item = _exact_fields(case, CASE_FIELDS, context=context)
    case_id = _required_string(item.get("case_id"), field="case_id", context=context)
    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise ValueError(f"{context}: case_id differs from contract")
    if item.get("split") != "test":
        raise ValueError(f"{case_id}: only the test split is permitted")
    if item.get("authoring_method") != AUTHORING_POLICY["method"]:
        raise ValueError(f"{case_id}: authoring method differs from contract")
    if item.get("retriever_output_viewed") is not False:
        raise ValueError(f"{case_id}: retriever output must remain unviewed")
    if item.get("authored_by") != "evaluation_query_author":
        raise ValueError(f"{case_id}: query author role differs from contract")
    _validate_timestamp(item.get("authored_at"), field="authored_at", context=case_id)
    _required_string(item.get("casting_group_id"), field="casting_group_id", context=case_id)
    _required_string(item.get("query_text"), field="query_text", context=case_id)
    tags = _string_list(item.get("noise_tags"), field="noise_tags", context=case_id)
    if not set(tags) <= ALLOWED_NOISE_TAGS:
        raise ValueError(f"{case_id}: query contains an unsupported noise tag")
    return item


def validate_query_pack(
    query_pack: dict[str, Any],
    *,
    registry: dict[str, Any],
    projection: dict[str, Any],
    human: dict[str, Any],
    system_under_test: dict[str, Any],
) -> dict[str, Any]:
    _exact_fields(
        query_pack,
        {
            "authorship_policy",
            "benchmark_version",
            "cases",
            "eligible_for",
            "excluded_from",
            "expected_counts",
            "query_pack_version",
            "schema_version",
            "split",
            "status",
            "system_under_test",
        },
        context="query pack",
    )
    if (
        query_pack.get("schema_version") != QUERY_PACK_SCHEMA
        or query_pack.get("query_pack_version") != QUERY_PACK_VERSION
        or query_pack.get("benchmark_version") != BENCHMARK_VERSION
        or query_pack.get("status") != "pending_owner_review"
    ):
        raise ValueError("query pack identity or status differs from contract")
    if query_pack.get("split") != "test":
        raise ValueError("query pack must be test-only")
    if query_pack.get("eligible_for") != ELIGIBLE_FOR:
        raise ValueError("query pack eligibility boundary differs from contract")
    if query_pack.get("excluded_from") != EXCLUDED_FROM:
        raise ValueError("query pack excluded uses differ from contract")
    if query_pack.get("authorship_policy") != AUTHORING_POLICY:
        raise ValueError("query pack authorship declaration differs from contract")
    if query_pack.get("system_under_test") != system_under_test:
        raise ValueError("query pack system-under-test freeze is stale or changed")
    if query_pack.get("expected_counts") != EXPECTED_CASE_COUNTS:
        raise ValueError("query pack expected counts differ from contract")

    cases = query_pack.get("cases")
    if not isinstance(cases, list) or len(cases) != 105:
        raise ValueError("query pack must contain exactly 105 cases")
    items = [_validate_case_common(case, index=index) for index, case in enumerate(cases)]
    case_ids = [item["case_id"] for item in items]
    queries = [_normalize(item["query_text"]) for item in items]
    if case_ids != sorted(case_ids):
        raise ValueError("query cases must be ordered by case_id")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("query pack contains duplicate case IDs")
    if any(not query for query in queries) or len(queries) != len(set(queries)):
        raise ValueError("query pack contains empty or duplicate normalized queries")

    case_counts = Counter(item["case_type"] for item in items)
    style_counts = Counter(item["challenge_style"] for item in items)
    if dict(sorted(case_counts.items())) != EXPECTED_CASE_COUNTS:
        raise ValueError("query case composition differs from contract")
    if dict(sorted(style_counts.items())) != EXPECTED_STYLE_COUNTS:
        raise ValueError("query challenge-style composition differs from contract")

    forbidden = _forbidden_query_texts(registry, projection, human)
    copied = set(queries) & forbidden
    if copied:
        raise ValueError("query text copies a prohibited indexed/staging/human-label string")

    family_by_id = {item["review_family_id"]: item for item in registry["new_families"]}
    document_by_id = {item["review_family_id"]: item for item in projection["documents"]}
    merge_by_id = {item["source_family_review_id"]: item for item in registry["merge_links"]}
    hold_by_id = {item["review_family_id"]: item for item in registry["hold_exclusions"]}
    human_by_id = {item["casting_id"]: item for item in human["castings"]}
    positive_styles: dict[str, set[str]] = defaultdict(set)
    positive_groups: dict[str, set[str]] = defaultdict(set)
    covered_merge: set[str] = set()
    covered_hold: set[str] = set()
    unrelated_controls: set[str] = set()
    knowledge_tokens = _knowledge_tokens(projection, human)

    for item, normalized_query in zip(items, queries, strict=True):
        case_id = item["case_id"]
        case_type = item["case_type"]
        style = item["challenge_style"]
        reference = item["review_reference"]
        if case_type == "positive_family":
            _exact_fields(
                reference, {"kind", "review_family_id"}, context=f"{case_id} reference"
            )
            family_id = reference.get("review_family_id")
            if reference.get("kind") != "review_family" or family_id not in family_by_id:
                raise ValueError(f"{case_id}: positive family reference is unknown")
            if item["casting_group_id"] != f"review:{family_id}":
                raise ValueError(f"{case_id}: positive casting group differs from contract")
            if style not in {"marketplace_noise", "lexical_variation"}:
                raise ValueError(f"{case_id}: positive challenge style is unsupported")
            document = document_by_id[family_id]
            casting = _normalize(document["casting"])
            if style == "lexical_variation":
                if not set(item["noise_tags"]) & LEXICAL_TAGS:
                    raise ValueError(f"{case_id}: lexical challenge tag is missing")
                if f" {casting} " in f" {normalized_query} ":
                    raise ValueError(f"{case_id}: lexical query retains the full casting phrase")
            positive_styles[family_id].add(style)
            positive_groups[family_id].add(item["casting_group_id"])
        elif case_type == "merge_control":
            _exact_fields(
                reference,
                {"kind", "source_family_review_id"},
                context=f"{case_id} reference",
            )
            family_id = reference.get("source_family_review_id")
            if reference.get("kind") != "merge_control" or family_id not in merge_by_id:
                raise ValueError(f"{case_id}: merge reference is unknown")
            if item["casting_group_id"] != f"merge:{family_id}":
                raise ValueError(f"{case_id}: merge casting group differs from contract")
            if style != "merge_existing_family":
                raise ValueError(f"{case_id}: merge challenge style is unsupported")
            if merge_by_id[family_id]["target_casting_id"] not in human_by_id:
                raise ValueError(f"{case_id}: merge target does not exist in human catalog")
            covered_merge.add(family_id)
        elif case_type == "hold_control":
            _exact_fields(
                reference, {"kind", "review_family_id"}, context=f"{case_id} reference"
            )
            family_id = reference.get("review_family_id")
            if reference.get("kind") != "hold_control" or family_id not in hold_by_id:
                raise ValueError(f"{case_id}: held-family reference is unknown")
            if item["casting_group_id"] != f"hold:{family_id}":
                raise ValueError(f"{case_id}: held-family group differs from contract")
            if style != "held_identity":
                raise ValueError(f"{case_id}: held challenge style is unsupported")
            covered_hold.add(family_id)
        elif case_type == "unrelated_control":
            _exact_fields(
                reference, {"control_id", "kind"}, context=f"{case_id} reference"
            )
            control_id = reference.get("control_id")
            if reference.get("kind") != "unrelated_control":
                raise ValueError(f"{case_id}: unrelated reference kind is unsupported")
            _required_string(control_id, field="control_id", context=case_id)
            if item["casting_group_id"] != f"unrelated:{control_id}":
                raise ValueError(f"{case_id}: unrelated group differs from contract")
            if style != "no_overlap" or "no_overlap" not in item["noise_tags"]:
                raise ValueError(f"{case_id}: unrelated challenge declaration is invalid")
            if set(normalized_query.split()) & knowledge_tokens:
                raise ValueError(f"{case_id}: unrelated query overlaps human knowledge tokens")
            unrelated_controls.add(control_id)
        else:
            raise ValueError(f"{case_id}: unsupported case type")

    if set(positive_styles) != set(family_by_id) or any(
        styles != {"marketplace_noise", "lexical_variation"}
        for styles in positive_styles.values()
    ):
        raise ValueError("positive cases do not cover every family in both styles")
    if any(len(groups) != 1 for groups in positive_groups.values()):
        raise ValueError("positive family cases do not share one casting group")
    if covered_merge != set(merge_by_id):
        raise ValueError("merge controls do not cover the complete registry")
    if covered_hold != set(hold_by_id):
        raise ValueError("hold controls do not cover the complete registry")
    if len(unrelated_controls) != 10:
        raise ValueError("unrelated controls must contain 10 unique groups")

    single_token_ids = sorted(
        family_id
        for family_id, document in document_by_id.items()
        if len(_normalize(document["casting"]).split()) == 1
    )
    if len(single_token_ids) != 4:
        raise ValueError("single-token family accounting differs from contract")
    return {
        "case_counts": dict(sorted(case_counts.items())),
        "challenge_style_counts": dict(sorted(style_counts.items())),
        "positive_family_group_count": len(positive_styles),
        "single_token_family_ids": single_token_ids,
        "split_counts": SPLIT_COUNTS,
    }


def expected_query_pack_manifest(
    query_pack_path: Path,
    query_pack: dict[str, Any],
    accounting: dict[str, Any],
) -> dict[str, Any]:
    return {
        "authorship_policy": AUTHORING_POLICY,
        "benchmark_version": BENCHMARK_VERSION,
        **accounting,
        "eligible_for": ELIGIBLE_FOR,
        "excluded_from": EXCLUDED_FROM,
        "query_pack_file": query_pack_path.name,
        "query_pack_sha256": _sha256(query_pack_path),
        "query_pack_version": QUERY_PACK_VERSION,
        "schema_version": QUERY_PACK_MANIFEST_SCHEMA,
        "status": "frozen_pre_score",
        "system_under_test": query_pack["system_under_test"],
    }


def _validate_query_pack_manifest(
    manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    if manifest != expected:
        raise ValueError("query-pack manifest is stale, incomplete, or widened")


def _validate_owner_decisions(
    decisions: dict[str, Any],
    *,
    decisions_path: Path,
    query_pack_path: Path,
    query_pack: dict[str, Any],
    registry: dict[str, Any],
    human: dict[str, Any],
) -> None:
    _exact_fields(
        decisions,
        {
            "benchmark_version",
            "decided_at",
            "decided_by",
            "decision_version",
            "decisions",
            "query_pack_file",
            "query_pack_sha256",
            "schema_version",
            "status",
        },
        context="owner decisions",
    )
    if (
        decisions.get("schema_version") != DECISIONS_SCHEMA
        or decisions.get("decision_version") != DECISIONS_VERSION
        or decisions.get("benchmark_version") != BENCHMARK_VERSION
        or decisions.get("status") != "approved_for_test_evaluation"
        or decisions.get("decided_by") != "project_owner"
    ):
        raise ValueError("owner-decision identity, reviewer, or status differs from contract")
    _validate_timestamp(decisions.get("decided_at"), field="decided_at", context="owner decisions")
    if (
        decisions.get("query_pack_file") != query_pack_path.name
        or decisions.get("query_pack_sha256") != _sha256(query_pack_path)
    ):
        raise ValueError("owner decisions do not bind the current frozen query pack")

    values = decisions.get("decisions")
    if not isinstance(values, list) or len(values) != 105:
        raise ValueError("owner decisions must cover exactly 105 cases")
    by_case = {item["case_id"]: item for item in query_pack["cases"]}
    decision_ids: list[str] = []
    family_ids = {item["review_family_id"] for item in registry["new_families"]}
    merge_by_id = {item["source_family_review_id"]: item for item in registry["merge_links"]}
    hold_ids = {item["review_family_id"] for item in registry["hold_exclusions"]}
    human_ids = {item["casting_id"] for item in human["castings"]}

    for index, value in enumerate(values):
        context = f"owner decision {index}"
        item = _exact_fields(
            value,
            {"case_id", "decided_at", "decided_by", "decision", "expected", "reason"},
            context=context,
        )
        case_id = _required_string(item.get("case_id"), field="case_id", context=context)
        decision_ids.append(case_id)
        if item.get("decision") != "approve" or item.get("decided_by") != "project_owner":
            raise ValueError(f"{case_id}: decision is not project-owner approved")
        _validate_timestamp(item.get("decided_at"), field="decided_at", context=case_id)
        _required_string(item.get("reason"), field="reason", context=case_id)
        if case_id not in by_case:
            raise ValueError(f"{case_id}: decision references an unknown query")
        case = by_case[case_id]
        expected = item.get("expected")
        reference = case["review_reference"]
        if case["case_type"] == "positive_family":
            _exact_fields(expected, {"knowledge_type", "review_family_id"}, context=case_id)
            family_id = reference["review_family_id"]
            if expected != {
                "knowledge_type": "review_family",
                "review_family_id": family_id,
            } or family_id not in family_ids:
                raise ValueError(f"{case_id}: positive expected label differs from registry")
        elif case["case_type"] == "merge_control":
            _exact_fields(
                expected,
                {"casting_id", "forbidden_review_family_id", "knowledge_type"},
                context=case_id,
            )
            family_id = reference["source_family_review_id"]
            link = merge_by_id[family_id]
            if expected != {
                "casting_id": link["target_casting_id"],
                "forbidden_review_family_id": family_id,
                "knowledge_type": "provisional_variant",
            } or link["target_casting_id"] not in human_ids:
                raise ValueError(f"{case_id}: merge expected label differs from registry")
        elif case["case_type"] == "hold_control":
            _exact_fields(
                expected,
                {"expected_materialized", "forbidden_review_family_id"},
                context=case_id,
            )
            family_id = reference["review_family_id"]
            if expected != {
                "expected_materialized": False,
                "forbidden_review_family_id": family_id,
            } or family_id not in hold_ids:
                raise ValueError(f"{case_id}: hold expected label differs from registry")
        else:
            _exact_fields(
                expected,
                {"expected_candidate_count", "zero_token_overlap"},
                context=case_id,
            )
            if expected != {"expected_candidate_count": 0, "zero_token_overlap": True}:
                raise ValueError(f"{case_id}: unrelated expected label differs from contract")

    if decision_ids != sorted(decision_ids):
        raise ValueError("owner decisions must be ordered by case_id")
    if len(decision_ids) != len(set(decision_ids)) or set(decision_ids) != set(by_case):
        raise ValueError("owner decisions are duplicate, partial, or changed")
    if not decisions_path.is_file():
        raise ValueError("owner-decision file is missing")


def build_benchmark(
    *,
    query_pack_path: Path,
    query_pack_manifest_path: Path,
    decisions_path: Path,
    registry_path: Path,
    registry_manifest_path: Path,
    projection_path: Path,
    projection_manifest_path: Path,
    human_path: Path,
    human_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    query_pack = _load(query_pack_path)
    query_pack_manifest = _load(query_pack_manifest_path)
    decisions = _load(decisions_path)
    registry = _load(registry_path)
    registry_manifest = _load(registry_manifest_path)
    projection = _load(projection_path)
    projection_manifest = _load(projection_manifest_path)
    human = _load(human_path)
    human_manifest = _load(human_manifest_path)
    sut = _validate_sources(
        registry_path=registry_path,
        registry=registry,
        registry_manifest_path=registry_manifest_path,
        registry_manifest=registry_manifest,
        projection_path=projection_path,
        projection=projection,
        projection_manifest_path=projection_manifest_path,
        projection_manifest=projection_manifest,
        human_path=human_path,
        human=human,
        human_manifest_path=human_manifest_path,
        human_manifest=human_manifest,
    )
    accounting = validate_query_pack(
        query_pack,
        registry=registry,
        projection=projection,
        human=human,
        system_under_test=sut,
    )
    expected_pack_manifest = expected_query_pack_manifest(
        query_pack_path, query_pack, accounting
    )
    _validate_query_pack_manifest(query_pack_manifest, expected_pack_manifest)
    _validate_owner_decisions(
        decisions,
        decisions_path=decisions_path,
        query_pack_path=query_pack_path,
        query_pack=query_pack,
        registry=registry,
        human=human,
    )
    expected_by_id = {item["case_id"]: item["expected"] for item in decisions["decisions"]}
    cases = [
        {**case, "expected": expected_by_id[case["case_id"]]}
        for case in query_pack["cases"]
    ]
    benchmark = {
        "benchmark_version": BENCHMARK_VERSION,
        "cases": cases,
        "decision_version": DECISIONS_VERSION,
        "eligible_for": ELIGIBLE_FOR,
        "excluded_from": EXCLUDED_FROM,
        "query_pack_version": QUERY_PACK_VERSION,
        "schema_version": BENCHMARK_SCHEMA,
        "split": "test",
        "status": "frozen_test_only",
        "system_under_test": sut,
    }
    benchmark_text = _stable_json(benchmark).encode("utf-8")
    benchmark_sha256 = hashlib.sha256(benchmark_text).hexdigest()
    manifest = {
        **accounting,
        "benchmark_file": "benchmark.json",
        "benchmark_sha256": benchmark_sha256,
        "benchmark_version": BENCHMARK_VERSION,
        "eligible_for": ELIGIBLE_FOR,
        "excluded_from": EXCLUDED_FROM,
        "inputs": {
            "human_catalog": _file_reference(human_path, version=HUMAN_VERSION),
            "human_catalog_manifest": _file_reference(human_manifest_path),
            "owner_decisions": _file_reference(decisions_path, version=DECISIONS_VERSION),
            "query_pack": _file_reference(query_pack_path, version=QUERY_PACK_VERSION),
            "query_pack_manifest": _file_reference(query_pack_manifest_path),
            "review_family_knowledge": _file_reference(
                projection_path, version=PROJECTION_VERSION
            ),
            "review_family_knowledge_manifest": _file_reference(projection_manifest_path),
            "review_family_registry": _file_reference(registry_path, version=REGISTRY_VERSION),
            "review_family_registry_manifest": _file_reference(registry_manifest_path),
        },
        "schema_version": BENCHMARK_MANIFEST_SCHEMA,
        "status": "frozen_test_only",
        "system_under_test": sut,
    }
    return benchmark, manifest


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _check_text(path: Path, expected: str) -> None:
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"{path.name}: frozen output is missing") from error
    if actual != expected:
        raise ValueError(f"{path.name}: frozen output is stale")


def _load_and_validate_query_pack(
    *,
    query_pack_path: Path,
    registry_path: Path,
    registry_manifest_path: Path,
    projection_path: Path,
    projection_manifest_path: Path,
    human_path: Path,
    human_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    query_pack = _load(query_pack_path)
    registry = _load(registry_path)
    projection = _load(projection_path)
    human = _load(human_path)
    sut = _validate_sources(
        registry_path=registry_path,
        registry=registry,
        registry_manifest_path=registry_manifest_path,
        registry_manifest=_load(registry_manifest_path),
        projection_path=projection_path,
        projection=projection,
        projection_manifest_path=projection_manifest_path,
        projection_manifest=_load(projection_manifest_path),
        human_path=human_path,
        human=human,
        human_manifest_path=human_manifest_path,
        human_manifest=_load(human_manifest_path),
    )
    accounting = validate_query_pack(
        query_pack,
        registry=registry,
        projection=projection,
        human=human,
        system_under_test=sut,
    )
    return query_pack, expected_query_pack_manifest(query_pack_path, query_pack, accounting)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query-pack", type=Path, default=EVALUATION_DIR / "query-pack.json")
    parser.add_argument(
        "--query-pack-manifest",
        type=Path,
        default=EVALUATION_DIR / "query-pack-manifest.json",
    )
    parser.add_argument(
        "--owner-decisions",
        type=Path,
        default=EVALUATION_DIR / "owner-decisions.json",
    )
    parser.add_argument("--registry", type=Path, default=ROOT / "data/review_family_registry.json")
    parser.add_argument(
        "--registry-manifest",
        type=Path,
        default=ROOT / "data/review_family_registry_manifest.json",
    )
    parser.add_argument(
        "--projection",
        type=Path,
        default=ROOT / "data/review_family_knowledge.json",
    )
    parser.add_argument(
        "--projection-manifest",
        type=Path,
        default=ROOT / "data/review_family_knowledge_manifest.json",
    )
    parser.add_argument(
        "--human-catalog",
        type=Path,
        default=ROOT / "data/human_backed_catalog.json",
    )
    parser.add_argument(
        "--human-catalog-manifest",
        type=Path,
        default=ROOT / "data/human_backed_catalog_manifest.json",
    )
    parser.add_argument("--output", type=Path, default=EVALUATION_DIR / "benchmark.json")
    parser.add_argument("--manifest", type=Path, default=EVALUATION_DIR / "benchmark-manifest.json")
    parser.add_argument("--freeze-query-pack", action="store_true")
    parser.add_argument("--check-query-pack", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if sum((arguments.freeze_query_pack, arguments.check_query_pack, arguments.check)) > 1:
        print("error: choose only one check/freeze mode", file=sys.stderr)
        return 2
    try:
        if arguments.freeze_query_pack or arguments.check_query_pack:
            _query_pack, expected_manifest = _load_and_validate_query_pack(
                query_pack_path=arguments.query_pack,
                registry_path=arguments.registry,
                registry_manifest_path=arguments.registry_manifest,
                projection_path=arguments.projection,
                projection_manifest_path=arguments.projection_manifest,
                human_path=arguments.human_catalog,
                human_manifest_path=arguments.human_catalog_manifest,
            )
            expected_text = _stable_json(expected_manifest)
            if arguments.check_query_pack:
                _check_text(arguments.query_pack_manifest, expected_text)
                print("family retrieval query pack is valid and frozen")
            else:
                _atomic_write(arguments.query_pack_manifest, expected_text)
                print(f"wrote {arguments.query_pack_manifest}")
            return 0

        benchmark, manifest = build_benchmark(
            query_pack_path=arguments.query_pack,
            query_pack_manifest_path=arguments.query_pack_manifest,
            decisions_path=arguments.owner_decisions,
            registry_path=arguments.registry,
            registry_manifest_path=arguments.registry_manifest,
            projection_path=arguments.projection,
            projection_manifest_path=arguments.projection_manifest,
            human_path=arguments.human_catalog,
            human_manifest_path=arguments.human_catalog_manifest,
        )
        benchmark_text = _stable_json(benchmark)
        manifest = {**manifest, "benchmark_file": arguments.output.name}
        manifest_text = _stable_json(manifest)
        if arguments.check:
            _check_text(arguments.output, benchmark_text)
            _check_text(arguments.manifest, manifest_text)
            print("family retrieval benchmark is reproducible")
        else:
            _atomic_write(arguments.output, benchmark_text)
            _atomic_write(arguments.manifest, manifest_text)
            print(f"wrote {arguments.output}")
            print(f"wrote {arguments.manifest}")
        return 0
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
