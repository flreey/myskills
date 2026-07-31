# Final Evidence Report

## Confirmed Execution Contract

- Contract version and approval evidence:
- Confirmed requirement and acceptance scope:
- Deviations, revisions, and reconfirmations:
- Authorization closure status:

## External Conversation And Model

- Conversation URL:
- Required underlying model: `GPT-5.6 Sol Pro`
- Fallback allowed: `false`
- Chat surface, picker label, official mapping source, and verification time:
- Recovery model checks:
- Native connected-app approval handoffs:

## Transport And Actors

- Decision: `READY_GITHUB` / `READY_HANDOFF_BRANCH` / `READY_BUNDLE` /
  `BLOCKED_AUTH` / `BLOCKED`
- Codex manager operations actually performed:
- ChatGPT Pro operations actually performed:
- Bundle or handoff operations actually performed:
- Explicitly forbidden operations that remained untouched:

## GitHub Source Identity

- Repository:
- Base branch and SHA:
- Task branch and creator:
- Current head SHA:
- Commit inventory:
- Changed-file inventory:
- Draft PR URL:
- Diff bytes and SHA-256:

For bundle:

- ZIP filename, bytes, SHA-256, included scope, excluded scope, and secret scan:

## Secret And Live-Validation Boundary

- Credential class:
- Public configuration supplied to Pro:
- Secret storage or injection surface:
- Credentialed checks run by Codex:
- Secret-bearing CI or production operations:
- Redaction limitations and unresolved risks:

State explicitly that no secret value entered ChatGPT, Git, PR content,
attachments, or evidence logs, or report the leak response if that statement
is false.

## Actual Changes And Corrections

- Behavior implemented:
- Important files:
- Dependency, lock-file, workflow, migration, or configuration changes:
- Scope intentionally unchanged:

| Round | Redacted evidence supplied | Requested correction | New head | Retest |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Independent Verification

| Gate | Command or check | Result | Evidence and limits |
|---|---|---|---|
| Diff/security review | ... | pass/fail | ... |
| Lint | ... | pass/fail/not run | ... |
| Typecheck | ... | pass/fail/not run | ... |
| Unit | ... | pass/fail/not run | ... |
| Contract/live integration | ... | pass/fail/not run | sandbox/mock/real |
| Build | ... | pass/fail/not run | ... |
| E2E/browser | ... | pass/fail/not run | local/deployed |

Do not collapse mocks, fixtures, local checks, deployed checks, and production
verification into one status.

## Unverified Risks And Repository State

- Remaining risks and blockers:
- Local modifications:
- Local commit:
- Remote task branch and pushed commits:
- Draft PR:
- Merged:
- Deployed:
- Production verified:

Never report a later state unless that action actually succeeded in this run.
