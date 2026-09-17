from __future__ import annotations

import os
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from product_variant_resolver.selenium_catalog import (
    TABLE_EXTRACTION_SCRIPT,
    create_chrome_driver,
    normalize_table_snapshots,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    os.environ.get("PVR_RUN_BROWSER_TESTS") != "1",
    reason="set PVR_RUN_BROWSER_TESTS=1 for the local Chrome/Selenium smoke test",
)
def test_selenium_reads_dynamic_local_fixture() -> None:
    driver = create_chrome_driver(headless=True, page_load_timeout=20)
    try:
        fixture_url = (ROOT / "tests" / "fixtures" / "fandom_like_catalog.html").as_uri()
        driver.get(fixture_url)
        WebDriverWait(driver, 5).until(
            lambda browser: len(browser.find_elements(By.CSS_SELECTOR, "table.wikitable")) == 2
        )
        snapshots = driver.execute_script(TABLE_EXTRACTION_SCRIPT)
        records, counters = normalize_table_snapshots(
            snapshots,
            source_url=fixture_url,
            page_title=driver.title,
            release_year=2025,
            brand="Example",
            scraped_at_utc="2026-09-16T12:00:00Z",
            max_records=100,
        )
    finally:
        driver.quit()

    assert len(records) == 3
    assert records[1]["variant_note"] == "2nd Color - Zamac"
    assert counters["rows_filtered_by_year"] == 1
