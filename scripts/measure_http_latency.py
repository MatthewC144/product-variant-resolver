#!/usr/bin/env python3
"""Measure warmed sequential HTTP latency for a running resolver endpoint."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_TITLE = "2022 Chevy Nomad Red #101"


def request_once(base_url: str, title: str, timeout_seconds: float) -> tuple[float, str]:
    request = Request(
        f"{base_url.rstrip('/')}/resolve",
        data=json.dumps({"title": title}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter_ns()
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status: {response.status}")
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    status = payload.get("status")
    if not isinstance(status, str):
        raise RuntimeError("response did not contain a string status")
    return elapsed_ms, status


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--docker-server-version", default="unknown")
    parser.add_argument("--container-python-version", default="unknown")
    args = parser.parse_args()
    if args.warmup < 0 or args.samples < 1:
        parser.error("--warmup must be non-negative and --samples must be positive")

    warmup_statuses = [
        request_once(args.base_url, args.title, args.timeout_seconds)[1]
        for _ in range(args.warmup)
    ]
    observations = [
        request_once(args.base_url, args.title, args.timeout_seconds)
        for _ in range(args.samples)
    ]
    samples_ms = [elapsed for elapsed, _ in observations]
    statuses = [status for _, status in observations]
    if len(set(warmup_statuses + statuses)) != 1:
        raise RuntimeError("resolver status changed during the measurement")

    result = {
        "schema_version": "pvr-http-latency-v1",
        "boundary": "host_to_docker_container_http",
        "endpoint": "POST /resolve",
        "method": {
            "client": f"Python urllib ({platform.python_version()})",
            "concurrency": 1,
            "request_pattern": "sequential",
            "connection_behavior": "one urllib request per sample; no explicit connection pool",
            "warmup_requests": args.warmup,
            "measured_requests": args.samples,
            "clock": "time.perf_counter_ns",
            "percentile_method": "nearest-rank",
            "included": [
                "host loopback HTTP client",
                "Docker Desktop port forwarding",
                "Uvicorn and FastAPI",
                "resolver pipeline",
                "JSON serialization and parsing",
            ],
            "excluded": [
                "container startup",
                "warmup requests",
                "TLS",
                "reverse proxy",
                "remote network",
                "concurrent load",
            ],
        },
        "environment": {
            "host_platform": platform.platform(),
            "host_machine": platform.machine(),
            "docker_server_version": args.docker_server_version,
            "container_python_version": args.container_python_version,
            "base_url": args.base_url,
        },
        "request": {
            "payload": {"title": args.title},
            "observed_status": statuses[0],
        },
        "summary_ms": {
            "minimum": min(samples_ms),
            "median": statistics.median(samples_ms),
            "p95": nearest_rank(samples_ms, 0.95),
            "maximum": max(samples_ms),
            "mean": statistics.fmean(samples_ms),
        },
        "raw_samples_ms": samples_ms,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary_ms"], sort_keys=True))


if __name__ == "__main__":
    main()
