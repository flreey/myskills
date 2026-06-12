# Harvest Protocol (Mode C)

Use to crystallize repeated corrections into skills. Sources: `tasks/lessons.md`, session history, the user describing "I keep having to tell agents X".

## Trigger threshold

**One occurrence = leave it in lessons.md. Second occurrence of the same class = skill candidate.**

"Same class" means same root cause, not same surface: "agent hand-edited a .prefab uuid" and "agent moved an asset without its .meta" are the same class (bypassing the editor's ownership of serialized state).

Do not harvest single events into skills — that fills the library with rules that never fire again and dilutes triggering for every other skill.

## Procedure

1. **Scan** the source for entries; group by root cause; count occurrences per class.
2. **Check against existing skills** — for each candidate class, three outcomes:
   - **Not covered** → run [forge-protocol.md](forge-protocol.md) for it (the interview is shorter — the lesson entries already answer most questions; confirm premises and counter-examples with the user).
   - **Partially covered by an existing skill** → add a section/row to that skill. Adjacent topics merge into one skill; do not create a sibling. Then re-validate the edited skill (an edit is a change — validation-protocol applies to edits too).
   - **Contradicts an existing skill** → the existing skill's premise has probably changed (version upgrade, policy change). **Default action: update the old skill and its premises block — never add a second skill that disagrees with the first.** Two contradicting rules in the library is worse than either alone.
3. **Crystallize, then delete.** Once content has landed in a skill (validated), remove the source entries from lessons.md, leaving one line: `→ promoted to skill: <name>`. Single source of truth; duplicated rules drift apart.
4. **Placement triage still applies** — some lessons.md entries are project conventions (→ CLAUDE.md) or mechanically checkable (→ hook), not skills.

## Library hygiene (run opportunistically during harvest)

- Every installed skill's description sits in the system prompt of every session. Prefer ten sharp skills over fifty vague ones; merge before creating.
- A skill whose premises name a version the user no longer uses → propose update or retirement to the user; do not delete on your own.
- A skill that demonstrably failed to trigger when it should have → that is a description bug; fix the description (add the symptom/error keywords that were present in the missed situation) and re-test triggering.
