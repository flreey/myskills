#!/usr/bin/env python3
"""Page engine for site-batch: gate combinations, write site-kit data, run waves.

    python3 geo_engine.py --root <site> <command> [options]

Commands
  lint                         validate facts, templates and combos (no writes)
  build [--target kit|json]    gate every combination, write geo/instances.jsonl and the site data:
                               kit: data/<template>.jsonl; json: geo/out/<template>.json, index.json, urls.txt
  scaffold --template ID       write src/site/collections/<ID>.ts, the geo item template override,
                               and print the site.config.ts collection entry
  status                       counts per template: rows, gated, failed by reason, waves
  questions --template ID      the gap samples seen through one template: openings with the page level
                               they route to (item, group, hub) and follow-ups grouped by kind, to set
                               question_slots, title patterns and group content
  wave-plan --per-template N [--control-ratio R] [--include-control]
                               put the next N gated, unreleased combinations of each template in a new
                               wave; with R, hold back that share of similar rows as the wave's control
  snapshot --template ID --base ORIGIN [--limit N]
                               adopt templates: save the live HTML of each row's existing URL before a
                               retrofit (geo/snapshots/<template>/), for before/after and rollback
  wave-release --wave K        mark wave K released (then build, check and deploy through site-kit)
  funnel                       crawl / index / AI fetch / citation rates by template, wave and arm
  prune --min-days 28          released pages still not indexed after N days: merge or noindex candidates

State contract: site-idea/references/state.md. Writes only geo/instances.jsonl, geo/waves.json,
data/<template>.jsonl or the json output directory and, on scaffold, src/site/collections/<id>.ts and
src/site/overrides/templates/DirectoryItem.astro. Never edits site.config.ts, combos or facts.
Python stdlib only.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
import re
import sys

STATUSES = {"met": "Yes", "conditional": "With conditions", "unmet": "No"}
# Follow-up kinds from site-idea samples; they decide the page section (references/question-mapping.md).
TURN_KINDS = {"constraint", "howto", "why", "compare", "resource", "other"}
# Section headings the geo overrides add; the kit's own headings come from its i18n messages.
LABELS = {"chooser": "Which one fits", "alternatives": "Other ways to do it"}
TEXT_FIELDS = ("core_answer", "headline")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
TOKEN = re.compile(r"[A-Za-z0-9]+|[぀-ヿ㐀-鿿가-힯]")
PLACE = re.compile(r"\{([a-z0-9_]+)(?:\.(label))?\}")
ITEM_TYPES = {"Thing", "CreativeWork", "Product", "Place", "Dataset", "SoftwareApplication", "DefinedTerm"}
HERE = Path(__file__).resolve().parent


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
    out = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                die(f"{p}:{i}: {e}")
    return out


def write_jsonl(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


class State:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.geo = self.root / "geo"
        self.project = self.geo / "project.json"
        self.dimensions = self.geo / "dimensions.json"
        self.facts = self.geo / "facts.jsonl"
        self.templates = self.geo / "templates"
        self.combos = self.geo / "combos"
        self.instances = self.geo / "instances.jsonl"
        self.waves = self.geo / "waves.json"
        self.snapshots = self.geo / "measure" / "snapshots.jsonl"
        self.samples = self.geo / "gap" / "samples.jsonl"
        self.data = self.root / "data"

    def load(self):
        proj = read_json(self.project)
        dims = read_json(self.dimensions)
        facts = {f["id"]: f for f in read_jsonl(self.facts) if f.get("id")}
        templates = {}
        if self.templates.exists():
            for p in sorted(self.templates.glob("*.json")):
                t = json.loads(p.read_text())
                templates[t.get("id") or p.stem] = t
        combos = {tid: read_jsonl(self.combos / f"{tid}.jsonl") for tid in templates}
        waves = read_json(self.waves, {"waves": []})
        return proj, dims, facts, templates, combos, waves

    def group_rows(self, tid):
        return read_jsonl(self.combos / f"{tid}.groups.jsonl")


# ---------- helpers ----------

STAGES = ["idea", "space", "gap", "decided", "blueprint", "pages"]


def advance(st, stage, note):
    proj = read_json(st.project)
    cur = proj.get("stage", "idea")
    if cur in STAGES and STAGES.index(stage) > STAGES.index(cur):
        proj["stage"] = stage
        proj.setdefault("log", []).append({"date": date.today().isoformat(), "stage": stage, "note": note})
        write_json(st.project, proj)

def is_adopt(t):
    """Adopt templates take over existing pages: rows carry the live URL, nothing new is created."""
    return bool(t.get("adopt"))


def labels(dims):
    out = {}
    for d in dims.get("dimensions", []):
        out[d["id"]] = {v["id"]: v.get("label", v["id"]) for v in d.get("values", [])}
    return out


def render(pattern, row, lab):
    def sub(m):
        key, lab_flag = m.group(1), m.group(2)
        combo = row.get("combo", {})
        if key in combo:
            return lab.get(key, {}).get(combo[key], combo[key]) if lab_flag else combo[key]
        v = row.get(key)
        return "" if v is None else str(v)
    return PLACE.sub(sub, pattern).strip()


def prose(row):
    parts = [str(row.get(f, "") or "") for f in TEXT_FIELDS]
    parts += [str(c.get("note", "")) for c in row.get("constraint_results", []) or []]
    parts += [f"{q.get('q', '')} {q.get('a', '')}" for q in row.get("follow_ups", []) or []]
    parts += [str(a.get("note", "")) for a in row.get("alternatives", []) or []]
    return " ".join(parts)


def tokens(text):
    return [t.lower() for t in TOKEN.findall(text)]


def shingles(text, n=3):
    t = tokens(text)
    return {" ".join(t[i:i + n]) for i in range(max(0, len(t) - n + 1))}


def filled(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return bool(v)
    return True


def subspace_ok(combo, decision):
    sub = (decision or {}).get("subspace") or {}
    return all(combo.get(k) in vs for k, vs in sub.items())


def arm_for(tid, combo_id, experiment):
    if not experiment or not experiment.get("arms"):
        return None
    h = int(hashlib.sha256(f"{tid}:{experiment.get('name', '')}:{combo_id}".encode()).hexdigest(), 16)
    arms = experiment["arms"]
    return arms[h % len(arms)]


def released_map(waves):
    out = {}
    for w in waves.get("waves", []):
        for tid, ids in (w.get("combos") or {}).items():
            for cid in ids:
                out[(tid, cid)] = (w["id"], w.get("status") == "released", w.get("released"))
    return out


# ---------- lint ----------

def lint_templates(templates, dims, errs, warns):
    dim_ids = {d["id"] for d in dims.get("dimensions", [])}
    paths = set()
    for tid, t in templates.items():
        w = f"templates/{tid}.json"
        if not SLUG.match(tid):
            errs.append(f"{w}: id must be a slug")
        for d in t.get("dimensions", []):
            if d not in dim_ids:
                errs.append(f"{w}: unknown dimension {d!r}")
        col = t.get("collection", {})
        if is_adopt(t) and col.get("groups"):
            warns.append(f"{w}: adopt templates keep the site's own group pages; collection.groups is ignored")
        for k in ("basePath", "label", "hub"):
            if not is_adopt(t) and not col.get(k):
                errs.append(f"{w}: collection.{k} is required")
        bp = col.get("basePath", "")
        if bp and bp in paths:
            errs.append(f"{w}: basePath {bp} is used by another template")
        paths.add(bp)
        if col.get("itemType", "Thing") not in ITEM_TYPES:
            errs.append(f"{w}: itemType must be one of {sorted(ITEM_TYPES)}")
        g = None if is_adopt(t) else col.get("groups")
        if g and g.get("by") not in t.get("dimensions", []):
            errs.append(f"{w}: groups.by must be one of the template's dimensions")
        pats = t.get("patterns", {})
        for k in ("slug", "name", "title", "h1", "description"):
            if not is_adopt(t) and not pats.get(k):
                errs.append(f"{w}: patterns.{k} is required")
        if not is_adopt(t) and pats.get("slug") and not all(f"{{{d}}}" in pats["slug"] for d in t.get("dimensions", [])):
            errs.append(f"{w}: patterns.slug must contain every dimension id so slugs stay unique")
        if "core_answer" not in t.get("required", []):
            errs.append(f"{w}: required must include core_answer (the answer-first paragraph)")
        if not t.get("approved"):
            warns.append(f"{w}: not approved by the owner yet (approved: {{by, date}})")
        sids = set()
        for q in t.get("question_slots", []) or []:
            if not q.get("id") or not SLUG.match(q["id"]) or q["id"] in sids:
                errs.append(f"{w}: question_slots ids must be unique slugs ({q.get('id')!r})")
            sids.add(q.get("id"))
            if not q.get("question"):
                errs.append(f"{w}: question slot {q.get('id')!r} needs the question text")
            if q.get("kind") not in TURN_KINDS:
                errs.append(f"{w}: question slot {q.get('id')!r} kind must be one of {sorted(TURN_KINDS)}")
        if not t.get("question_slots"):
            warns.append(f"{w}: no question_slots: rows outside the sample get no shared follow-ups (run questions)")
        for k, v in (t.get("labels") or {}).items():
            if k not in LABELS:
                errs.append(f"{w}: labels.{k} is not a label (use {sorted(LABELS)})")
            elif not isinstance(v, str) or not v.strip():
                errs.append(f"{w}: labels.{k} must be non-empty text")
        if not t.get("title_source"):
            warns.append(f"{w}: no title_source: say which real openings the title pattern follows")


def lint_facts(facts, errs, warns):
    for fid, f in facts.items():
        for k in ("value", "source", "checked"):
            if not f.get(k):
                errs.append(f"facts.jsonl: {fid}: {k} is required")


def unsourced_numbers(text, cited, extra_values, facts, t):
    sourced = " ".join(str(facts[f].get("value", "")) for f in cited if f in facts) + " " + " ".join(extra_values)
    ok = {n.replace(",", "") for n in NUM.findall(sourced)} | {str(n) for n in t.get("allow_numbers", [])}
    return sorted({n for n in NUM.findall(text) if n.replace(",", "") not in ok})


def gate_slots(row, t):
    failed = []
    slots = {q["id"]: q for q in t.get("question_slots", []) or [] if q.get("id")}
    answered = set()
    for f in row.get("follow_ups", []) or []:
        if not (f.get("q") and f.get("a")):
            failed.append("follow-up needs q and a")
        if f.get("slot"):
            answered.add(f["slot"])
    for c in row.get("constraint_results", []) or []:
        if c.get("slot"):
            answered.add(c["slot"])
    unknown = sorted(answered - set(slots))
    if unknown:
        failed.append(f"unknown question slots {unknown}")
    missing = [sid for sid, q in slots.items() if q.get("required", True) and sid not in answered]
    if missing:
        failed.append(f"unanswered question slots {missing}")
    return failed


def gate_row(row, t, lab, facts, decision):
    """Return (failed reasons, rendered fields). Uniqueness is added by build()."""
    failed = []
    combo = row.get("combo") or {}
    for d in t.get("dimensions", []):
        if d not in combo:
            failed.append(f"combo missing dimension {d}")
        elif combo[d] not in lab.get(d, {}):
            failed.append(f"unknown value {d}={combo[d]}")
    if combo and not subspace_ok(combo, decision):
        failed.append("outside the decided subspace")
    for f in t.get("required", []):
        if not filled(row.get(f)):
            failed.append(f"missing {f}")
    cited = row.get("fact_ids") or []
    missing = [f for f in cited if f not in facts]
    if missing:
        failed.append(f"unknown fact ids {missing}")
    for c in row.get("constraint_results", []) or []:
        st = c.get("status")
        if st == "unknown":
            failed.append(f"constraint {c.get('constraint')!r} is unknown")
        elif st not in STATUSES:
            failed.append(f"constraint {c.get('constraint')!r} has status {st!r}")
    for k in row.get("key_facts", []) or []:
        if not (k.get("fact_id") in facts or k.get("source")):
            failed.append(f"key fact {k.get('label')!r} has no fact_id or source")
    unsourced = unsourced_numbers(prose(row), cited, [str(k.get("value", "")) for k in row.get("key_facts", []) or []], facts, t)
    if unsourced:
        failed.append(f"numbers not in cited facts: {unsourced[:5]}")
    failed += gate_slots(row, t)
    r = row.get("resource")
    if r and not str(r.get("url", "")).startswith(("/", "http")):
        failed.append("resource.url must be a path or URL")
    pats = t.get("patterns", {})
    if is_adopt(t):
        # Existing page: the URL is its identity; title and the rest change only when the row or a pattern says so.
        url = str(row.get("url") or "")
        if not url.startswith("/"):
            failed.append("adopt rows need url: the existing page's path, starting with /")
        seg = url.rstrip("/").rsplit("/", 1)[-1] or "home"
        out = {"slug": row.get("slug") or re.sub(r"[^a-z0-9]+", "-", seg.lower()).strip("-") or "home", "url": url}
        for k in ("name", "title", "h1", "description"):
            out[k] = str(row.get(k) or (render(pats[k], row, lab) if pats.get(k) else ""))
        if out["description"] and not 50 <= len(out["description"]) <= 155:
            failed.append(f"description is {len(out['description'])} chars (50-155)")
        return failed, out
    out = {k: render(pats.get(k, ""), row, lab) for k in ("slug", "name", "title", "h1", "description")}
    if not SLUG.match(out["slug"]):
        failed.append(f"slug {out['slug']!r} is not a slug")
    if not 50 <= len(out["description"]) <= 155:
        failed.append(f"description is {len(out['description'])} chars (50-155)")
    base = (t.get("collection") or {}).get("basePath", "").rstrip("/")
    out["url"] = f"{base}/{out['slug']}"
    return failed, out


def to_facts(row, t):
    facts = []
    for c in row.get("constraint_results", []) or []:
        if c.get("status") in STATUSES:
            v = STATUSES[c["status"]] + (f" — {c['note']}" if c.get("note") else "")
            facts.append({"label": str(c.get("constraint", "")), "value": v})
    for k in row.get("key_facts", []) or []:
        facts.append({"label": str(k.get("label", "")), "value": str(k.get("value", "")), **({"mono": True} if k.get("mono") else {})})
    for spec in t.get("facts_fields", []) or []:
        v = row.get(spec.get("field"))
        if filled(v):
            facts.append({"label": spec.get("label", spec["field"]), "value": str(v)})
    return facts


def related_slugs(rows_by_cid, me, dims_order, limit=6):
    """Built siblings that differ from me in exactly one dimension, in dimension order."""
    out = []
    for d in dims_order:
        for cid, r in rows_by_cid.items():
            if cid == me["combo_id"]:
                continue
            diff = [k for k in dims_order if r["combo"].get(k) != me["combo"].get(k)]
            if diff == [d]:
                out.append(r["slug"])
                if len(out) >= limit:
                    return out
    return out


def evaluate(st):
    proj, dims, facts, templates, combos, waves = st.load()
    lab = labels(dims)
    decision = proj.get("decision")
    rel = released_map(waves)
    ctl = {(tid, cid): w["id"] for w in waves.get("waves", []) for tid, ids in (w.get("control") or {}).items() for cid in ids}
    result = {}
    for tid, t in templates.items():
        rows = combos.get(tid, [])
        seen_cid, seen_slug = set(), set()
        evald = []
        for row in rows:
            cid = row.get("combo_id") or "__".join(str(row.get("combo", {}).get(d, "")) for d in t.get("dimensions", []))
            arm = arm_for(tid, cid, t.get("experiment"))
            variant = (row.get("variants") or {}).get(arm) if arm else None
            if variant:
                row = {**row, **variant}
            failed, out = gate_row(row, t, lab, facts, decision)
            if cid in seen_cid:
                failed.append("duplicate combo_id")
            ident = out["url"] if is_adopt(t) else out["slug"]
            if ident in seen_slug:
                failed.append("duplicate url" if is_adopt(t) else "duplicate slug")
            seen_cid.add(cid)
            seen_slug.add(ident)
            evald.append({"row": row, "cid": cid, "arm": arm, "failed": failed, "out": out, "sh": shingles(prose(row))})
        counts = Counter(s for e in evald for s in e["sh"])
        minu = float(t.get("min_unique_ratio", 0.6))
        for e in evald:
            sh = e["sh"]
            e["unique"] = round(sum(1 for s in sh if counts[s] == 1) / len(sh), 2) if sh else 0.0
            if len(evald) > 1 and e["unique"] < minu:
                e["failed"].append(f"unique ratio {e['unique']} < {minu}")
            w = rel.get((tid, e["cid"]))
            e["wave"], e["released"], e["released_on"] = (w if w else (None, False, None))
            e["control_of"] = ctl.get((tid, e["cid"]))
        result[tid] = {"template": t, "items": evald}
    return proj, dims, facts, templates, waves, result


def cmd_lint(st, a):
    proj, dims, facts, templates, combos, waves = st.load()
    errs, warns = [], []
    if (proj.get("decision") or {}).get("verdict") not in ("go", "narrow"):
        errs.append("project.json: no go or narrow decision recorded (site-idea decide)")
    if not templates:
        errs.append("no templates in geo/templates/")
    lint_templates(templates, dims, errs, warns)
    validated = (proj.get("decision") or {}).get("dimensions")
    if validated:
        for tid, t in templates.items():
            for d in t.get("dimensions", []):
                if d not in validated:
                    errs.append(f"templates/{tid}.json: dimension {d!r} was not part of the gap check (site-idea)")
    lint_facts(facts, errs, warns)
    _, _, _, _, _, result = evaluate(st)
    for tid, r in result.items():
        n = len(r["items"])
        bad = sum(1 for e in r["items"] if e["failed"])
        if n == 0:
            warns.append(f"combos/{tid}.jsonl: no rows")
        elif bad:
            warns.append(f"combos/{tid}.jsonl: {n - bad}/{n} rows pass the gate (status shows why)")
    for e in errs:
        print(f"ERROR  {e}")
    for w in warns:
        print(f"WARN   {w}")
    print(json.dumps({"errors": len(errs), "warnings": len(warns)}))
    sys.exit(1 if errs else 0)


# ---------- build ----------

def cmd_build(st, a):
    proj, dims, facts, templates, waves, result = evaluate(st)
    errs, warns = [], []
    lint_templates(templates, dims, errs, warns)
    if errs:
        die("templates have errors, run lint: " + "; ".join(errs[:3]))
    target, out_dir = output_target(st, proj, a)
    instances, summary, index, urls = [], {}, [], []
    for tid, r in result.items():
        t = r["template"]
        base = (t.get("collection") or {}).get("basePath", "").rstrip("/")
        gby = None if is_adopt(t) else ((t.get("collection") or {}).get("groups") or {}).get("by")
        lab = labels(dims)
        built = {e["cid"]: {"combo_id": e["cid"], "combo": e["row"]["combo"], "slug": e["out"]["slug"]}
                 for e in r["items"] if not e["failed"]}
        data = []
        for e in r["items"]:
            row, out = e["row"], e["out"]
            instances.append({
                "template": tid, "combo_id": e["cid"], "slug": out["slug"], "url": out["url"],
                "adopt": is_adopt(t), "control_of": e["control_of"],
                "gate": {"pass": not e["failed"], "failed": e["failed"]}, "unique_ratio": e["unique"],
                "wave": e["wave"], "released": e["released"], "released_on": e["released_on"], "arm": e["arm"],
            })
            if e["failed"]:
                continue
            g = None
            if gby:
                v = row["combo"][gby]
                g = {"key": v, "name": lab.get(gby, {}).get(v, v)}
            data.append({
                **out, "combo_id": e["cid"], "answer": row["core_answer"], "facts": to_facts(row, t),
                "group": g, "related": related_slugs(built, built[e["cid"]], t["dimensions"]),
                "updated": row.get("updated"), "released": e["released"], "arm": e["arm"],
                "follow_ups": row.get("follow_ups") or [], "resource": row.get("resource"),
                "alternatives": row.get("alternatives") or [],
            })
        gcontent, gfail = group_content(st.group_rows(tid), t, data, facts, lab, base) if gby else ({}, {})
        labels_out = {**LABELS, **(t.get("labels") or {})}
        if is_adopt(t):
            # Existing pages on any stack: always plain JSON, read by the site's own templates.
            out_file = write_json_target(out_dir, tid, t, data, base)
            index.append({"id": tid, "file": out_file.name, "adopt": True,
                          "items": sum(1 for d in data if d["released"]), "pending": sum(1 for d in data if not d["released"])})
        elif target == "kit":
            out_file = st.data / f"{tid}.jsonl"
            write_jsonl(out_file, data)
            write_json(st.data / f"{tid}.labels.json", labels_out)
            if gby:
                write_json(st.data / f"{tid}.groups.json", gcontent)
        else:
            out_file = write_json_target(out_dir, tid, t, data, base, gcontent)
            index.append({"id": tid, "file": out_file.name, "basePath": base,
                          "items": sum(1 for d in data if d["released"]), "pending": sum(1 for d in data if not d["released"])})
            urls += [d["url"] for d in data if d["released"]]
        summary[tid] = {"rows": len(r["items"]), "gated": len(data),
                        "released": sum(1 for d in data if d["released"]), "output": str(out_file)}
        if gfail:
            summary[tid]["group_failures"] = gfail
    if target == "json" or any(i.get("adopt") for i in index):
        write_json(out_dir / "index.json", {"generated": date.today().isoformat(), "templates": index})
        (out_dir / "urls.txt").write_text("".join(u + "\n" for u in sorted(urls)))
    write_jsonl(st.instances, instances)
    if any(v["gated"] for v in summary.values()):
        advance(st, "blueprint", "first build with gated pages")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def group_content(rows, t, data, facts, lab, base):
    """Group pages answer questions that fix only the group dimension: an overview answer, a chooser
    that sends each condition to one released item page, and the group's own follow-ups."""
    gby = (t["collection"].get("groups") or {}).get("by")
    out, failed = {}, {}
    if not gby:
        return out, failed
    released = {d["slug"]: d for d in data if d["released"]}
    in_group = defaultdict(set)
    for d in data:
        if d["group"]:
            in_group[d["group"]["key"]].add(d["slug"])
    for g in rows:
        key, why = g.get("key"), []
        if key not in lab.get(gby, {}):
            failed[str(key)] = [f"unknown {gby} value"]
            continue
        if not filled(g.get("answer")):
            why.append("missing answer")
        cited = g.get("fact_ids") or []
        if [f for f in cited if f not in facts]:
            why.append("unknown fact ids")
        text = " ".join([str(g.get("answer", ""))] + [f"{c.get('when', '')} {c.get('why', '')}" for c in g.get("chooser", []) or []]
                        + [f"{q.get('q', '')} {q.get('a', '')}" for q in g.get("follow_ups", []) or []])
        nums = unsourced_numbers(text, cited, [], facts, t)
        if nums:
            why.append(f"numbers not in cited facts: {nums[:5]}")
        for c in g.get("chooser", []) or []:
            if c.get("slug") not in in_group[key]:
                why.append(f"chooser slug {c.get('slug')!r} is not a gated page of this group")
        if why:
            failed[key] = why
            continue
        chooser = [{"when": c["when"], "why": c.get("why", ""), "slug": c["slug"], "name": released[c["slug"]]["name"],
                    "url": f"{base}/{c['slug']}"} for c in g.get("chooser", []) or [] if c.get("slug") in released]
        out[key] = {"answer": g["answer"], "chooser": chooser,
                    "follow_ups": [q for q in g.get("follow_ups", []) or [] if q.get("q") and q.get("a")]}
    return out, failed


