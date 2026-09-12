#!/usr/bin/env python3
"""Build and validate the development-only family-retrieval challenge pack."""

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
DATA_DIR = ROOT / "data"
OUTPUT_DIR = DATA_DIR / "evaluation" / "family-retrieval-development-v1"

REGISTRY = DATA_DIR / "review_family_registry.json"
REGISTRY_MANIFEST = DATA_DIR / "review_family_registry_manifest.json"
PROJECTION = DATA_DIR / "review_family_knowledge.json"
PROJECTION_MANIFEST = DATA_DIR / "review_family_knowledge_manifest.json"
HUMAN = DATA_DIR / "human_backed_catalog.json"
HUMAN_MANIFEST = DATA_DIR / "human_backed_catalog_manifest.json"
V1_QUERY_PACK = DATA_DIR / "evaluation" / "family-retrieval-v1" / "query-pack.json"
V1_QUERY_PACK_MANIFEST = (
    DATA_DIR / "evaluation" / "family-retrieval-v1" / "query-pack-manifest.json"
)

PACK_SCHEMA = "pvr-family-retrieval-development-v1"
MANIFEST_SCHEMA = "pvr-family-retrieval-development-manifest-v1"
DEVELOPMENT_VERSION = "family-retrieval-development-v1"
REGISTRY_VERSION = "fandom-2025-review-families-r790665-v1"
PROJECTION_VERSION = "review-family-knowledge-fandom-2025-r790665-v1"
HUMAN_VERSION = "human-backed-catalog-v1"
V1_QUERY_PACK_VERSION = "family-retrieval-query-pack-v1"

CASE_COUNTS = {
    "hold_control": 7,
    "merge_control": 4,
    "positive_family": 168,
    "unrelated_control": 20,
}
STYLE_COUNTS = {
    "abbreviation_numeric": 42,
    "contextual_noise": 42,
    "generic_no_identity": 10,
    "held_identity": 7,
    "merge_existing_family": 4,
    "opaque_no_overlap": 10,
    "single_edit": 42,
    "spacing_punctuation": 42,
}
POSITIVE_STYLES = (
    "single_edit",
    "spacing_punctuation",
    "abbreviation_numeric",
    "contextual_noise",
)
ELIGIBLE_FOR = [
    "human_knowledge_retriever_implementation",
    "human_knowledge_retriever_configuration_selection",
]
EXCLUDED_FROM = [
    "calibration_training",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_variant_response",
    "family_retrieval_final_evaluation",
    "postgresql_ingestion",
    "production_accuracy_claim",
    "release_variant_ground_truth",
]
AUTHORING_POLICY = {
    "derived_from_indexed_identities": True,
    "development_only": True,
    "final_accuracy_eligible": False,
    "method": "deterministic-indexed-identity-transformations-v1",
    "retriever_output_viewed": False,
    "v1_query_text_used_only_for_non_reuse_validation": True,
}
SELECTION_CONTRACT = {
    "candidate_limit": 5,
    "character_rrf_weights": [0.5, 1.0, 1.5],
    "character_score_floors": [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55],
    "configuration_count": 21,
    "dense_dimensions": 192,
    "dense_weight": 1.0,
    "failure_rule": "no_qualifying_configuration_means_fail_without_runtime_artifact",
    "rrf_k": 60,
    "safety_gates": {
        "merge_recall_at_5_minimum": 1.0,
        "hold_materialized_count": 0,
        "positive_recall_at_5_minimum": 0.9,
        "positive_style_recall_at_5_minimum": 0.85,
        "merge_wrong_family_count": 0,
        "unrelated_nonempty_count": 0,
    },
    "sparse_weight": 1.0,
    "tie_break_order": [
        "positive_mrr_desc",
        "positive_recall_at_1_desc",
        "character_score_floor_desc",
        "character_rrf_weight_asc",
    ],
}

