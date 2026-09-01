from __future__ import annotations

import json
import math
import statistics
import time
from html import escape
from pathlib import Path
from typing import Any

from .config import Settings
from .evaluation import EvaluationReport, evaluate, load_benchmark, percentile, safe_divide


REPORT_SCHEMA_VERSION = "pvr-evaluation-report-v2"
NON_PRODUCTION_NOTICE = (
    "This report covers exactly 21 synthetic fixture test cases. It does not establish "
    "production accuracy, marketplace coverage, or production readiness."
)
METRIC_NAMES = (
    "recall_at_10", "recall_at_25", "recall_at_50", "top1_accuracy", "mrr_at_10",
    "hard_negative_accuracy", "precision", "coverage", "false_match_rate",
    "abstention_rate",
)


def measure_warmed_http_latency(
    settings: Settings, *, warmup_requests: int = 5,
) -> dict[str, Any]:
    """Measure the in-process HTTP/ASGI boundary after deterministic warm-up.

    TestClient exercises middleware, validation, endpoint dispatch, response-model
    serialization, and headers. It deliberately does not claim TCP, container, proxy,
    database, or concurrent-load costs.
    """

    from fastapi.testclient import TestClient

    from .api import create_app

    benchmark = load_benchmark(settings.benchmark_path)
    cases = [case for case in benchmark["cases"] if case["split"] == "test"]
    if not cases:
        raise ValueError("HTTP latency smoke has no frozen test cases")
    samples: list[float] = []
    with TestClient(create_app(settings)) as client:
        for index in range(warmup_requests):
            response = client.post("/resolve", json={"title": cases[index % len(cases)]["query"]})
            if response.status_code != 200:
                raise RuntimeError("HTTP latency warm-up did not return 200")
        for case in cases:
            started = time.perf_counter()
            response = client.post("/resolve", json={"title": case["query"]})
            samples.append((time.perf_counter() - started) * 1000)
            if response.status_code != 200:
                raise RuntimeError("HTTP latency sample did not return 200")
    return {
        "transport": "FastAPI TestClient in-process ASGI",
        "warmup_requests": warmup_requests,
        "sample_count": len(samples),
        "p50_latency_ms": statistics.median(samples),
        "p95_latency_ms": percentile(samples, .95),
        "samples_ms": samples,
        "includes_middleware_validation_serialization": True,
        "includes_tcp_network": False,
        "includes_container_runtime": False,
        "method": (
            "sequential warmed POST /resolve requests through in-process TestClient; "
            "app construction and warm-up excluded"
        ),
    }


