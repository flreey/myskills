#!/usr/bin/env python3
"""Idea-stage engine for site-idea: task space, gap samples, gap report, decision.

    python3 geo_idea.py --root <project> <command> [options]

Commands
  init     --name N --idea "one sentence"   create geo/project.json and empty files
  space    [--format text|json]             validate dimensions, count the page space
  sample   --n 40 [--seed 1] [--force]      stratified sample of combinations -> geo/gap/samples.jsonl
  probes                                    render geo/gap/probes.md from filled samples
  report   [--threshold 0.33]               aggregate judged runs -> geo/gap/report.json + report.md
  decide   --verdict go|narrow|stop --by user [--subspace JSON] [--note TEXT]
  extend   --dimension D --values a,b --by user   open more values of a validated dimension (long tail)
  check                                     validate every geo/ file this skill owns

State lives in <project>/geo/ (contract: references/state.md). This script never contacts an AI
service or the web; the model writes conversations, signals and judgements, the script counts.
Python stdlib only.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import itertools
import json
from pathlib import Path
import random
import sys

SCHEMA = 1
KINDS = {"entity", "task", "constraint"}
GAPS = {
    "generic": "high", "outdated": "high", "unmet_constraint": "high", "no_resource": "high",
    "weak_sources": "medium", "good": "low",
}
VERDICTS = {"go", "narrow", "stop"}
STAGES = ["idea", "space", "gap", "decided"]
ENUM_LIMIT = 200_000
SPACE_WARN = 50_000


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def read_json(p, default=None):
    if not p.exists():
        if default is not None:
            return default
        die(f"missing {p}")
    return json.loads(p.read_text())


def write_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_jsonl(p):
    if not p.exists():
        return []
    rows = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                die(f"{p}:{i}: {e}")
    return rows


def write_jsonl(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


class State:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.dir = self.root / "geo"
        self.project = self.dir / "project.json"
        self.dimensions = self.dir / "dimensions.json"
        self.samples = self.dir / "gap" / "samples.jsonl"
        self.runs = self.dir / "gap" / "runs.jsonl"
        self.raw = self.dir / "gap" / "raw"
        self.probes = self.dir / "gap" / "probes.md"
        self.report_json = self.dir / "gap" / "report.json"
        self.report_md = self.dir / "gap" / "report.md"


def set_stage(proj, stage, note):
    if STAGES.index(stage) > STAGES.index(proj.get("stage", "idea")):
        proj["stage"] = stage
    proj.setdefault("log", []).append({"date": date.today().isoformat(), "stage": stage, "note": note})


# ---------- task space ----------

def generating(dims):
    return [d for d in dims["dimensions"] if d.get("changes_answer")]


def combo_id(combo, gen):
    return "__".join(combo[d["id"]] for d in gen)


def excluded(combo, rules):
    for r in rules:
        if "same" in r:
            a, b = r["same"]
            if combo.get(a) is not None and combo.get(a) == combo.get(b):
                return True
            continue
        when = r.get("when", {})
        if when and all(combo.get(k) in (v if isinstance(v, list) else [v]) for k, v in when.items()):
            return True
    return False


def validate_dimensions(dims):
    errs, warns = [], []
    ids = set()
    for d in dims.get("dimensions", []):
        did = d.get("id")
        if not did or did in ids:
            errs.append(f"dimension id missing or duplicated: {did!r}")
        ids.add(did)
        if d.get("kind") not in KINDS:
            errs.append(f"{did}: kind must be one of {sorted(KINDS)}")
        if "changes_answer" not in d:
            errs.append(f"{did}: changes_answer is required (true/false)")
        if d.get("changes_answer") and not d.get("why"):
            errs.append(f"{did}: changes_answer=true needs 'why' (how the answer differs)")
        vals = d.get("values", [])
        vids = [v.get("id") for v in vals]
        if not vals:
            errs.append(f"{did}: no values")
        if len(vids) != len(set(vids)) or any(not v or "__" in v for v in vids):
            errs.append(f"{did}: value ids must be unique, non-empty and free of '__'")
        if not d.get("source"):
            warns.append(f"{did}: no 'source' for its values (where the list comes from)")
    for r in dims.get("exclude", []):
        keys = r.get("same") or list(r.get("when", {}).keys())
        for k in keys:
            if k not in ids:
                errs.append(f"exclude rule names unknown dimension {k!r}")
        if not r.get("why"):
            warns.append(f"exclude rule without 'why': {r}")
    gen = [d for d in dims.get("dimensions", []) if d.get("changes_answer")]
    if not gen:
        errs.append("no dimension has changes_answer=true: there is no page space")
    kinds = {d.get("kind") for d in gen}
    if gen and "entity" not in kinds and "task" not in kinds:
        warns.append("only constraint dimensions generate pages: check that an entity or task dimension is missing")
    return errs, warns


def count_space(dims):
    gen = generating(dims)
    product = 1
    for d in gen:
        product *= len(d["values"])
    rules = dims.get("exclude", [])
    if not rules:
        return product, product, True
    if product > ENUM_LIMIT:
        return product, None, False
    n = 0
    for vals in itertools.product(*[[v["id"] for v in d["values"]] for d in gen]):
        if not excluded(dict(zip([d["id"] for d in gen], vals)), rules):
            n += 1
    return product, n, True


def cmd_init(st, a):
    if st.project.exists():
        die(f"{st.project} already exists")
    proj = {
        "schema": SCHEMA, "name": a.name, "idea": a.idea,
        "audience": [], "market": {"countries": [], "languages": []},
        "platforms": [], "north_star": "", "stage": "idea",
        "decision": None, "log": [],
    }
    set_stage(proj, "idea", "initialised")
    write_json(st.project, proj)
    if not st.dimensions.exists():
        write_json(st.dimensions, {"dimensions": [], "exclude": []})
    st.raw.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"created": str(st.dir)}, ensure_ascii=False))


def cmd_space(st, a):
    dims = read_json(st.dimensions)
    errs, warns = validate_dimensions(dims)
    out = {"errors": errs, "warnings": warns}
    if not errs:
        product, n, exact = count_space(dims)
        gen = generating(dims)
        out.update({
            "generating": [{"id": d["id"], "kind": d["kind"], "values": len(d["values"])} for d in gen],
            "described_only": [d["id"] for d in dims["dimensions"] if not d.get("changes_answer")],
            "product": product, "after_excludes": n, "exact": exact,
        })
        size = n if n is not None else product
        if size > SPACE_WARN:
            warns.append(f"space of {size} combinations: plan to publish a small validated part, never all")
        proj = read_json(st.project)
        set_stage(proj, "space", f"space {size} combinations from {len(gen)} dimensions")
        write_json(st.project, proj)
    if a.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for e in errs:
            print(f"ERROR  {e}")
        for w in warns:
            print(f"WARN   {w}")
        if not errs:
            print("generating: " + ", ".join(f"{g['id']}({g['values']})" for g in out["generating"]))
            if out["described_only"]:
                print("described on the page only: " + ", ".join(out["described_only"]))
            tail = out["after_excludes"] if out["exact"] else "unknown (too large to enumerate)"
            print(f"combinations: {out['product']} before excludes, {tail} after")
    sys.exit(1 if errs else 0)


def cmd_sample(st, a):
    dims = read_json(st.dimensions)
    errs, _ = validate_dimensions(dims)
    if errs:
        die("fix dimensions first: " + "; ".join(errs))
    if st.samples.exists() and read_jsonl(st.samples) and not a.force:
        die(f"{st.samples} has rows; --force replaces it (filled conversations are lost)")
    gen = generating(dims)
    rules = dims.get("exclude", [])
    rng = random.Random(a.seed)
    use = {d["id"]: Counter() for d in gen}
    seen, rows = set(), []
    widest = max(len(d["values"]) for d in gen)
    tries = 0
    while len(rows) < a.n and tries < a.n * 200:
        tries += 1
        combo = {}
        for d in gen:
            vals = [v["id"] for v in d["values"]]
            low = min(use[d["id"]][v] for v in vals)
            pool = [v for v in vals if use[d["id"]][v] == low] if tries <= a.n * 20 else vals
            combo[d["id"]] = rng.choice(pool)
        cid = combo_id(combo, gen)
        if cid in seen or excluded(combo, rules):
            continue
        seen.add(cid)
        for k, v in combo.items():
            use[k][v] += 1
        rows.append({"combo_id": cid, "combo": combo, "persona": "", "opening": "",
                     "follow_ups": [], "signals": []})
    write_jsonl(st.samples, rows)
    uncovered = [f"{d['id']}={v['id']}" for d in gen for v in d["values"] if use[d["id"]][v["id"]] == 0]
    out = {"samples": len(rows), "file": str(st.samples), "uncovered_values": uncovered}
    if a.n < widest:
        out["warning"] = f"n={a.n} is below the widest dimension ({widest} values): some values go unsampled"
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_probes(st, a):
    rows = read_jsonl(st.samples)
    if not rows:
        die("no samples: run sample first")
    empty = [r["combo_id"] for r in rows if not r.get("opening")]
    if empty:
        die(f"{len(empty)} samples have no opening yet (first: {empty[0]}); write the conversations first")
    proj = read_json(st.project)
    platforms = proj.get("platforms") or ["ChatGPT"]
    lines = [
        f"# Probe sheet: {proj.get('name', '')}", "",
        f"Platforms: {', '.join(platforms)}. Each conversation in a new chat, memory off where possible.",
        "Ask the opening, then each follow-up in the same chat. Note the model and whether it searched the web.",
        "Paste the whole answer (all turns, with links) into the file named under each conversation.", "",
    ]
    for r in rows:
        lines += [f"## {r['combo_id']}", "", f"Persona: {r.get('persona', '')}", "", "Opening:", "",
                  "> " + r["opening"].replace("\n", "\n> "), ""]
        for i, f in enumerate(r.get("follow_ups", []), 1):
            lines += [f"Follow-up {i}: {f}", ""]
        files = ", ".join(f"`geo/gap/raw/{r['combo_id']}--{p.lower().replace(' ', '-')}--1.md`" for p in platforms)
        lines += [f"Save as: {files}", ""]
    st.probes.write_text("\n".join(lines))
    print(json.dumps({"file": str(st.probes), "conversations": len(rows), "platforms": platforms}, ensure_ascii=False))


# ---------- report ----------

def combo_level(levels):
    if not levels:
        return "unprobed"
    c = Counter(levels)
    if c["high"] * 2 >= len(levels):
        return "high"
    if (c["high"] + c["medium"]) * 2 >= len(levels):
        return "medium"
    return "low"


def build_report(samples, runs, threshold):
    by_combo = defaultdict(list)
    platforms, dates = Counter(), set()
    for r in runs:
        if r.get("gap") in GAPS:
            by_combo[r["combo_id"]].append(GAPS[r["gap"]])
            platforms[r.get("platform", "?")] += 1
            if r.get("date"):
                dates.add(r["date"])
    combos = []
    for s in samples:
        lv = combo_level(by_combo.get(s["combo_id"], []))
        combos.append({"combo_id": s["combo_id"], "combo": s["combo"], "level": lv,
                       "runs": len(by_combo.get(s["combo_id"], [])), "signals": len(s.get("signals", []))})
    probed = [c for c in combos if c["level"] != "unprobed"]
    high = [c for c in probed if c["level"] == "high"]
    per_value = defaultdict(lambda: {"probed": 0, "high": 0, "signals": 0})
    for c in probed:
        for k, v in c["combo"].items():
            pv = per_value[f"{k}={v}"]
            pv["probed"] += 1
            pv["high"] += c["level"] == "high"
            pv["signals"] += c["signals"] > 0
    values = sorted(
        ({"value": k, **v, "share_high": round(v["high"] / v["probed"], 2)} for k, v in per_value.items()),
        key=lambda x: (-x["share_high"], -x["probed"], x["value"]))
    share = round(len(high) / len(probed), 2) if probed else 0.0
    strong = [v["value"] for v in values if v["probed"] >= 2 and v["share_high"] >= threshold]
    if not probed:
        hint = "no judged runs yet"
    elif share >= threshold:
        hint = "go"
    elif strong:
        hint = "narrow"
    else:
        hint = "stop"
    return {
        "threshold": threshold, "samples": len(samples), "probed": len(probed), "high": len(high),
        "share_high": share, "with_signals": sum(1 for c in probed if c["signals"]),
        "levels": dict(Counter(c["level"] for c in combos)),
        "platform_runs": dict(platforms), "dates": sorted(dates),
        "hint": hint, "strong_values": strong, "values": values, "combos": combos,
    }


def report_md(rep, proj):
    L = [f"# Gap report: {proj.get('name', '')}", "",
         f"Hint (the decision is the owner's): **{rep['hint']}**. "
         f"{rep['high']} of {rep['probed']} probed combinations show a high-opportunity gap "
         f"({rep['share_high']:.0%}; threshold {rep['threshold']:.0%}). "
         f"{rep['with_signals']} of them have outside evidence.", "",
         f"Runs by platform: {', '.join(f'{k} {v}' for k, v in rep['platform_runs'].items()) or 'none'}. "
         f"Dates: {', '.join(rep['dates']) or 'none'}. AI answers are samples, not rankings.", "",
         "## By dimension value", "", "| Value | Probed | High | Share high | With signals |",
         "| --- | --- | --- | --- | --- |"]
    for v in rep["values"]:
        L.append(f"| {v['value']} | {v['probed']} | {v['high']} | {v['share_high']:.0%} | {v['signals']} |")
    L += ["", "## Combinations", "", "| Combination | Level | Runs | Signals |", "| --- | --- | --- | --- |"]
    order = {"high": 0, "medium": 1, "low": 2, "unprobed": 3}
    for c in sorted(rep["combos"], key=lambda c: (order[c["level"]], c["combo_id"])):
        L.append(f"| {c['combo_id']} | {c['level']} | {c['runs']} | {c['signals']} |")
    if rep["strong_values"]:
        L += ["", "Values at or above the threshold (candidate subspace): " + ", ".join(rep["strong_values"])]
    return "\n".join(L) + "\n"


def cmd_report(st, a):
    samples, runs = read_jsonl(st.samples), read_jsonl(st.runs)
    if not samples:
        die("no samples")
    rep = build_report(samples, runs, a.threshold)
    proj = read_json(st.project)
    write_json(st.report_json, rep)
    st.report_md.write_text(report_md(rep, proj))
    if rep["probed"]:
        set_stage(proj, "gap", f"gap report: {rep['high']}/{rep['probed']} high, hint {rep['hint']}")
        write_json(st.project, proj)
    print(json.dumps({k: rep[k] for k in ("probed", "high", "share_high", "hint", "strong_values")},
                     ensure_ascii=False, indent=2))


def cmd_decide(st, a):
    if a.verdict not in VERDICTS:
        die(f"verdict must be one of {sorted(VERDICTS)}")
    if not st.report_json.exists():
        die("no gap report: run report first")
    if a.by != "user":
        die("the decision is the owner's: pass --by user only after they said it in chat")
    proj = read_json(st.project)
    sub = json.loads(a.subspace) if a.subspace else None
    if a.verdict == "narrow" and not sub:
        die("narrow needs --subspace, e.g. '{\"source\": [\"heic\", \"png\"]}'")
    if sub:
        dims = {d["id"]: {v["id"] for v in d["values"]} for d in read_json(st.dimensions)["dimensions"]}
        for k, vs in sub.items():
            if k not in dims or not set(vs) <= dims[k]:
                die(f"subspace names unknown dimension or values: {k}={vs}")
    rep = read_json(st.report_json)
    if not rep.get("probed"):
        die("the gap report has no judged runs: probe and judge before deciding")
    proj["decision"] ={"verdict": a.verdict, "date": date.today().isoformat(), "by": "user",
                        "subspace": sub, "note": a.note or "",
                        "evidence": {"probed": rep["probed"], "share_high": rep["share_high"], "hint": rep["hint"]},
                        "dimensions": [d["id"] for d in generating(read_json(st.dimensions))],
                        "extensions": []}
    set_stage(proj, "decided", f"decision {a.verdict}")
    write_json(st.project, proj)
    print(json.dumps(proj["decision"], ensure_ascii=False, indent=2))


def cmd_extend(st, a):
    """Add values of an already validated dimension to the decided space (long-tail growth)."""
    if a.by != "user":
        die("extending the decided space is the owner's call: pass --by user only after they said it in chat")
    proj = read_json(st.project)
    dec = proj.get("decision") or {}
    if dec.get("verdict") not in ("go", "narrow"):
        die("no go or narrow decision to extend")
    dims = read_json(st.dimensions)
    gen = {d["id"]: d for d in generating(dims)}
    validated = dec.get("dimensions") or list(gen)
    if a.dimension not in validated:
        die(f"{a.dimension!r} was not part of the gap check: a new dimension needs site-idea sampling, not extend")
    if a.dimension not in gen:
        die(f"{a.dimension!r} is not a generating dimension in dimensions.json")
    known = {v["id"] for v in gen[a.dimension]["values"]}
    values = [v.strip() for v in a.values.split(",") if v.strip()]
    missing = [v for v in values if v not in known]
    if missing:
        die(f"add these values to dimensions.json first: {missing}")
    sub = dec.get("subspace") or {}
    added = []
    if a.dimension in sub:
        for v in values:
            if v not in sub[a.dimension]:
                sub[a.dimension].append(v)
                added.append(v)
        dec["subspace"] = sub
    dec.setdefault("extensions", []).append({"date": date.today().isoformat(), "by": "user",
                                             "dimension": a.dimension, "values": values,
                                             "added_to_subspace": added, "note": a.note or ""})
    proj["decision"] = dec
    proj.setdefault("log", []).append({"date": date.today().isoformat(), "stage": proj.get("stage", "decided"),
                                       "note": f"extend {a.dimension}: {', '.join(values)}"})
    write_json(st.project, proj)
    print(json.dumps({"dimension": a.dimension, "values": values, "added_to_subspace": added,
                      "already_open": a.dimension not in sub}, ensure_ascii=False, indent=2))


# ---------- check ----------

def cmd_check(st, a):
    errs = []
    proj = read_json(st.project)
    for k in ("name", "idea"):
        if not proj.get(k):
            errs.append(f"project.json: {k} is empty")
    if proj.get("stage") not in STAGES + ["blueprint", "pages"]:
        errs.append(f"project.json: unknown stage {proj.get('stage')!r}")
    dims = read_json(st.dimensions)
    derr, _ = validate_dimensions(dims)
    errs += [f"dimensions.json: {e}" for e in derr]
    values = {d["id"]: {v["id"] for v in d.get("values", [])} for d in dims.get("dimensions", [])}
    samples = read_jsonl(st.samples)
    sample_ids = set()
    for s in samples:
        sample_ids.add(s.get("combo_id"))
        for k, v in s.get("combo", {}).items():
            if v not in values.get(k, set()):
                errs.append(f"samples: {s.get('combo_id')}: unknown {k}={v}")
        for sig in s.get("signals", []):
            if not str(sig.get("url", "")).startswith("http"):
                errs.append(f"samples: {s.get('combo_id')}: signal without a URL")
    for i, r in enumerate(read_jsonl(st.runs), 1):
        where = f"runs:{i}"
        if r.get("combo_id") not in sample_ids:
            errs.append(f"{where}: combo_id {r.get('combo_id')!r} is not a sample")
        if r.get("gap") is not None and r.get("gap") not in GAPS:
            errs.append(f"{where}: gap must be one of {sorted(GAPS)} or null")
        for k in ("platform", "date", "mode"):
            if not r.get(k):
                errs.append(f"{where}: {k} is required")
        raw = r.get("raw")
        if raw and not (st.root / raw).exists():
            errs.append(f"{where}: raw file {raw} does not exist")
    for e in errs:
        print(f"ERROR  {e}")
    print(json.dumps({"errors": len(errs)}))
    sys.exit(1 if errs else 0)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--name", required=True)
    s.add_argument("--idea", required=True)
    s = sub.add_parser("space")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s = sub.add_parser("sample")
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--force", action="store_true")
    sub.add_parser("probes")
    s = sub.add_parser("report")
    s.add_argument("--threshold", type=float, default=0.33)
    s = sub.add_parser("decide")
    s.add_argument("--verdict", required=True)
    s.add_argument("--by", required=True)
    s.add_argument("--subspace")
    s.add_argument("--note")
    s = sub.add_parser("extend")
    s.add_argument("--dimension", required=True)
    s.add_argument("--values", required=True, help="comma-separated value ids already in dimensions.json")
    s.add_argument("--by", required=True)
    s.add_argument("--note")
    sub.add_parser("check")
    a = p.parse_args(argv)
    st = State(a.root)
    {"init": cmd_init, "space": cmd_space, "sample": cmd_sample, "probes": cmd_probes,
     "report": cmd_report, "decide": cmd_decide, "extend": cmd_extend, "check": cmd_check}[a.cmd](st, a)


if __name__ == "__main__":
    main()
