#!/usr/bin/env python3
"""Continuous GEO optimisation for a live site: question sets, rates with intervals, experiments.

    python3 geo_optimize.py --root <project> <command> [options]

Commands
  init                          create geo/optimize/ with empty files
  check                         validate clusters, conversations, constraints, runs, experiments
  sets [--holdout 0.3] [--sentinel 0.15] [--seed 1] [--force]
                                assign every cluster to optimize / holdout / sentinel (stable once set)
  report [--since DATE] [--until DATE] [--format md|json]
                                rates per set and per cluster with 95% Wilson intervals
  experiment --id ID            treatment vs control, before vs after: difference in differences,
                                with the sentinel set's drift over the same dates
  reads --own DOMAIN [--force]  fill own_read (our pages the assistant opened) and read (other pages) in
                                runs.jsonl from each raw file's stream URLs (same rules as site-idea reads)
  brief --page PATH [--force]   page brief skeleton for one page: the clusters it owns, their
                                conversation turns routed to sections, the constraints it must state

Data (contract in references/optimize.md): geo/optimize/clusters.jsonl, conversations.jsonl,
constraints.jsonl, runs.jsonl, experiments.jsonl. The model writes clusters, conversations,
constraints, runs and experiments; this script assigns sets and counts. It never calls an AI service
or the web. Python stdlib only.
"""
import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

QUERY_TYPES = {"recommend", "problem", "constraint", "compare", "howto", "integrate"}
LEVERS = {"offsite", "onsite", "docs", "tools"}
PAGE_STATUS = {"COVERED", "OPTIMIZE", "NEW_PAGE", "MERGE", "NOT_FIT"}
EVIDENCE = {"hypothesis", "signal", "validated"}
STATUS = ["absent", "mentioned", "listed", "first", "excluded"]
ROLES = {"tool", "evidence", "step", "called", None}
CONSTRAINT = {"met", "conditional", "unmet", "unknown"}
SETS = ("optimize", "holdout", "sentinel")
# Where a turn is answered on the page (same table as site-batch references/question-mapping.md).
SECTION_BY_KIND = {"constraint": "conditions", "howto": "faq_or_resource", "why": "faq",
                   "compare": "alternatives", "resource": "resource", "pick": "conditions", "other": "review"}
RANK = {"first": 3, "listed": 2, "mentioned": 1, "excluded": 0, "absent": 0}
ASSET_HOSTS = ("images.openai.com", "oaiusercontent.com", "cdn.openai.com")
ASSET_PATH = re.compile(r"\.(jpe?g|png|gif|webp|avif|svg|ico|mp4|webm|css|js)$", re.I)
MIN_N = 30


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


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
        self.dir = Path(root).resolve() / "geo" / "optimize"
        self.clusters = self.dir / "clusters.jsonl"
        self.conversations = self.dir / "conversations.jsonl"
        self.constraints = self.dir / "constraints.jsonl"
        self.runs = self.dir / "runs.jsonl"
        self.experiments = self.dir / "experiments.jsonl"
        self.briefs = self.dir / "briefs"


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def rates(runs):
    n = len(runs)
    inans = sum(1 for r in runs if r.get("status") in ("listed", "first"))
    first = sum(1 for r in runs if r.get("status") == "first")
    cited = sum(1 for r in runs if r.get("cited_own"))
    acc_c = sum(int((r.get("accuracy") or {}).get("correct", 0)) for r in runs)
    acc_t = acc_c + sum(int((r.get("accuracy") or {}).get(k, 0)) for r in runs for k in ("wrong", "stale"))
    excl = [r for r in runs if r.get("status") == "excluded"]
    # Absent although it opened one of our pages: lost the choice, not the search (fix the pages it read).
    opened = sum(1 for r in runs if r.get("status") == "absent" and r.get("own_read"))
    dropped = sum(1 for r in runs if dropped_after_follow_up(r))
    wrong_excl = sum(1 for r in excl if (r.get("exclusion") or {}).get("true_reason") is False)
    return {
        "n": n,
        "in_answer": round(inans / n, 3) if n else None, "in_answer_ci": wilson(inans, n),
        "first": round(first / n, 3) if n else None, "first_ci": wilson(first, n),
        "cited": round(cited / n, 3) if n else None, "cited_ci": wilson(cited, n),
        "accuracy": round(acc_c / acc_t, 3) if acc_t else None, "facts_checked": acc_t,
        "wrong_exclusions": wrong_excl, "exclusions": len(excl),
        "opened_not_named": opened, "dropped_after_follow_up": dropped,
        "reads_captured": sum(1 for r in runs if isinstance(r.get("own_read"), list)),
        "thin": n < MIN_N,
    }


