#!/usr/bin/env python3
"""Apply or verify the owner-authorized CAR-T4 catalog proposal batch."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from product_variant_resolver.canonical_authority_review import AuthorityContractError
from product_variant_resolver.canonical_catalog_application import (
    apply_catalog_application,
    check_catalog_application,
)


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--authorized-at must be an aware ISO-8601 timestamp")
    return parsed.astimezone(UTC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply/check the complete CAR catalog-proposal batch"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--owner-response")
    parser.add_argument("--authorized-exact-owner-response")
    parser.add_argument("--expected-owner-response")
    parser.add_argument("--authorized-at", type=_timestamp)
    args = parser.parse_args(argv)
    try:
        if args.check:
            if any(
                value is not None
                for value in (
                    args.owner_response,
                    args.authorized_exact_owner_response,
                    args.authorized_at,
                )
            ):
                raise AuthorityContractError("--check cannot use application write arguments")
            if args.expected_owner_response is None:
                raise AuthorityContractError(
                    "precommit --check requires --expected-owner-response from the external Gate"
                )
            manifest = check_catalog_application(
                args.root, expected_owner_response=args.expected_owner_response
            )
            status = "valid"
        else:
            if args.expected_owner_response is not None:
                raise AuthorityContractError("--expected-owner-response is only valid with --check")
            if args.owner_response is None or args.authorized_exact_owner_response is None:
                parser.error(
                    "application requires --owner-response and --authorized-exact-owner-response"
                )
            status, manifest = apply_catalog_application(
                args.root,
                owner_response_verbatim=args.owner_response,
                authorized_exact_owner_response=args.authorized_exact_owner_response,
                authorized_at=args.authorized_at,
            )
        print(
            json.dumps(
                {
                    "status": status,
                    "catalog_product_count": manifest.catalog_product_count,
                    "catalog_record_applied_count": manifest.catalog_record_applied_count,
                    "exact_authority_count": manifest.exact_authority_count,
                    "rhb_t5_authorized": manifest.rhb_t5_authorized,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (AuthorityContractError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
