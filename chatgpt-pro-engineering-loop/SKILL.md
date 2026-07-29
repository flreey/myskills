---
name: chatgpt-pro-engineering-loop
description: Use when the user explicitly asks Codex Desktop to delegate a substantial repository task to an already signed-in ChatGPT Pro session, including requests that provide only a natural-language requirement and expect an execution proposal first. NOT for ordinary local coding, simple review, generic web research, browser login, or requests that forbid external engineering.
---

# ChatGPT Pro Engineering Loop

## Premises

- Host: Codex Desktop with a controllable in-app browser session.
- External engineer: ChatGPT Pro is already signed in by the user.
- Repository: a local Git worktree whose instructions and test gates are discoverable.
- Preferred transport: GitHub Issue plus Draft PR when the exact baseline is
  already reachable on the remote, ChatGPT's repository capability is verified
  live, and every remote mutation is explicitly authorized.
- Fallback transport: a sanitized source bundle when the task depends on local
  uncommitted source or GitHub access is unavailable or unauthorized.
- Data boundary: each run must explicitly authorize either ChatGPT GitHub
  source access or bundle upload. Authority may be supplied up front or granted
  by confirming the exact execution contract drafted in Phase 0A. Existing
  repository integration is not standing authority for a new task.
- Checked: 2026-07-29. Browser UI, model labels, upload behavior, and subscription features may change; inspect the live page instead of relying on remembered UI details.
- Scope: this skill coordinates engineering work. It does not grant commit, push, pull-request, deployment, migration, production-data, or production-configuration authority.

Review these premises whenever the host browser, ChatGPT product surface, repository policy, or external-data policy changes.

## Desired Reflex

Treat ChatGPT Pro as an untrusted external engineer:

1. turn the user's concise requirement into a bounded execution contract;
2. obtain one explicit confirmation before any mutation or source transmission;
3. establish the local truth;
4. choose the safest eligible transport instead of assuming ZIP or GitHub;
5. prepare the smallest safe source handoff;
6. issue an acceptance-testable task exactly once;
7. preserve the conversation, Issue, Draft PR, commits, and artifacts;
8. independently fetch or apply, inspect, and test every proposed change;
9. return concrete defects for correction until the work passes or an external blocker is proven.

Never equate a polished answer, a claimed test result, or a downloadable attachment with a verified implementation.

## Trigger And Non-Trigger Boundary

Use this workflow only when the user explicitly asks to involve ChatGPT Pro or invokes this skill by name.

Do not trigger it for:

- ordinary local implementation or debugging;
- a small second-opinion review that can use an existing cross-review workflow;
- generic web research;
- signing in to ChatGPT;
- a request that explicitly forbids involving any external engineer or
  transmitting source outside the local environment.

The initial request may contain only a concrete natural-language requirement.
Do not require the user to pre-write acceptance criteria, test commands, or a
permission matrix. If the requirement itself is still a placeholder or leaves
a genuinely product-defining choice unresolved, ask only for that choice. Do
not invent product direction.

## Phase 0A — Draft And Confirm The Execution Contract

Before any upload, GitHub mutation, local implementation, persistent run
directory, dependency installation, or project command likely to write caches
or generated state, perform only the read-only repository discovery needed to
understand the request.

Read and fill
[references/execution-contract-template.md](references/execution-contract-template.md).
Keep an ordinary single-component task contract between 25 and 40 lines with
three to seven acceptance criteria. Expand only when material product, data, or
repository risk cannot be represented safely within that shape. Collapse
routine repository facts and permission explanations instead of repeating the
entire later run ledger. The contract must still contain:

- the interpreted requirement and user-visible outcome;
- repository evidence used to shape the proposal;
- proposed scope, non-goals, and architecture boundaries;
- acceptance criteria labeled as user-supplied or inferred;
- proposed verification commands and truthful environment limits;
- requested transport `auto` unless the user selected another mode;
- every local, GitHub, browser, and source-transmission operation proposed for
  this run;
- operations that remain forbidden;
- assumptions, recommended technical defaults, and any product decision that
  still needs the user.

