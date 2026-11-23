#!/usr/bin/env python3
"""Portfolio operating loop: data sources check, daily snapshots, guard alerts and the weekly review.

    python3 ops.py init     [--projects ~/Projects]             create the growth home from the sites found
    python3 ops.py check    [--site host]... [--format text|json]
    python3 ops.py collect  [--days 3] [--site host]...          upsert daily numbers into data/snapshots.sqlite
    python3 ops.py guard    [--no-notify]                        collect, check, alert on breakage
    python3 ops.py weekly   [--date YYYY-MM-DD] [--write] [--format md|json]
    python3 ops.py schedule [--install | --uninstall]            launchd jobs for guard (daily) and weekly

The growth home is ~/Projects/growth (override with GROWTH_HOME): portfolio.json (sites, stages,
thresholds, notify command), experiments.json, playbook.md, weekly/, alerts.md, data/ (not in git) and
credentials.local.json (not in git: bing_api_key, cloudflare_api_token; env BING_API_KEY and
CLOUDFLARE_API_TOKEN win). Search Console uses the local gcloud application-default credentials
(read-only scope is enough). Everything here only reads the sources; it writes nothing to them.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("GROWTH_HOME", Path.home() / "Projects" / "growth")).expanduser()
PLANS = HERE.parent / "references" / "tracking-plans.json"
PORTFOLIO_SCHEMA = "site-measure/portfolio@1"
STANDARD = ["core_start", "core_done", "takeaway", "error", "paid"]
STD_LABEL = {"core_start": "核心开始", "core_done": "核心完成", "takeaway": "拿走结果", "error": "报错", "paid": "付款"}
STAGES = {"validate": "验证", "growth": "增长", "monetize": "变现", "maintain": "维护"}
DEFAULT_THRESHOLDS = {
    "validate_weeks": 8,            # weeks of data before a validate site is judged
    "maintain_impressions_7d": 500,  # below this (Search Console) ...
    "maintain_north_star_7d": 10,    # ... and below this, suggest maintain
    "growth_visitors_7d": 100,       # validate -> growth when visitors reach this and the north star grows
    "monetize_visitors_7d": 300,     # growth -> monetize after 3 weeks at this level
    "small_sample": 30,              # below this a rate is an anecdote
    "use_rate": 0.2,                 # core_start / visitors
    "done_rate": 0.6,                # core_done / core_start
    "error_rate": 0.1,               # error / core_start
    "takeaway_rate": 0.3,            # takeaway / core_done
}
GUARD = {"event_min_daily": 5, "drop_min_daily": 20, "drop_ratio": 0.4, "error_5xx_share": 0.02, "error_min_requests": 200}
GSC_LAG_DAYS = 3


# ---------------------------------------------------------------- files

def home(path=None):
    return Path(path).expanduser() if path else HOME


def load_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    return json.loads(path.read_text())


def load_portfolio(root):
    data = load_json(root / "portfolio.json")
    if not data:
        raise ValueError(str(root / "portfolio.json") + " not found; run: python3 ops.py init")
    data.setdefault("thresholds", {})
    data["thresholds"] = {**DEFAULT_THRESHOLDS, **data["thresholds"]}
    return data


def credentials(root):
    stored = load_json(root / "credentials.local.json", {}) or {}
    return {
        "bing": os.environ.get("BING_API_KEY") or stored.get("bing_api_key"),
        "cloudflare": os.environ.get("CLOUDFLARE_API_TOKEN") or stored.get("cloudflare_api_token"),
    }


def site_spec(site):
    project = site.get("project")
    if not project:
        return None
    return load_json(Path(project).expanduser() / "umami-reports.json")


def plans():
    return load_json(PLANS)["types"]


# ---------------------------------------------------------------- standard events

def standard_events(site, spec, observed, plan_types=None):
    """Map the five standard events to the site's own event names.

    The site's umami-reports.json "standard" wins; otherwise each standard event takes the plan role of the
    site's type and matches observed event names against that role's aliases (a guess, labelled as one)."""
    explicit = (spec or {}).get("standard") or {}
    plan_types = plan_types or plans()
    mapping, origin = {}, {}
    for key in STANDARD:
        if key in explicit:
            names = explicit[key] if isinstance(explicit[key], list) else [explicit[key]]
            mapping[key], origin[key] = [n for n in names if n], "spec"
            continue
        names = []
        for t in site.get("types") or []:
            plan = plan_types.get(t) or {}
            role = (plan.get("standard") or {}).get(key)
            if not role:
                continue
            aliases = next((r["aliases"] for r in plan.get("roles", []) if r["role"] == role), None)
            pattern = re.compile("(?:" + (aliases + "|" if aliases else "") + re.escape(role) + ")$")
            names += [n for n in observed if pattern.match(n) and n not in names]
        mapping[key], origin[key] = names, "guess"
    return mapping, origin


def north_star(site, spec, plan_types=None):
    if spec and spec.get("northStar"):
        return spec["northStar"]
    plan_types = plan_types or plans()
    for t in site.get("types") or []:
        if (plan_types.get(t) or {}).get("north_star"):
            return plan_types[t]["north_star"]
    return "takeaway"


# ---------------------------------------------------------------- sources

class Http:
    def __init__(self, opener=None):
        self.opener = opener or urllib.request.build_opener()

    def json(self, url, headers=None, body=None, timeout=40):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers={"Accept": "application/json",
                                                              **({"Content-Type": "application/json"} if data else {}),
                                                              **(headers or {})})
        for attempt in (1, 2):
            try:
                with self.opener.open(req, timeout=timeout) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                raise RuntimeError("HTTP " + str(error.code) + " from " + url.split("?", 1)[0]) from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise RuntimeError("unreachable: " + url.split("?", 1)[0]) from None


def load_umami():
    spec = importlib.util.spec_from_file_location("site_measure_report", HERE / "report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool = module.load_tool()
    return UmamiSource(tool.Umami(), tool, module)


class UmamiSource:
    def __init__(self, api, tool, report):
        self.api, self.tool, self.report, self.ids = api, tool, report, {}

    def website(self, domain):
        if domain not in self.ids:
            found = self.api.find(self.tool.normalize_domain(domain))
            self.ids[domain] = found and found["id"]
        return self.ids[domain]

    def day(self, website_id, start_ms, end_ms):
        base = "/api/websites/" + website_id
        span = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms})
        stats = self.api.request(base + "/stats?" + span)
        query = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms, "type": "event", "limit": 500})
        events = self.report.rows(self.api.request(base + "/metrics?" + query))
        n = self.report.number
        out = {"pageviews": n(stats.get("pageviews")), "visitors": n(stats.get("visitors")), "visits": n(stats.get("visits"))}
        for row in events:
            out["event:" + row["value"]] = row["count"]
        return out

    def days(self, website_id, first, last):
        """Daily pageviews, visitors (sessions) and event counts for first..last (UTC) in two requests."""
        base = "/api/websites/" + website_id
        start, _ = day_ms(first)
        _, end = day_ms(last)
        query = urllib.parse.urlencode({"startAt": start, "endAt": end, "unit": "day", "timezone": "UTC"})
        out = {}
        views = self.api.request(base + "/pageviews?" + query)
        for key, metric in (("pageviews", "pageviews"), ("sessions", "visitors")):
            for row in views.get(key) or []:
                out.setdefault(row["x"][:10], {})[metric] = self.report.number(row["y"])
        for row in self.api.request(base + "/events/series?" + query) or []:
            out.setdefault(row["t"][:10], {})["event:" + str(row["x"])] = self.report.number(row["y"])
        return out


class SearchConsole:
    API = "https://www.googleapis.com/webmasters/v3"

    def __init__(self, http=None, token=None, project=None):
        self.http = http or Http()
        self.token, self.project, self._sites = token, project, None
        if not self.token:
            gcloud = shutil.which("gcloud") or "/usr/local/bin/gcloud"
            self.token = subprocess.run([gcloud, "auth", "application-default", "print-access-token"],
                                        capture_output=True, text=True, timeout=60).stdout.strip()
            self.project = self.project or os.environ.get("GSC_QUOTA_PROJECT") or subprocess.run(
                [gcloud, "config", "get-value", "project"], capture_output=True, text=True, timeout=60).stdout.strip()
        if not self.token:
            raise RuntimeError("no gcloud application-default credentials (gcloud auth application-default login)")

    def headers(self):
        h = {"Authorization": "Bearer " + self.token}
        if self.project:
            h["x-goog-user-project"] = self.project
        return h

    def property(self, domain, override=None):
        if self._sites is None:
            self._sites = {s["siteUrl"]: s.get("permissionLevel")
                           for s in self.http.json(self.API + "/sites", self.headers()).get("siteEntry", [])}
        for candidate in ([override] if override else []) + ["sc-domain:" + domain, "https://" + domain + "/",
                                                              "https://www." + domain + "/"]:
            level = self._sites.get(candidate)
            if level and level != "siteUnverifiedUser":
                return candidate
        return None

    def sitemaps(self, prop):
        url = self.API + "/sites/" + urllib.parse.quote(prop, safe="") + "/sitemaps"
        return self.http.json(url, self.headers()).get("sitemap", [])

    def daily(self, prop, start, end):
        url = self.API + "/sites/" + urllib.parse.quote(prop, safe="") + "/searchAnalytics/query"
        body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["date"], "dataState": "all"}
        rows = self.http.json(url, self.headers(), body).get("rows", [])
        return {r["keys"][0]: {"clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
                               "position": round(r.get("position", 0), 1)} for r in rows}


class Bing:
    """Bing Webmaster API (JSON). Shapes follow Microsoft's API reference; not yet run against a real key."""
    API = "https://ssl.bing.com/webmaster/api.svc/json/"

    def __init__(self, key, http=None):
        self.key, self.http, self._sites = key, http or Http(), None

    def site(self, domain):
        if self._sites is None:
            self._sites = self.http.json(self.API + "GetUserSites?apikey=" + urllib.parse.quote(self.key)).get("d") or []
        for s in self._sites:
            host = urllib.parse.urlsplit(s.get("Url", "")).hostname or ""
            if host in (domain, "www." + domain):
                return s
        return None

    def daily(self, site_url):
        query = urllib.parse.urlencode({"siteUrl": site_url, "apikey": self.key})
        out = {}
        for row in self.http.json(self.API + "GetRankAndTrafficStats?" + query).get("d") or []:
            ms = re.search(r"-?\d+", str(row.get("Date", "")))
            if ms:
                day = datetime.fromtimestamp(int(ms.group()) / 1000, timezone.utc).date().isoformat()
                out[day] = {"clicks": row.get("Clicks", 0), "impressions": row.get("Impressions", 0)}
        return out