def dropped_after_follow_up(r):
    a, b = r.get("status_opening"), r.get("status")
    return a in ("first", "listed") and b in RANK and RANK[b] < RANK[a]


def norm_url(u):
    p = urlsplit(str(u).strip().rstrip(".,;)\"'"))
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(q), ""))


def url_host(u):
    return urlsplit(u if "://" in str(u) else "https://" + str(u)).netloc.lower().removeprefix("www.")


def host_in(u, hosts):
    h = url_host(u)
    return any(h == o or h.endswith("." + o) for o in hosts)


def stream_urls(path):
    lines = Path(path).read_text().splitlines()
    if "=== STREAM URLS ===" not in lines:
        return None
    out = []
    for line in lines[lines.index("=== STREAM URLS ===") + 1:]:
        if line.startswith("=== "):
            break
        for u in re.findall(r"https?://\S+", line):
            n = norm_url(u)
            if n not in out and not host_in(n, ASSET_HOSTS) and not ASSET_PATH.search(urlsplit(n).path):
                out.append(n)
    return out


def cmd_reads(st, a):
    hosts = {url_host(d) for d in a.own}
    rows = read_jsonl(st.runs)
    out = {"own": sorted(hosts), "filled": 0, "kept": 0, "no_stream": 0, "no_raw": 0, "opened_not_named": 0}
    for r in rows:
        raw = st.dir.parent.parent / r["raw"] if r.get("raw") else None
        if isinstance(r.get("own_read"), list) and not a.force:
            out["kept"] += 1
        elif not raw or not raw.exists():
            out["no_raw"] += 1
        else:
            urls = stream_urls(raw)
            if urls is None:
                out["no_stream"] += 1
            else:
                r["own_read"] = [u for u in urls if host_in(u, hosts)]
                r["read"] = [u for u in urls if not host_in(u, hosts)]
                out["filled"] += 1
        out["opened_not_named"] += r.get("status") == "absent" and bool(r.get("own_read"))
    if out["filled"]:
        write_jsonl(st.runs, rows)
    print(json.dumps(out, ensure_ascii=False, indent=2))


def in_window(r, since, until):
    d = r.get("date", "")
    return (not since or d >= since) and (not until or d < until)


def load(st):
    clusters = {c["id"]: c for c in read_jsonl(st.clusters) if c.get("id")}
    convs = {c["id"]: c for c in read_jsonl(st.conversations) if c.get("id")}
    return clusters, convs, read_jsonl(st.runs), read_jsonl(st.experiments), read_jsonl(st.constraints)


def run_cluster(r, convs):
    return r.get("cluster") or (convs.get(r.get("conversation_id")) or {}).get("cluster")


# ---------- commands ----------

def cmd_init(st, a):
    st.dir.mkdir(parents=True, exist_ok=True)
    for p in (st.clusters, st.conversations, st.constraints, st.runs, st.experiments):
        if not p.exists():
            p.write_text("")
    print(json.dumps({"created": str(st.dir)}))