def report_payload(report: EvaluationReport, http_latency: dict[str, Any]) -> dict[str, Any]:
    versioned_stem = f"evaluation-{report.dataset_version}-{report.split}"
    metrics = {name: getattr(report, name) for name in METRIC_NAMES}
    metrics.update({
        "pipeline_p50_latency_ms": report.pipeline_p50_latency_ms,
        "pipeline_p95_latency_ms": report.pipeline_p95_latency_ms,
        "http_p50_latency_ms": http_latency["p50_latency_ms"],
        "http_p95_latency_ms": http_latency["p95_latency_ms"],
    })
    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "report_id": f"{versioned_stem}-rrf-default-v2",
        "disclosure": {
            "dataset_kind": "synthetic_fixture",
            "test_case_count": report.sample_count,
            "notice": NON_PRODUCTION_NOTICE,
        },
        "dataset": {
            "dataset_version": report.dataset_version,
            "catalog_version": report.catalog_version,
            "split": report.split,
            "sample_count": report.sample_count,
            "matched_count": report.matched_count,
        },
        "configuration": report.metadata,
        "headline_metrics": metrics,
        "raw_counts": report.raw_counts,
        "latency_evidence": {
            "pipeline": {
                "p50_latency_ms": report.pipeline_p50_latency_ms,
                "p95_latency_ms": report.pipeline_p95_latency_ms,
                "samples_ms": report.pipeline_latency_samples_ms,
                "sample_count": len(report.pipeline_latency_samples_ms),
                "method": report.metadata["pipeline_latency_method"],
            },
            "http": http_latency,
            "container": {
                "measured": False,
                "reason": (
                    "Docker/container, TCP network, reverse-proxy, and concurrent-load latency "
                    "were not measured by this report."
                ),
            },
        },
        "ablations": report.ablations,
        "ablation_raw_ranks": report.ablation_raw_ranks,
        "comparisons": {
            "reranker_top1_absolute_gain_over_rrf": (
                report.ablations["reranker"]["top1_accuracy"]
                - report.ablations["rrf"]["top1_accuracy"]
            ),
        },
        "runtime_ranker_decision": {
            "selected_default": report.metadata["default_ranker"],
            "heuristic_reranker_runtime_enabled": report.metadata["reranker_runtime_enabled"],
            "heuristic_reranker_ablation_model": report.metadata["reranker_ablation_model"],
            "rrf_top1_accuracy": report.ablations["rrf"]["top1_accuracy"],
            "heuristic_reranker_top1_accuracy": report.ablations["reranker"]["top1_accuracy"],
            "absolute_gain": (
                report.ablations["reranker"]["top1_accuracy"]
                - report.ablations["rrf"]["top1_accuracy"]
            ),
            "decision": (
                "Keep heuristic-v1 out of the default runtime path because it adds zero "
                "Top-1 accuracy on the frozen fixture test; retain it only as an opt-in "
                "offline ablation."
            ),
            "external_cross_encoder_evaluated": report.metadata["external_cross_encoder_evaluated"],
            "external_model_conclusion": (
                "No external cross-encoder was evaluated; this decision makes no claim about one."
            ),
        },
        "r13_http_smoke": {
            "budget_ms": 1500.0,
            "candidate_k": report.metadata["candidate_k"],
            "observed_http_p95_ms": http_latency["p95_latency_ms"],
            "passes_local_in_process_budget": (
                http_latency["p95_latency_ms"] <= 1500.0
                and report.metadata["candidate_k"] <= 25
            ),
            "scope": "warmed in-process ASGI HTTP boundary only",
            "container_latency_validated": False,
        },
        "artifacts": {
            "markdown": f"{versioned_stem}.md",
            "retrieval_ablation": "retrieval-ablation.svg",
            "reranker_comparison": "reranker-comparison.svg",
            "precision_coverage": "precision-coverage.svg",
            "latency": "latency.svg",
        },
    }


