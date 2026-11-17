#!/usr/bin/env python3
"""Read-only facts about a site for an AdSense evaluation. Python stdlib only; writes nothing but JSON on stdout.

  python3 adsense_facts.py example.com [--samples 12] [--timeout 20]

It reports what a crawler receives (raw HTML, no JavaScript). `flags` are leads to check, not verdicts.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import gzip
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; adsense-check/1.0)"
MAX_BYTES = 8_000_000
MAX_CHILD_SITEMAPS = 60
TRUST = {
    "about": r"about",
    "contact": r"contact",
    "privacy": r"privacy",
    "terms": r"terms|tos\b",
    "license": r"licen[cs]|attribution|credits|copyright",
}
FALLBACK_PATHS = {
    "about": ["/about", "/about-us"],
    "contact": ["/contact", "/contact-us"],
    "privacy": ["/privacy", "/privacy-policy"],
    "terms": ["/terms", "/terms-of-service"],
    "license": ["/license", "/licensing"],
}
CMP_SIGNS = {
    "Google Privacy & Messaging": "fundingchoicesmessages.google.com",
    "TCF API": "__tcfapi",
    "Cookiebot": "cookiebot",
    "OneTrust": "onetrust",
    "Quantcast": "quantcast.mgr.consensu",
    "Usercentrics": "usercentrics",
    "Didomi": "didomi",
    "Iubenda": "iubenda",
    "Termly": "termly",
    "CookieYes": "cookieyes",
}
PRIVACY_TERMS = {
    "cookies": r"\bcookies?\b",
    "advertising": r"\badvertis",
    "adsense_or_google_ads": r"adsense|google ads|doubleclick",
    "third_party": r"third[- ]part|vendors?\b",
    "opt_out": r"opt[- ]?out|adssettings|myadcenter|aboutads|youradchoices",
    "consent": r"\bconsent\b",
    "eea_uk_gdpr": r"\bEEA\b|\bGDPR\b|European Economic Area|United Kingdom|\bUK\b",
}
FILE_LINK = re.compile(r"\.(wav|mp3|ogg|flac|zip|pdf|exe|dmg|apk)(\?|$)", re.I)


def fetch(url: str, timeout: int, method: str = "GET") -> dict:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        status = resp.status
    except urllib.error.HTTPError as err:
        resp, status = err, err.code
    except Exception as err:  # network failures are facts too
        return {"url": url, "status": None, "error": str(err)[:160], "text": "", "final_url": url, "type": ""}
    body = b"" if method == "HEAD" else resp.read(MAX_BYTES)
    if body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except OSError:
            pass
    return {"url": url, "status": status, "final_url": resp.geturl(), "type": resp.headers.get("Content-Type", ""),
            "text": body.decode("utf-8", "replace")}


def visible_text(page: str) -> str:
    page = re.sub(r"<(script|style|noscript|template)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page))).strip()


def main_html(page: str) -> str | None:
    """The page's <main>, or None when it has none: navigation and footers can outweigh the content itself."""
    found = re.search(r"<main\b.*?</main>", page, flags=re.S | re.I)
    return found.group(0) if found else None


def word_count(text: str) -> int:
    latin = len(re.findall(r"[^\W぀-ヿ㐀-鿿가-힯]+", text))
    cjk = len(re.findall(r"[぀-ヿ㐀-鿿가-힯]", text))
    return latin + cjk // 2


def meta_content(page: str, name: str) -> str | None:
    for tag in re.findall(r"<meta\b[^>]*>", page, flags=re.I):
        if re.search(rf"""name\s*=\s*["']{re.escape(name)}["']""", tag, flags=re.I):
            found = re.search(r"""content\s*=\s*["']([^"']*)["']""", tag, flags=re.I)
            return found.group(1) if found else ""
    return None


