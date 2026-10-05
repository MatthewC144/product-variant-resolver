#!/usr/bin/env python3
"""Print the read-only RHB-T6 label-authoring readiness report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_variant_resolver.representative_benchmark_label_readiness import (
    LabelReadinessError,
    build_rhb_t6_label_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    try:
        readiness = build_rhb_t6_label_readiness(arguments.root)
    except (LabelReadinessError, ValueError) as error:
        parser.exit(1, f"RHB-T6 readiness failed: {error}\n")
    print(
        json.dumps(readiness.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
