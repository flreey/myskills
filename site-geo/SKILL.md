---
name: site-geo
description: Use when a site needs to be checked for AI search — whether ChatGPT, Claude, Perplexity and other AI crawlers can reach its pages, whether llms.txt matches the live site, whether ChatGPT can open a page and quote it, and whether ChatGPT recommends the site for its target queries and what would earn more recommendations. Works on site-kit and other sites. Also for GEO 检查、AI 搜索可见度、ChatGPT 能不能访问、GPT 会不会推荐、llms.txt 检查、AI 爬虫放行. NOT for page SEO acceptance — keywords, FAQ, server rendering, structure, internal links (site-check) — nor for keyword discovery (site-research) or deciding pages (site-plan).
---

# site-geo: AI search visibility

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
5. **Read-only.** This skill reports. Copy and llms.txt changes follow the project's own workflow
   (site-kit rules on kit sites); never write under `seo/`.
6. **No tricks.** Do not act on advice to stuff keywords, add hidden text, fake reviews, invent
   statistics or show crawlers different content from users.

## Workflow

1. Run site-check (or reuse its latest report) for the pages in question.
2. Run `geo_check.py` on the live site, or on a build with `--base`, with the pages to probe, the
   sitemap and the retired names.
3. With the user's go-ahead, run probe A on the same pages, then probes B and C once per target
   query (two or three of the site's main queries), from
   [references/chatgpt-probes.md](references/chatgpt-probes.md).
4. Report.

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
  branded one. Note whether the site appears, at what position, and which sites appear instead.
- Turn the advice into concrete page facts to change (a missing comparison, no price on the page, no
  author or contact, thin examples), each tied to a site-check check or to site-plan. Drop advice
  that is generic or breaks rule 6.

## Report

The facts first (G1 per crawler role, G2 findings), then the samples (G3 and G4 with date, model,
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