def cmd_check(st, a):
    clusters, convs, runs, exps, cons = load(st)
    errs = []
    for c in clusters.values():
        w = f"clusters {c['id']}"
        if not c.get("task"):
            errs.append(f"{w}: task is required")
        if c.get("query_type") not in QUERY_TYPES:
            errs.append(f"{w}: query_type must be one of {sorted(QUERY_TYPES)}")
        if c.get("lever") not in LEVERS:
            errs.append(f"{w}: lever must be one of {sorted(LEVERS)}")
        if c.get("evidence_level") not in EVIDENCE:
            errs.append(f"{w}: evidence_level must be one of {sorted(EVIDENCE)}")
        if c.get("page_status") and c["page_status"] not in PAGE_STATUS:
            errs.append(f"{w}: page_status must be one of {sorted(PAGE_STATUS)}")
        if c.get("set") and c["set"] not in SETS:
            errs.append(f"{w}: set must be one of {SETS}")
        if c.get("evidence_level") != "hypothesis" and not c.get("sources"):
            errs.append(f"{w}: {c.get('evidence_level')} needs sources (where people ask this)")
    for v in convs.values():
        if v.get("cluster") not in clusters:
            errs.append(f"conversations {v['id']}: unknown cluster {v.get('cluster')!r}")
        if not v.get("opening"):
            errs.append(f"conversations {v['id']}: opening is required")
    for c in cons:
        if c.get("status") not in CONSTRAINT:
            errs.append(f"constraints {c.get('id')}: status must be one of {sorted(CONSTRAINT)}")
        if c.get("status") in ("met", "conditional", "unmet") and not c.get("source"):
            errs.append(f"constraints {c.get('id')}: {c['status']} needs a source")
    for i, r in enumerate(runs, 1):
        w = f"runs:{i}"
        if r.get("conversation_id") not in convs:
            errs.append(f"{w}: unknown conversation_id {r.get('conversation_id')!r}")
        for k in ("platform", "mode", "date"):
            if not r.get(k):
                errs.append(f"{w}: {k} is required")
        if r.get("status") not in STATUS:
            errs.append(f"{w}: status must be one of {STATUS}")
        if r.get("status_opening") is not None and r.get("status_opening") not in STATUS:
            errs.append(f"{w}: status_opening must be one of {STATUS} or null")
        for k in ("own_read", "read"):
            v = r.get(k)
            if v is not None and not (isinstance(v, list) and all(isinstance(u, str) for u in v)):
                errs.append(f"{w}: {k} is a list of URLs, or null when not captured")
        if r.get("role", None) not in ROLES:
            errs.append(f"{w}: role must be tool, evidence, step, called or null")
        if r.get("status") == "excluded" and not (r.get("exclusion") or {}).get("reason"):
            errs.append(f"{w}: excluded needs exclusion.reason (the assistant's words)")
    for e in exps:
        w = f"experiments {e.get('id')}"
        for k in ("id", "change", "shipped", "treatment", "control"):
            if not e.get(k):
                errs.append(f"{w}: {k} is required")
        for side in ("treatment", "control"):
            for cid in e.get(side, []):
                if cid not in clusters:
                    errs.append(f"{w}: {side} names unknown cluster {cid!r}")
                elif clusters[cid].get("set") == "holdout":
                    errs.append(f"{w}: holdout cluster {cid} cannot be changed or used as control")
        if set(e.get("treatment", [])) & set(e.get("control", [])):
            errs.append(f"{w}: a cluster is both treatment and control")
    for e in errs:
        print(f"ERROR  {e}")
    print(json.dumps({"errors": len(errs), "clusters": len(clusters), "conversations": len(convs), "runs": len(runs)}))
    sys.exit(1 if errs else 0)


def cmd_sets(st, a):
    rows = read_jsonl(st.clusters)
    if not rows:
        die("no clusters")
    have = [c for c in rows if c.get("set")]
    if have and not a.force:
        new = [c for c in rows if not c.get("set")]
    else:
        new = rows
    for c in new:
        h = int(hashlib.sha256(f"{a.seed}:{c['id']}".encode()).hexdigest(), 16) / 2 ** 256
        if c.get("evidence_level") == "hypothesis":
            c["set"] = "optimize"  # unvalidated tasks never measure results
        elif h < a.holdout:
            c["set"] = "holdout"
        elif h < a.holdout + a.sentinel:
            c["set"] = "sentinel"
        else:
            c["set"] = "optimize"
        c["set_date"] = date.today().isoformat()
    write_jsonl(st.clusters, rows)
    counts = defaultdict(int)
    for c in rows:
        counts[c["set"]] += 1
    print(json.dumps({"assigned": len(new), "sets": dict(counts)}, indent=2))


