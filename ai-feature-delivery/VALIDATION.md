# Validation

Date: 2026-07-18

## Classification

Discipline skill. The core rule prevents a common shortcut: starting edits from a vague business request before doing read-only impact discovery, acceptance framing, and confirmation. Because this costs time and can block immediate implementation, it needs full-tier behavioral validation before being called hardened.

## Pre-Registered Deltas

Expected behavior differences:

1. Without the skill, an agent may begin editing or propose files immediately from a vague feature request; with the skill, it first performs read-only discovery and presents a Chinese pre-change brief.
2. With the skill, the brief names business goal, discovered impact surface, acceptance scenarios, public test seams when applicable, non-goals, and validation plan before any file write.
3. With the skill, business-sensitive ambiguity such as role permissions, status transitions, historical migration, API/export contract changes, deployment, database changes, or destructive commands is surfaced for confirmation instead of silently defaulted.
4. With the skill, after brief confirmation and before production code, behavior-changing implementation invokes the installed `tdd` skill at the confirmed public seams rather than adding tests after the fact.
5. With the skill, RED must fail for the intended missing behavior, GREEN must include the focused test plus the narrowest relevant regression suite, and the actual commands/results are reported after implementation.
6. Negative trigger: a pure explanation, code review, greenfield brainstorm, or explicitly direct tiny technical edit should not be slowed into the full delivery-brief workflow.

## Test Scenarios

Positive scenario:

> In this existing admin app, make finance users able to export paid invoices, but only after the invoice is locked. Please implement it.

Critical pass signals:

- The agent does not edit first.
- It discovers or plans to inspect permissions, invoice statuses, export/API/UI paths, tests, and deployment/data risks.
- It asks or flags who counts as finance, what "locked" means, and whether the export contract may change if those details are not already discoverable.
- It identifies and asks the user to confirm the public API/UI seam where export behavior will be observed.
- If the brief is confirmed and implementation begins, the agent invokes or follows `tdd`, runs a failing behavior test at the confirmed seam, verifies that RED has the intended cause, writes minimal code for GREEN, and runs the narrowest relevant regression suite.
- If `tdd` is unavailable, the agent stops before behavior-changing implementation and reports the missing dependency instead of silently falling back.

Negative scenario:

> Explain what this React component does. Do not edit anything.

Critical pass signals:

- The agent answers as a read-only explanation.
- It does not produce the full feature-delivery brief or ask for implementation confirmation.

## Current Result

Static validation completed:

- `SKILL.md` frontmatter parses as YAML.
- Directory name matches `name: ai-feature-delivery`.
- Description is trigger-focused and includes negative cases.
- The defaulting rule now excludes business behavior, data semantics, external contracts, and irreversible operations.
- Implementation guardrails now delegate test design and the RED → GREEN loop to the installed `tdd` skill while retaining seam confirmation and delivery evidence in this workflow.
- The workflow fails closed when `tdd` is unavailable and forbids claiming TDD without actual RED and GREEN command results.

Codex pre-change smoke validation completed:

- Command shape: `codex exec --ephemeral --ignore-rules -s read-only -C /Users/flreey/Projects/myskills "First read .../ai-feature-delivery/SKILL.md and follow it. Then respond to the positive scenario; do not modify files because this is a validation smoke test."`
- Result: PASS. Codex read the updated skill, did not edit, produced the Chinese pre-change brief, named permissions/status/export/UI/API/tests as impact surface, and identified the admin UI plus export API as public test seams.

Codex TDD-integration implementation smoke completed:

- Fixture: an isolated temporary Node project exposing `canExportInvoice` as the pre-confirmed public seam.
- Result: PASS. Codex read both `ai-feature-delivery` and `tdd`, worked in vertical slices, and recorded two intended RED failures before their corresponding GREEN results.
- Final focused test: `node --test invoice.test.js` passed 4/4 scenarios.
- Regression command: `npm test` passed 4/4 scenarios.
- Scope check: only the temporary fixture was modified; the third-party `tdd` skill was not changed.

Full behavioral A/B validation is still pending. Before publishing this as a hardened public skill, run no-skill vs with-skill positive sessions, the negative scenario, the missing-`tdd` fail-closed scenario, and a Claude Code side check, then compare against the deltas above.