def output_target(st, proj, a):
    """kit: data/<id>.jsonl for a site-kit directory site. json: plain files for any other stack."""
    out = proj.get("output") or {}
    target = getattr(a, "target", None) or out.get("target") or ("kit" if (st.root / ".sitekit.json").exists() else "json")
    if target not in ("kit", "json"):
        die("output target must be kit or json")
    out_dir = st.root / (getattr(a, "out", None) or out.get("dir") or "geo/out")
    return target, out_dir


def write_json_target(out_dir, tid, t, data, base, gcontent=None):
    """One file per template: released items only, related links limited to released pages."""
    released = [d for d in data if d["released"]]
    url_of = {d["slug"]: d.get("url") or f"{base}/{d['slug']}" for d in released}
    items = []
    for d in released:
        item = {k: v for k, v in d.items() if k != "released"}
        item["url"] = url_of[d["slug"]]
        item["related"] = [x for x in d["related"] if x in url_of]
        item["related_urls"] = [url_of[x] for x in item["related"]]
        items.append(item)
    col = t.get("collection") or {}
    groups = defaultdict(lambda: {"count": 0})
    for d in released:
        if d["group"]:
            g = groups[d["group"]["key"]]
            g.update(d["group"])
            g["count"] += 1
    gcfg = col.get("groups") or {}
    group_list = []
    for key, g in sorted(groups.items()):
        entry = {"key": key, "name": g["name"], "count": g["count"]}
        if gcfg.get("basePath"):
            entry["url"] = f"{gcfg['basePath'].rstrip('/')}/{key}"
            entry["indexable"] = g["count"] >= gcfg.get("minItems", 3)
        if gcontent and key in gcontent:
            entry["content"] = gcontent[key]
        group_list.append(entry)
    doc = {"template": tid, "version": t.get("version", 1), "generated": date.today().isoformat(),
           "adopt": is_adopt(t),
           "collection": {**{k: col[k] for k in ("basePath", "label", "hub", "itemType") if k in col},
                          "labels": {**LABELS, **(t.get("labels") or {})}},
           "groups": group_list, "items": items, "pending": len(data) - len(released)}
    if gcfg:
        doc["collection"]["groups"] = {k: v for k, v in gcfg.items() if k != "by"}
    path = out_dir / f"{tid}.json"
    write_json(path, doc)
    return path


