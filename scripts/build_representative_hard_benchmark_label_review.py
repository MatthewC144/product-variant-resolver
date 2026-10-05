#!/usr/bin/env python3
"""Build or check the owner-authorized local RHB-T6 review workspace."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.representative_benchmark_label_review import (
    materialize_label_review,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    print(materialize_label_review(arguments.root, check=arguments.check))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
