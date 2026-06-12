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
