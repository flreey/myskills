# AGENTS.md

## System Evolution Skill usage

When the user has a complex, unclear, strategic, or recurring problem and wants system-level analysis (not shallow advice), use the local skill in:

`system-evolution-skill/SKILL.md`

Use it for: product validation, customer acquisition, paid tools, startup decisions, trading or strategy research, learning systems, workflow/process design, business process improvement, AI agent or automation design, and recurring personal decision-making.

Do NOT use it for:
- Simple factual questions.
- Copy-ready LLM prompts → use `prompt-builder/SKILL.md`.
- Engineering implementation plans / specs / code changes → use brainstorming-style skills.

Workflow:

1. Classify the problem type (product / growth / trading / learning / workflow / agent).
2. Define the system boundary before giving any advice.
3. Separate facts, assumptions, hypotheses, inferences, and advice — never mix.
4. Walk through the 10 required output sections in `SKILL.md` (Problem Restatement → Practical Next Step).
5. Prefer one small measurable experiment over a large plan.
6. Be direct, critical, and practical. Do not assume the user's idea is good; evaluate it as a system.

Supporting assets — load only when relevant:

- `templates/system-map.md` — reusable system map artifact.
- `templates/feedback-loop.md` — explicit feedback metrics and decision rules.
- `templates/experiment-plan.md` — smallest useful experiment written as a plan.
- `templates/failure-diagnosis.md` — when the user brings observed failure data.
- `templates/evolution-roadmap.md` — when the user has feedback and needs the next iteration.
- `examples/` — compressed few-shot anchors for similar problem types; not the required full output format.
- `bin/system-skill.sh` — only when the user asks for a pasteable prompt wrapper.
