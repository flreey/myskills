#!/usr/bin/env python3
"""Tests for umami_reports.py against the Umami 3.4 funnel and goal routes checked on 2026-11-09. Values are synthetic."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_measure_umami_reports", HERE / "umami_reports.py")
ur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ur)

WEBSITE = {"id": "00000000-0000-4000-8000-000000000001", "name": "Demo", "domain": "demo-site.io"}


def spec_with(**extra):
    base = {"schema": ur.SCHEMA, "domain": "demo-site.io", "todo": [],
            "funnels": [{"name": "Tool", "window": 1440, "steps": ["path:/", "tool_file", "job_end[status=done]"]}],
            "goals": [{"name": "Download", "step": "tool_download"}]}
    base.update(extra)
    return base


class FakeClient:
    def __init__(self, funnels=None, goals=None, events=("tool_file", "job_end"), paths=("/",)):
        self.store = {"funnel": list(funnels or []), "goal": list(goals or [])}
        self.events, self.paths, self.writes = events, paths, []

    def request(self, path, body=None):
        route, _, query = path.partition("?")
        if route.endswith("/metrics"):
            values = self.events if "type=event" in query else self.paths
            return [{"x": v, "y": 1} for v in values]
        parts = route.split("/")
        kind = next(k for k in ("funnel", "goal") if k + "s" in parts)
        tail = parts[parts.index(kind + "s") + 1:]
        if body is not None:
            self.writes.append((route, body))
            if not tail:
                item = dict(body, id=kind + str(len(self.store[kind]) + 1))
                self.store[kind].append(item)
                return item
            item = next(i for i in self.store[kind] if i["id"] == tail[0])
            item.update(body)
            return item
        if tail and tail[-1] == "stats":
            item = next(i for i in self.store[kind] if i["id"] == tail[0])
            if kind == "goal":
                return {"num": 2, "total": 10}
            return [dict(s, visitors=10 - 3 * n) for n, s in enumerate(item["parameters"]["steps"])]
        return {"data": self.store[kind], "count": len(self.store[kind]), "page": 1, "pageSize": 100}


class StepTest(unittest.TestCase):
    def test_step_syntax(self):
        self.assertEqual(ur.parse_step("path:/app"), {"type": "path", "value": "/app"})
        self.assertEqual(ur.parse_step("path:/guides/*"), {"type": "path", "value": "/guides/*"})
        self.assertEqual(ur.parse_step("job_end[status=done;out!=4k]"), {"type": "event", "value": "job_end", "filters": [
            {"property": "status", "operator": "eq", "value": "done"}, {"property": "out", "operator": "neq", "value": "4k"}]})
        self.assertEqual(ur.step_text(ur.parse_step("job_end[status=done]")), "job_end[status=done]")

    def test_steps_umami_cannot_store_are_refused(self):
        for bad in ("a|b", "path:<tool page>", "<tool_done?>", "path:app", "path:/a*b", "bad name", "x[status]", "x[]"):
            with self.assertRaises(ValueError, msg=bad):
                ur.parse_step(bad)
        with self.assertRaises(ValueError):
            ur.parse_step("x[status=done]", allow_filters=False)


class SpecTest(unittest.TestCase):
    def test_todo_blocks_sync(self):
        with self.assertRaisesRegex(ValueError, "todo"):
            ur.desired(spec_with(todo=["pick one of tool_done, tool_preview"]))

    def test_limits(self):
        with self.assertRaisesRegex(ValueError, "2 to 8"):
            ur.desired(spec_with(funnels=[{"name": "One", "steps": ["path:/"]}]))
        with self.assertRaisesRegex(ValueError, "twice"):
            ur.desired(spec_with(goals=[{"name": "G", "step": "a"}, {"name": "G", "step": "b"}]))
        with self.assertRaisesRegex(ValueError, "window"):
            ur.desired(spec_with(funnels=[{"name": "W", "window": 0, "steps": ["path:/", "a"]}]))

    def test_load_spec_checks_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps({"schema": "other", "domain": "x.io"}))
            with self.assertRaisesRegex(ValueError, "schema"):
                ur.load_spec(path)


class SyncTest(unittest.TestCase):
    def test_preview_writes_nothing_and_apply_creates(self):
        client = FakeClient()
        result = ur.plan_sync(client, WEBSITE, ur.desired(spec_with()), seen_days=30, now_ms=10 ** 12)
        self.assertEqual([(a["kind"], a["action"]) for a in result["actions"]], [("funnel", "create"), ("goal", "create")])
        self.assertEqual(client.writes, [])
        self.assertEqual(result["warnings"], ["tool_download not seen in the last 30 days (used by Download)"])
        ur.apply_sync(client, WEBSITE, result)
        route, body = client.writes[0]
        self.assertEqual(route, "/api/websites/" + WEBSITE["id"] + "/funnels")
        self.assertEqual(body["parameters"]["steps"][2]["filters"], [{"property": "status", "operator": "eq", "value": "done"}])
        self.assertEqual(client.writes[1][1]["parameters"], {"type": "event", "value": "tool_download"})

    def test_rerun_is_idempotent_and_unmanaged_reports_stay(self):
        client = FakeClient()
        wanted = ur.desired(spec_with())
        ur.apply_sync(client, WEBSITE, ur.plan_sync(client, WEBSITE, wanted, seen_days=0))
        client.store["goal"].append({"id": "manual", "name": "Made by hand", "parameters": {"type": "path", "value": "/x"}})
        # Umami returns the window as stored; an int vs float window or a missing empty filter list is not a change.
        client.store["funnel"][0]["parameters"]["window"] = 1440.0
        client.writes.clear()
        result = ur.plan_sync(client, WEBSITE, wanted, seen_days=0)
        self.assertEqual([a["action"] for a in result["actions"]], ["unchanged", "unchanged", "unmanaged"])
        ur.apply_sync(client, WEBSITE, result)
        self.assertEqual(client.writes, [])

    def test_changed_steps_update_in_place(self):
        client = FakeClient(funnels=[{"id": "f1", "name": "Tool", "description": "",
                                      "parameters": {"window": 60, "steps": [{"type": "path", "value": "/"}, {"type": "event", "value": "tool_file"}]}}])
        result = ur.plan_sync(client, WEBSITE, ur.desired(spec_with(goals=[])), seen_days=0)
        self.assertEqual(result["actions"][0]["action"], "update")
        ur.apply_sync(client, WEBSITE, result)
        self.assertEqual(client.writes[0][0], "/api/websites/" + WEBSITE["id"] + "/funnels/f1")
        self.assertEqual(client.store["funnel"][0]["parameters"]["window"], 1440)

    def test_wildcards_count_as_seen(self):
        client = FakeClient(paths=("/guides/a",))
        wanted = ur.desired(spec_with(funnels=[{"name": "G", "steps": ["path:/guides/*", "tool_file"]}], goals=[]))
        self.assertEqual(ur.plan_sync(client, WEBSITE, wanted, seen_days=30, now_ms=10 ** 12)["warnings"], [])


class StatusAndDraftTest(unittest.TestCase):
    def test_status_and_funnel_py_command(self):
        client = FakeClient()
        ur.apply_sync(client, WEBSITE, ur.plan_sync(client, WEBSITE, ur.desired(spec_with()), seen_days=0))
        data = ur.status(client, WEBSITE, 0, 1)
        f = data["funnels"][0]
        self.assertEqual([s["visitors"] for s in f["steps"]], [10, 7, 4])
        self.assertEqual(f["funnel_py"], "python3 funnel.py --domain demo-site.io --days 14 --steps 'path:/,tool_file,job_end'")
        self.assertTrue(f["filters_dropped"])
        self.assertEqual(data["goals"][0], {"name": "Download", "step": "tool_download", "num": 2, "total": 10})
        self.assertIn("funnel.py has no field filters", ur.render_status(WEBSITE, data, 0, 1))

    def test_draft_resolves_roles_and_lists_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".sitekit.json").write_text(json.dumps({"site": {"type": "tool", "domain": "demo-site.io"}}))
            (root / "src").mkdir()
            (root / "src" / "Tool.tsx").write_text(
                "track('tool_file', {res});\ntrack('tool_start', {});\ntrack('tool_preview', {});\n"
                "track('tool_done', {});\ntrack('tool_error', {reason});\n")
            d = ur.draft(root)
        self.assertEqual(d["domain"], "demo-site.io")
        self.assertEqual(d["funnels"][0]["steps"], ["path:<tool page>", "tool_file", "tool_start", "tool_done", "<tool_takeaway?>"])
        todo = "\n".join(d["todo"])
        self.assertIn("path:<tool page>", todo)
        self.assertIn("tool_done, tool_preview", todo)
        self.assertIn("no event in the code fills role tool_takeaway", todo)
        with self.assertRaises(ValueError):
            ur.desired(d)


if __name__ == "__main__":
    unittest.main()
