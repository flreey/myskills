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
echo "| Hook | Event | Behavior | Evidence | False-positive risk | Recommendation |"
echo "|---|---|---|---|---|---|"
echo "| dangerous-shell-command | PreToolUse / shell command | remind by default; block only after confirmation | universal safety default | medium | recommended reminder |"
echo "| secret-edit-warning | PreToolUse / file edit | remind on real secret files or key-like values | universal safety default | medium | recommended reminder |"
echo "| large-artifact-warning | PostToolUse / file change | remind on large files, archives, logs, DB files, build outputs | universal repo hygiene default | low | recommended reminder |"
echo "| stop-status-reminder | Stop | remind about dirty diff, unrun tests, stale plan files | universal handoff default | low | recommended reminder |"
echo

echo "## Project-Specific Candidates"
echo
echo "| Hook | Event | Behavior | Evidence | False-positive risk | Recommendation |"
echo "|---|---|---|---|---|---|"
project_rows=0
if has_file package.json || has_file pyproject.toml || has_file Cargo.toml || has_file go.mod; then
  echo "| dependency-change-reminder | PostToolUse / file change | remind to install deps and run relevant tests after manifest or lockfile changes | manifest detected | low | recommended reminder |"
  project_rows=$((project_rows + 1))
fi
if [ "$detected" -eq 1 ]; then
  echo "| test-command-reminder | Stop | print inferred test/lint/build commands if source changed | commands detected above | low | recommended reminder |"
  project_rows=$((project_rows + 1))
fi
if has_dir .github/workflows; then
  echo "| ci-parity-reminder | Stop | remind to mirror CI commands locally before handoff | .github/workflows detected | low | optional reminder |"
  project_rows=$((project_rows + 1))
fi
if has_file .codex/hooks.json || has_file hooks.json || has_file .claude/settings.json || has_file .claude/settings.local.json; then
  echo "| existing-hook-audit | SessionStart / manual | summarize existing hooks before adding new ones | existing hook/settings config | low | recommended review before changes |"
  project_rows=$((project_rows + 1))
fi
if [ "$project_rows" -eq 0 ]; then
  echo "| none | n/a | no project-specific hook inferred | no manifests, CI, or hook config detected | low | default hooks only |"
fi
echo

echo "## High-Risk Confirmation Required"
echo
echo "| Hook | Event | Behavior | Evidence | False-positive risk | Recommendation |"
echo "|---|---|---|---|---|---|"
echo "| destructive-command-blocker | PreToolUse / shell command | block destructive shell commands | user must opt in | high | require confirmation |"
echo "| secret-edit-blocker | PreToolUse / file edit | block edits to real secret files | user must opt in | high | require confirmation |"
echo "| global-hook-install | install mode | modify global Codex or Claude config | affects all projects | high | require second confirmation |"
echo "| network-notifier | Stop / Notification | send local status externally | may leak paths or prompts | high | avoid unless explicitly requested |"
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
echo "Choose hooks to enable, target platform (Codex, Claude Code, or both), and install mode (template only, project install, or global install). Reminder hooks are safe defaults; blocking/global/network hooks need explicit confirmation."
