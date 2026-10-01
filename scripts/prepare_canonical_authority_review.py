#!/usr/bin/env python3
"""Prepare or verify the local CAR-T5P output-blind owner review packet."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.canonical_authority_preparation import prepare_authority_review
from product_variant_resolver.canonical_authority_review import AuthorityContractError

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="verify outputs without writing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        status = prepare_authority_review(args.root, check=args.check)
    except AuthorityContractError as error:
        raise SystemExit(f"CAR-T5P preparation failed: {error}") from error
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
