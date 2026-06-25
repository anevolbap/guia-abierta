"""Resource selection from CKAN listings: format preference, then fallback.

pick_resource is pure (operates on plain dicts, no network)."""
import unittest

from fetch import pick_resource


class TestPickResource(unittest.TestCase):
    def test_prefers_format_order_not_list_order(self):
        resources = [
            {"format": "ZIP", "url": "http://x/a.zip"},
            {"format": "GeoJSON", "url": "http://x/a.geojson"},
        ]
        picked = pick_resource(resources, ["geojson", "zip"])
        self.assertEqual(picked["url"], "http://x/a.geojson")

    def test_matches_on_url_suffix_when_format_missing(self):
        resources = [{"url": "http://x/streets.geojson"}]
        picked = pick_resource(resources, ["geojson"])
        self.assertEqual(picked["url"], "http://x/streets.geojson")

    def test_falls_back_to_first_with_url(self):
        resources = [{"format": "html"}, {"url": "http://x/data.bin"}]
        picked = pick_resource(resources, ["geojson"])
        self.assertEqual(picked["url"], "http://x/data.bin")

    def test_raises_when_nothing_downloadable(self):
        with self.assertRaises(RuntimeError):
            pick_resource([{"format": "html"}], ["geojson"])


if __name__ == "__main__":
    unittest.main()
