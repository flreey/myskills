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
         "assets": {"needs": "a converter run per pair", "have": 3, "source": "converter list"},
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


def ready_to_decide(root, levers=None, geo="geo"):
    """Meet the decision gates: task space checked, need x channel table with a lever per need."""
    run(root, "--geo-dir", geo, "space")
    rows = "".join(f"| {nid}: x | not probed | not measured | not measured | {lv} | |\n" for nid, lv in (levers or {}).items())
    (root / geo / "gap").mkdir(parents=True, exist_ok=True)
    (root / geo / "gap/channels.md").write_text(
        "| Need | Assistant chat | Search engines | Agents / API / MCP | Lever | Owner's note |\n"
        "| --- | --- | --- | --- | --- | --- |\n" + rows)


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

    def test_sample_tags_a_share_of_tool_seeking_openings(self):
        code, out = run(self.root, "sample", "--n", "9")
        self.assertEqual(json.loads(out)["angles"], {"problem": 6, "recommend": 3})
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        self.assertEqual([r["angle"] for r in rows].count("recommend"), 3)
        self.assertEqual(run(self.root, "sample", "--n", "4", "--force", "--tool-share", "1.5")[0], 2)
        run(self.root, "sample", "--n", "4", "--force", "--tool-share", "0")
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        self.assertEqual({r["angle"] for r in rows}, {"problem"})
        code, out = run(self.root, "check")
        self.assertIn("asks for a tool, site or app", out)    # WARN, not an error
        self.assertEqual(code, 0)

    def test_decide_with_the_site_absent_needs_the_owners_reason(self):
        run(self.root, "sample", "--n", "6")
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        base = {"platform": "ChatGPT", "date": "2026-11-18", "mode": "browser", "web_search": False}
        runs = [{**base, "combo_id": r["combo_id"], "gap": "generic",
                 "own": "listed" if r["angle"] == "recommend" and i == 0 else "absent"} for i, r in enumerate(rows)]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", runs)
        run(self.root, "report")
        rep = gi.read_json(self.root / "geo/gap/report.json")
        self.assertIn("recommend", rep["groups"]["angle"])     # presence is reported per angle
        ready_to_decide(self.root, {"n-a": "pages"})
        code, _ = run(self.root, "decide", "--verdict", "go", "--by", "user")
        self.assertEqual(code, 2)
        self.assertEqual(run(self.root, "decide", "--verdict", "stop", "--by", "user")[0], 0)  # stop needs no reason
        code, _ = run(self.root, "decide", "--verdict", "go", "--by", "user", "--note", "first wave of 18 as a test")
        self.assertEqual(code, 0)
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [{**r, "own": "first"} for r in runs])
        run(self.root, "report")
        self.assertEqual(run(self.root, "decide", "--verdict", "go", "--by", "user")[0], 0)  # picked: no reason needed

    def test_capability_space_leans_on_tool_seeking_openings(self):
        dims = json.loads(json.dumps(DIMS))
        dims["dimensions"][0]["kind"] = "capability"
        (self.root / "geo/dimensions.json").write_text(json.dumps(dims))
        code, out = run(self.root, "space", "--format", "json")
        self.assertEqual(json.loads(out)["shape"], "capability")
        self.assertEqual(gi.read_json(self.root / "geo/project.json")["space"]["shape"], "capability")
        code, out = run(self.root, "sample", "--n", "9")
        self.assertEqual(json.loads(out)["angles"], {"problem": 3, "recommend": 6})
        del dims["dimensions"][0]["assets"]
        (self.root / "geo/dimensions.json").write_text(json.dumps(dims))
        code, out = run(self.root, "space", "--format", "json")
        self.assertTrue(any("capability dimension states no assets" in w for w in json.loads(out)["warnings"]))

    def test_queries_split_find_searches_from_named_checks(self):
        run(self.root, "sample", "--n", "4")
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        base = {"platform": "ChatGPT", "date": "2026-11-18", "mode": "browser", "web_search": True, "gap": "generic"}
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {**base, "combo_id": rows[0]["combo_id"], "own": "first", "search_queries": [
                "free online heic to jpg converter no upload 2026", "heic to jpg converter free no upload browser",
                "Convert heic limits pricing"]},
            {**base, "combo_id": rows[1]["combo_id"], "own": "absent", "search_queries": [
                "CloudConvert heic jpg free limits", "site:cloudconvert.com heic to jpg", "iPhone Photos export JPG official",
                "Zamzar heic converter pricing"]},
        ])
        gi.write_jsonl(self.root / "geo/gap/runs-website.jsonl", [
            {**base, "combo_id": rows[2]["combo_id"], "own": "absent", "search_queries": ["batch pdf to png converter offline"]}])
        gi.write_jsonl(self.root / "geo/competitors.jsonl", [{"id": "zamzar", "name": "Zamzar", "domain": "zamzar.com", "kind": "tool"}])
        code, out = run(self.root, "queries")
        self.assertEqual(code, 0, out)
        q = gi.read_jsonl(self.root / "geo/gap/queries.jsonl")
        find = [r for r in q if r["kind"] == "find"]
        self.assertEqual(len(find), 2)                       # the two heic searches are one cluster
        heic = next(r for r in find if "heic" in r["key"])
        self.assertEqual(heic["n"], 2)
        self.assertEqual(heic["own_in_answer"], 1.0)
        named = {r["label"]: r for r in q if r["kind"] != "find"}
        self.assertEqual(named["Convert"]["kind"], "own")    # the project name: the assistant checking us
        self.assertEqual(named["CloudConvert"]["n"], 2)      # CloudConvert and cloudconvert.com are one
        self.assertIn("Photos", named)                       # iPhone is a platform word, not a candidate
        self.assertEqual(named["Zamzar"]["kind"], "named")   # a listed competitor is not us
        self.assertIn("Named checks", (self.root / "geo/gap/queries.md").read_text())
        rows_q = gi.read_jsonl(self.root / "geo/gap/queries.jsonl")
        i = next(n for n, r in enumerate(rows_q) if r["key"] == heic["key"])
        rows_q[i]["rank"] = {"engine": "bing", "date": "2026-11-19", "ours": 3, "url": "https://x/heic",
                             "winners": ["cloudconvert.com"], "source": "bing.com manual"}
        gi.write_jsonl(self.root / "geo/gap/queries.jsonl", rows_q)
        run(self.root, "queries")
        kept = next(r for r in gi.read_jsonl(self.root / "geo/gap/queries.jsonl") if r["key"] == heic["key"])
        self.assertEqual(kept["rank"]["ours"], 3)            # filled ranks survive a rerun
        rows_q[i]["rank"] = {"engine": "bing", "ours": 0, "winners_kind": "big"}
        gi.write_jsonl(self.root / "geo/gap/queries.jsonl", rows_q)
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("rank needs date", out)
        self.assertIn("rank.ours is our position", out)
        self.assertIn("winners_kind is dedicated", out)

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
        ready_to_decide(self.root)
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
        ready_to_decide(self.root)
        self.assertEqual(run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"source": ["heic"]}')[0], 0)
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

    def test_check_flags_bad_turn_kind_and_scope(self):
        run(self.root, "sample", "--n", "2")
        p = self.root / "geo/gap/samples.jsonl"
        rows = gi.read_jsonl(p)
        rows[0]["opening_scope"] = ["colour"]
        rows[0]["follow_ups"] = [{"q": "Is it free?", "kind": "price"}, "plain strings still allowed"]
        gi.write_jsonl(p, rows)
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("opening_scope names unknown dimension", out)
        self.assertIn("follow-up kind must be one of", out)

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
            r["opening_scope"] = ["source"]
            r["follow_ups"] = [{"q": "Can it run offline?", "kind": "constraint", "adds": ["need"]}]
        gi.write_jsonl(p, rows)
        code, _ = run(self.root, "probes")
        self.assertEqual(code, 0)
        self.assertIn("Follow-up 1", (self.root / "geo/gap/probes.md").read_text())


