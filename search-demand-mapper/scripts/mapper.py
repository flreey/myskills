#!/usr/bin/env python3
"""Search demand mapper (Python stdlib only).

Reads the observation pool written by search-demand-discovery (<root>/seo/discovery/) and keeps
the demand-to-page registry under <root>/seo/mapper/. Semantic judgement comes from the model in
reviewed batches; this script prepares batches, validates structure, applies confirmed changes,
computes evidence gates and checks registry invariants. It never decides semantics by keyword rules.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

S = "search-demand"

DEFAULT_MAPPER = {
    "review_batch": 100,          # review units per batch (a group counts as one unit)
    "review_max_keywords": 600,   # keywords per batch across groups and single items
    "review_facet_min": 3,        # keywords sharing the same extra words (across seeds) to form a facet group
    "tasks": ["acquire_asset", "acquire_collection", "use_tool", "learn", "compare", "buy", "integrate",
              "navigate", "check", "other"],
    "deliveries": ["asset", "collection", "tool", "explanation", "comparison", "integration", "website",
                   "video", "service", "other"],
    # needs_cluster=False: indexable pages that are not meant to own demand (one-item detail pages,
    # about/legal/docs); validate does not ask them for a primary cluster.
    "page_types": {"resource": {"min_items": 8}, "collection": {"min_items": 3}, "tool": {"min_items": 1},
                   "article": {"min_items": 0}, "filter": {"min_items": 3},
                   "asset": {"min_items": 1, "needs_cluster": False}, "info": {"min_items": 0, "needs_cluster": False}},
    "gate": {"min_keywords": 2, "strong_planner_high": 100, "strong_gsc_impressions": 50,
             "require_serp_for_create": True},
    # exclude_axes: axes whose values narrow a result set but almost never deserve a page of their own
    # (license, format); analyze does not list them as promotion candidates. A project can clear it.
    "promotion": {"min_keywords": 3, "min_items": 8, "exclude_axes": ["license", "format"]},
    "priority": {"p0_planner_high": 1000, "p0_gsc_impressions": 100, "p1_planner_high": 100, "p1_members": 5},
    "serp": {"top_n": 10, "merge_min_shared": 6, "split_max_shared": 3, "budget_per_session": 30},
    "gsc": {"windows_required": 2, "split_min_impressions": 100, "cannibal_min_share": 0.2,
            "cooldown_days": 28, "retire_after_days": 120, "retire_max_impressions": 10},
}
STATUSES = {"included", "excluded", "pending"}
BASES = {"explicit", "inferred", "unknown"}
PAGE_STATUSES = {"planned", "published", "noindex", "redirected", "gone"}
MAP_DECISIONS = {"keep", "improve_existing", "filter", "create", "defer"}
ROLES = {"primary", "secondary", "filter"}
IDENTITY = ("intent", "entity", "expected_result_set", "page_type")
STRONG_KINDS = ("gsc_impression", "historical_volume", "onsite_request")


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


def kw_id(keyword: str) -> str:
    return "kw_" + sha(keyword, 12)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    die(f"{path}:{i} invalid JSON: {exc}")
    return rows


def append_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
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


def norm_url(u: str) -> str:
    p = urllib.parse.urlparse(u.strip() if "://" in u else "https://" + u.strip())
    host = p.netloc.lower().removeprefix("www.")
    return host + (p.path.rstrip("/") or "/")


class Paths:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.seo = self.root / "seo"
        self.config = self.seo / "config.json"
        self.boundary = self.seo / "boundary.json"
        self.obs = self.seo / "discovery" / "observations.jsonl"
        self.m = self.seo / "mapper"
        self.clusters = self.m / "clusters.jsonl"
        self.decisions = self.m / "decisions.jsonl"
        self.reviews = self.m / "reviews"
        self.pages = self.m / "pages.jsonl"
        self.mappings = self.m / "mappings.jsonl"
        self.inventory = self.m / "inventory.json"
        self.serp = self.m / "evidence" / "serp.jsonl"
        self.serp_cmp = self.m / "evidence" / "serp-compare.jsonl"
        self.gsc = self.m / "evidence" / "gsc"
        self.changesets = self.m / "changesets"
        self.site_urls = self.m / "site-urls.json"
        self.work = self.seo / "work"


def cfg_of(p: Paths) -> dict:
    return deep_merge(DEFAULT_MAPPER, (read_json(p.config, {}) or {}).get("mapper", {}))


def market_of(p: Paths) -> dict:
    return (read_json(p.config, {}) or {}).get("market") or {"country": "US", "language": "en"}


def require(p: Paths):
    if not p.m.exists():
        die(f"{p.m} missing; run: mapper.py --root {p.root} init")


# ---------------------------------------------------------------- state loaders

def current(rows: list[dict], key: str) -> dict:
    cur = {}
    for r in rows:
        cur[r[key]] = r
    return cur


def load_clusters(p: Paths) -> dict:
    return current(read_jsonl(p.clusters), "id")


def load_decisions(p: Paths) -> dict:
    return current(read_jsonl(p.decisions), "keyword_id")


def load_pool(p: Paths) -> dict:
    """keyword_id -> {keyword, observations[]} from the discovery pool."""
    if not p.obs.exists():
        die(f"{p.obs} missing; build the pool with search-demand-discovery first")
    pool = {}
    for o in read_jsonl(p.obs):
        k = kw_id(o["keyword"])
        entry = pool.setdefault(k, {"keyword": o["keyword"], "observations": []})
        entry["observations"].append(o)
    for e in pool.values():
        e["evidence_hash"] = sha("|".join(sorted(o["id"] for o in e["observations"])))
    return pool


def stem_tuple(text: str) -> tuple:
    toks = re.findall(r"[^\W_]+(?:'[^\W_]+)?", norm(text))
    return tuple(t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t for t in toks)


# keep in sync with search-demand-discovery (generic modifiers and function words)
GENERIC_MODIFIERS = ["free", "download", "downloads", "best", "top", "online", "new", "latest", "hd", "4k",
                     "official", "cheap", "for free", "free download"]
FILLER = set("a an the of for to with without and or by from at is are be this that these those my your".split())


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:'[^\W_]+)?", norm(text))


def stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t


def contains_seq(hay: tuple, needle: tuple) -> int:
    n = len(needle)
    for i in range(len(hay) - n + 1):
        if hay[i : i + n] == needle:
            return i
    return -1


class Grouper:
    """Mechanical grouping for review. It proposes units; the model decides every unit.

    Uses the discovery contract only: seeds (+ aliases) and boundary (modifiers, head terms,
    adjacent/out terms). Without seeds every keyword is a single item.
    """

    def __init__(self, p: Paths):
        b = read_json(p.boundary, {}) or {}
        self.out = [(t, norm(x)) for x in b.get("out_terms", []) for t in [stem_tuple(x)] if t]
        self.adj = [(t, norm(x)) for x in b.get("adjacent_terms", []) for t in [stem_tuple(x)] if t]
        self.axes = {}
        for axis, vals in (b.get("modifiers") or {}).items():
            for v in vals:
                t = stem_tuple(v)
                if t and axis != "_generic":
                    self.axes[t] = (axis, norm(v))
        self.lex = set(self.axes) | {stem_tuple(x) for x in GENERIC_MODIFIERS + list(b.get("head_terms") or [])
                                     + list((b.get("modifiers") or {}).get("_generic", [])) if stem_tuple(x)}
        self.seeds = []
        for sd in read_jsonl(p.seo / "discovery" / "seeds.jsonl"):
            if sd.get("status") in ("rejected",):
                continue
            for t in [sd["text"]] + list(sd.get("aliases") or []):
                if stem_tuple(t):
                    self.seeds.append((stem_tuple(t), sd["text"]))
        self.seeds.sort(key=lambda x: -len(x[0]))

    def _strip(self, toks: list[str]):
        """Return (leftover words, attributes) after removing modifier phrases, head terms and filler."""
        st = [stem(t) for t in toks]
        attrs, left, i = defaultdict(list), [], 0
        while i < len(st):
            hit = next((n for n in (4, 3, 2, 1) if i + n <= len(st) and tuple(st[i : i + n]) in self.lex), 0)
            if hit:
                ax = self.axes.get(tuple(st[i : i + hit]))
                if ax and ax[1] not in attrs[ax[0]]:
                    attrs[ax[0]].append(ax[1])
                i += hit
                continue
            if toks[i] not in FILLER and not re.fullmatch(r"\d+", toks[i]):
                left.append(toks[i])
            i += 1
        return left, {k: v for k, v in attrs.items() if v}

    def classify(self, keyword: str):
        """-> (unit_key, seed_text, attributes). unit_key None means review the keyword on its own.

        Units: ("boundary", ring, term), ("variants", seed) and ("facet", extra words). Facet units
        only become groups when enough keywords share them (review_facet_min)."""
        toks = tokens(keyword)
        st = tuple(stem(t) for t in toks)
        for ph, term in self.out:
            if contains_seq(st, ph) >= 0:
                return ("boundary", "out", term), None, {}
        for ph, term in self.adj:
            if contains_seq(st, ph) >= 0:
                return ("boundary", "adjacent", term), None, {}
        hit = next(((k, txt) for k, txt in self.seeds if contains_seq(st, k) >= 0), None)
        if not hit:
            return None, None, {}
        pos = contains_seq(st, hit[0])
        left, attrs = self._strip(toks[:pos] + toks[pos + len(hit[0]):])
        if not left:
            return ("variants", hit[1]), hit[1], attrs
        return ("facet", " ".join(left)), hit[1], attrs  # same extra words across seeds


def site_host(p: Paths) -> str:
    url = ((read_json(p.boundary, {}) or {}).get("product") or {}).get("url") or ""
    return urllib.parse.urlparse(url if "://" in url else "https://" + url).netloc.lower().removeprefix("www.")


def page_key(url: str, host: str) -> str:
    """Registry URLs may be paths; GSC pages are absolute. Compare both as host/path."""
    return norm_url(host + url) if url.startswith("/") else norm_url(url)


def registry_form(url: str, host: str) -> str:
    """Absolute URLs on the site host become paths (the registry's usual form); others stay absolute."""
    u = urllib.parse.urlparse(url.strip())
    if u.netloc and u.netloc.lower().removeprefix("www.") == host:
        return u.path.rstrip("/") or "/"
    return url.strip()


def url_tokens(url: str) -> set:
    path = urllib.parse.urlparse(url).path if "://" in url else url
    return {stem(t) for t in re.findall(r"[a-z0-9]+", path.lower()) if not re.fullmatch(r"\d+", t)}


def head_stems(p: Paths) -> set:
    b = read_json(p.boundary, {}) or {}
    return {stem(t) for x in list(b.get("head_terms") or []) + ["sound", "sounds", "effect", "effects"]
            for t in tokens(x)}


def cluster_cores(c: dict, drop: set) -> list:
    """Stem sets naming a cluster (entity and label, minus head terms), for lexical page hints only."""
    cores = []
    for text in (c.get("entity"), c.get("label"), c["id"].replace("_", " ")):
        core = {stem(t) for t in tokens(text or "") if t not in FILLER} - drop
        if core and core not in cores:
            cores.append(core)
    return cores


def names_cluster(cores: list, toks: set) -> bool:
    return any(core <= toks for core in cores)


def live_url_hints(cores: list, candidates: dict, limit: int = 5) -> list:
    """Candidate live pages whose URL (or title, when known) names the cluster."""
    hits = [u for u, toks in candidates.items() if names_cluster(cores, toks)]
    return sorted(hits, key=lambda u: (len(candidates[u]), u))[:limit]


def load_site_urls(p: Paths):
    return read_json(p.site_urls, None)


def obs_strength(o: dict) -> int:
    return {"gsc_impression": 0, "onsite_request": 1, "historical_volume": 2, "trend_related": 3,
            "related_search": 4, "search_suggestion": 5}.get(o["kind"], 6)


def compact_obs(o: dict) -> dict:
    return {"id": o["id"], "source": o["source"], "kind": o["kind"], "market": o["market"],
            "period": o.get("period"), "metrics": {k: v for k, v in (o.get("metrics") or {}).items() if k != "monthly"},
            "query": (o.get("via") or {}).get("query")}


# ---------------------------------------------------------------- commands: init / review

def cmd_init(args):
    p = Paths(args.root)
    for d in (p.m, p.reviews, p.gsc, p.changesets, p.work):
        d.mkdir(parents=True, exist_ok=True)
    for f in (p.clusters, p.decisions, p.pages, p.mappings):
        f.touch(exist_ok=True)
    warn = [] if p.boundary.exists() else ["seo/boundary.json missing: bootstrap with search-demand-discovery"]
    emit({"initialized": str(p.m), "warnings": warn})


def cmd_prepare_review(args):
    p = Paths(args.root)
    require(p)
    cfg = cfg_of(p)
    pool = load_pool(p)
    decisions = load_decisions(p)
    clusters = load_clusters(p)
    market = market_of(p)
    wanted = set(args.id or [])
    picked, protected = [], 0
    for k, e in pool.items():
        langs = {o["market"].get("language") for o in e["observations"]}
        if market["language"] not in langs and "und" not in langs:
            continue
        d = decisions.get(k)
        reason = None
        if wanted:
            if k in wanted:
                reason = "requested"
        elif d is None:
            reason = "new"
        elif d["actor"] == "human":
            protected += 1
            continue
        elif d["evidence_hash"] != e["evidence_hash"]:
            reason = "evidence_changed"
        elif d.get("cluster_id") and clusters.get(d["cluster_id"], {}).get("version", 0) > d.get("cluster_version", 0):
            reason = "definition_changed"
        elif args.pending and d["status"] == "pending":
            reason = "pending"
        if not reason:
            continue
        strength = min(obs_strength(o) for o in e["observations"])
        picked.append((strength, -len(e["observations"]), e["keyword"], k, reason))
    picked.sort()
    if not picked:
        emit({"batch": 0, "protected_human": protected, "note": "nothing to review"})
        return
    grouper = Grouper(p)
    units, singles_by_seed, seed_rank = {}, defaultdict(list), {}
    classified = []
    facet_size = Counter()
    for rank, (strength, _, kw, k, reason) in enumerate(picked):
        unit, seed, attrs = grouper.classify(kw)
        classified.append((rank, kw, k, reason, unit, seed, attrs))
        if unit and unit[0] == "facet":
            facet_size[unit] += 1
    for rank, kw, k, reason, unit, seed, attrs in classified:
        if seed and seed not in seed_rank:
            seed_rank[seed] = rank
        if unit and unit[0] == "facet" and facet_size[unit] < cfg["review_facet_min"]:
            unit = None
        if unit and not args.no_groups:
            units.setdefault(unit, {"rank": rank, "members": []})["members"].append((kw, k, reason, attrs, seed))
        else:
            singles_by_seed[seed].append((rank, kw, k, reason, attrs))
    ordered = []  # boundary groups, then per seed: its variant group and its single items, then unseeded
    for unit, u in sorted(units.items(), key=lambda x: x[1]["rank"]):
        if unit[0] == "boundary":
            ordered.append(("group", unit, u["members"]))
    for seed in sorted(seed_rank, key=seed_rank.get):
        if ("variants", seed) in units:
            ordered.append(("group", ("variants", seed), units[("variants", seed)]["members"]))
        for _, kw, k, reason, attrs in singles_by_seed.get(seed, []):
            ordered.append(("single", seed, (kw, k, reason, attrs)))
    for _, kw, k, reason, attrs in sorted(singles_by_seed.get(None, [])):
        ordered.append(("single", None, (kw, k, reason, attrs)))
    # facet groups last: their "@seed" decisions need the seeds' clusters decided first
    for unit, u in sorted(units.items(), key=lambda x: (-len(x[1]["members"]), x[1]["rank"])):
        if unit[0] == "facet":
            ordered.append(("group", unit, u["members"]))
    if args.only:  # review one kind of unit first, e.g. variants before facets
        ordered = [it for it in ordered if (it[1][0] if it[0] == "group" else "single") == args.only]
    max_units, max_kw = args.limit or cfg["review_batch"], cfg["review_max_keywords"]
    if args.plan:  # size the whole queue without writing a batch
        kinds = defaultdict(lambda: {"units": 0, "keywords": 0})
        n_batches, n_units, n_kw = 0, 0, 0
        for item in ordered:
            kind = item[1][0] if item[0] == "group" else "single"
            size = len(item[2]) if item[0] == "group" else 1
            kinds[kind]["units"] += 1
            kinds[kind]["keywords"] += size
            while size > 0:
                take = min(size, max_kw)
                if n_units and (n_units >= max_units or n_kw + take > max_kw):
                    n_batches, n_units, n_kw = n_batches + 1, 0, 0
                n_units, n_kw, size = n_units + 1, n_kw + take, size - take
        emit({"queued_keywords": len(picked), "by_kind": dict(kinds), "batches": n_batches + (1 if n_units else 0),
              "batch_limits": {"units": max_units, "keywords": max_kw}, "protected_human": protected})
        return
    batch, n_units, n_kw = [], 0, 0
    for item in ordered:
        size = len(item[2]) if item[0] == "group" else 1
        if batch and (n_units >= max_units or n_kw + min(size, max_kw) > max_kw):
            break
        if item[0] == "group" and size > max_kw:  # oversized group: take one slice now, the rest queues again
            item = ("group", item[1], item[2][:max_kw])
            size = max_kw
        batch.append(item)
        n_units += 1
        n_kw += size
    review_id = "rv_" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + os.urandom(2).hex()
    active = {cid: c for cid, c in clusters.items() if c["status"] in ("active", "hold")}
    members = Counter(d["cluster_id"] for d in decisions.values() if d["status"] == "included")
    items, groups = [], []
    for item in batch:
        if item[0] == "single":
            kw, k, reason, attrs = item[2]
            e = pool[k]
            obs = sorted(e["observations"], key=obs_strength)[:8]
            d = decisions.get(k)
            hints = [cid for cid, c in active.items() if c.get("entity") and norm(c["entity"]) in kw]
            items.append({"keyword_id": k, "keyword": kw, "seed": item[1], "reason_queued": reason,
                          "evidence_hash": e["evidence_hash"], "observation_count": len(e["observations"]),
                          "observations": [compact_obs(o) for o in obs], "attributes_detected": attrs,
                          "previous": {x: d.get(x) for x in ("status", "cluster_id", "actor", "reason", "attributes")} if d else None,
                          "lexical_hints": hints[:5]})
        else:
            unit = item[1]
            gid = "g_" + sha("|".join(unit) + "|" + ",".join(sorted(m[1] for m in item[2])), 10)
            gm = []
            for kw, k, reason, attrs, seed in item[2]:
                e = pool[k]
                obs = sorted(e["observations"], key=obs_strength)
                gm.append({"keyword_id": k, "keyword": kw, "seed": seed, "reason_queued": reason,
                           "evidence_hash": e["evidence_hash"], "attributes_detected": attrs,
                           "observation_ids": [o["id"] for o in obs[:3]],
                           "sources": sorted({o["source"] for o in e["observations"]})})
            groups.append({"group_id": gid, "kind": unit[0], "seed": unit[1] if unit[0] == "variants" else None,
                           "facet": unit[1] if unit[0] == "facet" else None,
                           "boundary": {"ring": unit[1], "term": unit[2]} if unit[0] == "boundary" else None,
                           "members": gm})
    b = read_json(p.boundary, {}) or {}
    payload = {
        "schema": f"{S}/review-input@1",
        "review_id": review_id,
        "created_at": now(),
        "market": market,
        "protocol": {"statuses": sorted(STATUSES), "bases": sorted(BASES), "tasks": cfg["tasks"],
                     "deliveries": cfg["deliveries"], "page_types": sorted(cfg["page_types"])},
        "boundary": {k: b.get(k) for k in ("product", "rings", "modifiers", "adjacent_terms", "out_terms")},
        "clusters": [{"id": cid, "version": c["version"], "status": c["status"], "label": c.get("label"),
                      "intent": c["intent"], "entity": c["entity"], "page_type": c["page_type"],
                      "expected_result_set": c["expected_result_set"], "parent": c.get("parent"),
                      "definition": {x: c["definition"].get(x) for x in ("summary", "includes", "excludes", "neighbor_distinction")},
                      "members": members.get(cid, 0)} for cid, c in sorted(active.items())],
        "groups": groups,
        "keywords": items,
    }
    out = p.reviews / review_id / "input.json"
    write_json(out, payload)
    in_batch = len(items) + sum(len(g["members"]) for g in groups)
    emit({"review_id": review_id, "units": len(items) + len(groups), "groups": len(groups),
          "grouped_keywords": in_batch - len(items), "single_keywords": len(items), "keywords_in_batch": in_batch,
          "queued_total": len(picked), "protected_human": protected, "input": str(out)})


def seed_clusters(decisions: dict, pending: list) -> dict:
    """seed -> the cluster most of its included keywords belong to (applied decisions plus this batch)."""
    votes = defaultdict(Counter)
    for d in list(decisions.values()) + [x for x in pending if x.get("cluster_id") not in (None, "@seed")]:
        if d.get("status") == "included" and d.get("seed") and d.get("cluster_id"):
            votes[d["seed"]][d["cluster_id"]] += 1
    return {s: c.most_common(1)[0][0] for s, c in votes.items()}


SHORTHAND_DEFAULTS = {"language", "intent"}


def expand_shorthand(d: dict, defaults: dict, cluster_defs: dict, item: dict | None) -> None:
    """Fill what a decision may leave out. The model still decides status, cluster and reason per keyword."""
    for f in SHORTHAND_DEFAULTS:
        if d.get(f) is None and defaults.get(f) is not None:
            d[f] = json.loads(json.dumps(defaults[f]))
    cid = d.get("cluster_id")
    c = cluster_defs.get(cid) if cid and cid != "@seed" else None
    if d.get("intent") == "cluster" and c and d.get("status") == "included":
        d["intent"] = {
            "task": {"value": c["intent"]["task"], "basis": "inferred", "reason": f"asks for what {cid} delivers"},
            "job": {"value": None, "basis": "unknown", "reason": "no concrete use stated"},
            "delivery": {"value": c["intent"]["delivery"], "basis": "inferred", "reason": f"same delivery as {cid}"},
        }
    it = d.get("intent")
    if isinstance(it, dict) and any(not isinstance(it.get(dim), dict) for dim in ("task", "job", "delivery")):
        # compact form {"task": "learn", "delivery": null}: a string is inferred with the decision's reason
        d["intent"] = {dim: it[dim] if isinstance(it.get(dim), dict) else (
            {"value": it[dim], "basis": "inferred", "reason": d.get("reason") or "see decision reason"}
            if it.get(dim) is not None else {"value": None, "basis": "unknown", "reason": "not stated"})
            for dim in ("task", "job", "delivery")}
    if d.get("status") == "included" and not d.get("entity") and c:
        d["entity"] = c["entity"]
    if item is not None:
        if not d.get("evidence_ids"):
            d["evidence_ids"] = [o["id"] for o in item.get("observations") or []] or list(item.get("observation_ids") or [])
        if "attributes" not in d:
            d["attributes"] = {k: list(v) for k, v in (item.get("attributes_detected") or {}).items()}


def check_intent(kw: str, intent, cfg, where: str, errors: list):
    if intent == "cluster":
        errors.append(f"{where}: intent \"cluster\" only resolves for an included decision with a cluster")
        return
    if not isinstance(intent, dict):
        errors.append(f"{where}: intent must be an object with task/job/delivery")
        return
    for dim in ("task", "job", "delivery"):
        v = intent.get(dim)
        if not isinstance(v, dict):
            errors.append(f"{where}: intent.{dim} missing")
            continue
        basis, value = v.get("basis"), v.get("value")
        if basis not in BASES:
            errors.append(f"{where}: intent.{dim}.basis must be one of {sorted(BASES)}")
        if basis == "unknown" and value is not None:
            errors.append(f"{where}: intent.{dim} unknown must have value null")
        if basis in ("explicit", "inferred") and value is None:
            errors.append(f"{where}: intent.{dim} {basis} needs a value")
        if basis == "explicit" and (not v.get("quote") or norm(v["quote"]) not in kw):
            errors.append(f"{where}: intent.{dim} explicit needs a quote that appears in the keyword")
        if not v.get("reason"):
            errors.append(f"{where}: intent.{dim}.reason required")
        if dim == "task" and value is not None and value not in cfg["tasks"]:
            errors.append(f"{where}: task {value!r} not in {cfg['tasks']}")
        if dim == "delivery" and value is not None and value not in cfg["deliveries"]:
            errors.append(f"{where}: delivery {value!r} not in {cfg['deliveries']}")


def check_cluster(c: dict, cfg, clusters: dict, pool_ids: set, errors: list):
    cid = c.get("id", "")
    where = f"cluster {cid}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", cid):
        errors.append(f"{where}: id must be snake_case ascii")
    for f in ("label", "entity", "expected_result_set", "page_type"):
        if not c.get(f):
            errors.append(f"{where}: {f} required")
    it = c.get("intent") or {}
    if it.get("task") not in cfg["tasks"] or it.get("delivery") not in cfg["deliveries"]:
        errors.append(f"{where}: intent needs task in tasks and delivery in deliveries")
    if c.get("page_type") and c["page_type"] not in cfg["page_types"]:
        errors.append(f"{where}: page_type must be one of {sorted(cfg['page_types'])}")
    d = c.get("definition") or {}
    for f in ("summary", "neighbor_distinction"):
        if not d.get(f):
            errors.append(f"{where}: definition.{f} required")
    for f in ("includes", "excludes", "representative_keywords", "evidence_ids"):
        if not isinstance(d.get(f), list):
            errors.append(f"{where}: definition.{f} must be a list")
    if not d.get("includes") or not d.get("representative_keywords") or not d.get("evidence_ids"):
        errors.append(f"{where}: includes, representative_keywords and evidence_ids must be non-empty")
    bad = [e for e in d.get("evidence_ids") or [] if e not in pool_ids]
    if bad:
        errors.append(f"{where}: unknown evidence ids {bad[:3]}")
    old = clusters.get(cid)
    if old:
        changed = [f for f in IDENTITY if json.dumps(old.get(f), sort_keys=True) != json.dumps(c.get(f), sort_keys=True)]
        if changed:
            errors.append(f"{where}: identity fields {changed} changed; create a new id and merge/split instead")
        if c.get("version") != old["version"] + 1:
            errors.append(f"{where}: definition update must set version {old['version'] + 1}")
        if old["status"] == "retired":
            errors.append(f"{where}: retired clusters cannot be redefined")
    elif c.get("version", 1) != 1:
        errors.append(f"{where}: new cluster version must be 1")


