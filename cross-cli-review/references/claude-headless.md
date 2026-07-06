# Calling Claude Code from Codex CLI

Reviewer = Claude Code. You are inside Codex CLI.

## Binary and auth check

```bash
which claude || { echo "install: npm i -g @anthropic-ai/claude-code"; exit 1; }
claude --version > /dev/null 2>&1 || { echo "auth issue, run: claude login"; exit 1; }
```

The auth check matters: OAuth tokens occasionally need refresh. Doing this up front prevents Codex from silently waiting on a `claude` subprocess that's stuck on auth.

## OAuth caveat (`--bare` doesn't work)

`--bare` is Anthropic's [recommended scripted-call mode](https://code.claude.com/docs/en/headless#start-faster-with-bare-mode) — faster startup, no CLAUDE.md / plugins / MCP loaded. **But it requires `ANTHROPIC_API_KEY` (or `apiKeyHelper` via `--settings`) and skips OAuth/keychain.**

If you log in via `claude login` (browser OAuth), `--bare` fails with auth errors. **OAuth users: skip `--bare`.** All recipes below work with OAuth.

## Modes

### A. Stdin pattern (default — fast, won't hang, won't wander)

This is the [canonical Anthropic-recommended pattern for headless review](https://code.claude.com/docs/en/headless#add-claude-to-a-build-script). Diff goes in via stdin, role goes in `--append-system-prompt`, structured output comes out via `--output-format json`. The reviewer has tools available but **no incentive to use them** — the diff is already in the conversation, so it answers from that.

Use this for: any review where you can pre-extract the content into stdin. ~90% of cross-CLI reviews.

```bash
BASE="${BASE:-main}"
DIFF=$(git diff "$BASE"...HEAD)
[ -z "$DIFF" ] && { echo "no diff vs $BASE"; exit 0; }

echo "$DIFF" | timeout 180 claude -p \
  --append-system-prompt "You are an independent code reviewer. Be terse and adversarial. No compliments. No hedging. Output ONLY findings grouped under [P1 BLOCKER], [P2 IMPORTANT], [P3 NIT], each formatted as 'file:line — problem — concrete fix'. End with a single line: VERDICT: SHIP | SHIP-WITH-FIXES | DO-NOT-SHIP." \
  --output-format json \
  --no-session-persistence \
  2> /tmp/claude-err.txt \
  | jq -r '.result'
```

Why each piece:

| Piece | Why |
|---|---|
| stdin pipe | Diff isn't shell-quoted; reviewer can't accidentally read the wrong git state. Doesn't need Bash permission. |
| `timeout 180` | Hard 3-minute cap. Sub-500-line diffs typically finish in 10–30s. |
| `--append-system-prompt` | Locks reviewer role + output format more reliably than embedding it in the user prompt. |
| `--output-format json` + `jq -r '.result'` | Clean text output. JSON also gives `.total_cost_usd` and `.usage` if you want them. |
| `--no-session-persistence` | Don't pollute the resume picker. |

**Deliberately NOT included** (and why):
- `--permission-mode plan` — reviewer doesn't need tools; plan mode is redundant defense.
- `--tools ""` — works but stdin already removes the incentive to use tools; not the canonical Anthropic pattern.
- `--add-dir`, `--max-budget-usd` — irrelevant when reviewer doesn't browse.
- `--model claude-opus-4-7 --effort high` — default is fine. Add when you specifically need deeper reasoning.
- `--bare` — requires API key, OAuth users can't use it.

#### Plan / architecture review variant

Same shape, different stdin source — embed the plan content:

```bash
cat path/to/plan.md | timeout 300 claude -p \
  --append-system-prompt "You are reviewing a technical plan. Identify logical gaps, unstated assumptions, sequencing problems, and feasibility issues. Output ONLY findings + 1-line VERDICT (APPROVED / NEEDS-REVISION / REJECTED)." \
  --output-format json \
  --no-session-persistence \
  | jq -r '.result'
```

#### Avoid CLAUDE.md contamination

`claude -p` auto-loads the project's `CLAUDE.md` from cwd. Usually fine — reviewer benefits from project conventions. But if CLAUDE.md contains opinionated rules ("always use X framework") that bias the review, run from a clean dir:

```bash
( cd /tmp && echo "$DIFF" | claude -p ... )
```

OAuth users can't use `--bare` to skip this; the `cd /tmp` trick is the workaround.

### B. Browse pattern (reviewer must read other files)

Use only when the diff alone is insufficient — reviewer needs to grep callers, read referenced files, validate cross-cutting changes. E.g.:

- "This changes `auth/middleware.ts` — check all callers."
- Plan review where the plan references files you can't paste in full.
- Adversarial challenge — reviewer must actively explore the codebase.

```bash
cd "$REPO"
timeout 300 claude -p "<prompt referencing files in $REPO>" \
  --allowedTools "Read,Glob,Grep,Bash(git *)" \
  --permission-mode plan \
  --output-format stream-json --verbose --include-partial-messages \
  --no-session-persistence \
  2> /tmp/claude-err.txt \
  | jq -rj 'select(.type=="stream_event" and .event.delta.type?=="text_delta") | .event.delta.text'
```

Why this differs from Mode A:

- `--allowedTools` enumerates the read-only toolkit explicitly. Without it Claude has all built-in tools (Read/Edit/Write/Bash/agents/MCP/etc.).
- `--permission-mode plan` is a real safety boundary now (reviewer has tools, must not write).
- `stream-json + jq` streams output as it arrives — you see if reviewer is wandering (e.g. reading `~/.claude/skills/`) and can Ctrl-C early. Silent waiting is the #1 cause of "it's stuck".
- `timeout 300` (5 min) because tool loops take longer than pure inference.

If the reviewer wanders despite this, **fall back to Mode A** — pre-extract the relevant files into the stdin prompt yourself.

### C. Async pattern (large diffs, don't block)

Inspired by [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc)'s `/codex:review --background`. For multi-file changes where you don't want the host CLI to wait synchronously:

```bash
DIFF=$(git diff "${BASE:-main}"...HEAD)
OUT=/tmp/claude-review-$$.json
ERR=/tmp/claude-review-$$.err

echo "$DIFF" | nohup claude -p \
  --append-system-prompt "<reviewer role + output format>" \
  --output-format json \
  --no-session-persistence \
  > "$OUT" 2> "$ERR" &

PID=$!
echo "Review started: PID=$PID, output=$OUT"

# Continue with other work, then collect when ready:
wait $PID && jq -r '.result' "$OUT"
```

Use `disown` if you want to fully detach from the host shell.

**Status check caveat**: with `--output-format json`, claude writes NOTHING until it finishes — an empty `$OUT` mid-run is normal, not stuck. To check liveness: `kill -0 $PID`. If you need real progress visibility (each event as it happens), use `--output-format stream-json --verbose` instead and `tail -3 "$OUT" | cut -c1-300` to peek; the final result is then the last `result`-type JSONL line rather than a single JSON object (`jq -rs 'map(select(.type=="result"))[-1].result' "$OUT"`).

### D. JSON-schema enforced (programmatic gate)

When downstream code needs to parse findings programmatically (e.g. CI gate, automated triage):

```bash
echo "$DIFF" | claude -p \
  --append-system-prompt "You are a code reviewer." \
  --json-schema '{
    "type": "object",
    "properties": {
      "verdict": {"type": "string", "enum": ["SHIP","SHIP-WITH-FIXES","DO-NOT-SHIP"]},
      "findings": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "severity": {"type": "string", "enum": ["P1","P2","P3"]},
            "file": {"type": "string"},
            "line": {"type": "integer"},
            "problem": {"type": "string"},
            "fix": {"type": "string"}
          },
          "required": ["severity","problem","fix"]
        }
      }
    },
    "required": ["verdict","findings"]
  }' \
  --output-format json \
  --no-session-persistence \
  | jq '.structured_output'
```

The model is forced to produce output matching the schema. Cleanest cross-CLI pattern when you need machine-readable findings.

## Reasoning effort

Default is fine for most reviews. Override only when you need more depth:

| Review type | `--effort` |
|---|---|
| general / security / performance / challenge | (default) or `high` |
| architecture / plan / consult | (default) |
| user explicitly asks for deep review | `max` |

`--effort max` is 5–10x cost and rarely worth it.

## Timeout

- Mode A (stdin): **180s** (3 min) — pure inference, doesn't loop.
- Mode B (browse): **300s** (5 min) — has tool loops.
- Plan / architecture in browse mode: **600s** (10 min).

`timeout` is GNU coreutils. macOS: `brew install coreutils` (gives both `timeout` and `gtimeout`). Without it, omit the wrapper — but you lose the safety net.

## Auth note

Claude CLI uses keychain OAuth by default. Verify before invoking:

```bash
claude --version  # if errors mention auth: claude login
```

If your shell aliases `claude` to `--dangerously-skip-permissions`, the explicit flags above (Mode B's `--permission-mode plan`) override that for this invocation. Verify the working tree afterwards regardless:

```bash
git status  # should match pre-review state
```

## Common command mistakes

- ❌ `claude "<prompt>"` without `-p` → opens TUI, blocks forever in headless context.
- ❌ Embedding diff in `claude -p "<diff inline>"` instead of stdin → shell quoting hell, especially with backticks/dollar signs in diff.
- ❌ Using Mode A (stdin) but also passing `--allowedTools` / `--permission-mode plan` → harmless but cluttered; means you copied a Mode B recipe by mistake.
- ❌ Using Mode B (browse) without `--permission-mode plan` → reviewer may try to Edit/Write files.
- ❌ Using `--bare` with OAuth login → auth error.
- ❌ `--output-format text` then trying to parse the result as JSON → returns plain text. Use `json` if you want `.result` / `.usage`.
- ❌ Treating `--max-budget-usd` / `--no-session-persistence` / `--add-dir` as required — they are tuning knobs, not safety boundaries. Only add when the recipe actually needs them.
- ❌ `--effort max` by default → 5–10x cost for marginal gain.
