#!/usr/bin/env python3
"""Create a disposable Git fixture for the real ChatGPT Pro browser smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Sequence


NORMALIZER_SOURCE = '''"""Public display-name normalization API."""


def normalize_display_name(value: str) -> str:
    """Trim surrounding whitespace and collapse internal whitespace runs."""
    return value.strip()
'''

TEST_SOURCE = '''import unittest

from normalizer import normalize_display_name


class NormalizeDisplayNameTests(unittest.TestCase):
    def test_trims_and_collapses_ascii_whitespace(self) -> None:
        self.assertEqual(normalize_display_name("  Ada   Lovelace  "), "Ada Lovelace")

    def test_collapses_tabs_and_newlines(self) -> None:
        self.assertEqual(normalize_display_name("Grace\\tBrewster\\nHopper"), "Grace Brewster Hopper")

    def test_preserves_case_and_unicode(self) -> None:
        self.assertEqual(normalize_display_name("  李  小龙  "), "李 小龙")


if __name__ == "__main__":
    unittest.main()
'''

README_SOURCE = """# Browser Smoke Fixture

This is a disposable validation repository with no private source.

## Task

Fix `normalize_display_name` so it trims surrounding whitespace and collapses
every internal Unicode whitespace run to one ASCII space.

## Public API

- Keep `normalizer.normalize_display_name(value: str) -> str`.
- Preserve letter case and non-whitespace Unicode characters.
- Do not add dependencies or change the tests.

## Verification

```bash
python3 -m unittest -v
```
"""


def run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "normalizer.py").write_text(NORMALIZER_SOURCE, encoding="utf-8")
    (output_dir / "test_normalizer.py").write_text(TEST_SOURCE, encoding="utf-8")
    (output_dir / "README.md").write_text(README_SOURCE, encoding="utf-8")
    (output_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")

    run(["git", "init", "-q"], output_dir)
    run(["git", "config", "user.email", "fixture@example.test"], output_dir)
    run(["git", "config", "user.name", "Fixture"], output_dir)
    run(["git", "add", "."], output_dir)
    run(["git", "commit", "-q", "-m", "browser smoke baseline"], output_dir)

    baseline = run(["git", "rev-parse", "HEAD"], output_dir).stdout.strip()
    test = subprocess.run(
        ["python3", "-m", "unittest", "-v"],
        cwd=output_dir,
        check=False,
        text=True,
        capture_output=True,
    )
    if test.returncode == 0:
        raise SystemExit("Fixture must begin with a failing acceptance test.")

    print(
        json.dumps(
            {
                "fixture": str(output_dir),
                "baseline_commit": baseline,
                "initial_test_exit": test.returncode,
                "expected_failure": "internal whitespace is not collapsed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