def cmd_apply_review(args):
    p = Paths(args.root)
    require(p)
    cfg = cfg_of(p)
    out = read_json(Path(args.file))
    if not isinstance(out, dict):
        die("review output must be a JSON object")
    actor = args.actor
    pool = load_pool(p)
    pool_obs = {o["id"] for e in pool.values() for o in e["observations"]}
    clusters = load_clusters(p)
    decisions = load_decisions(p)
    review_id = out.get("review_id") if actor == "model" else "human_" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + os.urandom(2).hex()
    if not review_id:
        die("model output needs the review_id from its input")
    rdir = p.reviews / review_id
    digest = sha(json.dumps(out, sort_keys=True, ensure_ascii=False))
    applied = read_json(rdir / "applied.json")
    if applied:
        if applied["output_sha"] == digest:
            emit({"review_id": review_id, "status": "already_applied"})
            return
        die(f"{review_id} was already applied with different content; prepare a new review")
    errors, warnings = [], []
    inp = None
    if actor == "model":
        inp = read_json(rdir / "input.json")
        if not inp:
            die(f"no prepared input for {review_id}")
        for item in inp["keywords"] + [m for g in inp.get("groups", []) for m in g["members"]]:
            e = pool.get(item["keyword_id"])
            if not e or e["evidence_hash"] != item["evidence_hash"]:
                errors.append(f"{item['keyword']!r}: evidence changed since prepare; prepare a new review")
        for c in inp["clusters"]:
            if clusters.get(c["id"], {}).get("version") != c["version"]:
                errors.append(f"cluster {c['id']} changed since prepare; prepare a new review")
    elif not out.get("reason_source"):
        die("human decisions need reason_source (where the user stated them, e.g. 'chat 2026-09-29')")

    new_clusters = {c.get("id"): c for c in out.get("clusters", [])}
    for c in out.get("clusters", []):
        d = c.get("definition") or {}
        if isinstance(d, dict) and not d.get("evidence_ids"):  # shorthand: the representative keywords' own observations
            d["evidence_ids"] = [o["id"] for r in d.get("representative_keywords") or []
                                 for o in sorted((pool.get(kw_id(norm(r))) or {}).get("observations", []), key=obs_strength)[:3]]
        check_cluster(c, cfg, clusters, pool_obs, errors)
    usable = {cid for cid, c in clusters.items() if c["status"] in ("active", "hold")} | set(new_clusters)

    defaults = out.get("defaults") or {}
    if not isinstance(defaults, dict) or set(defaults) - SHORTHAND_DEFAULTS:
        errors.append(f"defaults may only set {sorted(SHORTHAND_DEFAULTS)}")
        defaults = {}
    for gd in out.get("group_decisions", []):
        for f in SHORTHAND_DEFAULTS:
            if gd.get(f) is None and defaults.get(f) is not None:
                gd[f] = json.loads(json.dumps(defaults[f]))
    decs = list(out.get("decisions", []))
    seed_of = {i["keyword_id"]: i.get("seed") for i in (inp or {}).get("keywords", [])}
    seed_of.update({m["keyword_id"]: m.get("seed") for g in (inp or {}).get("groups", []) for m in g["members"]})
    for d in decs:
        d.setdefault("seed", seed_of.get(d.get("keyword_id")))
    groups_in = {g["group_id"]: g for g in (inp or {}).get("groups", [])}
    for gd in out.get("group_decisions", []):
        g = groups_in.get(gd.get("group_id"))
        if not g:
            errors.append(f"group decision for unknown group {gd.get('group_id')!r}")
            continue
        member_ids = {m["keyword_id"] for m in g["members"]}
        exc = set(gd.get("except") or [])
        if gd.get("cluster_id") == "@seed":
            seed_cluster = seed_clusters(decisions, decs)
            missing = [m["keyword"] for m in g["members"] if m["keyword_id"] not in exc
                       and not seed_cluster.get(m.get("seed"))]
            if missing:
                errors.append(f"group {g['group_id']}: '@seed' needs each member's seed to have a cluster first; "
                              f"decide those seeds or except: {missing[:5]}")
        if exc - member_ids:
            errors.append(f"group {g['group_id']}: except lists non-members {sorted(exc - member_ids)[:3]}")
        for m in g["members"]:
            if m["keyword_id"] in exc:
                continue  # decided individually in "decisions"
            cid = gd.get("cluster_id")
            if cid == "@seed":
                cid = seed_clusters(decisions, decs).get(m.get("seed"))
            attrs = {k: list(v) for k, v in (m["attributes_detected"] or {}).items()}
            member_st = stem_tuple(m["keyword"])
            for axis, vals in (gd.get("add_attributes") or {}).items():
                for v in vals:  # a group attribute only applies where the member actually says it
                    if contains_seq(member_st, stem_tuple(v)) >= 0 and v not in attrs.setdefault(axis, []):
                        attrs[axis].append(v)
                if not attrs.get(axis):
                    attrs.pop(axis, None)
            decs.append({"keyword_id": m["keyword_id"], "status": gd.get("status"), "language": gd.get("language"),
                         "intent": gd.get("intent"), "entity": gd.get("entity") or m.get("seed"),
                         "attributes": attrs, "cluster_id": cid, "seed": m.get("seed"),
                         "reason": f"{gd.get('reason') or ''} [group {g['group_id']}]" if gd.get("reason") else None,
                         "evidence_ids": m["observation_ids"], "group_id": g["group_id"]})
    cluster_defs = {cid: c for cid, c in clusters.items()}
    cluster_defs.update(new_clusters)
    single_items = {i["keyword_id"]: i for i in (inp or {}).get("keywords", [])}
    member_items = {m["keyword_id"]: m for g in groups_in.values() for m in g["members"]}
    for d in decs:
        k = d.get("keyword_id")
        expand_shorthand(d, defaults, cluster_defs, single_items.get(k) or (None if d.get("group_id") else member_items.get(k)))
    ids = [d.get("keyword_id") for d in decs]
    if len(ids) != len(set(ids)):
        errors.append("each keyword needs exactly one decision (duplicates found)")
    if inp:
        expected = {i["keyword_id"] for i in inp["keywords"]} | {m["keyword_id"] for g in groups_in.values()
                                                                  for m in g["members"]}
        if set(ids) != expected:
            errors.append(f"decisions must cover exactly the batch: missing {sorted(expected - set(ids))[:5]}, "
                          f"extra {sorted(set(ids) - expected)[:5]}")
    for d in decs:
        k = d.get("keyword_id")
        e = pool.get(k)
        if not e:
            errors.append(f"unknown keyword_id {k}")
            continue
        kw = e["keyword"]
        where = f"{kw!r}"
        if d.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {sorted(STATUSES)}")
        if not d.get("language"):
            errors.append(f"{where}: language required (judged, not the request parameter)")
        if not d.get("reason"):
            errors.append(f"{where}: reason required")
        own = {o["id"] for o in e["observations"]}
        ev = d.get("evidence_ids") or []
        if not ev or any(x not in own for x in ev):
            errors.append(f"{where}: evidence_ids must be non-empty and belong to this keyword")
        check_intent(kw, d.get("intent"), cfg, where, errors)
        if d.get("status") == "included":
            if not d.get("entity"):
                errors.append(f"{where}: included needs entity")
            if d.get("cluster_id") not in usable:
                errors.append(f"{where}: cluster_id {d.get('cluster_id')!r} is not an active or newly defined cluster")
        elif d.get("cluster_id") is not None:
            errors.append(f"{where}: {d.get('status')} decisions must have cluster_id null")
        attrs = d.get("attributes") or {}
        if not isinstance(attrs, dict) or any(not isinstance(v, list) for v in attrs.values()):
            errors.append(f"{where}: attributes must map axis -> list")
        else:
            kw_st = stem_tuple(kw)
            for axis, vals in attrs.items():
                for v in vals:
                    if contains_seq(kw_st, stem_tuple(v)) < 0:
                        warnings.append(f"{where}: attribute {axis}={v!r} is not literally in the keyword")
        prev = decisions.get(k)
        if prev and prev["actor"] == "human" and actor == "model":
            errors.append(f"{where}: human decision exists; the model cannot overwrite it")
    for c in new_clusters.values():
        reps = (c.get("definition") or {}).get("representative_keywords") or []
        members = {pool[d["keyword_id"]]["keyword"] for d in decs
                   if d.get("cluster_id") == c.get("id") and d.get("keyword_id") in pool}
        existing = {pool[k]["keyword"] for k, d in decisions.items()
                    if d.get("cluster_id") == c.get("id") and k in pool}
        missing = [r for r in reps if norm(r) not in members | existing]
        if missing:
            errors.append(f"cluster {c.get('id')}: representative keywords must be members: {missing[:3]}")

    ops = out.get("operations", [])
    for op in ops:
        kind = op.get("kind")
        src = op.get("from")
        src = [src] if isinstance(src, str) else (src or [])
        dst = op.get("to")
        dst = [dst] if isinstance(dst, str) else (dst or [])
        if kind not in ("merge", "split") or not op.get("reason"):
            errors.append(f"operation needs kind merge|split and reason: {op}")
            continue
        if kind == "merge" and len(dst) != 1:
            errors.append("merge needs exactly one target")
        if kind == "split" and (len(src) != 1 or len(dst) < 2):
            errors.append("split needs one source and at least two targets")
        for s in src:
            if clusters.get(s, {}).get("status") not in ("active", "hold"):
                errors.append(f"{kind}: source {s} must be an existing active/hold cluster")
        for t in dst:
            if t not in usable or t in src:
                errors.append(f"{kind}: target {t} must be active or defined in this batch and differ from sources")
        op["_src"], op["_dst"] = src, dst
    if errors:
        die("review rejected:\n  " + "\n  ".join(errors[:60]) + ("\n  ..." if len(errors) > 60 else ""))

    ts = now()
    new_rows = []
    for c in new_clusters.values():
        row = dict(c, schema=f"{S}/cluster@1", status=clusters.get(c["id"], {}).get("status", "active"),
                   successors=[], parent=c.get("parent"), promoted_attrs=c.get("promoted_attrs") or {},
                   updated_at=ts, review_id=review_id)
        new_rows.append(row)
        clusters[c["id"]] = row
    dec_rows = []
    for d in decs:
        cid = d.get("cluster_id")
        dec_rows.append({
            "schema": f"{S}/decision@1", "keyword_id": d["keyword_id"], "keyword": pool[d["keyword_id"]]["keyword"],
            "status": d["status"], "cluster_id": cid, "cluster_version": clusters[cid]["version"] if cid else None,
            "language": d["language"], "intent": d["intent"], "entity": d.get("entity"),
            "attributes": d.get("attributes") or {}, "reason": d["reason"], "evidence_ids": d["evidence_ids"],
            "evidence_hash": pool[d["keyword_id"]]["evidence_hash"], "actor": actor, "review_id": review_id,
            "group_id": d.get("group_id"), "seed": d.get("seed"),
            "reason_source": out.get("reason_source"), "decided_at": ts,
        })
    decided = {r["keyword_id"] for r in dec_rows}
    for op in ops:
        for s in op["_src"]:
            old = clusters[s]
            new_rows.append(dict(old, status="retired", successors=op["_dst"], updated_at=ts, review_id=review_id,
                                 retired_reason=op["reason"]))
            for k, d in decisions.items():
                if d.get("cluster_id") != s or d["status"] != "included" or k in decided:
                    continue
                moved = dict(d, decided_at=ts, actor="lineage", review_id=review_id,
                             reason=f"{op['kind']} {s} -> {','.join(op['_dst'])}: {op['reason']}")
                if op["kind"] == "merge":
                    moved.update(cluster_id=op["_dst"][0], cluster_version=clusters[op["_dst"][0]]["version"])
                else:
                    moved.update(status="pending", cluster_id=None, cluster_version=None)
                dec_rows.append(moved)
    append_jsonl(p.clusters, new_rows)
    append_jsonl(p.decisions, dec_rows)
    write_json(rdir / "output.json", out)
    write_json(rdir / "applied.json", {"review_id": review_id, "output_sha": digest, "applied_at": ts, "actor": actor,
                                       "decisions": len(decs), "clusters": len(new_clusters), "operations": len(ops)})
    emit({"review_id": review_id, "applied": True, "decisions": dict(Counter(d["status"] for d in decs)),
          "clusters_written": len(new_rows), "operations": len(ops), "warnings": warnings[:30]})


