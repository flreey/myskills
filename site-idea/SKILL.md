---
name: site-idea
description: GEO 新页面空间验证（批量页面之前）：先从真实数据画需求地图（站内/API/MCP 搜索、没找到留言、生成描述、论坛原话：谁、要完成什么、卡在哪、在哪里问），再把每个需求从推荐、对比、出问题、问做法、购买、替代、条件、交给 agent 等角度展开成问题库（每条标依据，模型写的先算假设），可选竞品反推加盲测，然后拆任务空间（只保留会改变答案的维度）、抽样成真实对话、看 ChatGPT 等助手答得好不好（答案缺口）、我们出没出现、它改写成了哪些搜索词、靠哪些来源回答，再补搜索引擎和 agent/API 两个渠道的证据，按“需求 × 渠道”给结论（建页、站外、产品和文档、暂不做），最后由站长决定哪些格子做页面；新想法和已上线站点要开的新页面空间都适用；之后给已验证维度补长尾取值用 extend。Also for 需求地图、用户需求研究、问题库、AI 问法、竞品反推、新项目 GEO、想法验证、任务空间、AI 答案缺口、从 0 开始做 GEO、长尾取值扩展。不用于：已上线站点为什么不被推荐、改哪个现有页（site-geo optimize）、找关键词（site-research）、已有站点的关键词页规划（site-plan）、做页面（site-batch）。
---

# site-idea: is there a need, and a gap, worth hundreds of pages?

Real demand → needs → questions from several angles → task space → sampled conversations → how
assistants answer today, and whether they pick us → owner's decision. Nothing is built here.
Programmatic pages only work when each page holds an answer people need and assistants cannot give
on their own, so this skill finds out what people are trying to do and whether such answers exist
before anyone writes a template.

Engine (Python stdlib): `python3 <skill-dir>/scripts/geo_idea.py --root <project> [--geo-dir geo] <command>`
with `init`, `needs`, `bank`, `space`, `sample`, `probes`, `report`, `decide`, `extend`, `check`. State is
`<project>/geo/` (or `--geo-dir` when one repository holds several GEO projects); its contract, shared
with the later geo stages, is [references/state.md](references/state.md).

## When this skill, and when another

| Situation | Start |
| --- | --- |
| An idea, no site yet | here, step 0 with off-site evidence only |
| A live site wants a new space of pages (new long-tail pages, new templates) | here, `init --live`; first-party data leads the demand map |
| A live site is not recommended, or asks which existing page to change | site-geo optimize first (O1–O5: tasks, levers, baseline, source diagnosis); come here only for a new page space |
| Existing pages of one family should become GEO pages | site-geo optimize diagnosis first; site-batch adopt only when it says the pages are the bottleneck |

## Iron rules

0. **The goal card comes first.** Read `geo/goal.md` (written with the owner by the `site` skill)
   before step 0; without it, run the `site` skill's step 0 first. End every report with what this
   step dropped compared with the card, or "nothing".
1. **Needs before dimensions.** No dimension, sample or page before the demand map says who needs
   what and where they ask. A dimension makes pages only if it changes the answer: `changes_answer:
   true` needs a `why` naming how the answer differs. Who asks, the country or a synonym usually does
   not: keep them for wording.
2. **AI answers are samples.** Record platform, model as shown, mode, date and the full answer. Never
   report them as rankings or as what all users see.
3. **The user's AI accounts need their go-ahead in chat.** Default: hand them `gap/probes.md` and read
   back what they paste into `gap/raw/`. Driving their logged-in browser, or an API key, only after
   they say so for this project.
4. **Evidence is real or marked as missing.** Off-site evidence is a URL with a short verbatim quote;
   first-party evidence is a ref (table or export and window) with the query or words. Model-written
   needs and questions are hypotheses until a real source shows the same thing. None found is written
   as none.
5. **Measure the goal, not only the gap.** Every judged run records whether the site was in the answer
   (`own`), what was recommended, the cited sources and, when the browser allows, the search queries
   the assistant ran. A gap says the content has room; only presence and sources say whether pages
   will be found.
