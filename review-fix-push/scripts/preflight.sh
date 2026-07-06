#!/usr/bin/env bash
set -u

ROOT="${1:-.}"
if [ ! -d "$ROOT" ]; then
  echo "error: project path does not exist: $ROOT" >&2
  exit 2
fi

cd "$ROOT" || exit 2

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not inside a git work tree" >&2
  exit 2
fi

ROOT_ABS="$(git rev-parse --show-toplevel)"
cd "$ROOT_ABS" || exit 2

branch="$(git branch --show-current 2>/dev/null || true)"
if [ -z "$branch" ]; then
  branch="DETACHED"
fi

upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
remote_url=""
if [ -n "$upstream" ]; then
  remote_name="${upstream%%/*}"
  remote_url="$(git remote get-url "$remote_name" 2>/dev/null || true)"
fi

default_remote_head="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"
if [ -z "$default_remote_head" ]; then
  default_remote_head="main"
fi

echo "# Review Fix Push Preflight"
echo
echo "- Project: \`$ROOT_ABS\`"
echo "- Branch: \`$branch\`"
if [ -n "$upstream" ]; then
  echo "- Upstream: \`$upstream\`"
else
  echo "- Upstream: none"
fi
if [ -n "$remote_url" ]; then
  echo "- Remote URL: \`$remote_url\`"
fi
echo "- Origin default branch guess: \`$default_remote_head\`"
echo

echo "## Git Status"
status="$(git status --short)"
if [ -n "$status" ]; then
  printf '%s\n' "$status" | sed 's/^/- `/' | sed 's/$/`/'
else
  echo "- clean working tree"
fi
echo

echo "## Change Scope"
staged="$(git diff --cached --name-only)"
unstaged="$(git diff --name-only)"
untracked="$(git ls-files --others --exclude-standard)"

if [ -n "$staged" ]; then
  echo "### Staged"
  printf '%s\n' "$staged" | sed 's/^/- /'
else
  echo "### Staged"
  echo "- none"
fi
echo

if [ -n "$unstaged" ]; then
  echo "### Unstaged"
  printf '%s\n' "$unstaged" | sed 's/^/- /'
else
  echo "### Unstaged"
  echo "- none"
fi
echo

if [ -n "$untracked" ]; then
  echo "### Untracked"
  printf '%s\n' "$untracked" | sed 's/^/- /'
else
  echo "### Untracked"
  echo "- none"
fi
echo

echo "## Unpushed Commits"
if [ -n "$upstream" ]; then
  ahead_count="$(git rev-list --count "${upstream}..HEAD" 2>/dev/null || echo 0)"
  behind_count="$(git rev-list --count "HEAD..${upstream}" 2>/dev/null || echo 0)"
  echo "- Ahead of upstream: $ahead_count"
  echo "- Behind upstream: $behind_count"
  if [ "$ahead_count" != "0" ]; then
    git log --oneline "${upstream}..HEAD" | sed 's/^/- /'
  fi
else
  echo "- No upstream; pushing will publish all commits on \`$branch\` to origin unless a different remote is chosen."
  if git rev-parse --verify "origin/${default_remote_head}" >/dev/null 2>&1; then
    ahead_default="$(git rev-list --count "origin/${default_remote_head}..HEAD" 2>/dev/null || echo 0)"
    echo "- Commits ahead of \`origin/${default_remote_head}\`: $ahead_default"
    if [ "$ahead_default" != "0" ]; then
      git log --oneline "origin/${default_remote_head}..HEAD" | sed 's/^/- /'
    fi
  fi
fi
echo

echo "## Suspicious Files To Review Before Staging"
all_paths="$(printf '%s\n%s\n%s\n' "$staged" "$unstaged" "$untracked" | sed '/^$/d' | sort -u)"
if [ -z "$all_paths" ]; then
  echo "- none"
else
  suspicious_found=0
  while IFS= read -r path; do
    [ -z "$path" ] && continue
    case "$path" in
      .env|.env.*|*.pem|*.key|*.p12|*.sqlite|*.sqlite3|*.db|*.log|*.dump|*.tar|*.tar.gz|*.zip|*.7z|dist/*|build/*|coverage/*|node_modules/*|.DS_Store)
        case "$path" in
          .env.example|*.example|*.sample)
            ;;
          *)
            echo "- $path (secret/runtime/generated pattern)"
            suspicious_found=1
            ;;
        esac
        ;;
    esac
    if [ -f "$path" ]; then
      size="$(wc -c < "$path" 2>/dev/null | tr -d ' ')"
      if [ -n "$size" ] && [ "$size" -gt 5242880 ]; then
        echo "- $path (${size} bytes; large file)"
        suspicious_found=1
      fi
    fi
  done <<EOF
$all_paths
EOF
  if [ "$suspicious_found" -eq 0 ]; then
    echo "- none"
  fi
fi
echo

echo "## Likely Verification Commands"
commands_found=0
if [ -f package.json ]; then
  if grep -Eq '"test"[[:space:]]*:' package.json; then echo "- npm test"; commands_found=1; fi
  if grep -Eq '"lint"[[:space:]]*:' package.json; then echo "- npm run lint"; commands_found=1; fi
  if grep -Eq '"build"[[:space:]]*:' package.json; then echo "- npm run build"; commands_found=1; fi
fi
if [ -f pyproject.toml ] || [ -f pytest.ini ]; then
  echo "- pytest"
  commands_found=1
fi
if [ -f pyproject.toml ] || [ -f ruff.toml ]; then
  if grep -q "ruff" pyproject.toml ruff.toml 2>/dev/null; then
    echo "- ruff check ."
    commands_found=1
  fi
fi
if [ -f Cargo.toml ]; then
  echo "- cargo test"
  echo "- cargo fmt --check"
  commands_found=1
fi
if [ -f go.mod ]; then
  echo "- go test ./..."
  commands_found=1
fi
if [ "$commands_found" -eq 0 ]; then
  echo "- git diff --check"
fi
echo

echo "## Safe Next Step"
echo "- Review every path above, inspect suspicious files before staging, then classify findings as AUTO-FIX or ASK."