class Cloudflare:
    """Zone lookup plus daily requests and 5xx from the GraphQL Analytics API; not yet run against a real token."""
    API = "https://api.cloudflare.com/client/v4"
    QUERY = ("query($zone:String!,$since:Date!,$until:Date!){viewer{zones(filter:{zoneTag:$zone}){"
             "httpRequests1dGroups(limit:100,filter:{date_geq:$since,date_leq:$until}){dimensions{date}"
             "sum{requests responseStatusMap{edgeResponseStatus requests}}}}}}")

    def __init__(self, token, http=None):
        self.token, self.http = token, http or Http()

    def headers(self):
        return {"Authorization": "Bearer " + self.token}

    def zone(self, domain):
        result = self.http.json(self.API + "/zones?name=" + urllib.parse.quote(domain), self.headers()).get("result") or []
        return result[0]["id"] if result else None

    def daily(self, zone_id, start, end):
        body = {"query": self.QUERY, "variables": {"zone": zone_id, "since": start.isoformat(), "until": end.isoformat()}}
        data = self.http.json(self.API + "/graphql", self.headers(), body)
        if data.get("errors"):
            raise RuntimeError("Cloudflare GraphQL: " + str(data["errors"][0].get("message")))
        zones = ((data.get("data") or {}).get("viewer") or {}).get("zones") or []
        out = {}
        for group in (zones[0].get("httpRequests1dGroups") if zones else []) or []:
            statuses = group["sum"].get("responseStatusMap") or []
            out[group["dimensions"]["date"]] = {
                "requests": group["sum"].get("requests", 0),
                "5xx": sum(s["requests"] for s in statuses if 500 <= int(s["edgeResponseStatus"]) < 600)}
        return out


