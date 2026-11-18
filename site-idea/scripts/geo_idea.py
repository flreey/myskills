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
  report   [--threshold 0.33] [--where KEY=VALUE]... [--include-extra]
                                            aggregate judged runs -> geo/gap/report.json + report.md;
                                            --where filters runs by a field (slice=chatgpt-instant);
                                            gap/runs-*.jsonl are extra sets, reported apart unless --include-extra
  decide   --verdict go|narrow|stop --by user [--subspace JSON] [--note TEXT] [--without-probes]
  extend   --dimension D --values a,b --by user   open more values of a validated dimension (long tail)
  check                                     validate every geo/ file this skill owns
  queries                                   group the assistants' search queries -> geo/gap/queries.jsonl / .md
  slots    [--from <export>]...             search words against the dimensions -> geo/gap/slots.md / .json

State lives in <project>/geo/ (contract: references/state.md); --geo-dir names another folder when one
repository holds several GEO projects. This script never contacts an AI service or the web; the model
writes needs, questions, conversations, signals and judgements, the script checks and counts.
Python stdlib only.
"""
import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from datetime import date
import itertools
import json
from pathlib import Path
import random
import re
import sys

SCHEMA = 1
KINDS = {"capability", "entity", "task", "constraint"}
GAPS = {
    "generic": "high", "outdated": "high", "unmet_constraint": "high", "no_resource": "high",
    "weak_sources": "medium", "self_made": "medium", "good": "low",
}
VERDICTS = {"go", "narrow", "stop"}
# Need x channel table (gap/channels.md): one lever cell per need, chosen with the owner.
LEVERS = {"pages", "offsite", "product", "not-now"}
GOAL_FILE = "geo-goal.md"   # one goal card per site, at the project root (site skill, step 0)
THIN_NEED_RUNS = 8
THIN_TOTAL = 25
# Below this share of answers naming the site, pages need a stated reason (site rule 2: page levers
# rest on whether the assistant picks us, not on the gap alone).
PRESENCE_LINE = 0.25
# Combination samples: share whose opening asks for a tool, site or app (angle `recommend`); the rest
# start from the problem. With none, the probes measure the answer, never whether a tool gets picked.
TOOL_SHARE = 0.33
# A capability space (what the product can do x the conditions that change who qualifies) serves
# choosing conversations, so most of its openings ask for a tool, file, app or service.
TOOL_SHARE_CAPABILITY = 0.67
# Words that do not separate one search from another when grouping the assistants' queries.
QUERY_STOP = {"a", "an", "the", "for", "to", "of", "in", "on", "and", "or", "with", "how", "my", "is", "can",
              "i", "you", "best", "top", "vs", "what", "which", "do", "does", "it", "that", "your", "online",
              # added by assistants when they look a product up, not by the person
              "official", "documentation", "docs", "help", "center", "site", "support"}

VALUE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
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
OUTCOMES = {"competitor_page", "constraint_unmet", "lists_forums", "no_search", "own_recommended",
            "generic_rules", "other"}
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
        self.extra_runs = sorted((self.dir / "gap").glob("runs-*.jsonl"))
        self.raw = self.dir / "gap" / "raw"
        self.probes = self.dir / "gap" / "probes.md"
        self.report_json = self.dir / "gap" / "report.json"
        self.report_md = self.dir / "gap" / "report.md"
        self.channels = self.dir / "gap" / "channels.md"
        self.queries = self.dir / "gap" / "queries.jsonl"
        self.queries_md = self.dir / "gap" / "queries.md"
        self.slots_json = self.dir / "gap" / "slots.json"
        self.slots_md = self.dir / "gap" / "slots.md"
        self.goal = self.root / GOAL_FILE
        # A second need space on the same site shares the first one's demand map (init --needs-from).
        nf = read_json(self.project, {}).get("needs_from") if self.project.exists() else None
        if nf:
            self.needs = self.root / nf / "needs.jsonl"


def set_stage(proj, stage, note):
    # Later stages belong to site-batch; a report or check after them must not move the stage back.
    order = STAGES + ["blueprint", "pages"]
    cur = proj.get("stage", "idea")
    advanced = stage in order and order.index(stage) > (order.index(cur) if cur in order else -1)
    if advanced:
        proj["stage"] = stage
    # A step re-run behind the current stage is logged as a check, so the log never reads as a step back.
    if not advanced and stage != cur:
        stage, note = "check", f"{stage} re-run: {note}"
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
    if isinstance(sig, dict) and sig.get("ref") and not sig.get("url") and not sig.get("source"):
        return []  # a bare reference to evidence checked elsewhere (from `sample --from-questions`)
    if not str((sig or {}).get("url", "")).startswith("http"):
        return [f"{where}: signal without a URL (first-party signals need a source from {sorted(FIRST_PARTY_SOURCES)})"]
    return []


def first_party(s):
    """First-party signals of a sample: signals with a first-party source, plus legacy site_signals."""
    return [x for x in s.get("signals", []) if isinstance(x, dict) and x.get("source") in FIRST_PARTY_SOURCES] + \
        list(s.get("site_signals", []) or [])


def offsite(s):
    return [x for x in s.get("signals", []) if not (isinstance(x, dict) and (
        x.get("source") in FIRST_PARTY_SOURCES or (x.get("ref") and not x.get("url"))))]


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


def registrable(domain):
    """The name part of a domain: app.cinevva.com -> cinevva, itch.io -> itch."""
    host = re.sub(r"^[a-z]+://", "", str(domain or "").lower()).split("/")[0]
    parts = [p for p in host.split(".") if p]
    return parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")


def brand_terms(proj, competitors):
    """Names a probe question must not carry: ours (project name, site domain, `brands`) and each competitor's
    (name, domain, `aliases`), minus project `allowed_names` (platforms whose name changes the answer)."""
    terms = [proj.get("name", ""), registrable((proj.get("site") or {}).get("origin", ""))]
    terms += list(proj.get("brands") or [])
    for c in competitors:
        terms += [c.get("name", ""), registrable(c.get("domain", ""))] + list(c.get("aliases") or [])
    allowed = set()
    for t in proj.get("allowed_names") or []:
        allowed |= {str(t).lower(), registrable(t)} if "." in str(t) else {str(t).lower()}
    return sorted({str(t).lower() for t in terms if t and len(str(t)) > 2} - allowed)


EVIDENCE_REF = re.compile(r"([a-z0-9][\w-]*)#e(\d+)")


def evidence_ref_errors(refs, evidence_counts, where):
    """`<need_id>#e<N>` points at the Nth (1-based) evidence row of that need in needs.jsonl."""
    errs = []
    for e in refs or []:
        m = EVIDENCE_REF.fullmatch(str(e).strip())
        if not m:
            continue
        nid, i = m.group(1), int(m.group(2))
        if nid not in evidence_counts:
            errs.append(f"{where}: evidence {e!r} names need {nid!r}, which is not in needs.jsonl")
        elif not 1 <= i <= evidence_counts[nid]:
            errs.append(f"{where}: evidence {e!r} is out of range ({nid} has {evidence_counts[nid]} evidence rows)")
    return errs


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


def validate_bank(bank, needs, comp_ids, dims, proj, competitors):
    errs, warns, ids = [], [], set()
    need_ids = {n.get("id") for n in needs}
    ev_counts = {n.get("id"): len(n.get("evidence") or []) for n in needs}
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
        if lvl == "hypothesis" and q.get("evidence"):
            warns.append(f"{where}: a hypothesis with evidence: raise it to derived, or drop the evidence")
        if needs:
            errs += evidence_ref_errors(q.get("evidence"), ev_counts, where)
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
    errs, warns = validate_bank(bank, needs, comp_ids, dims, proj, competitors)
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

def space_shape(dims):
    """`capability` when a generating dimension is what the product can do (choosing conversations),
    else `situation` (the user's circumstances; how-to conversations)."""
    return "capability" if any(d.get("kind") == "capability" for d in generating(dims)) else "situation"


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
        odd = [v for v in vids if v and not VALUE_ID.match(v)]
        if odd:
            warns.append(f"{did}: {len(odd)} value ids are not slugs (lowercase, digits, . _ -), e.g. {odd[0][:60]!r}")
        if d.get("assets") is not None:
            ast = d["assets"]
            if not (isinstance(ast, dict) and ast.get("needs") and isinstance(ast.get("have", 0), (int, str))):
                errs.append(f"{did}: assets is {{needs, have, source}}: what one page needs, how many values or "
                            "combinations have it today (number or text), and where that count comes from")
        if not d.get("source"):
            warns.append(f"{did}: no 'source' for its values (where the list comes from)")
        if d.get("kind") == "capability" and d.get("changes_answer") and d.get("assets") is None:
            warns.append(f"{did}: a capability dimension states no assets: name the proof each value has "
                         "(a test output, the file, a measured result) so pages claim only what the product does")
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
    if gen and not kinds & {"entity", "task", "capability"}:
        warns.append("only constraint dimensions generate pages: check that an entity or task dimension is missing")
    return errs, warns


def dims_fingerprint(dims):
    """Changes whenever a dimension, value, asset note or exclude rule changes: `space` must run again."""
    return hashlib.sha1(json.dumps(dims, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


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
    if a.needs_from:
        if not (st.root / a.needs_from / "needs.jsonl").exists():
            die(f"no {a.needs_from}/needs.jsonl to share")
        proj["needs_from"] = a.needs_from.strip("/")
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
            "product": product, "after_excludes": n, "exact": exact, "shape": space_shape(dims),
        })
        size = n if n is not None else product
        if size > SPACE_WARN:
            warns.append(f"space of {size} combinations: plan to publish a small validated part, never all")
        assets = {d["id"]: d["assets"] for d in gen if d.get("assets")}
        out["assets"] = assets
        if not assets:
            warns.append("no generating dimension states its assets ({needs, have, source}): pages need the "
                         "page count and what each page needs shown to the owner first (rule 6b)")
        needs = read_jsonl(st.needs) if st.needs.exists() else []
        validated = [x for x in needs if x.get("evidence_level") == "validated"]
        proj = read_json(st.project)
        proj["space"] = {"date": date.today().isoformat(), "combinations": size, "shape": out["shape"],
                         "generating": [d["id"] for d in gen], "assets": assets,
                         "fingerprint": dims_fingerprint(dims)}
        if validated:
            set_stage(proj, "space", f"space {size} combinations from {len(gen)} dimensions")
        else:
            warns.append("no validated need in the demand map: needs come before dimensions (rule 1); "
                         "the space is recorded but the stage does not move")
        write_json(st.project, proj)
    if a.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for e in errs:
            print(f"ERROR  {e}")
        for w in warns:
            print(f"WARN   {w}")
        if not errs:
            print(f"shape: {out['shape']}")
            print("generating: " + ", ".join(f"{g['id']}({g['values']})" for g in out["generating"]))
            if out["described_only"]:
                print("described on the page only: " + ", ".join(out["described_only"]))
            tail = out["after_excludes"] if out["exact"] else "unknown (too large to enumerate)"
            print(f"combinations: {out['product']} before excludes, {tail} after")
            for did, ast in out["assets"].items():
                print(f"assets {did}: needs {ast.get('needs')}; have {ast.get('have', '?')}"
                      + (f" ({ast['source']})" if ast.get("source") else ""))
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


def need_evidence(st):
    """{need_id: [evidence rows]} from needs.jsonl, for `<need_id>#e<N>` references."""
    return {n.get("id"): n.get("evidence") or [] for n in read_jsonl(st.needs)} if st.needs.exists() else {}


def question_signals(q, evidence):
    """A sample's signals: the evidence rows a question rests on, copied from the demand map."""
    out = []
    for ref in q.get("evidence") or []:
        if not isinstance(ref, str):
            continue
        m = re.fullmatch(r"(.+)#e(\d+)", ref)
        rows = evidence.get(m.group(1)) if m else None
        if m and rows and 1 <= int(m.group(2)) <= len(rows):
            row = rows[int(m.group(2)) - 1]
            if isinstance(row, dict):
                keep = ("url", "quote", "date") if row.get("url") else ("source", "ref", "q", "quote", "n")
                out.append({k: row[k] for k in keep if k in row})
                continue
        out.append({"ref": ref})
    return out


def sample_from_questions(st, a, dims):
    """Samples are bank questions, spread over needs and angles, real wording first."""
    bank = read_jsonl(st.bank)
    if not bank:
        die(f"no questions in {st.bank}: write the question bank first")
    order = {"quoted": 0, "derived": 1, "hypothesis": 2}
    existing = read_jsonl(st.samples) if a.append and st.samples.exists() else []
    taken = {r.get("question_id") or r.get("combo_id") for r in existing}
    rng = random.Random(a.seed)
    if a.ids:
        # Hand-picked questions (a pilot): taken as named, hypotheses included, in the order given.
        by_id = {q.get("id"): q for q in bank}
        wanted = [i.strip() for i in a.ids.split(",") if i.strip()]
        missing = [i for i in wanted if i not in by_id]
        if missing:
            die(f"--ids not in the question bank: {', '.join(missing)}")
        picked = [by_id[i] for i in wanted if i not in taken]
    else:
        pool = [q for q in bank if a.include_hypothesis or q.get("evidence_level") != "hypothesis"]
        if a.origin:
            pool = [q for q in pool if q.get("origin", "model") == a.origin]
        pool = [q for q in pool if q.get("id") not in taken]
        if not pool:
            die("no questions left to sample: every one is a hypothesis, filtered out, or already sampled "
                "(--include-hypothesis, a different --origin, or no --append)")
        ordered = sorted(pool, key=lambda q: (order.get(q.get("evidence_level"), 3), rng.random()))
        weights = parse_weights(a.weight)
        if weights:
            picked = weighted_pick(ordered, a.n, weights, rng)
        else:
            groups = defaultdict(list)
            for q in ordered:
                groups[(q.get("need_id"), q.get("angle"))].append(q)
            picked = spread(groups, a.n, rng)
    evidence = need_evidence(st)
    rows = []
    for q in picked:
        rows.append({"combo_id": q["id"], "combo": q.get("combo") or {}, "question_id": q["id"],
                     "need_id": q.get("need_id"), "angle": q.get("angle"), "persona": q.get("persona", ""),
                     "opening": q.get("question", ""), "opening_scope": q.get("scope"),
                     "follow_ups": q.get("follow_ups") or [], "conditions": q.get("conditions") or [],
                     "evidence_level": q.get("evidence_level"), "signals": question_signals(q, evidence)})
    for r, q in zip(rows, picked):
        r["origin"] = q.get("origin", "model")
        if q.get("competitor"):
            r["competitor"] = q["competitor"]
    allrows = existing + rows
    write_jsonl(st.samples, allrows)
    covered = {r.get("need_id") for r in allrows}
    out = {"samples": len(allrows), "added": len(rows), "file": str(st.samples), "from": "questions",
           "needs_uncovered": sorted({str(q.get("need_id")) for q in bank} - {str(c) for c in covered}),
           "levels": dict(Counter(r.get("evidence_level") for r in rows)),
           "by_need": dict(Counter(r.get("need_id") for r in rows)),
           "origins": dict(Counter(r.get("origin") for r in rows))}
    print(json.dumps(out, ensure_ascii=False, indent=2))


def parse_weights(items):
    """--weight NEED=W (repeatable); needs not named weigh 1."""
    out = {}
    for item in items or []:
        nid, _, w = str(item).partition("=")
        try:
            out[nid.strip()] = float(w)
        except ValueError:
            die(f"--weight takes NEED=NUMBER, not {item!r}")
        if out[nid.strip()] < 0:
            die(f"--weight {item!r}: weights are 0 or more")
    return out


def weighted_pick(ordered, n, weights, rng):
    """Seats per need by weight (highest averages, capped by what each need has), then angles spread within."""
    by_need = defaultdict(list)
    for q in ordered:
        by_need[q.get("need_id")].append(q)
    seats = Counter()
    for _ in range(n):
        open_ = [k for k in by_need if seats[k] < len(by_need[k]) and weights.get(k, 1.0) > 0]
        if not open_:
            break
        best = max(open_, key=lambda k: (weights.get(k, 1.0) / (seats[k] + 1), str(k)))
        seats[best] += 1
    picked = []
    for k in sorted(by_need, key=str):
        groups = defaultdict(list)
        for q in by_need[k]:
            groups[q.get("angle")].append(q)
        picked += spread(groups, seats[k], rng)
    return picked


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
    if (a.append or a.ids or a.origin or a.weight) and not a.from_questions:
        die("--append, --ids, --origin and --weight work with --from-questions")
    if a.append and a.force:
        die("--append adds to samples.jsonl, --force replaces it: pick one")
    if st.samples.exists() and read_jsonl(st.samples) and not a.force and not a.append:
        die(f"{st.samples} has rows; --force replaces it (filled conversations are lost), --append adds to it")
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
    if a.tool_share is None:
        a.tool_share = TOOL_SHARE_CAPABILITY if space_shape(dims) == "capability" else TOOL_SHARE
    if not 0 <= a.tool_share <= 1:
        die("--tool-share is a share between 0 and 1")
    k = round(len(rows) * a.tool_share)
    # Evenly spaced over the rows, which are already spread over the values.
    tool = {int((i + 0.5) * len(rows) / k) for i in range(k)} if k else set()
    for i, r in enumerate(rows):
        r["angle"] = "recommend" if i in tool else "problem"
    write_jsonl(st.samples, rows)
    uncovered = [f"{d['id']}={v['id']}" for d in gen for v in d["values"] if use[d["id"]][v["id"]] == 0]
    out = {"samples": len(rows), "file": str(st.samples), "uncovered_values": uncovered,
           "angles": dict(Counter(r["angle"] for r in rows))}
    if a.n < widest:
        out["warning"] = f"n={a.n} is below the widest dimension ({widest} values): some values go unsampled"
    print(json.dumps(out, ensure_ascii=False, indent=2))


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "platform"


def cmd_probes(st, a):
    rows = read_jsonl(st.samples)
    if not rows:
        die("no samples: run sample first")
    empty = [r["combo_id"] for r in rows if not r.get("opening")]
    if empty:
        die(f"{len(empty)} samples have no opening yet (first: {empty[0]}); write the conversations first")
    proj = read_json(st.project)
    # `platforms` are the targets and may be free text; `probe_platforms` are the ones probed this round.
    platforms = proj.get("probe_platforms") or proj.get("platforms") or ["ChatGPT"]
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
        files = ", ".join(f"`{st.rel}/gap/raw/{r['combo_id']}--{slug(p)}--1.md`" for p in platforms)
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
    if probed and (len(probed) < THIN_TOTAL or len(platforms) <= 1):
        notes.append(f"thin sample: {len(probed)} probed on {len(platforms)} platform(s) "
                     f"({', '.join(platforms) or 'none'}); read it as one channel's sample, not a measurement")
    if presence["measured"]:
        if presence["in_answer_share"] < 0.25 and presence["lever_hint"] in ("offsite", "consensus"):
            notes.append(f"own site in {presence['in_answer_share']:.0%} of answers and the answers rest on "
                         f"{presence['lever_hint']} sources: pages alone are unlikely to change who gets "
                         "recommended; plan site-offsite (GEO mode) alongside or instead")
        elif presence["in_answer_share"] < 0.25:
            notes.append(f"own site in {presence['in_answer_share']:.0%} of answers: a gap is an opening for "
                         "the content, not proof the assistant will find the pages; check the captured "
                         "search queries against where the site ranks")
        if presence["in_answer_share"] < 0.25:
            notes.append("probes can undercount picks (one account, fresh chats, a few runs each): before "
                         "reading this as absence, compare with AI-referred landings by page")
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
         f"Assistant-chat hint ({', '.join(rep['platform_runs']) or 'no platform'} only; not a decision for "
         f"search engines or agents, and the decision is the owner's, per need × channel in gap/channels.md): "
         f"**{rep['hint']}**. "
         f"{rep['high']} of {rep['probed']} probed combinations show a high-opportunity gap "
         f"({rep['share_high']:.0%}; threshold {rep['threshold']:.0%}). "
         f"{rep['with_signals']} of the probed combinations have outside evidence, "
         f"{rep['with_first_party']} have first-party evidence.", "",
         f"Runs by platform: {', '.join(f'{k} {v}' for k, v in rep['platform_runs'].items()) or 'none'}. "
         f"Dates: {', '.join(rep['dates']) or 'none'}. AI answers are samples, not rankings.", ""]
    if rep.get("where"):
        L += ["Runs filtered by " + ", ".join(f"{k}={v}" for k, v in rep["where"].items()) + ".", ""]
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
    if rep.get("extra_sets"):
        L += ["## Extra run sets (not in the numbers above; `--include-extra` adds them)", ""]
        for name, e in rep["extra_sets"].items():
            share = f"{e['in_answer_share']:.0%}" if e.get("in_answer_share") is not None else "not recorded"
            L.append(f"- `{name}`: {e['runs']} runs; site in answer {share}; "
                     f"search queries captured in {e.get('queries_captured', 0)}.")
        L.append("")
    if rep.get("notes"):
        L += ["## Read before deciding", ""] + [f"- {n}" for n in rep["notes"]] + [""]
    for key, title in (("need_id", "By need"), ("angle", "By angle"), ("stratum", "By stratum")):
        g = (rep.get("groups") or {}).get(key)
        if not g:
            continue
        L += [f"## {title}", "", "| Value | Probed | Runs | High | Share high | Site in answer |",
              "| --- | --- | --- | --- | --- | --- |"]
        for k, v in g.items():
            sh = f"{v['share_high']:.0%}" if v["share_high"] is not None else "—"
            oa = f"{v['own_in_answer']:.0%} of {v['own_measured']}" if v["own_in_answer"] is not None else "—"
            runs = f"{v['runs']} (thin)" if v["runs"] < THIN_NEED_RUNS else str(v["runs"])
            L.append(f"| {k} | {v['probed']} | {runs} | {v['high']} | {sh} | {oa} |")
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


