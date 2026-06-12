# Forge Protocol (Mode B)

Use when the user knows what skill they want: a lesson, incident, recurring task, or domain practice to encode. Follow steps in order. Steps 0, 2 and 5 are gates — do not skip, do not reorder.

## Step 0 — Search before build (gate)

Search for existing skills covering this topic before writing anything:

- GitHub: `<topic> SKILL.md`, `<topic> claude skill`, `awesome claude skills`
- The user's installed skills and plugins (their skill list may already cover part of it)

Verdict, stated to the user explicitly:
- **≥80% fit** → adapt it (fork, trim to the user's premises) instead of writing from scratch.
- **Partial fit** → steal its structure, write the user's delta.
- **No fit** → proceed. Say what you searched so the user can correct you.

## Step 1 — Placement triage

For each candidate rule, route it before writing:

| Test | Destination |
|---|---|
| Enforceable by regex/lint/hook/CI? (e.g. "diff must not touch `__uuid__` lines") | Build the hook or lint rule. The skill keeps only the judgment part (why, recovery, alternatives). Offer the hook to the user — do not silently install it. |
| Single-project convention? | That project's CLAUDE.md / AGENTS.md |
| Model already knows it, or official docs answer it in one lookup? | Leave it out (delta principle). At most link the doc. |
| None of the above | Skill content |

If after triage nothing is left for the skill, tell the user that — "this should be a pre-commit hook, not a skill" is a successful outcome of this protocol.

## Step 2 — Extraction interview (gate)

**Self-research first.** Before asking anything, gather what you can: scan the project (versions from manifests, structure, existing CLAUDE.md / lessons.md), check official docs for the public part. Never ask the user something a file read would answer.

**Then ask the user what only they know.** Cover these six, skipping any already answered:

1. **The incident, concretely.** What exact operation, what broke, how was it discovered, how was it recovered? (For non-incident skills: what does a bad outcome look like?)
2. **Premises.** Which versions/platforms/toolchains is this pinned to? What is explicitly out of scope?
3. **Hard limits and thresholds.** What is never acceptable? What numeric boundaries exist (size caps, time budgets, rate limits)?
4. **Counter-examples.** When does this rule NOT apply? What exception is legitimate?
5. **Existing coverage.** Is part of this already in CLAUDE.md, lessons.md, or another skill? (Avoid duplicate sources that drift apart.)
6. **Desired reflex.** When a future agent hits this situation, what should its FIRST action be?

The answers to 1, 3, 4 and 6 are the skill's core content. If the user's answers are vague, push once with a concrete hypothetical ("an agent is about to do X — allowed or not?"). Vague answers produce advice; forced choices produce decision rules.

**Non-interactive runs:** if you cannot ask (single-turn, headless), the gate still applies — surface every unanswered question as an explicit assumptions table with a "which answer changes what" column in your deliverable. Silently assuming is the violation; visibly assuming is the fallback.

## Step 3 — Generate

Write the SKILL.md applying every Iron Rule from the main skill. Additionally:

- **Decision rules, not advice.** Quality test per line: "if I deleted this sentence, would an agent behave differently?" Delete every line that fails. "Be careful with serialized files" fails; "never edit a line containing `__uuid__`; if your diff touches one, stop and propose the editor workflow instead" passes.
- **Forbidden + alternative, in pairs.** Every "never do X" needs "do Y instead" — a blocked agent without an alternative will rationalize its way through the block.
- **Degrees-of-freedom matching.** Judgment calls where context matters → prose rules. Fragile deterministic procedures (exact ordered steps, zero tolerance for variation: recovery sequences, paired-file moves, environment setup) → an executable script in `scripts/`, with the body saying only WHEN to run it. A script executes identically every time and its source never enters context; the same steps as prose get re-interpreted — and eventually mis-interpreted — every session.
- **Premises block** near the top:
  ```markdown
  ## Premises
  - Engine: Cocos Creator 3.8.x (NOT 2.x — APIs incompatible)
  - Platform: WeChat minigame; size caps are policy numbers, re-check before quoting (checked 2026-06)
  ```
- **Description rules** (hard checks before moving on): starts with "Use when"; third person; lists triggering situations, symptoms, and error keywords; contains a NOT-for clause if confusable with another skill; contains NO rule content, NO "Provides/Covers + feature list"; under 500 chars target.
- **Recovery section** if the skill guards against a destructive failure: what to do when the incident has already happened.
- One excellent example beats many. No multi-language dilution.
- Directory name == frontmatter `name`. Long reference material goes to `references/`, not the body.

Quality bar reference: `overseas-micro-product-scout/SKILL.md` in this repo — hard filters, numeric thresholds, explicit NOT-for. That is the target texture.

## Step 4 — Self-review against baseline failures

Before validation, check the generated skill against the known failure list: no interview question unanswered, description compliant, body tool-agnostic, premises present, every rule paired with an alternative.

## Step 5 — Validate (gate)

Run [validation-protocol.md](validation-protocol.md). The skill is not deliverable before it passes.
