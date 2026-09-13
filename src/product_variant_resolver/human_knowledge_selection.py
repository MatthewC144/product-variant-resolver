"""Development-only, fixed-grid evaluation. Never reads the v1 benchmark or report."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import tempfile
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from .human_knowledge import (
    HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
    HUMAN_KNOWLEDGE_V3_FLOORS,
    HUMAN_KNOWLEDGE_V3_WEIGHTS,
    HumanKnowledgeCatalog,
    HumanKnowledgeDocument,
    HumanKnowledgeRetriever,
    HumanKnowledgeV3Config,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
)
from .retrieval import HashingEmbedding
from .signals import extract_signals

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "data/evaluation/family-retrieval-development-v1"
REPORT = ROOT / "reports/family-retrieval-development-v1/selection.json"
STYLES = ("single_edit", "spacing_punctuation", "abbreviation_numeric", "contextual_noise")
PACK_SHA = "23589b23567220dbba0de959ec5223cf60365b1222320f3a372f1b156244dbe9"
MANIFEST_SHA = "3b62969a33e92c6d0d869d8271649417fa177c77b99f1568d1018ca31397f920"
SOURCE_PATHS = (
    "data/evaluation/family-retrieval-development-v1/development-pack.json",
    "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json",
    "data/human_backed_catalog.json", "data/review_family_knowledge.json",
    "src/product_variant_resolver/human_knowledge.py",
    "src/product_variant_resolver/human_knowledge_selection.py",
    "src/product_variant_resolver/signals.py", "src/product_variant_resolver/retrieval.py",
    "src/product_variant_resolver/identity.py",
)
COUNTS = {"positive_family": 168, "merge_control": 4, "hold_control": 7,
          "unrelated_control": 20}
# Fixed measurement protocol: every configuration, three warm-ups, all 199 dev queries,
# and the first 20 case-ID-ordered dev queries on a deterministic synthetic scale index.
WARMUPS = 3
SCALE_SAMPLES = 20


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                 indent=2, allow_nan=False) + "\n")


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_development(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = root / DEV.relative_to(ROOT)
    pack_path = directory / "development-pack.json"
    manifest_path = directory / "development-pack-manifest.json"
    pack, manifest = load_object(pack_path), load_object(manifest_path)
    if (sha(pack_path) != PACK_SHA or manifest["development_sha256"] != PACK_SHA
            or sha(manifest_path) != MANIFEST_SHA):
        raise ValueError("development pack differs from pre-output freeze")
    if (pack["status"] != "frozen_development_only" or pack["split"] != "dev"
            or manifest["status"] != "frozen_before_configuration_execution"
            or pack["retrieval_executed"] is not False
            or manifest["configuration_output_viewed"] is not False
            or pack["authorship_policy"]["final_accuracy_eligible"] is not False):
        raise ValueError("development boundary differs from contract")
    if Counter(case["case_type"] for case in pack["cases"]) != COUNTS:
        raise ValueError("development counts differ")
    contract = pack["selection_contract"]
    if (contract != manifest["selection_contract"]
            or contract["character_score_floors"] != sorted(HUMAN_KNOWLEDGE_V3_FLOORS)
            or contract["character_rrf_weights"] != sorted(HUMAN_KNOWLEDGE_V3_WEIGHTS)
            or contract["configuration_count"] != 21 or contract["candidate_limit"] != 5):
        raise ValueError("selection grid differs from precommitted contract")
    # Historical query-pack references were checked at authoring time. Selection does not
    # open any v1 file, including references carrying source_integrity use tags.
    for reference in manifest["inputs"]:
        if "family-retrieval-v1" in reference["file"]:
            continue
        if sha(root / reference["file"]) != reference["sha256"]:
            raise ValueError(f"stale development source: {reference['file']}")
    return pack, manifest


def grid() -> list[dict[str, float]]:
    return [{"character_score_floor": floor, "character_rrf_weight": weight}
            for floor in sorted(HUMAN_KNOWLEDGE_V3_FLOORS)
            for weight in sorted(HUMAN_KNOWLEDGE_V3_WEIGHTS)]


def config(parameters: dict[str, float]) -> HumanKnowledgeV3Config:
    return HumanKnowledgeV3Config("human-knowledge-retrieval-v3-development", "experimental",
                                  parameters["character_score_floor"],
                                  parameters["character_rrf_weight"], 1.0, 1.0, 192, 60, 25,
                                  HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION)


def synthetic_catalog() -> HumanKnowledgeCatalog:
    documents: list[HumanKnowledgeDocument] = [ReviewFamilyKnowledgeDocument(
        uuid5(NAMESPACE_URL, f"pvr:synthetic-scale:{index}"), f"scale-{index:04d}",
        "Synthetic", f"Scale vehicle model {index:04d}",
        (f"Synthetic casting {index:04d}",), (), "synthetic_scale_only")
        for index in range(3000)]
    return HumanKnowledgeCatalog("synthetic-scale-v1", "synthetic-scale-v1", documents)


def latency(samples: list[float], metadata: dict[str, Any] | None) -> dict[str, Any]:
    ordered = sorted(samples)
    return {"samples_ms": samples, "sample_count": len(samples), "warmup_count": WARMUPS,
            "p50_ms": ordered[math.ceil(len(samples) * 0.5) - 1],
            "p95_ms": ordered[math.ceil(len(samples) * 0.95) - 1],
            "percentile_method": "nearest_rank", "index": metadata}


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    positive = Counter(total=0, hits_at_1=0, hits_at_5=0)
    styles = {style: Counter(total=0, hits_at_5=0) for style in STYLES}
    reciprocal = []
    merge_total = merge_hits = forbidden = unrelated = 0
    for case in cases:
        candidates = case["candidates"]
        expected = case["expected"]
        kind = case["case_type"]
        if kind == "positive_family":
            rank = next((index for index, item in enumerate(candidates, 1)
                         if item["knowledge_type"] == "review_family"
                         and item["knowledge_id"] == expected["review_family_id"]), None)
            positive["total"] += 1
            positive["hits_at_1"] += rank == 1
            positive["hits_at_5"] += rank is not None
            styles[case["challenge_style"]]["total"] += 1
            styles[case["challenge_style"]]["hits_at_5"] += rank is not None
            reciprocal.append(1 / rank if rank else 0.0)
        if kind == "merge_control":
            merge_total += 1
            merge_hits += any(item["knowledge_type"] == "provisional_variant"
                              and item["casting_id"] == expected["casting_id"]
                              for item in candidates)
        if kind in {"hold_control", "merge_control"}:
            forbidden += sum(item["knowledge_type"] == "review_family"
                             and item["knowledge_id"] == expected["forbidden_review_family_id"]
                             for item in candidates)
        if kind == "unrelated_control":
            unrelated += bool(candidates)
    raw: dict[str, Any] = {"positive": dict(positive), "positive_styles": {
        style: dict(counts) for style, counts in styles.items()},
        "reciprocal_rank_sum": math.fsum(reciprocal), "merge_total": merge_total,
        "merge_hits_at_5": merge_hits, "forbidden_family_candidates": forbidden,
        "unrelated_nonempty": unrelated}
    return {"raw_counts": raw, "recall_at_1": positive["hits_at_1"] / positive["total"],
            "recall_at_5": positive["hits_at_5"] / positive["total"],
            "mrr_at_5": raw["reciprocal_rank_sum"] / positive["total"]}


def rejection_reasons(metrics: dict[str, Any], cost: dict[str, Any]) -> list[str]:
    raw = metrics["raw_counts"]
    reasons = []
    if raw["forbidden_family_candidates"]:
        reasons.append("forbidden_family_hit")
    if raw["unrelated_nonempty"]:
        reasons.append("unrelated_nonempty")
    if raw["merge_hits_at_5"] != raw["merge_total"]:
        reasons.append("merge_recall_below_1")
    if metrics["recall_at_5"] < 0.90:
        reasons.append("positive_recall_below_0.90")
    for style in STYLES:
        item = raw["positive_styles"][style]
        if item["hits_at_5"] / item["total"] < 0.85:
            reasons.append(f"style_recall_below_0.85:{style}")
    if cost["real_142"]["p50_ms"] > 25 or cost["real_142"]["p95_ms"] > 25:
        reasons.append("real_142_latency_above_25ms")
    if cost["synthetic_3000"]["p95_ms"] > 150:
        reasons.append("synthetic_3000_latency_above_150ms")
    return reasons


def choose(entries: list[dict[str, Any]]) -> dict[str, float] | None:
    survivors = [entry for entry in entries if not entry["rejection_reasons"]]
    if not survivors:
        return None
    winner = max(survivors, key=lambda item: (
        item["metrics"]["mrr_at_5"], item["metrics"]["recall_at_1"],
        item["configuration"]["character_score_floor"],
        -item["configuration"]["character_rrf_weight"]))
    return cast(dict[str, float], winner["configuration"])


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    pack, manifest = load_development(root)
    catalog = load_human_knowledge_catalog(root / "data/human_backed_catalog.json",
                                          root / "data/review_family_knowledge.json",
                                          root / "data/review_family_knowledge_manifest.json")
    scale = synthetic_catalog()
    entries = []
    for parameters in grid():
        print(f"evaluating {parameters}", flush=True)
        real = HumanKnowledgeRetriever(catalog, HashingEmbedding(), config(parameters))
        large = HumanKnowledgeRetriever(scale, HashingEmbedding(), config(parameters))
        signals = [extract_signals(case["query_text"]) for case in pack["cases"]]
        for retriever in (real, large):
            for signal in signals[:WARMUPS]:
                retriever.retrieve(signal, 5)
        rows, samples, scale_times = [], [], []
        for case, signal in zip(pack["cases"], signals, strict=True):
            start = time.perf_counter_ns()
            candidates = real.retrieve(signal, 5)
            samples.append((time.perf_counter_ns() - start) / 1e6)
            # Expected labels are consulted only after the candidate list is finalized.
            serialized = []
            for candidate in candidates:
                data = asdict(candidate)
                data.pop("document")
                data.update(knowledge_id=candidate.document.knowledge_id,
                            knowledge_uuid=str(candidate.document.knowledge_uuid),
                            knowledge_type=candidate.document.knowledge_type,
                            casting_id=getattr(candidate.document, "casting_id", None))
                data["matched_tokens"] = list(data["matched_tokens"])
                serialized.append(data)
            rows.append({"case_id": case["case_id"], "case_type": case["case_type"],
                         "challenge_style": case["challenge_style"],
                         "query_text": case["query_text"], "expected": case["expected"],
                         "candidates": serialized})
        for signal in signals[:SCALE_SAMPLES]:
            start = time.perf_counter_ns()
            large.retrieve(signal, 5)
            scale_times.append((time.perf_counter_ns() - start) / 1e6)
        metrics = summarize(rows)
        cost = {"real_142": latency(samples, real.character_index_metadata),
                "synthetic_3000": latency(scale_times, large.character_index_metadata)}
        entries.append({"configuration": parameters, "cases": rows, "metrics": metrics,
                        "cost": cost, "rejection_reasons": rejection_reasons(metrics, cost)})
    winner = choose(entries)
    return {"schema_version": "pvr-human-knowledge-development-selection-v1",
            "development_version": pack["development_version"], "split": "dev",
            "case_count": 199, "selection_contract": manifest["selection_contract"],
            "sources": {path: sha(root / path) for path in SOURCE_PATHS},
            "verdict": "PASS" if winner else "FAIL", "winner": winner,
            "configurations": entries, "runtime": {
                "python": platform.python_version(), "system": platform.system(),
                "machine": platform.machine(), "processor": platform.processor(),
                "cpu_count": os.cpu_count(), "candidate_k": 5, "process_count": 1,
                "transport": "in_process", "clock": "perf_counter_ns",
                "scale_query_case_ids": [case["case_id"] for case in pack["cases"][:SCALE_SAMPLES]],
                "synthetic_construction": "3000 unique Scale vehicle model NNNN with Synthetic casting aliases"},
            "limitations": ["identity_derived_leaky_development_only", "not_final_accuracy",
                            "synthetic_scale_not_real_catalog_growth", "no_database_or_network",
                            "single_process_no_concurrency", "warm_queries_exclude_index_build",
                            "hashing_v1_not_neural", "human_debug_only_no_canonical_authority"]}


def validate_report(payload: dict[str, Any], root: Path = ROOT) -> None:
    pack, manifest = load_development(root)
    if (payload["schema_version"] != "pvr-human-knowledge-development-selection-v1"
            or payload["selection_contract"] != manifest["selection_contract"]
            or payload["split"] != "dev" or payload["case_count"] != 199
            or [entry["configuration"] for entry in payload["configurations"]] != grid()):
        raise ValueError("report grid or development contract differs")
    if set(payload["sources"]) != set(SOURCE_PATHS):
        raise ValueError("selection source references incomplete")
    catalog = load_human_knowledge_catalog(root / "data/human_backed_catalog.json",
                                          root / "data/review_family_knowledge.json",
                                          root / "data/review_family_knowledge_manifest.json")
    documents = {str(item.knowledge_uuid): item for item in catalog.documents}
    for path, checksum in payload["sources"].items():
        if "family-retrieval-v1" in path or sha(root / path) != checksum:
            raise ValueError("stale or prohibited selection source")
    for entry in payload["configurations"]:
        rows = entry["cases"]
        if len(rows) != 199:
            raise ValueError("missing raw cases")
        for row, case in zip(rows, pack["cases"], strict=True):
            for field in ("case_id", "case_type", "challenge_style", "query_text", "expected"):
                if row[field] != case[field]:
                    raise ValueError("report case differs from frozen development")
            candidates = row["candidates"]
            if len(candidates) > 5 or len({item["knowledge_uuid"] for item in candidates}) != len(candidates):
                raise ValueError("invalid candidate count/uniqueness")
            for rank, item in enumerate(candidates, 1):
                if item["rrf_rank"] != rank:
                    raise ValueError("invalid raw ordering")
                document = documents.get(item["knowledge_uuid"])
                if (document is None or item["knowledge_id"] != document.knowledge_id
                        or item["knowledge_type"] != document.knowledge_type
                        or item["casting_id"] != getattr(document, "casting_id", None)):
                    raise ValueError("raw candidate identity not in frozen corpus")
                for source in ("sparse", "dense", "character"):
                    source_rank, score = item[f"{source}_rank"], item[f"{source}_score"]
                    if ((source_rank is None) != (score is None)
                            or (source_rank is not None and (type(source_rank) is not int
                                                           or not 1 <= source_rank <= 50))):
                        raise ValueError("invalid raw source rank")
                weight = entry["configuration"]["character_rrf_weight"]
                fusion = sum(source_weight / (60 + item[f"{source}_rank"])
                             for source, source_weight in (("sparse", 1), ("dense", 1), ("character", weight))
                             if item[f"{source}_rank"] is not None)
                if not math.isclose(item["rrf_score"], fusion, rel_tol=1e-12):
                    raise ValueError("raw fusion score does not recompute")
                for field in ("sparse_score", "dense_score", "character_score", "rrf_score"):
                    if item[field] is not None and not math.isfinite(item[field]):
                        raise ValueError("nonfinite raw score")
        for label, count, samples in (("real_142", 142, 199), ("synthetic_3000", 3000, SCALE_SAMPLES)):
            cost = entry["cost"][label]
            if (cost["index"]["document_count"] != count or len(cost["samples_ms"]) != samples
                    or any(not math.isfinite(value) or value < 0 for value in cost["samples_ms"])
                    or cost != latency(cost["samples_ms"], cost["index"])):
                raise ValueError("cost disclosure does not recompute")
        metrics = summarize(rows)
        if metrics != entry["metrics"] or entry["rejection_reasons"] != rejection_reasons(metrics, entry["cost"]):
            raise ValueError("metrics or rejection reasons do not recompute")
    winner = choose(payload["configurations"])
    if payload["winner"] != winner or payload["verdict"] != ("PASS" if winner else "FAIL"):
        raise ValueError("selection outcome does not recompute")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = load_object(args.output)
    else:
        payload = evaluate()
    validate_report(payload)
    if not args.check:
        write_json(args.output, payload)
    print(f"development selection {payload['verdict']}; winner={payload['winner']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