def parse_where(items):
    out = []
    for it in items or []:
        k, sep, v = it.partition("=")
        if not sep or not k:
            die(f"--where needs KEY=VALUE, got {it!r}")
        out.append((k, v))
    return out


def filter_runs(runs, where):
    return [r for r in runs if all(str(r.get(k)) == v for k, v in where)]


def cmd_report(st, a):
    samples = read_jsonl(st.samples)
    if not samples:
        die("no samples")
    where = parse_where(a.where)
    runs = filter_runs(read_jsonl(st.runs), where)
    extra = {p.stem: filter_runs(read_jsonl(p), where) for p in st.extra_runs}
    if a.include_extra:
        runs = runs + [r for rows in extra.values() for r in rows]
    rep = build_report(samples, runs, a.threshold)
    if where:
        rep["where"] = dict(where)
    if extra and not a.include_extra:
        keep = ("measured", "in_answer_share", "first_share", "queries_captured", "outcomes")
        rep["extra_sets"] = {name: {"runs": len(rows), **{k: v for k, v in build_presence(rows).items() if k in keep}}
                             for name, rows in extra.items()}
    proj = read_json(st.project)
    write_json(st.report_json, rep)
    st.report_md.write_text(report_md(rep, proj))
    if rep["probed"]:
        set_stage(proj, "gap", f"gap report: {rep['high']}/{rep['probed']} high, hint {rep['hint']}")
        write_json(st.project, proj)
    if not st.channels.exists():
        write_channels(st, proj, rep)
    out = {k: rep[k] for k in ("probed", "high", "share_high", "hint", "strong_values", "notes")}
    out["channels"] = str(st.channels)
    out.update({k: rep["presence"][k] for k in ("in_answer_share", "first_share", "lever_hint", "queries_captured")})
    print(json.dumps(out, ensure_ascii=False, indent=2))


