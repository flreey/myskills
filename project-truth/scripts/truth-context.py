#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


_MANIFEST_NAMES = {
    "Cargo.toml",
    "go.mod",
    "package.json",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
    "tsconfig.json",
    "uv.lock",
    "yarn.lock",
}


def _candidate_directory(start: Path) -> Path:
    candidate = start.expanduser().resolve()
    return candidate.parent if candidate.is_file() else candidate


def _git(
    repository: Path,
    *arguments: str,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=text,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("project-truth: Git command exceeded 30 seconds", file=sys.stderr)
        raise SystemExit(124) from None
    if check and completed.returncode != 0:
        stderr = completed.stderr
        if isinstance(stderr, bytes):
            message = stderr.decode(errors="replace").strip()
        else:
            message = stderr.strip()
        raise ValueError(message or f"git exited with {completed.returncode}")
    return completed


def _repository_root(start: Path) -> Path:
    candidate = _candidate_directory(start)
    completed = _git(candidate, "rev-parse", "--show-toplevel")
    assert isinstance(completed.stdout, str)
    return Path(completed.stdout.strip()).resolve()


def _run_ptruth(script: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            [str(script), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        print("project-truth: command exceeded 180 seconds", file=sys.stderr)
        raise SystemExit(124) from None
    if completed.returncode != 0:
        if completed.stdout:
            sys.stderr.write(completed.stdout)
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout


def _repository_files(repository: Path) -> list[str]:
    completed = _git(
        repository,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
        text=False,
    )
    assert isinstance(completed.stdout, bytes)
    paths: list[str] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(
                "repository contains a path that is not valid UTF-8"
            ) from error
        normalized = path.replace("\\", "/")
        if not normalized.startswith(".project-truth/"):
            paths.append(normalized)
    return sorted(set(paths))


def _limited(values: list[str], limit: int = 50) -> dict[str, Any]:
    return {
        "count": len(values),
        "paths": values[:limit],
        "truncated": len(values) > limit,
    }


def _intent_paths(paths: list[str]) -> list[str]:
    selected: list[str] = []
    for path in paths:
        lowered = path.lower()
        name = Path(path).name.lower()
        if (
            name in {"agents.md", "readme", "readme.md", "readme.rst", "readme.txt"}
            or lowered.startswith(("docs/", "openspec/", "specs/"))
            or "prd" in name
        ):
            selected.append(path)
    return selected


def _language_detection(paths: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    python_evidence = [
        path
        for path in paths
        if Path(path).name
        in {
            "pyproject.toml",
            "requirements.txt",
            "setup.cfg",
            "setup.py",
            "uv.lock",
        }
        or path.endswith(".py")
    ]
    typescript_evidence = [
        path
        for path in paths
        if Path(path).name == "tsconfig.json"
        or path.endswith((".ts", ".tsx", ".mts", ".cts"))
    ]
    evidence = {
        "python": python_evidence[:20],
        "typescript": typescript_evidence[:20],
    }
    languages = [language for language, items in evidence.items() if items]
    return languages, evidence


def _project_id(name: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not candidate or not candidate[0].isalpha():
        candidate = f"project-{candidate}".rstrip("-")
    candidate = candidate[:64].rstrip("-")
    if len(candidate) < 2:
        candidate = f"{candidate}x"
    return candidate


def _truth_root_status(repository: Path) -> dict[str, Any]:
    root = repository / ".project-truth"
    if not root.exists():
        return {"path": str(root), "state": "absent", "entry_count": 0, "entries": []}
    if not root.is_dir():
        return {
            "path": str(root),
            "state": "invalid_path",
            "entry_count": 1,
            "entries": [root.name],
        }
    entries = sorted(path.name for path in root.iterdir())
    return {
        "path": str(root),
        "state": "empty" if not entries else "non_empty_without_authority",
        "entry_count": len(entries),
        "entries": entries[:20],
    }


def _bootstrap_context(repository: Path, pin: str) -> dict[str, Any]:
    paths = _repository_files(repository)
    manifests = [path for path in paths if Path(path).name in _MANIFEST_NAMES]
    intents = _intent_paths(paths)
    languages, language_evidence = _language_detection(paths)

    branch_result = _git(
        repository, "symbolic-ref", "--quiet", "--short", "HEAD", check=False
    )
    assert isinstance(branch_result.stdout, str)
    branch = branch_result.stdout.strip() or None

    commit_result = _git(repository, "rev-parse", "--verify", "HEAD", check=False)
    assert isinstance(commit_result.stdout, str)
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None

    status_result = _git(
        repository, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    )
    assert isinstance(status_result.stdout, str)

    remote_result = _git(repository, "remote")
    assert isinstance(remote_result.stdout, str)
    remote_names = sorted(line for line in remote_result.stdout.splitlines() if line)

    origin_head = _git(
        repository,
        "symbolic-ref",
        "--quiet",
        "--short",
        "refs/remotes/origin/HEAD",
        check=False,
    )
    assert isinstance(origin_head.stdout, str)
    remote_default = origin_head.stdout.strip()
    if remote_default.startswith("origin/"):
        remote_default = remote_default.removeprefix("origin/")
    local_branches_result = _git(repository, "branch", "--format=%(refname:short)")
    assert isinstance(local_branches_result.stdout, str)
    local_branches = set(local_branches_result.stdout.splitlines())
    conventional_default = next(
        (candidate for candidate in ("main", "master") if candidate in local_branches),
        None,
    )
    default_branch = remote_default or conventional_default or branch

    truth_root = _truth_root_status(repository)
    blockers: list[str] = []
    choices: list[str] = []
    if truth_root["state"] not in {"absent", "empty"}:
        blockers.append("NON_EMPTY_PROJECT_TRUTH_ROOT")
    if commit is None:
        blockers.append("UNBORN_HEAD")
    if len(languages) != 1:
        choices.append("language")
    if default_branch is None:
        choices.append("default_branch")

    if blockers:
        readiness = "blocked"
    elif choices:
        readiness = "needs_input"
    else:
        readiness = "ready_for_plan"

    if blockers:
        next_action = "resolve_blockers"
    elif choices:
        next_action = "collect_user_choices"
    else:
        next_action = "review_initialization_plan"

    return {
        "schema": "project-truth/bootstrap-context@1",
        "mode": "uninitialized",
        "engine_commit": pin,
        "readiness": readiness,
        "repository": {
            "root": str(repository),
            "name": repository.name,
            "branch": branch,
            "commit": commit,
            "dirty": bool(status_result.stdout),
            "remote_names": remote_names,
        },
        "project_truth_root": truth_root,
        "detected": {
            "supported_languages": languages,
            "language_evidence": language_evidence,
            "manifests": _limited(manifests),
            "intent_paths": _limited(intents),
        },
        "recommended_init": {
            "project_id": _project_id(repository.name),
            "name": repository.name,
            "default_branch": default_branch,
            "language": languages[0] if len(languages) == 1 else None,
        },
        "requires_user_choice": choices,
        "blockers": blockers,
        "next_action": next_action,
    }


def _criterion_item(
    capability: dict[str, Any], criterion: dict[str, Any]
) -> dict[str, Any]:
    return {
        "capability_id": capability["id"],
        "capability_name": capability["name"],
        "criterion_id": criterion["criterion_id"],
        "dimension": criterion["dimension"],
        "state": criterion["state"],
        "reason_code": criterion["reason_code"],
        "explanation": criterion["explanation"],
        "next_action": criterion.get("next_action"),
        "receipt_ids": criterion["receipts"],
    }


def _compact(status: dict[str, Any], pin: str) -> dict[str, Any]:
    criterion_counts: Counter[str] = Counter()
    capability_rows: list[dict[str, Any]] = []
    actionable: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    authority_review: list[dict[str, Any]] = []

    for capability in status["capabilities"]:
        local_attention: list[dict[str, Any]] = []
        for criterion in capability["criteria"]:
            criterion_counts[criterion["state"]] += 1
            if criterion["state"] == "PASS":
                continue
            item = _criterion_item(capability, criterion)
            local_attention.append(item)
            if criterion["state"] == "MANUAL":
                manual.append(item)
            elif criterion["state"] == "CONFLICT":
                blocked.append(item)
            else:
                actionable.append(item)

        definition_gaps: list[dict[str, Any]] = []
        for dimension_name, dimension in capability["dimensions"].items():
            if dimension["state"] == "PASS" or dimension["criteria"]:
                continue
            gap = {
                "capability_id": capability["id"],
                "capability_name": capability["name"],
                "dimension": dimension_name,
                "state": dimension["state"],
                "reason_code": dimension["reason_code"],
                "explanation": dimension["explanation"],
                "requires": "authority_review",
            }
            definition_gaps.append(gap)
            authority_review.append(gap)

        capability_rows.append(
            {
                "id": capability["id"],
                "name": capability["name"],
                "lifecycle": capability["lifecycle"],
                "posture": capability["posture"],
                "delivery": capability["delivery"],
                "criterion_counts": dict(
                    sorted(
                        Counter(
                            item["state"] for item in capability["criteria"]
                        ).items()
                    )
                ),
                "attention_criterion_ids": [
                    item["criterion_id"] for item in local_attention
                ],
                "definition_gap_dimensions": [
                    item["dimension"] for item in definition_gaps
                ],
            }
        )

    return {
        "schema": "project-truth/skill-context@1",
        "engine_commit": pin,
        "project_id": status["project_id"],
        "revision": status["revision"],
        "evaluated_at": status["evaluated_at"],
        "criterion_counts": dict(sorted(criterion_counts.items())),
        "work_queue": {
            "actionable": actionable,
            "manual": manual,
            "blocked": blocked,
            "authority_review": authority_review,
        },
        "capabilities": capability_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect initialization readiness or validate Project Truth and emit compact "
            "read-only AI context."
        )
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    script = Path(__file__).resolve().with_name("ptruth")
    pin = _run_ptruth(script, "--skill-pin").strip()
    try:
        repository = _repository_root(args.root)
        if not (repository / ".project-truth/project.yaml").is_file():
            output = _bootstrap_context(repository, pin)
        else:
            _run_ptruth(script, "validate", "--root", str(repository))
            raw_status = _run_ptruth(
                script, "status", "--root", str(repository), "--json"
            )
            try:
                status = json.loads(raw_status)
            except json.JSONDecodeError as error:
                print(
                    f"project-truth: status returned invalid JSON: {error}",
                    file=sys.stderr,
                )
                return 1
            if status.get("schema") != "project-truth/status@1":
                print("project-truth: unsupported status schema", file=sys.stderr)
                return 1
            output = _compact(status, pin)
    except ValueError as error:
        parser.error(str(error))

    separators = None if args.pretty else (",", ":")
    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            separators=separators,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
