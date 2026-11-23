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
        self.events, self.paths, self.writes, self.deleted, self.queries = events, paths, [], [], []
        self.values = {}

    def delete(self, path):
        parts = path.split("/")
        kind = parts[-2][:-1]
        self.deleted.append(path)
        self.store[kind] = [i for i in self.store[kind] if i["id"] != parts[-1]]
        return {"ok": True}

    def request(self, path, body=None):
        route, _, query = path.partition("?")
        if route.endswith("/event-data/values"):
            self.queries.append(query)
            return self.values.get(dict(kv.split("=", 1) for kv in query.split("&"))["propertyName"], [])
        if route.endswith("/metrics"):
            self.queries.append(query)
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
        self.assertEqual(ur.parse_step("path:*-quiz"), {"type": "path", "value": "*-quiz"})
        self.assertEqual(ur.parse_step("job_end[status=done;out!=4k]"), {"type": "event", "value": "job_end", "filters": [
            {"property": "status", "operator": "eq", "value": "done"}, {"property": "out", "operator": "neq", "value": "4k"}]})
        self.assertEqual(ur.step_text(ur.parse_step("job_end[status=done]")), "job_end[status=done]")

    def test_steps_umami_cannot_store_are_refused(self):
        for bad in ("a|b", "path:<tool page>", "<tool_done?>", "path:app", "path:/a*b", "path:*", "path:*a*b", "bad name", "x[status]", "x[]"):
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


def funnel(id_, name, *steps):
    return {"id": id_, "name": name, "description": "", "parameters": {"window": 1440, "steps": [
        {"type": "path", "value": s[5:]} if s.startswith("path:") else {"type": "event", "value": s} for s in steps]}}


class PruneTest(unittest.TestCase):
    def client(self):
        return FakeClient(
            funnels=[funnel("f1", "Tool", "path:/", "tool_file"), funnel("f2", "Old", "path:/", "gone_event"),
                     funnel("f3", "Hand made", "path:/", "job_end"), funnel("f4", "Tool broken", "path:/", "never_sent")],
            goals=[{"id": "g1", "name": "Old", "parameters": {"type": "path", "value": "/retired"}}],
            events=("tool_file", "job_end"), paths=("/",))

    def plan(self, client, spec_names=None):
        if spec_names is None:
            spec_names = {"funnel": {"Tool", "Tool broken"}, "goal": set()}
        return ur.plan_prune(client, WEBSITE, spec_names, days=30, now_ms=10 ** 12)

    def test_verdicts_and_counts(self):
        client = self.client()
        data = self.plan(client)
        got = {(r["kind"], r["name"]): r["verdict"] for r in data["reports"]}
        self.assertEqual(got, {("funnel", "Tool"): "keep", ("funnel", "Tool broken"): "fix",
                               ("funnel", "Old"): "delete", ("funnel", "Hand made"): "review", ("goal", "Old"): "delete"})
        old = next(r for r in data["reports"] if r["id"] == "f2")
        self.assertEqual(old["steps"], [{"step": "path:/", "count": 1}, {"step": "gone_event", "count": 0}])
        # Every path counts, not a top-500 list (sfxmint has thousands of pages).
        self.assertTrue(all("limit=" + str(ur.SEEN_LIMIT) in q for q in client.queries))
        self.assertEqual(client.writes + client.deleted, [])

    def test_without_spec_nothing_is_kept_by_membership(self):
        data = ur.plan_prune(self.client(), WEBSITE, None, days=30, now_ms=10 ** 12)
        self.assertTrue(all(r["in_spec"] is None and r["verdict"] in ("delete", "review") for r in data["reports"]))

    def test_field_filters_count_matching_events_only(self):
        client = FakeClient(funnels=[funnel("f1", "Taxi", "path:/", "job_end")], events=("job_end",))
        client.events = ("job_end",)
        client.store["funnel"][0]["parameters"]["steps"][1]["filters"] = [{"property": "card", "operator": "eq", "value": "taxi"}]
        client.values = {"card": [{"value": "allergy", "total": 12}]}
        r = ur.plan_prune(client, WEBSITE, None, days=30, now_ms=10 ** 12)["reports"][0]
        self.assertEqual((r["steps"][1], r["verdict"]), ({"step": "job_end[card=taxi]", "count": 0}, "delete"))
        self.assertTrue(any("startAt=" + str(10 ** 12 - 30 * 86_400_000) in q for q in client.queries))
        events, values = {"job_end": 20}, [{"value": "taxi", "total": 5}, {"value": "allergy", "total": 12}]
        step = {"type": "event", "value": "job_end", "filters": [{"property": "card", "operator": "neq", "value": "taxi"}]}
        self.assertEqual(ur.step_count(type("C", (), {"request": lambda self, p: values})(), "w", step, events, {}, 10 ** 12, 30, {}), 15)

    def test_wildcard_counts_add_up(self):
        self.assertEqual(ur.seen_count("/guides/*", {"/guides/a": 2, "/guides/b": 3, "/other": 9}), 5)
        self.assertEqual(ur.seen_count("tool_done", {"tool_done_x": 4}), 0)

    def test_deletes_only_named_reports_not_in_spec(self):
        client = self.client()
        data = self.plan(client)
        chosen = ur.pick(data["reports"], ["f2", "goal:Old"])
        text = ur.render_prune(WEBSITE, data, chosen, applied=False)
        self.assertIn("would delete (marked -): funnel:Old, goal:Old", text)
        self.assertEqual(client.deleted, [])
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp) / "b.json"
            ur.apply_prune(client, WEBSITE, chosen, backup)
            saved = json.loads(backup.read_text())["reports"]
        self.assertEqual([(r["kind"], r["id"], r["name"]) for r in saved], [("funnel", "f2", "Old"), ("goal", "g1", "Old")])
        self.assertEqual(saved[0]["parameters"]["steps"][1], {"type": "event", "value": "gone_event"})
        base = "/api/websites/" + WEBSITE["id"]
        self.assertEqual(client.deleted, [base + "/funnels/f2", base + "/goals/g1"])
        self.assertEqual([i["id"] for i in client.store["funnel"]], ["f1", "f3", "f4"])

    def test_refuses_unclear_or_spec_names(self):
        data = self.plan(self.client())
        for bad, why in (("Old", "matches 2"), ("Tool", "in the spec"), ("nope", "no saved report")):
            with self.assertRaisesRegex(ValueError, why, msg=bad):
                ur.pick(data["reports"], [bad])
        self.assertEqual(ur.pick(data["reports"], []), [])

    def test_no_delete_when_the_backup_cannot_be_written(self):
        client = self.client()
        chosen = ur.pick(self.plan(client)["reports"], ["f2"])
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "file"
            blocker.write_text("")
            with self.assertRaises(OSError):
                ur.apply_prune(client, WEBSITE, chosen, blocker / "b.json")
        self.assertEqual(client.deleted, [])


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
