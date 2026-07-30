# External Engineering Task Brief

Fill every required field. Remove instructional placeholders before dispatch.

## Identity

- Task ID:
- Confirmed execution contract version:
- Contract confirmation evidence:
- Conversation purpose:
- Requested external role: senior engineer responsible for research, design, and implementation proposal
- Required external model: `GPT-5.6 Sol Pro`
- Model fallback allowed: `false`
- Verified conversation surface:
- Verified picker label:
- Model verification time and official mapping source:

## Background And Goal

- User need:
- Business or user-visible outcome:
- Why the current behavior is insufficient:

## Selected Transport And Authority

- Transport: `github-pr` / `github-issue-patch` / `bundle`
- Current-run source-access authority:
- Current-run GitHub mutation authority:
- Explicitly forbidden remote operations:

## Supplied Baseline

- Repository name:
- Branch:
- Commit:
- Dirty baseline: yes/no
- Dirty-state digest:

For GitHub transport:

- Repository identity:
- Remote name:
- Fetched remote refs containing the baseline:
- GitHub Issue URL:
- Target base branch:
- Task branch, when authorized:
- ChatGPT GitHub capability verified live: read/write

For bundle transport:

- Archive filename:
- Archive bytes:
- Archive SHA-256:
- Included paths:
- Intentionally excluded paths:

State which source surface is complete for this task. GitHub access applies only
to the identified repository and baseline. Bundle access applies only to the
attached archive. You cannot access the local filesystem, unrelated private
repositories, internal network, browser state, credentials, services, or
production environment.

## Architecture And Boundaries

- Runtime and dependency versions:
- Relevant components and ownership boundaries:
- Public contracts that must remain compatible:
- Existing user changes that must not be overwritten:
- Security and data boundaries:
- Non-goals:

## Research And Modification Scope

Research:

1. ...

Modify:

1. ...

Do not modify:

1. ...

## Required Deliverables

For `github-pr`, return all of the following:

1. An engineering report covering findings, design, assumptions, acceptance
   mapping, and residual risks.
2. A Draft PR against the supplied base, with base SHA, head SHA, commit
   inventory, and changed-file inventory.
3. Exact test commands actually run, results, and environment limitations.
4. A mapping from each acceptance criterion to the implementation and test.

For `github-issue-patch` or `bundle`, return all of the following:

1. `engineering-report.md` covering findings, design, assumptions, changed-file inventory, and residual risks.
2. A unified patch against the supplied baseline, preferably `changes.patch`; if that is impossible, a ZIP containing only changed files at their repository-relative paths.
3. Byte size and SHA-256 for every attachment.
4. Exact local commands Codex should run for verification.
5. A mapping from each acceptance criterion to the implementation and test that proves it.

Conversation code blocks are previews only. They are not a substitute for the
selected machine-usable deliverable: an immutable Draft PR head or a verified
patch or changed-files archive.

## Required Tests

- Focused tests:
- Lint:
- Typecheck:
- Unit:
- Contract/integration:
- Production build:
- E2E or browser:
- Other repository gate:

You may analyze or propose tests from the selected source surface. Do not claim
these commands ran unless this conversation actually provides an execution
environment containing the supplied repository and shows their results. Codex
will run the authoritative local verification.

## Forbidden Operations And Claims

- Do not claim access outside the selected source surface, internal services, credentials, or production.
- Do not request `.env`, API keys, tokens, private keys, Cookies, passwords, verification codes, or recovery codes.
- Perform only the GitHub operations explicitly listed as authorized above.
- Never merge, force-push, delete remote branches, release, deploy, migrate,
  change Actions or repository settings, alter secrets, change production
  configuration, or touch real user data.
- Do not broaden dependencies, update lock files, reformat unrelated files, or refactor outside scope without a demonstrated necessity.
- Do not describe mocks, static analysis, or local simulations as real production verification.

## Acceptance Criteria

1. ...
2. ...
3. ...

For each criterion, state one of:

- implemented and covered by a proposed local verification;
- blocked, with exact missing evidence;
- out of scope, with reason.

## Response Discipline

- Work only in this conversation while its selected underlying model remains
  `GPT-5.6 Sol Pro`; if the product reports a model change or availability
  problem, stop and report it without continuing on another model.
- Read all supplied relevant files before proposing changes.
- State uncertainty instead of guessing.
- Prefer the smallest complete patch.
- Preserve repository conventions and existing interfaces.
- If a requirement is internally inconsistent, identify the conflict and choose no behavior silently.
