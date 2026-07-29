from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "select_transport.py"


class TransportFixture:
    def __init__(self, *, push_baseline: bool = True) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        subprocess.run(
            ["git", "init", "--bare", "-q", str(self.remote)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.test")
        self.git("config", "user.name", "Fixture")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-q", "-m", "baseline")
        self.git("remote", "add", "origin", str(self.remote))
        if push_baseline:
            self.git("push", "-q", "-u", "origin", "HEAD")

    def close(self) -> None:
        self.tempdir.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def select(self, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        return result, json.loads(result.stdout)


PR_AUTHORITY = (
    "--allow-github-source-access",
    "--allow-create-issue",
    "--allow-create-branch",
    "--allow-commit",
    "--allow-push",
    "--allow-create-pr",
    "--allow-comment",
)


class SelectTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = TransportFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_auto_prefers_github_pr_when_every_precondition_is_verified(self) -> None:
        result, payload = self.fixture.select(
            "--chatgpt-github-access",
            "write",
            *PR_AUTHORITY,
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "github-pr")
        self.assertTrue(payload["candidates"]["github-pr"]["eligible"])
        self.assertTrue(
            payload["repository"]["fetched_remote_refs_containing_head"]
        )

    def test_auto_uses_issue_patch_when_chatgpt_is_read_only(self) -> None:
        result, payload = self.fixture.select(
            "--chatgpt-github-access",
            "read",
            "--allow-github-source-access",
            "--allow-create-issue",
            "--allow-comment",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "github-issue-patch")
        self.assertIn(
            "chatgpt-github-write-unverified",
            payload["candidates"]["github-pr"]["blockers"],
        )

    def test_auto_falls_back_to_bundle_without_github_access(self) -> None:
        result, payload = self.fixture.select("--allow-bundle-upload")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "bundle")

    def test_task_requiring_dirty_source_forces_bundle(self) -> None:
        (self.fixture.repo / "README.md").write_text("dirty fixture\n", encoding="utf-8")
        result, payload = self.fixture.select(
            "--chatgpt-github-access",
            "write",
            *PR_AUTHORITY,
            "--allow-bundle-upload",
            "--task-needs-local-dirty",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "bundle")
        self.assertIn(
            "task-requires-local-dirty-state",
            payload["candidates"]["github-pr"]["blockers"],
        )

    def test_unpushed_baseline_forces_bundle(self) -> None:
        self.fixture.git("commit", "--allow-empty", "-q", "-m", "local only")
        result, payload = self.fixture.select(
            "--chatgpt-github-access",
            "write",
            *PR_AUTHORITY,
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "bundle")
        self.assertIn(
            "baseline-not-in-fetched-remote-refs",
            payload["candidates"]["github-pr"]["blockers"],
        )

    def test_explicit_github_pr_fails_closed_when_authority_is_missing(self) -> None:
        result, payload = self.fixture.select(
            "--requested",
            "github-pr",
            "--chatgpt-github-access",
            "write",
            "--allow-github-source-access",
        )

        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIsNone(payload["selected_transport"])
        self.assertIn(
            "missing-authority:create_issue",
            payload["candidates"]["github-pr"]["blockers"],
        )

    def test_auto_blocks_when_neither_github_nor_bundle_is_authorized(self) -> None:
        result, payload = self.fixture.select()

        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertEqual(payload["result"], "blocked")
        self.assertIsNone(payload["selected_transport"])


if __name__ == "__main__":
    unittest.main()
