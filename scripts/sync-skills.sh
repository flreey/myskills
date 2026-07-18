#!/bin/bash
# Sync myskills into the cross-agent registry (~/.agents/skills) and Claude's view.
# Idempotent, safe for hooks. Codex discovers ~/.agents/skills natively (skill root r1).
# Runs from git post-commit — caller may be the user, Claude, or Codex; a sandboxed
# caller (codex workspace-write) cannot write outside the repo, so failures WARN loudly.
set -u
MYSKILLS="$HOME/Projects/myskills"
AGENTS="$HOME/.agents/skills"
CLAUDE="$HOME/.claude/skills"
failed=0
agent_paths=()
for d in "$MYSKILLS"/*/; do
  n=$(basename "$d")
  [ -f "$d/SKILL.md" ] || continue
  if [ ! -e "$AGENTS/$n" ]; then
    if ln -s "$MYSKILLS/$n" "$AGENTS/$n" 2>/dev/null; then
      echo "sync-skills: registered $n (agents)"
      agent_paths+=("skills/$n")
    else
      failed=1
    fi
  fi
  if [ -e "$AGENTS/$n" ] && [ ! -e "$CLAUDE/$n" ]; then
    if ln -s "../../.agents/skills/$n" "$CLAUDE/$n" 2>/dev/null; then
      echo "sync-skills: registered $n (claude)"
    else
      failed=1
    fi
  fi
done
if [ "${#agent_paths[@]}" -gt 0 ] && [ -d "$HOME/.agents/.git" ]; then
  if git -C "$HOME/.agents" add -- "${agent_paths[@]}" >/dev/null 2>&1; then
    git -C "$HOME/.agents" commit -qm "auto-sync: register new myskills" -- "${agent_paths[@]}" >/dev/null 2>&1 || failed=1
  else
    failed=1
  fi
fi
if [ "$failed" -eq 1 ]; then
  echo "sync-skills: WARN registry update incomplete — inspect links and git status manually"
fi
exit 0
