# Claude Code Hook Templates

Use this reference only when the target platform is Claude Code or the user asks for both Codex and Claude templates.

## Premises

- Claude Code hooks live in Claude settings or skill frontmatter depending on the packaging style.
- Claude hook schemas are similar in spirit to Codex but not identical. Adapt event names, matchers, and handler fields deliberately.
- Do not paste Codex `hooks.json` into Claude settings without review.

## Skill Frontmatter Example

```yaml
---
name: project-hook-pack
description: Use when this project needs session-scoped hook reminders.
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "bash ${CLAUDE_SKILL_DIR}/hooks/dangerous-shell-warning.sh"
  Stop:
    - hooks:
        - type: command
          command: "bash ${CLAUDE_SKILL_DIR}/hooks/stop-status-reminder.sh"
---
```

## Settings Example

Use settings-level hooks only after confirmation because they may affect more than one project.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/dangerous-shell-warning.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/stop-status-reminder.sh"
          }
        ]
      }
    ]
  }
}
```

## Porting Rules From Codex

| Codex template concern | Claude adaptation |
|---|---|
| Project `hooks.json` | Claude settings or skill frontmatter |
| Plugin root env vars | Prefer `${CLAUDE_SKILL_DIR}` inside skill packages |
| Reminder script | Usually portable unchanged if it reads stdin and exits 0 |
| Blocking script | Re-check Claude's expected decision payload before enabling |
| Global config | Require explicit confirmation |

## Dry-Run Rule

Every generated Claude hook script still needs the same dry-run payloads as Codex:

```bash
printf '{"command":"git push --force origin main"}' | bash .claude/hooks/dangerous-shell-warning.sh
printf '{"file_path":"README.md"}' | bash .claude/hooks/dependency-change-reminder.sh
```

If a script relies on Claude-specific payload fields, include one positive and one negative sample from a real observed payload before installation.
