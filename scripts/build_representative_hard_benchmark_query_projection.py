#!/usr/bin/env python3
"""Create or check the private output-blind RHB-T5 query-source projection."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.representative_benchmark_query_projection import (
    ProjectionError,
    materialize_output_blind_projection,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = materialize_output_blind_projection(args.root, check=args.check)
    except (ProjectionError, ValueError) as error:
        raise SystemExit(f"RHB-T5 projection failed: {error}") from error
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
