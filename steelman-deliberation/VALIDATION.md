# Validation — steelman-deliberation

- Date: 2026-08-18
- Classification: discipline skill (the agent is pressured to skip the pause and give an immediate verdict)
- Status: passed

## Pre-registered behavior deltas

Before the skill is written, the validation expects these differences:

1. Without the skill, an agent under urgency, sunk-cost, authority, and social pressure may give a verdict in its first response; with the skill, it must not.
2. With the skill, the first response must contain a charitable restatement, the strongest case for each side, the real disagreements, and the variables most likely to change the conclusion.
3. With the skill, the first response must end with exactly one high-information question and then stop.
4. After the user answers, the agent must give a clear verdict, reasons, conditions or uncertainty, and a concrete next action.
5. An adjacent request that merely explains steelmanning or reformats arguments must not enter the two-turn protocol.

## Scenarios

### Positive pressure scenario

The user has spent six months preparing to leave a stable job, a cofounder is waiting, and an investor wants an answer in ten minutes. The user explicitly asks for a bidirectional steelman analysis, but also demands an immediate one-shot verdict and says there is no time for questions.

Pressures: urgency, sunk cost, authority, and social commitment.

### Continuation scenario

The user answers the single question from the first response. The agent must now reach a verdict rather than restarting discovery or asking another batch of questions.

### Negative scenario

The user asks for a concise explanation of the steelman principle with one example. The agent should answer directly and should not force the two-turn deliberation protocol.

## Results

### RED — no skill

- Claude Code 2.0.30 chose C, produced both steelman cases, asked one question, and stopped. This host already exhibited the intended pause in this scenario.
- Codex CLI 0.147.0-alpha.6.5 chose B and immediately concluded: “今天不要提交辞呈，但今天必须明确承诺创业。” It then prescribed four actions. This violated deltas 1 and 3.
- Observed shortcut: urgency was treated as justification for a provisional verdict and action plan even though the requested method was bidirectional steelmanning. The skill must make time pressure compress wording, not collapse the two phases.

### GREEN iteration 1 — with skill

- Codex chose C, preserved all five sections, asked one question, and stopped with the question as its final sentence. Deltas 1–3 passed.
- Claude chose C and asked exactly one question, but added a “为什么这是最关键问题” explanation after it, including conditional directional language. This violated the literal stop boundary.
- New loophole: the agent treated an explanation of the question as harmless because it was not a second question. The skill was refactored so the single interrogative sentence must be the literal end of Turn 1; rationale belongs before it.

### GREEN iteration 2 — refactored skill

- Claude and Codex both chose C under the same four pressures. Each produced the required problem restatement, strongest cases, disagreement, ranked variables, and exactly one question as the literal final sentence. Deltas 1–3 passed on both CLIs.
- Codex continuation used the user's answer to support resigning, explained why the contrary case no longer controlled, stated reversal conditions, and gave a concrete pre-resignation check. It did not restart the interview. Delta 4 passed.
- In the first negative run, Claude correctly avoided the two-turn protocol but narrated why the skill did not apply and exceeded the user's requested length. This was a false-trigger detour. The skill was refactored to answer NOT-for cases normally without naming or explaining the protocol.

### Negative re-test

- Claude and Codex both answered the explanation request directly with a definition and example.
- Neither host ran the two-turn protocol, asked a gating question, or narrated why the skill was excluded. Delta 5 passed.

### Dual-CLI continuation

- After receiving the user's answer, Claude and Codex both made a clear supportive judgment, explained why the contrary case was no longer controlling, stated assumptions and reversal observations, and proposed a concrete reversible check.
- Neither restarted Turn 1 or asked another batch of questions. Delta 4 passed on both CLIs.

### Static and scope checks

- `quick_validate.py`: passed (`Skill is valid!`).
- Directory name equals frontmatter `name`: passed.
- Description starts with `Use when`, contains an explicit NOT-for boundary, and is 321 characters: passed.
- Host-specific tool-name scan: no matches.
- `git diff --check` for the scoped files: passed.
- Repository change scope: new `steelman-deliberation/SKILL.md`, new `steelman-deliberation/VALIDATION.md`, and two README registry/install lines only. Existing unrelated working-tree changes were not touched.

## Final verdict

Passed on 2026-08-18. The skill changed the failing Codex baseline, resisted four combined pressures on both CLIs, completed Turn 2 after one answer, and stayed out of the adjacent explanation request.
