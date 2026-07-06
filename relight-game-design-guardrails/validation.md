# Validation Notes

## 2026-06-12 forge validation

Skill type: mixed knowledge/discipline. The discipline pressure is "ship novelty fast by adding mechanics or larger boards"; validation uses light A/B plus pressure checks.

Pre-registered expected deltas:

1. For a "connecting for its own sake" prompt, with-skill output must begin by asking what player meaning appears after connection, not by listing mechanics.
2. With-skill output must reject "bigger boards / more rules" as sufficient novelty and propose meaning-return categories.
3. With-skill output must require one dominant chapter lesson and 12-level star-chart/page alignment when discussing chapters.
4. With-skill output must produce a concrete pre-design guardrail check before implementation.
5. Negative task such as a bug fix or small visual polish must not be blocked by this skill.

Positive scenario:

> In `/Users/flreey/Projects/cocos/Relight`, the user says the game feels like connecting for its own sake. Propose the next gameplay/chapter direction before implementation.

Pressure scenario:

> The user wants fast novelty for the next Relight chapter and suggests portals, locks, black holes, and larger 8x8 boards. Decide what to do.

Negative scenario:

> In `/Users/flreey/Projects/cocos/Relight`, fix a Cocos HUD overlap bug on the level screen.

Result summary:

- Search-before-build found broad public game-development/game-design skills, but no 80% fit for Relight's star-chart connection-meaning problem.
- Codex validation should compare baseline vs with-skill for positive and pressure scenarios, then run the negative scenario with-skill.

Executed checks:

- Baseline positive output proposed a plausible new chapter around "Resonance Alignment" and cited existing color/bonus-core affordances, but it did not require a guardrail check or explicitly reject novelty-for-novelty's-sake before proposing content.
- With-skill positive output reframed the issue as missing "connection meaning return", produced a full Guardrail Check, rejected portals/black holes/locks/timers/8x8, and proposed "Constellation Trace" as a chapter where solved paths become visible constellation strokes.
- With-skill pressure output rejected portals, black holes, and 8x8 as the next v1 chapter direction, allowed locks only as small support, and chose "Twin Star Prism" / existing color-splitter-bonus-core depth as the lower-risk path.
- With-skill negative output correctly said this skill should not lead a HUD overlap bug; it routed the task to view/layout delivery, kept pure game logic out of scope, and proposed browser verification after implementation.

Verdict:

- PASS for trigger precision: planning/gameplay prompts load useful constraints; a HUD bug is not over-captured.
- PASS for behavioral delta: with-skill output consistently starts from player meaning and scope discipline instead of feature lists.
- PASS for Relight specificity: outputs reference star-chart restoration, 12-level chapter rhythm, existing color/splitter/bonus-core systems, and browser-facing payoff.

Limitations:

- Validation was Codex-only. Claude smoke was not run because the local Claude launcher previously failed with `exec: node: not found`.
- No files in `/Users/flreey/Projects/cocos/Relight` were modified during validation.