def cmd_report(st, a):
    clusters, convs, runs, exps, cons = load(st)
    runs = [r for r in runs if in_window(r, a.since, a.until) and r.get("status") in STATUS]
    by_set, by_cluster = defaultdict(list), defaultdict(list)
    for r in runs:
        cid = run_cluster(r, convs)
        if cid in clusters:
            by_set[clusters[cid].get("set", "unassigned")].append(r)
            by_cluster[cid].append(r)
    out = {"window": [a.since, a.until], "runs": len(runs),
           "sets": {s: rates(v) for s, v in sorted(by_set.items())},
           "clusters": []}
    for cid, c in sorted(clusters.items()):
        rr = rates(by_cluster.get(cid, []))
        excl = [r["exclusion"]["reason"] for r in by_cluster.get(cid, []) if r.get("status") == "excluded" and r.get("exclusion")]
        out["clusters"].append({"id": cid, "set": c.get("set"), "query_type": c.get("query_type"), "lever": c.get("lever"),
                                "page_status": c.get("page_status"), **rr, "exclusion_reasons": excl[:3]})
    unknown = [c["id"] for c in cons if c.get("status") == "unknown"]
    out["unknown_constraints"] = unknown
    if a.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    pct = lambda v: "—" if v is None else f"{v:.0%}"
    ci = lambda v: "" if not v else f" ({v[0]:.0%}–{v[1]:.0%})"
    L = [f"Runs: {len(runs)}. Window: {a.since or 'start'} → {a.until or 'now'}. Report the holdout set as the result; "
         "rates with n < 30 are marked thin. \"Opened, not named\": absent although it opened one of our pages "
         "(a selection loss: fix the pages it read). \"Dropped\": named in the opening, lower after a follow-up.", "",
         "| Set | n | In answer | First | Cited | Accuracy | Opened, not named | Dropped |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s, r in out["sets"].items():
        L.append(f"| {s}{' (thin)' if r['thin'] else ''} | {r['n']} | {pct(r['in_answer'])}{ci(r['in_answer_ci'])} | "
                 f"{pct(r['first'])} | {pct(r['cited'])}{ci(r['cited_ci'])} | {pct(r['accuracy'])} | "
                 f"{r['opened_not_named'] if r['reads_captured'] else 'not captured'} | {r['dropped_after_follow_up']} |")
    L += ["", "| Cluster | Set | Type | Lever | n | In answer | Cited | Wrong exclusions | Page |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in out["clusters"]:
        L.append(f"| {c['id']} | {c['set']} | {c['query_type']} | {c['lever']} | {c['n']} | {pct(c['in_answer'])} | "
                 f"{pct(c['cited'])} | {c['wrong_exclusions']}/{c['exclusions']} | {c['page_status'] or ''} |")
    if unknown:
        L += ["", f"Constraints still unknown: {', '.join(unknown)}"]
    print("\n".join(L))


def cmd_experiment(st, a):
    clusters, convs, runs, exps, cons = load(st)
    e = next((x for x in exps if x.get("id") == a.id), None)
    if not e:
        die(f"no experiment {a.id!r}")
    start = e.get("recrawled") or e["shipped"]
    sentinel = [cid for cid, c in clusters.items() if c.get("set") == "sentinel"]

    def group(ids):
        pre = [r for r in runs if run_cluster(r, convs) in ids and r.get("date", "") < e["shipped"]]
        post = [r for r in runs if run_cluster(r, convs) in ids and r.get("date", "") >= start]
        return rates(pre), rates(post)

    out = {"id": a.id, "change": e["change"], "shipped": e["shipped"], "measured_from": start}
    for name, ids in (("treatment", set(e["treatment"])), ("control", set(e["control"])), ("sentinel", set(sentinel))):
        pre, post = group(ids)
        out[name] = {"before": pre, "after": post}
    for metric in ("in_answer", "cited"):
        t, c = out["treatment"], out["control"]
        vals = [t["before"][metric], t["after"][metric], c["before"][metric], c["after"][metric]]
        if None in vals:
            out[f"did_{metric}"] = None
            continue
        did = (vals[1] - vals[0]) - (vals[3] - vals[2])
        var = 0.0
        for g, k in ((t, "before"), (t, "after"), (c, "before"), (c, "after")):
            p, n = g[k][metric], g[k]["n"]
            var += p * (1 - p) / n if n else 0
        h = 1.96 * math.sqrt(var)
        out[f"did_{metric}"] = {"estimate": round(did, 3), "ci": [round(did - h, 3), round(did + h, 3)]}
    s = out["sentinel"]
    drift = None
    if s["before"]["in_answer"] is not None and s["after"]["in_answer"] is not None:
        drift = round(s["after"]["in_answer"] - s["before"]["in_answer"], 3)
    out["sentinel_drift_in_answer"] = drift
    thin = any(out[g][k]["thin"] for g in ("treatment", "control") for k in ("before", "after"))
    d = out.get("did_in_answer")
    if thin:
        verdict = "insufficient: a group has fewer than 30 runs"
    elif drift is not None and abs(drift) >= 0.15:
        verdict = "no conclusion: the sentinel set moved as much as an effect would (platform or model change)"
    elif d and d["ci"][0] > 0:
        verdict = "improved: the interval is above zero"
    elif d and d["ci"][1] < 0:
        verdict = "worse: the interval is below zero"
    else:
        verdict = "no detectable effect at this sample size"
    out["verdict"] = verdict
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_brief(st, a):
    clusters, convs, runs, exps, cons = load(st)
    page = a.page.rstrip("/") or "/"
    own = [c for c in clusters.values() if (c.get("primary_page") or "").rstrip("/") == page]
    if not own:
        die(f"no cluster has primary_page {page!r}: set it in clusters.jsonl (O4) first")
    con_by_id = {c.get("id"): c for c in cons}
    brief = {"page": page, "date": date.today().isoformat(), "clusters": [], "answer_first": [],
             "conditions": [], "faq": [], "faq_or_resource": [], "alternatives": [], "resource": [], "review": [],
             "unknown_constraints": [], "not_this_page": []}
    seen = set()
    for c in own:
        brief["clusters"].append({"id": c["id"], "task": c.get("task"), "query_type": c.get("query_type"),
                                  "lever": c.get("lever"), "page_status": c.get("page_status"), "set": c.get("set")})
        for v in convs.values():
            if v.get("cluster") != c["id"]:
                continue
            brief["answer_first"].append({"cluster": c["id"], "opening": v.get("opening")})
            for f in v.get("follow_ups", []) or []:
                q, kind = (f.get("q"), f.get("kind", "other")) if isinstance(f, dict) else (f, "other")
                key = (q or "").strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                brief[SECTION_BY_KIND.get(kind, "review")].append({"cluster": c["id"], "q": q, "kind": kind})
        for cid in c.get("constraints", []) or []:
            k = con_by_id.get(cid)
            if not k:
                continue
            item = {"id": cid, "constraint": k.get("constraint"), "status": k.get("status"), "note": k.get("note", "")}
            if k.get("status") == "unknown":
                brief["unknown_constraints"].append(item)
            elif item not in brief["conditions"]:
                brief["conditions"].append(item)
        if c.get("lever") != "onsite":
            brief["not_this_page"].append({"cluster": c["id"], "lever": c.get("lever"),
                                           "note": "won mainly off the page; the page states facts, the work is elsewhere"})
    slug = page.strip("/").replace("/", "--") or "home"
    path = st.briefs / f"{slug}.json"
    if path.exists() and not a.force:
        die(f"{path} exists; edit it, or --force to rebuild the skeleton (edits are lost)")
    st.briefs.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"brief": str(path), "clusters": len(own),
                      "sections": {k: len(brief[k]) for k in ("answer_first", "conditions", "faq", "faq_or_resource",
                                                              "alternatives", "resource", "review", "unknown_constraints")}},
                     ensure_ascii=False, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("check")
    s = sub.add_parser("sets")
    s.add_argument("--holdout", type=float, default=0.3)
    s.add_argument("--sentinel", type=float, default=0.15)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("report")
    s.add_argument("--since")
    s.add_argument("--until")
    s.add_argument("--format", choices=["md", "json"], default="md")
    s = sub.add_parser("experiment")
    s.add_argument("--id", required=True)
    s = sub.add_parser("reads")
    s.add_argument("--own", action="append", required=True, metavar="DOMAIN", help="our domain (repeatable)")
    s.add_argument("--force", action="store_true", help="refill runs that already have own_read")
    s = sub.add_parser("brief")
    s.add_argument("--page", required=True)
    s.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    st = State(a.root)
    {"init": cmd_init, "check": cmd_check, "sets": cmd_sets, "report": cmd_report,
     "experiment": cmd_experiment, "brief": cmd_brief, "reads": cmd_reads}[a.cmd](st, a)


if __name__ == "__main__":
    main()