def links(page: str, base: str) -> list[dict]:
    out = []
    for attrs, inner in re.findall(r"<a\b([^>]*)>(.*?)</a>", page, flags=re.S | re.I):
        href = re.search(r"""href\s*=\s*["']([^"']+)["']""", attrs, flags=re.I)
        if not href or href.group(1).startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        out.append({"href": urllib.parse.urljoin(base, html.unescape(href.group(1))), "text": visible_text(inner)[:80],
                    "download": bool(re.search(r"\bdownload\b", attrs, flags=re.I))})
    return out


def controls(page: str, base: str, limit: int = 30) -> list[dict]:
    """The first links and buttons in the body: what a reviewer sees first, and where each goes."""
    body = re.sub(r"<(script|style|template)\b.*?</\1>", " ", page, flags=re.S | re.I)
    start = re.search(r"<main\b", body, flags=re.I)
    body = body[start.start():] if start else body
    out = []
    for tag, attrs, inner in re.findall(r"<(a|button)\b([^>]*)>(.*?)</\1>", body, flags=re.S | re.I):
        label = visible_text(inner)[:80]
        if not label:
            continue
        href = re.search(r"""href\s*=\s*["']([^"']+)["']""", attrs, flags=re.I)
        out.append({"tag": tag.lower(), "label": label, "to": urllib.parse.urljoin(base, html.unescape(href.group(1))) if href else None})
        if len(out) >= limit:
            break
    return out


def ad_state(page: str) -> dict:
    script = bool(re.search(r"<script\b[^>]*(adsbygoogle\.js|pagead2\.googlesyndication\.com)", page, flags=re.I))
    units = len(re.findall(r"<ins\b[^>]*adsbygoogle", page, flags=re.I))
    verification = meta_content(page, "google-adsense-account")
    ids = sorted(set(re.findall(r"\bca-pub-\d{10,}\b", page)))
    other = sorted(n for n, sign in {"Ad Manager (GPT)": r"securepubads\.g\.doubleclick\.net|gpt\.js"}.items() if re.search(sign, page, flags=re.I))
    state = "ad-script" if script or units or other else "verification-only" if verification or ids else "none"
    return {"state": state, "ad_script": script, "ad_units_in_html": units, "verification_meta": verification, "publisher_ids": ids, "other_ad_tech": other}


def parse_sitemap(text: str) -> tuple[list[str], list[str]]:
    """Returns (child sitemaps, page URLs)."""
    try:
        root = ET.fromstring(text.strip())
    except ET.ParseError:
        return [], []
    locs = [el.text.strip() for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "loc" and el.text]
    return (locs, []) if root.tag.rsplit("}", 1)[-1] == "sitemapindex" else ([], locs)


def read_sitemaps(origin: str, robots_text: str, timeout: int) -> dict:
    declared = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_text)
    declared = list(dict.fromkeys(declared))
    queue = list(declared) or [f"{origin}/sitemap.xml"]
    seen, files, urls, skipped = set(), [], [], 0
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        if len(seen) >= MAX_CHILD_SITEMAPS:
            skipped += 1
            continue
        seen.add(url)
        got = fetch(url, timeout)
        children, pages = parse_sitemap(got["text"]) if got["status"] == 200 else ([], [])
        queue.extend(children)
        urls.extend(pages)
        files.append({"url": url, "status": got["status"], "children": len(children), "urls": len(pages)})
    return {"declared_in_robots": declared, "files": files, "total_urls": len(set(urls)), "files_not_read": skipped, "urls": list(dict.fromkeys(urls))}


def robots_blocks_google(robots_text: str) -> list[str]:
    blocked, agents, in_rules = [], [], False
    for raw in robots_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            agents = [value.lower()] if in_rules else agents + [value.lower()]
            in_rules = False
        elif key in ("allow", "disallow"):
            in_rules = True
            if key == "disallow" and value == "/":
                blocked += [a for a in agents if a in ("*", "googlebot", "mediapartners-google", "adsbot-google")]
    return sorted(set(blocked))


