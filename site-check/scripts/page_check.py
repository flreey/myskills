#!/usr/bin/env python3
"""Read-only evidence for one page's SEO acceptance, from the raw HTML a crawler receives.

    python3 page_check.py --url <url> [--keyword "phrase"]... [--brief <brief.json>] [--format text|json]

Collects what checks 1-4 of site-check need: where the target phrases sit (title, description, H1,
headings, opening text, URL), the FAQ questions on the page next to the brief's questions, whether
the content is in the server HTML or only appears after JavaScript, and what robots.txt, meta robots,
X-Robots-Tag and OpenAI user-agent probes show. It never writes files. Judgement stays with the model.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

SCHEMA = "site-check/page@1"
MAX_BYTES = 3_000_000
TIMEOUT = 20
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
# Tokens from OpenAI's bot documentation; the full strings are probes, not exact copies.
OPENAI_BOTS = {
    "OAI-SearchBot": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "ChatGPT-User": "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
    "GPTBot": "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)",
}
CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-chl-|challenge-platform|Attention Required!|captcha", re.I)
OPENING_WORDS = 150
SKIP_TEXT = {"script", "style", "template", "svg", "noscript"}
HEADINGS = {"h1", "h2", "h3"}
CHROME = {"nav", "header", "footer", "aside"}
QUESTION = re.compile(r"^(.{6,200}?[?？])[^\w?？]*$")
STOPWORDS = set("a an and are be can do does for how i in is it my of on or should the this to what when where "
                "which who why will with you your".split())


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta = {}
        self.canonical = None
        self.headings = []        # (tag, text)
        self.jsonld = []
        self.text = []            # (text, zone): zone is main, chrome (nav/header/footer/aside) or body
        self.scripts = 0
        self._stack = []
        self._buf = None          # collects text for title / heading / json-ld
        self._kind = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
            return
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonical = a.get("href")
            return
        if tag in {"br", "img", "input", "hr"}:
            return
        self._stack.append(tag)
        if tag == "script":
            self.scripts += 1
            if a.get("type", "").lower() == "application/ld+json":
                self._buf, self._kind = [], "jsonld"
        elif tag in HEADINGS or tag == "title":
            self._buf, self._kind = [], tag

    def handle_endtag(self, tag):
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass
        if self._kind and (tag == self._kind or (self._kind == "jsonld" and tag == "script")):
            value = " ".join("".join(self._buf).split())
            if self._kind == "title":
                self.title = value
            elif self._kind == "jsonld":
                self.jsonld.append("".join(self._buf))
            else:
                self.headings.append((self._kind, value))
            self._buf, self._kind = None, None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)
        if not any(t in SKIP_TEXT for t in self._stack) and "title" not in self._stack and data.strip():
            zone = "main" if "main" in self._stack else "chrome" if CHROME & set(self._stack) else "body"
            self.text.append((" ".join(data.split()), zone))

    def content(self):
        """Main content: <main> when the page has one, else everything outside nav/header/footer/aside."""
        main = [t for t, z in self.text if z == "main"]
        return " ".join(main or [t for t, z in self.text if z == "body"])

    def questions(self):
        """Visible text nodes that read as a question, trailing icons stripped."""
        found = [m.group(1) for t, z in self.text if z != "chrome" for m in [QUESTION.match(t)] if m]
        return list(dict.fromkeys(found))


def fetch(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES)
            status, headers, final = r.status, r.headers, r.geturl()
    except urllib.error.HTTPError as e:
        body, status, headers, final = e.read(MAX_BYTES), e.code, e.headers, url
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"ok": False, "error": str(getattr(e, "reason", e)), "status": None}
    charset = headers.get_content_charset() or "utf-8"
    return {"ok": True, "status": status, "final_url": final, "html": body.decode(charset, "replace"),
            "x_robots_tag": headers.get("X-Robots-Tag"), "server": headers.get("Server"),
            "cf_mitigated": headers.get("cf-mitigated"), "content_type": headers.get("Content-Type")}


def norm(s):
    return " ".join(re.findall(r"\w+", s.lower()))


def tokens(s):
    return set(norm(s).split())


def contains(text, phrase):
    """exact: the phrase appears in order; all_words: every word appears somewhere."""
    t, p = norm(text), norm(phrase)
    if not p:
        return "no"
    if f" {p} " in f" {t} ":
        return "exact"
    if re.search(r"[぀-ヿ㐀-鿿]", p) and p.replace(" ", "") in t.replace(" ", ""):
        return "exact"
    return "all_words" if tokens(p) <= tokens(text) else "no"


def faq_from_jsonld(blocks):
    questions, types = [], []    # questions: (name, answer text)

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            t = node.get("@type")
            types.extend(t if isinstance(t, list) else [t] if t else [])
            if t == "Question" and isinstance(node.get("name"), str):
                answer = node.get("acceptedAnswer") or {}
                text = answer.get("text", "") if isinstance(answer, dict) else ""
                questions.append((" ".join(node["name"].split()), re.sub(r"<[^>]+>", " ", text)))
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
    for raw in blocks:
        try:
            walk(json.loads(raw))
        except ValueError:
            types.append("(invalid JSON-LD)")
    return questions, sorted(set(types))


def load_brief(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    phrasings, questions, subneeds = [], [], []
    for c in data.get("clusters", []):
        if c.get("role") == "primary":
            phrasings += [p["keyword"] for p in c.get("phrasings", [])[:3]]
        questions += c.get("questions", [])
        subneeds += [s["attribute"] for s in c.get("subneeds", []) if s.get("status") in ("covered", "write_it")]
    return {"page": data.get("page"), "phrasings": phrasings, "questions": questions, "subneeds": subneeds}


def match_questions(wanted, on_page):
    """Lexical pre-sort only: overlap of words. The model decides what a question really covers."""
    out = []
    for q in wanted:
        best, score = None, 0.0
        for p in on_page:
            a, b = tokens(q) - STOPWORDS, tokens(p) - STOPWORDS
            s = len(a & b) / len(a | b) if a | b else 0
            if s > score:
                best, score = p, s
        out.append({"question": q, "closest_on_page": best, "overlap": round(score, 2),
                    "hint": "likely_answered" if score >= 0.5 else "check" if score >= 0.34 else "likely_missing"})
    return out


def robots(url):
    parts = urllib.parse.urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    got = fetch(robots_url, BROWSER_UA)
    result = {"url": robots_url, "status": got.get("status"), "agents": {}}
    if not got["ok"] or got["status"] >= 400:
        result["note"] = "no robots.txt read: crawlers treat 4xx as allow-all; 5xx may stop crawling"
        return result
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(got["html"].splitlines())
    for name in list(OPENAI_BOTS) + ["Googlebot", "Bingbot"]:
        result["agents"][name] = "allowed" if rp.can_fetch(name, url) else "disallowed"
    return result


def check(url, keywords, brief_path=None):
    brief = load_brief(brief_path) if brief_path else None
    if brief and not keywords:
        keywords = brief["phrasings"]
    raw = fetch(url, BROWSER_UA)
    report = {"schema": SCHEMA, "url": url, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "fetch": {k: v for k, v in raw.items() if k != "html"}}
    if not raw["ok"]:
        return report
    page = Page()
    page.feed(raw["html"])
    text = page.content()
    visible = norm(" ".join(t for t, _ in page.text))
    words = text.split()
    opening = " ".join(words[:OPENING_WORDS])
    h1 = [t for tag, t in page.headings if tag == "h1"]
    subheads = [t for tag, t in page.headings if tag != "h1"]
    path = urllib.parse.unquote(urllib.parse.urlsplit(raw["final_url"]).path).replace("-", " ").replace("/", " ")
    report["page"] = {"title": page.title, "description": page.meta.get("description"),
                      "meta_robots": page.meta.get("robots"), "canonical": page.canonical,
                      "h1": h1, "headings": [f"{tag}: {t}" for tag, t in page.headings][:60],
                      "opening_text": " ".join(words[:40]), "server_text_words": len(words), "scripts": page.scripts}
    report["keywords"] = [{
        "keyword": k,
        "title": contains(page.title, k), "description": contains(page.meta.get("description") or "", k),
        "h1": contains(" ".join(h1), k), "subheadings": sum(contains(h, k) != "no" for h in subheads),
        "opening_text": contains(opening, k), "url": contains(path, k),
        "body_exact_count": f" {norm(text)} ".count(f" {norm(k)} ") if norm(k) else 0,
    } for k in keywords]
    ld_questions, ld_types = faq_from_jsonld(page.jsonld)
    on_page = page.questions()
    report["faq"] = {"visible_questions": on_page, "faqpage_schema_questions": [q for q, _ in ld_questions],
                     "schema_only": [q for q, _ in ld_questions if norm(q) not in visible],
                     "schema_answer_not_visible": [q for q, a in ld_questions
                                                   if norm(q) in visible and norm(a)[:80] not in visible],
                     "jsonld_types": ld_types}
    if brief:
        report["brief"] = {"page": brief["page"], "subneeds": brief["subneeds"],
                           "questions": match_questions(brief["questions"], on_page)}
    shell = len(words) < 80 and page.scripts >= 3
    report["rendering"] = {
        "server_text_words": len(words), "h1_in_server_html": bool(h1),
        "verdict": "client_rendered_shell" if shell else "thin_server_html" if len(words) < 200 else "server_html_has_content",
        "next": "compare with the rendered page text; anything only there is invisible to crawlers that do not run JS"}
    report["crawlers"] = {"robots_txt": robots(url), "x_robots_tag": raw.get("x_robots_tag"),
                          "meta_robots": page.meta.get("robots"), "probes": {}}
    for name, ua in OPENAI_BOTS.items():
        got = fetch(url, ua)
        html = got.get("html") or ""
        report["crawlers"]["probes"][name] = {
            "status": got.get("status"), "error": got.get("error"), "cf_mitigated": got.get("cf_mitigated"),
            "challenge_page": bool(CHALLENGE.search(html[:20000])),
            "same_size_as_browser": abs(len(html) - len(raw["html"])) < max(500, len(raw["html"]) // 10)}
    report["crawlers"]["limits"] = ("probes send the user-agent from this machine; firewalls that verify bots by "
                                    "IP can still treat the real crawler differently. Ask ChatGPT to open the URL.")
    return report


def render(r):
    out = [f"site-check page: {r['url']}  ({r['checked_at']})"]
    f = r["fetch"]
    if not f.get("ok"):
        return "\n".join(out + [f"fetch failed: {f.get('error')}"])
    p = r["page"]
    out += [f"status {f['status']}  final {f['final_url']}",
            f"title: {p['title']!r}", f"description: {p['description']!r}", f"h1: {p['h1']}",
            f"opening: {p['opening_text']!r}",
            f"canonical: {p['canonical']}  meta robots: {p['meta_robots']}  X-Robots-Tag: {r['crawlers']['x_robots_tag']}",
            "", "1 keywords (exact / all_words / no):"]
    for k in r["keywords"] or [{"keyword": "(none given)"}]:
        if "title" in k:
            out.append(f"  {k['keyword']!r}: title {k['title']}, description {k['description']}, h1 {k['h1']}, "
                       f"subheadings {k['subheadings']}, opening {k['opening_text']}, url {k['url']}, body x{k['body_exact_count']}")
        else:
            out.append("  " + k["keyword"])
    fq = r["faq"]
    out += ["", f"2 FAQ: {len(fq['visible_questions'])} visible questions, {len(fq['faqpage_schema_questions'])} in FAQPage schema"]
    out += [f"  - {q}" for q in fq["visible_questions"][:30]]
    if fq["schema_only"]:
        out.append(f"  schema-only (not visible): {fq['schema_only']}")
    if fq["schema_answer_not_visible"]:
        out.append(f"  schema answer not in server HTML text: {fq['schema_answer_not_visible']}")
    if "brief" in r:
        out.append(f"  brief questions ({r['brief']['page']}):")
        out += [f"  [{q['hint']}] {q['question']}  ~ {q['closest_on_page']}" for q in r["brief"]["questions"]]
    rd = r["rendering"]
    out += ["", f"3 rendering: {rd['verdict']} ({rd['server_text_words']} words in server HTML, h1 {rd['h1_in_server_html']})"]
    rb = r["crawlers"]["robots_txt"]
    out += ["", f"4 crawlers: robots.txt {rb['status']} {rb.get('note', '')}".rstrip()]
    out += [f"  {a}: {v}" for a, v in rb["agents"].items()]
    for name, pr in r["crawlers"]["probes"].items():
        out.append(f"  probe {name}: status {pr['status']}{' ' + pr['error'] if pr['error'] else ''}, "
                   f"cf-mitigated {pr['cf_mitigated']}, challenge {pr['challenge_page']}, same size {pr['same_size_as_browser']}")
    out.append(f"  limits: {r['crawlers']['limits']}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="site-check: raw-HTML evidence for one page")
    ap.add_argument("--url", required=True)
    ap.add_argument("--keyword", action="append", default=[], help="target phrase; repeatable")
    ap.add_argument("--brief", help="site-plan brief JSON (seo/work/briefs/<slug>.json)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    a = ap.parse_args(argv)
    r = check(a.url, a.keyword, a.brief)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.format == "json" else render(r))
    return 0 if r["fetch"].get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
