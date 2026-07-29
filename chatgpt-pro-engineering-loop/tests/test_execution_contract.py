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
            "operation authority creates a new contract version and requires\n"
            "  reconfirmation",
            self.skill,
        )
        self.assertIn(
            "Confirmation authorizes only the operations listed above.",
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


if __name__ == "__main__":
    unittest.main()