# ---------------------------------------------------------------- analysis and gates

def load_pages(p: Paths) -> dict:
    return {r["url"]: r for r in read_jsonl(p.pages)}


def load_mappings(p: Paths) -> list[dict]:
    return read_jsonl(p.mappings)


def serp_captures(p: Paths) -> dict:
    return current([dict(r, _key=norm(r["query"])) for r in read_jsonl(p.serp)], "_key")


def cmd_analyze(args):
    p = Paths(args.root)
    require(p)
    cfg = cfg_of(p)
    pool = load_pool(p)
    clusters = load_clusters(p)
    decisions = load_decisions(p)
    pages = load_pages(p)
    mappings = load_mappings(p)
    inv = (read_json(p.inventory, {}) or {}).get("clusters", {})
    serp = serp_captures(p)
    host = site_host(p)
    snap = load_site_urls(p)
    registered = {page_key(u, host) for u in pages}
    drop = head_stems(p)
    unregistered = {} if not snap else {
        u: url_tokens(u) | {stem(t) for t in tokens((snap.get("titles") or {}).get(u, ""))}
        for u in snap["urls"] if page_key(u, host) not in registered}
    members = defaultdict(list)
    for k, d in decisions.items():
        if d["status"] == "included" and d.get("cluster_id") and k in pool:
            members[d["cluster_id"]].append((pool[k], d))
    by_cluster_maps = defaultdict(list)
    for m in mappings:
        by_cluster_maps[m["cluster_id"]].append(m)
    g, pr, promo = cfg["gate"], cfg["priority"], cfg["promotion"]
    report, needs_serp = [], []
    for cid, c in sorted(clusters.items()):
        if c["status"] not in ("active", "hold"):
            continue
        mem = members.get(cid, [])
        planner_best, gsc_sum, gsc_periods, sources, kinds = None, 0.0, set(), Counter(), Counter()
        attrs = defaultdict(lambda: {"members": 0, "examples": [], "gsc": 0.0, "planner_high": 0})
        for e, d in mem:
            latest_gsc = None
            for o in e["observations"]:
                sources[o["source"]] += 1
                kinds[o["kind"]] += 1
                vol = (o.get("metrics") or {}).get("avg_monthly_searches")
                if o["kind"] == "historical_volume" and vol and (planner_best is None or vol["high"] > planner_best[1]):
                    planner_best = (e["keyword"], vol["high"], o.get("period"))
                if o["kind"] == "gsc_impression" and (latest_gsc is None or o["period"]["end"] > latest_gsc["period"]["end"]):
                    latest_gsc = o
            if latest_gsc:
                gsc_sum += (latest_gsc.get("metrics") or {}).get("impressions") or 0
                gsc_periods.add(f"{latest_gsc['period']['start']}..{latest_gsc['period']['end']}")
            for axis, vals in (d.get("attributes") or {}).items():
                for v in vals:
                    a = attrs[f"{axis}={norm(v)}"]
                    a["members"] += 1
                    if len(a["examples"]) < 3:
                        a["examples"].append(e["keyword"])
        evidence = {"external": bool(mem), "serp": any(norm(e["keyword"]) in serp for e, _ in mem),
                    "gsc": gsc_sum > 0}
        planner_high = planner_best[1] if planner_best else 0
        strong = planner_high >= g["strong_planner_high"] or gsc_sum >= g["strong_gsc_impressions"]
        if planner_high >= pr["p0_planner_high"] or gsc_sum >= pr["p0_gsc_impressions"]:
            tier = "P0"
        elif planner_high >= pr["p1_planner_high"] or gsc_sum > 0 or len(mem) >= pr["p1_members"]:
            tier = "P1"
        else:
            tier = "P2"
        maps = by_cluster_maps.get(cid, [])
        primary = next((m for m in maps if m["role"] == "primary"), None)
        items = (inv.get(cid) or {}).get("items")
        min_items = cfg["page_types"].get(c["page_type"], {}).get("min_items", 0)
        checks = {
            "members": {"pass": len(mem) >= g["min_keywords"] or strong, "value": len(mem)},
            "inventory": {"pass": items is not None and items >= min_items, "value": items, "need": min_items},
            "serp_checked": {"pass": evidence["serp"] or not g["require_serp_for_create"]},
            "parent_page": {"value": next((m["page"] for m in by_cluster_maps.get(c.get("parent") or "", [])
                                           if m["role"] == "primary"), None)},
        }
        hints = [] if primary else live_url_hints(cluster_cores(c, drop), unregistered)
        if c["status"] == "hold":
            suggestion = "hold"
        elif hints:  # a live page probably serves this already; register it before planning a new one
            suggestion = "check_existing_page"
            checks["live_url_hints"] = hints
        elif primary:
            page = pages.get(primary["page"], {})
            newer = sum(1 for _, d in mem if d["decided_at"] > primary.get("updated_at", ""))
            suggestion = "keep_or_improve_existing"
            checks["mapped"] = {"page": primary["page"], "page_status": page.get("status"),
                                "members_since_mapping": newer}
        elif all(checks[x]["pass"] for x in ("members", "inventory", "serp_checked")):
            suggestion = "create_candidate"
        else:
            missing = [x for x in ("members", "inventory", "serp_checked") if not checks[x]["pass"]]
            suggestion = "improve_parent_or_defer" if checks["parent_page"]["value"] else "defer"
            checks["missing"] = missing
        if not primary and not evidence["serp"] and mem:
            rep = (c.get("definition") or {}).get("representative_keywords", [mem[0][0]["keyword"]])[0]
            needs_serp.append({"type": "page_type", "cluster_id": cid, "queries": [rep]})
        promotions = []
        inv_attrs = (inv.get(cid) or {}).get("attrs", {})
        for key, a in sorted(attrs.items(), key=lambda kv: -kv[1]["members"]):
            if a["members"] < promo["min_keywords"] or key.split("=", 1)[0] in promo.get("exclude_axes", []):
                continue
            ai = inv_attrs.get(key)
            cand = {"attribute": key, "members": a["members"], "examples": a["examples"], "inventory": ai,
                    "inventory_ok": ai is not None and ai >= promo["min_items"]}
            promotions.append(cand)
            rep = (c.get("definition") or {}).get("representative_keywords", [None])[0]
            if rep and a["examples"]:
                needs_serp.append({"type": "promotion", "cluster_id": cid, "attribute": key,
                                   "queries": [rep, a["examples"][0]]})
        report.append({
            "cluster_id": cid, "label": c.get("label"), "status": c["status"], "page_type": c["page_type"],
            "members": len(mem), "tier": tier, "evidence": evidence,
            "demand": {"planner_best": planner_best, "gsc_impressions_latest_sum": gsc_sum,
                       "gsc_periods": sorted(gsc_periods), "sources": dict(sources), "kinds": dict(kinds),
                       "note": "signals are listed per source; they are never summed into one demand score"},
            "mappings": [{k: m.get(k) for k in ("page", "role", "decision", "conditions")} for m in maps],
            "suggestion": suggestion, "checks": checks, "attribute_candidates": promotions,
        })
    tier_rank = {"P0": 0, "P1": 1, "P2": 2}
    report.sort(key=lambda r: (tier_rank[r["tier"]], -r["members"]))
    budget = cfg["serp"]["budget_per_session"]
    if snap:
        coverage = {"snapshot_captured_at": snap.get("captured_at"), "source": snap.get("source"),
                    "live_urls": len(snap["urls"]), "unregistered": len(unregistered)}
        if unregistered:
            coverage["warning"] = (f"{len(unregistered)} live URLs are not in the registry; create_candidate and "
                                   "defer are unreliable until they are synced (sync-check, then a change set)")
    else:
        coverage = {"snapshot_captured_at": None,
                    "warning": "registry completeness unknown: run sync-check --sitemap <sitemap> first"}
    result = {"schema": f"{S}/analysis@1", "generated_at": now(), "registry_coverage": coverage, "clusters": report,
              "needs_serp": needs_serp[:budget], "needs_serp_total": len(needs_serp),
              "undecided_keywords": sum(1 for k in pool if k not in decisions),
              "pending_keywords": sum(1 for d in decisions.values() if d["status"] == "pending")}
    write_json(p.work / "analysis.json", result)
    emit({"analysis": str(p.work / "analysis.json"), "registry_coverage": coverage, "clusters": len(report),
          "by_suggestion": dict(Counter(r["suggestion"] for r in report)),
          "by_tier": dict(Counter(r["tier"] for r in report)),
          "needs_serp": len(needs_serp), "undecided_keywords": result["undecided_keywords"],
          "pending_keywords": result["pending_keywords"]})


