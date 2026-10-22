#!/usr/bin/env python3
"""Read-only evidence for one page's SEO acceptance, from the raw HTML a crawler receives.

    python3 page_check.py --url <url> [--keyword "phrase"]... [--brief <brief.json>] [--pool <observations.jsonl>]
                          [--retired "phrase"]... [--format text|json]
    python3 page_check.py --sitemap <url|file> [--base <origin>] [--limit N] [--retired "phrase"]... [--format text|json]

Collects what the page checks of site-check need: where the target phrases sit (title, description, H1,
headings, opening text, URL), whether the H1 keeps the title's lead phrase, the FAQ questions on the
page next to the brief's questions, whether the content is in the server HTML or only appears after
JavaScript, robots for search crawlers, structured data types, breadcrumbs, image alt text and dated
copy. With --sitemap it sweeps every listed URL for the mechanical facts only and adds the site-wide
ones: issues grouped by URL pattern, templated FAQs and headings, near-duplicate pages, internal links
(inlinks, dead ends, links to noindex or broken pages) and the Organization's sameAs. AI-search
probes (OpenAI user-agents, llms.txt, ChatGPT) belong to site-geo. It never writes files. Judgement
stays with the model.
"""
import argparse
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

SCHEMA = "site-check/page@2"
SWEEP_SCHEMA = "site-check/sweep@2"
MAX_BYTES = 3_000_000
TIMEOUT = 20
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
# Crawlers that decide whether a page can appear in search results (Google, Bing, ChatGPT search).
SEARCH_BOTS = ["Googlebot", "Bingbot", "OAI-SearchBot"]
OPENING_WORDS = 150
SKIP_TEXT = {"script", "style", "template", "svg", "noscript"}
HEADINGS = {"h1", "h2", "h3"}
CHROME = {"nav", "header", "footer", "aside"}
QUESTION = re.compile(r"^(.{6,200}?[?？])[^\w?？]*$")
# Words that name the kind of tool, not its subject; ignored when matching pool questions to a page.
GENERIC = {"random", "generator", "generate", "free", "online", "tool", "tools", "maker", "picker", "best"}
QUESTION_START = re.compile(r"^(how|what|whats|what's|can|is|are|does|do|why|which|when|where|should|will|who)\b", re.I)
TEMPLATE_MIN_PAGES = 3
STOPWORDS = set("a an and are be by can do does for from how i in is it my of on or should the this to what when where "
                "which who why will with you your".split())
# Structured-data nodes that frame a page rather than say what it is about.
FRAME_TYPES = {"Organization", "WebSite", "WebPage", "BreadcrumbList", "FAQPage", "Question", "Answer", "ListItem",
               "Person", "ImageObject", "Offer", "AggregateOffer", "Brand", "SearchAction", "EntryPoint"}
TITLE_LEAD_WORDS = 4          # the title's lead phrase: its first content words before ':', '|', ',' or a dash
TITLE_H1_MIN = 0.7            # share of the lead words the H1 must keep
ALT_MIN_IMAGES = 3            # content images before missing alt text counts as an issue
RELATIVE_DATE = re.compile(r"\b(?:in \d+ days?|\d+ days? (?:left|to go|away))\b", re.I)
# One-word H2s that label a UI block rather than name a topic.
LABELS = {"questions", "faq", "faqs", "filter", "filters", "menu", "search", "results", "overview", "details",
          "description", "features", "reviews", "more", "related", "contents", "summary", "info", "information",
          "help", "sort", "share", "resources", "links", "inspiration", "extras"}
