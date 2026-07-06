# Codex Hook Templates

Use this reference when the target platform is Codex.

## Premises

- Codex hooks are executable commands and may require hook trust before running.
- Keep project hooks project-local unless the user explicitly asks for global hooks.
- Use a top-level `hooks` object in `hooks.json`. Do not include undocumented metadata fields unless current Codex docs confirm them.
- Plugin-packaged hooks may use plugin root environment variables; standalone project hooks should prefer relative paths resolved by the command itself.

## Minimal Project `hooks.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .codex/hooks/dangerous-shell-warning.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .codex/hooks/stop-status-reminder.sh",
            "timeout": 20
          }
        ]
      }
    ]
  }
}
```

## Dangerous Shell Warning Script

Reminder version. Upgrade to blocking only after explicit confirmation.

```bash
#!/usr/bin/env bash
set -u

payload="$(cat)"
if printf '%s' "$payload" | grep -Eiq 'rm[[:space:]].*-rf[[:space:]]+/|git[[:space:]]+reset[[:space:]]+--hard|git[[:space:]]+push.*--force|DROP[[:space:]]+DATABASE|kubectl[[:space:]]+delete|terraform[[:space:]]+destroy'; then
  cat >&2 <<'MSG'
[hook-template-builder] Risky shell command detected.
Review the target, confirm the project/environment, and prefer a dry-run or safer command.
MSG
fi
exit 0
```

Dry-run:

```bash
printf '{"command":"git push --force origin main"}' | bash .codex/hooks/dangerous-shell-warning.sh
printf '{"command":"rm ./tmp.txt"}' | bash .codex/hooks/dangerous-shell-warning.sh
```

## Dependency Change Reminder Script

```bash
#!/usr/bin/env bash
set -u

payload="$(cat)"
if printf '%s' "$payload" | grep -Eiq 'package.json|package-lock.json|pnpm-lock.yaml|yarn.lock|pyproject.toml|uv.lock|poetry.lock|Cargo.toml|Cargo.lock|go.mod|go.sum'; then
  cat >&2 <<'MSG'
[hook-template-builder] Dependency metadata changed.
Install/update dependencies as needed and run the detected test/build commands before handoff.
MSG
fi
exit 0
```

Dry-run:

```bash
printf '{"file_path":"package.json"}' | bash .codex/hooks/dependency-change-reminder.sh
printf '{"file_path":"README.md"}' | bash .codex/hooks/dependency-change-reminder.sh
```

## Stop Status Reminder Script

```bash
#!/usr/bin/env bash
set -u

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "[hook-template-builder] Dirty git diff remains. Summarize it before handoff." >&2
  fi
fi

if [ -f task_plan.md ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git diff --quiet -- task_plan.md; then
    echo "[hook-template-builder] task_plan.md changed; make sure statuses are current." >&2
  fi
fi

exit 0
```

Dry-run:

```bash
printf '{}' | bash .codex/hooks/stop-status-reminder.sh
```

## Install / Uninstall Pattern

Project install:

```bash
mkdir -p .codex/hooks
cp generated-hooks/*.sh .codex/hooks/
cp generated-hooks/hooks.json .codex/hooks.json
chmod +x .codex/hooks/*.sh
```

Uninstall:

```bash
rm -f .codex/hooks.json
rm -rf .codex/hooks
```

Global install is not a default. If requested, show the generated config first and ask for a second confirmation because it affects every Codex project.
