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
with `init`, `needs`, `bank`, `space`, `sample`, `probes`, `report`, `queries`, `decide`, `extend`, `check`. State is
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

0. **The site skill's rules apply** (goal card first and passed on, one channel never decides for
   all, dropping is the owner's call, small first, tools get one hour). Read `geo-goal.md` at the
   project root before step 0; without it, run the `site` skill's step 0 first. End every report with
   what this step dropped compared with the card, or "nothing".
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
6. **The decision is the owner's, per need × channel.** `gap/channels.md` has one row per need and one
   Lever per row (pages, offsite, product, not-now), picked with the owner; probes fill only the
   assistant-chat column, and the report's `hint` reads that column only. `decide --by user` runs
   after the owner chose in chat and refuses while a Lever is still `?`. `go` or `narrow` records the
   part of the space that gets pages and needs at least one need with `pages`; a decision that makes no
   pages is `stop`, with the other levers in the table. When the site is in under 25% of the answers,
   `go` or `narrow` needs the owner's reason in `--note` (pages rest on being picked, not on the gap).
   Decisions are kept in `decisions`, never overwritten.
6b. **No pages without a task space.** `decide go|narrow` refuses unless `dimensions.json` has a
   generating dimension, `space` ran on the current file, and the generating dimensions state their
   assets (`{needs, have, source}`): the owner sees how many pages are possible and what each needs.
   The question-bank route needs it too. `space` itself does not move the stage while no need is
   validated (needs before dimensions).
7. **Writes stay in the geo folder.** This skill touches no site, registry or other project file.

## Two shapes of page space

Assistants behave differently by conversation type, so a space takes one of two shapes (`space` prints
it):

- **Capability × condition** (`kind: capability` on a generating dimension): what the product lets
  people get or do (an operation, a file type, a feature, a service) × the conditions that change who
  qualifies (free tier, no upload, no install, on a phone, a size or length, a licence, an
  integration). This serves **choosing** conversations: the user wants something picked, the assistant
  searches with "capability + conditions", then checks the candidates' own pages for those conditions
  and picks the one that states them plainly. It is the default for a live product whose AI referrals
  come from people looking for a tool, file or service. Values need proof (`assets`: a test output, the
  file, a measured result); a condition every value meets (free, no upload) is a fact on every page,
  not a dimension; only conditions that change the shortlist and that people search become dimensions.
  How many pages it holds depends on how wide the capability dimension is (hundreds of format pairs or
  sound kinds; tens of video operations).
- **Situation** (no capability dimension): the user's circumstances (where the file came from, what it
  is for). This serves **how-to** conversations, which assistants mostly answer from memory without
  searching; pages here pay only when the answer needs data only we have (our own tests, files,
  measurements).

Demand still comes first (rule 1): the demand map decides which capabilities and conditions matter;
the shape decides how the pages are cut. A site can hold both, one GEO folder each.

## Workflow

