# GitHub Transport Protocol

Use this protocol only after `scripts/select_transport.py` selects
`github-pr` or `github-issue-patch`.

## Preconditions

Record evidence for all of the following:

- the configured remote name, without copying credential-bearing remote URLs
  into reports;
- exact local `HEAD`;
- freshly fetched remote refs containing that commit;
- whether the task depends on uncommitted source;
- ChatGPT's repository capability observed in the live product surface:
  `read`, `write`, or `none`;
- every authorized GitHub mutation for this run.

Fetching remote refs is local synchronization, not permission to change the
remote. Existing repository access, an installed integration, or an earlier
task does not authorize the current run.

If the task depends on uncommitted source, stop GitHub transport and use the
bundle path. Do not create and push a WIP handoff commit as a workaround.

## Least-Privilege Authority

`github-pr` requires explicit authority for:

- ChatGPT GitHub source access;
- one task Issue;
- one task branch;
- task-scoped commits and regular pushes;
- one Draft PR;
- task-scoped Issue and PR comments.

`github-issue-patch` requires explicit authority for:

- ChatGPT GitHub source access;
- one task Issue;
- task-scoped Issue comments.

Neither mode authorizes:

- merge or auto-merge;
- force-push;
- remote branch deletion;
- releases or tags;
- Actions, repository settings, collaborators, secrets, environments, or
  protection-rule changes;
- deployment, migration, production configuration, or real user data.

## Issue As The Task Contract

Create one Issue only after the selected transport and authority ledger are
persisted. The Issue must contain a sanitized form of the engineering brief:

- task ID, background, and goal;
- exact base commit;
- architecture boundaries and allowed file scope;
- required tests and truthful test-claim boundary;
- forbidden operations;
- acceptance criteria;
- required deliverable mode.

Do not publish local absolute paths, private ChatGPT conversation URLs,
credentials, raw secret-scan findings, internal logs, or unrelated dirty-state
filenames.

Record the Issue URL and immutable Issue number in the private run ledger.

## `github-pr` Delivery

Use a task branch such as:

```text
codex/chatgpt-pro/<task-id>
```

The protected base branch remains untouched. Require a Draft PR whose base is
the agreed base branch and whose history descends from the recorded base
commit.

The Draft PR or external report must identify:

- base commit SHA;
- current head commit SHA;
- commit inventory;
- changed-file inventory;
- implementation and acceptance mapping;
- test commands actually run, their results, and limitations;
- unresolved assumptions and risks.

Prefer additive correction commits. A force-pushed or rebased head invalidates
previous artifact identity. Preserve the old head SHA, record the new one, and
restart verification from source identity.

Do not treat branch name, PR number, green checks, review approval, or
ChatGPT's summary as immutable code identity. The recorded head SHA is the
artifact.

## `github-issue-patch` Delivery

ChatGPT may read the exact remote baseline but may not mutate repository code.
Require a downloadable patch or changed-files archive through the ChatGPT
conversation. Verify its bytes and SHA-256 exactly as in bundle mode.

Do not let read-only repository access become implied branch, commit, push, or
PR authority. Codex may later publish a validated patch only when those
operations receive separate authorization.

## Local Synchronization And Verification

Synchronize by fetching remote refs. Never pull, merge, or check out the task
branch over the user's primary worktree.

For `github-pr`:

1. resolve and record the Draft PR base and head SHAs;
2. confirm the head descends from the expected base;
3. create a detached worktree at the exact head;
4. persist a binary-safe base-to-head diff in the private run directory;
5. record diff byte size and SHA-256;
6. inspect commits, changed files, dependencies, lock files, executable
   workflows, migrations, network behavior, and data boundaries;
7. run all required repository gates from the detached worktree.

For `github-issue-patch`, create the detached worktree at the recorded remote
baseline and apply only the verified artifact.

If the PR head changes during validation, discard no evidence. Record the
superseded head, fetch the new head, regenerate the diff hash, and rerun from
the earliest invalidated gate.

## Correction Loop

Send one evidence packet in the ChatGPT conversation and, when authorized, the
Draft PR or Issue:

- failed acceptance criterion;
- exact command, working directory, and exit status;
- minimal relevant log excerpt;
- file and line location;
- correct repository constraint;
- requested smallest complete correction.

For `github-pr`, require new additive correction commits and record the new head
SHA. For `github-issue-patch`, require a replacement artifact and new hash.

## Completion Boundary

Passing independent validation changes the run state to `passed`; it does not
merge, close the Issue, delete the branch, release, or deploy.

Final reporting must separately state:

- Issue created;
- branch created;
- commits pushed;
- Draft PR created;
- locally fetched and tested;
- locally integrated;
- merged;
- deployed;
- production verified.

Only report a state that actually occurred in the current run.
