# Validation Record — skill-forge

Method: RED-GREEN-REFACTOR per superpowers:writing-skills, applied to skill-forge itself.

## 2026-06-12 — initial release

**Scenarios** (identical prompts for baseline and with-skill runs):
- A (forge): "turn this incident into a skill — agent hand-edited .prefab uuid in a Cocos Creator project, corrupted all asset references"
- B (bootstrap): "starting a Cocos Creator 3.8 + WeChat minigame project, build me a skill so agents avoid the pitfalls"

**Pre-registered deltas**: interview gate holds (questions asked / assumptions surfaced, vs zero questions); search-before-build performed; placement triage performed (hook/CLAUDE.md routing); no delivery without validation; description trigger-only; tool-agnostic body; premises block present.

**RED (baseline, no skill)**: both runs delivered a finished SKILL.md with zero questions. A: 2.x/3.x version mix-up from not asking; description 700+ chars containing rule summary; suggested a hook but kept everything in the skill anyway. B: speculative coverage (physics/payments/leaderboards unasked); verbatim rationalization "这些是文档和社区反复验证过的坑" used to skip validation. Full notes: repo tasks/baseline-notes.md.

**GREEN (with skill)**: all pre-registered deltas hit in both scenarios. A: searched GitHub (3 repos found, no-fit verdict reasoned), triaged uuid-check to hooks, surfaced assumptions table, ran its own A/B against a fake project (no-skill codex emitted a perl uuid-rewrite one-liner; with-skill codex and claude 4/4). B: thin primer with harvest growth plan, ran its own light A/B + codex smoke, shrank model-known API table per delta principle, fixed a real trigger gap (Chinese keywords).

**Codex smoke (skill-forge itself)**: `codex exec -s read-only` reading SKILL.md — stopped at the interview gate, refused to generate, asked the 6 interview questions; self-researched local projects first; honest about restricted network; raised single-project-vs-skill boundary. Pass.

**REFACTOR**: codified the observed non-interactive fallback into forge-protocol Step 2 (assumptions table with "which answer changes what"; silently assuming is the violation).

**Known limitation**: with-skill test agents had the superpowers plugin in context (same as baseline, so the comparison is controlled), but compliance on a bare environment without superpowers is untested.

## 2026-06-12 — edit round: negative scenarios, degrees-of-freedom, opportunity scan

**Edits under test** (sourced from Anthropic internal-practice research): validation-protocol light tier gains a mandatory negative (should-NOT-trigger) scenario; forge-protocol Step 3 gains degrees-of-freedom matching (fragile deterministic procedures → `scripts/`); bootstrap-protocol Step 1 gains the 9-category opportunity scan (menu → harvest watch-list, no upfront building).

**Pre-registered deltas**: A-run validation plan includes an executed negative scenario; A-run weighs script vs prose for the recovery procedure; B-run presents the opportunity scan with watch-list framing; thin-primer stance retained.

**Result: PASS — all deltas hit on re-runs of both original scenarios.**
- A: negative scenario (same project, .ts edit) pre-registered and executed, no false blocking; recovery steps explicitly triaged per degrees-of-freedom (verdict: judgment steps stay prose, git-restore steps optional script — reasoning, not just compliance). Bonus: its own full-tier loop caught Codex treating the exception clause as an authorization checklist; fixed via two-step informed consent + rationalization table, re-passed on both CLIs.
- B: negative scenario (pure TS utility) executed clean; opportunity-scan menu surfaced with candidates recorded as harvest watch-list, primer stayed thin. Its validation also caught and fixed a "user said it's fine" bypass in Codex.

**Side findings**: claude CLI 2.0.64 headless + tool calls → API 400 `tool_use ids must be unique` (fixed in 2.1.173); validation runs should use a current CLI.

## 2026-06-12 — edit round: artifact placement rules

**Edits under test**: forge-protocol Step 3 gains artifact placement (premises-driven: project-pinned → project skills dir; cross-project → skills repo + symlink to both global dirs; one-layer-only rule; promotion path). bootstrap-protocol Step 3 gains primer placement (project dir by construction, pollution rationale).

**Pre-registered delta**: deliverable states the save path WITH the reason; scenario A expected to choose the cross-project branch, scenario B the project-level branch.

**Result: PASS — both scenarios hit the correct branch.** A: repo path + symlink both globals, reason "engine-level, applies to all of the user's Cocos projects", plus explicit "do not also copy into project layer". B: project skills dir, reason "premises pin this project; global placement pollutes unrelated sessions' prompts". Cost-constrained runs (told to reuse prior validation) stayed honest on both sides: pre-registered the deltas their generated skills still need and declared them not-done until run — no fabricated validation claims. Bonus: A's self-research found an overlapping rule in an existing user skill and proposed pointer-based dedup unprompted (harvest hygiene surfacing in forge mode).
