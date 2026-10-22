#!/usr/bin/env python3
"""Read-only facts for AI-search visibility: can AI crawlers reach the site, and does llms.txt match it.

    python3 geo_check.py --site <origin> [--url <page>]... [--sitemap <url|file>] [--base <origin>]
                         [--retired "phrase"]... [--format text|json]

Reports robots.txt rules for AI crawlers (search, user-initiated and training), what each AI user-agent
gets back on the pages given (status, challenge page, same HTML as a browser), and whether /llms.txt
exists, links to live pages, covers the sitemap and avoids retired names. ChatGPT itself is asked by
the model with references/chatgpt-probes.md; this script never contacts an AI service. It never writes
files. Page SEO (keywords, FAQ, rendering, structure) belongs to site-check.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

SCHEMA = "site-geo/check@1"
MAX_BYTES = 3_000_000
TIMEOUT = 20
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
# robots.txt tokens by role. "search" decides whether pages can appear in that assistant's answers;
# "user" fetches when a person asks; "training" only feeds model training. Google-Extended and
# Applebot-Extended are robots tokens only, never sent as a user-agent.
AI_AGENTS = {
    "OAI-SearchBot": "search", "ChatGPT-User": "user", "GPTBot": "training",
    "Claude-SearchBot": "search", "Claude-User": "user", "ClaudeBot": "training",
    "PerplexityBot": "search", "Perplexity-User": "user",
    "Google-Extended": "training", "Applebot-Extended": "training",
}
# User-agent strings for probes, modelled on the vendors' documentation; they test rules keyed on the
# user-agent only, not firewalls that verify crawlers by IP.
PROBES = {
    "OAI-SearchBot": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "ChatGPT-User": "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
    "GPTBot": "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
}
CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-chl-|challenge-platform|Attention Required!|captcha", re.I)
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
MAX_LLMS_LINKS = 60


def fetch(url, ua=BROWSER_UA):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html,text/plain,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES)
            status, headers, final = r.status, r.headers, r.geturl()
    except urllib.error.HTTPError as e:
        body, status, headers, final = e.read(MAX_BYTES), e.code, e.headers, url
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"ok": False, "error": str(getattr(e, "reason", e)), "status": None}
    charset = headers.get_content_charset() or "utf-8"
    return {"ok": True, "status": status, "final_url": final, "body": body.decode(charset, "replace"),
            "cf_mitigated": headers.get("cf-mitigated"), "x_robots_tag": headers.get("X-Robots-Tag")}


def norm(s):
    return " ".join(re.findall(r"\w+", s.lower()))


def origin_of(url):
    p = urllib.parse.urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def path_key(url):
    return urllib.parse.urlsplit(url).path.rstrip("/") or "/"


def robots_for(origin, pages):
    got = fetch(f"{origin}/robots.txt")
    out = {"url": f"{origin}/robots.txt", "status": got.get("status"), "agents": {}}
    if not got["ok"] or got["status"] >= 400:
        out["note"] = "no robots.txt read: crawlers treat 4xx as allow-all; 5xx may stop crawling"
        return out
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(got["body"].splitlines())
    for agent, role in AI_AGENTS.items():
        blocked = [path_key(u) for u in pages if not rp.can_fetch(agent, u)]
        out["agents"][agent] = {"role": role, "blocked_pages": blocked}
    return out


def probe(url):
    browser = fetch(url)
    size = len(browser.get("body") or "")
    out = {"url": url, "browser_status": browser.get("status"), "agents": {}}
    for name, ua in PROBES.items():
        got = fetch(url, ua)
        body = got.get("body") or ""
        out["agents"][name] = {"status": got.get("status"), "error": got.get("error"),
                               "cf_mitigated": got.get("cf_mitigated"),
                               "challenge_page": bool(CHALLENGE.search(body[:20000])),
                               "same_size_as_browser": abs(len(body) - size) < max(500, size // 10)}
    return out


def rebase(url, base):
    if not base:
        return url
    parts, b = urllib.parse.urlsplit(url), urllib.parse.urlsplit(base)
    return urllib.parse.urlunsplit((b.scheme, b.netloc, parts.path, parts.query, ""))


def sitemap_paths(source, limit=2000, seen=None, base=None):
    seen = seen if seen is not None else set()
    if source in seen:
        return []
    seen.add(source)
    if re.match(r"https?://", source):
        got = fetch(source)
        if not got["ok"] or got["status"] >= 400:
            raise SystemExit(f"sitemap {source}: {got.get('error') or got.get('status')}")
        xml = got["body"]
    else:
        xml = Path(source).read_text(encoding="utf-8")
    locs = LOC.findall(xml)
    if re.search(r"<sitemapindex", xml, re.I):
        out = []
        for loc in locs:
            out += sitemap_paths(rebase(loc, base), limit, seen, base)
        return out[:limit]
    return [path_key(u) for u in dict.fromkeys(locs)][:limit]


def llms(origin, sitemap=None, retired=(), site_host=None, base=None):
    got = fetch(f"{origin}/llms.txt")
    out = {"url": f"{origin}/llms.txt", "status": got.get("status")}
    if not got["ok"] or got["status"] != 200:
        out["present"] = False
        return out
    text = got["body"]
    host = urllib.parse.urlsplit(origin).netloc
    links, hosts = [], {host, site_host} - {None}
    for label, href in MD_LINK.findall(text):
        target = urllib.parse.urlsplit(urllib.parse.urljoin(origin + "/", href))
        links.append({"label": label, "href": href, "internal": target.netloc in hosts or not target.netloc,
                      "path": target.path.rstrip("/") or "/"})
    internal = [l for l in links if l["internal"]]
    for l in internal[:MAX_LLMS_LINKS]:
        r = fetch(origin + l["path"])
        l["status"] = r.get("status")
        l["noindex"] = "noindex" in (r.get("x_robots_tag") or "").lower() or bool(
            re.search(r'<meta[^>]+name="robots"[^>]+noindex', r.get("body") or "", re.I))
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), None)
    words = f" {norm(text)} "
    out.update({"present": True, "title": title, "lines": len(text.splitlines()), "links": len(links),
                "broken": [l["path"] for l in internal if l.get("status") not in (None, 200)],
                "noindex": [l["path"] for l in internal if l.get("noindex")],
                "retired": [p for p in retired if norm(p) and f" {norm(p)} " in words]})
    if sitemap:
        listed = sitemap_paths(sitemap, base=base)
        mentioned = {l["path"] for l in internal}
        out["sitemap_pages"] = len(listed)
        out["not_in_llms"] = [p for p in listed if p not in mentioned]
        out["not_in_sitemap"] = sorted(p for p in mentioned if p not in set(listed))
    return out


def check(site, urls=(), sitemap=None, base=None, retired=()):
    origin = origin_of(base or site)
    pages = [urllib.parse.urljoin(origin + "/", urllib.parse.urlsplit(u).path or "/") for u in urls] or [origin + "/"]
    return {"schema": SCHEMA, "site": site, "base": base,
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "robots_txt": robots_for(origin, pages), "probes": [probe(u) for u in pages],
            "llms_txt": llms(origin, sitemap, retired, urllib.parse.urlsplit(site).netloc, base),
            "limits": "probes send the user-agent from this machine; firewalls that verify bots by IP "
                      "(Cloudflare AI crawler controls) can still treat the real crawler differently"}


def render(r):
    out = [f"site-geo: {r['site']}{' -> ' + r['base'] if r['base'] else ''}  ({r['checked_at']})"]
    rb = r["robots_txt"]
    out += ["", f"G1 robots.txt {rb['status']} {rb.get('note', '')}".rstrip()]
    for agent, v in rb["agents"].items():
        state = "allowed" if not v["blocked_pages"] else f"blocked on {v['blocked_pages']}"
        out.append(f"  {agent} ({v['role']}): {state}")
    for p in r["probes"]:
        out.append(f"  probes on {p['url']} (browser {p['browser_status']}):")
        for name, a in p["agents"].items():
            flags = [f"cf-mitigated {a['cf_mitigated']}"] if a["cf_mitigated"] else []
            flags += ["challenge page"] if a["challenge_page"] else []
            flags += [] if a["same_size_as_browser"] else ["different HTML"]
            out.append(f"    {name}: {a['status'] or a['error']}{'; ' + ', '.join(flags) if flags else ''}")
    out.append(f"  limits: {r['limits']}")
    lt = r["llms_txt"]
    out += ["", f"G2 llms.txt {lt['status']}"]
    if lt.get("present"):
        out.append(f"  title {lt['title']!r}, {lt['lines']} lines, {lt['links']} links")
        for key, label in (("broken", "links that do not return 200"), ("noindex", "links to noindex pages"),
                           ("retired", "retired phrases"), ("not_in_sitemap", "links to pages outside the sitemap")):
            if lt.get(key):
                out.append(f"  {label}: {lt[key]}")
        if "not_in_llms" in lt:
            out.append(f"  sitemap pages not in llms.txt: {len(lt['not_in_llms'])} of {lt['sitemap_pages']}"
                       + (f" {lt['not_in_llms'][:15]}" if lt["not_in_llms"] else ""))
    else:
        out.append("  no llms.txt")
    out += ["", "G3/G4 ChatGPT probes: ask with references/chatgpt-probes.md (needs the user's go-ahead)"]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="site-geo: AI crawler access and llms.txt facts")
    ap.add_argument("--site", required=True, help="the site's origin, e.g. https://example.com")
    ap.add_argument("--url", action="append", default=[], help="page to probe; repeatable (default: the home page)")
    ap.add_argument("--sitemap", help="sitemap URL or file, to compare with llms.txt")
    ap.add_argument("--base", help="fetch from this origin instead (a local build or preview)")
    ap.add_argument("--retired", action="append", default=[], help="phrase the site no longer uses; repeatable")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    a = ap.parse_args(argv)
    r = check(a.site, a.url, a.sitemap, a.base, a.retired)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.format == "json" else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
