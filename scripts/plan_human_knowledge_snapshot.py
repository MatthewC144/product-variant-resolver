#!/usr/bin/env python3
"""Publish/check a local-only T49.1 snapshot plan. No network or SQL operations."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge_snapshot import (  # noqa: E402
    check_bundle,
    publish_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/human-knowledge-snapshot-v1")
    args = parser.parse_args()
    try:
        plan = (publish_bundle(args.output, ROOT) if args.run
                else check_bundle(args.output, ROOT))
    except (OSError, ValueError) as error:
        print(f"snapshot plan rejected: {error}", file=sys.stderr)
        return 1
    print(f"PASS local PLAN: 100 provisional + 42 family; snapshot={plan['snapshot_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