def cmd_serp(args):
    p = Paths(args.root)
    require(p)
    cfg = cfg_of(p)["serp"]
    if args.action == "add":
        data = read_json(Path(args.file))
        rows = data.get("captures", data) if isinstance(data, dict) else data
        out = []
        for r in rows:
            results = r.get("results") or []
            urls = [x["url"] if isinstance(x, dict) else x for x in results]
            if not r.get("query") or not urls:
                die(f"capture needs query and results: {r}")
            out.append({"schema": f"{S}/serp-capture@1", "query": norm(r["query"]),
                        "market": r.get("market") or market_of(p), "captured_at": r.get("captured_at") or now(),
                        "urls": [norm_url(u) for u in urls][: cfg["top_n"]],
                        "result_types": r.get("result_types"), "features": r.get("features"),
                        "served_host": r.get("served_host"), "localized": r.get("localized"),
                        "note": r.get("note")})
        append_jsonl(p.serp, out)
        unknown = [x["query"] for x in out if not x["served_host"] or x["localized"] is None]
        emit({"captures_added": len(out), "warnings": [
            f"{len(unknown)} captures lack served_host/localized (which engine domain answered, and whether "
            f"the target market's ranking was verified): {unknown[:5]}"] if unknown else []})
        return
    caps = serp_captures(p)
    if args.pairs:
        pairs = read_json(Path(args.pairs))
    else:
        analysis = read_json(p.work / "analysis.json", {}) or {}
        pairs = [n["queries"] for n in analysis.get("needs_serp", []) if len(n["queries"]) == 2]
    results, missing = [], set()
    for a, b in pairs:
        ca, cb = caps.get(norm(a)), caps.get(norm(b))
        if not ca or not cb:
            missing.update(q for q, c in ((a, ca), (b, cb)) if not c)
            continue
        shared = len(set(ca["urls"][: cfg["top_n"]]) & set(cb["urls"][: cfg["top_n"]]))
        if shared >= cfg["merge_min_shared"]:
            verdict = "same_result_set"
        elif shared <= cfg["split_max_shared"]:
            verdict = "different_result_set"
        else:
            verdict = "related"
        results.append({"schema": f"{S}/serp-compare@1", "a": norm(a), "b": norm(b), "shared": shared,
                        "top_n": cfg["top_n"], "verdict": verdict, "compared_at": now(),
                        "captured": [ca["captured_at"], cb["captured_at"]]})
    append_jsonl(p.serp_cmp, results)
    emit({"compared": results, "missing_captures": sorted(missing)})