SHINGLE = 5
# Jaccard similarity of 5-word shingles. Set on tinywonderpost.com (2026-10-22): sibling chart pages built from one
# template scored 0.37-0.41 and two letter sets 0.33; unrelated pages stayed at or under 0.29.
NEAR_DUPLICATE = 0.33
MAX_LINK_TARGETS = 40         # linked URLs outside the sitemap fetched once each
SKIP_LINK = re.compile(r"\.(?:png|jpe?g|webp|gif|svg|pdf|zip|xml|txt|ico|css|js|json|mp4|webm)$", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta = {}
        self.canonical = None
        self.headings = []        # (tag, text)
        self.heading_zones = []   # zone of each heading
        self.jsonld = []
        self.text = []            # (text, zone): zone is main, chrome (nav/header/footer/aside) or body
        self.collapsed = []       # per text node: inside a closed <details>, outside that details' <summary>
        self.images = []          # {"alt": str or None, "src", "zone", "hidden"}
        self.links = []           # {"href", "text", "zone"}
        self.breadcrumb = []      # visible breadcrumb items, separators dropped
        self._details = []        # open <details> elements: {"open": bool, "in_summary": bool}
        self.scripts = 0
        self._stack = []
        self._hidden = []         # per open element: aria-hidden or role=presentation
        self._buf = None          # collects text for title / heading / json-ld
        self._kind = None
        self._zone = None
        self._link = None
        self._crumb_depth = None

    def zone(self):
        return "main" if "main" in self._stack else "chrome" if CHROME & set(self._stack) else "body"

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
        if tag == "img":
            self.images.append({"alt": a.get("alt") if "alt" in a else None, "src": a.get("src", ""), "zone": self.zone(),
                                "hidden": any(self._hidden) or a.get("aria-hidden") == "true"
                                or a.get("role") == "presentation"})
            return
        if tag in {"br", "input", "hr"}:
            return
        if tag == "nav" and "breadcrumb" in a.get("aria-label", "").lower() and self._crumb_depth is None:
            self._crumb_depth = len(self._stack)
        self._stack.append(tag)
        self._hidden.append(a.get("aria-hidden") == "true" or a.get("role") == "presentation")
        if tag == "details":
            self._details.append({"open": "open" in a, "in_summary": False})
        elif tag == "summary" and self._details:
            self._details[-1]["in_summary"] = True
        if tag == "a" and a.get("href"):
            # A link in nav/header/footer/aside is site chrome even inside <main> (breadcrumbs, tables of contents).
            self._link = {"href": a["href"], "text": [], "zone": "chrome" if CHROME & set(self._stack) else self.zone()}
        if tag == "script":
            self.scripts += 1
            if a.get("type", "").lower() == "application/ld+json":
                self._buf, self._kind = [], "jsonld"
        elif tag in HEADINGS or tag == "title":
            self._buf, self._kind, self._zone = [], tag, self.zone()

    def handle_endtag(self, tag):
        if tag == "summary" and self._details:
            self._details[-1]["in_summary"] = False
        elif tag == "details" and self._details:
            self._details.pop()
        if tag == "a" and self._link is not None:
            self._link["text"] = " ".join(" ".join(self._link["text"]).split())
            self.links.append(self._link)
            self._link = None
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                self._hidden.pop()
            self._hidden.pop()
            if self._crumb_depth is not None and len(self._stack) <= self._crumb_depth:
                self._crumb_depth = -1   # one breadcrumb per page
        if self._kind and (tag == self._kind or (self._kind == "jsonld" and tag == "script")):
            value = " ".join("".join(self._buf).split())
            if self._kind == "title":
                self.title = value
            elif self._kind == "jsonld":
                self.jsonld.append("".join(self._buf))
            else:
                self.headings.append((self._kind, value))
                self.heading_zones.append(self._zone)
            self._buf, self._kind = None, None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)
        if self._link is not None:
            self._link["text"].append(data)
        if self._crumb_depth not in (None, -1) and data.strip() and data.strip() not in {"/", "›", "»", ">", "|", "·"}:
            self.breadcrumb.append(" ".join(data.split()))
        if not any(t in SKIP_TEXT for t in self._stack) and "title" not in self._stack and data.strip():
            self.text.append((" ".join(data.split()), self.zone()))
            self.collapsed.append(any(not d["open"] and not d["in_summary"] for d in self._details))

    def content(self):
        """Main content: <main> when the page has one, else everything outside nav/header/footer/aside."""
        main = [t for t, z in self.text if z == "main"]
        return " ".join(main or [t for t, z in self.text if z == "body"])

    def subheadings(self):
        """H2s outside nav, header, footer and aside: the page's section titles (H3s are often card names)."""
        return [t for (tag, t), z in zip(self.headings, self.heading_zones) if tag == "h2" and z != "chrome"]

    def questions(self, collapsed=None):
        """Text nodes that read as a question, trailing icons stripped. collapsed=True keeps only the
        ones a visitor sees only after opening a closed <details>; False only the ones shown on load."""
        found = [m.group(1) for (t, z), c in zip(self.text, self.collapsed)
                 if z != "chrome" and (collapsed is None or c == collapsed) for m in [QUESTION.match(t)] if m]
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
            "content_type": headers.get("Content-Type")}


def norm(s):
    return " ".join(re.findall(r"\w+", s.lower()))


def tokens(s):
    return set(norm(s).split())


def stem(word):
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


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


def title_lead(title):
    """The title's lead phrase: its first content words before ':', '|', ',', or a spaced dash."""
    head = re.split(r"\s[|–—-]\s|[:|,]", title)[0]
    words = [stem(w) for w in norm(head).split() if w not in STOPWORDS]
    return words[:TITLE_LEAD_WORDS]


def title_h1(title, h1):
    """Share of the title's lead words the H1 keeps; None when there is nothing to compare."""
    lead = title_lead(title)
    if not lead or not h1:
        return None
    kept = {stem(w) for w in norm(h1).split()}
    return round(sum(w in kept for w in lead) / len(lead), 2)


def ld_nodes(blocks):
    """Every JSON-LD node, @graph flattened; invalid blocks become {"@type": "(invalid JSON-LD)"}."""
    out = []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            out.append(node)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
    for raw in blocks:
        try:
            walk(json.loads(raw))
        except ValueError:
            out.append({"@type": "(invalid JSON-LD)"})
    return out


