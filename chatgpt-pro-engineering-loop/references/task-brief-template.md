# External Engineering Task Brief

Fill every required field and remove placeholders before dispatch.

## Identity

- Task ID:
- Confirmed execution contract version:
- Conversation purpose:
- Required external model: `GPT-5.6 Sol Pro`
- Model fallback allowed: `false`
- Verified Chat surface and picker label:
- Model verification time and official mapping source:

## Background And Goal

- User need:
- Intended outcome:
- Why current behavior is insufficient:

## Actor And GitHub Boundary

- Codex manager owns: exact base, task branch creation, Draft PR, head tracking,
  independent verification, and correction evidence.
- ChatGPT Pro owns: research, design, and additive commits only to the assigned
  task branch.
- Repository:
- Base branch and exact base SHA:
- Assigned task branch:
- Allowed file scope:
- Concurrent tasks and explicitly non-overlapping boundaries:
- Current Pro GitHub capability:
- Explicitly forbidden remote operations:

For bundle transport:

- Archive filename, bytes, and SHA-256:
- Included and intentionally excluded paths:

State that the selected GitHub repository/branch or attached bundle is the
complete source surface for this task. Pro cannot access the local filesystem,
other repositories, internal networks, browser state, credentials, services,
or production.

## Secret And Live-Validation Contract

- Credential class: `none` / `interface-only` / `local-test` / `ci-test` /
  `production`
- Public configuration names and formats Pro may use:
- Sanitized fixtures or public documentation supplied:
- Credentialed checks reserved for Codex:
- Explicitly forbidden secret and production behavior:

Never request or reveal a key, token, password, Cookie, certificate, private
key, connection string, verification code, recovery code, or production data.

## Architecture And Scope

- Runtime and dependency versions:
- Relevant components and ownership boundaries:
- Public contracts that must remain compatible:
- Existing user changes that must not be overwritten:
- Security and data boundaries:
- Non-goals:

Research:

1. ...

Modify:

1. ...

Do not modify:

1. ...

## Required Deliverables

For GitHub:

1. Additive commits on the assigned branch.
2. Engineering report covering findings, design, assumptions, acceptance
   mapping, and residual risks.
3. Current head SHA, commit inventory, and changed-file inventory.
4. Exact test commands actually run, results, and environment limitations.

Codex creates the Draft PR after the first valid commit. Pro must not create an
Issue, PR, merge, force-push, branch deletion, release, deployment, secret, or
repository-setting change unless the brief explicitly overrides that boundary.
Pro must not inspect, modify, or comment on another task's branch or
conversation.

For bundle:

1. `engineering-report.md`.
2. Unified patch against the supplied baseline or a changed-files archive.
3. Byte size and SHA-256 for every attachment.
4. Exact commands Codex should run.

Conversation code blocks are previews, not machine-usable delivery.

## Required Tests And Acceptance

- Focused tests:
- Lint:
- Typecheck:
- Unit:
- Contract/integration:
- Production build:
- E2E or browser:
- Other repository gate:

Do not claim a command ran unless the current environment actually ran it.
Codex performs the authoritative local verification and any authorized
credentialed integration.

Acceptance criteria:

1. ...
2. ...
3. ...

For each criterion, report implemented, blocked with evidence, or out of scope
with reason.

## Response Discipline

- Stop if the selected model is no longer `GPT-5.6 Sol Pro`.
- Read all relevant supplied source before modifying it.
- Prefer the smallest complete change.
- Preserve repository conventions and existing interfaces.
- State uncertainty instead of guessing.
- Never broaden dependencies, lock files, workflows, source scope, or secret
  access merely to make a test pass.