# ---------------------------------------------------------------- Search Console feedback

def parse_period(text: str):
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", (text or "").strip())
    if not m:
        die("--period must look like 2026-08-01..2026-08-28")
    return m.group(1), m.group(2)


def cmd_gsc(args):
    p = Paths(args.root)
    require(p)
    if args.action == "import":
        start, end = parse_period(args.period)
        path = Path(args.file).expanduser()
        filters = {}
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                names = {n.lower(): n for n in z.namelist()}
                qn = next((names[n] for n in names if n.endswith("queries.csv")), None)
                if not qn:
                    die("zip has no Queries.csv")
                text = z.read(qn).decode("utf-8-sig", errors="replace")
                fn = next((names[n] for n in names if n.endswith("filters.csv")), None)
                if fn:
                    for row in csv.reader(z.read(fn).decode("utf-8-sig", errors="replace").splitlines()[1:]):
                        if len(row) >= 2:
                            filters[row[0].strip().lower()] = row[1].strip()
        else:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        header = [h.strip().lower() for h in next(reader)]
        qi = next((header.index(h) for h in ("top queries", "query", "queries") if h in header), -1)
        pi = next((header.index(h) for h in ("page", "top pages", "landing page", "url") if h in header), -1)
        if qi < 0:
            die("no query column")
        fpage = args.page
        if not fpage and filters.get("page"):
            m = re.search(r"https?://\S+", filters["page"])
            fpage = m.group(0) if m else None
        rows = []
        for r in reader:
            if qi >= len(r) or not r[qi].strip():
                continue
            page = r[pi].strip() if 0 <= pi < len(r) else fpage
            vals = {}
            for name in ("clicks", "impressions", "ctr", "position"):
                if name in header and header.index(name) < len(r):
                    try:
                        vals[name] = float(r[header.index(name)].strip().rstrip("%"))
                    except ValueError:
                        vals[name] = None
            rows.append(dict(vals, query=norm(r[qi]), page=norm_url(page) if page else None))
        dest = p.gsc / f"{start}_{end}.jsonl"
        existing = {(x["query"], x["page"]) for x in read_jsonl(dest)}
        new = [dict(r, schema=f"{S}/gsc-row@1", period={"start": start, "end": end}) for r in rows
               if (r["query"], r["page"]) not in existing]
        append_jsonl(dest, new)
        emit({"window": f"{start}..{end}", "rows": len(rows), "added": len(new), "page_filter": fpage,
              "note": None if (pi >= 0 or fpage) else "no page dimension: rows only feed unmapped-demand checks"})
        return

    cfg = cfg_of(p)["gsc"]
    windows = sorted(p.gsc.glob("*.jsonl"))
    if not windows:
        die("no GSC windows imported; run: mapper.py gsc import --file ... --period START..END")
    use = windows[-cfg["windows_required"]:]
    decisions = load_decisions(p)
    by_kw = {d["keyword"]: d for d in decisions.values()}
    pages = load_pages(p)
    host = site_host(p)
    if not host and any(u.startswith("/") for u in pages):
        die("registry uses path URLs; set product.url in seo/boundary.json so GSC pages can be matched")
    keyed = {page_key(u, host): u for u in pages}
    primary = {m["cluster_id"]: page_key(m["page"], host) for m in load_mappings(p) if m["role"] == "primary"}
    latest_end = use[-1].stem.split("_")[1]
    latest_date = date.fromisoformat(latest_end)

    def age_days(url):
        pub = pages.get(keyed.get(url, ""), {}).get("published_at")
        return (latest_date - date.fromisoformat(pub[:10])).days if pub else None

    flags = defaultdict(lambda: defaultdict(list))
    unmapped = Counter()
    page_impr = Counter()
    for w in use:
        label = w.stem
        cluster_pages = defaultdict(Counter)
        attr_impr = defaultdict(Counter)
        for r in read_jsonl(w):
            impr = r.get("impressions") or 0
            d = by_kw.get(r["query"])
            if not d or d["status"] != "included":
                if w == use[-1]:
                    unmapped[r["query"]] += impr
                continue
            if not r.get("page"):
                continue
            if w == use[-1]:
                page_impr[r["page"]] += impr
            cid = d["cluster_id"]
            cluster_pages[cid][r["page"]] += impr
            if primary.get(cid) == r["page"]:
                for axis, vals in (d.get("attributes") or {}).items():
                    for v in vals:
                        attr_impr[(cid, r["page"])][f"{axis}={norm(v)}"] += impr
        for cid, cp in cluster_pages.items():
            total = sum(cp.values()) or 1
            heavy = [u for u, v in cp.items() if v / total >= cfg["cannibal_min_share"]]
            if len(heavy) >= 2:
                flags["cannibalization"][(cid, tuple(sorted(heavy)))].append(label)
            owner = primary.get(cid)
            top = cp.most_common(1)[0][0]
            if owner and top != owner:
                flags["wrong_owner"][(cid, top)].append(label)
            if not owner:
                flags["unowned_cluster"][(cid, top)].append(label)
        for (cid, page), attrs in attr_impr.items():
            for a, v in attrs.items():
                if v >= cfg["split_min_impressions"]:
                    flags["promotion_signal"][(cid, page, a)].append(label)
    need = len(use)
    out = {}
    for kind, items in flags.items():
        rows = []
        for key, labels in items.items():
            pagesin = [k for k in key if isinstance(k, str) and "/" in k] + [u for k in key if isinstance(k, tuple) for u in k]
            cooling = [u for u in pagesin if (age_days(u) is not None and age_days(u) < cfg["cooldown_days"])]
            status = "confirmed" if len(labels) >= need else "watch"
            if cooling and kind in ("cannibalization", "promotion_signal"):
                status = "cooldown"
            rows.append({"key": list(key) if not isinstance(key, str) else key, "windows": labels, "status": status,
                         "cooling_pages": cooling})
        out[kind] = rows
    retire = []
    for url, pg in pages.items():
        if pg.get("status") != "published" or not pg.get("published_at"):
            continue
        k = page_key(url, host)
        a = age_days(k)
        if a is not None and a >= cfg["retire_after_days"] and page_impr.get(k, 0) <= cfg["retire_max_impressions"]:
            retire.append({"page": url, "age_days": a, "impressions_latest": page_impr.get(k, 0)})
    result = {"schema": f"{S}/gsc-review@1", "generated_at": now(), "windows": [w.stem for w in use],
              "windows_required": cfg["windows_required"], "flags": out, "retire_candidates": retire,
              "unmapped_queries": [{"query": q, "impressions": v} for q, v in unmapped.most_common(200)],
              "notes": ["anonymized queries are absent from exports; missing queries do not mean missing demand",
                        "query and query+page views describe the same impressions; never add them together"]}
    write_json(p.work / "gsc-review.json", result)
    emit({"review": str(p.work / "gsc-review.json"), "windows": result["windows"],
          "flags": {k: dict(Counter(r["status"] for r in v)) for k, v in out.items()},
          "retire_candidates": len(retire), "unmapped_queries": len(unmapped)})


