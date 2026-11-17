#!/usr/bin/env python3
"""Tests for geo_idea.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_*.py'"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("geo_idea", HERE / "geo_idea.py")
gi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gi)

DIMS = {
    "dimensions": [
        {"id": "source", "kind": "entity", "changes_answer": True, "why": "method differs", "source": "list",
         "values": [{"id": "heic"}, {"id": "png"}, {"id": "pdf"}]},
        {"id": "target", "kind": "entity", "changes_answer": True, "why": "loss differs", "source": "list",
         "values": [{"id": "jpg"}, {"id": "png"}, {"id": "pdf"}]},
        {"id": "need", "kind": "constraint", "changes_answer": True, "why": "tools differ", "source": "list",
         "values": [{"id": "batch"}, {"id": "offline"}]},
        {"id": "persona", "kind": "entity", "changes_answer": False, "source": "list",
         "values": [{"id": "student"}, {"id": "designer"}]},
    ],
    "exclude": [{"same": ["source", "target"], "why": "no-op"},
                {"when": {"source": "pdf", "need": "offline"}, "why": "out of scope"}],
}


def run(root, *args):
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            gi.main(["--root", str(root), *args])
        except SystemExit as e:
            code = e.code or 0
    return code, out.getvalue()


class GeoIdeaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run(self.root, "init", "--name", "Convert", "--idea", "convert files")
        (self.root / "geo/dimensions.json").write_text(json.dumps(DIMS))

    def tearDown(self):
        self.tmp.cleanup()

    def test_space_counts_after_excludes(self):
        code, out = run(self.root, "space", "--format", "json")
        self.assertEqual(code, 0)
        rep = json.loads(out)
        # 3*3*2 = 18; same source/target hits png->png and pdf->pdf (heic is no target): -4 -> 14;
        # pdf+offline removes pdf->jpg and pdf->png (pdf->pdf already gone): -2 -> 12
        self.assertEqual(rep["product"], 18)
        self.assertEqual(rep["after_excludes"], 12)
        self.assertEqual(rep["described_only"], ["persona"])

    def test_space_rejects_missing_why(self):
        bad = json.loads(json.dumps(DIMS))
        del bad["dimensions"][0]["why"]
        (self.root / "geo/dimensions.json").write_text(json.dumps(bad))
        code, out = run(self.root, "space", "--format", "json")
        self.assertEqual(code, 1)
        self.assertTrue(any("why" in e for e in json.loads(out)["errors"]))

    def test_sample_covers_every_value_and_skips_excluded(self):
        code, out = run(self.root, "sample", "--n", "6")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["uncovered_values"], [])
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        self.assertEqual(len(rows), 6)
        for r in rows:
            self.assertFalse(gi.excluded(r["combo"], DIMS["exclude"]))
            self.assertNotIn("persona", r["combo"])
        self.assertEqual(len({r["combo_id"] for r in rows}), 6)

    def test_sample_refuses_to_overwrite(self):
        run(self.root, "sample", "--n", "4")
        code, _ = run(self.root, "sample", "--n", "4")
        self.assertEqual(code, 2)

    def test_report_levels_and_hint(self):
        run(self.root, "sample", "--n", "4")
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        a, b, c, d = (r["combo_id"] for r in rows)
        runs = [
            {"combo_id": a, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "generic"},
            {"combo_id": a, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "good"},
            {"combo_id": b, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "good"},
            {"combo_id": c, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "weak_sources"},
            {"combo_id": d, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": None},
        ]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", runs)
        code, out = run(self.root, "report", "--threshold", "0.5")
        self.assertEqual(code, 0)
        rep = json.loads((self.root / "geo/gap/report.json").read_text())
        levels = {x["combo_id"]: x["level"] for x in rep["combos"]}
        self.assertEqual(levels[a], "high")      # one high of two runs = half
        self.assertEqual(levels[b], "low")
        self.assertEqual(levels[c], "medium")
        self.assertEqual(levels[d], "unprobed")  # unjudged run ignored
        self.assertEqual(rep["probed"], 3)
        self.assertEqual(rep["hint"], "narrow" if rep["strong_values"] else "stop")
        self.assertTrue((self.root / "geo/gap/report.md").exists())

    def test_decide_requires_owner_and_valid_subspace(self):
        run(self.root, "sample", "--n", "4")
        run(self.root, "report")
        code, _ = run(self.root, "decide", "--verdict", "go", "--by", "user")
        self.assertEqual(code, 2)  # no judged runs yet
        cid = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")[0]["combo_id"]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {"combo_id": cid, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "generic"}])
        run(self.root, "report")
        code, _ = run(self.root, "decide", "--verdict", "go", "--by", "model")
        self.assertEqual(code, 2)
        code, _ = run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"source": ["gif"]}')
        self.assertEqual(code, 2)
        code, _ = run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"source": ["heic"]}')
        self.assertEqual(code, 0)
        proj = json.loads((self.root / "geo/project.json").read_text())
        self.assertEqual(proj["stage"], "decided")
        self.assertEqual(proj["decision"]["subspace"], {"source": ["heic"]})

    def test_extend_opens_values_of_validated_dimensions_only(self):
        run(self.root, "sample", "--n", "4")
        cid = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")[0]["combo_id"]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {"combo_id": cid, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "generic"}])
        run(self.root, "report")
        run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"source": ["heic"]}')
        code, _ = run(self.root, "extend", "--dimension", "source", "--values", "png", "--by", "model")
        self.assertEqual(code, 2)
        code, _ = run(self.root, "extend", "--dimension", "source", "--values", "gif", "--by", "user")
        self.assertEqual(code, 2)  # value not in dimensions.json yet
        code, out = run(self.root, "extend", "--dimension", "source", "--values", "png,heic", "--by", "user")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["added_to_subspace"], ["png"])
        dims = json.loads((self.root / "geo/dimensions.json").read_text())
        dims["dimensions"].append({"id": "engine", "kind": "entity", "changes_answer": True, "why": "api differs",
                                   "source": "list", "values": [{"id": "godot"}]})
        (self.root / "geo/dimensions.json").write_text(json.dumps(dims))
        code, _ = run(self.root, "extend", "--dimension", "engine", "--values", "godot", "--by", "user")
        self.assertEqual(code, 2)  # new dimension needs a gap check
        proj = json.loads((self.root / "geo/project.json").read_text())
        self.assertEqual(proj["decision"]["subspace"], {"source": ["heic", "png"]})
        self.assertEqual(proj["decision"]["dimensions"], ["source", "target", "need"])

    def test_check_flags_bad_runs(self):
        run(self.root, "sample", "--n", "3")
        cid = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")[0]["combo_id"]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {"combo_id": cid, "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "great"},
            {"combo_id": "nope", "platform": "ChatGPT", "date": "2026-11-17", "mode": "manual", "gap": "good"},
        ])
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("gap must be one of", out)
        self.assertIn("is not a sample", out)

    def test_probes_needs_openings(self):
        run(self.root, "sample", "--n", "2")
        code, _ = run(self.root, "probes")
        self.assertEqual(code, 2)
        p = self.root / "geo/gap/samples.jsonl"
        rows = gi.read_jsonl(p)
        for r in rows:
            r["opening"] = "I have 300 HEIC photos..."
            r["follow_ups"] = ["Can it run offline?"]
        gi.write_jsonl(p, rows)
        code, _ = run(self.root, "probes")
        self.assertEqual(code, 0)
        self.assertIn("Follow-up 1", (self.root / "geo/gap/probes.md").read_text())


if __name__ == "__main__":
    unittest.main()
