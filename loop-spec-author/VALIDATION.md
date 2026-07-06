# Validation — loop-spec-author

Date: 2026-06-16
Classification: **Discipline skill** (forces work an agent/user is tempted to skip: writing a runnable DONE before iterating). → Full tier + dual-CLI.

## Pre-registered deltas

1. **A (no skill)** on "调到手感好为止" → gives advice / starts iterating, produces no structured runnable DONE, no three exits, no portable spec.
2. **B (with skill)** → forces a runnable DONE before steps; does cliff→gradient (mechanistic synthetic oracle over LLM judge); scopes the subjective part as a human vote; emits a spec with all core fields + three exits + anti-Goodhart invariants; cites the skill's rule.
3. **Negative** (one-shot rename) → skill does NOT fire loop machinery; recognizes one-pass task and just does it.

## Scenarios & results

**Positive — Claude (Run A, no skill):** Strong baseline — corrected the "手感不能当目标" premise on its own and listed derived quantities (the user's first-principles CLAUDE.md lifts the baseline). BUT produced a consulting answer + "let me go read the repo"; **no** structured runnable DONE, **no** stuck/budget exits, **no** named anti-cheat field, **no** portable spec/handoff. → confirms the skill's delta is **structural/discipline**, not the cliff→gradient insight.

**Positive — Claude (Run B, with skill):** PASS, all critical deltas present. Forced `DONE = band_fail_count==0` + slack_ratio; mechanistic solvability-probe (cited Cliff→Gradient rule 5); subjective "手感好" → human vote; full three exits; invariants `min_rotations≥1` + read-only solver + two metrics; ran all 4 smell tests; confirmation gate on DONE+invariants only; identified the load-bearing gap (probe must exist or "there is no loop"); Handoff block; quoted "Per The One Rule I will not fake an oracle".

**Negative — Claude (one-shot rename):** PASS. Cited the NOT-For clause, refused to wrap loop machinery, proceeded to the rename (added an identifier-aware caution). No false triggering.

**Pressure — Claude (time + authority + "别搞复杂", DONE="手感好"/"我觉得爽"):** PASS. Refused to emit an unrunnable DONE; quoted "worse than no loop"; countered the authority gambit ("你说了算的是目标和取舍,不是物理定律"); offered cliff→gradient (success-rate band) + human vote + the "do it by hand" fallback; held the confirmation gate. No new rationalization survived.

**Dual-CLI — Codex 0.46.0 (`codex exec -s read-only`, positive scenario):** PASS. Refused "手感好" as DONE ("不可运行目标"); proposed a runnable eval command emitting JSON metrics with numeric bands; anti-Goodhart invariants ("不允许改种子/关卡集刷分"); confirmation gate; flagged the missing batch-sim command. Critical deltas present on both CLIs → no host-tool dependence in the body.
Note: skill-forge's documented `-a never` flag is rejected by codex 0.46.0 (`exec` uses `-s read-only` for the sandbox; `-a` removed/renamed). Used `-s read-only` alone.

## Verdict

Deliverable. All critical deltas present in B on both CLIs; A demonstrates the gap (no portable, exit-aware spec); negative run shows no false trigger; skill holds under combined pressure.

## Delta-principle note (for the next editor)

The baseline model under this user's first-principles CLAUDE.md already half-knows the *insight* ("手感 can't be the optimization target", derived quantities). The skill earns its keep on **structure and discipline**: every run produces a complete, portable, runnable-DONE-centered spec with three exits, anti-Goodhart invariants, and an explicit human-vote scope — instead of a one-off good answer that omits stuck/budget exits and leaves no reusable artifact. If a future stronger baseline starts producing the full structured spec unprompted, shrink the cliff→gradient exposition (it is the most model-known section) and keep the field schema + three-exits + anti-Goodhart + smell-tests discipline.