class Sources:
    """Lazily opened clients; a source that cannot open is recorded once and reported as unavailable."""

    def __init__(self, root, factories=None):
        self.root, self.errors, self.cache = root, {}, {}
        creds = credentials(root)
        self.factories = factories or {
            "umami": load_umami,
            "gsc": lambda: SearchConsole(),
            "bing": (lambda: Bing(creds["bing"])) if creds["bing"] else None,
            "cloudflare": (lambda: Cloudflare(creds["cloudflare"])) if creds["cloudflare"] else None,
        }

    def get(self, name):
        if name in self.cache:
            return self.cache[name]
        factory, client = self.factories.get(name), None
        if factory is None:
            self.errors[name] = "nocred"
        else:
            try:
                client = factory()
            except Exception as error:  # noqa: BLE001 - reported per source
                self.errors[name] = str(error)
        self.cache[name] = client
        return client


# ---------------------------------------------------------------- snapshots

def db(root):
    (root / "data").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(root / "data" / "snapshots.sqlite")
    con.execute("CREATE TABLE IF NOT EXISTS metrics (site TEXT, day TEXT, source TEXT, metric TEXT, value REAL,"
                " PRIMARY KEY (site, day, source, metric))")
    con.execute("CREATE TABLE IF NOT EXISTS checks (site TEXT, source TEXT, item TEXT, status TEXT, detail TEXT,"
                " checked_at TEXT, PRIMARY KEY (site, source, item))")
    return con


def upsert(con, site, day, source, values):
    con.executemany("INSERT OR REPLACE INTO metrics VALUES (?,?,?,?,?)",
                    [(site, day, source, k, float(v)) for k, v in values.items() if isinstance(v, (int, float))])


def series(con, site, source, metric, first, last):
    rows = con.execute("SELECT day, value FROM metrics WHERE site=? AND source=? AND metric=? AND day BETWEEN ? AND ?",
                       (site, source, metric, first.isoformat(), last.isoformat())).fetchall()
    return dict(rows)


def total(con, site, source, metrics, first, last):
    if isinstance(metrics, str):
        metrics = [metrics]
    if not metrics:
        return 0
    marks = ",".join("?" * len(metrics))
    row = con.execute("SELECT SUM(value) FROM metrics WHERE site=? AND source=? AND metric IN (" + marks + ")"
                      " AND day BETWEEN ? AND ?", (site, source, *metrics, first.isoformat(), last.isoformat())).fetchone()
    return row[0] or 0


def observed_events(con, site, days=60, today=None):
    today = today or datetime.now(timezone.utc).date()
    rows = con.execute("SELECT DISTINCT metric FROM metrics WHERE site=? AND source='umami' AND metric LIKE 'event:%'"
                       " AND day >= ?", (site, (today - timedelta(days=days)).isoformat())).fetchall()
    return sorted(r[0][6:] for r in rows)


def day_ms(day):
    start = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)
    return start, start + 86_400_000 - 1


def collect(root, portfolio, sources, days=3, only=None, today=None, log=print):
    today = today or datetime.now(timezone.utc).date()
    con = db(root)
    for site in portfolio["sites"]:
        domain = site["domain"]
        if only and domain not in only:
            continue
        umami = sources.get("umami")
        if umami:
            try:
                website = umami.website(domain)
                if website:  # today is partial; the next run overwrites it
                    for day, values in umami.days(website, today - timedelta(days=days), today).items():
                        upsert(con, domain, day, "umami", values)
                    for back in range(min(days, 8), -1, -1):  # visits need /stats per day; the week is enough
                        day = today - timedelta(days=back)
                        upsert(con, domain, day.isoformat(), "umami", {"visits": umami.day(website, *day_ms(day))["visits"]})
            except Exception as error:  # noqa: BLE001
                log("umami " + domain + ": " + str(error))
        gsc = sources.get("gsc")
        if gsc:
            try:
                prop = gsc.property(domain, site.get("gsc"))
                if prop:
                    span = max(days, GSC_LAG_DAYS + 2)
                    for day, values in gsc.daily(prop, today - timedelta(days=span), today).items():
                        upsert(con, domain, day, "gsc", values)
            except Exception as error:  # noqa: BLE001
                log("gsc " + domain + ": " + str(error))
        bing = sources.get("bing")
        if bing:
            try:
                found = bing.site(domain)
                if found:
                    for day, values in bing.daily(found["Url"]).items():
                        upsert(con, domain, day, "bing", values)
            except Exception as error:  # noqa: BLE001
                log("bing " + domain + ": " + str(error))
        cf = sources.get("cloudflare")
        if cf:
            try:
                zone = cf.zone(domain)
                if zone:
                    for day, values in cf.daily(zone, today - timedelta(days=days), today).items():
                        upsert(con, domain, day, "cloudflare", values)
            except Exception as error:  # noqa: BLE001
                log("cloudflare " + domain + ": " + str(error))
        con.commit()
    con.close()


# ---------------------------------------------------------------- check

