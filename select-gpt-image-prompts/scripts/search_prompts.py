#!/usr/bin/env python3
"""Search and rank prompts in the local SQLite catalog."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sqlite3
import sys
import unicodedata


DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "assets" / "prompt-catalog.sqlite"

SCENES: dict[str, dict[str, tuple[str, ...]]] = {
    "profile-avatar": {
        "categories": ("个人资料 / 头像",),
        "aliases": (
            "个人头像",
            "个人资料",
            "头像",
            "人像",
            "自拍",
            "证件照",
            "portrait",
            "avatar",
            "selfie",
        ),
    },
    "social-media-post": {
        "categories": ("社交媒体帖子",),
        "aliases": ("社交媒体", "小红书", "instagram", "post", "朋友圈", "社媒"),
    },
    "infographic-edu-visual": {
        "categories": ("信息图 / 教育视觉图",),
        "aliases": (
            "信息图",
            "教育视觉图",
            "教育视觉",
            "教育图",
            "知识卡片",
            "图表",
            "infographic",
            "diagram",
        ),
    },
    "youtube-thumbnail": {
        "categories": ("YouTube 缩略图",),
        "aliases": ("youtube", "缩略图", "视频封面", "thumbnail", "b站封面"),
    },
    "comic-storyboard": {
        "categories": ("漫画 / 故事板",),
        "aliases": ("漫画", "故事板", "分镜", "comic", "storyboard"),
    },
    "product-marketing": {
        "categories": ("产品营销",),
        "aliases": ("产品营销", "产品广告", "营销图", "宣传图", "campaign", "advertising"),
    },
    "ecommerce-main-image": {
        "categories": ("电商主图",),
        "aliases": ("电商", "主图", "商品图", "详情页", "ecommerce", "product shot"),
    },
    "game-asset": {
        "categories": ("游戏素材",),
        "aliases": ("游戏素材", "游戏角色", "游戏场景", "game asset", "game ui"),
    },
    "poster-flyer": {
        "categories": ("海报 / 传单",),
        "aliases": ("海报", "传单", "poster", "flyer"),
    },
    "app-web-design": {
        "categories": ("App / 网页设计",),
        "aliases": ("网页设计", "app设计", "界面", "ui", "website", "landing page"),
    },
}

STOP_BIGRAMS = {
    "一个",
    "一种",
    "这个",
    "那个",
    "帮我",
    "我要",
    "需要",
    "生成",
    "制作",
    "图片",
    "画面",
    "风格",
    "做一",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def cjk_ngrams(value: str) -> set[str]:
    grams: set[str] = set()
    for chunk in re.findall(r"[\u3400-\u9fff]+", value):
        for size in (2, 3, 4):
            for index in range(max(0, len(chunk) - size + 1)):
                gram = chunk[index : index + size]
                if gram not in STOP_BIGRAMS:
                    grams.add(gram)
    return grams


def ascii_terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9][a-z0-9.+-]+", value) if len(term) > 1}


def detect_scenes(query: str, category_hint: str) -> list[str]:
    normalized_query = normalize(f"{query} {category_hint}")
    detected: list[str] = []
    for slug, details in SCENES.items():
        values = (slug, *details["categories"], *details["aliases"])
        if any(normalize(value) in normalized_query for value in values):
            detected.append(slug)
    return detected


def strip_scene_terms(query: str, scenes: list[str]) -> str:
    value = normalize(query)
    removable = {
        normalize(term)
        for scene in scenes
        for term in (
            scene,
            *SCENES[scene]["categories"],
            *SCENES[scene]["aliases"],
        )
    }
    for term in sorted(removable, key=len, reverse=True):
        value = value.replace(term, " ")
    return re.sub(r"\s+", " ", value).strip()


def score_record(record: sqlite3.Row, query: str, scenes: list[str]) -> tuple[float, list[str]]:
    normalized_query = strip_scene_terms(query, scenes)
    query_grams = cjk_ngrams(normalized_query)
    query_terms = ascii_terms(normalized_query)
    score = 0.0
    reasons: list[str] = []

    scene_categories = {
        category
        for scene in scenes
        for category in SCENES[scene]["categories"]
    }
    if record["category"] in scene_categories:
        score += 24.0
        reasons.append(f"用途匹配：{record['category']}")

    fields = (
        ("title", record["title"], 8.0),
        ("category", record["category"], 10.0),
        ("description", record["description"], 4.0),
        ("prompt", record["prompt"], 1.5),
    )
    matched_terms: Counter[str] = Counter()
    for _, raw_value, weight in fields:
        value = normalize(raw_value)
        if normalized_query and len(normalized_query) >= 3 and normalized_query in value:
            score += weight * 3
        field_grams = cjk_ngrams(value)
        overlap = query_grams & field_grams
        if query_grams:
            score += weight * 4 * (len(overlap) / len(query_grams))
        for gram in overlap:
            matched_terms[gram] += 1
        field_terms = ascii_terms(value)
        ascii_overlap = query_terms & field_terms
        score += weight * 2 * len(ascii_overlap)
        for term in ascii_overlap:
            matched_terms[term] += 1

    if record["featured"]:
        score += 0.5
    if matched_terms:
        readable = [term for term, _ in matched_terms.most_common(4)]
        reasons.append("关键词匹配：" + "、".join(readable))
    if not reasons:
        reasons.append("视觉结构相近")
    return round(score, 3), reasons


def open_database(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(
            f"Catalog not found at {path}. Run scripts/sync_catalog.py first."
        )
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def search(
    connection: sqlite3.Connection,
    query: str,
    category_hint: str,
    scenes: list[str],
    limit: int,
) -> list[dict[str, object]]:
    combined_query = " ".join(part for part in (query, category_hint) if part)
    rows = connection.execute("SELECT * FROM prompts").fetchall()
    ranked: list[dict[str, object]] = []
    for row in rows:
        score, reasons = score_record(row, combined_query, scenes)
        ranked.append(
            {
                "id": row["id"],
                "score": score,
                "match_reasons": reasons,
                "featured": bool(row["featured"]),
                "category": row["category"],
                "title": row["title"],
                "description": row["description"],
                "prompt": row["prompt"],
                "author": row["author"],
                "source_url": row["source_url"],
                "detail_url": row["detail_url"],
                "preview_url": row["preview_url"],
            }
        )
    ranked.sort(key=lambda item: (float(item["score"]), bool(item["featured"])), reverse=True)
    return ranked[:limit]


def render_markdown(results: list[dict[str, object]], warnings: list[str]) -> str:
    lines: list[str] = []
    for warning in warnings:
        lines.append(f"> 注意：{warning}")
    if warnings:
        lines.append("")
    for index, result in enumerate(results, start=1):
        lines.extend(
            (
                f"## {index}. {result['title']}",
                "",
                f"- 分类：{result['category']}",
                f"- 匹配分：{result['score']}",
                f"- 原因：{'；'.join(result['match_reasons'])}",
                f"- 描述：{result['description']}",
            )
        )
        source = result["source_url"] or result["detail_url"]
        if source:
            lines.append(f"- 来源：{source}")
        lines.extend(("", "```text", str(result["prompt"]), "```", ""))
    return "\n".join(lines).rstrip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search the local GPT Image prompt catalog."
    )
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--category", default="", help="Category slug or natural-language hint")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--list-categories", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1 or args.limit > 20:
        print("--limit must be between 1 and 20", file=sys.stderr)
        return 2
    database = args.database.expanduser().resolve()
    try:
        connection = open_database(database)
    except (FileNotFoundError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.list_categories:
        payload = [
            {
                "slug": slug,
                "catalog_categories": list(details["categories"]),
                "aliases": list(details["aliases"]),
            }
            for slug, details in SCENES.items()
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not args.query and not args.category:
        print("Provide a query or --category", file=sys.stderr)
        return 2

    scenes = detect_scenes(args.query, args.category)
    available_categories = {
        row[0] for row in connection.execute("SELECT DISTINCT category FROM prompts")
    }
    missing_categories = sorted(
        {
            category
            for scene in scenes
            for category in SCENES[scene]["categories"]
            if category not in available_categories
        }
    )
    warnings = [
        f"本地目录没有“{category}”分类样本，结果是跨分类近似匹配"
        for category in missing_categories
    ]
    results = search(connection, args.query, args.category, scenes, args.limit)
    connection.close()
    if args.format == "json":
        print(
            json.dumps(
                {
                    "query": args.query,
                    "category_hint": args.category,
                    "detected_scenes": scenes,
                    "warnings": warnings,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_markdown(results, warnings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
