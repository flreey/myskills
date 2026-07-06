---
name: loop-spec-author
description: "Use when the user wants to turn a goal into a runnable, self-terminating loop spec before handing it to an executor — \"帮我定个 loop / 逼出退出条件 / 这个该怎么 loop / 反复做到符合预期\". Forces a machine-checkable DONE (turning subjective \"cliffs\" into measurable gradients), scopes uncheckable parts out as human votes, emits a consumer-agnostic loop spec. Explicit-invoke only. NOT for requirements/PRD/idea discovery (use brainstorming / agile-prd), NOT a loop executor (hand the spec to agile-dev-agent / ralph-loop / manual)."
---

# Loop Spec Author

## Purpose

Turn a vague goal into a **loop spec**: a short artifact whose center is a *runnable* exit condition, so an executor (or the user) can iterate without re-describing the chain every time.

Core principle:

> You do not loop on a task. You loop toward a runnable DONE. If DONE is not runnable, there is no loop yet — only a wish.

This skill is a **converging interrogator**, not a brainstormer. Its questions stop when DONE can be run, not when the user feels good. A clarified goal that still has no runnable DONE is a **failed** output, not a partial success.

## Premises

- Tool-agnostic process skill. Works in any agent CLI; names no host-specific tools.
- **Output is consumer-agnostic**: the spec can feed agile-dev-agent, ralph-loop, a `/loop` command, a workflow script, or a human iterating by hand.
- **v1 emits a spec only. It does not execute the loop** and does not write executor-specific adapter code.
- **Explicit-invoke only.** Do not fire on a normal "build X / fix Y" request.
- Checked 2026-06.

## Use When

- "帮我定个 loop / 这个该怎么 loop / 反复做到符合预期为止"
- the user wants an exit condition / DONE forced out of a fuzzy goal
- the user has an iterative goal and wants it shaped before handing to an executor

## NOT For

- Requirements gathering, PRD normalization, or idea discovery → that is brainstorming / agile-prd. Producing "a clearer goal" is this skill failing.
- Executing the loop → hand the finished spec to agile-dev-agent / ralph-loop / `/loop` / manual iteration.
- One-shot, non-iterative tasks (rename a symbol, answer a question, single edit). If the task completes in one pass with no "until good enough", there is no loop — say so and stop. Do not wrap loop machinery around it.

## The One Rule

**Produce a runnable DONE before writing any iteration step.**

- A runnable DONE is a check you can execute *right now*, against the current unfinished state, that returns pass/fail (ideally plus a number). "tests in `X` pass", "`cmd` exits 0", "failing-case count == 0", "judge score ≥ 8 on rubric R".
- If part of the goal has no runnable DONE: **do not invent one and do not loop blindly.** Scope the loop down to the checkable part, and mark the rest as a `human vote` in the spec. Shipping a scoped loop + an explicit human vote is a correct outcome.
- Never emit a spec whose DONE is "looks good", "feels right", or anything you cannot run. A loop with an unrunnable DONE iterates confidently toward the wrong target — worse than no loop.

## Authoring Order — backwards, outside-in

Fill in this order. Most people start at step 5; that is the mistake.

1. **真目标 (real goal)** — one plain sentence. What "符合预期" actually means to a human.
2. **DONE** — the runnable exit condition. **This is where 80% of the work is** (see Cliff → Gradient). If you cannot write a runnable DONE here, STOP and either manufacture an oracle or scope it down per The One Rule. Do not proceed to steps.
3. **进度信号 (progress signal)** — the number that moves monotonically toward DONE. Often falls straight out of DONE.
4. **不变量 (invariants)** — what must never break (anti-cheat; see Anti-Goodhart).
5. **每轮动作 (per-iteration action)** — what one iteration does. Only meaningful once DONE exists.
6. **三个出口 (the three exits)** — success / stuck / budget.
7. **人工检查点 (human checkpoints)** — where a person keeps veto.

## Field-count Rule — invariant core + conditional shell

Do not ask a fixed list of questions. The number of fields scales with the task, but the scaling has a rule.

**Invariant core (always present, never droppable):**
- DONE (runnable)
- exits (at least: when to give up)
- per-iteration action (may default to the standard change → check chain)

**Conditional shell (include only when its trigger fires):**

| Field | Include when | Drop when |
|---|---|---|
| 真目标 | DONE is a proxy (DONE ≠ the real goal itself) | DONE *is* the real goal |
| 进度信号 | DONE is a cliff (binary, no partial credit) | DONE is already a gradient → it is the signal |
| 不变量 | DONE is cheatable (the loop can edit the checker) | DONE is tamper-proof (read-only tests, external judge) |
| 状态落盘 | loop spans many iterations / sessions / long context | short loop in one pass |
| 人工检查点 | action is irreversible / high-risk / outward-facing | cheap and reversible |

Hard constraint: **the shell is flexible, DONE is not.** Never drop DONE to "keep it light". Every shell trigger above is a property of DONE or the action — diagnose those properties, then activate the matching fields.

## Cliff → Gradient — making DONE runnable