# ---------------------------------------------------------------- registry changes

def validate_state(clusters, decisions, pages, mappings, cfg) -> tuple[list, list]:
    errors, warnings = [], []
    for cid, c in clusters.items():
        if c["status"] == "retired":
            for s in c.get("successors") or []:
                if s not in clusters:
                    errors.append(f"cluster {cid}: successor {s} missing")
        if c.get("parent") and c["parent"] not in clusters:
            errors.append(f"cluster {cid}: parent {c['parent']} missing")
    for d in decisions.values():
        if d["status"] == "included":
            c = clusters.get(d.get("cluster_id"))
            if not c:
                errors.append(f"decision {d['keyword']!r}: cluster {d.get('cluster_id')} missing")
            elif c["status"] == "retired":
                errors.append(f"decision {d['keyword']!r}: points to retired cluster {c['id']}")
    prim = Counter()
    for m in mappings:
        if m["cluster_id"] not in clusters:
            errors.append(f"mapping: unknown cluster {m['cluster_id']}")
        if m["page"] not in pages:
            errors.append(f"mapping {m['cluster_id']}: page {m['page']} not in registry")
        if m["role"] not in ROLES or m["decision"] not in MAP_DECISIONS:
            errors.append(f"mapping {m['cluster_id']}: bad role/decision")
        if m["role"] == "primary":
            prim[m["cluster_id"]] += 1
        if m["role"] == "filter" and not m.get("conditions"):
            errors.append(f"mapping {m['cluster_id']}: filter role needs conditions")
    for cid, n in prim.items():
        if n > 1:
            errors.append(f"cluster {cid}: {n} primary pages (one owner page per cluster)")
    primary_pages = {m["page"] for m in mappings if m["role"] == "primary"}
    for url, pg in pages.items():
        st = pg.get("status")
        if st not in PAGE_STATUSES:
            errors.append(f"page {url}: status {st!r}")
        if pg.get("page_type") not in cfg["page_types"]:
            errors.append(f"page {url}: page_type {pg.get('page_type')!r}")
        if pg.get("indexable"):
            if pg.get("canonical", url) != url:
                errors.append(f"page {url}: indexable pages must be self-canonical")
            if st in ("redirected", "gone"):
                errors.append(f"page {url}: {st} pages cannot be indexable")
            if pg.get("page_type") == "filter" and url not in primary_pages:
                errors.append(f"page {url}: filter URLs stay noindex unless promoted to own a cluster")
        elif pg.get("canonical") and pg["canonical"] != url and pg["canonical"] not in pages:
            warnings.append(f"page {url}: canonical target {pg['canonical']} not in registry")
        if st == "redirected":
            t = pages.get(pg.get("redirect_to"))
            if not t:
                errors.append(f"page {url}: redirect target missing")
            elif t.get("status") == "redirected":
                errors.append(f"page {url}: redirect chain via {pg['redirect_to']}")
            elif t.get("status") != "published":
                warnings.append(f"page {url}: redirect target is {t.get('status')}")
        needs_cluster = cfg["page_types"].get(pg.get("page_type"), {}).get("needs_cluster", True)
        if st == "published" and pg.get("indexable") and needs_cluster and url not in primary_pages:
            warnings.append(f"page {url}: indexable but owns no cluster")
    return errors, warnings


