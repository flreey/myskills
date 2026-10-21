#!/usr/bin/env python3
"""Tests for page_check.py: python3 -B -m unittest discover -s <skill>/scripts -p 'test_*.py'"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("site_check_page", HERE / "page_check.py")
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

FILLER = " ".join(["Generate secure random passwords in your browser with length and symbol options."] * 30)
SSR = f"""<!doctype html><html><head><title>Random Password Generator – Free and Secure</title>
<meta name="description" content="Free random password generator that runs in your browser.">
<link rel="canonical" href="/random-password-generator">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
 {{"@type":"Question","name":"Is this password generator safe?","acceptedAnswer":{{"@type":"Answer","text":"Yes. Generation happens locally."}}}},
 {{"@type":"Question","name":"Do you store passwords?","acceptedAnswer":{{"@type":"Answer","text":"No."}}}}]}}</script>
</head><body><nav>Home Tools Pricing</nav><main><h1>Random Password Generator</h1><p>Use this random password generator to create strong passwords. {FILLER}</p>
<h2>How long should a password be?</h2><p>At least 16 characters.</p>
<details><summary>Is this password generator safe?<span aria-hidden="true">+</span></summary><p>Yes, nothing leaves your browser.</p></details>
<p>Generate now</p></main><footer>Is this a footer question?</footer></body></html>"""
SPA = """<!doctype html><html><head><title>App</title><script src="/a.js"></script><script src="/b.js"></script>
<script src="/c.js"></script></head><body><div id="root"></div></body></html>"""
ROBOTS = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        ua = self.headers.get("User-Agent", "")
        if self.path == "/robots.txt":
            return self.send(200, ROBOTS, "text/plain")
        if "OAI-SearchBot" in ua:
            return self.send(403, "<title>Just a moment...</title>", "text/html", {"cf-mitigated": "challenge"})
        if self.path == "/spa":
            return self.send(200, SPA, "text/html")
        return self.send(200, SSR, "text/html; charset=utf-8")

    def send(self, status, body, ctype, extra=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)


class PageCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_keyword_placement_and_faq(self):
        r = pc.check(self.base + "/random-password-generator", ["random password generator", "strong password"])
        k = {x["keyword"]: x for x in r["keywords"]}
        self.assertEqual(k["random password generator"]["title"], "exact")
        self.assertEqual(k["random password generator"]["h1"], "exact")
        self.assertEqual(k["random password generator"]["url"], "exact")
        self.assertEqual(k["strong password"]["title"], "no")
        self.assertEqual(r["faq"]["visible_questions"], ["How long should a password be?", "Is this password generator safe?"])
        self.assertEqual(r["faq"]["schema_answer_not_visible"], ["Is this password generator safe?"])
        self.assertTrue(r["page"]["opening_text"].startswith("Random Password Generator Use this"))
        self.assertEqual(r["faq"]["schema_only"], ["Do you store passwords?"])
        self.assertIn("FAQPage", r["faq"]["jsonld_types"])
        self.assertEqual(r["rendering"]["verdict"], "server_html_has_content")
        self.assertIn("Use this random password generator", pc.render(r))

    def test_client_rendered_shell(self):
        r = pc.check(self.base + "/spa", [])
        self.assertEqual(r["rendering"]["verdict"], "client_rendered_shell")
        self.assertFalse(r["rendering"]["h1_in_server_html"])

    def test_robots_and_probes(self):
        r = pc.check(self.base + "/x", [])
        agents = r["crawlers"]["robots_txt"]["agents"]
        self.assertEqual(agents["GPTBot"], "disallowed")
        self.assertEqual(agents["OAI-SearchBot"], "allowed")
        probe = r["crawlers"]["probes"]["OAI-SearchBot"]
        self.assertEqual((probe["status"], probe["cf_mitigated"], probe["challenge_page"]), (403, "challenge", True))
        self.assertTrue(r["crawlers"]["probes"]["ChatGPT-User"]["same_size_as_browser"])

    def test_brief_questions(self):
        brief = {"page": "/random-password-generator", "clusters": [{
            "role": "primary", "phrasings": [{"keyword": "random password generator"}],
            "questions": ["is a password generator safe", "how to remember a random password"],
            "subneeds": [{"attribute": "length=16", "status": "covered"}]}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(brief, f)
        r = pc.check(self.base + "/random-password-generator", [], f.name)
        Path(f.name).unlink()
        self.assertEqual(r["keywords"][0]["keyword"], "random password generator")
        hints = {q["question"]: q["hint"] for q in r["brief"]["questions"]}
        self.assertEqual(hints["is a password generator safe"], "likely_answered")
        self.assertEqual(hints["how to remember a random password"], "likely_missing")

    def test_unreachable(self):
        self.assertEqual(pc.main(["--url", "http://127.0.0.1:9/none", "--format", "json"]), 1)


if __name__ == "__main__":
    unittest.main()
