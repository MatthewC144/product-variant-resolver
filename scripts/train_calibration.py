#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from product_variant_resolver.config import Settings
from product_variant_resolver.training import train_and_select


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit calibration on train and policy on dev")
    parser.add_argument("--output-directory", type=Path, default=Path("artifacts"))
    arguments = parser.parse_args()
    artifact, policy = train_and_select(Settings.from_env(), arguments.output_directory)
    print(f"calibration={artifact}")
    print(f"policy={policy}")


if __name__ == "__main__":
    main()

