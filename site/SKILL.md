---
name: site
description: GEO 总入口（让 AI 助手推荐和引用我们的站）：不知道该用哪个 site-* skill、项目进行到哪一步、下一步做什么时用它。按一个循环走——0 目标卡和现状 → 1 需求和问法（site-idea）→ 2 机会：需求 × 渠道（AI 助手、搜索引擎、agent/API）谁在赢、我们在不在、能做多少页 → 3 先做一小批改动（页面 site-batch、站外 site-offsite、产品和文档）→ 4 复测和数据（site-geo、site-measure），再回到 1 或 2；共用 site-kit 建站、site-check 验收、site-adsense 广告、site-stripe 收款。它只写目标卡，其余只读项目文件，然后指向对应的 skill。Also for GEO 流程、下一步做什么、用哪个 site skill、目标卡、上线前检查。不用于：关键词 SEO（独立路线，直接用 site-research → site-plan）。
---

# site: GEO entry and loop

Goal: assistants (ChatGPT, Claude, Perplexity, Gemini, coding agents) recommend and cite the site for
the tasks its users bring them. This skill keeps a project on that goal: it writes the goal card,
finds where the project is in the loop, names the next skill and command, and loads it. It writes no
other project file.

Keyword SEO (search volume, SERP, keyword → page) is a separate route and does not start here: use
`site-research` (keywords) → `site-plan` (keyword pages) directly. GEO still reads search engines as a
channel (assistants search before they answer), through the evidence in step 2, not through keyword
research.

## The loop

| # | Question | Output | Skill |
| --- | --- | --- | --- |
| 0 | Where are we, and what result do we want? | Goal card `geo-goal.md` with the current state | here ([references/goal-card.md](references/goal-card.md)) |
| 1 | What are users trying to do, and how do they ask? | Demand map `needs.jsonl`, question bank | `site-idea` steps 0–1 |
| 2 | Where is the opportunity? | Need × channel table: who wins now, are we there, what only we have, how many pages it supports | `site-idea` steps 2–7 (task space, probes, other channels, decision) |
| 3 | Make a small batch of changes | Pages, off-site entries, or product and docs changes, whichever the table points to | `site-batch` (pages), `site-offsite` GEO mode (lists, communities, directories), the product's own workflow (API, MCP, tool listings); `site-kit` builds, `site-check` GEO mode accepts |
| 4 | Did it work? | Retest of the same questions, crawl, index, AI referrals, downloads; expand, change or stop | `site-batch` review, `site-geo` (check and optimize), `site-measure` |

Then back to step 1 (new needs) or 2 (same needs, new evidence). Steps 2 and 4 are where the method is
least settled; run them small and let results correct the method, rather than designing everything
before anything ships.

Where to enter:

| Start | Enter at |
| --- | --- |
| Only an idea, no site | 0, then `site-idea` with off-site evidence only |
| Live site, wants a new space of pages | 0 (current state matters), then `site-idea init --live` |
| Live site, assistants recommend others for tasks it already has pages for | 0, then `site-geo` optimize O1–O5 (baseline, source diagnosis); its levers feed step 3 |
| Live site whose AI-referred landings sit mostly on the home page or a few core pages | 0, then `site-geo` optimize on those pages first (the conditions assistants check: price and free tier, limits, upload, signup, watermark, devices, written on the page), alongside any new space |
| A wave or change is past its window | 4 |

## Rules for every step

These hold in every site-* GEO skill (site-idea, site-batch, site-geo, site-offsite and site-check in
GEO mode); the others point here instead of repeating them. Where an engine can check a rule, it does:
`decide` refuses pages without the need × channel table and a task space, `wave-plan` refuses
unapproved templates, `check` warns when the goal card is missing or project.json drifts from it.

1. **The goal card travels.** Every step, and every brief handed to another thread or agent, starts
   from `geo-goal.md` (project root) as written, not from the previous step's summary, and the card's
   **main bet** (the approach the owner wants tested) stays the default plan until the owner sets it
   aside. Every hand-off ends with one line: what this step dropped compared with the card (needs,
   audiences, channels, levers, any part of the main bet), or "nothing".
2. **One channel never decides for all, and evidence matches the question.** Evidence and decisions
   are per need × channel (assistant chat, search engines, agents/API/MCP). An assistant probe that
   shows no room says nothing about search or agent demand for the same need. Within a channel, keep
   two kinds apart: **picked** (does the assistant find and choose us: probe presence, its fetches of
   our pages, landings) and **after landing** (do people take something: take rate, downloads). Levers
   that change what assistants find, pages above all, are decided on picked evidence; after-landing
   evidence decides what the page or product must hold. Never infer "pages will not help" from a
   take rate.
3. **Dropping is the owner's call.** Dropping a need, an audience, a channel or a lever needs the
   owner's yes in chat, with what it costs (volume, evidence) stated; record it under "Not doing" in
   the card.
4. **Small first.** Step 3 starts with tens of pages or a few changes, with a control where possible.
   A probe is not a substitute for shipping and measuring.
