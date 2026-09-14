#!/usr/bin/env python3
"""Publish a genuine qualified v4 winner only; FAIL leaves existing artifacts untouched."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge_identity_selection import REPORT, freeze  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=REPORT)
    parser.add_argument("--output", type=Path, default=ROOT / "config/human-knowledge-retrieval-v4.json")
    args = parser.parse_args()
    if freeze(args.selection, args.output):
        print("froze qualified v4 artifact; commit before unseen final authoring; default remains v2")
    else:
        print("v4 selection FAIL: artifact untouched, v2 active, final authoring/T49 blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
