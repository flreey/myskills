---
name: project-truth
description: Use to initialize Project Truth in a new or existing Git repository, inspect capability status, update reviewed authority, implement or continue capabilities, record receipts, handle human acceptance, and rebuild the truth dashboard. Trigger when the user invokes $project-truth, asks what is complete or next, or mentions Project Truth, capability truth, authority, criteria, receipts, coverage, or the truth dashboard. Drive work from validated machine state and stop at authority approval, manual acceptance, Git, deployment, and other external-action boundaries.
---

# Project Truth

Use one `$project-truth` entry point for the complete truth lifecycle. Treat Project Truth as the
deterministic engine and this Skill as its workflow router. Read machine output; never scrape the
HTML dashboard or recompute truth in the model.

## Inspect first

Resolve this Skill directory and run the same read-only command for every invocation:

```bash
python3 <skill-dir>/scripts/truth-context.py --root <repository>
```

Route by its schema:

- `project-truth/bootstrap-context@1`: the Git repository is uninitialized. Read
  [initialization-workflow.md](references/initialization-workflow.md) and follow it.
- `project-truth/skill-context@1`: authority is initialized and validated. Continue from its work
  queue and the user's intent.
- Command failure: report the exact validation, schema, Git, or engine blocker; do not guess.

If the user invokes only `$project-truth`, inspect and continue the next safe step. Stay read-only
when the next step requires confirmation.

## Route the lifecycle

Use Project Truth as the control and evidence layer, not as a replacement for specialist process
Skills.

| Situation | Action |
| --- | --- |
| Uninitialized repository | Assess, propose parameters and Authority scope, dry-run, then wait |
| Explanation, status, or review | Report compact machine context without writing |
| Missing Product mapping, Capability, criterion, or required dimension | Propose a versioned Authority change and wait |
| Reviewed actionable criterion | Select one slice and use the project's matching implementation flow |
| Product failure or runtime mismatch | Use the matching investigation flow before rerunning evidence |
| `MANUAL` or `CONFLICT` | Stop for the required human decision or evidence-source review |
| New evidence or confirmed Authority change | Rebuild state and Dashboard, then reread context |

For implementation, preserve repository instructions and choose only one matching primary process
Skill for the current stage. Project Truth retains ownership of Capability selection, Authority,
bindings, criteria, Receipts, and final truth reporting.

## Change Authority carefully

Read the current Product Intent, Journeys, Features, Outcomes, Capabilities, criteria, and resolved
binding paths before proposing an update. Describe observable behavior and affected paths. Never
invent Authority to make current code appear complete.

Wait for confirmation before creating or changing Authority files. Keep new definitions
`proposed` until the human reviews their meaning. When semantics change, increment the applicable
definition, criterion, or binding version; allow previous evidence to become stale.

Read [evidence-boundaries.md](references/evidence-boundaries.md) before any state-changing Project
Truth command.

## Implement against Authority

1. Select one reviewed criterion or one explicit user-selected slice.
2. Keep changes inside confirmed bindings and impact surface.
3. Establish the required public-seam test before behavior-changing implementation.
4. Run focused and regression validation, but do not call ordinary test output a Project Truth
   PASS.
5. If Authority is wrong or incomplete, stop and propose a versioned correction instead of
   weakening tests or fabricating evidence.

## Record evidence

For a confirmed command criterion, use the pinned engine:

```bash
<skill-dir>/scripts/ptruth run CAP-0001 AC-01 --root <repository>
```

Preserve the exit code and distinguish `PASS`, product failure, evaluator error, and configuration
failure. Never write Receipt JSON manually. Never use `accept` or `reject` as an agent decision;
run one only after the human explicitly supplies the decision and note in the current conversation.

Treat `revoke`, commit, push, deployment, publication, credentials, paid calls, live environments,
and an engine pin upgrade as separate authorization boundaries.

## Rebuild and close the loop

After new evidence or confirmed Authority changes:

```bash
<skill-dir>/scripts/ptruth status --root <repository> --json
<skill-dir>/scripts/ptruth build --root <repository>
python3 <skill-dir>/scripts/truth-context.py --root <repository>
```

Verify standalone `state.json` and `coverage.json` and confirm the Dashboard was built from the
same state. Never edit `.project-truth/generated/` or `.project-truth/logs/` directly.

Report separately:

- implemented behavior and focused/regression tests;
- Product Feature to Capability and criterion traceability, including derived Feature state;
- Receipt IDs and resulting criterion states;
- Dashboard/read-model build result;
- remaining manual, Authority, dirty-worktree, discovery, Git, remote, or production boundaries.

Never describe local tests as committed, pushed, deployed, released, provider-verified, or
production-verified evidence.
