# GitHub Manager–Developer Protocol

Use this protocol only after the execution contract is confirmed, the exact
model gate passes, and `scripts/select_transport.py` selects `github` or
`handoff-branch`.

## Actor Ownership

Codex is the repository manager:

- resolves and records the exact base SHA;
- creates the task branch from that SHA;
- opens and updates the Draft PR after the first valid developer commit;
- fetches immutable heads, reviews diffs, runs tests, and records evidence;
- sends correction evidence to the Pro conversation;
- never merges or deploys without separate authority.

ChatGPT Pro is the branch developer:

- reads only the assigned repository and task scope;
- commits only to the assigned task branch;
- never reads, modifies, or comments on another active task's branch;
- reports head SHA, commits, files, tests, and limitations;
- adds correction commits without rewriting observed history;
- does not create an Issue by default, manage secrets, merge, deploy, or change
  repository settings.

The user owns:

- the execution-contract confirmation;
- native ChatGPT/GitHub approval controls;
- authentication and account selection;
- any later authority for secrets, merge, deployment, or production access.

## Fast Preconditions

Record:

- repository identity and expected account;
- exact local `HEAD` and fetched remote refs containing it;
- whether the task depends on uncommitted source;
- current Codex manager write capability for the target repository;
- current ChatGPT Pro write capability or the latest same-account/repository
  proof;
- native connected-app state: `unknown`, `ready`, `prompt`, or `blocked`;
- exact GitHub operations authorized for this run.

Do not create a synthetic smoke branch for every task. A prior proof is a hint,
not standing authority. The first real task mutation is the action-time proof.
If it fails, record the native error and select an already authorized fallback.

## Authorization Closure

The normal GitHub closure may include:

- Codex creating one task branch from the recorded base;
- ChatGPT Pro reading the assigned source and adding task-scoped commits;
- Codex creating or updating one Draft PR;
- Codex and Pro reading branch, commit, PR, CI, and review state;
- task-scoped correction comments when useful;
- regular fast-forward head advancement through additive commits;
- local fetch, detached worktree creation, review, and tests.

It does not include:

- Issue creation unless separately listed;
- force-push, rebase of observed commits, or branch deletion;
- merge or auto-merge;
- tags, releases, deployments, migrations, settings, collaborators, Actions
  configuration, secrets, environments, or production data.

If a native GitHub confirmation appears, hand it to the user. Recommend
conversation-scoped approval for the personal workflow. Do not ask the user to
reconfirm the execution contract and do not choose a broader persistent
permission for them.

## Establish The Task Branch

Use a branch such as:

```text
codex/chatgpt-pro/<task-id>
```

Codex creates it from the exact recorded base SHA before dispatch. Verify the
resulting ref before telling Pro to modify it.

For concurrent work, every code-changing task has a distinct task branch and
registry-approved non-overlapping edit scopes. Different branch names do not
make overlapping files safe. Serialize tasks that share a parent/child scope,
dependency or lock file, workflow, migration, schema, generated contract, or
public interface.

If Codex cannot create the branch but Pro's live action surface can, Pro may
create the exact pre-authorized branch from the exact base SHA. Record the
actor and native approval. Do not silently give Pro a broader branch naming or
base choice.

## Reviewed Handoff Branch

Use `handoff-branch` only when the task needs local uncommitted source and the
user has authorized that exact source scope for GitHub publication.

1. Run `scripts/prepare_bundle.py` against only the approved paths.
2. Stop on secret findings, unsafe paths, unexpected binary content, or size
   policy failure.
3. Treat the manifest's file hashes as the immutable handoff inventory.
4. Create an isolated worktree from the recorded remote base.
5. Extract or copy only the scanned bytes into that worktree.
6. Recalculate and compare every file hash before staging.
7. Commit and push the reviewed inventory from the isolated worktree.
8. Keep the primary dirty worktree unchanged.

If any file changes after scanning, rerun the scanner. If the source must not
be published, use bundle transport instead.

## Developer Commits

The external brief supplies:

- repository;
- task branch;
- base SHA;
- allowed file scope;
- architecture and data boundaries;
- acceptance criteria and required tests;
- secret classification;
- forbidden operations.

Prefer one atomic multi-file commit when blob/tree/commit/ref actions are
available. Otherwise a small sequence of file commits is acceptable. Each
commit must stay inside the task scope.

Require additive commits after Codex has recorded a head. A force-pushed or
rebased branch invalidates prior evidence; preserve the old head, record the
new one, and restart source-identity verification.

## Draft PR Ownership

After the first valid Pro commit:

1. Codex verifies that the head descends from the expected base.
2. Codex inspects the changed-file inventory for obvious scope violations.
3. Codex creates one Draft PR against the agreed base.
4. Codex records the PR URL, base SHA, head SHA, commits, and files.
5. Later Pro corrections advance the same PR through additive commits.

The PR body contains the requirement, acceptance criteria, current validation
status, and explicit unverified risks. Private ChatGPT conversation URLs,
local absolute paths, secret metadata, and internal logs do not belong in the
PR.

## Local Synchronization And Verification

Never pull, merge, or check out the task branch over the user's primary dirty
worktree merely to inspect it.

For each observed head:

1. resolve the branch and PR head SHA;
2. confirm it descends from the expected base;
3. fetch that exact SHA;
4. create a detached disposable worktree;
5. persist a binary-safe base-to-head diff;
6. record diff bytes and SHA-256;
7. inspect commits, files, dependencies, lock files, executable workflows,
   scripts, migrations, network behavior, and secret/data boundaries;
8. run every repository-required gate.

If the head changes during validation, preserve old evidence, fetch the new
head, regenerate the diff identity, and rerun from the earliest invalidated
gate.

## Correction Loop

Send one evidence packet in the same Pro conversation:

- failed acceptance criterion;
- exact command, working directory, and exit status;
- minimal redacted log excerpt;
- file and line location;
- correct repository constraint;
- smallest complete requested correction.

Pro adds normal commits to the same branch. Codex records the new head and
revalidates. Neither actor sends secret values or broadens the task to make a
test pass.

## Completion Boundary

Independent validation changes the task to `validated-draft`; it does not
merge, close, delete, release, deploy, or verify production.

Final reporting distinguishes:

- task branch created and by which actor;
- commits pushed and current head;
- Draft PR created;
- locally fetched and tested;
- locally integrated;
- merged;
- deployed;
- production verified.
