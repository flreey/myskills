from __future__ import annotations

import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class ExecutionContractPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.template = (
            SKILL_ROOT / "references" / "execution-contract-template.md"
        ).read_text(encoding="utf-8")
        cls.browser_protocol = (
            SKILL_ROOT / "references" / "browser-and-recovery-protocol.md"
        ).read_text(encoding="utf-8")
        cls.github_protocol = (
            SKILL_ROOT / "references" / "github-transport-protocol.md"
        ).read_text(encoding="utf-8")
        cls.final_evidence = (
            SKILL_ROOT / "references" / "final-evidence-template.md"
        ).read_text(encoding="utf-8")
        cls.readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        cls.metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

    def test_contract_confirmation_precedes_mutating_workflow(self) -> None:
        draft_phase = self.skill.index(
            "## Phase 0A — Draft And Confirm The Execution Contract"
        )
        authority_phase = self.skill.index(
            "## Phase 0B — Establish Authority And Preconditions"
        )
        transport_phase = self.skill.index("## Phase 3 — Select The Transport")
        self.assertLess(draft_phase, authority_phase)
        self.assertLess(authority_phase, transport_phase)

    def test_minimal_requirement_does_not_require_user_authored_matrix(self) -> None:
        self.assertIn(
            "The initial request may contain only a concrete natural-language "
            "requirement.",
            self.skill,
        )
        self.assertIn(
            "Do not require the user to pre-write acceptance criteria, test "
            "commands, or a\npermission matrix.",
            self.skill,
        )
        self.assertIn("需求", self.metadata)
        self.assertIn("等我确认后再执行", self.metadata)

    def test_confirmation_is_exact_and_expansion_requires_reconfirmation(
        self,
    ) -> None:
        self.assertIn(
            "approval authorizes only the operations explicitly listed in "
            "that contract",
            self.skill,
        )
        self.assertIn(
            "operation authority; or an unlisted, destructive, production, or\n"
            "  irreversible operation",
            self.skill,
        )
        self.assertIn(
            "One confirmation activates the task-scoped authorization closure",
            self.template,
        )

    def test_template_covers_scope_acceptance_transport_and_forbidden_ops(
        self,
    ) -> None:
        for heading in (
            "## Goal And Scope",
            "## Acceptance And Verification",
            "## Transport And Authority",
            "## Boundaries And Decisions",
            "## Confirmation",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.template)

    def test_presented_contract_shape_remains_compact(self) -> None:
        rendered = self.template[self.template.index("## Goal And Scope") :]
        line_count = len(rendered.splitlines())
        self.assertGreaterEqual(line_count, 25)
        self.assertLessEqual(line_count, 40)

    def test_one_confirmation_creates_action_time_authorization_closure(
        self,
    ) -> None:
        self.assertIn(
            "That confirmation creates an **authorization closure**",
            self.skill,
        )
        self.assertIn(
            "when all fields match, act without asking permission again",
            self.skill,
        )
        self.assertIn(
            "Codex will not ask again before those operations",
            self.template,
        )
        self.assertIn("我确认一次后，契约内操作不要重复询问权限", self.metadata)

    def test_standard_auto_preset_covers_complete_engineering_loop(self) -> None:
        for required in (
            "create persistent run metadata and a safe bundle",
            "upload only the approved sanitized",
            "send the brief and corrections",
            "create one task Issue and task branch",
            "task-scoped commits and regular pushes",
            "create or update one Draft PR",
            "publish task-scoped Issue/PR comments",
            "eligible GitHub delivery and sanitized-bundle fallback",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.template)

    def test_browser_actions_do_not_create_new_permission_checkpoints(
        self,
    ) -> None:
        self.assertIn("## Authorization Closure", self.browser_protocol)
        self.assertIn(
            "An exact match proceeds immediately without another "
            "agent-generated\n  permission question",
            self.browser_protocol,
        )
        self.assertIn(
            "Dispatch, recovery, correction messages, and replacement "
            "downloads",
            self.browser_protocol,
        )
        self.assertIn(
            "mandatory native confirmation control",
            self.browser_protocol,
        )

    def test_github_actions_do_not_create_new_permission_checkpoints(
        self,
    ) -> None:
        self.assertIn("## Authorization Closure", self.github_protocol)
        self.assertIn(
            "Creating the listed Issue, task branch, task-scoped commits, "
            "regular pushes,\n  Draft PR, and comments does not create "
            "separate approval checkpoints",
            self.github_protocol,
        )
        self.assertIn(
            "Additive correction commits, head updates by regular push",
            self.github_protocol,
        )
        self.assertIn(
            "perform the comment,\ncommit, regular push, artifact download, "
            "and revalidation without asking again",
            self.github_protocol,
        )

    def test_reconfirmation_is_limited_to_boundary_changes(self) -> None:
        for boundary in (
            "different\n  repository, account, or external destination",
            "expanded source exposure",
            "sensitive data",
            "product behavior",
            "acceptance criteria",
            "required\n  model",
            "unlisted, destructive, production",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, self.skill)
        self.assertIn(
            "correction rounds, same-scope regenerated bundles",
            self.skill,
        )
        self.assertIn(
            "do not require reconfirmation when already listed",
            self.skill,
        )

    def test_full_access_is_separate_from_contract_authority(self) -> None:
        self.assertIn(
            "host Full Access affects the local tool sandbox only",
            self.skill,
        )
        self.assertIn(
            "Full Access 只控制本机工具的文件系统和命令沙箱",
            self.readme,
        )
        self.assertIn(
            "产品或认证交接，不是重新确认契约",
            self.readme,
        )

    def test_native_connected_app_prompt_mode_is_explained(self) -> None:
        self.assertIn(
            "ChatGPT connected apps have their own user-configured prompt mode",
            self.skill,
        )
        self.assertIn("Settings > Apps", self.skill)
        self.assertIn("Settings > Apps", self.browser_protocol)
        self.assertIn("only ask before important changes", self.browser_protocol)
        self.assertIn(
            '"connected_app_permission_mode": '
            '"always-ask|before-changes|important-only|unknown"',
            self.browser_protocol,
        )
        self.assertIn("Settings > Apps", self.readme)
        self.assertIn(
            "Observed ChatGPT connected-app permission mode",
            self.final_evidence,
        )

    def test_ledger_and_final_report_audit_redundant_prompts(self) -> None:
        self.assertIn('"authorization_closure": {', self.browser_protocol)
        self.assertIn(
            '"redundant_agent_permission_prompts": 0',
            self.browser_protocol,
        )
        self.assertIn("## Authorization Closure", self.final_evidence)
        self.assertIn(
            "Agent-generated permission questions after confirmation: `0`",
            self.final_evidence,
        )


if __name__ == "__main__":
    unittest.main()
