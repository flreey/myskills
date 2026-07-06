# review-fix-push

`review-fix-push` is a lightweight delivery skill for the phrase: "review this, fix clear issues, then commit and push."

It is not a release workflow and does not create PRs by default. Its job is to prevent the two common failures in this flow:

- committing/pushing before a real review
- reviewing only tracked diffs and missing untracked files or unpushed commits

## Quick Preflight

```bash
./scripts/preflight.sh /path/to/repo
```

This is read-only. It reports:

- branch, upstream, remote
- staged, unstaged, and untracked files
- unpushed commits
- suspicious files that need review before staging
- likely verification commands

## Default Behavior

1. Review the whole delivery surface.
2. Auto-fix clear issues.
3. Ask only for judgment calls.
4. Run fresh verification.
5. Stage only reviewed files.
6. Commit one logical change.
7. Push the current branch with a regular push.

No force push, no automatic rebase/pull, no PR unless explicitly requested.