def types_of(node):
    t = node.get("@type")
    return t if isinstance(t, list) else [t] if t else []


def faq_from_jsonld(blocks):
    questions, types = [], []    # questions: (name, answer text)
    for node in ld_nodes(blocks):
        types.extend(types_of(node))
        if node.get("@type") == "Question" and isinstance(node.get("name"), str):
            answer = node.get("acceptedAnswer") or {}
            text = answer.get("text", "") if isinstance(answer, dict) else ""
            questions.append((" ".join(node["name"].split()), re.sub(r"<[^>]+>", " ", text)))
    return questions, sorted(set(types))


def structured(page):
    """What the structured data says the page is: primary types (WebPage.mainEntity, else the non-frame
    nodes), breadcrumb depth, dateModified and the Organization's sameAs."""
    nodes = ld_nodes(page.jsonld)
    by_id = {n.get("@id"): n for n in nodes if n.get("@id") and n.get("@type")}
    webpage = next((n for n in nodes if any(str(t).endswith("Page") and t != "FAQPage" for t in types_of(n))), None)
    main = (webpage or {}).get("mainEntity")
    main = by_id.get(main.get("@id"), main) if isinstance(main, dict) else None
    primary = types_of(main) if main else sorted({t for n in nodes for t in types_of(n)
                                                   if t not in FRAME_TYPES and not str(t).endswith("Page")})
    crumbs = next((n for n in nodes if "BreadcrumbList" in types_of(n)), None)
    org = next((n for n in nodes if "Organization" in types_of(n)), None)
    return {"primary_types": [str(t) for t in primary],
            "breadcrumb_items": len(crumbs.get("itemListElement") or []) if crumbs else None,
            "date_modified": (webpage or {}).get("dateModified"),
            "organization": {"name": org.get("name"), "same_as": org.get("sameAs") or []} if org else None}


