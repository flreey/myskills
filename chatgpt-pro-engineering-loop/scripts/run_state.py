#!/usr/bin/env python3
"""Persist and resolve resumable ChatGPT Pro engineering tasks."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import urlsplit


SCHEMA_VERSION = 4
DEFAULT_MAX_CODE_TASKS = 2
DEFAULT_LEASE_SECONDS = 300
SECRET_CLASSES = ("none", "interface-only", "local-test", "ci-test", "production")
TRANSPORT_DECISIONS = (
    "READY_GITHUB",
    "READY_HANDOFF_BRANCH",
    "READY_BUNDLE",
    "BLOCKED_AUTH",
    "BLOCKED",
)
TERMINAL_STATUSES = {"completed", "abandoned", "superseded"}
ACTIVE_STATUSES = {
    "prepared",
    "awaiting-auth",
    "running",
    "delivered",
    "reviewing",
    "correcting",
    "blocked",
    "validated-draft",
}
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
CONVERSATION_PATH_RE = re.compile(r"^/c/([A-Za-z0-9_-]+?)/?$")
SAFE_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class RegistryError(RuntimeError):
    def __init__(
        self,
        decision: str,
        message: str,
        *,
        exit_code: int = 6,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.decision = decision
        self.exit_code = exit_code
        self.details = details or {}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_task_id(task_id: str) -> str:
    if not TASK_ID_RE.fullmatch(task_id):
        raise RegistryError(
            "INVALID_TASK_ID",
            "task ID must contain only letters, numbers, dot, underscore, or dash",
            exit_code=2,
        )
    return task_id


def validate_owner(owner: str) -> str:
    if not owner or len(owner) > 200 or any(ord(character) < 32 for character in owner):
        raise RegistryError(
            "INVALID_OWNER",
            "owner must be a short non-secret task label without control characters",
            exit_code=2,
        )
    return owner


def validate_git_identity(args: argparse.Namespace) -> None:
    if not GITHUB_REPO_RE.fullmatch(args.github_repo):
        raise RegistryError(
            "INVALID_GITHUB_REPO",
            "GitHub repository must use the owner/name form",
            exit_code=2,
        )
    if not GIT_SHA_RE.fullmatch(args.base_sha):
        raise RegistryError(
            "INVALID_BASE_SHA",
            "base SHA must be a full 40-64 character hexadecimal object ID",
            exit_code=2,
        )
    branch = args.task_branch
    branch_parts = branch.split("/") if branch else []
    if (
        not branch
        or not SAFE_BRANCH_RE.fullmatch(branch)
        or any(not part or part.startswith(".") for part in branch_parts)
        or any(part.casefold().endswith(".lock") for part in branch_parts)
        or ".." in branch
        or "@{" in branch
        or "//" in branch
        or branch.startswith((".", "/"))
        or branch.endswith((".", "/"))
    ):
        raise RegistryError(
            "INVALID_TASK_BRANCH",
            "task branch is not a safe Git ref name",
            exit_code=2,
        )
    if not SHA256_RE.fullmatch(args.contract_sha256):
        raise RegistryError(
            "INVALID_CONTRACT_SHA256",
            "execution contract identity must be a full SHA-256",
            exit_code=2,
        )


def canonicalize_conversation_url(url: str) -> tuple[str, str]:
    parsed = urlsplit(url.strip())
    try:
        port = parsed.port
    except ValueError as error:
        raise RegistryError(
            "INVALID_CONVERSATION_URL",
            "conversation URL contains an invalid port",
            exit_code=2,
        ) from error
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() != "chatgpt.com"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise RegistryError(
            "INVALID_CONVERSATION_URL",
            "conversation URL must use https://chatgpt.com",
            exit_code=2,
        )
    match = CONVERSATION_PATH_RE.fullmatch(parsed.path)
    if not match:
        raise RegistryError(
            "CONVERSATION_URL_NOT_STABLE",
            "wait until ChatGPT changes the route to /c/<conversation-id>",
            exit_code=2,
        )
    conversation_id = match.group(1)
    return f"https://chatgpt.com/c/{conversation_id}", conversation_id


def normalize_scope(scope: str) -> str:
    value = scope.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if not value or value.startswith("/"):
        raise RegistryError(
            "INVALID_EDIT_SCOPE",
            f"edit scope must be a repository-relative path: {scope!r}",
            exit_code=2,
        )
    wildcard_at = min(
        (value.find(token) for token in ("*", "?", "[") if token in value),
        default=-1,
    )
    if wildcard_at >= 0:
        value = value[:wildcard_at]
    parts = []
    for part in value.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise RegistryError(
                "INVALID_EDIT_SCOPE",
                f"edit scope must not escape the repository: {scope!r}",
                exit_code=2,
            )
        parts.append(part)
    return "/".join(parts) or "*"


def scopes_overlap(left: Sequence[str], right: Sequence[str]) -> bool:
    for raw_left in left:
        left_scope = normalize_scope(raw_left).casefold()
        for raw_right in right:
            right_scope = normalize_scope(raw_right).casefold()
            if "*" in {left_scope, right_scope}:
                return True
            if left_scope == right_scope:
                return True
            if left_scope.startswith(f"{right_scope}/"):
                return True
            if right_scope.startswith(f"{left_scope}/"):
                return True
    return False


def default_registry_root() -> Path:
    return Path.home() / ".codex" / "chatgpt-pro-runs"


def repo_identity(repo_root: str | Path) -> str:
    return str(Path(repo_root).expanduser().resolve())


def repo_key(repo_root: str) -> str:
    return hashlib.sha256(repo_root.encode("utf-8")).hexdigest()[:16]


def run_path(root: Path, repo_root: str, task_id: str) -> Path:
    return root / "runs" / repo_key(repo_root) / task_id / "run.json"


@contextlib.contextmanager
def registry_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    lock_path = root / ".registry.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RegistryError(
            "REGISTRY_CORRUPT",
            f"cannot read registry state at {path}: {error}",
            exit_code=2,
        ) from error
    if not isinstance(payload, dict):
        raise RegistryError(
            "REGISTRY_CORRUPT",
            f"registry state at {path} is not an object",
            exit_code=2,
        )
    return payload


def scan_runs(root: Path) -> list[dict[str, Any]]:
    runs_root = root / "runs"
    if not runs_root.exists():
        return []
    runs: list[dict[str, Any]] = []
    for path in sorted(runs_root.glob("*/*/run.json")):
        if path.is_symlink():
            continue
        payload = load_json(path)
        payload["_path"] = str(path)
        runs.append(payload)
    return runs


def public_run(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if key != "_path"}


def write_index(root: Path, runs: Sequence[dict[str, Any]]) -> None:
    entries = []
    for run in runs:
        entries.append(
            {
                "task_id": run["task_id"],
                "repo_root": run["repo"]["root"],
                "github_repo": run["repo"]["github"],
                "mode": run["mode"],
                "status": run["status"],
                "task_branch": run["github"]["task_branch"],
                "conversation_id": run["conversation"]["id"],
                "updated_at": run["updated_at"],
                "run_path": run["_path"],
            }
        )
    atomic_write_json(
        root / "index.json",
        {
            "schema_version": SCHEMA_VERSION,
            "updated_at": format_time(utc_now()),
            "runs": entries,
        },
    )


def save_run(root: Path, run: dict[str, Any]) -> None:
    path = Path(run["_path"])
    atomic_write_json(path, public_run(run))
    runs = scan_runs(root)
    write_index(root, runs)


def lease_active(run: dict[str, Any], now: datetime | None = None) -> bool:
    lease = run.get("lease")
    if not lease:
        return False
    current = now or utc_now()
    return parse_time(lease["expires_at"]) > current


def acquire_lease(
    run: dict[str, Any],
    *,
    owner: str,
    lease_seconds: int,
    takeover: bool,
) -> None:
    now = utc_now()
    previous = run.get("lease")
    if previous and lease_active(run, now) and previous["owner"] != owner:
        if not takeover:
            raise RegistryError(
                "LOCKED",
                "another Codex task currently owns this engineering task",
                exit_code=7,
                details={
                    "task_id": run["task_id"],
                    "lease_owner": previous["owner"],
                    "lease_expires_at": previous["expires_at"],
                },
            )
        history = run.setdefault("lease_history", [])
        history.append(
            {
                "event": "takeover",
                "from": previous["owner"],
                "to": owner,
                "at": format_time(now),
            }
        )
        del history[:-20]
    run["lease"] = {
        "owner": owner,
        "acquired_at": format_time(now),
        "expires_at": format_time(now + timedelta(seconds=lease_seconds)),
    }


def require_owner(run: dict[str, Any], owner: str) -> None:
    lease = run.get("lease")
    if not lease or not lease_active(run) or lease["owner"] != owner:
        raise RegistryError(
            "LEASE_REQUIRED",
            "acquire or resume the task lease before changing run state",
            exit_code=7,
            details={"task_id": run["task_id"]},
        )


def load_run(root: Path, repo_root: str, task_id: str) -> dict[str, Any]:
    path = run_path(root, repo_root, validate_task_id(task_id))
    if not path.exists():
        raise RegistryError(
            "RUN_NOT_FOUND",
            f"no run exists for task {task_id!r}",
            exit_code=4,
        )
    run = load_json(path)
    run["_path"] = str(path)
    return run


def active_runs_for_repo(root: Path, repo_root: str) -> list[dict[str, Any]]:
    return [
        run
        for run in scan_runs(root)
        if run["repo"]["root"] == repo_root and run["status"] in ACTIVE_STATUSES
    ]


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    task_id = validate_task_id(args.task_id)
    validate_owner(args.owner)
    validate_git_identity(args)
    edit_scope = [normalize_scope(scope) for scope in args.edit_scope]
    if args.mode == "code" and not edit_scope:
        raise RegistryError(
            "EDIT_SCOPE_REQUIRED",
            "code-changing tasks require at least one edit scope",
            exit_code=2,
        )
    with registry_lock(root):
        path = run_path(root, repository, task_id)
        if path.exists():
            raise RegistryError(
                "TASK_EXISTS",
                f"task {task_id!r} already has a run",
                details={"run_path": str(path)},
            )
        active = active_runs_for_repo(root, repository)
        blockers: list[dict[str, Any]] = []
        if args.mode == "code":
            active_code = [run for run in active if run["mode"] == "code"]
            if len(active_code) >= args.max_code_tasks:
                blockers.append(
                    {
                        "reason": "code-task-capacity",
                        "active": [run["task_id"] for run in active_code],
                        "limit": args.max_code_tasks,
                    }
                )
            for run in active_code:
                if scopes_overlap(edit_scope, run["edit_scope"]):
                    blockers.append(
                        {
                            "reason": "edit-scope-overlap",
                            "task_id": run["task_id"],
                            "scope": run["edit_scope"],
                        }
                    )
        if blockers:
            raise RegistryError(
                "CONCURRENCY_BLOCKED",
                "task cannot start concurrently with the active run set",
                details={"blockers": blockers},
            )

        now = utc_now()
        run: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "task_id": task_id,
            "mode": args.mode,
            "repo": {"root": repository, "github": args.github_repo},
            "execution_contract_sha256": args.contract_sha256,
            "authorization": {
                "secret_class": args.secret_class,
                "allowed_operations": sorted(set(args.allowed_operation)),
            },
            "baseline_commit": args.base_sha,
            "edit_scope": edit_scope,
            "model_policy": {
                "required": "GPT-5.6 Sol Pro",
                "fallback_allowed": False,
            },
            "model_checks": [],
            "transport": {
                "decision": None,
                "selected": None,
                "native_auth_state": "unknown",
            },
            "github": {
                "task_branch": args.task_branch,
                "latest_head": None,
                "draft_pr_url": None,
            },
            "conversation": {"id": None, "canonical_url": None},
            "status": "prepared",
            "last_phase": "contract-confirmed",
            "remaining_acceptance": [],
            "lease": None,
            "lease_history": [],
            "created_at": format_time(now),
            "updated_at": format_time(now),
            "_path": str(path),
        }
        acquire_lease(
            run,
            owner=args.owner,
            lease_seconds=args.lease_seconds,
            takeover=False,
        )
        save_run(root, run)
        return {"decision": "CREATED", "run": public_run(run)}


def select_resume_candidate(
    candidates: Sequence[dict[str, Any]],
    *,
    task_id: str | None,
    task_branch: str | None,
) -> list[dict[str, Any]]:
    selected = list(candidates)
    if task_id:
        selected = [run for run in selected if run["task_id"] == task_id]
    if task_branch:
        selected = [
            run for run in selected if run["github"]["task_branch"] == task_branch
        ]
    return selected


def command_resume(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    if args.task_id:
        validate_task_id(args.task_id)
    validate_owner(args.owner)
    with registry_lock(root):
        candidates = select_resume_candidate(
            active_runs_for_repo(root, repository),
            task_id=args.task_id,
            task_branch=args.task_branch,
        )
        if not candidates:
            return {"decision": "NEW_TASK", "candidates": []}
        if len(candidates) > 1:
            raise RegistryError(
                "AMBIGUOUS",
                "multiple active tasks match; provide task ID or task branch",
                details={
                    "candidates": [
                        {
                            "task_id": run["task_id"],
                            "task_branch": run["github"]["task_branch"],
                            "status": run["status"],
                        }
                        for run in candidates
                    ]
                },
            )
        run = candidates[0]
        acquire_lease(
            run,
            owner=args.owner,
            lease_seconds=args.lease_seconds,
            takeover=args.takeover,
        )
        run["updated_at"] = format_time(utc_now())
        save_run(root, run)
        return {"decision": "RESUME", "run": public_run(run)}


def command_bind(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    validate_owner(args.owner)
    canonical_url, conversation_id = canonicalize_conversation_url(args.url)
    with registry_lock(root):
        run = load_run(root, repository, args.task_id)
        require_owner(run, args.owner)
        existing_id = run["conversation"]["id"]
        if existing_id and existing_id != conversation_id:
            raise RegistryError(
                "CONVERSATION_ID_CONFLICT",
                "a task cannot be rebound to a different ChatGPT conversation",
                details={
                    "task_id": run["task_id"],
                    "conversation_id": existing_id,
                },
            )
        run["conversation"] = {
            "id": conversation_id,
            "canonical_url": canonical_url,
        }
        run["status"] = args.status
        run["last_phase"] = "dispatched"
        run["updated_at"] = format_time(utc_now())
        save_run(root, run)
        return {"decision": "CONVERSATION_BOUND", "run": public_run(run)}


def command_update(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    validate_owner(args.owner)
    if args.latest_head and not GIT_SHA_RE.fullmatch(args.latest_head):
        raise RegistryError(
            "INVALID_HEAD_SHA",
            "latest head must be a full 40-64 character hexadecimal object ID",
            exit_code=2,
        )
    with registry_lock(root):
        run = load_run(root, repository, args.task_id)
        require_owner(run, args.owner)
        if args.status:
            run["status"] = args.status
        if args.last_phase:
            run["last_phase"] = args.last_phase
        if args.latest_head:
            run["github"]["latest_head"] = args.latest_head
        if args.draft_pr_url:
            run["github"]["draft_pr_url"] = args.draft_pr_url
        if args.transport_decision:
            run["transport"]["decision"] = args.transport_decision
        if args.selected_transport:
            run["transport"]["selected"] = args.selected_transport
        if args.native_auth_state:
            run["transport"]["native_auth_state"] = args.native_auth_state
        if args.remaining_acceptance is not None:
            run["remaining_acceptance"] = args.remaining_acceptance
        acquire_lease(
            run,
            owner=args.owner,
            lease_seconds=args.lease_seconds,
            takeover=False,
        )
        run["updated_at"] = format_time(utc_now())
        save_run(root, run)
        return {"decision": "UPDATED", "run": public_run(run)}


def command_record_model(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    validate_owner(args.owner)
    if args.result == "passed" and args.mapped_model != "GPT-5.6 Sol Pro":
        raise RegistryError(
            "MODEL_GATE_MISMATCH",
            "a passed model check must map exactly to GPT-5.6 Sol Pro",
            exit_code=2,
        )
    with registry_lock(root):
        run = load_run(root, repository, args.task_id)
        require_owner(run, args.owner)
        run["model_checks"].append(
            {
                "event": args.event,
                "surface": args.surface,
                "picker_label": args.picker_label,
                "mapped_underlying_model": args.mapped_model,
                "official_mapping_url": args.mapping_url,
                "verified_at": args.verified_at or format_time(utc_now()),
                "result": args.result,
            }
        )
        del run["model_checks"][:-20]
        acquire_lease(
            run,
            owner=args.owner,
            lease_seconds=args.lease_seconds,
            takeover=False,
        )
        run["updated_at"] = format_time(utc_now())
        save_run(root, run)
        return {"decision": "MODEL_RECORDED", "run": public_run(run)}


def command_release(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    validate_owner(args.owner)
    with registry_lock(root):
        run = load_run(root, repository, args.task_id)
        require_owner(run, args.owner)
        run["lease"] = None
        run["updated_at"] = format_time(utc_now())
        save_run(root, run)
        return {"decision": "RELEASED", "run": public_run(run)}


def command_finish(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    validate_owner(args.owner)
    with registry_lock(root):
        run = load_run(root, repository, args.task_id)
        require_owner(run, args.owner)
        run["status"] = args.status
        run["last_phase"] = args.status
        run["lease"] = None
        run["updated_at"] = format_time(utc_now())
        save_run(root, run)
        return {"decision": "FINISHED", "run": public_run(run)}


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.expanduser().resolve()
    repository = repo_identity(args.repo_root)
    with registry_lock(root):
        runs = [
            public_run(run)
            for run in scan_runs(root)
            if run["repo"]["root"] == repository
            and (args.include_terminal or run["status"] in ACTIVE_STATUSES)
        ]
    return {"decision": "LIST", "runs": runs}


def add_common_task_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--owner", required=True)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_registry_root())
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    add_common_task_arguments(init)
    init.add_argument("--github-repo", required=True)
    init.add_argument("--base-sha", required=True)
    init.add_argument("--task-branch", required=True)
    init.add_argument("--contract-sha256", required=True)
    init.add_argument("--secret-class", choices=SECRET_CLASSES, required=True)
    init.add_argument("--allowed-operation", action="append", default=[])
    init.add_argument("--mode", choices=("code", "review"), default="code")
    init.add_argument("--edit-scope", action="append", default=[])
    init.add_argument("--max-code-tasks", type=int, default=DEFAULT_MAX_CODE_TASKS)
    init.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--repo-root", required=True)
    resume.add_argument("--owner", required=True)
    resume.add_argument("--task-id")
    resume.add_argument("--task-branch")
    resume.add_argument("--takeover", action="store_true")
    resume.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)

    bind = subparsers.add_parser("bind-conversation")
    add_common_task_arguments(bind)
    bind.add_argument("--url", required=True)
    bind.add_argument(
        "--status",
        choices=("awaiting-auth", "running", "delivered"),
        default="running",
    )

    update = subparsers.add_parser("update")
    add_common_task_arguments(update)
    update.add_argument("--status", choices=tuple(sorted(ACTIVE_STATUSES)))
    update.add_argument("--last-phase")
    update.add_argument("--latest-head")
    update.add_argument("--draft-pr-url")
    update.add_argument("--transport-decision", choices=TRANSPORT_DECISIONS)
    update.add_argument(
        "--selected-transport",
        choices=("github", "handoff-branch", "bundle"),
    )
    update.add_argument(
        "--native-auth-state",
        choices=("unknown", "ready", "prompt", "blocked"),
    )
    update.add_argument("--remaining-acceptance", action="append")
    update.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)

    record_model = subparsers.add_parser("record-model")
    add_common_task_arguments(record_model)
    record_model.add_argument(
        "--event",
        choices=("conversation-created", "pre-dispatch", "recovery"),
        required=True,
    )
    record_model.add_argument("--surface", required=True)
    record_model.add_argument("--picker-label", required=True)
    record_model.add_argument("--mapped-model", required=True)
    record_model.add_argument("--mapping-url", required=True)
    record_model.add_argument("--verified-at")
    record_model.add_argument("--result", choices=("passed", "blocked"), required=True)
    record_model.add_argument(
        "--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS
    )

    release = subparsers.add_parser("release")
    add_common_task_arguments(release)

    finish = subparsers.add_parser("finish")
    add_common_task_arguments(finish)
    finish.add_argument(
        "--status",
        choices=tuple(sorted(TERMINAL_STATUSES)),
        default="completed",
    )

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--repo-root", required=True)
    list_parser.add_argument("--include-terminal", action="store_true")

    return parser.parse_args(argv)


def validate_lease_seconds(value: int) -> None:
    if value < 30 or value > 3600:
        raise RegistryError(
            "INVALID_LEASE_DURATION",
            "lease duration must be between 30 and 3600 seconds",
            exit_code=2,
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if hasattr(args, "lease_seconds"):
            validate_lease_seconds(args.lease_seconds)
        if getattr(args, "max_code_tasks", 1) < 1:
            raise RegistryError(
                "INVALID_CAPACITY",
                "max code tasks must be at least one",
                exit_code=2,
            )
        handler = {
            "init": command_init,
            "resume": command_resume,
            "bind-conversation": command_bind,
            "update": command_update,
            "record-model": command_record_model,
            "release": command_release,
            "finish": command_finish,
            "list": command_list,
        }[args.command]
        result = handler(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except RegistryError as error:
        payload = {
            "decision": error.decision,
            "error": str(error),
            **error.details,
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