# ---------- scaffold ----------

MODULE = """// Generated by geo_engine.py scaffold from geo/templates/{tid}.json (template v{version}).
// Data: data/{tid}.jsonl, written by geo_engine.py build. Change the template and rebuild instead of
// editing rows; wording patterns live in the template, answers in geo/combos/{tid}.jsonl.
import {{ defineCollection, type Fact }} from '../../kit/directory/types.ts';

interface Row {{
  slug: string;
  name: string;
  title: string;
  h1: string;
  description: string;
  answer: string;
  facts: Fact[];
  group: {{ key: string; name: string }} | null;
  related: string[];
  updated?: string | null;
  released: boolean;
}}

export default defineCollection<Row>({{
  slug: (r) => r.slug,
  name: (r) => r.name,
  title: (r) => r.title,
  h1: (r) => r.h1,
  description: (r) => r.description,
  answer: (r) => r.answer,
  facts: (r) => r.facts,
  group: (r) => r.group,
  related: (r) => r.related,
  updated: (r) => r.updated ?? undefined,
  // Waves: rows of unreleased waves fail the gate; with ungated: 'omit' they are not built at all.
  gate: (r) => (r.released ? {{ indexable: true }} : {{ indexable: false, reason: 'not released yet (geo wave)' }}),
{group_intro}}});
"""


