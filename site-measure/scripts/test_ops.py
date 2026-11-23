#!/usr/bin/env python3
"""Tests for ops.py with fake sources and a temporary growth home. All values are synthetic."""
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_measure_ops", HERE / "ops.py")
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)

TODAY = date(2026, 11, 23)


class FakeUmami:
    def __init__(self, days):
        self.days_data = days  # {iso day: {metric: value}}

    def website(self, domain):
        return None if domain == "unregistered.io" else "id-" + domain

    def day(self, website_id, start_ms, end_ms):
        from datetime import datetime, timezone
        first = datetime.fromtimestamp(start_ms / 1000, timezone.utc).date()
        last = datetime.fromtimestamp(end_ms / 1000, timezone.utc).date()
        out = {}
        d = first
        while d <= last:
            for k, v in self.days_data.get(d.isoformat(), {}).items():
                out[k] = out.get(k, 0) + v
            d += timedelta(days=1)
        return out

    def days(self, website_id, first, last):
        out, d = {}, first
        while d <= last:
            if d.isoformat() in self.days_data:
                out[d.isoformat()] = {k: v for k, v in self.days_data[d.isoformat()].items() if k != "visits"}
            d += timedelta(days=1)
        return out


class FakeGsc:
    def property(self, domain, override=None):
        return None if domain == "unregistered.io" else "sc-domain:" + domain

    def sitemaps(self, prop):
        return [{"path": "https://x/sitemap.xml", "lastDownloaded": "2026-11-20T00:00:00Z"}]

    def daily(self, prop, start, end):
        return {(end - timedelta(days=i)).isoformat(): {"clicks": 1, "impressions": 40, "position": 9.5} for i in range(5)}


def traffic(days, visitors=30, generate=20, copy=10, until=TODAY):
    return {(until - timedelta(days=i)).isoformat(): {"pageviews": visitors * 2, "visitors": visitors, "visits": visitors + 3,
                                                       "event:generate": generate, "event:copy_success": copy}
            for i in range(days)}


HOMES = []


def tearDownModule():
    for tmp in HOMES:
        tmp.cleanup()


class Home:
    def __init__(self, sites, spec_by_domain=None):
        self.tmp = tempfile.TemporaryDirectory()
        HOMES.append(self.tmp)
        self.root = Path(self.tmp.name)
        for s in sites:
            project = self.root / s["domain"]
            project.mkdir()
            s["project"] = str(project)
            if spec_by_domain and s["domain"] in spec_by_domain:
                (project / "umami-reports.json").write_text(json.dumps(spec_by_domain[s["domain"]]))
        portfolio = {"schema": ops.PORTFOLIO_SCHEMA, "thresholds": {}, "sites": sites}
        (self.root / "portfolio.json").write_text(json.dumps(portfolio))
        self.portfolio = ops.load_portfolio(self.root)

    def sources(self, umami, gsc=None):
        return ops.Sources(self.root, {"umami": lambda: umami, "gsc": lambda: gsc or FakeGsc(), "bing": None, "cloudflare": None})


class StandardEventsTest(unittest.TestCase):
    def test_guess_from_aliases_and_spec_override(self):
        site = {"types": ["tool"], "sells": True}
        mapping, origin = ops.standard_events(site, None, ["generate", "copy_success", "purchase", "nav_account"])
        self.assertEqual(mapping["core_start"], ["generate"])
        self.assertEqual(mapping["takeaway"], ["copy_success"])
        self.assertEqual(mapping["paid"], ["purchase"])  # kit event, not a tool role
        self.assertEqual(origin["takeaway"], "guess")
        spec_ = {"standard": {"takeaway": ["game_complete"]}, "northStar": "takeaway"}
        mapping, origin = ops.standard_events(site, spec_, ["game_complete"])
        self.assertEqual((mapping["takeaway"], origin["takeaway"]), (["game_complete"], "spec"))
        self.assertEqual(ops.north_star({"types": ["app"]}, None), "core_done")


