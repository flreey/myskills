---
name: project-truth
description: Use when a repository contains .project-truth/project.yaml and the user asks to inspect, implement, verify, review, or continue product capabilities, or explicitly mentions Project Truth, capability truth, receipts, coverage, or the truth dashboard. Drive work from validated machine state, record real evidence through the pinned CLI, rebuild the offline dashboard, and stop at authority, manual-acceptance, Git, deployment, or other external-action boundaries.
---

# Project Truth

Treat Project Truth as a deterministic engine and this Skill as its AI workflow adapter. Read
machine output; do not scrape the HTML dashboard or recompute truth in the model.

## Locate the project

Resolve this Skill directory and invoke bundled scripts by absolute path.

1. Find the nearest ancestor containing `.project-truth/project.yaml`.
2. If none exists, report that Project Truth is not initialized. `ptruth init` writes files, so
   propose its scope and wait for confirmation before running it.
3. Run the read-only context command before planning or reporting capability work:

```bash
python3 <skill-dir>/scripts/truth-context.py --root <repository>
```

The command validates authority and emits compact JSON from `ptruth status --json`. Treat an
invalid authority file, unsupported schema, Git error, or malformed output as a blocker.

## Choose the workflow

- For explanation, status, review, or planning requests, remain read-only and report the compact
  context. Do not write receipts or rebuild artifacts unless requested.
- For an existing Capability implementation, select one reviewed criterion or one explicit
  user-selected slice. Read its authority YAML and resolved binding paths before editing code.
- For a missing Capability, missing criterion, or `NO_REQUIRED_CRITERIA`, propose an authority
  change with bindings and observable acceptance behavior. Wait for confirmation; do not invent
  authority merely to make current code appear complete.
- For `MANUAL`, `CONFLICT`, or an authority mismatch, stop at the corresponding human review.

Read [evidence-boundaries.md](references/evidence-boundaries.md) before any state-changing
Project Truth command.

## Implement against authority

1. Preserve the project's own planning, testing, and permission rules.
2. Keep the change inside the selected Capability bindings and confirmed impact surface.
3. Establish the required public-seam test before behavior-changing implementation.
4. Run focused validation during implementation, but do not call ordinary test output a Project
   Truth PASS.
5. If implementation reveals that the authority is wrong or incomplete, stop and propose a
   versioned authority correction instead of weakening the test or fabricating evidence.

## Record evidence

For a confirmed command criterion, run the configured evaluator through the pinned engine:

```bash
<skill-dir>/scripts/ptruth run CAP-0001 AC-01 --root <repository>
```

This command executes the authority-owned command and writes an immutable Receipt. Preserve its
exit code and distinguish `PASS`, product failure, evaluator error, and configuration failure.

Never write Receipt JSON manually. Never use `accept` or `reject` to represent an agent decision.
Run a manual command only after the human explicitly supplies the decision and note in the current
conversation. Treat `revoke`, commit, push, deployment, publication, credentials, paid calls, and
live-environment actions as separate authorization boundaries.

## Rebuild and close the loop

After new evidence or confirmed authority changes:

```bash
<skill-dir>/scripts/ptruth status --root <repository> --json
<skill-dir>/scripts/ptruth build --root <repository>
python3 <skill-dir>/scripts/truth-context.py --root <repository>
```

Verify that standalone `state.json` and `coverage.json` validate and that the dashboard was built
from the same state. Do not edit `.project-truth/generated/` or `.project-truth/logs/` directly.

Report separately:

- implemented behavior;
- focused and regression tests;
- newly recorded Receipt IDs and resulting criterion states;
- Dashboard/read-model build result;
- manual, authority, dirty-worktree, discovery, Git, remote, or production boundaries still open.

Do not describe local tests as committed, pushed, deployed, released, provider-verified, or
production-verified evidence.
