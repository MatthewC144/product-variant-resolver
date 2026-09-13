#!/usr/bin/env python3
"""Render the complete, checksum-validated development grid as a compact report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge_selection import (  # noqa: E402
    REPORT,
    atomic_write,
    load_object,
    validate_report,
)


def render(payload: dict) -> str:
    validate_report(payload)
    lines = ["# Human Knowledge v3 — Development Selection", "",
             f"Verdict: {payload['verdict']}; winner: {payload['winner']}", "",
             "199 identity-derived, intentionally leaky development cases; not final accuracy.",
             "All 21 precommitted configurations were executed. Raw JSON retains every ordered",
             "Top-5 candidate, score, expected identity, latency sample, and source checksum.", "",
             "| Floor | Char weight | Recall@1 | Recall@5 | MRR@5 | Unrelated nonempty | Merge hits | 142 p50/p95 ms | 3000 p95 ms | Rejection reasons |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for entry in payload["configurations"]:
        p, m, c = entry["configuration"], entry["metrics"], entry["cost"]
        raw = m["raw_counts"]
        lines.append(f"| {p['character_score_floor']} | {p['character_rrf_weight']} | "
                     f"{m['recall_at_1']:.4f} | {m['recall_at_5']:.4f} | {m['mrr_at_5']:.4f} | "
                     f"{raw['unrelated_nonempty']}/20 | {raw['merge_hits_at_5']}/4 | "
                     f"{c['real_142']['p50_ms']:.2f}/{c['real_142']['p95_ms']:.2f} | "
                     f"{c['synthetic_3000']['p95_ms']:.2f} | "
                     f"{', '.join(entry['rejection_reasons']) or 'none'} |")
    lines.extend(["", "## Measurement boundary", "",
                  f"Runtime: `{payload['runtime']}`", "",
                  "Each configuration: three warmed queries, all 199 development queries on 142",
                  "typed documents, first 20 case-ID-ordered development queries on 3000 synthetic",
                  "family documents. Nearest-rank percentiles; K=5; one process; index-build time",
                  "excluded. Synthetic common-word identities deliberately stress shared postings.",
                  "No PostgreSQL, network, concurrent load, independent final accuracy or production claim.", "",
                  "FAIL preserves v2. No grid expansion, gate relaxation, runtime artifact, new final",
                  "holdout or database promotion is authorized by this report.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=REPORT)
    parser.add_argument("--output", type=Path, default=REPORT.with_suffix(".md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render(load_object(args.selection))
    if args.check:
        if args.output.read_text(encoding="utf-8") != text:
            raise ValueError("Markdown differs from raw report")
    else:
        atomic_write(args.output, text)
    print("development Markdown report validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
