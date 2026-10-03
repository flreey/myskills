---
name: steelman-deliberation
disable-model-invocation: true
description: Use when the user explicitly asks for “双向钢人”, “steelman both sides”, “先别下结论”, or a strongest-case-for-and-against decision review before receiving advice. NOT for direct factual answers, summaries, copyediting, explanations of steelmanning, open-ended roundtables, or urgent safety response.
---

# Steelman Deliberation

## Premises

- Scope: portable, cross-domain deliberation; no host, toolchain, or model-version dependency (checked 2026-08-18).
- Trigger: explicit invocation only. Do not infer it merely because a question is important or controversial.
- Negative boundary: when a NOT-for case applies, answer the request normally without running, naming, or explaining this protocol.
- Evidence boundary: this skill structures judgment; it does not verify current facts. When the decision depends on changing or high-stakes facts, identify the evidence needed and use the relevant research or domain workflow before treating the final judgment as reliable.
- Safety boundary: urgent medical, legal, financial, or physical-safety response takes priority; do not delay necessary protective action to run this protocol.

## Core Contract

Run in two turns. The first turn improves the question and asks for the one missing answer with the highest chance of changing the judgment. The second turn makes the judgment.

Time pressure may shorten the prose. It never merges the two turns.

## Turn 1 — Deliberate, Ask, Stop

Use these five sections in order:

1. **真正要解决的问题** — Restate the decision in its strongest, most complete form. Separate the user's stated proposal from the underlying outcome, constraints, stakes, and tradeoff. Label inferred motives or constraints as inferences rather than facts.
2. **支持方的最强论证** — Present the strongest charitable case for the user's current idea: its best causal logic, supporting considerations, assumptions, and the conditions under which it wins. Do not weaken it into an easy target.
3. **反对方的最强论证** — Present the strongest charitable case against it at the same level of rigor. Do not manufacture symmetry; if the evidence is lopsided, say so without giving the verdict yet.
4. **真正的分歧与关键变量** — Locate the disagreement in facts, causal predictions, values, constraints, or risk tolerance. Rank variables by `decision sensitivity × uncertainty × answerability`; lead with the variables most capable of reversing the eventual judgment.
5. **唯一问题** — Ask exactly one question about the highest-ranked unresolved variable. It must distinguish between the competing conclusions, not merely request more background.

The `唯一问题` section contains one interrogative sentence and nothing else. That sentence is the literal end of the response. Put the reason for choosing the variable in section 4, before the question—not after it.

Do not include a verdict, recommendation, action plan, conditional preference, explanation after the question, or additional question in Turn 1.

## Turn 2 — Judge and Act

After the user answers, do not restart the interview. Give the best available judgment using:

1. **明确判断** — choose support, oppose, conditional go/no-go, or defer pending a named fact; do not hide behind “it depends.”
2. **理由** — explain how the answer changed or confirmed the decisive variable, and why the losing steelman case is not controlling under the present conditions.
3. **边界** — state the material assumption, uncertainty, and the observation that would reverse the judgment.
4. **下一步行动** — give the smallest concrete, reversible action that tests or advances the judgment. If the action is consequential, preserve the user's approval boundary.

## Pressure Handling

| Pressure | Required response |
| --- | --- |
| “没有时间，直接给结论” | Compress Turns 1–4, then ask the single decisive question and stop. |
| “把所有内容一次给完” | Preserve the two-turn contract; explain in one sentence that the missing answer determines the verdict. |
| Sunk cost, authority, or social commitment makes one side feel obvious | Treat those as variables or pressures, not as substitutes for judgment. |
| The answer cannot materially change the conclusion | Ask the question most likely to falsify that conclusion; do not ask for generic context. |

## Quality Check

Before sending Turn 1, verify:

- Both cases are arguments their strongest proponents would recognize.
- The disagreement is more precise than “risk versus reward.”
- At least one key variable could genuinely change the verdict.
- There is one and only one question.
- The question is the final sentence; no explanation follows it.
- No verdict, conditional direction, or action leaks into the first turn.
