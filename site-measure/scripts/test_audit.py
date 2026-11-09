#!/usr/bin/env python3
"""Tests for audit.py on small synthetic projects (no real site code)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_measure_audit", HERE / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

WRAPPER = """export function track(name: string, data = {}): void {
  try { (globalThis as any).umami?.track?.(name, data); } catch {}
}
"""
TOOL = """import { track } from './track';
export function Tool() {
  const ctx = useRef<{ res: string; length: string; mode: string }>({ res: '', length: '', mode: '' });
  const elapsed = () => Math.round((performance.now() - startedAt) / 1000);
  function load(v) {
    ctx.current = { ...ctx.current, res: band(v), length: lengthBand(v.duration) };
    track('tool_file', { ...ctx.current });
  }
  function run(full) {
    track(full ? 'tool_full' : 'tool_start', { ...ctx.current });
  }
  w.onmessage = (m) => {
    if (m.done) track('tool_done', { ...ctx.current, msPerFrame: Math.round(m.ms), seconds: elapsed() });
    if (m.error) track('tool_error', { reason: errorReason(m.message) });
  };
  return <a href="/pricing" data-umami-event="buy_click" data-umami-event-from="tool_hint">Buy</a>;
}
"""
APP = """import { track } from '../components/track';
for (const j of ended) track('cloud_job_end', { status: j.status, seconds: Math.round(j.seconds) });
track('cloudStart', { fileName: file.name, title: doc.title, colour: 'red' });
track('cloud_start', cancelled ? { product: cancelled } : {});
"""
KIT = """function track(name, data) { window.umami?.track(name, data); }
track('checkout_start', { product });
"""
CONFIG = """export default {
  type: 'tool',
  modules: { legal: { analyticsEvents: 'Events record the resolution band, a length band, the mode, how many seconds it took and a short error category.' } },
};
"""


def project(files, kit_type="tool"):
    root = Path(tempfile.mkdtemp())
    if kit_type:
        (root / ".sitekit.json").write_text(json.dumps({"site": {"type": kit_type}}))
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.root = project({
            "src/site/components/track.ts": WRAPPER,
            "src/site/components/Tool.tsx": TOOL,
            "src/site/app/App.tsx": APP,
            "src/kit/ui/Billing.tsx": KIT,
            "site.config.ts": CONFIG,
            "tests/tool.test.ts": "track('test_only_event', { email: 'x' });\n",
        })
        self.report = audit.audit(self.root)
        self.events = {e["name"]: e for e in self.report["events"]}

    def test_finds_names_fields_and_spreads(self):
        self.assertEqual(self.report["types"], ["tool"])
        self.assertEqual(self.events["tool_file"]["fields"], ["length", "mode", "res"])
        self.assertIn("tool_full", self.events)  # both arms of the ternary name
        self.assertIn("tool_start", self.events)
        self.assertEqual(self.events["tool_done"]["fields"], ["length", "mode", "msPerFrame", "res", "seconds"])
        self.assertEqual(self.events["buy_click"]["fields"], ["from"])
        self.assertEqual(self.events["cloud_start"]["fields"], ["product"])  # ternary data argument
        self.assertTrue(self.events["checkout_start"]["kit"])
        self.assertNotIn("test_only_event", self.events)
        # The wrappers' own forwarding calls have a variable name, so they are listed, not counted.
        self.assertTrue(any(d["first_arg"] == "name" for d in self.report["dynamic_calls"]))

    def test_missing_roles(self):
        missing = {r["role"] for r in self.report["missing"]}
        self.assertEqual(missing, {"tool_takeaway"})  # no download/copy event

    def test_naming(self):
        issues = " | ".join(n["issue"] + ": " + n["name"] for n in self.report["naming"])
        self.assertIn("event name is not snake_case: cloudStart", issues)
        self.assertIn("event names differ only by case or separators: cloudStart, cloud_start", issues)
        self.assertIn("'seconds' means two things: processing time in tool_done; the input's length in cloud_job_end", issues)

    def test_fields(self):
        by_key = {f["key"]: f["issue"] for f in self.report["fields"]}
        self.assertEqual(by_key["fileName"], "private-looking key")
        self.assertEqual(by_key["title"], "private-looking key")
        self.assertEqual(by_key["colour"], "not in the plan's allowlist")
        self.assertNotIn("msPerFrame", by_key)

    def test_private_value(self):
        root = project({"src/a.ts": "track('tool_file', { kind: file.name });\n"})
        report = audit.audit(root)
        self.assertEqual(report["fields"][0]["issue"], "value may carry private data")

    def test_media_length_only(self):
        root = project({"src/a.ts": "track('tool_done', { seconds: video.duration });\n"})
        issues = [n["issue"] for n in audit.audit(root)["naming"]]
        self.assertTrue(any("filled from the input's length" in i for i in issues))

    def test_privacy_keywords(self):
        p = self.report["privacy"]
        self.assertEqual(p["status"], "MANUAL")
        self.assertTrue(p["text_found"])
        self.assertIn("from", p["fields_without_mention"])
        self.assertIn("msPerFrame", p["fields_without_mention"])
        self.assertNotIn("res", p["fields_without_mention"])
        self.assertNotIn("checkout_start", p["site_events"])  # the kit discloses its own events

    def test_no_disclosure_is_a_fix(self):
        root = project({"src/a.ts": "track('tool_file', { res: '480p' });\n", "site.config.ts": "export default {}\n"})
        self.assertEqual(audit.audit(root)["privacy"]["status"], "fix")

    def test_types(self):
        root = project({"src/a.ts": "track('outbound_click', { from: 'card' });\n"}, kit_type=None)
        with self.assertRaisesRegex(ValueError, "pass --type"):
            audit.audit(root)
        with self.assertRaisesRegex(ValueError, "Unknown --type"):
            audit.audit(root, ["shop"])
        report = audit.audit(root, ["directory", "content"])
        self.assertEqual([r["role"] for r in report["missing"]], ["cta_click"])
        self.assertIn("MISS content.cta_click", audit.render(report))

    def test_plans_are_consistent(self):
        plans = audit.load_plans()
        for name, plan in plans["types"].items():
            roles = {r["role"] for r in plan["roles"]}
            for step in plan["funnel"]:
                self.assertTrue(step.startswith("path:") or step in roles, name + ": " + step)


if __name__ == "__main__":
    unittest.main()