class LoopTest(unittest.TestCase):
    def test_collect_check_weekly(self):
        home = Home([{"domain": "tools.io", "types": ["tool"], "stage": "validate"},
                     {"domain": "unregistered.io", "types": ["app"], "stage": "validate", "sells": True}],
                    {"tools.io": {"domain": "tools.io", "standard": {"core_start": ["generate"], "core_done": ["generate"],
                                                                     "takeaway": ["copy_success"]}}})
        sources = home.sources(FakeUmami(traffic(40)))
        ops.collect(home.root, home.portfolio, sources, days=40, today=TODAY, log=lambda m: None)
        results = ops.check(home.root, home.portfolio, sources, today=TODAY)
        by = {(r["site"], r["source"], r["item"]): r for r in results}
        self.assertEqual(by[("tools.io", "umami", "website")]["status"], "ok")
        self.assertEqual(by[("tools.io", "umami", "event:takeaway")]["status"], "ok")
        self.assertEqual(by[("tools.io", "gsc", "sitemap")]["status"], "ok")
        self.assertEqual(by[("unregistered.io", "umami", "website")]["status"], "fail")
        self.assertEqual(by[("unregistered.io", "gsc", "property")]["status"], "fail")
        self.assertEqual(by[("unregistered.io", "umami", "event:paid")]["status"], "fail")
        self.assertEqual(by[("tools.io", "bing", "site")]["status"], "nocred")
        report = ops.weekly(home.root, home.portfolio, TODAY - timedelta(days=1))
        site = next(s for s in report["sites"] if s["site"] == "tools.io")
        self.assertEqual(site["north_star"]["value"], 70)  # 7 days x 10 copies
        self.assertEqual(site["visitors"], 210)
        self.assertEqual(site["rates"]["takeaway"], 0.5)
        self.assertEqual(site["bottleneck"][0], "—")
        other = next(s for s in report["sites"] if s["site"] == "unregistered.io")
        self.assertEqual(other["bottleneck"][0], "数据")
        text = ops.render_weekly(report)
        self.assertIn("tools.io", text)
        self.assertIn("数据接入问题", text)

    def test_small_sample_and_demand_bottleneck(self):
        home = Home([{"domain": "tiny.io", "types": ["tool"], "stage": "validate"}])
        sources = home.sources(FakeUmami(traffic(10, visitors=3, generate=2, copy=1)))
        ops.collect(home.root, home.portfolio, sources, days=10, today=TODAY, log=lambda m: None)
        site = ops.weekly(home.root, home.portfolio, TODAY - timedelta(days=1))["sites"][0]
        self.assertIsNone(site["rates"]["use"])  # 21 visitors < 30
        self.assertEqual(site["bottleneck"][0], "需求")

    def test_maintain_suggestion_after_validate_weeks(self):
        home = Home([{"domain": "slow.io", "types": ["tool"], "stage": "validate"}])
        sources = home.sources(FakeUmami(traffic(70, visitors=2, generate=1, copy=0)))
        ops.collect(home.root, home.portfolio, sources, days=70, today=TODAY, log=lambda m: None)
        site = ops.weekly(home.root, home.portfolio, TODAY - timedelta(days=1))["sites"][0]
        self.assertEqual(site["suggest"][0], "maintain")

    def test_guard_event_zero_and_regression(self):
        home = Home([{"domain": "tools.io", "types": ["tool"], "stage": "growth"}])
        days = traffic(20, until=TODAY - timedelta(days=2))
        days[(TODAY - timedelta(days=1)).isoformat()] = {"pageviews": 60, "visitors": 30, "visits": 33,
                                                          "event:generate": 20}  # copy_success stopped
        sources = home.sources(FakeUmami(days))
        ops.collect(home.root, home.portfolio, sources, days=20, today=TODAY, log=lambda m: None)
        ops.check(home.root, home.portfolio, sources, today=TODAY)
        alerts = ops.guard(home.root, home.portfolio, sources, today=TODAY)
        self.assertTrue(any("拿走结果事件昨天为 0" in a for a in alerts), alerts)
        self.assertFalse(any("流量断崖" in a for a in alerts))

    def test_experiments_due(self):
        home = Home([{"domain": "tools.io", "types": ["tool"]}])
        (home.root / "experiments.json").write_text(json.dumps({"items": [
            {"id": "e1", "site": "tools.io", "status": "running", "review": "2026-11-20", "hypothesis": "h"},
            {"id": "e2", "site": "tools.io", "status": "running", "review": "2026-12-20"},
            {"id": "e3", "site": "tools.io", "status": "done", "review": "2026-11-01"}]}))
        running, due = ops.due_experiments(home.root, TODAY)
        self.assertEqual([i["id"] for i in running], ["e1", "e2"])
        self.assertEqual([i["id"] for i in due], ["e1"])


class InitTest(unittest.TestCase):
    def test_discover_and_init_keep_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            (projects / "kitsite").mkdir(parents=True)
            (projects / "kitsite" / ".sitekit.json").write_text(json.dumps({"site": {"domain": "kit.io", "type": "app"}}))
            (projects / "nested" / "site").mkdir(parents=True)
            (projects / "nested" / "site" / ".sitekit.json").write_text(json.dumps({"site": {"domain": "nested.io", "type": "tool"}}))
            (projects / "plain").mkdir()
            (projects / "plain" / "umami.config.json").write_text(json.dumps({"domain": "plain.io"}))
            root = Path(tmp) / "growth"
            added = ops.init(root, projects)
            self.assertEqual(sorted(s["domain"] for s in added), ["kit.io", "nested.io", "plain.io"])
            self.assertTrue(next(s for s in added if s["domain"] == "kit.io")["sells"])
            data = json.loads((root / "portfolio.json").read_text())
            data["sites"][0]["stage"] = "growth"
            (root / "portfolio.json").write_text(json.dumps(data))
            self.assertEqual(ops.init(root, projects), [])
            self.assertEqual(json.loads((root / "portfolio.json").read_text())["sites"][0]["stage"], "growth")
            self.assertIn("data/", (root / ".gitignore").read_text())

    def test_plist_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = ops.schedule(Path(tmp))
            self.assertEqual(len(out), 2)
            self.assertIn("<key>Weekday</key><integer>1</integer>", out[1])


if __name__ == "__main__":
    unittest.main()
