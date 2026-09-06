#!/usr/bin/env python3
"""Import reviewed recognition names into a portable, evaluation-safe corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET_VERSION = "human-labeled-real-noisy-v1"
SCHEMA_VERSION = "pvr-human-labeled-name-pairs-v1"
REQUIRED_COLUMNS = {
    "case_id",
    "review_status",
    "candidate_1",
    "candidate_1_confidence",
    "deterministic_keyword",
    "identity_ai_keyword",
    "identity_conditional_evidence_ai_keyword",
    "full_multimodal_verifier_keyword",
    "human_expected_candidate",
    "human_expected_brand",
    "human_expected_casting",
    "human_expected_series",
    "human_expected_variant",
    "human_expected_pricing_keyword",
    "human_failure_categories",
    "human_label_confidence",
}


def _clean(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _categories(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _confidence(value: str | None, *, case_id: str) -> float | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        result = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"{case_id}: invalid candidate_1_confidence") from exc
    if not 0 <= result <= 1:
        raise ValueError(f"{case_id}: candidate_1_confidence must be in [0, 1]")
    return result


def build_dataset(source_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    with source_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError(f"source is missing columns: {', '.join(missing_columns)}")
        source_rows = list(reader)

    records: list[dict[str, Any]] = []
    excluded_count = 0
    seen_ids: set[str] = set()
    for row in source_rows:
        case_id = _clean(row.get("case_id"))
        if case_id is None:
            raise ValueError("source row is missing case_id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate case_id: {case_id}")
        seen_ids.add(case_id)
        if row.get("review_status") == "excluded":
            excluded_count += 1
            continue

        human_label_name = _clean(row.get("human_expected_candidate"))
        human_label_casting = _clean(row.get("human_expected_casting"))
        human_label_pricing_keyword = _clean(row.get("human_expected_pricing_keyword"))
        human_label_confidence = _clean(row.get("human_label_confidence"))
        if not all(
            (human_label_name, human_label_casting, human_label_pricing_keyword)
        ):
            raise ValueError(f"{case_id}: included row is missing a required human label")
        if human_label_confidence != "confirmed":
            raise ValueError(f"{case_id}: included row does not have a confirmed human label")

        initial_name = _clean(row.get("candidate_1"))
        records.append(
            {
                "case_id": case_id,
                "source_type": "human_labeled_real_noisy_scan",
                "initial_output_status": "candidate" if initial_name else "no_candidate",
                "initial_name": initial_name,
                "initial_confidence": _confidence(
                    row.get("candidate_1_confidence"), case_id=case_id
                ),
                "pipeline_outputs": {
                    "deterministic_keyword": _clean(row.get("deterministic_keyword")),
                    "identity_ai_keyword": _clean(row.get("identity_ai_keyword")),
                    "identity_conditional_evidence_ai_keyword": _clean(
                        row.get("identity_conditional_evidence_ai_keyword")
                    ),
                    "full_multimodal_verifier_keyword": _clean(
                        row.get("full_multimodal_verifier_keyword")
                    ),
                },
                "human_label_name": human_label_name,
                "human_label_brand": _clean(row.get("human_expected_brand")),
                "human_label_casting": human_label_casting,
                "human_label_series": _clean(row.get("human_expected_series")),
                "human_label_variant": _clean(row.get("human_expected_variant")),
                "human_label_pricing_keyword": human_label_pricing_keyword,
                "human_label_confidence": human_label_confidence,
                "failure_categories": _categories(row.get("human_failure_categories")),
            }
        )

    dataset = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "description": (
            "Human-reviewed name pairs from real noisy scans. This auxiliary corpus is "
            "not part of canonical resolver accuracy or calibration gates until records "
            "are mapped to this repository's immutable catalog identities."
        ),
        "usage_scope": [
            "candidate_name_evaluation",
            "name_normalization_evaluation",
            "future_catalog_alignment",
        ],
        "excluded_from": [
            "canonical_resolution_accuracy",
            "calibration_training",
            "threshold_selection",
        ],
        "records": records,
    }
    paired_count = sum(record["initial_name"] is not None for record in records)
    manifest = {
        "schema_version": "pvr-human-labeled-name-pairs-manifest-v1",
        "dataset_version": DATASET_VERSION,
        "source_dataset_id": "real-noisy-scans",
        "source_label_version": "human-labels-v1",
        "source_file_name": source_path.name,
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "source_row_count": len(source_rows),
        "excluded_source_row_count": excluded_count,
        "record_count": len(records),
        "paired_initial_name_count": paired_count,
        "missing_initial_name_count": len(records) - paired_count,
    }
    return dataset, manifest


def write_outputs(
    dataset: dict[str, Any],
    manifest: dict[str, Any],
    *,
    output_path: Path,
    manifest_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_text = json.dumps(dataset, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path.write_text(dataset_text, encoding="utf-8")
    manifest["dataset_file_name"] = output_path.name
    manifest["dataset_sha256"] = hashlib.sha256(dataset_text.encode("utf-8")).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "human_labeled_names.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "human_labeled_names_manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset, manifest = build_dataset(args.source)
    write_outputs(dataset, manifest, output_path=args.output, manifest_path=args.manifest)
    print(
        f"imported {manifest['record_count']} reviewed records "
        f"({manifest['paired_initial_name_count']} with initial names, "
        f"{manifest['missing_initial_name_count']} no-candidate cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
