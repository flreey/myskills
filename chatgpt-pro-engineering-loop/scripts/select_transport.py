#!/usr/bin/env python3
"""Choose the fast GitHub, handoff-branch, or bundle path for a Pro task."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence


TRANSPORTS = (
    "auto",
    "github",
    "handoff-branch",
    "bundle",
    "github-pr",
    "github-issue-patch",
)
GITHUB_ACCESS_LEVELS = ("none", "read", "write")
NATIVE_AUTH_STATES = ("unknown", "ready", "prompt", "blocked")
LEGACY_ALIASES = {
    "github-pr": "github",
    "github-issue-patch": "bundle",
}


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


def github_base_blockers(
    *,
    remote_present: bool,
    remote_refs: Sequence[str],
    pro_github_access: str,
    manager_github_access: str,
    github_authorized: bool,
    native_auth_state: str,
) -> list[str]:
    blockers: list[str] = []
    if not remote_present:
        blockers.append("missing-git-remote")
    elif not remote_refs:
        blockers.append("baseline-not-in-fetched-remote-refs")
    if pro_github_access != "write":
        blockers.append("pro-github-write-unverified")
    if manager_github_access != "write":
        blockers.append("manager-github-write-unverified")
    if not github_authorized:
        blockers.append("missing-authority:github-collaboration")
    if native_auth_state == "blocked":
        blockers.append("github-native-auth-blocked")
    return blockers


def evaluate_candidates(
    *,
    remote_present: bool,
    remote_refs: Sequence[str],
    source_dirty: bool,
    task_needs_local_dirty: bool,
    dirty_source_safe_for_github: bool,
    pro_github_access: str,
    manager_github_access: str,
    native_auth_state: str,
    github_authorized: bool,
    handoff_authorized: bool,
    bundle_authorized: bool,
) -> dict[str, list[str]]:
    github_base = github_base_blockers(
        remote_present=remote_present,
        remote_refs=remote_refs,
        pro_github_access=pro_github_access,
        manager_github_access=manager_github_access,
        github_authorized=github_authorized,
        native_auth_state=native_auth_state,
    )

    github_blockers = list(github_base)
    if task_needs_local_dirty:
        github_blockers.append("task-requires-local-dirty-state")

    handoff_blockers = list(github_base)
    if not task_needs_local_dirty:
        handoff_blockers.append("handoff-not-needed")
    if task_needs_local_dirty and not source_dirty:
        handoff_blockers.append("task-relevant-dirty-state-not-present")
    if not dirty_source_safe_for_github:
        handoff_blockers.append("dirty-source-github-safety-unverified")
    if not handoff_authorized:
        handoff_blockers.append("missing-authority:handoff-branch")

    bundle_blockers: list[str] = []
    if task_needs_local_dirty and not source_dirty:
        bundle_blockers.append("task-relevant-dirty-state-not-present")
    if not bundle_authorized:
        bundle_blockers.append("missing-authority:bundle-upload")

    return {
        "github": github_blockers,
        "handoff-branch": handoff_blockers,
        "bundle": bundle_blockers,
    }


def choose_transport(
    requested: str,
    blockers: dict[str, list[str]],
) -> tuple[str | None, list[str]]:
    if requested != "auto":
        return (
            requested if not blockers[requested] else None,
            list(blockers[requested]),
        )

    for candidate in ("github", "handoff-branch", "bundle"):
        if not blockers[candidate]:
            skipped = [
                f"{name}:{reason}"
                for name in ("github", "handoff-branch", "bundle")
                if name != candidate
                for reason in blockers[name]
            ]
            return candidate, skipped

    all_blockers = [
        f"{name}:{reason}"
        for name in ("github", "handoff-branch", "bundle")
        for reason in blockers[name]
    ]
    return None, all_blockers


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--requested", choices=TRANSPORTS, default="auto")
    parser.add_argument("--remote", default="origin")
    parser.add_argument(
        "--pro-github-access",
        "--chatgpt-github-access",
        dest="pro_github_access",
        choices=GITHUB_ACCESS_LEVELS,
        default="none",
        help="Live-observed ChatGPT Pro GitHub capability.",
    )
    parser.add_argument(
        "--manager-github-access",
        choices=("none", "write"),
        default="none",
        help=(
            "Live-observed Codex manager capability to create the task branch "
            "and Draft PR for the target repo."
        ),
    )
    parser.add_argument(
        "--native-auth-state",
        choices=NATIVE_AUTH_STATES,
        default="unknown",
        help="Current ChatGPT connected-app approval state.",
    )
    parser.add_argument(
        "--task-needs-local-dirty",
        action="store_true",
        help="The task depends on current uncommitted source.",
    )
    parser.add_argument(
        "--dirty-source-safe-for-github",
        action="store_true",
        help="The exact dirty handoff scope passed secret review and may be published.",
    )
    parser.add_argument("--allow-github-collaboration", action="store_true")
    parser.add_argument("--allow-handoff-branch", action="store_true")
    parser.add_argument("--allow-bundle-upload", action="store_true")
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

    requested = LEGACY_ALIASES.get(args.requested, args.requested)
    deprecated_request = (
        {"requested": args.requested, "mapped_to": requested}
        if args.requested in LEGACY_ALIASES
        else None
    )
    blockers = evaluate_candidates(
        remote_present=remote_present,
        remote_refs=remote_refs,
        source_dirty=source_dirty,
        task_needs_local_dirty=args.task_needs_local_dirty,
        dirty_source_safe_for_github=args.dirty_source_safe_for_github,
        pro_github_access=args.pro_github_access,
        manager_github_access=args.manager_github_access,
        native_auth_state=args.native_auth_state,
        github_authorized=args.allow_github_collaboration,
        handoff_authorized=args.allow_handoff_branch,
        bundle_authorized=args.allow_bundle_upload,
    )
    selected, decision_reasons = choose_transport(requested, blockers)

    needs_native_approval = (
        selected in {"github", "handoff-branch"}
        and args.native_auth_state == "prompt"
    )
    if selected is None:
        result = "blocked"
        decision = "BLOCKED"
    elif needs_native_approval:
        result = "needs-user-action"
        decision = "BLOCKED_AUTH"
    else:
        result = "ready"
        decision = {
            "github": "READY_GITHUB",
            "handoff-branch": "READY_HANDOFF_BRANCH",
            "bundle": "READY_BUNDLE",
        }[selected]

    payload = {
        "schema_version": 2,
        "result": result,
        "decision": decision,
        "requested_transport": args.requested,
        "normalized_requested_transport": requested,
        "deprecated_request": deprecated_request,
        "selected_transport": selected,
        "decision_reasons": decision_reasons,
        "next_action": (
            "approve-native-github-prompt" if needs_native_approval else None
        ),
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
            "dirty_source_safe_for_github": args.dirty_source_safe_for_github,
            "remote": args.remote,
            "remote_present": remote_present,
            "fetched_remote_refs_containing_head": remote_refs,
        },
        "capabilities": {
            "pro_github_access": args.pro_github_access,
            "manager_github_access": args.manager_github_access,
            "native_auth_state": args.native_auth_state,
        },
        "authority": {
            "github_collaboration": args.allow_github_collaboration,
            "handoff_branch": args.allow_handoff_branch,
            "bundle_upload": args.allow_bundle_upload,
        },
        "forbidden_without_separate_authority": [
            "merge",
            "force-push",
            "delete-remote-branch",
            "release",
            "deploy",
            "repository-settings",
            "secret-values",
            "production-data",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if selected else 6


if __name__ == "__main__":
    raise SystemExit(main())