def validate_report_payload(payload: dict[str, Any]) -> None:
    if payload.get("report_schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unsupported evaluation report schema")
    disclosure = payload.get("disclosure", {})
    dataset = payload.get("dataset", {})
    if disclosure.get("dataset_kind") != "synthetic_fixture":
        raise ValueError("report must disclose synthetic fixture construction")
    if disclosure.get("test_case_count") != 21 or dataset.get("sample_count") != 21:
        raise ValueError("fixture-v1 report must disclose exactly 21 test cases")
    notice = str(disclosure.get("notice", "")).casefold()
    for phrase in ("synthetic", "does not establish production accuracy", "production readiness"):
        if phrase not in notice:
            raise ValueError(f"missing report disclosure: {phrase}")

    metrics = payload.get("headline_metrics", {})
    raw = payload.get("raw_counts", {})
    matched = int(raw.get("matched_cases", 0))
    cases = int(raw.get("test_cases", 0))
    nonmatches = int(raw.get("nonmatch_cases", 0))
    predicted = int(raw.get("predicted_matches", 0))
    derivations = {
        "recall_at_10": safe_divide(raw.get("retrieved_at_10", 0), matched),
        "recall_at_25": safe_divide(raw.get("retrieved_at_25", 0), matched),
        "recall_at_50": safe_divide(raw.get("retrieved_at_50", 0), matched),
        "top1_accuracy": safe_divide(raw.get("correct_top1", 0), matched),
        "mrr_at_10": safe_divide(raw.get("reciprocal_rank_sum_at_10", 0), matched),
        "hard_negative_accuracy": safe_divide(raw.get("hard_correct", 0), raw.get("hard_total", 0)),
        "precision": safe_divide(raw.get("correct_matches", 0), predicted),
        "coverage": safe_divide(raw.get("correct_matches", 0), matched),
        "false_match_rate": safe_divide(raw.get("false_matches", 0), nonmatches),
        "abstention_rate": safe_divide(cases - predicted, cases),
    }
    for name, expected in derivations.items():
        actual = metrics.get(name)
        if not isinstance(actual, (int, float)) or not math.isclose(actual, expected, abs_tol=1e-12):
            raise ValueError(f"headline metric is not traceable to raw counts: {name}")

    ablations = payload.get("ablations", {})
    raw_ranks = payload.get("ablation_raw_ranks", {})
    for stage in ("sparse", "dense", "rrf", "reranker"):
        ranks = raw_ranks.get(stage)
        if not isinstance(ranks, list) or len(ranks) != matched:
            raise ValueError(f"ablation ranks do not match matched cases: {stage}")
        expected = {
            "top1_accuracy": safe_divide(sum(rank == 1 for rank in ranks), matched),
            "recall_at_25": safe_divide(sum(rank is not None and rank <= 25 for rank in ranks), matched),
            "mrr_at_10": safe_divide(
                sum(1.0 / rank for rank in ranks if rank is not None and rank <= 10), matched,
            ),
        }
        for name, expected_value in expected.items():
            actual_value = ablations.get(stage, {}).get(name, -1)
            if not math.isclose(actual_value, expected_value, abs_tol=1e-12):
                raise ValueError(f"ablation metric is not traceable to raw ranks: {stage}.{name}")

    latency_evidence = payload.get("latency_evidence", {})
    pipeline = latency_evidence.get("pipeline", {})
    http = latency_evidence.get("http", {})
    container = latency_evidence.get("container", {})
    for prefix, evidence in (("pipeline", pipeline), ("http", http)):
        samples = evidence.get("samples_ms", [])
        if len(samples) != cases or not all(
            isinstance(value, (int, float)) and value >= 0 for value in samples
        ):
            raise ValueError(f"{prefix} latency samples do not match raw test-case count")
        p50 = statistics.median(samples)
        p95 = percentile(samples, .95)
        if not math.isclose(metrics.get(f"{prefix}_p50_latency_ms", -1), p50, abs_tol=1e-12):
            raise ValueError(f"{prefix} p50 is not traceable to latency samples")
        if not math.isclose(metrics.get(f"{prefix}_p95_latency_ms", -1), p95, abs_tol=1e-12):
            raise ValueError(f"{prefix} p95 is not traceable to latency samples")
    if http.get("warmup_requests", 0) < 1 or http.get("includes_container_runtime") is not False:
        raise ValueError("HTTP latency evidence must be warmed and scoped to in-process ASGI")
    if container.get("measured") is not False or "not measured" not in str(container.get("reason", "")):
        raise ValueError("container latency limitation must remain explicit")

    r13 = payload.get("r13_http_smoke", {})
    expected_r13 = (
        metrics.get("http_p95_latency_ms", math.inf) <= r13.get("budget_ms", 0)
        and r13.get("candidate_k", 26) <= 25
    )
    if r13.get("passes_local_in_process_budget") is not expected_r13:
        raise ValueError("R13 HTTP smoke result is inconsistent with raw evidence")
    if r13.get("container_latency_validated") is not False:
        raise ValueError("R13 must not claim unmeasured container latency")

    ranker_decision = payload.get("runtime_ranker_decision", {})
    gain = payload.get("comparisons", {}).get("reranker_top1_absolute_gain_over_rrf")
    if ranker_decision.get("selected_default") != "rrf":
        raise ValueError("R11 alternative decision must keep RRF as the fixture default")
    if ranker_decision.get("heuristic_reranker_runtime_enabled") is not False:
        raise ValueError("heuristic reranker must remain disabled by default")
    if not math.isclose(ranker_decision.get("absolute_gain", math.inf), gain, abs_tol=1e-12):
        raise ValueError("R11 decision is inconsistent with ablation evidence")
    if ranker_decision.get("external_cross_encoder_evaluated") is not False:
        raise ValueError("report must not imply an external cross-encoder was evaluated")
    external_conclusion = str(ranker_decision.get("external_model_conclusion", "")).casefold()
    if "no external cross-encoder was evaluated" not in external_conclusion:
        raise ValueError("external model limitation is missing")

    configuration = payload.get("configuration", {})
    required_config = {
        "candidate_k", "dense_model", "default_ranker", "reranker",
        "reranker_runtime_enabled", "reranker_ablation_model", "external_cross_encoder_evaluated",
        "calibrator_artifact", "policy_version",
        "policy_thresholds", "benchmark_sha256", "catalog_sha256", "runtime", "machine",
        "pipeline_latency_method", "pipeline_warmup_requests",
    }
    if not required_config.issubset(configuration):
        raise ValueError("report configuration metadata is incomplete")
    expected_artifacts = {
        "markdown", "retrieval_ablation", "reranker_comparison", "precision_coverage", "latency",
    }
    if set(payload.get("artifacts", {})) != expected_artifacts:
        raise ValueError("report artifact manifest is incomplete")


