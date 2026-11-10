#!/usr/bin/env python3
"""Read-only helpers for the branch-cleanup skill.

  inventory [--base BRANCH] [--json]   classify every branch / worktree against the base branch
  snapshot  --out FILE                 record every local commit tip (branches, worktree HEADs, stash)
  verify    --snapshot FILE            check every recorded tip is still reachable from the base or a tag

None of these commands change the repository. Run them from anywhere inside the repo.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REGENERABLE = {
    "node_modules", ".next", "out", "dist", "build", ".turbo", ".cache", "__pycache__",
    ".venv", "venv", "target", "coverage", ".DS_Store", ".pytest_cache", ".wrangler",
    ".mypy_cache", ".ruff_cache", ".parcel-cache", ".svelte-kit", ".nuxt", ".gradle",
}


def git(*args: str, cwd: str | None = None, check: bool = True) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout.rstrip("\n")


def git_rc(*args: str, cwd: str | None = None) -> tuple[int, str]:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout.rstrip("\n")


def is_ancestor(a: str, b: str) -> bool:
    return git_rc("merge-base", "--is-ancestor", a, b)[0] == 0


def ref_exists(ref: str) -> bool:
    return git_rc("rev-parse", "--verify", "--quiet", ref + "^{commit}")[0] == 0


def detect_base(explicit: str | None) -> str:
    if explicit:
        return explicit
    rc, out = git_rc("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if rc == 0 and out.startswith("origin/"):
        cand = out[len("origin/"):]
        if ref_exists("refs/heads/" + cand):
            return cand
    for cand in ("main", "master"):
        if ref_exists("refs/heads/" + cand):
            return cand
    sys.exit("cannot detect base branch; pass --base")


def worktrees() -> list[dict]:
    out = git("worktree", "list", "--porcelain")
    items, cur = [], {}
    for line in out.splitlines() + [""]:
        if not line:
            if cur:
                items.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur["path"] = val
        elif key == "HEAD":
            cur["head"] = val
        elif key == "branch":
            cur["branch"] = val.removeprefix("refs/heads/")
        elif key == "detached":
            cur["detached"] = True
        elif key == "bare":
            cur["bare"] = True
        elif key == "locked":
            cur["locked"] = val or "locked"
        elif key == "prunable":
            cur["prunable"] = val or "prunable"
    if items:
        items[0]["main_worktree"] = True
    return items


def cwd_processes() -> list[tuple[int, str, str]]:
    """(pid, command, cwd) of every process lsof can see."""
    try:
        res = subprocess.run(["lsof", "-n", "-d", "cwd", "-Fpcn"], capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    procs, pid, cmd = [], None, ""
    for line in res.stdout.splitlines():
        if line.startswith("p"):
            pid, cmd = int(line[1:]), ""
        elif line.startswith("c"):
            cmd = line[1:]
        elif line.startswith("n") and pid is not None:
            procs.append((pid, cmd, line[1:]))
    return procs


def full_command(pid: int) -> str:
    res = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
    return res.stdout.strip()


def under(path: str, root: str) -> bool:
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root.rstrip("/") + "/")


def only_symlinks(path: str, limit: int = 200) -> bool:
    """True for a directory whose entries are all symlinks (nothing real would be lost)."""
    if not os.path.isdir(path) or os.path.islink(path):
        return False
    seen = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for name in filenames + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]:
            seen += 1
            if seen > limit or not os.path.islink(os.path.join(dirpath, name)):
                return False
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
    return seen > 0


def worktree_details(wt: dict, procs: list[tuple[int, str, str]], others: list[str]) -> dict:
    path = wt["path"]
    d: dict = {}
    if not os.path.isdir(path):
        d["missing"] = True
        return d
    st = git("status", "--porcelain=v1", "--ignored=traditional", "--untracked-files=normal", cwd=path, check=False)
    staged = unstaged = untracked = 0
    ignored = []
    for line in st.splitlines():
        xy, name = line[:2], line[3:]
        if xy == "??":
            untracked += 1
        elif xy == "!!":
            ignored.append(name)
        else:
            if xy[0] not in " ?":
                staged += 1
            if xy[1] not in " ?":
                unstaged += 1
    d.update(staged=staged, unstaged=unstaged, untracked=untracked)
    d["dirty"] = bool(staged or unstaged or untracked)
    if wt.get("main_worktree"):
        return d  # never removed by this skill; only its cleanliness matters
    # ignored files that `git worktree remove` would delete and that are not obvious caches
    keep = []
    for name in ignored:
        base = name.rstrip("/").split("/")[-1]
        full = os.path.join(path, name.rstrip("/"))
        if base in REGENERABLE or base.endswith(".pyc") or os.path.islink(full) or only_symlinks(full):
            continue
        keep.append(name)
    d["ignored_notable"] = keep
    # symlinks (never follow them when deleting or installing)
    links = []
    res = subprocess.run(
        ["find", path, "-maxdepth", "4", "-type", "l", "-not", "-path", "*/node_modules/*", "-not", "-path", "*/.git/*",
         "-not", "-path", "*/.venv*/*", "-not", "-path", "*/venv/*"],
        capture_output=True, text=True,
    )
    for p in res.stdout.splitlines():
        target = os.readlink(p)
        resolved = os.path.realpath(p)
        links.append({"link": os.path.relpath(p, path), "target": target, "outside": not under(resolved, path)})
    d["symlinks"] = links
    # processes whose cwd is inside this worktree but not inside a nested worktree
    nested = [o for o in others if o != path and under(o, path)]
    users = []
    for pid, cmd, cwd in procs:
        if under(cwd, path) and not any(under(cwd, n) for n in nested):
            users.append({"pid": pid, "cmd": cmd, "cwd": cwd, "command": full_command(pid)[:160]})
    d["processes"] = users
    d["claude_like"] = "/.claude/worktrees/" in path or any("claude" in u["command"].lower() for u in users)
    d["is_cwd"] = under(os.getcwd(), path) and not any(under(os.getcwd(), n) for n in nested)
    gitdir = git("rev-parse", "--absolute-git-dir", cwd=path, check=False)
    newest = 0.0
    for f in ("index", "logs/HEAD", "HEAD"):
        fp = os.path.join(gitdir, f)
        if os.path.exists(fp):
            newest = max(newest, os.path.getmtime(fp))
    d["last_git_activity"] = int(newest) if newest else None
    return d


def classify(base: str, ref: str) -> dict:
    behind, ahead = (int(x) for x in git("rev-list", "--left-right", "--count", f"{base}...{ref}").split())
    info = {"ahead": ahead, "behind": behind}
    if ahead == 0:
        info["state"] = "merged"
        return info
    files = git("diff", "--name-only", f"{base}...{ref}").splitlines()
    info["files_changed"] = len(files)
    if behind == 0:
        info["state"] = "ff"
        return info
    rc, out = git_rc("merge-tree", "--write-tree", "--name-only", base, ref)
    lines = out.splitlines()
    tree = lines[0] if lines else ""
    if rc == 0:
        base_tree = git("rev-parse", f"{base}^{{tree}}")
        info["state"] = "equivalent" if tree == base_tree else "clean"
    elif rc == 1:
        conflicted = []
        for ln in lines[1:]:
            if not ln.strip():
                break
            conflicted.append(ln)
        info["state"] = "conflict"
        info["conflicts"] = conflicted
    else:
        info["state"] = "unknown"
    return info


SUGGEST = {
    "merged": "delete (-d)",
    "ff": "ff-merge if finished, else archive",
    "clean": "merge if finished, else archive",
    "equivalent": "archive tag + delete (content already in base)",
    "conflict": "archive tag + delete",
    "unknown": "inspect",
}


def inventory(args) -> None:
    base = detect_base(args.base)
    wts = worktrees()
    procs = cwd_processes()
    paths = [w["path"] for w in wts]
    by_branch = {w.get("branch"): w for w in wts if w.get("branch")}
    report: dict = {"repo": git("rev-parse", "--show-toplevel"), "base": base}

    base_sha = git("rev-parse", base)
    report["base_sha"] = base_sha
    base_wt = by_branch.get(base)
    report["base_worktree"] = base_wt["path"] if base_wt else None
    up = f"origin/{base}"
    if ref_exists(up):
        behind, ahead = (int(x) for x in git("rev-list", "--left-right", "--count", f"{up}...{base}").split())
        report["base_vs_origin"] = {"ahead": ahead, "behind": behind}
    else:
        report["base_vs_origin"] = None

    wt_rows = []
    for w in wts:
        row = dict(w)
        row.update(worktree_details(w, procs, paths))
        if w.get("detached") and w.get("head"):
            row["detached_state"] = classify(base, w["head"])
        wt_rows.append(row)
    report["worktrees"] = wt_rows

    branches = []
    fmt = "%(refname:short)\t%(objectname)\t%(committerdate:short)\t%(subject)"
    for line in git("for-each-ref", "--format", fmt, "refs/heads").splitlines():
        name, sha, date, subject = (line.split("\t", 3) + [""])[:4]
        if name == base:
            continue
        row = {"branch": name, "sha": sha, "date": date, "subject": subject}
        row.update(classify(base, name))
        if name in by_branch:
            row["worktree"] = by_branch[name]["path"]
        row["suggest"] = SUGGEST[row["state"]]
        branches.append(row)
    report["branches"] = branches

    remotes = []
    for line in git("for-each-ref", "--format", "%(refname:short)\t%(objectname)\t%(symref)", "refs/remotes").splitlines():
        name, sha, symref = (line.split("\t") + ["", ""])[:3]
        if symref or name == f"origin/{base}" or "/" not in name:
            continue
        local = name.split("/", 1)[1]
        r = {"remote_branch": name, "sha": sha, "has_local": ref_exists("refs/heads/" + local)}
        r.update(classify(base, name))
        remotes.append(r)
    report["remote_branches"] = remotes
    report["stash_count"] = len(git("stash", "list", check=False).splitlines())
    report["archive_tags"] = git("tag", "-l", "archive/*").splitlines()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    print_report(report)


def print_report(r: dict) -> None:
    print(f"repo: {r['repo']}")
    print(f"base: {r['base']} @ {r['base_sha'][:10]}  worktree: {r['base_worktree'] or '(not checked out)'}")
    bo = r["base_vs_origin"]
    if bo is None:
        print(f"base vs origin: no origin/{r['base']}")
    else:
        print(f"base vs origin: ahead {bo['ahead']}, behind {bo['behind']}")
    print(f"stash entries: {r['stash_count']}   existing archive tags: {len(r['archive_tags'])}")
    print("\n== local branches ==")
    if not r["branches"]:
        print("(none besides base)")
    for b in r["branches"]:
        extra = f" files={b['files_changed']}" if "files_changed" in b else ""
        if b.get("conflicts"):
            extra += f" conflicts={','.join(b['conflicts'][:5])}"
        wt = f" [worktree {b['worktree']}]" if b.get("worktree") else ""
        print(f"- {b['branch']}: {b['state']} (+{b['ahead']}/-{b['behind']}{extra}) {b['date']} {b['sha'][:8]} "
              f"\"{b['subject'][:60]}\"{wt}\n    suggest: {b['suggest']}")
    print("\n== worktrees ==")
    for w in r["worktrees"]:
        tag = "main worktree" if w.get("main_worktree") else (w.get("branch") or "DETACHED")
        print(f"- {w['path']} ({tag})")
        if w.get("missing"):
            print("    directory missing -> `git worktree prune`")
            continue
        flags = []
        if w.get("dirty"):
            flags.append(f"DIRTY staged={w['staged']} unstaged={w['unstaged']} untracked={w['untracked']}")
        if w.get("locked"):
            flags.append(f"LOCKED ({w['locked']})")
        if w.get("prunable"):
            flags.append(f"PRUNABLE ({w['prunable']})")
        if w.get("is_cwd"):
            flags.append("CURRENT SHELL IS HERE")
        if w.get("claude_like"):
            flags.append("looks like an agent session worktree")
        if w.get("detached_state"):
            ds = w["detached_state"]
            flags.append(f"detached HEAD {w['head'][:8]} is {ds['state']} (+{ds['ahead']})")
        if flags:
            print("    " + "; ".join(flags))
        for p in w.get("processes", []):
            print(f"    process pid={p['pid']} {p['command'] or p['cmd']} (cwd {p['cwd']})")
        for s in w.get("symlinks", []):
            print(f"    symlink {s['link']} -> {s['target']}{'  (points OUTSIDE worktree)' if s['outside'] else ''}")
        if w.get("ignored_notable"):
            print("    ignored files deleted with worktree: " + ", ".join(w["ignored_notable"][:12]))
        if w.get("last_git_activity"):
            import time
            age_h = (time.time() - w["last_git_activity"]) / 3600
            print(f"    last git activity {age_h:.1f} h ago")
    print("\n== remote branches (report only) ==")
    if not r["remote_branches"]:
        print("(none besides base)")
    for b in r["remote_branches"]:
        print(f"- {b['remote_branch']}: {b['state']} (+{b['ahead']}/-{b['behind']}) local={'yes' if b['has_local'] else 'no'}")


def tips() -> dict:
    """Every commit a cleanup must not lose: local branches, worktree HEADs, stash entries."""
    out: dict = {}
    for line in git("for-each-ref", "--format", "%(refname)\t%(objectname)", "refs/heads").splitlines():
        ref, sha = line.split("\t")
        out[ref] = sha
    for w in worktrees():
        if w.get("head"):
            out[f"worktree:{w['path']}"] = w["head"]
    for i, sha in enumerate(git("log", "-g", "--format=%H", "refs/stash", check=False).splitlines()):
        out[f"stash@{{{i}}}"] = sha
    return out


def snapshot(args) -> None:
    data = {"base": detect_base(args.base), "tips": tips()}
    data["base_sha"] = git("rev-parse", data["base"])
    Path(args.out).write_text(json.dumps(data, indent=2))
    print(f"recorded {len(data['tips'])} tips to {args.out} (base {data['base']} @ {data['base_sha'][:10]})")


def verify(args) -> None:
    data = json.loads(Path(args.snapshot).read_text())
    base = args.base or data["base"]
    keepers = [f"refs/heads/{base}"] + git("for-each-ref", "--format", "%(refname)", "refs/tags").splitlines()
    keepers += git("for-each-ref", "--format", "%(refname)", "refs/heads").splitlines()
    keepers = list(dict.fromkeys(keepers))
    stash_now = set(git("log", "-g", "--format=%H", "refs/stash", check=False).splitlines())
    lost = []
    for name, sha in data["tips"].items():
        if git_rc("cat-file", "-e", sha + "^{commit}")[0] != 0:
            lost.append((name, sha, "object missing"))
            continue
        if name.startswith("stash@"):
            if sha not in stash_now:
                lost.append((name, sha, "no longer in the stash list"))
            continue
        holders = git("for-each-ref", "--contains", sha, "--format", "%(refname)", *keepers, check=False).splitlines()
        if not holders:
            lost.append((name, sha, "not reachable from base, any branch or any tag"))
    if lost:
        for name, sha, why in lost:
            print(f"LOST {name} {sha[:10]}: {why}")
        sys.exit(1)
    print(f"ok: all {len(data['tips'])} recorded tips are reachable from {base}, a remaining branch or a tag")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("--base")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=inventory)
    p = sub.add_parser("snapshot")
    p.add_argument("--base")
    p.add_argument("--out", required=True)
    p.set_defaults(func=snapshot)
    p = sub.add_parser("verify")
    p.add_argument("--base")
    p.add_argument("--snapshot", required=True)
    p.set_defaults(func=verify)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
