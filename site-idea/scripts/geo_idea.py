#!/usr/bin/env python3
"""Idea-stage engine for site-idea: demand map, question bank, task space, gap samples, report, decision.

    python3 geo_idea.py --root <project> [--geo-dir geo] <command> [options]

Commands
  init     --name N --idea "one sentence" [--live --origin URL]   create geo/project.json and empty files
  needs    [--quotes FILE]                  validate geo/needs.jsonl (demand map) -> geo/needs.md; with FILE
                                            (CSV/JSONL of url, quote) every off-site quote must be verbatim
  bank                                      validate geo/questions.jsonl (question bank) -> geo/bank.md
  space    [--format text|json]             validate dimensions, count the page space
  sample   --n 40 [--seed 1] [--force]      stratified sample of combinations -> geo/gap/samples.jsonl
           [--from-questions [--include-hypothesis]]   ... or of question-bank rows, spread over needs and angles
           [--pool FILE]                    ... or of candidate rows (existing pages), spread over their strata
  probes                                    render geo/gap/probes.md from filled samples
  report   [--threshold 0.33]               aggregate judged runs -> geo/gap/report.json + report.md
  decide   --verdict go|narrow|stop --by user [--subspace JSON] [--note TEXT] [--without-probes]
  extend   --dimension D --values a,b --by user   open more values of a validated dimension (long tail)
  check                                     validate every geo/ file this skill owns

State lives in <project>/geo/ (contract: references/state.md); --geo-dir names another folder when one
repository holds several GEO projects. This script never contacts an AI service or the web; the model
writes needs, questions, conversations, signals and judgements, the script checks and counts.
Python stdlib only.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import itertools
import json
from pathlib import Path
import random
import re
import sys

SCHEMA = 1
KINDS = {"entity", "task", "constraint"}
GAPS = {
    "generic": "high", "outdated": "high", "unmet_constraint": "high", "no_resource": "high",
    "weak_sources": "medium", "self_made": "medium", "good": "low",
}
VERDICTS = {"go", "narrow", "stop"}
# What a follow-up asks decides where a page answers it (site-batch references/question-mapping.md).
TURN_KINDS = {"constraint", "howto", "why", "compare", "resource", "other"}
STAGES = ["idea", "needs", "space", "gap", "decided"]
ENUM_LIMIT = 200_000
SPACE_WARN = 50_000

# Demand map and question bank (references/demand-map.md, references/question-bank.md).
NEED_LEVELS = {"validated", "derived", "hypothesis"}
QUESTION_LEVELS = {"quoted", "derived", "hypothesis"}
ANGLES = {"recommend", "compare", "problem", "howto", "purchase", "alternative", "constraint", "integrate"}
Q_STAGES = {"exploring", "choosing", "using", "troubleshooting"}
ORIGINS = {"real", "model", "competitor"}
WHERE_ASKED = {"assistant", "search_engine", "site_search", "agent", "product", "forum", "support", "other"}
# Evidence: off-site posts carry a URL; first-party records carry a ref (table or export and window).
OFFSITE_SOURCES = {"forum", "review", "qa", "social", "video", "competitor_page", "web"}
FIRST_PARTY_SOURCES = {"site_search", "api_search", "mcp_search", "search_miss", "feedback", "support",
                       "product_log", "ai_fetch", "ai_referral", "survey"}
COMPETITOR_KINDS = {"library", "video", "game", "generator", "list", "marketplace", "tool", "other"}
# Probe runs: where the project stands in the answer, and what the competitor-probe outcome was.
OWN_STATUS = {"absent", "mentioned", "listed", "first", "excluded"}
OUTCOMES = {"competitor_page", "constraint_unmet", "lists_forums", "no_search", "own_recommended", "other"}
IN_ANSWER = {"mentioned", "listed", "first"}
TOKEN = re.compile(r"[a-z0-9]+")
NEAR_DUP = 0.8
SEARCH_PAGE = re.compile(r"/search\b|/tags?/|[?&](q|query|s|search|term)=", re.I)


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
    def __init__(self, root, geo_dir="geo"):
        self.root = Path(root).resolve()
        self.dir = self.root / geo_dir
        self.rel = geo_dir.strip("/")
        self.project = self.dir / "project.json"
        self.dimensions = self.dir / "dimensions.json"
        self.needs = self.dir / "needs.jsonl"
        self.needs_md = self.dir / "needs.md"
        self.bank = self.dir / "questions.jsonl"
        self.bank_md = self.dir / "bank.md"
        self.competitors = self.dir / "competitors.jsonl"
        self.samples = self.dir / "gap" / "samples.jsonl"
        self.runs = self.dir / "gap" / "runs.jsonl"
        self.raw = self.dir / "gap" / "raw"
        self.probes = self.dir / "gap" / "probes.md"
        self.report_json = self.dir / "gap" / "report.json"
        self.report_md = self.dir / "gap" / "report.md"


def set_stage(proj, stage, note):
    # Later stages belong to site-batch; a report or check after them must not move the stage back.
    order = STAGES + ["blueprint", "pages"]
    cur = proj.get("stage", "idea")
    if stage in order and order.index(stage) > (order.index(cur) if cur in order else -1):
        proj["stage"] = stage
    log = proj.setdefault("log", [])
    # Re-running a check with the same result is not an event: log only what changed.
    if not log or (log[-1].get("stage"), log[-1].get("note")) != (stage, note):
        log.append({"date": date.today().isoformat(), "stage": stage, "note": note})


# ---------- evidence, demand map, question bank ----------

def evidence_errors(ev, where):
    """One evidence item: an off-site post (URL + quote) or a first-party record (ref + q or quote)."""
    if not isinstance(ev, dict):
        return [f"{where}: evidence items are objects"]
    src = ev.get("source")
    url = str(ev.get("url", ""))
    if src in FIRST_PARTY_SOURCES:
        errs = []
        if not ev.get("ref"):
            errs.append(f"{where}: first-party evidence ({src}) needs ref: the table or export and its window")
        if not (ev.get("q") or ev.get("quote") or (ev.get("value") and ev.get("n") is not None)):
            errs.append(f"{where}: first-party evidence ({src}) needs q (the query), quote (the words), "
                        "or value and n (a counted answer option, e.g. a survey choice)")
        return errs
    if src is None or src in OFFSITE_SOURCES:
        errs = []
        if not url.startswith("http"):
            errs.append(f"{where}: off-site evidence needs a URL")
        if not ev.get("quote"):
            errs.append(f"{where}: off-site evidence needs a short real quote")
        return errs
    return [f"{where}: evidence source must be one of {sorted(OFFSITE_SOURCES | FIRST_PARTY_SOURCES)}"]


def signal_errors(sig, where):
    """Sample signals: legacy rows are off-site {url, quote}; rows with a first-party source follow evidence rules."""
    if isinstance(sig, dict) and sig.get("source") in FIRST_PARTY_SOURCES:
        return evidence_errors(sig, where)
    if not str((sig or {}).get("url", "")).startswith("http"):
        return [f"{where}: signal without a URL (first-party signals need a source from {sorted(FIRST_PARTY_SOURCES)})"]
    return []


def first_party(s):
    """First-party signals of a sample: signals with a first-party source, plus legacy site_signals."""
    return [x for x in s.get("signals", []) if isinstance(x, dict) and x.get("source") in FIRST_PARTY_SOURCES] + \
        list(s.get("site_signals", []) or [])


def offsite(s):
    return [x for x in s.get("signals", []) if not (isinstance(x, dict) and x.get("source") in FIRST_PARTY_SOURCES)]


def validate_needs(needs):
    errs, warns, ids = [], [], set()
    for i, n in enumerate(needs, 1):
        nid = n.get("id")
        where = f"needs:{i} ({nid})"
        if not nid or nid in ids:
            errs.append(f"{where}: id missing or duplicated")
        ids.add(nid)
        if not n.get("need"):
            errs.append(f"{where}: need is empty (what the person is trying to get done)")
        if not n.get("personas"):
            errs.append(f"{where}: personas is empty (who has this need)")
        lvl = n.get("evidence_level")
        if lvl not in NEED_LEVELS:
            errs.append(f"{where}: evidence_level must be one of {sorted(NEED_LEVELS)}")
        ev = n.get("evidence") or []
        if lvl in ("validated", "derived") and not ev:
            errs.append(f"{where}: {lvl} needs evidence; with none it is a hypothesis")
        for j, e in enumerate(ev, 1):
            errs += evidence_errors(e, f"{where} evidence {j}")
        bad = set(n.get("where_asked") or []) - WHERE_ASKED
        if bad:
            errs.append(f"{where}: where_asked has unknown places {sorted(bad)} (use {sorted(WHERE_ASKED)})")
        if not n.get("where_asked"):
            warns.append(f"{where}: no where_asked: say where people bring this need (assistant, site_search, forum…)")
        if n.get("count") is not None and not isinstance(n.get("count"), int):
            errs.append(f"{where}: count must be an integer (evidence rows behind the need)")
        cbs = n.get("count_by_source")
        if cbs is not None and not (isinstance(cbs, dict) and all(isinstance(v, int) for v in cbs.values())):
            errs.append(f"{where}: count_by_source maps a source to an integer count, e.g. {{\"forum\": 40}}")
        if n.get("volume") is not None and volume_rows(n["volume"]) is None:
            errs.append(f"{where}: volume is a list of {{ref, what, n}} or a map of metric -> count "
                        "(or metric -> {source: count}); counts are requests, not people")
    return errs, warns, ids


def volume_rows(v):
    """Normalise volume to [(what, total, {source: n})]; None when the shape is wrong.
    Accepts [{"ref", "what", "n"}] or {"metric": n} or {"metric": {"api": n, "web": n}}."""
    num = (int, float)
    if isinstance(v, list):
        out = []
        for x in v:
            if not (isinstance(x, dict) and x.get("ref") and isinstance(x.get("n"), num)):
                return None
            out.append((x.get("what") or x["ref"], x["n"], {}))
        return out
    if isinstance(v, dict):
        out = []
        for k, x in v.items():
            if isinstance(x, num):
                out.append((k, x, {}))
            elif isinstance(x, str) and x.strip():
                out.append((k, x.strip(), {}))   # a described figure, shown as written
            elif isinstance(x, dict) and x and all(isinstance(y, num) for y in x.values()):
                out.append((k, sum(x.values()), x))
            else:
                return None
        return out
    return None


def quote_index(path):
    """url -> list of normalised quotes, from a CSV or JSONL with url and quote fields."""
    import csv
    rows = read_jsonl(path) if path.suffix == ".jsonl" else list(csv.DictReader(path.open()))
    idx = defaultdict(list)
    for r in rows:
        if r.get("url") and r.get("quote"):
            idx[r["url"]].append(norm_quote(r["quote"]))
    return idx


def norm_quote(t):
    t = str(t).replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", t).strip().strip("…").strip().lower()


def unverified_quotes(needs, idx):
    """Off-site quotes that are not a substring of a source row with the same URL."""
    out = []
    for n in needs:
        for e in n.get("evidence") or []:
            if isinstance(e, dict) and str(e.get("url", "")).startswith("http") and e.get("quote"):
                q = norm_quote(e["quote"])
                if not any(q in x for x in idx.get(e["url"], [])):
                    out.append(f"needs {n.get('id')}: quote not found verbatim at {e['url'][:80]}: {e['quote'][:60]!r}")
    return out


def need_summary(needs):
    rows = []
    for n in needs:
        ev = n.get("evidence") or []
        fp = sum(1 for e in ev if isinstance(e, dict) and e.get("source") in FIRST_PARTY_SOURCES)
        rows.append({"id": n.get("id"), "need": n.get("need", ""), "level": n.get("evidence_level"),
                     "personas": n.get("personas") or [], "count": n.get("count"),
                     "count_by_source": n.get("count_by_source") or {}, "volume": volume_rows(n.get("volume") or []) or [],
                     "first_party": fp, "offsite": len(ev) - fp, "where_asked": n.get("where_asked") or []})
    rows.sort(key=lambda r: (-(r["count"] or 0), r["id"] or ""))
    return rows


def needs_md(rows, proj):
    L = [f"# Demand map: {proj.get('name', '')}", "",
         f"{len(rows)} needs; {sum(1 for r in rows if r['level'] == 'validated')} validated, "
         f"{sum(1 for r in rows if r['level'] == 'hypothesis')} hypotheses.", "",
         "Count = evidence rows (quotes, messages, descriptions), not market size; one row may count under "
         "several needs, so counts are not added up. Volume = search or API requests, a different measure, "
         "never added to the count.", "",
         "| Need | Who | Level | Count (by source) | Volume | Evidence (first-party / off-site) | Asked in |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        cnt = "—" if r["count"] is None else str(r["count"])
        if r["count_by_source"]:
            cnt += " (" + ", ".join(f"{k} {v}" for k, v in sorted(r["count_by_source"].items(), key=lambda kv: -kv[1])) + ")"
        vol = "; ".join(f"{what.replace('_', ' ')} " + (f"{total:,}" if not isinstance(total, str) else total) +
                        (" (" + ", ".join(f"{k} {n:,}" for k, n in by.items()) + ")" if by else "")
                        for what, total, by in r["volume"]) or "—"
        L.append(f"| {r['id']}: {r['need']} | {', '.join(r['personas']) or '—'} | {r['level']} | {cnt} | {vol} | "
                 f"{r['first_party']} / {r['offsite']} | {', '.join(r['where_asked']) or '—'} |")
    return "\n".join(L) + "\n"


def cmd_needs(st, a):
    needs = read_jsonl(st.needs)
    if not needs:
        die(f"no needs in {st.needs}: write the demand map first (references/demand-map.md)")
    errs, warns, _ = validate_needs(needs)
    if a.quotes:
        qpath = Path(a.quotes) if Path(a.quotes).is_absolute() else st.root / a.quotes
        if not qpath.exists():
            die(f"no quotes file {qpath}")
        errs += unverified_quotes(needs, quote_index(qpath))
    rows = need_summary(needs)
    proj = read_json(st.project)
    for e in errs:
        print(f"ERROR  {e}")
    for w in warns:
        print(f"WARN   {w}")
    if not errs:
        st.needs_md.write_text(needs_md(rows, proj))
        if any(r["level"] == "validated" for r in rows):
            set_stage(proj, "needs", f"demand map: {len(rows)} needs")
            write_json(st.project, proj)
    print(json.dumps({"errors": len(errs), "needs": len(rows),
                      "validated": sum(1 for r in rows if r["level"] == "validated"),
                      "file": str(st.needs_md) if not errs else None}, ensure_ascii=False))
    sys.exit(1 if errs else 0)


def qtokens(text):
    return set(TOKEN.findall(str(text).lower()))


def brand_terms(proj, competitors):
    terms = [proj.get("name", "")] + [c.get("name", "") for c in competitors] + \
            [str(c.get("domain", "")).split(".")[0] for c in competitors]
    return sorted({t.lower() for t in terms if t and len(t) > 2})


def validate_competitors(rows):
    errs, ids = [], set()
    for i, c in enumerate(rows, 1):
        where = f"competitors:{i} ({c.get('id')})"
        if not c.get("id") or c["id"] in ids:
            errs.append(f"{where}: id missing or duplicated")
        ids.add(c.get("id"))
        if not c.get("name"):
            errs.append(f"{where}: name is required")
        if c.get("kind") not in COMPETITOR_KINDS:
            errs.append(f"{where}: kind must be one of {sorted(COMPETITOR_KINDS)}")
    return errs, ids


def validate_bank(bank, need_ids, comp_ids, dims, proj, competitors):
    errs, warns, ids = [], [], set()
    values = {d["id"]: {v["id"] for v in d.get("values", [])} for d in (dims or {}).get("dimensions", [])}
    brands = brand_terms(proj, competitors)
    for i, q in enumerate(bank, 1):
        qid = q.get("id")
        where = f"questions:{i} ({qid})"
        if not qid or qid in ids:
            errs.append(f"{where}: id missing or duplicated")
        ids.add(qid)
        text = str(q.get("question", ""))
        if not text.strip():
            errs.append(f"{where}: question is empty")
        if need_ids and q.get("need_id") not in need_ids:
            errs.append(f"{where}: need_id {q.get('need_id')!r} is not in needs.jsonl")
        if not q.get("persona"):
            errs.append(f"{where}: persona is empty")
        if q.get("angle") not in ANGLES:
            errs.append(f"{where}: angle must be one of {sorted(ANGLES)}")
        if q.get("stage") not in Q_STAGES:
            errs.append(f"{where}: stage must be one of {sorted(Q_STAGES)}")
        lvl = q.get("evidence_level")
        if lvl not in QUESTION_LEVELS:
            errs.append(f"{where}: evidence_level must be one of {sorted(QUESTION_LEVELS)}")
        if lvl in ("quoted", "derived") and not q.get("evidence"):
            errs.append(f"{where}: {lvl} needs evidence (ids or URLs of what it rests on); with none it is a hypothesis")
        origin = q.get("origin", "model")
        if origin not in ORIGINS:
            errs.append(f"{where}: origin must be one of {sorted(ORIGINS)}")
        if origin == "competitor" and comp_ids and q.get("competitor") not in comp_ids:
            errs.append(f"{where}: competitor {q.get('competitor')!r} is not in competitors.jsonl")
        for f in q.get("follow_ups", []) or []:
            if not isinstance(f, dict) or not f.get("q") or f.get("kind") not in TURN_KINDS:
                errs.append(f"{where}: follow-ups are {{q, kind}} with kind in {sorted(TURN_KINDS)}")
                break
        for k, v in (q.get("combo") or {}).items():
            if values and v not in values.get(k, set()):
                errs.append(f"{where}: combo has unknown {k}={v}")
        low = text.lower()
        named = [b for b in brands if re.search(rf"\b{re.escape(b)}\b", low)]
        if named:
            warns.append(f"{where}: names {named}: probe questions stay unbranded (a branded one measures recall, not choice)")
    # Near-duplicates within a need: the same question reworded is one question.
    by_need = defaultdict(list)
    for q in bank:
        by_need[q.get("need_id")].append(q)
    for nid, qs in by_need.items():
        toks = [(q.get("id"), qtokens(q.get("question", ""))) for q in qs]
        for x in range(len(toks)):
            for y in range(x + 1, len(toks)):
                a, b = toks[x][1], toks[y][1]
                if a and b and len(a & b) / len(a | b) >= NEAR_DUP:
                    warns.append(f"questions {toks[x][0]} and {toks[y][0]} ({nid}) are near-duplicates: keep one")
    # Coverage: angles per need, and a bank that leans on the same three words is a keyword list.
    for nid, qs in by_need.items():
        angles = {q.get("angle") for q in qs}
        if len(angles) < 4:
            warns.append(f"need {nid}: {len(angles)} angles ({', '.join(sorted(a for a in angles if a))}); aim for 4 or more")
    if bank:
        stock = sum(1 for q in bank if qtokens(q.get("question", "")) & {"best", "free", "ai"})
        if stock * 3 > len(bank):
            warns.append(f"{stock}/{len(bank)} questions use best/free/AI: people mostly describe their situation instead")
    return errs, warns


def bank_md(bank, needs, proj):
    angles = sorted(ANGLES)
    by_need = defaultdict(Counter)
    levels = defaultdict(Counter)
    for q in bank:
        by_need[q.get("need_id")][q.get("angle")] += 1
        levels[q.get("need_id")][q.get("evidence_level")] += 1
    names = {n.get("id"): n.get("need", "") for n in needs}
    L = [f"# Question bank: {proj.get('name', '')}", "",
         f"{len(bank)} questions over {len(by_need)} needs. Model-written questions are hypotheses until a real "
         "source or a probe shows the same wording; none of them is presented as a real user's question.", "",
         "| Need | " + " | ".join(angles) + " | quoted / derived / hypothesis |",
         "| --- | " + " | ".join("---" for _ in angles) + " | --- |"]
    for nid in sorted(by_need, key=str):
        c, lv = by_need[nid], levels[nid]
        label = f"{nid}: {names.get(nid, '')}".strip(": ")
        L.append(f"| {label} | " + " | ".join(str(c.get(x, 0) or "") for x in angles) +
                 f" | {lv.get('quoted', 0)} / {lv.get('derived', 0)} / {lv.get('hypothesis', 0)} |")
    return "\n".join(L) + "\n"


def cmd_bank(st, a):
    bank = read_jsonl(st.bank)
    if not bank:
        die(f"no questions in {st.bank}: write the question bank first (references/question-bank.md)")
    proj = read_json(st.project)
    needs = read_jsonl(st.needs)
    competitors = read_jsonl(st.competitors)
    cerrs, comp_ids = validate_competitors(competitors)
    dims = read_json(st.dimensions, {"dimensions": []})
    errs, warns = validate_bank(bank, {n.get("id") for n in needs}, comp_ids, dims, proj, competitors)
    errs = cerrs + errs
    for e in errs:
        print(f"ERROR  {e}")
    for w in warns:
        print(f"WARN   {w}")
    if not errs:
        st.bank_md.write_text(bank_md(bank, needs, proj))
    lv = Counter(q.get("evidence_level") for q in bank)
    print(json.dumps({"errors": len(errs), "warnings": len(warns), "questions": len(bank), "levels": dict(lv),
                      "angles": dict(Counter(q.get("angle") for q in bank)),
                      "file": str(st.bank_md) if not errs else None}, ensure_ascii=False))
    sys.exit(1 if errs else 0)


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
        "site": {"live": bool(a.live), "origin": a.origin or ""},
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


def spread(groups, n, rng):
    """Round-robin over groups (each already in preference order) until n rows are taken."""
    keys = sorted(groups, key=str)
    rng.shuffle(keys)
    queues = {k: list(groups[k]) for k in keys}
    out = []
    while len(out) < n and any(queues.values()):
        for k in keys:
            if queues[k] and len(out) < n:
                out.append(queues[k].pop(0))
    return out


def sample_from_questions(st, a, dims):
    """Samples are bank questions, spread over needs and angles, real wording first."""
    bank = read_jsonl(st.bank)
    if not bank:
        die(f"no questions in {st.bank}: write the question bank first")
    order = {"quoted": 0, "derived": 1, "hypothesis": 2}
    pool = [q for q in bank if a.include_hypothesis or q.get("evidence_level") != "hypothesis"]
    if not pool:
        die("every question is a hypothesis: add evidence, or pass --include-hypothesis")
    rng = random.Random(a.seed)
    groups = defaultdict(list)
    for q in sorted(pool, key=lambda q: (order.get(q.get("evidence_level"), 3), rng.random())):
        groups[(q.get("need_id"), q.get("angle"))].append(q)
    rows = []
    for q in spread(groups, a.n, rng):
        rows.append({"combo_id": q["id"], "combo": q.get("combo") or {}, "question_id": q["id"],
                     "need_id": q.get("need_id"), "angle": q.get("angle"), "persona": q.get("persona", ""),
                     "opening": q.get("question", ""), "opening_scope": q.get("scope"),
                     "follow_ups": q.get("follow_ups") or [], "conditions": q.get("conditions") or [],
                     "evidence_level": q.get("evidence_level"), "signals": []})
    write_jsonl(st.samples, rows)
    covered = {r["need_id"] for r in rows}
    out = {"samples": len(rows), "file": str(st.samples), "from": "questions",
           "needs_uncovered": sorted({str(q.get("need_id")) for q in bank} - {str(c) for c in covered}),
           "levels": dict(Counter(r["evidence_level"] for r in rows))}
    print(json.dumps(out, ensure_ascii=False, indent=2))


def sample_from_pool(st, a, dims):
    """Samples are candidate rows (existing pages), spread over their strata (e.g. traffic tiers)."""
    path = Path(a.pool)
    if not path.is_absolute():
        path = st.root / path
    pool = read_jsonl(path)
    if not pool:
        die(f"no rows in {path}")
    gen = generating(dims)
    values = {d["id"]: {v["id"] for v in d["values"]} for d in gen}
    rng = random.Random(a.seed)
    groups, seen = defaultdict(list), set()
    for p in pool:
        combo = p.get("combo") or {}
        if set(combo) != set(values) or any(combo[k] not in values[k] for k in combo):
            die(f"pool row {p} must set every generating dimension to a known value")
        cid = combo_id(combo, gen)
        if cid in seen:
            continue
        seen.add(cid)
        groups[p.get("stratum", "all")].append({**p, "combo_id": cid})
    for g in groups.values():
        rng.shuffle(g)
    rows = []
    for p in spread(groups, a.n, rng):
        r = {"combo_id": p["combo_id"], "combo": p["combo"], "stratum": p.get("stratum", "all"), "persona": "",
             "opening": "", "opening_scope": None, "follow_ups": [], "signals": []}
        if p.get("url"):
            r["url"] = p["url"]
        rows.append(r)
    write_jsonl(st.samples, rows)
    print(json.dumps({"samples": len(rows), "file": str(st.samples), "from": "pool",
                      "strata": dict(Counter(r["stratum"] for r in rows))}, ensure_ascii=False, indent=2))


def cmd_sample(st, a):
    dims = read_json(st.dimensions, {"dimensions": []} if a.from_questions else None)
    if st.samples.exists() and read_jsonl(st.samples) and not a.force:
        die(f"{st.samples} has rows; --force replaces it (filled conversations are lost)")
    if a.from_questions:
        return sample_from_questions(st, a, dims)
    errs, _ = validate_dimensions(dims)
    if errs:
        die("fix dimensions first: " + "; ".join(errs))
    if a.pool:
        return sample_from_pool(st, a, dims)
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
                     "opening_scope": None, "follow_ups": [], "signals": []})
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
        "Paste the whole answer (all turns, with links) into the file named under each conversation.",
        "When the browser allows it, also save the search queries the assistant ran (site-geo "
        "references/chatgpt-probes.md, section D); otherwise write 'queries: not captured'.", "",
    ]
    for r in rows:
        lines += [f"## {r['combo_id']}", "", f"Persona: {r.get('persona', '')}", "", "Opening:", "",
                  "> " + r["opening"].replace("\n", "\n> "), ""]
        for i, f in enumerate(r.get("follow_ups", []), 1):
            f = f.get("q", "") if isinstance(f, dict) else f
            lines += [f"Follow-up {i}: {f}", ""]
        files = ", ".join(f"`{st.rel}/gap/raw/{r['combo_id']}--{p.lower().replace(' ', '-')}--1.md`" for p in platforms)
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
                       "runs": len(by_combo.get(s["combo_id"], [])), "signals": len(offsite(s)),
                       "first_party": len(first_party(s))})
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
    by_sample = {s["combo_id"]: s for s in samples}
    level_of = {c["combo_id"]: c["level"] for c in combos}
    presence = build_presence(runs)
    groups = {}
    for key in ("need_id", "stratum", "angle"):
        g = defaultdict(lambda: {"probed": 0, "high": 0, "runs": 0, "in_answer": 0, "own_measured": 0})
        for s in samples:
            if s.get(key) is None or level_of.get(s["combo_id"], "unprobed") == "unprobed":
                continue
            row = g[s[key]]
            row["probed"] += 1
            row["high"] += level_of[s["combo_id"]] == "high"
        for r in runs:
            s = by_sample.get(r.get("combo_id"))
            if not s or s.get(key) is None or r.get("gap") not in GAPS:
                continue
            row = g[s[key]]
            row["runs"] += 1
            if r.get("own") in OWN_STATUS:
                row["own_measured"] += 1
                row["in_answer"] += r["own"] in IN_ANSWER
        if g:
            groups[key] = {k: {**v, "share_high": round(v["high"] / v["probed"], 2) if v["probed"] else None,
                               "own_in_answer": round(v["in_answer"] / v["own_measured"], 2) if v["own_measured"] else None}
                           for k, v in sorted(g.items(), key=lambda kv: str(kv[0]))}
    notes = []
    if presence["measured"]:
        if presence["in_answer_share"] < 0.25 and presence["lever_hint"] in ("offsite", "consensus"):
            notes.append(f"own site in {presence['in_answer_share']:.0%} of answers and the answers rest on "
                         f"{presence['lever_hint']} sources: pages alone are unlikely to change who gets "
                         "recommended; plan site-offsite (GEO mode) alongside or instead")
        elif presence["in_answer_share"] < 0.25:
            notes.append(f"own site in {presence['in_answer_share']:.0%} of answers: a gap is an opening for "
                         "the content, not proof the assistant will find the pages; check the captured "
                         "search queries against where the site ranks")
    else:
        notes.append("own presence not recorded (runs have no 'own'): the report shows answer gaps only, "
                     "not whether the assistant would pick this site")
    if presence["lever_hint"] == "onsite" and (presence["competitor_search_page_share"] or 0) >= 0.5:
        notes.append(f"{presence['competitor_search_page_share']:.0%} of the competitor pages cited are search or "
                     "tag result pages: they win on catalogue size and retrieval, so 'onsite' here means being "
                     "found for those queries (titles, indexing, off-site), not only a better page")
    if presence["self_made"]:
        notes.append(f"{presence['self_made']} runs: the assistant made the asset itself (self_made); "
                     "that is competition the page must beat on quality or conditions")
    return {
        "threshold": threshold, "samples": len(samples), "probed": len(probed), "high": len(high),
        "share_high": share, "with_signals": sum(1 for c in probed if c["signals"]),
        "with_first_party": sum(1 for c in probed if c.get("first_party")),
        "levels": dict(Counter(c["level"] for c in combos)),
        "platform_runs": dict(platforms), "dates": sorted(dates),
        "hint": hint, "strong_values": strong, "values": values, "combos": combos,
        "presence": presence, "groups": groups, "notes": notes,
    }


def build_presence(runs):
    """Where the project stood in the judged answers, what was recommended instead, and on what sources."""
    judged = [r for r in runs if r.get("gap") in GAPS]
    own = [r for r in judged if r.get("own") in OWN_STATUS]
    status = Counter(r["own"] for r in own)
    recommended = Counter(n for r in judged for n in (r.get("recommended") or []))
    cited_own = sum(1 for r in own if r.get("cited_own") or r.get("own_urls"))
    captured = [r for r in judged if isinstance(r.get("search_queries"), list)]
    queries = Counter(q for r in captured for q in r["search_queries"])
    # Source mix where the project is not in the answer: decides on-site versus off-site work
    # (site-geo references/optimize.md, source diagnosis).
    mix = Counter()
    for r in judged:
        if r.get("own") in IN_ANSWER:
            continue
        if r.get("web_search") is False or not r.get("cited"):
            mix["none"] += 1
            continue
        types = Counter((c or {}).get("type", "other") for c in r["cited"])
        top = types.most_common(1)[0][0]
        mix["competitor" if top in ("competitor", "brand") else "lists_forums" if top in ("list", "forum", "video") else "other"] += 1
    # A competitor winning with its search-result or tag pages wins on catalogue size and retrieval,
    # not on one page's content: a better page alone will not take that place.
    comp_urls = [str((c or {}).get("url", "")) for r in judged if r.get("own") not in IN_ANSWER
                 for c in r.get("cited") or [] if (c or {}).get("type") in ("competitor", "brand")]
    listing = sum(1 for u in comp_urls if SEARCH_PAGE.search(u))
    total = sum(mix.values())
    lever = None
    if total:
        top, n = mix.most_common(1)[0]
        lever = {"competitor": "onsite", "lists_forums": "offsite", "none": "consensus", "other": "mixed"}[top]
        if n * 2 < total:
            lever = "mixed"
    return {
        "measured": len(own), "status": dict(status),
        "in_answer_share": round(sum(status[s] for s in IN_ANSWER) / len(own), 2) if own else None,
        "first_share": round(status["first"] / len(own), 2) if own else None,
        "cited_own_share": round(cited_own / len(own), 2) if own else None,
        "recommended": recommended.most_common(12),
        "queries_captured": len(captured), "top_queries": queries.most_common(15),
        "source_mix_without_us": dict(mix), "lever_hint": lever,
        "competitor_search_page_share": round(listing / len(comp_urls), 2) if comp_urls else None,
        "outcomes": dict(Counter(r.get("outcome") for r in judged if r.get("outcome"))),
        "self_made": sum(1 for r in judged if r.get("gap") == "self_made"),
    }


def report_md(rep, proj):
    L = [f"# Gap report: {proj.get('name', '')}", "",
         f"Hint (the decision is the owner's): **{rep['hint']}**. "
         f"{rep['high']} of {rep['probed']} probed combinations show a high-opportunity gap "
         f"({rep['share_high']:.0%}; threshold {rep['threshold']:.0%}). "
         f"{rep['with_signals']} of the probed combinations have outside evidence, "
         f"{rep['with_first_party']} have first-party evidence.", "",
         f"Runs by platform: {', '.join(f'{k} {v}' for k, v in rep['platform_runs'].items()) or 'none'}. "
         f"Dates: {', '.join(rep['dates']) or 'none'}. AI answers are samples, not rankings.", ""]
    p = rep.get("presence") or {}
    L += ["## Is the site in the answer", ""]
    if p.get("measured"):
        st = p["status"]
        L += [f"Over {p['measured']} judged runs with `own` recorded: in the answer {p['in_answer_share']:.0%} "
              f"(first {p['first_share']:.0%}, own page cited {p['cited_own_share']:.0%}); "
              + ", ".join(f"{k} {st.get(k, 0)}" for k in ("first", "listed", "mentioned", "excluded", "absent")) + ".", ""]
    else:
        L += ["Not recorded: add `own` to each run (gap-rubric.md, presence).", ""]
    if p.get("recommended"):
        L += ["Recommended in the answers: " + ", ".join(f"{n} {c}" for n, c in p["recommended"]) + ".", ""]
    if p.get("source_mix_without_us"):
        L += ["Sources behind answers without the site: " +
              ", ".join(f"{k} {v}" for k, v in p["source_mix_without_us"].items()) +
              f". Lever hint: **{p['lever_hint']}** (site-geo optimize, source diagnosis).", ""]
    if p.get("outcomes"):
        L += ["Competitor-probe outcomes: " + ", ".join(f"{k} {v}" for k, v in p["outcomes"].items()) + ".", ""]
    L += [f"Search queries captured in {p.get('queries_captured', 0)} runs" +
          (": " + "; ".join(f"`{q}` ({n})" for q, n in p["top_queries"]) if p.get("top_queries") else "") + ".", ""]
    if rep.get("notes"):
        L += ["## Read before deciding", ""] + [f"- {n}" for n in rep["notes"]] + [""]
    for key, title in (("need_id", "By need"), ("angle", "By angle"), ("stratum", "By stratum")):
        g = (rep.get("groups") or {}).get(key)
        if not g:
            continue
        L += [f"## {title}", "", "| Value | Probed | High | Share high | Site in answer |", "| --- | --- | --- | --- | --- |"]
        for k, v in g.items():
            sh = f"{v['share_high']:.0%}" if v["share_high"] is not None else "—"
            oa = f"{v['own_in_answer']:.0%} of {v['own_measured']}" if v["own_in_answer"] is not None else "—"
            L.append(f"| {k} | {v['probed']} | {v['high']} | {sh} | {oa} |")
        L.append("")
    if rep["values"]:
        L += ["## By dimension value", "", "| Value | Probed | High | Share high | With signals |",
              "| --- | --- | --- | --- | --- |"]
        for v in rep["values"]:
            L.append(f"| {v['value']} | {v['probed']} | {v['high']} | {v['share_high']:.0%} | {v['signals']} |")
        L.append("")
    L += ["## Combinations", "", "| Combination | Level | Runs | Signals | First-party |", "| --- | --- | --- | --- | --- |"]
    order = {"high": 0, "medium": 1, "low": 2, "unprobed": 3}
    for c in sorted(rep["combos"], key=lambda c: (order[c["level"]], c["combo_id"])):
        L.append(f"| {c['combo_id']} | {c['level']} | {c['runs']} | {c['signals']} | {c.get('first_party', 0)} |")
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
    out = {k: rep[k] for k in ("probed", "high", "share_high", "hint", "strong_values", "notes")}
    out.update({k: rep["presence"][k] for k in ("in_answer_share", "first_share", "lever_hint", "queries_captured")})
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_decide(st, a):
    if a.verdict not in VERDICTS:
        die(f"verdict must be one of {sorted(VERDICTS)}")
    if a.by != "user":
        die("the decision is the owner's: pass --by user only after they said it in chat")
    if a.without_probes:
        return decide_without_probes(st, a)
    if not st.report_json.exists():
        die("no gap report: run report first (or --without-probes on first-party evidence)")
    proj = read_json(st.project)
    sub = subspace_arg(st, a)
    rep = read_json(st.report_json)
    if not rep.get("probed"):
        die("the gap report has no judged runs: probe and judge before deciding")
    pres = rep.get("presence") or {}
    proj["decision"] = {"verdict": a.verdict, "date": date.today().isoformat(), "by": "user",
                        "subspace": sub, "note": a.note or "",
                        "evidence": {"probed": rep["probed"], "share_high": rep["share_high"], "hint": rep["hint"],
                                     "in_answer_share": pres.get("in_answer_share"), "lever_hint": pres.get("lever_hint")},
                        "dimensions": [d["id"] for d in generating(read_json(st.dimensions))],
                        "extensions": []}
    set_stage(proj, "decided", f"decision {a.verdict}")
    write_json(st.project, proj)
    print(json.dumps(proj["decision"], ensure_ascii=False, indent=2))


def subspace_arg(st, a):
    sub = json.loads(a.subspace) if a.subspace else None
    if a.verdict == "narrow" and not sub:
        die("narrow needs --subspace, e.g. '{\"source\": [\"heic\", \"png\"]}'")
    if sub:
        dims = {d["id"]: {v["id"] for v in d["values"]} for d in read_json(st.dimensions)["dimensions"]}
        for k, vs in sub.items():
            if k not in dims or not set(vs) <= dims[k]:
                die(f"subspace names unknown dimension or values: {k}={vs}")
    return sub


def decide_without_probes(st, a):
    """A decision on first-party demand alone (site search, agent queries, feedback), when the owner
    chooses not to make AI probes a precondition. The demand map must have validated needs."""
    needs = read_jsonl(st.needs)
    errs, _, _ = validate_needs(needs)
    if errs:
        die("fix needs.jsonl first: " + "; ".join(errs[:3]))
    validated = [n for n in needs if n.get("evidence_level") == "validated"]
    if not validated:
        die("--without-probes needs validated needs in needs.jsonl (real evidence behind them)")
    dims = read_json(st.dimensions)
    derr, _ = validate_dimensions(dims)
    if derr:
        die("fix dimensions first: " + "; ".join(derr))
    proj = read_json(st.project)
    sub = subspace_arg(st, a)
    rep = read_json(st.report_json, {})
    proj["decision"] = {"verdict": a.verdict, "date": date.today().isoformat(), "by": "user",
                        "subspace": sub, "note": a.note or "",
                        "evidence": {"basis": "first-party demand", "needs_validated": len(validated),
                                     "probed": rep.get("probed", 0), "share_high": rep.get("share_high"),
                                     "hint": rep.get("hint")},
                        "dimensions": [d["id"] for d in generating(dims)], "extensions": []}
    set_stage(proj, "decided", f"decision {a.verdict} on first-party demand")
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
    dims = read_json(st.dimensions, {"dimensions": [], "exclude": []})
    # Before the task space exists (demand map and question bank only), empty dimensions are fine.
    if dims.get("dimensions") or proj.get("stage") not in ("idea", "needs"):
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
        for k in s.get("opening_scope", []) or []:
            if k not in values:
                errs.append(f"samples: {s.get('combo_id')}: opening_scope names unknown dimension {k!r}")
        for f in s.get("follow_ups", []) or []:
            if isinstance(f, dict):
                if not f.get("q"):
                    errs.append(f"samples: {s.get('combo_id')}: follow-up without q")
                if f.get("kind") not in TURN_KINDS:
                    errs.append(f"samples: {s.get('combo_id')}: follow-up kind must be one of {sorted(TURN_KINDS)}")
        for sig in s.get("signals", []):
            errs += [f"samples: {s.get('combo_id')}: {e}" for e in signal_errors(sig, "signal")]
        for sig in s.get("site_signals", []) or []:
            if not (isinstance(sig, dict) and (sig.get("q") or sig.get("quote"))):
                errs.append(f"samples: {s.get('combo_id')}: site_signals need q or quote")
    if st.needs.exists():
        nerr, _, need_ids = validate_needs(read_jsonl(st.needs))
        errs += nerr
    else:
        need_ids = set()
    competitors = read_jsonl(st.competitors)
    cerr, comp_ids = validate_competitors(competitors)
    errs += cerr
    if st.bank.exists():
        berr, _ = validate_bank(read_jsonl(st.bank), need_ids, comp_ids, dims, proj, competitors)
        errs += berr
    for s in samples:
        if need_ids and s.get("need_id") is not None and s["need_id"] not in need_ids:
            errs.append(f"samples: {s.get('combo_id')}: need_id {s['need_id']!r} is not in needs.jsonl")
    for i, r in enumerate(read_jsonl(st.runs), 1):
        where = f"runs:{i}"
        if r.get("combo_id") not in sample_ids:
            errs.append(f"{where}: combo_id {r.get('combo_id')!r} is not a sample")
        if r.get("gap") is not None and r.get("gap") not in GAPS:
            errs.append(f"{where}: gap must be one of {sorted(GAPS)} or null")
        if r.get("own") is not None and r.get("own") not in OWN_STATUS:
            errs.append(f"{where}: own must be one of {sorted(OWN_STATUS)} or null")
        if r.get("outcome") is not None and r.get("outcome") not in OUTCOMES:
            errs.append(f"{where}: outcome must be one of {sorted(OUTCOMES)} or null")
        sq = r.get("search_queries")
        if sq is not None and not (isinstance(sq, list) and all(isinstance(q, str) for q in sq)):
            errs.append(f"{where}: search_queries is a list of strings, or null when not captured")
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
    p.add_argument("--geo-dir", default="geo", help="state folder under the root (default geo)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--name", required=True)
    s.add_argument("--idea", required=True)
    s.add_argument("--live", action="store_true", help="the site is already live (new page space on a live site)")
    s.add_argument("--origin", help="the live site's origin, e.g. https://example.com")
    s = sub.add_parser("needs")
    s.add_argument("--quotes", help="CSV or JSONL of the collected off-site posts (url, quote): every off-site "
                                    "quote in needs.jsonl must appear verbatim under its URL")
    sub.add_parser("bank")
    s = sub.add_parser("space")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s = sub.add_parser("sample")
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--force", action="store_true")
    s.add_argument("--from-questions", action="store_true", help="sample question-bank rows instead of combinations")
    s.add_argument("--include-hypothesis", action="store_true", help="with --from-questions: allow hypothesis questions")
    s.add_argument("--pool", help="JSONL of candidate rows {combo, url?, stratum?}: sample them, spread over strata")
    sub.add_parser("probes")
    s = sub.add_parser("report")
    s.add_argument("--threshold", type=float, default=0.33)
    s = sub.add_parser("decide")
    s.add_argument("--verdict", required=True)
    s.add_argument("--by", required=True)
    s.add_argument("--subspace")
    s.add_argument("--note")
    s.add_argument("--without-probes", action="store_true",
                   help="decide on first-party demand (validated needs) when the owner does not make probes a precondition")
    s = sub.add_parser("extend")
    s.add_argument("--dimension", required=True)
    s.add_argument("--values", required=True, help="comma-separated value ids already in dimensions.json")
    s.add_argument("--by", required=True)
    s.add_argument("--note")
    sub.add_parser("check")
    a = p.parse_args(argv)
    st = State(a.root, a.geo_dir)
    {"init": cmd_init, "needs": cmd_needs, "bank": cmd_bank, "space": cmd_space, "sample": cmd_sample,
     "probes": cmd_probes, "report": cmd_report, "decide": cmd_decide, "extend": cmd_extend,
     "check": cmd_check}[a.cmd](st, a)


if __name__ == "__main__":
    main()
