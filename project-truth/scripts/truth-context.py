#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _repository_root(start: Path) -> Path:
    candidate = start.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / ".project-truth/project.yaml").is_file():
            return directory
    raise ValueError(
        "no .project-truth/project.yaml found in this path or its ancestors"
    )


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
        description="Validate Project Truth and emit compact read-only AI context."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        repository = _repository_root(args.root)
    except ValueError as error:
        parser.error(str(error))

    script = Path(__file__).resolve().with_name("ptruth")
    pin = _run_ptruth(script, "--skill-pin").strip()
    _run_ptruth(script, "validate", "--root", str(repository))
    raw_status = _run_ptruth(script, "status", "--root", str(repository), "--json")
    try:
        status = json.loads(raw_status)
    except json.JSONDecodeError as error:
        print(f"project-truth: status returned invalid JSON: {error}", file=sys.stderr)
        return 1
    if status.get("schema") != "project-truth/status@1":
        print("project-truth: unsupported status schema", file=sys.stderr)
        return 1

    separators = None if args.pretty else (",", ":")
    print(
        json.dumps(
            _compact(status, pin),
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            separators=separators,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
