# AGENTS.md

## Prompt Builder usage

When the user gives a vague, short, casual, or incomplete request and wants to turn it into a useful prompt, use the local skill in:

`prompt-builder-agent-skill/SKILL.md`

Follow its workflow:

1. Classify the task type.
2. Restate the likely goal.
3. Ask up to 3 guided questions.
4. Use defaults when the user is unsure.
5. Produce a copy-ready final prompt with goal, context, inputs, outputs, constraints, structure, key mechanism, quality bar, avoid list, and acceptance criteria.

Do not ask too many open-ended questions. Prefer choices.