OPAQUE_QUERIES = tuple(f"qxjv{index:02d}zorphelt" for index in range(10))
GENERIC_QUERIES = (
    "sealed blue collector model from storage box",
    "loose red miniature with light shelf wear",
    "carded silver toy vehicle local pickup",
    "unopened black collector item estate find",
    "green diecast piece missing outer package",
    "orange miniature vehicle from display case",
    "white toy car in protective blister pack",
    "purple collectible model sold as pictured",
    "yellow small scale vehicle cabinet find",
    "gray boxed miniature with unknown maker",
)


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name}: could not read valid JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return payload


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"{path.name}: could not read file for checksum") from error


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w]+", normalized, flags=re.UNICODE))


def _source_reference(path: Path, version: str, use: str) -> dict[str, str]:
    return {
        "file": str(path.relative_to(ROOT)),
        "sha256": _sha256(path),
        "use": use,
        "version": version,
    }


def _validate_manifest_binding(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    schema: str,
    data_path: Path,
    file_field: str,
    hash_field: str,
) -> None:
    if manifest.get("schema_version") != schema:
        raise ValueError(f"{manifest_path.name}: schema differs from contract")
    if manifest.get(file_field) != data_path.name or manifest.get(hash_field) != _sha256(
        data_path
    ):
        raise ValueError(f"{manifest_path.name}: source binding is stale or mismatched")


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
    v1_query_pack_path: Path,
    v1_query_pack: dict[str, Any],
    v1_query_pack_manifest_path: Path,
    v1_query_pack_manifest: dict[str, Any],
) -> None:
    if registry.get("registry_version") != REGISTRY_VERSION:
        raise ValueError("review-family registry version differs from contract")
    for section, count in (("new_families", 42), ("merge_links", 4), ("hold_exclusions", 7)):
        if not isinstance(registry.get(section), list) or len(registry[section]) != count:
            raise ValueError(f"review-family registry {section} count differs from contract")
    _validate_manifest_binding(
        manifest=registry_manifest,
        manifest_path=registry_manifest_path,
        schema="pvr-review-family-registry-manifest-v1",
        data_path=registry_path,
        file_field="registry_file",
        hash_field="registry_sha256",
    )

    if projection.get("knowledge_version") != PROJECTION_VERSION:
        raise ValueError("review-family projection version differs from contract")
    documents = projection.get("documents")
    if not isinstance(documents, list) or len(documents) != 42:
        raise ValueError("review-family projection must contain exactly 42 documents")
    _validate_manifest_binding(
        manifest=projection_manifest,
        manifest_path=projection_manifest_path,
        schema="pvr-review-family-knowledge-manifest-v1",
        data_path=projection_path,
        file_field="projection_file",
        hash_field="projection_sha256",
    )

    if human.get("catalog_version") != HUMAN_VERSION:
        raise ValueError("human-backed catalog version differs from contract")
    castings = human.get("castings")
    if not isinstance(castings, list) or len(castings) != 97:
        raise ValueError("human-backed catalog must contain exactly 97 castings")
    _validate_manifest_binding(
        manifest=human_manifest,
        manifest_path=human_manifest_path,
        schema="pvr-human-backed-catalog-manifest-v1",
        data_path=human_path,
        file_field="catalog_file",
        hash_field="catalog_sha256",
    )

    if v1_query_pack.get("query_pack_version") != V1_QUERY_PACK_VERSION:
        raise ValueError("v1 query-pack version differs from contract")
    v1_cases = v1_query_pack.get("cases")
    if not isinstance(v1_cases, list) or len(v1_cases) != 105:
        raise ValueError("v1 query pack must contain exactly 105 cases")
    _validate_manifest_binding(
        manifest=v1_query_pack_manifest,
        manifest_path=v1_query_pack_manifest_path,
        schema="pvr-family-retrieval-query-pack-manifest-v1",
        data_path=v1_query_pack_path,
        file_field="query_pack_file",
        hash_field="query_pack_sha256",
    )

    registry_ids = {item["review_family_id"] for item in registry["new_families"]}
    projection_ids = {item["review_family_id"] for item in documents}
    if len(registry_ids) != 42 or projection_ids != registry_ids:
        raise ValueError("projection coverage differs from the accepted-family registry")
    human_ids = {item["casting_id"] for item in castings}
    if any(item["target_casting_id"] not in human_ids for item in registry["merge_links"]):
        raise ValueError("a merge target is missing from the human-backed catalog")


