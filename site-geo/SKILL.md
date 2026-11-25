---
name: site-geo
description: 已上线站点的 GEO（三种模式）：缺口扫描模式——只给网址，用公开来源（竞品页面结构、联想词、ChatGPT 回答）建需求池，按站型校准问法，经 Glasser 批量问 ChatGPT 网页版，判断每个需求卡在哪一关（不搜、没检索到、检索到没提、已赢），分五类给改法（查收录、改成用户说法、写清能力、补内容、补功能），按搜索量排序；检查模式——AI 爬虫（ChatGPT、Claude、Perplexity 等）能不能访问页面、llms.txt 是否与线上一致、ChatGPT 能否打开并引用页面、会不会为目标问题推荐这个站；持续优化模式——从真实来源（AI 爬虫抓取、AI 引荐落地页、站内/API/MCP 搜索落空、客服和社区原话、Bing AI Performance）找用户交给 AI 的任务，建限制条件矩阵和多轮对话，按问题类型选杠杆（站内、站外、文档、工具渠道），先测基线、做来源诊断，再用留出集、哨兵集和对照组做实验，看提及、首推、引用、准确率和 AI 引荐转化。site-kit 站和其他站都适用。另有站外模式：进入 AI 回答实际引用的榜单、目录、社区和工具注册表（要投稿的来源进 bl 外链池）。Also for 让 AI 引用我们、进入 AI 引用的榜单、MCP 目录、插件商店上架、GEO 检查、AI 搜索可见度、ChatGPT 能不能访问、GPT 会不会推荐、llms.txt、AI 爬虫放行、AI 为什么推荐别人、GEO 持续优化、AI 引用占比、改哪个页、缺口扫描、AI 流量缺在哪、该补哪些长尾页或功能、只有网址怎么诊断。不用于：页面验收（site-check）、新想法的答案缺口验证（site-idea）、批量生成页面（site-batch）、找关键词（site-research）。
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
`init`, `check`, `sets`, `reads`, `report`, `experiment`, `brief`; data in `<project>/geo/optimize/`, contract and loop in
[references/optimize.md](references/optimize.md).

## Modes

| Mode | When | Path |
| --- | --- | --- |
| **Scan** | A live site wants more AI visits and the question is what to change: which needs it loses, at which gate, and which kind of fix (index, retitle, first screen, content, capability). Works from the URL alone | [references/gap-scan.md](references/gap-scan.md), engine `scripts/gap_scan.py`; Glasser calls are paid, name the price first |
| **Check** | A site or page should be reachable, quotable and recommended by AI assistants; before and after a launch | G1–G4 below |
| **Optimize** | A live site wants more AI recommendations and citations over time: which tasks, why assistants pick others, what to change, did it work | G5 below, then the loop in [references/optimize.md](references/optimize.md) (O1–O8) |
| **Retrofit** | Existing pages should become GEO pages without losing search traffic | [references/retrofit.md](references/retrofit.md): single pages step by step; families of similar pages through site-batch adopt mode, only after O4–O5 show the pages are the bottleneck |
| **Off-site** | Assistants recommend from lists, directories, communities and docs where the product is absent: get into the sources they actually cite | [references/offsite-sources.md](references/offsite-sources.md), engine `scripts/cited_sources.py`; submissions and their records go through the bl pool (`bl guide`), not a separate ledger |

Read the project's goal card (`geo-goal.md` at the project root, written by the `site` skill) first
when it exists; when it does not, a check needs none, but optimize starts with the `site` skill's step
0. Optimize follows the site skill's rules (per-channel decisions, dropping is the owner's call). Optimize starts from tasks, not keywords; Google keyword data is context only. New sites with no
traffic start in site-idea instead, and so does a new space of pages on a live site (`init --live`).
When a site-idea demand map exists (`geo/needs.jsonl`), O1 starts from it rather than collecting the
same sources again.

## Iron rules

1. **Facts and samples stay apart.** Script output is a fact about the server; a ChatGPT answer is a
   sample. Never merge them into one verdict.
2. **ChatGPT answers are samples, not measurements.** Record the date, model, mode and full prompt;
   repeat in fresh chats; never report one answer as a fact about ranking or traffic.
3. **Using the user's ChatGPT account needs their go-ahead** in chat. Otherwise hand them the
   prompts and read back what they paste. Batch probes go through Glasser's ChatGPT LLM Scraper with
   `force_web_search=false` (gap-scan.md, “Checks against reality”); the account is for a few spot
   checks and pick turns: automated runs got it logged out.
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
   statistics or show crawlers different content from users. A "best X tools" or "alternatives" page
   that ranks our product says we publish it and shows how the ranking was tested.

## Workflow

1. Run site-check (or reuse its latest report) for the pages in question.
2. Run `geo_check.py` on the live site, or on a build with `--base`, with the pages to probe, the
   sitemap and the retired names.
3. If most visitors come from AI assistants, read the demand sources for G5 and pick target
   queries from them: low citation share first.
4. With the user's go-ahead, run probe A on the same pages, probes B and C for each target query
   (two or three of the site's main queries), probe A2 on pages live for 2–4 weeks, and probes E and F once for the site, each three times in
   fresh chats, from [references/chatgpt-probes.md](references/chatgpt-probes.md). Run them in the
   user's browser as [site-idea's probe-runs.md](../site-idea/references/probe-runs.md) says.
5. Report.

## Checks

### G1. AI crawlers can reach the pages

- Search crawlers (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) decide whether pages can
  appear in that assistant's answers; user crawlers (`ChatGPT-User`, `Claude-User`,
  `Perplexity-User`) fetch when a person asks; training crawlers only feed models (rule 4).