Propose ordinary engineering decisions rather than asking the user to choose
among equivalent implementations. Stop only for authentication or a choice
that changes product behavior, external data exposure, irreversible state, or
the authority envelope.

Present the complete contract and wait for an unambiguous approval such as
“确认执行” or “按这个方案执行”. A short confirmation is valid only when it
immediately follows one clearly identified contract version.

Confirmation rules:

- approval authorizes only the operations explicitly listed in that contract;
- omitted operations remain forbidden;
- a user narrowing the proposal confirms only the narrowed version;
- any later change to scope, acceptance criteria, source-transmission path, or
  operation authority creates a new contract version and requires
  reconfirmation before the new operation;
- discovering a different eligible `auto` transport does not require
  reconfirmation when both transports and their exact operations were already
  listed as authorized fallbacks;
- progress updates, technical discussion, or approval from a manager or
  external agent are not user confirmation.

Skip the separate pause only when the initial request explicitly says to
execute immediately and already supplies a complete requirement, acceptance
criteria, and exact operation authority. Treat that request as confirmed
contract version 1 and restate its authority ledger before acting.

## Phase 0B — Establish Authority And Preconditions

After confirmation and before any upload or file edit, copy the exact approved
operations into an authority ledger for this run:

| Operation | Default |
|---|---|
| Read repository and run read-only discovery | allowed |
| Let ChatGPT access the repository through GitHub | allowed only when listed in the confirmed contract |
| Create a GitHub Issue | forbidden unless listed in the confirmed contract |
| Create a task branch or commit | forbidden unless listed in the confirmed contract |
| Push the task branch | forbidden unless listed in the confirmed contract |
| Create or update a Draft PR | forbidden unless listed in the confirmed contract |
| Publish task-scoped Issue or PR comments | forbidden unless listed in the confirmed contract |
| Build and upload a sanitized source archive | allowed only when listed in the confirmed contract |
| Communicate and iterate in ChatGPT Pro | allowed only when listed in the confirmed contract |
| Modify local code and run tests | allowed only when listed in the confirmed contract |
| Merge, force-push, delete a remote branch, release, deploy, migrate, change repository settings or secrets, modify production, or touch real user data | forbidden unless separately explicit |

Confirm that:

- the target is a Git worktree;
- the in-app browser is available;
- the visible ChatGPT session is signed in and shows the intended Pro-capable surface;
- the confirmed contract contains a concrete requirement, acceptance criteria,
  and exact authority.

If sign-in, account selection, password, CAPTCHA, Passkey, recovery code, or two-step verification is required, pause and ask the user to complete it in the in-app browser. Never request or inspect a password, Cookie, verification code, recovery code, browser profile, local storage, or session store.

Create a persistent run directory outside the target repository:

```text
~/.codex/chatgpt-pro-runs/<repo-name>/<UTC-run-id>/
```

Store only run metadata and task artifacts there. Never copy browser state or credentials into it.

## Phase 1 — Establish Local Truth

Read the smallest set that establishes project policy and architecture:

1. every applicable `AGENTS.md` and `CLAUDE.md`;
2. the root `README` and relevant architecture or design documents;
3. manifests and lock files such as `package.json`, `pyproject.toml`, `Cargo.toml`, or equivalents;
4. CI workflows and nearby tests that reveal mandatory gates;
5. the source seams directly related to the request.

Then record:

- repository root, branch, `HEAD`, upstream, and worktree status;
- remotes, fetched remote refs containing `HEAD`, and whether the task depends
  on current uncommitted source;
- staged, unstaged, untracked, and unpushed state;
- runtime and dependency versions;
- relevant architecture boundaries;
- required lint, typecheck, unit, contract, build, and E2E commands;
- current user changes that must be preserved.

Do not clean, reset, stash, rebase, checkout over, or otherwise hide existing changes.

## Phase 2 — Split Work Without Polluting Context

Build a task graph before opening ChatGPT:

- Keep dependent research, design, implementation, and corrections in one conversation.
- Give independent complex tasks separate conversations and separate run subdirectories.
- Do not split by file when the files implement one behavior.
- Do not run two external conversations against overlapping files unless their outputs are review-only.

Assign each task a stable task ID and use it in the GitHub Issue or archive,
brief, artifact directory, and final report.

