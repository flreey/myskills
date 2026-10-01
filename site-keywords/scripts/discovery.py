#!/usr/bin/env python3
"""Search demand discovery engine (Python stdlib only).

State lives under <root>/seo/. The observation pool is append-only and every keyword in it
comes from an external source; model output never becomes an observation. Seeds and concept
triage drive recursive expansion; rounds measure yield so discovery knows when to stop.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import http.client
import io
import json
import os
import random
import re
import shutil
import signal
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

S = "search-demand"

DEFAULT_CONFIG = {
    "schema": f"{S}/config@1",
    "market": {"country": "US", "language": "en"},
    "discovery": {
        "engines": ["google", "youtube", "bing"],
        "level": "standard",
        "max_requests_per_run": 600,
        "max_seconds_per_run": 1800,
        "delay_seconds": [1.0, 1.3],
        "cache_ttl_days": 7,
        "max_depth": 2,
        "alpha_top_seeds": 20,
        "prefixes": ["free", "best"],
        "suffixes": ["for", "without", "with", "like", "vs"],
        "stop_yield": 0.02,
        "stop_rounds": 2,
        "modifier_gate_min_base": 5,
        "modifier_early_stop_after": 3,
        "modifier_early_stop_min_new": 3,
        "concept_min_count": 2,
        "triage_batch": 80,
    },
}

DEFAULT_BOUNDARY = {
    "schema": f"{S}/boundary@1",
    "version": 1,
    "updated_at": None,
    "product": {"name": "", "summary": "", "url": ""},
    "rings": {"in": [], "adjacent": [], "out": []},
    "head_terms": [],
    "expression_templates": [],
    "modifiers": {},
    "adjacent_terms": [],
    "out_terms": [],
    "inventory": [],
    "question_templates": [],
    "competitors": [],
    "taxonomies": [],
    "open_questions": [],
}

KINDS = {
    "search_suggestion",
    "related_search",
    "historical_volume",
    "trend_related",
    "gsc_impression",
    "onsite_request",
    "external_reference",
}
SEED_ORIGINS = ["gsc", "onsite", "inventory", "reviewed_concept", "topdown", "taxonomy", "user"]
LEVELS = {"quick": ["base"], "standard": ["base", "modifiers"], "deep": ["base", "modifiers", "alpha"]}
GENERIC_MODIFIERS = [
    "free", "download", "downloads", "best", "top", "online", "new", "latest", "hd", "4k",
    "official", "cheap", "for free", "free download",
]
STOPWORDS = set(
    "a an the of for to with without and or vs versus by from at is are be what how why when "
    "where which who do does did can could should i my your me you it its this that these those like "
    "into onto about".split()
)
# particles such as over/on/off/in/up/no change meaning ("game over", "fade in", "power off"); they stay
# in entity keys and concept residuals. Only these pure function words are dropped from entity keys.
ENTITY_STOP = set("a an the of for to with and or by from at into onto is are be my your its this that".split())
LEADING_STOP = STOPWORDS | set("over under on off in out up down no not".split())  # leading particles carry no meaning
SITEMAP_STOP = set(
    "category categories cat tag tags page pages p search download downloads en us uk de fr es it "
    "index html htm php amp www item items detail details product products".split()
)
ENGINE_SOURCE = {"google": "google_suggest", "youtube": "youtube_suggest", "bing": "bing_suggest"}
ENGINE_HOST = {"google": "suggestqueries.google.com", "youtube": "suggestqueries.google.com", "bing": "api.bing.com"}
RETRY_BACKOFF = [5, 15, 45, 120, 300]  # seconds; network errors (flaky proxies) retry, blocks (403/429/503/non-JSON) pause at once


# ---------------------------------------------------------------- utilities

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def die(msg: str, code: int = 2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def sha(text: str, n: int = 16) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def norm(text) -> str:
    t = unicodedata.normalize("NFKC", str(text)).lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t.strip(" \t\"'`.,;:!?()[]{}<>")


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:'[^\W_]+)?", norm(text))


def stem(tok: str) -> str:
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def stem_tuple(text: str) -> tuple:
    return tuple(stem(t) for t in tokens(text))


def contains_seq(hay: tuple, needle: tuple) -> int:
    """Return start index of contiguous needle in hay, or -1."""
    n = len(needle)
    if not n or n > len(hay):
        return -1
    for i in range(len(hay) - n + 1):
        if hay[i : i + n] == needle:
            return i
    return -1


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                die(f"{path}:{i} invalid JSON: {exc}")
    return out


def append_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"{path} invalid JSON: {exc}")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def deep_merge(base: dict, override: dict) -> dict:
    out = json.loads(json.dumps(base))
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def emit(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


class Paths:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.seo = self.root / "seo"
        self.config = self.seo / "config.json"
        self.boundary = self.seo / "boundary.json"
        self.d = self.seo / "discovery"
        self.state = self.d / "state.json"
        self.seeds = self.d / "seeds.jsonl"
        self.obs = self.d / "observations.jsonl"
        self.concepts = self.d / "concepts.jsonl"
        self.runs = self.d / "runs.jsonl"
        self.cache = self.d / "cache"
        self.raw = self.d / "raw"
        self.work = self.seo / "work"


def require_init(p: Paths) -> dict:
    state = read_json(p.state)
    if not state:
        die(f"{p.d} is not initialized; run: discovery.py --root {p.root} init")
    return state


def load_config(p: Paths) -> dict:
    return deep_merge(DEFAULT_CONFIG, read_json(p.config, {}))


def load_boundary(p: Paths) -> dict:
    return deep_merge(DEFAULT_BOUNDARY, read_json(p.boundary, {}))


def market_of(cfg: dict, args) -> dict:
    m = dict(cfg["market"])
    if getattr(args, "country", None):
        m["country"] = args.country.upper()
    if getattr(args, "language", None):
        m["language"] = args.language.lower()
    return m


def parse_period(text: str | None):
    if not text:
        return None
    m = re.fullmatch(r"(\d{4}-\d{2}(?:-\d{2})?)\.\.(\d{4}-\d{2}(?:-\d{2})?)", text.strip())
    if not m:
        die(f"--period must look like 2026-06-01..2026-08-31 (got {text!r})")
    return {"start": m.group(1), "end": m.group(2)}


def obs_id(keyword, source, ref, market, period) -> str:
    p = period or {}
    key = "\x1f".join([keyword, source, ref, market.get("country", ""), market.get("language", ""),
                       p.get("start", ""), p.get("end", "")])
    return "obs_" + sha(key)


def make_obs(keyword, raw, source, kind, ref, market, period, metrics, run, via=None) -> dict:
    return {
        "schema": f"{S}/observation@1",
        "id": obs_id(keyword, source, ref, market, period),
        "keyword": keyword,
        "raw": raw,
        "source": source,
        "kind": kind,
        "source_ref": ref,
        "market": market,
        "period": period,
        "metrics": metrics or {},
        "via": via,
        "run": run,
        "observed_at": now(),
    }


class Pool:
    """In-memory view of the observation pool for dedup and novelty checks."""

    def __init__(self, p: Paths):
        self.p = p
        self.ids = set()
        self.keywords = set()
        self.base_counts = defaultdict(set)  # (seed_id, source) -> distinct keywords from base queries
        for o in read_jsonl(p.obs):
            self.ids.add(o["id"])
            self.keywords.add(o["keyword"])
            self._track(o)
        self.buffer = []

    def _track(self, obs: dict):
        via = obs.get("via") or {}
        if via.get("group") == "base":
            self.base_counts[(via.get("seed_id"), obs["source"])].add(obs["keyword"])

    def add(self, obs: dict) -> tuple[bool, bool]:
        """Return (new_observation, new_keyword)."""
        self._track(obs)
        if obs["id"] in self.ids:
            return False, False
        new_kw = obs["keyword"] not in self.keywords
        self.ids.add(obs["id"])
        self.keywords.add(obs["keyword"])
        self.buffer.append(obs)
        if len(self.buffer) >= 200:
            self.flush()
        return True, new_kw

    def flush(self):
        if self.buffer:
            append_jsonl(self.p.obs, self.buffer)
            self.buffer = []


def lexicon(boundary: dict) -> set:
    phrases = list(GENERIC_MODIFIERS) + list(boundary.get("head_terms", []))
    for values in (boundary.get("modifiers") or {}).values():
        phrases.extend(values)
    return {stem_tuple(x) for x in phrases if stem_tuple(x)}


BOUNDARY_FIELDS = {"modifier": "modifiers", "head_term": "head_terms", "adjacent": "adjacent_terms", "out": "out_terms"}
DECISION_FIELD = {"modifier": "modifier", "head_term": "head_term", "adjacent": "adjacent", "out": "out"}


def boundary_lists(b: dict, field: str, axis=None) -> list[list]:
    """The boundary list(s) a triage field writes to; modifiers without an axis means every axis."""
    if field == "modifier":
        mods = b.setdefault("modifiers", {})
        return [mods[axis]] if axis and axis in mods else ([] if axis else list(mods.values()))
    return [b.setdefault(BOUNDARY_FIELDS[field], [])]


def boundary_list(b: dict, field: str, axis=None, create=False, all_axes=False):
    if field == "modifier":
        if all_axes and not axis:
            return [t for lst in b.get("modifiers", {}).values() for t in lst]
        if create:
            return b.setdefault("modifiers", {}).setdefault(axis or "_generic", [])
        return b.get("modifiers", {}).get(axis or "_generic", [])
    return b.setdefault(BOUNDARY_FIELDS[field], [])


def phrase_set(items) -> list[tuple]:
    return [t for t in (stem_tuple(x) for x in items or []) if t]


def matches_any(stemmed: tuple, phrases: list[tuple]) -> bool:
    return any(contains_seq(stemmed, ph) >= 0 for ph in phrases)


def strip_lexicon(toks: list[str], lex: set) -> list[str]:
    """Remove lexicon phrases (longest first), stopwords and numbers; keep order."""
    st = [stem(t) for t in toks]
    keep = [True] * len(toks)
    i = 0
    while i < len(st):
        hit = 0
        for n in (4, 3, 2, 1):
            if i + n <= len(st) and tuple(st[i : i + n]) in lex:
                hit = n
                break
        if hit:
            for j in range(i, i + hit):
                keep[j] = False
            i += hit
        else:
            i += 1
    out = []
    for t, k in zip(toks, keep):
        if not k or t in STOPWORDS or re.fullmatch(r"\d+", t):
            continue
        out.append(t)
    return out


def read_text_any(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16")
    if data[:200].count(b"\x00") > 20:
        try:
            return data.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8-sig", errors="replace")


def file_sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def keep_raw(p: Paths, source: str, path: Path) -> str:
    digest = file_sha(path)[:8]
    dest = p.raw / source / f"{datetime.now():%Y%m%d}-{digest}-{path.name}"
    if not any((p.raw / source).glob(f"*-{digest}-{path.name}")):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return digest


def parse_volume(text):
    if text is None:
        return None
    t = str(text).strip().replace(",", "").replace("–", "-").replace("—", "-")
    if not t or t in {"-", "--", "n/a", "N/A"}:
        return None

    def num(x):
        x = x.strip().upper()
        mult = 1
        if x.endswith("K"):
            mult, x = 1000, x[:-1]
        elif x.endswith("M"):
            mult, x = 1_000_000, x[:-1]
        try:
            return int(float(x) * mult)
        except ValueError:
            return None

    if "-" in t:
        lo, hi = (num(x) for x in t.split("-", 1))
        if lo is not None and hi is not None:
            return {"low": lo, "high": hi}
        return None
    v = num(t)
    return None if v is None else {"low": v, "high": v}


def month_end(ym: datetime) -> str:
    nxt = (ym.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (nxt - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- state helpers

def load_seeds(p: Paths) -> list[dict]:
    return read_jsonl(p.seeds)


def seed_record(text, origin, ring, depth, run, parent=None, evidence=None, note=None, aliases=None) -> dict:
    t = norm(text)
    return {
        "aliases": sorted({norm(a) for a in aliases or [] if norm(a) and norm(a) != t}),
        "schema": f"{S}/seed@1",
        "id": "seed_" + sha(t, 12),
        "text": t,
        "origin": origin,
        "ring": ring,
        "depth": depth,
        "parent_seed_id": parent,
        "evidence": evidence or [],
        "note": note,
        "status": "pending",
        "expanded": {},
        "stats": {},
        "added_run": run,
        "added_at": now(),
    }


def log_run(p: Paths, entry: dict) -> None:
    append_jsonl(p.runs, [dict(entry, at=now())])


# ---------------------------------------------------------------- commands

def cmd_init(args):
    p = Paths(args.root)
    for d in (p.d, p.cache, p.raw, p.work):
        d.mkdir(parents=True, exist_ok=True)
    created = []
    if not p.config.exists():
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        if args.country:
            cfg["market"]["country"] = args.country.upper()
        if args.language:
            cfg["market"]["language"] = args.language.lower()
        write_json(p.config, cfg)
        created.append(str(p.config))
    if not p.boundary.exists():
        b = json.loads(json.dumps(DEFAULT_BOUNDARY))
        b["updated_at"] = now()
        write_json(p.boundary, b)
        created.append(str(p.boundary))
    gi = p.seo / ".gitignore"
    if not gi.exists():
        gi.write_text(
            "# search-demand: caches, raw exports and derived work files stay local\n"
            "discovery/cache/\ndiscovery/raw/\nmapper/evidence/gsc/\nwork/\n*.tmp\n",
            encoding="utf-8",
        )
        created.append(str(gi))
    if not p.state.exists():
        write_json(p.state, {"schema": f"{S}/discovery-state@1", "run": 1, "run_started_at": now()})
        created.append(str(p.state))
    emit({"initialized": str(p.seo), "created": created,
          "next": "fill seo/boundary.json from bootstrap research, then seed add"})


def cmd_seed(args):
    p = Paths(args.root)
    state = require_init(p)
    if args.action == "review":
        return seed_review(p, args)
    if args.action == "apply-review":
        return seed_apply_review(p, state, args)
    if args.action == "aliases":
        return seed_aliases(p, state, args)
    seeds = load_seeds(p)
    by_text = {s["text"]: s for s in seeds}
    if args.action == "list":
        rows = [s for s in seeds if not args.status or s["status"] == args.status]
        emit([{k: s[k] for k in ("id", "text", "origin", "ring", "depth", "status")} for s in rows])
        return
    if args.action == "reject":
        changed = 0
        for t in args.text or []:
            s = by_text.get(norm(t))
            if s:
                s["status"] = "rejected"
                changed += 1
        write_jsonl(p.seeds, seeds)
        emit({"rejected": changed})
        return
    items = []
    if args.file:
        data = read_json(Path(args.file))
        items = data.get("seeds", data) if isinstance(data, dict) else data
    for t in args.text or []:
        items.append({"text": t, "origin": args.origin, "ring": args.ring})
    added, skipped = [], []
    for it in items:
        origin = it.get("origin") or args.origin
        if origin not in SEED_ORIGINS:
            die(f"seed origin must be one of {SEED_ORIGINS} (got {origin!r})")
        if origin == "reviewed_concept":
            die("reviewed_concept seeds are created only by triage, which attaches evidence")
        ring = it.get("ring") or args.ring
        if ring not in ("in", "adjacent"):
            die("seed ring must be in or adjacent")
        rec = seed_record(it["text"], origin, ring, 0, state["run"], evidence=it.get("evidence"), note=it.get("note"),
                          aliases=it.get("aliases"))
        if it.get("status", "pending") not in ("pending", "parked"):
            die("seed file status must be pending or parked")
        rec["status"] = it.get("status", "pending")
        if not rec["text"]:
            continue
        if rec["text"] in by_text:
            skipped.append(rec["text"])
            continue
        by_text[rec["text"]] = rec
        seeds.append(rec)
        added.append(rec["text"])
    write_jsonl(p.seeds, seeds)
    emit({"added": len(added), "skipped_existing": len(skipped), "seeds_total": len(seeds), "added_texts": added[:50]})


def load_seed_review(p: Paths):
    rv = read_json(p.work / "seed-review.json")
    if not rv or rv.get("status") != "ready_for_review":
        die("no seed review yet: run consolidate (and probe) until it writes seo/work/seed-review.json")
    rows = {r["name"]: r for r in rv["review"] + rv["no_signal"]}
    decided = {}
    for d in read_jsonl(p.d / "seed-review-decisions.jsonl"):
        # decisions carry over by row name when a re-consolidation changes the review; the latest wins
        for n in d["names"]:
            if n in rows:
                decided[n] = dict(d, carried=d["review_hash"] != rv["review_hash"])
    return rv, rows, decided


def seed_review(p: Paths, args):
    """Show undecided consolidation rows with their evidence. Every row needs an explicit decision."""
    rv, rows, decided = load_seed_review(p)
    todo = [r for n, r in rows.items() if n not in decided]
    todo.sort(key=lambda r: (-(r["signal"] > 0 or bool(r["signal_leaves"])), -r["items"], r["name"]))
    batch = todo[: args.limit] if args.limit else todo
    active = sorted(x["text"] for x in load_seeds(p) if x["status"] in ("pending", "active", "exhausted"))
    sources = defaultdict(set)  # seed text -> rows that created it
    for d in read_jsonl(p.d / "seed-review-decisions.jsonl"):
        if d["action"] == "seed" and d.get("text"):
            sources[d["text"]].update(d["names"])
    stale = sorted(t for t in active if sources.get(t) and not sources[t] & set(rows))
    emit({
        "review_hash": rv["review_hash"], "rows_total": len(rows), "decided": len(decided),
        "carried_from_earlier_reviews": sum(1 for d in decided.values() if d.get("carried")), "undecided": len(todo),
        "actions": ["seed", "alias", "park", "out"],
        "stale_seeds": {"seeds": stale, "how": "their source rows vanished after re-consolidation; keep them, "
                        "or retire with `seed reject --text ...` when a renamed row now covers them"},
        "seeds_so_far": active,
        "rows": [{"name": r["name"], "kind": r["kind"], "signal": r["probe"], "items": r["items"],
                  "groups": len(r["groups"]), "aliases": r["aliases"][:30], "children": r["children"][:10],
                  "signal_leaves": r["signal_leaves"][:10], "samples": r["samples"][:6], "origins": r["origins"]}
                 for r in batch],
    })


def seed_apply_review(p: Paths, state: dict, args):
    """Apply explicit model decisions for consolidation rows; the command never decides on its own."""
    rv, rows, decided = load_seed_review(p)
    data = read_json(Path(args.file)) or {}
    if data.get("review_hash") != rv["review_hash"]:
        die("review_hash does not match the current seed-review.json; run `seed review` again")
    seeds = load_seeds(p)
    by_text = {x["text"]: x for x in seeds}
    errors, warnings = [], []
    seen = set()
    new_seed_texts = set()
    for i, d in enumerate(data.get("decisions", [])):
        names = d.get("names") or ([d["name"]] if d.get("name") else [])
        where = f"decision {i} ({d.get('action')} {names[:2]})"
        if d.get("action") not in ("seed", "alias", "park", "out"):
            errors.append(f"{where}: action must be seed|alias|park|out")
        if not d.get("reason"):
            errors.append(f"{where}: reason required")
        if not names:
            errors.append(f"{where}: names required")
        for n in names:
            if n not in rows:
                errors.append(f"{where}: unknown row {n!r}")
            elif n in seen:
                errors.append(f"{where}: row {n!r} decided twice in this file")
            elif n in decided and not args.revise:
                errors.append(f"{where}: row {n!r} already decided (use --revise to change it)")
            seen.add(n)
        if d.get("action") == "seed":
            text = norm(d.get("text") or (names[0] if len(names) == 1 else ""))
            if not text:
                errors.append(f"{where}: seed decisions over several rows need text")
            new_seed_texts.add(text)
            d["_text"] = text
            for pr in d.get("promote") or []:
                if not norm(pr.get("text", "")) or not pr.get("reason"):
                    errors.append(f"{where}: promote entries need text and reason")
                new_seed_texts.add(norm(pr.get("text", "")))
    active_texts = {t for t, x in by_text.items() if x["status"] in ("pending", "active", "exhausted")}
    for i, d in enumerate(data.get("decisions", [])):
        if d.get("action") == "alias":
            tgt = norm(d.get("target", ""))
            if tgt not in new_seed_texts | active_texts:
                errors.append(f"decision {i}: alias target {tgt!r} is not an active seed or a seed decided in this file")
            d["_target"] = tgt
    if errors:
        die("apply-review rejected:\n  " + "\n  ".join(errors[:60]))

    def ensure(text, origin, note):
        x = by_text.get(text)
        if x is None:
            x = seed_record(text, origin, "in", 0, state["run"], note=note)
            seeds.append(x)
            by_text[text] = x
        elif x["status"] in ("parked", "rejected"):
            x["status"] = "pending"
        return x

    def attach(x, names, add, drop):
        al = set(x.get("aliases") or [])
        for n in names:
            al.add(norm(n))
            al.update(norm(a) for a in rows[n]["aliases"])
        al.update(norm(a) for a in add or [])
        al -= {norm(a) for a in drop or []}
        al.discard(x["text"])
        x["aliases"] = sorted(a for a in al if a)

    counts = Counter()
    for d in data["decisions"]:
        names, act = d.get("names") or [d["name"]], d["action"]
        if act == "seed":
            x = ensure(d["_text"], d.get("origin", "inventory"), d["reason"])
            first_time = not any(n in decided for n in names)  # a revision only applies its own add/drop
            attach(x, names if first_time else [], d.get("add_aliases"), d.get("drop_aliases"))
            if d.get("confirm_aliases"):
                x["aliases_confirmed"] = sorted(set(x.get("aliases_confirmed") or []) | {norm(a) for a in d["confirm_aliases"]})
            for pr in d.get("promote") or []:
                ensure(norm(pr["text"]), d.get("origin", "inventory"), pr["reason"])
                counts["promoted"] += 1
        elif act == "park":
            for n in names:
                x = by_text.get(norm(n)) or ensure(norm(n), d.get("origin", "inventory"), d["reason"])
                if x["status"] == "pending" and not x.get("expanded"):
                    x["status"] = "parked"
        counts[act] += len(names)
    for d in data["decisions"]:  # aliases after seeds so same-file targets exist
        if d["action"] == "alias":
            names = d.get("names") or [d["name"]]
            first_time = not any(n in decided for n in names)
            attach(by_text[d["_target"]], names if first_time else [], d.get("add_aliases"), d.get("drop_aliases"))
    # ambiguity checks: the model resolves these, the command does not pick a side
    owners = defaultdict(set)
    live = [x for x in seeds if x["status"] in ("pending", "active", "exhausted")]
    live_texts = {x["text"] for x in live}
    for x in live:
        for a in x.get("aliases") or []:
            owners[a].add(x["text"])
    for a, o in owners.items():
        if len(o) > 1:
            errors.append(f"alias {a!r} is attached to several seeds {sorted(o)}; drop it where it does not belong")
        if a in live_texts:
            errors.append(f"alias {a!r} of {sorted(o)} is also a seed; drop the alias or merge the seed")
    if errors:
        die("apply-review rejected (nothing written):\n  " + "\n  ".join(errors[:60]))
    confirmed = {a for x in live for a in x.get("aliases_confirmed") or []}
    single = {a for a in owners if len(tokens(a)) == 1 and a not in confirmed}
    if single:
        # evidence, not a word list: a one-word alias that shows up under many different seeds' searches
        # would pull unrelated keywords into its seed during concept extraction
        spread = defaultdict(set)
        for o in read_jsonl(p.obs):
            src = (o.get("via") or {}).get("seed")
            if src:
                for w in set(tokens(o["keyword"])) & single:
                    spread[w].add(src)
        risky = sorted(((len(spread[a]), a, sorted(owners[a])[0]) for a in single if len(spread[a]) >= args.alias_spread),
                       reverse=True)
        warnings.append({"single_word_aliases": len(single),
                         "ambiguous_by_evidence": [{"alias": a, "seed": o, "seen_under_seeds": n} for n, a, o in risky[:80]],
                         "how": "drop the ones that are not specific to their seed (seed decision with --revise and drop_aliases)"})
    write_jsonl(p.seeds, seeds)
    log = []
    for d in data["decisions"]:
        log.append({"review_hash": rv["review_hash"], "names": d.get("names") or [d["name"]], "action": d["action"],
                    "text": d.get("_text"), "target": d.get("_target"), "reason": d["reason"], "at": now()})
    append_jsonl(p.d / "seed-review-decisions.jsonl", log)
    remaining = len(rows) - len(set(decided) | seen)
    emit({"applied": dict(counts), "undecided_rows": remaining, "active_seeds": len(live),
          "parked_seeds": sum(1 for x in seeds if x["status"] == "parked"), "warnings": warnings})


def seed_aliases(p: Paths, state: dict, args):
    """Alias hygiene on the current pool. Without --file: evidence report. With --file: apply model decisions."""
    seeds = load_seeds(p)
    live = [x for x in seeds if x["status"] in ("pending", "active", "exhausted")]
    by_text = {x["text"]: x for x in live}
    if args.file:
        data = read_json(Path(args.file)) or {}
        items = data.get("decisions", data) if isinstance(data, dict) else data
        errors = []
        for i, d in enumerate(items):
            x = by_text.get(norm(d.get("seed", "")))
            if not x:
                errors.append(f"decision {i}: {d.get('seed')!r} is not an active seed")
                continue
            if not d.get("reason") or not (d.get("drop") or d.get("confirm")):
                errors.append(f"decision {i} ({x['text']}): drop or confirm, and reason, are required")
            have = set(x.get("aliases") or [])
            for a in (d.get("drop") or []) + (d.get("confirm") or []):
                if norm(a) not in have:
                    errors.append(f"decision {i} ({x['text']}): {a!r} is not one of its aliases")
        if errors:
            die("alias review rejected:\n  " + "\n  ".join(errors[:60]))
        counts = Counter()
        for d in items:
            x = by_text[norm(d["seed"])]
            drop = {norm(a) for a in d.get("drop") or []}
            x["aliases"] = [a for a in x.get("aliases") or [] if a not in drop]
            x["aliases_confirmed"] = sorted((set(x.get("aliases_confirmed") or []) - drop)
                                            | {norm(a) for a in d.get("confirm") or []})
            counts["dropped"] += len(drop)
            counts["confirmed"] += len(d.get("confirm") or [])
        write_jsonl(p.seeds, seeds)
        log_run(p, {"type": "alias_review", "run": state["run"], **counts,
                    "decisions": [{k: d.get(k) for k in ("seed", "drop", "confirm", "reason")} for d in items]})
        emit({"applied": dict(counts)})
        return
    # evidence: which other seeds' searches produced keywords containing the alias
    kw_seeds = defaultdict(set)
    for o in read_jsonl(p.obs):
        src = (o.get("via") or {}).get("seed")
        kw_seeds[o["keyword"]].add(src or f"source:{o['source']}")
    index = defaultdict(list)  # first stem -> [(stemmed keyword, keyword)]
    for kw in kw_seeds:
        st = stem_tuple(kw)
        for t in set(st):
            index[t].append((st, kw))
    seed_stems = {x["text"]: stem_tuple(x["text"]) for x in live}
    rows = []
    for x in live:
        confirmed = set(x.get("aliases_confirmed") or [])
        for a in x.get("aliases") or []:
            ph = stem_tuple(a)
            if not ph or a in confirmed:
                continue
            hits = [kw for st, kw in index.get(ph[0], []) if contains_seq(st, ph) >= 0]
            other = {s for kw in hits for s in kw_seeds[kw]} - {x["text"]}
            inside = sorted(t for t, st in seed_stems.items() if t != x["text"] and contains_seq(st, ph) >= 0)
            if len(other) < args.alias_spread and not inside:
                continue
            foreign = [kw for kw in hits if not kw_seeds[kw] & {x["text"]}]
            rows.append({"seed": x["text"], "alias": a, "keywords": len(hits), "seen_under_other_seeds": len(other),
                         "inside_other_seed_names": inside[:8], "foreign_samples": sorted(foreign)[:6]})
    rows.sort(key=lambda r: (-len(r["inside_other_seed_names"]) - r["seen_under_other_seeds"], r["seed"]))
    lim = args.limit or 150
    emit({"flagged": len(rows), "shown": min(lim, len(rows)), "min_spread": args.alias_spread,
          "how": "an alias routes every keyword that contains it to its seed (concept extraction, mapper groups). "
                 "Drop aliases that are not specific to the seed; confirm true synonyms. "
                 "Write {decisions:[{seed, drop:[], confirm:[], reason}]} and run `seed aliases --file`.",
          "rows": rows[:lim]})


def seed_queries(seed: dict, group: str, boundary: dict, dc: dict) -> list[str]:
    text = seed["text"]
    heads = phrase_set(boundary.get("head_terms"))
    templates = boundary.get("expression_templates") or []
    if not templates or matches_any(stem_tuple(text), heads):
        exprs = [text]
    else:
        exprs = [norm(t.replace("{seed}", text)) for t in templates]
    exprs = list(dict.fromkeys(exprs))
    primary = exprs[0]
    if group == "base":
        return exprs
    if group == "modifiers":
        q = [f"{x} {primary}" for x in dc["prefixes"]] + [f"{primary} {x}" for x in dc["suffixes"]]
        q += [t.replace("{seed}", text) for t in boundary.get("question_templates") or []]
        return list(dict.fromkeys(norm(x) for x in q))
    if group == "alpha":
        return [f"{primary} {c}" for c in "abcdefghijklmnopqrstuvwxyz"]
    die(f"unknown query group {group}")


def suggest_url(engine: str, q: str, market: dict) -> str:
    lang, country = market["language"], market["country"]
    if engine == "google":
        return "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
            {"client": "firefox", "hl": lang, "gl": country.lower(), "q": q})
    if engine == "youtube":
        return "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
            {"client": "firefox", "ds": "yt", "hl": lang, "gl": country.lower(), "q": q})
    if engine == "bing":
        return "https://api.bing.com/osjson.aspx?" + urllib.parse.urlencode(
            {"query": q, "language": f"{lang}-{country}"})
    die(f"unknown engine {engine}")


class SuggestClient:
    """One persistent HTTPS connection per host (through the environment's proxy when set).

    Reusing the connection avoids a TLS handshake per request, which dominated latency through
    proxies and caused most of the connection resets.
    """

    def __init__(self):
        self.conns = {}

    def _conn(self, host: str):
        c = self.conns.get(host)
        if c is None:
            proxy = urllib.request.getproxies().get("https")
            if proxy and not urllib.request.proxy_bypass(host):
                pu = urllib.parse.urlparse(proxy if "://" in proxy else "http://" + proxy)
                c = http.client.HTTPSConnection(pu.hostname, pu.port or 80, timeout=15)  # CONNECT tunnel via proxy
                c.set_tunnel(host, 443)
            else:
                c = http.client.HTTPSConnection(host, 443, timeout=15)
            self.conns[host] = c
        return c

    def close(self, host: str):
        c = self.conns.pop(host, None)
        if c:
            c.close()

    def fetch(self, engine: str, q: str, market: dict):
        """Return (status, suggestions). status: ok | blocked | error."""
        u = urllib.parse.urlparse(suggest_url(engine, q, market))
        path = u.path + ("?" + u.query if u.query else "")
        try:
            c = self._conn(u.netloc)
            c.request("GET", path, headers={"User-Agent": f"Python-urllib/{sys.version_info[0]}.{sys.version_info[1]}"})
            r = c.getresponse()
            body = r.read()
            charset = r.headers.get_content_charset() or "utf-8"
            if r.status != 200:
                if r.getheader("connection", "").lower() == "close":
                    self.close(u.netloc)
                return ("blocked" if r.status in (403, 429, 503) else "error"), f"HTTP {r.status}"
            if r.getheader("connection", "").lower() == "close":
                self.close(u.netloc)
        except (http.client.HTTPException, OSError) as exc:
            self.close(u.netloc)
            return "error", str(exc) or exc.__class__.__name__
        try:
            data = json.loads(body.decode(charset, errors="replace"))
            items = data[1]
            if not isinstance(items, list):
                raise ValueError("unexpected shape")
        except (ValueError, IndexError, TypeError, json.JSONDecodeError):
            return "blocked", "non-JSON response (consent page, captcha or format change)"
        return "ok", [str(x) for x in items if isinstance(x, str)]


def fetch_suggest(engine: str, q: str, market: dict):
    """One-off fetch (tests, ad-hoc use); harvest lanes use a persistent SuggestClient."""
    client = SuggestClient()
    try:
        return client.fetch(engine, q, market)
    finally:
        for h in list(client.conns):
            client.close(h)


class SuggestCache:
    def __init__(self, p: Paths, engine: str, ttl_days: int):
        self.path = p.cache / f"suggest-{engine}.jsonl"
        self.ttl = timedelta(days=ttl_days)
        self.rows = {}
        for r in read_jsonl(self.path):
            self.rows[(r["query"], r["country"], r["language"])] = r

    def get(self, q, market):
        r = self.rows.get((q, market["country"], market["language"]))
        if not r:
            return None
        fetched = datetime.fromisoformat(r["fetched_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - fetched > self.ttl:
            return None
        return r["suggestions"]

    def put(self, q, market, suggestions):
        r = {"query": q, "country": market["country"], "language": market["language"],
             "fetched_at": now(), "suggestions": suggestions}
        self.rows[(q, market["country"], market["language"])] = r
        append_jsonl(self.path, [r])


class Harvest:
    """Result and shared counters of one harvest run."""

    def __init__(self, engines):
        self.counters = Counter()
        self.per_engine = {e: {"requests": 0, "cache_hits": 0, "new_keywords": 0, "gated_queries": 0,
                               "early_stopped_queries": 0} for e in engines}
        self.paused = {}
        self.stopped_by = "done"
        self.lanes = {}
        self.left = 0
        self.elapsed = 0.0


def harvest(p: Paths, dc: dict, market: dict, queues: dict, max_requests: int, max_seconds: int,
            record, skip=None, on_exit=None) -> Harvest:
    """Fetch every queued query with one worker per host.

    queues: {engine: deque[task]} where task[-1] is the query text. Each host keeps its own
    start-to-start delay (>= 1 s); network errors back off, blocks pause the engine.
    record(engine, task, suggestions, h) and skip(engine, task, h) run under a shared lock.
    """
    lo, hi = dc["delay_seconds"]
    if lo < 1.0:
        die("delay_seconds lower bound must stay >= 1.0")
    engines = list(queues)
    h = Harvest(engines)
    caches = {e: SuggestCache(p, e, dc["cache_ttl_days"]) for e in engines}
    lanes = defaultdict(list)
    for e in engines:
        lanes[ENGINE_HOST[e]].append(e)
    h.lanes = dict(lanes)
    lock = threading.Lock()
    stop = threading.Event()
    started = time.monotonic()

    def lane_body(lane_engines):
        client = SuggestClient()
        last = 0.0
        retry_at = {e: 0.0 for e in lane_engines}
        errors = Counter()
        turn = 0
        while not stop.is_set():
            active = [e for e in lane_engines if e not in h.paused and queues[e]]
            if not active:
                return
            ready = [e for e in active if retry_at[e] <= time.monotonic()]
            if not ready:
                stop.wait(max(0.0, min(retry_at[e] for e in active) - time.monotonic()))
                continue
            e = ready[turn % len(ready)]
            turn += 1
            task = queues[e][0]
            if skip:
                with lock:
                    if skip(e, task, h):
                        queues[e].popleft()
                        continue
            q = task[-1]
            cached = caches[e].get(q, market)
            if cached is None:
                with lock:
                    if h.counters["requests"] >= max_requests:
                        h.stopped_by = "max_requests"
                        stop.set()
                        return
                    if time.monotonic() - started >= max_seconds:
                        h.stopped_by = "max_seconds"
                        stop.set()
                        return
                    h.counters["requests"] += 1
                    h.per_engine[e]["requests"] += 1
                wait = last + random.uniform(lo, hi) - time.monotonic()
                if wait > 0 and stop.wait(wait):
                    return
                last = time.monotonic()  # spacing is start-to-start: at most one request per delay per host
                status, result = client.fetch(e, q, market)
                if status != "ok":
                    errors[e] += 1
                    if status == "blocked" or errors[e] > len(RETRY_BACKOFF):
                        with lock:
                            h.paused[e] = result
                        print(f"[{e}] paused: {result}", file=sys.stderr)
                    else:
                        delay = RETRY_BACKOFF[errors[e] - 1]
                        retry_at[e] = time.monotonic() + delay
                        print(f"[{e}] transient error ({result}); retry in {delay}s", file=sys.stderr)
                    continue
                errors[e] = 0
                caches[e].put(q, market, result)
                suggestions = result
            else:
                with lock:
                    h.counters["cache_hits"] += 1
                    h.per_engine[e]["cache_hits"] += 1
                suggestions = cached
            with lock:
                queues[e].popleft()
                record(e, task, suggestions, h)

    def lane(lane_engines):
        try:
            lane_body(lane_engines)
        except Exception as exc:  # noqa: BLE001 - surface the failure instead of dying silently
            with lock:
                for e in lane_engines:
                    h.paused.setdefault(e, f"crash: {exc!r}")
            print(f"[{'/'.join(lane_engines)}] crashed: {exc!r}", file=sys.stderr)

    threads = [threading.Thread(target=lane, args=(es,), daemon=True) for es in lanes.values()]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.5)
    except KeyboardInterrupt:
        h.stopped_by = "interrupted"
        stop.set()
        for t in threads:
            t.join(timeout=20)
    finally:
        with lock:
            if on_exit:
                on_exit()
    h.left = sum(len(q) for q in queues.values())
    if h.stopped_by == "done" and h.left:
        h.stopped_by = "paused"
    h.elapsed = round(time.monotonic() - started, 1)
    return h


def cmd_suggest(args):
    p = Paths(args.root)
    state = require_init(p)
    cfg = load_config(p)
    dc = cfg["discovery"]
    boundary = load_boundary(p)
    market = market_of(cfg, args)
    engines = args.engine or dc["engines"]
    for e in engines:
        if e not in ENGINE_SOURCE:
            die(f"engine must be one of {sorted(ENGINE_SOURCE)}")
    level = args.level or dc["level"]
    groups = LEVELS[level]
    max_requests = args.max_requests or dc["max_requests_per_run"]
    max_seconds = args.max_seconds or dc["max_seconds_per_run"]

    seeds = load_seeds(p)
    wanted = {norm(t) for t in args.seed or []}
    missing = wanted - {s["text"] for s in seeds}
    if missing:
        die(f"unknown seeds (add them first): {sorted(missing)}")
    order = {o: i for i, o in enumerate(SEED_ORIGINS)}
    pool_seeds = [
        s for s in seeds
        if s["status"] in ("pending", "active") and s["ring"] == "in" and s["depth"] <= dc["max_depth"]
        and (not wanted or s["text"] in wanted)
    ]
    pool_seeds.sort(key=lambda s: (s["depth"], order.get(s["origin"], 99), s.get("added_at", "")))
    if args.max_seeds:
        pool_seeds = pool_seeds[: args.max_seeds]

    alpha_ok = set()
    if "alpha" in groups:
        if args.all_seeds or wanted:
            alpha_ok = {s["id"] for s in pool_seeds}
        else:
            def productivity(s):
                st = s.get("stats", {})
                req = sum(v.get("requests", 0) for v in st.values())
                new = sum(v.get("new_keywords", 0) for v in st.values())
                return new / req if req else 0.0
            ready = [s for s in pool_seeds if all("modifiers" in s.get("expanded", {}).get(e, []) for e in engines)]
            ready.sort(key=productivity, reverse=True)
            alpha_ok = {s["id"] for s in ready[: dc["alpha_top_seeds"]]}

    by_id = {s["id"]: s for s in seeds}
    queues = {e: deque() for e in engines}
    remaining = Counter()
    for s in pool_seeds:
        for g in groups:
            if g == "alpha" and s["id"] not in alpha_ok:
                continue
            for e in engines:
                if g in s.get("expanded", {}).get(e, []) and not args.refresh:
                    continue
                for q in seed_queries(s, g, boundary, dc):
                    queues[e].append((s["id"], g, q))
                    remaining[(s["id"], e, g)] += 1

    total_tasks = sum(len(q) for q in queues.values())
    if args.dry_run:
        emit({"level": level, "engines": engines, "market": market, "seeds": len(pool_seeds),
              "queries": total_tasks, "sample": [t[2] for q in queues.values() for t in list(q)[:5]]})
        return

    gate_min = 0 if args.no_gate else int(dc.get("modifier_gate_min_base") or 0)
    stop_after = 0 if args.no_gate else int(dc.get("modifier_early_stop_after") or 0)
    stop_min_new = int(dc.get("modifier_early_stop_min_new") or 0)
    pool = Pool(p)
    gated_seeds = set()

    def finish(sid, e, g, gate_info=None):
        remaining[(sid, e, g)] -= 1
        if remaining[(sid, e, g)] == 0:
            s = by_id[sid]
            done = s.setdefault("expanded", {}).setdefault(e, [])
            if g not in done:
                done.append(g)
            if gate_info:
                s.setdefault("gated", {})[e] = gate_info
                gated_seeds.add(sid)
            s["status"] = "active"
            if all(set(LEVELS["deep"]) <= set(s["expanded"].get(x, [])) for x in engines):
                s["status"] = "exhausted"

    def skip(e, task, h):
        sid, g, _ = task
        if g != "modifiers" or args.no_gate:
            return False
        st = by_id[sid].get("stats", {}).get(e, {})
        if gate_min and "base" in by_id[sid].get("expanded", {}).get(e, []):
            n = len(pool.base_counts[(sid, ENGINE_SOURCE[e])])
            if n < gate_min:
                h.per_engine[e]["gated_queries"] += 1
                finish(sid, e, g, {"group": "modifiers", "reason": "thin_base", "base_distinct": n, "min": gate_min})
                return True
        # early stop: the first modifier queries (highest-yield patterns first) found almost nothing new
        if stop_after and st.get("modifier_queries", 0) >= stop_after and st.get("modifier_new", 0) < stop_min_new:
            h.per_engine[e]["early_stopped_queries"] += 1
            finish(sid, e, g, {"group": "modifiers", "reason": "early_stop", "after": st.get("modifier_queries", 0),
                               "new": st.get("modifier_new", 0)})
            return True
        return False

    def record(e, task, suggestions, h):
        sid, g, q = task
        s = by_id[sid]
        st = s.setdefault("stats", {}).setdefault(e, {"requests": 0, "suggestions": 0, "new_keywords": 0})
        st["requests"] += 1
        if g == "modifiers":
            st["modifier_queries"] = st.get("modifier_queries", 0) + 1
            st.setdefault("modifier_new", 0)  # empty answers still count as a modifier query with 0 new
        for rank, raw in enumerate(suggestions):
            kw = norm(raw)
            if not kw:
                continue
            o = make_obs(kw, raw, ENGINE_SOURCE[e], "search_suggestion", f"suggest:{e}:{q}", market, None,
                         {"rank": rank}, state["run"], via={"seed_id": sid, "seed": s["text"], "query": q, "group": g})
            is_new, is_new_kw = pool.add(o)
            h.counters["new_observations"] += is_new
            h.counters["new_keywords"] += is_new_kw
            h.per_engine[e]["new_keywords"] += is_new_kw
            st["suggestions"] += 1
            st["new_keywords"] += is_new_kw
            if g == "modifiers":
                st["modifier_new"] = st.get("modifier_new", 0) + is_new_kw
        finish(sid, e, g)

    h = harvest(p, dc, market, queues, max_requests, max_seconds, record, skip,
                on_exit=lambda: (pool.flush(), write_jsonl(p.seeds, seeds)))
    summary = {
        "type": "suggest", "run": state["run"], "level": level, "engines": engines, "market": market,
        "lanes": h.lanes, "modifier_gate_min_base": gate_min, "requests": h.counters["requests"],
        "cache_hits": h.counters["cache_hits"], "new_observations": h.counters["new_observations"],
        "new_keywords": h.counters["new_keywords"], "per_engine": h.per_engine, "gated_seeds": len(gated_seeds),
        "paused": h.paused, "stopped_by": h.stopped_by, "queries_left": h.left, "elapsed_seconds": h.elapsed,
    }
    log_run(p, summary)
    emit(summary)
    if h.paused and h.left and not any(queues[e] for e in engines if e not in h.paused):
        sys.exit(3)


# ---------------------------------------------------------------- imports

def header_index(lines: list[str], names: set) -> int:
    for i, line in enumerate(lines[:50]):
        cells = [c.strip().strip('"').lower() for c in re.split(r"[\t,]", line)]
        if any(c in names for c in cells):
            return i
    return -1


def table(lines: list[str], idx: int):
    delim = "\t" if "\t" in lines[idx] else ","
    reader = csv.reader(lines[idx:], delimiter=delim)
    header = [h.strip().lower() for h in next(reader)]
    return header, [r for r in reader if any(c.strip() for c in r)]


KEYWORD_COLS = {"keyword", "keywords", "query", "queries", "top queries", "search term", "search query",
                "term", "suggestion", "search terms"}
VOLUME_COLS = ["avg. monthly searches", "avg monthly searches", "search volume", "volume", "monthly searches",
               "global volume"]


def col(header, *names):
    for n in names:
        if n in header:
            return header.index(n)
    return -1


def import_gkp(path, args, market):
    lines = read_text_any(path).splitlines()
    idx = header_index(lines, {"keyword"})
    if idx < 0:
        die("Keyword Planner export: no 'Keyword' header found")
    header, rows = table(lines, idx)
    k = col(header, "keyword")
    v = col(header, *VOLUME_COLS)
    months = []
    for i, h in enumerate(header):
        m = re.fullmatch(r"searches:\s*([a-z]{3}) (\d{4})", h)
        if m:
            months.append((i, datetime.strptime(f"{m.group(1)} {m.group(2)}", "%b %Y")))
    period = parse_period(args.period)
    if not period:
        if not months:
            die("this Keyword Planner export has no monthly columns; pass --period YYYY-MM..YYYY-MM")
        first, last = min(m[1] for m in months), max(m[1] for m in months)
        period = {"start": first.strftime("%Y-%m-%d"), "end": month_end(last)}
    out = []
    for r in rows:
        if k >= len(r) or not r[k].strip():
            continue
        metrics = {"avg_monthly_searches": parse_volume(r[v]) if 0 <= v < len(r) else None}
        for name, key in (("competition", "competition"), ("competition (indexed value)", "competition_index"),
                          ("top of page bid (low range)", "bid_low"), ("top of page bid (high range)", "bid_high")):
            c = col(header, name)
            if 0 <= c < len(r) and r[c].strip():
                metrics[key] = r[c].strip()
        if months:
            metrics["monthly"] = {d.strftime("%Y-%m"): (parse_volume(r[i]) or {}).get("low")
                                  for i, d in months if i < len(r)}
        out.append((r[k], "historical_volume", metrics, period, None))
    return out


def import_gsc(path, args):
    filters = {}
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = {n.lower(): n for n in z.namelist()}
            qn = next((names[n] for n in names if n.endswith("queries.csv")), None)
            if not qn:
                die("GSC zip has no Queries.csv")
            text = z.read(qn).decode("utf-8-sig", errors="replace")
            fn = next((names[n] for n in names if n.endswith("filters.csv")), None)
            if fn:
                for row in csv.reader(z.read(fn).decode("utf-8-sig", errors="replace").splitlines()[1:]):
                    if len(row) >= 2:
                        filters[row[0].strip().lower()] = row[1].strip()
    else:
        text = read_text_any(path)
    lines = text.splitlines()
    idx = header_index(lines, {"top queries", "query", "queries"})
    if idx < 0:
        die("GSC export: no query header found")
    header, rows = table(lines, idx)
    k = col(header, "top queries", "query", "queries")
    period = parse_period(args.period)
    if not period:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", filters.get("date", ""))
        if len(dates) == 2:
            period = {"start": dates[0], "end": dates[1]}
        else:
            die(f"GSC export date range is {filters.get('date', 'unknown')!r}; pass --period START..END")
    page = args.page or filters.get("page")
    out = []
    for r in rows:
        if k >= len(r) or not r[k].strip():
            continue
        metrics = {}
        for name in ("clicks", "impressions", "ctr", "position"):
            c = col(header, name)
            if 0 <= c < len(r):
                val = r[c].strip().rstrip("%")
                try:
                    metrics[name] = float(val)
                except ValueError:
                    metrics[name] = None
        if page:
            metrics["page_filter"] = page
        out.append((r[k], "gsc_impression", metrics, period, None))
    return out


def import_trends(path, args):
    section = None
    out = []
    period = parse_period(args.period)
    for line in read_text_any(path).splitlines():
        s = line.strip()
        if s.upper() in ("TOP", "RISING"):
            section = s.lower()
            continue
        if not section or "," not in s:
            continue
        q, value = s.rsplit(",", 1)
        q = q.strip().strip('"')
        if not q or q.lower() in ("query", "top", "rising"):
            continue
        out.append((q, "trend_related", {"section": section, "value": value.strip()}, period, None))
    if not out:
        die("no TOP/RISING related queries found in Trends CSV")
    return out


def import_csv(path, args):
    lines = read_text_any(path).splitlines()
    idx = header_index(lines, KEYWORD_COLS)
    if idx < 0:
        die(f"no keyword column found (accepted: {sorted(KEYWORD_COLS)})")
    header, rows = table(lines, idx)
    k = col(header, *KEYWORD_COLS)
    v = col(header, *VOLUME_COLS)
    period = parse_period(args.period)
    warned = False
    out = []
    for r in rows:
        if k >= len(r) or not r[k].strip():
            continue
        metrics = {h: r[i].strip() for i, h in enumerate(header) if i != k and i < len(r) and r[i].strip()}
        kind = args.kind or "external_reference"
        if 0 <= v < len(r) and r[v].strip():
            vol = parse_volume(r[v])
            if period:
                kind = "historical_volume"
                metrics["avg_monthly_searches"] = vol
            else:
                metrics["volume_unperiodized"] = vol
                warned = True
        out.append((r[k], kind, metrics, period, None))
    if warned:
        print("warning: volume column without --period kept as volume_unperiodized (not historical_volume)",
              file=sys.stderr)
    return out


def import_json(path, args):
    data = read_json(path)
    rows = data.get("observations", []) if isinstance(data, dict) else data
    out = []
    for r in rows:
        if not isinstance(r, dict) or not r.get("keyword"):
            die("JSON observations need a keyword field")
        kind = r.get("kind") or args.kind or "external_reference"
        period = r.get("period") or parse_period(args.period)
        if kind == "historical_volume" and not period:
            die(f"historical_volume for {r['keyword']!r} needs a period")
        out.append((r["keyword"], kind, r.get("metrics") or {}, period, r))
    return out


def import_lines(path, args):
    kind = args.kind or "related_search"
    return [(line.strip(), kind, {}, parse_period(args.period), None)
            for line in read_text_any(path).splitlines() if line.strip() and not line.startswith("#")]


def cmd_import(args):
    p = Paths(args.root)
    state = require_init(p)
    cfg = load_config(p)
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        die(f"file not found: {path}")
    defaults = {"gkp": "google_keyword_planner", "gsc": "google_search_console", "trends": "google_trends"}
    source = args.source or defaults.get(args.format)
    if not source:
        die(f"--source is required for --format {args.format}")
    if args.kind and args.kind not in KINDS:
        die(f"--kind must be one of {sorted(KINDS)}")
    market = market_of(cfg, args)
    if args.format == "gsc":
        market = {"country": (args.country or "ALL").upper(), "language": "und"}
    parsers = {"gkp": lambda: import_gkp(path, args, market), "gsc": lambda: import_gsc(path, args),
               "trends": lambda: import_trends(path, args), "csv": lambda: import_csv(path, args),
               "json": lambda: import_json(path, args), "lines": lambda: import_lines(path, args)}
    rows = parsers[args.format]()
    digest = keep_raw(p, source, path)
    base_ref = f"file:{digest}" + (f"#{args.ref}" if args.ref else "")
    pool = Pool(p)
    new_obs = new_kw = dup = 0
    for raw, kind, metrics, period, extra in rows:
        kw = norm(raw)
        if not kw:
            continue
        m = market
        ref = base_ref
        src = source
        if extra:
            m = extra.get("market") or market
            ref = extra.get("source_ref") or base_ref
            src = extra.get("source") or source
        o = make_obs(kw, raw, src, kind, ref, m, period, metrics, state["run"])
        is_new, is_new_kw = pool.add(o)
        new_obs += is_new
        new_kw += is_new_kw
        dup += not is_new
    pool.flush()
    summary = {"type": "import", "run": state["run"], "format": args.format, "source": source,
               "file": str(path), "rows": len(rows), "new_observations": new_obs, "new_keywords": new_kw,
               "duplicates": dup, "market": market}
    log_run(p, summary)
    emit(summary)


# ---------------------------------------------------------------- competitor sitemaps

def http_get(url: str, limit: int = 30_000_000) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as r:
        data = r.read(limit)
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def cmd_sitemap(args):
    p = Paths(args.root)
    state = require_init(p)
    start = args.url.rstrip("/")
    parsed = urllib.parse.urlparse(start)
    if not parsed.scheme:
        die("--url needs a scheme, e.g. https://example.com")
    domain = parsed.netloc
    if re.search(r"\.xml(\.gz)?$", parsed.path):
        queue = deque([start])
    else:
        queue = deque()
        base = f"{parsed.scheme}://{domain}"
        try:
            robots = http_get(base + "/robots.txt").decode("utf-8", errors="replace")
            queue.extend(m.strip() for m in re.findall(r"(?im)^sitemap:\s*(\S+)", robots))
        except Exception as exc:  # noqa: BLE001 - report and fall back
            print(f"robots.txt unavailable: {exc}", file=sys.stderr)
        if not queue:
            queue.extend([base + "/sitemap.xml", base + "/sitemap_index.xml"])
    seen, urls, fetched, failures = set(), [], 0, []
    while queue and fetched < args.max_sitemaps and len(urls) < args.max_urls:
        sm = queue.popleft()
        if sm in seen:
            continue
        seen.add(sm)
        try:
            root = ET.fromstring(http_get(sm))
            fetched += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"sitemap": sm, "error": str(exc)[:200]})
            continue
        time.sleep(1.0)
        tag = root.tag.rsplit("}", 1)[-1]
        locs = [el.text.strip() for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "loc" and el.text]
        if tag == "sitemapindex":
            queue.extend(locs)
        else:
            urls.extend(locs[: args.max_urls - len(urls)])
    phrases = Counter()
    examples = defaultdict(list)
    for u in urls:
        segs = [s for s in urllib.parse.urlparse(u).path.split("/") if s]
        if not segs or len(segs) > args.max_depth:
            continue
        seg = urllib.parse.unquote(re.sub(r"\.(html?|php|aspx?)$", "", segs[-1]))
        toks = [t for t in re.split(r"[-_+\s.]+", seg.lower()) if t]
        toks = [t for t in toks if not re.fullmatch(r"\d+|[0-9a-f]{8,}|[a-z0-9]{16,}", t) and t not in SITEMAP_STOP]
        if not toks or len(toks) > 6:
            continue
        ph = " ".join(toks)
        phrases[ph] += 1
        if len(examples[ph]) < 3:
            examples[ph].append(u)
    snapshot = {"domain": domain, "fetched_at": now(), "sitemaps_fetched": fetched, "urls": len(urls),
                "failures": failures, "phrases": [{"text": t, "count": c, "examples": examples[t]}
                                                  for t, c in phrases.most_common(args.top)]}
    write_json(p.raw / "sitemaps" / f"{domain}-{datetime.now():%Y%m%d}.json", snapshot)
    concepts = {c["key"]: c for c in read_jsonl(p.concepts)}
    added = 0
    for row in snapshot["phrases"]:
        key = " ".join(stem_tuple(row["text"]))
        c = concepts.get(key)
        origin = f"sitemap:{domain}"
        if c:
            if origin not in c["origins"]:
                c["origins"].append(origin)
                c["evidence"] = (c["evidence"] + row["examples"])[:20]
            continue
        concepts[key] = concept_record(row["text"], "hypothesis", row["count"], [], row["examples"], [],
                                       origin, state["run"])
        added += 1
    write_jsonl(p.concepts, concepts.values())
    emit({"domain": domain, "sitemaps_fetched": fetched, "urls": len(urls), "phrases": len(phrases),
          "new_hypothesis_concepts": added, "failures": failures[:5]})


# ---------------------------------------------------------------- concepts and triage

def concept_record(text, kind, count, examples, evidence, parents, origin, run) -> dict:
    return {
        "schema": f"{S}/concept@1",
        "key": " ".join(stem_tuple(text)),
        "text": norm(text),
        "kind": kind,
        "status": "pending",
        "count": count,
        "examples": examples[:5],
        "evidence": evidence[:20],
        "parent_seed_ids": parents[:10],
        "origins": [origin],
        "first_run": run,
        "decided_run": None,
        "reason": None,
        "axis": None,
    }


def cmd_concepts(args):
    p = Paths(args.root)
    state = require_init(p)
    cfg = load_config(p)
    b = load_boundary(p)
    lex = lexicon(b)
    out_ph = phrase_set(b.get("out_terms"))
    known_ph = phrase_set(b.get("adjacent_terms")) + out_ph
    seeds = load_seeds(p)
    seed_keys = []
    for s in seeds:
        if s["status"] == "rejected":
            continue
        for t in [s["text"]] + list(s.get("aliases") or []):
            if stem_tuple(t):
                seed_keys.append((stem_tuple(t), s["id"]))
    seed_keys.sort(key=lambda x: -len(x[0]))
    concepts = {c["key"]: c for c in read_jsonl(p.concepts)}
    agg = defaultdict(lambda: {"kind": None, "keywords": set(), "obs": [], "parents": Counter(), "strong": False})
    strong_kinds = {"gsc_impression", "historical_volume", "onsite_request"}
    for o in read_jsonl(p.obs):
        toks = tokens(o["keyword"])
        st = tuple(stem(t) for t in toks)
        if matches_any(st, out_ph):
            continue
        hit = None
        for key, sid in seed_keys:  # find known seeds first so modifiers inside a seed ("game over") survive
            pos = contains_seq(st, key)
            if pos >= 0:
                hit = (pos, len(key))
                break
        if hit:
            pos, n = hit
            extras = [strip_lexicon(toks[:pos], lex), strip_lexicon(toks[pos + n :], lex)]
            items = [(" ".join(x), "term") for x in extras if x]
        else:
            residual = strip_lexicon(toks, lex)
            if not residual:
                continue
            items = [(" ".join(residual), "phrase")]
        for text, kind in items:
            key = " ".join(stem_tuple(text))
            if not key or matches_any(stem_tuple(text), known_ph):
                continue
            a = agg[key]
            a["kind"] = a["kind"] or kind
            a["text"] = a.get("text") or text
            a["keywords"].add(o["keyword"])
            if len(a["obs"]) < 20:
                a["obs"].append(o["id"])
            sid = (o.get("via") or {}).get("seed_id")
            if sid:
                a["parents"][sid] += 1
            a["strong"] = a["strong"] or o["kind"] in strong_kinds
    seed_key_set = {" ".join(k) for k, _ in seed_keys}
    min_count = args.min_count or cfg["discovery"]["concept_min_count"]
    added = 0
    for key, a in agg.items():
        if key in seed_key_set:
            continue
        count = len(a["keywords"])
        c = concepts.get(key)
        if c:
            if c["status"] == "stale":
                c.update(status="pending", reason=None)
            c["count"] = max(c["count"], count)
            c["examples"] = (c["examples"] + sorted(a["keywords"])[:5])[:5] if len(c["examples"]) < 5 else c["examples"]
            if "observed" not in c["origins"]:
                c["origins"].append("observed")
            if c["kind"] == "hypothesis":
                c["evidence"] = (a["obs"] + c["evidence"])[:20]
                c["parent_seed_ids"] = [s for s, _ in a["parents"].most_common(10)]
            continue
        if count < min_count and not a["strong"]:
            continue
        concepts[key] = concept_record(a["text"], a["kind"], count, sorted(a["keywords"])[:5], a["obs"],
                                       [s for s, _ in a["parents"].most_common(10)], "observed", state["run"])
        added += 1
    stale = 0
    for key, c in concepts.items():  # alias or boundary edits can make an old extraction disappear
        if c["status"] == "pending" and c["kind"] != "hypothesis" and key not in agg:
            c.update(status="stale", decided_run=state["run"], reason="no longer extracted from the pool")
            stale += 1
    live_seeds = [(k, " ".join(k)) for k, _ in seed_keys]
    subsumed = 0
    for c in concepts.values():
        if c["status"] != "pending" or c["kind"] == "term":
            continue
        ck = tuple(c["key"].split())
        base = next((txt for k, txt in live_seeds if len(k) < len(ck) and contains_seq(ck, k) >= 0), None)
        if base:
            c.update(status="subsumed", decided_run=state["run"], reason=f"contains seed '{base}'; re-extracted as terms")
            subsumed += 1
    write_jsonl(p.concepts, concepts.values())
    pending = [c for c in concepts.values() if c["status"] == "pending"]
    pending.sort(key=lambda c: (-c["count"], {"phrase": 0, "hypothesis": 1, "term": 2}[c["kind"]], c["text"]))
    phrase_keys = [tuple(c["key"].split()) for c in pending if c["kind"] != "term"]
    variants = defaultdict(list)
    batch = []
    for c in pending:
        ck = tuple(c["key"].split())
        base = None
        if c["kind"] != "term":
            base = next((k for k in phrase_keys if len(k) < len(ck) and contains_seq(ck, k) >= 0), None)
        if base:
            variants[" ".join(base)].append(c["text"])
        else:
            batch.append(c)
    batch = batch[: args.limit or cfg["discovery"]["triage_batch"]]
    triage = {
        "schema": f"{S}/triage-input@1",
        "run": state["run"],
        "pending_total": len(pending),
        "boundary": {"rings": b["rings"], "modifier_axes": sorted((b.get("modifiers") or {}).keys())},
        "decisions_allowed": ["seed", "modifier", "head_term", "adjacent", "out", "noise"],
        "items": [{"text": c["text"], "kind": c["kind"], "count": c["count"], "examples": c["examples"],
                   "origins": c["origins"], "variants": variants.get(c["key"], [])[:10]} for c in batch],
    }
    out = p.work / "triage-input.json"
    write_json(out, triage)
    emit({"new_concepts": added, "subsumed": subsumed, "stale": stale, "pending_total": len(pending), "batch": len(batch),
          "held_as_variants": sum(len(v) for v in variants.values()), "triage_input": str(out)})


def audit_terms(p: Paths, items: list[tuple]) -> list[dict]:
    """Collateral check for adjacent/out phrases: pool keywords where the phrase sits inside a seed or
    alias name ("spell" inside "magic spell sound effect"). Lexical evidence for the model; never a verdict."""
    seeds = [s for s in load_seeds(p) if s.get("status") != "rejected" and s.get("ring", "in") == "in"]
    by_first = defaultdict(list)
    for s in seeds:
        for t in [s["text"]] + list(s.get("aliases") or []):
            ph = stem_tuple(t)
            if ph:
                by_first[ph[0]].append((ph, s["text"]))
    kws = sorted({o["keyword"] for o in read_jsonl(p.obs)})
    st_kw = [(k, stem_tuple(k)) for k in kws]
    by_tok = defaultdict(list)
    for i, (_, st) in enumerate(st_kw):
        for t in set(st):
            by_tok[t].append(i)
    rows = []
    for field, term in items:
        ph = stem_tuple(term)
        if not ph:
            continue
        matched, hits, names = 0, [], Counter()
        for i in by_tok.get(ph[0], []):
            k, st = st_kw[i]
            pos = contains_seq(st, ph)
            if pos < 0:
                continue
            matched += 1
            lo, hi = pos, pos + len(ph)
            for j in range(len(st)):
                for sp, name in by_first.get(st[j], []):
                    # the seed name overlaps the phrase and reaches beyond it; a phrase that already
                    # contains the whole name ("electric snow shovel") is a deliberate narrowing
                    if (st[j : j + len(sp)] == sp and j < hi and j + len(sp) > lo
                            and (j < lo or j + len(sp) > hi)):
                        hits.append(k)
                        names[name] += 1
                        break
                else:
                    continue
                break
        rows.append({"field": field, "term": term, "single_word": len(ph) == 1, "matches": matched,
                     "inside_seed_names": len(hits), "seeds": [n for n, _ in names.most_common(3)],
                     "examples": hits[:5]})
    rows.sort(key=lambda r: (-r["inside_seed_names"], -r["matches"]))
    return rows


def cmd_boundary(args):
    """Read-only audit: adjacent/out phrases that also catch in-scope entity names."""
    p = Paths(args.root)
    require_init(p)
    b = load_boundary(p)
    items = [(f, t) for f in ("adjacent_terms", "out_terms") for t in b.get(f, [])]
    rows = audit_terms(p, items)
    flagged = [r for r in rows if r["inside_seed_names"]]
    write_json(p.work / "boundary-audit.json", {"schema": f"{S}/boundary-audit@1", "generated_at": now(),
                                                "boundary_version": b.get("version"), "terms": rows})
    emit({"audit": str(p.work / "boundary-audit.json"), "terms": len(rows), "flagged": len(flagged),
          "top": [{k: r[k] for k in ("field", "term", "matches", "inside_seed_names", "seeds", "examples")}
                  for r in flagged[: args.top]],
          "next": "narrow flagged phrases with a triage boundary op (remove the broad term, add the narrower "
                  "phrase the keywords show, e.g. 'spell' -> 'how to spell'); keep terms whose hits are noise"})


def cmd_triage(args):
    p = Paths(args.root)
    state = require_init(p)
    cfg = load_config(p)
    b = load_boundary(p)
    data = read_json(Path(args.file))
    decisions = data.get("decisions", []) if isinstance(data, dict) else data
    concepts = {c["key"]: c for c in read_jsonl(p.concepts)}
    seeds = load_seeds(p)
    seed_by_id = {s["id"]: s for s in seeds}
    seed_texts = {s["text"] for s in seeds}
    allowed = {"seed", "modifier", "head_term", "adjacent", "out", "noise"}
    ops = data.get("boundary", []) if isinstance(data, dict) else []
    errors = []
    for d in decisions:
        key = " ".join(stem_tuple(d.get("text", "")))
        if key not in concepts:
            errors.append(f"unknown concept {d.get('text')!r}")
        elif concepts[key]["status"] == "seed" and d.get("decision") != "seed":
            errors.append(f"{d.get('text')!r} is already a seed: retire it with `seed reject --text` first")
        if d.get("decision") not in allowed:
            errors.append(f"{d.get('text')!r}: decision must be one of {sorted(allowed)}")
        if not d.get("reason"):
            errors.append(f"{d.get('text')!r}: reason is required")
    observed = None
    for d in decisions:
        if d.get("as"):
            if d.get("decision") != "seed":
                errors.append(f"{d.get('text')!r}: `as` only applies to seed decisions")
                continue
            if observed is None:
                observed = {stem_tuple(o["keyword"]) for o in read_jsonl(p.obs)}
            ph = stem_tuple(d["as"])
            if not ph or not any(contains_seq(k, ph) >= 0 for k in observed):
                errors.append(f"{d.get('text')!r}: seed text {d['as']!r} occurs in no observed keyword")
    for i, op in enumerate(ops):
        where = f"boundary op {i} ({op.get('op')} {op.get('term')!r})"
        if op.get("op") not in ("add", "remove") or op.get("field") not in BOUNDARY_FIELDS:
            errors.append(f"{where}: op must be add|remove and field one of {sorted(BOUNDARY_FIELDS)}")
            continue
        if not stem_tuple(op.get("term", "")) or not op.get("reason"):
            errors.append(f"{where}: term and reason are required")
            continue
        if op["op"] == "add":
            if observed is None:
                observed = {stem_tuple(o["keyword"]) for o in read_jsonl(p.obs)}
            ph = stem_tuple(op["term"])
            if not any(contains_seq(k, ph) >= 0 for k in observed):
                errors.append(f"{where}: no observed keyword contains this phrase")
        elif norm(op["term"]) not in boundary_list(b, op["field"], op.get("axis"), all_axes=True):
            errors.append(f"{where}: not in the boundary")
    if errors:
        die("triage rejected:\n  " + "\n  ".join(errors))
    counts = Counter()
    for op in ops:  # explicit boundary edits (phrases narrower or wider than a concept, bootstrap terms)
        term = norm(op["term"])
        if op["op"] == "add":
            lst = boundary_list(b, op["field"], op.get("axis") or "_generic", create=True)
            if term not in lst:
                lst.append(term)
        else:
            for lst in boundary_lists(b, op["field"], op.get("axis")):
                while term in lst:
                    lst.remove(term)
        counts[f"boundary_{op['op']}"] += 1
    for d in decisions:
        c = concepts[" ".join(stem_tuple(d["text"]))]
        dec = d["decision"]
        if c["status"] in DECISION_FIELD:  # a re-decision withdraws the earlier boundary entry
            for lst in boundary_lists(b, DECISION_FIELD[c["status"]], c.get("axis")):
                while c["text"] in lst:
                    lst.remove(c["text"])
            counts["revised"] += 1
        c.update(status=dec, decided_run=state["run"], reason=d["reason"], axis=d.get("axis"))
        counts[dec] += 1
        text = c["text"]
        if dec == "seed":
            text = norm(d.get("as") or text)  # the name users actually search ("emotional" -> "emotional damage")
            if text in seed_texts:
                old = next(s for s in seeds if s["text"] == text)
                if old["status"] == "parked":  # parked for lack of signal; the pool now shows demand
                    old.update(status="pending", note=f"unparked by triage: {d['reason']}")
                    old["evidence"] = (old.get("evidence") or []) + c["evidence"][:10]
                    counts["unparked"] += 1
                continue
            if c["kind"] == "hypothesis" and not c["parent_seed_ids"]:
                rec = seed_record(text, "topdown", d.get("ring", "in"), 0, state["run"], evidence=c["evidence"],
                                  note="competitor/taxonomy hypothesis; unverified until observed")
            else:
                if not c["evidence"]:
                    die(f"{text!r} has no observation evidence; it cannot become a reviewed seed")
                parents = [seed_by_id[s] for s in c["parent_seed_ids"] if s in seed_by_id]
                depth = (min(s["depth"] for s in parents) + 1) if parents else 1
                rec = seed_record(text, "reviewed_concept", d.get("ring", "in"), depth, state["run"],
                                  parent=parents[0]["id"] if parents else None, evidence=c["evidence"])
                if depth > cfg["discovery"]["max_depth"]:
                    rec["status"] = "deferred"
            seeds.append(rec)
            seed_texts.add(text)
        elif dec == "modifier":
            axis = d.get("axis") or "_generic"
            vals = b.setdefault("modifiers", {}).setdefault(axis, [])
            if text not in vals:
                vals.append(text)
        elif dec == "head_term":
            if text not in b["head_terms"]:
                b["head_terms"].append(text)
        elif dec in ("adjacent", "out"):
            field = "adjacent_terms" if dec == "adjacent" else "out_terms"
            if text not in b[field]:
                b[field].append(text)
    b["version"] = int(b.get("version", 1)) + 1
    b["updated_at"] = now()
    write_json(p.boundary, b)
    write_jsonl(p.concepts, concepts.values())
    write_jsonl(p.seeds, seeds)
    log_run(p, {"type": "triage", "run": state["run"], "decisions": dict(counts),
                "boundary_ops": [{k: op.get(k) for k in ("op", "field", "axis", "term", "reason")} for op in ops]})
    added = [(BOUNDARY_FIELDS[op["field"]], norm(op["term"])) for op in ops
             if op["op"] == "add" and op["field"] in ("adjacent", "out")]
    added += [("adjacent_terms" if d["decision"] == "adjacent" else "out_terms", norm(d["text"]))
              for d in decisions if d["decision"] in ("adjacent", "out")]
    wide = [r for r in audit_terms(p, added) if r["inside_seed_names"]] if added else []
    emit({"applied": len(decisions) + len(ops), "by_decision": dict(counts), "boundary_version": b["version"],
          "breadth_warnings": [{k: r[k] for k in ("field", "term", "inside_seed_names", "seeds", "examples")}
                               for r in wide]})


# ---------------------------------------------------------------- seed consolidation and probing

def entity_key(words: list[str]) -> tuple:
    """Order-free key for grouping names: stems plus -ing/-e folding (knocking -> knock, crackle -> crackl)."""
    out = []
    for t in words:
        if t in ENTITY_STOP:
            continue
        t = stem(t)
        if len(t) > 5 and t.endswith("ing"):
            t = t[:-3]
            if len(t) > 2 and t[-1] == t[-2] and t[-1] not in "slz":  # running -> run, but passing -> pass
                t = t[:-1]
        if len(t) > 4 and t.endswith("e"):
            t = t[:-1]
        out.append(t)
    return tuple(sorted(set(out)))


def clean_name(text: str, lex: set, keep_numbers=None) -> tuple[str, tuple]:
    """Display text and key of a candidate name.

    Drops variant suffixes (" - ...", "(...)"), ID-like tokens and lexicon phrases at the edges only,
    so "phone case for kids" keeps its inner head term. keep_numbers=None keeps every number
    (group names such as "iphone 15"); a set keeps only those numbers (leaf titles such as "clear 03").
    """
    t = re.split(r"\s+[\u2014\u2013-]\s+|\s*[|(\[]", norm(text))[0]
    words = [w for w in tokens(t) if not re.fullmatch(r"v\d+|[0-9a-f]{8,}|[a-z0-9]{16,}", w)
             and (not re.fullmatch(r"\d+", w) or keep_numbers is None or w in keep_numbers)]
    original = list(words)

    def strip_edges(ws):
        changed = True
        while changed and ws:
            changed = False
            for n in (4, 3, 2, 1):
                if len(ws) >= n and tuple(stem(x) for x in ws[:n]) in lex:
                    ws, changed = ws[n:], True
                    break
                if len(ws) >= n and tuple(stem(x) for x in ws[-n:]) in lex:
                    ws, changed = ws[:-n], True
                    break
        return ws

    words = strip_edges(words)
    if words and words[0] in STOPWORDS and original and original[0] not in STOPWORDS:
        words = original  # the stripped head term was part of the name ("sound effects for games")
    while words and words[0] in LEADING_STOP:
        words = words[1:]
    while words and words[-1] in STOPWORDS:  # trailing particles stay: "game over", "power on"
        words = words[:-1]
    return " ".join(words), entity_key(words)


def probe_query(text: str, boundary: dict) -> str:
    templates = boundary.get("expression_templates") or []
    if not templates or matches_any(stem_tuple(text), phrase_set(boundary.get("head_terms"))):
        return norm(text)
    return norm(templates[0].replace("{seed}", text))


def probe_signal(caches: dict, q: str, market: dict, key: tuple, samples: list | None = None):
    """Per engine, distinct suggestions that still contain every core word of the entity.

    Some engines answer anything with loosely related completions ("ride bell" -> "bike bell");
    those are not evidence for the entity. Returns None while any engine has not been probed.
    Appends up to 3 raw suggestions per engine to `samples` so a reviewer can rename the entity.
    """
    out = {}
    need = set(key)
    for e, c in caches.items():
        got = c.get(q, market)
        if got is None:
            return None
        uniq = list(dict.fromkeys(norm(x) for x in got if norm(x)))
        out[e] = sum(1 for x in uniq if need <= set(entity_key(tokens(x))))
        if samples is not None:
            samples.extend(f"{e}: {x}" for x in uniq[:3])
    return out


def cmd_consolidate(args):
    p = Paths(args.root)
    require_init(p)
    cfg = load_config(p)
    dc = cfg["discovery"]
    b = load_boundary(p)
    market = market_of(cfg, args)
    engines = args.engine or dc["engines"]
    data = read_json(Path(args.file))
    light = {stem_tuple(x) for x in list(GENERIC_MODIFIERS) + list(b.get("head_terms", [])) if stem_tuple(x)}
    full = lexicon(b)
    full_words = {x for ph in full for w in ph for x in entity_key([w])}
    caches = {e: SuggestCache(p, e, dc["cache_ttl_days"]) for e in engines}
    ents = {}
    alias_of = {}
    group_ent = {}

    def ent(key, name, kind):
        e = ents.get(key)
        if not e:
            e = ents[key] = {"key": key, "name": name, "kind": kind, "groups": set(), "names": set(),
                             "items": 0, "children": set(), "origins": set(), "leaves": {}, "collapsed_leaves": 0}
        return e

    for g in data.get("groups", []):
        name, key = clean_name(g["name"], light)
        if not key:
            continue
        e = ent(alias_of.get(key, key), name, "group")
        e["groups"].add(g["id"])
        e["items"] += int(g.get("items") or 0)
        e["origins"].add(g.get("origin", "group"))
        group_ent[g["id"]] = e["key"]
        for a in g.get("aliases") or []:
            an, ak = clean_name(a, light)
            if ak and ak != e["key"] and ak not in ents:
                alias_of[ak] = e["key"]
                e["names"].add(an)
    for n in data.get("names", []):
        name, key = clean_name(n["text"], light)
        if not key:  # a pure category name ("free sound effects") is itself a seed candidate
            name = norm(n["text"])
            key = ("=" + name,)
        target = alias_of.get(key, key)
        gs = [group_ent[g] for g in n.get("groups") or [] if g in group_ent]
        if target in ents:
            ents[target]["names"].add(name)
            ents[target]["origins"].add(n.get("origin", "name"))
        elif len(set(gs)) == 1:
            alias_of[key] = gs[0]
            ents[gs[0]]["names"].add(name)
            ents[gs[0]]["origins"].add(n.get("origin", "name"))
        else:
            e = ent(key, name, "parent" if len(set(gs)) > 1 else "free")
            e["children"].update(gs)
            e["origins"].add(n.get("origin", "name"))
    # words that recur across many groups' leaves describe variants (soft, heavy, short), not entities
    spread = defaultdict(set)
    group_words = {w for k in group_ent.values() for w in k}
    group_numbers = {gid: {w for w in ents[k]["key"] if w.isdigit()} for gid, k in group_ent.items()}
    for leaf in data.get("leaves", []):
        for w in clean_name(leaf["text"], light, group_numbers.get(leaf.get("group"), set()))[1]:
            spread[w].add(leaf.get("group"))
    inferred = {w for w, gs in spread.items() if len(gs) >= args.spread and w not in group_words}
    attr_words = full_words | inferred
    for leaf in data.get("leaves", []):
        parent = group_ent.get(leaf.get("group"))
        if not parent:
            continue
        name, _ = clean_name(leaf["text"], light, group_numbers.get(leaf.get("group"), set()))
        words = [w for w in name.split() if not entity_key([w]) or entity_key([w])[0] not in attr_words]
        while words and words[0] in LEADING_STOP:
            words = words[1:]
        while words and words[-1] in STOPWORDS:
            words = words[:-1]
        name, key = " ".join(words), entity_key(words)  # leaf minus variant words = the entity it names
        pe = ents[parent]
        target = alias_of.get(key, key)
        extra = set(key) - set(parent)
        if not key or target == parent or not extra:
            pe["collapsed_leaves"] += 1
        elif target in ents:
            ents[target]["collapsed_leaves"] += 1
        else:
            v = pe["leaves"].setdefault(key, {"name": name, "count": 0})
            v["count"] += 1

    needs, review, parked, leaf_pending = [], [], [], 0
    for e in ents.values():
        e["query"] = probe_query(e["name"], b)
        e["samples"] = []
        match_key = entity_key(tokens(e["name"])) if e["key"][0].startswith("=") else e["key"]
        e["probe"] = probe_signal(caches, e["query"], market, match_key, e["samples"])
        if e["probe"] is None:
            needs.append(e["name"])
        variants = sorted(e["leaves"].values(), key=lambda v: (-v["count"], v["name"]))
        sample, rest = variants[: args.leaf_sample], variants[args.leaf_sample :]
        signal_leaves, open_sample = [], False
        for v in sample:
            v["probe"] = probe_signal(caches, probe_query(v["name"], b), market, entity_key(v["name"].split()))
            if v["probe"] is None:
                needs.append(v["name"])
                open_sample = True
            elif sum(v["probe"].values()) >= args.min_signal:
                signal_leaves.append(v)
        if signal_leaves and not open_sample:
            for v in rest:
                v["probe"] = probe_signal(caches, probe_query(v["name"], b), market, entity_key(v["name"].split()))
                if v["probe"] is None:
                    needs.append(v["name"])
                elif sum(v["probe"].values()) >= args.min_signal:
                    signal_leaves.append(v)
        elif rest and not open_sample:
            e["collapsed_leaves"] += sum(v["count"] for v in rest)  # sample had no signal: fold the rest into the group
        leaf_pending += open_sample
        e["signal_leaves"] = signal_leaves
    needs = list(dict.fromkeys(needs))
    out_path = p.work / "consolidation.json"
    summary = {"candidates": {k: len(data.get(k, [])) for k in ("groups", "names", "leaves")},
               "entities": len(ents), "by_kind": dict(Counter(e["kind"] for e in ents.values())),
               "aliases_merged": len(alias_of), "leaves_collapsed": sum(e["collapsed_leaves"] for e in ents.values()),
               "inferred_modifier_words": sorted(inferred), "needs_probe": len(needs)}
    if needs:
        write_json(out_path, {"schema": f"{S}/consolidation@1", "status": "needs_probe", "engines": engines,
                              "market": market, "needs_probe": needs, "summary": summary})
        emit(dict(summary, next=f"probe --file {out_path}", file=str(out_path)))
        return
    for e in sorted(ents.values(), key=lambda x: (-x["items"], x["name"])):
        sig = sum((e["probe"] or {}).values())
        row = {"name": e["name"], "kind": e["kind"], "probe": e["probe"], "signal": sig, "items": e["items"],
               "groups": sorted(e["groups"]), "aliases": sorted(e["names"] - {e["name"]}),
               "children": sorted(ents[c]["name"] for c in e["children"] if c in ents),
               "origins": sorted(e["origins"]), "samples": e["samples"][:6],
               "signal_leaves": [{"name": v["name"], "count": v["count"], "signal": sum(v["probe"].values())}
                                 for v in e["signal_leaves"]],
               "collapsed_leaves": e["collapsed_leaves"]}
        (review if sig >= args.min_signal or row["signal_leaves"] else parked).append(row)
    rows_sig = sorted((r["name"], r["signal"], len(r["signal_leaves"])) for r in review + parked)
    result = {"schema": f"{S}/seed-review@1", "status": "ready_for_review",
              "review_hash": sha(json.dumps(rows_sig, ensure_ascii=False)), "engines": engines, "market": market,
              "min_signal": args.min_signal, "summary": dict(summary, with_signal=len(review), no_signal=len(parked)),
              "review": review, "no_signal": parked}
    write_json(p.work / "seed-review.json", result)
    write_json(out_path, {"schema": f"{S}/consolidation@1", "status": "complete", "summary": result["summary"]})
    emit(dict(result["summary"], review_file=str(p.work / "seed-review.json")))


def cmd_probe(args):
    p = Paths(args.root)
    state = require_init(p)
    cfg = load_config(p)
    dc = cfg["discovery"]
    b = load_boundary(p)
    plan = read_json(Path(args.file)) or {}
    texts = plan.get("needs_probe") or []
    if not texts:
        die("nothing to probe; rerun consolidate")
    market = plan.get("market") or market_of(cfg, args)
    engines = args.engine or plan.get("engines") or dc["engines"]
    queues = {e: deque((t, probe_query(t, b)) for t in texts) for e in engines}
    pool = Pool(p)

    def record(e, task, suggestions, h):
        text, q = task
        for rank, raw in enumerate(suggestions):
            kw = norm(raw)
            if kw:
                o = make_obs(kw, raw, ENGINE_SOURCE[e], "search_suggestion", f"suggest:{e}:{q}", market, None,
                             {"rank": rank}, state["run"], via={"seed_id": None, "seed": text, "query": q, "group": "probe"})
                is_new, is_new_kw = pool.add(o)
                h.counters["new_observations"] += is_new
                h.counters["new_keywords"] += is_new_kw
        h.counters["probed"] += 1
        h.counters["with_signal"] += bool(suggestions)

    h = harvest(p, dc, market, queues, args.max_requests or dc["max_requests_per_run"],
                args.max_seconds or dc["max_seconds_per_run"], record, on_exit=pool.flush)
    summary = {"type": "probe", "run": state["run"], "engines": engines, "texts": len(texts),
               "requests": h.counters["requests"], "cache_hits": h.counters["cache_hits"],
               "probed": h.counters["probed"], "with_signal": h.counters["with_signal"],
               "new_keywords": h.counters["new_keywords"], "paused": h.paused, "stopped_by": h.stopped_by,
               "queries_left": h.left, "elapsed_seconds": h.elapsed, "next": "rerun consolidate"}
    log_run(p, summary)
    emit(summary)


# ---------------------------------------------------------------- rounds, status, export

def keyword_first_run(p: Paths) -> dict:
    first = {}
    for o in read_jsonl(p.obs):
        r = o.get("run", 0)
        if o["keyword"] not in first or r < first[o["keyword"]]:
            first[o["keyword"]] = r
    return first


def cmd_round(args):
    p = Paths(args.root)
    state = require_init(p)
    cfg = load_config(p)
    dc = cfg["discovery"]
    run = state["run"]
    first = keyword_first_run(p)
    new_keywords = sum(1 for r in first.values() if r == run)
    seeds = load_seeds(p)
    new_seeds = [s for s in seeds if s["added_run"] == run and s["origin"] == "reviewed_concept"]
    concepts = read_jsonl(p.concepts)
    pending_concepts = sum(1 for c in concepts if c["status"] == "pending")
    need = set(LEVELS[dc["level"]])
    expandable = sum(
        1 for s in seeds
        if s["status"] in ("pending", "active") and s["ring"] == "in" and s["depth"] <= dc["max_depth"]
        and not all(need <= set(s.get("expanded", {}).get(e, [])) for e in dc["engines"])
    )
    entries = [e for e in read_jsonl(p.runs) if e.get("run") == run]
    requests = sum(e.get("requests", 0) for e in entries if e.get("type") == "suggest")
    yld = round(len(new_seeds) / new_keywords, 4) if new_keywords else 0.0
    source_yield = {}
    for e in entries:
        if e.get("type") == "suggest":
            for eng, st in (e.get("per_engine") or {}).items():
                y = source_yield.setdefault(ENGINE_SOURCE[eng], {"requests": 0, "new_keywords": 0})
                y["requests"] += st["requests"]
                y["new_keywords"] += st["new_keywords"]
        if e.get("type") == "import":
            y = source_yield.setdefault(e["source"], {"requests": 0, "new_keywords": 0})
            y["new_keywords"] += e.get("new_keywords", 0)
    history = [e for e in read_jsonl(p.runs) if e.get("type") == "round"]
    recent = [h["yield"] for h in history[-(dc["stop_rounds"] - 1):]] + [yld] if dc["stop_rounds"] > 1 else [yld]
    reasons = []
    if expandable == 0:
        verdict = "STOP"
        reasons.append(f"frontier exhausted: every in-boundary seed within max_depth finished level {dc['level']} on all engines")
    elif len(recent) >= dc["stop_rounds"] and all(y < dc["stop_yield"] for y in recent) and new_keywords > 0:
        verdict = "STOP"
        reasons.append(f"yield below {dc['stop_yield']} for {dc['stop_rounds']} rounds: new keywords mostly repeat known concepts")
    else:
        verdict = "CONTINUE"
        reasons.append(f"{expandable} seeds not yet expanded to level {dc['level']} on all engines")
    if pending_concepts:
        if not args.force:
            emit({"run": run, "verdict": "TRIAGE_FIRST", "closed": False,
                  "reasons": [f"{pending_concepts} concepts pending triage; triage first so yield is not understated"]})
            sys.exit(4)
        reasons.append(f"closed with {pending_concepts} untriaged concepts; yield may be understated")
    entry = {"type": "round", "run": run, "new_keywords": new_keywords, "new_reviewed_seeds": len(new_seeds),
             "yield": yld, "requests": requests, "pending_concepts": pending_concepts,
             "expandable_seeds": expandable, "keywords_total": len(first), "verdict": verdict,
             "reasons": reasons, "source_yield": source_yield}
    log_run(p, entry)
    state.update(run=run + 1, run_started_at=now())
    write_json(p.state, state)
    emit(dict(entry, closed=True, next_run=run + 1))


def coverage(p: Paths, b: dict, keywords: set) -> list[dict]:
    rows = []
    stemmed = [(k, stem_tuple(k)) for k in keywords]
    for item in b.get("inventory") or []:
        names = [item.get("name", "")] + list(item.get("aliases") or [])
        phs = phrase_set(names)
        hits = [k for k, st in stemmed if matches_any(st, phs)]
        rows.append({"name": item.get("name"), "inventory": item.get("count"), "keywords": len(hits),
                     "examples": sorted(hits)[:3]})
    rows.sort(key=lambda r: r["keywords"])
    return rows


def cmd_status(args):
    p = Paths(args.root)
    state = require_init(p)
    b = load_boundary(p)
    obs = read_jsonl(p.obs)
    keywords = {o["keyword"] for o in obs}
    out_ph = phrase_set(b.get("out_terms"))
    seeds = load_seeds(p)
    concepts = read_jsonl(p.concepts)
    rounds = [e for e in read_jsonl(p.runs) if e.get("type") == "round"]
    cov = coverage(p, b, keywords)
    emit({
        "run": state["run"],
        "observations": len(obs),
        "keywords": len(keywords),
        "keywords_matching_out_terms": sum(1 for k in keywords if matches_any(stem_tuple(k), out_ph)),
        "by_source": dict(Counter(o["source"] for o in obs)),
        "by_kind": dict(Counter(o["kind"] for o in obs)),
        "seeds": {"total": len(seeds), "by_status": dict(Counter(s["status"] for s in seeds)),
                  "by_depth": dict(Counter(str(s["depth"]) for s in seeds))},
        "concepts": dict(Counter(c["status"] for c in concepts)),
        "recent_rounds": [{k: r[k] for k in ("run", "new_keywords", "new_reviewed_seeds", "yield", "verdict")}
                          for r in rounds[-5:]],
        "boundary_version": b.get("version"),
        "inventory_coverage_gaps": [c for c in cov if c["keywords"] == 0][:30],
        "inventory_coverage": cov[:50] if args.coverage else None,
    })


def cmd_export(args):
    p = Paths(args.root)
    require_init(p)
    cfg = load_config(p)
    b = load_boundary(p)
    out_ph = phrase_set(b.get("out_terms"))
    rows = defaultdict(lambda: {"observations": 0, "sources": set(), "kinds": set(), "planner_high": None,
                                "gsc_impressions": 0.0, "first_run": None})
    for o in read_jsonl(p.obs):
        r = rows[o["keyword"]]
        r["observations"] += 1
        r["sources"].add(o["source"])
        r["kinds"].add(o["kind"])
        r["first_run"] = o.get("run") if r["first_run"] is None else min(r["first_run"], o.get("run", 0))
        vol = (o.get("metrics") or {}).get("avg_monthly_searches")
        if o["kind"] == "historical_volume" and vol:
            r["planner_high"] = max(r["planner_high"] or 0, vol.get("high") or 0)
        if o["kind"] == "gsc_impression":
            r["gsc_impressions"] += (o.get("metrics") or {}).get("impressions") or 0
    p.work.mkdir(parents=True, exist_ok=True)
    if args.format == "planner":
        market = cfg["market"]
        todo = [k for k, r in rows.items() if "historical_volume" not in r["kinds"]
                and not matches_any(stem_tuple(k), out_ph)]
        todo.sort()
        files = []
        for i in range(0, len(todo), args.chunk):
            f = p.work / f"planner-upload-{i // args.chunk + 1:03d}.csv"
            f.write_text("Keyword\n" + "\n".join(todo[i : i + args.chunk]) + "\n", encoding="utf-8")
            files.append(str(f))
        emit({"keywords_without_volume": len(todo), "files": files, "market": market,
              "note": "upload in Keyword Planner > Get search volume and forecasts; re-import the export with --format gkp"})
        return
    out = Path(args.out) if args.out else p.work / "keywords.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["keyword", "observations", "sources", "kinds", "planner_high", "gsc_impressions", "out_term", "first_run"])
        for k in sorted(rows):
            r = rows[k]
            w.writerow([k, r["observations"], "|".join(sorted(r["sources"])), "|".join(sorted(r["kinds"])),
                        r["planner_high"] or "", int(r["gsc_impressions"]) or "",
                        int(matches_any(stem_tuple(k), out_ph)), r["first_run"]])
    emit({"exported": len(rows), "file": str(out)})


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description="site-keywords: search demand discovery engine")
    ap.add_argument("--root", default=".", help="project root that holds (or will hold) seo/")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("init", help="create seo/ with config, boundary skeleton and state")
    a.add_argument("--country")
    a.add_argument("--language")
    a.set_defaults(fn=cmd_init)

    a = sub.add_parser("seed", help="add, list, reject seeds; review/apply-review consolidation decisions; alias hygiene")
    a.add_argument("action", choices=["add", "list", "reject", "review", "apply-review", "aliases"])
    a.add_argument("--limit", type=int, help="review/aliases: rows per batch")
    a.add_argument("--revise", action="store_true", help="apply-review: allow changing earlier decisions")
    a.add_argument("--alias-spread", type=int, default=5,
                   help="apply-review/aliases: flag aliases seen under this many different seeds' searches")
    a.add_argument("--text", action="append")
    a.add_argument("--file")
    a.add_argument("--origin", default="user", choices=SEED_ORIGINS)
    a.add_argument("--ring", default="in", choices=["in", "adjacent"])
    a.add_argument("--status")
    a.set_defaults(fn=cmd_seed)

    a = sub.add_parser("suggest", help="harvest autocomplete suggestions for pending seeds")
    a.add_argument("--engine", action="append", choices=sorted(ENGINE_SOURCE))
    a.add_argument("--level", choices=sorted(LEVELS))
    a.add_argument("--seed", action="append", help="restrict to these seed texts")
    a.add_argument("--max-seeds", type=int)
    a.add_argument("--max-requests", type=int)
    a.add_argument("--max-seconds", type=int)
    a.add_argument("--all-seeds", action="store_true", help="deep level: alpha-expand every selected seed")
    a.add_argument("--refresh", action="store_true", help="re-run groups already expanded (cache still applies)")
    a.add_argument("--no-gate", action="store_true", help="expand modifiers even for seeds whose base queries returned little")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--country")
    a.add_argument("--language")
    a.set_defaults(fn=cmd_suggest)

    a = sub.add_parser("import", help="import a keyword export into the observation pool")
    a.add_argument("--format", required=True, choices=["gkp", "gsc", "trends", "csv", "json", "lines"])
    a.add_argument("--file", required=True)
    a.add_argument("--source")
    a.add_argument("--kind")
    a.add_argument("--period", help="START..END, required when the export does not state it")
    a.add_argument("--page", help="GSC: page filter the export was taken with")
    a.add_argument("--ref", help="what was captured, e.g. the Trends term or SERP query")
    a.add_argument("--country")
    a.add_argument("--language")
    a.set_defaults(fn=cmd_import)

    a = sub.add_parser("sitemap", help="turn a competitor sitemap into hypothesis concepts")
    a.add_argument("--url", required=True)
    a.add_argument("--max-sitemaps", type=int, default=20)
    a.add_argument("--max-urls", type=int, default=20000)
    a.add_argument("--max-depth", type=int, default=3, help="max URL path depth kept")
    a.add_argument("--top", type=int, default=300)
    a.set_defaults(fn=cmd_sitemap)

    a = sub.add_parser("concepts", help="extract novel concepts and terms for triage")
    a.add_argument("--min-count", type=int)
    a.add_argument("--limit", type=int)
    a.set_defaults(fn=cmd_concepts)

    a = sub.add_parser("boundary", help="audit adjacent/out phrases that also catch in-scope entity names")
    a.add_argument("action", choices=["audit"])
    a.add_argument("--top", type=int, default=25)
    a.set_defaults(fn=cmd_boundary)

    a = sub.add_parser("triage", help="apply triage decisions to seeds and boundary")
    a.add_argument("--file", required=True)
    a.set_defaults(fn=cmd_triage)

    a = sub.add_parser("consolidate", help="collapse raw seed candidates to entity-level seeds")
    a.add_argument("--file", required=True, help="seed-candidates JSON: groups, names, leaves")
    a.add_argument("--engine", action="append", choices=sorted(ENGINE_SOURCE))
    a.add_argument("--leaf-sample", type=int, default=2, help="leaf variants probed per entity before folding")
    a.add_argument("--min-signal", type=int, default=1, help="distinct suggestions that count as search signal")
    a.add_argument("--spread", type=int, default=8, help="leaf words seen in this many groups count as modifiers")
    a.add_argument("--country")
    a.add_argument("--language")
    a.set_defaults(fn=cmd_consolidate)

    a = sub.add_parser("probe", help="one cheap autocomplete query per text in a consolidation plan")
    a.add_argument("--file", required=True)
    a.add_argument("--engine", action="append", choices=sorted(ENGINE_SOURCE))
    a.add_argument("--max-requests", type=int)
    a.add_argument("--max-seconds", type=int)
    a.add_argument("--country")
    a.add_argument("--language")
    a.set_defaults(fn=cmd_probe)

    a = sub.add_parser("round", help="close the current run and compute yield / stop verdict")
    a.add_argument("--force", action="store_true", help="close even with pending concepts")
    a.set_defaults(fn=cmd_round)

    a = sub.add_parser("status", help="pool summary and inventory coverage")
    a.add_argument("--coverage", action="store_true")
    a.set_defaults(fn=cmd_status)

    a = sub.add_parser("export", help="export keywords (csv) or planner upload chunks")
    a.add_argument("--format", choices=["csv", "planner"], default="csv")
    a.add_argument("--out")
    a.add_argument("--chunk", type=int, default=1000)
    a.set_defaults(fn=cmd_export)

    args = ap.parse_args(argv)

    def interrupt(signum, frame):
        raise KeyboardInterrupt  # SIGTERM (and SIGINT in background jobs) stop cleanly: flush pool, keep cache

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    args.fn(args)


if __name__ == "__main__":
    main()