- Probes with AI user-agents should return 200, no challenge page, about the same HTML as a browser.
- Read each probe's `answer`. Cloudflare applies its AI crawler and agent policies to verified bots
  and to unverified requests that claim to be them, so a spoofed user agent meets the same policy:
  `policy` (a plain-text 403 "Your request was blocked.", or 402) is that policy and a fix for search
  and user crawlers. `blocked` or `challenge` (an HTML block or challenge page) may be bot protection
  catching our fake crawler only: settle it with probe A, where the real `ChatGPT-User` fetches.
  Probe the pricing page too (`--url /pricing`): with ads on it (`ads on page`) and the home page
  passing, a `policy` there means "Block on pages with ads". The robots.txt section also shows
  Cloudflare's managed block and its `Content-Signal` when the zone syncs its policies there.
- What stays MANUAL: the exact zone settings (Security → Settings → AI Crawler and Agent access
  policies, Bot Fight Mode), or a read-only API token with Bot Management Read
  (`GET /zones/{id}/bot_management`: `ai_search`, `ai_user`, `ai_training`, `ai_agents`,
  `fight_mode`). MissedByAI's scan runs the same outside check (`src/site/scan/access.ts`).
- **ChatGPT's Cloud browser** (it replaced ChatGPT agent) visits and uses a site for a person. It
  signs requests (Web Bot Auth, `Signature-Agent: "https://chatgpt.com"`) instead of using a fixed
  user agent, so a UA probe cannot test it. MANUAL: in Cloudflare, Security → Settings → AI Crawler
  and Agent access policies → Personal Agents → `dots, OpenAI` set to Allow (or a WAF skip rule on
  detection ID `129220581`); proxies in front of the origin keep the `Signature`, `Signature-Input`
  and `Signature-Agent` headers. Vercel allows it with no setting.
- **The free path works for an agent.** With the user's go-ahead (rule 3), ask ChatGPT's Cloud browser
  to do the site's main task end to end (upload, process, download). It cannot sign in, pay or pass a
  captcha, so a free path behind any of these fails. Check the output yourself: a run that reports
  success after a stalled upload is a fail.
- **Markdown for agents** (only when the zone serves it: the probe output says `Markdown served`): the Markdown of the home and pricing pages keeps every plan's price, free allowance
  and limits; a missing page does not return 200; the origin sets its own `Content-Signal` header,
  since Cloudflare otherwise adds `ai-train=yes` whatever robots.txt says about training (rule 4).
  Cloudflare offers it on Pro plans and up; no evidence yet that it raises recommendations.

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
- After launch (2–4 weeks), probe A2 asks for a sentence only that page has, without the URL. A
  passing and A2 failing means the page can be fetched but is not indexed: fix indexing, not copy.

### G4. Would ChatGPT recommend the site (probes B and C)

- Unbranded probes first (the user's real task in the market's language, no site name), then the
  branded one. Count named, linked and first recommendation separately over the runs, and note which
  sites appear instead.
- Probe E checks what it says about the site (use, price, limits, license) against the live pages.
- Probe F asks for the official site by brand name: a clone domain, a name collision or a wrong
  domain is a fix before anything else (one consistent domain everywhere, Organization `sameAs`,
  report clones to the owner).
- Where the page allows it, capture the search queries behind probe B (probe D). They separate
  "searched and not chosen" from "never searched for it".
- Turn the advice into concrete page facts to change (a missing comparison, no price on the page, no
  author or contact, thin examples), each tied to a site-check check or to site-plan. Drop advice
  that is generic or breaks rule 7.

### G5. Where AI demand is and which pages lose citations

- Run this on existing sites whose visitors come mostly from AI assistants.
- Read the sources: search crawler and user crawler fetch logs, Bing Webmaster AI Performance, and site search misses.
- In the same logs, list paths the assistants invent (404s to user crawlers or AI-referred visits) and
  redirect the repeated ones to the page that does the job ([references/ai-demand.md](references/ai-demand.md)).
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
- Checked 2026-11-22 against OpenAI's help center: ChatGPT agent is no longer available (Operator
  folded into it earlier); its successor, ChatGPT Work's Cloud browser, signs requests per RFC 9421,
  cannot sign in or pay at launch, and is allowlisted as above (help.openai.com/en/articles/11845367,
  developers.openai.com/commerce/agent-access). Cloudflare's Markdown for Agents doc (dateModified
  2026-11-09): Pro and up, default `Content-Signal: ai-train=yes, search=yes, ai-input=yes` unless the
  origin sets one. Cloudflare's press releases and current docs disagree on whether new zones block
  agents on ad pages by default: read the zone, not either source.
- Cloud browser, Markdown, probe F, the reputation turn and the self-ranking rule came from the second
  gbot round (2026-11-22, 90 more X posts and 18 official pages). Most X figures there are second-hand
  (for example "two answers on the same day share about 40% of their sources"); only the official
  lines above were checked.
- Probe A2 and the invented-path check were added 2026-11-22 from a summary of 116 X posts on GEO
  (gbot, “GEO方法论”): page retrieval by a unique sentence (Ann Smarty) and 404s from URLs AI
  assistants make up. Neither has been run on our sites yet.
- Split out of site-check on 2026-10-22 so page SEO acceptance stays reproducible and AI samples,
  which need the user's account, run on their own. First run on tinywonderpost.com (local build):
  every AI crawler allowed; llms.txt still said "Story Kits" after the shop moved to holiday
  printables, and did not list the home page or /pricing.
