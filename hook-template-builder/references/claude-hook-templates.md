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
If `.claude/settings.json` or `.claude/settings.local.json` already exists, merge into its `hooks` object. Do not replace existing settings.

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

## Project Install Contract

A Claude project install is complete only when:

- scripts exist under `.claude/hooks/`
- a project settings file or skill package frontmatter references those scripts
- any previous `hooks` entries are preserved
- duplicate commands were not added twice to the same event/matcher
- JSON/YAML parses successfully for the file being modified
- dry-run positive and negative samples pass

Install pattern for project settings:

1. Back up `.claude/settings.local.json` or `.claude/settings.json`.
2. Parse the existing JSON. Stop if it is invalid.
3. Create `.claude/hooks/` and write scripts there.
4. Merge new hook entries into the existing `hooks` object.
5. Skip an entry if the same command already exists for that event/matcher.
6. Run the activation checks below.

Prefer `.claude/settings.local.json` for repo-local user install when available. Avoid modifying global `~/.claude/settings.json` unless the user explicitly asks for global install.

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

## Activation Checks

After install:

```bash
test -d .claude/hooks
python3 -m json.tool .claude/settings.local.json >/dev/null 2>&1 || python3 -m json.tool .claude/settings.json >/dev/null
grep -R "hook-template-builder" .claude/settings.local.json .claude/settings.json .claude/hooks 2>/dev/null
printf '{"command":"git push --force origin main"}' | bash .claude/hooks/dangerous-shell-warning.sh
printf '{"command":"git push origin main"}' | bash .claude/hooks/dangerous-shell-warning.sh
```

Then report:

- `installed config`: `.claude/settings.local.json`, `.claude/settings.json`, or skill frontmatter path
- `installed scripts`: `.claude/hooks/*.sh`
- `activation caveat`: whether Claude Code needs a new session, hook trust approval, or settings reload before first automatic execution

Uninstall must remove only hook-template-builder commands and scripts. Do not delete unrelated `.claude` settings.
