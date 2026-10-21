#!/usr/bin/env python3
"""Tests for report.py against Umami 3.4 response shapes checked on 2026-10-01 (plus the Umami 2 stats shape).

All values are synthetic."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest
import urllib.parse

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_analytics_report", HERE / "report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

WEBSITE = {"id": "00000000-0000-4000-8000-000000000001", "name": "Demo", "domain": "demo-site.io"}
METRICS = {
    "path": [{"x": "/tools/alpha", "y": 2}, {"x": "/zh", "y": 1}],
    "referrer": [{"x": "google.com", "y": 1}],
    "channel": [{"x": "direct", "y": 3}, {"x": "organicSearch", "y": 1}],
    "event": [{"x": "generate", "y": 9}, {"x": "copy_success", "y": 1}],
    "country": [{"x": "SG", "y": 2}, {"x": "", "y": 1}],
}


class FakeClient:
    def __init__(self, stats):
        self.stats, self.paths = stats, []

    def request(self, path):
        self.paths.append(path)
        route, _, query = path.partition("?")
        params = dict(urllib.parse.parse_qsl(query))
        if route.endswith("/stats"):
            return self.stats
        if route.endswith("/metrics"):
            return METRICS[params["type"]]
        if route.endswith("/pageviews"):
            return {"pageviews": [{"x": "2026-10-01T00:00:00Z", "y": 5}],
                    "sessions": [{"x": "2026-10-01T00:00:00Z", "y": 4}]}
        raise AssertionError("unexpected request " + path)


class ReportTest(unittest.TestCase):
    def test_umami3_shapes(self):
        client = FakeClient({"pageviews": 5, "visitors": 4, "visits": 4, "bounces": 3, "totaltime": 34,
                             "comparison": {"pageviews": 2, "visitors": 2, "visits": 2, "bounces": 1, "totaltime": 10}})
        result = report.build_report(client, WEBSITE, 0, 7 * report.DAY_MS, limit=1, daily=True)
        self.assertEqual(result["schema"], "site-analytics/report@1")
        self.assertEqual(result["totals"], {"pageviews": 5, "visitors": 4, "visits": 4, "bounces": 3,
                                            "bounce_rate": 0.75, "avg_visit_seconds": 8, "views_per_visit": 1.25})
        self.assertEqual(result["previous_period"]["pageviews"], 2)
        self.assertEqual(result["top"]["pages"], [{"value": "/tools/alpha", "count": 2}])
        self.assertEqual(result["top"]["events"], [{"value": "generate", "count": 9}])
        self.assertEqual(result["daily"], [{"date": "2026-10-01", "pageviews": 5, "visits": 4}])
        self.assertEqual(result["range"]["days"], 7)
        # The page dimension is "path" in Umami 3 ("url" returns HTTP 400).
        self.assertTrue(any("type=path" in path for path in client.paths))
        self.assertFalse(any("type=url" in path for path in client.paths))
        text = report.render(result)
        self.assertIn("pageviews 5 (+150%)", text)
        self.assertIn("generate", text)

    def test_umami2_stats_shape_and_empty_values(self):
        client = FakeClient({"pageviews": {"value": 10, "prev": 5}, "visitors": {"value": 6, "prev": 3},
                             "visits": {"value": 0, "prev": 4}, "bounces": {"value": 0, "prev": 1},
                             "totaltime": {"value": 0, "prev": 9}})
        result = report.build_report(client, WEBSITE, 0, report.DAY_MS, limit=5)
        self.assertEqual(result["totals"]["pageviews"], 10)
        self.assertIsNone(result["totals"]["bounce_rate"])
        self.assertEqual(result["previous_period"]["visits"], 4)
        self.assertEqual(result["top"]["countries"][1], {"value": "(none)", "count": 1})
        self.assertNotIn("daily", result)

    def test_date_range(self):
        start, end = report.date_range(start="2026-10-01", end="2026-10-07")
        self.assertEqual(report.iso(start), "2026-10-01T00:00:00Z")
        self.assertEqual(report.iso(end), "2026-10-07T23:59:59Z")
        now = datetime(2026, 10, 8, tzinfo=timezone.utc)
        start, end = report.date_range(days=7, now=now)
        self.assertEqual(end - start, 7 * report.DAY_MS)
        for bad in ({"start": "2026-10-07", "end": "2026-10-01"}, {"start": "2026-10-01"}, {"days": 0}):
            with self.assertRaises(ValueError):
                report.date_range(**bad)

    def test_date_range_in_a_time_zone(self):
        la = report.zone_for("America/Los_Angeles")
        start, end = report.date_range(start="2026-10-01", end="2026-10-07", zone=la)
        self.assertEqual(report.iso(start), "2026-10-01T07:00:00Z")
        self.assertEqual(report.iso(end), "2026-10-08T06:59:59Z")
        # US daylight saving time ends on 2026-11-01, so that day lasts 25 hours in Los Angeles.
        start, end = report.date_range(start="2026-11-01", end="2026-11-01", zone=la)
        self.assertEqual(end + 1 - start, 25 * 3_600_000)
        with self.assertRaisesRegex(ValueError, "Unknown --timezone"):
            report.zone_for("Mars/Base")

    def test_daily_buckets_and_range_use_the_time_zone(self):
        client = FakeClient({"pageviews": 1, "visitors": 1, "visits": 1, "bounces": 0, "totaltime": 0})
        zone = report.zone_for("America/Los_Angeles")
        start, end = report.date_range(start="2026-10-01", end="2026-10-01", zone=zone)
        result = report.build_report(client, WEBSITE, start, end, daily=True, tz_name="America/Los_Angeles")
        self.assertEqual(result["range"]["timezone"], "America/Los_Angeles")
        self.assertEqual(result["range"]["start"], "2026-10-01T00:00:00-07:00")
        self.assertTrue(any("timezone=America%2FLos_Angeles" in path for path in client.paths if "/pageviews" in path))
        self.assertIn("(America/Los_Angeles, 1.0 days)", report.render(result))

    def test_lookup_never_creates_a_website(self):
        class Api:
            def find(self, domain):
                self.looked_up = domain
                return None

            def ensure(self, *args):
                raise AssertionError("report.py must never create websites")

        class Tool:
            @staticmethod
            def normalize_domain(value):
                return value.lower()

        api = Api()
        with self.assertRaisesRegex(ValueError, "No Umami website for Example.com"):
            report.find_website(api, Tool, domain="Example.com")
        self.assertEqual(api.looked_up, "example.com")


if __name__ == "__main__":
    unittest.main()
