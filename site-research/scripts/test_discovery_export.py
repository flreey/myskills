#!/usr/bin/env python3
"""Tests for discovery.py export: Search Console impressions are never added across periods or exports.

All data is synthetic."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_keywords_discovery", HERE / "discovery.py")
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def run(root, *argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        discovery.main(["--root", str(root), *argv])
    return json.loads(out.getvalue())


class ExportTest(unittest.TestCase):
    def test_gsc_impressions_are_the_latest_period_and_largest_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run(root, "init")
            market = {"country": "ALL", "language": "und"}

            def gsc(i, start, end, impressions):
                return {"id": f"obs_{i}", "keyword": "us states quiz", "source": "google_search_console",
                        "kind": "gsc_impression", "market": market, "period": {"start": start, "end": end},
                        "metrics": {"impressions": impressions}, "run": 1}

            rows = [gsc(1, "2026-09-01", "2026-09-28", 50),   # older window
                    gsc(2, "2026-09-29", "2026-10-26", 30),   # query export
                    gsc(3, "2026-09-29", "2026-10-26", 45)]   # query+page export of the same window
            (root / "seo" / "discovery" / "observations.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            out = root / "keywords.csv"
            run(root, "export", "--out", str(out))
            with out.open(encoding="utf-8") as fh:
                row = next(csv.DictReader(fh))
            self.assertEqual(row["gsc_impressions"], "45")
            self.assertEqual(row["gsc_period"], "2026-09-29..2026-10-26")


if __name__ == "__main__":
    unittest.main()
