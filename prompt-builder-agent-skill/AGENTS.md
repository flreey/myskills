# AGENTS.md

## Prompt Builder usage

When the user gives a vague, short, casual, or incomplete request and wants help turning it into a useful prompt, use the local skill in:

`prompt-builder-agent-skill/SKILL.md`

Workflow:

1. Classify the task type (image / product / writing / code / business / research / agent / general).
2. Restate the likely goal in plain language.
3. Ask up to 3 guided multiple-choice questions; always include "Not sure, choose for me."
4. Use defaults when the user is unsure.
5. Draft a prompt using the universal structure (Goal / Context / Audience / Inputs / Outputs / Constraints / Structure / Mechanism / Quality bar / Avoid / Acceptance criteria).
6. Self-critique on three axes (specificity / actionability / robustness, 1-5 each); fix anything below 4 inline.
7. Adapt to the target model (Claude → XML tags + cache-friendly ordering; GPT → markdown; portable by default).
8. Deliver the final prompt as a single copy-ready fenced block.

Reference templates per type live under `references/templates/<type>.md` — load the relevant one as a few-shot anchor when drafting.

Do not ask too many open-ended questions. Prefer choices. Do not skip the self-critique step.
