"""One frozen v4 development grid; checking/replaying evidence never runs retrieval."""
from __future__ import annotations

import argparse
import os
import platform
import subprocess
import tempfile
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .human_knowledge import HumanKnowledgeCandidate, load_human_knowledge_catalog
from .human_knowledge_identity import (
    MANIFEST_SHA256,
    PROTOCOL_SHA256,
    VERSION,
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
)
from .human_knowledge_identity_artifact import (
    ARTIFACT_SCHEMA,
    REPORT_DIRECTORY,
    ROOT,
    RUNTIME_SOURCES,
    identity_rejection_reasons,
    load_human_knowledge_v4_config,
    load_identity_protocol,
    safe_path,
    validate_identity_selection_report,
)
from .human_knowledge_selection import (
    choose,
    grid,
    latency,
    load_object,
    sha,
    summarize,
    synthetic_catalog,
    write_json,
)
from .retrieval import HashingEmbedding
from .signals import extract_signals

REPORT = ROOT / REPORT_DIRECTORY / "selection.json"
IMPLEMENTATION = "src/product_variant_resolver/human_knowledge_identity_selection.py"
LIMITATIONS = ["already_viewed_identity_derived_development_not_final_accuracy",
    "synthetic_scale_not_real_catalog_growth", "numeric_synthetic_cores_wrapper_edit_not_core_typo",
    "single_process_non_isolated_host_no_concurrent_load", "hashing_v1_not_neural",
    "human_debug_only_canonical_authority_unchanged",
    "timing_excludes_index_startup_signal_extraction_serialization_http_sql_network"]


def serialize(candidate: HumanKnowledgeCandidate) -> dict[str, Any]:
    data = asdict(candidate)
    data.pop("document")
    data.update(knowledge_id=candidate.document.knowledge_id,
        knowledge_uuid=str(candidate.document.knowledge_uuid), knowledge_type=candidate.document.knowledge_type,
        casting_id=getattr(candidate.document, "casting_id", None))
    data["matched_tokens"] = list(data["matched_tokens"])
    return data


