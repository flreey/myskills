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
ROBOTS = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: OAI-SearchBot\nDisallow: /private\n\nUser-agent: *\nAllow: /\n"
NOINDEX = """<html><head><title>{name}</title><meta name="robots" content="noindex"></head>
<body><main><h1>{name}</h1><p>{filler}</p><details><summary>About this tool</summary>
<h3>How do I use {lower}?</h3><p>Press go.</p>
<h3>Will changing settings replace my result?</h3><p>No.</p></details></main></body></html>"""
# The index names the production host, as a local build's sitemap does; the sweep reads it from --base.
INDEX = """<?xml version="1.0"?><sitemapindex><sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap></sitemapindex>"""
PAGES = """<urlset>""" + "".join(f"<url><loc>https://example.com{p}</loc></url>" for p in
                                  ["/random-password-generator", "/spa", "/tools/alpha", "/tools/beta", "/tools/gamma", "/private",
                                   "/products/alpha", "/products/beta", "/products/gamma"]) + "</urlset>"
# A shop template: breadcrumb levels differ from BreadcrumbList, images lack alt text, a label heading, dated copy,
# a retired name, links to a noindex and a missing page. /products/beta's H1 drops the title's lead phrase.
PRODUCT = """<!doctype html><html><head><title>{name} Chart Printable for Kids: Personalized</title>
<meta name="description" content="A {name} chart."><meta property="og:image" content="/og.png">
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[
 {{"@type":"Organization","@id":"/#org","name":"Shop","sameAs":["https://www.etsy.com/shop/example"]}},
 {{"@type":"WebPage","@id":"/p#webpage","mainEntity":{{"@id":"/p#primary"}},"dateModified":"2026-01-01"}},
 {{"@type":"Product","@id":"/p#primary","name":"{h1}"}},
 {{"@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home"}},
  {{"@type":"ListItem","position":2,"name":"{h1}"}}]}}]}}</script></head>
<body><main><nav aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/everyday">Everyday</a>
<span aria-hidden="true">/</span><span>{h1}</span></nav><h1>{h1}</h1><p>{filler}</p>
<h2>What’s inside</h2><img src="/a.png" alt=""><img src="/b.png"><img src="/c.png" alt="A weekly chart">
<div aria-hidden="true"><img src="/deco.png" alt=""></div><h3>{name} card</h3>
<h2>Questions</h2><p>The sale ends in 12 days. Also in the Old Bundle.</p>
<a href="/hidden">Make yours</a> <a href="/gone">Old link</a> <a href="/products/beta">Beta</a></main></body></html>"""
HIDDEN = """<html><head><title>Editor</title><meta name="robots" content="noindex"></head><body><h1>Editor</h1></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/robots.txt":
            return self.send(200, ROBOTS, "text/plain")
        if self.path == "/sitemap.xml":
            return self.send(200, INDEX, "application/xml")
        if self.path == "/sitemap-pages.xml":
            return self.send(200, PAGES, "application/xml")
        if self.path.startswith("/tools/"):
            name = self.path.rsplit("/", 1)[1].title() + " Widget"
            return self.send(200, NOINDEX.format(name=name, lower=name.lower(), filler=FILLER), "text/html")
        if self.path.startswith("/products/"):
            name = self.path.rsplit("/", 1)[1].title()
            h1 = "Something Else Entirely" if name == "Beta" else f"{name} Chart Printable"
            return self.send(200, PRODUCT.format(name=name, h1=h1, filler=FILLER), "text/html")
        if self.path == "/hidden":
            return self.send(200, HIDDEN, "text/html")
        if self.path == "/gone":
            return self.send(404, "<title>Not found</title>", "text/html")
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
        self.assertEqual(r["faq"]["collapsed_questions"], [])  # one accordion item: its question shows
        self.assertTrue(r["page"]["opening_text"].startswith("Random Password Generator Use this"))
        self.assertEqual(r["faq"]["schema_only"], ["Do you store passwords?"])
        self.assertIn("FAQPage", r["faq"]["jsonld_types"])
        self.assertEqual(r["rendering"]["verdict"], "server_html_has_content")
        self.assertIn("Use this random password generator", pc.render(r))

    def test_client_rendered_shell(self):
        r = pc.check(self.base + "/spa", [])
        self.assertEqual(r["rendering"]["verdict"], "client_rendered_shell")
        self.assertFalse(r["rendering"]["h1_in_server_html"])

    def test_robots_for_search_crawlers(self):
        r = pc.check(self.base + "/x", [])
        agents = r["crawlers"]["robots_txt"]["agents"]
        self.assertEqual(agents, {"Googlebot": "allowed", "Bingbot": "allowed", "OAI-SearchBot": "allowed"})
        self.assertNotIn("probes", r["crawlers"])   # user-agent probes and ChatGPT belong to site-geo
        blocked = pc.check(self.base + "/private", [])["crawlers"]["robots_txt"]["agents"]
        self.assertEqual(blocked["OAI-SearchBot"], "disallowed")

    def test_page_facts(self):
        r = pc.check(self.base + "/products/beta", [], retired=["old bundle", "never used"])
        f = r["facts"]
        self.assertEqual(f["title_lead"], ["beta", "chart", "printable", "kid"])
        self.assertEqual(f["title_h1"], 0.0)
        self.assertEqual(f["label_headings"], ["Questions"])
        self.assertEqual((f["images"]["content"], f["images"]["missing_alt"]), (3, 2))   # the aria-hidden image is decoration
        self.assertEqual(f["breadcrumb"], {"visible": ["Home", "Everyday", "Something Else Entirely"], "structured_items": 2})
        self.assertEqual(f["structured"]["primary_types"], ["Product"])
        self.assertEqual(f["structured"]["organization"]["same_as"], ["https://www.etsy.com/shop/example"])
        self.assertEqual(f["relative_dates"]["found"], ["in 12 days"])
        self.assertEqual(f["retired"], ["old bundle"])
        self.assertEqual(f["issues"], ["title_h1_drift", "label_heading", "images_without_alt", "breadcrumb_mismatch",
                                       "stale_relative_dates", "retired_term"])
        alpha = pc.check(self.base + "/products/alpha", [])["facts"]
        self.assertEqual(alpha["title_h1"], 0.75)
        self.assertNotIn("title_h1_drift", alpha["issues"])
        self.assertIn("5 page facts", pc.render(r))

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

    def test_sweep_groups_issues_by_pattern(self):
        r = pc.sweep(self.base + "/sitemap.xml", base=self.base)
        self.assertEqual(r["urls"], 9)
        self.assertTrue(all(u["url"].startswith(self.base) for u in r["pages"]))
        issues = r["issues"]
        self.assertEqual(issues["noindex"]["patterns"][0], {"pattern": "/tools/*", "hit": 3, "of": 3, "urls": [
            self.base + "/tools/alpha", self.base + "/tools/beta", self.base + "/tools/gamma"]})
        self.assertEqual(issues["faq_hidden"]["patterns"][0]["hit"], 3)
        self.assertNotIn("faq_hidden", next(p for p in r["pages"] if p["url"].endswith("/random-password-generator"))["issues"])
        shapes = {t["question_shape"]: t["pages"] for t in r["faq"]["templated_questions"]}
        self.assertEqual(shapes, {"how do i use {page}": 3, "will changing settings replace my result": 3})
        self.assertEqual(issues["client_rendered_shell"]["count"], 1)
        self.assertEqual(issues["search_bot_disallowed"]["patterns"][0]["urls"], [self.base + "/private"])
        self.assertEqual(issues["faq_schema_only"]["count"], 2)
        self.assertEqual(issues["faq_answer_not_in_html"]["count"], 2)
        self.assertEqual(r["site"]["robots_txt"]["agents"]["Googlebot"], "allowed")
        self.assertNotIn("probes", r["site"])
        self.assertEqual(issues["title_h1_drift"]["patterns"][0]["urls"], [self.base + "/products/beta"])
        self.assertEqual(issues["breadcrumb_mismatch"]["patterns"][0], {"pattern": "/products/*", "hit": 3, "of": 3, "urls": [
            self.base + "/products/alpha", self.base + "/products/beta", self.base + "/products/gamma"]})
        self.assertEqual(issues["links_to_noindex"]["count"], 3)
        self.assertEqual(issues["links_to_error"]["count"], 3)
        outside = {x["path"]: x["status"] for x in r["links"]["outside_sitemap"]}
        self.assertEqual(outside, {"/hidden": "noindex", "/gone": "error"})
        inlinks = {x["url"]: x["content_inlinks"] for x in r["links"]["lowest_inlinks"]}
        self.assertEqual(inlinks[self.base + "/products/beta"], 2)
        self.assertEqual(r["site"]["organization"]["same_as"], ["https://www.etsy.com/shop/example"])
        self.assertEqual(r["site"]["primary_types"]["Product"]["pages"], 3)
        headings = {t["heading"]: t["pages"] for t in r["templated_headings"]}
        self.assertEqual((headings["What’s inside"], headings["Questions"]), (3, 3))
        self.assertNotIn("Alpha card", headings)   # H3 card names are not section titles
        dup = [d["pages"] for d in r["near_duplicates"]]
        self.assertIn([self.base + "/products/alpha", self.base + "/products/beta"], dup)
        text = pc.render_sweep(r)
        self.assertIn("likely a shared template", text)
        self.assertEqual(pc.main(["--sitemap", self.base + "/sitemap-pages.xml", "--base", self.base, "--limit", "2"]), 0)

    def test_pool_questions(self):
        rows = ["is a random password safe", "is a random password safe", "how long should a password be",
                "how to spell generator", "password generator", "what is a uuid"]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(json.dumps({"keyword": k}) for k in rows))
        found = pc.pool_questions(f.name, ["random password generator"])
        self.assertEqual(found, ["is a random password safe", "how long should a password be"])
        r = pc.check(self.base + "/random-password-generator", ["random password generator"], pool_path=f.name)
        Path(f.name).unlink()
        hints = {q["question"]: q["hint"] for q in r["pool_questions"]}
        self.assertEqual(hints["how long should a password be"], "likely_answered")

    def test_unreachable(self):
        self.assertEqual(pc.main(["--url", "http://127.0.0.1:9/none", "--format", "json"]), 1)


if __name__ == "__main__":
    unittest.main()
