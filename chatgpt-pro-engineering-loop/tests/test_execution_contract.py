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
        cls.browser = (
            SKILL_ROOT / "references" / "browser-and-recovery-protocol.md"
        ).read_text(encoding="utf-8")
        cls.github = (
            SKILL_ROOT
            / "references"
            / "github-manager-developer-protocol.md"
        ).read_text(encoding="utf-8")
        cls.secrets = (
            SKILL_ROOT / "references" / "secrets-and-live-validation.md"
        ).read_text(encoding="utf-8")
        cls.brief = (
            SKILL_ROOT / "references" / "task-brief-template.md"
        ).read_text(encoding="utf-8")
        cls.final = (
            SKILL_ROOT / "references" / "final-evidence-template.md"
        ).read_text(encoding="utf-8")
        cls.readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        cls.metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

    def test_contract_confirmation_precedes_mutating_workflow(self) -> None:
        contract_phase = self.skill.index("## Phase 0 — Draft One Execution Contract")
        local_phase = self.skill.index("## Phase 1 — Establish Local Truth")
        github_phase = self.skill.index("## Phase 4 — Establish The GitHub Task")
        self.assertLess(contract_phase, local_phase)
        self.assertLess(local_phase, github_phase)

    def test_minimal_requirement_is_enough(self) -> None:
        self.assertIn("A concrete one-sentence requirement is enough.", self.skill)
        self.assertIn("infer ordinary\nacceptance criteria", self.skill)
        self.assertIn("<填写需求>", self.metadata)
        self.assertIn("等我确认后执行", self.metadata)

    def test_negative_trigger_stays_local(self) -> None:
        for excluded_case in (
            "ordinary local implementation or debugging",
            "a small second-opinion review",
            "generic web research",
            "browser login by itself",
            "work that forbids external source access",
        ):
            with self.subTest(excluded_case=excluded_case):
                self.assertIn(excluded_case, self.skill)

    def test_contract_is_compact_and_complete(self) -> None:
        rendered = self.template[self.template.index("## Goal And Scope") :]
        line_count = len(rendered.splitlines())
        self.assertGreaterEqual(line_count, 20)
        self.assertLessEqual(line_count, 35)
        for heading in (
            "## Goal And Scope",
            "## Acceptance And Verification",
            "## Transport, Actors, And Authority",
            "## Secret And Production Boundary",
            "## Confirmation",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.template)

    def test_one_confirmation_creates_authorization_closure(self) -> None:
        self.assertIn("authorization closure", self.skill)
        self.assertIn(
            "does not ask again before the listed branch, commit, Draft PR",
            self.skill,
        )
        self.assertIn(
            "One confirmation activates the task-scoped authorization closure",
            self.template,
        )
        self.assertIn(
            "Native authentication and connected-app approvals remain user",
            self.template,
        )

    def test_manager_developer_split_is_consistent(self) -> None:
        for document in (self.skill, self.github, self.brief, self.readme, self.metadata):
            with self.subTest(document=document[:30]):
                self.assertIn("Codex", document)
                self.assertIn("ChatGPT Pro", document)

        self.assertIn(
            "Codex creates `codex/chatgpt-pro/<task-id>`", self.skill
        )
        self.assertIn(
            "ChatGPT Pro reads and commits only to that assigned branch",
            self.skill,
        )
        self.assertIn(
            "after the first valid Pro commit, Codex creates the Draft PR",
            self.skill,
        )
        self.assertIn("does not create an Issue by default", self.skill)

    def test_native_prompt_is_user_handoff_not_reconfirmation(self) -> None:
        self.assertIn(
            "mandatory native ChatGPT/GitHub confirmation is a user handoff",
            self.browser,
        )
        self.assertIn("Allow GitHub for this conversation", self.browser)
        self.assertIn("Do not choose `Always allow`", self.browser)
        self.assertIn("Full Access", self.skill)
        self.assertIn("原生确认", self.readme)

    def test_secret_classes_and_value_boundary_are_present(self) -> None:
        for classification in (
            "`none`",
            "`interface-only`",
            "`local-test`",
            "`ci-test`",
            "`production`",
        ):
            with self.subTest(classification=classification):
                self.assertIn(classification, self.secrets)

        for document in (self.skill, self.template, self.brief, self.final, self.readme):
            with self.subTest(document=document[:30]):
                self.assertIn("secret", document.lower())

        self.assertIn("Secret values never enter", self.secrets)
        self.assertIn("ChatGPT messages or attachments", self.secrets)
        self.assertIn("require a new execution contract", self.secrets)

    def test_credentialed_execution_requires_diff_review(self) -> None:
        self.assertIn(
            "review the complete executable diff before injection", self.secrets
        )
        self.assertIn(
            "A same-repository branch is not automatically trusted", self.secrets
        )
        self.assertIn(
            "Before any test receives `local-test` or `ci-test` credentials",
            self.skill,
        )

    def test_github_issue_is_not_mandatory(self) -> None:
        self.assertIn("Issue 默认不创建", self.readme)
        self.assertIn("does not create an Issue by default", self.github)
        self.assertNotIn("create one task Issue", self.template)

    def test_final_evidence_separates_states(self) -> None:
        for state in (
            "Local modifications:",
            "Local commit:",
            "Remote task branch and pushed commits:",
            "Draft PR:",
            "Merged:",
            "Deployed:",
            "Production verified:",
        ):
            with self.subTest(state=state):
                self.assertIn(state, self.final)


if __name__ == "__main__":
    unittest.main()
