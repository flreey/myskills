# Bootstrap Protocol (Mode A)

Use when the user starts a new domain/stack and does not know what skills they need ("我要开发一款 Cocos 游戏，都不知道需要哪些 skill").

**Core stance: do not enumerate skills upfront from imagination.** Half would cover what the model already knows; the other half would guess at pitfalls not yet hit. Instead: build ONE thin domain primer now, and let the rest grow via [harvest-protocol.md](harvest-protocol.md) as real friction appears. Tell the user this plan explicitly.

## Step 1 — Scope interview

Self-research first (read the project if it exists: manifests, engine version, target config). Then ask only what remains:

1. Exact tool/engine/framework **version** (the #1 source of agent errors in versioned ecosystems is training-data version mix-up)
2. **Target platform(s)** — each adds its own constraints (e.g. WeChat minigame: no DOM, size caps)
3. Greenfield or existing project?
4. What part of the workflow runs through a **GUI tool** the agent cannot operate (editor, designer, console)?
5. How does the user currently **verify** things work (build command, preview, device test)?

Do not ask about genre/features/architecture — the primer is about agent-environment fit, not product design.

**Then run the opportunity scan.** Most users can only name 2–3 kinds of skill because they don't know the other kinds exist (Anthropic's internal finding across hundreds of skills). Walk the user through this menu and ask which exist in their workflow:

library/API reference · product verification (how to prove a change works) · data fetching & analysis · business-process automation (recurring multi-step chores) · scaffolding & templates · code quality/review rules · CI/CD & deploy · runbooks (symptom → response) · infrastructure operations

Menu hits do NOT get built now — record them as a harvest watch-list in the primer's notes, unless one is an immediate recurring need the user confirms. The scan converts "unknown unknowns" into named candidates; the thin-primer stance still applies.

## Step 2 — Research the predictable failure modes

For the named stack and version, research (docs + known issues) specifically:

- Version fault lines: incompatible API generations the model is likely to mix up
- File types agents must not hand-edit (serialized/generated/GUI-owned files)
- What can only be done in the GUI vs. from code/CLI
- Platform hard limits (size, API availability, review policies) — mark policy numbers as re-check-before-quoting
- How an agent can self-verify without the GUI (type check, headless build, lint)

## Step 3 — Generate the primer skill

One thin skill, four skeleton sections — and nothing else:

1. **Version pins** — exact version, the API generation to use, how to detect it from the project (premises block doubles as this)
2. **Capability boundary** — agent can do / must hand to the user as an explicit GUI step list / must never touch
3. **Verification method** — the commands an agent runs to prove a change works without opening the GUI; what "cannot be verified here" looks like and how to say so
4. **Forbidden zones + recovery** — files/operations that corrupt state, each paired with the safe alternative, plus what to do if it already happened

Resist completeness. If a section is speculative ("they might use physics..."), cut it — harvest will add it the day it is actually needed. A primer over ~150 lines is probably padding.

All Iron Rules from the main skill apply (description, tool-agnostic body, premises).

## Step 4 — Validate

Run [validation-protocol.md](validation-protocol.md) (a primer is a knowledge skill → light A/B tier). Then set the growth loop: point harvest at the project's lessons.md and remind the user that corrections recurring twice become skill candidates.
