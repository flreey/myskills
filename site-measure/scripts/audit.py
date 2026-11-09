#!/usr/bin/env python3
"""Read-only tracking audit: the project's Umami events against the tracking plan for its site type.

    python3 audit.py --project <dir> [--type tool --type app] [--privacy <file>] [--format text|json]

Finds `track(...)`, `umami.track(...)` and `data-umami-event` call sites (tests and tooling skipped),
resolves event names and field keys (including `...ctx.current`-style spreads defined in the same file),
and compares them with references/tracking-plans.json:

- missing: required roles of the chosen types that no event fills;
- naming: names or keys that break the style, keys that differ only by case, and time keys that mean
  two things (processing time in one event, the input's length in another);
- fields: keys that look private, and keys outside the plan's allowlist;
- privacy: site-kit sites compare site events with `modules.legal.analyticsEvents` in site.config.ts
  (the kit discloses its own paid-funnel events); other sites with the privacy page text. Matching is
  by keyword, so the result is a list to read, not a verdict.

The type comes from .sitekit.json when there is one; pass --type (repeatable) to override or add.
It never writes files.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
SCHEMA = "site-measure/audit@1"
PLANS_PATH = HERE.parent / "references" / "tracking-plans.json"

_spec = importlib.util.spec_from_file_location("site_measure_scan", HERE / "scan.py")
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)

SOURCE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts", ".astro", ".vue", ".svelte",
              ".html", ".htm", ".njk", ".hbs", ".liquid", ".ejs", ".php"}
CALL = re.compile(r"(?:\bumami\s*(?:\?\.|\.)\s*track|(?<![\w.$])track)\s*(?:\?\.\s*)?\(")
ATTR_NAME = re.compile(r"""['"]?data-umami-event['"]?\s*[=:]\s*\{?\s*(['"`])([^'"`]+)\1""")
ATTR_DYNAMIC = re.compile(r"""['"]?data-umami-event['"]?\s*=\s*\{(?!\s*['"`])""")
ATTR_FIELD = re.compile(r"""['"]?data-umami-event-([A-Za-z0-9_-]+)['"]?\s*[=:]""")
STRING = re.compile(r"""(['"`])((?:\\.|(?!\1).)*)\1""")
SNAKE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
LOWER_WORD = re.compile(r"^[a-z][a-z0-9]*$")
CAMEL = re.compile(r"^[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+$")
PRIVATE_VALUE = re.compile(r"\.name\b|\bemail\b|location\.(?:href|search)|\.value\b|textContent|innerText|"
                           r"\bquery\b|JSON\.stringify|\.message\b(?!\))", re.I)
KIT_CONFIG_EVENTS = re.compile(r"analyticsEvents\s*:\s*(['\"`])((?:\\.|(?!\1).)*)\1", re.S)

# Plain-language words a disclosure uses for a field. Unlisted keys fall back to their own words.
DISCLOSURE_HINTS = {
    "res": r"resolution", "length": r"length|duration", "size": r"size", "mode": r"\bmode",
    "out": r"output", "msPerFrame": r"millisecond|per frame|speed", "ms": r"millisecond",
    "seconds": r"second|how long|time", "backend": r"backend|graphics|gpu", "reason": r"error|reason",
    "error": r"error", "state": r"device|support|capab|gpu", "from": r"which .{0,20}(?:link|button)|clicked|placement|where",
    "tier": r"tier|plan|pack", "plan": r"plan", "files": r"number of files|files", "credits": r"credit",
    "partial": r"part of|partial", "missing": r"credit|short|missing", "fits": r"fit", "status": r"finish|fail|status",
    "product": r"product", "amount": r"amount", "currency": r"currency", "results": r"result",
    "depth": r"scroll|depth|read",
}


def load_plans(path=PLANS_PATH):
    return json.loads(Path(path).read_text())


def find_kit(project):
    for root in (project, project / "site"):
        path = root / ".sitekit.json"
        if path.is_file():
            try:
                return root, json.loads(path.read_text())
            except (OSError, ValueError):
                return root, {}
    return None, None


def closing(text, start):
    """Index just past the bracket that closes text[start] (an opening bracket), skipping strings."""
    depth, i, quote = 0, start, None
    pairs = {"(": ")", "{": "}", "[": "]"}
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c == "/" and text[i:i + 2] == "//":
            nl = text.find("\n", i)
            i = len(text) if nl < 0 else nl
            continue
        elif c in pairs:
            depth += 1
        elif c in ")}]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def split_top(text, seps=","):
    parts, depth, quote, buf, i = [], 0, None, [], 0
    while i < len(text):
        c = text[i]
        if quote:
            buf.append(c)
            if c == "\\" and i + 1 < len(text):
                buf.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
            buf.append(c)
        elif c in "({[":
            depth += 1
            buf.append(c)
        elif c in ")}]":
            depth -= 1
            buf.append(c)
        elif c in seps and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


def object_entries(body, seps=","):
    """Entries of an object or type literal body: [(key, value_expr)], spreads as ('...', expr)."""
    entries = []
    for part in split_top(body, seps):
        part = re.sub(r"^\s*(?://[^\n]*\n|/\*.*?\*/)\s*", "", part, flags=re.S).strip()
        if not part:
            continue
        if part.startswith("..."):
            entries.append(("...", part[3:].strip()))
            continue
        m = re.match(r"""^(?:(['"])([^'"]+)\1|([A-Za-z_$][\w$]*))\s*\??\s*(?::\s*(.*))?$""", part, re.S)
        if m:
            entries.append((m.group(2) or m.group(3), (m.group(4) or (m.group(3) or "")).strip()))
    return entries


def spread_keys(text, expr, seen=None):
    """Keys of an object spread like `...ctx.current`, from literals assigned to it in the same file."""
    seen = seen or set()
    expr = expr.strip()
    base = re.match(r"^([A-Za-z_$][\w$]*)(\.current|\(\s*\))?$", expr)
    if not base or base.group(1) in seen:
        return set(), False
    name = base.group(1)
    seen.add(name)
    keys, found = set(), False
    if base.group(2) and base.group(2).startswith("("):
        # A helper such as `const fileCtx = () => (file ? { ...ctx.current } : {})`.
        arrow = re.compile(r"\b" + re.escape(name) + r"\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>\s*\(")
        for m in arrow.finditer(text):
            start = m.end() - 1
            more, still = arg_fields(text, text[start + 1:closing(text, start) - 1])
            keys |= set(more)
            found = found or (bool(more) or not still)
        return keys, found
    for m in re.finditer(r"\b" + re.escape(name) + r"\.([A-Za-z_$][\w$]*)\s*=(?!=)", text):  # data.seconds = ...
        if m.group(1) != "current":
            keys.add(m.group(1))
            found = True
    # `name = {`, `const name: Record<string, number> = {`, `name.current = {`, `useRef<{ ... }>`.
    pattern = re.compile(r"\b" + re.escape(name) + r"(?:\.current)?\s*(?::\s*[\w<>,\s|\[\]]+?)?=\s*(?:useRef\s*<\s*)?\{")
    for m in pattern.finditer(text):
        start = m.end() - 1
        body = text[start + 1:closing(text, start) - 1]
        typed = "useRef" in m.group(0)
        for key, value in object_entries(body, ",;" if typed else ","):
            if key == "...":
                more, ok = spread_keys(text, value, seen)
                keys |= more
                found = found or ok
            else:
                keys.add(key)
                found = True
    return keys, found


def first_arg_names(arg):
    """Event names from the first argument: a literal, or every literal in a ternary."""
    literals = [m.group(2) for m in STRING.finditer(arg)]
    if not literals or re.match(r"^[A-Za-z_$][\w$.]*$", arg.strip()):
        return []
    return [name for name in literals if re.match(r"^[\w:.\- ]+$", name)]


def parse_calls(text):
    calls = []
    for m in CALL.finditer(text):
        before = text[max(0, m.start() - 40):m.start()]
        if re.search(r"\bfunction\s*$", before):  # the wrapper's own definition
            continue
        open_at = m.end() - 1
        args = split_top(text[open_at + 1:closing(text, open_at) - 1])
        if not args:
            continue
        names = first_arg_names(args[0])
        line = text.count("\n", 0, m.start()) + 1
        if not names:
            calls.append({"line": line, "names": [], "dynamic": args[0].strip()[:40]})
            continue
        fields, unresolved = arg_fields(text, args[1]) if len(args) > 1 else ({}, [])
        calls.append({"line": line, "names": names, "fields": fields, "unresolved": unresolved, "kind": "track"})
    return calls


def literal_bodies(expr):
    """Bodies of the object literals at the top of an expression: `{...}`, or both arms of a ternary."""
    bodies, i, quote = [], 0, None
    while i < len(expr):
        c = expr[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c == "{":
            end = closing(expr, i)
            bodies.append(expr[i + 1:end - 1])
            i = end
            continue
        elif c == "(":
            i = closing(expr, i)
            continue
        i += 1
    return bodies


def arg_fields(text, expr):
    """Field keys of a track() data argument, resolving spreads and variables defined in the file."""
    fields, unresolved = {}, []
    expr = expr.strip()
    bodies = literal_bodies(expr)
    if not bodies:
        keys, ok = spread_keys(text, expr)
        if ok:
            return {k: "(via " + expr + ")" for k in keys}, []
        return {}, [expr[:40]]
    for body in bodies:
        for key, value in object_entries(body):
            inner = value.strip()
            inner = inner[1:-1] if key == "..." and inner.startswith("(") and inner.endswith(")") else inner
            if key == "..." and literal_bodies(inner):  # ...(cond ? { a } : {})
                more, still = arg_fields(text, inner)
                fields.update({k: v for k, v in more.items() if k not in fields})
                unresolved += still
            elif key == "...":
                keys, ok = spread_keys(text, value)
                for k in keys:
                    fields.setdefault(k, "(via ..." + value + ")")
                if not ok:
                    unresolved.append(value[:40])
            else:
                fields[key] = value
    return fields, unresolved


def parse_attributes(text):
    found, orphan_fields = [], []
    for number, line in enumerate(text.splitlines(), 1):
        names = [m.group(2) for m in ATTR_NAME.finditer(line)]
        fields = {m.group(1): "(attribute)" for m in ATTR_FIELD.finditer(line)}
        if names:
            for name in names:
                found.append({"line": number, "names": [name], "fields": dict(fields), "unresolved": [], "kind": "attribute"})
        elif ATTR_DYNAMIC.search(line):
            found.append({"line": number, "names": [], "dynamic": "data-umami-event={...}"})
        elif fields:
            orphan_fields.append((number, fields))
    named = [c for c in found if c["names"]]
    if orphan_fields and len({c["names"][0] for c in named}) == 1:
        for number, fields in orphan_fields:
            named[0]["fields"].update(fields)
    return found


def collect(root):
    """[{name, file, line, fields, kind, kit}] for every literal event name, plus dynamic call sites."""
    events, dynamic = [], []
    for path, kind, text in scan.walk(root):
        relpath = scan.rel(root, path)
        if kind != "code" or path.suffix not in SOURCE_EXT or scan.TEST_PATH.search(relpath) or scan.TOOLING.match(relpath):
            continue
        if "track" not in text and "data-umami-event" not in text:
            continue
        kit = relpath.startswith(("src/kit/", "scripts/kit/"))
        for call in parse_calls(text) + parse_attributes(text):
            where = relpath + ":" + str(call["line"])
            if not call["names"]:
                dynamic.append({"where": where, "first_arg": call["dynamic"]})
                continue
            for name in call["names"]:
                events.append({"name": name, "where": where, "fields": call["fields"], "unresolved": call["unresolved"],
                               "kind": call["kind"], "kit": kit})
    return events, dynamic


def style(key):
    if SNAKE.match(key):
        return "snake" if "_" in key else "word"
    if CAMEL.match(key):
        return "camel"
    return "other"


def audit(project, types=None, privacy_file=None, plans=None):
    plans = plans or load_plans()
    project = Path(project).expanduser().resolve()
    kit_root, kit = find_kit(project)
    root = kit_root or project
    kit_type = ((kit or {}).get("site") or {}).get("type")
    types = list(types or ([kit_type] if kit_type else []))
    if not types:
        raise ValueError("No .sitekit.json here; pass --type (" + ", ".join(plans["types"]) + ")")
    unknown = [t for t in types if t not in plans["types"]]
    if unknown:
        raise ValueError("Unknown --type " + ", ".join(unknown) + "; use " + ", ".join(plans["types"]))
    events, dynamic = collect(root)

    by_name = {}
    for e in events:
        item = by_name.setdefault(e["name"], {"name": e["name"], "where": [], "fields": {}, "kit": True, "unresolved": []})
        item["where"].append(e["where"])
        item["kit"] = item["kit"] and e["kit"]
        item["unresolved"] += e["unresolved"]
        for key, value in e["fields"].items():
            item["fields"].setdefault(key, []).append(value)

    roles, allowed = [], set(plans["safe_fields"])
    mapped = set()
    for t in types:
        for role in plans["types"][t]["roles"]:
            allowed |= set(role["fields"])
            pattern = re.compile("^(?:" + role["aliases"] + ")$")
            names = sorted(n for n in by_name if pattern.match(n))
            mapped |= set(names)
            roles.append({"type": t, "role": role["role"], "required": role["required"], "events": names})
    missing = [r for r in roles if r["required"] and not r["events"]]

    naming = []
    for name in sorted(by_name):
        if not SNAKE.match(name):
            naming.append({"issue": "event name is not snake_case", "name": name, "where": by_name[name]["where"][0]})
    folded = {}
    for name in by_name:
        folded.setdefault(re.sub(r"[^a-z0-9]", "", name.lower()), []).append(name)
    for names in folded.values():
        if len(names) > 1:
            naming.append({"issue": "event names differ only by case or separators", "name": ", ".join(sorted(names))})
    site_keys = {}
    for item in by_name.values():
        for key, values in item["fields"].items():
            site_keys.setdefault(key, []).append((item["name"], values))
    styles = {}
    for key in site_keys:
        styles.setdefault(style(key), []).append(key)
    if len([s for s in styles if s in ("snake", "camel")]) > 1 or "other" in styles:
        main = "camel" if len(styles.get("camel", [])) > len(styles.get("snake", [])) else "snake"
        odd = sorted(k for s, ks in styles.items() if s not in (main, "word") for k in ks)
        if odd:
            naming.append({"issue": "field keys mix styles (most are " + main + " or one word)", "name": ", ".join(odd)})
    for names in _fold(site_keys).values():
        if len(names) > 1:
            naming.append({"issue": "field keys differ only by case or separators", "name": ", ".join(sorted(names))})
    time_re = re.compile(plans["time_fields"], re.I)
    elapsed_re, media_re = re.compile(plans["elapsed_expr"]), re.compile(plans["media_length_expr"])
    for key, uses in sorted(site_keys.items()):
        if not time_re.match(key):
            continue
        meaning = {}
        for event, values in uses:
            for value in values:
                kind = "elapsed" if elapsed_re.search(value) else "media length" if media_re.search(value) else None
                if kind:
                    meaning.setdefault(kind, set()).add(event)
        if len(meaning) > 1:
            naming.append({"issue": "'" + key + "' means two things: processing time in " + ", ".join(sorted(meaning["elapsed"]))
                           + "; the input's length in " + ", ".join(sorted(meaning["media length"])), "name": key})
        elif "media length" in meaning:
            naming.append({"issue": "'" + key + "' is filled from the input's length, not the processing time ("
                           + ", ".join(sorted(meaning["media length"])) + ")", "name": key})

    private_re = re.compile(plans["private_fields"], re.I)
    fields = []
    for key, uses in sorted(site_keys.items()):
        events_using = sorted({event for event, _ in uses})
        values = [v for _, vs in uses for v in vs]
        if private_re.search(key):
            fields.append({"issue": "private-looking key", "key": key, "events": events_using})
        elif any(PRIVATE_VALUE.search(v) for v in values if not v.startswith("(")):
            fields.append({"issue": "value may carry private data", "key": key, "events": events_using,
                           "value": next(v for v in values if PRIVATE_VALUE.search(v))[:60]})
        elif key not in allowed:
            fields.append({"issue": "not in the plan's allowlist", "key": key, "events": events_using})
    unresolved = sorted({u + " (" + item["name"] + ")" for item in by_name.values() for u in item["unresolved"]})

    privacy = privacy_check(root, kit, by_name, privacy_file)
    return {
        "schema": SCHEMA,
        "project": str(root),
        "site_kit": bool(kit),
        "types": types,
        "events": [{"name": n, "kit": by_name[n]["kit"], "where": by_name[n]["where"],
                    "fields": sorted(by_name[n]["fields"])} for n in sorted(by_name)],
        "roles": roles,
        "missing": missing,
        "extra": sorted(n for n in by_name if n not in mapped and n not in plans["kit_events"]),
        "naming": naming,
        "fields": fields,
        "unresolved_spreads": unresolved,
        "dynamic_calls": dynamic,
        "privacy": privacy,
    }


def _fold(keys):
    folded = {}
    for key in keys:
        folded.setdefault(re.sub(r"[^a-z0-9]", "", key.lower()), []).append(key)
    return folded


def words(key):
    return [w.lower() for w in re.findall(r"[A-Z]?[a-z]+|\d+", key) if len(w) > 2]


def privacy_check(root, kit, by_name, privacy_file=None):
    site_events = {n: i for n, i in by_name.items() if not i["kit"]}
    keys = sorted({k for i in site_events.values() for k in i["fields"]})
    result = {"status": "MANUAL", "source": None, "text_found": False, "fields_without_mention": [], "site_events": sorted(site_events)}
    text = ""
    if privacy_file:
        path = Path(privacy_file).expanduser()
        result["source"] = str(path)
        text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    elif kit is not None:
        config = root / "site.config.ts"
        result["source"] = "site.config.ts modules.legal.analyticsEvents"
        if config.is_file():
            m = KIT_CONFIG_EVENTS.search(config.read_text(encoding="utf-8", errors="ignore"))
            text = m.group(2) if m else ""
        result["note"] = "the kit discloses its own paid-funnel events (pricing_buy, checkout_*, purchase) on sites that sell"
    else:
        pages = [p for p, kind, _ in scan.walk(root) if scan.PRIVACY_PATH.search(scan.rel(root, p)) and "privacy" in p.name.lower()
                 and not scan.TEST_PATH.search(scan.rel(root, p))]
        if pages:
            result["source"] = ", ".join(scan.rel(root, p) for p in pages[:3])
            text = " ".join(p.read_text(encoding="utf-8", errors="ignore") for p in pages[:3])
    result["text_found"] = bool(text.strip())
    if not text.strip():
        result["status"] = "fix" if site_events else "pass"
        result["note"] = (result.get("note", "") + "; " if result.get("note") else "") + "no event disclosure found"
        result["fields_without_mention"] = keys
        return result
    low = text.lower()
    for key in keys:
        hint = DISCLOSURE_HINTS.get(key)
        hit = re.search(hint, low) if hint else any(w in low for w in words(key) or [key.lower()])
        if not hit:
            result["fields_without_mention"].append(key)
    return result


def render(report):
    lines = ["Tracking audit: " + report["project"] + " (types: " + ", ".join(report["types"])
             + ("; site-kit" if report["site_kit"] else "") + ")", ""]
    lines.append("Events found (" + str(len(report["events"])) + "):")
    for e in report["events"]:
        lines.append("  " + e["name"].ljust(20) + (" [kit]" if e["kit"] else "      ") + "  " + ", ".join(e["fields"] or ["-"])
                     + "   " + e["where"][0] + (" +" + str(len(e["where"]) - 1) if len(e["where"]) > 1 else ""))
    lines += ["", "Plan roles:"]
    for r in report["roles"]:
        mark = "ok  " if r["events"] else ("MISS" if r["required"] else "-   ")
        lines.append("  " + mark + " " + r["type"] + "." + r["role"] + ("" if r["required"] else " (optional)")
                     + ": " + (", ".join(r["events"]) or "none"))
    sections = [
        ("Missing required events", [r["type"] + "." + r["role"] for r in report["missing"]]),
        ("Events outside the plan (fine if intended)", report["extra"]),
        ("Naming", [n["issue"] + ": " + n["name"] for n in report["naming"]]),
        ("Fields", [f["issue"] + ": " + f["key"] + " (" + ", ".join(f["events"]) + ")"
                    + (" value " + f["value"] if f.get("value") else "") for f in report["fields"]]),
        ("Spreads the audit could not resolve (check their keys by hand)", report["unresolved_spreads"]),
        ("Call sites with a non-literal event name (wrappers are expected)",
         [d["where"] + " " + d["first_arg"] for d in report["dynamic_calls"]]),
    ]
    for title, items in sections:
        lines += ["", title + ":" + ("" if items else " none")]
        lines += ["  - " + i for i in items]
    p = report["privacy"]
    lines += ["", "Privacy disclosure (" + p["status"] + "): " + (p["source"] or "no privacy text found")]
    if p.get("note"):
        lines.append("  " + p["note"])
    lines.append("  site events to cover: " + (", ".join(p["site_events"]) or "none"))
    lines.append("  fields with no matching words in the text: " + (", ".join(p["fields_without_mention"]) or "none"))
    lines.append("  Read the text against the events above; keyword matching only points at gaps.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="Project folder (a site-kit site may sit in <dir>/site)")
    parser.add_argument("--type", action="append", help="Site type from tracking-plans.json; repeat for two (tool + app)")
    parser.add_argument("--privacy", help="File holding the privacy text (non-kit sites; default: privacy pages found)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    try:
        report = audit(args.project, args.type, args.privacy)
    except (ValueError, OSError) as error:
        print("Error: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
