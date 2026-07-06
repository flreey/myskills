---
name: review-fix-push
description: "Use when the user asks to review current code changes, fix any clear issues, then commit and push: 'review 一下没问题就提交 push', '检查代码有问题修掉然后 commit push', '修到完成再推', or '无法决定的问我'. NOT for opening PRs by default, release shipping, CI-only debugging, or force-push workflows."
---

# Review Fix Push

## Premises

- Default target: current branch, regular `git push`, no PR.
- Reusable across projects. Project-specific verification commands must come from the target repo's manifests, CI, instructions, or existing scripts.
- Checked on 2026-07-06 against the user's repeated preference: real diff review first, fix concrete issues, fresh verification, then commit and push.
- Superpowers `requesting-code-review` and `receiving-code-review` may be used when available for independent review and feedback handling, but this skill owns the working-tree audit, fix loop, commit, and push safety.

## First Reflex

When triggered, do not ask "should I review?" and do not jump to `git add`.

Immediately establish the complete delivery surface:

```bash
review-fix-push/scripts/preflight.sh .
```

If the skill is installed elsewhere, use the absolute path to `scripts/preflight.sh`.

The preflight is read-only. It reports branch/upstream, dirty files, untracked files, unpushed commits, suspicious artifacts, and likely verification commands.

## Workflow

### 1. Define Scope Before Review

Review all changes that would be committed or pushed:

- staged diff
- unstaged tracked diff
- untracked files that are not ignored
- unpushed commits on the current branch

If there is no dirty working tree and no unpushed commit, stop with "nothing to commit or push."

If there are unpushed commits not created in this task, still review them because `git push` will publish them. If ownership is unclear or the branch contains unrelated work, ask before pushing.

### 2. Review First

Read the full diff before flagging anything:

```bash
git diff --cached
git diff
git ls-files --others --exclude-standard
```

For untracked text files, inspect their contents before deciding to stage them. For untracked binary, archive, DB, log, or large files, treat as ASK unless the user explicitly requested them.

When superpowers review skills are available:

- Use `requesting-code-review` for an independent review of the complete scope.
- Use `receiving-code-review` rules when handling reviewer feedback: verify against the codebase before implementing, push back on incorrect suggestions, and ask when unclear.

When superpowers are unavailable, perform the same local review yourself.

Review must include:

- behavioral bugs and regressions
- security and secret leakage
- missing or stale tests
- script, README, docs, examples, comments, and CLI usage drift
- migration/backward-compatibility risks
- new files and untracked files
- generated/runtime artifacts that should not be committed

### 3. Classify Findings

Every finding gets one of these decisions:

| Class | Apply when | Action |
|---|---|---|
| `AUTO-FIX` | Clear bug, typo, stale docs/script comment, formatting issue, missing import, obvious test update, deterministic config drift | Fix immediately |
| `ASK` | Product behavior choice, public API change, data migration, destructive operation, security tradeoff, suspicious secret, unclear ownership, unrelated branch history | Stop and ask |
| `SKIP` | Reviewer suggestion is incorrect, already handled, or irrelevant after code inspection | Record concise reason |

Critical rule: never convert an `ASK` item into an `AUTO-FIX` just to keep moving.

### 4. Fix Until Clean

Apply all `AUTO-FIX` items, then re-run the relevant review and verification.

Loop until:

- no `AUTO-FIX` findings remain, and
- verification passes, and
- no `ASK` blockers remain.

If the same issue fails three times, stop and ask with the exact failure output and attempted fixes.

### 5. Fresh Verification

Use commands from the target repo, in this priority order:

1. user-provided command
2. repo instructions (`AGENTS.md`, `CLAUDE.md`, README, task plan)
3. CI workflow commands
4. manifest scripts (`npm test`, `npm run build`, `pytest`, `cargo test`, `go test ./...`, etc.)
5. fallback hygiene (`git diff --check`)

If code changed after a verification run, rerun the affected verification before committing. Never push with stale verification evidence.

If verification cannot run because dependencies or credentials are missing, report the blocker and ask before committing unless the user explicitly allowed best-effort commits.

### 6. Stage Safely

Stage only reviewed, intended files:

```bash
git add <reviewed-files>
```

Do not stage with `git add -A` until you have compared the full status and excluded suspicious artifacts.

Never commit:

- real secrets (`.env`, private keys, tokens, certificates)
- local DBs, SQLite files, logs, dumps
- build output, caches, coverage output
- editor/OS junk
- unrelated files not covered by review

Safe templates such as `.env.example` may be committed only after checking they contain placeholders, not real values.

### 7. Commit

Default to one logical commit. Ask before splitting unless the diff clearly contains unrelated work.

Commit message should summarize the actual reviewed change, not "update" or "fix stuff":

```bash
git commit -m "<type>: <concise reviewed change>"
```

If there are no staged changes after review/fix, do not create an empty commit.

### 8. Push

Push the current branch with a regular push:

```bash
git push
```

If there is no upstream:

```bash
git push -u origin "$(git branch --show-current)"
```

Never force push. If push is rejected because of non-fast-forward, remote divergence, auth failure, protected branch, or missing remote, stop and ask. Do not auto-rebase, auto-pull, or change branch history.

## Output Contract

Final response must include:

- review result: no issues / auto-fixed / ASK blocked
- files committed
- verification commands and pass/fail summary
- commit SHA
- push remote and branch
- any skipped or deferred issues

If blocked before commit/push, include:

- blocker
- why it cannot be decided safely
- exact user decision needed

## Optional Modes

Only use these when the user explicitly asks:

- `no-push`: commit only.
- `pr`: after push, create or update a PR.
- `split-commits`: group by logical changes and commit separately.
- `full-ship`: hand off to a release/ship workflow instead of this lightweight flow.

## Hard Stops

Stop and ask before commit or push when:

- a suspected secret or local artifact is in scope
- branch contains unrelated or unclear unpushed commits
- verification fails and no deterministic fix remains
- a reviewer finding requires product, API, migration, or risk judgment
- push would require force, rebase, merge, pull, or auth changes
- target branch is main/master/default and the repo convention is unclear

## Recovery

If a bad commit was created but not pushed, use a non-destructive fix-forward commit by default. Only rewrite history if the user explicitly asks.

If a bad commit was pushed, do not force push. Create a follow-up fix commit unless the user explicitly chooses a history rewrite and understands the remote impact.
