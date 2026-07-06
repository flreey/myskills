---
name: hook-template-builder
description: "Use when the user wants agent hooks for Codex or Claude Code: scan a project, recommend safety/productivity hooks, generate hook templates, or decide whether a rule belongs in hooks, git hooks, CI, or project instructions. NOT for React hooks or product webhooks."
---

# Hook Template Builder

## Premises

- Default target: Codex hooks first, Claude Code templates only when requested or clearly needed.
- Checked on 2026-07-06 against Codex CLI 0.142.5 and current OpenAI/Anthropic hook docs. Re-check official docs before installing hooks globally or using a field not present in this skill's references.
- Hooks can execute shell commands. Treat every generated hook as executable code that needs review, dry-run tests, and user confirmation before installation.
- This skill is reusable across projects; project-specific rules belong in the target project's `AGENTS.md`, `CLAUDE.md`, CI, or local hook config.

## First Reflex

When the user asks for hooks, decide the hook type before doing anything else:

| User intent | Destination |
|---|---|
| Agent should warn, block, log, or remind during Codex/Claude work | This skill |
| Deterministic check before commit/push | Git hook or CI, with this skill only generating a helper template if asked |
| App receives HTTP callbacks | Product webhook implementation, not this skill |
| React state/effect reuse | React hook implementation, not this skill |
| One repository convention | Project `AGENTS.md`/`CLAUDE.md` plus optional project hook |

If the intent is agent hooks, scan first, propose second, generate/install only after confirmation.

## Hard Rule: Installed Means Loaded

Do not call generated files "installed" unless they are placed in a hook location that the target agent actually loads and the installed config references the generated scripts.

Use these labels precisely:

| Label | Meaning |
|---|---|
| Template generated | Files exist in a docs/temp/generated folder only; no agent will run them automatically. |
| Project-installed | Files are written into the current repo's agent hook location and merged into the repo-level hook config or settings that the target agent reads. |
| Global-installed | Files are written into the user's global agent config/plugin/skill location and affect more than one repo. Requires second confirmation. |

After project or global install, run the activation checks in this skill. If the agent cannot prove the hook is referenced by a loaded config, say "generated but not active" and do not claim success.

## Workflow

### 1. Read-Only Project Scan

Run the bundled scanner from the project root when a repository is available:

```bash
hook-template-builder/scripts/scan-project-hooks.sh .
```

If the skill is installed elsewhere, use the absolute path to the script. The scanner is read-only and reports:

- languages and package managers
- likely test, lint, format, build, and e2e commands
- CI files
- `AGENTS.md` / `CLAUDE.md`
- existing Codex, Claude, git, and package-manager hooks
- recommended hook candidates grouped by risk

If the script cannot run, manually inspect only these sources: manifests, lockfiles, CI files, existing hook configs, `AGENTS.md`, `CLAUDE.md`, and package scripts. Do not scan unrelated large directories.

### 2. Existing Hook Audit

Before proposing install changes, inspect existing hook surfaces and summarize them. Never overwrite an existing hook config without merging.

Check at minimum:

| Platform | Project-level surfaces | Global surfaces |
|---|---|---|
| Codex | `.codex/hooks.json`, `.codex/hooks/`, repo-local plugin/skill hook files if present | `~/.codex/config.toml`, `~/.codex/skills/`, `~/.codex/plugins/cache/*/*/*/hooks/` |
| Claude Code | `.claude/settings.json`, `.claude/settings.local.json`, `.claude/hooks/`, skill frontmatter `hooks:` | `~/.claude/settings.json`, `~/.claude/skills/`, `~/.claude/plugins/cache/*/*/*/hooks/` |
| Git | `.git/hooks/*`, `.husky/*`, `lefthook.yml`, `.pre-commit-config.yaml`, package manager hook config | n/a |

For every existing hook, report:

- event name
- matcher
- command
- behavior if obvious: reminder, blocker, logger, notifier
- whether it overlaps a proposed hook

Conflict rules:

- Same event + same matcher + same command: duplicate; do not add another copy.
- Same event + same matcher + different command: merge by appending, preserving existing order.
- Existing blocking hook on the same event: high-risk; stop and ask unless the new hook is reminder-only and clearly independent.
- Invalid JSON/TOML/YAML or unreadable config: stop and ask before modifying.
- Unknown schema: generate a template and ask for confirmation before install.

### 3. Produce a Decision Table

Before writing hook files or installing anything, show a table with these columns:

| Hook | Event | Behavior | Evidence | Existing-hook impact | False-positive risk | Recommendation |
|---|---|---|---|---|---|---|

Group candidates as:

- **Default recommended:** reminder/logging hooks that do not block work.
- **Project-specific:** commands inferred from manifests or CI.
- **High-risk confirmation required:** anything that blocks a command, blocks a file edit, changes global config, or sends data outside the machine.
- **Do not use hooks:** rules better handled by CI, git hooks, tests, or project instructions.

