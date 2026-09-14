#!/usr/bin/env python3
"""Freeze verified conversation approval/family labels, or validate them without retrieval."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from product_variant_resolver.family_retrieval_final_v2_labels import (  # noqa: E402
    freeze,
    require_committed_benchmark,
    validate,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--check-committed", action="store_true")
    parser.add_argument("--target-confirmation")
    parser.add_argument("--scope-explained")
    parser.add_argument("--proceed-confirmation")
    args = parser.parse_args()
    if args.freeze:
        freeze({"target_confirmation": args.target_confirmation,
            "scope_explained": args.scope_explained, "proceed_confirmation": args.proceed_confirmation})
    elif args.check_committed:
        print("Benchmark commit:", require_committed_benchmark())
    else:
        validate()
    print("Final-v2 owner-approved family benchmark verified; no final retrieval or scoring.")


if __name__ == "__main__":
    main()
