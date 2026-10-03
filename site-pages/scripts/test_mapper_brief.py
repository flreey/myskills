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


class Fixture(unittest.TestCase):
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


class BriefTest(Fixture):
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


class GscStoreTest(Fixture):
    """Search Console rows live once, in mapper/evidence/gsc; analyze, brief and review read them there."""

    def import_api_rows(self):
        api = self.root / "gsc.json"
        api.write_text(json.dumps({"dimensions": ["query", "page"], "rows": [
            {"keys": ["us states quiz", "https://demo-quiz.io/states-quiz"], "clicks": 5, "impressions": 100,
             "ctr": 0.05, "position": 8.2},
            {"keys": ["us states quiz", "https://demo-quiz.io/capitals-quiz"], "clicks": 0, "impressions": 40,
             "ctr": 0.0, "position": 30.1},
            {"keys": ["guess the us state", "https://demo-quiz.io/states-quiz"], "clicks": 1, "impressions": 30,
             "ctr": 0.033, "position": 12.0},
            {"keys": ["world map quiz", "https://demo-quiz.io/states-quiz"], "clicks": 0, "impressions": 20,
             "ctr": 0.0, "position": 40.0},
            {"keys": ["world map quiz", "https://demo-quiz.io/capitals-quiz"], "clicks": 0, "impressions": 15,
             "ctr": 0.0, "position": 45.0}]}))
        return run(self.root, "gsc", "import", "--file", str(api), "--period", "2026-10-02..2026-10-29")

    def test_api_rows_import_with_page_and_percent_ctr(self):
        out = self.import_api_rows()
        self.assertEqual((out["rows"], out["added"], out["note"]), (5, 5, None))
        rows = mapper.read_jsonl(self.root / "seo" / "mapper" / "evidence" / "gsc" / "2026-10-02_2026-10-29.jsonl")
        first = rows[0]
        self.assertEqual((first["query"], first["page"], first["ctr"]), ("us states quiz", "demo-quiz.io/states-quiz", 5.0))
        self.assertEqual(self.import_api_rows()["added"], 0)  # re-import adds nothing

    def test_analyze_and_brief_read_the_mapper_store_without_summing_pages(self):
        self.import_api_rows()
        run(self.root, "analyze")
        analysis = json.loads((self.root / "seo" / "work" / "analysis.json").read_text())
        demand = next(c for c in analysis["clusters"] if c["cluster_id"] == "us_states")["demand"]
        # us states quiz: largest page row 100 (not 100 + 40); guess the us state: 30
        self.assertEqual(demand["gsc_impressions_latest_sum"], 130)
        self.assertEqual(demand["gsc_source"], "mapper/evidence/gsc")
        b = self.brief()
        guess = next(s for s in b["clusters"][0]["subneeds"] if s["attribute"] == "mode=guess")
        self.assertEqual(guess["gsc_impressions"], 30)
        self.assertEqual([q["query"] for q in b["gsc"]["queries"]], ["us states quiz", "guess the us state",
                                                                      "world map quiz"])
        self.assertFalse(b["gsc"]["queries"][2]["owned_here"])

    def test_review_writes_unmapped_queries_that_discovery_imports(self):
        self.import_api_rows()
        run(self.root, "gsc", "review")
        data = json.loads((self.root / "seo" / "work" / "unmapped-queries.json").read_text())
        self.assertEqual([(o["keyword"], o["metrics"]["impressions"]) for o in data["observations"]],
                         [("world map quiz", 20)])
        dspec = importlib.util.spec_from_file_location(
            "site_keywords_discovery", HERE.parent.parent / "site-keywords" / "scripts" / "discovery.py")
        discovery = importlib.util.module_from_spec(dspec)
        dspec.loader.exec_module(discovery)

        class Args:
            kind = period = None

        rows = discovery.import_json(self.root / "seo" / "work" / "unmapped-queries.json", Args())
        self.assertEqual([(r[0], r[1], r[3]) for r in rows],
                         [("world map quiz", "gsc_impression", {"start": "2026-10-02", "end": "2026-10-29"})])


if __name__ == "__main__":
    unittest.main()
