#!/usr/bin/env python3
"""Tests for scan.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_*.py'"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_analytics_scan", HERE / "scan.py")
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


def write(root, files):
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def git_commit(root, message):
    run = ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", str(root)]
    subprocess.run(run + ["init", "-q"], check=True)
    subprocess.run(run + ["add", "-A"], check=True)
    subprocess.run(run + ["commit", "-qm", message], check=True)


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def report(self, domain=None):
        result = scan.scan(self.root, domain)
        self.text = json.dumps(result) + scan.render(result)
        return result

    def test_next_app_with_ga_only(self):
        write(self.root, {
            "package.json": {"dependencies": {"next": "16.0.0", "react": "19.0.0"}},
            "src/app/layout.tsx": "export const metadata = { metadataBase: new URL('https://www.shop-demo.io') };\n"
                                  "export default function L({children}) { return <html><body><GoogleAnalytics />{children}</body></html>; }\n",
            "src/components/GoogleAnalytics.tsx": "export function GoogleAnalytics() {\n"
                                                  "  return <Script src={`https://www.googletagmanager.com/gtag/js?id=G-ABCDEFGH12`} />;\n}\n",
            "src/lib/analytics.ts": "export function send(name, params) {\n"
                                    "  if (window.location.hostname !== 'shop-demo.io') return;\n"
                                    "  if (navigator.webdriver) return;\n"
                                    "  const qa = new URLSearchParams(window.location.search).get('qa');\n"
                                    "  window.gtag('event', name, params);\n}\n",
            "src/app/privacy/page.tsx": "<p>We use Google Analytics, which sets the _ga cookie.</p>\n",
            ".env.example": "NEXT_PUBLIC_GA_ID=\nOTHER=1\n",
            ".env": "NEXT_PUBLIC_GA_ID=G-SECRETVALUE1\nAPI_SECRET=supersecretvalue\n",
            "scripts/ga4-report.mjs": "import { BetaAnalyticsDataClient } from '@google-analytics/data';\n",
            "tests/analytics.test.ts": "expect(html).toContain('googletagmanager');\n",
            "public/_headers": "/*\n  Content-Security-Policy: script-src 'self' https://www.googletagmanager.com\n",
            "node_modules/pkg/index.js": "window.gtag('event', 'from-dependency');\n",
            "docs/notes.md": "Privacy note: Google Analytics everywhere\n",
        })
        result = self.report()
        self.assertEqual(result["framework"]["kind"], "next-app")
        self.assertEqual(result["framework"]["connect"], "auto")
        self.assertEqual(result["framework"]["entries"], ["src/app/layout.tsx"])
        self.assertEqual(result["phase"], "ga-only")
        self.assertEqual(result["domain_candidates"], ["shop-demo.io"])
        self.assertIn("G-ABCDEFGH12", result["ga_ids"])
        categories = result["categories"]
        self.assertEqual(categories["ga_events"]["files"], ["src/lib/analytics.ts"])
        guards = {item["match"] for item in categories["ga_guards"]["items"]}
        self.assertTrue({"production host check", "bot / automation filter", "QA / debug flag"} <= guards)
        self.assertEqual(categories["privacy_text"]["files"], ["src/app/privacy/page.tsx"])
        self.assertEqual(categories["checks"]["files"], ["tests/analytics.test.ts"])
        self.assertEqual(categories["ga_reports"]["files"], ["scripts/ga4-report.mjs"])
        self.assertEqual(result["csp"]["with_google"], ["public/_headers"])
        self.assertEqual(result["csp"]["without_umami_host"], ["public/_headers"])
        self.assertIn(".env:1 (value not shown)", result["env_names"]["NEXT_PUBLIC_GA_ID"])
        self.assertIn(".env.example:1", result["env_names"]["NEXT_PUBLIC_GA_ID"])
        self.assertIn("--dry-run", result["connect_preview"])
        self.assertIn("shop-demo.io", result["connect_preview"])
        # Secrets from real env files and dependency or note files never reach the output.
        for leaked in ("supersecretvalue", "G-SECRETVALUE1", "from-dependency", "docs/notes.md", "node_modules"):
            self.assertNotIn(leaked, self.text)

    def test_astro_with_several_layouts_needs_entries(self):
        write(self.root, {
            "package.json": {"devDependencies": {"astro": "5.0.0"}},
            "astro.config.mjs": "export default { site: 'https://docs-demo.io' };\n",
            "src/layouts/Base.astro": "---\n---\n<html><head><title>x</title></head><body><slot /></body></html>\n",
            "src/layouts/Docs.astro": "---\n---\n<html><head></head><body><slot /></body></html>\n",
            "src/layouts/Card.astro": "<div><slot /></div>\n",
        })
        result = self.report()
        self.assertEqual(result["framework"]["connect"], "entry")
        self.assertEqual(result["framework"]["entries"], ["src/layouts/Base.astro", "src/layouts/Docs.astro"])
        self.assertEqual(result["phase"], "none")
        self.assertIn("--framework astro --entry src/layouts/Base.astro --entry src/layouts/Docs.astro",
                      result["connect_preview"])

    def test_parallel_vite_site_reports_umami_and_since_date(self):
        write(self.root, {
            "package.json": {"devDependencies": {"vite": "7.0.0"}},
            "index.html": "<html><head>\n<script async src=\"https://www.googletagmanager.com/gtag/js?id=G-ABCDEFGH12\"></script>\n"
                          "<script defer src=\"https://analytics.plugxai.com/script.js\" data-website-id=\"x\" "
                          "data-before-send=\"siteBeforeSend\"></script>\n</head><body></body></html>\n",
            "umami.config.json": {"generator": "umami-connect", "schema_version": 1, "domain": "vite-demo.io"},
            "public/_headers": "/*\n  Content-Security-Policy: script-src 'self' https://www.googletagmanager.com "
                               "https://analytics.plugxai.com; connect-src 'self' https://analytics.plugxai.com\n",
        })
        if shutil.which("git"):
            git_commit(self.root, "connect umami")
        result = self.report("vite-demo.io")
        self.assertEqual(result["phase"], "parallel")
        self.assertEqual(result["umami"]["config"]["generator"], "umami-connect")
        self.assertEqual(result["csp"]["without_umami_host"], [])
        self.assertIsNone(result["connect_preview"])
        if shutil.which("git"):
            self.assertIsNotNone(result["umami"]["since"])
            self.assertEqual(result["umami"]["days_in_git"], 0)

    def test_umami_only_lists_ga_leftovers(self):
        write(self.root, {
            "package.json": {"dependencies": {"next": "16.0.0"}},
            "src/app/layout.tsx": "<html><body><UmamiAnalytics /></body></html>\n",
            "src/components/UmamiAnalytics.tsx": "<Script src=\"https://analytics.plugxai.com/script.js\" data-website-id=\"x\" />\n",
            "src/app/privacy/page.tsx": "<p>Google Analytics 4 sets _ga cookies.</p><p>Umami counts visits without cookies.</p>\n",
            ".env.example": "NEXT_PUBLIC_GA_ID=\n",
        })
        result = self.report("next-demo.io")
        self.assertEqual(result["phase"], "umami-only")
        self.assertIn("GA env variable names", result["next_step"])
        self.assertIn("GA wording in privacy/legal text", result["next_step"])
        self.assertEqual(result["umami"]["privacy_mentions_umami"], ["src/app/privacy/page.tsx"])

    def test_static_pages_with_shared_partial_are_not_auto_connected(self):
        write(self.root, {
            "pages/index.html": "<html><head><link rel=\"canonical\" href=\"https://static-demo.io/\"></head><body></body></html>\n",
            "pages/about/index.html": "<html><head></head><body></body></html>\n",
            "partials/analytics.html": "<script>gtag('config', 'G-ABCDEFGH12');</script>\n",
            "dist-site/index.html": "<html><head></head><body>built copy</body></html>\n",
        })
        result = self.report()
        self.assertEqual(result["framework"]["kind"], "static-html")
        self.assertEqual(result["framework"]["entries"], ["pages/about/index.html", "pages/index.html"])
        self.assertIn("partials/analytics.html", result["framework"]["note"])
        self.assertIsNone(result["connect_preview"])
        self.assertEqual(result["domain_candidates"], ["static-demo.io"])
        self.assertNotIn("dist-site", self.text)


if __name__ == "__main__":
    unittest.main()