def ts_str(s):
    return json.dumps(s, ensure_ascii=False)


def cmd_scaffold(st, a):
    proj, dims, facts, templates, combos, waves = st.load()
    t = templates.get(a.template)
    if not t:
        die(f"no template {a.template!r} in geo/templates/")
    errs, warns = [], []
    lint_templates({a.template: t}, dims, errs, warns)
    if errs:
        die("; ".join(errs))
    col = t["collection"]
    gi = ""
    if col.get("groups") and col["groups"].get("intro"):
        gi = f"  groupIntro: (_key, name, count) => {ts_str(col['groups']['intro'])}.replace('{{name}}', name).replace('{{count}}', String(count)),\n"
    mod = st.root / "src/site/collections" / f"{a.template}.ts"
    mod.parent.mkdir(parents=True, exist_ok=True)
    mod.write_text(MODULE.format(tid=a.template, version=t.get("version", 1), group_intro=gi))
    written = []
    for name in ("DirectoryItem.astro", "DirectoryGroup.astro"):
        ov = st.root / "src/site/overrides/templates" / name
        if not ov.exists() or a.force_override:
            ov.parent.mkdir(parents=True, exist_ok=True)
            ov.write_text((HERE / name).read_text())
            written.append(str(ov))
    entry = {
        "id": a.template, "label": col["label"], "basePath": col["basePath"], "hub": col["hub"],
        "itemType": col.get("itemType", "Thing"), "pageSize": col.get("pageSize", 100), "ungated": "omit",
    }
    if col.get("groups"):
        g = col["groups"]
        entry["groups"] = {"basePath": g["basePath"], "label": g.get("label", g["by"]), "minItems": g.get("minItems", 3)}
    print(json.dumps({"module": str(mod), "overrides_written": written or "kept existing",
                      "site_config_entry": entry,
                      "next": "add site_config_entry to modules.directory.collections in site.config.ts, "
                              "set seo.registry.mode to 'advisory', then build and npm run check"},
                     ensure_ascii=False, indent=2))


