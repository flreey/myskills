#!/usr/bin/env python3
"""Read-only inventory of Google Analytics and Umami usage in a website project.

    python3 scan.py --project <dir> [--domain example.com] [--format text|json]

Lists, with file:line evidence, everything a GA-to-Umami change has to touch: GA loaders and IDs,
custom events, the guards inside GA code, CSP, privacy text, checks and tests, env variable names,
GA4 report scripts, and any existing Umami integration. It never writes files and never prints
values from real .env or .dev.vars files (only variable names).
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = "site-analytics/scan@1"
UMAMI_HOST = os.environ.get("SITE_ANALYTICS_UMAMI_HOST", "analytics.plugxai.com")
TOOL_ROOT = Path(os.environ.get("UMAMI_TOOL_ROOT", Path.home() / "Projects" / "umami")).expanduser()
MAX_BYTES = 1_500_000
PER_FILE = 6     # findings kept per file and category
PER_CATEGORY = 40

# Build output, dependencies and tool caches: never site source.
SKIP_DIRS = {"node_modules", "dist", "build", "out", "coverage", "__pycache__", "venv", "target",
             "bower_components", "vendor", "storybook-static", "output", "outputs", "artifacts", "tmp", "temp",
             "logs", "backups", "snapshots"}
SKIP_PREFIXES = ("dist-", "build-", "out-")
# Notes, reports, raw captures and datasets: skipped unless they sit inside a site content root
# (public/docs or src/content/docs are pages; docs/reports at the repo root is not).
NOTE_DIRS = {"tasks", "docs", "doc", "seo-audit", "audits", "audit", "notes", "evidence", "archive",
             "archives", "fixtures", "__fixtures__", "examples", "reports", "raw", "data", "ops-data"}
SITE_ROOTS = {"src", "public", "app", "pages", "content", "site", "static"}
CONTENT_DIRS = {"src", "content", "pages", "app", "public", "site", "partials", "layouts", "templates", "views"}
CODE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts", ".astro", ".vue", ".svelte",
            ".html", ".htm", ".njk", ".hbs", ".liquid", ".ejs", ".php", ".py", ".toml", ".yaml", ".yml", ".jsonc"}
CONFIG_NAMES = {"_headers", "_redirects", "package.json", "wrangler.json", "vercel.json", "netlify.toml",
                "umami.config.json"}
CONTENT_EXT = {".md", ".mdx", ".json", ".txt"}
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock",
             "composer.lock", "poetry.lock", "Cargo.lock"}
ENV_EXAMPLE = re.compile(r"\.(example|sample|template|dist)$")

GA_LOADER = [
    ("gtag.js", re.compile(r"googletagmanager\.com/gtag/js")),
    ("Google Tag Manager", re.compile(r"googletagmanager\.com/gtm\.js")),
    ("gtag config", re.compile(r"gtag\s*(?:\?\.)?\s*\(\s*['\"](?:config|js|set)['\"]")),
    ("Universal Analytics", re.compile(r"google-analytics\.com/(?:analytics|ga)\.js|\bga\(\s*['\"]create['\"]")),
    ("@next/third-parties", re.compile(r"@next/third-parties/google")),
    ("GA library", re.compile(r"['\"](?:react-ga4?|vue-gtag|ngx-google-analytics|@analytics/google-analytics)['\"]")),
]
GA_ID = re.compile(r"(?<![A-Za-z0-9-])(G-[A-Z0-9]{8,12}|UA-\d{4,10}-\d{1,4}|GTM-[A-Z0-9]{5,9})(?![A-Za-z0-9-])")
GA_EVENT = re.compile(r"gtag\s*(?:\?\.)?\s*\(\s*['\"]event['\"]|\bsendGAEvent\s*\(|\bReactGA\.event\s*\(|"
                      r"dataLayer\.push\(\s*\{\s*['\"]?event['\"]?\s*:")
GA_MENTION = re.compile(r"\bgtag\b|\bdataLayer\b|googletagmanager|google-analytics\.com|\bGA4?\b|"
                        r"Google Analytics|G-[A-Z0-9]{8,12}")
GUARDS = [
    ("production host check", re.compile(r"location\.(?:hostname|host|origin)\b|\bhostname\s*(?:===|!==|==|!=)|"
                                         r"['\"][a-z0-9-]+\.[a-z]{2,}['\"]\s*\]\s*\.includes")),
    ("QA / debug flag", re.compile(r"[?&]qa=|['\"]qa['\"]|\bdebug_mode\b|\btraffic_origin\b|analytics=off|\bnoanalytics\b", re.I)),
    ("opt-out storage", re.compile(r"\blocalStorage\b|\bsessionStorage\b|ga-disable-|opt[-_]?out", re.I)),
    ("bot / automation filter", re.compile(r"navigator\.webdriver|\bwebdriver\b|\bisbot\b|\bheadless|\bcrawler\b|"
                                           r"\bspider\b|\bbots?\b", re.I)),
    ("consent / do-not-track", re.compile(r"\bdoNotTrack\b|gtag\s*\(\s*['\"]consent['\"]|\bconsent\b", re.I)),
    ("URL scrubbing", re.compile(r"\bpage_location\b|\bpage_path\b|searchParams\.delete|\bredact|\bscrub|"
                                 r"PRIVATE_QUERY|\bsanitiz", re.I)),
]
TOOLING = re.compile(r"^(scripts|tools|bin)/")
CSP = re.compile(r"Content-Security-Policy|\bscript-src\b|\bconnect-src\b", re.I)
GOOGLE_DOMAINS = re.compile(r"googletagmanager\.com|google-analytics\.com|analytics\.google\.com", re.I)
PRIVACY_PATH = re.compile(r"privacy|cookie|legal|terms|policy|about|imprint|disclaimer|datenschutz|gdpr|trust", re.I)
PRIVACY_WORDS = re.compile(r"privacy|cookie", re.I)
PRIVACY_GA = re.compile(r"Google Analytics|\b_ga\b|_ga_\*|\bgtag\b|\bGA4\b|Google Tag Manager|googletagmanager")
PRIVACY_UMAMI = re.compile(r"\bUmami\b", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|cypress|playwright)(/|$)|"
                       r"[._-](test|spec)\.[a-z]+$|(^|/)(tests?|check|verify|smoke|audit)[-_.][^/]*$", re.I)
GA_REPORT = re.compile(r"@google-analytics/(?:data|admin)|\b(?:Beta)?AnalyticsDataClient\b|"
                       r"analyticsdata\.googleapis\.com|analyticsadmin\.googleapis\.com|\brunReport\b|"
                       r"\brunRealtimeReport\b|\bbatchRunReports\b|\bGA4_PROPERTY")
UMAMI_CODE = re.compile(re.escape(UMAMI_HOST) + r"|data-website-id|\bumami\.track\b|window\.umami\b|"
                        r"data-umami-event|data-before-send|umami-connect", re.I)
OTHER_ANALYTICS = [
    ("Cloudflare Web Analytics", re.compile(r"static\.cloudflareinsights\.com|cloudflareinsights", re.I)),
    ("Plausible", re.compile(r"plausible\.io/js", re.I)),
    ("PostHog", re.compile(r"\bposthog\b", re.I)),
    ("Microsoft Clarity", re.compile(r"clarity\.ms", re.I)),
    ("Hotjar", re.compile(r"\bhotjar\b", re.I)),
    ("Mixpanel", re.compile(r"\bmixpanel\b", re.I)),
]
ADS = re.compile(r"\badsbygoogle\b|pagead2\.googlesyndication|ca-pub-\d{10,}")
ENV_NAME = re.compile(r"(?:^|_)(?:GA|GA4|GTAG|GTM)(?:_|$)|GOOGLE_ANALYTICS|MEASUREMENT_ID|GA4?_PROPERTY")
ENV_IN_CODE = re.compile(r"(?:process\.env|import\.meta\.env|\benv)\s*(?:\.\s*|\[\s*['\"])([A-Z][A-Z0-9_]*)")
ENV_ASSIGN = re.compile(r"^\s*(?:export\s+)?['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*[:=]")
DOMAIN_PATTERNS = [
    re.compile(r"metadataBase\s*:\s*new URL\(\s*['\"`]https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9.-])"),
    re.compile(r"\b(?:SITE_URL|SITE_ORIGIN|SITE|siteUrl|siteURL|ORIGIN|CANONICAL_ORIGIN)\s*[:=]\s*['\"`]https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9.-])"),
    re.compile(r"^\s*site\s*:\s*['\"`]https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9.-])", re.M),
    re.compile(r"rel=['\"]canonical['\"][^>]*href=['\"]https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9.-])"),
    re.compile(r"['\"]?pattern['\"]?\s*[:=]\s*['\"]([a-z0-9.-]+\.[a-z]{2,})(?:/\*)?['\"]"),
]
NOT_DOMAINS = re.compile(r"(^|\.)(localhost|example\.(com|org|net)|workers\.dev|pages\.dev|vercel\.app|netlify\.app|"
                         r"local|test|invalid|schema\.org|w3\.org|google\.com|googletagmanager\.com|"
                         r"google-analytics\.com|github\.com|cloudflare\.com|" + re.escape(UMAMI_HOST) + r")$|"
                         r"^\d{1,3}(\.\d{1,3}){3}$")


def rel(root, path):
    return path.relative_to(root).as_posix()


def snippet(line):
    text = " ".join(line.strip().split())
    return text if len(text) <= 160 else text[:157] + "..."


def classify(root, path):
    """Return code, env, content, or None for files the scan should not read."""
    name = path.name
    if name in LOCKFILES or name.endswith((".min.js", ".min.mjs", ".map")):
        return None
    if name.startswith(".env") or name.startswith(".dev.vars"):
        return "env"
    if name.startswith("."):
        return None
    if name in CONFIG_NAMES or path.suffix in CODE_EXT:
        return "code"
    parts = set(path.relative_to(root).parts[:-1])
    if path.suffix in CONTENT_EXT and parts & CONTENT_DIRS:
        return "content"
    return None


def keep_dir(root, directory, name):
    if name in SKIP_DIRS or name.startswith(".") or name.startswith(SKIP_PREFIXES):
        return False
    if name in NOTE_DIRS:
        return bool(set(Path(directory).relative_to(root).parts) & SITE_ROOTS)
    return True


def walk(root):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if keep_dir(root, directory, name))
        for name in sorted(filenames):
            path = Path(directory) / name
            kind = classify(root, path)
            if not kind:
                continue
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            yield path, kind, text


def add(bucket, key, item):
    items = bucket.setdefault(key, [])
    if len(items) < PER_FILE:
        items.append(item)


def scan_files(root):
    found = {name: {} for name in ("ga_loader", "ga_events", "ga_guards", "csp", "privacy_text", "checks",
                                   "ga_reports", "umami", "other_analytics", "ads")}
    ga_ids, env_names, html_pages, html_fragments, privacy_umami = {}, {}, [], [], set()
    csp_flags, domains = {}, {}
    for path, kind, text in walk(root):
        relative = rel(root, path)
        if kind == "env":
            # Names only: real env files can hold secrets.
            example = bool(ENV_EXAMPLE.search(path.name))
            for number, line in enumerate(text.splitlines(), 1):
                match = ENV_ASSIGN.match(line)
                if match and ENV_NAME.search(match.group(1)):
                    env_names.setdefault(match.group(1), []).append(
                        relative + ":" + str(number) + ("" if example else " (value not shown)"))
            continue
        is_test = bool(TEST_PATH.search(relative))
        if path.suffix in {".html", ".htm"} and not is_test:
            (html_pages if re.search(r"</head\s*>", text, re.I) else html_fragments).append(relative)
        if kind == "code" and not is_test:
            for pattern in DOMAIN_PATTERNS:
                for host in pattern.findall(text):
                    host = host.lower().strip(".")
                    host = host[4:] if host.startswith("www.") else host
                    if "." in host and not NOT_DOMAINS.search(host):
                        domains[host] = domains.get(host, 0) + 1
        lines = text.splitlines()
        ga_related = False
        privacy_file = bool(PRIVACY_PATH.search(relative)) or (kind == "content" and PRIVACY_WORDS.search(text))
        for number, line in enumerate(lines, 1):
            where = {"file": relative, "line": number, "text": snippet(line)}
            if kind == "code":
                for label, pattern in GA_LOADER:
                    if pattern.search(line):
                        ga_related = True
                        if not is_test:
                            add(found["ga_loader"], relative, {**where, "match": label})
                        break
                for ga in GA_ID.findall(line):
                    ga_related = True
                    if not is_test:
                        ga_ids.setdefault(ga, []).append(relative + ":" + str(number))
                if GA_EVENT.search(line):
                    ga_related = True
                    if not is_test:
                        add(found["ga_events"], relative, where)
                if GA_REPORT.search(line) and not is_test:
                    add(found["ga_reports"], relative, where)
                if CSP.search(line) and not is_test and not TOOLING.search(relative):
                    add(found["csp"], relative, where)
                if ADS.search(line) and not is_test:
                    add(found["ads"], relative, where)
                for label, pattern in OTHER_ANALYTICS:
                    if pattern.search(line) and not is_test:
                        add(found["other_analytics"], relative, {**where, "match": label})
                for env in ENV_IN_CODE.findall(line):
                    if ENV_NAME.search(env):
                        env_names.setdefault(env, []).append(relative + ":" + str(number))
            if UMAMI_CODE.search(line):
                add(found["umami"], relative, {**where, "test": is_test})
            if PRIVACY_GA.search(line) and (privacy_file or (kind == "code" and PRIVACY_WORDS.search(line))):
                if not is_test:
                    add(found["privacy_text"], relative, where)
            if PRIVACY_UMAMI.search(line) and privacy_file and not is_test:
                privacy_umami.add(relative)
        if kind == "code" and is_test and GA_MENTION.search(text):
            hits = [number for number, line in enumerate(lines, 1) if GA_MENTION.search(line)]
            for number in hits[:3]:
                add(found["checks"], relative, {"file": relative, "line": number, "text": snippet(lines[number - 1])})
        if kind == "code" and found["csp"].get(relative):
            csp_flags[relative] = {"google": bool(GOOGLE_DOMAINS.search(text)), "umami": UMAMI_HOST in text}
        if kind == "code" and not is_test and (ga_related or re.search(r"analytic", path.name, re.I)):
            if ga_related or GA_MENTION.search(text):
                for number, line in enumerate(lines, 1):
                    for label, pattern in GUARDS:
                        if pattern.search(line):
                            add(found["ga_guards"], relative,
                                {"file": relative, "line": number, "match": label, "text": snippet(line)})
                            break
    ranked = [host for host, _ in sorted(domains.items(), key=lambda item: (-item[1], item[0]))][:5]
    return {"found": found, "ga_ids": ga_ids, "env_names": env_names, "html_pages": html_pages,
            "html_fragments": html_fragments, "privacy_umami": privacy_umami, "csp_flags": csp_flags,
            "domains": ranked}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def detect_framework(root, html_pages, html_fragments=()):
    package = read_json(root / "package.json") or {}
    deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    names = [name for name in ("next", "astro") if name in deps]
    app_layouts = [prefix + "app/layout." + ext for prefix in ("", "src/") for ext in ("tsx", "jsx", "js")
                   if (root / (prefix + "app/layout." + ext)).is_file()]
    pages_router = [prefix + "pages/" + name + "." + ext for prefix in ("", "src/") for name in ("_document", "_app")
                    for ext in ("tsx", "jsx", "js") if (root / (prefix + "pages/" + name + "." + ext)).is_file()]
    if len(names) > 1:
        return {"kind": "ambiguous", "connect": "manual", "entries": [],
                "note": "package.json lists both next and astro; pass --framework and --entry explicitly"}
    if names == ["next"]:
        if len(app_layouts) == 1:
            return {"kind": "next-app", "connect": "auto", "entries": app_layouts}
        if app_layouts:
            return {"kind": "next-app", "connect": "entry", "entries": app_layouts,
                    "note": "several root layouts; pass each shared root layout with --entry"}
        return {"kind": "next-pages", "connect": "manual", "entries": pages_router,
                "note": "Pages Router is not auto-connected; add the tracker in pages/_document or pages/_app"}
    if names == ["astro"]:
        layouts = sorted(rel(root, path) for path in (root / "src" / "layouts").glob("*.astro")
                         if re.search(r"</head\s*>", path.read_text(encoding="utf-8", errors="ignore"), re.I))
        if len(layouts) == 1:
            return {"kind": "astro", "connect": "auto", "entries": layouts}
        if layouts:
            return {"kind": "astro", "connect": "entry", "entries": layouts,
                    "note": "several layouts contain </head>; pass every shared layout with --entry"}
        return {"kind": "astro", "connect": "manual", "entries": [],
                "note": "no src/layouts/*.astro contains </head>; find where <head> is rendered"}
    others = sorted(page for page in html_pages if page != "index.html")
    partials = (" HTML fragments without </head> (likely shared partials): " + ", ".join(list(html_fragments)[:8])
                if html_fragments else "")
    if (root / "index.html").is_file():
        kind = "vite-html" if "vite" in deps else "html"
        if others:
            return {"kind": kind, "connect": "entry", "entries": ["index.html"] + others[:30],
                    "note": str(len(others)) + " more HTML pages; connect each with --entry or the shared "
                            "include/partial/script that every page loads." + partials}
        return {"kind": kind, "connect": "auto", "entries": ["index.html"]}
    if others:
        return {"kind": "vite-html" if "vite" in deps else "static-html", "connect": "entry", "entries": others[:30],
                "note": str(len(others)) + " HTML pages and no root index.html; use --framework html with --entry, "
                        "or edit the shared include/script every page loads." + partials}
    if "hono" in deps or (root / "wrangler.toml").is_file() or (root / "wrangler.jsonc").is_file():
        return {"kind": "worker-ssr", "connect": "manual", "entries": [],
                "note": "server-rendered HTML; add the tracker to the shared <head> template by hand"}
    return {"kind": "unknown", "connect": "manual", "entries": []}


def git(root, *args):
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def umami_since(root, config):
    """Date the Umami integration first landed in git history, if the project is a git repo."""
    if config:
        out = git(root, "log", "--diff-filter=A", "--format=%cI", "--", "umami.config.json")
        if out and out.strip():
            return out.strip().splitlines()[-1]
    out = git(root, "log", "-S" + UMAMI_HOST, "--format=%cI", "--reverse")
    return out.strip().splitlines()[0] if out and out.strip() else None


def flatten(bucket):
    items = [item for values in bucket.values() for item in values]
    return items[:PER_CATEGORY], max(0, len(items) - PER_CATEGORY)


def scan(root, domain=None):
    facts = scan_files(root)
    found, ga_ids, env_names = facts["found"], facts["ga_ids"], facts["env_names"]
    privacy_umami, csp_flags = facts["privacy_umami"], facts["csp_flags"]
    framework = detect_framework(root, facts["html_pages"], facts["html_fragments"])
    config = read_json(root / "umami.config.json")
    if config and config.get("generator") != "umami-connect":
        config = {"unmanaged": True}
    umami_live = [item for values in found["umami"].values() for item in values if not item["test"]]
    ga_present = bool(found["ga_loader"] or found["ga_events"] or ga_ids)
    umami_present = bool(config or umami_live)
    privacy_ga = sorted(found["privacy_text"])
    csp_google = sorted(path for path, flags in csp_flags.items() if flags["google"])
    csp_missing_umami = sorted(path for path, flags in csp_flags.items() if not flags["umami"])
    leftovers = []
    if not ga_present:
        if env_names:
            leftovers.append("GA env variable names")
        if csp_google:
            leftovers.append("Google domains in CSP")
        if privacy_ga:
            leftovers.append("GA wording in privacy/legal text")
        if found["ga_reports"]:
            leftovers.append("GA4 report scripts")
        if found["checks"]:
            leftovers.append("checks/tests that mention GA")
    if ga_present and not umami_present:
        phase, step = "ga-only", "Release 1: add Umami next to GA (parallel), keep GA running"
    elif ga_present:
        phase, step = "parallel", "Check the parallel period with report.py, then Release 2 removes GA"
    elif umami_present:
        phase = "umami-only"
        step = "Remove GA leftovers: " + ", ".join(leftovers) if leftovers else "Nothing left to migrate"
    else:
        phase, step = "none", "No GA to replace: connect Umami only"
    since = umami_since(root, config) if umami_present else None
    days = None
    if since:
        try:
            days = (datetime.now(timezone.utc) - datetime.fromisoformat(since)).days
        except ValueError:
            days = None
    domains = [domain] if domain else facts["domains"]
    command = None
    simple = framework["connect"] == "auto" or (
        framework["connect"] == "entry" and len(framework["entries"]) <= 6 and "fragments" not in framework.get("note", ""))
    if not umami_present and simple:
        parts = [str(TOOL_ROOT / "umami-connect"), domains[0] if domains else "<domain>", "--project", str(root),
                 "--name", "'<Site name>'"]
        if framework["connect"] == "entry":
            parts += ["--framework", "next" if framework["kind"].startswith("next") else
                      "astro" if framework["kind"] == "astro" else "html"]
            for entry in framework["entries"]:
                parts += ["--entry", entry]
        command = " ".join(parts + ["--dry-run"])
    dirty = git(root, "status", "--porcelain")
    categories = {}
    for name in ("ga_loader", "ga_events", "ga_guards", "csp", "privacy_text", "checks", "ga_reports",
                 "umami", "other_analytics", "ads"):
        items, more = flatten(found[name])
        categories[name] = {"files": sorted(found[name]), "items": items, "more": more}
    return {
        "schema": SCHEMA,
        "project": str(root),
        "scanned_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "framework": framework,
        "domain_candidates": domains,
        "phase": phase,
        "next_step": step,
        "connect_preview": command,
        "git_dirty_files": None if dirty is None else len([line for line in dirty.splitlines() if line.strip()]),
        "umami": {"config": config, "since": since, "days_in_git": days,
                  "privacy_mentions_umami": sorted(privacy_umami)},
        "ga_ids": {key: value[:6] for key, value in sorted(ga_ids.items())},
        "env_names": {key: value[:6] for key, value in sorted(env_names.items())},
        "csp": {"files": sorted(csp_flags), "with_google": csp_google, "without_umami_host": csp_missing_umami},
        "categories": categories,
    }


TITLES = [
    ("ga_loader", "GA loader"),
    ("ga_events", "GA custom events (call sites)"),
    ("ga_guards", "Guards inside GA code (port each: before-send, or --exclude-search/--exclude-hash for URL scrubbing)"),
    ("csp", "CSP directives"),
    ("privacy_text", "Privacy/legal text mentioning GA"),
    ("checks", "Checks/tests mentioning GA (read each: own-GA assertion or product feature?)"),
    ("ga_reports", "GA4 report scripts (switch to report.py or retire, user decides)"),
    ("umami", "Existing Umami code"),
    ("other_analytics", "Other analytics (keep them in the privacy text)"),
    ("ads", "Ads (their cookies stay disclosed after GA goes)"),
]


def render(report):
    framework = report["framework"]
    lines = ["site-analytics scan: " + report["project"],
             "framework: " + framework["kind"] + " (umami-connect: " + framework["connect"]
             + ((", entries: " + ", ".join(framework["entries"][:8])) if framework["entries"] else "") + ")"]
    if framework.get("note"):
        lines.append("  note: " + framework["note"])
    lines.append("domain candidates: " + (", ".join(report["domain_candidates"]) or "none found (pass --domain)"))
    if report["git_dirty_files"]:
        lines.append("git: " + str(report["git_dirty_files"]) + " uncommitted file(s); do not edit files someone else is changing")
    umami = report["umami"]
    phase = "phase: " + report["phase"]
    if umami["since"]:
        phase += (" (Umami in git since " + umami["since"][:10] + ("" if umami["days_in_git"] is None else
                  ", " + str(umami["days_in_git"]) + " days ago") + "; production counts from the deploy:"
                  " report.py --daily shows the first day with data)")
    lines += [phase, "next: " + report["next_step"]]
    if report["connect_preview"]:
        lines.append("preview: " + report["connect_preview"])
    if report["ga_ids"]:
        lines.append("GA IDs: " + "; ".join(key + " (" + ", ".join(value[:3]) + ")" for key, value in report["ga_ids"].items()))
    if report["env_names"]:
        lines.append("GA env names: " + "; ".join(key + " (" + ", ".join(value[:3]) + ")"
                                                   for key, value in report["env_names"].items()))
    csp = report["csp"]
    if csp["files"]:
        lines.append("CSP files: " + ", ".join(csp["files"]) + (" | Google domains in: " + ", ".join(csp["with_google"])
                                                               if csp["with_google"] else "")
                     + (" | missing " + UMAMI_HOST + " in: " + ", ".join(csp["without_umami_host"])
                        if csp["without_umami_host"] else ""))
    if umami["privacy_mentions_umami"]:
        lines.append("privacy text already mentions Umami in: " + ", ".join(umami["privacy_mentions_umami"]))
    for key, title in TITLES:
        category = report["categories"][key]
        if not category["items"]:
            continue
        lines.append("")
        lines.append(title + " (" + str(len(category["files"])) + " file(s))")
        for item in category["items"]:
            label = (" [" + item["match"] + "]") if item.get("match") else ""
            test = " [test]" if item.get("test") else ""
            lines.append("  " + item["file"] + ":" + str(item["line"]) + label + test + "  " + item["text"])
        if category["more"]:
            lines.append("  ... " + str(category["more"]) + " more (use --format json)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root (default: current directory)")
    parser.add_argument("--domain", help="Production domain, if the scan cannot find it")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    if not root.is_dir():
        print("Error: project directory does not exist: " + str(root), file=sys.stderr)
        return 2
    report = scan(root, args.domain)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