def chat_cell(rep, nid):
    g = ((rep or {}).get("groups") or {}).get("need_id", {}).get(nid)
    if not g or not g.get("runs"):
        return "picked: not probed · after landing: not measured"
    thin = " (thin)" if g["runs"] < THIN_NEED_RUNS else ""
    sh = f"{g['share_high']:.0%}" if g.get("share_high") is not None else "—"
    oa = f"{g['in_answer']}/{g['own_measured']}" if g.get("own_measured") else "not recorded"
    return f"picked: {g['runs']} runs{thin}; high gap {sh}; site in answer {oa} · after landing: not measured"


def agent_cell(n):
    where = set(n.get("where_asked") or [])
    vol = volume_rows(n.get("volume") or []) or []
    parts = [f"{what.replace('_', ' ')} {total:,}" if not isinstance(total, str) else f"{what.replace('_', ' ')} {total}"
             for what, total, _ in vol]
    if parts:
        return "volume: " + "; ".join(parts)
    if where & {"agent", "site_search", "product"}:
        return "asked there (" + ", ".join(sorted(where & {"agent", "site_search", "product"})) + "); volume not measured"
    return "not measured"


def write_channels(st, proj, rep=None):
    """Skeleton of the need x channel table; the agent fills evidence it has, the owner picks the lever."""
    needs = read_jsonl(st.needs) if st.needs.exists() else []
    L = [f"# Need × channel: {proj.get('name', '')}", "",
         f"Skeleton written {date.today().isoformat()} by geo_idea.py. Drop a column the goal card "
         f"(`{GOAL_FILE}`) marks out of scope. Fill each cell with evidence or `not measured`; the owner picks "
         f"the Lever for every need: {', '.join(sorted(LEVERS))} (several joined by `+`), `?` until chosen. "
         "`decide` reads the Lever column.", "",
         "| Need | Assistant chat | Search engines | Agents / API / MCP | Lever | Owner's note |",
         "| --- | --- | --- | --- | --- | --- |"]
    for n in needs:
        search = ("asked there; index and rank not measured" if "search_engine" in (n.get("where_asked") or [])
                  else "not measured")
        L.append(f"| {n.get('id')}: {n.get('need', '')} | {chat_cell(rep, n.get('id'))} | {search} | "
                 f"{agent_cell(n)} | ? | |")
    st.channels.parent.mkdir(parents=True, exist_ok=True)
    st.channels.write_text("\n".join(L) + "\n")


