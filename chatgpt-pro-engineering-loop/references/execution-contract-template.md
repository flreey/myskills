# Execution Contract

Use this template for the Codex-to-user confirmation gate. It is not the task
brief sent to ChatGPT Pro.

For an ordinary single-component task, use 25–40 lines, three to seven
acceptance criteria, and the five headings below. Expand only when material
product, data, or repository risk cannot be represented safely in that shape.
Do not repeat the future run ledger or explain every permission separately.
Remove instructional placeholders before presenting the contract.

## Goal And Scope

- Contract version:
- Requirement and intended outcome:
- Target repository, ChatGPT account, and external destinations:
- Material repository evidence and existing changes to preserve:
- Proposed scope, non-goals, and recommended technical defaults:
- Required external model: `GPT-5.6 Sol Pro`
- Model fallback allowed: `false`

## Acceptance And Verification

Label each item `user-supplied` or `inferred`.
1. ...
2. ...
3. ...
- Focused tests, required repository gates, and environment/evidence limits:

## Transport And Authority

- Requested transport: `auto` / `github-pr` / `github-issue-patch` / `bundle`; authority preset: standard engineering loop / narrowed custom.
- Allowed local operations: create persistent run metadata and a safe bundle; create isolated worktrees; fetch, inspect, apply or integrate scoped changes; run required tests and verification.
- Allowed ChatGPT/browser operations: open and recover task conversations; select and recheck `GPT-5.6 Sol Pro`; upload only the approved sanitized bundle; send the brief and corrections; download declared reports, patches, and replacements.
- Allowed GitHub operations: let ChatGPT access this repository; create one task Issue and task branch; create task-scoped commits and regular pushes; create or update one Draft PR; publish task-scoped Issue/PR comments.
- Authorized `auto` paths: eligible GitHub delivery and sanitized-bundle fallback are both authorized; capability-based switching needs no new confirmation.

## Boundaries And Decisions

- Still forbidden: merge or auto-merge, force-push, remote branch deletion, release or tag, deployment, migration, production configuration, repository settings or secrets, and real user data.
- Required-model failure behavior: block before packaging, source transmission, task dispatch, or GitHub task mutation; do not downgrade.
- Product, data-exposure, irreversible, or authority-changing decisions: none / one necessary question.

## Confirmation

State:

> Reply “确认执行” or otherwise unambiguously approve this contract version.
> One confirmation activates the task-scoped authorization closure for every operation listed above, including correction and verification rounds.
> Codex will not ask again before those operations. A different repository, account, destination, data or edit scope, product behavior, acceptance criteria, model, authority, or an unlisted/destructive/production operation requires a revised contract and another confirmation.