def robots_disallows(robots_text: str, url: str) -> bool:
    """Whether the rules for all crawlers (User-agent: *) disallow this URL. The longest matching rule wins; a tie goes to Allow."""
    parts = urllib.parse.urlsplit(url)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    rules, agents, in_rules = [], [], False
    for raw in robots_text.splitlines():
        key, _, value = raw.split("#", 1)[0].strip().partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            agents = [value.lower()] if in_rules else agents + [value.lower()]
            in_rules = False
        elif key in ("allow", "disallow"):
            in_rules = True
            if value and "*" in agents:
                rules.append((key, value))
    best = None
    for kind, rule in rules:
        anchored = rule.endswith("$")
        pattern = ".*".join(re.escape(piece) for piece in rule.rstrip("$").split("*")) + ("$" if anchored else "")
        if re.match(pattern, target) and (best is None or (len(rule), kind == "allow") > (len(best[1]), best[0] == "allow")):
            best = (kind, rule)
    return bool(best and best[0] == "disallow")


def canonical_of(page: str, base: str) -> str | None:
    for tag in re.findall(r"<link\b[^>]*>", page, flags=re.I):
        if re.search(r"""rel\s*=\s*["']canonical["']""", tag, flags=re.I):
            href = re.search(r"""href\s*=\s*["']([^"']+)["']""", tag, flags=re.I)
            return urllib.parse.urljoin(base, html.unescape(href.group(1))) if href else None
    return None


def page_facts(url: str, timeout: int) -> dict:
    got = fetch(url, timeout)
    text = visible_text(got["text"])
    main = main_html(got["text"])
    return {"url": url, "status": got["status"], "words": word_count(text), "main_words": word_count(visible_text(main)) if main else None,
            "robots": meta_content(got["text"], "robots"),
            "canonical": canonical_of(got["text"], got["final_url"]), "ad_script": ad_state(got["text"])["ad_script"],
            "html": got["text"], "final_url": got["final_url"], "text": text}


def even_sample(items: list[str], n: int) -> list[str]:
    if len(items) <= n:
        return items
    return [items[int(i * len(items) / n)] for i in range(n)]


def build_flags(r: dict) -> list[str]:
    flags = []
    if r["home"]["status"] != 200:
        flags.append("home is not HTTP 200")
    if r["ads"]["state"] == "ad-script" and not r["cmp"]["detected"]:
        flags.append("ad script present but no known CMP in raw HTML; check EEA/UK consent (a CMP may load by JavaScript)")
    if r["ads"]["state"] != "none" and r["ads_txt"]["status"] != 200:
        flags.append("no ads.txt")
    if r["ads_txt"]["status"] == 200 and not r["ads_txt"]["google_lines"]:
        flags.append("ads.txt has no google.com line")
    ids = {i.replace("ca-pub-", "pub-") for i in r["ads"]["publisher_ids"]}
    if ids and r["ads_txt"]["google_lines"] and not any(i in line for i in ids for line in r["ads_txt"]["google_lines"]):
        flags.append("ads.txt does not match the publisher id on the page")
    if r["robots"]["blocks_google"]:
        flags.append(f"robots.txt disallows everything for: {', '.join(r['robots']['blocks_google'])}")
    if not r["sitemap"]["total_urls"]:
        flags.append("no sitemap URLs found")
    for name, page in r["trust_pages"].items():
        if not page["url"] or page["status"] != 200:
            flags.append(f"no {name} page found at a common path or in the home links; check by hand")
        elif page["robots"] and "noindex" in page["robots"].lower():
            flags.append(f"{name} page is noindex")
    if r["trust_pages"]["privacy"]["status"] == 200:
        missing = [k for k, on in r["privacy"]["mentions"].items() if not on]
        if missing:
            flags.append(f"privacy policy does not mention: {', '.join(missing)}")
    thin = [p["url"] for p in r["sampled_pages"] + r["off_sitemap_pages"] if p["status"] == 200 and (p["main_words"] if p["main_words"] is not None else p["words"]) < 200
            and not (p["robots"] and "noindex" in p["robots"].lower())]
    if thin:
        flags.append(f"{len(thin)} sampled indexable pages under 200 words of main content in raw HTML (may be JS-rendered): {', '.join(thin[:5])}")
    if r["off_sitemap_pages"]:
        flags.append(f"{len(r['off_sitemap_pages'])} sampled internal pages are linked but not in the sitemap; compare their content with the listed pages")
    broken = [p["url"] for p in r["sampled_pages"] if p["status"] != 200]
    if broken:
        flags.append(f"{len(broken)} sampled sitemap URLs not HTTP 200: {', '.join(broken[:5])}")
    open_query = [p["url"] for p in r["query_pages"] if p["status"] == 200 and not (p["robots"] and "noindex" in p["robots"].lower())
                  and not p["robots_disallowed"] and (not p["canonical"] or p["canonical"] == p["url"])]
    if open_query:
        flags.append(f"{len(open_query)} sampled query URLs are indexable, with no noindex, robots rule or other canonical: {', '.join(open_query[:5])}")
    dead = [d["url"] for d in r["file_links"] if d["status"] not in (200, 206, 301, 302, 303, 307, 308)]
    if dead:
        flags.append(f"{len(dead)} file links did not answer OK: {', '.join(dead[:5])}")
    return flags


