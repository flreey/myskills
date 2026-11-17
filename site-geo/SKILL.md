---
name: site-geo
description: 已上线站点的 GEO（两种模式）：检查模式——AI 爬虫（ChatGPT、Claude、Perplexity 等）能不能访问页面、llms.txt 是否与线上一致、ChatGPT 能否打开并引用页面、会不会为目标问题推荐这个站；持续优化模式——从真实来源（AI 爬虫抓取、AI 引荐落地页、站内/API/MCP 搜索落空、客服和社区原话、Bing AI Performance）找用户交给 AI 的任务，建限制条件矩阵和多轮对话，按问题类型选杠杆（站内、站外、文档、工具渠道），先测基线、做来源诊断，再用留出集、哨兵集和对照组做实验，看提及、首推、引用、准确率和 AI 引荐转化。site-kit 站和其他站都适用。Also for GEO 检查、AI 搜索可见度、ChatGPT 能不能访问、GPT 会不会推荐、llms.txt、AI 爬虫放行、AI 为什么推荐别人、GEO 持续优化、AI 引用占比、改哪个页。不用于：页面验收（site-check）、新想法的答案缺口验证（site-idea）、批量生成页面（site-batch）、找关键词（site-research）。
---

# site-geo: GEO for a live site (check and optimize)

Two kinds of evidence, kept apart. **Facts** come from `geo_check.py`: robots.txt rules per AI
crawler, what each AI user-agent gets back, and whether llms.txt matches the site. **Samples** come
from asking ChatGPT with fixed prompts: they vary per run, model and account, so they are recorded,
repeated and never reported as a measurement. Page SEO is site-check's job; run it first, because a
page that fails there will not do better in AI answers.

Engine (Python stdlib, read-only), `python3 <skill-dir>/scripts/geo_check.py`:

- `--site <origin> [--url <page>]... [--sitemap <url|file>] [--base <origin>] [--retired "phrase"]...`.
  `--url` picks the pages to probe (default: home); `--sitemap` compares llms.txt with the listed
  pages; `--base` reads a local build or preview while links keep the production host; `--retired`
  lists names the site no longer uses. `--format json` for the full record.

Optimize engine (Python stdlib), `python3 <skill-dir>/scripts/geo_optimize.py --root <project>` with
`init`, `check`, `sets`, `report`, `experiment`, `brief`; data in `<project>/geo/optimize/`, contract and loop in
[references/optimize.md](references/optimize.md).

## Modes

| Mode | When | Path |
| --- | --- | --- |
| **Check** | A site or page should be reachable, quotable and recommended by AI assistants; before and after a launch | G1–G4 below |
| **Optimize** | A live site wants more AI recommendations and citations over time: which tasks, why assistants pick others, what to change, did it work | G5 below, then the loop in [references/optimize.md](references/optimize.md) (O1–O8) |
| **Retrofit** | Existing pages should become GEO pages without losing search traffic | [references/retrofit.md](references/retrofit.md): single pages step by step; families of similar pages through site-batch adopt mode |

Optimize starts from tasks, not keywords; Google keyword data is context only. New sites with no
traffic start in site-idea instead.

## Iron rules

1. **Facts and samples stay apart.** Script output is a fact about the server; a ChatGPT answer is a
   sample. Never merge them into one verdict.
2. **ChatGPT answers are samples, not measurements.** Record the date, model, mode and full prompt;
   repeat in fresh chats; never report one answer as a fact about ranking or traffic.
3. **Using the user's ChatGPT account needs their go-ahead** in chat. Otherwise hand them the
   prompts and read back what they paste.
4. **Training is the owner's choice.** Blocking a training crawler (GPTBot, ClaudeBot,
   Google-Extended) is a decision, not a defect; blocking a search or user crawler is a fix unless
   the owner chose it.
5. **Reports and its own data only.** Check mode writes nothing; optimize mode writes only
   `geo/optimize/`. Copy, page and llms.txt changes follow the project's own workflow (site-kit rules on
   kit sites); never write under `seo/`.
6. **Results come from the holdout set and experiments.** Never report the optimize set's rise as
   the effect, never change holdout or sentinel clusters, and never swap the question set between a
   baseline and its review.
7. **No tricks.** Do not act on advice to stuff keywords, add hidden text, fake reviews, invent
   statistics or show crawlers different content from users.

## Workflow

1. Run site-check (or reuse its latest report) for the pages in question.
2. Run `geo_check.py` on the live site, or on a build with `--base`, with the pages to probe, the
   sitemap and the retired names.
3. If most visitors come from AI assistants, read the demand sources for G5 and pick target
   queries from them: low citation share first.
