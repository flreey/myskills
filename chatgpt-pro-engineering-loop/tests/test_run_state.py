from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "run_state.py"


class RunStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "registry"
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cli(
        self,
        *args: str,
        expected: int | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.root),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if expected is not None:
            self.assertEqual(
                result.returncode, expected, result.stderr or result.stdout
            )
        return result, json.loads(result.stdout)

    def init_task(
        self,
        task_id: str,
        scope: str,
        *,
        owner: str = "codex-a",
        mode: str = "code",
        max_tasks: int = 2,
        expected: int | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        return self.run_cli(
            "init",
            "--repo-root",
            str(self.repo),
            "--github-repo",
            "example/repo",
            "--task-id",
            task_id,
            "--base-sha",
            "a" * 40,
            "--task-branch",
            f"codex/chatgpt-pro/{task_id}",
            "--contract-sha256",
            "b" * 64,
            "--secret-class",
            "none",
            "--allowed-operation",
            "github-collaboration",
            "--mode",
            mode,
            "--edit-scope",
            scope,
            "--max-code-tasks",
            str(max_tasks),
            "--owner",
            owner,
            expected=expected,
        )

    def release(self, task_id: str, owner: str = "codex-a") -> None:
        self.run_cli(
            "release",
            "--repo-root",
            str(self.repo),
            "--task-id",
            task_id,
            "--owner",
            owner,
            expected=0,
        )

    def test_conversation_url_is_canonicalized_and_persisted(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)

        _, payload = self.run_cli(
            "bind-conversation",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-a",
            "--url",
            "https://chatgpt.com/c/abc-123?messageId=finalAgentTurnStart#fragment",
            expected=0,
        )

        self.assertEqual(payload["decision"], "CONVERSATION_BOUND")
        self.assertEqual(payload["run"]["conversation"]["id"], "abc-123")
        self.assertEqual(
            payload["run"]["conversation"]["canonical_url"],
            "https://chatgpt.com/c/abc-123",
        )
        index = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["runs"][0]["conversation_id"], "abc-123")

    def test_root_chat_url_is_rejected_as_not_stable(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)

        _, payload = self.run_cli(
            "bind-conversation",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-a",
            "--url",
            "https://chatgpt.com/",
            expected=2,
        )

        self.assertEqual(payload["decision"], "CONVERSATION_URL_NOT_STABLE")

    def test_task_cannot_be_rebound_to_another_conversation(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)
        for url, expected in (
            ("https://chatgpt.com/c/conversation-a", 0),
            ("https://chatgpt.com/c/conversation-b", 6),
        ):
            _, payload = self.run_cli(
                "bind-conversation",
                "--repo-root",
                str(self.repo),
                "--task-id",
                "task-a",
                "--owner",
                "codex-a",
                "--url",
                url,
                expected=expected,
            )

        self.assertEqual(payload["decision"], "CONVERSATION_ID_CONFLICT")
        self.assertEqual(payload["conversation_id"], "conversation-a")

    def test_model_evidence_is_persisted_for_recovery(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)

        _, payload = self.run_cli(
            "record-model",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-a",
            "--event",
            "pre-dispatch",
            "--surface",
            "Chat",
            "--picker-label",
            "Pro",
            "--mapped-model",
            "GPT-5.6 Sol Pro",
            "--mapping-url",
            "https://help.openai.com/example",
            "--result",
            "passed",
            expected=0,
        )

        self.assertEqual(payload["decision"], "MODEL_RECORDED")
        self.assertFalse(payload["run"]["model_policy"]["fallback_allowed"])
        self.assertEqual(
            payload["run"]["model_checks"][0]["mapped_underlying_model"],
            "GPT-5.6 Sol Pro",
        )

    def test_passed_model_check_rejects_any_fallback_model(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)

        _, payload = self.run_cli(
            "record-model",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-a",
            "--event",
            "pre-dispatch",
            "--surface",
            "Chat",
            "--picker-label",
            "Pro",
            "--mapped-model",
            "GPT-5.6 Sol",
            "--mapping-url",
            "https://help.openai.com/example",
            "--result",
            "passed",
            expected=2,
        )

        self.assertEqual(payload["decision"], "MODEL_GATE_MISMATCH")

    def test_resume_reopens_the_one_matching_active_task(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)
        self.run_cli(
            "bind-conversation",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-a",
            "--url",
            "https://chatgpt.com/c/conversation-a",
            expected=0,
        )
        self.release("task-a")

        _, payload = self.run_cli(
            "resume",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-b",
            expected=0,
        )

        self.assertEqual(payload["decision"], "RESUME")
        self.assertEqual(
            payload["run"]["conversation"]["canonical_url"],
            "https://chatgpt.com/c/conversation-a",
        )
        self.assertEqual(payload["run"]["lease"]["owner"], "codex-b")

    def test_two_non_overlapping_code_tasks_can_run(self) -> None:
        self.init_task("task-a", "backend/payments", expected=0)
        self.init_task("task-b", "frontend/settings", owner="codex-b", expected=0)

        _, payload = self.run_cli(
            "list",
            "--repo-root",
            str(self.repo),
            expected=0,
        )

        self.assertEqual(
            {run["task_id"] for run in payload["runs"]},
            {"task-a", "task-b"},
        )

    def test_overlapping_edit_scope_is_blocked(self) -> None:
        self.init_task("task-a", "backend", expected=0)

        _, payload = self.init_task(
            "task-b",
            "backend/payments",
            owner="codex-b",
            expected=6,
        )

        self.assertEqual(payload["decision"], "CONCURRENCY_BLOCKED")
        self.assertIn(
            "edit-scope-overlap",
            {item["reason"] for item in payload["blockers"]},
        )

    def test_case_only_scope_difference_is_still_a_conflict(self) -> None:
        self.init_task("task-a", "Backend/Payments", expected=0)

        _, payload = self.init_task(
            "task-b",
            "backend/payments/refunds",
            owner="codex-b",
            expected=6,
        )

        self.assertEqual(payload["decision"], "CONCURRENCY_BLOCKED")
        self.assertIn(
            "edit-scope-overlap",
            {item["reason"] for item in payload["blockers"]},
        )

    def test_lexical_scope_alias_is_still_a_conflict(self) -> None:
        self.init_task("task-a", "backend//payments/./refunds", expected=0)

        _, payload = self.init_task(
            "task-b",
            "backend/payments",
            owner="codex-b",
            expected=6,
        )

        self.assertEqual(payload["decision"], "CONCURRENCY_BLOCKED")
        self.assertIn(
            "edit-scope-overlap",
            {item["reason"] for item in payload["blockers"]},
        )

    def test_default_capacity_blocks_a_third_code_task(self) -> None:
        self.init_task("task-a", "backend", expected=0)
        self.init_task("task-b", "frontend", owner="codex-b", expected=0)

        _, payload = self.init_task(
            "task-c",
            "docs",
            owner="codex-c",
            expected=6,
        )

        self.assertEqual(payload["decision"], "CONCURRENCY_BLOCKED")
        self.assertIn(
            "code-task-capacity",
            {item["reason"] for item in payload["blockers"]},
        )

    def test_review_task_does_not_consume_code_capacity_or_conflict(self) -> None:
        self.init_task("task-a", "backend", expected=0)
        self.init_task(
            "review-a",
            "backend",
            owner="codex-review",
            mode="review",
            expected=0,
        )
        self.init_task("task-b", "frontend", owner="codex-b", expected=0)

        _, payload = self.run_cli(
            "list",
            "--repo-root",
            str(self.repo),
            expected=0,
        )
        self.assertEqual(len(payload["runs"]), 3)

    def test_active_lease_blocks_another_owner_without_takeover(self) -> None:
        self.init_task("task-a", "backend", expected=0)

        _, blocked = self.run_cli(
            "resume",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-b",
            expected=7,
        )
        self.assertEqual(blocked["decision"], "LOCKED")

        _, resumed = self.run_cli(
            "resume",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-b",
            "--takeover",
            expected=0,
        )
        self.assertEqual(resumed["run"]["lease"]["owner"], "codex-b")
        self.assertEqual(resumed["run"]["lease_history"][-1]["event"], "takeover")

    def test_multiple_active_tasks_require_an_explicit_selector(self) -> None:
        self.init_task("task-a", "backend", expected=0)
        self.init_task("task-b", "frontend", owner="codex-b", expected=0)
        self.release("task-a", "codex-a")
        self.release("task-b", "codex-b")

        _, payload = self.run_cli(
            "resume",
            "--repo-root",
            str(self.repo),
            "--owner",
            "codex-c",
            expected=6,
        )

        self.assertEqual(payload["decision"], "AMBIGUOUS")
        self.assertEqual(
            {item["task_id"] for item in payload["candidates"]},
            {"task-a", "task-b"},
        )

    def test_completed_task_is_not_resumed(self) -> None:
        self.init_task("task-a", "backend", expected=0)
        self.run_cli(
            "finish",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "task-a",
            "--owner",
            "codex-a",
            "--status",
            "completed",
            expected=0,
        )

        _, payload = self.run_cli(
            "resume",
            "--repo-root",
            str(self.repo),
            "--owner",
            "codex-b",
            expected=0,
        )
        self.assertEqual(payload["decision"], "NEW_TASK")

    def test_task_id_cannot_escape_registry_directory(self) -> None:
        _, payload = self.init_task("../escape", "backend", expected=2)
        self.assertEqual(payload["decision"], "INVALID_TASK_ID")
        self.assertFalse((self.root.parent / "escape").exists())

    def test_unsafe_git_branch_is_rejected(self) -> None:
        _, payload = self.run_cli(
            "init",
            "--repo-root",
            str(self.repo),
            "--github-repo",
            "example/repo",
            "--task-id",
            "task-a",
            "--base-sha",
            "a" * 40,
            "--task-branch",
            "codex/chatgpt-pro/task~a",
            "--contract-sha256",
            "b" * 64,
            "--secret-class",
            "none",
            "--mode",
            "code",
            "--edit-scope",
            "backend",
            "--owner",
            "codex-a",
            expected=2,
        )

        self.assertEqual(payload["decision"], "INVALID_TASK_BRANCH")


if __name__ == "__main__":
    unittest.main()
