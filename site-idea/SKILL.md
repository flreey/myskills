---
name: site-idea
description: 新想法验证（批量页面之前）：一个产品还只是想法、打算靠大量能被 AI 找到和推荐的页面增长时，先把想法拆成任务空间（只保留会改变答案的维度）、算组合数、抽样写成真实对话、看 ChatGPT 等助手现在答得好不好（答案缺口）、找外部真实提问，最后由站长决定做、缩小范围还是放弃；之后给已验证维度补长尾取值用 extend。Also for 新项目 GEO、想法验证、任务空间、AI 答案缺口、从 0 开始做 GEO、长尾取值扩展。不用于：已上线站点的 AI 可见度（site-geo）、找关键词（site-research）、已有站点的页面规划（site-plan）、做页面（site-batch）。
---

# site-idea: is there a gap worth hundreds of pages?

Idea → task space → sampled conversations → how assistants answer today → owner's decision.
First stage of a new GEO project; nothing is built here. Programmatic pages only work when each page
holds an answer the assistants cannot give on their own, so this skill finds out whether such answers
exist before anyone writes a template.

Engine (Python stdlib): `python3 <skill-dir>/scripts/geo_idea.py --root <project> <command>` with
`init`, `space`, `sample`, `probes`, `report`, `decide`, `extend`, `check`. State is `<project>/geo/`; its
contract, shared with the later geo stages, is [references/state.md](references/state.md).

## Iron rules

1. **A dimension makes pages only if it changes the answer.** `changes_answer: true` needs a `why`
   naming how the answer differs. Who asks, the country or a synonym usually does not: keep them for
   wording.
2. **AI answers are samples.** Record platform, model as shown, mode, date and the full answer. Never
   report them as rankings or as what all users see.
3. **The user's AI accounts need their go-ahead in chat.** Default: hand them `gap/probes.md` and read
   back what they paste into `gap/raw/`. Driving their logged-in browser, or an API key, only after
   they say so for this project.
4. **Signals are real or absent.** Outside evidence is a URL with a short real quote. None found is
   written as none.
5. **The decision is the owner's.** The report gives a hint; `decide --by user` runs only after they
   chose in chat. No asset, template or page work starts before a `go` or `narrow` is recorded.
6. **Writes stay in `geo/`.** This skill touches no site, registry or other project file.

## Workflow

1. **Start.** `init --name <Name> --idea "<who, situation, task in one sentence>"`. Fill
   `project.json` (`audience`, `market`, `platforms`, `north_star`) from what the user said; ask only
   for what is missing and changes the work (market language, target assistants).
2. **Task space.** Write `geo/dimensions.json` (shape in references/state.md): entity, task and
   constraint dimensions, their values with a source, excludes for combinations that make no sense or
   that the product will not serve. Run `space`; fix every ERROR, read every WARN. Show the user the
   generating dimensions, the described-only ones and the count in a short table, and adjust with
   them before sampling: a wrong dimension here multiplies into every later page.
3. **Sample.** `sample --n 40` (at least the widest dimension's value count). For each row write
   `persona`, `opening`, `follow_ups` and look for `signals`, following
   [references/conversations.md](references/conversations.md). Then `probes` renders the sheet.
4. **Probe.** Per rule 3: give the user `geo/gap/probes.md` (one new chat per conversation, each
   target platform, paste the whole answer into the named file), or run it the way they approved.
   Browser runs follow [references/probe-runs.md](references/probe-runs.md): hand them to a Grok Bot
   via `gbot` when available; otherwise use a separate agent with one call per conversation.
   Save every answer under `geo/gap/raw/` and add a row to `geo/gap/runs.jsonl` with `gap: null`.
5. **Judge.** Label every run with [references/gap-rubric.md](references/gap-rubric.md): `gap`,
   `gap_note`, `cited`, `recommended`. Then `check`, then `report`.
6. **Decide.** Show the user `geo/gap/report.md`: the share of high-opportunity combinations, the
   values where gaps concentrate, which of them have outside signals, and what the assistants
   recommend today. Offer the three choices: `go` (whole space), `narrow` (the subspace of strong
   values), `stop` (or change the idea and return to step 2). Record their answer with
   `decide --verdict <v> --by user [--subspace '<json>'] [--note "<why>"]`.

## Long tail: more values later

When pages exist and the owner wants more values of a dimension the gap check already covered (more
events, formats, places), add the values to `geo/dimensions.json`, then, after the owner agrees in
chat, `extend --dimension <id> --values a,b --by user`. No new probing is needed: the template's
validation carries over, and site-batch's gate and wave funnel judge the new pages. A new dimension or
a new task type is a new space: sample and probe it (20–30 combinations are enough for one dimension)
before `decide`.

## Reading the report

- `hint` is `go` when the high share reaches the threshold (default 0.33, `report --threshold`),
  `narrow` when only some values with two or more probed combinations reach it, `stop` otherwise.
  It is a starting point for the conversation, not the verdict.
- High share with no signals: the gap may be real but nobody asks. Say so; it argues for narrowing
  to the values that have both.
- What assistants recommend and cite in `good` answers is the competition; in high-gap answers it is
  the list of sources to appear in later (off-site work).
- Fewer than about 25 probed combinations, or a single platform: say the result is thin.

## Report

Stage reached and files written → the space (generating dimensions, count) → gap results with sample
size, platforms and dates → signals coverage → the owner's decision, or the question waiting for it →
next step: after `go` or `narrow`, site-batch (assets, facts and templates, then waves and
measurement).

## Premises

Written 2026-11-17 from the GEO zero-to-one method (`~/Projects/GEO/geo-zero-to-one.md`). The 0.33
threshold and 40 samples are starting values with no project behind them yet: recalibrate after the
first real run and record what changed here.
