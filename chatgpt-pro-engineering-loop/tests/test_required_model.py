from __future__ import annotations

import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class RequiredModelPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.model_gate = (
            SKILL_ROOT / "references" / "model-gate-protocol.md"
        ).read_text(encoding="utf-8")
        cls.browser = (
            SKILL_ROOT / "references" / "browser-and-recovery-protocol.md"
        ).read_text(encoding="utf-8")
        cls.contract = (
            SKILL_ROOT / "references" / "execution-contract-template.md"
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

    def test_exact_underlying_model_and_no_fallback_are_mandatory(self) -> None:
        for document in (
            self.skill,
            self.model_gate,
            self.contract,
            self.brief,
            self.final,
            self.readme,
            self.metadata,
        ):
            with self.subTest(document=document[:40]):
                self.assertIn("GPT-5.6 Sol Pro", document)

        self.assertIn("Fallback allowed: `false`", self.model_gate)
        self.assertIn("Model fallback allowed: `false`", self.contract)
        self.assertIn("Model fallback allowed: `false`", self.brief)
        self.assertIn("Fallback allowed: `false`", self.final)
        self.assertIn('"fallback_allowed": false', self.browser)

    def test_model_gate_precedes_transport_and_github_mutation(self) -> None:
        model_phase = self.skill.index(
            "## Phase 2 — Pass The Model And Secret Gates"
        )
        transport_phase = self.skill.index(
            "## Phase 3 — Select The Fast Transport"
        )
        github_phase = self.skill.index(
            "## Phase 4 — Establish The GitHub Task"
        )
        dispatch_phase = self.skill.index(
            "## Phase 6 — Dispatch The Engineering Brief Once"
        )
        self.assertLess(model_phase, transport_phase)
        self.assertLess(model_phase, github_phase)
        self.assertLess(model_phase, dispatch_phase)
        self.assertIn(
            "Before creating a task branch, packaging source, mentioning the repository",
            " ".join(self.skill.split()),
        )

    def test_stable_conversation_url_is_recorded_after_dispatch(self) -> None:
        self.assertIn("stable conversation URL", self.skill)
        self.assertIn(
            "do not invent a stable conversation URL", self.model_gate
        )
        self.assertIn('"conversation_url": null', self.model_gate)
        self.assertIn('"url": null', self.browser)
        self.assertIn("Save the stable conversation URL", self.browser)

    def test_picker_policy_accepts_only_documented_pro_mapping(self) -> None:
        compact = " ".join(self.model_gate.split())
        for label in ("Pro Extended", "Pro Standard", "`Pro`"):
            with self.subTest(label=label):
                self.assertIn(label, self.model_gate)

        self.assertIn(
            "only when the current documentation still maps the visible choice "
            "to `GPT-5.6 Sol Pro`",
            compact,
        )
        for rejected in (
            "`5.6 Sol Light`",
            "Medium, High, or Extra High",
            "Work with `5.6 Sol Extra High`",
            "Instant",
            "Terra, Luna",
            "ambiguous",
        ):
            with self.subTest(rejected=rejected):
                self.assertIn(rejected, self.model_gate)

    def test_account_tier_and_nearby_models_are_not_evidence(self) -> None:
        self.assertIn("Account tier alone is not evidence.", self.model_gate)
        self.assertIn(
            "A generic GPT-5.6 label alone is not evidence.", self.model_gate
        )
        self.assertIn("A Pro account\nbadge", self.skill)
        self.assertIn("Medium, High, Extra High", self.skill)

    def test_recovery_requires_a_fresh_model_check(self) -> None:
        for event in (
            "after reconnecting or reopening the saved conversation",
            "after creating a replacement conversation",
            "before sending a continuation after context recovery",
            "whenever the picker label changes",
        ):
            with self.subTest(event=event):
                self.assertIn(event, self.model_gate)
        self.assertIn("rerun the model gate", self.browser)

    def test_model_evidence_is_preserved(self) -> None:
        for field in (
            '"required": "GPT-5.6 Sol Pro"',
            '"surface"',
            '"picker_label"',
            '"mapped_underlying_model"',
            '"official_mapping_url"',
            '"verified_at"',
            '"result"',
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.browser)
        self.assertIn("External Conversation And Model", self.final)
        self.assertIn(
            "Model verification time and official mapping source", self.brief
        )


if __name__ == "__main__":
    unittest.main()