0. **Start and map demand.** Read `geo-goal.md` (rule 0). `init --name <Name> --idea "<who, situation, task in one sentence>"`
   (`--live --origin <url>` for a live site; `--needs-from <folder>` for a second need space on the
   same site, which then reads that folder's `needs.jsonl` instead of copying it). Copy `audience`,
   `market`, `platforms` and `north_star` into `project.json` from the goal card; the card wins. Then
   collect first-party and off-site evidence, group it into needs and write `geo/needs.jsonl`
   ([references/demand-map.md](references/demand-map.md)); `needs` checks it and writes
   `geo/needs.md`. Show the owner the map (needs, counts, where each is asked) and agree which needs
   and audiences to serve.
1. **Question bank.** Expand each chosen need into questions from several angles, with evidence on
   each ([references/question-bank.md](references/question-bank.md), prompt included); run `bank` and
   fix what it flags. In a crowded market, add questions reverse-engineered from competitors
   ([references/competitor-probes.md](references/competitor-probes.md)).
2. **Task space.** Pick the shape first (above): on a live product whose AI landings are people
   looking for a tool, file or service, start with capability × condition. Write `geo/dimensions.json`
   (shape in references/state.md) from the needs: capability, entity, task and constraint dimensions
   whose values change the answer, each value with a source, excludes
   for combinations that make no sense or that the product will not serve. Run `space`; fix every
   ERROR, read every WARN. Show the generating dimensions, the described-only ones and the count in a
   short table, and adjust with the owner before sampling: a wrong dimension multiplies into every
   later page. Give each generating dimension `assets: {needs, have, source}`: what one page needs,
   how many values or combinations have it today or could have it (generated, collected), and where
   that count comes from; `space` prints it and records it in `project.json.space`. That, not the
   number of questions, sets how many pages are possible. One folder holds one need space: a dimension
   for another need that would multiply with these is a new folder (`--needs-from`). Skipping this step
   is allowed only for a decision that makes no pages (rule 6b).
3. **Sample.** One of: `sample --n 40` (combinations, at least the widest dimension's value count),
   `sample --from-questions --n 40` (bank questions spread over needs and angles, real wording first;
   `--weight`, `--origin`, `--ids`, `--append` in [references/question-bank.md](references/question-bank.md)),
   or `sample --pool <file> --n 40` (existing pages as candidates, spread over strata such as traffic
   tiers). Combinations come marked with an `angle`: `recommend` (the opening asks for a tool, site or
   app) or `problem`; about two thirds `recommend` in a capability space, a third otherwise. Fill `persona`, `opening`, `follow_ups` and `signals` where empty, following
   [references/conversations.md](references/conversations.md). Then `probes` renders the sheet.
4. **Probe.** Per rule 3: give the user `geo/gap/probes.md` (one new chat per conversation, each
   target platform, paste the whole answer into the named file), or run it the way they approved.
   Browser runs follow [references/probe-runs.md](references/probe-runs.md): a page script in a
   logged-in browser tab first, in ego-browser by default (it also captures the assistant's search
   queries); a Grok Bot via `gbot` only as a fallback. The one-hour tool rule (site skill rule 5) applies to both. Save every answer under `geo/gap/raw/` and add a row to
   `geo/gap/runs.jsonl` with `gap: null`.
5. **Judge.** Label every run with [references/gap-rubric.md](references/gap-rubric.md): `gap`,
   `gap_note`, `own`, `cited`, `recommended`, `search_queries`, and `outcome` for competitor probes.
   Then `check`, then `report`; on its first run `report` also writes the skeleton of
   `gap/channels.md` (`channels` writes it on demand, e.g. for `--without-probes`).
6. **Other channels.** Probes cover assistant chat. For the same needs, collect what is cheap and
   real: search engines — run `queries`: it splits the captured queries into **find searches**
   (generic: the assistant looks for candidates), grouped into clusters, and **named checks** (a site
   or product it already has in mind: its shortlist). Fill `rank` per find cluster (Bing first, as
   ChatGPT search leans on it; Google SERP or Search Console when Bing is not available, said so):
   whether our pages rank there decides whether they can be picked. Note whether the winners are pages made for that search
   (`winners_kind: dedicated`) or broad tool and home pages (`general`): site-batch makes a combination
   a page of its own only for the first. When most queries are named checks
   and we are not on the shortlist, the assistant answers from memory: that cell's lever is off-site
   (lists, communities, reviews), not pages; agents, API and MCP (first-party search logs, zero-result queries, tool directory and
   registry presence). Write what was looked at and what was not; "not measured" is a valid cell.
7. **Decide.** Complete `gap/channels.md`: drop the columns the goal card keeps out of scope, fill each
   cell with evidence or `not measured`, in two parts: `picked:` (whether the assistant finds and
   chooses us: probe presence, its fetches, landings, who wins) and `after landing:` (take rate,
   downloads), and propose a Lever per need. Page levers rest on the picked part (site rule 2); a
   proposal that leaves the goal card's main bet without work is asked on its own (site rule 7). Show it with `gap/report.md`: the share of high-opportunity combinations or
   questions, where gaps concentrate (by value, need, angle, stratum), whether the site is in the
   answers, the sources behind answers without it and the lever hint, the captured queries, and the
   notes. Offer `go` (whole space), `narrow` (the subspace of strong values), `stop` (or change the idea
   and return to step 0). Record their answer with `decide --verdict <v> --by user [--subspace '<json>']
   [--note "<why>"]`. When the owner does not want probes as a precondition, `decide --without-probes`
   records a decision on validated first-party needs instead; say that the gap and presence are then
   unknown. A lever for one need or channel lives in `channels.md`; `stop` means no pages from this
   space, not that the needs are dropped.

## Long tail: more values later

A new need or task type is a new space and a new GEO folder: `init --geo-dir <dir> --needs-from
<first folder>`, then steps 2–7 there. More values of a dimension already decided stay in the folder.

When pages exist and the owner wants more values of a dimension the gap check already covered (more
events, formats, places), add the values to `geo/dimensions.json`, then, after the owner agrees in
chat, `extend --dimension <id> --values a,b --by user`. No new probing is needed: the template's
validation carries over, and site-batch's gate and wave funnel judge the new pages. New values should
come from the demand map (searches, misses, quotes), not from a word list. A new dimension is a new
space (above): sample and probe it (20–30 combinations are enough for one dimension) before `decide`.

## Reading the report

- The report's first line says which platforms the hint comes from. `hint` and `lever_hint` read
  assistant-chat probes only: use them for that column of `channels.md`, never as the decision for a
  need. A need with fewer than 8 runs is marked `thin`; under 25 probed or a single platform, the first
  note says the whole sample is thin.
- `hint` is `go` when the high share reaches the threshold (default 0.33, `report --threshold`),
  `narrow` when only some values with two or more probed combinations reach it, `stop` otherwise.
  It is a starting point for the conversation, not the verdict.
- Probes can undercount: SFXMint was in 0 of 71 probe answers while ChatGPT sent it about 31,000
  visits in 28 days, most landing on single-sound and family pages. Before reading low presence as
  absence, compare with AI-referred landings by page; they are the stronger picked evidence.
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
Revised again on 2026-11-18 after the ToHD round: all 70 combination openings described a problem and
none asked for a tool, so ChatGPT answered from memory and the site was in 0 of 70 answers, while 15
tool-seeking openings named it 7 times; `go` was still recorded with no remark. Combination samples now
carry an angle (a third `recommend`), `check` warns when none asks for a tool, and `decide go|narrow`
under 25% presence needs the owner's reason. The same day the two space shapes were written down:
ToHD's 129 captured queries were 6 find searches and 123 checks of named products (Topaz 20), and its
ChatGPT landings went to the home page, while SFXMint's main line (`geo-find`: sound × variant, with
format and licence written on every page) already had that shape and its landings went to matching
single-sound pages. `kind: capability`, the space shape and `queries` were added for that; the
capability default (two thirds tool-seeking openings) is a starting value.
