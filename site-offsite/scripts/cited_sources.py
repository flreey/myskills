#!/usr/bin/env python3
"""Which outside sources do AI assistants cite for a project's tasks? Targets for GEO off-site work.

    python3 cited_sources.py --root <project> --own <domain> [--own <domain>]... [--format json|md]

Reads the AI runs a GEO project already recorded: geo/gap/runs.jsonl (site-idea gap check) and
geo/optimize/runs.jsonl (site-geo optimize), each row with combo_id or cluster, platform, date, gap,
cited [{url, type}] and recommended [names]. Groups the cited URLs by domain and reports, per domain:
how many runs and tasks cite it, its source types, the platforms, whether the project's own domains
were cited in the same answers, and how many of those answers had a high-opportunity gap. Domains
cited where the project is absent come first: they are where the assistants already look.
Read-only; Python stdlib only.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

HIGH = {"generic", "outdated", "unmet_constraint", "no_resource"}
FILES = ("geo/gap/runs.jsonl", "geo/optimize/runs.jsonl")


def domain(url):
    host = urlparse(url if "//" in url else "https://" + url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def read_runs(root):
    rows = []
    for rel in FILES:
        p = root / rel
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if line.strip():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError as e:
                    sys.exit(f"{p}:{i}: {e}")
                r["_file"] = rel
                rows.append(r)
    return rows


def aggregate(rows, own):
    own = {d.lower().removeprefix("www.") for d in own}
    agg = defaultdict(lambda: {"runs": 0, "tasks": set(), "types": set(), "platforms": set(),
                               "with_own": 0, "high_gap": 0, "examples": []})
    for r in rows:
        cited = r.get("cited") or []
        doms = {domain(c.get("url", "")) for c in cited if c.get("url")}
        own_cited = bool(doms & own)
        task = r.get("combo_id") or r.get("cluster") or "?"
        for c in cited:
            d = domain(c.get("url", ""))
            if not d or d in own:
                continue
            a = agg[d]
            a["runs"] += 1
            a["tasks"].add(task)
            if c.get("type"):
                a["types"].add(c["type"])
            a["platforms"].add(r.get("platform", "?"))
            a["with_own"] += own_cited
            a["high_gap"] += r.get("gap") in HIGH
            if len(a["examples"]) < 3 and c["url"] not in a["examples"]:
                a["examples"].append(c["url"])
    out = []
    for d, a in agg.items():
        out.append({"domain": d, "runs": a["runs"], "tasks": len(a["tasks"]), "types": sorted(a["types"]),
                    "platforms": sorted(a["platforms"]), "own_also_cited": a["with_own"],
                    "high_gap_runs": a["high_gap"], "examples": a["examples"]})
    # Where the assistants look but the project is absent first, then by reach.
    out.sort(key=lambda x: (x["own_also_cited"] > 0, -x["tasks"], -x["runs"], x["domain"]))
    return out


def to_md(out, n_runs):
    lines = [f"{n_runs} recorded AI runs. Domains cited, project-absent first.", "",
             "| Domain | Tasks | Runs | Types | Own site also cited | High-gap runs | Example |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for x in out:
        lines.append(f"| {x['domain']} | {x['tasks']} | {x['runs']} | {', '.join(x['types']) or '?'} | "
                     f"{x['own_also_cited']} | {x['high_gap_runs']} | {x['examples'][0] if x['examples'] else ''} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    p.add_argument("--own", action="append", default=[], help="the project's own domain(s)")
    p.add_argument("--format", choices=["json", "md"], default="md")
    a = p.parse_args(argv)
    rows = read_runs(Path(a.root).resolve())
    if not rows:
        sys.exit("no recorded runs in geo/gap/runs.jsonl or geo/optimize/runs.jsonl")
    out = aggregate(rows, a.own)
    if a.format == "json":
        print(json.dumps({"runs": len(rows), "domains": out}, ensure_ascii=False, indent=2))
    else:
        print(to_md(out, len(rows)), end="")


if __name__ == "__main__":
    main()
