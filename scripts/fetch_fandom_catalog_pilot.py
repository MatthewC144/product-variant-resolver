from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_variant_resolver.fandom_ingestion import (
    FandomRevision,
    STAGING_SCHEMA_VERSION,
    fetch_revision,
    fetch_rights_info,
    parse_mainline_records,
    sha256_text,
    stable_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a review-only Hot Wheels Wiki catalog pilot"
    )
    parser.add_argument("--page", default="List of 2025 Hot Wheels")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--raw-input",
        type=Path,
        help="rebuild normalized artifacts from a previously frozen raw.json without network",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/pilot-2025"),
    )
    arguments = parser.parse_args()

    if arguments.raw_input:
        frozen = json.loads(arguments.raw_input.read_text(encoding="utf-8"))
        frozen_source = frozen["source"]
        license_info = {
            "name": frozen_source["license"],
            "url": frozen_source["license_url"],
        }
        if license_info != {
            "name": "CC-BY-SA",
            "url": "https://www.fandom.com/licensing",
        }:
            raise ValueError("frozen raw source has an unexpected license")
        revision = FandomRevision(
            page_id=frozen_source["page_id"],
            page_title=frozen_source["page_title"],
            revision_id=frozen_source["revision_id"],
            revision_timestamp=frozen_source["revision_timestamp"],
            wikitext=frozen["wikitext"],
        )
    else:
        license_info = fetch_rights_info()
        revision = fetch_revision(arguments.page)
    records = parse_mainline_records(
        revision,
        release_year=arguments.year,
        limit=arguments.limit,
        license_info=license_info,
    )
    dataset_version = (
        f"fandom-hot-wheels-{arguments.year}-pilot-r{revision.revision_id}-v1"
    )
    source = {
        "wiki": "Hot Wheels Wiki",
        "page_id": revision.page_id,
        "page_title": revision.page_title,
        "page_url": (
            "https://hotwheels.fandom.com/wiki/"
            f"{revision.page_title.replace(' ', '_')}?oldid={revision.revision_id}"
        ),
        "revision_id": revision.revision_id,
        "revision_timestamp": revision.revision_timestamp,
        "license": license_info["name"],
        "license_url": license_info["url"],
    }
    raw_payload = {
        "schema_version": "fandom-mediawiki-raw-v1",
        "source": source,
        "wikitext": revision.wikitext,
    }
    normalized_payload = {
        "schema_version": STAGING_SCHEMA_VERSION,
        "dataset_version": dataset_version,
        "record_count": len(records),
        "scope": "review-only catalog candidates; excluded from canonical API and evaluation",
        "source": source,
        "records": records,
    }
    raw_text = stable_json(raw_payload)
    normalized_text = stable_json(normalized_payload)
    manifest_payload = {
        "schema_version": "fandom-pilot-manifest-v1",
        "dataset_version": dataset_version,
        "record_count": len(records),
        "source_revision_id": revision.revision_id,
        "license": license_info,
        "files": {
            "raw.json": {"sha256": sha256_text(raw_text)},
            "normalized.json": {"sha256": sha256_text(normalized_text)},
        },
        "usage_limits": [
            "needs_canonical_review",
            "not_canonical_ground_truth",
            "not_evaluation_or_threshold_training",
            "text_only_no_images_downloaded",
        ],
    }
    output = arguments.output_directory
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw.json").write_text(raw_text, encoding="utf-8")
    (output / "normalized.json").write_text(normalized_text, encoding="utf-8")
    (output / "manifest.json").write_text(
        stable_json(manifest_payload), encoding="utf-8"
    )
    print(
        stable_json(
            {
                "status": "complete",
                "dataset_version": dataset_version,
                "record_count": len(records),
                "output_directory": str(output),
                "source_revision_id": revision.revision_id,
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
