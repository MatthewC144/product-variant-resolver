#!/usr/bin/env python3
"""Validate RHB-T5 query-authoring readiness without authoring queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_variant_resolver.representative_benchmark_query_readiness import (
    QueryReadinessError,
    build_rhb_t5_query_readiness,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        readiness = build_rhb_t5_query_readiness(args.root)
    except (QueryReadinessError, ValueError) as error:
        raise SystemExit(f"RHB-T5 readiness failed: {error}") from error
    print(json.dumps(readiness.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
