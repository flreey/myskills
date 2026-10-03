---
name: meihua-reasoning
disable-model-invocation: true
description: "Use when the user asks to cast or interpret a Meihua Yishu hexagram, compare possible symbol mappings, or turn a divination reading into testable hypotheses. NOT for generic I Ching study, deterministic factual forecasting, or using divination alone for trading, medical, legal, or other high-stakes decisions."
---

# Meihua Reasoning

## Premises

- Scope: structured hypothesis generation and decision reflection, not supernatural or scientifically validated prediction.
- Casting methods: supplied hexagram, two-number, three-number, and Gregorian-time casting only.
- Calendar rule: Gregorian numbers; no silent lunar-calendar conversion.
- Changing-line rule: remainder `0` means line `6`; trigram remainder `0` means Kun (`8`).
- Language: respond in Chinese unless the user explicitly requests another language.
- Checked: 2026-07-20. Recheck the premises before adding another lineage, calendar convention, or casting method.

## First Reflex

Before casting, make the question scoreable. Obtain or state:

1. one decision or outcome;
2. a bounded time horizon;
3. the subject represented by the body trigram;
4. only the background known at casting time;
5. an observable success condition.

If the question is vague, narrow it once. If the user declines, continue as reflection but label the result `不可评分` rather than inventing precision.

Never choose the casting method or input numbers because they produce a convenient hexagram. Use the user's supplied method and data. If none are supplied, ask the user to choose one of the supported methods; do not manufacture an omen.

## Workflow

### 1. Freeze the input

Record the exact question, horizon, casting method, inputs, timezone, and known context before interpretation. Do not rewrite these after seeing the hexagram or later outcome.

For deterministic calculation, run `scripts/cast.py`. Do not calculate six lines, mutual hexagram, transformed hexagram, or body-use assignment from memory when the script can calculate them.

Supported commands are documented by `python3 scripts/cast.py --help`. If the user supplies an already cast hexagram, use `--upper`, `--lower`, and `--moving`.

### 2. Mechanical layer

Report only what follows from the frozen input:

- primary, mutual, and transformed hexagrams;
- upper and lower trigrams;
- moving line;
- body and function trigrams;
- five-element relation.

Treat the body-function relation as a traditional structural signal, never as an automatic verdict. `用克体` may suggest pressure on the subject; it does not mean “一定失败”.

If multiple or zero changing lines are supplied, do not invent a body-function rule. Mark body/function as `未定义` and explain that this skill's body-function convention covers exactly one changing line.

### 3. Candidate mapping layer

Read [references/symbol-mapping.md](references/symbol-mapping.md). For every important mapping, label its level:

- `A 经典原生象`;
- `B 现代稳定延伸`;
- `C 本次情境假设`.

Generate 2-4 plausible mappings for each decisive trigram or relation. Every candidate must include:

- mapped real-world object or role;
- why it fits the question;
- evidence against it;
- what observation would distinguish it from competitors.

Reject a candidate when it relies only on wordplay, hindsight, or an unobservable hidden cause. Never disguise a C-level hypothesis as ancient doctrine.

### 4. Competing-path layer

Build four paths from the surviving mappings:

1. main path;
2. strongest contrary path;
3. stage-transition path;
4. null path: the hexagram adds no reliable information beyond the known context.

Each path must use the same frozen input. Do not change the meaning of a trigram between paths without explicitly stating the alternative mapping.

Rank paths by coherence with the mechanical layer and discriminating observations. Do not rank by narrative fluency. If no path is materially stronger, say `无法区分`.

### 5. Reality check

Separate evidence known before interpretation from evidence fetched or supplied afterward. For current markets, laws, medicine, or other changing/high-stakes facts, verify through suitable current sources before using them.

The reality check may weaken or reject a symbolic path. It must not be used to retrofit the hexagram. Preserve the rejected path and state why it lost.

For a high-stakes choice, provide a conventional evidence-based analysis alongside the reading and state that the reading must not determine the action by itself.

### 6. Testable synthesis

Use [references/output-contract.md](references/output-contract.md). A valid conclusion contains:

- most-supported path and runner-up;
- bounded horizon;
- observable claim;
- verification events;
- invalidation events;
- confidence in the mapping, not a claim of supernatural probability;
- what evidence would change the ranking;
- safe next action.

Do not output unfalsifiable phrases such as “有波折但仍有机会”. Replace them with observable conditions or mark the claim `不可评分`.

## Interpretation Boundaries

- Do not claim that Meihua Yishu has validated predictive accuracy. A public 2026 experiment found a Meihua agent statistically indistinguishable from chance; see [references/sources.md](references/sources.md).
- Do not infer a precise price, date, diagnosis, legal result, or life event from symbolic language alone.
- Do not increase confidence because many symbolic associations can be made to fit.
- Do not use facts learned after the outcome as if they were available at casting time.
- Do not advise leverage, concentrated trading, stopping treatment, ignoring professional advice, or another irreversible action from a reading. Use ordinary risk controls and reversible tests instead.

## Compact Example

Question: “未来30天，项目能否取得首位付费用户？”

Good output does not jump from `坎为险` to “不能”. It may compare:

- A/B mapping: Kan as an uncertain or obstructed acquisition channel;
- C mapping: the current onboarding step is the specific bottleneck;
- contrary mapping: Kan as repeated contact or flow, suggesting that outreach volume matters more than product readiness;
- null path: the reading adds nothing beyond the known absence of qualified leads.

It then commits to an observable claim, such as “within 30 days, payment occurs only if at least five qualified users reach the onboarding step,” and invalidates that path if payment occurs without that condition or the condition is met without payment.