NEEDS = [
    {"id": "n-safe", "need": "use sounds in a commercial game without claims", "personas": ["indie game dev"],
     "where_asked": ["assistant", "forum"], "evidence_level": "validated", "count": 111,
     "evidence": [{"source": "forum", "url": "https://www.reddit.com/r/gamedev/x", "quote": "100% copyright free sounds"},
                  {"source": "site_search", "ref": "search_log 2026-09-18..11-17", "q": "cc0 gunshot", "n": 9}]},
    {"id": "n-fit", "need": "a sound that drops straight into the engine", "personas": ["indie game dev"],
     "where_asked": ["agent"], "evidence_level": "hypothesis", "evidence": []},
]


def q(qid, need, angle, text, level="derived", **kw):
    r = {"id": qid, "need_id": need, "question": text, "persona": "first-time Godot dev", "stage": "choosing",
         "angle": angle, "evidence_level": level, "evidence": ["forum-1"] if level != "hypothesis" else [],
         "follow_ups": [{"q": "Do I have to credit anyone?", "kind": "constraint"}], "origin": "model"}
    r.update(kw)
    return r


BANK = [
    q("q1", "n-safe", "recommend", "Where do I get gun sounds I can ship in a Steam game without crediting anyone?", "quoted"),
    q("q2", "n-safe", "constraint", "If I sell my game, do I need to credit whoever made the sound effects?"),
    q("q3", "n-safe", "problem", "My trailer got a copyright claim on a royalty-free sound, what now?"),
    q("q4", "n-safe", "compare", "Is a CC0 library safer than a royalty-free subscription for a small game?"),
    q("q5", "n-fit", "howto", "How do I make a footstep loop cleanly in Godot?", "hypothesis"),
]


class DemandAndBankTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run(self.root, "init", "--name", "Mint", "--idea", "sounds for games", "--live", "--origin", "https://example.com")

    def tearDown(self):
        self.tmp.cleanup()

    def test_needs_validates_evidence_and_advances_stage(self):
        bad = json.loads(json.dumps(NEEDS))
        bad[0]["evidence"][1].pop("ref")
        bad[1]["evidence_level"] = "validated"
        gi.write_jsonl(self.root / "geo/needs.jsonl", bad)
        code, out = run(self.root, "needs")
        self.assertEqual(code, 1)
        self.assertIn("needs ref", out)
        self.assertIn("validated needs evidence", out)
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        code, out = run(self.root, "needs")
        self.assertEqual(code, 0)
        proj = json.loads((self.root / "geo/project.json").read_text())
        self.assertEqual(proj["stage"], "needs")
        self.assertTrue(proj["site"]["live"])
        self.assertIn("n-safe", (self.root / "geo/needs.md").read_text())
        code, _ = run(self.root, "check")
        self.assertEqual(code, 0)  # no task space yet is fine at the needs stage

    def test_bank_flags_brands_duplicates_and_thin_angles(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/competitors.jsonl", [{"id": "pixabay", "name": "Pixabay", "domain": "pixabay.com", "kind": "library"}])
        bank = BANK + [q("q6", "n-safe", "alternative", "Is Pixabay ok for a commercial game?"),
                       q("q7", "n-safe", "constraint", "If I sell my game, do I need to credit whoever made the sound effects??"),
                       q("q8", "n-zzz", "recommend", "Where?")]
        gi.write_jsonl(self.root / "geo/questions.jsonl", bank)
        code, out = run(self.root, "bank")
        self.assertEqual(code, 1)
        self.assertIn("need_id 'n-zzz' is not in needs.jsonl", out)
        self.assertIn("names ['pixabay']", out)
        self.assertIn("q2 and q7", out)
        self.assertIn("need n-fit: 1 angles", out)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        code, _ = run(self.root, "bank")
        self.assertEqual(code, 0)
        self.assertIn("quoted / derived / hypothesis", (self.root / "geo/bank.md").read_text())

    def test_sample_from_questions_spreads_needs_and_skips_hypotheses(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        code, out = run(self.root, "sample", "--n", "10", "--from-questions")
        self.assertEqual(code, 0)
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        self.assertEqual({r["question_id"] for r in rows}, {"q1", "q2", "q3", "q4"})
        self.assertEqual(json.loads(out)["needs_uncovered"], ["n-fit"])
        code, _ = run(self.root, "sample", "--n", "10", "--from-questions", "--include-hypothesis", "--force")
        self.assertEqual(len(gi.read_jsonl(self.root / "geo/gap/samples.jsonl")), 5)
        code, _ = run(self.root, "probes")
        self.assertEqual(code, 0)

    def test_bank_checks_evidence_refs_and_brand_sources(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/competitors.jsonl", [
            {"id": "cinevva", "name": "Cinevva guide", "domain": "app.cinevva.com", "kind": "list"},
            {"id": "itch", "name": "itch.io assets", "domain": "itch.io", "kind": "marketplace"}])
        bank = BANK + [q("q6", "n-safe", "alternative", "Can I use these for a paid itch.io release?", evidence=["n-safe#e2"]),
                       q("q7", "n-safe", "compare", "What does the cinevva list say?", evidence=["n-safe#e3"]),
                       q("q8", "n-safe", "howto", "Is example good for trailers?", evidence=["n-nope#e1"]),
                       q("q9", "n-fit", "recommend", "Where do I find drop-in door sounds?", "hypothesis", evidence=["n-safe#e1"])]
        gi.write_jsonl(self.root / "geo/questions.jsonl", bank)
        code, out = run(self.root, "bank")
        self.assertEqual(code, 1)
        self.assertIn("'n-safe#e3' is out of range (n-safe has 2 evidence rows)", out)
        self.assertIn("names need 'n-nope'", out)
        self.assertIn("names ['cinevva']", out)          # registrable part of a subdomain
        self.assertIn("(q8): names ['example']", out)  # our own site domain
        self.assertIn("(q6): names ['itch']", out)
        self.assertIn("a hypothesis with evidence", out)
        proj = gi.read_json(self.root / "geo/project.json")
        proj["allowed_names"] = ["itch.io"]
        gi.write_json(self.root / "geo/project.json", proj)
        code, out = run(self.root, "bank")
        self.assertNotIn("(q6): names", out)
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("out of range", out)

    def test_sample_weights_origin_ids_and_append(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        bank = BANK + [q(f"f{i}", "n-fit", a, f"Fit question number {i} about {a} with its own words {i}")
                       for i, a in enumerate(["recommend", "howto", "problem", "compare", "constraint", "alternative"])]
        bank += [q("c1", "n-safe", "problem", "Cancelled a subscription, are old videos still safe?", origin="competitor",
                   competitor="pixabay"),
                 q("c2", "n-fit", "howto", "Their loops click in Godot, why?", "hypothesis", evidence=[],
                   origin="competitor", competitor="pixabay")]
        gi.write_jsonl(self.root / "geo/questions.jsonl", bank)
        code, out = run(self.root, "sample", "--n", "6", "--from-questions", "--weight", "n-safe=2")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["by_need"], {"n-safe": 4, "n-fit": 2})
        code, out = run(self.root, "sample", "--from-questions", "--ids", "c2,c1", "--force")
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        self.assertEqual([r["question_id"] for r in rows], ["c2", "c1"])  # hand-picked hypotheses are kept
        self.assertEqual(rows[0]["origin"], "competitor")
        code, out = run(self.root, "sample", "--n", "3", "--from-questions", "--origin", "model")
        self.assertNotEqual(code, 0)  # rows exist: needs --append or --force
        code, out = run(self.root, "sample", "--n", "3", "--from-questions", "--origin", "model", "--append")
        self.assertEqual(code, 0)
        rows = gi.read_jsonl(self.root / "geo/gap/samples.jsonl")
        self.assertEqual(len(rows), 5)
        self.assertEqual({r["origin"] for r in rows[2:]}, {"model"})
        code, out = run(self.root, "sample", "--from-questions", "--ids", "c1", "--append")
        self.assertEqual(json.loads(out)["added"], 0)  # already sampled
        code, out = run(self.root, "sample", "--n", "3", "--ids", "c1")
        self.assertNotEqual(code, 0)  # --ids needs --from-questions

    def test_bank_route_checks_and_narrows_by_need(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "4", "--from-questions")
        base = {"platform": "ChatGPT", "date": "2026-11-18", "mode": "browser", "web_search": True, "own": "absent"}
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [{**base, "combo_id": q, "gap": "generic"} for q in ("q1", "q2", "q3", "q4")])
        self.assertEqual(run(self.root, "report")[0], 0)
        code, out = run(self.root, "check")
        self.assertEqual(code, 0, out)  # no task-space dimensions on the bank route
        ready_to_decide(self.root, {"n-safe": "pages+offsite", "n-fit": "not-now"})
        code, out = run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"need": ["n-safe"]}')
        self.assertNotEqual(code, 0)  # the bank route still needs a task space before pages (rule 6b)
        # a task-space dimension called `need` would shadow need ids in --subspace: use another name
        (self.root / "geo/dimensions.json").write_text(json.dumps(DIMS).replace('"need"', '"mode"'))
        ready_to_decide(self.root, {"n-safe": "pages+offsite", "n-fit": "not-now"})
        code, out = run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"need": ["n-nope"]}')
        self.assertNotEqual(code, 0)
        code, out = run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"need": ["n-safe"]}')
        self.assertEqual(code, 2)  # site absent from every answer: the owner's reason is required
        code, out = run(self.root, "decide", "--verdict", "narrow", "--by", "user", "--subspace", '{"need": ["n-safe"]}',
                        "--note", "small first wave as a test, offsite alongside")
        self.assertEqual(code, 0, out)
        self.assertEqual(gi.read_json(self.root / "geo/project.json")["decision"]["subspace"], {"need": ["n-safe"]})

    def test_report_presence_lever_and_notes(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "4", "--from-questions")
        base = {"platform": "ChatGPT", "date": "2026-11-18", "mode": "browser", "web_search": True}
        lists = [{"url": "https://list.example/top-10", "type": "list"}, {"url": "https://reddit.com/x", "type": "forum"}]
        runs = [
            {**base, "combo_id": "q1", "gap": "no_resource", "own": "absent", "cited": lists, "recommended": ["A", "B"],
             "search_queries": ["free gun sound effects commercial no attribution"]},
            {**base, "combo_id": "q2", "gap": "generic", "own": "absent", "cited": lists, "recommended": ["A"], "search_queries": None},
            {**base, "combo_id": "q3", "gap": "self_made", "own": "absent", "cited": lists, "outcome": "lists_forums"},
            {**base, "combo_id": "q4", "gap": "good", "own": "listed", "cited_own": True,
             "cited": [{"url": "https://example.com/x", "type": "brand"}], "recommended": ["A", "Mint"]},
        ]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", runs)
        code, _ = run(self.root, "check")
        self.assertEqual(code, 0)
        code, out = run(self.root, "report")
        self.assertEqual(code, 0)
        rep = json.loads((self.root / "geo/gap/report.json").read_text())
        p = rep["presence"]
        self.assertEqual(p["in_answer_share"], 0.25)
        self.assertEqual(p["lever_hint"], "offsite")
        self.assertEqual(p["queries_captured"], 1)
        self.assertEqual(p["self_made"], 1)
        self.assertEqual(rep["groups"]["need_id"]["n-safe"]["probed"], 4)
        self.assertTrue(any("self_made" in n for n in rep["notes"]))
        md = (self.root / "geo/gap/report.md").read_text()
        self.assertIn("Is the site in the answer", md)
        self.assertIn("Lever hint: **offsite**", md)
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [{**runs[0], "own": "maybe", "search_queries": "x"}])
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("own must be one of", out)
        self.assertIn("search_queries is a list", out)

    def test_low_presence_note_when_lever_is_offsite(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "4", "--from-questions")
        lists = [{"url": "https://list.example/top-10", "type": "list"}]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {"combo_id": c, "platform": "ChatGPT", "date": "2026-11-18", "mode": "manual", "web_search": True,
             "gap": "generic", "own": "absent", "cited": lists} for c in ("q1", "q2", "q3", "q4")])
        run(self.root, "report")
        rep = json.loads((self.root / "geo/gap/report.json").read_text())
        self.assertEqual(rep["hint"], "go")
        self.assertTrue(any("pages alone are unlikely" in n for n in rep["notes"]))

    def test_competitor_search_pages_get_their_own_note(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "3", "--from-questions")
        cited = [{"url": "https://pixabay.com/sound-effects/search/dog%20bark/", "type": "competitor"},
                 {"url": "https://mixkit.co/free-sound-effects/dog/", "type": "competitor"}]
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {"combo_id": c, "platform": "ChatGPT", "date": "2026-11-18", "mode": "manual", "web_search": True,
             "gap": "generic", "own": "absent", "cited": cited} for c in ("q1", "q2", "q3")])
        run(self.root, "report")
        rep = json.loads((self.root / "geo/gap/report.json").read_text())
        self.assertEqual(rep["presence"]["lever_hint"], "onsite")
        self.assertEqual(rep["presence"]["competitor_search_page_share"], 0.5)
        self.assertTrue(any("search or tag result pages" in n for n in rep["notes"]))

    def test_decide_without_probes_needs_validated_needs(self):
        (self.root / "geo/dimensions.json").write_text(json.dumps(DIMS))
        code, _ = run(self.root, "decide", "--verdict", "go", "--by", "user", "--without-probes")
        self.assertEqual(code, 2)
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        code, _ = run(self.root, "decide", "--verdict", "go", "--by", "model", "--without-probes")
        self.assertEqual(code, 2)
        ready_to_decide(self.root, {"n-safe": "pages", "n-fit": "product"})
        code, out = run(self.root, "decide", "--verdict", "go", "--by", "user", "--without-probes")
        self.assertEqual(code, 0)
        dec = json.loads((self.root / "geo/project.json").read_text())["decision"]
        self.assertEqual(dec["levers"], {"n-fit": ["product"], "n-safe": ["pages"]})
        self.assertEqual(dec["evidence"]["basis"], "first-party demand")
        self.assertEqual(dec["evidence"]["needs_validated"], 1)

    def test_pool_sample_spreads_strata_and_first_party_signals(self):
        dims = {"dimensions": [{"id": "family", "kind": "entity", "changes_answer": True, "why": "different sounds",
                                "source": "catalog", "values": [{"id": f"f{i}"} for i in range(12)]}]}
        (self.root / "geo/dimensions.json").write_text(json.dumps(dims))
        pool = [{"combo": {"family": f"f{i}"}, "url": f"/sounds/f{i}", "stratum": "high" if i < 3 else "low"} for i in range(12)]
        gi.write_jsonl(self.root / "pool.jsonl", pool)
        code, out = run(self.root, "sample", "--n", "6", "--pool", "pool.jsonl")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["strata"], {"high": 3, "low": 3})
        p = self.root / "geo/gap/samples.jsonl"
        rows = gi.read_jsonl(p)
        self.assertTrue(all(r["url"].startswith("/sounds/") for r in rows))
        rows[0]["signals"] = [{"source": "site_search", "ref": "search_log 60d", "q": "dog bark", "n": 163},
                              {"source": "site_search", "q": "no ref"}]
        gi.write_jsonl(p, rows)
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("needs ref", out)

    def test_report_after_pages_stage_keeps_the_stage(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "2", "--from-questions")
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {"combo_id": "q1", "platform": "ChatGPT", "date": "2026-11-18", "mode": "manual", "gap": "generic"}])
        p = self.root / "geo/project.json"
        proj = json.loads(p.read_text())
        proj["stage"] = "pages"
        p.write_text(json.dumps(proj))
        code, _ = run(self.root, "report")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(p.read_text())["stage"], "pages")

    def test_needs_volume_sources_quotes_and_quiet_log(self):
        needs = json.loads(json.dumps(NEEDS))
        needs[0]["count_by_source"] = {"forum": 80, "feedback": 5}
        needs[0]["volume"] = [{"ref": "search_log 60d", "what": "licence words", "n": 23}]
        needs[0]["where_asked"] = ["assistant", "product"]
        needs[0]["evidence"].append({"source": "survey", "ref": "purchase_source_feedback", "value": "ai_assistant", "n": 5})
        gi.write_jsonl(self.root / "geo/needs.jsonl", needs)
        code, out = run(self.root, "needs")
        self.assertEqual(code, 0, out)
        md = (self.root / "geo/needs.md").read_text()
        self.assertIn("forum 80, feedback 5", md)
        self.assertIn("licence words 23", md)
        self.assertIn("indie game dev", md)
        run(self.root, "needs")
        log = json.loads((self.root / "geo/project.json").read_text())["log"]
        self.assertEqual(sum(1 for x in log if x["stage"] == "needs"), 1)   # same result twice, logged once
        gi.write_jsonl(self.root / "posts.jsonl", [{"url": "https://www.reddit.com/r/gamedev/x",
                                                    "quote": "Looking for 100%  copyright free sounds to use"}])
        code, _ = run(self.root, "needs", "--quotes", "posts.jsonl")
        self.assertEqual(code, 0)
        gi.write_jsonl(self.root / "posts.jsonl", [{"url": "https://www.reddit.com/r/gamedev/x", "quote": "something else"}])
        code, out = run(self.root, "needs", "--quotes", "posts.jsonl")
        self.assertEqual(code, 1)
        self.assertIn("quote not found verbatim", out)
        needs[0]["volume"] = {"licence_words": {"api": 1, "mcp": 13, "web": 9}, "pasted_lists": 186}
        gi.write_jsonl(self.root / "geo/needs.jsonl", needs)
        self.assertEqual(run(self.root, "needs")[0], 0)
        self.assertIn("licence words 23 (api 1, mcp 13, web 9)", (self.root / "geo/needs.md").read_text())
        needs[0]["volume"] = [{"n": 3}]
        gi.write_jsonl(self.root / "geo/needs.jsonl", needs)
        self.assertIn("volume is a list of", run(self.root, "needs")[1])

    def test_geo_dir_keeps_two_projects_apart(self):
        code, _ = run(self.root, "--geo-dir", "geo-families", "init", "--name", "Families", "--idea", "x")
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "geo-families/project.json").exists())
        self.assertEqual(json.loads((self.root / "geo/project.json").read_text())["name"], "Mint")

    def test_probes_use_probe_platforms_and_safe_slugs(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "2", "--from-questions")
        pj = self.root / "geo/project.json"
        proj = json.loads(pj.read_text())
        proj["platforms"] = ["coding agents via API/MCP (Claude Code, Codex)", "ChatGPT"]
        pj.write_text(json.dumps(proj))
        run(self.root, "probes")
        self.assertIn("coding-agents-via-api-mcp-claude-code-codex--1.md", (self.root / "geo/gap/probes.md").read_text())
        proj["probe_platforms"] = ["ChatGPT Instant"]
        pj.write_text(json.dumps(proj))
        run(self.root, "probes")
        md = (self.root / "geo/gap/probes.md").read_text()
        self.assertIn("--chatgpt-instant--1.md", md)
        self.assertNotIn("coding-agents", md)

    def test_sample_copies_evidence_into_signals(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        bank = [q("q1", "n-safe", "recommend", "Where do I get gun sounds for Steam?", "quoted", evidence=["n-safe#e1"]),
                q("q2", "n-safe", "problem", "My trailer got a claim, what now?",
                  evidence=["n-safe#e2", "https://x.example/p"])]
        gi.write_jsonl(self.root / "geo/questions.jsonl", bank)
        run(self.root, "sample", "--n", "2", "--from-questions")
        by = {r["combo_id"]: r for r in gi.read_jsonl(self.root / "geo/gap/samples.jsonl")}
        self.assertEqual(by["q1"]["signals"], [{"url": "https://www.reddit.com/r/gamedev/x",
                                                "quote": "100% copyright free sounds"}])
        self.assertEqual(by["q2"]["signals"][0], {"source": "site_search", "ref": "search_log 2026-09-18..11-17",
                                                  "q": "cc0 gunshot", "n": 9})
        self.assertEqual(by["q2"]["signals"][1], {"ref": "https://x.example/p"})
        self.assertEqual(run(self.root, "check")[0], 0)

    def test_report_where_extra_sets_slice_and_generic_rules(self):
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "4", "--from-questions")
        base = {"platform": "ChatGPT", "date": "2026-11-18", "mode": "browser", "own": "absent"}
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [
            {**base, "combo_id": "q1", "gap": "generic", "slice": "chatgpt-instant", "outcome": "generic_rules"},
            {**base, "combo_id": "q2", "gap": "good", "slice": "chatgpt-thinking"}])
        gi.write_jsonl(self.root / "geo/gap/runs-captured.jsonl", [
            {**base, "combo_id": "q3", "gap": "generic", "slice": "chatgpt-instant", "search_queries": ["a b"]}])
        self.assertEqual(run(self.root, "check")[0], 0)
        run(self.root, "report", "--where", "slice=chatgpt-instant")
        rep = json.loads((self.root / "geo/gap/report.json").read_text())
        self.assertEqual(rep["probed"], 1)
        self.assertEqual(rep["presence"]["outcomes"], {"generic_rules": 1})
        self.assertEqual(rep["extra_sets"]["runs-captured"]["runs"], 1)
        self.assertIn("Extra run sets", (self.root / "geo/gap/report.md").read_text())
        run(self.root, "report", "--where", "slice=chatgpt-instant", "--include-extra")
        rep = json.loads((self.root / "geo/gap/report.json").read_text())
        self.assertEqual(rep["probed"], 2)
        self.assertNotIn("extra_sets", rep)
        gi.write_jsonl(self.root / "geo/gap/runs-captured.jsonl", [{**base, "combo_id": "zz", "gap": "good"}])
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("runs-captured:1", out)
        self.assertNotEqual(run(self.root, "report", "--where", "oops")[0], 0)

