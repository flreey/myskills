#!/usr/bin/env python3
"""Build a deterministic, task-scoped source ZIP after fail-closed secret checks."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


SCANNER_VERSION = "chatgpt-pro-bundle-scanner-v1"
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

DENIED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".codex",
    ".claude",
    ".agents",
    ".serena",
    "node_modules",
    "bower_components",
    "dist",
    "build",
    "out",
    "target",
    "coverage",
    ".coverage",
    ".next",
    ".nuxt",
    ".cache",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "Pods",
    "DerivedData",
    "Library",
    "Temp",
    "tmp",
    "logs",
    "browser-state",
    "browser-profile",
}

DENIED_SUFFIXES = {
    ".db",
    ".db3",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
    ".mobileprovision",
    ".cookie",
    ".cookies",
    ".pid",
    ".sock",
    ".log",
    ".trace",
}

SENSITIVE_NAME_RE = re.compile(
    r"(^|[._-])(?:"
    r"\.env(?:[._-].*)?|"
    r"credentials?|secrets?|cookies?|"
    r"id_(?:rsa|dsa|ecdsa|ed25519)|"
    r"service[._-]?account|"
    r"auth[._-]?(?:state|token)|"
    r"session[._-]?(?:state|token)"
    r")($|[._-])",
    re.IGNORECASE,
)

PLACEHOLDER_RE = re.compile(
    r"(?:example|sample|dummy|placeholder|changeme|replace[_-]?me|"
    r"your[_-]?(?:api[_-]?)?(?:key|token|secret|password)|"
    r"test[_-]?(?:api[_-]?)?(?:key|token|secret))",
    re.IGNORECASE,
)

IGNORED_ENTROPY_LINE_RE = re.compile(
    r"(?:integrity|checksum|sha(?:1|224|256|384|512)|contenthash|"
    r"sourceMappingURL|lockfileVersion)",
    re.IGNORECASE,
)

SECRET_PATTERNS: Sequence[tuple[str, re.Pattern[str]]] = (
    (
        "private-key",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "github-token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    ),
    ("openai-style-token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("npm-token", re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b")),
    ("pypi-token", re.compile(r"\bpypi-[A-Za-z0-9_-]{20,}\b")),
    (
        "credential-assignment",
        re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|
            secret[_-]?key|password|passwd)\b
            \s*(?:=|:)\s*
            ["']?([A-Za-z0-9_./+=:@-]{8,})["']?
            """
        ),
    ),
)

ENTROPY_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_+/=-]{28,160}(?![A-Za-z0-9])")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    category: str


@dataclass(frozen=True)
class SelectedFile:
    relative_path: str
    size: int
    sha256: str
    data: bytes


class SizeLimitExceeded(Exception):
    def __init__(self, selected_bytes: int, max_bytes: int, file_count: int) -> None:
        super().__init__(
            f"selected source is {selected_bytes} bytes; limit is {max_bytes} bytes"
        )
        self.selected_bytes = selected_bytes
        self.max_bytes = max_bytes
        self.file_count = file_count


def run_git(repo: Path, args: Sequence[str], *, text: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=text,
    )
    if result.returncode != 0:
        stderr = result.stderr if text else result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return result.stdout


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def exclusion_reason(relative_path: str, absolute_path: Path, output_dir: Path) -> str | None:
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts:
        return "unsafe-path"
    if any(part in DENIED_DIR_NAMES for part in pure.parts[:-1]):
        return "denied-directory"

    lowered_name = pure.name.lower()
    if SENSITIVE_NAME_RE.search(lowered_name):
        return "sensitive-filename"
    if any(lowered_name.endswith(suffix) for suffix in DENIED_SUFFIXES):
        return "denied-file-type"
    if is_within(absolute_path, output_dir):
        return "output-directory"
    if absolute_path.is_symlink():
        return "symlink"
    if not absolute_path.is_file():
        return "not-regular-file"
    return None


