from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.selenium_catalog import (
    export_xlsx,
    is_denied_host,
    normalize_table_snapshots,
    validate_remote_target,
)

ROOT = Path(__file__).resolve().parents[2]


def test_target_must_match_exact_allowed_host_and_blocks_fandom() -> None:
    assert validate_remote_target(
        "https://catalog.example.test/wiki/2025", "catalog.example.test"
    ) == ("catalog.example.test")
    assert is_denied_host("hotwheels.fandom.com")
    assert is_denied_host("community.wikia.org")
    with pytest.raises(ValueError, match="intentionally blocked"):
        validate_remote_target(
            "https://hotwheels.fandom.com/wiki/Hot_Wheels", "hotwheels.fandom.com"
        )
    with pytest.raises(ValueError, match="exactly match"):
        validate_remote_target("https://other.example.test/wiki/2025", "catalog.example.test")
    with pytest.raises(ValueError, match="credentials"):
        validate_remote_target(
            "https://user:pass@catalog.example.test/wiki/2025", "catalog.example.test"
        )


def test_normalizes_table_filters_year_and_preserves_raw_fields() -> None:
    snapshots = [
        {
            "table_index": 1,
            "headers": ["Toy #", "Col.#", "Model Name", "Series", "Series #", "Color", "Year"],
            "rows": [
                {
                    "row_index": 1,
                    "cells": [
                        {"text": "AAA01"},
                        {"text": "001"},
                        {"text": "Example Car (2nd Color - Zamac)"},
                        {"text": "City Cars"},
                        {"text": "1/5"},
                        {"text": "Zamac"},
                        {"text": "2025"},
                    ],
                },
                {
                    "row_index": 2,
                    "cells": [
                        {"text": "OLD01"},
                        {"text": "009"},
                        {"text": "Old Car"},
                        {"text": "Archive"},
                        {"text": "9/9"},
                        {"text": "Black"},
                        {"text": "2024"},
                    ],
                },
            ],
        }
    ]
    records, counters = normalize_table_snapshots(
        snapshots,
        source_url="https://catalog.example.test/wiki/2025",
        page_title="Example catalog",
        release_year=2025,
        brand="Example",
        scraped_at_utc="2026-09-16T12:00:00Z",
        max_records=100,
    )

    assert len(records) == 1
    assert records[0]["casting_name"] == "Example Car"
    assert records[0]["variant_note"] == "2nd Color - Zamac"
    assert records[0]["color"] == "Zamac"
    assert '"Toy #": "AAA01"' in records[0]["raw_fields_json"]
    assert counters == {
        "candidate_tables": 1,
        "eligible_tables": 1,
        "rows_seen": 2,
        "rows_filtered_by_year": 1,
        "records_exported": 1,
    }


def test_missing_identifiers_are_exported_as_auditable_parse_error() -> None:
    snapshots = [
        {
            "table_index": 1,
            "headers": ["Toy #", "Model Name"],
            "rows": [{"row_index": 1, "cells": [{"text": ""}, {"text": "Mystery Car"}]}],
        }
    ]
    records, _ = normalize_table_snapshots(
        snapshots,
        source_url="https://catalog.example.test/wiki/2025",
        page_title="Example catalog",
        release_year=2025,
        brand="Example",
        scraped_at_utc="2026-09-16T12:00:00Z",
        max_records=100,
    )
    assert records[0]["parse_status"] == "error"
    assert records[0]["parse_error"] == "missing toy and collector numbers"


def test_portable_python_export_writes_review_workbook(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    payload = json.loads(
        (ROOT / "tests" / "fixtures" / "fandom_like_catalog_export.json").read_text(
            encoding="utf-8"
        )
    )
    output = tmp_path / "catalog.xlsx"

    export_xlsx(payload, output_path=output)

    workbook = openpyxl.load_workbook(output, data_only=False)
    assert workbook.sheetnames == ["Summary", "Releases"]
    assert workbook["Summary"]["B8"].value == "=COUNTA(Releases!A7:A9)"
    assert workbook["Releases"]["E7"].value == "001"
    assert workbook["Releases"]["E7"].number_format == "@"
    assert workbook["Releases"].freeze_panes == "D7"
    assert workbook.calculation.calcMode == "auto"
    assert workbook.calculation.fullCalcOnLoad is True
