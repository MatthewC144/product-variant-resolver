from __future__ import annotations

import json
import unittest

from product_variant_resolver.fandom_ingestion import (
    FandomRevision,
    parse_mainline_records,
)


WIKITEXT = '''
Intro
{|class="sortable wikitable" width="100%"
|-
! Toy #
! Col.#
! Model Name
! Series
! Series #
! Photo
|-
|AAA01
|001
|[[Example Car (2025)|Example Car]]
|bgcolor="#000"|[[Example Series (2025)|<font color="white">Example Series</font>]]<br>{{NM|2025}}
|1/10
|[[File:Example.jpg|center|75px]]
|-
|AAA02
|001
|[[Example Car (2025)|Example Car]] (2nd Color - Zamac)
|[[Example Series (2025)|Example Series]]<br>{{WM|2025}}
|1/10
|[[File:Example2.jpg|center|75px]]
|}
Other table
'''


class FandomIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.revision = FandomRevision(
            page_id=1,
            page_title="List of 2025 Hot Wheels",
            revision_id=123,
            revision_timestamp="2026-01-01T00:00:00Z",
            wikitext=WIKITEXT,
        )
        self.license = {
            "name": "CC-BY-SA",
            "url": "https://www.fandom.com/licensing",
        }

    def test_parses_text_without_promoting_or_copying_images(self) -> None:
        records = parse_mainline_records(
            self.revision,
            release_year=2025,
            limit=2,
            license_info=self.license,
        )

        self.assertEqual(records[0]["casting_name"], "Example Car")
        self.assertEqual(records[0]["source_row"], 1)
        self.assertEqual(records[0]["series"], "Example Series")
        self.assertEqual(records[0]["source_markers"], ["NM"])
        self.assertEqual(records[1]["variant_note"], "2nd Color - Zamac")
        self.assertEqual(records[1]["source_row"], 2)
        self.assertEqual(records[1]["source_markers"], ["WM"])
        self.assertTrue(all(record["color"] is None for record in records))
        self.assertTrue(all(record["canonical_uuid"] is None for record in records))
        self.assertNotIn("File:", json.dumps(records))

    def test_is_deterministic_and_validates_limits_and_table_size(self) -> None:
        first = parse_mainline_records(
            self.revision,
            release_year=2025,
            limit=2,
            license_info=self.license,
        )
        repeated = parse_mainline_records(
            self.revision,
            release_year=2025,
            limit=2,
            license_info=self.license,
        )
        self.assertEqual(first, repeated)
        with self.assertRaisesRegex(ValueError, "between 1 and 500"):
            parse_mainline_records(
                self.revision,
                release_year=2025,
                limit=0,
                license_info=self.license,
            )
        with self.assertRaisesRegex(ValueError, "expected 3"):
            parse_mainline_records(
                self.revision,
                release_year=2025,
                limit=3,
                license_info=self.license,
            )
if __name__ == "__main__":
    unittest.main()