# ---------- snapshots ----------

def page_summary(html):
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    clean = lambda m: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""
    return {"title": clean(title), "h1": clean(h1), "words": len(text.split())}


def cmd_snapshot(st, a):
    proj, dims, facts, templates, combos, waves = st.load()
    t = templates.get(a.template)
    if not t:
        die(f"no template {a.template!r}")
    if not is_adopt(t):
        die("snapshot is for adopt templates: generated pages have no earlier version")
    rows = [r for r in combos.get(a.template, []) if str(r.get("url", "")).startswith("/")][: a.limit]
    day = date.today().isoformat()
    folder = st.geo / "snapshots" / a.template / day
    folder.mkdir(parents=True, exist_ok=True)
    index_rows, failed = [], 0
    for i, r in enumerate(rows):
        url = a.base.rstrip("/") + r["url"]
        req = urllib.request.Request(url, headers={"User-Agent": "site-batch-snapshot/1.0 (+owner's own site)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                status, html = resp.status, resp.read(3_000_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, html = e.code, ""
        except (urllib.error.URLError, TimeoutError) as e:
            status, html = None, ""
        name = re.sub(r"[^a-z0-9]+", "-", r["url"].lower()).strip("-") or "home"
        row = {"date": day, "url": r["url"], "combo_id": r.get("combo_id"), "status": status}
        if html:
            (folder / f"{name}.html").write_text(html)
            row.update(page_summary(html), file=str((folder / f"{name}.html").relative_to(st.root)),
                       sha256=hashlib.sha256(html.encode()).hexdigest()[:16])
        else:
            failed += 1
        index_rows.append(row)
        if a.delay and i < len(rows) - 1:
            time.sleep(a.delay)
    idx = st.geo / "snapshots" / a.template / "index.jsonl"
    write_jsonl(idx, read_jsonl(idx) + index_rows)
    print(json.dumps({"saved": len(index_rows) - failed, "failed": failed, "folder": str(folder)}, ensure_ascii=False, indent=2))


# ---------- questions ----------

def route_level(scope, t):
    dims = set(t.get("dimensions", []))
    gby = (t["collection"].get("groups") or {}).get("by")
    scope = set(scope or [])
    if dims and dims <= scope:
        return "item"
    if gby and gby in scope:
        return "group"
    return "hub"


def cmd_questions(st, a):
    proj, dims, facts, templates, combos, waves = st.load()
    t = templates.get(a.template)
    if not t:
        die(f"no template {a.template!r}")
    samples = [s for s in read_jsonl(st.samples) if all(d in (s.get("combo") or {}) for d in t.get("dimensions", []))]
    if not samples:
        die("no gap samples cover this template's dimensions (geo/gap/samples.jsonl)")
    openings, levels = [], defaultdict(int)
    turns = defaultdict(list)
    for s in samples:
        scope = s.get("opening_scope")
        lvl = route_level(scope, t) if scope is not None else "unknown"   # [] = fixes nothing = hub
        levels[lvl] += 1
        if s.get("opening"):
            openings.append({"combo_id": s["combo_id"], "level": lvl, "scope": scope, "opening": s["opening"]})
        for f in s.get("follow_ups", []) or []:
            if isinstance(f, dict):
                turns[f.get("kind", "other")].append({"q": f.get("q", ""), "combo_id": s["combo_id"], "adds": f.get("adds", [])})
            else:
                turns["unlabelled"].append({"q": f, "combo_id": s["combo_id"]})
    out = {"template": a.template, "samples": len(samples), "levels": dict(levels), "openings": openings,
           "follow_ups_by_kind": {k: v for k, v in sorted(turns.items(), key=lambda kv: -len(kv[1]))},
           "slots": [q.get("id") for q in t.get("question_slots", []) or []],
           "next": "cluster follow-ups by meaning into 5-8 question_slots; item-level openings shape title_source; "
                   "group-level openings become group content (combos/<id>.groups.jsonl); hub-level ones go to the hub intro or off-site"}
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------- status and waves ----------

def cmd_status(st, a):
    proj, dims, facts, templates, waves, result = evaluate(st)
    out = {}
    for tid, r in result.items():
        reasons = Counter(re.sub(r"[:\[(].*", "", f).strip() for e in r["items"] for f in e["failed"])
        out[tid] = {
            "rows": len(r["items"]), "gated": sum(1 for e in r["items"] if not e["failed"]),
            "in_wave": sum(1 for e in r["items"] if e["wave"] is not None),
            "released": sum(1 for e in r["items"] if e["released"] and not e["failed"]),
            "failed_by_reason": dict(reasons.most_common()),
        }
    out["waves"] = [{"id": w["id"], "status": w["status"], "planned": w.get("planned"), "released": w.get("released"),
                     "size": sum(len(v) for v in w.get("combos", {}).values())} for w in waves.get("waves", [])]
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_wave_plan(st, a):
    proj, dims, facts, templates, waves, result = evaluate(st)
    if any(w["status"] == "planned" for w in waves["waves"]):
        die("a planned wave exists: release it or edit geo/waves.json first")
    combos, control = {}, {}
    for tid, r in result.items():
        if a.template and tid != a.template:
            continue
        ready = [e for e in r["items"] if not e["failed"] and e["wave"] is None
                 and (e["control_of"] is None or a.include_control)]
        ready.sort(key=lambda e: (-float(e["row"].get("priority", 0) or 0), e["cid"]))
        if a.control_ratio:
            # Alternate along the priority order so the two groups stay alike: every k-th row is held back.
            k = max(2, round(1 / a.control_ratio))
            take = ready[: round(a.per_template / (1 - 1 / k))]
            pick = [e["cid"] for i, e in enumerate(take) if i % k != k - 1][: a.per_template]
            hold = [e["cid"] for i, e in enumerate(take) if i % k == k - 1]
            if hold:
                control[tid] = hold
        else:
            pick = [e["cid"] for e in ready[: a.per_template]]
        if pick:
            combos[tid] = pick
    if not combos:
        die("nothing to plan: no gated combinations outside earlier waves")
    wid = max([w["id"] for w in waves["waves"]] + [0]) + 1
    wave = {"id": wid, "status": "planned", "planned": date.today().isoformat(),
            "released": None, "combos": combos, "note": a.note or ""}
    if control:
        wave["control"] = control
    waves["waves"].append(wave)
    write_json(st.waves, waves)
    print(json.dumps({"wave": wid, "sizes": {k: len(v) for k, v in combos.items()},
                      "control": {k: len(v) for k, v in control.items()}}, ensure_ascii=False, indent=2))


def cmd_wave_release(st, a):
    waves = read_json(st.waves)
    w = next((w for w in waves["waves"] if w["id"] == a.wave), None)
    if not w:
        die(f"no wave {a.wave}")
    if w["status"] == "released":
        die(f"wave {a.wave} is already released")
    w["status"], w["released"] = "released", a.date or date.today().isoformat()
    write_json(st.waves, waves)
    advance(st, "pages", f"wave {a.wave} released")
    print(json.dumps({"wave": a.wave, "released": w["released"],
                      "next": "geo_engine.py build, then npm run check and the site-kit release steps"}, ensure_ascii=False))


# ---------- measurement ----------

def latest_snapshots(st):
    latest = {}
    for s in read_jsonl(st.snapshots):
        u = s.get("url")
        if u and (u not in latest or s.get("date", "") >= latest[u].get("date", "")):
            latest[u] = s
    return latest


def rate(n, d):
    return round(n / d, 2) if d else None


def cmd_funnel(st, a):
    all_inst = read_jsonl(st.instances)
    inst = [i for i in all_inst if i["gate"]["pass"] and i["released"]]
    if not inst:
        die("no released pages in geo/instances.jsonl: release a wave and build first")
    snaps = latest_snapshots(st)
    groups = defaultdict(list)
    for i in all_inst:
        # Held-back rows of a wave: same kind of page, left as it was (adopt) or not yet published.
        if i.get("control_of") is not None and not i["released"]:
            groups[(i["template"], f"wave {i['control_of']}", "control")].append(i)
    for i in inst:
        groups[(i["template"], "all", "all")].append(i)
        groups[(i["template"], f"wave {i['wave']}", "all")].append(i)
        if i.get("arm"):
            groups[(i["template"], "all", f"arm {i['arm']}")].append(i)
    rows = []
    for (tid, wave, arm), items in sorted(groups.items()):
        measured = [snaps[i["url"]] for i in items if i["url"] in snaps]
        row = {"template": tid, "wave": wave, "arm": arm, "released": len(items), "measured": len(measured)}
        for k in ("crawled", "indexed", "ai_fetch", "cited"):
            known = [s for s in measured if s.get(k) is not None]
            row[k] = rate(sum(1 for s in known if s[k]), len(known))
        row["referrals"] = sum(int(s.get("referrals") or 0) for s in measured)
        rows.append(row)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_prune(st, a):
    snaps = latest_snapshots(st)
    today = date.fromisoformat(a.today) if a.today else date.today()
    out = []
    for i in read_jsonl(st.instances):
        if not (i["gate"]["pass"] and i["released"] and i.get("released_on")):
            continue
        age = (today - date.fromisoformat(i["released_on"])).days
        s = snaps.get(i["url"])
        if age < a.min_days or not s:
            continue
        if s.get("indexed") is False:
            out.append({"url": i["url"], "template": i["template"], "wave": i["wave"], "days": age,
                        "crawled": s.get("crawled"), "suggest": "check links and content first; then merge into a sibling or hub, or noindex"})
    print(json.dumps({"candidates": out, "count": len(out)}, ensure_ascii=False, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint")
    s = sub.add_parser("build")
    s.add_argument("--target", choices=["kit", "json"], help="default: project.json output.target, else kit when .sitekit.json exists, else json")
    s.add_argument("--out", help="json target directory (default geo/out)")
    s = sub.add_parser("scaffold")
    s.add_argument("--template", required=True)
    s.add_argument("--force-override", action="store_true")
    sub.add_parser("status")
    s = sub.add_parser("snapshot")
    s.add_argument("--template", required=True)
    s.add_argument("--base", required=True, help="origin of the live site, e.g. https://example.com")
    s.add_argument("--limit", type=int, default=500)
    s.add_argument("--delay", type=float, default=0.5)
    s = sub.add_parser("questions")
    s.add_argument("--template", required=True)
    s = sub.add_parser("wave-plan")
    s.add_argument("--per-template", type=int, required=True)
    s.add_argument("--control-ratio", type=float, default=0.0, help="share of picked rows held back as control (e.g. 0.5)")
    s.add_argument("--include-control", action="store_true", help="allow rows held back by an earlier wave")
    s.add_argument("--template")
    s.add_argument("--note")
    s = sub.add_parser("wave-release")
    s.add_argument("--wave", type=int, required=True)
    s.add_argument("--date")
    sub.add_parser("funnel")
    s = sub.add_parser("prune")
    s.add_argument("--min-days", type=int, default=28)
    s.add_argument("--today")
    a = p.parse_args(argv)
    st = State(a.root)
    {"lint": cmd_lint, "build": cmd_build, "scaffold": cmd_scaffold, "status": cmd_status, "questions": cmd_questions, "snapshot": cmd_snapshot,
     "wave-plan": cmd_wave_plan, "wave-release": cmd_wave_release, "funnel": cmd_funnel,
     "prune": cmd_prune}[a.cmd](st, a)


if __name__ == "__main__":
    main()