def coverage_warnings(p: Paths, pages: dict) -> list:
    snap = load_site_urls(p)
    if not snap:
        return ["registry completeness unknown: no site URL snapshot (run sync-check --sitemap <sitemap>)"]
    host = site_host(p)
    live = {page_key(u, host) for u in snap["urls"]}
    keys = {page_key(u, host): u for u in pages}
    out = []
    missing = sorted(u for u in snap["urls"] if page_key(u, host) not in keys)
    if missing:
        out.append(f"{len(missing)} live URLs (snapshot {snap.get('captured_at')}) not in the registry, "
                   f"e.g. {missing[:5]}")
    gone = sorted(u for k, u in keys.items() if k not in live and pages[u].get("status") == "published"
                  and pages[u].get("indexable"))
    if gone:
        out.append(f"{len(gone)} published indexable registry pages absent from the live snapshot, e.g. {gone[:5]}")
    return out


def cmd_apply_changes(args):
    p = Paths(args.root)
    require(p)
    cfg = cfg_of(p)
    cs = read_json(Path(args.file))
    if not isinstance(cs, dict) or not cs.get("id"):
        die("change set needs an id")
    if not cs.get("approved_by") and not args.dry_run:
        die("change set needs approved_by (who approved it and where); --dry-run checks a proposal without it")
    dest = p.changesets / f"{cs['id']}.json"
    if dest.exists():
        die(f"change set {cs['id']} already applied")
    before = {"pages": len(load_pages(p)), "mappings": len(load_mappings(p))}
    clusters = load_clusters(p)
    decisions = load_decisions(p)
    pages = load_pages(p)
    mappings = load_mappings(p)
    pool = load_pool(p)
    pool_obs = {o["id"] for e in pool.values() for o in e["observations"]}
    ts = now()
    new_clusters, new_decisions, errors = [], [], []
    for i, ch in enumerate(cs.get("changes", [])):
        kind = ch.get("kind")
        where = f"change {i} ({kind})"
        if not ch.get("reason"):
            errors.append(f"{where}: reason required")
        if kind == "page_upsert":
            url = ch.get("url")
            if not url or not url.startswith("/") and "://" not in url:
                errors.append(f"{where}: url must be a path or absolute URL")
                continue
            row = dict(pages.get(url, {"schema": f"{S}/page@1", "url": url, "created_at": ts}))
            for k in ("page_type", "status", "indexable", "canonical", "title", "parent", "covered_attributes",
                      "published_at", "redirect_to", "experiment", "notes"):
                if k in ch:
                    row[k] = ch[k]
            row.setdefault("canonical", url)
            row["updated_at"] = ts
            pages[url] = row
        elif kind == "map":
            m = {k: ch.get(k) for k in ("cluster_id", "page", "role", "decision", "conditions")}
            mappings = [x for x in mappings if not (x["cluster_id"] == m["cluster_id"] and x["page"] == m["page"]
                                                     and x["role"] == m["role"])]
            mappings.append(dict(m, schema=f"{S}/mapping@1", reason=ch["reason"], updated_at=ts, changeset=cs["id"]))
        elif kind == "unmap":
            mappings = [x for x in mappings if not (x["cluster_id"] == ch.get("cluster_id") and x["page"] == ch.get("page"))]
        elif kind == "redirect":
            src, dst = ch.get("from"), ch.get("to")
            if src not in pages or dst not in pages:
                errors.append(f"{where}: both pages must be in the registry")
                continue
            pages[src] = dict(pages[src], status="redirected", redirect_to=dst, indexable=False, updated_at=ts)
            moved = []
            for x in mappings:
                if x["page"] == src:
                    x = dict(x, page=dst, updated_at=ts, changeset=cs["id"])
                moved.append(x)
            mappings = list({(x["cluster_id"], x["page"], x["role"]): x for x in moved}.values())
        elif kind == "cluster_status":
            c = clusters.get(ch.get("cluster_id"))
            if not c or ch.get("status") not in ("active", "hold", "ignored"):
                errors.append(f"{where}: needs existing cluster_id and status active|hold|ignored")
                continue
            row = dict(c, status=ch["status"], updated_at=ts, status_reason=ch["reason"])
            clusters[c["id"]] = row
            new_clusters.append(row)
        elif kind == "promote":
            parent = clusters.get(ch.get("parent"))
            nc = ch.get("cluster") or {}
            attr = ch.get("attribute") or {}
            if not parent or not attr or len(attr) != 1:
                errors.append(f"{where}: needs parent cluster and one attribute axis=value")
                continue
            errs = []
            check_cluster(nc, cfg, clusters, pool_obs, errs)
            errors.extend(f"{where}: {e}" for e in errs)
            axis, value = next(iter(attr.items()))
            row = dict(nc, schema=f"{S}/cluster@1", status="active", successors=[], parent=parent["id"],
                       promoted_attrs={axis: norm(value)}, updated_at=ts, changeset=cs["id"])
            clusters[nc.get("id")] = row
            new_clusters.append(row)
            for k, d in decisions.items():
                vals = [norm(v) for v in (d.get("attributes") or {}).get(axis, [])]
                if d.get("cluster_id") == parent["id"] and d["status"] == "included" and norm(value) in vals:
                    nd = dict(d, cluster_id=row["id"], cluster_version=row.get("version", 1), actor="lineage",
                              decided_at=ts, reason=f"promoted {axis}={value} from {parent['id']}: {ch['reason']}")
                    decisions[k] = nd
                    new_decisions.append(nd)
        else:
            errors.append(f"{where}: unknown kind (page_upsert|map|unmap|redirect|cluster_status|promote)")
    v_err, v_warn = validate_state(clusters, decisions, pages, mappings, cfg)
    errors += v_err
    if errors:
        die("change set rejected:\n  " + "\n  ".join(errors[:60]))
    if args.dry_run:
        emit({"changeset": cs["id"], "dry_run": True, "would_apply": len(cs.get("changes", [])),
              "by_kind": dict(Counter(ch.get("kind") for ch in cs.get("changes", []))),
              "pages": [before["pages"], len(pages)], "mappings": [before["mappings"], len(mappings)],
              "clusters_changed": len(new_clusters), "decisions_moved": len(new_decisions),
              "warnings": v_warn[:30] + coverage_warnings(p, pages), "warnings_total": len(v_warn)})
        return
    write_jsonl(p.pages, sorted(pages.values(), key=lambda r: r["url"]))
    write_jsonl(p.mappings, sorted(mappings, key=lambda r: (r["cluster_id"], r["role"], r["page"])))
    append_jsonl(p.clusters, new_clusters)
    append_jsonl(p.decisions, new_decisions)
    write_json(dest, dict(cs, applied_at=ts))
    emit({"changeset": cs["id"], "applied": len(cs.get("changes", [])), "warnings": v_warn[:30] + coverage_warnings(p, pages),
          "warnings_total": len(v_warn)})


