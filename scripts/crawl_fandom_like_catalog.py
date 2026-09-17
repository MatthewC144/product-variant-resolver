from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_variant_resolver.selenium_catalog import (
    collect_page,
    create_chrome_driver,
    export_xlsx,
    validate_remote_target,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect one permitted Fandom-like catalog page with Selenium and export XLSX"
    )
    parser.add_argument("--start-url", required=True)
    parser.add_argument("--allowed-host", required=True)
    parser.add_argument("--confirm-permission", action="store_true")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--brand", default="Hot Wheels")
    parser.add_argument("--max-records", type=int, default=3000)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--page-load-timeout", type=float, default=30.0)
    parser.add_argument("--wait-timeout", type=float, default=15.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "selenium-fandom-like-crawler-v1" / "catalog.xlsx",
    )
    arguments = parser.parse_args()

    if not arguments.confirm_permission:
        parser.error(
            "--confirm-permission is required: use it only after confirming the target permits automated access"
        )
    validate_remote_target(arguments.start_url, arguments.allowed_host)
    driver = create_chrome_driver(
        headless=not arguments.headed,
        page_load_timeout=arguments.page_load_timeout,
    )
    try:
        payload = collect_page(
            driver,
            start_url=arguments.start_url,
            allowed_host=arguments.allowed_host,
            release_year=arguments.year,
            brand=arguments.brand,
            wait_timeout=arguments.wait_timeout,
            max_records=arguments.max_records,
        )
    finally:
        driver.quit()
    export_xlsx(
        payload,
        output_path=arguments.output,
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "records": len(payload["records"]),
                "source": payload["source"]["final_url"],
                "output": str(arguments.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
