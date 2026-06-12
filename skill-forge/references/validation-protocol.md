# Validation Protocol

Every forged, bootstrapped, harvested, or **edited** skill passes through here before it is presented as done. The point is not "are the facts true" — it is "does this skill change agent behavior in the intended way".

## Step 1 — Classify the skill, pick the tier

**Discipline skill**: contains rules an agent has an incentive to bypass — compliance costs time, forces rework, blocks a shortcut (TDD-style rules, "never edit X even when it looks faster"). → Full tier.

**Knowledge skill**: domain facts, decision rules, API pins, boundaries the agent has no motive to fight. → Light tier.

Mixed skills: validate the discipline part at full tier. When unsure, ask: "would an agent under deadline pressure WANT to ignore this rule?" Yes → discipline.

## Step 2 — Pre-register expected deltas

BEFORE running anything, write down 3–5 concrete behavior differences the skill must cause, e.g.:

- A (no skill) writes engine code from memory; B (with skill) detects/asks the version first
- A hand-edits the serialized file; B refuses and outputs the editor step list
- B cites the skill's rule when refusing

Pre-registration prevents grading on vibes after the fact. The deltas come straight from the interview's "desired reflex" answers.

## Step 3 — Light tier (knowledge skills): A/B run

1. Build TWO scenarios. **Positive**: a realistic task from the original incident/domain; the prompt must NOT hint at expected behaviors (no "be careful with uuids"). **Negative**: an adjacent task where the skill must NOT change behavior (e.g. for a serialized-asset guard: a plain TypeScript gameplay edit in the same project). False triggering is the main pollution source as a skill library grows.
2. **Run A** — fresh agent session, positive scenario only, no skill.
3. **Run B** — fresh agent session, instructed to read the skill file first, then the same scenario. Run the negative scenario with the skill too.
4. Compare against pre-registered deltas. **Pass = every critical delta present in B's positive run, A demonstrates the failure the skill exists to prevent, AND the negative run shows no behavior change** (no refusals, warnings, or detours the task didn't need). (If A already behaves perfectly, the skill may be covering model-known ground — shrink it per the delta principle. If the negative run gets blocked or lectured, the skill's rules are scoped too wide — tighten the triggers and NOT-for clause.)
5. **Trigger check** (separate from behavior check): does the description alone catch the positive scenario — and stay silent on the negative one? Verify the positive scenario's natural wording shares keywords/symptoms with the description, and the negative scenario's wording does not.

Cost: ~15–25 minutes. This tier is deliberately cheap so it never gets skipped.

## Step 4 — Full tier (discipline skills)

Apply the superpowers writing-skills methodology (RED-GREEN-REFACTOR with pressure scenarios):

- 3+ combined pressures per scenario (time + sunk cost + authority…), forced A/B/C choice
- Capture rationalizations verbatim; add explicit counters + rationalization-table rows for each
- Loop until no new rationalization survives

Reference: superpowers:writing-skills skill and its `testing-skills-with-subagents.md`. Do not reproduce that methodology here — load it.

## Step 5 — Dual-CLI check

The skill must work in both Claude Code and Codex:

- **Claude side**: run A/B as fresh subagent sessions, or headless: `timeout 180 claude -p "<prompt>"`.
- **Codex side** (smoke, one scenario): 
  ```bash
  timeout 300 codex exec -a never -s read-only -C "<project dir>" \
    "First read <absolute path to SKILL.md> and follow it. Then: <scenario>"
  ```
- Pass = critical deltas appear on both sides. A Codex-side miss usually means host-specific tool names or Claude-specific phrasing in the body — fix and re-run.

## Step 6 — On failure: refactor, re-run

B missed a delta → the skill is unclear or the content is buried; revise the specific section and re-run the SAME scenario. Found a new rationalization (full tier) → add the counter and re-test. Never downgrade a failing result to "good enough" — shrink the skill's claims instead if a delta turns out to be unachievable.

## Step 7 — Record

Append a short validation note to the skill's directory (scenario used, deltas checked, result, date). This is the evidence the next editor needs before changing the skill.