def check(root, portfolio, sources, only=None, today=None):
    """One row per site and item: status ok | warn | fail | nocred | skip, with a short detail."""
    today = today or datetime.now(timezone.utc).date()
    week = (today - timedelta(days=7), today)
    results = []
    con = db(root)
    plan_types = plans()
    for site in portfolio["sites"]:
        domain = site["domain"]
        if only and domain not in only:
            continue
        rows = []

        def add(source, item, status, detail=""):
            rows.append({"site": domain, "source": source, "item": item, "status": status, "detail": detail})

        umami = sources.get("umami")
        if not umami:
            add("umami", "website", "fail", sources.errors.get("umami", ""))
        else:
            website_id = None
            try:
                website_id = umami.website(domain)
            except Exception as error:  # noqa: BLE001
                add("umami", "website", "fail", str(error))
            if website_id:
                add("umami", "website", "ok")
                pv = total(con, domain, "umami", "pageviews", *week)
                if pv == 0:  # snapshot may be empty on a first run: read Umami directly
                    start, _ = day_ms(week[0])
                    _, end = day_ms(today)
                    pv = umami.day(website_id, start, end).get("pageviews", 0)
                add("umami", "pageviews_7d", "ok" if pv else "fail", str(int(pv)))
            elif not any(r["item"] == "website" for r in rows):
                add("umami", "website", "fail", "not registered")
        spec = site_spec(site)
        add("umami", "spec", "ok" if spec else "warn", "umami-reports.json" if spec else "no umami-reports.json")
        observed = observed_events(con, domain, today=today)
        mapping, origin = standard_events(site, spec, observed, plan_types)
        needed = {north_star(site, spec, plan_types), "core_start", "core_done"} | ({"paid"} if site.get("sells") else set())
        for key in STANDARD:
            if key not in needed:
                continue
            names = mapping.get(key) or []
            count = total(con, domain, "umami", ["event:" + n for n in names], *week)
            if not names:
                add("umami", "event:" + key, "fail", "no event mapped (set standard." + key + " in umami-reports.json)")
            elif count == 0:
                add("umami", "event:" + key, "warn", ",".join(names) + " seen 0 times in 7 days")
            else:
                add("umami", "event:" + key, "ok" if origin[key] == "spec" else "warn",
                    ",".join(names) + " = " + str(int(count)) + ("" if origin[key] == "spec" else " (guessed; confirm in spec)"))

        gsc = sources.get("gsc")
        if not gsc:
            add("gsc", "property", "nocred", sources.errors.get("gsc", ""))
        else:
            try:
                prop = gsc.property(domain, site.get("gsc"))
                add("gsc", "property", "ok" if prop else "fail", prop or "not verified in this Google account")
                if prop:
                    maps = gsc.sitemaps(prop)
                    downloaded = [m.get("lastDownloaded", "")[:10] for m in maps if m.get("lastDownloaded")]
                    if not maps:
                        add("gsc", "sitemap", "fail", "no sitemap submitted")
                    elif not downloaded or max(downloaded) < (today - timedelta(days=14)).isoformat():
                        add("gsc", "sitemap", "warn", "last read by Google " + (max(downloaded) if downloaded else "never"))
                    else:
                        add("gsc", "sitemap", "ok", "read " + max(downloaded))
            except Exception as error:  # noqa: BLE001
                add("gsc", "property", "fail", str(error))

        for name, item, finder in (("bing", "site", lambda c: c.site(domain)), ("cloudflare", "zone", lambda c: c.zone(domain))):
            client = sources.get(name)
            if not client:
                add(name, item, "nocred", "credential not set" if sources.errors.get(name) == "nocred" else sources.errors.get(name, ""))
                continue
            try:
                found = finder(client)
                add(name, item, "ok" if found else "fail", "" if found else "not found")
            except Exception as error:  # noqa: BLE001
                add(name, item, "fail", str(error))
        if site.get("sells"):
            add("stripe", "revenue", "skip", "not connected yet")
        results += rows
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    previous = {(r[0], r[1], r[2]): r[3] for r in con.execute("SELECT site, source, item, status FROM checks")}
    for r in results:
        r["previous"] = previous.get((r["site"], r["source"], r["item"]))
        con.execute("INSERT OR REPLACE INTO checks VALUES (?,?,?,?,?,?)",
                    (r["site"], r["source"], r["item"], r["status"], r["detail"], stamp))
    con.commit()
    con.close()
    return results


MARK = {"ok": "✅", "warn": "⚠️", "fail": "❌", "nocred": "🔑", "skip": "—"}


def render_check(results):
    lines, current = [], None
    for r in results:
        if r["site"] != current:
            current = r["site"]
            lines.append("")
            lines.append(current)
        lines.append("  " + MARK[r["status"]] + " " + r["source"] + "." + r["item"] + ("  " + r["detail"] if r["detail"] else ""))
    bad = sum(r["status"] == "fail" for r in results)
    lines.append("")
    lines.append(str(bad) + " failing, " + str(sum(r["status"] == "warn" for r in results)) + " warnings, "
                 + str(sum(r["status"] == "nocred" for r in results)) + " without credentials")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------- weekly

def ratio(a, b, floor):
    if b < floor:
        return None
    return round(a / b, 2) if b else None


