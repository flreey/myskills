---
name: chatgpt-pro-engineering-loop
description: Use when the user explicitly asks Codex Desktop to delegate substantial repository implementation to an already signed-in ChatGPT Pro session, including a short natural-language requirement that needs an execution proposal first. NOT for ordinary local coding, simple review, generic research, login-only requests, or work that must not leave the local environment.
---

# ChatGPT Pro Engineering Loop

## Premises

- Host: Codex Desktop with the controllable in-app browser.
- Manager: Codex owns repository discovery, task boundaries, GitHub task state,
  independent verification, and final truth.
- Developer: ChatGPT Pro researches, designs, and commits code only to the
  assigned task branch.
- Required external model: `GPT-5.6 Sol Pro`; fallback is forbidden.
- Normal code transport: GitHub task branch plus Draft PR.
- Exception transports: a reviewed handoff branch for publishable local dirty
  source, or a sanitized bundle when the source must not be published.
- Secret transport: none. Secret values never enter ChatGPT, Git, Issues, PRs,
  comments, attachments, or evidence logs.
- Live proof: on 2026-07-31, the signed-in Pro surface created a branch and a
  one-file commit in `flreey/myskills` through the GitHub plugin after one
  native approval. This proves that account/repository pair only; another
  account, repository, or changed plugin surface still needs a fast read-only
  capability check.
- Model mapping and product UI checked 2026-07-31. Recheck the official mapping
  and visible picker for every run.
- Standard scope excludes merge, deployment, migration, repository settings,
  secret management, production configuration, production credentials, and
  real user data.

Review these premises when the browser, ChatGPT account, GitHub connection,
repository policy, or model picker changes.

## Desired Reflex

Use four separate planes:

1. **Codex control plane** — local truth, execution contract, task branch,
   Draft PR, acceptance, and correction evidence.
2. **ChatGPT Pro development plane** — source reading and additive commits on
   one assigned branch.
3. **GitHub code plane** — immutable base/head identities, commits, Draft PR,
   CI, and review evidence.
4. **Secret plane** — local environment, secret manager, or gated CI only;
   never ChatGPT or repository content.

Treat ChatGPT Pro as an untrusted external engineer. A polished report, a
claimed test pass, or a green remote check does not replace local review and
verification at the exact head SHA.

## Trigger Boundary

Trigger only when the user explicitly asks to involve ChatGPT Pro or invokes
this skill by name.

Do not trigger for:

- ordinary local implementation or debugging;
- a small second-opinion review;
- generic web research;
- browser login by itself;
- work that forbids external source access.

A concrete one-sentence requirement is enough. Codex must infer ordinary
acceptance criteria and technical defaults instead of demanding a long user
template. Ask only for authentication, a product-defining decision, sensitive
data exposure, irreversible state, or expanded authority.

## Phase 0 — Draft One Execution Contract

Before source transmission, GitHub mutation, persistent run state, local
implementation, dependency installation, or a project command that writes
state, perform only the smallest read-only repository discovery needed to
prepare the contract.

Fill
[references/execution-contract-template.md](references/execution-contract-template.md).
Keep an ordinary contract between 20 and 35 lines with three to seven
acceptance criteria. It must identify:

- requirement, outcome, scope, non-goals, and architecture boundaries;
- inferred versus user-supplied acceptance criteria;
- exact local verification commands and evidence limits;
- required model `GPT-5.6 Sol Pro` with no fallback;
- requested transport `auto`;
- GitHub collaboration, optional reviewed handoff branch, and sanitized bundle
  fallback authority;
- secret classification: `none`, `interface-only`, `local-test`, `ci-test`, or
  `production`;
- operations that remain forbidden.

Present the contract and wait for an unambiguous confirmation such as
“确认执行”. One confirmation activates an **authorization closure** for every
exact operation listed in that contract.

Within the active closure:

- Codex does not ask again before the listed branch, commit, Draft PR, browser,
  correction, fetch, artifact, or verification operations;
- switching among already authorized `auto` paths after a capability failure
  does not require reconfirmation;
- additive correction commits and repeated verification remain authorized;
- a native ChatGPT/GitHub approval control is a user handoff, not a new
  execution-contract question.

Require a revised contract only for a different repository, account,
destination, data or edit scope, product behavior, acceptance criteria, model,
secret class, or operation authority, or for an unlisted destructive or
production operation.

Host Full Access controls the local sandbox only. ChatGPT connected-app
permissions are separate. Never promise to bypass their native prompts or
change the user's account setting automatically.

## Phase 1 — Establish Local Truth

Read the smallest relevant set:

1. applicable `AGENTS.md` and `CLAUDE.md`;
2. root README and relevant architecture documents;
3. manifests, lock files, and runtime versions;
4. CI workflows and nearby tests;
5. source seams related to the requirement.

Record:

- repository root, branch, `HEAD`, upstream, and worktree status;
- remote refs containing `HEAD`;
- staged, unstaged, untracked, and unpushed state;
- whether the task needs current uncommitted source;
- relevant architecture and compatibility boundaries;
- required lint, typecheck, unit, contract, build, and E2E gates;
- existing user changes that must be preserved.

