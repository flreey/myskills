#!/usr/bin/env python3
"""Tests for geo_optimize.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_geo_optimize.py'"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("geo_optimize", HERE / "geo_optimize.py")
go = importlib.util.module_from_spec(spec)
spec.loader.exec_module(go)


def run(root, *args):
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            go.main(["--root", str(root), *args])
        except SystemExit as e:
            code = e.code or 0
    return code, out.getvalue()


def cluster(i, **kw):
    c = {"id": f"k{i}", "task": f"task {i}", "query_type": "problem", "lever": "onsite",
         "evidence_level": "signal", "sources": ["site search"]}
    c.update(kw)
    return c


def runs_for(conv, date, n_in, n):
    return [{"conversation_id": conv, "platform": "ChatGPT", "mode": "manual", "date": date,
             "status": "listed" if i < n_in else "absent", "cited_own": i < n_in // 2} for i in range(n)]


class OptimizeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run(self.root, "init")
        self.st = go.State(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_wilson_interval(self):
        lo, hi = go.wilson(45, 150)
        self.assertAlmostEqual(lo, 0.232, places=2)
        self.assertAlmostEqual(hi, 0.377, places=2)
        self.assertIsNone(go.wilson(0, 0))

    def test_sets_are_stable_and_hypotheses_never_measure(self):
        go.write_jsonl(self.st.clusters, [cluster(i) for i in range(40)] + [cluster(99, evidence_level="hypothesis", sources=[])])
        run(self.root, "sets")
        first = {c["id"]: c["set"] for c in go.read_jsonl(self.st.clusters)}
        self.assertEqual(first["k99"], "optimize")
        self.assertTrue({"optimize", "holdout", "sentinel"} <= set(first.values()))
        rows = go.read_jsonl(self.st.clusters) + [cluster(41)]
        go.write_jsonl(self.st.clusters, rows)
        run(self.root, "sets")
        again = {c["id"]: c["set"] for c in go.read_jsonl(self.st.clusters)}
        self.assertTrue(all(again[k] == v for k, v in first.items()))  # existing assignments kept
        self.assertIn("k41", again)

    def test_check_rules(self):
        go.write_jsonl(self.st.clusters, [cluster(1, set="holdout"), cluster(2, set="optimize"),
                                          cluster(3, query_type="vibes", evidence_level="validated", sources=[])])
        go.write_jsonl(self.st.conversations, [{"id": "c1", "cluster": "k1", "opening": "hi"}])
        go.write_jsonl(self.st.runs, [{"conversation_id": "c1", "platform": "ChatGPT", "mode": "manual",
                                       "date": "2026-11-01", "status": "excluded"}])
        go.write_jsonl(self.st.experiments, [{"id": "e1", "change": "x", "shipped": "2026-11-10",
                                              "treatment": ["k2"], "control": ["k1"]}])
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("query_type must be one of", out)
        self.assertIn("validated needs sources", out)
        self.assertIn("excluded needs exclusion.reason", out)
        self.assertIn("holdout cluster k1 cannot be changed", out)

    def test_report_rates_per_set(self):
        go.write_jsonl(self.st.clusters, [cluster(1, set="holdout"), cluster(2, set="optimize")])
        go.write_jsonl(self.st.conversations, [{"id": "c1", "cluster": "k1", "opening": "a"},
                                               {"id": "c2", "cluster": "k2", "opening": "b"}])
        go.write_jsonl(self.st.runs, runs_for("c1", "2026-11-01", 12, 40) + runs_for("c2", "2026-11-01", 5, 10))
        code, out = run(self.root, "report", "--format", "json")
        rep = json.loads(out)
        self.assertEqual(rep["sets"]["holdout"]["n"], 40)
        self.assertEqual(rep["sets"]["holdout"]["in_answer"], 0.3)
        self.assertFalse(rep["sets"]["holdout"]["thin"])
        self.assertTrue(rep["sets"]["optimize"]["thin"])

    def test_experiment_difference_in_differences(self):
        go.write_jsonl(self.st.clusters, [cluster(1, set="optimize"), cluster(2, set="optimize"), cluster(3, set="sentinel")])
        go.write_jsonl(self.st.conversations, [{"id": f"c{i}", "cluster": f"k{i}", "opening": "x"} for i in (1, 2, 3)])
        runs = (runs_for("c1", "2026-10-01", 10, 50) + runs_for("c1", "2026-12-01", 35, 50)
                + runs_for("c2", "2026-10-01", 10, 50) + runs_for("c2", "2026-12-01", 12, 50)
                + runs_for("c3", "2026-10-01", 10, 50) + runs_for("c3", "2026-12-01", 11, 50))
        go.write_jsonl(self.st.runs, runs)
        go.write_jsonl(self.st.experiments, [{"id": "e1", "change": "answer first", "shipped": "2026-11-01",
                                              "recrawled": "2026-11-10", "treatment": ["k1"], "control": ["k2"]}])
        code, out = run(self.root, "experiment", "--id", "e1")
        rep = json.loads(out)
        self.assertAlmostEqual(rep["did_in_answer"]["estimate"], 0.46, places=2)  # (0.7-0.2)-(0.24-0.2)
        self.assertGreater(rep["did_in_answer"]["ci"][0], 0)
        self.assertTrue(rep["verdict"].startswith("improved"))
        self.assertAlmostEqual(rep["sentinel_drift_in_answer"], 0.02, places=2)

    def test_brief_routes_turns_to_sections(self):
        go.write_jsonl(self.st.clusters, [
            cluster(1, primary_page="/sounds/ui-click", constraints=["c-free", "c-loop"]),
            cluster(2, primary_page="/sounds/ui-click/", query_type="recommend", lever="offsite"),
            cluster(3, primary_page="/other")])
        go.write_jsonl(self.st.constraints, [
            {"id": "c-free", "constraint": "free for commercial use", "status": "met", "source": "/license"},
            {"id": "c-loop", "constraint": "seamless loop", "status": "unknown"}])
        go.write_jsonl(self.st.conversations, [
            {"id": "v1", "cluster": "k1", "opening": "subtle tap sounds for my app",
             "follow_ups": [{"q": "Can I use them commercially?", "kind": "constraint"},
                            {"q": "How do I add them in Unity?", "kind": "howto"},
                            {"q": "Better than Kenney?", "kind": "compare"}]},
            {"id": "v2", "cluster": "k1", "opening": "click sounds that don't annoy",
             "follow_ups": [{"q": "can I use them commercially?", "kind": "constraint"}, "plain follow-up"]},
            {"id": "v3", "cluster": "k2", "opening": "best free UI sound packs?"}])
        code, out = run(self.root, "brief", "--page", "/sounds/ui-click")
        self.assertEqual(code, 0)
        b = json.loads((self.st.briefs / "sounds--ui-click.json").read_text())
        self.assertEqual(len(b["clusters"]), 2)
        self.assertEqual(len(b["answer_first"]), 3)
        # constraint questions (deduplicated) and the constraint facts both land in the conditions section
        self.assertEqual([x["q"] for x in b["conditions"] if "q" in x], ["Can I use them commercially?"])
        self.assertEqual([x["id"] for x in b["conditions"] if "id" in x], ["c-free"])
        self.assertEqual(b["unknown_constraints"][0]["id"], "c-loop")
        self.assertEqual(len(b["faq_or_resource"]), 1)
        self.assertEqual(len(b["alternatives"]), 1)
        self.assertEqual(len(b["review"]), 1)                                  # unlabelled follow-up
        self.assertEqual(b["not_this_page"][0]["cluster"], "k2")
        code, _ = run(self.root, "brief", "--page", "/sounds/ui-click")
        self.assertEqual(code, 2)                                              # no silent overwrite

    def test_experiment_thin_and_drift(self):
        go.write_jsonl(self.st.clusters, [cluster(1, set="optimize"), cluster(2, set="optimize"), cluster(3, set="sentinel")])
        go.write_jsonl(self.st.conversations, [{"id": f"c{i}", "cluster": f"k{i}", "opening": "x"} for i in (1, 2, 3)])
        runs = (runs_for("c1", "2026-10-01", 10, 50) + runs_for("c1", "2026-12-01", 35, 50)
                + runs_for("c2", "2026-10-01", 10, 50) + runs_for("c2", "2026-12-01", 12, 50)
                + runs_for("c3", "2026-10-01", 10, 50) + runs_for("c3", "2026-12-01", 30, 50))
        go.write_jsonl(self.st.runs, runs)
        go.write_jsonl(self.st.experiments, [{"id": "e1", "change": "x", "shipped": "2026-11-01",
                                              "treatment": ["k1"], "control": ["k2"]}])
        rep = json.loads(run(self.root, "experiment", "--id", "e1")[1])
        self.assertTrue(rep["verdict"].startswith("no conclusion"))
        go.write_jsonl(self.st.runs, runs_for("c1", "2026-10-01", 2, 5) + runs_for("c1", "2026-12-01", 4, 5)
                       + runs_for("c2", "2026-10-01", 2, 5) + runs_for("c2", "2026-12-01", 2, 5))
        rep = json.loads(run(self.root, "experiment", "--id", "e1")[1])
        self.assertTrue(rep["verdict"].startswith("insufficient"))

    def test_reads_and_selection_losses(self):
        raw = self.root / "geo/optimize/raw"
        raw.mkdir(parents=True)
        (raw / "v1.md").write_text("=== TURN 1 ASSISTANT ===\nx\n=== STREAM URLS ===\n"
                                   "https://www.example.com/pricing?utm_source=chatgpt.com\n"
                                   "https://list.example/top-10/\nhttps://images.openai.com/a.png\n")
        (raw / "v2.md").write_text("no stream here\n")
        go.write_jsonl(self.st.conversations, [{"id": "v1", "cluster": "k1", "opening": "x"}])
        base = {"conversation_id": "v1", "platform": "ChatGPT", "mode": "browser", "date": "2026-11-19"}
        go.write_jsonl(self.st.runs, [
            {**base, "status": "absent", "raw": "geo/optimize/raw/v1.md"},
            {**base, "status": "listed", "status_opening": "first", "raw": "geo/optimize/raw/v2.md"},
        ])
        code, out = run(self.root, "reads", "--own", "example.com")
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertEqual((res["filled"], res["no_stream"], res["opened_not_named"]), (1, 1, 1))
        rows = go.read_jsonl(self.st.runs)
        self.assertEqual(rows[0]["own_read"], ["https://www.example.com/pricing"])
        self.assertEqual(rows[0]["read"], ["https://list.example/top-10"])
        r = go.rates(rows)
        self.assertEqual((r["opened_not_named"], r["dropped_after_follow_up"]), (1, 1))
        go.write_jsonl(self.st.runs, [{**base, "status": "absent", "status_opening": "maybe", "own_read": "x"}])
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("status_opening must be one of", out)
        self.assertIn("own_read is a list of URLs", out)


if __name__ == "__main__":
    unittest.main()