def load_brief(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    phrasings, questions, subneeds = [], [], []
    for c in data.get("clusters", []):
        if c.get("role") == "primary":
            phrasings += [p["keyword"] for p in c.get("phrasings", [])[:3]]
        questions += c.get("questions", [])
        subneeds += [s["attribute"] for s in c.get("subneeds", []) if s.get("status") in ("covered", "write_it")]
    return {"page": data.get("page"), "phrasings": phrasings, "questions": questions, "subneeds": subneeds}


def pool_questions(path, keywords, limit=40):
    """Question-form queries from a site-research pool that share a subject word with the keywords."""
    subject = set().union(*(tokens(k) for k in keywords)) - GENERIC - STOPWORDS if keywords else set()
    found = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            k = json.loads(line).get("keyword") or ""
        except ValueError:
            continue
        if QUESTION_START.match(k) and subject & tokens(k):
            found[k] = found.get(k, 0) + 1
    return [k for k, _ in sorted(found.items(), key=lambda kv: (-kv[1], kv[0]))][:limit]


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


def load_robots(url):
    """(summary, parser); parser is None when no robots.txt was read."""
    parts = urllib.parse.urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    got = fetch(robots_url, BROWSER_UA)
    result = {"url": robots_url, "status": got.get("status"), "agents": {}}
    if not got["ok"] or got["status"] >= 400:
        result["note"] = "no robots.txt read: crawlers treat 4xx as allow-all; 5xx may stop crawling"
        return result, None
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(got["html"].splitlines())
    return result, rp


def robots(url):
    result, rp = load_robots(url)
    if rp is not None:
        result["agents"] = {name: "allowed" if rp.can_fetch(name, url) else "disallowed" for name in SEARCH_BOTS}
    return result


def faq_gaps(page):
    visible = norm(" ".join(t for t, _ in page.text))
    ld_questions, ld_types = faq_from_jsonld(page.jsonld)
    return ({"schema_only": [q for q, _ in ld_questions if norm(q) not in visible],
             "schema_answer_not_visible": [q for q, a in ld_questions
                                           if norm(q) in visible and norm(a)[:80] not in visible]},
            ld_questions, ld_types)


def rendering_verdict(words, scripts):
    if words < 80 and scripts >= 3:
        return "client_rendered_shell"
    return "thin_server_html" if words < 200 else "server_html_has_content"


def page_facts(page, retired=(), today=None):
    """Facts shared by the page check and the sweep: title/H1, headings, images, breadcrumbs,
    structured data, dated copy and retired phrases."""
    h1 = [t for tag, t in page.headings if tag == "h1"]
    content = page.content()
    images = [i for i in page.images if i["zone"] != "chrome" and not i["hidden"]]
    sd = structured(page)
    dated = sorted(set(m.group(0) for m in RELATIVE_DATE.finditer(content)))
    age = None
    if dated and isinstance(sd["date_modified"], str) and re.match(r"\d{4}-\d{2}-\d{2}", sd["date_modified"]):
        age = ((today or date.today()) - date.fromisoformat(sd["date_modified"][:10])).days
    everything = norm(" ".join([page.title, page.meta.get("description") or ""] + [t for t, _ in page.text]))
    return {
        "title_h1": title_h1(page.title, h1[0]) if h1 else None, "title_lead": title_lead(page.title),
        "label_headings": [t for (tag, t), z in zip(page.headings, page.heading_zones)
                           if tag == "h2" and z != "chrome" and norm(t) in LABELS],
        "images": {"content": len(images), "missing_alt": sum(1 for i in images if not (i["alt"] or "").strip()),
                   "examples": [i["src"] for i in images if not (i["alt"] or "").strip()][:5]},
        "og_image": page.meta.get("og:image"),
        "breadcrumb": {"visible": page.breadcrumb, "structured_items": sd["breadcrumb_items"]},
        "structured": sd,
        "relative_dates": {"found": dated, "days_since_modified": age},
        "retired": [p for p in retired if norm(p) and f" {norm(p)} " in f" {everything} "],
    }


def fact_issues(f):
    issues = []
    if f["title_h1"] is not None and f["title_h1"] < TITLE_H1_MIN:
        issues.append("title_h1_drift")
    if f["label_headings"]:
        issues.append("label_heading")
    if f["images"]["content"] >= ALT_MIN_IMAGES and f["images"]["missing_alt"] * 2 >= f["images"]["content"]:
        issues.append("images_without_alt")
    if not f["og_image"]:
        issues.append("no_og_image")
    bc = f["breadcrumb"]
    if bc["visible"] and bc["structured_items"] is None:
        issues.append("breadcrumb_not_structured")
    elif bc["visible"] and bc["structured_items"] != len(bc["visible"]):
        issues.append("breadcrumb_mismatch")
    if f["relative_dates"]["days_since_modified"] is not None and f["relative_dates"]["days_since_modified"] > 1:
        issues.append("stale_relative_dates")
    if f["retired"]:
        issues.append("retired_term")
    return issues


def check(url, keywords, brief_path=None, pool_path=None, retired=()):
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
    gaps, ld_questions, ld_types = faq_gaps(page)
    on_page = page.questions()
    report["faq"] = {"visible_questions": on_page, "collapsed_questions": page.questions(collapsed=True),
                     "faqpage_schema_questions": [q for q, _ in ld_questions],
                     **gaps, "jsonld_types": ld_types}
    if brief:
        report["brief"] = {"page": brief["page"], "subneeds": brief["subneeds"],
                           "questions": match_questions(brief["questions"], on_page)}
    if pool_path:
        report["pool_questions"] = match_questions(pool_questions(pool_path, keywords), on_page)
    report["rendering"] = {
        "server_text_words": len(words), "h1_in_server_html": bool(h1),
        "verdict": rendering_verdict(len(words), page.scripts),
        "next": "compare with the rendered page text; anything only there is invisible to crawlers that do not run JS"}
    report["crawlers"] = {"robots_txt": robots(url), "x_robots_tag": raw.get("x_robots_tag"),
                          "meta_robots": page.meta.get("robots")}
    facts = page_facts(page, retired)
    report["facts"] = {**facts, "issues": fact_issues(facts)}
    return report


def render(r):
    out = [f"site-check page: {r['url']}  ({r['checked_at']})"]
    f = r["fetch"]
    if not f.get("ok"):
        return "\n".join(out + [f"fetch failed: {f.get('error')}"])
    p = r["page"]
    fa = r["facts"]
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
    out.append(f"  H1 keeps {fa['title_h1']} of the title's lead words {fa['title_lead']}")
    if fa["label_headings"]:
        out.append(f"  H2s that label a block, not a topic: {fa['label_headings']}")
    fq = r["faq"]
    out += ["", f"2 FAQ: {len(fq['visible_questions'])} visible questions, {len(fq['faqpage_schema_questions'])} in FAQPage schema"]
    out += [f"  - {q}" for q in fq["visible_questions"][:30]]
    if fq["collapsed_questions"]:
        out.append(f"  collapsed on load (inside a closed <details>): {len(fq['collapsed_questions'])} questions")
    if fq["schema_only"]:
        out.append(f"  schema-only (not visible): {fq['schema_only']}")
    if fq["schema_answer_not_visible"]:
        out.append(f"  schema answer not in server HTML text: {fq['schema_answer_not_visible']}")
    if "brief" in r:
        out.append(f"  brief questions ({r['brief']['page']}):")
        out += [f"  [{q['hint']}] {q['question']}  ~ {q['closest_on_page']}" for q in r["brief"]["questions"]]
    if "pool_questions" in r:
        out.append(f"  keyword-pool questions ({len(r['pool_questions'])}):")
        out += [f"  [{q['hint']}] {q['question']}  ~ {q['closest_on_page']}" for q in r["pool_questions"]]
    rd = r["rendering"]
    out += ["", f"3 rendering: {rd['verdict']} ({rd['server_text_words']} words in server HTML, h1 {rd['h1_in_server_html']})"]
    rb = r["crawlers"]["robots_txt"]
    out += ["", f"4 indexing: robots.txt {rb['status']} {rb.get('note', '')}".rstrip()]
    out += [f"  {a}: {v}" for a, v in rb["agents"].items()]
    sd, img, bc = fa["structured"], fa["images"], fa["breadcrumb"]
    out += ["", "5 page facts:",
            f"  structured data: primary {sd['primary_types'] or 'none'}; dateModified {sd['date_modified']}",
            f"  images: {img['missing_alt']} of {img['content']} content images without alt text; og:image {fa['og_image'] or 'missing'}",
            f"  breadcrumb: visible {bc['visible'] or 'none'}; structured items {bc['structured_items']}"]
    if fa["relative_dates"]["found"]:
        out.append(f"  dated copy {fa['relative_dates']['found']}: {fa['relative_dates']['days_since_modified']} days since dateModified")
    if fa["retired"]:
        out.append(f"  retired phrases on the page: {fa['retired']}")
    out.append(f"  issues: {fa['issues'] or 'none'}")
    return "\n".join(out)


LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
# Each issue is a mechanical fact; the order is the report order.
ISSUES = {
    "fetch_error": "could not fetch", "http_status": "status is not 200", "redirected": "redirects elsewhere",
    "noindex": "noindex in meta robots or X-Robots-Tag", "canonical_other": "canonical points to another URL",
    "search_bot_disallowed": "robots.txt blocks a search crawler (Googlebot, Bingbot or OAI-SearchBot)",
    "client_rendered_shell": "server HTML is a JS shell",
    "thin_server_html": "under 200 words of main text in server HTML", "no_title": "no <title>",
    "no_description": "no meta description", "no_h1": "no H1 in server HTML", "multiple_h1": "more than one H1",
    "title_h1_drift": f"the H1 keeps under {int(TITLE_H1_MIN * 100)}% of the title's lead words",
    "label_heading": "an H2 that labels a block (Filter, Questions, Related) instead of naming the topic",
    "faq_schema_only": "FAQPage question not visible on the page",
    "faq_answer_not_in_html": "FAQ question visible but its answer is not in server HTML",
    "faq_hidden": "FAQ questions start collapsed inside a closed <details>; visitors must click to find them",
    "images_without_alt": "half or more of the content images have no alt text",
    "no_og_image": "no og:image",
    "breadcrumb_not_structured": "visible breadcrumb without BreadcrumbList",
    "breadcrumb_mismatch": "visible breadcrumb and BreadcrumbList have a different number of levels",
    "stale_relative_dates": "copy such as 'in 12 days' is more than a day older than the page's dateModified",
    "retired_term": "a retired product name or phrase is still on the page",
    "links_to_noindex": "links to a noindex page in the main content",
    "links_to_error": "links to a page that does not return 200",
}
FAQ_HIDDEN_MIN = 2   # collapsed questions before a page counts as hiding its FAQ


def sitemap_urls(source, limit, seen=None, base=None):
    """URLs from a sitemap file or URL; follows sitemap indexes (fetched from base when given)."""
    seen = seen if seen is not None else set()
    if source in seen:
        return []
    seen.add(source)
    if re.match(r"https?://", source):
        got = fetch(source, BROWSER_UA)
        if not got["ok"] or got["status"] >= 400:
            raise SystemExit(f"sitemap {source}: {got.get('error') or got.get('status')}")
        xml = got["html"]
    else:
        xml = Path(source).read_text(encoding="utf-8")
    locs = LOC.findall(xml)
    if re.search(r"<sitemapindex", xml, re.I):
        urls = []
        for loc in locs:
            urls += sitemap_urls(rebase(loc, base), limit - len(urls), seen, base)
            if len(urls) >= limit:
                break
        return urls[:limit]
    return list(dict.fromkeys(locs))[:limit]


def rebase(url, base):
    if not base:
        return url
    parts, b = urllib.parse.urlsplit(url), urllib.parse.urlsplit(base)
    return urllib.parse.urlunsplit((b.scheme, b.netloc, parts.path, parts.query, ""))


def pattern(url):
    """URL shape for grouping: /, /<page>, /<section>/*."""
    segs = [s for s in urllib.parse.urlsplit(url).path.split("/") if s]
    return "/" if not segs else "/<page>" if len(segs) == 1 else f"/{segs[0]}/*"


def path_key(url):
    p = urllib.parse.urlsplit(url).path
    return p.rstrip("/") or "/"


def internal_links(page, page_url, hosts):
    """Paths this page links to from its content (outside nav/header/footer/aside), and whether any carry a query."""
    out = []
    for link in page.links:
        if link["zone"] == "chrome" or link["href"].startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        target = urllib.parse.urlsplit(urllib.parse.urljoin(page_url, link["href"]))
        if target.netloc not in hosts or SKIP_LINK.search(target.path) or target.path.startswith("/api/"):
            continue
        out.append({"path": target.path.rstrip("/") or "/", "query": bool(target.query), "text": link["text"]})
    return out


def page_issues(url, raw, rp, retired=()):
    if not raw["ok"]:
        return ["fetch_error"], {"error": raw.get("error")}, None
    issues = []
    if raw["status"] != 200:
        issues.append("http_status")
    if urllib.parse.urlsplit(raw["final_url"]).path.rstrip("/") != urllib.parse.urlsplit(url).path.rstrip("/"):
        issues.append("redirected")
    page = Page()
    page.feed(raw["html"])
    robots_values = f"{page.meta.get('robots', '')} {raw.get('x_robots_tag') or ''}".lower()
    if "noindex" in robots_values:
        issues.append("noindex")
    if page.canonical:
        target = urllib.parse.urlsplit(urllib.parse.urljoin(raw["final_url"], page.canonical)).path.rstrip("/")
        if target != urllib.parse.urlsplit(raw["final_url"]).path.rstrip("/"):
            issues.append("canonical_other")
    if rp is not None and any(not rp.can_fetch(bot, url) for bot in SEARCH_BOTS):
        issues.append("search_bot_disallowed")
    words = len(page.content().split())
    verdict = rendering_verdict(words, page.scripts)
    if verdict != "server_html_has_content":
        issues.append(verdict)
    h1 = [t for tag, t in page.headings if tag == "h1"]
    if not page.title:
        issues.append("no_title")
    if not (page.meta.get("description") or "").strip():
        issues.append("no_description")
    if not h1:
        issues.append("no_h1")
    elif len(h1) > 1:
        issues.append("multiple_h1")
    gaps, _, _ = faq_gaps(page)
    collapsed = page.questions(collapsed=True)
    if len(collapsed) >= FAQ_HIDDEN_MIN:
        issues.append("faq_hidden")
    if gaps["schema_only"]:
        issues.append("faq_schema_only")
    if gaps["schema_answer_not_visible"]:
        issues.append("faq_answer_not_in_html")
    facts = page_facts(page, retired)
    issues += fact_issues(facts)
    issues = [code for code in ISSUES if code in issues]
    ld_questions, _ = faq_from_jsonld(page.jsonld)
    subject = norm(h1[0]) if h1 else ""
    faq = [{"q": q, "shape": question_shape(q, subject)} for q in page.questions()]
    answers = {question_shape(q, subject): norm(a) for q, a in ld_questions if a}
    return issues, {"status": raw["status"], "words": words, "title": page.title, "h1": h1[0] if h1 else None,
                    "canonical": page.canonical, "faq": faq, "faq_answers": answers,
                    "subheadings": page.subheadings(), "facts": facts,
                    **{k: v for k, v in gaps.items() if v}}, page


def question_shape(question, subject):
    """The question with the page's own subject (its H1) replaced, so templated questions collide."""
    q = f" {norm(question)} "
    if subject:
        q = q.replace(f" {subject} ", " {page} ")
        for word in sorted(tokens(subject) - GENERIC - STOPWORDS, key=len, reverse=True):
            q = q.replace(f" {word} ", " {page} ")
    return " ".join(q.split())


def faq_templates(pages):
    """Question shapes asked on many pages, and whether their answers are identical too."""
    shapes = {}
    for p in pages:
        for item in p.get("faq", []):
            shapes.setdefault(item["shape"], []).append(p["url"])
    out = []
    for shape, urls in shapes.items():
        urls = list(dict.fromkeys(urls))
        if len(urls) < TEMPLATE_MIN_PAGES:
            continue
        answers = [p["faq_answers"].get(shape) for p in pages if p["url"] in urls and p.get("faq_answers", {}).get(shape)]
        out.append({"question_shape": shape, "pages": len(urls), "urls": urls,
                    "same_answer_pages": max((answers.count(a) for a in set(answers)), default=0)})
    return sorted(out, key=lambda t: -t["pages"])


def heading_templates(pages):
    """H2 texts repeated word for word on many pages: section labels from a template, not the page's topic."""
    seen = {}
    for p in pages:
        for h in dict.fromkeys(p.get("subheadings", [])):
            seen.setdefault(norm(h), {"heading": h, "urls": []})["urls"].append(p["url"])
    out = [{"heading": v["heading"], "pages": len(v["urls"]), "urls": v["urls"]}
           for k, v in seen.items() if k and len(v["urls"]) >= TEMPLATE_MIN_PAGES]
    return sorted(out, key=lambda t: -t["pages"])


def shingles(text):
    words = norm(text).split()
    return {" ".join(words[i:i + SHINGLE]) for i in range(max(0, len(words) - SHINGLE + 1))}


def near_duplicates(contents):
    """Page pairs whose main text shares many 5-word runs (Jaccard of shingles)."""
    items = [(u, shingles(t)) for u, t in contents.items()]
    out = []
    for i, (a, sa) in enumerate(items):
        for b, sb in items[i + 1:]:
            if sa and sb:
                j = len(sa & sb) / len(sa | sb)
                if j >= NEAR_DUPLICATE:
                    out.append({"pages": [a, b], "similarity": round(j, 2)})
    return sorted(out, key=lambda d: -d["similarity"])


def link_report(pages, parsed, hosts, fetch_path):
    """Internal links across the swept pages: content inlinks, dead ends, and linked URLs outside the
    sitemap (fetched once each: noindex or error marks the linking pages)."""
    swept = {path_key(p["url"]): p["url"] for p in pages}
    inlinks = {u: set() for u in swept.values()}
    outside = {}
    for p in pages:
        page = parsed.get(p["url"])
        if page is None:
            continue
        links = internal_links(page, p["url"], hosts)
        targets = {l["path"] for l in links}
        p["content_links"] = len(targets - {path_key(p["url"])})
        for t in targets:
            if t in swept and swept[t] != p["url"]:
                inlinks[swept[t]].add(p["url"])
            elif t not in swept:
                outside.setdefault(t, set()).add(p["url"])
        p["query_links"] = sum(1 for l in links if l["query"])
    checked = {}
    for t in sorted(outside, key=lambda t: -len(outside[t]))[:MAX_LINK_TARGETS]:
        got = fetch_path(t)
        if not got["ok"]:
            checked[t] = "error"
            continue
        page = Page()
        page.feed(got["html"])
        noindex = "noindex" in f"{page.meta.get('robots', '')} {got.get('x_robots_tag') or ''}".lower()
        checked[t] = "error" if got["status"] != 200 else "noindex" if noindex else "ok"
    for p in pages:
        bad = {t: checked[t] for t, src in outside.items() if p["url"] in src and checked.get(t) in ("noindex", "error")}
        for code, kind in (("links_to_noindex", "noindex"), ("links_to_error", "error")):
            if kind in bad.values() and code not in p["issues"]:
                p["issues"].append(code)
        if bad:
            p["bad_links"] = bad
    counts = sorted(((len(v), u) for u, v in inlinks.items()))
    return {"lowest_inlinks": [{"url": u, "content_inlinks": n} for n, u in counts[:10]],
            "dead_ends": [p["url"] for p in pages if p.get("content_links", 1) == 0],
            "outside_sitemap": [{"path": t, "linked_from": len(outside[t]), "status": checked.get(t, "not fetched")}
                                for t in sorted(outside, key=lambda t: -len(outside[t]))]}


def sweep(source, base=None, limit=500, retired=()):
    listed = sitemap_urls(source, limit, base=base)
    urls = [rebase(u, base) for u in listed]
    report = {"schema": SWEEP_SCHEMA, "sitemap": source, "base": base,
              "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "urls": len(urls)}
    if not urls:
        return {**report, "pages": [], "issues": {}, "site": {}}
    robots_summary, rp = load_robots(urls[0])
    origin = urllib.parse.urlsplit(urls[0])
    hosts = {origin.netloc} | {urllib.parse.urlsplit(u).netloc for u in listed}
    pages, parsed, contents = [], {}, {}
    for url in urls:
        raw = fetch(url, BROWSER_UA)
        if not raw["ok"]:   # one retry: a single timeout should not read as a broken page
            raw = fetch(url, BROWSER_UA)
        issues, facts, page = page_issues(url, raw, rp, retired)
        pages.append({"url": url, "pattern": pattern(url), "issues": issues, **facts})
        if page is not None:
            parsed[url] = page
            if "noindex" not in issues:
                contents[url] = page.content()
    links = link_report(pages, parsed, hosts,
                        lambda path: fetch(urllib.parse.urlunsplit((origin.scheme, origin.netloc, path, "", "")), BROWSER_UA))
    grouped = {}
    for code in ISSUES:
        hit = [p for p in pages if code in p["issues"]]
        if hit:
            by_pattern = {}
            for p in hit:
                by_pattern.setdefault(p["pattern"], []).append(p["url"])
            total = {pat: sum(1 for p in pages if p["pattern"] == pat) for pat in by_pattern}
            grouped[code] = {"meaning": ISSUES[code], "count": len(hit),
                             "patterns": [{"pattern": pat, "hit": len(us), "of": total[pat], "urls": us}
                                          for pat, us in sorted(by_pattern.items(), key=lambda kv: -len(kv[1]))]}
    if rp is not None:
        robots_summary["agents"] = {n: "allowed" if rp.can_fetch(n, urls[0]) else "disallowed" for n in SEARCH_BOTS}
    types = {}
    for p in pages:
        for t in (p.get("facts") or {}).get("structured", {}).get("primary_types") or ["(none)"]:
            types.setdefault(t, []).append(p["url"])
    org = next((p["facts"]["structured"]["organization"] for p in pages
                if (p.get("facts") or {}).get("structured", {}).get("organization")), None)
    with_faq = sum(1 for p in pages if p.get("faq"))
    return {**report, "site": {"robots_txt": robots_summary, "organization": org,
                               "primary_types": {t: {"pages": len(us), "urls": us} for t, us in types.items()}},
            "issues": grouped, "clean": sum(1 for p in pages if not p["issues"]),
            "faq": {"pages_with_questions": with_faq, "templated_questions": faq_templates(pages)},
            "templated_headings": heading_templates(pages), "near_duplicates": near_duplicates(contents),
            "links": links, "pages": pages}


def render_sweep(r):
    out = [f"site-check sweep: {r['sitemap']}{' -> ' + r['base'] if r['base'] else ''}  ({r['checked_at']})",
           f"{r['urls']} URLs, {r.get('clean', 0)} without issues"]
    site = r.get("site") or {}
    if site:
        rb = site["robots_txt"]
        out.append(f"robots.txt {rb['status']}: " + (", ".join(f"{a} {v}" for a, v in rb["agents"].items())
                                                    or rb.get("note", "")))
        org = site.get("organization")
        out.append(f"Organization: {org['name']!r}, sameAs {org['same_as'] or 'none'}" if org
                   else "Organization: none in structured data")
        out.append("primary structured-data types: " + ", ".join(
            f"{t} {v['pages']}" for t, v in sorted(site["primary_types"].items(), key=lambda kv: -kv[1]["pages"])))
    for code, g in r["issues"].items():
        out += ["", f"{code} ({g['count']}): {g['meaning']}"]
        for p in g["patterns"]:
            share = " (every page of this shape: likely a shared template)" if p["hit"] == p["of"] and p["of"] > 1 else ""
            out.append(f"  {p['pattern']}: {p['hit']} of {p['of']}{share}")
            out += [f"    {u}" for u in p["urls"][:8]]
            if len(p["urls"]) > 8:
                out.append(f"    … {len(p['urls']) - 8} more (see --format json)")
    if not r["issues"]:
        out += ["", "no mechanical issues found"]
    fq = r.get("faq") or {}
    if fq:
        out += ["", f"FAQ: {fq['pages_with_questions']} of {r['urls']} pages show questions; "
                    f"{len(fq['templated_questions'])} question shapes repeat on {TEMPLATE_MIN_PAGES}+ pages"]
        for t in fq["templated_questions"][:15]:
            same = f", identical schema answer on {t['same_answer_pages']}" if t["same_answer_pages"] > 1 else ""
            out.append(f"  {t['pages']} pages{same}: {t['question_shape']}")
    th = r.get("templated_headings") or []
    if th:
        out += ["", f"headings repeated word for word on {TEMPLATE_MIN_PAGES}+ pages ({len(th)}):"]
        out += [f"  {t['pages']} pages: {t['heading']}" for t in th[:15]]
    nd = r.get("near_duplicates") or []
    if nd:
        out += ["", f"pages sharing much of their main text (5-word shingles, Jaccard >= {NEAR_DUPLICATE}): {len(nd)} pairs"]
        out += [f"  {d['similarity']}: {d['pages'][0]}  ~  {d['pages'][1]}" for d in nd[:15]]
    ln = r.get("links") or {}
    if ln:
        out += ["", "internal links (main content only):",
                "  fewest inlinks: " + ", ".join(f"{urllib.parse.urlsplit(x['url']).path} {x['content_inlinks']}"
                                                 for x in ln["lowest_inlinks"])]
        if ln["dead_ends"]:
            out.append(f"  dead ends (no content links to other pages): {ln['dead_ends']}")
        if ln["outside_sitemap"]:
            out.append("  linked but not in the sitemap: " + ", ".join(
                f"{x['path']} ({x['linked_from']} pages, {x['status']})" for x in ln["outside_sitemap"][:15]))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="site-check: raw-HTML evidence for one page, or a sitemap sweep")
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--url")
    target.add_argument("--sitemap", help="sitemap URL or file; sweeps every listed URL")
    ap.add_argument("--base", help="sweep: fetch listed paths from this origin instead (e.g. http://127.0.0.1:3000)")
    ap.add_argument("--limit", type=int, default=500, help="sweep: maximum URLs")
    ap.add_argument("--keyword", action="append", default=[], help="target phrase; repeatable")
    ap.add_argument("--brief", help="site-plan brief JSON (seo/work/briefs/<slug>.json)")
    ap.add_argument("--pool", help="site-research pool (seo/discovery/observations.jsonl): question queries for check 2")
    ap.add_argument("--retired", action="append", default=[],
                    help="product name or phrase the site no longer uses; repeatable")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    a = ap.parse_args(argv)
    if a.sitemap:
        r = sweep(a.sitemap, a.base, a.limit, a.retired)
        print(json.dumps(r, ensure_ascii=False, indent=2) if a.format == "json" else render_sweep(r))
        return 0
    r = check(a.url, a.keyword, a.brief, a.pool, a.retired)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.format == "json" else render(r))
    return 0 if r["fetch"].get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