def site_week(con, site, spec, thresholds, end, plan_types=None):
    """Numbers for the 7 days ending `end` (inclusive) against the 4 weeks before; Search Console lags 3 days."""
    plan_types = plan_types or plans()
    domain = site["domain"]
    first = end - timedelta(days=6)
    mapping, origin = standard_events(site, spec, observed_events(con, domain, today=end), plan_types)
    ns_key = north_star(site, spec, plan_types)

    def ev(key, a, b):
        return total(con, domain, "umami", ["event:" + n for n in mapping.get(key) or []], a, b)

    weeks = []
    for back in range(4, -1, -1):  # oldest first, last is this week
        b = end - timedelta(days=7 * back)
        a = b - timedelta(days=6)
        weeks.append({"start": a.isoformat(), "visitors": total(con, domain, "umami", "visitors", a, b),
                      "north_star": ev(ns_key, a, b)})
    g_end = end - timedelta(days=GSC_LAG_DAYS)
    g_first = g_end - timedelta(days=6)
    gsc = {"impressions": total(con, domain, "gsc", "impressions", g_first, g_end),
           "clicks": total(con, domain, "gsc", "clicks", g_first, g_end),
           "impressions_prev": total(con, domain, "gsc", "impressions", g_first - timedelta(days=7), g_first - timedelta(days=1))}
    data_days = con.execute("SELECT MIN(day) FROM metrics WHERE site=? AND ((source='umami' AND metric='pageviews' AND value>0)"
                            " OR (source='gsc' AND metric='impressions' AND value>0))", (domain,)).fetchone()[0]
    week = {
        "site": domain, "stage": site.get("stage", "validate"), "types": site.get("types"),
        "north_star": {"key": ns_key, "label": STD_LABEL[ns_key], "events": mapping.get(ns_key), "origin": origin.get(ns_key)},
        "visitors": total(con, domain, "umami", "visitors", first, end),
        "visits": total(con, domain, "umami", "visits", first, end),
        "pageviews": total(con, domain, "umami", "pageviews", first, end),
        "events": {k: ev(k, first, end) for k in STANDARD},
        "mapping": mapping, "origin": origin, "weeks": weeks, "gsc": gsc,
        "bing_impressions": total(con, domain, "bing", "impressions", g_first, g_end),
        "cf": {"requests": total(con, domain, "cloudflare", "requests", first, end),
               "5xx": total(con, domain, "cloudflare", "5xx", first, end)},
        "first_data": data_days,
    }
    week["weeks_of_data"] = ((end - date.fromisoformat(data_days)).days // 7) if data_days else 0
    prev4 = [w["north_star"] for w in weeks[:-1]]
    week["north_star"]["value"] = weeks[-1]["north_star"]
    week["north_star"]["avg_prev4"] = round(sum(prev4) / 4, 1)
    e, s = week["events"], thresholds["small_sample"]

    def rate(a, b):
        mapped = lambda k: k == "visitors" or bool(mapping.get(k))  # noqa: E731
        if not (mapped(a) and mapped(b)):
            return None
        return ratio(e[a] if a != "visitors" else week["visitors"], e[b] if b != "visitors" else week["visitors"], s)

    week["rates"] = {"use": rate("core_start", "visitors"), "done": rate("core_done", "core_start"),
                     "error": rate("error", "core_start"), "takeaway": rate("takeaway", "core_done"),
                     "return": ratio(week["visits"], week["visitors"], s)}
    week["bottleneck"] = bottleneck(week, site, thresholds)
    week["suggest"] = suggest_stage(week, site, thresholds)
    return week


def bottleneck(week, site, t):
    """The first layer that looks broken, top of the funnel first. A heuristic: the reason is printed with it."""
    e, r = week["events"], week["rates"]
    if not week["mapping"].get(week["north_star"]["key"]):
        return ("数据", "北极星事件没有对应的埋点")
    if week["visitors"] < t["growth_visitors_7d"]:
        return ("需求", "7 天访客 " + str(int(week["visitors"])) + " < " + str(t["growth_visitors_7d"]))
    if r["use"] is not None and r["use"] < t["use_rate"]:
        return ("使用", "开始使用率 " + pct(r["use"]))
    if r["error"] is not None and r["error"] > t["error_rate"]:
        return ("完成", "报错率 " + pct(r["error"]))
    if r["done"] is not None and r["done"] < t["done_rate"]:
        return ("完成", "完成率 " + pct(r["done"]))
    if r["takeaway"] is not None and r["takeaway"] < t["takeaway_rate"]:
        return ("拿走", "拿走率 " + pct(r["takeaway"]))
    if site.get("sells") and e["paid"] == 0:
        return ("付费", "7 天没有付款")
    return ("—", "没有明显卡点")


def suggest_stage(week, site, t):
    stage = site.get("stage", "validate")
    ns = [w["north_star"] for w in week["weeks"]]
    visitors = [w["visitors"] for w in week["weeks"]]
    if stage == "validate":
        if (week["north_star"]["events"] and week["weeks_of_data"] >= t["validate_weeks"]
                and week["gsc"]["impressions"] < t["maintain_impressions_7d"]
                and ns[-1] < t["maintain_north_star_7d"] and visitors[-1] < t["growth_visitors_7d"]):
            return ("maintain", "上线 " + str(week["weeks_of_data"]) + " 周，曝光和北极星都低于阈值")
        if visitors[-1] >= t["growth_visitors_7d"] and ns[-1] > ns[-2] > ns[-3]:
            return ("growth", "访客达到阈值，北极星连续 3 周增长")
    if stage == "growth" and min(visitors[-3:]) >= t["monetize_visitors_7d"]:
        return ("monetize", "连续 3 周访客 ≥ " + str(t["monetize_visitors_7d"]))
    return None


def pct(value):
    return "-" if value is None else str(round(value * 100)) + "%"


def num(value):
    return str(int(value)) if value == int(value) else str(value)


def delta(now, before):
    if not before:
        return ""
    return " ({:+.0%})".format((now - before) / before)


def due_experiments(root, today):
    items = (load_json(root / "experiments.json", {}) or {}).get("items", [])
    running = [i for i in items if i.get("status") == "running"]
    return running, [i for i in running if i.get("review") and i["review"] <= today.isoformat()]


def weekly(root, portfolio, end=None, checks=None):
    end = end or (datetime.now(timezone.utc).date() - timedelta(days=1))
    con = db(root)
    plan_types = plans()
    sites = [site_week(con, s, site_spec(s), portfolio["thresholds"], end, plan_types) for s in portfolio["sites"]]
    if checks is None:
        checks = [dict(zip(("site", "source", "item", "status", "detail"), r))
                  for r in con.execute("SELECT site, source, item, status, detail FROM checks")]
    con.close()
    running, due = due_experiments(root, end + timedelta(days=1))
    return {"schema": "site-measure/weekly@1", "end": end.isoformat(), "start": (end - timedelta(days=6)).isoformat(),
            "sites": sites, "checks": [c for c in checks if c["status"] in ("fail", "warn", "nocred")],
            "experiments": {"running": running, "due": due}, "thresholds": portfolio["thresholds"]}


def render_weekly(report):
    iso = date.fromisoformat(report["end"]).isocalendar()
    out = ["# 组合周报 " + str(iso[0]) + "-W" + str(iso[1]).zfill(2),
           "", report["start"] + " 至 " + report["end"] + "（UTC）。Search Console 和 Bing 数据往前错 "
           + str(GSC_LAG_DAYS) + " 天。事件数是次数不是人数，含站长自己的访问；少于 "
           + str(report["thresholds"]["small_sample"]) + " 的比例不计算。", ""]
    out += ["## 总览", "", "访客是每天访客数相加（同一人隔天再来算两次）。", "", "| 站 | 阶段 | 北极星（7 天） | 前 4 周均值 | 访客 | 搜索曝光 | 卡在 | 建议 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    order = sorted(report["sites"], key=lambda s: -s["visitors"])
    for s in order:
        ns = s["north_star"]
        sug = s["suggest"]
        out.append("| " + " | ".join([
            s["site"], STAGES.get(s["stage"], s["stage"]),
            ns["label"] + " " + num(ns["value"]) + ("" if ns["events"] else "（无埋点）"),
            num(ns["avg_prev4"]), num(s["visitors"]),
            num(s["gsc"]["impressions"]) + delta(s["gsc"]["impressions"], s["gsc"]["impressions_prev"]),
            s["bottleneck"][0], ("→ " + STAGES[sug[0]]) if sug else ""]) + " |")
    if report["experiments"]["due"]:
        out += ["", "## 到期要复查的实验", ""]
        for item in report["experiments"]["due"]:
            out.append("- **" + item.get("id", "?") + "**（" + item.get("site", "") + "）：" + item.get("hypothesis", "")
                       + "；看 " + str(item.get("metric", "")) + "，预期 " + str(item.get("expect", "")) + "，复查日 " + item["review"])
    if report["experiments"]["running"]:
        out += ["", "进行中的实验 " + str(len(report["experiments"]["running"])) + " 个。"]
    problems = [c for c in report["checks"] if c["status"] == "fail"]
    if problems:
        out += ["", "## 数据接入问题（先修这些，数字才可信）", ""]
        grouped = {}
        for c in problems:
            grouped.setdefault(c["site"], []).append(c)
        for site, items in grouped.items():
            events = [c["item"][6:] for c in items if c["item"].startswith("event:")]
            other = [c["source"] + "." + c["item"] + (" (" + c["detail"] + ")" if c["detail"] else "") for c in items
                     if not c["item"].startswith("event:")]
            parts = other + (["缺标准事件：" + ", ".join(STD_LABEL.get(k, k) for k in events)] if events else [])
            out.append("- " + site + "：" + "；".join(parts))
    out += ["", "## 各站", ""]
    for s in order:
        e, r, ns = s["events"], s["rates"], s["north_star"]
        out += ["### " + s["site"] + "（" + STAGES.get(s["stage"], s["stage"]) + "）", ""]
        out.append("- 北极星：" + ns["label"] + " = " + num(ns["value"]) + delta(ns["value"], ns["avg_prev4"])
                   + "，近 5 周 " + " → ".join(num(w["north_star"]) for w in s["weeks"])
                   + ("；事件 " + ", ".join(ns["events"]) + ("（按类型推测，待确认）" if ns["origin"] == "guess" else "") if ns["events"] else "；没有对应事件"))
        out.append("- 流量：访客 " + num(s["visitors"]) + "，访问 " + num(s["visits"]) + "，浏览 " + num(s["pageviews"])
                   + "；近 5 周访客 " + " → ".join(num(w["visitors"]) for w in s["weeks"]))
        out.append("- 搜索：Google 曝光 " + num(s["gsc"]["impressions"]) + "、点击 " + num(s["gsc"]["clicks"])
                   + (("；Bing 曝光 " + num(s["bing_impressions"])) if s["bing_impressions"] else ""))
        out.append("- 漏斗：" + "，".join(STD_LABEL[k] + " " + num(e[k]) for k in STANDARD if s["mapping"].get(k))
                   + "；开始使用率 " + pct(r["use"]) + "、完成率 " + pct(r["done"]) + "、报错率 " + pct(r["error"])
                   + "、拿走率 " + pct(r["takeaway"]) + "、每访客访问 " + ("-" if r["return"] is None else str(r["return"])))
        if s["cf"]["requests"]:
            out.append("- Cloudflare：请求 " + num(s["cf"]["requests"]) + "，5xx " + num(s["cf"]["5xx"]))
        out.append("- 卡在：" + s["bottleneck"][0] + "（" + s["bottleneck"][1] + "）")
        if s["suggest"]:
            out.append("- 阶段建议：→ " + STAGES[s["suggest"][0]] + "（" + s["suggest"][1] + "），由站长确认后改 portfolio.json")
        out.append("")
    out += ["## 下周改动", "", "（由 site-measure 读完本报告后提出，最多 3 条，站长批准后写进 experiments.json。）", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- guard

def guard(root, portfolio, sources, today=None):
    """Alerts for yesterday (UTC): a core event went to zero, traffic fell off a cliff, 5xx spiked, or a check broke."""
    today = today or datetime.now(timezone.utc).date()
    collect(root, portfolio, sources, days=3, today=today, log=lambda _m: None)
    yesterday = today - timedelta(days=1)
    base = (yesterday - timedelta(days=7), yesterday - timedelta(days=1))
    con = db(root)
    alerts = []
    plan_types = plans()
    for site in portfolio["sites"]:
        if site.get("stage") == "maintain" and not site.get("guard_in_maintain", True):
            continue
        domain, spec = site["domain"], site_spec(site)
        mapping, _ = standard_events(site, spec, observed_events(con, domain, today=today), plan_types)
        for key in ("core_start", "core_done", "takeaway", "paid"):
            names = ["event:" + n for n in mapping.get(key) or []]
            if not names:
                continue
            avg = total(con, domain, "umami", names, *base) / 7
            if avg >= GUARD["event_min_daily"] and total(con, domain, "umami", names, yesterday, yesterday) == 0:
                alerts.append(domain + "：" + STD_LABEL[key] + "事件昨天为 0（前 7 天日均 " + str(round(avg, 1)) + "），埋点可能坏了")
        avg = total(con, domain, "umami", "pageviews", *base) / 7
        pv = total(con, domain, "umami", "pageviews", yesterday, yesterday)
        if avg >= GUARD["drop_min_daily"] and pv < avg * GUARD["drop_ratio"]:
            alerts.append(domain + "：昨天浏览 " + num(pv) + "，前 7 天日均 " + str(round(avg)) + "，流量断崖")
        req = total(con, domain, "cloudflare", "requests", yesterday, yesterday)
        errors = total(con, domain, "cloudflare", "5xx", yesterday, yesterday)
        if req >= GUARD["error_min_requests"] and errors / req > GUARD["error_5xx_share"]:
            alerts.append(domain + "：昨天 5xx 占 " + pct(errors / req) + "（" + num(errors) + "/" + num(req) + "）")
    con.close()
    for r in check(root, portfolio, sources, today=today):
        if r["status"] == "fail" and r["previous"] in ("ok", "warn"):
            alerts.append(r["site"] + "：" + r["source"] + "." + r["item"] + " 从正常变成失败" + ("（" + r["detail"] + "）" if r["detail"] else ""))
    return alerts


def notify(root, portfolio, alerts, send=True):
    if not alerts:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(root / "alerts.md", "a") as handle:
        handle.write("\n## " + stamp + "\n\n" + "".join("- " + a + "\n" for a in alerts))
    if not send:
        return
    push(portfolio, "**site-measure 守护：" + str(len(alerts)) + " 条提醒**\n\n" + "\n".join("- " + a for a in alerts),
         str(len(alerts)) + " 条提醒，详见 alerts.md：" + alerts[0], "site-measure 守护")


def push(portfolio, message, short, title):
    """Send through notify.command (reads the message on stdin, e.g. lark-cli --markdown -); else a macOS notification."""
    command = (portfolio.get("notify") or {}).get("command")
    if command:
        result = subprocess.run(command, shell=True, input=message, text=True, timeout=60, capture_output=True)
        if result.returncode == 0:
            return True
        print("notify command failed: " + (result.stderr or result.stdout)[-300:], file=sys.stderr)
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", 'display notification "' + short[:200].replace('"', "'") + '" with title "' + title + '"'],
                       timeout=30)
    return False


def weekly_summary(report, path):
    """The overview as a short message: one line per site with traffic or a north star, plus counts of open items."""
    iso = date.fromisoformat(report["end"]).isocalendar()
    lines = ["**组合周报 " + str(iso[0]) + "-W" + str(iso[1]).zfill(2) + "**（" + report["start"] + " 至 " + report["end"] + "）", ""]
    for s in sorted(report["sites"], key=lambda s: -s["visitors"]):
        if not (s["visitors"] or s["north_star"]["value"]):
            continue
        ns = s["north_star"]
        sug = s["suggest"]
        lines.append("- " + s["site"] + "：" + ns["label"] + " " + num(ns["value"]) + delta(ns["value"], ns["avg_prev4"])
                     + "，访客 " + num(s["visitors"]) + "，卡在" + s["bottleneck"][0] + ("，建议→" + STAGES[sug[0]] if sug else ""))
    broken = len({c["site"] for c in report["checks"] if c["status"] == "fail"})
    lines += ["", "数据接入有问题的站 " + str(broken) + " 个；到期实验 " + str(len(report["experiments"]["due"])) + " 个。",
              "完整报告：" + str(path) + "。要下周改动建议，在 Claude 里说 `/site-measure 周报`。"]
    return "\n".join(lines)


# ---------------------------------------------------------------- init and schedule

RESERVED_TLDS = (".example", ".test", ".invalid", ".localhost", ".local")


def discover(projects):
    """Sites from site-kit projects (.sitekit.json, also under site/) and non-kit projects with umami.config.json."""
    found = []
    for path in sorted(Path(projects).expanduser().iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        kit = next((p for p in (path / ".sitekit.json", path / "site" / ".sitekit.json") if p.is_file()), None)
        if kit:
            info = json.loads(kit.read_text()).get("site") or {}
            if info.get("domain") and not info["domain"].endswith(RESERVED_TLDS):
                found.append({"domain": info["domain"], "project": str(path), "types": [info.get("type") or "tool"],
                              "stage": "validate", "since": date.today().isoformat(), "sells": info.get("type") == "app",
                              "kit": True})
            continue
        config = load_json(path / "umami.config.json")
        if config and config.get("domain") and not config["domain"].endswith(RESERVED_TLDS):
            found.append({"domain": config["domain"], "project": str(path), "types": ["tool"], "stage": "validate",
                          "since": date.today().isoformat(), "sells": False, "kit": False})
    return found


TEMPLATE_FILES = {
    ".gitignore": "data/\nlogs/\n*.local.*\n",
    "experiments.json": json.dumps({"schema": "site-measure/experiments@1", "items": []}, indent=2) + "\n",
    "playbook.md": "# 打法库\n\n有结论的改法记在这里：有效的写明在哪些站验证过、推进 kit 没有；无效的写明为什么，避免重复试。\n\n## 有效\n\n## 无效\n",
    "alerts.md": "# 守护提醒\n",
}


def init(root, projects):
    root.mkdir(parents=True, exist_ok=True)
    (root / "weekly").mkdir(exist_ok=True)
    for name, text in TEMPLATE_FILES.items():
        if not (root / name).exists():
            (root / name).write_text(text)
    path = root / "portfolio.json"
    existing = load_json(path)
    sites = discover(projects)
    if existing:
        known = {s["domain"] for s in existing["sites"]}
        added = [s for s in sites if s["domain"] not in known]
        existing["sites"] += added
        data = existing
    else:
        added = sites
        data = {"schema": PORTFOLIO_SCHEMA, "notify": {"command": None}, "thresholds": DEFAULT_THRESHOLDS, "sites": sites}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return added


LABEL = "local.site-measure."


def plist(name, args, calendar, root):
    python = sys.executable or "/usr/local/bin/python3"
    items = "".join("<string>" + a + "</string>" for a in [python, str(HERE / "ops.py")] + args)
    cal = "".join("<key>" + k + "</key><integer>" + str(v) + "</integer>" for k, v in calendar.items())
    log = str(root / "logs" / (name + ".log"))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
            "<key>Label</key><string>" + LABEL + name + "</string>"
            "<key>ProgramArguments</key><array>" + items + "</array>"
            "<key>StartCalendarInterval</key><dict>" + cal + "</dict>"
            "<key>EnvironmentVariables</key><dict><key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>"
            "<key>GROWTH_HOME</key><string>" + str(root) + "</string></dict>"
            "<key>StandardOutPath</key><string>" + log + "</string><key>StandardErrorPath</key><string>" + log + "</string>"
            "</dict></plist>\n")


def schedule(root, install=False, uninstall=False):
    agents = Path.home() / "Library" / "LaunchAgents"
    jobs = {"guard": (["guard"], {"Hour": 9, "Minute": 0}),
            "weekly": (["weekly", "--write"], {"Weekday": 1, "Hour": 9, "Minute": 30})}
    (root / "logs").mkdir(parents=True, exist_ok=True)
    uid = str(os.getuid())
    done = []
    for name, (args, cal) in jobs.items():
        target = agents / (LABEL + name + ".plist")
        if uninstall:
            subprocess.run(["launchctl", "bootout", "gui/" + uid + "/" + LABEL + name], capture_output=True)
            if target.exists():
                target.unlink()
            done.append("removed " + str(target))
            continue
        text = plist(name, args, cal, root)
        if not install:
            done.append(str(target) + " (preview)\n" + text)
            continue
        agents.mkdir(parents=True, exist_ok=True)
        subprocess.run(["launchctl", "bootout", "gui/" + uid + "/" + LABEL + name], capture_output=True)
        target.write_text(text)
        subprocess.run(["launchctl", "bootstrap", "gui/" + uid, str(target)], check=True)
        done.append("installed " + str(target))
    return done


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", help="growth home (default GROWTH_HOME or ~/Projects/growth)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--projects", default=str(Path.home() / "Projects"))
    p = sub.add_parser("check")
    p.add_argument("--site", action="append")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p = sub.add_parser("collect")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--site", action="append")
    p = sub.add_parser("guard")
    p.add_argument("--no-notify", action="store_true")
    p = sub.add_parser("weekly")
    p.add_argument("--date", help="last day of the week (default yesterday, UTC)")
    p.add_argument("--write", action="store_true", help="save to weekly/<year>-W<nn>.md and send its summary")
    p.add_argument("--no-notify", action="store_true", help="with --write: do not send the summary")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p = sub.add_parser("schedule")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--install", action="store_true")
    group.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    root = home(args.home)
    try:
        if args.command == "init":
            added = init(root, args.projects)
            print("growth home: " + str(root))
            for s in added:
                print("  + " + s["domain"] + " (" + ",".join(s["types"]) + ") " + s["project"])
            print("Review portfolio.json: stage, types, sells, and drop sites that are not yours to run.")
            return 0
        if args.command == "schedule":
            print("\n".join(schedule(root, args.install, args.uninstall)))
            return 0
        portfolio = load_portfolio(root)
        if args.command == "weekly":
            end = date.fromisoformat(args.date) if args.date else None
            report = weekly(root, portfolio, end)
            text = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render_weekly(report)
            if args.write:
                iso = date.fromisoformat(report["end"]).isocalendar()
                target = root / "weekly" / (str(iso[0]) + "-W" + str(iso[1]).zfill(2) + ".md")
                target.parent.mkdir(exist_ok=True)
                target.write_text(render_weekly(report) + "\n")
                print("wrote " + str(target))
                if not args.no_notify:
                    push(portfolio, weekly_summary(report, target), "周报已生成：" + target.name, "site-measure 周报")
            else:
                print(text)
            return 0
        sources = Sources(root)
        if args.command == "collect":
            collect(root, portfolio, sources, max(0, args.days), set(args.site or []) or None,
                    log=lambda m: print(m, file=sys.stderr))
            print("collected " + str(args.days) + " days into " + str(root / "data" / "snapshots.sqlite"))
            return 0
        if args.command == "check":
            results = check(root, portfolio, sources, set(args.site or []) or None)
            print(json.dumps(results, ensure_ascii=False, indent=2) if args.format == "json" else render_check(results))
            return 1 if any(r["status"] == "fail" for r in results) else 0
        if args.command == "guard":
            alerts = guard(root, portfolio, sources)
            notify(root, portfolio, alerts, send=not args.no_notify)
            print("\n".join(alerts) if alerts else "no alerts")
            return 0
    except Exception as error:  # noqa: BLE001 - one clear line
        print("Error: " + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
