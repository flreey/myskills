# Validation - hook-template-builder

Date: 2026-07-06
Classification: Mixed discipline/knowledge skill. Discipline part is the confirmation gate: agents are tempted to install hooks immediately, over-block, or mix Codex/Claude schemas.

## Pre-Registered Deltas

1. Without the skill, an agent may jump to writing hook config; with the skill, it scans first and presents a decision table before generation or installation.
2. With the skill, "generated template" and "installed active hook" are distinct states; installation must write to a loaded hook config and pass activation checks.
3. With the skill, existing hooks are audited and merged rather than overwritten.
4. With the skill, reminder hooks are default, while blocking/global/network hooks require explicit confirmation.
5. With the skill, Codex and Claude templates are generated from separate references and not mixed.
6. With the skill, deterministic pre-commit/merge checks are routed to git hooks or CI instead of agent hooks.
7. Negative case: a React hook or product webhook request should not trigger agent-hook generation.

## Smoke Validation

Static and scanner checks run:

- `bash -n hook-template-builder/scripts/scan-project-hooks.sh` - PASS.
- `hook-template-builder/scripts/scan-project-hooks.sh /Users/flreey/Projects/myskills` - PASS; reports no common manifest, existing Claude settings, default recommendations, existing hook surfaces, and existing-hook audit.
- Temporary Node/React-like project with `package.json`, `pnpm-lock.yaml`, GitHub Actions, Vitest, and Playwright - PASS; detects npm scripts, CI, dependency reminder, test reminder, and CI parity reminder.
- Temporary Python project with `pyproject.toml`, `pytest.ini`, `uv.lock`, and Ruff config - PASS; detects `pytest`, `ruff check`, and `ruff format --check`.
- Temporary Rust/Go project with `Cargo.toml` and `go.mod` - PASS; detects cargo and go command reminders.
- Temporary empty project - PASS; emits default hooks only and no project-specific command claims.

Template dry-runs:

- Dangerous shell warning sample matched `git push --force origin main` and `git push origin --force`, and stayed quiet for `rm ./tmp.txt` / ordinary push.
- Dependency change reminder sample matched `package.json` and stayed quiet for `README.md`.
- Existing hook surface smoke: scanner lists `.codex/hooks.json`, `.claude/settings*.json`, `.codex/hooks/`, `.claude/hooks/`, `.husky/`, `lefthook.yml`, and `.pre-commit-config.yaml` when present; project-install flow requires merge and activation checks instead of overwrite.

## Result

Deliverable for initial use. The skill enforces scan-first and confirmation-first behavior, separates template generation from active installation, defaults to reminder hooks, requires existing-hook merge checks, routes deterministic checks to CI/git hooks, and keeps Codex/Claude templates separate. Full A/B subagent validation is still recommended before publishing as a hardened public release.
