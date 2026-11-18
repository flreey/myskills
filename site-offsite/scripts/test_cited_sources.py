#!/usr/bin/env python3
"""Tests for cited_sources.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_cited*.py'"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cited_sources", HERE / "cited_sources.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


class CitedSourcesTest(unittest.TestCase):
    def test_groups_by_domain_and_puts_project_absent_first(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "geo/gap").mkdir(parents=True)
            (root / "geo/optimize").mkdir(parents=True)
            runs = [
                {"combo_id": "a", "platform": "ChatGPT", "gap": "generic",
                 "cited": [{"url": "https://www.reddit.com/r/gamedev/x", "type": "forum"},
                           {"url": "https://list.example/best", "type": "list"}]},
                {"combo_id": "b", "platform": "Perplexity", "gap": "good",
                 "cited": [{"url": "https://list.example/best", "type": "list"},
                           {"url": "https://mysite.com/page", "type": "brand"}]},
            ]
            (root / "geo/gap/runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
            (root / "geo/optimize/runs.jsonl").write_text(json.dumps(
                {"cluster": "c1", "platform": "ChatGPT", "gap": "unmet_constraint",
                 "cited": [{"url": "reddit.com/r/sfx", "type": "forum"}]}) + "\n")
            out = cs.aggregate(cs.read_runs(root), ["www.mysite.com"])
            by = {x["domain"]: x for x in out}
            self.assertNotIn("mysite.com", by)
            self.assertEqual((by["reddit.com"]["runs"], by["reddit.com"]["tasks"], by["reddit.com"]["high_gap_runs"]), (2, 2, 2))
            self.assertEqual(by["list.example"]["own_also_cited"], 1)
            self.assertEqual(out[0]["domain"], "reddit.com")  # project absent, widest reach
            self.assertEqual(out[-1]["domain"], "list.example")
            self.assertIn("| reddit.com | 2 | 2 | forum |", cs.to_md(out, 3))

    def test_geo_dirs_and_extra_run_sets(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "geo-longtail/gap").mkdir(parents=True)
            (root / "geo-longtail/gap/runs.jsonl").write_text(json.dumps(
                {"combo_id": "q1", "platform": "ChatGPT", "gap": "generic", "cited": [{"url": "https://a.example/x"}]}) + "\n")
            (root / "geo-longtail/gap/runs-thinking.jsonl").write_text(json.dumps(
                {"combo_id": "q2", "platform": "ChatGPT", "gap": "good", "cited": [{"url": "https://b.example/y"}]}) + "\n")
            self.assertEqual(cs.read_runs(root), [])
            rows = cs.read_runs(root, ["geo-longtail"])
            self.assertEqual(len(rows), 2)
            self.assertEqual({x["domain"] for x in cs.aggregate(rows, [])}, {"a.example", "b.example"})


if __name__ == "__main__":
    unittest.main()
