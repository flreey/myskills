#!/usr/bin/env python3
"""Read-only Umami funnel and event-field report for one website, with the owner's sessions left out.

    python3 funnel.py --domain example.com [--days 14 | --start D --end D] [--timezone Zone]
        [--steps 'path:/,tool_file,tool_start|tool_full,tool_done,tool_download'] [--plan tool [--plan app]]
        [--fields] [--field tool_done.seconds ...]
        [--exclude-session ID] [--exclude-screen 1440x900] [--exclude-city Lisbon]
        [--exclude-country US] [--exclude-device laptop] [--list-sessions 10] [--format text|json]

- Funnel: every session in the range walks the steps in order (a session counts at step k once it
  reached steps 1..k in that order). A step is an event name, `path:/app` (a page view of that path;
  `path:/guides/*` for a prefix, `path:*` for any page), or alternatives joined with `|`. `--plan` takes
  the standard funnel of a site type from references/tracking-plans.json, matching event names by the
  plan's aliases; its `path:<...>` placeholders become "any page view". Umami sessions can hold several
  visits on different days, so this is a per-visitor funnel, not a per-visit one.
- Fields: `--fields` lists every event field with its value counts (text) or its spread (numbers:
  min, p25, median, p75, p90, max, mean); `--field event.key` limits it to those fields. Values are
  read per event (`/event-data/:eventId`), so exclusions apply. Above --max-event-data events it
  falls back to the server totals (`/event-data/values`), which include every session, and says so.
- Exclusions: sessions matching any rule are dropped from every number (ids accept an 8+ character
  prefix). `--list-sessions N` prints the busiest sessions (short id, screen, city, device, counts) so
  the owner's own testing can be spotted; nothing here writes to Umami or stores session data.

Authenticates like report.py (UMAMI_API_KEY or credentials.local.txt in the Umami tool root); credentials
never appear in the output.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import re
import statistics
import sys
import urllib.parse

HERE = Path(__file__).resolve().parent
SCHEMA = "site-measure/funnel@1"
PAGE_SIZE = 500
PLANS_PATH = HERE.parent / "references" / "tracking-plans.json"

_spec = importlib.util.spec_from_file_location("site_measure_report", HERE / "report.py")
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


def paged(client, path, start_ms, end_ms, extra=None):
    """All rows of a paged Umami list endpoint, and whether the server said it capped them."""
    rows, page, capped = [], 1, False
    while True:
        query = {"startAt": start_ms, "endAt": end_ms, "page": page, "pageSize": PAGE_SIZE}
        query.update(extra or {})
        result = client.request(path + "?" + urllib.parse.urlencode(query))
        data = result.get("data", []) if isinstance(result, dict) else result
        rows += data or []
        capped = capped or bool(isinstance(result, dict) and result.get("isCapped"))
        count = result.get("count", 0) if isinstance(result, dict) else 0
        if not data or page * PAGE_SIZE >= count:
            return rows, capped
        page += 1


def excluded_sessions(sessions, rules):
    """{session_id: [rule, ...]} for sessions that match an exclusion rule."""
    out = {}
    ids = [i.lower() for i in rules.get("session", [])]
    for i in ids:
        if len(i) < 8:
            raise ValueError("--exclude-session needs at least 8 characters of the id")
    checks = [
        ("screen", "screen", lambda v, want: v == want),
        ("city", "city", lambda v, want: v.lower() == want.lower()),
        ("country", "country", lambda v, want: v.upper() == want.upper()),
        ("device", "device", lambda v, want: v.lower() == want.lower()),
    ]
    for s in sessions:
        sid = str(s.get("id", ""))
        hits = ["session " + i[:8] for i in ids if sid.lower().startswith(i)]
        for rule, key, match in checks:
            for want in rules.get(rule, []):
                if match(str(s.get(key) or ""), want):
                    hits.append(rule + " " + want)
        if hits:
            out[sid] = hits
    return out


def parse_steps(spec):
    steps = []
    for raw in [s.strip() for s in spec.split(",") if s.strip()]:
        steps.append({"label": raw, "match": [alt.strip() for alt in raw.split("|") if alt.strip()]})
    if len(steps) < 2:
        raise ValueError("--steps needs at least two steps, separated by commas")
    return steps


def plan_steps(types, names, plans=None):
    """The plan's funnel for each type, with roles matched to event names seen in the data."""
    plans = plans or json.loads(PLANS_PATH.read_text())
    funnels = []
    for t in types:
        if t not in plans["types"]:
            raise ValueError("Unknown --plan " + t + "; use " + ", ".join(plans["types"]))
        roles = {r["role"]: r for r in plans["types"][t]["roles"]}
        steps = []
        for step in plans["types"][t]["funnel"]:
            if step.startswith("path:"):
                concrete = step if "<" not in step else "path:*"
                steps.append({"label": step if concrete == step else "any page view", "match": [concrete]})
                continue
            pattern = re.compile("^(?:" + roles[step]["aliases"] + ")$")
            matched = sorted(n for n in names if pattern.match(n))
            steps.append({"label": step + " (" + ("|".join(matched) or "no events seen") + ")", "match": matched or ["\0none"]})
        funnels.append({"name": t, "steps": steps})
    return funnels


