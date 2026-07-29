#!/usr/bin/env python3
"""Select the safest available ChatGPT Pro source and code transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence


TRANSPORTS = ("auto", "github-pr", "github-issue-patch", "bundle")
GITHUB_ACCESS_LEVELS = ("none", "read", "write")
AUTHORITY_FIELDS = (
    "github_source_access",
    "create_issue",
    "create_branch",
    "commit",
    "push",
    "create_pr",
    "comment",
    "bundle_upload",
)


def run_git(
    repo: Path,
    args: Sequence[str],
    *,
    check: bool = True,
    text: bool = False,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=text,
    )
    if check and result.returncode != 0:
        stderr = result.stderr if text else result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return result


def git_text(repo: Path, *args: str) -> str:
    result = run_git(repo, args, text=True)
    assert isinstance(result.stdout, str)
    return result.stdout.strip()


def status_facts(repo: Path) -> tuple[bool, str]:
    result = run_git(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    assert isinstance(result.stdout, bytes)
    return bool(result.stdout), hashlib.sha256(result.stdout).hexdigest()


def remote_facts(repo: Path, remote: str, head: str) -> tuple[bool, list[str]]:
    remote_result = run_git(
        repo,
        ["remote", "get-url", remote],
        check=False,
        text=True,
    )
    assert isinstance(remote_result.stdout, str)
    if remote_result.returncode != 0:
        return False, []

    refs_result = run_git(
        repo,
        [
            "for-each-ref",
            "--format=%(refname:short)",
            f"--contains={head}",
            f"refs/remotes/{remote}",
        ],
        text=True,
    )
    assert isinstance(refs_result.stdout, str)
    refs = sorted(
        line.strip()
        for line in refs_result.stdout.splitlines()
        if line.strip() and line.strip() != f"{remote}/HEAD"
    )
    return True, refs


def missing_authority(
    authority: dict[str, bool], required: Sequence[str]
) -> list[str]:
    return [f"missing-authority:{name}" for name in required if not authority[name]]


def github_common_blockers(
    *,
    remote_present: bool,
    remote_refs: Sequence[str],
    source_dirty: bool,
    task_needs_local_dirty: bool,
    authority: dict[str, bool],
) -> list[str]:
    blockers: list[str] = []
    if not remote_present:
        blockers.append("missing-git-remote")
    elif not remote_refs:
        blockers.append("baseline-not-in-fetched-remote-refs")
    if source_dirty and task_needs_local_dirty:
        blockers.append("task-requires-local-dirty-state")
    blockers.extend(missing_authority(authority, ["github_source_access"]))
    return blockers


def evaluate_candidates(
    *,
    github_access: str,
    common_blockers: Sequence[str],
    authority: dict[str, bool],
) -> dict[str, list[str]]:
    pr_blockers = list(common_blockers)
    if github_access != "write":
        pr_blockers.append("chatgpt-github-write-unverified")
    pr_blockers.extend(
        missing_authority(
            authority,
            [
                "create_issue",
                "create_branch",
                "commit",
                "push",
                "create_pr",
                "comment",
            ],
        )
    )

    issue_patch_blockers = list(common_blockers)
    if github_access not in {"read", "write"}:
        issue_patch_blockers.append("chatgpt-github-read-unverified")
    issue_patch_blockers.extend(
        missing_authority(authority, ["create_issue", "comment"])
    )

    bundle_blockers = missing_authority(authority, ["bundle_upload"])
    return {
        "github-pr": pr_blockers,
        "github-issue-patch": issue_patch_blockers,
        "bundle": bundle_blockers,
    }


def choose_transport(
    requested: str, blockers: dict[str, list[str]]
) -> tuple[str | None, list[str]]:
    if requested != "auto":
        requested_blockers = blockers[requested]
        return (
            (requested if not requested_blockers else None),
            list(requested_blockers),
        )

    for candidate in ("github-pr", "github-issue-patch", "bundle"):
        if not blockers[candidate]:
            skipped = [
                f"{name}:{reason}"
                for name in ("github-pr", "github-issue-patch", "bundle")
                if name != candidate
                for reason in blockers[name]
            ]
            return candidate, skipped

    all_blockers = [
        f"{name}:{reason}"
        for name in ("github-pr", "github-issue-patch", "bundle")
        for reason in blockers[name]
    ]
    return None, all_blockers


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--requested", choices=TRANSPORTS, default="auto")
    parser.add_argument("--remote", default="origin")
    parser.add_argument(
        "--chatgpt-github-access",
        choices=GITHUB_ACCESS_LEVELS,
        default="none",
        help="Live-verified ChatGPT GitHub capability; never infer from subscription.",
    )
    parser.add_argument(
        "--task-needs-local-dirty",
        action="store_true",
        help="The task depends on current uncommitted source.",
    )
    for field in AUTHORITY_FIELDS:
        parser.add_argument(f"--allow-{field.replace('_', '-')}", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        repo = Path(
            git_text(args.repo.resolve(), "rev-parse", "--show-toplevel")
        ).resolve()
        head = git_text(repo, "rev-parse", "HEAD")
        branch = git_text(repo, "branch", "--show-current") or "(detached)"
        source_dirty, status_sha256 = status_facts(repo)
        remote_present, remote_refs = remote_facts(repo, args.remote, head)
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2

    authority = {
        field: bool(getattr(args, f"allow_{field}")) for field in AUTHORITY_FIELDS
    }
    common_blockers = github_common_blockers(
        remote_present=remote_present,
        remote_refs=remote_refs,
        source_dirty=source_dirty,
        task_needs_local_dirty=args.task_needs_local_dirty,
        authority=authority,
    )
    blockers = evaluate_candidates(
        github_access=args.chatgpt_github_access,
        common_blockers=common_blockers,
        authority=authority,
    )
    selected, decision_reasons = choose_transport(args.requested, blockers)

    payload = {
        "schema_version": 1,
        "result": "selected" if selected else "blocked",
        "requested_transport": args.requested,
        "selected_transport": selected,
        "decision_reasons": decision_reasons,
        "candidates": {
            name: {"eligible": not reasons, "blockers": reasons}
            for name, reasons in blockers.items()
        },
        "repository": {
            "root": str(repo),
            "branch": branch,
            "head": head,
            "dirty": source_dirty,
            "status_sha256": status_sha256,
            "task_needs_local_dirty": args.task_needs_local_dirty,
            "remote": args.remote,
            "remote_present": remote_present,
            "fetched_remote_refs_containing_head": remote_refs,
        },
        "chatgpt_github_access": args.chatgpt_github_access,
        "authority": authority,
        "forbidden_without_separate_authority": [
            "merge",
            "force-push",
            "delete-remote-branch",
            "release",
            "deploy",
            "repository-settings",
            "secrets",
            "production-data",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if selected else 6


if __name__ == "__main__":
    raise SystemExit(main())
