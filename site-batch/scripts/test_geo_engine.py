#!/usr/bin/env python3
"""Tests for geo_engine.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_*.py'"""
import contextlib
import importlib.util
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
