# Cross-CLI Review Pitfalls

Failure modes seen in practice. Each entry: symptom → root cause → fix.

---

## P1: Reviewer reads skill files instead of source code

**Symptom:** Output mentions `gstack-config`, `SKILL.md`, `~/.claude/skills/`, `~/.codex/skills/`, or returns a generic checklist that ignores your actual code.

**Cause:** No filesystem boundary in the prompt. The reviewer's auto-discovery finds `.claude/` or `.codex/` skill directories first and reads those for context.

**Fix:** Always start the prompt with the filesystem boundary block from `SKILL.md` Step 5. After running, scan output for the trigger words above; if any appear, retry with a stricter boundary.

---

## P2: Reviewer modifies the working tree

**Symptom:** `git status` shows changes after the review. Files have been "fixed" or "improved".

**Cause:**
- Codex: missing `-s read-only` (default is `workspace-write`).
- Codex: user's shell aliases `codex` to `--dangerously-bypass-approvals-and-sandbox` (overrides without explicit `-s`).
- Claude: missing `--permission-mode plan`, or used `bypassPermissions` / `acceptEdits`.

**Fix:** Always pass the read-only flag explicitly. Verify post-call with `git status`. If files were modified, `git stash` immediately before deciding what to keep.

---

## P3: Plan passed by path, reviewer can't read it

**Symptom:** Reviewer spends 5+ tool calls trying to find the plan, gives up, returns a generic plan-review template with no specific findings.

**Cause:** Plan file (`~/.claude/plans/foo.md`, `tasks/todo.md`) is outside the reviewer's sandbox. Codex with `-C "$REPO"` cannot read `~/.claude/plans/`. Claude with `--add-dir "$REPO"` cannot either.

**Fix:** Read the plan file yourself, embed the FULL CONTENT verbatim in the prompt under `THE PLAN:`. Do NOT pass a path. Also list any source file paths referenced inside the plan so the reviewer reads them directly.

---

## P4: Reasoning effort wrong for the task

**Symptom:**
- Hangs for 30+ minutes, eventually times out or returns truncated output.
- OR: review is shallow, misses obvious issues, returns in 30 seconds.

**Cause:** `xhigh`/`max` on a small diff (~23x token cost, exponential time on large context). Or `low`/`medium` on a complex architecture / plan review.

**Fix:** Match effort to task using the table in `SKILL.md` Step 3. Default to `high` for diff/security/perf, `medium` for architecture/plan/consult. Only use `xhigh`/`max` on explicit user request, and only on bounded inputs.

---

## P5: Generic prompt → generic output

**Symptom:** Output is a 30-bullet checklist of generic advice ("consider adding tests", "validate inputs", "improve error handling") with no file or line references.

**Cause:** Prompt was "review this code" or "look at the diff and tell me what you think". No specific questions, no required output format, no severity tags.

**Fix:** Use the templates in `review-prompts.md`. Every prompt MUST include:
1. Specific numbered focus areas (5-8 items).
2. Required output format with severity tags ([P1]/[P2]/[P3]).
3. "DO NOT" section (no compliments, no restatement, no unrelated refactors).
4. Concrete examples of what counts as a finding vs. not.

---

## P6: Reviewer wanders the entire repo

**Symptom:** Reviewer reads 50+ files, returns findings about code that wasn't changed.

**Cause:** No scope in the prompt. Reviewer searches the whole repo trying to be helpful.

**Fix:**
- Diff review: explicitly say `run \`git diff <base>...HEAD\`` and review ONLY the changed lines.
- File review: list exact file paths.
- Add to DO NOT: "Do not review files outside the listed scope. Do not suggest unrelated refactors."

---

## P7: Token usage / cost runaway

**Symptom:** Single review burns $5-50 in tokens.

**Cause:**
- No `--max-budget-usd` cap (Claude).
- `xhigh`/`max` on large input.
- Reviewer in a loop reading many files.

**Fix:**
- Claude: always pass `--max-budget-usd <N>` with a sensible cap (5 USD for diff, 10 USD for architecture).
- Codex: prefer `high` over `xhigh` unless explicitly asked.
- Bound the scope (no whole-repo review without a reason).

---

## P8: Output truncated / lost

**Symptom:** Review output ends mid-sentence, or no token count visible.

**Cause:**
- Stderr not captured separately (Codex prints token usage there).
- Used `--output-format text` and the text exceeded terminal buffer.
- Review hit timeout and was killed.

**Fix:**
- Always redirect stderr to a temp file: `2> /tmp/<reviewer>-err.txt`.
- For long reviews, use `--output-format json` (Claude) or `--json` (Codex) and parse.
- For very long reviews, increase timeout to 10 min.

---

## P9: Two CLIs disagree, user gets stuck

**Symptom:** Claude says ship, Codex says don't ship (or vice versa). User doesn't know what to do.

**Cause:** Real disagreement (different mental models) OR one of the reviewers got bad context.

**Fix:**
1. First, check both reviewers had the same scope. Re-run if one was reading the wrong thing.
2. If genuinely disagreed: present both verdicts side-by-side, identify the specific finding(s) they disagree about, and explain WHY each thinks what it thinks.
3. The user decides. Do not auto-resolve. The user has context (domain, business, taste) the models don't.

---

## P10: Session pollution

**Symptom:** Reviewer's previous session contaminates the current review (carries over assumptions from a different repo, different language).

**Cause:**
- Codex: passed a `session-id` from an unrelated session.
- Claude: didn't pass `--no-session-persistence`, picked up a stale session.

**Fix:**
- Codex: only resume a session when continuing the same review thread.
- Claude: always pass `--no-session-persistence` for one-shot reviews.

---

## Quick triage checklist

Before running, verify:

- [ ] Filesystem boundary is the FIRST line of the prompt.
- [ ] Sandbox flag is explicit (`-s read-only` or `--permission-mode plan`).
- [ ] Working dir pinned (`-C "$REPO"` or `cd "$REPO" && --add-dir "$REPO"`).
- [ ] Reasoning effort matches review type.
- [ ] Prompt has specific focus, output format, and DO NOT section.
- [ ] Scope is concrete (diff base / file paths / embedded plan content).
- [ ] Stderr captured to a temp file.
- [ ] Cost cap set (Claude: `--max-budget-usd`).
- [ ] Timeout matches review type (5min / 10min).

After running, verify:

- [ ] `git status` is unchanged from pre-review state.
- [ ] Output doesn't mention skill files / wrong directories.
- [ ] Token count is in the output.
- [ ] Findings reference specific file:line locations.
- [ ] Verdict line is present.