def matches(event, alternatives):
    for alt in alternatives:
        if alt.startswith("path:"):
            if event.get("eventType") != 1:
                continue
            path, want = event.get("urlPath") or "", alt[5:]
            if want == "*" or path == want or (want.endswith("*") and path.startswith(want[:-1])):
                return True
        elif event.get("eventType") == 2 and event.get("eventName") == alt:
            return True
    return False


def ts(event):
    return datetime.fromisoformat(event["createdAt"].replace("Z", "+00:00")).timestamp()


def funnel(events, steps):
    by_session = {}
    for e in events:
        by_session.setdefault(e.get("sessionId"), []).append(e)
    reached = [0] * len(steps)
    anywhere = [0] * len(steps)
    took = [[] for _ in steps]
    for evs in by_session.values():
        evs.sort(key=ts)
        k, first = 0, None
        for e in evs:
            if k < len(steps) and matches(e, steps[k]["match"]):
                first = ts(e) if k == 0 else first
                reached[k] += 1
                if k:
                    took[k].append(ts(e) - first)
                k += 1
        for i, step in enumerate(steps):
            if any(matches(e, step["match"]) for e in evs):
                anywhere[i] += 1
    rows = []
    for i, step in enumerate(steps):
        rows.append({
            "step": step["label"], "sessions": reached[i], "any_order": anywhere[i],
            "from_previous": round(reached[i] / reached[i - 1], 3) if i and reached[i - 1] else None,
            "from_first": round(reached[i] / reached[0], 3) if i and reached[0] else None,
            "median_seconds_from_first": round(statistics.median(took[i])) if took[i] else None,
        })
    return rows


def spread(values):
    values = sorted(values)
    if not values:
        return None

    def q(p):
        if len(values) == 1:
            return values[0]
        pos = (len(values) - 1) * p
        lo = int(pos)
        hi = min(lo + 1, len(values) - 1)
        return round(values[lo] + (values[hi] - values[lo]) * (pos - lo), 2)

    return {"n": len(values), "min": values[0], "p25": q(0.25), "median": q(0.5), "p75": q(0.75), "p90": q(0.9),
            "max": values[-1], "mean": round(sum(values) / len(values), 2)}


