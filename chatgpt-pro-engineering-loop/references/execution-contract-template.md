# Execution Contract

Use this for the one Codex-to-user confirmation gate. Remove placeholders
before presenting it. Keep an ordinary contract between 20 and 35 physical
lines with three to seven acceptance criteria.

## Goal And Scope

- Contract version:
- Requirement and intended outcome:
- Target repository, account, and external destinations:
- Material repository evidence and user changes to preserve:
- Proposed scope, non-goals, and technical defaults:
- Task ID, `code`/`review` mode, exact edit scope, and concurrency limit:
- Required external model: `GPT-5.6 Sol Pro`; Model fallback allowed: `false`
## Acceptance And Verification

Label each criterion `user-supplied` or `inferred`.
1. ...
2. ...
3. ...
- Focused tests, repository gates, and truthful evidence limits:
## Transport, Actors, And Authority

- Requested transport: `auto`; normal path: GitHub; authorized fallbacks: reviewed handoff branch and/or sanitized bundle.
- Codex manager authority: create one task branch from the exact base; create or update one Draft PR after the first developer commit; fetch, isolate, inspect, test, and send correction evidence.
- ChatGPT Pro authority: read the repository and add task-scoped commits only to the assigned task branch.
- Browser authority: open/recover one model-gated conversation, send the brief and corrections, and download declared artifacts.
- Fallback authority: scan and publish only the approved dirty handoff scope, or upload only the approved sanitized bundle.
## Secret And Production Boundary

- Credential class: `none` / `interface-only` / `local-test` / `ci-test` / `production`; allowed public configuration:
- Secret values never enter ChatGPT, Git, Issue/PR content, attachments, or evidence logs.
- Still forbidden: Issue by default, merge, auto-merge, force-push, branch deletion, release, deployment, migration, settings, secret provisioning, production configuration, production credentials, and real user data.
## Confirmation

> Reply “确认执行” or otherwise unambiguously approve this contract version. One confirmation activates the task-scoped authorization closure for every listed operation and correction round.
> Codex will ask again only when the repository, account, destination, data or edit scope, product behavior, acceptance criteria, model, secret class, authority, or production boundary changes. Native authentication and connected-app approvals remain user handoffs.
