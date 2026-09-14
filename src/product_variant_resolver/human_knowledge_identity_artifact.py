"""Strict v4 artifact/evidence contract. Parsing never executes retrieval or selects floats."""
from __future__ import annotations

import math
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from .human_knowledge import load_human_knowledge_catalog
from .human_knowledge_identity import (
    MANIFEST_SHA256,
    NOISE,
    PROTOCOL_SHA256,
    VERSION,
    HumanKnowledgeV4Config,
    IdentityLimits,
    IdentityRetrievalWork,
)
from .human_knowledge_selection import (
    choose,
    grid,
    latency,
    load_object,
    rejection_reasons,
    sha,
    summarize,
    synthetic_catalog,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_DIRECTORY = Path("data/evaluation/human-knowledge-identity-development-v1")
REPORT_DIRECTORY = Path("reports/human-knowledge-identity-development-v1")
RUNTIME_SOURCES = (
    "src/product_variant_resolver/human_knowledge_identity.py",
    "src/product_variant_resolver/human_knowledge_identity_artifact.py",
    "src/product_variant_resolver/config.py", "src/product_variant_resolver/service.py",
    "src/product_variant_resolver/schemas.py", "src/product_variant_resolver/api.py", "ui/app.js",
)
ARTIFACT_SCHEMA = "pvr-human-knowledge-identity-retrieval-artifact-v1"


def safe_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("v4 evidence path is outside the workspace")
    return path


def load_identity_protocol(root: Path = ROOT) -> dict[str, Any]:
    directory = root / PROTOCOL_DIRECTORY
    if sha(directory / "protocol.json") != PROTOCOL_SHA256 or sha(directory / "protocol-manifest.json") != MANIFEST_SHA256:
        raise ValueError("v4 protocol/manifest checksum differs from freeze")
    manifest = load_object(directory / "protocol-manifest.json")
    for name, checksum in manifest["input_sha256"].items():
        if sha(safe_path(root, name)) != checksum:
            raise ValueError(f"v4 protocol source is stale: {name}")
    for name, checksum in manifest["file_sha256"].items():
        if sha(safe_path(directory, name)) != checksum:
            raise ValueError(f"v4 protocol artifact is stale: {name}")
    protocol = load_object(directory / "protocol.json")
    if set(protocol["identity_policy"]["noise_tokens"]) != NOISE or protocol["limits"] != asdict(IdentityLimits()):
        raise ValueError("v4 code policy/limits differ from protocol")
    return cast(dict[str, Any], protocol)


def _check_work(row: dict[str, Any]) -> None:
    work = row["work"]
    if set(work) != set(asdict(IdentityRetrievalWork())):
        raise ValueError("v4 work fields differ")
    for field in ("query_forms", "posting_entries_visited", "scored_forms", "exact_candidates", "character_candidates", "dense_union"):
        if type(work[field]) is not int or work[field] < 0:
            raise ValueError("v4 work counters invalid")
    if (work["policy_version"] != "identity-core-policy-v1"
            or work["posting_entries_visited"] > 1_000_000 or work["dense_union"] > 50
            or work["exact_candidates"] > 25 or work["character_candidates"] > 25
            or work["abstention_reason"] not in {None, "query_limit", "noise_only", "window_limit", "posting_limit"}):
        raise ValueError("v4 work contract invalid")
    if work["abstention_reason"] and (row["candidates"] or work["dense_union"]):
        raise ValueError("v4 abstention publishes partial candidates")
    if (not work["abstention_reason"] and work["query_forms"] > 256
            or work["dense_union"] > work["exact_candidates"] + work["character_candidates"]
            or len(row["candidates"]) > work["dense_union"]):
        raise ValueError("v4 work does not cover published candidates")


def _check_candidates(row: dict[str, Any], documents: dict[str, Any], parameters: dict[str, float]) -> None:
    candidates = row["candidates"]
    if len(candidates) > 5 or len({item["knowledge_uuid"] for item in candidates}) != len(candidates):
        raise ValueError("v4 candidate count/uniqueness invalid")
    for rank, item in enumerate(candidates, 1):
        document = documents.get(item["knowledge_uuid"])
        if (document is None or item["knowledge_id"] != document.knowledge_id
                or item["knowledge_type"] != document.knowledge_type
                or item["casting_id"] != getattr(document, "casting_id", None)
                or item["rrf_rank"] != rank):
            raise ValueError("v4 candidate identity/rank invalid")
        for source in ("sparse", "dense", "character"):
            source_rank, score = item[f"{source}_rank"], item[f"{source}_score"]
            maximum = 50 if source == "dense" else 25
            if ((source_rank is None) != (score is None)
                    or source_rank is not None and (type(source_rank) is not int or not 1 <= source_rank <= maximum)
                    or score is not None and (type(score) not in {int, float} or not math.isfinite(score))):
                raise ValueError("v4 source evidence invalid")
            if source_rank is not None and source_rank > row["work"][{
                    "sparse": "exact_candidates", "character": "character_candidates", "dense": "dense_union"}[source]]:
                raise ValueError("v4 source rank exceeds counted candidates")
        if item["dense_rank"] is None or not math.isfinite(item["rrf_score"]):
            raise ValueError("v4 required dense/fused evidence missing")
        if (item["sparse_rank"] is None and item["character_rank"] is None
                or item["character_score"] is not None and not parameters["character_score_floor"] <= item["character_score"] <= 1 + 1e-12
                or item["sparse_score"] is not None and item["sparse_score"] <= 0):
            raise ValueError("v4 candidate lacks valid identity admission")
        fusion = sum(weight / (60 + item[f"{source}_rank"]) for source, weight in
                     (("sparse", 1), ("dense", 1), ("character", parameters["character_rrf_weight"]))
                     if item[f"{source}_rank"] is not None)
        if not math.isclose(fusion, item["rrf_score"], rel_tol=1e-12):
            raise ValueError("v4 fusion does not recompute")
    if candidates != sorted(candidates, key=lambda item: (-item["rrf_score"], item["knowledge_uuid"])):
        raise ValueError("v4 fused order/tie-break differs")
    _check_work(row)


def identity_rejection_reasons(metrics: dict[str, Any], cost: dict[str, Any], scale_hits: dict[str, int]) -> list[str]:
    reasons = rejection_reasons(metrics, cost)
    for group, minimum in (("exact_identity", 60), ("contextual_identity", 20), ("single_edit", 17)):
        if scale_hits[group] < minimum:
            reasons.append(f"synthetic_correctness_failed:{group}")
    return cast(list[str], reasons)


def validate_identity_selection_report(payload: dict[str, Any], root: Path = ROOT) -> dict[str, float] | None:
    protocol = load_identity_protocol(root)
    if (payload["schema_version"] != "pvr-human-knowledge-identity-selection-v1"
            or payload["protocol_sha256"] != PROTOCOL_SHA256
            or payload["protocol_manifest_sha256"] != MANIFEST_SHA256
            or [entry["configuration"] for entry in payload["configurations"]] != grid()
            or set(payload["sources"]) != set(RUNTIME_SOURCES)):
        raise ValueError("v4 selection contract/grid/sources differ")
    for name, checksum in payload["sources"].items():
        if sha(safe_path(root, name)) != checksum:
            raise ValueError("v4 selection runtime source is stale")
    implementation = payload["evaluation_implementation"]
    if (implementation["file"] != "src/product_variant_resolver/human_knowledge_identity_selection.py"
            or sha(safe_path(root, implementation["file"])) != implementation["sha256"]):
        raise ValueError("v4 selection implementation is stale")
    from .human_knowledge_identity_selection import LIMITATIONS, subgroup_cost, work_summary
    runtime = payload["runtime"]
    if (payload["split"] != "dev" or payload["case_count"] != 199 or payload["scale_case_count"] != 120
            or payload["selection_contract"] != protocol["selection_contract"] or payload["limits"] != protocol["limits"]
            or payload["limitations"] != LIMITATIONS
            or any(runtime[key] != value for key, value in {
                "candidate_k": 5, "warmup_count_per_corpus": 3, "process_count": 1,
                "transport": "in_process", "clock": "perf_counter_ns", "percentile_method": "nearest_rank",
                "host_isolated": False, "measured_boundary": "retrieve_with_work_only"}.items())
            or any(not isinstance(runtime[key], str) or not runtime[key] for key in
                ("python", "system", "system_release", "machine", "processor"))):
        raise ValueError("v4 runtime/development disclosure differs")
    pack = load_object(root / "data/evaluation/family-retrieval-development-v1/development-pack.json")
    catalog = load_human_knowledge_catalog(root / "data/human_backed_catalog.json",
                                          root / "data/review_family_knowledge.json",
                                          root / "data/review_family_knowledge_manifest.json")
    real_docs = {str(item.knowledge_uuid): item for item in catalog.documents}
    scale_docs = {str(item.knowledge_uuid): item for item in synthetic_catalog().documents}
    for entry in payload["configurations"]:
        if len(entry["cases"]) != 199 or len(entry["scale_cases"]) != 120:
            raise ValueError("v4 raw cases missing")
        for row, reference in zip(entry["cases"], pack["cases"], strict=True):
            if any(row[field] != reference[field] for field in ("case_id", "case_type", "query_text", "challenge_style", "expected")):
                raise ValueError("v4 raw development case differs")
            _check_candidates(row, real_docs, entry["configuration"])
        hits = {"exact_identity": 0, "contextual_identity": 0, "single_edit": 0}
        for row, reference in zip(entry["scale_cases"], protocol["scale_workload"], strict=True):
            if any(row[field] != value for field, value in reference.items()):
                raise ValueError("v4 scale target/query differs")
            _check_candidates(row, scale_docs, entry["configuration"])
            if reference["correctness_eligible"]:
                hits[reference["group"]] += any(item["knowledge_uuid"] == reference["target_knowledge_uuid"] for item in row["candidates"])
        for label, samples, audit in (("real_142", 199, "real"), ("synthetic_3000", 120, "synthetic")):
            cost = entry["cost"][label]
            metadata = protocol["audit_summary"][audit]
            if (len(cost["samples_ms"]) != samples
                    or any(not math.isfinite(value) or value < 0 for value in cost["samples_ms"])
                    or cost != latency(cost["samples_ms"], cost["index"])
                    or cost["index"]["document_count"] != metadata["document_count"]
                    or cost["index"]["form_count"] != metadata["form_count"]
                    or cost["index"]["posting_entry_count"] != metadata["form_posting_entry_count"]
                    or cost["index"]["posting_count"] != metadata["gram_posting_key_count"]):
                raise ValueError("v4 cost evidence does not recompute")
            rows = entry["cases"] if label == "real_142" else entry["scale_cases"]
            if any(row["work"]["scored_forms"] > metadata["form_count"] for row in rows):
                raise ValueError("v4 work exceeds index form count")
        if (entry["scale_subgroups"] != subgroup_cost(entry["scale_cases"], entry["cost"]["synthetic_3000"]["samples_ms"],
                    entry["cost"]["synthetic_3000"]["index"])
                or entry["work_summary"] != {"real_142": work_summary(entry["cases"]),
                    "synthetic_3000": work_summary(entry["scale_cases"])}):
            raise ValueError("v4 subgroup/work summary does not recompute")
        metrics = summarize(entry["cases"])
        if (metrics != entry["metrics"] or hits != entry["scale_hits"]
                or entry["rejection_reasons"] != identity_rejection_reasons(metrics, entry["cost"], hits)):
            raise ValueError("v4 metrics/rejections do not recompute")
    winner = choose(payload["configurations"])
    if payload["winner"] != winner or payload["verdict"] != ("PASS" if winner else "FAIL"):
        raise ValueError("v4 winner does not recompute")
    return cast(dict[str, float] | None, winner)


def load_human_knowledge_v4_config(artifact_path: Path, *, human_catalog_path: Path,
                                  review_family_path: Path, development_pack_path: Path,
                                  development_manifest_path: Path, dense_dimensions: int,
                                  root: Path = ROOT) -> HumanKnowledgeV4Config:
    protocol = load_identity_protocol(root)
    artifact = load_object(artifact_path)
    if set(artifact) != {"schema_version", "artifact_version", "retriever_version", "status", "configuration",
                         "identity_policy", "limits", "protocol_sha256", "protocol_manifest_sha256",
                         "sources", "selection_evidence", "eligible_for", "excluded_from"}:
        raise ValueError("v4 artifact fields differ")
    if (artifact["schema_version"] != ARTIFACT_SCHEMA or artifact["retriever_version"] != VERSION
            or artifact["status"] != "selected_development_configuration"
            or not re.fullmatch(r"human-knowledge-retrieval-v4-[a-z0-9-]+", artifact["artifact_version"])
            or artifact["identity_policy"] != protocol["identity_policy"] or artifact["limits"] != protocol["limits"]
            or artifact["protocol_sha256"] != PROTOCOL_SHA256 or artifact["protocol_manifest_sha256"] != MANIFEST_SHA256
            or artifact["eligible_for"] != ["human_knowledge_debug_retrieval"]
            or artifact["excluded_from"] != protocol["excluded_from"]):
        raise ValueError("v4 artifact policy/version/boundary differs")
    manifest = load_object(root / PROTOCOL_DIRECTORY / "protocol-manifest.json")
    for path, name in ((human_catalog_path, "data/human_backed_catalog.json"),
                       (review_family_path, "data/review_family_knowledge.json"),
                       (development_pack_path, "data/evaluation/family-retrieval-development-v1/development-pack.json"),
                       (development_manifest_path, "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json")):
        if sha(path) != manifest["input_sha256"][name]:
            raise ValueError("v4 configured corpus/development differs from protocol")
    configuration = artifact["configuration"]
    fixed = {"dense_dimensions": 192, "dense_rrf_weight": 1.0, "sparse_rrf_weight": 1.0,
             "rrf_k": 60, "selection_candidate_limit": 5, "source_candidate_limit": 25}
    if (set(configuration) != set(fixed) | {"character_score_floor", "character_rrf_weight"}
            or any(type(configuration[key]) not in {int, float} or configuration[key] != value for key, value in fixed.items()) or dense_dimensions != 192):
        raise ValueError("v4 artifact fixed parameters differ")
    config = HumanKnowledgeV4Config(configuration["character_score_floor"], configuration["character_rrf_weight"],
                                   artifact["artifact_version"], sha(artifact_path))
    evidence = artifact["selection_evidence"]
    if not isinstance(evidence, dict) or set(evidence) != {"file", "sha256", "configuration_summaries"}:
        raise ValueError("v4 mandatory selection evidence missing")
    evidence_path = safe_path(root, evidence["file"])
    if evidence_path.parent != (root / REPORT_DIRECTORY).resolve() or sha(evidence_path) != evidence["sha256"]:
        raise ValueError("v4 selection evidence path/checksum differs")
    report = load_object(evidence_path)
    winner = validate_identity_selection_report(report, root)
    summaries = [{key: entry[key] for key in ("configuration", "metrics", "scale_hits", "rejection_reasons")}
                 for entry in report["configurations"]]
    if (winner != {"character_score_floor": config.character_score_floor, "character_rrf_weight": config.character_rrf_weight}
            or evidence["configuration_summaries"] != summaries or artifact["sources"] != report["sources"]):
        raise ValueError("v4 selection evidence has no qualified matching winner")
    return config