def _format(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _bar_chart(
    title: str,
    subtitle: str,
    values: list[tuple[str, float, str]],
    *,
    maximum: float,
    unit: str = "",
) -> str:
    width, height = 840, 460
    left, right, top, bottom = 88, 32, 92, 88
    plot_width, plot_height = width - left - right, height - top - bottom
    slot = plot_width / max(1, len(values))
    bar_width = min(94, slot * .52)
    maximum = maximum if maximum > 0 else 1.0
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="840" height="460" viewBox="0 0 840 460" role="img">',
        f"<title>{escape(title)}</title>",
        '<rect width="840" height="460" fill="#08101a" rx="18"/>',
        f'<text x="40" y="44" fill="#f4f7fb" font-size="22" font-family="system-ui">{escape(title)}</text>',
        f'<text x="40" y="69" fill="#92a0b3" font-size="13" font-family="system-ui">{escape(subtitle)}</text>',
    ]
    for tick in range(5):
        ratio = tick / 4
        y = top + plot_height * (1 - ratio)
        value = maximum * ratio
        lines.extend([
            f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#253244" stroke-width="1"/>',
            f'<text x="{left-12}" y="{y+4:.2f}" text-anchor="end" fill="#748196" font-size="11" font-family="monospace">{escape(_format(value) + unit)}</text>',
        ])
    for index, (label, value, color) in enumerate(values):
        x = left + slot * index + (slot - bar_width) / 2
        bounded = max(0.0, min(value, maximum))
        bar_height = plot_height * bounded / maximum
        y = top + plot_height - bar_height
        lines.extend([
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="7" fill="{color}"/>',
            f'<text x="{x+bar_width/2:.2f}" y="{y-10:.2f}" text-anchor="middle" fill="#f4f7fb" font-size="12" font-family="monospace">{escape(_format(value) + unit)}</text>',
            f'<text x="{x+bar_width/2:.2f}" y="{height-bottom+28}" text-anchor="middle" fill="#c5d0df" font-size="12" font-family="system-ui">{escape(label)}</text>',
        ])
    lines.append('</svg>\n')
    return "\n".join(lines)


