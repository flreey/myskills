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


GITHUB_READY = (
    "--pro-github-access",
    "write",
    "--manager-github-access",
    "write",
    "--native-auth-state",
    "ready",
    "--allow-github-collaboration",
)


class SelectTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = TransportFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_clean_remote_baseline_uses_github_fast_path(self) -> None:
        result, payload = self.fixture.select(
            *GITHUB_READY,
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["decision"], "READY_GITHUB")
        self.assertEqual(payload["selected_transport"], "github")
        self.assertTrue(payload["candidates"]["github"]["eligible"])

    def test_unrelated_dirty_state_does_not_block_github(self) -> None:
        (self.fixture.repo / "LOCAL_NOTES.md").write_text(
            "unrelated local note\n",
            encoding="utf-8",
        )
        result, payload = self.fixture.select(
            *GITHUB_READY,
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["repository"]["dirty"])
        self.assertFalse(payload["repository"]["task_needs_local_dirty"])
        self.assertEqual(payload["decision"], "READY_GITHUB")

    def test_native_prompt_preserves_github_selection_but_requires_user_action(
        self,
    ) -> None:
        result, payload = self.fixture.select(
            "--pro-github-access",
            "write",
            "--manager-github-access",
            "write",
            "--native-auth-state",
            "prompt",
            "--allow-github-collaboration",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["result"], "needs-user-action")
        self.assertEqual(payload["decision"], "BLOCKED_AUTH")
        self.assertEqual(payload["selected_transport"], "github")
        self.assertEqual(payload["next_action"], "approve-native-github-prompt")

    def test_local_dirty_dependency_uses_authorized_safe_handoff_branch(
        self,
    ) -> None:
        (self.fixture.repo / "README.md").write_text("dirty fixture\n", encoding="utf-8")
        result, payload = self.fixture.select(
            *GITHUB_READY,
            "--task-needs-local-dirty",
            "--dirty-source-safe-for-github",
            "--allow-handoff-branch",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["decision"], "READY_HANDOFF_BRANCH")
        self.assertEqual(payload["selected_transport"], "handoff-branch")
        self.assertIn(
            "task-requires-local-dirty-state",
            payload["candidates"]["github"]["blockers"],
        )

    def test_unreviewed_dirty_dependency_falls_back_to_bundle(self) -> None:
        (self.fixture.repo / "README.md").write_text("dirty fixture\n", encoding="utf-8")
        result, payload = self.fixture.select(
            *GITHUB_READY,
            "--task-needs-local-dirty",
            "--allow-handoff-branch",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["decision"], "READY_BUNDLE")
        self.assertIn(
            "dirty-source-github-safety-unverified",
            payload["candidates"]["handoff-branch"]["blockers"],
        )

    def test_declared_dirty_dependency_blocks_when_no_dirty_state_exists(
        self,
    ) -> None:
        result, payload = self.fixture.select(
            *GITHUB_READY,
            "--task-needs-local-dirty",
            "--dirty-source-safe-for-github",
            "--allow-handoff-branch",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertEqual(payload["decision"], "BLOCKED")
        self.assertIn(
            "task-relevant-dirty-state-not-present",
            payload["candidates"]["handoff-branch"]["blockers"],
        )
        self.assertIn(
            "task-relevant-dirty-state-not-present",
            payload["candidates"]["bundle"]["blockers"],
        )

    def test_missing_pro_write_falls_back_to_bundle(self) -> None:
        result, payload = self.fixture.select(
            "--pro-github-access",
            "read",
            "--manager-github-access",
            "write",
            "--allow-github-collaboration",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["decision"], "READY_BUNDLE")
        self.assertIn(
            "pro-github-write-unverified",
            payload["candidates"]["github"]["blockers"],
        )

    def test_missing_manager_write_falls_back_to_bundle(self) -> None:
        result, payload = self.fixture.select(
            "--pro-github-access",
            "write",
            "--allow-github-collaboration",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "bundle")
        self.assertIn(
            "manager-github-write-unverified",
            payload["candidates"]["github"]["blockers"],
        )

    def test_unpushed_baseline_falls_back_to_bundle(self) -> None:
        self.fixture.git("commit", "--allow-empty", "-q", "-m", "local only")
        result, payload = self.fixture.select(
            *GITHUB_READY,
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "bundle")
        self.assertIn(
            "baseline-not-in-fetched-remote-refs",
            payload["candidates"]["github"]["blockers"],
        )

    def test_explicit_github_fails_closed_without_collaboration_authority(
        self,
    ) -> None:
        result, payload = self.fixture.select(
            "--requested",
            "github",
            "--pro-github-access",
            "write",
            "--manager-github-access",
            "write",
        )

        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertEqual(payload["decision"], "BLOCKED")
        self.assertIsNone(payload["selected_transport"])
        self.assertIn(
            "missing-authority:github-collaboration",
            payload["candidates"]["github"]["blockers"],
        )

    def test_auto_blocks_when_no_transport_is_authorized(self) -> None:
        result, payload = self.fixture.select()

        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertEqual(payload["result"], "blocked")
        self.assertEqual(payload["decision"], "BLOCKED")
        self.assertIsNone(payload["selected_transport"])

    def test_legacy_github_pr_name_maps_to_github(self) -> None:
        result, payload = self.fixture.select(
            "--requested",
            "github-pr",
            *GITHUB_READY,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "github")
        self.assertEqual(
            payload["deprecated_request"],
            {"requested": "github-pr", "mapped_to": "github"},
        )

    def test_legacy_issue_patch_name_maps_to_bundle(self) -> None:
        result, payload = self.fixture.select(
            "--requested",
            "github-issue-patch",
            "--allow-bundle-upload",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["selected_transport"], "bundle")
        self.assertEqual(payload["decision"], "READY_BUNDLE")
        self.assertEqual(
            payload["deprecated_request"],
            {"requested": "github-issue-patch", "mapped_to": "bundle"},
        )


if __name__ == "__main__":
    unittest.main()