### 4. Confirmation Gate

Never silently install hooks. Ask the user to choose:

- hook list to enable
- platform: Codex, Claude Code, or both
- install mode: template only, project install, or global install
- behavior: remind, block, log, or notify

Defaults when the user says "use the defaults":

- Enable reminder/logging hooks only.
- Project-install the selected reminder hooks when the user explicitly asked for usable hooks.
- Generate templates only when the user asks for templates, preview, dry-run, or "do not install".
- Do not modify global config.
- Do not enable blocking hooks.
- Do not send network requests.

### 5. Generate or Install

Use the reference templates:

- Codex: `references/codex-hook-templates.md`
- Claude Code: `references/claude-hook-templates.md`

Template output must include:

- hook config snippet or file
- script body
- sample payload
- dry-run command
- install and uninstall commands
- note explaining whether the hook is reminder, blocker, logger, or notifier

Project install output must additionally:

- write scripts to the repo-local hook script directory (`.codex/hooks/` or `.claude/hooks/`)
- merge hook entries into the repo-local loaded config/settings instead of replacing existing entries
- preserve all existing hook entries and formatting as much as practical
- report exactly which file now loads each hook
- run dry-runs for every installed script
- run an activation proof: parse config, verify commands point to existing executable scripts, and explain whether a new agent session or trust prompt is required before first run

Prefer small scripts over long inline commands. Scripts must be deterministic, portable to macOS/Linux, and safe when expected environment variables are missing.

### 6. Activation Checks

After install, check:

| Check | Required result |
|---|---|
| Config parse | Hook config/settings parse successfully. |
| Reference check | Every generated command in config points to an existing script. |
| Permission check | Scripts are executable or invoked with `bash`. |
| Duplicate check | No identical hook command was added twice to the same event/matcher. |
| Dry-run | Positive sample emits the expected reminder/block; negative sample stays quiet. |
| Load caveat | If the agent requires a new session, trust approval, or settings reload, say so explicitly. |

Only after all checks pass may you say "installed and ready for next agent session." If any check fails, fix it or downgrade the result to "generated but not active."

## Default Hook Candidates

Recommend these for most coding repositories:

| Hook | Default behavior | Confirmation rule |
|---|---|---|
| Dangerous shell command guard | Warn on `rm -rf`, `git reset --hard`, force-push, `DROP DATABASE`, production deploy commands | Blocking requires explicit confirmation |
| Secret file / secret-looking edit guard | Warn on real secret files and key-like content | Do not warn on `.env.example` unless it contains real-looking values |
| Dependency manifest reminder | After manifest/lockfile edits, remind to install dependencies and run relevant tests | Reminder only by default |
| Large/generated artifact reminder | Warn on large files, logs, DB files, build outputs, archives | Reminder only by default |
| Stop-time status reminder | At stop, remind about dirty diff, unrun tests, or stale plan files | Reminder only by default |

Project-specific candidates come from scan evidence:

| Project signal | Candidate |
|---|---|
| `package.json` scripts | Remind with `npm test`, `npm run build`, `npm run lint`, `npm run format`, or detected package-manager equivalents |
| `pytest.ini`, `pyproject.toml`, `ruff.toml` | Remind with `pytest`, `ruff check`, `ruff format --check` |
| `Cargo.toml` | Remind with `cargo test`, `cargo fmt --check`, `cargo clippy` |
| `go.mod` | Remind with `go test ./...`, `gofmt` check |
| Playwright/Vitest/Cypress dependency | Add optional e2e/unit-test reminder |
| CI workflow | Mirror CI commands as reminders, not blockers, unless the user asks for enforcement |

## What Not To Encode

Do not put these in agent hooks unless the user explicitly confirms the tradeoff:

- slow full-suite tests on every file edit
- business-specific semantic judgments written as shell regex
- global hooks that only make sense for one project
- network notifications containing file paths, prompts, diffs, or secrets
- hooks that mutate source files automatically
- hook configs copied from Claude to Codex or from Codex to Claude without adapting schema

If a rule is fully deterministic and belongs before commit, propose a git pre-commit hook or CI check instead. If a rule is explanatory or project-specific, propose `AGENTS.md` or `CLAUDE.md`.

## Review Checklist

Before presenting generated hooks as ready:

- The scan evidence is named; no recommendation appears without a source or default rationale.
- Every blocking hook has an alternative action and explicit user confirmation.
- Every generated script has a non-match sample proving it stays quiet.
- Install and uninstall commands are present.
- Global install instructions include a second confirmation warning.
- Codex and Claude templates are separate; event names and config shape are not mixed.

## Recovery

If an installed hook blocks useful work:

1. Disable the project hook first, not the global hook, when both exist.
2. Re-run the sample payload that falsely matched.
3. Downgrade blocker to reminder unless the rule protects secrets, destructive commands, or production state.
4. Move project-specific conditions out of global config.