Never clean, reset, stash, rebase, or hide user work.

## Phase 2 — Pass The Model And Secret Gates

Before creating a task branch, packaging source, mentioning the repository in
ChatGPT, or dispatching the task, follow
[references/model-gate-protocol.md](references/model-gate-protocol.md).

The gate passes only when the selected Chat surface and documented picker
mapping prove the underlying model is exactly `GPT-5.6 Sol Pro`. A Pro account
badge, generic GPT-5.6 label, Medium, High, Extra High, or Work model is not
enough.

Create one blank conversation per independent task. Default to one active
code-changing conversation. Multiple conversations are allowed only when their
branches and edit scopes do not overlap; review-only conversations may overlap.

Classify credential needs using
[references/secrets-and-live-validation.md](references/secrets-and-live-validation.md):

- `none` and `interface-only` may proceed normally;
- `local-test` keeps the value local and lets Codex run the integration;
- `ci-test` requires separately authorized secret provisioning and a reviewed,
  gated workflow;
- `production` blocks the standard loop and requires a new contract.

If login, account selection, password, CAPTCHA, Passkey, recovery code, or
two-step verification is required, stop for the user. Never inspect browser
authentication state or ask for credentials in chat.

## Phase 3 — Select The Fast Transport

Run `scripts/select_transport.py` after local discovery and live read-only
capability inspection.

The selector returns one of:

| Decision | Meaning |
|---|---|
| `READY_GITHUB` | exact baseline is remote; Codex and Pro have verified write capability; local dirty source is not required |
| `READY_HANDOFF_BRANCH` | task needs local dirty source; the exact scope passed secret review and is explicitly authorized for GitHub publication |
| `READY_BUNDLE` | GitHub is unavailable or the source must remain off GitHub; sanitized upload is authorized |
| `BLOCKED_AUTH` | GitHub is selected but a native product approval is waiting for the user |
| `BLOCKED` | no safe authorized path exists |

Do not create a synthetic smoke branch on every run. Inspect the current action
surface and target-repository permission cheaply; let the first real
task-scoped mutation prove write availability. If it fails, record the native
error and select an already authorized fallback.

An unrelated dirty worktree does not block GitHub. If the task needs dirty
source, never make a WIP commit in the primary worktree.

## Phase 4 — Establish The GitHub Task

For `github` and `handoff-branch`, follow
[references/github-manager-developer-protocol.md](references/github-manager-developer-protocol.md).

Default ownership:

- Codex creates `codex/chatgpt-pro/<task-id>` from the exact base SHA;
- ChatGPT Pro reads and commits only to that assigned branch;
- after the first valid Pro commit, Codex creates the Draft PR;
- Codex owns PR metadata, acceptance evidence, and head tracking;
- ChatGPT Pro does not create an Issue by default and never merges.

The manager may delegate branch creation to Pro only when the same exact
repository, base SHA, branch name, and operation are already authorized. This
is a recovery option, not the normal split.

Prefer an atomic multi-file commit when the current GitHub action surface
supports blob/tree/commit/ref operations. Otherwise accept a small sequence of
task-scoped commits and verify the final head. Never force-push or rewrite an
already observed head.

For `handoff-branch`:

1. run the bundle scanner on only the approved dirty paths;
2. reject any secret, unsafe path, unexpected binary, or scope expansion;
3. reconstruct the scanned bytes in an isolated worktree at the recorded base;
4. verify every file hash against the scanner manifest;
5. commit and push from that isolated worktree to the handoff branch;
6. preserve the user's primary dirty worktree unchanged.

## Phase 5 — Prepare Bundle Only When Needed

For `bundle`, use `scripts/prepare_bundle.py`; do not reproduce its scanning
procedure manually.

The bundle must be task-scoped and produce:

- deterministic ZIP;
- base `HEAD`, branch, dirty-state digest, file list, and per-file hashes;
- exclusions, byte size, ZIP SHA-256, manifest, and `.sha256` file.

The default uncompressed soft limit is 50 MiB. Exclude `.env`, credentials,
databases, browser state, caches, build output, symlinks, device files, and
unapproved binary content.

If the scanner reports a candidate secret, do not create or upload the archive.
Remove the file from scope or create a sanitized fixture, then rerun from the
beginning. Never paste the finding value into chat or logs.

## Phase 6 — Dispatch The Engineering Brief Once

Fill [references/task-brief-template.md](references/task-brief-template.md).
The brief must contain:

- background, goal, scope, architecture boundaries, and exact baseline;
- assigned repository and task branch for GitHub, or bundle identity and hash;
- permitted Pro operations and Codex-owned operations;
- secret classification and the exact public configuration contract;
- required deliverables and tests;
- forbidden operations and claims;
- acceptance criteria and unresolved risks.

For GitHub, require:

- additive commits on the assigned branch;
- current head SHA, commit inventory, and changed-file inventory;
- test commands actually run, results, and limitations;
- acceptance mapping and engineering report.

Do not ask Pro to create the Draft PR; Codex opens it after the first valid
commit. For bundle mode, require a downloadable patch or changed-files archive
with size and SHA-256. A conversation code block alone is provisional.

Use [references/browser-and-recovery-protocol.md](references/browser-and-recovery-protocol.md).
Send the brief once, save the stable conversation URL after dispatch, and
record the model, baseline, branch or bundle identity, and dispatch time.

When the native GitHub prompt appears, ask the user to approve it in the
browser. Recommend conversation-scoped approval for a personal workflow; do
not select a broader persistent permission on the user's behalf.

## Phase 7 — Observe And Recover

Do not interrupt or duplicate a task while progress is visible. Poll no more
often than every two minutes. After two unchanged observations spanning at
least ten minutes, inspect for a real error, stopped response, reconnect
control, or authentication requirement.

Recover the saved conversation from the last completed heading. After a
reconnect, replacement conversation, visible model change, or availability
warning, rerun the model gate before sending more repository context.

Track GitHub progress through repository state when possible; use the browser
for task communication, native approvals, and recovery. A changed branch head
is new external state and invalidates verification performed against the old
head.

## Phase 8 — Verify At The Exact Head

After the first Pro commit:

1. verify that the task branch descends from the recorded base;
2. inspect changed files before opening a Draft PR;
3. let Codex create the Draft PR against the agreed base;
4. record base SHA, head SHA, commit inventory, and changed-file inventory;
5. fetch the exact head without pulling it into the primary worktree;
6. create a disposable detached worktree;
7. persist a binary-safe base-to-head diff and its SHA-256;
8. review dependencies, lock files, workflows, scripts, migrations, network
   calls, and secret/data boundaries;
9. run every required repository gate and record command, working directory,
   exit status, duration, and discovered test count.

Before any test receives `local-test` or `ci-test` credentials, review the
entire diff that can execute in that environment. A Pro-authored workflow or
script never receives secrets merely because it is on a same-repository
branch.

Do not claim:

- mocked or fixture-backed behavior is a live integration;
- a unit test is E2E;
- local verification is deployed or production verification;
- an unrun command passed;
- ChatGPT's claimed test execution ran locally.

Missing credentials, devices, services, or platform access produce an explicit
unverified risk, not a pass.

## Phase 9 — Correction Loop

When verification fails, send one evidence packet in the same Pro conversation:

- failed acceptance criterion;
- exact command, working directory, and exit status;
- minimal redacted log excerpt;
- file and line location;
- correct repository constraint;
- requested smallest complete correction.

Pro adds ordinary correction commits to the same branch. Codex records the new
head and reruns from the earliest invalidated gate. Never send a secret value
or allow force-push as a shortcut.

Continue until every required criterion passes or an external blocker is
proven within current authority. Do not ask the user to relay technical
messages.

## Phase 10 — Finish Without Overclaiming

Do not automatically merge, delete the branch, release, deploy, migrate,
configure secrets, or modify production. These require separate authority.

Fill [references/final-evidence-template.md](references/final-evidence-template.md)
and report separately:

- ChatGPT conversation URL;
- selected transport and any native approval handoff;
- repository, base SHA, task branch, head SHA, commits, and Draft PR;
- actual changed files and behavior;
- corrections requested from Pro;
- independent tests and their limits;
- credential class and which live checks were or were not run;
- remaining risks;
- local modification, commit, push, PR, merge, deploy, and production states.

Keep valuable sanitized evidence in the repository only when it has future
engineering value. Private conversation URLs, local paths, secret metadata,
source archives, and credentials stay outside the repository.

## Rationalization Guard

| Temptation | Required response |
|---|---|
| “Pro can manage the whole repository now.” | Assign one branch; Codex owns the base, Draft PR, acceptance, and final state. |
| “The capability test passed, so skip per-repository checks forever.” | Reuse the proof only for the same account/repo shape; perform a cheap current permission check and let the first real mutation prove availability. |
| “An Issue makes the task official.” | Use the contract, branch, conversation, and Draft PR; create an Issue only when task tracking adds value. |
| “The key is only needed for testing, so paste it to Pro.” | Give the interface and sanitized fixtures; Codex performs the credentialed test locally or in gated CI. |
| “GitHub Secrets make any workflow safe.” | Review every executable diff first; secrets do not protect against code that intentionally exports them. |
| “A quick WIP commit is easier than bundle handling.” | Use a scanned isolated handoff branch only when publication is authorized; otherwise use the sanitized bundle. |
| “The PR is green, so the code passed.” | Fetch the exact head and run authoritative local gates in isolation. |
| “Full Access should suppress the GitHub prompt.” | Full Access is local; hand the native connected-app approval to the user. |
| “The fix is small, so force-push is harmless.” | Require additive commits and preserve every observed head identity. |
| “The implementation is done, so merge it.” | Stop at a validated Draft PR unless merge is separately authorized. |