def _knowledge_tokens(projection: dict[str, Any], human: dict[str, Any]) -> set[str]:
    values: list[str] = []
    for document in projection["documents"]:
        values.extend((document["brand"], document["casting"], *document["aliases"]))
    for casting in human["castings"]:
        values.extend((casting["brand"], casting["casting"]))
        for variant in casting["provisional_variants"]:
            for field in ("human_label_names", "pricing_keywords", "initial_names"):
                values.extend(variant[field])
    return set(_normalize(" ".join(values)).split())


def _identity_phrases(
    registry: dict[str, Any], projection: dict[str, Any], human: dict[str, Any]
) -> set[str]:
    values: list[str] = []
    for document in projection["documents"]:
        values.extend((document["casting"], *document["aliases"]))
    for section in ("new_families", "merge_links", "hold_exclusions"):
        values.extend(item["display_name"] for item in registry[section])
    values.extend(item["casting"] for item in human["castings"])
    return {_normalize(value) for value in values if _normalize(value)}


def _single_edit(identity: str) -> str:
    tokens = _normalize(identity).split()
    eligible = [(len(token), index, token) for index, token in enumerate(tokens) if len(token) >= 3]
    if not eligible:
        raise ValueError(f"identity cannot support a single-edit transformation: {identity}")
    _, index, token = max(eligible)
    position = max(1, len(token) // 2)
    tokens[index] = token[:position] + token[position + 1 :]
    return f"{' '.join(tokens)} loose collector piece"


def _spacing_punctuation(identity: str) -> str:
    tokens = _normalize(identity).split()
    if len(tokens) == 1:
        token = tokens[0]
        position = max(1, len(token) // 2)
        changed = f"{token[:position]} {token[position:]}"
    else:
        changed = "".join(tokens)
    return f"carded {changed} miniature"


def _abbreviation_numeric(identity: str) -> str:
    tokens = _normalize(identity).split()
    changed = list(tokens)
    numeric_index = next((i for i, token in enumerate(tokens) if any(c.isdigit() for c in token)), None)
    if numeric_index is not None:
        token = tokens[numeric_index]
        if token.isdigit() and len(token) == 4:
            changed[numeric_index] = token[-2:]
        else:
            changed[numeric_index] = token.replace("0", "o", 1) if "0" in token else f"{token}x"
    else:
        index = max(range(len(tokens)), key=lambda item: (len(tokens[item]), item))
        token = tokens[index]
        changed[index] = token[: max(2, len(token) // 2)]
    return f"{' '.join(changed)} diecast vehicle"


def _positive_case(document: dict[str, Any], style: str) -> dict[str, Any]:
    family_id = document["review_family_id"]
    identity = document["casting"]
    suffix = family_id.removeprefix("fandom-family-")
    transformations = {
        "single_edit": (_single_edit(identity), ["misspelling"]),
        "spacing_punctuation": (_spacing_punctuation(identity), ["punctuation", "spacing"]),
        "abbreviation_numeric": (_abbreviation_numeric(identity), ["abbreviation", "year_noise"]),
        "contextual_noise": (
            f"warehouse find {identity} unboxed collector sale",
            ["condition_noise", "marketplace_wrapper"],
        ),
    }
    query, tags = transformations[style]
    return {
        "case_id": f"frd-positive-{suffix}-{style.replace('_', '-')}",
        "case_type": "positive_family",
        "casting_group_id": f"review:{family_id}",
        "challenge_style": style,
        "derived_from_indexed_identity": True,
        "expected": {
            "knowledge_type": "review_family",
            "review_family_id": family_id,
        },
        "noise_tags": tags,
        "query_origin": "indexed_identity_transformation",
        "query_text": query,
        "split": "dev",
        "transformation_method": style,
    }


def _control_case(item: dict[str, Any], kind: str) -> dict[str, Any]:
    if kind == "merge":
        family_id = item["source_family_review_id"]
        return {
            "case_id": f"frd-merge-{family_id.removeprefix('fandom-family-')}",
            "case_type": "merge_control",
            "casting_group_id": f"merge:{family_id}",
            "challenge_style": "merge_existing_family",
            "derived_from_indexed_identity": True,
            "expected": {
                "casting_id": item["target_casting_id"],
                "forbidden_review_family_id": family_id,
                "knowledge_type": "provisional_variant",
            },
            "noise_tags": ["condition_noise", "marketplace_wrapper"],
            "query_origin": "governance_identity_transformation",
            "query_text": f"preowned {item['display_name']} miniature from collector cabinet",
            "split": "dev",
            "transformation_method": "merge_control_wrapper",
        }
    family_id = item["review_family_id"]
    return {
        "case_id": f"frd-hold-{family_id.removeprefix('fandom-family-')}",
        "case_type": "hold_control",
        "casting_group_id": f"hold:{family_id}",
        "challenge_style": "held_identity",
        "derived_from_indexed_identity": True,
        "expected": {
            "expected_materialized": False,
            "forbidden_review_family_id": family_id,
        },
        "noise_tags": ["identity_ambiguity", "seller_wrapper"],
        "query_origin": "governance_identity_transformation",
        "query_text": f"unverified listing {item['display_name']} loose model lineage unclear",
        "split": "dev",
        "transformation_method": "hold_control_wrapper",
    }


def _unrelated_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, query in enumerate(OPAQUE_QUERIES):
        control_id = f"opaque-{index:02d}"
        cases.append(
            {
                "case_id": f"frd-unrelated-{control_id}",
                "case_type": "unrelated_control",
                "casting_group_id": f"unrelated:{control_id}",
                "challenge_style": "opaque_no_overlap",
                "derived_from_indexed_identity": False,
                "expected": {"expected_candidate_count": 0, "zero_token_overlap": True},
                "noise_tags": ["no_overlap"],
                "query_origin": "synthetic_negative_control",
                "query_text": query,
                "split": "dev",
                "transformation_method": "opaque_token_generation",
            }
        )
    for index, query in enumerate(GENERIC_QUERIES):
        control_id = f"generic-{index:02d}"
        cases.append(
            {
                "case_id": f"frd-unrelated-{control_id}",
                "case_type": "unrelated_control",
                "casting_group_id": f"unrelated:{control_id}",
                "challenge_style": "generic_no_identity",
                "derived_from_indexed_identity": False,
                "expected": {"expected_candidate_count": 0, "zero_token_overlap": False},
                "noise_tags": ["generic_marketplace", "marketplace_wrapper"],
                "query_origin": "synthetic_negative_control",
                "query_text": query,
                "split": "dev",
                "transformation_method": "generic_marketplace_without_identity",
            }
        )
    return cases


def _validate_pack(
    pack: dict[str, Any],
    *,
    registry: dict[str, Any],
    projection: dict[str, Any],
    human: dict[str, Any],
    v1_query_pack: dict[str, Any],
) -> dict[str, Any]:
    expected_pack_fields = {
        "authorship_policy",
        "cases",
        "configuration_output_viewed",
        "derived_from_indexed_identity",
        "development_version",
        "eligible_for",
        "excluded_from",
        "expected_counts",
        "retrieval_executed",
        "schema_version",
        "selection_contract",
        "split",
        "status",
    }
    if set(pack) != expected_pack_fields:
        raise ValueError("development pack fields differ from contract")
    if (
        pack.get("schema_version") != PACK_SCHEMA
        or pack.get("development_version") != DEVELOPMENT_VERSION
    ):
        raise ValueError("development pack identity differs from contract")
    if (
        pack.get("status") != "frozen_development_only"
        or pack.get("split") != "dev"
        or pack.get("eligible_for") != ELIGIBLE_FOR
        or pack.get("excluded_from") != EXCLUDED_FROM
        or pack.get("authorship_policy") != AUTHORING_POLICY
        or pack.get("selection_contract") != SELECTION_CONTRACT
        or pack.get("expected_counts") != CASE_COUNTS
        or pack.get("derived_from_indexed_identity") is not True
        or pack.get("retrieval_executed") is not False
        or pack.get("configuration_output_viewed") is not False
    ):
        raise ValueError("development pack governance boundary differs from contract")
    cases = pack.get("cases")
    if not isinstance(cases, list) or len(cases) != 199:
        raise ValueError("development pack must contain exactly 199 cases")
    case_ids = [item.get("case_id") for item in cases]
    queries = [_normalize(str(item.get("query_text", ""))) for item in cases]
    if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("development cases must have unique, sorted case IDs")
    if any(not query for query in queries) or len(queries) != len(set(queries)):
        raise ValueError("development queries must be non-empty and normalized-unique")
    v1_queries = {_normalize(str(item.get("query_text", ""))) for item in v1_query_pack["cases"]}
    if set(queries) & v1_queries:
        raise ValueError("development query reuses a frozen v1 query")

    case_counts = Counter(item.get("case_type") for item in cases)
    style_counts = Counter(item.get("challenge_style") for item in cases)
    if dict(sorted(case_counts.items())) != CASE_COUNTS:
        raise ValueError("development case composition differs from contract")
    if dict(sorted(style_counts.items())) != STYLE_COUNTS:
        raise ValueError("development challenge-style composition differs from contract")

    family_ids = {item["review_family_id"] for item in registry["new_families"]}
    merge_by_id = {
        item["source_family_review_id"]: item for item in registry["merge_links"]
    }
    hold_ids = {item["review_family_id"] for item in registry["hold_exclusions"]}
    positive_styles: dict[str, set[str]] = defaultdict(set)
    covered_merge: set[str] = set()
    covered_hold: set[str] = set()
    unrelated_groups: set[str] = set()
    for case in cases:
        required = {
            "case_id",
            "case_type",
            "casting_group_id",
            "challenge_style",
            "derived_from_indexed_identity",
            "expected",
            "noise_tags",
            "query_origin",
            "query_text",
            "split",
            "transformation_method",
        }
        if set(case) != required or case["split"] != "dev":
            raise ValueError(f"{case.get('case_id')}: fields or split differ from contract")
        if (
            not isinstance(case["query_text"], str)
            or not isinstance(case["casting_group_id"], str)
            or not isinstance(case["expected"], dict)
            or not isinstance(case["noise_tags"], list)
            or not all(isinstance(tag, str) and tag for tag in case["noise_tags"])
        ):
            raise ValueError(f"{case['case_id']}: query or noise tags are invalid")
        if case["case_type"] == "positive_family":
            family_id = case["expected"].get("review_family_id")
            if (
                not isinstance(family_id, str)
                or family_id not in family_ids
                or case["casting_group_id"] != f"review:{family_id}"
            ):
                raise ValueError(f"{case['case_id']}: positive family binding is invalid")
            if case["expected"].get("knowledge_type") != "review_family":
                raise ValueError(f"{case['case_id']}: positive expected type is invalid")
            if (
                case["query_origin"] != "indexed_identity_transformation"
                or case["derived_from_indexed_identity"] is not True
                or case["transformation_method"] != case["challenge_style"]
            ):
                raise ValueError(f"{case['case_id']}: derived identity disclosure is invalid")
            positive_styles[family_id].add(case["challenge_style"])
        elif case["case_type"] == "merge_control":
            family_id = case["expected"].get("forbidden_review_family_id")
            if not isinstance(family_id, str):
                raise ValueError(f"{case['case_id']}: merge family ID is invalid")
            link = merge_by_id.get(family_id)
            if link is None or case["expected"] != {
                "casting_id": link["target_casting_id"],
                "forbidden_review_family_id": family_id,
                "knowledge_type": "provisional_variant",
            }:
                raise ValueError(f"{case['case_id']}: merge expected label is invalid")
            if (
                case["casting_group_id"] != f"merge:{family_id}"
                or case["challenge_style"] != "merge_existing_family"
                or case["query_origin"] != "governance_identity_transformation"
                or case["derived_from_indexed_identity"] is not True
            ):
                raise ValueError(f"{case['case_id']}: merge governance binding is invalid")
            covered_merge.add(family_id)
        elif case["case_type"] == "hold_control":
            family_id = case["expected"].get("forbidden_review_family_id")
            if not isinstance(family_id, str) or family_id not in hold_ids or case["expected"] != {
                "expected_materialized": False,
                "forbidden_review_family_id": family_id,
            }:
                raise ValueError(f"{case['case_id']}: hold expected label is invalid")
            if (
                case["casting_group_id"] != f"hold:{family_id}"
                or case["challenge_style"] != "held_identity"
                or case["query_origin"] != "governance_identity_transformation"
                or case["derived_from_indexed_identity"] is not True
            ):
                raise ValueError(f"{case['case_id']}: hold governance binding is invalid")
            covered_hold.add(family_id)
        elif case["case_type"] == "unrelated_control":
            group = case["casting_group_id"]
            control_id = group.removeprefix("unrelated:")
            expected = {
                "expected_candidate_count": 0,
                "zero_token_overlap": case["challenge_style"] == "opaque_no_overlap",
            }
            if (
                group != f"unrelated:{control_id}"
                or not control_id
                or case["expected"] != expected
                or case["query_origin"] != "synthetic_negative_control"
                or case["derived_from_indexed_identity"] is not False
            ):
                raise ValueError(f"{case['case_id']}: unrelated control binding is invalid")
            unrelated_groups.add(control_id)
        else:
            raise ValueError(f"{case['case_id']}: case type is unsupported")
    if set(positive_styles) != family_ids or any(
        set(POSITIVE_STYLES) != styles for styles in positive_styles.values()
    ):
        raise ValueError("every accepted family must have exactly four declared positive styles")
    if covered_merge != set(merge_by_id):
        raise ValueError("merge controls do not cover the complete registry")
    if covered_hold != hold_ids:
        raise ValueError("hold controls do not cover the complete registry")
    if len(unrelated_groups) != 20:
        raise ValueError("unrelated controls must contain 20 unique groups")

    knowledge_tokens = _knowledge_tokens(projection, human)
    identity_phrases = _identity_phrases(registry, projection, human)
    for case, query in zip(cases, queries, strict=True):
        if case["challenge_style"] == "opaque_no_overlap" and set(query.split()) & knowledge_tokens:
            raise ValueError(f"{case['case_id']}: opaque control overlaps knowledge tokens")
        if case["challenge_style"] == "generic_no_identity" and any(
            f" {identity} " in f" {query} " for identity in identity_phrases
        ):
            raise ValueError(f"{case['case_id']}: generic control contains a known identity")
    return {
        "case_counts": dict(sorted(case_counts.items())),
        "challenge_style_counts": dict(sorted(style_counts.items())),
        "positive_family_group_count": len(positive_styles),
        "split_counts": {"dev": 199, "test": 0, "train": 0},
    }


def build_development_pack(
    *,
    registry_path: Path = REGISTRY,
    registry_manifest_path: Path = REGISTRY_MANIFEST,
    projection_path: Path = PROJECTION,
    projection_manifest_path: Path = PROJECTION_MANIFEST,
    human_path: Path = HUMAN,
    human_manifest_path: Path = HUMAN_MANIFEST,
    v1_query_pack_path: Path = V1_QUERY_PACK,
    v1_query_pack_manifest_path: Path = V1_QUERY_PACK_MANIFEST,
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = _load(registry_path)
    registry_manifest = _load(registry_manifest_path)
    projection = _load(projection_path)
    projection_manifest = _load(projection_manifest_path)
    human = _load(human_path)
    human_manifest = _load(human_manifest_path)
    v1_query_pack = _load(v1_query_pack_path)
    v1_query_pack_manifest = _load(v1_query_pack_manifest_path)
    _validate_sources(
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
        v1_query_pack_path=v1_query_pack_path,
        v1_query_pack=v1_query_pack,
        v1_query_pack_manifest_path=v1_query_pack_manifest_path,
        v1_query_pack_manifest=v1_query_pack_manifest,
    )
    documents = sorted(projection["documents"], key=lambda item: item["review_family_id"])
    cases = [_positive_case(document, style) for document in documents for style in POSITIVE_STYLES]
    cases.extend(_control_case(item, "merge") for item in registry["merge_links"])
    cases.extend(_control_case(item, "hold") for item in registry["hold_exclusions"])
    cases.extend(_unrelated_cases())
    pack = {
        "authorship_policy": AUTHORING_POLICY,
        "cases": sorted(cases, key=lambda item: item["case_id"]),
        "configuration_output_viewed": False,
        "derived_from_indexed_identity": True,
        "development_version": DEVELOPMENT_VERSION,
        "eligible_for": ELIGIBLE_FOR,
        "excluded_from": EXCLUDED_FROM,
        "expected_counts": CASE_COUNTS,
        "retrieval_executed": False,
        "schema_version": PACK_SCHEMA,
        "selection_contract": SELECTION_CONTRACT,
        "split": "dev",
        "status": "frozen_development_only",
    }
    accounting = _validate_pack(
        pack,
        registry=registry,
        projection=projection,
        human=human,
        v1_query_pack=v1_query_pack,
    )
    pack_text = _stable_json(pack)
    manifest = {
        **accounting,
        "authorship_policy": AUTHORING_POLICY,
        "configuration_output_viewed": False,
        "derived_from_indexed_identity": True,
        "development_file": "development-pack.json",
        "development_sha256": _sha256_text(pack_text),
        "development_version": DEVELOPMENT_VERSION,
        "eligible_for": ELIGIBLE_FOR,
        "excluded_from": EXCLUDED_FROM,
        "inputs": [
            _source_reference(
                ROOT / "scripts" / "build_family_retrieval_development.py",
                DEVELOPMENT_VERSION,
                "authoring_and_validation_implementation",
            ),
            _source_reference(registry_path, REGISTRY_VERSION, "identity_and_governance_source"),
            _source_reference(registry_manifest_path, REGISTRY_VERSION, "source_integrity"),
            _source_reference(projection_path, PROJECTION_VERSION, "indexed_identity_source"),
            _source_reference(projection_manifest_path, PROJECTION_VERSION, "source_integrity"),
            _source_reference(human_path, HUMAN_VERSION, "merge_target_and_vocabulary_validation"),
            _source_reference(human_manifest_path, HUMAN_VERSION, "source_integrity"),
            _source_reference(v1_query_pack_path, V1_QUERY_PACK_VERSION, "non_reuse_validation_only"),
            _source_reference(v1_query_pack_manifest_path, V1_QUERY_PACK_VERSION, "source_integrity"),
        ],
        "retrieval_executed": False,
        "schema_version": MANIFEST_SCHEMA,
        "selection_contract": SELECTION_CONTRACT,
        "split": "dev",
        "status": "frozen_before_configuration_execution",
    }
    return pack, manifest


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def freeze(output_dir: Path, **source_paths: Path) -> None:
    pack, manifest = build_development_pack(**source_paths)
    _atomic_write(output_dir / "development-pack.json", _stable_json(pack))
    _atomic_write(output_dir / "development-pack-manifest.json", _stable_json(manifest))


def check(output_dir: Path) -> None:
    pack, manifest = build_development_pack()
    expected = {
        output_dir / "development-pack.json": _stable_json(pack),
        output_dir / "development-pack-manifest.json": _stable_json(manifest),
    }
    for path, text in expected.items():
        try:
            current = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"{path.name}: frozen output is missing") from error
        if current != text:
            raise ValueError(f"{path.name}: frozen bytes are stale or changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true", help="write deterministic frozen artifacts")
    mode.add_argument("--check", action="store_true", help="validate checked-in artifacts byte-for-byte")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    try:
        freeze(args.output_dir) if args.freeze else check(args.output_dir)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    action = "froze" if args.freeze else "verified"
    print(f"{action} {DEVELOPMENT_VERSION}: 199 dev cases; retrieval_executed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
