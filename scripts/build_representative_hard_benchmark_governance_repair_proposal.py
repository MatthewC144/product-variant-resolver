#!/usr/bin/env python3
"""Build or check the non-authorizing RHB-T6 governance-repair proposal."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.representative_benchmark_governance_repair import (
    materialize_governance_repair_proposal,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    print(materialize_governance_repair_proposal(arguments.root, check=arguments.check))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
