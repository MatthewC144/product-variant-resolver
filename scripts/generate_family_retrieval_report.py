#!/usr/bin/env python3
"""Render the frozen family-retrieval evaluation JSON as deterministic Markdown."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATION = ROOT / "reports/family-retrieval-v1/evaluation.json"
DEFAULT_OUTPUT = ROOT / "reports/family-retrieval-v1/evaluation.md"


def _load_contract() -> Any:
    sys.path.insert(0, str(ROOT / "src"))
    try:
        return importlib.import_module("product_variant_resolver.human_knowledge_evaluation")
    finally:
        sys.path.pop(0)


def _metric(value: float) -> str:
    return str(value) if isinstance(value, int) else f"{value:.4f}"


def _target(operator: str, threshold: float) -> str:
    return f"{operator}{_metric(threshold)}"


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(payload: Mapping[str, Any], contract: Any | None = None) -> str:
    contract = contract or _load_contract()
    contract.validate_evaluation_report(payload)
    benchmark = payload["benchmark"]
    raw = payload["raw_counts"]
    lines = [
        "# Human Knowledge RAG v2 — Frozen Holdout Evaluation",
        "",
        f"> Verdict: **{payload['verdict']}**",
        ">",
        "> This is a one-time, test-only result. It must not be used to tune the same retriever.",
        "",
        "## Evaluation identity",
        "",
        f"- Benchmark: `{benchmark['benchmark_version']}` ({benchmark['case_count']} cases)",
        f"- Benchmark SHA-256: `{benchmark['benchmark_sha256']}`",
        f"- Benchmark manifest SHA-256: `{benchmark['manifest_sha256']}`",
        f"- AI-eval record: [`{payload['ai_eval_record']}`](../../{payload['ai_eval_record']})",
        f"- Retriever: `{payload['system_under_test']['retriever_version']}`",
        (
            f"- Dense representation: `{payload['system_under_test']['dense_provider']}` / "
            f"{payload['system_under_test']['dense_dimensions']} dimensions"
        ),
        (
            f"- Query preprocessor: `{payload['query_preprocessor']['version']}` "
            f"(`{payload['query_preprocessor']['source_sha256']}`)"
        ),
        "",
        "## Precommitted gates",
        "",
        "| Gate | Actual | Required | Result |",
        "|---|---:|---:|:---:|",
    ]
    for name, _, _ in contract.GATE_POLICY:
        gate = payload["gates"][name]
        lines.append(
            f"| `{name}` | {_metric(gate['actual'])} | "
            f"{_target(gate['operator'], gate['threshold'])} | "
            f"{'PASS' if gate['passed'] else 'FAIL'} |"
        )
    positive = raw["positive"]
    family = raw["family_coverage"]
    merge = raw["merge_control"]
    safety = raw["safety_controls"]
    lines.extend(
        [
            "",
            "## Recomputable raw counts",
            "",
            f"- Positive Recall@1: `{positive['hits_at_1']} / {positive['total']}`",
            f"- Positive Recall@5: `{positive['hits_at_5']} / {positive['total']}`",
            (f"- Positive MRR@5: `{positive['reciprocal_rank_sum_at_5']} / {positive['total']}`"),
            f"- Family coverage@5: `{family['covered_at_5']} / {family['total']}`",
            f"- Merge-control Recall@5: `{merge['hits_at_5']} / {merge['total']}`",
        ]
    )
    for style in contract.POSITIVE_STYLES:
        item = raw["positive_styles"][style]
        lines.append(f"- {style} Recall@5: `{item['hits_at_5']} / {item['total']}`")
    lines.extend(
        [
            (
                f"- Forbidden family hits: `{safety['forbidden_family_hit_candidates']}` "
                f"candidates across `{safety['forbidden_family_hit_cases']}` cases"
            ),
            (
                f"- Unrelated non-empty results: `{safety['unrelated_non_empty_results']} / "
                f"{safety['unrelated_total']}`"
            ),
            "",
            "## Error categories",
            "",
            "| Category | Cases |",
            "|---|---:|",
        ]
    )
    for category, count in payload["error_category_counts"].items():
        lines.append(f"| `{category}` | {count} |")

    failed = [item for item in payload["cases"] if item["error_category"] != "none"]
    lines.extend(
        [
            "",
            f"## Case-level errors ({len(failed)})",
            "",
            (
                "The JSON report retains the complete ordered candidates and scores for all 105 cases. "
                "This table is the compact failure view."
            ),
            "",
            "| Case | Type / style | Expected rank | Error | Returned identities (rank order) |",
            "|---|---|---:|---|---|",
        ]
    )
    for item in failed:
        returned = (
            ", ".join(
                f"{candidate['knowledge_type']}:{candidate['knowledge_id']}"
                for candidate in item["candidates"]
            )
            or "—"
        )
        lines.append(
            f"| `{_escape(item['case_id'])}` | "
            f"{_escape(item['case_type'])} / {_escape(item['challenge_style'])} | "
            f"{item['expected_rank'] if item['expected_rank'] is not None else '—'} | "
            f"`{_escape(item['error_category'])}` | {_escape(returned)} |"
        )
    if not failed:
        lines.append("| — | — | — | `none` | — |")

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "This result measures retrieval over 42 accepted casting-family identities, four merge "
                "controls, seven hold controls, and ten unrelated controls. It does not establish release-"
                "variant accuracy, canonical matching accuracy, calibration quality, production readiness, "
                "or PostgreSQL/pgvector scale performance."
            ),
            "",
            "Recorded limitations: "
            + ", ".join(f"`{item}`" for item in payload["limitations"])
            + ".",
            "",
            (
                "A failed gate is preserved as evidence. Any retriever redesign informed by these errors "
                "requires a separately authored v2 holdout before new final-quality claims are made."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        contract = _load_contract()
        payload = contract._load_object(arguments.evaluation, label="evaluation")
        text = render_markdown(payload, contract)
        if arguments.check:
            if arguments.output.read_text(encoding="utf-8") != text:
                raise ValueError("Markdown output differs from reproducible report")
            print("family retrieval Markdown report is reproducible")
        else:
            _atomic_write(arguments.output, text)
            print(f"wrote family retrieval Markdown report; verdict={payload['verdict']}")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"family retrieval report failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
