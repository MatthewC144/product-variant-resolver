#!/usr/bin/env python3
"""Build or check the private RHB-T5 query pack and safe public manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.representative_benchmark_query_authoring import (
    materialize_query_pack,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    print(materialize_query_pack(arguments.root, check=arguments.check))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
