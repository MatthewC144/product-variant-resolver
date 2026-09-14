#!/usr/bin/env python3
"""Render/check v4's complete raw evidence; never rerun or replace frozen results."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge_identity_artifact import (
    validate_identity_selection_report,  # noqa: E402
)
from product_variant_resolver.human_knowledge_identity_selection import REPORT  # noqa: E402
from product_variant_resolver.human_knowledge_selection import (  # noqa: E402
    atomic_write,
    load_object,
)


def render(payload: dict) -> str:
    validate_identity_selection_report(payload)
    lines = ["# Human Knowledge v4 — Identity-Bounded Development Selection", "",
        f"Verdict: {payload['verdict']}; winner: {payload['winner']}", "",
        "All 21 frozen configurations; 199 already-viewed identity-derived dev cases per setting.",
        "4,179 real outputs plus 2,520 synthetic outputs retain candidates, work and raw latency.",
        "This is development evidence, not final accuracy or real 3,000-row catalog ingestion.", "",
        "| Floor | Char weight | Positive R@1 | Positive R@5 | MRR@5 | Unrelated nonempty | Merge | Forbidden | Real p50/p95 ms | Scale p95 ms | Exact/edit/context hits | Rejections |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for entry in payload["configurations"]:
        p, m, c, h = entry["configuration"], entry["metrics"], entry["cost"], entry["scale_hits"]
        raw = m["raw_counts"]
        lines.append(f"| {p['character_score_floor']} | {p['character_rrf_weight']} | {m['recall_at_1']:.4f} | "
            f"{raw['positive']['hits_at_5']}/168 | {m['mrr_at_5']:.4f} | {raw['unrelated_nonempty']}/20 | "
            f"{raw['merge_hits_at_5']}/4 | {raw['forbidden_family_candidates']} | "
            f"{c['real_142']['p50_ms']:.2f}/{c['real_142']['p95_ms']:.2f} | {c['synthetic_3000']['p95_ms']:.2f} | "
            f"{h['exact_identity']}/60; {h['single_edit']}/20; {h['contextual_identity']}/20 | "
            f"{', '.join(entry['rejection_reasons']) or 'none'} |")
    lines += ["", "## Positive styles, work and subgroup cost", "",
        "| Floor / weight | Edit | Spacing | Abbreviation | Context | Scale original-20/exact/edit/context p95 ms | Real/scale max visits | Real/scale abstentions |",
        "|---|---:|---:|---:|---:|---|---|---|"]
    for entry in payload["configurations"]:
        p, styles, sub, work = entry["configuration"], entry["metrics"]["raw_counts"]["positive_styles"], entry["scale_subgroups"], entry["work_summary"]
        hits = [styles[key]["hits_at_5"] for key in ("single_edit", "spacing_punctuation", "abbreviation_numeric", "contextual_noise")]
        times = "/".join(f"{sub[key]['latency']['p95_ms']:.2f}" for key in ("original_dev_20", "exact_identity", "single_edit", "contextual_identity"))
        lines.append(f"| {p['character_score_floor']} / {p['character_rrf_weight']} | "
            + " | ".join(f"{hit}/42" for hit in hits) + f" | {times} | "
            f"{work['real_142']['counters']['posting_entries_visited']['maximum']}/"
            f"{work['synthetic_3000']['counters']['posting_entries_visited']['maximum']} | "
            f"{work['real_142']['abstentions']}/{work['synthetic_3000']['abstentions']} |")
    lines += ["", "## Measurement and interpretation", "",
        "```json", json.dumps(payload["runtime"], ensure_ascii=False, sort_keys=True, indent=2), "```", "",
        "Three warm-ups per corpus/configuration; K=5; nearest-rank percentiles. All 199 real and",
        "120 scale raw samples determine cost gates. Original-20, 60 exact, 20 edited and 20 contextual",
        "scale groups are additionally shown separately; subgroup figures do not replace aggregate gates.",
        "Complete retrieve_with_work timing only: index/startup, extraction, serialization, HTTP, SQL,",
        "network and concurrent load excluded. Non-isolated single-machine in-process measurements.",
        "Synthetic casting cores retain digits; Scale→Scxle edits a removed wrapper, not retained",
        "identity. Its hit gate prevents empty-only timing claims, but is not genuine core-typo proof.", "",
        "All quality/safety/cost gates apply together. No closest-winner or threshold/cap/policy tuning.",
        "FAIL preserves v2 and blocks final authoring/T49. PASS only permits a committed experimental",
        "artifact before separately owner-reviewed unseen final questions; no default activation.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=REPORT)
    parser.add_argument("--output", type=Path, default=REPORT.with_suffix(".md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.output.resolve().parent != REPORT.parent:
        raise ValueError("Markdown must stay in v4 development directory")
    text = render(load_object(args.selection))
    if args.check:
        if args.output.read_text(encoding="utf-8") != text:
            raise ValueError("Markdown differs from raw report")
    else:
        if args.output.exists():
            raise ValueError("Markdown exists; check it, never replace frozen results")
        atomic_write(args.output, text)
    print("v4 development Markdown validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