def _markdown(payload: dict[str, Any]) -> str:
    metrics = payload["headline_metrics"]
    raw = payload["raw_counts"]
    config = payload["configuration"]
    ablations = payload["ablations"]
    artifacts = payload["artifacts"]
    latency = payload["latency_evidence"]
    r13 = payload["r13_http_smoke"]
    ranker_decision = payload["runtime_ranker_decision"]
    metric_rows = [
        ("Recall@10", metrics["recall_at_10"], "retrieved_at_10 / matched_cases"),
        ("Recall@25", metrics["recall_at_25"], "retrieved_at_25 / matched_cases"),
        ("Recall@50", metrics["recall_at_50"], "retrieved_at_50 / matched_cases"),
        ("Top-1 accuracy", metrics["top1_accuracy"], "correct_top1 / matched_cases"),
        ("MRR@10", metrics["mrr_at_10"], "reciprocal_rank_sum_at_10 / matched_cases"),
        ("Hard-negative accuracy", metrics["hard_negative_accuracy"], "hard_correct / hard_total"),
        ("Precision", metrics["precision"], "correct_matches / predicted_matches"),
        ("Coverage", metrics["coverage"], "correct_matches / matched_cases"),
        ("False-match rate", metrics["false_match_rate"], "false_matches / nonmatch_cases"),
        ("Abstention rate", metrics["abstention_rate"], "(test_cases - predicted_matches) / test_cases"),
    ]
    lines = [
        f"# Product Variant Resolver evaluation — {payload['dataset']['dataset_version']} / test",
        "",
        f"> **Scope disclosure:** {payload['disclosure']['notice']}",
        "",
        "## Frozen data and configuration",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Test cases | {payload['dataset']['sample_count']} |",
        f"| Matched cases | {payload['dataset']['matched_count']} |",
        f"| Split strategy | {config['split_strategy']} |",
        f"| Benchmark SHA-256 | `{config['benchmark_sha256']}` |",
        f"| Catalog SHA-256 | `{config['catalog_sha256']}` |",
        f"| Candidate K | {config['candidate_k']} |",
        f"| Dense baseline | `{config['dense_model']}` |",
        f"| Default ranker | `{config['default_ranker']}` |",
        f"| Runtime reranker | `{config['reranker']}` |",
        f"| Ablation-only reranker | `{config['reranker_ablation_model']}` |",
        f"| Calibrator | `{config['calibrator_artifact']}` |",
        f"| Policy | `{config['policy_version']}`; `{json.dumps(config['policy_thresholds'], sort_keys=True)}` |",
        "",
        "## Headline metrics",
        "",
        "Every value below is derivable from `raw_counts` in the adjacent versioned JSON report.",
        "",
        "| Metric | Value | Raw derivation |",
        "|---|---:|---|",
    ]
    lines.extend(f"| {name} | {_format(value)} | `{derivation}` |" for name, value, derivation in metric_rows)
    lines.extend([
        "",
        "## Retrieval and reranking ablation",
        "",
        "All stages use the same 12 matched test queries and candidate configuration.",
        "",
        "| Stage | Top-1 | Recall@25 | MRR@10 |",
        "|---|---:|---:|---:|",
    ])
    for stage in ("sparse", "dense", "rrf", "reranker"):
        values = ablations[stage]
        lines.append(
            f"| {stage} | {_format(values['top1_accuracy'])} | "
            f"{_format(values['recall_at_25'])} | {_format(values['mrr_at_10'])} |"
        )
    lines.extend([
        "",
        f"Reranking changes Top-1 by **{_format(payload['comparisons']['reranker_top1_absolute_gain_over_rrf'])} absolute** over RRF.",
        "",
        "### R11 alternative decision",
        "",
        f"- Selected default: **{ranker_decision['selected_default']}**.",
        f"- Frozen test evidence: RRF Top-1 {_format(ranker_decision['rrf_top1_accuracy'])}; "
        f"heuristic-v1 Top-1 {_format(ranker_decision['heuristic_reranker_top1_accuracy'])}; "
        f"absolute gain {_format(ranker_decision['absolute_gain'])}.",
        f"- Decision: {ranker_decision['decision']}",
        f"- External-model boundary: {ranker_decision['external_model_conclusion']}",
        "",
        f"![Retrieval ablation]({artifacts['retrieval_ablation']})",
        "",
        f"![Reranker comparison]({artifacts['reranker_comparison']})",
        "",
        "## Reliability operating point",
        "",
        "This is one frozen policy operating point, not a full precision–coverage curve.",
        "",
        f"![Precision and coverage]({artifacts['precision_coverage']})",
        "",
        "## Latency metadata",
        "",
        "The two measurements below are intentionally separate:",
        "",
        "| Boundary | p50 | p95 | Samples | Method |",
        "|---|---:|---:|---:|---|",
        f"| Internal pipeline | {_format(metrics['pipeline_p50_latency_ms'])} ms | "
        f"{_format(metrics['pipeline_p95_latency_ms'])} ms | {latency['pipeline']['sample_count']} | "
        f"{latency['pipeline']['method']} |",
        f"| Warmed HTTP `/resolve` | {_format(metrics['http_p50_latency_ms'])} ms | "
        f"{_format(metrics['http_p95_latency_ms'])} ms | {latency['http']['sample_count']} | "
        f"{latency['http']['method']} |",
        "",
        f"- HTTP warm-up requests excluded from samples: {latency['http']['warmup_requests']}",
        f"- Pipeline warm-up requests excluded from samples: {config['pipeline_warmup_requests']}",
        "- HTTP smoke includes FastAPI middleware, validation, dispatch, response serialization, and headers.",
        "- HTTP smoke is in-process ASGI; it excludes TCP/network, Docker/container, reverse proxy, and concurrency.",
        f"- Container latency measured: **{str(latency['container']['measured']).lower()}** — {latency['container']['reason']}",
        f"- Runtime/hardware: Python {config['runtime']}; `{config['machine']}` / `{config['processor'] or 'unreported'}`",
        "- Both sets of 21 raw samples are retained in the JSON report.",
        "",
        "### R13 local evidence",
        "",
        f"The warmed in-process HTTP p95 is **{_format(r13['observed_http_p95_ms'])} ms** against "
        f"the **{_format(r13['budget_ms'])} ms** fixture budget at candidate K={r13['candidate_k']}: "
        f"**{'PASS' if r13['passes_local_in_process_budget'] else 'FAIL'} for this limited scope**.",
        "This does not validate Docker/container or real network latency.",
        "",
        f"![Latency summary]({artifacts['latency']})",
        "",
        "## Raw counts",
        "",
        "```json",
        json.dumps(raw, indent=2, sort_keys=True),
        "```",
        "",
        "## Limitations",
        "",
        "- The catalog and queries are deterministic synthetic/curated fixtures, not a real marketplace sample.",
        "- The test split contains only 21 cases, including 12 matched cases.",
        "- Latency includes direct-pipeline and in-process HTTP/ASGI smoke measurements; container, database, TCP network, and concurrency costs are excluded.",
        "- These numbers must not be presented as production accuracy or broad Hot Wheels coverage.",
        "",
    ])
    return "\n".join(lines)


