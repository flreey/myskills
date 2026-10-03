#!/usr/bin/env python3
"""Tests for mapper.py brief, the inputs fingerprint (status stale flags) and sync-check drift.

All data is synthetic: one tool page that owns a "us states" cluster, one neighbour cluster."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_pages_mapper", HERE / "mapper.py")
mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapper)

MARKET = {"country": "US", "language": "en"}
PERIOD = {"start": "2025-09-01", "end": "2026-08-31"}
# keyword -> (planner high or None, attributes)
KEYWORDS = {
    "us states quiz": (50000, {"entity_type": ["states"]}),
    "us states quiz no borders": (500, {"difficulty": ["no borders"]}),
    "us states practice": (500, {"mode": ["practice"]}),
    "50 states typing quiz": (500, {"mode": ["typing"]}),
    "label the us states game": (50, {"mode": ["label"]}),
    "guess the us state": (5000, {"mode": ["guess"]}),
    "seterra us states": (None, {"competitor_brand": ["seterra"]}),
    "how many states are there quiz": (50, {}),
}


def jl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def run(root, *argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        mapper.main(["--root", str(root), *argv])
    return json.loads(out.getvalue())


class BriefTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = root = Path(self.tmp.name)
        seo = root / "seo"
        (seo / "config.json").parent.mkdir(parents=True)
        (seo / "config.json").write_text(json.dumps(
            {"market": MARKET, "mapper": {"brief": {"min_members": 1, "exclude_axes": ["entity_type"]}}}))
        (seo / "boundary.json").write_text(json.dumps({"product": {"url": "https://demo-quiz.io"}}))
        obs, decisions = [], []
        for i, (kw, (vol, attrs)) in enumerate(KEYWORDS.items()):
            o = {"id": f"obs_{i}", "keyword": kw, "source": "google_suggest", "kind": "search_suggestion",
                 "market": MARKET, "period": None, "metrics": {}}
            obs.append(o)
            if vol:
                obs.append(dict(o, id=f"obs_{i}_gkp", source="google_keyword_planner", kind="historical_volume",
                                period=PERIOD, metrics={"avg_monthly_searches": {"low": vol // 10, "high": vol}}))
            decisions.append({"keyword_id": mapper.kw_id(kw), "keyword": kw, "status": "included",
                              "cluster_id": "us_states", "attributes": attrs, "actor": "model",
                              "decided_at": "2026-10-01T00:00:00Z"})
        jl(seo / "discovery" / "observations.jsonl", obs)
        m = seo / "mapper"
        jl(m / "clusters.jsonl", [
            {"id": "us_states", "status": "active", "label": "US states map quiz", "entity": "the 50 US states",
             "page_type": "tool", "intent": {"task": "use_tool", "delivery": "tool"},
             "definition": {"representative_keywords": ["us states quiz"],
                            "excludes": ["state capitals (us_capitals)"], "neighbor_distinction": "capitals differ"}},
            {"id": "us_capitals", "status": "active", "label": "US state capitals quiz", "entity": "state capitals",
             "page_type": "tool", "intent": {"task": "use_tool", "delivery": "tool"}, "definition": {}}])
        jl(m / "decisions.jsonl", decisions)
        jl(m / "pages.jsonl", [
            {"url": "/states-quiz/", "page_type": "tool", "status": "published", "indexable": True,
             "canonical": "/states-quiz/", "title": "States Quiz | Demo",
             "covered_attributes": {"difficulty": ["no borders"], "mode": ["typing"]}},
            {"url": "/capitals-quiz/", "page_type": "tool", "status": "published", "indexable": True,
             "canonical": "/capitals-quiz/", "title": "Capitals Quiz | Demo"}])
        jl(m / "mappings.jsonl", [
            {"cluster_id": "us_states", "page": "/states-quiz/", "role": "primary", "decision": "keep"},
            {"cluster_id": "us_capitals", "page": "/capitals-quiz/", "role": "primary", "decision": "keep"}])
        self.inventory = {"as_of": "2026-10-01", "source": "test", "clusters": {"us_states": {"items": 50, "attrs": {
            "difficulty=no borders": 1, "mode=practice": 1, "mode=typing": 0, "mode=label": 0}}}}
        (m / "inventory.json").write_text(json.dumps(self.inventory))
        (m / "changesets").mkdir()
        (m / "evidence" / "gsc").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def brief(self):
        run(self.root, "brief", "--page", "https://demo-quiz.io/states-quiz")
        return json.loads((self.root / "seo" / "work" / "briefs" / "states-quiz.json").read_text())

    def test_statuses_follow_inventory_and_covered_attributes(self):
        b = self.brief()
        c = b["clusters"][0]
        status = {s["attribute"]: s["status"] for s in c["subneeds"]}
        self.assertEqual(status, {
            "difficulty=no borders": "covered",       # inventory has it, page says so
            "mode=practice": "write_it",              # inventory has it, page silent
            "mode=typing": "unbacked_claim",          # page claims it, inventory says no
            "mode=label": "feature_candidate",        # inventory says no, page silent
            "mode=guess": "unknown",                  # not counted
        })
        self.assertNotIn("entity_type=states", status)  # identity restatement excluded by config
        self.assertEqual([x["name"] for x in c["competitors"]], ["seterra"])
        self.assertEqual(c["questions"], ["how many states are there quiz"])
        self.assertEqual(c["phrasings"][0], {"keyword": "us states quiz", "planner_high": 50000})
        guess = next(s for s in c["subneeds"] if s["attribute"] == "mode=guess")
        self.assertEqual(guess["planner_high"], 5000)
        self.assertEqual([(n["cluster_id"], n["primary_page"]) for n in c["neighbors"]],
                         [("us_capitals", "/capitals-quiz/")])

    def test_status_flags_stale_briefs_after_inventory_change(self):
        self.brief()
        derived = {d["file"]: d for d in run(self.root, "status")["derived"]}
        self.assertFalse(derived["work/briefs/states-quiz.json"]["stale"])
        self.inventory["clusters"]["us_states"]["attrs"]["mode=guess"] = 0
        (self.root / "seo" / "mapper" / "inventory.json").write_text(json.dumps(self.inventory))
        derived = {d["file"]: d for d in run(self.root, "status")["derived"]}
        self.assertEqual(derived["work/briefs/states-quiz.json"]["changed"], ["inventory"])

    def test_derived_file_without_fingerprint_is_stale(self):
        work = self.root / "seo" / "work"
        work.mkdir(parents=True, exist_ok=True)
        (work / "analysis.json").write_text(json.dumps({"generated_at": "2026-10-01T00:00:00Z"}))
        derived = {d["file"]: d for d in run(self.root, "status")["derived"]}
        self.assertTrue(derived["work/analysis.json"]["stale"])

    def test_sync_check_reports_title_drift_and_drafts_a_refresh(self):
        sitemap = self.root / "urls.txt"
        sitemap.write_text("https://demo-quiz.io/states-quiz\nhttps://demo-quiz.io/capitals-quiz\n")
        facts = self.root / "pages.json"
        facts.write_text(json.dumps({"pages": [
            {"url": "/states-quiz", "title": "States Quiz: All 50 | Demo", "pageType": "tool", "indexable": True},
            {"url": "/capitals-quiz", "title": "Capitals Quiz | Demo", "pageType": "tool", "indexable": True}]}))
        out = run(self.root, "sync-check", "--sitemap", str(sitemap), "--pages", str(facts))
        self.assertEqual(out["drift"], {"title": 1})
        draft = json.loads((self.root / "seo" / "work" / "sync-refresh.json").read_text())
        self.assertEqual([(c["url"], c["title"]) for c in draft["changes"]],
                         [("/states-quiz/", "States Quiz: All 50 | Demo")])
        draft["approved_by"] = "test"
        cs = self.root / "cs.json"
        cs.write_text(json.dumps(draft))
        run(self.root, "apply-changes", "--file", str(cs))
        out = run(self.root, "sync-check", "--sitemap", str(sitemap), "--pages", str(facts))
        self.assertEqual(out["drift"], {})
        self.assertFalse((self.root / "seo" / "work" / "sync-refresh.json").exists())
        page =mapper.load_pages(mapper.Paths(str(self.root)))["/states-quiz/"]
        self.assertEqual(page["covered_attributes"], {"difficulty": ["no borders"], "mode": ["typing"]})


if __name__ == "__main__":
    unittest.main()
