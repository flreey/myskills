#!/usr/bin/env python3
"""Tests for probe_run_to_raw.py."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe_run_to_raw", HERE / "probe_run_to_raw.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DATA = {
    "turns": [{"id": "q1", "turn": 2, "q": "follow", "answer": "second"},
              {"id": "q1", "turn": 1, "q": "open", "answer": "first"},
              {"id": "q2", "turn": 1, "q": "open2", "answer": None}],
    "per": {"q1": {"search_queries": ["a b"], "stream_urls": ["https://x.example"]}, "q2": {"search_queries": [], "stream_urls": []}},
    "meta": {"q1": {"unpers": "Unpersonalized", "model": "Instant", "err": None}, "q2": {"err": "turn timeout"}},
}


class ConvertTest(unittest.TestCase):
    def test_writes_format_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            lines = mod.convert(DATA, d, "2026-11-18")
            self.assertIn("q1: 2 turns, 11 chars, 1 queries, ok", lines[0])
            self.assertIn("check:", lines[1])
            text = (Path(d) / "q1--chatgpt-instant--1.md").read_text()
            self.assertTrue(text.startswith("platform: ChatGPT via browser script\nslice: chatgpt-instant"))
            self.assertLess(text.index("=== TURN 1 USER ==="), text.index("=== TURN 2 ASSISTANT ==="))
            self.assertIn('=== SEARCH QUERIES ===\n["a b"]', text)
            self.assertIn("=== STREAM URLS ===\nhttps://x.example", text)
            (Path(d) / "q1--chatgpt-instant--1.md").write_text("keep")
            self.assertIn("skipped", mod.convert(DATA, d, "2026-11-18")[0])
            self.assertEqual((Path(d) / "q1--chatgpt-instant--1.md").read_text(), "keep")
            self.assertIn("q1: 2 turns", mod.convert(DATA, d, "2026-11-18", run=2)[0])
            self.assertIn("run: 2", (Path(d) / "q1--chatgpt-instant--2.md").read_text())


if __name__ == "__main__":
    unittest.main()