def read_sitemap(src: str, depth: int = 0) -> list[tuple]:
    """(url, lastmod) from a sitemap (urlset or index, file or URL, optionally gzipped) or a plain URL list."""
    if re.match(r"https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "search-demand-mapper/1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    else:
        raw = Path(src).read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", "replace")
    if "<urlset" not in text and "<sitemapindex" not in text:
        return [(x.strip(), None) for x in text.splitlines() if x.strip() and not x.startswith("#")]
    entries = []
    for block in re.findall(r"<(?:url|sitemap)>(.*?)</(?:url|sitemap)>", text, re.S):
        loc = re.search(r"<loc>\s*([^<]+?)\s*</loc>", block)
        mod = re.search(r"<lastmod>\s*([^<]+?)\s*</lastmod>", block)
        if loc:
            entries.append((html.unescape(loc[1]), mod[1] if mod else None))
    if "<sitemapindex" not in text:
        return entries
    if depth >= 2:
        die(f"sitemap index nested too deep at {src}")
    urls = []
    for loc, _ in entries:
        urls += read_sitemap(loc, depth + 1)
    return urls


def cmd_sync_check(args):
    """Compare the live URL set with the registry and snapshot it for analyze/validate."""
    p = Paths(args.root)
    require(p)
    host = site_host(p)
    lastmod = {}
    for u, mod in read_sitemap(args.sitemap):
        lastmod.setdefault(registry_form(u, host), mod)
    live = list(lastmod)
    facts = {}
    if args.pages:
        rows = read_json(Path(args.pages))
        for r in rows.get("pages", rows) if isinstance(rows, dict) else rows:
            facts[registry_form(r["url"], host)] = {k: v for k, v in r.items() if k != "url"}
    snap = {"schema": f"{S}/site-urls@1", "source": args.sitemap, "captured_at": now(), "host": host,
            "urls": live, "lastmod": {u: m for u, m in lastmod.items() if m},
            "titles": {u: f["title"] for u, f in facts.items() if f.get("title")}}
    write_json(p.site_urls, snap)
    pages = load_pages(p)
    keys = {page_key(u, host): u for u in pages}
    live_keys = {page_key(u, host) for u in live}
    clusters = {cid: c for cid, c in load_clusters(p).items() if c["status"] in ("active", "hold")}
    drop = head_stems(p)
    cores = {cid: cluster_cores(c, drop) for cid, c in clusters.items()}
    owned = {m["cluster_id"]: m["page"] for m in load_mappings(p) if m["role"] == "primary"}
    unregistered = []
    for u in live:
        if page_key(u, host) in keys:
            continue
        toks = url_tokens(u) | {stem(t) for t in tokens((facts.get(u) or {}).get("title", ""))}
        hints = [{"cluster_id": cid, "label": c.get("label"), "primary_page": owned.get(cid)}
                 for cid, c in clusters.items() if names_cluster(cores[cid], toks)]
        hints.sort(key=lambda h: (h["primary_page"] is not None, -max(len(x) for x in cores[h["cluster_id"]])))
        unregistered.append(dict({"url": u, "lastmod": lastmod.get(u)}, **(facts.get(u) or {}), cluster_hints=hints[:8]))
    mismatch = [{"url": u, "status": pages[u].get("status"), "indexable": pages[u].get("indexable")}
                for k, u in keys.items() if k in live_keys and not (pages[u].get("status") == "published"
                                                                   and pages[u].get("indexable"))]
    absent = [u for k, u in keys.items() if k not in live_keys and pages[u].get("status") == "published"
              and pages[u].get("indexable")]
    unowned = sorted(cid for cid in clusters if cid not in owned)
    out = {"schema": f"{S}/sync-check@1", "generated_at": now(), "source": args.sitemap, "live_urls": len(live),
           "registered": len(pages), "unregistered": unregistered, "live_but_not_published_indexable": mismatch,
           "published_but_not_live": absent, "clusters_without_primary": unowned,
           "note": "cluster_hints are lexical (URL/title contains every stem of the entity or label); the model decides ownership"}
    write_json(p.work / "sync-check.json", out)
    emit({"sync_check": str(p.work / "sync-check.json"), "snapshot": str(p.site_urls), "live_urls": len(live),
          "registered": len(pages), "unregistered": len(unregistered),
          "unregistered_with_hints": sum(1 for x in unregistered if x["cluster_hints"]),
          "live_but_not_published_indexable": len(mismatch), "published_but_not_live": len(absent),
          "clusters_without_primary": len(unowned)})


def cmd_validate(args):
    p = Paths(args.root)
    require(p)
    pages = load_pages(p)
    errors, warnings = validate_state(load_clusters(p), load_decisions(p), pages, load_mappings(p), cfg_of(p))
    warnings += coverage_warnings(p, pages)
    emit({"ok": not errors, "errors": errors, "warnings": warnings})
    if errors:
        sys.exit(1)


def cmd_sitemap(args):
    p = Paths(args.root)
    require(p)
    urls = sorted(u for u, pg in load_pages(p).items()
                  if pg.get("status") == "published" and pg.get("indexable") and pg.get("canonical", u) == u)
    if args.json:
        emit(urls)
    else:
        print("\n".join(urls))


def cmd_status(args):
    p = Paths(args.root)
    require(p)
    clusters = load_clusters(p)
    decisions = load_decisions(p)
    pages = load_pages(p)
    mappings = load_mappings(p)
    pool = load_pool(p) if p.obs.exists() else {}
    emit({
        "keywords_in_pool": len(pool),
        "decisions": dict(Counter(d["status"] for d in decisions.values())),
        "decisions_by_actor": dict(Counter(d["actor"] for d in decisions.values())),
        "undecided": sum(1 for k in pool if k not in decisions),
        "clusters": dict(Counter(c["status"] for c in clusters.values())),
        "pages": dict(Counter(pg.get("status") for pg in pages.values())),
        "mappings": dict(Counter(f"{m['role']}:{m['decision']}" for m in mappings)),
        "gsc_windows": sorted(w.stem for w in p.gsc.glob("*.jsonl")),
        "serp_captures": len(read_jsonl(p.serp)),
    })


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description="search-demand mapper")
    ap.add_argument("--root", default=".", help="project root that holds seo/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    a = sub.add_parser("prepare-review", help="queue new/changed keywords for a model review batch")
    a.add_argument("--limit", type=int)
    a.add_argument("--pending", action="store_true", help="also re-queue pending decisions")
    a.add_argument("--id", action="append", help="explicit keyword ids (overrides queue rules)")
    a.add_argument("--no-groups", action="store_true", help="list every keyword on its own")
    a.add_argument("--only", choices=["boundary", "variants", "facet", "single"], help="only this kind of unit")
    a.add_argument("--plan", action="store_true", help="size the whole queue (units, keywords, batches); write nothing")
    a.set_defaults(fn=cmd_prepare_review)
    a = sub.add_parser("apply-review", help="validate and apply a review output")
    a.add_argument("--file", required=True)
    a.add_argument("--actor", choices=["model", "human"], default="model")
    a.set_defaults(fn=cmd_apply_review)
    sub.add_parser("analyze", help="cluster evidence, gates and SERP needs").set_defaults(fn=cmd_analyze)
    a = sub.add_parser("serp", help="store SERP captures or compare result overlap")
    a.add_argument("action", choices=["add", "compare"])
    a.add_argument("--file")
    a.add_argument("--pairs")
    a.set_defaults(fn=cmd_serp)
    a = sub.add_parser("gsc", help="import GSC windows or review them against the registry")
    a.add_argument("action", choices=["import", "review"])
    a.add_argument("--file")
    a.add_argument("--period")
    a.add_argument("--page")
    a.set_defaults(fn=cmd_gsc)
    a = sub.add_parser("apply-changes", help="apply a user-approved change set to the registry")
    a.add_argument("--file", required=True)
    a.add_argument("--dry-run", action="store_true", help="run every check and report the result; write nothing")
    a.set_defaults(fn=cmd_apply_changes)
    a = sub.add_parser("sync-check", help="compare live URLs (sitemap) with the registry and snapshot them")
    a.add_argument("--sitemap", required=True, help="sitemap file or URL (urlset, index, .gz) or a plain URL list")
    a.add_argument("--pages", help="optional JSON list of {url, title, ...} page facts for hints and review")
    a.set_defaults(fn=cmd_sync_check)
    sub.add_parser("validate", help="check registry invariants").set_defaults(fn=cmd_validate)
    a = sub.add_parser("sitemap", help="list published, indexable, self-canonical URLs")
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_sitemap)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = ap.parse_args(argv)
    if args.cmd == "serp" and args.action == "add" and not args.file:
        die("serp add needs --file")
    if args.cmd == "gsc" and args.action == "import" and not (args.file and args.period):
        die("gsc import needs --file and --period")
    args.fn(args)


if __name__ == "__main__":
    main()
