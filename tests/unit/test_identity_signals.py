import unittest

from product_variant_resolver.identity import (
    assert_identity_immutable, fingerprint, mint_slug, mint_uuid,
)
from product_variant_resolver.signals import extract_signals


class IdentitySignalTests(unittest.TestCase):
    def setUp(self):
        self.product = {
            "brand": "Hot Wheels", "casting": "Chevy Nomad", "release_year": 2000,
            "series": "Mainline", "color": "Orange", "collector_number": "196", "edition": None,
        }

    def test_identity_changes_with_variant_fields_and_ignores_description(self):
        other = dict(self.product, color="Blue")
        described = dict(self.product, description="corrected prose")
        self.assertNotEqual(fingerprint(self.product), fingerprint(other))
        self.assertEqual(fingerprint(self.product), fingerprint(described))
        self.assertEqual(mint_uuid(self.product), mint_uuid(described))
        self.assertIn("chevy-nomad", mint_slug(self.product))

    def test_slug_collision_gets_deterministic_suffix(self):
        base = mint_slug(self.product)
        collision = mint_slug(self.product, {base: "different"})
        self.assertTrue(collision.startswith(base + "-"))
        self.assertEqual(collision, mint_slug(self.product, {base: "different"}))

    def test_immutable_identity_guard(self):
        before = {"canonical_uuid": "a", "canonical_id": "one"}
        with self.assertRaises(ValueError):
            assert_identity_immutable(before, {**before, "canonical_id": "two"})

    def test_generic_signal_extraction_uses_catalog_color_vocabulary(self):
        signals = extract_signals(
            "2022 Nomad Chartreuse Galaxy Run #101 3/10 lot of 4",
            {"chartreuse", "orange"}, {"Galaxy Run", "Mainline"},
        )
        self.assertEqual(signals.year, 2022)
        self.assertEqual(signals.collector_number, "101")
        self.assertEqual(signals.series_position, "3/10")
        self.assertEqual(signals.quantity, 4)
        self.assertEqual(signals.color_hints, ["chartreuse"])
        self.assertEqual(signals.series_hints, ["galaxy run"])
        boundary = extract_signals("Mainliner edition", series_vocabulary={"Mainline"})
        self.assertEqual(boundary.series_hints, [])

    def test_false_positive_boundaries(self):
        signals = extract_signals("model 12022 xylophone #A12B")
        self.assertIsNone(signals.year)
        self.assertIsNone(signals.quantity)


if __name__ == "__main__":
    unittest.main()
