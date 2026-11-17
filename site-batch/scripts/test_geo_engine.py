#!/usr/bin/env python3
"""Tests for geo_engine.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_*.py'"""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import threading
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("geo_engine", HERE / "geo_engine.py")
ge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ge)

PROJECT = {"schema": 1, "name": "Convert", "idea": "convert files", "stage": "blueprint",
           "decision": {"verdict": "narrow", "by": "user", "subspace": {"source": ["heic", "webp"]}}}
DIMS = {"dimensions": [
    {"id": "source", "kind": "entity", "changes_answer": True, "why": "x", "source": "s",
     "values": [{"id": "heic", "label": "HEIC"}, {"id": "webp", "label": "WebP"}, {"id": "pdf", "label": "PDF"}]},
    {"id": "target", "kind": "entity", "changes_answer": True, "why": "x", "source": "s",
     "values": [{"id": "jpg", "label": "JPG"}, {"id": "png", "label": "PNG"}]},
]}
FACTS = [
    {"id": "f1", "value": "The converter handles up to 500 files per batch in the browser.", "source": "/docs/limits", "checked": "2026-11-17"},
    {"id": "f2", "value": "JPG output at quality 92 keeps EXIF dates.", "source": "own test 2026-11-16", "checked": "2026-11-16"},
]
TEMPLATE = {
    "id": "convert", "task": "convert {source} to {target}", "dimensions": ["source", "target"],
    "collection": {"basePath": "/convert", "label": {"singular": "Conversion", "plural": "Conversions"},
                   "hub": {"title": "All conversions", "description": "Every format conversion we cover."},
                   "groups": {"by": "source", "basePath": "/convert/from", "label": "Source", "minItems": 1,
                              "intro": "{count} ways to convert {name} files."},
                   "itemType": "Thing"},
    "patterns": {"slug": "{source}-to-{target}", "name": "{source.label} to {target.label}",
                 "title": "{source.label} to {target.label}: {headline}", "h1": "Convert {source.label} to {target.label}",
                 "description": "How to convert {source.label} to {target.label} in the browser, with what you lose and what is kept."},
    "required": ["core_answer", "constraint_results"], "min_unique_ratio": 0.3,
    "experiment": {"name": "answer-order", "arms": ["a", "b"]},
    "allow_numbers": ["1"],
    "approved": {"by": "user", "date": "2026-11-17"}, "version": 1,
}


def row(src, tgt, answer, **kw):
    r = {"combo_id": f"{src}__{tgt}", "combo": {"source": src, "target": tgt}, "headline": f"{src} {tgt} guide",
         "core_answer": answer, "fact_ids": ["f1", "f2"],
         "constraint_results": [{"constraint": "No upload", "status": "met", "note": f"{src} stays on your device"}],
         "follow_ups": [{"q": f"Does {src} keep dates?", "a": "Yes, EXIF dates are kept at quality 92."}],
         "resource": {"label": "Open the converter", "url": f"/tools/{src}-to-{tgt}"}}
    r.update(kw)
    return r


COMBOS = [
    row("heic", "jpg", "HEIC photos from an iPhone become JPG in the browser, up to 500 files per batch, dates kept."),
    row("heic", "png", "HEIC to PNG is lossless here but files grow; transparency is not part of HEIC photos."),
    row("webp", "jpg", "WebP images flatten to JPG; animated WebP keeps only frame 1 and loses transparency."),
    row("webp", "png", "WebP to PNG keeps transparency and animation is dropped.", constraint_results=[]),  # missing required
    row("pdf", "jpg", "PDF pages render to JPG one image per page at a fixed resolution."),  # outside subspace
]


