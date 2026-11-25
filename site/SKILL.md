---
name: site
description: GEO 总入口（让 AI 助手推荐和引用我们的站）：先选模式再给下一步。新产品模式四步——1 选战场（ChatGPT 里问一批“有没有能 X 的网站”并追问“你选哪个”，看谁赢、凭什么条件）→ 2 定产品（我们在哪个条件上赢过赢家，写能力表）→ 3 上线（首页、价格页、能力页第一屏写同一组条件，site-kit 建站、site-check 核验）→ 4 复测（同一批问题、看输在哪一步）。扩量模式是已上线站点的完整循环：目标卡 → 需求和问法（site-idea）→ 需求 × 渠道 → 一小批改动（site-batch、site-offsite、产品文档）→ 复测（site-geo、site-measure）。它只写目标卡，其余只读项目文件，然后指向对应的 skill。Also for GEO 流程、新产品怎么做 GEO、下一步做什么、用哪个 site skill、目标卡、上线前检查。不用于：关键词 SEO（独立路线，直接用 site-research → site-plan）。
---

# site: GEO entry

Goal: assistants (ChatGPT, Claude, Perplexity, Gemini, coding agents) recommend the product for the
tasks people bring them. This skill picks the mode, writes the goal card `geo-goal.md` at the project
root, finds the current step, and names the next skill and command. It writes no other project file.

Keyword SEO (search volume, SERP, keyword → page) is a separate route: `site-research` → `site-plan`.

## How assistants pick (the premise of both modes)

When someone asks for a tool, the assistant searches with "capability + conditions", **opens the
candidates' own pages** (home, pricing, FAQ) to check the conditions (free? limits? signup? upload?
works on a phone?), and picks the one whose page states the best match most plainly. On ToHD
(2026-11-18) 8 of 12 losses in "free website" questions came after ChatGPT had opened or named ToHD,
and two first picks flipped to "genuinely free, unlimited" competitors once it read ToHD's pricing
page. So GEO is first a product and pricing question, then a page question.

## Pick the mode

| The project | Mode |
| --- | --- |
| No site yet, a new product, or a new product on an existing domain | **New product** (four steps) |
| A live site with AI referrals, many pages, or a page space to grow | **Grow** (the loop) |

Ask the owner only if it is unclear. Write the mode on the goal card's first line.

## New product: four steps

Each step makes one decision, writes one thing, and passes one test before the next.

| # | Decision | Do | Writes | Passes when |
| --- | --- | --- | --- | --- |
| 1 | Which tool-picking need to compete in | 10–20 questions of the form "is there a free site that can X?", each ending "which one would you pick for me, and is it really Y?"; 3 runs each in ChatGPT | `<geo-dir>/gap/` runs and report; card: Battlefield | The assistant searches and names tools (not just steps), and the winners' reasons cluster on a few conditions |
| 2 | Which condition we beat the winner on | Capability × conditions sheet, every row tested | card: Capabilities and Edge | One condition the assistant cares about, which we beat and can prove in one sentence; else back to 1 or stop |
| 3 | Where those conditions are written | One main page per capability; home and pricing state the same conditions on the first screen, same numbers; pricing kept simple | the site | `site-check` with `--capabilities` on home, pricing and each capability page shows the conditions on the first screen, matching the card |
| 4 | Where we lost, and what to change | Same questions after indexing (2–4 weeks), `reads`, report; AI referrals and core actions | card: Retest row | Read the loss below; picked with referrals that convert means the bet works |

Commands:

1. `geo_idea.py --root . init --name <product> --idea "<one line>"`, write the questions to a text
   file (`question || hardest condition` per line), `sample --pilot <file>`, `probes`, then run them
   as site-idea `references/probe-runs.md` says (browser script, one pass per run number:
   `probe_run_to_raw.py --run 1`, `2`, `3`; 20 questions × 3 runs is about 60 conversations, 1–1.5
   hours). Judge each run with site-idea `references/gap-rubric.md`: `gap`, `recommended`, `cited`
   (the report counts only runs with a `gap`); leave `own` null while the product does not exist.
   `reads` (no domain yet: it fills only `read`, the pages the assistant opened), then `report`. From
   the answers, fill Battlefield: per question group, the winner and the conditions it gave as
   reasons. Take the wording of the questions from real posts where they exist (Reddit, forums,
   reviews: "is there a free site that…"); questions the model wrote are a guess at the market.