def contains_nul(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def scan_text(relative_path: str, data: bytes) -> list[Finding]:
    text = data.decode("utf-8", errors="replace")
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()

    for line_number, line in enumerate(text.splitlines(), start=1):
        for category, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            candidate = match.group(1) if match.lastindex else match.group(0)
            if PLACEHOLDER_RE.search(candidate):
                continue
            marker = (line_number, category)
            if marker not in seen:
                findings.append(Finding(relative_path, line_number, category))
                seen.add(marker)

        if IGNORED_ENTROPY_LINE_RE.search(line) or PLACEHOLDER_RE.search(line):
            continue
        for match in ENTROPY_TOKEN_RE.finditer(line):
            candidate = match.group(0).strip("=_-")
            if (
                len(candidate) >= 28
                and any(char.isalpha() for char in candidate)
                and any(char.isdigit() for char in candidate)
                and shannon_entropy(candidate) >= 4.3
            ):
                marker = (line_number, "high-entropy-token")
                if marker not in seen:
                    findings.append(Finding(relative_path, line_number, "high-entropy-token"))
                    seen.add(marker)
                break
    return findings


def list_candidate_paths(repo: Path, includes: Sequence[str]) -> list[str]:
    args = ["ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *includes]
    raw = run_git(repo, args)
    assert isinstance(raw, bytes)
    return sorted(
        {
            item.decode("utf-8", errors="strict")
            for item in raw.split(b"\0")
            if item
        }
    )


def select_files(
    repo: Path,
    output_dir: Path,
    includes: Sequence[str],
    max_bytes: int,
) -> tuple[list[SelectedFile], list[dict[str, str]], list[Finding]]:
    selected: list[SelectedFile] = []
    excluded: list[dict[str, str]] = []
    findings: list[Finding] = []
    selected_bytes = 0

    for relative_path in list_candidate_paths(repo, includes):
        unresolved_path = repo / relative_path
        if unresolved_path.is_symlink():
            excluded.append({"path": relative_path, "reason": "symlink"})
            continue

        absolute_path = unresolved_path.resolve(strict=False)
        if not is_within(absolute_path, repo):
            excluded.append({"path": relative_path, "reason": "outside-repository"})
            continue

        reason = exclusion_reason(relative_path, absolute_path, output_dir)
        if reason:
            excluded.append({"path": relative_path, "reason": reason})
            continue

        file_size = absolute_path.stat().st_size
        if selected_bytes + file_size > max_bytes:
            raise SizeLimitExceeded(
                selected_bytes=selected_bytes + file_size,
                max_bytes=max_bytes,
                file_count=len(selected) + 1,
            )

        data = absolute_path.read_bytes()
        if len(data) != file_size:
            raise OSError(f"{relative_path} changed size while it was being scanned")
        if contains_nul(data):
            excluded.append({"path": relative_path, "reason": "unapproved-binary"})
            continue
        findings.extend(scan_text(relative_path, data))

        selected.append(
            SelectedFile(
                relative_path=relative_path,
                size=len(data),
                sha256=sha256_bytes(data),
                data=data,
            )
        )
        selected_bytes += len(data)

    return selected, excluded, findings


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("._-")
    if not slug:
        raise ValueError("task ID or repository name has no safe filename characters")
    return slug


def build_manifest(
    repo: Path,
    selected: Sequence[SelectedFile],
    excluded: Sequence[dict[str, str]],
    includes: Sequence[str],
) -> dict[str, object]:
    commit = str(run_git(repo, ["rev-parse", "HEAD"], text=True)).strip()
    branch = str(run_git(repo, ["branch", "--show-current"], text=True)).strip() or "(detached)"
    status_raw = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    assert isinstance(status_raw, bytes)
    status_entries = [
        item.decode("utf-8", errors="replace")
        for item in status_raw.split(b"\0")
        if item
    ]

    return {
        "schema_version": 1,
        "scanner_version": SCANNER_VERSION,
        "git": {
            "commit": commit,
            "branch": branch,
            "dirty": bool(status_entries),
            "status_sha256": sha256_bytes(status_raw),
            "status_entries": status_entries,
        },
        "selection": {
            "includes": list(includes),
            "file_count": len(selected),
            "uncompressed_bytes": sum(item.size for item in selected),
            "files": [
                {
                    "path": item.relative_path,
                    "bytes": item.size,
                    "sha256": item.sha256,
                }
                for item in selected
            ],
            "excluded": list(excluded),
        },
    }


def write_deterministic_zip(
    archive_path: Path, selected: Sequence[SelectedFile], manifest: dict[str, object]
) -> None:
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    with zipfile.ZipFile(
        archive_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for item in selected:
            info = zipfile.ZipInfo(item.relative_path, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, item.data)

        manifest_info = zipfile.ZipInfo("bundle-manifest.json", FIXED_ZIP_TIME)
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        manifest_info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(manifest_info, manifest_bytes)


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Git pathspec to include; repeat as needed. Defaults to the repository root.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Maximum uncompressed selected bytes (default: {DEFAULT_MAX_BYTES}).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo = args.repo.resolve()
    output_dir = args.output_dir.resolve()
    includes = tuple(args.include or ["."])

    if args.max_bytes <= 0:
        print("--max-bytes must be positive", file=sys.stderr)
        return 2

    try:
        root = Path(str(run_git(repo, ["rev-parse", "--show-toplevel"], text=True)).strip()).resolve()
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    if root != repo:
        repo = root

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        selected, excluded, findings = select_files(
            repo, output_dir, includes, args.max_bytes
        )
    except SizeLimitExceeded as error:
        size_report = {
            "schema_version": 1,
            "result": "blocked",
            "reason": "size-limit",
            "selected_bytes": error.selected_bytes,
            "max_bytes": error.max_bytes,
            "file_count": error.file_count,
        }
        report_path = output_dir / "size-limit-report.json"
        write_json(report_path, size_report)
        print(json.dumps({"result": "blocked", "report": str(report_path)}))
        return 5
    except (RuntimeError, OSError, UnicodeError) as error:
        print(str(error), file=sys.stderr)
        return 2

    if findings:
        report = {
            "schema_version": 1,
            "scanner_version": SCANNER_VERSION,
            "result": "blocked",
            "finding_count": len(findings),
            "findings": [
                {"path": item.path, "line": item.line, "category": item.category}
                for item in findings
            ],
            "note": "Secret values are intentionally omitted.",
        }
        report_path = output_dir / "secret-scan-report.json"
        write_json(report_path, report)
        print(json.dumps({"result": "blocked", "report": str(report_path)}))
        return 3

    if not selected:
        print("No eligible source files matched the requested scope.", file=sys.stderr)
        return 4

    total_bytes = sum(item.size for item in selected)
    manifest = build_manifest(repo, selected, excluded, includes)
    repo_slug = safe_slug(repo.name)
    task_slug = safe_slug(args.task_id)
    commit_short = str(manifest["git"]["commit"])[:12]  # type: ignore[index]
    base_name = f"{repo_slug}-{task_slug}-source-{commit_short}"
    archive_path = output_dir / f"{base_name}.zip"
    manifest_path = output_dir / f"{base_name}.manifest.json"
    sha_path = output_dir / f"{base_name}.sha256"

    write_deterministic_zip(archive_path, selected, manifest)
    write_json(manifest_path, manifest)
    archive_sha256 = sha256_file(archive_path)
    sha_path.write_text(f"{archive_sha256}  {archive_path.name}\n", encoding="utf-8")

    summary = {
        "result": "ok",
        "archive": str(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": archive_sha256,
        "manifest": str(manifest_path),
        "sha256_file": str(sha_path),
        "source_commit": manifest["git"]["commit"],  # type: ignore[index]
        "source_branch": manifest["git"]["branch"],  # type: ignore[index]
        "source_dirty": manifest["git"]["dirty"],  # type: ignore[index]
        "source_status_sha256": manifest["git"]["status_sha256"],  # type: ignore[index]
        "selected_files": len(selected),
        "selected_bytes": total_bytes,
        "excluded_files": len(excluded),
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