def run(root, *args):
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            ge.main(["--root", str(root), *args])
        except SystemExit as e:
            code = e.code or 0
    return code, out.getvalue()


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        ge.write_json(r / "geo/project.json", PROJECT)
        ge.write_json(r / "geo/dimensions.json", DIMS)
        ge.write_jsonl(r / "geo/facts.jsonl", FACTS)
        ge.write_json(r / "geo/templates/convert.json", TEMPLATE)
        ge.write_jsonl(r / "geo/combos/convert.jsonl", COMBOS)

    def tearDown(self):
        self.tmp.cleanup()

    def gates(self):
        run(self.root, "build", "--target", "kit")
        return {i["combo_id"]: i for i in ge.read_jsonl(self.root / "geo/instances.jsonl")}

    def test_gate_reasons(self):
        g = self.gates()
        self.assertTrue(g["heic__jpg"]["gate"]["pass"], g["heic__jpg"]["gate"])
        self.assertTrue(g["heic__png"]["gate"]["pass"])
        self.assertIn("missing constraint_results", g["webp__png"]["gate"]["failed"])
        self.assertIn("outside the decided subspace", g["pdf__jpg"]["gate"]["failed"])

    def test_unsourced_number_and_unknown_fact(self):
        rows = COMBOS[:2] + [row("webp", "jpg", "WebP converts to JPG in 3 seconds.", fact_ids=["f1", "f9"])]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        failed = self.gates()["webp__jpg"]["gate"]["failed"]
        self.assertTrue(any("unknown fact ids" in f for f in failed))
        self.assertTrue(any("numbers not in cited facts" in f and "3" in f for f in failed))

    def test_unknown_constraint_and_duplicate_text(self):
        same = "Exactly the same words on every page about converting images in the browser quickly."
        rows = [row("heic", "jpg", same), row("heic", "png", same),
                row("webp", "jpg", "Unique words here.", constraint_results=[{"constraint": "Offline", "status": "unknown"}])]
        for r in rows:
            r["follow_ups"], r["constraint_results"] = [], r["constraint_results"] if r["combo_id"] == "webp__jpg" else [{"constraint": "x", "status": "met"}]
            r["headline"] = "same"
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        g = self.gates()
        self.assertTrue(any("unique ratio" in f for f in g["heic__jpg"]["gate"]["failed"]))
        self.assertTrue(any("is unknown" in f for f in g["webp__jpg"]["gate"]["failed"]))

    def test_build_writes_kit_rows_with_related_and_groups(self):
        run(self.root, "build", "--target", "kit")
        data = {d["slug"]: d for d in ge.read_jsonl(self.root / "data/convert.jsonl")}
        self.assertEqual(set(data), {"heic-to-jpg", "heic-to-png", "webp-to-jpg"})
        d = data["heic-to-jpg"]
        self.assertEqual(d["title"], "HEIC to JPG: heic jpg guide")
        self.assertEqual(d["group"], {"key": "heic", "name": "HEIC"})
        self.assertEqual(d["related"], ["webp-to-jpg", "heic-to-png"])  # differ in source first, then target
        self.assertEqual(d["facts"][0], {"label": "No upload", "value": "Yes — heic stays on your device"})
        self.assertFalse(d["released"])
        self.assertIn(d["arm"], ("a", "b"))
        self.assertEqual(d["resource"]["url"], "/tools/heic-to-jpg")

    def test_waves_plan_release_and_build(self):
        run(self.root, "build", "--target", "kit")
        code, out = run(self.root, "wave-plan", "--per-template", "2")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["sizes"], {"convert": 2})
        code, _ = run(self.root, "wave-plan", "--per-template", "2")
        self.assertEqual(code, 2)  # a planned wave is open
        run(self.root, "wave-release", "--wave", "1", "--date", "2026-10-01")
        run(self.root, "build", "--target", "kit")
        data = ge.read_jsonl(self.root / "data/convert.jsonl")
        self.assertEqual(sum(d["released"] for d in data), 2)
        code, out = run(self.root, "wave-plan", "--per-template", "5")
        self.assertEqual(json.loads(out)["sizes"], {"convert": 1})  # only the last gated row is left

    def test_funnel_and_prune(self):
        run(self.root, "build")
        run(self.root, "wave-plan", "--per-template", "3")
        run(self.root, "wave-release", "--wave", "1", "--date", "2026-10-01")
        run(self.root, "build")
        ge.write_jsonl(self.root / "geo/measure/snapshots.jsonl", [
            {"date": "2026-10-20", "url": "/convert/heic-to-jpg", "crawled": True, "indexed": False},
            {"date": "2026-11-10", "url": "/convert/heic-to-jpg", "crawled": True, "indexed": True, "ai_fetch": True, "referrals": 4},
            {"date": "2026-11-10", "url": "/convert/heic-to-png", "crawled": True, "indexed": False, "ai_fetch": False},
        ])
        code, out = run(self.root, "funnel")
        self.assertEqual(code, 0)
        allrow = next(r for r in json.loads(out) if r["wave"] == "all" and r["arm"] == "all")
        self.assertEqual((allrow["released"], allrow["measured"], allrow["indexed"], allrow["referrals"]), (3, 2, 0.5, 4))
        code, out = run(self.root, "prune", "--min-days", "28", "--today", "2026-11-17")
        self.assertEqual([c["url"] for c in json.loads(out)["candidates"]], ["/convert/heic-to-png"])

    def test_scaffold_writes_module_override_and_entry(self):
        code, out = run(self.root, "scaffold", "--template", "convert")
        self.assertEqual(code, 0)
        rep = json.loads(out)
        mod = (self.root / "src/site/collections/convert.ts").read_text()
        self.assertIn("defineCollection<Row>", mod)
        self.assertIn("groupIntro", mod)
        self.assertTrue((self.root / "src/site/overrides/templates/DirectoryItem.astro").exists())
        self.assertEqual(rep["site_config_entry"]["ungated"], "omit")
        self.assertEqual(rep["site_config_entry"]["groups"]["basePath"], "/convert/from")

    def test_variants_follow_the_arm_and_stage_advances(self):
        rows = [dict(r, variants={"b": {"core_answer": r["core_answer"] + " Variant B wording."}}) for r in COMBOS[:3]]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        run(self.root, "build", "--target", "kit")
        for d in ge.read_jsonl(self.root / "data/convert.jsonl"):
            self.assertEqual(d["answer"].endswith("Variant B wording."), d["arm"] == "b")
        self.assertEqual(json.loads((self.root / "geo/project.json").read_text())["stage"], "blueprint")
        run(self.root, "wave-plan", "--per-template", "1")
        run(self.root, "wave-release", "--wave", "1")
        self.assertEqual(json.loads((self.root / "geo/project.json").read_text())["stage"], "pages")

    def test_json_target_for_non_kit_sites(self):
        run(self.root, "build")  # no .sitekit.json: json target by default
        self.assertFalse((self.root / "data/convert.jsonl").exists())
        doc = json.loads((self.root / "geo/out/convert.json").read_text())
        self.assertEqual((doc["items"], doc["pending"]), ([], 3))
        run(self.root, "wave-plan", "--per-template", "2")
        run(self.root, "wave-release", "--wave", "1")
        run(self.root, "build")
        doc = json.loads((self.root / "geo/out/convert.json").read_text())
        slugs = {i["slug"] for i in doc["items"]}
        self.assertEqual(len(slugs), 2)
        for i in doc["items"]:
            self.assertTrue(i["url"].startswith("/convert/"))
            self.assertTrue(set(i["related"]) <= slugs)  # never links an unreleased page
            self.assertNotIn("released", i)
        self.assertEqual(doc["pending"], 1)
        self.assertEqual(doc["groups"][0]["url"], "/convert/from/heic")
        idx = json.loads((self.root / "geo/out/index.json").read_text())
        self.assertEqual(idx["templates"][0]["items"], 2)
        self.assertEqual(len((self.root / "geo/out/urls.txt").read_text().split()), 2)

    def test_kit_target_when_site_kit(self):
        (self.root / ".sitekit.json").write_text("{}")
        run(self.root, "build")
        self.assertTrue((self.root / "data/convert.jsonl").exists())
        self.assertFalse((self.root / "geo/out").exists())

    def test_lint_rejects_dimension_outside_gap_check(self):
        ge.write_json(self.root / "geo/project.json", dict(PROJECT, decision=dict(PROJECT["decision"], dimensions=["source"])))
        code, out = run(self.root, "lint")
        self.assertEqual(code, 1)
        self.assertIn("'target' was not part of the gap check", out)

    def test_question_slots_gate(self):
        t = dict(TEMPLATE, question_slots=[
            {"id": "keeps-dates", "question": "Does it keep photo dates?", "kind": "constraint"},
            {"id": "offline", "question": "Does it work offline?", "kind": "constraint", "required": False}])
        ge.write_json(self.root / "geo/templates/convert.json", t)
        rows = [row("heic", "jpg", "HEIC to JPG in the browser, up to 500 files, dates kept."),
                row("heic", "png", "HEIC to PNG keeps every pixel but the files grow larger."),
                row("webp", "jpg", "WebP flattens to JPG and loses transparency on the way.")]
        rows[0]["follow_ups"][0]["slot"] = "keeps-dates"                       # answered as a follow-up
        rows[1]["constraint_results"][0]["slot"] = "keeps-dates"               # answered in the table
        rows[2]["follow_ups"][0]["slot"] = "battery"                           # unknown slot
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        g = self.gates()
        self.assertTrue(g["heic__jpg"]["gate"]["pass"], g["heic__jpg"]["gate"])
        self.assertTrue(g["heic__png"]["gate"]["pass"], g["heic__png"]["gate"])
        failed = g["webp__jpg"]["gate"]["failed"]
        self.assertTrue(any("unknown question slots" in f for f in failed))
        self.assertTrue(any("unanswered question slots ['keeps-dates']" in f for f in failed))

    def test_group_content_kit_and_json(self):
        ge.write_jsonl(self.root / "geo/combos/convert.groups.jsonl", [
            {"key": "heic", "answer": "iPhone photos are HEIC; convert them in the browser, up to 500 at a time.",
             "fact_ids": ["f1"],
             "chooser": [{"when": "a site only takes JPG", "slug": "heic-to-jpg", "why": "smallest files"},
                         {"when": "you need lossless", "slug": "heic-to-png"}],
             "follow_ups": [{"q": "Why are my photos HEIC?", "a": "iPhones save HEIC by default."}]},
            {"key": "webp", "answer": "WebP converts in 3 seconds.", "chooser": []},     # unsourced number
            {"key": "heic-x", "answer": "x"},                                           # unknown value
        ])
        run(self.root, "build", "--target", "kit")
        run(self.root, "wave-plan", "--per-template", "1")                          # releases heic-to-jpg only
        run(self.root, "wave-release", "--wave", "1")
        code, out = run(self.root, "build", "--target", "kit")
        summary = json.loads(out)["convert"]
        self.assertIn("webp", summary["group_failures"])
        self.assertIn("heic-x", summary["group_failures"])
        groups = json.loads((self.root / "data/convert.groups.json").read_text())
        self.assertEqual(list(groups), ["heic"])
        self.assertEqual([c["slug"] for c in groups["heic"]["chooser"]], ["heic-to-jpg"])  # unreleased choice dropped
        self.assertEqual(groups["heic"]["chooser"][0]["url"], "/convert/heic-to-jpg")
        run(self.root, "build", "--target", "json")
        doc = json.loads((self.root / "geo/out/convert.json").read_text())
        self.assertEqual(doc["groups"][0]["content"]["follow_ups"][0]["q"], "Why are my photos HEIC?")

    def test_questions_routes_openings_by_scope(self):
        ge.write_jsonl(self.root / "geo/gap/samples.jsonl", [
            {"combo_id": "heic__jpg", "combo": {"source": "heic", "target": "jpg"}, "opening": "upload fails with iPhone photos",
             "opening_scope": ["source"], "follow_ups": [{"q": "does it keep dates?", "kind": "constraint", "adds": []},
                                                         {"q": "how do I do it on Windows?", "kind": "howto"}]},
            {"combo_id": "webp__png", "combo": {"source": "webp", "target": "png"}, "opening": "turn webp into png",
             "opening_scope": ["source", "target"], "follow_ups": ["is it free?"]},
            {"combo_id": "pdf__jpg", "combo": {"source": "pdf", "target": "jpg"}, "opening": "best converter?",
             "opening_scope": [], "follow_ups": []},
        ])
        code, out = run(self.root, "questions", "--template", "convert")
        self.assertEqual(code, 0)
        rep = json.loads(out)
        self.assertEqual(rep["levels"], {"group": 1, "item": 1, "hub": 1})
        self.assertEqual(len(rep["follow_ups_by_kind"]["constraint"]), 1)
        self.assertIn("unlabelled", rep["follow_ups_by_kind"])
        self.assertEqual(ge.route_level([], TEMPLATE), "hub")

    def test_section_labels(self):
        run(self.root, "build", "--target", "kit")
        self.assertEqual(json.loads((self.root / "data/convert.labels.json").read_text())["chooser"], "Which one fits")
        ge.write_json(self.root / "geo/templates/convert.json", dict(TEMPLATE, labels={"chooser": "怎么选", "alternatives": "其他做法"}))
        run(self.root, "build", "--target", "kit")
        self.assertEqual(json.loads((self.root / "data/convert.labels.json").read_text()),
                         {"chooser": "怎么选", "alternatives": "其他做法"})
        run(self.root, "build", "--target", "json")
        self.assertEqual(json.loads((self.root / "geo/out/convert.json").read_text())["collection"]["labels"]["alternatives"], "其他做法")
        ge.write_json(self.root / "geo/templates/convert.json", dict(TEMPLATE, labels={"faq": "问题", "chooser": " "}))
        code, out = run(self.root, "lint")
        self.assertIn("labels.faq is not a label", out)
        self.assertIn("labels.chooser must be non-empty", out)

    def test_scaffold_writes_both_overrides(self):
        code, out = run(self.root, "scaffold", "--template", "convert")
        self.assertEqual(len(json.loads(out)["overrides_written"]), 2)
        self.assertTrue((self.root / "src/site/overrides/templates/DirectoryGroup.astro").exists())

    def adopt_setup(self):
        t = {"id": "families", "adopt": True, "task": "find {source} sounds", "dimensions": ["source", "target"],
             "required": ["core_answer"], "min_unique_ratio": 0.2, "approved": {"by": "user", "date": "2026-11-17"},
             "patterns": {"title": "{source.label} to {target.label}: {headline}"}}
        ge.write_json(self.root / "geo/templates/families.json", t)
        rows = []
        for i, (src, tgt) in enumerate([("heic", "jpg"), ("heic", "png"), ("webp", "jpg"), ("webp", "png")]):
            r = row(src, tgt, f"Answer {'abcd'[i]} about {src} and {tgt} with its own wording, variant {'wxyz'[i]}.", url=f"/sounds/{src}-{tgt}",
                    priority=4 - i)
            r["fact_ids"], r["follow_ups"] = ["f1"], []
            r["constraint_results"][0]["note"] = f"{src} {tgt} note"
            rows.append(r)
        rows.append(row("heic", "jpg", "Duplicate url row.", url="/sounds/heic-jpg", combo_id="heic__jpg2"))
        rows.append(row("webp", "jpg", "No url row.", combo_id="webp__jpg2"))
        ge.write_jsonl(self.root / "geo/combos/families.jsonl", rows)
        (self.root / "geo/templates/convert.json").unlink()

    def test_adopt_rows_keep_their_urls_and_output_json(self):
        self.adopt_setup()
        (self.root / ".sitekit.json").write_text("{}")          # even on a kit site, adopt goes to JSON
        code, out = run(self.root, "lint")
        self.assertNotIn("collection.basePath is required", out)
        run(self.root, "build")
        inst = {i["combo_id"]: i for i in ge.read_jsonl(self.root / "geo/instances.jsonl")}
        self.assertEqual(inst["heic__jpg"]["url"], "/sounds/heic-jpg")
        self.assertTrue(inst["heic__jpg"]["gate"]["pass"], inst["heic__jpg"]["gate"])
        self.assertIn("duplicate url", inst["heic__jpg2"]["gate"]["failed"])
        self.assertTrue(any("adopt rows need url" in f for f in inst["webp__jpg2"]["gate"]["failed"]))
        self.assertFalse((self.root / "data/families.jsonl").exists())
        run(self.root, "wave-plan", "--per-template", "2", "--control-ratio", "0.5")
        waves = json.loads((self.root / "geo/waves.json").read_text())
        self.assertEqual(waves["waves"][0]["combos"]["families"], ["heic__jpg", "webp__jpg"])   # 1st and 3rd by priority
        self.assertEqual(waves["waves"][0]["control"]["families"], ["heic__png", "webp__png"])  # 2nd and 4th held back
        run(self.root, "wave-release", "--wave", "1", "--date", "2026-10-01")
        run(self.root, "build")
        doc = json.loads((self.root / "geo/out/families.json").read_text())
        self.assertTrue(doc["adopt"])
        self.assertEqual(sorted(i["url"] for i in doc["items"]), ["/sounds/heic-jpg", "/sounds/webp-jpg"])
        self.assertEqual(doc["items"][0]["title"].split(":")[0], "HEIC to JPG")
        self.assertTrue(all(set(i["related_urls"]) <= {"/sounds/heic-jpg", "/sounds/webp-jpg"} for i in doc["items"]))
        code, out = run(self.root, "wave-plan", "--per-template", "5")
        self.assertEqual(code, 2)                                   # only control rows left, held back
        code, out = run(self.root, "wave-plan", "--per-template", "5", "--include-control")
        self.assertEqual(json.loads(out)["sizes"], {"families": 2})
        ge.write_jsonl(self.root / "geo/measure/snapshots.jsonl", [
            {"date": "2026-11-01", "url": "/sounds/heic-jpg", "cited": True},
            {"date": "2026-11-01", "url": "/sounds/heic-png", "cited": False}])
        rows = json.loads(run(self.root, "funnel")[1])
        ctrl = next(r for r in rows if r["arm"] == "control")
        self.assertEqual((ctrl["wave"], ctrl["released"], ctrl["cited"]), ("wave 1", 2, 0.0))

    def test_snapshot_saves_live_html(self):
        self.adopt_setup()

        class H(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/sounds/webp-png":
                    self.send_response(404); self.end_headers(); return
                body = f"<html><head><title>Old {self.path}</title></head><body><h1>Old page</h1><p>a b c</p></body></html>".encode()
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)

        srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            code, out = run(self.root, "snapshot", "--template", "families", "--base",
                            f"http://127.0.0.1:{srv.server_address[1]}", "--delay", "0")
        finally:
            srv.shutdown()
        rep = json.loads(out)
        self.assertEqual((rep["saved"], rep["failed"]), (4, 1))   # 5 rows with urls (one duplicate), one 404
        idx = ge.read_jsonl(self.root / "geo/snapshots/families/index.jsonl")
        ok = next(r for r in idx if r["url"] == "/sounds/heic-png")
        self.assertEqual((ok["status"], ok["title"], ok["h1"]), (200, "Old /sounds/heic-png", "Old page"))
        self.assertTrue((self.root / ok["file"]).exists())
        code, _ = run(self.root, "snapshot", "--template", "nope", "--base", "http://x")
        self.assertEqual(code, 2)

    def test_lint_requires_decision_and_valid_template(self):
        bad = dict(TEMPLATE, patterns=dict(TEMPLATE["patterns"], slug="{source}"))
        ge.write_json(self.root / "geo/templates/convert.json", bad)
        ge.write_json(self.root / "geo/project.json", dict(PROJECT, decision=None))
        code, out = run(self.root, "lint")
        self.assertEqual(code, 1)
        self.assertIn("no go or narrow decision", out)
        self.assertIn("patterns.slug must contain every dimension", out)


if __name__ == "__main__":
    unittest.main()
