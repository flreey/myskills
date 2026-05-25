# cross-cli-review (Codex notes)

Codex-specific guidance for using this skill. The main instructions are in `SKILL.md`. This file adds Codex-side details.

## When you (Codex) load this skill

You are inside Codex CLI. Reviewer = Claude Code. Use `references/claude-headless.md` for command templates.

Verify Claude is on PATH:

```bash
which claude || echo "install: npm i -g @anthropic-ai/claude-code"
```

## Codex shell sandbox interactions

The user's shell may default Codex to `--dangerously-bypass-approvals-and-sandbox`. When you spawn `claude -p`, that subprocess runs under the user's normal permissions, NOT under Codex's sandbox. So:

- Always pass `--permission-mode plan` to the spawned Claude.
- Always pass `--add-dir "$(git rev-parse --show-toplevel)"` to scope it to the repo.
- Always pass `--no-session-persistence` so the review doesn't pollute the user's resume picker.
- Always pass `--max-budget-usd <N>` (5 default, 10 for architecture) so a runaway review can't burn unlimited tokens.

## Output handling

Claude `-p --output-format text` writes the review to stdout, ends with a blank line, exits. Capture:

```bash
claude -p "<prompt>" \
  --model claude-opus-4-7 --effort high \
  --permission-mode plan \
  --add-dir "$REPO" \
  --output-format text \
  --max-budget-usd 5 \
  --no-session-persistence \
  > /tmp/claude-out.txt 2> /tmp/claude-err.txt

# Token usage / cost is in stderr or in JSON output.
# For exact numbers, prefer --output-format json:
```

For machine-parseable findings, use `--output-format json` and `jq`:

```bash
jq -r '.result' /tmp/claude-out.json     # the review
jq    '.usage'  /tmp/claude-out.json     # tokens
jq -r '.cost'   /tmp/claude-out.json     # USD
```

Or use `--json-schema` to force structured findings (see `references/claude-headless.md` section C).

## Don't do this from Codex

- Don't have Claude resume one of your Codex sessions — they are different session stores.
- Don't pass `~/.codex/` paths to Claude — Claude's `--add-dir` won't include them by default and shouldn't.
- Don't ask Claude to "review the plan I just made" without embedding the plan content. Claude reads its own session history, not Codex's.

## Reasoning effort mapping

Codex `model_reasoning_effort` ↔ Claude `--effort`:

| Codex | Claude |
|---|---|
| `"low"` | `low` |
| `"medium"` | `medium` |
| `"high"` | `high` |
| `"xhigh"` | `max` |

Default to `high` for diff/security/perf review, `medium` for plan/architecture/consult.

## Reading SKILL.md

Treat `SKILL.md` as your primary instruction set. Load `references/*.md` only when needed for the current review type.
