#!/usr/bin/env python3
"""Record or verify one supported CAR-T5 T5-G1 family-batch review decision."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from product_variant_resolver.canonical_authority_decisions import (
    record_t5_g1_batch_review,
)
from product_variant_resolver.canonical_authority_review import AuthorityContractError

ROOT = Path(__file__).resolve().parents[1]


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timestamp must be ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include a UTC offset")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--batch-ordinal", type=int, default=2)
    parser.add_argument("--outcome", default="reviewed")
    parser.add_argument("--owner-response", required=True)
    parser.add_argument("--authorized-exact-owner-response", required=True)
    parser.add_argument("--reviewed-at", type=_aware_datetime)
    parser.add_argument("--check", action="store_true", help="verify outputs without writing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        status = record_t5_g1_batch_review(
            args.root,
            owner_response_verbatim=args.owner_response,
            authorized_exact_owner_response=args.authorized_exact_owner_response,
            batch_ordinal=args.batch_ordinal,
            expected_outcome=args.outcome,
            reviewed_at=args.reviewed_at,
            check=args.check,
        )
    except AuthorityContractError as error:
        raise SystemExit(f"CAR-T5 T5-G1 decision failed: {error}") from error
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
