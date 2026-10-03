#!/usr/bin/env python3
"""Deterministic Gregorian Meihua casting for meihua-reasoning."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class Trigram:
    number: int
    name: str
    symbol: str
    element: str
    lines: tuple[int, int, int]


TRIGRAMS = {
    1: Trigram(1, "乾", "☰", "金", (1, 1, 1)),
    2: Trigram(2, "兑", "☱", "金", (1, 1, 0)),
    3: Trigram(3, "离", "☲", "火", (1, 0, 1)),
    4: Trigram(4, "震", "☳", "木", (1, 0, 0)),
    5: Trigram(5, "巽", "☴", "木", (0, 1, 1)),
    6: Trigram(6, "坎", "☵", "水", (0, 1, 0)),
    7: Trigram(7, "艮", "☶", "土", (0, 0, 1)),
    8: Trigram(8, "坤", "☷", "土", (0, 0, 0)),
}

TRIGRAM_BY_LINES = {trigram.lines: trigram for trigram in TRIGRAMS.values()}

# (upper, lower) using trigram names.
HEXAGRAM_NAMES = {
    ("乾", "乾"): "乾为天", ("兑", "乾"): "泽天夬", ("离", "乾"): "火天大有", ("震", "乾"): "雷天大壮",
    ("巽", "乾"): "风天小畜", ("坎", "乾"): "水天需", ("艮", "乾"): "山天大畜", ("坤", "乾"): "地天泰",
    ("乾", "兑"): "天泽履", ("兑", "兑"): "兑为泽", ("离", "兑"): "火泽睽", ("震", "兑"): "雷泽归妹",
    ("巽", "兑"): "风泽中孚", ("坎", "兑"): "水泽节", ("艮", "兑"): "山泽损", ("坤", "兑"): "地泽临",
    ("乾", "离"): "天火同人", ("兑", "离"): "泽火革", ("离", "离"): "离为火", ("震", "离"): "雷火丰",
    ("巽", "离"): "风火家人", ("坎", "离"): "水火既济", ("艮", "离"): "山火贲", ("坤", "离"): "地火明夷",
    ("乾", "震"): "天雷无妄", ("兑", "震"): "泽雷随", ("离", "震"): "火雷噬嗑", ("震", "震"): "震为雷",
    ("巽", "震"): "风雷益", ("坎", "震"): "水雷屯", ("艮", "震"): "山雷颐", ("坤", "震"): "地雷复",
    ("乾", "巽"): "天风姤", ("兑", "巽"): "泽风大过", ("离", "巽"): "火风鼎", ("震", "巽"): "雷风恒",
    ("巽", "巽"): "巽为风", ("坎", "巽"): "水风井", ("艮", "巽"): "山风蛊", ("坤", "巽"): "地风升",
    ("乾", "坎"): "天水讼", ("兑", "坎"): "泽水困", ("离", "坎"): "火水未济", ("震", "坎"): "雷水解",
    ("巽", "坎"): "风水涣", ("坎", "坎"): "坎为水", ("艮", "坎"): "山水蒙", ("坤", "坎"): "地水师",
    ("乾", "艮"): "天山遁", ("兑", "艮"): "泽山咸", ("离", "艮"): "火山旅", ("震", "艮"): "雷山小过",
    ("巽", "艮"): "风山渐", ("坎", "艮"): "水山蹇", ("艮", "艮"): "艮为山", ("坤", "艮"): "地山谦",
    ("乾", "坤"): "天地否", ("兑", "坤"): "泽地萃", ("离", "坤"): "火地晋", ("震", "坤"): "雷地豫",
    ("巽", "坤"): "风地观", ("坎", "坤"): "水地比", ("艮", "坤"): "山地剥", ("坤", "坤"): "坤为地",
}

GENERATES = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
OVERCOMES = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}


def normalized_remainder(value: int, modulus: int) -> int:
    remainder = value % modulus
    return modulus if remainder == 0 else remainder


def shichen(hour: int) -> int:
    if not 0 <= hour <= 23:
        raise ValueError("hour must be between 0 and 23")
    return ((hour + 1) // 2) % 12 + 1


def cast_two_numbers(first: int, second: int) -> tuple[int, int, int]:
    return (
        normalized_remainder(first, 8),
        normalized_remainder(second, 8),
        normalized_remainder(first + second, 6),
    )


def cast_three_numbers(first: int, second: int, third: int) -> tuple[int, int, int]:
    return (
        normalized_remainder(first, 8),
        normalized_remainder(second, 8),
        normalized_remainder(third, 6),
    )


def cast_gregorian_time(value: datetime) -> tuple[int, int, int]:
    year_branch = (value.year - 4) % 12 + 1
    date_total = year_branch + value.month + value.day
    hour_branch = shichen(value.hour)
    return (
        normalized_remainder(date_total, 8),
        normalized_remainder(date_total + hour_branch, 8),
        normalized_remainder(date_total + hour_branch, 6),
    )


def relation(body: str, function: str) -> str:
    if body == function:
        return "体用比和"
    if GENERATES[function] == body:
        return "用生体"
    if GENERATES[body] == function:
        return "体生用"
    if OVERCOMES[body] == function:
        return "体克用"
    if OVERCOMES[function] == body:
        return "用克体"
    raise AssertionError("unreachable element relation")


def hexagram(lines: Sequence[int]) -> dict:
    lower = TRIGRAM_BY_LINES[tuple(lines[:3])]
    upper = TRIGRAM_BY_LINES[tuple(lines[3:])]
    return {
        "name": HEXAGRAM_NAMES[(upper.name, lower.name)],
        "upper": asdict(upper),
        "lower": asdict(lower),
        "lines_bottom_to_top": list(lines),
    }


def compute(upper_number: int, lower_number: int, moving_line: int) -> dict:
    if upper_number not in TRIGRAMS or lower_number not in TRIGRAMS:
        raise ValueError("upper and lower trigram numbers must be 1..8")
    if not 1 <= moving_line <= 6:
        raise ValueError("moving line must be 1..6")

    upper = TRIGRAMS[upper_number]
    lower = TRIGRAMS[lower_number]
    primary_lines = list(lower.lines + upper.lines)
    mutual_lines = primary_lines[1:4] + primary_lines[2:5]
    changed_lines = primary_lines.copy()
    changed_lines[moving_line - 1] ^= 1

    body = upper if moving_line <= 3 else lower
    function = lower if moving_line <= 3 else upper

    return {
        "primary": hexagram(primary_lines),
        "mutual": hexagram(mutual_lines),
        "transformed": hexagram(changed_lines),
        "moving_line": moving_line,
        "body": asdict(body),
        "function": asdict(function),
        "five_element_relation": relation(body.element, function.element),
        "convention": "single-changing-line body/function; Gregorian time when time mode is used",
    }


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("time must be ISO-8601, e.g. 2026-07-20T08:30:00+08:00") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_subparsers(dest="mode", required=True)

    two = modes.add_parser("two", help="two-number casting")
    two.add_argument("first", type=int)
    two.add_argument("second", type=int)

    three = modes.add_parser("three", help="three-number casting")
    three.add_argument("first", type=int)
    three.add_argument("second", type=int)
    three.add_argument("third", type=int)

    time_parser = modes.add_parser("time", help="Gregorian-time casting")
    time_parser.add_argument("value", type=parse_datetime, help="ISO-8601 datetime with timezone preferred")

    supplied = modes.add_parser("supplied", help="already-cast upper/lower trigram numbers")
    supplied.add_argument("--upper", type=int, required=True, choices=range(1, 9))
    supplied.add_argument("--lower", type=int, required=True, choices=range(1, 9))
    supplied.add_argument("--moving", type=int, required=True, choices=range(1, 7))
    return result


def main() -> None:
    args = parser().parse_args()
    if args.mode == "two":
        numbers = cast_two_numbers(args.first, args.second)
        source = {"method": "two-number", "inputs": [args.first, args.second]}
    elif args.mode == "three":
        numbers = cast_three_numbers(args.first, args.second, args.third)
        source = {"method": "three-number", "inputs": [args.first, args.second, args.third]}
    elif args.mode == "time":
        numbers = cast_gregorian_time(args.value)
        source = {"method": "Gregorian-time", "input": args.value.isoformat()}
    else:
        numbers = (args.upper, args.lower, args.moving)
        source = {"method": "supplied", "upper": args.upper, "lower": args.lower, "moving": args.moving}

    output = {"source": source, **compute(*numbers)}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