class GatesTest(unittest.TestCase):
    """The rules the 2026-11-18 validation found unenforced: per-channel decisions, task space first,
    decisions kept, needs before dimensions, the goal card."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run(self.root, "init", "--name", "Mint", "--idea", "sounds", "--live", "--origin", "https://example.com")
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS)
        run(self.root, "needs")
        gi.write_jsonl(self.root / "geo/questions.jsonl", BANK)
        run(self.root, "sample", "--n", "4", "--from-questions")
        base = {"platform": "ChatGPT", "date": "2026-11-18", "mode": "browser", "own": "absent"}
        gi.write_jsonl(self.root / "geo/gap/runs.jsonl", [{**base, "combo_id": "q1", "gap": "generic"}])
        run(self.root, "report")

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_marks_one_channel_and_thin_samples_and_writes_the_table(self):
        md = (self.root / "geo/gap/report.md").read_text()
        self.assertIn("Assistant-chat hint (ChatGPT only", md)
        self.assertIn("1 (thin)", md)
        rep = gi.read_json(self.root / "geo/gap/report.json")
        self.assertTrue(rep["notes"][0].startswith("thin sample"))
        table = (self.root / "geo/gap/channels.md").read_text()
        self.assertIn("| n-safe: ", table)
        self.assertIn("picked: 1 runs (thin)", table)
        self.assertIn("after landing: not measured", table)
        self.assertIn("| ? |", table)
        self.assertEqual(run(self.root, "channels")[0], 2)          # never overwritten by accident

    def test_decide_needs_levers_task_space_and_pages(self):
        code, out = run(self.root, "decide", "--verdict", "go", "--by", "user")
        self.assertEqual(code, 2)                                     # levers still `?`
        t = self.root / "geo/gap/channels.md"
        t.write_text(t.read_text().replace("| ? |", "| offsite |"))
        self.assertEqual(run(self.root, "decide", "--verdict", "go", "--by", "user")[0], 2)  # no task space
        (self.root / "geo/dimensions.json").write_text(json.dumps(DIMS))
        run(self.root, "space")
        self.assertEqual(run(self.root, "decide", "--verdict", "go", "--by", "user")[0], 2)  # no need has pages
        self.assertEqual(run(self.root, "decide", "--verdict", "stop", "--by", "user", "--note", "offsite only")[0], 0)
        t.write_text(t.read_text().replace("| offsite |", "| pages+offsite |", 1))
        dims = json.loads(json.dumps(DIMS))
        dims["dimensions"][1]["values"].append({"id": "gif"})
        (self.root / "geo/dimensions.json").write_text(json.dumps(dims))
        self.assertEqual(run(self.root, "decide", "--verdict", "go", "--by", "user")[0], 2)  # space is stale
        run(self.root, "space")
        self.assertEqual(run(self.root, "decide", "--verdict", "go", "--by", "user", "--note", "second")[0], 0)
        proj = gi.read_json(self.root / "geo/project.json")
        self.assertEqual([d["verdict"] for d in proj["decisions"]], ["stop", "go"])   # history kept
        self.assertEqual(proj["decision"]["note"], "second")
        self.assertEqual(proj["decisions"][0]["note"], "offsite only")

    def test_space_without_validated_needs_does_not_advance(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        run(root, "init", "--name", "Idea", "--idea", "x")
        gi.write_jsonl(root / "geo/needs.jsonl", [NEEDS[1]])        # a hypothesis only
        (root / "geo/dimensions.json").write_text(json.dumps(DIMS))
        code, out = run(root, "space")
        self.assertEqual(code, 0)
        self.assertIn("no validated need", out)
        self.assertEqual(gi.read_json(root / "geo/project.json")["stage"], "idea")
        tmp.cleanup()

    def test_rerun_behind_the_stage_logs_a_check_and_needs_are_shared(self):
        p = self.root / "geo/project.json"
        proj = gi.read_json(p)
        proj["stage"] = "pages"
        gi.write_json(p, proj)
        gi.write_jsonl(self.root / "geo/needs.jsonl", NEEDS + [{**NEEDS[1], "id": "n-new"}])
        run(self.root, "needs")
        log = gi.read_json(p)["log"]
        self.assertEqual(log[-1]["stage"], "check")
        self.assertEqual(gi.read_json(p)["stage"], "pages")
        code, _ = run(self.root, "--geo-dir", "geo-find", "init", "--name", "Find", "--idea", "y", "--needs-from", "geo")
        self.assertEqual(code, 0)
        code, out = run(self.root, "--geo-dir", "geo-find", "needs")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out.splitlines()[-1])["needs"], 3)
        self.assertFalse((self.root / "geo-find/needs.jsonl").exists())

    def test_check_warns_about_goal_card_and_old_decisions(self):
        _, out = run(self.root, "check")
        self.assertIn("no goal card geo-goal.md", out)
        (self.root / "geo-goal.md").write_text("# Goal card\n\n## North star\nAI referrals that download, per week\n\n## Goal\nx\n")
        p = self.root / "geo/project.json"
        proj = gi.read_json(p)
        proj["north_star"] = "page views"
        proj["decision"] = {"verdict": "narrow"}
        gi.write_json(p, proj)
        (self.root / "geo/gap/channels.md").unlink()
        _, out = run(self.root, "check")
        self.assertIn("north_star differs", out)
        self.assertIn("no 'Main bet' section", out)
        self.assertIn("predates the need × channel table", out)


if __name__ == "__main__":
    unittest.main()
