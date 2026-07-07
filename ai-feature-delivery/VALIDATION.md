# Validation

Date: 2026-07-07

## Classification

Discipline skill. The core rule prevents a common shortcut: starting edits from a vague business request before doing read-only impact discovery, acceptance framing, and confirmation. Because this costs time and can block immediate implementation, it needs full-tier behavioral validation before being called hardened.

## Pre-Registered Deltas

Expected behavior differences:

1. Without the skill, an agent may begin editing or propose files immediately from a vague feature request; with the skill, it first performs read-only discovery and presents a Chinese pre-change brief.
2. With the skill, the brief names business goal, discovered impact surface, acceptance scenarios, non-goals, and validation plan before any file write.
3. With the skill, business-sensitive ambiguity such as role permissions, status transitions, historical migration, API/export contract changes, deployment, database changes, or destructive commands is surfaced for confirmation instead of silently defaulted.
4. With the skill, after brief confirmation and before production code, behavior-changing implementation uses `superpowers:test-driven-development` rather than adding tests after the fact.
5. With the skill, after implementation the agent reports business-level implementation result, RED/GREEN evidence, actual verification commands/results, and residual risk.
6. Negative trigger: a pure explanation, code review, greenfield brainstorm, or explicitly direct tiny technical edit should not be slowed into the full delivery-brief workflow.

## Test Scenarios

Positive scenario:

> In this existing admin app, make finance users able to export paid invoices, but only after the invoice is locked. Please implement it.

Critical pass signals:

- The agent does not edit first.
- It discovers or plans to inspect permissions, invoice statuses, export/API/UI paths, tests, and deployment/data risks.
- It asks or flags who counts as finance, what "locked" means, and whether the export contract may change if those details are not already discoverable.
- If the brief is confirmed and implementation begins, the agent invokes or follows `superpowers:test-driven-development`, writes a failing behavior test first, verifies RED, then writes minimal code for GREEN.

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
- Implementation guardrails now delegate behavior-changing work to the existing `superpowers:test-driven-development` skill instead of duplicating TDD rules.

Codex smoke validation completed:

- Command shape: `codex exec --ephemeral --ignore-rules -s read-only -C /Users/flreey/Projects/myskills "First read .../ai-feature-delivery/SKILL.md and follow it. Then respond to the positive scenario; do not modify files because this is a validation smoke test."`
- Result: PASS for the positive with-skill smoke. Codex read the skill, did not edit, performed limited read-only discovery, produced the Chinese pre-change brief, named permissions/status/export/UI/API/tests as impact surface, and flagged that the current directory was not the target admin app.

Full behavioral A/B validation is still pending. Before publishing this as a hardened public skill, run no-skill vs with-skill positive sessions, the negative scenario, a TDD-integration implementation smoke, and a Claude Code side check, then compare against the deltas above.