## Phase 3 — Select The Transport

Use `scripts/select_transport.py` after repository discovery and live capability
inspection. Record every authority flag from the confirmed contract; do not
infer authority beyond that contract from an existing remote, prior run,
installed integration, or Pro subscription.

The default request is `auto`, evaluated in this order:

| Transport | Required facts |
|---|---|
| `github-pr` | exact `HEAD` is in freshly fetched remote refs; task does not depend on local dirty source; ChatGPT GitHub write is verified; GitHub source access, Issue, branch, commit, push, Draft PR, and comment operations are all authorized |
| `github-issue-patch` | the same remote-baseline and clean-task facts; ChatGPT GitHub read is verified; GitHub source access, Issue, and comment operations are authorized |
| `bundle` | bundle upload is authorized |

If none is eligible, stop before transmitting source or mutating GitHub.
Explicitly requesting an ineligible transport fails closed; do not silently
downgrade it.

An unrelated dirty worktree does not by itself block GitHub. Preserve it. If
the task needs any current uncommitted source, use `bundle`; do not manufacture
a WIP handoff commit unless the user separately authorizes the exact paths,
commit, and push.

For `github-pr` or `github-issue-patch`, read
[references/github-transport-protocol.md](references/github-transport-protocol.md).
For `bundle`, continue with Phase 4.

## Phase 4 — Prepare A Safe Bundle Handoff

Use `scripts/prepare_bundle.py`; do not reproduce its packaging or secret-scanning procedure manually.

Select only the paths needed for the task. Repository-wide packaging is acceptable only when the relevant surface cannot be isolated and the archive remains under the size policy.

The script must complete successfully before upload. A successful run produces:

- a deterministic ZIP;
- the source `HEAD`, branch, dirty-state digest, file list, per-file hashes, exclusions, scanner version, byte size, and ZIP SHA-256;
- a separate `.sha256` file and JSON manifest.

The default uncompressed soft limit is 50 MiB. If it is exceeded, narrow or split the task. Do not use the product's maximum upload size as a reason to send excess source.

The default packager is source-only and excludes every NUL-containing binary,
including images and fonts. If a task genuinely depends on binary assets, do
not weaken or bypass the scanner. Build a separate, narrowly scoped,
human-inspectable fixture or obtain explicit authority for a reviewed
asset-handoff procedure.

If the scanner reports a candidate secret:

1. do not create or upload the ZIP;
2. inspect only the named file and finding category;
3. remove the file from scope or create a sanitized task fixture;
4. rerun the scanner from the beginning.

Never dismiss a finding as a false positive merely to continue. Never paste the suspected value into chat, logs, or the run ledger.

Skip this phase for an eligible GitHub transport. The exact remote baseline and
task-scoped GitHub surface replace the source ZIP; they do not replace the
acceptance brief or independent validation.

## Phase 5 — Write The External Engineering Brief

Read and fill [references/task-brief-template.md](references/task-brief-template.md). Do not send the user's raw request by itself.
Derive the brief from the confirmed execution contract. It may narrow the
contract based on repository evidence, but it must never widen scope,
acceptance criteria, source access, or operation authority without a revised
contract and confirmation.

The brief must include:

- background and business goal;
- selected transport and its current-run authority;
- exact branch and commit baseline;
- for GitHub, repository identity, Issue URL, fetched baseline evidence, and
  permitted remote operations;
- for bundle, archive size, scope, and SHA-256;
- relevant architecture and boundaries that must not break;
- exact research and modification scope;
- explicit deliverables;
- required tests and what ChatGPT cannot truthfully claim to have run;
- forbidden operations;
- acceptance criteria;
- required uncertainty and evidence reporting.

Require the machine-usable deliverable for the selected transport:

- `github-pr`: an engineering report, a Draft PR against the supplied base,
  base and head commit SHAs, changed-file and commit inventories, test claims
  with limitations, and unresolved risks;
- `github-issue-patch`: an engineering report plus a unified patch or
  changed-files archive, with size and SHA-256 for every attachment;
- `bundle`: the same report and patch or changed-files archive requirements as
  before.

