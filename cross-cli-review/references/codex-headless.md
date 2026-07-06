# Calling Codex from Claude Code

Reviewer = Codex. You are inside Claude Code.

Verified against `codex-cli 0.46.0`, `0.130.0`, and `0.142.5`. Versions differ in important ways (see below — notably `codex review` does not exist in 0.46.0). Run `codex --version` first and re-check `codex exec --help` if anything errors.

## Binary check

```bash
which codex || { echo "install: npm i -g @openai/codex"; exit 1; }
```

## Anti-hang prerequisite: `-a never`

For headless codex (any subcommand), **`-a never` (`--ask-for-approval never`) is required to prevent hangs waiting for tool approval**. Without it, when the reviewer tries to call a tool the model isn't sure about, Codex pauses waiting for human input that will never come (no human, no TTY). With `-a never`, sandbox-blocked operations return failures to the model instead, and the model adapts.

Verified against `codex --help` (0.46.0, 0.130.0, and 0.142.5):
- `-a, --ask-for-approval <APPROVAL_POLICY>` — values: `untrusted`, `on-failure`, `on-request`, `never`.

**`-a` is a GLOBAL flag only — it must go BEFORE the subcommand.** `codex -a never ... exec "<prompt>"` works on all verified versions; `codex exec -a never "<prompt>"` fails with `unexpected argument '-a' found` (verified on 0.46.0 — `exec` accepts `-s`/`-C` as subcommand flags but not `-a`).

**Always combine with `-s read-only`**: `-a never` removes the approval gate, `-s read-only` ensures auto-allowed operations still can't write. This is the safe headless pattern.

(Note: some old or third-party docs mention `--full-auto`; do NOT use it for review. It is absent from verified `codex --help` output in 0.142.5, and when a version provides an auto-write convenience mode it is unsafe for review because it can allow workspace writes.)

## Flag placement — important

Codex has TWO levels of flags:

- **Global flags** (go BEFORE the subcommand): `-a/--ask-for-approval`, `-C/--cd`, `-s/--sandbox`, `--search`, `-c/--config`, `--enable`, `--disable`.
- **Subcommand flags** (go AFTER the subcommand): `--base`, `--uncommitted`, `--commit`, `--title` (for `review`, where it exists); `--json`, `-i/--image`, `-m/--model`, `-o/--output-last-message`, `--skip-git-repo-check` (for `exec`).

`-a` is global-only on every verified version — `codex exec` rejects it as a subcommand flag (0.46.0: `unexpected argument '-a' found`). `codex review` (where it exists) does NOT accept `-C` or `-s` as subcommand flags either. Same for `codex exec resume`.

`codex exec` accepts `-C` and `-s` as subcommand flags too, but NOT `-a` — so put ALL of them at global position throughout this file. One placement rule, no exceptions.

Working dir pin (always):

```bash
REPO=$(git rev-parse --show-toplevel) || exit 1
```

## Modes

### A. Diff review (use `codex review` — NEWER VERSIONS ONLY)

Best for: branch-vs-base diff, uncommitted changes, single commit.

**Version gate (mandatory before using this mode).** The `review` subcommand does not exist in older versions (e.g. 0.46.0). Worse: on those versions `codex review ...` is NOT an error — "review" is forwarded to the interactive TUI as a prompt, which hangs forever in headless mode. Check first:

```bash
codex --help 2>/dev/null | grep -qE '^\s+review\b' && echo HAS_REVIEW || echo NO_REVIEW
```

If `NO_REVIEW` → skip this mode and do diff review via Mode B (`codex exec`), putting the diff scope in the prompt:

```bash
timeout 300 codex -a never -C "$REPO" -s read-only \
  -c 'model_reasoning_effort="high"' \
  exec "<filesystem boundary + ROLE...>

SCOPE: run \`git diff <base-branch>...HEAD\` to see the changes, then review them.
<FOCUS / OUTPUT FORMAT / DO NOT — per SKILL.md Step 5>" \
  > /tmp/codex-out.txt 2> /tmp/codex-err.txt
```

If `HAS_REVIEW`, proceed. Codex needs more required flags than Claude because its defaults are unsafer for review:
- Default sandbox is `workspace-write` (can modify files) → `-s read-only` is mandatory.
- `codex review` reviews the entire repo unless you scope it → `--base` / `--uncommitted` / `--commit` is mandatory.
- Default `model_reasoning_effort` is `medium` → fine for plans, light for code review.

