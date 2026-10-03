#!/usr/bin/env python3
"""Build a local SQLite prompt catalog from the public Chinese README."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from typing import Iterable
from urllib.request import Request, urlopen


DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/YouMind-OpenLab/"
    "awesome-gpt-image-2/main/README_zh.md"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "prompt-catalog.sqlite"
USER_AGENT = "select-gpt-image-prompts/1.0"

SECTION_RE = re.compile(
    r"^### No\. (?P<number>\d+): (?P<title>.+?)\s*$\n"
    r"(?P<body>.*?)(?=^### No\. \d+: |^## )",
    re.MULTILINE | re.DOTALL,
)


def fetch_source_document(url: str, timeout: int) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        markdown = response.read().decode(charset)
        return markdown, response.headers.get("ETag", "").strip('"')


def clean_markdown(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", value)
    value = re.sub(r"[*_`]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def extract_block(body: str, start_heading: str, end_heading: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(start_heading)}\s*$\n(?P<value>.*?)"
        rf"(?=^{re.escape(end_heading)}\s*$)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    return clean_markdown(match.group("value")) if match else ""


def extract_prompt(body: str) -> str:
    match = re.search(
        r"^#### 📝 提示词\s*$\n+\s*```[^\n]*\n(?P<prompt>.*?)\n```",
        body,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("prompt").strip() if match else ""


def extract_markdown_link(body: str, label: str) -> tuple[str, str]:
    pattern = re.compile(
        rf"^- \*\*{re.escape(label)}:\*\*\s*"
        r"(?:\[(?P<name>[^\]]+)\]\((?P<url>[^\)]+)\)|(?P<plain>.+?))\s*$",
        re.MULTILINE,
    )
    match = pattern.search(body)
    if not match:
        return "", ""
    return (
        (match.group("name") or match.group("plain") or "").strip(),
        (match.group("url") or "").strip(),
    )


def extract_detail(body: str, label: str) -> str:
    match = re.search(
        rf"^- \*\*{re.escape(label)}:\*\*\s*(?P<value>.+?)\s*$",
        body,
        re.MULTILINE,
    )
    return clean_markdown(match.group("value")) if match else ""


def extract_first_url(body: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, body, re.MULTILINE)
        if match:
            return match.group("url").strip()
    return ""


def parse_catalog(markdown: str) -> list[dict[str, object]]:
    regular_marker = markdown.find("## 📋 所有提示词")
    if regular_marker < 0:
        raise ValueError("Could not find the regular prompt section in README_zh.md")

    records: list[dict[str, object]] = []
    seen_hashes: set[str] = set()
    for match in SECTION_RE.finditer(markdown):
        body = match.group("body")
        full_title = match.group("title").strip()
        featured = match.start() < regular_marker
        category = "精选"
        title = full_title
        if not featured and " - " in full_title:
            category, title = (part.strip() for part in full_title.split(" - ", 1))

        prompt = extract_prompt(body)
        description = extract_block(body, "#### 📖 描述", "#### 📝 提示词")
        if not prompt:
            continue

        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)

        author, author_url = extract_markdown_link(body, "作者")
        _, source_url = extract_markdown_link(body, "来源")
        preview_url = extract_first_url(
            body,
            (
                r'<img\s+src="(?P<url>[^"]+)"',
                r"^!\[[^\]]*\]\((?P<url>[^\)]+)\)",
            ),
        )
        detail_url = extract_first_url(
            body,
            (r"^\*\*\[👉[^\]]*\]\((?P<url>[^\)]+)\)\*\*",),
        )
        records.append(
            {
                "sequence": len(records) + 1,
                "source_number": int(match.group("number")),
                "featured": int(featured),
                "category": category,
                "title": title,
                "full_title": full_title,
                "description": description,
                "prompt": prompt,
                "author": author,
                "author_url": author_url,
                "source_url": source_url,
                "detail_url": detail_url,
                "preview_url": preview_url,
                "language": extract_detail(body, "多语言"),
                "published_at": extract_detail(body, "发布时间"),
                "prompt_sha256": digest,
            }
        )

    if len(records) < 10:
        raise ValueError(f"Parsed only {len(records)} prompts; refusing to replace the catalog")
    return records


def extract_claimed_total(markdown: str) -> str:
    match = re.search(r"提示词总数\s*\|\s*\*\*(\d+)\*\*", markdown)
    return match.group(1) if match else ""


def build_database(
    output: Path,
    records: list[dict[str, object]],
    metadata: dict[str, str],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        connection = sqlite3.connect(temporary)
        connection.executescript(
            """
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE prompts (
                id INTEGER PRIMARY KEY,
                sequence INTEGER NOT NULL,
                source_number INTEGER NOT NULL,
                featured INTEGER NOT NULL CHECK (featured IN (0, 1)),
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                full_title TEXT NOT NULL,
                description TEXT NOT NULL,
                prompt TEXT NOT NULL,
                author TEXT NOT NULL,
                author_url TEXT NOT NULL,
                source_url TEXT NOT NULL,
                detail_url TEXT NOT NULL,
                preview_url TEXT NOT NULL,
                language TEXT NOT NULL,
                published_at TEXT NOT NULL,
                prompt_sha256 TEXT NOT NULL UNIQUE
            );
            CREATE INDEX prompts_category_idx ON prompts(category);
            CREATE INDEX prompts_featured_idx ON prompts(featured);
            CREATE VIRTUAL TABLE prompts_fts USING fts5(
                title,
                full_title,
                category,
                description,
                prompt,
                content='prompts',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );
            """
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items()
        )
        columns = tuple(records[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO prompts({', '.join(columns)}) VALUES ({placeholders})",
            ([record[column] for column in columns] for record in records),
        )
        connection.execute(
            "INSERT INTO prompts_fts(rowid, title, full_title, category, description, prompt) "
            "SELECT id, title, full_title, category, description, prompt FROM prompts"
        )
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        connection.close()
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        os.replace(temporary, output)
        output.chmod(0o644)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync public awesome-gpt-image-2 prompts into a local SQLite catalog."
    )
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown, source_etag = fetch_source_document(args.source_url, args.timeout)
    records = parse_catalog(markdown)
    metadata = {
        "source_url": args.source_url,
        "source_repository": "https://github.com/YouMind-OpenLab/awesome-gpt-image-2",
        "source_etag": source_etag,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "record_count": str(len(records)),
        "featured_count": str(sum(int(record["featured"]) for record in records)),
        "upstream_claimed_total": extract_claimed_total(markdown),
        "license": "CC BY 4.0",
    }
    output = args.output.expanduser().resolve()
    build_database(output, records, metadata)
    print(
        json.dumps(
            {"output": str(output), **metadata},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
