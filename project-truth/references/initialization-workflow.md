# Initialization workflow

Read this file only when `truth-context.py` emits `project-truth/bootstrap-context@1`.

## Contents

- [1. Assess without writing](#1-assess-without-writing)
- [2. Propose the bootstrap contract](#2-propose-the-bootstrap-contract)
- [3. Preview, confirm, and initialize](#3-preview-confirm-and-initialize)
- [4. Draft proposed Authority](#4-draft-proposed-authority)
- [5. Validate the first read model](#5-validate-the-first-read-model)

## 1. Assess without writing

Use the bootstrap context as inventory, then read only the relevant manifest, repository
instructions, README, PRD, specs, and tests. Do not claim that file discovery proves a Capability.

Stop and resolve these conditions before initialization:

- `NON_EMPTY_PROJECT_TRUTH_ROOT`: preserve the directory and inspect why it is partial.
- `UNBORN_HEAD`: explain that validation requires a Git commit; committing remains separately
  authorized.
- multiple or zero supported languages: ask the human to choose `python` or `typescript`.
- detached HEAD or an uncertain default branch: confirm the intended default branch.

## 2. Propose the bootstrap contract

Present one initialization plan containing:

- repository root, project ID, display name, default branch, remote name (or `null`), and target
  language;
- Dashboard locale (`zh-CN` for Simplified Chinese when requested, otherwise `en`);
- proposed Product Intent, Journey, Feature, Outcome, and Capability boundaries derived from
  reviewed project intent;
- each Capability's bindings and observable command/manual criteria;
- whether generated state and raw logs should be committed or ignored;
- files to create or modify and commands used for validation.

Treat these as proposals. Do not infer completion, approve Authority, or record evidence from
existing code during bootstrap.

## 3. Preview, confirm, and initialize

Run the no-write preview first:

```bash
<skill-dir>/scripts/ptruth init \
  --project-id <id> \
  --name <name> \
  --default-branch <branch> \
  --language <python-or-typescript> \
  --root <repository> \
  --dry-run
```

Show the planned paths and wait for confirmation. After confirmation, rerun without `--dry-run`.
Never remove or overwrite a non-empty `.project-truth/` directory.

## 4. Draft proposed Authority

Initialization creates a `project@2` authority, one placeholder `proposed` Product Intent, one
example `proposed` Outcome, and no Journey, Feature, or Capability. Replace the placeholders with
project-specific proposals and create Product/Capability definitions only within the confirmed
scope.

Use these authoring rules:

- IDs are stable: `JNY-0001`, `FEAT-0001`, `OUT-0001`, `CAP-0001`, `BIND-*`, and `AC-*`.
- Start versions at `1`; increment the changed definition, binding, or criterion later.
- Keep Product Intent, Journey, Feature, Outcome, and Capability lifecycle `proposed` until the
  human explicitly reviews them.
- Map each active Product Feature to explicit Capability criteria; Product Feature state must be
  derived from those criteria and must never be declared manually.
- Bind only repository-relative paths. Include public entry points, implementation, configuration,
  integration, and tests when they materially define the behavior.
- Prefer command criteria that exercise a public seam. Use `binding_resolves` for path presence and
  `manual` only for behavior that genuinely needs human judgment.
- An `active` Capability must contain at least one required criterion.
- Never weaken criteria to match current implementation and never mark a proposal complete.

Minimal Capability shape for the pinned `project-truth/capability@2` schema:

```yaml
schema: project-truth/capability@2
id: CAP-0001
name: Example capability
slug: example-capability
definition_version: 1
lifecycle: proposed
kind: product
statement: Describe observable behavior.
outcomes: [OUT-0001]
aliases: []
dependencies: []
bindings:
  - id: BIND-ENTRY
    version: 1
    kind: cli
    role: entrypoint
    required: true
    watch: [src/example.ts]
acceptance:
  - id: AC-CMD
    version: 1
    name: Public command verifies the behavior
    dimension: verification
    required: true
    evaluator:
      kind: command
      command: pnpm test -- example
      cwd: .
      timeout_seconds: 300
      pass_exit_codes: [0]
    subjects: [BIND-ENTRY]
    source_policy: {mode: all}
superseded_by: []
```

Adapt binding kind, paths, command, and language to the repository. Do not copy the example as
project truth without reviewing every field.

## 5. Validate the first read model

After the confirmed draft is written:

```bash
<skill-dir>/scripts/ptruth validate --root <repository>
<skill-dir>/scripts/ptruth build --root <repository>
python3 <skill-dir>/scripts/truth-context.py --root <repository> --pretty
```

Verify that the context is now `project-truth/skill-context@1`, the Dashboard locale and policy
match the reviewed plan, proposed definitions remain visibly unverified, and no Receipt was
created. Ask for explicit Authority review before changing lifecycle to `active` or executing its
criteria.
