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
        cls.final_evidence = (
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
            self.final_evidence,
            self.readme,
            self.metadata,
        ):
            with self.subTest(document=document[:40]):
                self.assertIn("GPT-5.6 Sol Pro", document)

        self.assertIn("Fallback allowed: `false`", self.model_gate)
        self.assertIn("Model fallback allowed: `false`", self.contract)
        self.assertIn("Model fallback allowed: `false`", self.brief)
        self.assertIn("Fallback allowed: `false`", self.final_evidence)
        self.assertIn("fallback_allowed", self.browser)
        self.assertIn('"fallback_allowed": false', self.browser)

    def test_model_gate_precedes_transport_and_source_handoff(self) -> None:
        compact_skill = " ".join(self.skill.split())
        model_gate_phase = self.skill.index(
            "## Phase 2A — Open Conversations And Pass The Model Gate"
        )
        transport_phase = self.skill.index("## Phase 3 — Select The Transport")
        bundle_phase = self.skill.index("## Phase 4 — Prepare A Safe Bundle Handoff")
        dispatch_phase = self.skill.index(
            "## Phase 6 — Dispatch Once And Preserve Recovery State"
        )

        self.assertLess(model_gate_phase, transport_phase)
        self.assertLess(model_gate_phase, bundle_phase)
        self.assertLess(model_gate_phase, dispatch_phase)
        self.assertIn(
            "Create no Issue, branch, commit, push, Draft PR, source archive, "
            "upload, or task message",
            compact_skill,
        )

    def test_stable_conversation_url_is_recorded_only_after_dispatch(self) -> None:
        self.assertIn("record `conversation_url: null`", self.skill)
        self.assertIn(
            "do not invent a stable conversation URL", self.model_gate
        )
        self.assertIn('"conversation_url": null', self.model_gate)
        self.assertIn('"url": null', self.browser)
        self.assertIn(
            "Wait for the resulting stable conversation URL and save it immediately.",
            self.browser,
        )
        self.assertIn(
            "wait for the resulting stable conversation URL and save it immediately",
            self.skill,
        )

    def test_picker_policy_accepts_only_documented_pro_mapping(self) -> None:
        compact_model_gate = " ".join(self.model_gate.split())
        for label in ("Pro Extended", "Pro Standard", "`Pro`"):
            with self.subTest(label=label):
                self.assertIn(label, self.model_gate)

        self.assertIn(
            "only when the current documentation still maps the visible "
            "choice to `GPT-5.6 Sol Pro`",
            compact_model_gate,
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

        self.assertIn(
            "If the current surface lacks an eligible Pro choice but another visible "
            "surface offers one, switch to the eligible surface",
            " ".join(self.model_gate.split()),
        )
        self.assertIn(
            "A Work surface showing Extra High must yield to an eligible "
            "Chat surface showing Pro",
            " ".join(self.skill.split()),
        )

    def test_account_tier_and_nearby_model_are_not_evidence(self) -> None:
        self.assertIn("Account tier alone is not evidence.", self.model_gate)
        self.assertIn(
            "A generic GPT-5.6 label alone is not evidence.", self.model_gate
        )
        self.assertIn(
            "The account says Pro, so the conversation must be using the Pro model.",
            self.skill,
        )
        self.assertIn(
            "Extra High or Sol Light is still GPT-5.6, so it is close enough.",
            self.skill,
        )

    def test_recovery_requires_a_fresh_model_check(self) -> None:
        for event in (
            "after reconnecting or reopening the saved conversation",
            "after creating a replacement conversation",
            "before sending a continuation after context recovery",
            "whenever the picker label changes",
        ):
            with self.subTest(event=event):
                self.assertIn(event, self.model_gate)

        self.assertIn(
            "rerun the model gate; stop without sending a continuation if it fails",
            self.browser,
        )

    def test_model_evidence_is_carried_through_the_run(self) -> None:
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

        self.assertIn("## External Model Gate", self.final_evidence)
        self.assertIn("Model verification time and official mapping source", self.brief)
        self.assertIn("Required-model failure behavior", self.contract)


if __name__ == "__main__":
    unittest.main()
