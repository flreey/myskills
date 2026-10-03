# Validation Record

## Pre-registration — 2026-07-20

Classification: mixed knowledge/discipline skill. The interpretation constraints resist a model's tendency to jump to a fluent single-story reading, so the discipline behavior is treated as critical.

Positive scenario:

> 我在做一个面向海外独立开发者的小工具，目前还没有付费用户。我想用数字23和41按梅花易数看看：未来30天能不能获得第一个付费用户？直接给我判断。

Negative scenario:

> 介绍一下邵雍“以物观物”的思想，并和普通的主观观察做个简短比较。

Expected critical deltas:

1. The skilled run freezes the question, 30-day horizon, observable first-payment condition, method, and inputs before interpretation.
2. It uses the deterministic script result rather than silently inventing or hand-waving the cast.
3. It separates A/B/C mapping levels and gives support, objection, and a discriminator for decisive mappings.
4. It presents main, contrary, stage-transition, and null paths instead of one fluent verdict.
5. It ends with a bounded claim plus verification and invalidation events, and frames the reading as a symbolic hypothesis.

Negative-run expectation: answer the philosophy question directly, with no casting intake, four-path framework, or divination warning detour.

Results are appended below after fresh-session runs.

## Results — 2026-07-20

### Codex A/B

- Baseline A gave a fluent single verdict: `倾向“能”`, followed by one narrative. It did not freeze an observable success contract, separate mapping levels, provide objections/discriminators, retain four competing paths, or specify a proper null model.
- Skilled B read the skill and references, then ran `scripts/cast.py two 23 41`. It froze the question and success condition, reported the deterministic cast, separated A/B/C mappings with objections and signals, retained all four paths, and ended with verification/invalidation conditions and a symbolic-hypothesis boundary.
- All five pre-registered critical deltas passed.

### Negative trigger

The skilled negative run answered “以物观物” directly. It did not request casting data, produce candidate mappings, invoke four paths, or add a divination warning. Negative trigger passed.

### Trigger wording

- Positive wording contains `梅花易数`, `数字`, a bounded horizon, and a requested judgment, matching the description.
- Negative wording is a philosophy explanation request and contains none of the casting/interpretation trigger language. The `NOT for generic I Ching study` boundary reinforces non-triggering.

### Deterministic checks

- `python3 -m unittest discover -s meihua-reasoning/tests -v`: 6/6 passed.
- Coverage includes remainder-zero rules, two/three-number casts, Gregorian-time determinism, a known primary/mutual/transformed result, body-function relation, and unique names for all 64 upper/lower combinations.
- Frontmatter parsed successfully; description starts with `Use when` and is 310 characters.

### Dual-CLI status

- Codex CLI 0.145.0-alpha.18: passed positive A/B and negative smoke runs.
- Claude Code 2.0.30: blocked before model execution by `401 Invalid authentication credentials; Please run /login` in all three fresh-session attempts.

Overall status: **Codex validated; Claude compatibility pending authentication**. Do not call the skill fully dual-CLI validated until the Claude smoke run succeeds.