A cliff = the only available check outputs {pass, fail} with no signal in between ("is it good?"). A gradient = a check that outputs a score or an ordered set of gates. Convert cliffs using these, **in priority order — exhaust mechanical checks before reaching for a judge:**

1. **Decompose one big binary into N small binaries; the count is the gradient.** "is this well-designed?" → 20 checkable assertions; 12/20 → 18/20 is a gradient.
2. **Return distance, not verdict.** Not "do tests pass" but "how many fail": 8 → 3 → 0. Also: error count, diff size vs golden, numeric metric (latency ms, accuracy). Pick something continuous and monotone toward the goal.
3. **Ladder of ordered milestones.** compiles → runs without crash → happy path → edge cases → perf bar. Each rung a small cliff; the ladder is a gradient. Size each rung so one iteration can plausibly clear it.
4. **Golden / reference anchoring.** distance-to-reference: snapshot diff, pixel/DOM diff vs design, golden input/output pairs.
5. **Rubric + synthetic oracle (last resort, for genuinely subjective targets).** An explicit rubric scored per dimension, with anchor examples (what a 2/5 vs 5/5 looks like). Prefer a **mechanistic synthetic oracle** (e.g. a scripted player/user model that yields a pass-rate) over an LLM judge when the domain has clear mechanics — it is less noisy and harder to game.

If after all five a chunk still has no runnable check: that chunk is **un-loopable**. Scope it out as a human vote. Do not fake it.

## The Three Exits — always present

A loop with only a success exit either hangs or burns budget. Specify all three:

- **Success** — DONE passes (all gates green / score in target band).
- **Stuck** — N consecutive iterations with no progress-signal movement (oscillation, same failure repeating). Action: stop, hand the conflict to a human. Stuck often signals a real design tension the loop cannot resolve.
- **Budget** — max iterations / token / time cap reached. Action: stop, surface the best candidate so far.

Stuck and budget both **escalate to a human**; they do not keep spinning.

## Anti-Goodhart — assume the loop will cheat

Once a proxy metric is the target, an executor will optimize the metric, not the real goal — it will delete the failing test, hardcode the expected output, or special-case the assertion to satisfy DONE. This is default behavior, not a hypothetical. Defend in the invariants field:

- **Held-out checks** the loop cannot see or modify (e.g. the test file is read-only to it).
- **Multiple independent metrics** — one is easy to game, a set is hard to game at once.
- **Human spot-check** that the metric still correlates with the real goal (proxies drift).

If DONE has no cheat surface (tamper-proof external check), the invariants field can be thin or absent — but say so, do not skip it silently.

## Smell Tests — run before emitting the spec

1. **Runs now?** Can you execute DONE against the current unfinished state and get a number? No → it is not machine-checkable yet; go back to Cliff → Gradient.
2. **Zero-context stop?** Could someone with no context read this spec and know when to stop? No → DONE is underspecified.
3. **Unhappy pass?** Is there a way to satisfy DONE you would be unhappy with? Yes → add an invariant.
4. **One iteration moves the needle?** Can a single iteration plausibly move the progress signal? No → loop granularity too big; split into nested loops with nearer exit conditions.

A spec that fails any smell test is not ready to emit.

## Human Confirmation Gate

Before finalizing the spec, ask the user to confirm **DONE and the invariants** — not the steps. This is the single highest-leverage human gate: a wrong step self-corrects inside the loop, but a wrong DONE makes the loop run confidently toward the wrong target. Do not ask the user to approve the per-iteration steps; ask them to approve the definition of "done" and the anti-cheat constraints.

## Output Format

Emit one markdown loop spec. Include core fields always; include shell fields only when triggered. End with a Handoff block.

```markdown
## Loop Spec: <name>

真目标:   <one plain sentence — only if DONE is a proxy>
DONE:     <a check you can run NOW, returns pass/fail (+ number)>
进度信号: <the monotone number — omit if DONE is already a gradient>
不变量:   <what must never break; held-out checks; what the loop may NOT edit — omit if DONE is tamper-proof>
每轮动作: <what one iteration does: change → re-run DONE>
状态落盘: <where spec + per-iteration progress live — omit for short single-pass loops>

出口:
  成功 = <DONE all green>
  卡死 = <N iterations no signal movement> → 交人
  预算 = <max iters / tokens / time> → 交出最优候选

人工票 (human votes — the parts that stay un-loopable):
  - <subjective chunk that has no runnable check, left for human judgement>

人工检查点: <where a person keeps veto — omit if action is cheap & reversible>

## Handoff
- agile-dev-agent: feed DONE + 每轮动作 as the Dev Loop objective; 出口 → its stop conditions.
- ralph-loop / /loop: wrap 每轮动作; check DONE each cycle; honor 卡死/预算.
- manual: run 每轮动作 by hand, re-run DONE each pass, stop on any of the three exits.
```

If a chunk of the goal is un-loopable, it goes in `人工票` and the loop is scoped to the rest. Saying "this part is not loop-able, do it by hand" is a valid, complete output.

## Tone

Direct. The interrogation converges and stops — at DONE-is-runnable, not at user-satisfaction. Refuse to emit a loop spec when no runnable DONE exists for any in-scope chunk; offer the scope-down + human-vote alternative instead.
