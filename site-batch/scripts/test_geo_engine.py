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
         "resource": {"label": "Open the converter", "url": f"/tools/{src}-to-{tgt}"},
         "key_facts": [{"label": "Our test", "value": f"{src} to {tgt} sample set", "source": f"own test {src}-{tgt}"}]}
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

    def test_own_evidence_gate(self):
        facts = FACTS + [
            {"id": "f-heic", "value": "HEIC is the iPhone photo format.", "source": "Apple docs", "checked": "2026-11-17", "scope": "source=heic"},
            {"id": "f-jpg", "value": "JPG has no transparency.", "source": "spec", "checked": "2026-11-17", "scope": "target=jpg"},
            {"id": "f-pair", "value": "HEIC to JPG keeps the EXIF date in our test.", "source": "own test", "checked": "2026-11-17",
             "scope": "source=heic;target=jpg"},
            {"id": "f-all", "value": "Everything runs in the browser.", "source": "/docs", "checked": "2026-11-17", "scope": "all"},
        ]
        ge.write_jsonl(self.root / "geo/facts.jsonl", facts)
        # Parent-page facts only: one per dimension value, plus a site-wide one. Thin by construction.
        parent = {"fact_ids": ["f-heic", "f-jpg", "f-all"], "key_facts": [{"label": "Format", "value": "HEIC", "fact_id": "f-heic"}]}
        rows = [row("heic", "jpg", "HEIC photos become JPG files that open anywhere, made on your device.", **parent),
                row("heic", "png", "HEIC photos become PNG files with no further loss at all, made on your device.",
                    fact_ids=["f-heic", "f-all"], key_facts=[{"label": "Format", "value": "HEIC", "fact_id": "f-heic"}])]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        g = self.gates()
        self.assertTrue(any(f.startswith("own evidence 0 < 1") for f in g["heic__jpg"]["gate"]["failed"]))
        self.assertEqual(g["heic__jpg"]["own_evidence"], 0)
        # A fact scoped to the whole combination is this page's own.
        rows[0]["fact_ids"] = ["f-heic", "f-pair"]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        g = self.gates()
        self.assertFalse(any(f.startswith("own evidence") for f in g["heic__jpg"]["gate"]["failed"]))
        self.assertTrue(any(f.startswith("own evidence") for f in g["heic__png"]["gate"]["failed"]))
        # Row data named in evidence_fields counts (a page's own files).
        t = dict(TEMPLATE, evidence_fields=["files"])
        ge.write_json(self.root / "geo/templates/convert.json", t)
        rows[1]["files"] = ["png-sample-1", "png-sample-2"]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        self.assertFalse(any(f.startswith("own evidence") for f in self.gates()["heic__png"]["gate"]["failed"]))
        # Turning it off needs a reason.
        ge.write_json(self.root / "geo/templates/convert.json", dict(TEMPLATE, min_own_evidence=0))
        code, out = run(self.root, "lint")
        self.assertIn("min_own_evidence_why", out)

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
        picked, held = waves["waves"][0]["combos"]["families"], waves["waves"][0]["control"]["families"]
        # Pairs in priority order (heic__jpg, heic__png), (webp__jpg, webp__png): one of each pair on each side.
        for pair in ({"heic__jpg", "heic__png"}, {"webp__jpg", "webp__png"}):
            self.assertEqual(len(pair & set(picked)), 1)
            self.assertEqual(len(pair & set(held)), 1)
        self.assertIn("heic__jpg", picked)   # fixed by the hash for this template and wave
        run(self.root, "wave-release", "--wave", "1", "--date", "2026-10-01")
        run(self.root, "build")
        doc = json.loads((self.root / "geo/out/families.json").read_text())
        self.assertTrue(doc["adopt"])
        live = sorted(inst[c]["url"] for c in picked)
        self.assertEqual(sorted(i["url"] for i in doc["items"]), live)
        self.assertEqual(doc["pending"], 0)   # held-back control rows are not pending
        self.assertEqual(next(i for i in doc["items"] if i["combo_id"] == "heic__jpg")["title"].split(":")[0], "HEIC to JPG")
        self.assertTrue(all(set(i["related_urls"]) <= set(live) for i in doc["items"]))
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

    def test_questions_on_adopt_template_without_collection(self):
        self.adopt_setup()
        ge.write_jsonl(self.root / "geo/gap/samples.jsonl", [
            {"combo_id": "heic__jpg", "combo": {"source": "heic", "target": "jpg"}, "opening": "x",
             "opening_scope": ["source", "target"], "follow_ups": [{"q": "Loop?", "kind": "constraint"}]}])
        code, out = run(self.root, "questions", "--template", "families")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["levels"], {"item": 1})
        code, _ = run(self.root, "scaffold", "--template", "families")
        self.assertEqual(code, 2)   # adopt templates are read by the site's own template, not a kit module
        code, out = run(self.root, "lint")
        self.assertIn("adopt template without diagnosis", out)

    def test_status_groups_reasons_without_numbers(self):
        same = "Exactly the same words on every page about converting images in the browser quickly."
        rows = [row("heic", "jpg", same), row("heic", "png", same + " Also more."), row("webp", "jpg", same + " And so.")]
        for r in rows:
            r["follow_ups"], r["headline"], r["constraint_results"] = [], "same", [{"constraint": "x", "status": "met"}]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        out = json.loads(run(self.root, "status")[1])
        self.assertEqual(list(out["convert"]["failed_by_reason"]), ["unique ratio N < N"])

    def test_shared_text_is_left_out_of_the_unique_ratio(self):
        shared = "All sounds are CC0 and free for commercial use without credit."
        rows = [row(s, t, f"{shared} {s} to {t} keeps its own detail number one.") for s, t in (("heic", "jpg"), ("heic", "png"), ("webp", "jpg"))]
        for r in rows:
            r["follow_ups"], r["headline"] = [], f"{r['combo_id']} head"
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        t = json.loads(json.dumps(TEMPLATE))
        t["min_unique_ratio"] = 0.6
        ge.write_json(self.root / "geo/templates/convert.json", t)
        before = self.gates()["heic__jpg"]["unique_ratio"]
        t["shared_text"] = [shared]
        ge.write_json(self.root / "geo/templates/convert.json", t)
        after = self.gates()["heic__jpg"]["unique_ratio"]
        self.assertGreater(after, before)

    def test_assets_gate_and_queue(self):
        rows = json.loads(json.dumps(COMBOS))
        rows[0]["assets"] = [{"id": "a1", "kind": "sound", "status": "to_generate", "brief": "metal footsteps on stairs"},
                             {"id": "a2", "kind": "sound", "status": "ready"}]
        rows[1]["assets"] = [{"id": "a3", "status": "maybe"}]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        g = self.gates()
        self.assertIn("assets not ready: 1 to_generate", g["heic__jpg"]["gate"]["failed"])
        self.assertTrue(any("has status 'maybe'" in f for f in g["heic__png"]["gate"]["failed"]))
        out = json.loads(run(self.root, "assets")[1])["convert"]
        self.assertEqual(out["rows_waiting"], 2)
        self.assertEqual(out["queue"][0]["assets"][0]["brief"], "metal footsteps on stairs")
        self.assertEqual(json.loads(run(self.root, "status")[1])["convert"]["assets_pending"], 2)

    def test_hidden_key_facts_source_numbers_but_stay_off_the_page(self):
        rows = COMBOS[:2] + [row("webp", "jpg", "WebP to JPG: pick the 3 files named below.",
                                 key_facts=[{"label": "files", "value": "3", "source": "computed from catalog", "hidden": True}])]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        self.assertTrue(self.gates()["webp__jpg"]["gate"]["pass"])
        data = {d["combo_id"]: d for d in ge.read_jsonl(self.root / "data/convert.jsonl")}
        self.assertNotIn("files", [f["label"] for f in data["webp__jpg"]["facts"]])

    def test_slot_when_limits_required_slots(self):
        t = json.loads(json.dumps(TEMPLATE))
        t["question_slots"] = [{"id": "loop", "question": "Does it loop?", "kind": "constraint", "when": {"source": "webp"}}]
        ge.write_json(self.root / "geo/templates/convert.json", t)
        g = self.gates()
        self.assertTrue(g["heic__jpg"]["gate"]["pass"], g["heic__jpg"]["gate"])
        self.assertIn("unanswered question slots ['loop']", g["webp__jpg"]["gate"]["failed"])
        t["question_slots"][0]["when"] = {"colour": "red"}
        ge.write_json(self.root / "geo/templates/convert.json", t)
        self.assertIn("not a template dimension", run(self.root, "lint")[1])

    def test_rows_can_name_related_combinations(self):
        rows = json.loads(json.dumps(COMBOS))
        rows[0]["related"] = ["webp__jpg", "nope"]
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        run(self.root, "build", "--target", "kit")
        data = {d["combo_id"]: d for d in ge.read_jsonl(self.root / "data/convert.jsonl")}
        self.assertEqual(data["heic__jpg"]["related"], ["webp-to-jpg"])

    def test_preview_renders_one_row_without_touching_waves(self):
        run(self.root, "build", "--target", "json")
        before = (self.root / "geo/instances.jsonl").read_text()
        code, out = run(self.root, "build", "--target", "json", "--preview", "convert:heic__jpg")
        self.assertEqual(code, 0)
        doc = json.loads((self.root / "geo/out/preview/convert.json").read_text())
        self.assertEqual([i["combo_id"] for i in doc["items"]], ["heic__jpg"])
        self.assertFalse((self.root / "geo/waves.json").exists())
        self.assertEqual((self.root / "geo/instances.jsonl").read_text(), before)
        code, _ = run(self.root, "build", "--preview", "convert:webp__png")
        self.assertEqual(code, 2)   # failing rows cannot be previewed as pages

    def test_deployed_date_drives_prune_and_baselines_are_summed(self):
        rows = json.loads(json.dumps(COMBOS))
        for i, r in enumerate(rows):
            r["baseline"], r["priority"] = {"ai_landings": 10 * (i + 1)}, 5 - i
        ge.write_jsonl(self.root / "geo/combos/convert.jsonl", rows)
        run(self.root, "build")
        code, out = run(self.root, "wave-plan", "--per-template", "1", "--control-ratio", "0.5")
        plan = json.loads(out)
        self.assertEqual(plan["sizes"], {"convert": 1})
        b = plan["baseline"]["convert"]
        self.assertEqual(sorted([b["wave"]["ai_landings"], b["control"]["ai_landings"]]), [10.0, 20.0])
        out = json.loads(run(self.root, "wave-release", "--wave", "1", "--date", "2026-10-01")[1])
        self.assertIn("wave-deployed", out["next"])
        code, _ = run(self.root, "wave-deployed", "--wave", "1", "--date", "2026-11-01")
        self.assertEqual(code, 0)
        run(self.root, "build")
        live = [i for i in ge.read_jsonl(self.root / "geo/instances.jsonl") if i["released"]]
        self.assertEqual(live[0]["deployed_on"], "2026-11-01")
        ge.write_jsonl(self.root / "geo/measure/snapshots.jsonl", [
            {"date": "2026-11-15", "url": live[0]["url"], "crawled": True, "indexed": False}])
        cands = json.loads(run(self.root, "prune", "--min-days", "28", "--today", "2026-11-17")[1])["candidates"]
        self.assertEqual(cands, [])   # 16 days since the deploy, though 47 since release

    def test_geo_dir(self):
        (self.root / "geo").rename(self.root / "geo-families")
        code, out = run(self.root, "--geo-dir", "geo-families", "build", "--target", "kit")
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "geo-families/instances.jsonl").exists())

    def test_geo_dir_json_output_stays_in_its_folder(self):
        (self.root / "geo").rename(self.root / "geo-find")
        (self.root / "geo").mkdir()
        (self.root / "geo/out").mkdir()
        (self.root / "geo/out/index.json").write_text('{"other": true}')
        code, out = run(self.root, "--geo-dir", "geo-find", "build", "--target", "json")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / "geo-find/out/convert.json").exists())
        self.assertEqual(json.loads((self.root / "geo/out/index.json").read_text()), {"other": True})

    def test_unapproved_template_cannot_be_planned_or_released(self):
        ge.write_json(self.root / "geo/templates/convert.json", dict(TEMPLATE, approved=None))
        code, _ = run(self.root, "wave-plan", "--per-template", "1")
        self.assertEqual(code, 2)
        ge.write_json(self.root / "geo/templates/convert.json", TEMPLATE)
        self.assertEqual(run(self.root, "wave-plan", "--per-template", "1")[0], 0)
        ge.write_json(self.root / "geo/templates/convert.json", dict(TEMPLATE, approved=None))
        self.assertEqual(run(self.root, "wave-release", "--wave", "1")[0], 2)

    def test_questions_on_the_bank_route_match_by_need(self):
        ge.write_json(self.root / "geo/project.json",
                      dict(PROJECT, decision={"verdict": "narrow", "by": "user", "subspace": {"need": ["n-safe"]}}))
        ge.write_jsonl(self.root / "geo/gap/samples.jsonl", [
            {"combo_id": "q1", "question_id": "q1", "need_id": "n-safe", "combo": {}, "opening": "can I ship it?",
             "follow_ups": [{"q": "credit needed?", "kind": "constraint"}]},
            {"combo_id": "q2", "question_id": "q2", "need_id": "n-fit", "combo": {}, "opening": "loop it?"}])
        code, out = run(self.root, "questions", "--template", "convert")
        self.assertEqual(code, 0, out)
        rep = json.loads(out)
        self.assertEqual((rep["samples"], rep["matched_by"]), (1, "need"))

    def test_snapshot_titles_are_unescaped(self):
        self.assertEqual(ge.page_summary("<title>Cats &amp; Dogs</title><h1>A &#39;b&#39;</h1>")["title"], "Cats & Dogs")

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

    def test_snapshot_keeps_index_when_interrupted_and_resumes(self):
        self.adopt_setup()

        class H(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = f"<html><head><title>Old {self.path}</title></head><body><h1>Old</h1></body></html>".encode()
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)

        srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        idx_path = self.root / "geo/snapshots/families/index.jsonl"
        real, calls = ge.page_summary, []

        def stop_on_third(html):
            calls.append(1)
            if len(calls) == 3:
                raise KeyboardInterrupt                      # e.g. a background time limit kills the run
            return real(html)

        ge.page_summary = stop_on_third
        try:
            with self.assertRaises(KeyboardInterrupt):
                run(self.root, "snapshot", "--template", "families", "--base", base, "--delay", "0")
            ge.page_summary = real
            first = ge.read_jsonl(idx_path)
            self.assertEqual(len(first), 2)                  # pages saved before the interruption stay indexed
            rep = json.loads(run(self.root, "snapshot", "--template", "families", "--base", base, "--delay", "0")[1])
        finally:
            ge.page_summary = real
            srv.shutdown()
        saved_first = {r["url"] for r in first}
        rows = [r for r in ge.read_jsonl(self.root / "geo/combos/families.jsonl") if r.get("url")]
        self.assertEqual(rep["skipped"], sum(r["url"] in saved_first for r in rows))   # already saved today
        self.assertEqual(rep["saved"] + rep["skipped"], len(rows))
        urls = {r["url"] for r in ge.read_jsonl(idx_path)}
        self.assertEqual(urls, {r["url"] for r in rows})     # every page ends up indexed

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
