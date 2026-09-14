#!/usr/bin/env python3
"""Validate final-v2 JSON/Markdown from stored raw outputs; never rerun final retrieval."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from product_variant_resolver.family_retrieval_final_v2_evaluation import main  # noqa: E402

if __name__ == "__main__":
    main()
