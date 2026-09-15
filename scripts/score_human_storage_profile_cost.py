#!/usr/bin/env python3
"""Score one already-published HSP-4 raw timing artifact with frozen budgets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports/human-storage-profile-hsp4-raw-v1.json"
OUTPUT = ROOT / "reports/human-storage-profile-hsp4-evaluation-v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("cannot score an empty duration set")
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def metric(values: list[float], budget: float) -> dict[str, Any]:
    return {
        "samples": len(values),
        "p50_ms": nearest_rank(values, 0.50),
        "p95_ms": nearest_rank(values, 0.95),
        "max_ms": max(values),
        "budget_p95_max_ms": budget,
        "pass": nearest_rank(values, 0.95) <= budget,
    }


def score(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_bytes())
    if (
        raw.get("schema_version") != "pvr-human-storage-hsp4-raw-v1"
        or raw.get("publication_status") != "raw_unscored"
    ):
        raise ValueError("input is not HSP-4 raw unscored evidence")
    if raw["cleanup"]["errors"] or raw["cleanup"]["remaining_owned_resources"]:
        raise ValueError("HSP-4 resources were not completely cleaned")
    result = raw["runner_result"]
    contract = result["measurement_contract"]
    expected_contract = {
        "fresh_startup_samples_per_profile": 5,
        "http_samples_per_profile": 199,
        "core_samples_per_profile": 199,
        "warmups_before_http_per_profile": 3,
        "warmups_before_core_per_profile": 3,
        "startup_p95_max_ms": 5000,
        "integrity_p95_max_ms": 150,
        "http_p95_max_ms": 250,
        "core_p95_max_ms": 25,
        "percentile_method": "nearest_rank",
        "http_transport": "real_Uvicorn_loopback_not_TestClient",
        "concurrency": 1,
        "worker_count": 1,
        "timed_retries_or_budget_reruns": 0,
    }
    if any(contract.get(key) != value for key, value in expected_contract.items()):
        raise ValueError("frozen HSP-4 measurement contract differs")
    if result["timed_retries"] != 0 or result["old_final_105_used"] or result["real_3000_claim"]:
        raise ValueError("cost scope differs")
    metrics: dict[str, Any] = {"startup": {}, "http": {}, "integrity": {}, "core": {}}
    for profile in ("file", "postgres"):
        startup = result["startup_samples"][profile]
        if len(startup) != 5 or any(row["error"] is not None for row in startup):
            raise ValueError("startup samples are incomplete")
        http = [row[profile] for row in result["http_samples"]]
        core = [row[profile] for row in result["core_samples"]]
        if (
            len(http) != 199
            or len(core) != 199
            or any(row["status"] != 200 or row["error"] is not None for row in http)
            or any(row["status"] != "ok" or row["error"] is not None for row in core)
        ):
            raise ValueError("HTTP/core samples include an error or wrong count")
        http_warmups = result["http_warmups"][profile]
        core_warmups = result["core_warmups"][profile]
        if (
            len(http_warmups) != 3
            or len(core_warmups) != 3
            or any(row["status"] != 200 or row["error"] is not None for row in http_warmups)
            or any(row["status"] != "ok" or row["error"] is not None for row in core_warmups)
        ):
            raise ValueError("warmup count differs")
        metrics["startup"][profile] = metric(
            [row["duration_ms"] for row in startup], contract["startup_p95_max_ms"]
        )
        metrics["http"][profile] = metric(
            [row["duration_ms"] for row in http], contract["http_p95_max_ms"]
        )
        metrics["integrity"][profile] = metric(
            [row["integrity_ms"] for row in http], contract["integrity_p95_max_ms"]
        )
        metrics["core"][profile] = metric(
            [row["duration_ms"] for row in core], contract["core_p95_max_ms"]
        )
    verdict = (
        "PASS"
        if all(item["pass"] for group in metrics.values() for item in group.values())
        else "FAIL"
    )
    return {
        "schema_version": "pvr-human-storage-hsp4-evaluation-v1",
        "verdict": verdict,
        "raw_file": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "raw_sha256": sha(path),
        "raw_published_before_scoring": True,
        "percentile_method": "nearest_rank",
        "metrics": metrics,
        "scope": "local arm64,142 documents,concurrency1; not production,real3k,throughput,durability or SLA",
    }


def publish(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink() or path.parent != ROOT / "reports":
        raise ValueError("HSP-4 evaluation must be a new exclusive reports file")
    descriptor, name = tempfile.mkstemp(prefix=".hsp4-score-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
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
    print(f"HSP-4 cost: {result['verdict']}; evidence={args.output}")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
