#!/usr/bin/env python3
"""Convert the JSON that chatgpt_probe_runner.js (part B) downloads into gap/raw files.

  python3 probe_run_to_raw.py chatgpt-probe-run.json --out <project>/geo/gap/raw [--date 2026-11-18]

Input: {"turns": [{id, turn, q, answer}], "per": {id: {search_queries, stream_urls}}, "meta": {id: {...}}}.
Output: one <id>--chatgpt-instant--1.md per conversation, so answers never pass through the model.
An existing file is never overwritten. Prints one status line per conversation.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

SLICE = "chatgpt-instant"


def render(cid, turns, per, meta, date):
    errs = []
    answered = [t for t in turns if t.get("answer")]
    if len(answered) != len(turns):
        errs.append(f"{len(turns) - len(answered)} empty answers")
    if meta.get("err"):
        errs.append(str(meta["err"]))
    if meta and meta.get("unpers") not in (None, "Unpersonalized"):
        errs.append(f"mode {meta['unpers']}")
    status = "ok" if not errs else "check: " + "; ".join(errs)
    L = ["platform: ChatGPT via browser script", f"slice: {SLICE}", f"conversation: {cid}",
         f"date: {date}", f"model: {meta.get('model') or 'not displayed'}",
         f"mode: temporary chat, {meta.get('unpers') or 'mode not read'}", f"STATUS: {status}", ""]
    for t in turns:
        L += [f"=== TURN {t['turn']} USER ===", t.get("q", ""), "",
              f"=== TURN {t['turn']} ASSISTANT ===", t.get("answer") or "", ""]
    sq = per.get("search_queries")
    L += ["=== SEARCH QUERIES ===", json.dumps(sq if sq is not None else None, ensure_ascii=False), "",
          "=== STREAM URLS ==="] + list(per.get("stream_urls") or []) + [""]
    return "\n".join(L), status, sum(len(t.get("answer") or "") for t in turns)


def convert(data, out, date):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    by = defaultdict(list)
    for t in data.get("turns", []):
        by[t["id"]].append(t)
    lines = []
    for cid, turns in by.items():
        turns.sort(key=lambda t: t["turn"])
        path = out / f"{cid}--{SLICE}--1.md"
        if path.exists():
            lines.append(f"{cid}: skipped, {path.name} exists")
            continue
        text, status, chars = render(cid, turns, (data.get("per") or {}).get(cid, {}),
                                     (data.get("meta") or {}).get(cid, {}), date)
        path.write_text(text)
        sq = ((data.get("per") or {}).get(cid) or {}).get("search_queries") or []
        lines.append(f"{cid}: {len(turns)} turns, {chars} chars, {len(sq)} queries, {status}")
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("json_file")
    p.add_argument("--out", required=True, help="gap/raw folder")
    p.add_argument("--date", default=None, help="run date (default: today)")
    a = p.parse_args(argv)
    from datetime import date
    data = json.loads(Path(a.json_file).read_text())
    for line in convert(data, a.out, a.date or date.today().isoformat()):
        print(line)


if __name__ == "__main__":
    sys.exit(main())