4. With the user's go-ahead, run probe A on the same pages, probes B and C for each target query
   (two or three of the site's main queries) and probe E once for the site, each three times in
   fresh chats, from [references/chatgpt-probes.md](references/chatgpt-probes.md). Run them in the
   user's browser as [site-idea's probe-runs.md](../site-idea/references/probe-runs.md) says.
5. Report.

## Checks

### G1. AI crawlers can reach the pages

- Search crawlers (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) decide whether pages can
  appear in that assistant's answers; user crawlers (`ChatGPT-User`, `Claude-User`,
  `Perplexity-User`) fetch when a person asks; training crawlers only feed models (rule 4).
- Probes with AI user-agents should return 200, no challenge page, about the same HTML as a browser.
- A probe only shows rules keyed on the user-agent string. Firewalls that verify crawlers by IP
  (Cloudflare bot settings and AI crawler controls) are checked in the dashboard: a MANUAL item
  for the user, with the zone named.

### G2. llms.txt matches the site

- Present, titled with the site's name, and describing what the site sells or does today.
- Every link returns 200 and is indexable; the important indexable pages are listed (compare
  `not_in_llms` with the site's main pages, not every legal page); no links to pages outside the
  sitemap unless they are meant to be found.
- No retired product names or old positioning (`--retired`).
- llms.txt is a proposal with no confirmed use by the large assistants' crawlers: keep it accurate,
  do not expect traffic from it.

### G3. ChatGPT can open the page (probe A)

- Pass when it quotes the real title and the first lines, matching the raw HTML in site-check.
- Fail when it cannot open the page, quotes an older version, or answers from search snippets.
  Compare with G1 to find which layer blocks it. A changed page may take time to show.

### G4. Would ChatGPT recommend the site (probes B and C)

- Unbranded probes first (the user's real task in the market's language, no site name), then the
  branded one. Count named, linked and first recommendation separately over the runs, and note which
  sites appear instead.
- Probe E checks what it says about the site (use, price, limits, license) against the live pages.
- Where the page allows it, capture the search queries behind probe B (probe D). They separate
  "searched and not chosen" from "never searched for it".
- Turn the advice into concrete page facts to change (a missing comparison, no price on the page, no
  author or contact, thin examples), each tied to a site-check check or to site-plan. Drop advice
  that is generic or breaks rule 7.

### G5. Where AI demand is and which pages lose citations

- Run this on existing sites whose visitors come mostly from AI assistants.
- Read the sources: search crawler and user crawler fetch logs, Bing Webmaster AI Performance, and site search misses.
- Classify each gap (not mentioned, mentioned without a link, linked without visits, visits without action), then sort the findings into pages to improve, new pages and missing content.
- Before a page changes, write down the baseline, the pages left unchanged, the review dates and the result that would show the idea was wrong. Sources, tests, hand-offs and follow-up are in [references/ai-demand.md](references/ai-demand.md).
- G5 is the entry to optimize mode: its sources feed O1 (tasks), and the gap classes feed O5. Run the
  full loop in [references/optimize.md](references/optimize.md) when the owner wants changes measured,
  not only found.

## Report

The facts first (G1 per crawler role, G2 findings, G5 sources with their windows), then the samples (G3 and G4 with date, model,
mode and prompt per run), then the fixes in priority order, the MANUAL items, and what was not
checked. Save it to a file only when the user asks, outside `seo/`.

## Premises

- Checked 2026-10-21 against OpenAI's bot documentation: `OAI-SearchBot` (ChatGPT search; robots.txt
  applies; changes take about 24 hours), `GPTBot` (training; robots.txt applies), `ChatGPT-User`
  (user-initiated fetches; robots.txt may not apply; not used for search inclusion), `OAI-AdsBot`
  (ad landing pages only). IP lists: `openai.com/searchbot.json`, `gptbot.json`, `chatgpt-user.json`.
- Claude (`ClaudeBot`, `Claude-User`, `Claude-SearchBot`), Perplexity (`PerplexityBot`,
  `Perplexity-User`), `Google-Extended` and `Applebot-Extended` roles and user-agent strings were
  written from memory on 2026-10-22 and not re-checked against the vendors' pages: confirm before
  reporting a block as a vendor-specific fact.
- Checked 2026-10-21 (news reports, not Cloudflare docs): from 2026-09-15 Cloudflare groups bots as
  Search, Agent and Training; new domains block Training and Agent crawlers by default on pages with
  ads, with Search allowed. Where OpenAI's bots fall was not confirmed, so check the zone's settings.
- Split out of site-check on 2026-10-22 so page SEO acceptance stays reproducible and AI samples,
  which need the user's account, run on their own. First run on tinywonderpost.com (local build):
  every AI crawler allowed; llms.txt still said "Story Kits" after the shop moved to holiday
  printables, and did not list the home page or /pricing.