A code block is provisional. A Draft PR at an immutable recorded head SHA, or a
downloaded machine-usable artifact with a verified hash, is required before
acceptance.

## Phase 6 — Dispatch Once And Preserve Recovery State

Read [references/browser-and-recovery-protocol.md](references/browser-and-recovery-protocol.md) before browser dispatch.

For each task:

1. open a separate ChatGPT conversation;
2. save its stable URL as soon as the conversation exists;
3. for GitHub, provide the Issue, repository identity, and exact baseline SHA
   from the brief; do not upload a duplicate source bundle;
4. for bundle, upload the ZIP and verify the visible attachment name; verify
   the size too when displayed, otherwise record the UI omission and retain the
   locally measured size;
5. send the task brief once;
6. record the dispatch time, visible model or surface label, selected
   transport, source identity, and conversation URL.

## Phase 7 — Observe And Recover

Do not send duplicate task messages while ChatGPT is still working.

Poll no more often than every two minutes. A long runtime alone is not failure.
After two unchanged observations spanning at least ten minutes, inspect the
page for an error, stopped generation, disconnected state, or a continue
control. Recover in the same conversation from the last completed point.
Reopen the saved URL when the tab is lost.

For GitHub, also preserve the Issue and Draft PR URLs. A changed PR head is new
external state: record the old and new SHAs, then validate the new head from the
beginning. Never treat a mutable branch name as artifact identity.

If the page requires authentication, stop at the authentication boundary
described in Phase 0B.

## Phase 8 — Receive And Verify Deliverables

Save every report and external artifact identity in the persistent run
directory.

For `github-pr`:

- record Issue and Draft PR URLs, base SHA, head SHA, commit inventory, and
  changed-file inventory;
- fetch the exact head without checking it out over the primary worktree;
- persist a binary-safe diff from base to head and calculate its local byte
  size and SHA-256;
- reject unexpected base changes, force-push ambiguity, unrelated commits,
  dependency churn, forbidden workflows, or files outside approved scope.

For an attachment:

- record the visible filename and reported size when the UI provides one;
- calculate the local byte size and SHA-256 after download;
- compare them with ChatGPT's inventory;
- inspect archive members before extraction;
- reject absolute paths, parent traversal, symlinks, device files, unexpected binaries, embedded credentials, or files outside the approved scope.

Check the report against the actual repository and, for drift-prone claims, the current official documentation or source. ChatGPT's citations and version claims are leads, not proof.

## Phase 9 — Apply Or Fetch In Isolation And Test

Create a disposable detached Git worktree:

- `github-pr`: from the recorded PR head SHA after verifying its base;
- `github-issue-patch`: from the recorded remote baseline, then apply the
  verified patch;
- `bundle`: from recorded `HEAD`, reconstruct the packaged dirty baseline, then
  apply the verified patch.

Never `pull`, merge, or check out the PR branch into the user's primary dirty
worktree merely to inspect it.

Then:

1. verify the patch targets the supplied baseline;
2. inspect every changed file and the full diff;
3. reject unexplained dependency or lock-file churn;
4. inspect new executables, scripts, generated files, migrations, configuration, network calls, and data-handling changes;
5. run the repository's required focused and regression gates;
6. run the relevant lint, typecheck, unit, contract, production build, and E2E commands discovered in Phase 1;
7. verify that each gate actually discovered the expected tests or targets; a
   zero-test success is not a pass unless the repository explicitly defines it
   as valid;
8. record command, working directory, exit status, duration, discovered test
   count, and relevant failure evidence.

Do not claim:

- a mocked service was a production integration;
- a local browser check was a deployed check;
- a unit test was an E2E test;
- a build passed when it was not run;
- ChatGPT's claimed tests ran locally.

Missing credentials, devices, services, or platform access produce an explicit unverified risk, not a pass.

## Phase 10 — Correction Loop

When a defect is found, continue the same task conversation and, when
authorized, mirror the same evidence in the Issue or Draft PR. Send one packet
containing:

- the failed acceptance criterion;
- exact command and exit status;
- the minimal relevant log excerpt;
- file and line location;
- the correct repository constraint;
- the requested smallest complete correction;
- an instruction not to broaden dependencies or unrelated files.