def parse_channels(path):
    """{need_id: set(levers)} from the Lever column; unknown words are returned separately."""
    levers, unknown, col = {}, [], None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if col is None:
            low = [c.lower() for c in cells]
            if "lever" in low:
                col = low.index("lever")
            continue
        if set(cells[0]) <= set("-: "):
            continue
        nid = cells[0].split(":")[0].strip().strip("`")
        cell = cells[col] if col < len(cells) else ""
        words = {w.strip().lower() for w in re.split(r"[+,/ ]+", cell) if w.strip() and w.strip() != "?"}
        unknown += [f"{nid}: {w}" for w in words - LEVERS]
        levers[nid] = words & LEVERS
    return levers, unknown, col is not None


def decision_gates(st, a, proj, dims, sub):
    errs, warns, levers = [], [], {}
    if not st.channels.exists():
        errs.append(f"no {st.rel}/gap/channels.md: run `channels` (or `report`), fill it and pick each need's "
                    "Lever with the owner; the decision is per need × channel")
    else:
        levers, unknown, ok = parse_channels(st.channels)
        if not ok:
            errs.append("gap/channels.md has no Lever column")
        undecided = [n for n, l in levers.items() if not l]
        if undecided:
            errs.append(f"Lever not chosen in gap/channels.md for: {', '.join(undecided)}")
        if unknown:
            errs.append(f"unknown levers in gap/channels.md ({', '.join(sorted(LEVERS))}): {', '.join(unknown)}")
    if a.verdict in ("go", "narrow"):
        gen = [d["id"] for d in generating(dims)] if dims.get("dimensions") else []
        space = proj.get("space") or {}
        if not gen:
            errs.append("no task space: pages need dimensions.json with generating dimensions, checked by `space` "
                        "(rule 6b); a decision that makes no pages is --verdict stop, with the other levers "
                        "in gap/channels.md")
        elif space.get("fingerprint") != dims_fingerprint(dims):
            errs.append("dimensions.json changed since the last `space` (or `space` never ran): run space")
        elif not space.get("assets"):
            errs.append("the task space states no assets: add {needs, have, source} to the generating "
                        "dimensions and run space, so the owner sees the page count and what each page needs")
        if levers and all(levers.values()) and not any("pages" in l for l in levers.values()):
            errs.append("no need has the lever `pages` in gap/channels.md: a decision without pages is --verdict stop")
        for nid in (sub or {}).get("need", []):
            if levers.get(nid) and "pages" not in levers[nid]:
                errs.append(f"subspace need {nid} does not have the lever `pages` in gap/channels.md")
        needs = read_jsonl(st.needs) if st.needs.exists() else []
        if not any(n.get("evidence_level") == "validated" for n in needs):
            warns.append("no validated need behind this decision: every need is derived or a hypothesis")
    if errs:
        die("; ".join(errs))
    for w in warns:
        print(f"WARN   {w}", file=sys.stderr)
    return {n: sorted(l) for n, l in levers.items()}