6. **The decision is the owner's, per need × channel.** Channels are assistant chat, search engines
   and agents/API/MCP. Probes are evidence for the assistant-chat channel only: the report's `hint`
   never drops a need on its own, and a need with no room in chat may still be worth pages for search
   or agents. `decide --by user` runs only after the owner chose in chat; `go` or `narrow` records which
   part of the space gets pages, and `geo/gap/channels.md` records every cell's lever. No asset,
   template or page work starts before that.
6a. **Dropping needs the owner.** Leaving out a need, audience, channel or lever (at the demand map,
   the bank, the space or the decision) is put to the owner with what it costs (volume, quotes) and,
   once they agree, written under "Not doing" in the goal card. Never as a side remark in a step.
6b. **No pages without a task space.** The question-bank path may sample before `space`, but a `go`
   or `narrow` that leads to pages needs `geo/dimensions.json` checked by `space`, with the page count
   and the assets each combination needs, shown to the owner.
6c. **Tools get one hour.** A probe tool or browser problem not solved in about an hour gets a simpler
   path (hand the sheet to the user, fewer conversations) or is skipped and reported.
7. **Writes stay in the geo folder.** This skill touches no site, registry or other project file.

## Workflow

0. **Start and map demand.** Read `geo/goal.md` (rule 0). `init --name <Name> --idea "<who, situation, task in one sentence>"`
   (`--live --origin <url>` for a live site). Fill `project.json` (`audience`, `market`, `platforms`,
   `north_star`) from what the user said; ask only for what is missing and changes the work. Then
   collect first-party and off-site evidence, group it into needs and write `geo/needs.jsonl`
   ([references/demand-map.md](references/demand-map.md)); `needs` checks it and writes
   `geo/needs.md`. Show the owner the map (needs, counts, where each is asked) and agree which needs
   and audiences to serve.
1. **Question bank.** Expand each chosen need into questions from several angles, with evidence on
   each ([references/question-bank.md](references/question-bank.md), prompt included); run `bank` and
   fix what it flags. In a crowded market, add questions reverse-engineered from competitors
   ([references/competitor-probes.md](references/competitor-probes.md)).
2. **Task space.** Write `geo/dimensions.json` (shape in references/state.md) from the needs: entity,
   task and constraint dimensions whose values change the answer, each value with a source, excludes
   for combinations that make no sense or that the product will not serve. Run `space`; fix every
   ERROR, read every WARN. Show the generating dimensions, the described-only ones and the count in a
   short table, and adjust with the owner before sampling: a wrong dimension multiplies into every
   later page. For each generating dimension, note which assets a page needs and how many
   combinations have them today or could have them (generated, collected): that, not the number of
   questions, sets how many pages are possible. Skipping this step is allowed only for a decision that
   leads to no pages (rule 6b).