For `github-pr`, require additive correction commits and record the new head
SHA. Do not accept a force-pushed replacement without preserving both
identities. For patch transports, require a replacement artifact with new
hashes. Re-run verification, isolation, review, and tests from the relevant
earliest failed stage.

Continue until:

- every required criterion passes; or
- an external blocker is demonstrated with evidence and cannot be resolved within current authority.

Do not ask the user to relay technical messages. Ask only for authentication or a genuinely product-defining decision.

## Phase 11 — Land Locally Without Losing User Work

Before transferring a validated change to the user's primary worktree, compare
its current `HEAD` and dirty-state digest with the recorded baseline.

- If untouched paths drifted, preserve them and continue.
- If a ChatGPT-touched path drifted, integrate the validated change manually against the current file and rerun the affected tests.
- If safe integration would require choosing new product behavior, stop and ask.

Never reset, overwrite, or discard user changes. A validated Draft PR does not
authorize merge or local integration. Local implementation authority does not
imply commit, push, pull-request, merge, deploy, migration, or production
authority.

## Phase 12 — Persist Evidence And Report Truthfully

Read and fill [references/final-evidence-template.md](references/final-evidence-template.md).

The persistent run directory must contain:

- confirmed execution contract, version, and approval evidence;
- task brief;
- selected transport and authority ledger;
- Issue and Draft PR URLs plus base, head, commit inventory, diff bytes, and
  diff SHA-256; or bundle manifest and ZIP SHA-256;
- conversation URL ledger;
- downloaded reports and attachments;
- original and corrected patch hashes;
- local review notes;
- test evidence;
- final local diff inventory;
- deviations from the confirmed contract and whether they were reconfirmed;
- unresolved risks.

Persist a sanitized report in the repository only when it adds future engineering value and does not expose a private conversation URL, local path, source archive, or sensitive metadata.

The final user report must distinguish:

- locally modified;
- committed;
- pushed;
- Issue created;
- pull request created;
- merged;
- deployed;
- production verified.

Never collapse those states into “done”.

## Rationalization Guard

| Temptation | Required response |
|---|---|
| “The user invoked the skill, so normal GitHub and upload permissions are implicit.” | Invocation authorizes only read-only contract preparation; list every proposed operation and wait for confirmation. |
| “The acceptance criteria are obvious, so start now and document them later.” | Draft them from repository evidence and obtain confirmation before acting. |
| “The user already confirmed, and this is only a small scope or permission change.” | Version the changed contract and reconfirm before the new operation. |
| “ChatGPT Pro is the senior engineer, so its answer is probably right.” | Independently inspect and test every deliverable. |
| “The archive is small, so a secret scan is unnecessary.” | Every upload passes the same scanner. |
| “The scanner finding looks like a fixture.” | Remove or sanitize it, then rerun; do not override. |
| “The repository already has an origin, so GitHub is authorized.” | A remote proves configuration, not current-run source-access or mutation authority. |
| “ChatGPT Pro probably has GitHub write access.” | Verify the live repository capability; subscription labels are not evidence. |
| “The task needs dirty files, so make a temporary WIP commit and push it.” | Use bundle transport unless the exact commit and push are separately authorized. |
| “The PR exists, so pull it into the current branch to test.” | Fetch the exact head SHA and test it in a detached worktree. |
| “The PR branch name is unchanged, so previous tests still apply.” | Record and compare the immutable head SHA; any change invalidates prior verification. |
| “It has been generating for a long time; resend the task.” | Observe at the defined cadence and recover the same conversation. |
| “The code block is enough to implement from.” | Require a machine-usable patch or changed-files archive. |
| “ChatGPT said tests pass.” | Run the repository gates locally and record them. |
| “The test command exited zero, even though it found no tests.” | Reject the result, correct the working directory or discovery command, and rerun. |
| “Only the happy path changed.” | Run the acceptance and regression gates discovered from the repository. |
| “Tests cannot run here, but the code looks correct.” | Mark the criterion unverified; do not report a pass. |
| “Local edit permission includes shipping.” | Commit, push, deploy, migrations, and production operations remain forbidden without explicit authority. |
