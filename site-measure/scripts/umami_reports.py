#!/usr/bin/env python3
"""Keep a site's saved Umami funnels and goals in one reviewed spec file, committed in the project.

    python3 umami_reports.py draft  --project <dir> [--type tool --type app] [--domain host] [--window 1440]
    python3 umami_reports.py sync   --spec umami-reports.json [--apply] [--seen-days 30] [--format text|json]
    python3 umami_reports.py status (--spec umami-reports.json | --domain host) [--days 14] [--format text|json]

- draft (read-only, no network): builds a spec from the plan of the site's type
  (references/tracking-plans.json: funnel, more_funnels, goals) and the events the code sends (audit.py).
  A role the code fills with one event becomes that event. A role with several events, no event, or a
  `path:<placeholder>` goes into `todo`; read the code, pick one event per step (or split it into
  consecutive steps when the flow forces both), fill the paths, then empty `todo`.
- sync: matches the spec's funnels and goals to the website's saved ones by name. It prints what it would
  create, update or leave unchanged, and the saved reports the spec does not list (never deleted). It
  writes only with --apply. It refuses a spec whose `todo` is not empty or whose steps Umami cannot store,
  and warns about events and paths not seen in the last --seen-days days (typos, or events not shipped yet).
- status: each saved funnel's steps with visitors, and each goal's count, over --days. These numbers come
  from Umami and include every session, the owner's too; funnel.py gives the same funnel without them,
  and status prints the matching funnel.py command (event-data filters are left out there).

Spec (`site-measure/umami-reports@1`):

    {"schema": "site-measure/umami-reports@1", "domain": "example.com", "todo": [],
     "funnels": [{"name": "Tool: upload to download", "description": "...", "window": 1440,
                  "steps": ["path:/", "tool_file", "tool_done", "job_end[status=done]", "tool_download"]}],
     "goals": [{"name": "Goal: download", "step": "tool_download"}]}

A step is an event name or `path:/x`; a leading or trailing `*` matches a prefix or suffix (`path:/guides/*`).
Event steps in funnels may filter on event fields: `event[key=value]`, `event[key!=value]`, several joined
with `;`. `window` is the most minutes allowed between two consecutive steps. Funnels take 2 to 8 steps;
goals take one step and no filters.

Authenticates like report.py (UMAMI_API_KEY or credentials.local.txt in the Umami tool root); credentials
never appear in the output.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
SCHEMA = "site-measure/umami-reports@1"
PLANS_PATH = HERE.parent / "references" / "tracking-plans.json"
DEFAULT_WINDOW = 1440
EVENT_NAME = re.compile(r"^\*?[A-Za-z0-9_.:-]+\*?$")
FILTER = re.compile(r"^([A-Za-z0-9_.-]+)(!=|=)(.*)$")
STEP = re.compile(r"^([^\[\]]+)(?:\[(.*)\])?$")


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = _load("site_measure_report", "report.py")


# ---------- steps ----------

def parse_step(raw, allow_filters=True):
    """`path:/x`, `event` or `event[key=value;key!=value]` -> Umami step parameters."""
    text = str(raw).strip()
    if "|" in text:
        raise ValueError("step '" + text + "': Umami steps take one value; pick one event or split it into two steps")
    if "<" in text or ">" in text:
        raise ValueError("step '" + text + "' is still a placeholder")
    if text.startswith("path:"):
        value = text[5:].strip()
        if not value.lstrip("*").startswith("/") or "*" in value.strip("*") or "[" in value:
            raise ValueError("step '" + text + "': a path starts with / and may only start or end with *")
        return {"type": "path", "value": value}
    match = STEP.match(text)
    if not match or not EVENT_NAME.match(match.group(1).strip()):
        raise ValueError("step '" + text + "' is not an event name, path:/x or event[key=value]")
    step = {"type": "event", "value": match.group(1).strip()}
    if match.group(2) is not None:
        if not allow_filters:
            raise ValueError("step '" + text + "': goals take no field filters")
        filters = []
        for part in [p.strip() for p in match.group(2).split(";") if p.strip()]:
            f = FILTER.match(part)
            if not f:
                raise ValueError("step '" + text + "': filter '" + part + "' is not key=value or key!=value")
            filters.append({"property": f.group(1), "operator": "neq" if f.group(2) == "!=" else "eq",
                            "value": f.group(3).strip()})
        if not filters:
            raise ValueError("step '" + text + "' has empty brackets")
        step["filters"] = filters
    return step


def step_text(step):
    if step.get("type") == "path":
        return "path:" + step.get("value", "")
    ops = {"eq": "=", "neq": "!="}
    filters = ";".join(f.get("property", "") + ops.get(f.get("operator"), " " + str(f.get("operator")) + " ") + str(f.get("value", ""))
                       for f in step.get("filters") or [])
    return step.get("value", "") + ("[" + filters + "]" if filters else "")


def funnel_command(domain, steps):
    """The funnel.py command for the same steps; funnel.py has no field filters, so they are dropped."""
    plain = [step_text({k: v for k, v in s.items() if k != "filters"}) for s in steps]
    return "python3 funnel.py --domain " + domain + " --days 14 --steps '" + ",".join(plain) + "'"


# ---------- spec ----------

def load_spec(path):
    path = Path(path).expanduser()
    spec = json.loads(path.read_text())
    if spec.get("schema") != SCHEMA:
        raise ValueError(str(path) + ": schema must be " + SCHEMA)
    if not spec.get("domain"):
        raise ValueError(str(path) + ": domain is missing")
    return spec


def desired(spec):
    """Validate the spec; return {'funnel': {name: definition}, 'goal': {name: definition}}."""
    if spec.get("todo"):
        raise ValueError("todo is not empty; resolve it first:\n  - " + "\n  - ".join(map(str, spec["todo"])))
    out = {"funnel": {}, "goal": {}}
    for item in spec.get("funnels") or []:
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 200:
            raise ValueError("every funnel needs a name of 1 to 200 characters")
        if name in out["funnel"]:
            raise ValueError("funnel name used twice: " + name)
        steps = [parse_step(s) for s in item.get("steps") or []]
        if not 2 <= len(steps) <= 8:
            raise ValueError("funnel '" + name + "' needs 2 to 8 steps (has " + str(len(steps)) + ")")
        window = item.get("window", DEFAULT_WINDOW)
        if not isinstance(window, (int, float)) or isinstance(window, bool) or window <= 0:
            raise ValueError("funnel '" + name + "': window is minutes between steps, a positive number")
        out["funnel"][name] = {"name": name, "description": _description(item, name),
                               "parameters": {"window": window, "steps": steps}}
    for item in spec.get("goals") or []:
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 200:
            raise ValueError("every goal needs a name of 1 to 200 characters")
        if name in out["goal"]:
            raise ValueError("goal name used twice: " + name)
        step = parse_step(item.get("step") or "", allow_filters=False)
        out["goal"][name] = {"name": name, "description": _description(item, name), "parameters": step}
    if not out["funnel"] and not out["goal"]:
        raise ValueError("the spec lists no funnels and no goals")
    return out


def _description(item, name):
    text = str(item.get("description") or "")
    if len(text) > 500:
        raise ValueError("'" + name + "': description is longer than 500 characters")
    return text


def normalize(kind, parameters):
    """Compare saved and wanted parameters without key order, missing empty filters or 1440 vs 1440.0."""
    p = parameters or {}
    if kind == "goal":
        return {"type": p.get("type"), "value": p.get("value")}
    steps = []
    for s in p.get("steps") or []:
        step = {"type": s.get("type"), "value": s.get("value")}
        if s.get("filters"):
            step["filters"] = [{"property": f.get("property"), "operator": f.get("operator"), "value": f.get("value")}
                               for f in s["filters"]]
        steps.append(step)
    window = p.get("window")
    try:
        window = float(window)
    except (TypeError, ValueError):
        pass
    return {"window": window, "steps": steps}


# ---------- draft ----------

def draft(project, types=None, domain=None, window=DEFAULT_WINDOW, plans=None):
    plans = plans or json.loads(PLANS_PATH.read_text())
    audit = _load("site_measure_audit", "audit.py")
    found = audit.audit(project, types, plans=plans)
    by_role = {(r["type"], r["role"]): r["events"] for r in found["roles"]}
    kit_domain = None
    kit_file = Path(found["project"]) / ".sitekit.json"
    if kit_file.is_file():
        kit_domain = (json.loads(kit_file.read_text()).get("site") or {}).get("domain")
    todo, funnels, goals = [], [], []

    def resolve(t, step, where):
        if step.startswith("path:"):
            if "<" in step:
                todo.append(where + ": replace " + step + " with the real path (path:/x, or path:/x/* for a prefix)")
            return step
        events = by_role.get((t, step))
        if events is None:
            role = {r["role"]: r for r in plans["types"][t]["roles"]}.get(step)
            pattern = re.compile("^(?:" + role["aliases"] + ")$") if role else None
            events = sorted(e["name"] for e in found["events"] if pattern and pattern.match(e["name"]))
        if len(events) == 1:
            return events[0]
        if not events:
            todo.append(where + ": no event in the code fills role " + step + "; add it (audit.py) or drop the step")
            return "<" + step + "?>"
        todo.append(where + ": role " + step + " has " + ", ".join(events) + "; read the code and keep one per step, "
                    "or split into consecutive steps when the flow forces both")
        return step if step in events else events[0]

    for t in found["types"]:
        plan = plans["types"][t]
        for key, steps in [(t, plan["funnel"])] + [(t + " " + f["key"], f["steps"]) for f in plan.get("more_funnels", [])]:
            name = key + " funnel"
            funnels.append({"name": name, "description": plan["question"][:500], "window": window,
                            "steps": [resolve(t, s, "funnel '" + name + "'") for s in steps]})
        for role in plan.get("goals", []):
            step = resolve(t, role, "goal " + role)
            name = "Goal: " + step.strip("<?>")
            if not any(g["name"] == name for g in goals):
                goals.append({"name": name, "description": t + " plan role " + role, "step": step})
    return {"schema": SCHEMA, "domain": domain or kit_domain or "<domain>", "types": found["types"],
            "todo": todo + ([] if domain or kit_domain else ["set domain"]), "funnels": funnels, "goals": goals}


# ---------- sync ----------

def saved(client, website_id, kind):
    items, page = [], 1
    while True:
        r = client.request("/api/websites/" + website_id + "/" + kind + "s?page=" + str(page) + "&pageSize=100")
        items += r.get("data") or []
        if len(items) >= int(r.get("count") or 0) or not r.get("data"):
            return items
        page += 1


def seen(client, website_id, days, now_ms=None):
    end = now_ms or int(time.time() * 1000)
    span = "startAt=" + str(end - days * report.DAY_MS) + "&endAt=" + str(end)
    base = "/api/websites/" + website_id + "/metrics?" + span + "&limit=500&type="
    return ({row["value"] for row in report.rows(client.request(base + "event"))},
            {row["value"] for row in report.rows(client.request(base + "path"))})


def _matches_seen(value, names):
    if value.startswith("*") or value.endswith("*"):
        core = value.strip("*")
        return any((value.startswith("*") or n.startswith(core)) and (value.endswith("*") or n.endswith(core))
                   and core in n for n in names if n)
    return value in names


def plan_sync(client, website, wanted, seen_days=30, now_ms=None):
    actions, unseen = [], {}
    events, paths = seen(client, website["id"], seen_days, now_ms) if seen_days else (None, None)
    for kind in ("funnel", "goal"):
        current = {}
        for item in saved(client, website["id"], kind):
            current.setdefault(item.get("name"), item)
        for name, want in wanted[kind].items():
            have = current.pop(name, None)
            if have is None:
                actions.append({"kind": kind, "name": name, "action": "create", "body": want})
            elif (normalize(kind, have.get("parameters")) != normalize(kind, want["parameters"])
                  or (have.get("description") or "") != want["description"]):
                actions.append({"kind": kind, "name": name, "action": "update", "id": have["id"], "body": want,
                                "was": have.get("parameters")})
            else:
                actions.append({"kind": kind, "name": name, "action": "unchanged", "id": have["id"]})
        for name, item in current.items():
            actions.append({"kind": kind, "name": name, "action": "unmanaged", "id": item.get("id")})
        if events is None:
            continue
        for want in wanted[kind].values():
            steps = want["parameters"]["steps"] if kind == "funnel" else [want["parameters"]]
            for s in steps:
                pool = events if s["type"] == "event" else paths
                if not _matches_seen(s["value"], pool):
                    unseen.setdefault(step_text(s).split("[")[0], set()).add(want["name"])
    warnings = [step + " not seen in the last " + str(seen_days) + " days (used by " + ", ".join(sorted(names)) + ")"
                for step, names in sorted(unseen.items())]
    return {"actions": actions, "warnings": warnings}


def apply_sync(client, website, result):
    for a in result["actions"]:
        base = "/api/websites/" + website["id"] + "/" + a["kind"] + "s"
        if a["action"] == "create":
            a["id"] = client.request(base, a["body"]).get("id")
            a["done"] = True
        elif a["action"] == "update":
            client.request(base + "/" + a["id"], a["body"])
            a["done"] = True
    return result


# ---------- status ----------

def status(client, website, start_ms, end_ms):
    query = "?startAt=" + str(start_ms) + "&endAt=" + str(end_ms) + "&timezone=UTC"
    out = {"funnels": [], "goals": []}
    for item in sorted(saved(client, website["id"], "funnel"), key=lambda i: i.get("name") or ""):
        stats = client.request("/api/websites/" + website["id"] + "/funnels/" + item["id"] + "/stats" + query)
        steps = (item.get("parameters") or {}).get("steps") or []
        out["funnels"].append({"name": item.get("name"), "window": (item.get("parameters") or {}).get("window"),
                               "steps": [{"step": step_text(s), "visitors": s.get("visitors", 0)} for s in stats or []],
                               "funnel_py": funnel_command(website.get("domain") or "<domain>", steps),
                               "filters_dropped": any(s.get("filters") for s in steps)})
    for item in sorted(saved(client, website["id"], "goal"), key=lambda i: i.get("name") or ""):
        stats = client.request("/api/websites/" + website["id"] + "/goals/" + item["id"] + "/stats" + query) or {}
        out["goals"].append({"name": item.get("name"), "step": step_text(item.get("parameters") or {}),
                             "num": stats.get("num", 0), "total": stats.get("total", 0)})
    return out


# ---------- output ----------

def render_sync(website, result, applied):
    lines = ["Umami saved reports: " + str(website.get("name")) + " (" + str(website.get("domain")) + ")",
             "mode: " + ("applied" if applied else "preview only; re-run with --apply to write")]
    for a in result["actions"]:
        mark = {"create": "+", "update": "~", "unchanged": "=", "unmanaged": "?"}[a["action"]]
        note = {"unmanaged": " (saved in Umami, not in the spec; left alone)"}.get(a["action"], "")
        lines.append("  " + mark + " " + a["kind"] + "  " + a["name"] + "  [" + a["action"] + ("d" if a.get("done") else "") + "]" + note)
        if a["action"] in ("create", "update"):
            p = a["body"]["parameters"]
            shown = " -> ".join(step_text(s) for s in p["steps"]) + "  (window " + str(p["window"]) + " min)" if a["kind"] == "funnel" else step_text(p)
            lines.append("      " + shown)
    for w in result["warnings"]:
        lines.append("  warning: " + w)
    return "\n".join(lines)


def render_status(website, data, start_ms, end_ms):
    lines = ["Umami saved reports: " + str(website.get("name")) + " (" + str(website.get("domain")) + ")",
             "range: " + report.iso(start_ms) + " to " + report.iso(end_ms) + " (UTC); every session counts, the owner's too"]
    if not data["funnels"] and not data["goals"]:
        lines.append("  no saved funnels or goals; write a spec (draft) and sync it")
    for f in data["funnels"]:
        lines.append("")
        lines.append("Funnel: " + str(f["name"]) + "  (window " + str(f["window"]) + " min)")
        first = f["steps"][0]["visitors"] if f["steps"] else 0
        for i, s in enumerate(f["steps"], 1):
            share = " " + str(round(100 * s["visitors"] / first)) + "%" if first and i > 1 else ""
            lines.append("  %d. %-44s %6s%s" % (i, s["step"], s["visitors"], share))
        lines.append("  without the owner: " + f["funnel_py"] + " --exclude-..."
                     + ("  (funnel.py has no field filters)" if f["filters_dropped"] else ""))
    if data["goals"]:
        lines.append("")
        lines.append("Goals: visitors who reached it / all visitors")
        for g in data["goals"]:
            lines.append("  %-40s %-24s %s / %s" % (g["name"], g["step"], g["num"], g["total"]))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draft", help="Draft a spec from the site type's plan and the code's events (read-only)")
    d.add_argument("--project", required=True)
    d.add_argument("--type", action="append", help="Site type, repeatable (default: .sitekit.json site.type)")
    d.add_argument("--domain")
    d.add_argument("--window", type=float, default=DEFAULT_WINDOW, help="Minutes allowed between steps")
    s = sub.add_parser("sync", help="Create or update the saved funnels and goals the spec lists")
    s.add_argument("--spec", required=True)
    s.add_argument("--apply", action="store_true", help="Write to Umami (default: preview only)")
    s.add_argument("--seen-days", type=int, default=30, help="Warn about steps not seen in this many days (0: skip)")
    s.add_argument("--format", choices=["text", "json"], default="text")
    st = sub.add_parser("status", help="Saved funnels and goals with their numbers")
    target = st.add_mutually_exclusive_group(required=True)
    target.add_argument("--spec")
    target.add_argument("--domain")
    st.add_argument("--days", type=int, default=14)
    st.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    try:
        if args.command == "draft":
            window = int(args.window) if float(args.window).is_integer() else args.window
            print(json.dumps(draft(args.project, args.type, args.domain, window), ensure_ascii=False, indent=2))
            return 0
        domain = load_spec(args.spec)["domain"] if getattr(args, "spec", None) else args.domain
        tool = report.load_tool()
        api = tool.Umami()
        website = report.find_website(api, tool, domain)
        if args.command == "sync":
            wanted = desired(load_spec(args.spec))
            result = plan_sync(api, website, wanted, max(0, args.seen_days))
            if args.apply:
                apply_sync(api, website, result)
            text = render_sync(website, result, args.apply)
            payload = {"schema": SCHEMA, "website": website, "applied": args.apply, **result}
        else:
            start_ms, end_ms = report.date_range(args.days)
            data = status(api, website, start_ms, end_ms)
            text = render_status(website, data, start_ms, end_ms)
            payload = {"schema": SCHEMA, "website": website, "start": report.iso(start_ms), "end": report.iso(end_ms), **data}
    except Exception as error:  # ApiError, ValueError, KeyError, OSError: one clear line, no stack trace
        print("Error: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.format == "json" else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
