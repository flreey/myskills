# Evidence and authority boundaries

## Source hierarchy

Use these sources in order:

1. `.project-truth/project.yaml`, `outcomes.yaml`, and `capabilities/*.yaml` are reviewed
   authority.
2. Repository files matched by bindings are the observed implementation subject.
3. `receipts/` and `revocations/` are immutable evidence history.
4. `ptruth status --json` is the current derived truth.
5. `generated/state.json`, `coverage.json`, and `index.html` are rebuildable projections.

Never edit generated files to change truth. Never treat prose, an issue checkbox, a previous chat,
or the Dashboard appearance as stronger evidence than current authority, subjects, and Receipts.

## Command effects

| Command | Effect | Boundary |
| --- | --- | --- |
| `validate` | Reads and validates authority, evidence, bindings, and Git state | Read-only |
| `status --json` | Derives current truth | Read-only |
| `init --dry-run` | Lists the initial authority layout without creating it | Read-only |
| `build` | Replaces only the configured generated artifact set | Local generated write |
| `run` | Executes one authority-owned command and creates an immutable Receipt/log | Evidence write |
| `accept` / `reject` | Records an explicit human decision | Human decision required |
| `revoke` | Invalidates historical evidence without deleting it | Explicit authorization required |
| `init` | Creates initial authority layout without overwriting non-empty content | Confirm the preview and scope before use |

Commit, push, pull request, deployment, publication, database, credential, paid-provider, and live
environment actions remain outside Project Truth command authorization.

## State handling

- `PASS`: current applicable evidence satisfies the criterion; it does not imply committed,
  pushed, deployed, or production-verified delivery.
- `FAIL`: current evidence observed a product failure. Fix the behavior, then rerun the configured
  evaluator.
- `UNKNOWN`: evidence is missing or the required definition is absent. Do not rewrite it as PASS.
- `STALE`: evidence no longer matches current versions, bindings, subject digests, or validity
  window. Rerun the reviewed evaluator when appropriate.
- `CONFLICT`: equally applicable evidence disagrees. Stop for evidence-source review.
- `MANUAL`: an explicit human decision is required. An agent must not self-accept.

`DIRTY_WORKSPACE` is a delivery fact, not a test failure. `DISCOVERY_NOT_RUN` and repository
completeness `unknown` mean the defined Capability set is not a claim of whole-repository coverage.

## Version changes

Change definition, criterion, or binding versions when their semantics change. Existing Receipts
may then become stale by design. Do not preserve a green Dashboard by retaining an old version for
a materially changed acceptance contract.

The bundled runner pins Project Truth commit
`bdd1fb1a04d6a2abc44fb1fca9d078157a851139`. Update the pin only after the new engine commit passes
its full test suite and the Skill is forward-tested against its supported status schema.
The first uncached invocation needs `uvx`, private-repository access, and network connectivity.
After the exact revision is cached, the runner prefers an offline invocation and does not refresh
from a branch or floating tag.