def summarize(field_rows):
    """field_rows: {(event, key): [value, ...]} -> sorted list of field summaries."""
    out = []
    for (event, key), values in sorted(field_rows.items()):
        numbers = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        item = {"event": event, "field": key, "count": len(values)}
        if numbers and len(numbers) == len(values):
            item["numbers"] = spread(numbers)
        else:
            counts = {}
            for v in values:
                label = "(empty)" if v in (None, "") else str(v)
                counts[label] = counts.get(label, 0) + 1
            item["values"] = [{"value": k, "count": c} for k, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        out.append(item)
    return out


def event_values(rows):
    """Rows of /event-data/:eventId -> [(key, value)]."""
    out = []
    for row in rows or []:
        key = row.get("dataKey") or row.get("propertyName")
        if row.get("dataType") == 2 or (row.get("numberValue") is not None and row.get("stringValue") is None):
            value = row.get("numberValue")
            value = float(value) if isinstance(value, str) else value
            value = int(value) if isinstance(value, float) and value.is_integer() else value
        else:
            value = row.get("stringValue")
        if key is not None:
            out.append((key, value))
    return out


def fields_report(client, base, events, start_ms, end_ms, wanted=None, max_fetch=1500):
    """Per-field summaries for the kept events, or the server totals when there are too many events."""
    keep = [e for e in events if e.get("eventType") == 2 and e.get("hasData")]
    if wanted:
        names = {w.split(".", 1)[0] for w in wanted}
        keep = [e for e in keep if e.get("eventName") in names]
    want_keys = {tuple(w.split(".", 1)) for w in wanted or [] if "." in w}

    def ok(event, key):
        return not want_keys or (event, key) in want_keys or not any(w[0] == event for w in want_keys)

    rows = {}
    if len(keep) <= max_fetch:
        def fetch(e):
            return e, client.request(base + "/event-data/" + str(e["id"]))
        with ThreadPoolExecutor(max_workers=6) as pool:
            for e, data in pool.map(fetch, keep):
                for key, value in event_values(data):
                    if ok(e["eventName"], key):
                        rows.setdefault((e["eventName"], key), []).append(value)
        return {"source": "per event (exclusions applied)", "events_read": len(keep), "fields": summarize(rows)}
    span = {"startAt": start_ms, "endAt": end_ms}
    props = client.request(base + "/event-data/properties?" + urllib.parse.urlencode(span))
    for p in props:
        event, key = p.get("eventName"), p.get("propertyName")
        if (wanted and event not in {w.split(".", 1)[0] for w in wanted}) or not ok(event, key):
            continue
        query = dict(span, event=event, propertyName=key)
        values = client.request(base + "/event-data/values?" + urllib.parse.urlencode(query))
        for v in values:
            value = v.get("value")
            if p.get("dataType") == 2:
                try:
                    value = float(value)
                    value = int(value) if value.is_integer() else value
                except (TypeError, ValueError):
                    pass
            rows.setdefault((event, key), []).extend([value] * int(v.get("total", 0)))
    return {"source": "server totals: every session, exclusions NOT applied (" + str(len(keep)) + " events > --max-event-data)",
            "events_read": 0, "fields": summarize(rows)}


def session_rows(sessions, excluded, limit):
    busy = sorted(sessions, key=lambda s: (-int(s.get("events") or 0), -int(s.get("views") or 0)))[:limit]
    return [{"id": str(s.get("id", ""))[:8], "screen": s.get("screen"), "city": s.get("city"), "country": s.get("country"),
             "device": s.get("device"), "browser": s.get("browser"), "os": s.get("os"), "visits": s.get("visits"),
             "views": int(s.get("views") or 0), "events": int(s.get("events") or 0),
             "first": (s.get("firstAt") or "")[:16], "last": (s.get("lastAt") or "")[:16],
             "excluded": bool(excluded.get(str(s.get("id"))))} for s in busy]


def build(client, website, start_ms, end_ms, tz_name="UTC", steps=None, plans=None, rules=None, fields=False,
          wanted=None, list_sessions=0, max_fetch=1500):
    zone = report.zone_for(tz_name)
    base = "/api/websites/" + website["id"]
    sessions, s_capped = paged(client, base + "/sessions", start_ms, end_ms)
    events, e_capped = paged(client, base + "/events", start_ms, end_ms)
    excluded = excluded_sessions(sessions, rules or {})
    kept = [e for e in events if e.get("sessionId") not in excluded]
    by_rule = {}
    for hits in excluded.values():
        for h in hits:
            by_rule[h] = by_rule.get(h, 0) + 1
    counts = {}
    for e in events:
        if e.get("eventType") == 2:
            row = counts.setdefault(e.get("eventName"), {"event": e.get("eventName"), "all": 0, "kept": 0, "kept_sessions": set()})
            row["all"] += 1
            if e.get("sessionId") not in excluded:
                row["kept"] += 1
                row["kept_sessions"].add(e.get("sessionId"))
    out = {
        "schema": SCHEMA,
        "website": {"name": website.get("name"), "domain": website.get("domain")},
        "range": {"start": report.iso(start_ms, zone), "end": report.iso(end_ms, zone), "timezone": tz_name},
        "warnings": [w for w, on in (("Umami capped the session list", s_capped), ("Umami capped the event list", e_capped)) if on],
        "sessions": {"all": len(sessions), "excluded": len(excluded), "kept": len(sessions) - len(excluded), "by_rule": by_rule},
        "events": {"all": len(events), "kept": len(kept),
                   "pageviews_kept": sum(1 for e in kept if e.get("eventType") == 1),
                   "custom": sorted(({"event": r["event"], "all": r["all"], "kept": r["kept"], "kept_sessions": len(r["kept_sessions"])}
                                     for r in counts.values()), key=lambda r: (-r["kept"], r["event"] or ""))},
        "funnels": [],
    }
    if steps:
        out["funnels"].append({"name": "steps", "rows": funnel(kept, steps)})
    if plans:
        names = {e.get("eventName") for e in events if e.get("eventType") == 2}
        for f in plan_steps(plans, names):
            out["funnels"].append({"name": "plan " + f["name"], "rows": funnel(kept, f["steps"])})
    if fields or wanted:
        out["fields"] = fields_report(client, base, kept, start_ms, end_ms, wanted, max_fetch)
    if list_sessions:
        out["busiest_sessions"] = session_rows(sessions, excluded, list_sessions)
    return out


def pct(value):
    return "-" if value is None else "{:.0%}".format(value)


def render(r):
    s, e = r["sessions"], r["events"]
    lines = ["Umami funnel: " + (r["website"]["name"] or "") + " (" + (r["website"]["domain"] or "") + ")",
             "range: " + r["range"]["start"] + " to " + r["range"]["end"] + " (" + r["range"]["timezone"] + ")",
             "sessions " + str(s["kept"]) + " kept of " + str(s["all"]) + " (" + str(s["excluded"]) + " excluded"
             + ("; " + ", ".join(k + ": " + str(v) for k, v in sorted(s["by_rule"].items())) if s["by_rule"] else "") + ")",
             "events " + str(e["kept"]) + " kept of " + str(e["all"]) + " (page views kept: " + str(e["pageviews_kept"]) + ")"]
    lines += ["warning: " + w for w in r["warnings"]]
    lines += ["", "Custom events: kept (all) sessions"]
    for row in e["custom"]:
        lines.append("  " + str(row["kept"]).rjust(6) + " (" + str(row["all"]).rjust(4) + ")  " + str(row["kept_sessions"]).rjust(4)
                     + "  " + str(row["event"]))
    for f in r["funnels"]:
        lines += ["", "Funnel " + f["name"] + ": sessions | from previous | from first | median time from step 1 | any order"]
        for i, row in enumerate(f["rows"], 1):
            took = row["median_seconds_from_first"]
            lines.append("  " + str(i) + ". " + row["step"].ljust(42) + str(row["sessions"]).rjust(5) + "  "
                         + pct(row["from_previous"]).rjust(5) + "  " + pct(row["from_first"]).rjust(5) + "  "
                         + ("-" if took is None else str(took) + "s").rjust(7) + "  " + str(row["any_order"]).rjust(5))
    if "fields" in r:
        lines += ["", "Event fields (" + r["fields"]["source"] + "):"]
        if not r["fields"]["fields"]:
            lines.append("  none")
        for item in r["fields"]["fields"]:
            head = "  " + item["event"] + "." + item["field"] + " (" + str(item["count"]) + "): "
            if "numbers" in item:
                n = item["numbers"]
                lines.append(head + "min " + str(n["min"]) + ", p25 " + str(n["p25"]) + ", median " + str(n["median"])
                             + ", p75 " + str(n["p75"]) + ", p90 " + str(n["p90"]) + ", max " + str(n["max"]) + ", mean " + str(n["mean"]))
            else:
                lines.append(head + ", ".join(v["value"] + " " + str(v["count"]) for v in item["values"][:12])
                             + (" ..." if len(item["values"]) > 12 else ""))
    if r.get("busiest_sessions"):
        lines += ["", "Busiest sessions (short id, screen, city, device/browser/os, visits/views/events, first-last):"]
        for b in r["busiest_sessions"]:
            lines.append("  " + ("x " if b["excluded"] else "  ") + b["id"] + "  " + str(b["screen"]).ljust(10) + " "
                         + (str(b["city"]) + ", " + str(b["country"])).ljust(22) + " " + "/".join(str(x) for x in (b["device"], b["browser"], b["os"]))
                         + "  " + "/".join(str(x) for x in (b["visits"], b["views"], b["events"])) + "  " + b["first"] + " - " + b["last"])
        lines.append("  (x = excluded)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--domain", help="Website domain registered in Umami")
    target.add_argument("--website-id", help="Umami website ID")
    parser.add_argument("--days", type=int, help="Last N days ending now (default 7)")
    parser.add_argument("--start", help="First day, YYYY-MM-DD (in --timezone)")
    parser.add_argument("--end", help="Last day, YYYY-MM-DD (in --timezone, inclusive)")
    parser.add_argument("--timezone", default="UTC", help="IANA time zone for day boundaries (default UTC)")
    parser.add_argument("--steps", help="Comma-separated funnel steps: event names, path:/x, alternatives a|b")
    parser.add_argument("--plan", action="append", help="Standard funnel of a site type (tool, landing, directory, app, content)")
    parser.add_argument("--fields", action="store_true", help="Distribution of every event field")
    parser.add_argument("--field", action="append", help="Only this field (event.key) or event; repeatable")
    parser.add_argument("--max-event-data", type=int, default=1500, help="Events read one by one before falling back to server totals")
    for rule, example in (("session", "1a2b3c4d"), ("screen", "1440x900"), ("city", "Lisbon"), ("country", "US"), ("device", "laptop")):
        parser.add_argument("--exclude-" + rule, action="append", default=[], help="Drop sessions with this " + rule + " (e.g. " + example + "); repeatable")
    parser.add_argument("--list-sessions", type=int, default=0, help="Show the N busiest sessions to spot the owner's testing")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if args.days is not None and (args.start or args.end):
        parser.error("use --days or --start/--end, not both")
    try:
        start_ms, end_ms = report.date_range(args.days, args.start, args.end, zone=report.zone_for(args.timezone))
        steps = parse_steps(args.steps) if args.steps else None
        rules = {k: getattr(args, "exclude_" + k) for k in ("session", "screen", "city", "country", "device")}
        tool = report.load_tool()
        api = tool.Umami()
        website = report.find_website(api, tool, args.domain, args.website_id)
        result = build(api, website, start_ms, end_ms, args.timezone, steps, args.plan, rules, args.fields, args.field,
                       max(0, args.list_sessions), max(0, args.max_event_data))
    except Exception as error:  # ApiError, ValueError, KeyError, OSError: one clear line, no stack trace
        print("Error: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