3. **Sample.** One of: `sample --n 40` (combinations, at least the widest dimension's value count),
   `sample --from-questions --n 40` (bank questions spread over needs and angles, real wording first;
   `--weight`, `--origin`, `--ids`, `--append` in [references/question-bank.md](references/question-bank.md)),
   or `sample --pool <file> --n 40` (existing pages as candidates, spread over strata such as traffic
   tiers). Fill `persona`, `opening`, `follow_ups` and `signals` where empty, following
   [references/conversations.md](references/conversations.md). Then `probes` renders the sheet.
4. **Probe.** Per rule 3: give the user `geo/gap/probes.md` (one new chat per conversation, each
   target platform, paste the whole answer into the named file), or run it the way they approved.
   Browser runs follow [references/probe-runs.md](references/probe-runs.md): a page script in a
   logged-in browser tab first (it also captures the assistant's search queries); a Grok Bot via
   `gbot` only as a fallback. Rule 6c applies to both. Save every answer under `geo/gap/raw/` and add a row to
   `geo/gap/runs.jsonl` with `gap: null`.
5. **Judge.** Label every run with [references/gap-rubric.md](references/gap-rubric.md): `gap`,
   `gap_note`, `own`, `cited`, `recommended`, `search_queries`, and `outcome` for competitor probes.
   Then `check`, then `report`.
6. **Other channels.** Probes cover assistant chat. For the same needs, collect what is cheap and
   real: search engines (whether our pages and the winners' pages are indexed and rank under the
   assistants' captured queries and the needs' natural wording, from Bing/Google results or Search
   Console); agents, API and MCP (first-party search logs, zero-result queries, tool directory and
   registry presence). Write what was looked at and what was not; "not measured" is a valid cell.
7. **Decide.** Write `geo/gap/channels.md`: one row per need, one column per channel in the goal
   card, each cell with the evidence (or "not measured"), who wins, whether we appear, what only we
   have, and the proposed lever (pages, off-site, product and docs, not now). Show it with
   `geo/gap/report.md`: the share of high-opportunity combinations or
   questions, where gaps concentrate (by value, need, angle, stratum), whether the site is in the
   answers, the sources behind answers without it and the lever hint, the captured queries, and the
   notes. Offer `go` (whole space), `narrow` (the subspace of strong values), `stop` (or change the idea
   and return to step 0). Record their answer with `decide --verdict <v> --by user [--subspace '<json>']
   [--note "<why>"]`. When the owner does not want probes as a precondition, `decide --without-probes`
   records a decision on validated first-party needs instead; say that the gap and presence are then
   unknown. A `stop` for one channel is written in `channels.md`, not as `stop` for the space.

## Long tail: more values later

When pages exist and the owner wants more values of a dimension the gap check already covered (more
events, formats, places), add the values to `geo/dimensions.json`, then, after the owner agrees in
chat, `extend --dimension <id> --values a,b --by user`. No new probing is needed: the template's
validation carries over, and site-batch's gate and wave funnel judge the new pages. New values should
come from the demand map (searches, misses, quotes), not from a word list. A new dimension or a new
task type is a new space: sample and probe it (20–30 combinations are enough for one dimension)
before `decide`.

## Reading the report

- `hint` and `lever_hint` read assistant-chat probes only. Use them for that column of
  `channels.md`, never as the decision for a need.
- `hint` is `go` when the high share reaches the threshold (default 0.33, `report --threshold`),
  `narrow` when only some values with two or more probed combinations reach it, `stop` otherwise.
  It is a starting point for the conversation, not the verdict.
- Read the notes first. A high gap with the site absent from most answers, and answers resting on
  lists, forums or no search, means pages alone will not change who is recommended: plan site-offsite
  (GEO mode) with the pages, or instead of them.
- `lever_hint` follows site-geo's source diagnosis: `onsite` when competitor pages win, `offsite` when
  lists and forums do, `consensus` when the assistant answers without searching.
- High share with no signals: the gap may be real but nobody asks. Say so; it argues for narrowing
  to the values that have both.
- What assistants recommend and cite is the competition; in high-gap answers it is the list of
  sources to appear in later (off-site work).
- Fewer than about 25 probed combinations, or a single platform: say the result is thin.

## Report

Stage reached and files written → the demand map (needs, evidence, where asked) → the question bank
(angles, evidence levels) → the space (generating dimensions, count) → gap and presence results with
sample size, platforms and dates → lever hint and captured queries → signals coverage → the need ×
channel table → the owner's decision, or the question waiting for it → next step per lever: pages to
site-batch (assets, facts and templates, then a small first wave), off-site to site-offsite GEO mode,
product and docs to the product's own workflow → what this step dropped compared with the goal card.

## Premises

Written 2026-11-17 from the GEO zero-to-one method (`~/Projects/GEO/geo-zero-to-one.md`). Revised the
same day after the first live run (SFXMint family pages): the gap share alone said `go` while the site
was in 4 of 25 answers and the answers rested on lists and big libraries; the demand map, question
bank, presence fields, lever hint and competitor probes were added for that. The 0.33 threshold, 40
samples and the 25% presence line in the notes are starting values: recalibrate after the next run
and record what changed here. Revised 2026-11-18 after the SFXMint long-tail round: the ChatGPT-only
probes narrowed the space to licence guides, the agent/API channel had been dropped at the demand map
without the owner, and the task space was skipped, so the largest need (finding a specific sound) had
no plan. The goal card, per-channel decision, drop rule and mandatory task space were added for that.