**Minimum viable** — read-only diff review, default reasoning:

```bash
codex -a never -C "$REPO" -s read-only \
  review --base "<base-branch>" "<prompt>" \
  2> /tmp/codex-err.txt
```

**Recommended** — raise reasoning for code review depth:

```bash
timeout 300 codex -a never -C "$REPO" -s read-only \
  -c 'model_reasoning_effort="high"' \
  review --base "<base-branch>" "<prompt>" \
  > /tmp/codex-out.txt 2> /tmp/codex-err.txt
```

(`tokens used: N` lives in stderr for non-JSON modes — capture both streams.)

**Variants** (subcommand flags, after `review`):
- Uncommitted only: `--uncommitted` instead of `--base <branch>`.
- Single commit: `--commit <sha>` instead of `--base`.

**Optional hardening** — add when relevant, not by default:

| Flag | Position | When to add |
|---|---|---|
| `--search` | global (before `review`) | Review needs live web docs / API specs. Metered — opt in. |
| `-c 'model_reasoning_effort="medium"'` | global | Plan / architecture review (cheaper, often enough). |
| `-c 'model_reasoning_effort="xhigh"'` | global | Explicit user request only — ~23x tokens of `high`, can hang 30-60min. |

Verdict parsing: scan output for `[P1` markers. Any P1 → FAIL gate. None → PASS.

### B. Free-form review / consult / challenge (use `codex exec`)

Best for: plan review, architecture question, adversarial challenge, anything that is not a pure diff.

```bash
timeout 300 codex \
  -a never \
  -C "$REPO" \
  -s read-only \
  -c 'model_reasoning_effort="high"' \
  exec \
    --json \
    "<full prompt>" \
  2> /tmp/codex-err.txt \
  | python3 -u -c '
import sys, json
for line in sys.stdin:
    try:
        o = json.loads(line)
        t = o.get("type", "")
        if t == "item.completed":
            it = o.get("item", {})
            kind = it.get("type", "")
            text = it.get("text", "")
            if kind == "reasoning" and text:
                print(f"[codex thinking] {text}\n", flush=True)
            elif kind == "agent_message" and text:
                print(text, flush=True)
            elif kind == "command_execution":
                cmd = it.get("command", "")
                if cmd: print(f"[codex ran] {cmd}", flush=True)
        elif t == "thread.started":
            tid = o.get("thread_id", "")
            if tid: print(f"SESSION_ID:{tid}", flush=True)
        elif t == "turn.completed":
            u = o.get("usage", {})
            n = u.get("input_tokens", 0) + u.get("output_tokens", 0)
            if n: print(f"\ntokens used: {n}", flush=True)
    except Exception: pass
'
```

In `--json` mode, token usage comes from stdout JSONL (`turn.completed.usage`), not stderr.

Capture `SESSION_ID:<id>` if the user wants follow-ups.

### C. Resume an earlier conversation

`codex exec resume` does NOT accept `-C`, `-s`, or `--search` as subcommand flags — all of those must be global (before `exec`):

```bash
codex \
  -a never \
  -C "$REPO" \
  -s read-only \
  -c 'model_reasoning_effort="medium"' \
  exec resume \
    --json \
    <session-id> \
    "<follow-up prompt>"
```

## Reasoning effort

| Review type | `model_reasoning_effort` |
|---|---|
| general / security / performance / challenge | `"high"` |
| architecture / plan / consult | `"medium"` |
| user passed `--xhigh` | `"xhigh"` |

`"xhigh"` warning: ~23x tokens of `"high"`, can hang 30-60min on large inputs. Only use when explicitly requested.

## Sandbox

Always `-s read-only`. The user's shell may default Codex to `--dangerously-bypass-approvals-and-sandbox` via shell function — `-s read-only` overrides that for this invocation. Verify after the call:

```bash
git status   # should be clean unless the user had uncommitted changes already
```

## Background execution (long tasks)

For `xhigh` or very large diffs where blocking the host synchronously is unacceptable:

- **Inside Claude Code**: use the Bash tool's `run_in_background` option on the exact same command — keeps the `> out 2> err` stream split, exit code, and auto-notifies on completion. Preferred.
- **Any other host**: `nohup` with the same redirections, then poll the PID:

