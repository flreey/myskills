#!/usr/bin/env python3
"""Tests for funnel.py against Umami 3.4 response shapes checked on 2026-11-09. All values are synthetic."""
import importlib.util
from pathlib import Path
import unittest
import urllib.parse

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_measure_funnel", HERE / "funnel.py")
funnel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(funnel)

WEBSITE = {"id": "00000000-0000-4000-8000-000000000001", "name": "Demo", "domain": "demo-site.io"}
OWNER = "aaaaaaaa-0000-4000-8000-000000000001"
A, B, C = ("bbbbbbbb-0000-4000-8000-00000000000" + str(i) for i in (1, 2, 3))
SESSIONS = [
    {"id": OWNER, "screen": "1440x900", "city": "Testville", "country": "US", "device": "laptop", "browser": "chrome",
     "os": "Mac OS", "visits": 5, "views": 40, "events": 9, "firstAt": "2026-11-01T00:00:00Z", "lastAt": "2026-11-02T00:00:00Z"},
    {"id": A, "screen": "390x844", "city": "Paris", "country": "FR", "device": "mobile", "views": 2, "events": 3},
    {"id": B, "screen": "1920x1080", "city": "Berlin", "country": "DE", "device": "desktop", "views": 1, "events": 2},
    {"id": C, "screen": "1920x1080", "city": "Berlin", "country": "DE", "device": "desktop", "views": 1, "events": 0},
]


def ev(n, session, minute, name=None, path="/", data=None):
    return {"id": "e" + str(n), "sessionId": session, "createdAt": "2026-11-01T10:%02d:00Z" % minute, "urlPath": path,
            "eventType": 2 if name else 1, "eventName": name, "hasData": bool(data), "_data": data or {}}


EVENTS = [
    # Owner: the whole funnel, which must disappear once excluded.
    ev(1, OWNER, 0), ev(2, OWNER, 1, "tool_file", data={"res": "480p"}), ev(3, OWNER, 2, "tool_start"),
    ev(4, OWNER, 3, "tool_done", data={"seconds": 900}), ev(5, OWNER, 4, "tool_download"),
    # A: page view, file, start, done (no download).
    ev(6, A, 0), ev(7, A, 1, "tool_file", data={"res": "720p"}), ev(8, A, 2, "tool_start"),
    ev(9, A, 4, "tool_done", data={"seconds": 20}),
    # B: done before file (out of order), so the ordered funnel stops at step 1.
    ev(10, B, 0), ev(11, B, 1, "tool_done", data={"seconds": 40}), ev(12, B, 2, "tool_file", data={"res": "720p"}),
    # C: page view only, on another page.
    ev(13, C, 0, path="/guides/x"),
]


class FakeClient:
    def __init__(self, page_size=None):
        self.paths = []

    def request(self, path):
        self.paths.append(path)
        route, _, query = path.partition("?")
        params = dict(urllib.parse.parse_qsl(query))
        if route.endswith("/sessions"):
            return self.page(SESSIONS, params)
        if route.endswith("/events"):
            return self.page([{k: v for k, v in e.items() if k != "_data"} for e in EVENTS], params)
        if "/event-data/" in route and not route.endswith(("/properties", "/values")):
            event = next(e for e in EVENTS if e["id"] == route.rsplit("/", 1)[1])
            return [{"eventId": event["id"], "eventName": event["eventName"], "dataKey": k,
                     "stringValue": None if isinstance(v, int) else v, "numberValue": v if isinstance(v, int) else None,
                     "dataType": 2 if isinstance(v, int) else 1} for k, v in event["_data"].items()]
        if route.endswith("/event-data/properties"):
            return [{"eventName": "tool_done", "propertyName": "seconds", "dataType": 2, "total": 3}]
        if route.endswith("/event-data/values"):
            return [{"value": "20", "total": 1}, {"value": "40", "total": 1}, {"value": "900", "total": 1}]
        raise AssertionError("unexpected request " + path)

    @staticmethod
    def page(rows, params):
        page, size = int(params["page"]), int(params["pageSize"])
        return {"data": rows[(page - 1) * size:page * size], "count": len(rows), "page": page, "pageSize": size, "isCapped": False}


STEPS = funnel.parse_steps("path:/,tool_file,tool_start|tool_full,tool_done,tool_download")


