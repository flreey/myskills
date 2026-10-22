#!/usr/bin/env python3
"""Tests for geo_check.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_*.py'"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import threading
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_geo_check", HERE / "geo_check.py")
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)

PAGE = "<html><head><title>Shop</title></head><body><h1>Shop</h1>" + "<p>Printable letters.</p>" * 80 + "</body></html>"
ROBOTS = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: PerplexityBot\nDisallow: /private\n\nUser-agent: *\nAllow: /\n"
# Links use the production host, as a local build's llms.txt does.
LLMS = """# Example Shop

> Printable letters. Our Story Kits plan the season.

- [Shop](https://example.com/shop)
- [Old page](https://example.com/old)
- [Editor](/editor)
- [Elsewhere](https://other.example.org/x)
"""
INDEX = """<sitemapindex><sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap></sitemapindex>"""
PAGES = "<urlset>" + "".join(f"<url><loc>https://example.com{p}</loc></url>" for p in ["/", "/shop", "/about"]) + "</urlset>"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        ua = self.headers.get("User-Agent", "")
        if self.path == "/robots.txt":
            return self.send(200, ROBOTS, "text/plain")
        if self.path == "/llms.txt":
            return self.send(200, LLMS, "text/plain")
        if self.path == "/sitemap.xml":
            return self.send(200, INDEX, "application/xml")
        if self.path == "/sitemap-pages.xml":
            return self.send(200, PAGES, "application/xml")
        if "OAI-SearchBot" in ua:
            return self.send(403, "<title>Just a moment...</title>", "text/html", {"cf-mitigated": "challenge"})
        if self.path == "/old":
            return self.send(404, "<title>Not found</title>", "text/html")
        if self.path == "/editor":
            return self.send(200, '<html><head><meta name="robots" content="noindex"></head></html>', "text/html")
        return self.send(200, PAGE, "text/html")

    def send(self, status, body, ctype, extra=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)


class GeoCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def run_check(self):
        return gc.check("https://example.com", ["/", "/private"], self.base + "/sitemap.xml", self.base, ["story kits", "unused"])

    def test_robots_by_role(self):
        agents = self.run_check()["robots_txt"]["agents"]
        self.assertEqual(agents["GPTBot"], {"role": "training", "blocked_pages": ["/", "/private"]})
        self.assertEqual(agents["PerplexityBot"], {"role": "search", "blocked_pages": ["/private"]})
        self.assertEqual(agents["OAI-SearchBot"]["blocked_pages"], [])

    def test_probes(self):
        home = self.run_check()["probes"][0]
        blocked = home["agents"]["OAI-SearchBot"]
        self.assertEqual((blocked["status"], blocked["cf_mitigated"], blocked["challenge_page"]), (403, "challenge", True))
        self.assertTrue(home["agents"]["ClaudeBot"]["same_size_as_browser"])

    def test_llms_txt(self):
        r = self.run_check()
        lt = r["llms_txt"]
        self.assertEqual((lt["present"], lt["title"], lt["links"]), (True, "Example Shop", 4))
        self.assertEqual(lt["broken"], ["/old"])
        self.assertEqual(lt["noindex"], ["/editor"])
        self.assertEqual(lt["retired"], ["story kits"])
        self.assertEqual(lt["not_in_llms"], ["/", "/about"])
        self.assertEqual(lt["not_in_sitemap"], ["/editor", "/old"])
        text = gc.render(r)
        self.assertIn("G2 llms.txt 200", text)
        self.assertIn("PerplexityBot (search): blocked on ['/private']", text)

    def test_cli(self):
        self.assertEqual(gc.main(["--site", "https://example.com", "--base", self.base, "--format", "json"]), 0)


if __name__ == "__main__":
    unittest.main()
