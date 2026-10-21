---
name: site-check
description: Use when a built or live page needs SEO acceptance before or after release — checking that the copy is written around its target keywords, that the FAQ answers the questions users ask, that the content is in the server-rendered HTML, that ChatGPT's crawlers can reach the page, and what ChatGPT says about recommending the site and how to earn more recommendations. Works on site-kit and other sites. Also for 页面 SEO 验收、上线前检查、关键词文案检查、FAQ 检查、是否服务端渲染、ChatGPT 能不能访问、GPT 会不会推荐. NOT for keyword discovery (site-research), deciding which pages to build (site-plan) or kit build gates (site-kit npm run check).
---

# site-check: page SEO acceptance

Five checks on one page at a time, each ending in pass, fix or unknown with evidence. Checks 1–4
start from what a crawler receives: the raw HTML, not the page in a browser. Check 5 is opinion
evidence from ChatGPT, kept apart from facts.

Engine (Python stdlib, read-only):
`python3 <skill-dir>/scripts/page_check.py --url <url> [--keyword "<phrase>"]... [--brief <brief.json>] [--format json]`.
With `--brief seo/work/briefs/<slug>.json` from site-plan it takes the primary phrasings, questions
and sub-needs from there.

## Iron rules

1. **Target first.** The keywords come from the site-plan brief or the page registry. Without them,
   ask the user for the page's target query; never infer it from the page's own copy.
2. **Raw HTML is the evidence** for checks 1–4. Text that appears only after JavaScript does not
   count as on the page.
3. **The script pre-sorts, the model judges.** Placement flags and question overlaps are hints.
   Whether the copy serves the intent, and whether an FAQ answer really answers, is your call,
   quoted from the page.
4. **ChatGPT answers are samples, not measurements.** They vary per run, model and account. Record
   the date, model, mode and full prompt; repeat in fresh chats; never report one answer as a fact
   about ranking.
5. **Using the user's ChatGPT account needs their go-ahead** in chat. Otherwise hand them the
   prompts and read back what they paste.
6. **Read-only.** This skill reports. Copy changes follow the project's own workflow (site-kit rules
   on kit sites); new sub-needs or pages go back to site-plan. Never write under `seo/`.
7. **No tricks.** Do not act on advice to stuff keywords, add hidden text, fake reviews, invent
   statistics or show crawlers different content from users.

## Workflow

1. Get the URL (live, preview or local) and the target: `--brief`, or `--keyword` for each phrase.
2. Run `page_check.py`. If the fetch fails, stop and report it: every other check depends on it.
3. Open the same URL in the browser and read the rendered text (`get_page_text`) for check 3.
4. Work through checks 1–5 below; for 4 and 5 use [references/chatgpt-probes.md](references/chatgpt-probes.md).
5. Report.

## Checks

### 1. Copy is written around the keyword

- The primary phrase, or a natural form of it, is in the title, H1 and opening paragraph. The
  description should contain it; a subheading or two should carry the close variants.
- Read the opening text: does it answer what the searcher wants (task, result, who it is for)
  before anything else? Sub-needs marked `covered` or `write_it` in the brief are stated in the copy.
- Fail on stuffing as well: the same exact phrase repeated where a person would not say it.

### 2. FAQ answers what users ask

- Sources of questions, in this order: the brief's `questions`, GSC queries for the page (the
  brief's `gsc` block), People Also Ask and related searches from a SERP capture, the product's
  own support and reviews. List each with answered / missing / partly.
- `visible_questions` is every question-like text outside nav, header, footer and aside; drop demo
  text and headings that are not FAQ items. `schema_answer_not_visible` means the question shows
  but its answer is not in the server HTML (often an accordion that renders on click): a fix.
- Every answer is visible on the page, in the server HTML, starting with the direct answer in the
  first sentence. Questions found only in `FAQPage` schema (`schema_only`) are a fix.
- Since 2023-08 Google shows FAQ rich results only for well-known government and health sites, so `FAQPage`
  markup is optional; visible questions and answers are what counts.

### 3. Server-rendered

- `rendering.verdict`: `server_html_has_content` passes; `thin_server_html` needs a look;
  `client_rendered_shell` fails.
- Compare the rendered text with the raw HTML: title, H1, main copy, FAQ answers and internal
  links must all be in the raw HTML. Name anything present only after JavaScript.
- Kit sites are prerendered by design; a failure there is a kit bug or a client-only island.

### 4. ChatGPT crawlers can reach the page

- `OAI-SearchBot` decides whether the page can appear in ChatGPT search; `GPTBot` is training
  only; `ChatGPT-User` fetches when a user asks. robots.txt must not disallow `OAI-SearchBot`
  (blocking `GPTBot` is the owner's choice and does not affect search).
- No `noindex` in meta robots or `X-Robots-Tag`. Probes with OpenAI user-agents should return
  200, no challenge page, about the same HTML as a browser.
- A probe only shows rules keyed on the user-agent string. Firewalls that verify bots by IP
  (Cloudflare bot settings and AI crawler controls) are checked in the dashboard: that is a MANUAL
  item for the user, with the zone named.
- Then ask ChatGPT to open the URL (probe A in the reference). Pass when it quotes the real title
  and the first lines; fail when it cannot open the page, or when it answers from search snippets
  or guesses.

### 5. Would ChatGPT recommend the site

- Run the unbranded probes first (the user's real task in the target market's language, no site
  name), then the branded one. Note whether the site appears, at what position, and which sites
  appear instead.
- Turn the improvement advice into a list of concrete page facts to change (a missing comparison,
  no pricing on the page, no author or contact, thin examples), each tied to a check above or to
  site-plan. Drop advice that is generic or breaks rule 7.

## Report

One table per page: check, result (pass / fix / unknown / MANUAL), evidence (quoted text, field
from the script output, or the ChatGPT answer with date and model) and the fix. Then the fixes in
priority order, the MANUAL items, and what was not checked. Save it to a file only when the user
asks, outside `seo/`.

## Premises

- Checked 2026-10-21 against OpenAI's bot documentation: tokens `OAI-SearchBot` (ChatGPT search;
  robots.txt applies; changes take about 24 hours), `GPTBot` (training; robots.txt applies),
  `ChatGPT-User` (user-initiated fetches; robots.txt may not apply; not used for search
  inclusion), `OAI-AdsBot` (ad landing pages only). IP lists: `openai.com/searchbot.json`,
  `gptbot.json`, `chatgpt-user.json`.
- Checked 2026-10-21 (news reports, not Cloudflare docs): from 2026-09-15 Cloudflare groups bots as
  Search, Agent and Training; new domains block Training and Agent crawlers by default on pages with
  ads, with Search allowed. Where OpenAI's bots fall was not confirmed, so check the zone's settings.
- Not yet run on a real site in a fresh session; thresholds (`thin_server_html` below 200 words,
  question overlap 0.5 / 0.34) are uncalibrated.