def presence_gate(a, rep, pres):
    """Pages rest on whether the assistant picks the site (site rule 2). A low presence does not block
    the owner's go, but the reason has to be written down, next to the presence by angle."""
    if a.verdict not in ("go", "narrow"):
        return
    share = pres.get("in_answer_share")
    if share is None:
        print("WARN   own presence not recorded in the runs: this decision rests on the answer gap only, "
              "not on whether the assistant would pick the site", file=sys.stderr)
        return
    if share >= PRESENCE_LINE:
        return
    by_angle = (rep.get("groups") or {}).get("angle") or {}
    angles = ", ".join(f"{k} {v['own_in_answer']:.0%}" for k, v in by_angle.items() if v.get("own_in_answer") is not None)
    msg = (f"own site in {share:.0%} of answers (lever hint {pres.get('lever_hint') or 'none'}"
           + (f"; by angle: {angles}" if angles else "") + "): pages rest on whether the assistant picks the site "
           "(site rule 2), and these probes say it does not yet")
    if "recommend" not in by_angle:
        msg += "; no probed sample asked for a tool, site or app (angle recommend), so picking was not tested"
    if not (a.note or "").strip():
        die(msg + ". Record the owner's reason with --note (e.g. AI-referred landings on matching pages, "
            "which probes undercount; or a first small wave as a test, with the off-site or existing-page "
            "levers alongside), or decide narrow / stop")
    print(f"WARN   {msg}", file=sys.stderr)


def record_decision(st, proj, dec, stage_note):
    """Decisions are appended, never overwritten: `decision` is the current one, `decisions` the history."""
    hist = proj.setdefault("decisions", [])
    if proj.get("decision") and (not hist or hist[-1] != proj["decision"]):
        hist.append(proj["decision"])
    hist.append(dec)
    proj["decision"] = dec
    set_stage(proj, "decided", stage_note)
    write_json(st.project, proj)
    print(json.dumps(dec, ensure_ascii=False, indent=2))


def cmd_channels(st, a):
    if st.channels.exists() and not a.force:
        die(f"{st.channels} exists: edit it (or --force rebuilds the skeleton and loses the edits)")
    write_channels(st, read_json(st.project), read_json(st.report_json, None))
    print(json.dumps({"written": str(st.channels)}, ensure_ascii=False))


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
    dims = read_json(st.dimensions, {"dimensions": []})
    levers = decision_gates(st, a, proj, dims, sub)
    pres = rep.get("presence") or {}
    presence_gate(a, rep, pres)
    dec = {"verdict": a.verdict, "date": date.today().isoformat(), "by": "user",
           "subspace": sub, "note": a.note or "", "levers": levers,
           "evidence": {"probed": rep["probed"], "share_high": rep["share_high"], "hint": rep["hint"],
                        "platforms": sorted(rep.get("platform_runs") or {}),
                        "in_answer_share": pres.get("in_answer_share"), "lever_hint": pres.get("lever_hint")},
           "dimensions": [d["id"] for d in generating(dims)] if dims.get("dimensions") else [],
           "extensions": []}
    record_decision(st, proj, dec, f"decision {a.verdict}")


def subspace_arg(st, a):
    sub = json.loads(a.subspace) if a.subspace else None
    if a.verdict == "narrow" and not sub:
        die("narrow needs --subspace, e.g. '{\"source\": [\"heic\", \"png\"]}'")
    if sub:
        dims = {d["id"]: {v["id"] for v in d["values"]} for d in read_json(st.dimensions, {"dimensions": []})["dimensions"]}
        # The bank route narrows by need (and optionally angle) instead of by a task-space dimension.
        dims.setdefault("need", {n.get("id") for n in read_jsonl(st.needs)})
        dims.setdefault("angle", set(ANGLES))
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
    dims = read_json(st.dimensions, {"dimensions": []})
    if dims.get("dimensions"):
        derr, _ = validate_dimensions(dims)
        if derr:
            die("fix dimensions first: " + "; ".join(derr))
    proj = read_json(st.project)
    sub = subspace_arg(st, a)
    levers = decision_gates(st, a, proj, dims, sub)
    rep = read_json(st.report_json, {})
    dec = {"verdict": a.verdict, "date": date.today().isoformat(), "by": "user",
           "subspace": sub, "note": a.note or "", "levers": levers,
           "evidence": {"basis": "first-party demand", "needs_validated": len(validated),
                        "probed": rep.get("probed", 0), "share_high": rep.get("share_high"),
                        "hint": rep.get("hint")},
           "dimensions": [d["id"] for d in generating(dims)] if dims.get("dimensions") else [],
           "extensions": []}
    record_decision(st, proj, dec, f"decision {a.verdict} on first-party demand")


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

def query_tokens(q):
    t = re.findall(r"[a-z0-9][a-z0-9.+'-]*", q.lower())
    return frozenset(w for w in t if w not in QUERY_STOP and not re.fullmatch(r"20\d\d", w))


DOMAIN_RE = re.compile(r"(?:site:)?((?:[a-z0-9-]+\.)+(?:com|ai|app|io|net|org|video|co|online|tools|dev|me))\b", re.I)
NAME_RE = re.compile(r"^(?:[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*|[A-Z][a-z]{2,}[A-Za-z0-9]*|[A-Z]{1,2}[a-z][A-Za-z0-9]*)$")
NOT_NAMES = {"Free", "Best", "How", "Online", "Official", "What", "Which", "Top", "Why", "Can", "Is", "Super", "Mac",
             "Windows", "Android", "iPhone"}


def named_entity(q):
    """The site or product a query checks: a domain, else its first proper name (CapCut, HandBrake)."""
    m = DOMAIN_RE.search(q)
    if m:
        return m.group(1).lower().removeprefix("www.")
    for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9.+-]*", q):
        if NAME_RE.match(w) and w not in NOT_NAMES:
            return w
    return None


def cluster_queries(queries):
    """Greedy grouping, most frequent first: a query joins the first group whose seed shares at least
    60% of the shorter query's words (overlap coefficient)."""
    freq = Counter(queries)
    groups = []
    for q, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])):
        tok = query_tokens(q)
        if not tok:
            continue
        for g in groups:
            if len(tok & g["seed"]) / min(len(tok), len(g["seed"])) >= 0.6:
                g["queries"].append(q)
                break
        else:
            groups.append({"seed": tok, "label": q, "queries": [q]})
    return groups