class FunnelTest(unittest.TestCase):
    def test_ordered_funnel_with_owner_excluded(self):
        result = funnel.build(FakeClient(), WEBSITE, 0, 1, steps=STEPS, rules={"screen": ["1440x900"]})
        self.assertEqual(result["schema"], "site-measure/funnel@1")
        self.assertEqual(result["sessions"], {"all": 4, "excluded": 1, "kept": 3, "by_rule": {"screen 1440x900": 1}})
        rows = result["funnels"][0]["rows"]
        # B gives a file after its page view but was "done" before that, so it stops at step 2.
        self.assertEqual([r["sessions"] for r in rows], [2, 2, 1, 1, 0])
        self.assertEqual([r["any_order"] for r in rows], [2, 2, 1, 2, 0])
        self.assertEqual(rows[2]["from_previous"], 0.5)
        self.assertEqual(rows[3]["from_first"], 0.5)
        self.assertEqual(rows[3]["median_seconds_from_first"], 240)
        self.assertNotIn(OWNER[:8], funnel.render(result))  # no session ids unless asked

    def test_without_exclusions_the_owner_counts(self):
        rows = funnel.build(FakeClient(), WEBSITE, 0, 1, steps=STEPS)["funnels"][0]["rows"]
        self.assertEqual([r["sessions"] for r in rows], [3, 3, 2, 2, 1])

    def test_exclusion_rules(self):
        hits = funnel.excluded_sessions(SESSIONS, {"session": [OWNER[:8]], "city": ["berlin"], "country": ["fr"]})
        self.assertEqual(set(hits), {OWNER, A, B, C})
        self.assertEqual(hits[B], ["city berlin"])
        with self.assertRaisesRegex(ValueError, "at least 8"):
            funnel.excluded_sessions(SESSIONS, {"session": ["aaaa"]})

    def test_paths_and_prefixes(self):
        steps = funnel.parse_steps("path:/guides/*,tool_file")
        rows = funnel.funnel([{k: v for k, v in e.items()} for e in EVENTS], steps)
        self.assertEqual(rows[0]["sessions"], 1)
        with self.assertRaisesRegex(ValueError, "at least two"):
            funnel.parse_steps("tool_file")

    def test_plan_funnel_maps_aliases(self):
        result = funnel.build(FakeClient(), WEBSITE, 0, 1, plans=["tool"], rules={"session": [OWNER]})
        f = result["funnels"][0]
        self.assertEqual(f["name"], "plan tool")
        labels = [r["step"] for r in f["rows"]]
        self.assertEqual(labels[0], "any page view")
        self.assertEqual(labels[1], "tool_input (tool_file)")
        self.assertEqual(labels[4], "tool_takeaway (tool_download)")
        self.assertEqual([r["sessions"] for r in f["rows"]], [3, 2, 1, 1, 0])

    def test_fields_per_event_respect_exclusions(self):
        result = funnel.build(FakeClient(), WEBSITE, 0, 1, rules={"screen": ["1440x900"]}, fields=True)
        by = {(f["event"], f["field"]): f for f in result["fields"]["fields"]}
        self.assertEqual(by[("tool_done", "seconds")]["numbers"]["max"], 40)
        self.assertEqual(by[("tool_done", "seconds")]["numbers"]["median"], 30)
        self.assertEqual(by[("tool_file", "res")]["values"], [{"value": "720p", "count": 2}])
        self.assertIn("exclusions applied", result["fields"]["source"])

    def test_field_filter_and_server_fallback(self):
        client = FakeClient()
        result = funnel.build(client, WEBSITE, 0, 1, wanted=["tool_done.seconds"], max_fetch=1)
        self.assertIn("exclusions NOT applied", result["fields"]["source"])
        self.assertEqual(result["fields"]["fields"][0]["numbers"]["n"], 3)
        self.assertTrue(any("/event-data/values" in p and "propertyName=seconds" in p for p in client.paths))
        only = funnel.build(FakeClient(), WEBSITE, 0, 1, wanted=["tool_done.seconds"])
        self.assertEqual([(f["event"], f["field"]) for f in only["fields"]["fields"]], [("tool_done", "seconds")])

    def test_spread_and_sessions_list(self):
        self.assertEqual(funnel.spread([1, 2, 3, 4]), {"n": 4, "min": 1, "p25": 1.75, "median": 2.5, "p75": 3.25,
                                                      "p90": 3.7, "max": 4, "mean": 2.5})
        self.assertIsNone(funnel.spread([]))
        result = funnel.build(FakeClient(), WEBSITE, 0, 1, rules={"screen": ["1440x900"]}, list_sessions=2)
        busy = result["busiest_sessions"]
        self.assertEqual(busy[0]["id"], OWNER[:8])
        self.assertTrue(busy[0]["excluded"])
        self.assertIn("x aaaaaaaa", funnel.render(result))

    def test_paging(self):
        old = funnel.PAGE_SIZE
        funnel.PAGE_SIZE = 5
        try:
            client = FakeClient()
            result = funnel.build(client, WEBSITE, 0, 1)
            self.assertEqual(result["events"]["all"], len(EVENTS))
            self.assertEqual(sum(1 for p in client.paths if "/events?" in p), 3)
        finally:
            funnel.PAGE_SIZE = old


if __name__ == "__main__":
    unittest.main()