```bash
nohup timeout 600 codex -a never -C "$REPO" -s read-only \
  -c 'model_reasoning_effort="high"' \
  exec "<full prompt>" \
  > /tmp/codex-out.txt 2> /tmp/codex-err.txt &
CODEX_PID=$!
# later: kill -0 "$CODEX_PID" 2>/dev/null && echo running || cat /tmp/codex-out.txt
```

Do NOT wrap headless codex in tmux for backgrounding. tmux's value is a human-attachable terminal; automation pays its full cost for nothing: `capture-pane` merges stdout/stderr (breaks token parsing), exit codes are lost, orphan sessions accumulate. CLI flag drift isn't mitigated either — the same command line runs inside the pane. For follow-ups, reuse the *conversation*, not a terminal process: `codex exec resume <session-id>` (Mode C) survives process exit at zero residency cost.

### Status check — "is it doing anything?"

**Prerequisite: background runs should use `--json`.** Verified (0.46.0): JSONL events stream to the output file as they happen — each reasoning step, each command (`item.started` with `status: in_progress`, then `item.completed` with exit code), so the file IS the live status. Non-JSON mode prints progress to stderr but less structured.

Three questions, three checks:

```bash
# 1. Alive?
kill -0 "$CODEX_PID" 2>/dev/null && echo running || echo exited

# 2. What is it doing right now? (truncate — events can embed whole file contents)
tail -3 /tmp/codex-out.txt | cut -c1-300

# 3. Stuck? Compare size across two checks ~2-3 min apart.
ls -l /tmp/codex-out.txt
```

Interpretation:
- Last event is `item.started` with a `command` → it's running that command. Long commands (test suites, big greps) legitimately produce no new events for minutes — not stuck.
- Alive + file size unchanged across two checks several minutes apart AND no `item.started` in flight → likely stuck; let `timeout` reap it or `kill "$CODEX_PID"`.
- Last event is `turn.completed` → done; collect output (`usage` field has token counts in `--json` mode).

Don't `cat` the whole output file as a status check — `command_execution` events embed full command output (can be tens of KB). `tail | cut` is the right shape.

## Timeout

- Diff review: 5 min (`timeout 300 codex ...`).
- Plan / architecture: 10 min (`timeout 600 codex ...`).

`timeout` is GNU coreutils. Available on Linux by default; on macOS available as `timeout` if installed via `brew install coreutils` (this user has it). If not available, omit the wrapper — Codex will eventually return on its own.

## Output capture

For `codex review` and non-JSON `codex exec`: stderr contains `tokens used: N`. Parse from stderr.

For `codex exec --json`: tokens in stdout JSONL `turn.completed.usage`. Stderr contains diagnostics only.

## Web search

Pass `--search` (global, before subcommand) only when the review needs live docs/API specs. It is metered — do not enable by default. The old `--enable web_search_cached` syntax is no longer the canonical interface.

## Common command mistakes

- ❌ `codex exec` without `-a never` → hangs waiting for tool approval (no human, no TTY in headless mode).
- ❌ `codex exec -a never "<prompt>"` → `unexpected argument '-a' found`; `-a` is global-only, put it before `exec`.
- ❌ `codex review ...` on a version without the `review` subcommand (e.g. 0.46.0) → "review" becomes a TUI prompt and hangs forever headless. Run the version gate check first.
- ❌ Using `--full-auto` for review → flag availability varies and auto-write modes are unsafe for review. Use `-a never -s read-only`.
- ❌ `codex review -s read-only --base main "<prompt>"` → `-s` not accepted by `review`; must be global.
- ❌ `codex review` without `--base`/`--uncommitted`/`--commit` → reviews entire repo, not the diff.
- ❌ `codex exec` without `-C "$REPO"` → may run from wrong cwd, see no source files.
- ❌ `codex exec` without `-s read-only` → may modify files (Codex default is `workspace-write`).
- ❌ `codex exec resume <id> "<prompt>" -C "$REPO" -s read-only` → flags don't apply to resume; move them before `exec`.
- ❌ `codex review --xhigh` on a 5-line diff → wastes ~$2 in tokens.
- ❌ Passing `~/.claude/plans/foo.md` as a path → Codex sandbox can't read it; embed content in prompt instead.
- ❌ Forgetting `2> stderr-file` → token count is lost; cost summary missing (non-JSON modes).
- ❌ Forgetting `timeout 300` → if reviewer somehow hangs despite `-a never`, you're stuck indefinitely.