def cmd_queries(st, a):
    """Find searches (generic: the assistant looks for candidates) are grouped into clusters whose rank
    decides whether our pages can be picked; named checks (a site or product it already has in mind)
    show its shortlist."""
    proj = read_json(st.project)
    by_sample = {s["combo_id"]: s for s in read_jsonl(st.samples)}
    # Our own names only: brand_terms also holds competitors' names (for the probe-question check).
    brands = sorted({str(b).lower() for b in [proj.get("name", ""), registrable((proj.get("site") or {}).get("origin", ""))]
                     + list(proj.get("brands") or []) if b and len(str(b)) > 2})
    items = []
    for path in [st.runs] + list(st.extra_runs):
        for r in read_jsonl(path):
            for q in r.get("search_queries") or []:
                if isinstance(q, str) and q.strip():
                    items.append((q.strip(), r))
    if not items:
        die("no captured search queries in the runs (search_queries): capture them in the browser runs first")
    kind_of = {}
    for q, _ in items:
        if any(re.search(rf"\b{re.escape(b)}\b", q.lower()) for b in brands):
            kind_of[q] = ("own", proj.get("name", "own"))
        elif named_entity(q):
            kind_of[q] = ("named", named_entity(q))
        else:
            kind_of[q] = ("find", None)

    def summary(qs):
        runs = [r for q, r in items if q in qs]
        own = [r for r in runs if r.get("own") in OWN_STATUS]
        return {"n": len(runs), "conversations": len({r.get("combo_id") for r in runs}),
                "examples": sorted(qs)[:5], "combos": sorted({r.get("combo_id") for r in runs}),
                "angles": dict(Counter((by_sample.get(r.get("combo_id")) or {}).get("angle") for r in runs)),
                "own_in_answer": round(sum(r["own"] in IN_ANSWER for r in own) / len(own), 2) if own else None}

    old = {row.get("key"): row for row in read_jsonl(st.queries)} if st.queries.exists() else {}
    rows = []
    for i, g in enumerate(cluster_queries([q for q, _ in items if kind_of[q][0] == "find"]), 1):
        key = " ".join(sorted(g["seed"]))
        rows.append({"id": f"f{i}", "kind": "find", "key": key, "label": g["label"], **summary(set(g["queries"])),
                     "rank": (old.get(key) or {}).get("rank")})
    named, label = defaultdict(set), {}
    for q, (k, ent) in kind_of.items():
        if k in ("named", "own"):
            # TensorPix and tensorpix.ai are one candidate: key on the name part, lower case.
            key = (k, registrable(ent) if "." in ent else ent.lower())
            named[key].add(q)
            label.setdefault(key, ent)
    for i, (key, qs) in enumerate(sorted(named.items(), key=lambda kv: (kv[0][0] != "own", -len(kv[1]), kv[0][1])), 1):
        rows.append({"id": f"n{i}", "kind": key[0], "key": f"{key[0]}:{key[1]}", "label": label[key], **summary(qs)})
    write_jsonl(st.queries, rows)
    find = [r for r in rows if r["kind"] == "find"]
    checks = [r for r in rows if r["kind"] != "find"]
    convs = len({r.get("combo_id") for _, r in items})
    L = [f"# Assistants' search queries: {proj.get('name', '')}", "",
         f"{len(items)} captured queries from {convs} conversations: "
         f"{sum(r['n'] for r in find)} find searches in {len(find)} clusters, "
         f"{sum(r['n'] for r in checks)} checks of {len(checks)} named sites or products.", "",
         "## Find searches (rank decides whether our pages can be picked)", "",
         "Fill `rank` in queries.jsonl per cluster (engine, date, our position or null, our URL, the winners' "
         "domains, source) and rerun: filled ranks are kept.", "",
         "`winners_kind`: dedicated when pages made for this exact search win (a page of its own can win), "
         "general when broad tool or home pages win (answer it as a section of one), mixed otherwise. "
         "site-batch reads it before a combination of two dimensions becomes a page.", "",
         "| Cluster | Runs | We are in the answer | Our rank | Winners | Example queries |",
         "| --- | --- | --- | --- | --- | --- |"]
    for r in find:
        rk = r["rank"] or {}
        rank = (f"{rk.get('engine')}: {rk.get('ours') if rk.get('ours') is not None else 'not in results'}"
                if rk else "not measured")
        share = f"{r['own_in_answer']:.0%}" if r["own_in_answer"] is not None else "not recorded"
        L.append(f"| {r['id']} | {r['n']} | {share} | {rank} | {rk.get('winners_kind') or '?'} | " + "; ".join(f"`{q}`" for q in r["examples"][:3]) + " |")
    L += ["", "## Named checks (the assistant's shortlist: who it already has in mind)", "",
          "When we are not on this list, the assistant answers from memory and checks others: lists, "
          "communities and reviews (site-offsite GEO mode) change the shortlist; pages alone do not.", "",
          "| Checked | Kind | Runs | Conversations | Example queries |", "| --- | --- | --- | --- | --- |"]
    for r in checks:
        L.append(f"| {r['label']} | {r['kind']} | {r['n']} | {r['conversations']} | "
                 + "; ".join(f"`{q}`" for q in r["examples"][:2]) + " |")
    st.queries_md.write_text("\n".join(L) + "\n")
    print(json.dumps({"find_clusters": len(find), "find_queries": sum(r["n"] for r in find),
                      "named": len(checks), "named_queries": sum(r["n"] for r in checks),
                      "own_checks": sum(r["n"] for r in checks if r["kind"] == "own"),
                      "ranked": sum(1 for r in find if r["rank"]), "file": str(st.queries)}, ensure_ascii=False))


Q_FIELDS = ("q", "query", "term", "search", "keyword", "quote")
N_FIELDS = ("n", "count", "searches", "volume", "hits")


def read_query_file(path):
    """Real searches from an export: CSV or JSONL with a query column (q, query, term, search, keyword) and an
    optional count (n, count, searches, volume, hits); plain text is one query per line, optionally `query<TAB>n`."""
    p = Path(path)
    if not p.exists():
        die(f"--from {path}: no such file")
    out = []

    def num(v):
        try:
            return max(float(v), 0.0)
        except (TypeError, ValueError):
            return 1.0

    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                low = {str(k).strip().lower(): v for k, v in r.items() if k}
                q = next((low[k] for k in Q_FIELDS if low.get(k)), None)
                n = next((low[k] for k in N_FIELDS if low.get(k) not in (None, "")), 1)
                if q:
                    out.append((q.strip(), num(n)))
    elif p.suffix.lower() in (".jsonl", ".ndjson"):
        for r in read_jsonl(p):
            q = next((r[k] for k in Q_FIELDS if r.get(k)), None)
            n = next((r[k] for k in N_FIELDS if r.get(k) not in (None, "")), 1)
            if isinstance(q, str) and q.strip():
                out.append((q.strip(), num(n)))
    else:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            q, _, n = line.partition("\t")
            if q.strip():
                out.append((q.strip(), num(n) if n.strip() else 1.0))
    return out


SEARCH_SOURCES = {"site_search", "api_search", "mcp_search", "search_miss"}


def word_list(text):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9'+.-]*", str(text).lower())
            if w not in QUERY_STOP and not re.fullmatch(r"[\d.,]+", w)]


