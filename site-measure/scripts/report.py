#!/usr/bin/env python3
"""Read-only Umami traffic report for one website (replaces per-project GA4 report scripts).

    python3 report.py --domain example.com [--days 7 | --start 2026-10-01 --end 2026-10-07]
                      [--timezone America/Los_Angeles] [--limit 10] [--daily] [--format text|json]

Authenticates exactly like the Umami tool (`UMAMI_API_KEY`, else credentials.local.txt in the tool
root, default ~/Projects/umami, override with UMAMI_TOOL_ROOT). It looks websites up by domain and
never creates or changes anything. --start/--end are calendar days in --timezone (default UTC; use the
GA property's time zone when comparing with GA) and --end is inclusive.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import urllib.parse
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = "site-analytics/report@1"
TOOL_ROOT = Path(os.environ.get("UMAMI_TOOL_ROOT", Path.home() / "Projects" / "umami")).expanduser()
DIMENSIONS = [("pages", "path"), ("referrers", "referrer"), ("channels", "channel"), ("events", "event"),
              ("countries", "country")]
DAY_MS = 86_400_000


def load_tool():
    path = TOOL_ROOT / "scripts" / "add-website.py"
    if not path.is_file():
        raise ValueError("Umami tool not found at " + str(path) + "; set UMAMI_TOOL_ROOT")
    spec = importlib.util.spec_from_file_location("umami_registration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def number(value):
    """Umami 3 returns plain numbers; Umami 2 returned {value, prev}."""
    if isinstance(value, dict):
        value = value.get("value", 0)
    return value if isinstance(value, (int, float)) else 0


def totals(raw):
    pageviews, visitors, visits = number(raw.get("pageviews")), number(raw.get("visitors")), number(raw.get("visits"))
    bounces, seconds = number(raw.get("bounces")), number(raw.get("totaltime"))
    return {
        "pageviews": pageviews, "visitors": visitors, "visits": visits, "bounces": bounces,
        "bounce_rate": round(bounces / visits, 3) if visits else None,
        "avg_visit_seconds": round(seconds / visits) if visits else None,
        "views_per_visit": round(pageviews / visits, 2) if visits else None,
    }


def previous(raw):
    if isinstance(raw.get("comparison"), dict):
        return totals(raw["comparison"])
    if isinstance(raw.get("pageviews"), dict):  # Umami 2 shape
        return totals({key: {"value": value.get("prev", 0)} for key, value in raw.items() if isinstance(value, dict)})
    return None


def rows(raw):
    items = raw.get("data", []) if isinstance(raw, dict) else raw
    result = []
    for item in items or []:
        name = item.get("x", item.get("name"))
        count = item.get("y", item.get("value"))
        result.append({"value": "(none)" if name in (None, "") else str(name), "count": number(count)})
    return result


def build_report(client, website, start_ms, end_ms, limit=10, daily=False, tz_name="UTC"):
    """client.request(path) returns parsed JSON; website has id, name and domain."""
    zone = ZoneInfo(tz_name)
    base = "/api/websites/" + website["id"]
    span = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms})
    stats = client.request(base + "/stats?" + span)
    report = {
        "schema": SCHEMA,
        "website": {"id": website["id"], "name": website.get("name"), "domain": website.get("domain")},
        "range": {"start": iso(start_ms, zone), "end": iso(end_ms, zone), "days": round((end_ms - start_ms) / DAY_MS, 2),
                  "timezone": tz_name},
        "totals": totals(stats),
        "previous_period": previous(stats),
        "top": {},
    }
    for key, kind in DIMENSIONS:
        query = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms, "type": kind, "limit": limit})
        report["top"][key] = rows(client.request(base + "/metrics?" + query))[:limit]
    if daily:
        query = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms, "unit": "day", "timezone": tz_name})
        series = client.request(base + "/pageviews?" + query)
        visits = {row["x"]: number(row["y"]) for row in series.get("sessions", [])}
        report["daily"] = [{"date": row["x"][:10], "pageviews": number(row["y"]), "visits": visits.get(row["x"], 0)}
                           for row in series.get("pageviews", [])]
    return report


def iso(ms, zone=timezone.utc):
    return datetime.fromtimestamp(ms / 1000, zone).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def zone_for(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Unknown --timezone " + repr(name) + "; use an IANA name such as America/Los_Angeles")


def date_range(days=None, start=None, end=None, now=None, zone=timezone.utc):
    now = now or datetime.now(timezone.utc)
    if start or end:
        if not (start and end):
            raise ValueError("Pass both --start and --end (YYYY-MM-DD)")
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if last < first:
            raise ValueError("--end is before --start")
        # Midnight to midnight in the zone, so a day with a DST change lasts 23 or 25 hours.
        begin = datetime(first.year, first.month, first.day, tzinfo=zone)
        finish = datetime(last.year, last.month, last.day, tzinfo=zone) + timedelta(days=1)
        return int(begin.timestamp() * 1000), int(finish.timestamp() * 1000) - 1
    days = 7 if days is None else days
    if days <= 0:
        raise ValueError("--days must be positive")
    end_ms = int(now.timestamp() * 1000)
    return end_ms - days * DAY_MS, end_ms


def find_website(api, tool, domain=None, website_id=None):
    if website_id:
        website = api.request("/api/websites/" + str(uuid.UUID(website_id)))
        return {"id": website["id"], "name": website.get("name"), "domain": website.get("domain")}
    website = api.find(tool.normalize_domain(domain))  # lookup only; never ensure/create
    if not website:
        raise ValueError("No Umami website for " + domain + "; connect the site first (umami-connect)")
    return {"id": website["id"], "name": website.get("name"), "domain": website.get("domain")}


def fmt(value, suffix=""):
    return "-" if value is None else str(value) + suffix


def change(now, before):
    if before in (None, 0) or now is None:
        return ""
    return " ({:+.0%})".format((now - before) / before)


def render(report):
    t, p = report["totals"], report["previous_period"] or {}
    lines = [
        "Umami report: " + (report["website"]["name"] or "") + " (" + (report["website"]["domain"] or report["website"]["id"]) + ")",
        "range: " + report["range"]["start"] + " to " + report["range"]["end"] + " (" + report["range"]["timezone"]
        + ", " + str(report["range"]["days"]) + " days)",
        "pageviews " + str(t["pageviews"]) + change(t["pageviews"], p.get("pageviews"))
        + " | visitors " + str(t["visitors"]) + change(t["visitors"], p.get("visitors"))
        + " | visits " + str(t["visits"]) + change(t["visits"], p.get("visits")),
        "bounce rate " + fmt(None if t["bounce_rate"] is None else round(t["bounce_rate"] * 100), "%")
        + " | avg visit " + fmt(t["avg_visit_seconds"], "s") + " | views/visit " + fmt(t["views_per_visit"]),
    ]
    if p:
        lines.append("previous period: pageviews " + str(p["pageviews"]) + ", visitors " + str(p["visitors"])
                     + ", visits " + str(p["visits"]))
    titles = {"pages": "Top pages", "referrers": "Referrers", "channels": "Channels", "events": "Events",
              "countries": "Countries"}
    for key, title in titles.items():
        items = report["top"].get(key) or []
        lines.append("")
        lines.append(title + ":" + ("" if items else " none"))
        for item in items:
            lines.append("  " + str(item["count"]).rjust(7) + "  " + item["value"])
    if report.get("daily"):
        lines.append("")
        lines.append("Daily (" + report["range"]["timezone"] + "): date  pageviews  visits")
        for row in report["daily"]:
            lines.append("  " + row["date"] + "  " + str(row["pageviews"]).rjust(9) + "  " + str(row["visits"]).rjust(6))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--domain", help="Website domain registered in Umami")
    target.add_argument("--website-id", help="Umami website ID")
    parser.add_argument("--days", type=int, help="Last N days ending now (default 7)")
    parser.add_argument("--start", help="First day, YYYY-MM-DD (in --timezone)")
    parser.add_argument("--end", help="Last day, YYYY-MM-DD (in --timezone, inclusive)")
    parser.add_argument("--timezone", default="UTC", help="IANA time zone for day boundaries and --daily (default UTC)")
    parser.add_argument("--limit", type=int, default=10, help="Rows per dimension (default 10)")
    parser.add_argument("--daily", action="store_true", help="Add daily pageviews and visits")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if args.days is not None and (args.start or args.end):
        parser.error("use --days or --start/--end, not both")
    try:
        start_ms, end_ms = date_range(args.days, args.start, args.end, zone=zone_for(args.timezone))
        tool = load_tool()
        api = tool.Umami()
        website = find_website(api, tool, args.domain, args.website_id)
        report = build_report(api, website, start_ms, end_ms, max(1, args.limit), args.daily, args.timezone)
    except Exception as error:  # ApiError, ValueError, KeyError, OSError: one clear line, no stack trace
        print("Error: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
