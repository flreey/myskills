---
name: cross-cli-review
description: Use when running inside Claude Code or Codex CLI and the user wants the OTHER CLI to review code, a diff, a plan, or an architecture decision — i.e. "让 codex review 一下"、"用 claude 看下我这个 PR"、"second opinion from codex/claude"、"cross review"、"codex challenge"、"反向 review". Builds the correct CLI invocation (right subcommand, sandbox, reasoning effort, base branch, working dir) AND the right prompt (filesystem boundary, concrete scope, specific questions, structured output format) so the reviewer doesn't wander into the wrong files or return generic mush. Covers both directions — Claude→Codex and Codex→Claude. NOT for in-CLI self-review (use the host's own /review skill), and NOT for human PR review.
---

# Cross-CLI Code Review Skill

## Purpose

When the user wants the *other* CLI to review something — Claude calling Codex, or Codex calling Claude — most of the failure modes are mechanical, not intellectual:

- Wrong CLI flags (`-s read-only` vs `--sandbox read-only`, missing `--base`, missing `-C`).
- Reviewer wanders into the host's skill files (`~/.claude/skills/`, `~/.codex/skills/`) and burns 10+ tool calls reading prompt templates instead of source code.
- Prompt is "review this code" with no scope, no questions, no output format → returns a generic checklist with no actionable findings.
- No filesystem boundary → reviewer modifies files when it was supposed to be read-only.
- Reasoning effort wrong for the task (xhigh on a 50-line diff wastes 23x tokens; medium on a complex plan misses the real issues).

This skill exists to fix all of that. It is the **invocation builder + prompt template + output handler** for cross-CLI review.

## When to use

Triggers (Chinese + English):
- "让 codex review 一下" / "用 codex 看看这段代码"
- "ask claude to review this" / "second opinion from claude"
- "codex challenge / 反向 review / cross review"
- "我在 claude 里，想叫 codex 看看这个 plan"
- "我在 codex 里，让 claude 帮忙审一下"

