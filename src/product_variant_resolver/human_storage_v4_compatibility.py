"""Exact-hash bridge between frozen v4 math evidence and the optional storage app.

The historical selection report remains immutable and continues to reject source drift through its
original loader. This module is deliberately narrower: it permits one enumerated wrapper revision
for the separately selected human-storage app while preserving every identity-math binding.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .human_knowledge_identity import (
    MANIFEST_SHA256,
    PROTOCOL_SHA256,
    VERSION,
    HumanKnowledgeV4Config,
)
from .human_knowledge_identity_artifact import (
    ARTIFACT_SCHEMA,
    PROTOCOL_DIRECTORY,
    REPORT_DIRECTORY,
    load_identity_protocol,
    safe_path,
)
from .human_knowledge_selection import load_object, sha

ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY_FILE = Path(
    "data/evaluation/human-storage-profile-development-v1/"
    "runtime-v4-compatibility-v1.json"
)
COMPATIBILITY_SHA256 = "532da37ed79280b2aa047766ad9aaaa1aeec51f12ab756e3d250cdeb4e3d86bd"
MATH_ARTIFACT_SHA256 = "82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b"
SELECTION_REPORT_SHA256 = "f52f85f775806d43a57c11e5fa9f7f965da980f54cc58a814d727fdfe7876f42"
PROTOCOL_MANIFEST_FILE_SHA256 = (
    "b7634f7f3d52277c4ee4d92489b656fcf1a6c446d56085c5affb7cb7a12c6ea7"
)

_EXPECTED_TOP_LEVEL = {
    "allowed_current_wrapper_sources",
    "artifact_version",
    "bindings",
    "historical_selection_sources",
    "preserved_claims",
    "prohibited_actions",
    "schema_version",
    "status",
    "unchanged_runtime_sources",
}
_EXPECTED_BINDINGS = {
    "math_artifact_file": "config/human-knowledge-retrieval-v4.json",
    "math_artifact_sha256": MATH_ARTIFACT_SHA256,
    "protocol_file_sha256": PROTOCOL_SHA256,
    "protocol_manifest_file_sha256": PROTOCOL_MANIFEST_FILE_SHA256,
    "selection_report_file": str(REPORT_DIRECTORY / "selection.json"),
    "selection_report_sha256": SELECTION_REPORT_SHA256,
}
_PRESERVED_CLAIMS = [
    "historical_selection_evidence_is_byte_identical",
    "identity_math_sources_are_byte_identical",
    "canonical_response_parity_requires_current_tests",
    "compatibility_is_exact_hash_and_storage_app_only",
]
_PROHIBITED_ACTIONS = [
    "rewrite_or_refreeze_historical_selection_evidence",
    "claim_historical_evaluation_used_current_wrappers",
    "change_v4_identity_parameters_or_candidate_math",
    "enable_human_storage_as_default_runtime",
    "admit_unlisted_future_source_versions",
]


def _validate_compatibility(root: Path) -> dict[str, Any]:
    path = safe_path(root, str(COMPATIBILITY_FILE))
    if sha(path) != COMPATIBILITY_SHA256:
        raise ValueError("human-storage v4 compatibility artifact checksum differs")
    payload = load_object(path)
    if (set(payload) != _EXPECTED_TOP_LEVEL
            or payload["schema_version"] != "pvr-human-storage-v4-runtime-compatibility-v1"
            or payload["artifact_version"] != "human-storage-v4-runtime-compatibility-v1"
            or payload["status"] != "exact_wrapper_compatibility_only"
            or payload["bindings"] != _EXPECTED_BINDINGS
            or payload["preserved_claims"] != _PRESERVED_CLAIMS
            or payload["prohibited_actions"] != _PROHIBITED_ACTIONS):
        raise ValueError("human-storage v4 compatibility contract differs")

    historical = payload["historical_selection_sources"]
    current = payload["allowed_current_wrapper_sources"]
    unchanged = payload["unchanged_runtime_sources"]
    if (not isinstance(historical, dict) or not isinstance(current, dict)
            or not isinstance(unchanged, dict)
            or set(current) != {
                "src/product_variant_resolver/api.py",
                "src/product_variant_resolver/config.py",
                "src/product_variant_resolver/service.py",
            }):
        raise ValueError("human-storage v4 compatibility source boundary differs")
    for sources, label in ((current, "allowed wrapper"), (unchanged, "unchanged runtime")):
        for relative, checksum in sources.items():
            if (not isinstance(relative, str) or not isinstance(checksum, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", checksum)
                    or sha(safe_path(root, relative)) != checksum):
                raise ValueError(f"human-storage v4 {label} source differs")
    return payload


def load_human_storage_v4_config(
    artifact_path: Path,
    *,
    human_catalog_path: Path,
    review_family_path: Path,
    development_pack_path: Path,
    development_manifest_path: Path,
    dense_dimensions: int,
    root: Path = ROOT,
) -> HumanKnowledgeV4Config:
    """Load frozen v4 math under one exact storage-wrapper compatibility artifact."""
    compatibility = _validate_compatibility(root)
    protocol = load_identity_protocol(root)
    bindings = compatibility["bindings"]
    expected_artifact = safe_path(root, bindings["math_artifact_file"])
    if artifact_path.resolve() != expected_artifact or sha(artifact_path) != MATH_ARTIFACT_SHA256:
        raise ValueError("human-storage v4 math artifact path/checksum differs")

    artifact = load_object(artifact_path)
    expected_artifact_fields = {
        "schema_version", "artifact_version", "retriever_version", "status", "configuration",
        "identity_policy", "limits", "protocol_sha256", "protocol_manifest_sha256", "sources",
        "selection_evidence", "eligible_for", "excluded_from",
    }
    if (set(artifact) != expected_artifact_fields
            or artifact["schema_version"] != ARTIFACT_SCHEMA
            or artifact["retriever_version"] != VERSION
            or artifact["status"] != "selected_development_configuration"
            or not re.fullmatch(
                r"human-knowledge-retrieval-v4-[a-z0-9-]+", artifact["artifact_version"]
            )
            or artifact["identity_policy"] != protocol["identity_policy"]
            or artifact["limits"] != protocol["limits"]
            or artifact["protocol_sha256"] != PROTOCOL_SHA256
            or artifact["protocol_manifest_sha256"] != MANIFEST_SHA256
            or artifact["eligible_for"] != ["human_knowledge_debug_retrieval"]
            or artifact["excluded_from"] != protocol["excluded_from"]):
        raise ValueError("human-storage v4 math artifact contract differs")

    historical = compatibility["historical_selection_sources"]
    unchanged = compatibility["unchanged_runtime_sources"]
    if (artifact["sources"] != historical
            or any(historical.get(name) != checksum for name, checksum in unchanged.items()
                   if name in historical)):
        raise ValueError("human-storage v4 historical source binding differs")

    manifest = load_object(root / PROTOCOL_DIRECTORY / "protocol-manifest.json")
    inputs = (
        (human_catalog_path, "data/human_backed_catalog.json"),
        (review_family_path, "data/review_family_knowledge.json"),
        (
            development_pack_path,
            "data/evaluation/family-retrieval-development-v1/development-pack.json",
        ),
        (
            development_manifest_path,
            "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json",
        ),
    )
    if any(sha(path) != manifest["input_sha256"][name] for path, name in inputs):
        raise ValueError("human-storage v4 configured corpus/development differs")

    configuration = artifact["configuration"]
    fixed = {
        "dense_dimensions": 192,
        "dense_rrf_weight": 1.0,
        "sparse_rrf_weight": 1.0,
        "rrf_k": 60,
        "selection_candidate_limit": 5,
        "source_candidate_limit": 25,
    }
    if (set(configuration) != set(fixed) | {
            "character_score_floor", "character_rrf_weight"}
            or any(type(configuration[key]) not in {int, float}
                   or configuration[key] != value for key, value in fixed.items())
            or dense_dimensions != 192):
        raise ValueError("human-storage v4 fixed parameters differ")

    evidence = artifact["selection_evidence"]
    if (not isinstance(evidence, dict)
            or set(evidence) != {"file", "sha256", "configuration_summaries"}
            or evidence["file"] != bindings["selection_report_file"]
            or evidence["sha256"] != SELECTION_REPORT_SHA256):
        raise ValueError("human-storage v4 selection evidence binding differs")
    report_path = safe_path(root, evidence["file"])
    if (report_path.parent != (root / REPORT_DIRECTORY).resolve()
            or sha(report_path) != SELECTION_REPORT_SHA256):
        raise ValueError("human-storage v4 selection report checksum differs")
    report = load_object(report_path)
    summaries = [
        {key: entry[key] for key in (
            "configuration", "metrics", "scale_hits", "rejection_reasons",
        )}
        for entry in report["configurations"]
    ]
    selected = {
        "character_score_floor": configuration["character_score_floor"],
        "character_rrf_weight": configuration["character_rrf_weight"],
    }
    if (report.get("schema_version") != "pvr-human-knowledge-identity-selection-v1"
            or report.get("protocol_sha256") != PROTOCOL_SHA256
            or report.get("protocol_manifest_sha256") != MANIFEST_SHA256
            or report.get("sources") != historical
            or report.get("winner") != selected
            or report.get("verdict") != "PASS"
            or evidence["configuration_summaries"] != summaries):
        raise ValueError("human-storage v4 frozen selection evidence differs")
    return HumanKnowledgeV4Config(
        configuration["character_score_floor"],
        configuration["character_rrf_weight"],
        artifact["artifact_version"],
        MATH_ARTIFACT_SHA256,
    )
