from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_variant_resolver.fandom_ingestion import sha256_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a frozen Fandom catalog pilot")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/pilot-2025"),
    )
    arguments = parser.parse_args()
    directory = arguments.directory
    raw_text = (directory / "raw.json").read_text(encoding="utf-8")
    normalized_text = (directory / "normalized.json").read_text(encoding="utf-8")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    normalized = json.loads(normalized_text)
    raw = json.loads(raw_text)

    assert manifest["files"]["raw.json"]["sha256"] == sha256_text(raw_text)
    assert manifest["files"]["normalized.json"]["sha256"] == sha256_text(
        normalized_text
    )
    records = normalized["records"]
    assert len(records) == manifest["record_count"] == normalized["record_count"] == 100
    assert raw["source"] == normalized["source"]
    assert normalized["source"]["revision_id"] == manifest["source_revision_id"]
    assert normalized["source"]["license"] == "CC-BY-SA"
    assert len({record["source_record_id"] for record in records}) == len(records)
    assert len({record["toy_number"] for record in records}) == len(records)
    assert [record["source_row"] for record in records] == list(range(1, 101))
    for record in records:
        assert record["brand"] == "Hot Wheels"
        assert record["release_year"] == 2025
        assert record["toy_number"]
        assert record["casting_name"]
        assert record["series"]
        assert record["color"] is None
        assert record["canonical_uuid"] is None
        assert record["review_status"] == "needs_canonical_review"
        assert record["usage"] == "staging_only_not_evaluation_or_canonical"
        assert "File:" not in json.dumps(record)
    print(
        json.dumps(
            {
                "status": "passed",
                "dataset_version": normalized["dataset_version"],
                "record_count": len(records),
                "unique_toy_numbers": len({row["toy_number"] for row in records}),
                "records_with_variant_note": sum(
                    row["variant_note"] is not None for row in records
                ),
                "records_with_unknown_color": sum(
                    row["color"] is None for row in records
                ),
                "canonical_promotions": sum(
                    row["canonical_uuid"] is not None for row in records
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