def value_tokens(v):
    """The words a value is searched by: its id split on - and _, or a short label."""
    ids = set(word_list(re.sub(r"[-_]+", " ", v.get("id", ""))))
    lab = set(word_list(v.get("label", "")))
    return [t for t in (ids, lab if 0 < len(lab) <= 3 else set()) if t]


def cmd_slots(st, a):
    """Which words real searches use, against the task space: per dimension, how often its values are
    searched; and the frequent words no dimension holds yet, with the values they come with. It counts;
    the owner and the model decide what each word is (a dimension, a variant, a page fact, wording)."""
    dims = read_json(st.dimensions, {"dimensions": []})
    items = []                          # (query, weight, origin)
    for path in a.from_ or []:
        items += [(q, n, Path(path).name) for q, n in read_query_file(path)]
    for path in [st.runs] + list(st.extra_runs):
        for r in read_jsonl(path):
            for q in r.get("search_queries") or []:
                if isinstance(q, str) and q.strip():
                    items.append((q.strip(), 1.0, "assistant searches"))
    if st.needs.exists():
        # Only what people typed: search records (weighted by their count) and off-site quotes. Analytics
        # rows in the demand map describe behaviour, not wording.
        for n in read_jsonl(st.needs):
            for e in n.get("evidence") or []:
                if e.get("source") in SEARCH_SOURCES and isinstance(e.get("q"), str) and e["q"].strip():
                    w = e.get("n")
                    items.append((e["q"].strip(), float(w) if isinstance(w, (int, float)) and w > 0 else 1.0,
                                  "demand map searches"))
                elif e.get("url") and isinstance(e.get("quote"), str) and e["quote"].strip():
                    items.append((e["quote"].strip(), 1.0, "demand map quotes"))
    if not items:
        die("no queries: pass --from <site search export>, or capture search_queries in runs, or fill needs.jsonl evidence")
    total = sum(w for _, w, _ in items)
    toks = [(set(word_list(q)), w) for q, w, _ in items]

    def mentions(v, t):
        return any(vt <= t for vt in value_tokens(v))

    dim_rows, owned = [], {}
    for d in dims.get("dimensions", []):
        counts = Counter()
        hit = 0.0
        for t, w in toks:
            m = [v["id"] for v in d.get("values", []) if mentions(v, t)]
            for vid in m:
                counts[vid] += w
            hit += w if m else 0
        for v in d.get("values", []):
            for vt in value_tokens(v):
                for word in vt:
                    owned.setdefault(word, d["id"])
        dim_rows.append({"id": d["id"], "kind": d.get("kind"), "generating": bool(d.get("changes_answer")),
                         "share": round(hit / total, 3) if total else 0.0,
                         "values": [{"id": v["id"], "n": round(counts[v["id"]], 1)} for v in d.get("values", [])],
                         "never": [v["id"] for v in d.get("values", []) if not counts[v["id"]]]})
    gen_vals = [(d["id"], v) for d in dims.get("dimensions", []) if d.get("changes_answer") for v in d.get("values", [])]
    words, pairs, co = Counter(), Counter(), defaultdict(Counter)
    # A word written as a proper name in most of its uses (Topaz, CapCut), or a listed competitor, is a
    # candidate the assistant checks, not a slot of the task.
    cased, seen = Counter(), Counter()
    for q, _, _ in items:
        for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9'+.-]*", q):
            seen[raw.lower()] += 1
            if NAME_RE.match(raw) and raw not in NOT_NAMES:
                cased[raw.lower()] += 1
    names = {x for x in seen if cased[x] * 2 > seen[x]}
    names |= {str(c.get("name", "")).lower() for c in read_jsonl(st.competitors)}
    for (q, w, _), (t, _) in zip(items, toks):
        seq = word_list(q)
        for x in set(seq):
            words[x] += w
        for x, y in set(zip(seq, seq[1:])):
            pairs[f"{x} {y}"] += w
        vals = [f"{did}={v['id']}" for did, v in gen_vals if mentions(v, t)]
        for x in set(seq):
            if x not in owned:
                for vv in vals:
                    co[x][vv] += w
    free = [{"word": x, "n": round(n, 1), "share": round(n / total, 3),
             "with": [k for k, _ in co[x].most_common(3)]}
            for x, n in words.most_common() if x not in owned and x not in names][: a.top]
    named = [{"word": x, "n": round(n, 1)} for x, n in words.most_common() if x in names and x not in owned][: a.top // 2]
    free_pairs = [{"words": x, "n": round(n, 1)} for x, n in pairs.most_common()
                  if not all(y in owned for y in x.split())][: a.top // 2]
    rep = {"date": date.today().isoformat(), "queries": len(items), "weight": round(total, 1),
           "sources": dict(Counter(o for _, _, o in items)), "dimensions": dim_rows,
           "unassigned_words": free, "unassigned_pairs": free_pairs, "names": named}
    write_json(st.slots_json, rep)
    proj = read_json(st.project)
    L = [f"# Search words against the task space: {proj.get('name', '')}", "",
         f"{len(items)} queries (weight {total:g}) from " + ", ".join(f"{k} {v}" for k, v in rep["sources"].items())
         + f"; {rep['date']}. Counts are weighted by each query's count where the export has one.", "",
         "Read with site-idea `references/dimensions.md`: a dimension real searches never name is a guess; a "
         "frequent word no dimension holds is a missing dimension, a variant of a value, a fact every page "
         "states, or wording. The counts do not decide which.", "",
         "## Dimensions", "", "| Dimension | Generates pages | Share of searches naming a value | Top values | Never searched |",
         "| --- | --- | --- | --- | --- |"]
    for d in dim_rows:
        top = sorted(d["values"], key=lambda v: -v["n"])[:5]
        L.append(f"| {d['id']} ({d['kind']}) | {'yes' if d['generating'] else 'no'} | {d['share']:.0%} | "
                 + ", ".join(f"{v['id']} {v['n']:g}" for v in top if v["n"]) + f" | {len(d['never'])}: "
                 + ", ".join(d["never"][:6]) + (" …" if len(d["never"]) > 6 else "") + " |")
    L += ["", "## Frequent words no dimension holds", "",
          "| Word | Weight | Share of searches | Comes with |", "| --- | --- | --- | --- |"]
    L += [f"| {x['word']} | {x['n']:g} | {x['share']:.0%} | {', '.join(x['with'])} |" for x in free]
    L += ["", "## Names in the searches (sites and products checked, not slots)", "",
          ", ".join(f"{x['word']} {x['n']:g}" for x in named) or "none"]
    L += ["", "## Frequent word pairs with an unassigned word", "", "| Words | Weight |", "| --- | --- |"]
    L += [f"| {x['words']} | {x['n']:g} |" for x in free_pairs]
    st.slots_md.write_text("\n".join(L) + "\n")
    print(json.dumps({"queries": len(items), "file": str(st.slots_md),
                      "dimensions": {d["id"]: d["share"] for d in dim_rows},
                      "top_unassigned": [x["word"] for x in free[:10]]}, ensure_ascii=False))


def rank_errors(rk, where):
    if rk is None:
        return []
    if not isinstance(rk, dict):
        return [f"{where}: rank is an object {{engine, date, ours, url, winners, source}} or null"]
    errs = [f"{where}: rank needs {k}" for k in ("engine", "date", "source") if not rk.get(k)]
    if rk.get("ours") is not None and not (isinstance(rk["ours"], int) and rk["ours"] >= 1):
        errs.append(f"{where}: rank.ours is our position (1 or more), or null when we are not in the results")
    if not isinstance(rk.get("winners", []), list):
        errs.append(f"{where}: rank.winners is a list of domains")
    if rk.get("winners_kind") not in (None, "dedicated", "general", "mixed"):
        errs.append(f"{where}: rank.winners_kind is dedicated (pages for this exact search win), general "
                    "(broad tool or home pages win) or mixed")
    return errs


def cmd_check(st, a):
    errs = []
    proj = read_json(st.project)
    for k in ("name", "idea"):
        if not proj.get(k):
            errs.append(f"project.json: {k} is empty")
    if proj.get("stage") not in STAGES + ["blueprint", "pages"]:
        errs.append(f"project.json: unknown stage {proj.get('stage')!r}")
    dims = read_json(st.dimensions, {"dimensions": [], "exclude": []})
    # Before the task space exists (demand map and question bank only), empty dimensions are fine;
    # so is a project that sampled its question bank instead of combinations (the bank route).
    bank_route = st.bank.exists() and any(s.get("question_id") for s in read_jsonl(st.samples))
    if dims.get("dimensions") or (proj.get("stage") not in ("idea", "needs") and not bank_route):
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
        berr, _ = validate_bank(read_jsonl(st.bank), read_jsonl(st.needs) if st.needs.exists() else [],
                                comp_ids, dims, proj, competitors)
        errs += berr
    for s in samples:
        if need_ids and s.get("need_id") is not None and s["need_id"] not in need_ids:
            errs.append(f"samples: {s.get('combo_id')}: need_id {s['need_id']!r} is not in needs.jsonl")
    run_sets = [(st.runs.name, read_jsonl(st.runs))] + [(p.name, read_jsonl(p)) for p in st.extra_runs]
    for set_name, i, r in [(n, i, r) for n, rows in run_sets for i, r in enumerate(rows, 1)]:
        where = f"{set_name.removesuffix('.jsonl')}:{i}"
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
        if r.get("slice") is not None and not (isinstance(r["slice"], str) and r["slice"]):
            errs.append(f"{where}: slice is a non-empty string, or absent")
        for k in ("platform", "date", "mode"):
            if not r.get(k):
                errs.append(f"{where}: {k} is required")
        raw = r.get("raw")
        if raw and not (st.root / raw).exists():
            errs.append(f"{where}: raw file {raw} does not exist")
    for i, row in enumerate(read_jsonl(st.queries) if st.queries.exists() else [], 1):
        if row.get("kind") == "find":
            errs += rank_errors(row.get("rank"), f"queries:{row.get('id', i)}")
    warns = goal_warnings(st, proj)
    combo_rows = [s for s in samples if not s.get("question_id") and not s.get("url")]
    if combo_rows and not any(s.get("angle") == "recommend" for s in combo_rows):
        warns.append(f"none of the {len(combo_rows)} combination samples asks for a tool, site or app (angle "
                     "recommend): the probes measure the answer, not whether the assistant picks a tool; "
                     "re-sample (`sample --force`, --tool-share) or append such samples with angle recommend")
    for e in errs:
        print(f"ERROR  {e}")
    for w in warns:
        print(f"WARN   {w}")
    print(json.dumps({"errors": len(errs), "warnings": len(warns)}))
    sys.exit(1 if errs else 0)


def goal_section(text, title):
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    return " ".join(x.strip() for x in m.group(1).splitlines() if x.strip())


def goal_warnings(st, proj):
    """The goal card is the site's source of truth; project.json copies must not drift from it."""
    warns = []
    if not st.goal.exists():
        warns.append(f"no goal card {GOAL_FILE} at the project root: the site skill's step 0 writes it with the owner")
    else:
        if not goal_section(st.goal.read_text(), "Main bet"):
            warns.append(f"{GOAL_FILE} has no 'Main bet' section: write the approach this round tests, with the owner")
        star = goal_section(st.goal.read_text(), "North star")
        mine = (proj.get("north_star") or "").strip()
        norm = lambda t: re.sub(r"[\W_]+", " ", t).strip().lower()
        # project.json may hold the whole section or its opening; anything not found in the card is drift.
        if star and mine and norm(mine) not in norm(star):
            warns.append(f"project.json north_star differs from {GOAL_FILE}: the goal card wins; copy it over")
    if proj.get("decision") and not st.channels.exists():
        warns.append("a decision exists without gap/channels.md: it predates the need × channel table; "
                     "back to step 2 and let the owner review it")
    return warns


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
    s.add_argument("--needs-from", help="another GEO folder whose needs.jsonl this space shares (a second need space on one site)")
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
    s.add_argument("--origin", choices=sorted(ORIGINS), help="with --from-questions: only questions of this origin")
    s.add_argument("--ids", help="with --from-questions: comma-separated question ids to take as they are (a pilot)")
    s.add_argument("--weight", action="append", metavar="NEED=W",
                   help="with --from-questions: share of seats per need (repeatable; unnamed needs weigh 1)")
    s.add_argument("--append", action="store_true", help="add to samples.jsonl, skipping questions already in it")
    s.add_argument("--pool", help="JSONL of candidate rows {combo, url?, stratum?}: sample them, spread over strata")
    s.add_argument("--tool-share", type=float, default=None,
                   help="combinations: share of samples whose opening asks for a tool, site or app (angle recommend); "
                        f"default {TOOL_SHARE_CAPABILITY} for a capability space, {TOOL_SHARE} otherwise")
    sub.add_parser("probes")
    s = sub.add_parser("report")
    s.add_argument("--threshold", type=float, default=0.33)
    s.add_argument("--where", action="append", metavar="KEY=VALUE",
                   help="only runs whose field equals VALUE, e.g. slice=chatgpt-instant (repeatable)")
    s.add_argument("--include-extra", action="store_true",
                   help="count the runs-*.jsonl sets in the main numbers (default: reported separately)")
    s = sub.add_parser("channels")
    s.add_argument("--force", action="store_true", help="rebuild the skeleton (loses edits)")
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
    sub.add_parser("queries")
    s = sub.add_parser("slots")
    s.add_argument("--from", dest="from_", action="append", metavar="FILE",
                   help="real searches: CSV/JSONL with q|query|term and n|count, or text, one per line (repeatable)")
    s.add_argument("--top", type=int, default=40, help="how many unassigned words to list")
    a = p.parse_args(argv)
    st = State(a.root, a.geo_dir)
    {"init": cmd_init, "needs": cmd_needs, "bank": cmd_bank, "space": cmd_space, "sample": cmd_sample, "queries": cmd_queries, "slots": cmd_slots,
     "probes": cmd_probes, "report": cmd_report, "channels": cmd_channels, "decide": cmd_decide, "extend": cmd_extend,
     "check": cmd_check}[a.cmd](st, a)


if __name__ == "__main__":
    main()