def subgroup_cost(rows: list[dict[str, Any]], samples: list[float], metadata: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for group in ("original_dev_20", "exact_identity", "single_edit", "contextual_identity"):
        selected = [(row, sample) for row, sample in zip(rows, samples, strict=True) if row["group"] == group]
        result[group] = {"case_ids": [row["case_id"] for row, _ in selected],
            "latency": latency([sample for _, sample in selected], metadata)}
    return result


def work_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = ("query_forms", "posting_entries_visited", "scored_forms", "exact_candidates", "character_candidates", "dense_union")
    return {"sample_count": len(rows), "abstentions": dict(sorted(Counter(
        row["work"]["abstention_reason"] for row in rows if row["work"]["abstention_reason"]).items())),
        "counters": {field: {"total": sum(row["work"][field] for row in rows),
            "maximum": max(row["work"][field] for row in rows)} for field in fields}}


def runtime_info() -> dict[str, Any]:
    processor = platform.processor()
    if platform.system() == "Darwin":
        result = subprocess.run(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True, check=False)
        processor = result.stdout.strip() or processor or "unavailable"
    return {"python": platform.python_version(), "system": platform.system(),
        "system_release": platform.release(), "machine": platform.machine(), "processor": processor,
        "cpu_count": os.cpu_count(), "candidate_k": 5, "warmup_count_per_corpus": 3,
        "process_count": 1, "transport": "in_process", "clock": "perf_counter_ns",
        "percentile_method": "nearest_rank", "host_isolated": False,
        "measured_boundary": "retrieve_with_work_only"}


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_identity_protocol(root)
    pack = load_object(root / "data/evaluation/family-retrieval-development-v1/development-pack.json")
    catalog = load_human_knowledge_catalog(root / "data/human_backed_catalog.json",
        root / "data/review_family_knowledge.json", root / "data/review_family_knowledge_manifest.json")
    scale = synthetic_catalog()
    # Only query strings enter retrieval. Expected identities are attached after each result is complete.
    signals = [extract_signals(case["query_text"]) for case in pack["cases"]]
    scale_signals = [extract_signals(case["query_text"]) for case in protocol["scale_workload"]]
    sources = {name: sha(root / name) for name in RUNTIME_SOURCES}
    implementation_hash = sha(root / IMPLEMENTATION)
    entries = []
    for parameters in grid():
        print(f"evaluating v4 {parameters}", flush=True)
        config = HumanKnowledgeV4Config(**parameters)
        real = HumanKnowledgeIdentityRetriever(catalog, HashingEmbedding(), config)
        large = HumanKnowledgeIdentityRetriever(scale, HashingEmbedding(), config)
        for service, queries in ((real, signals), (large, scale_signals)):
            for signal in queries[:3]:
                service.retrieve_with_work(signal, 5)
        rows, scale_rows, samples, scale_samples = [], [], [], []
        for case, signal in zip(pack["cases"], signals, strict=True):
            start = time.perf_counter_ns()
            candidates, work = real.retrieve_with_work(signal, 5)
            samples.append((time.perf_counter_ns() - start) / 1e6)
            serialized = [serialize(candidate) for candidate in candidates]
            rows.append({key: case[key] for key in ("case_id", "case_type", "challenge_style", "query_text", "expected")}
                | {"candidates": serialized, "work": work.as_dict()})
        hits = {"exact_identity": 0, "single_edit": 0, "contextual_identity": 0}
        for case, signal in zip(protocol["scale_workload"], scale_signals, strict=True):
            start = time.perf_counter_ns()
            candidates, work = large.retrieve_with_work(signal, 5)
            scale_samples.append((time.perf_counter_ns() - start) / 1e6)
            serialized = [serialize(candidate) for candidate in candidates]
            scale_rows.append(dict(case) | {"candidates": serialized, "work": work.as_dict()})
            if case["correctness_eligible"]:
                hits[case["group"]] += any(item["knowledge_uuid"] == case["target_knowledge_uuid"] for item in serialized)
        metrics = summarize(rows)
        metadata = large.character_index_metadata
        cost = {"real_142": latency(samples, real.character_index_metadata),
            "synthetic_3000": latency(scale_samples, metadata)}
        entry = {"configuration": parameters, "cases": rows, "scale_cases": scale_rows,
            "metrics": metrics, "cost": cost, "scale_hits": hits,
            "scale_subgroups": subgroup_cost(scale_rows, scale_samples, metadata),
            "work_summary": {"real_142": work_summary(rows), "synthetic_3000": work_summary(scale_rows)},
            "rejection_reasons": identity_rejection_reasons(metrics, cost, hits)}
        print(f"  hits={metrics['raw_counts']['positive']['hits_at_5']}/168; "
            f"scale={hits}; p95={cost['real_142']['p95_ms']:.2f}/{cost['synthetic_3000']['p95_ms']:.2f}ms; "
            f"rejections={entry['rejection_reasons']}", flush=True)
        entries.append(entry)
    if sources != {name: sha(root / name) for name in RUNTIME_SOURCES} or implementation_hash != sha(root / IMPLEMENTATION):
        raise ValueError("source changed during selection; do not freeze mixed-code evidence")
    winner = choose(entries)
    return {"schema_version": "pvr-human-knowledge-identity-selection-v1",
        "protocol_sha256": PROTOCOL_SHA256, "protocol_manifest_sha256": MANIFEST_SHA256,
        "sources": sources, "evaluation_implementation": {"file": IMPLEMENTATION, "sha256": implementation_hash},
        "split": "dev", "case_count": 199, "scale_case_count": 120,
        "selection_contract": protocol["selection_contract"], "limits": protocol["limits"],
        "verdict": "PASS" if winner else "FAIL", "winner": winner, "configurations": entries,
        "runtime": runtime_info(), "limitations": LIMITATIONS}


def freeze(selection: Path, output: Path, root: Path = ROOT) -> bool:
    payload = load_object(selection)
    winner = validate_identity_selection_report(payload, root)
    if winner is None:
        return False  # FAIL never creates a directory or touches an existing runtime artifact.
    if selection.resolve().parent != (root / REPORT_DIRECTORY).resolve():
        raise ValueError("selection must be inside the new v4 report directory")
    if output.exists():
        raise ValueError("artifact exists; refuse replacement")
    if not output.resolve().is_relative_to(root.resolve()):
        raise ValueError("artifact must remain inside project")
    protocol = load_identity_protocol(root)
    configuration = dict(winner) | {"dense_dimensions": 192, "dense_rrf_weight": 1.0,
        "sparse_rrf_weight": 1.0, "rrf_k": 60, "selection_candidate_limit": 5, "source_candidate_limit": 25}
    artifact = {"schema_version": ARTIFACT_SCHEMA,
        "artifact_version": f"human-knowledge-retrieval-v4-dev-{sha(selection)[:12]}",
        "retriever_version": VERSION, "status": "selected_development_configuration",
        "configuration": configuration, "identity_policy": protocol["identity_policy"], "limits": protocol["limits"],
        "protocol_sha256": PROTOCOL_SHA256, "protocol_manifest_sha256": MANIFEST_SHA256,
        "sources": payload["sources"], "selection_evidence": {"file": str(selection.resolve().relative_to(root.resolve())),
            "sha256": sha(selection), "configuration_summaries": [{key: entry[key] for key in
                ("configuration", "metrics", "scale_hits", "rejection_reasons")} for entry in payload["configurations"]]},
        "eligible_for": ["human_knowledge_debug_retrieval"], "excluded_from": protocol["excluded_from"]}
    def validate(path: Path) -> None:
        # Validate temporary bytes with the genuine runtime loader before publishing a new artifact.
        load_human_knowledge_v4_config(path, root=root, human_catalog_path=root / "data/human_backed_catalog.json",
            review_family_path=root / "data/review_family_knowledge.json",
            development_pack_path=root / "data/evaluation/family-retrieval-development-v1/development-pack.json",
            development_manifest_path=root / "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json",
            dense_dimensions=192)
    publish_new(output, artifact, validate)
    return True


def publish_new(output: Path, payload: dict[str, Any], validate: Callable[[Path], None] | None = None) -> None:
    """Validate private temporary bytes, then link exclusively; never overwrite concurrent files."""
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        write_json(temporary, payload)
        if validate is not None:
            validate(temporary)
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    output = args.output.resolve()
    safe_path(ROOT, str(output.relative_to(ROOT)))
    if output.parent != REPORT.parent:
        raise ValueError("raw report must remain in v4 development directory")
    if args.run and output.exists():
        raise ValueError("selection already exists; check it, never replace frozen results")
    payload = evaluate() if args.run else load_object(output)
    winner = validate_identity_selection_report(payload)
    if args.run:
        publish_new(output, payload)
    print(f"v4 development {payload['verdict']}; winner={winner}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
