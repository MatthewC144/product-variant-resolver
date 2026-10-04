#!/usr/bin/env python3
"""Check CAR-T5F readiness or freeze the owner-authorized authority bundle."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from product_variant_resolver.canonical_authority_freeze import (
    build_car_t5f_readiness,
    freeze_authority_bundle,
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
    parser.add_argument(
        "--readiness",
        action="store_true",
        help="validate current inputs without writing authorization or bundle artifacts",
    )
    parser.add_argument("--owner-response")
    parser.add_argument("--authorized-car-t5f-owner-response")
    parser.add_argument("--authorized-at", type=_aware_datetime)
    parser.add_argument(
        "--check", action="store_true", help="verify frozen outputs without writing"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.readiness:
            if args.check or args.owner_response or args.authorized_car_t5f_owner_response:
                raise AuthorityContractError(
                    "readiness is read-only and cannot be combined with freeze arguments"
                )
            report = build_car_t5f_readiness(args.root)
            print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
            return 0
        if not args.owner_response or not args.authorized_car_t5f_owner_response:
            raise AuthorityContractError(
                "freezing requires owner-response and authorized-car-t5f-owner-response"
            )
        status = freeze_authority_bundle(
            args.root,
            owner_response_verbatim=args.owner_response,
            authorized_car_t5f_owner_response=args.authorized_car_t5f_owner_response,
            authorized_at=args.authorized_at,
            check=args.check,
        )
    except AuthorityContractError as error:
        raise SystemExit(f"CAR-T5F failed: {error}") from error
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
