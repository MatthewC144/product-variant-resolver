#!/usr/bin/env python3
"""Build/check the output-blind CAR-T4 local owner review packet."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.canonical_authority_packet import publish_workspace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--local-output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(
        publish_workspace(
            args.root,
            output_dir=args.local_output_dir,
            check=args.check,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