def run(site: str, samples: int, timeout: int) -> dict:
    site = site.strip()
    home_url = site if site.startswith(("http://", "https://")) else f"https://{site}"
    home_got = fetch(home_url, timeout)
    final = urllib.parse.urlsplit(home_got["final_url"])
    default_port = {"https": 443, "http": 80}.get(final.scheme)
    origin = f"{final.scheme}://{final.hostname}" + (f":{final.port}" if final.port and final.port != default_port else "")
    page = home_got["text"]
    text = visible_text(page)
    robots_got = fetch(f"{origin}/robots.txt", timeout)
    robots_text = robots_got["text"] if robots_got["status"] == 200 else ""
    ads_txt = fetch(f"{origin}/ads.txt", timeout)
    ads_txt_text = ads_txt["text"] if ads_txt["status"] == 200 and "html" not in ads_txt["type"].lower() else ""
    sitemap = read_sitemaps(origin, robots_text, timeout)
    home_links = links(page, origin)
    same_site = [l for l in home_links if urllib.parse.urlsplit(l["href"]).hostname == final.hostname]

    trust_targets = {}
    for name, pattern in TRUST.items():
        hit = next((l["href"] for l in same_site if re.search(pattern, urllib.parse.urlsplit(l["href"]).path + " " + l["text"], flags=re.I)), None)
        trust_targets[name] = hit
    with cf.ThreadPoolExecutor(8) as pool:
        for name, hit in list(trust_targets.items()):
            if not hit:
                for path in FALLBACK_PATHS[name]:
                    if fetch(origin + path, timeout, "HEAD")["status"] == 200:
                        trust_targets[name] = origin + path
                        break
        trust_found = {n: pool.submit(page_facts, u, timeout) if u else None for n, u in trust_targets.items()}
        trust_raw = {n: (f.result() if f else None) for n, f in trust_found.items()}
        sampled = even_sample(sitemap["urls"], samples)
        sampled_raw = list(pool.map(lambda u: page_facts(u, timeout), sampled))
        query_urls = []
        for source in [{"html": page, "final_url": home_got["final_url"]}, *sampled_raw]:
            for l in links(source["html"], source["final_url"]):
                parts = urllib.parse.urlsplit(l["href"])
                if parts.hostname == final.hostname and parts.query and l["href"] not in query_urls:
                    query_urls.append(l["href"])
        query_raw = list(pool.map(lambda u: page_facts(u, timeout), query_urls[:6]))
        # Linked pages the sitemap leaves out: often the thinnest on the site, and a reviewer can still reach them.
        listed = {u.rstrip("/") for u in sitemap["urls"]} | {(u or "").rstrip("/") for u in trust_targets.values()}
        off_urls = []
        for source in sampled_raw:
            for l in links(source["html"], source["final_url"]):
                parts = urllib.parse.urlsplit(l["href"])
                clean = l["href"].split("#", 1)[0].rstrip("/")
                if sitemap["urls"] and parts.hostname == final.hostname and not parts.query and not FILE_LINK.search(parts.path) \
                        and clean != origin and clean not in listed and clean not in off_urls:
                    off_urls.append(clean)
        off_raw = [p for p in pool.map(lambda u: page_facts(u, timeout), even_sample(off_urls, 6)) if p["status"] == 200 and "html" in p["html"][:2000].lower()]
        file_urls = []
        for source in [{"html": page, "final_url": home_got["final_url"]}, *sampled_raw]:
            for l in links(source["html"], source["final_url"]):
                if (FILE_LINK.search(urllib.parse.urlsplit(l["href"]).path) or l["download"]) and l["href"] not in file_urls:
                    file_urls.append(l["href"])
        file_raw = list(pool.map(lambda u: fetch(u, timeout, "HEAD"), file_urls[:6]))

    privacy_text = (trust_raw.get("privacy") or {}).get("text", "")
    last_updated = re.search(r"(?:last (?:updated|modified)|effective(?: date)?)[:\s]+([A-Z][a-z]+ \d{1,2},? \d{4}|\d{1,2} [A-Z][a-z]+ \d{4}|\d{4}-\d{2}-\d{2})", privacy_text, flags=re.I)
    raw_lower = page.lower()
    report = {
        "checked_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site": origin,
        "method": "raw HTML, no JavaScript; word counts include navigation and footers",
        "home": {"url": home_got["final_url"], "status": home_got["status"], "https": final.scheme == "https", "error": home_got.get("error"),
                 "title": html.unescape((re.search(r"<title[^>]*>(.*?)</title>", page, flags=re.S | re.I) or [None, ""])[1]).strip()[:160],
                 "lang": (re.search(r"""<html\b[^>]*\blang\s*=\s*["']([^"']+)""", page, flags=re.I) or [None, None])[1],
                 "words": word_count(text), "text_start": text[:600], "controls": controls(page, origin)},
        "ads": ad_state(page),
        "ads_txt": {"status": ads_txt["status"], "google_lines": [l.strip() for l in ads_txt_text.splitlines() if l.strip().lower().startswith("google.com")]},
        "robots": {"status": robots_got["status"], "blocks_google": robots_blocks_google(robots_text)},
        "sitemap": {k: v for k, v in sitemap.items() if k != "urls"},
        "trust_pages": {n: {"url": trust_targets[n], "status": (r or {}).get("status"), "words": (r or {}).get("words"), "robots": (r or {}).get("robots")} for n, r in trust_raw.items()},
        "privacy": {"mentions": {k: bool(re.search(p, privacy_text, flags=re.I)) for k, p in PRIVACY_TERMS.items()}, "last_updated": last_updated.group(1).strip() if last_updated else None},
        "cmp": {"detected": sorted(n for n, s in CMP_SIGNS.items() if s in raw_lower), "note": "raw HTML only; a CMP loaded by JavaScript or shown only in the EEA is not seen"},
        "sampled_pages": [{k: p[k] for k in ("url", "status", "words", "main_words", "robots", "ad_script")} for p in sampled_raw],
        "off_sitemap_pages": [{k: p[k] for k in ("url", "status", "words", "main_words", "robots", "canonical")} for p in off_raw],
        "query_pages": [{**{k: p[k] for k in ("url", "status", "words", "robots", "canonical")}, "robots_disallowed": robots_disallows(robots_text, p["url"])} for p in query_raw],
        "file_links": [{"url": f["url"], "status": f["status"], "type": f["type"]} for f in file_raw],
    }
    report["flags"] = build_flags(report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site")
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()
    report = run(args.site, args.samples, args.timeout)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if report["home"]["status"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