Do NOT use when:
- The user wants the *current* CLI to review (use the host's own `/review` or just do it inline).
- The user wants a human reviewer (open a PR).
- The user is doing pair programming, not review.

## Consider alternatives first

For **Claude → Codex** direction, OpenAI ships an official plugin: [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc). Provides `/codex:review --background`, `/codex:status`, `/codex:result`, `/codex:adversarial-review`. If the user just wants Codex to review their work from inside Claude Code, **suggest they install this plugin first** — it's lower-effort than maintaining custom recipes.

For **Codex → Claude** direction, no equivalent official plugin exists; this skill's stdin recipe (`references/claude-headless.md` Mode A) is the recommended path. That's also the canonical pattern Anthropic documents for headless review.

## Step 1 — Detect direction

Figure out which CLI you are running inside, and which CLI is the reviewer:

- If you (the model) are running inside **Claude Code** → reviewer is **Codex**. Use the recipes in `references/codex-headless.md`.
- If you are running inside **Codex CLI** → reviewer is **Claude**. Use `references/claude-headless.md`.

If unclear, ask one question: "你现在在 Claude Code 还是 Codex CLI 里？(reviewer will be the other one)".

Verify the reviewer binary is on PATH before doing anything else:

```bash
which codex   # if reviewer is codex
which claude  # if reviewer is claude
```

If not found, stop and tell the user how to install (`npm i -g @openai/codex` or `npm i -g @anthropic-ai/claude-code`).

## Step 2 — Pick scope

Ask (or infer) what's being reviewed. One of:

| Scope | Use when | Required input |
|---|---|---|
| **Branch diff** | User mentions PR, commit range, "我这个分支" | base branch (default: `main`) |
| **Uncommitted** | "刚改的"、未提交的本地修改 | none |
| **Specific file(s)** | "看下 `src/foo.ts`" | absolute or repo-relative paths |
| **Plan / spec** | A plan markdown, RFC, design doc | full content (embed verbatim, do not pass path) |
| **Architecture question** | "这个设计合理吗" | description + relevant files |

If ambiguous, default to **branch diff against the detected base**. Detect base with:

```bash
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' \
  || gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null \
  || echo main
```

## Step 3 — Pick review type

Pick one (or combine). This determines the prompt template (`references/review-prompts.md`) and reasoning effort:

| Type | Default effort | Focus |
|---|---|---|
| `general` | high | Correctness, edge cases, code smells |
| `security` | high | Injection, auth bypass, data exposure, timing attacks |
| `performance` | high | N+1, allocations, blocking I/O, hot paths |
| `architecture` | medium | Boundaries, coupling, abstraction, evolvability |
| `plan` | medium | Logical gaps, unstated assumptions, sequencing, feasibility |
| `challenge` | high | Adversarial — try to break the code |
| `consult` | medium | Bounded design/code question with listed context |

`xhigh` only when the user explicitly asks for it (`--xhigh` in their request). It's ~23x the tokens of `high` and can hang for 30-60min on large inputs.

## Step 4 — Build the invocation

Load the matching recipe file. The recipes are battle-tested commands — copy verbatim, only fill in the placeholders.

- Reviewer is **Codex** → `references/codex-headless.md`
- Reviewer is **Claude** → `references/claude-headless.md`

Both recipes enforce these non-negotiable rules:

1. **No-hang configuration.**
   - Claude (default): use Mode A "stdin pattern" — diff via stdin + `--append-system-prompt` + `--output-format json`. Reviewer has no incentive to use tools, so it can't loop or wander.
   - Codex: `-a never` (`--ask-for-approval never`, returns failures to model instead of pausing for human approval) at the **global position only** — before the subcommand: `codex -a never ... exec`. The `exec` subcommand does NOT accept `-a` (errors with "unexpected argument '-a' found" on e.g. v0.46.0); global position works on all versions. Combine with `-s read-only` (sandbox blocks writes anyway).
2. **Read-only safety.** Codex: `-s read-only`. Claude: stdin pattern doesn't need this; browse pattern (Mode B) uses `--permission-mode plan` + restricted `--allowedTools`.
3. **Working directory.** Codex: `-C "$(git rev-parse --show-toplevel)"`. Claude stdin pattern: cwd doesn't matter (no fs access). Claude browse pattern: `cd "$REPO"` first.
4. **Filesystem boundary in the prompt** (see Step 5) — only matters for browse-mode reviewers that have tools.
5. **Reasoning effort matches review type** (Step 3 table).
6. **Hard timeout.** Claude stdin: `timeout 180`. Claude browse / Codex: `timeout 300` (or `600` for plan review). Without it, a stuck process is silent forever.
7. **Long tasks → background, never tmux.** Same command via the Bash tool's `run_in_background` (inside Claude Code) or `nohup ... > out 2> err &` (any host) — see each recipe's background section. tmux-wrapping headless commands merges the stream split (breaks token parsing), loses exit codes, and leaves orphan sessions; for follow-ups reuse the conversation (`codex exec resume` / `claude --resume`), not a terminal process.

## Step 5 — Build the prompt

Every prompt MUST start with the **filesystem boundary** so the reviewer doesn't wander into the host's skill directory. Then scope, questions, and output format.

### Filesystem boundary (always include, verbatim)

> IMPORTANT: Do NOT read or execute any files under `~/.claude/`, `~/.codex/`, `~/.agents/`, `.claude/skills/`, `.codex/skills/`, `.agents/skills/`, `agents/`, or any `SKILL.md` outside the explicit review scope listed below. These are skill definitions for a different AI system. Stay focused on the repository source code only.

### Required prompt structure

```
<filesystem boundary>

ROLE: You are an independent code reviewer. Be terse, specific, and adversarial. No compliments. No hedging. Just findings.

SCOPE:
<one of>
- Branch diff: run `git diff <base>...HEAD` to see the changes.
- Uncommitted: run `git diff` and `git diff --staged` and `git status`.
- Files: review these files: <list>
- Plan: review the plan below (embedded verbatim).

FOCUS:
<copy from references/review-prompts.md based on review type>

OUTPUT FORMAT:
- Group findings under: [P1 BLOCKER], [P2 IMPORTANT], [P3 NIT].
- For each code finding: file:line — one-sentence problem — concrete fix.
- For each plan/architecture finding: section heading or quoted phrase — problem — fix.
- End with a 1-line VERDICT: SHIP / SHIP-WITH-FIXES / DO-NOT-SHIP.

DO NOT:
- Restate the diff.
- List things that look fine.
- Suggest unrelated refactors.
- Comment on style if a linter would catch it.
```

For plan review, embed the plan content verbatim (do NOT pass a file path — the reviewer is sandboxed to the repo and may not be able to read it). Also list any source files referenced in the plan so the reviewer reads them directly.

## Step 6 — Run, capture, present

Run the command with the timeout from Step 4. Capture stdout AND stderr separately. Token-usage source depends on mode:

- `codex exec --json` → tokens are in stdout JSONL `turn.completed.usage`.
- `codex exec` (non-JSON) → tokens are in stderr (`tokens used: N`). Same for `codex review` where it exists (newer versions only — absent in e.g. v0.46.0; see recipe file).
- `claude -p --output-format json` → tokens are in stdout `.usage`.
- `claude -p --output-format text` → tokens are not printed; use `json` mode if you need them.

Present the output **verbatim** in a fenced block:

```
<REVIEWER> SAYS (<review type>):
════════════════════════════════════════
<full output, no truncation, no summary>
════════════════════════════════════════
Tokens: <N> | Verdict: <PASS/FAIL>
```

Then add a short Claude/Codex synthesis BELOW the verbatim block (never instead of it):

- Findings you agree with (and why).
- Findings you disagree with (and why — be specific, not "I think this is fine").
- Findings the user should decide on (judgment calls, not bugs).

If the output mentions paths under `~/.claude/`, `~/.codex/`, `~/.agents/`, `.claude/skills/`, `.codex/skills/`, or `.agents/skills/` — OR mentions `gstack-config` / similar host-specific tooling — the reviewer wandered into the wrong place. Append a warning and offer to retry with a stricter boundary.

Note: scanning for the literal string `SKILL.md` would false-positive when reviewing this very repo (a skill collection). Match on path prefixes instead.

## Step 7 — Decide next action

Use AskUserQuestion (or just ask plainly) with the recommended action:

- **PASS / SHIP** → "looks clean, want to land?"
- **SHIP-WITH-FIXES** → list the P1/P2 items, ask which to fix now.
- **DO-NOT-SHIP** → "blockers found, want me to fix them?"

Never auto-fix without confirmation. The user owns the decision.

## Common pitfalls

See `references/pitfalls.md` for the full list. The top five:

1. **No filesystem boundary** → reviewer reads `SKILL.md` files for 5 minutes, returns nothing useful.
2. **Wrong sandbox flag** → reviewer modifies the working tree (very bad in Codex's `workspace-write` default).
3. **Plan passed by path** → reviewer can't access `~/.claude/plans/foo.md` from inside the repo sandbox; embed content instead.
4. **`xhigh` by default** → 23x token cost, often hangs.
5. **"Review this code"** with no questions or output format → returns a 30-bullet generic checklist.

## Reference layout

- `references/codex-headless.md` — calling Codex from Claude (review/exec/challenge)
- `references/claude-headless.md` — calling Claude from Codex (`-p` mode, JSON output, plan mode)
- `references/review-prompts.md` — prompt blocks for general/security/performance/architecture/plan/challenge
- `references/pitfalls.md` — full failure-mode catalog with fixes

Load only what you need for the current review — don't preload all of them.