def write_report(
    report: EvaluationReport, http_latency: dict[str, Any], output_root: Path,
) -> dict[str, Path]:
    payload = report_payload(report, http_latency)
    validate_report_payload(payload)
    output_directory = output_root / report.dataset_version
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"evaluation-{report.dataset_version}-{report.split}"
    paths = {
        "json": output_directory / f"{stem}.json",
        "markdown": output_directory / f"{stem}.md",
        "retrieval_ablation": output_directory / "retrieval-ablation.svg",
        "reranker_comparison": output_directory / "reranker-comparison.svg",
        "precision_coverage": output_directory / "precision-coverage.svg",
        "latency": output_directory / "latency.svg",
    }
    paths["json"].write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["markdown"].write_text(_markdown(payload), encoding="utf-8")

    palette = ("#7ba9ff", "#74f0c1", "#ffc96b", "#ff7e82")
    paths["retrieval_ablation"].write_text(_bar_chart(
        "Retrieval ablation — Top-1 accuracy", "12 matched synthetic fixture test cases",
        [(stage, report.ablations[stage]["top1_accuracy"], palette[index])
         for index, stage in enumerate(("sparse", "dense", "rrf", "reranker"))],
        maximum=1.0,
    ), encoding="utf-8")
    paths["reranker_comparison"].write_text(_bar_chart(
        "Reranker value comparison", "RRF versus pointwise reranker; identical frozen test candidates",
        [("RRF Top-1", report.ablations["rrf"]["top1_accuracy"], palette[0]),
         ("Reranker Top-1", report.ablations["reranker"]["top1_accuracy"], palette[1])],
        maximum=1.0,
    ), encoding="utf-8")
    paths["precision_coverage"].write_text(_bar_chart(
        "Reliability operating point", "One frozen threshold policy; not a full curve",
        [("Precision", report.precision, palette[1]), ("Coverage", report.coverage, palette[0]),
         ("False match", report.false_match_rate, palette[3]),
         ("Abstention", report.abstention_rate, palette[2])],
        maximum=1.0,
    ), encoding="utf-8")
    latency_maximum = max(
        report.pipeline_p95_latency_ms, http_latency["p95_latency_ms"], 1.0,
    ) * 1.15
    paths["latency"].write_text(_bar_chart(
        "Pipeline versus warmed HTTP latency",
        "In-process ASGI only; Docker/container and TCP network latency not measured",
        [("Pipeline p50", report.pipeline_p50_latency_ms, palette[0]),
         ("Pipeline p95", report.pipeline_p95_latency_ms, palette[1]),
         ("HTTP p50", http_latency["p50_latency_ms"], palette[2]),
         ("HTTP p95", http_latency["p95_latency_ms"], palette[3])],
        maximum=latency_maximum, unit=" ms",
    ), encoding="utf-8")
    return paths


def generate_report(settings: Settings, output_root: Path) -> dict[str, Path]:
    report = evaluate(settings)
    http_latency = measure_warmed_http_latency(settings)
    return write_report(report, http_latency, output_root)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate versioned fixture evaluation evidence")
    parser.add_argument("--output-directory", type=Path, default=Path("reports"))
    arguments = parser.parse_args()
    paths = generate_report(Settings.from_env(), arguments.output_directory)
    for name, path in paths.items():
        print(f"{name}={path}")


if __name__ == "__main__":
    main()
