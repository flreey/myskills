#!/usr/bin/env bash
set -u

ROOT="${1:-.}"
if [ ! -d "$ROOT" ]; then
  echo "error: project path does not exist: $ROOT" >&2
  exit 2
fi

cd "$ROOT" || exit 2
ROOT_ABS="$(pwd)"

has_file() {
  [ -f "$1" ]
}

has_dir() {
  [ -d "$1" ]
}

find_first() {
  find . -maxdepth 3 -path './.git' -prune -o -name "$1" -print 2>/dev/null | sed -n '1p'
}

print_json_hook_commands() {
  file="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -r '
      .hooks // {} |
      to_entries[] as $event |
      ($event.value // [])[]? as $entry |
      ($entry.matcher // "*") as $matcher |
      ($entry.hooks // [])[]? |
      "- " + $event.key + " / " + $matcher + " / " + (.type // "command") + " / " + (.command // "<no command>")
    ' "$file" 2>/dev/null
  else
    grep -En '"(PreToolUse|PostToolUse|Stop|SessionStart|Notification|UserPromptSubmit|PermissionRequest|command|matcher)"' "$file" 2>/dev/null | sed 's/^/- /'
  fi
}

package_script_exists() {
  script="$1"
  has_file package.json && grep -Eq "\"$script\"[[:space:]]*:" package.json
}

package_dep_exists() {
  dep="$1"
  has_file package.json && grep -Eiq "\"$dep\"[[:space:]]*:" package.json
}

print_command_if_script() {
  script="$1"
  cmd="$2"
  if package_script_exists "$script"; then
    echo "- $cmd"
    return 0
  fi
  return 1
}

echo "# Hook Candidate Scan"
echo
echo "- Project: \`$ROOT_ABS\`"
echo "- Mode: read-only scan"
echo

echo "## Project Signals"

signals=0
if has_file package.json; then
  echo "- Node/JavaScript: package.json"
  signals=$((signals + 1))
  if has_file package-lock.json; then echo "- Package manager: npm"; fi
  if has_file pnpm-lock.yaml; then echo "- Package manager: pnpm"; fi
  if has_file yarn.lock; then echo "- Package manager: yarn"; fi
fi
if has_file pyproject.toml || has_file pytest.ini || has_file requirements.txt; then
  echo "- Python: pyproject.toml / pytest.ini / requirements.txt"
  signals=$((signals + 1))
  if has_file uv.lock; then echo "- Python package manager: uv"; fi
  if grep -q "tool.poetry" pyproject.toml 2>/dev/null; then echo "- Python package manager: poetry"; fi
fi
if has_file Cargo.toml; then
  echo "- Rust: Cargo.toml"
  signals=$((signals + 1))
fi
if has_file go.mod; then
  echo "- Go: go.mod"
  signals=$((signals + 1))
fi
if has_dir .github/workflows; then
  echo "- CI: .github/workflows"
  signals=$((signals + 1))
fi
agent_instructions="$(find_first "AGENTS.md")"
if [ -n "$agent_instructions" ]; then
  echo "- Agent instructions: $agent_instructions"
fi
claude_instructions="$(find_first "CLAUDE.md")"
if [ -n "$claude_instructions" ]; then
  echo "- Claude instructions: $claude_instructions"
fi
if has_file .codex/hooks.json || has_file hooks.json; then
  echo "- Existing Codex hook config detected"
fi
if has_file .claude/settings.json || has_file .claude/settings.local.json; then
  echo "- Existing Claude settings detected"
fi
if has_dir .git/hooks; then
  active_git_hooks="$(find .git/hooks -maxdepth 1 -type f ! -name '*.sample' -perm -111 2>/dev/null | wc -l | tr -d ' ')"
  echo "- Active git hooks: $active_git_hooks"
fi
if [ "$signals" -eq 0 ]; then
  echo "- No common manifest detected"
fi
echo

echo "## Existing Hook Surfaces"
echo
hook_surfaces=0
for file in .codex/hooks.json hooks.json .claude/settings.json .claude/settings.local.json; do
  if has_file "$file"; then
    hook_surfaces=$((hook_surfaces + 1))
    echo "### \`$file\`"
    echo
    if grep -q '"hooks"' "$file" 2>/dev/null; then
      print_json_hook_commands "$file" | sed -n '1,40p'
    else
      echo "- No top-level hooks object found"
    fi
    echo
  fi
done
if has_dir .codex/hooks; then
  hook_surfaces=$((hook_surfaces + 1))
  echo "### \`.codex/hooks/\`"
  find .codex/hooks -maxdepth 1 -type f -print 2>/dev/null | sort | sed 's/^/- /' | sed -n '1,40p'
  echo
fi
if has_dir .claude/hooks; then
  hook_surfaces=$((hook_surfaces + 1))
  echo "### \`.claude/hooks/\`"
  find .claude/hooks -maxdepth 1 -type f -print 2>/dev/null | sort | sed 's/^/- /' | sed -n '1,40p'
  echo
fi
if has_dir .husky; then
  hook_surfaces=$((hook_surfaces + 1))
  echo "### \`.husky/\`"
  find .husky -maxdepth 1 -type f -print 2>/dev/null | sort | sed 's/^/- /' | sed -n '1,40p'
  echo
fi
for file in lefthook.yml lefthook.yaml .pre-commit-config.yaml; do
  if has_file "$file"; then
    hook_surfaces=$((hook_surfaces + 1))
    echo "### \`$file\`"
    grep -En '(^[[:space:]]*[a-zA-Z0-9_-]+:|command:|run:)' "$file" 2>/dev/null | sed 's/^/- /' | sed -n '1,40p'
    echo
  fi
done
if [ "$hook_surfaces" -eq 0 ]; then
  echo "- No project hook surfaces detected."
  echo
fi

echo "## Detected Commands"

detected=0
if has_file package.json; then
  if print_command_if_script test "npm test"; then detected=1; fi
  if print_command_if_script lint "npm run lint"; then detected=1; fi
  if print_command_if_script build "npm run build"; then detected=1; fi
  if print_command_if_script format "npm run format"; then detected=1; fi
  if package_dep_exists vitest; then echo "- npx vitest run"; detected=1; fi
  if package_dep_exists playwright; then echo "- npx playwright test"; detected=1; fi
  if package_dep_exists cypress; then echo "- npx cypress run"; detected=1; fi
fi
if has_file pyproject.toml || has_file pytest.ini; then
  echo "- pytest"
  detected=1
fi
if has_file pyproject.toml || has_file ruff.toml; then
  if grep -q "ruff" pyproject.toml ruff.toml 2>/dev/null; then
    echo "- ruff check ."
    echo "- ruff format --check ."
    detected=1
  fi
fi
if has_file Cargo.toml; then
  echo "- cargo test"
  echo "- cargo fmt --check"
  echo "- cargo clippy --all-targets --all-features"
  detected=1
fi
if has_file go.mod; then
  echo "- go test ./..."
  echo "- gofmt check for changed .go files"
  detected=1
fi
if [ "$detected" -eq 0 ]; then
  echo "- No standard test/lint/build command inferred"
fi
echo

echo "## Default Recommended Hooks"
echo
echo "| Hook | Event | Behavior | Evidence | Existing-hook impact | False-positive risk | Recommendation |"
echo "|---|---|---|---|---|---|---|"
echo "| dangerous-shell-command | PreToolUse / shell command | remind by default; block only after confirmation | universal safety default | audit existing PreToolUse/Bash before install | medium | recommended reminder |"
echo "| secret-edit-warning | PreToolUse / file edit | remind on real secret files or key-like values | universal safety default | audit existing PreToolUse Edit/Write before install | medium | recommended reminder |"
echo "| large-artifact-warning | PostToolUse / file change | remind on large files, archives, logs, DB files, build outputs | universal repo hygiene default | audit existing PostToolUse before install | low | recommended reminder |"
echo "| stop-status-reminder | Stop | remind about dirty diff, unrun tests, stale plan files | universal handoff default | append to existing Stop hooks; do not replace | low | recommended reminder |"
echo

echo "## Project-Specific Candidates"
echo
echo "| Hook | Event | Behavior | Evidence | Existing-hook impact | False-positive risk | Recommendation |"
echo "|---|---|---|---|---|---|---|"
project_rows=0
if has_file package.json || has_file pyproject.toml || has_file Cargo.toml || has_file go.mod; then
  echo "| dependency-change-reminder | PostToolUse / file change | remind to install deps and run relevant tests after manifest or lockfile changes | manifest detected | merge with existing PostToolUse hooks | low | recommended reminder |"
  project_rows=$((project_rows + 1))
fi
if [ "$detected" -eq 1 ]; then
  echo "| test-command-reminder | Stop | print inferred test/lint/build commands if source changed | commands detected above | append to existing Stop hooks | low | recommended reminder |"
  project_rows=$((project_rows + 1))
fi
if has_dir .github/workflows; then
  echo "| ci-parity-reminder | Stop | remind to mirror CI commands locally before handoff | .github/workflows detected | append to existing Stop hooks | low | optional reminder |"
  project_rows=$((project_rows + 1))
fi
if has_file .codex/hooks.json || has_file hooks.json || has_file .claude/settings.json || has_file .claude/settings.local.json; then
  echo "| existing-hook-audit | install preflight | summarize existing hooks before adding new ones | existing hook/settings config | required before modifying hook config | low | required review before changes |"
  project_rows=$((project_rows + 1))
fi
if [ "$project_rows" -eq 0 ]; then
  echo "| none | n/a | no project-specific hook inferred | no manifests, CI, or hook config detected | no existing hook impact detected | low | default hooks only |"
fi
echo

echo "## High-Risk Confirmation Required"
echo
echo "| Hook | Event | Behavior | Evidence | Existing-hook impact | False-positive risk | Recommendation |"
echo "|---|---|---|---|---|---|---|"
echo "| destructive-command-blocker | PreToolUse / shell command | block destructive shell commands | user must opt in | may conflict with existing Bash blockers | high | require confirmation |"
echo "| secret-edit-blocker | PreToolUse / file edit | block edits to real secret files | user must opt in | may conflict with existing Edit/Write blockers | high | require confirmation |"
echo "| global-hook-install | install mode | modify global Codex or Claude config | affects all projects | may affect every repo hook chain | high | require second confirmation |"
echo "| network-notifier | Stop / Notification | send local status externally | may leak paths or prompts | conflicts with privacy defaults | high | avoid unless explicitly requested |"
echo

echo "## Better Outside Agent Hooks"
echo
echo "| Rule | Better destination | Reason |"
echo "|---|---|---|"
echo "| must pass full test suite before merge | CI | slow and deterministic |"
echo "| commit message format | git commit-msg hook or CI | belongs to git workflow |"
echo "| generated code must match source schema | CI or package script | deterministic build artifact check |"
echo "| project-specific style prose | AGENTS.md / CLAUDE.md | agent instruction, not executable policy |"
echo

echo "## Next Step"
echo
echo "Choose hooks to enable, target platform (Codex, Claude Code, or both), and install mode (template only, project install, or global install). If you choose install, existing hooks must be merged and activation-checked before success is claimed. Reminder hooks are safe defaults; blocking/global/network hooks need explicit confirmation."
