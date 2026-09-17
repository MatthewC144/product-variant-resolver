from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "outputs" / "selenium-fandom-like-crawler-v1" / "sample_catalog.xlsx"


def test_sample_workbook_has_expected_sheets_formulas_and_identifier_types() -> None:
    with ZipFile(WORKBOOK) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        summary_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        releases_xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")

    assert 'name="Summary"' in workbook_xml
    assert 'name="Releases"' in workbook_xml
    assert "COUNTA(Releases!A7:A9)" in summary_xml
    assert 'r="E7"' in releases_xml
    assert re.search(r'r="E7"[^>]*t="str"><x:v>001</x:v>', releases_xml)
    assert 'name="CollectedReleases"' not in releases_xml
    assert '<x:tableParts count="1">' in releases_xml