4b. **Overlap means the same thing.** A running experiment blocks changes to its own URLs, their
   content and links added from them, nothing wider. New URLs for the same need do not overlap; keep
   links from the experiment's pages out of them and say so in the plan.
5. **Tools get one hour.** A tool or automation problem that is not solved in about an hour gets a
   simpler path or is skipped and reported; it never drives the plan.
6. **Say where we are.** Before each step, tell the owner which step this is, what it answers and how
   far the project is from the card's goal.
7. **Direction is asked on its own.** A choice that changes the main bet, the channels or the scale
   (no pages, a different main lever, a much smaller batch) is put to the owner as a separate
   question with what it gives up, never bundled into "as recommended". Numbers that drive such a
   choice are checked at the method, not only the total, before they are relayed.

## Find the step

Read only what exists under the project root. The goal card is one per site; GEO folders may be
several (`geo/`, `geo-longtail/`, … each with its own `project.json`, passed as `--geo-dir`): report the
step of each folder, one line each, then the next step for the one the owner is working on. A new need
space is a new folder (`init --geo-dir <dir> --needs-from <first folder>`), never new dimensions in an
existing one.

Before the stage rows, read the goal card's AI-landing line (step 0 writes it): when most AI-referred
landings go to the home page or a few core pages and those pages lose the tool-seeking probes, name
site-geo optimize for them as a step-3 item next to whatever the stage rows say; that is where most of
the traffic is.

Check the rows in order; the first that matches decides:

| Evidence | Means |
| --- | --- |
| no `geo-goal.md` at the project root | step 0 next, whatever else exists |
| `geo-goal.md` older than the folder's last decision, or its "current state" older than about 30 days | refresh step 0 before the next step |
| `decision` in `project.json` but no `gap/channels.md`, or `channels.md` has a channel the card keeps in scope measured nowhere (`not measured` down the whole column) | back to step 2: fill the table and let the owner review the old decision (`decide` again; earlier decisions stay in `decisions`) |
| `stage`: `idea`, `needs` | step 1 (site-idea) |
| `stage`: `space`, `gap`, or `dimensions.json` without a generating dimension | step 2 (site-idea); no pages before the task space exists |
| `stage`: `decided`, `blueprint`, `pages` | step 3: pages for the needs whose Lever in `gap/channels.md` includes `pages` (site-batch); `offsite` to site-offsite; `product` to the product's workflow |
| a released wave past its window (`waves.json`) | step 4 |
| `optimize/` in a GEO folder | site-geo optimize has run; its experiments feed step 4 |
| `.sitekit.json` | kit site: build, check and release go through `site-kit` |
| `umami.config.json` | Umami wired (site-measure) |

Report the step in one line, the next command, and anything blocking it. Then load the named skill
and follow it; its own rules and approvals apply.

## Shared skills

| Skill | GEO use |
| --- | --- |
| `site-kit` | Build, check, release and upgrade kit sites; GEO batch pages land on its directory sites |
| `site-check` | GEO mode: answer first, constraints written out, follow-ups visible, numbers match the facts; plus the mechanical sweep (status, canonical, server rendering, FAQ in HTML) |
| `site-offsite` | GEO mode: get into the sources assistants cite |
| `site-measure` | Umami: AI referrals, landing pages, downloads and other conversions |
| `site-adsense` | AdSense pre-check |
| `site-stripe` | Stripe from sandbox to live |

Page acceptance: `site-check` GEO mode on the changed pages; kit sites also pass `npm run check`
(rules in site-kit `references/seo-gates.md`). AI crawler access and llms.txt: `site-geo` check mode.

## Ownership

Each fact has one owner: goal card → this skill (`geo-goal.md`); demand map, question bank, task
space, need × channel table and decision → site-idea (`project.json`, `needs.jsonl`, `questions.jsonl`,
`dimensions.json`, `gap/` in each GEO folder); templates, page data and waves → site-batch
(`geo/`); live-site findings and experiments → site-geo (`geo/optimize/`); off-site ledger →
site-offsite; what the built pages say → the site build; traffic → site-measure. site-check owns no
data: it reports.

## Premises

Revised 2026-11-18 (later) after the ToHD round: the stage rows sent a live site to a new situation
space while about 92% of its ChatGPT landings went to the home page and its existing pages were not
found for tool-seeking questions. The AI-landing line, the capability sheet in the goal card and the
optimize-first row were added; site-idea gained the capability × condition space shape and `queries`.

Rewritten 2026-11-18 after the SFXMint long-tail round drifted: each step handed on the previous
step's conclusion instead of the goal, one channel's probes (ChatGPT chat) narrowed the whole space,
the agent/API channel was dropped without the owner seeing it, the task space was skipped, and tool
problems took about ten hours. The GEO-or-SEO choice was removed from this entry for the same reason:
assistants search before they answer, so search ranking is a GEO channel, not a separate mode. The
loop and these rules are a hypothesis; correct them after the next full round.