2. Capabilities from real tests (the product's own bench, not claims). Edge is one sentence.
3. Build with `site-kit` (or the site's own stack). Check with `site-check`:
   `page_check.py --url <page> --capabilities geo-goal.md` for home, pricing and each capability page;
   AI crawler access with `site-geo` check mode.
4. Rerun the same samples (`probe_run_to_raw.py --run 4`, `5`, `6`) into their own run set
   `gap/runs-retest-<date>.jsonl`, judged with `own` and `own_opening` now; `reads --own <domain>`,
   `report`: the retest appears apart from the pre-launch pilot, with where it was lost and the runs
   dropped after the pick turn. AI referrals and conversions from `site-measure`. Add a Retest row.

Where the loss sends you (step 4, and step 4 of grow mode):

| Lost at | Means | Next |
| --- | --- | --- |
| Never opened a page of ours | retrieval | indexing, rank under the queries it ran (`queries`), the lists in `read` (`site-offsite` GEO mode) |
| Opened our pages or named us, picked another; or dropped after the pick turn | selection | the pages it opened: conditions on the first screen, same as the card (`site-check --capabilities`); if the product itself loses on the condition, that is a product decision for the owner |
| Answered without searching | consensus | off-site, long term; pages will not change it soon |
| Picked, few referrals or no core action | landing | the landing page's first screen and next step (`site-measure`) |

Not in this mode: demand maps, question banks, dimensions, batch pages, holdout sets. Switch to grow
mode when AI referrals are steady and a dimension (device, source, format) shows dedicated pages
winning its searches; that is when batch pages pay.

## Grow: the loop

| # | Question | Output | Skill |
| --- | --- | --- | --- |
| 0 | Where are we, and what result do we want? | Goal card (full template) with the current state | here ([references/goal-card.md](references/goal-card.md)) |
| 1 | What are users trying to do, and how do they ask? | Demand map `needs.jsonl`, question bank | `site-idea` steps 0–1 |
| 2 | Where is the opportunity? | Need × channel table: who wins, are we there, what only we have, how many pages | `site-idea` steps 2–7 |
| 3 | Make a small batch of changes | Pages, off-site entries, or product and docs changes | `site-batch`, `site-offsite` GEO mode, the product's workflow; `site-kit` builds, `site-check` accepts |
| 4 | Did it work, and where did we lose? | Retest, crawl, index, AI referrals; the loss table above | `site-batch` review, `site-geo` (check and optimize), `site-measure` |

Then back to 1 (new needs), 2 (same needs, new evidence) or, for a selection loss, 0 (the Capabilities
row and its public pages). Where to enter:

| Start | Enter at |
| --- | --- |
| Live site, wants more AI visits and does not know what is missing (only the URL, or little data) | `site-geo` scan (gap-scan.md): which needs it loses, at which gate, and which kind of fix; its gaps feed the rows below |
| Live site, wants a new space of pages | 0, then `site-idea init --live` |
| Assistants recommend others for tasks it already has pages for | 0, then `site-geo` optimize O1–O5 |
| AI-referred landings sit mostly on the home page or a few core pages | 0, then `site-geo` optimize on those pages first (conditions on the page), alongside any new space |
| A wave or change is past its window | 4 |

## Rules for every step

These hold in every site-* GEO skill; the others point here. Where an engine can check a rule, it does.

1. **The goal card travels.** Every step and every brief to another thread or agent starts from
   `geo-goal.md` as written, and its main bet stays the plan until the owner sets it aside. Every
   hand-off ends with what this step dropped compared with the card, or "nothing".
2. **Picked before after-landing.** Whether the assistant finds and chooses us (probe presence, the
   pages it opened, landings) decides levers that change what it finds; take rates decide what the
   page or product must hold. Grow mode: evidence and decisions are per need × channel (assistant
   chat, search engines, agents/API/MCP); one channel never decides for all.
3. **Dropping is the owner's call.** A need, audience, channel or lever is dropped only with the
   owner's yes, its cost stated, recorded under "Not doing".
4. **Small first.** A few pages or changes, a control where possible. A probe is not shipping.
5. **Experiments block only their own URLs**, their content and links added from them. New URLs for
   the same need do not overlap; keep links from the experiment's pages out of them.
6. **Tools get one hour.** Past that, a simpler path or skip and report.
7. **Say where we are.** Before each step: mode, step, what it answers, how far from the goal.
8. **Direction is asked on its own.** Changing the main bet, the channels or the scale is a separate
   question with what it gives up; numbers behind it are checked at the method first.

## Before building a page: three questions

Every new page, single or long-tail, passes these before any work starts. One "no" means no new page.

1. **Real demand.** At least one piece of evidence: a tracked need (MissedByAI, `gap/`), GSC queries,
   search volume, or people's own words. "Someone might search this" is not evidence.
2. **No existing page can answer it.** If a paragraph or an FAQ entry on a page we have covers it,
   change that page instead.
3. **Something only this page has.** A real output sample, screenshot, comparison table or a product
   behaviour specific to the task. A new introduction around the same tool is not enough.

When the page is built, `site-check` pre-launch mode is the last step before release.

## Find the step

Read only what exists under the project root.

| Evidence | Step |
| --- | --- |
| no `geo-goal.md` | pick the mode, write the card |
| new product: no samples in the GEO folder | 1: write the pilot questions |
| new product: samples, fewer than 3 runs each, or runs without `own` | 1: probe and judge |
| new product: Battlefield empty | 1: fill it from the answers |
| new product: no Edge, or Capabilities without proof | 2 |
| new product: no site, or home / pricing / capability pages not checked against the card | 3 |
| new product: live and indexed, no Retest row in the last ~30 days | 4 |
| grow: card older than the last decision or its current state older than ~30 days | refresh 0 |
| grow: the card's AI-landing line says most AI-referred landings hit the home page or a few core pages, and those pages lose the tool-seeking probes | `site-geo` optimize on those pages as a step-3 item, next to whatever the rows below say |
| grow: `decision` but no `gap/channels.md`, or a kept channel measured nowhere | 2 |
| grow: `stage` `idea`, `needs` | 1 |
| grow: `stage` `space`, `gap`, or no generating dimension | 2 |
| grow: `stage` `decided`, `blueprint`, `pages` | 3 (by the Lever column) |
| grow: a released wave past its window, or `optimize/` experiments due | 4 |

Several GEO folders (`geo/`, `geo-longtail/`, …, each with its own `project.json`, passed as
`--geo-dir`): one line each, then the next step for the one in work. A new need space is a new folder
(`init --geo-dir <dir> --needs-from <first folder>`), never new dimensions in an existing one.
Kit sites (`.sitekit.json`) build and release through `site-kit`; `umami.config.json` means
site-measure is wired. Report the step in one line, the next command and anything blocking it, then
load the named skill.

## Shared skills

| Skill | GEO use |
| --- | --- |
| `site-kit` | Build, check, release kit sites; batch pages land on its directory sites |
| `site-check` | Pre-launch mode: the 7-item close-out for every new page. GEO mode: conditions on the first screen and matching the card (`--capabilities`), answer first, follow-ups visible, facts match; plus the mechanical sweep |
| `site-geo` | Gap scan of a live site from its URL (scan mode); AI crawler access and llms.txt (check mode); continuous optimisation of a live site (optimize mode) |
| `site-offsite` | GEO mode: get into the lists and sources assistants read and cite |
| `site-measure` | Umami: AI referrals, landing pages, core actions |
| `site-stripe`, `site-adsense` | Payments; AdSense pre-check |

## Ownership

Goal card → this skill. Probes, demand map, question bank, task space, need × channel table and
decision → site-idea (each GEO folder). Templates, page data, waves → site-batch. Live-site
experiments → site-geo (`optimize/`). Off-site ledger → site-offsite. Traffic → site-measure.
site-check owns no data.

## Premises

Revised 2026-11-19: split into two modes. The single loop (demand map → dimensions → batch pages)
was built for growing live sites and read as noise for a new product, where the result turns on one
thing: whether the assistant, after opening our pages, finds a condition it cares about stated better
than the winner's. Step 4 now routes by where the site was lost (`reads`).

2026-11-18: AI-landing line, capability sheet and optimize-first row added after ~92% of ToHD's
ChatGPT landings were on the home page; the loop and rules rewritten after the SFXMint long-tail
round handed on conclusions instead of the goal. These are hypotheses; correct them after the next
full round.
