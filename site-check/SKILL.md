---
name: site-check
description: Use when a site or a built or live page needs SEO acceptance before or after release — sweeping every sitemap URL for mechanical problems (status, noindex, canonical, JS-only content, FAQ answers missing from HTML, robots blocking OAI-SearchBot), then checking that the copy is written around its target keywords, that the FAQ answers the questions users ask, that the content is in the server-rendered HTML, that ChatGPT's crawlers can reach the page, and what ChatGPT says about recommending the site and how to earn more recommendations. Works on site-kit and other sites. Also for 全站 SEO 检查、页面 SEO 验收、上线前检查、关键词文案检查、FAQ 检查、是否服务端渲染、ChatGPT 能不能访问、GPT 会不会推荐. NOT for keyword discovery (site-research), deciding which pages to build (site-plan) or kit build gates (site-kit npm run check).
---

# site-check: page SEO acceptance

Two layers. The **sweep** covers every sitemap URL with mechanical facts only; the script does it,
not the model. The **page checks** (five, each ending in pass, fix or unknown with evidence) run on
pages you pick. Checks 1–4 start from what a crawler receives: the raw HTML, not the page in a
browser. Check 5 is opinion evidence from ChatGPT, kept apart from facts, and is asked per target
query, not per page.

Engine (Python stdlib, read-only), `python3 <skill-dir>/scripts/page_check.py`:

- `--sitemap <url|file> [--base <origin>] [--limit N]`: sweep. Follows sitemap indexes; `--base`
  fetches the listed paths from another origin (a local build or preview). Groups issues by URL
  shape (`/`, `/<page>`, `/<section>/*`); a shape where every page has the issue points at a shared
  template or component. Also lists FAQ question shapes repeated on 3+ pages (`templated_questions`)
  and pages whose FAQ starts collapsed (`faq_hidden`). About one second per URL.
- `--url <url> [--keyword "<phrase>"]... [--brief <brief.json>] [--pool <observations.jsonl>]`: one
  page in depth. With
  `--brief seo/work/briefs/<slug>.json` from site-plan it takes the primary phrasings, questions
  and sub-needs from there.

Both take `--format json`.

## Iron rules

1. **Target first.** The keywords come from the site-plan brief or the page registry. Without them,
   ask the user for the page's target query; never infer it from the page's own copy.
2. **Raw HTML is the evidence** for checks 1–4. Text that appears only after JavaScript does not
   count as on the page.
3. **Never loop the page check over the whole site.** Site-wide questions go to the sweep; the
   model reads its grouped output, not one report per URL.
4. **The script pre-sorts, the model judges.** Placement flags and question overlaps are hints.
   Whether the copy serves the intent, and whether an FAQ answer really answers, is your call,
   quoted from the page.
5. **ChatGPT answers are samples, not measurements.** They vary per run, model and account. Record
   the date, model, mode and full prompt; repeat in fresh chats; never report one answer as a fact
   about ranking.
6. **Using the user's ChatGPT account needs their go-ahead** in chat. Otherwise hand them the
   prompts and read back what they paste.
7. **Read-only.** This skill reports. Copy changes follow the project's own workflow (site-kit rules
   on kit sites); new sub-needs or pages go back to site-plan. Never write under `seo/`.
8. **No tricks.** Do not act on advice to stuff keywords, add hidden text, fake reviews, invent
   statistics or show crawlers different content from users.

## Workflow

1. **Sweep** the sitemap (live, or a local build with `--base`). Skip it only when the user asks
   about one page. On kit sites `npm run check` already gates the build; the sweep then checks the
   deployed result. Read the grouped issues: fix shared causes once (template, component, robots,
   headers), not page by page. `thin_server_html` is a flag to look at, not a verdict: a tool page
   can be short and still serve its query.
2. **Pick pages** for the page checks: new or changed pages, the pages with the most GSC
   impressions (site-plan's latest window), and one page per issue shape from the sweep. Say which
   pages were picked and why; the rest of the site is covered only by the sweep.
3. For each picked page: get the target (`--brief`, or `--keyword` per phrase), run
   `page_check.py --url`, open the same URL in the browser, read the rendered text
   (`get_page_text`) for check 3 and screenshot the FAQ area for 2c, then work through checks 1–4. If the fetch fails, stop that page
   and report it.
4. **Check 5 once per target query**, not per page: two or three of the site's main queries with
   [references/chatgpt-probes.md](references/chatgpt-probes.md).
5. Report.

## Checks

### 1. Copy is written around the keyword

- The primary phrase, or a natural form of it, is in the title, H1 and opening paragraph. The
  description should contain it; a subheading or two should carry the close variants.
- Read the opening text: does it answer what the searcher wants (task, result, who it is for)
  before anything else? Sub-needs marked `covered` or `write_it` in the brief are stated in the copy.
- Fail on stuffing as well: the same exact phrase repeated where a person would not say it.

### 2. FAQ: nothing missing, everything right, easy to find

Three separate verdicts. A page can answer every question and still be wrong, or be right and miss
what people ask.

**2a. Missing.** Which questions do searchers have that the page does not answer?

- Sources, in this order: the brief's `questions`; GSC queries for the page (the brief's `gsc`
  block); question queries from the site-research pool (`--pool seo/discovery/observations.jsonl`,
  matched on the page's subject words); People Also Ask from a SERP capture; the product's own
  support mail and reviews. List each with answered / partly / missing.
- A missing question goes on the page when it is about this page's task and the product can answer
  it truthfully. Questions about a different task belong to another page or to site-plan; questions
  the product cannot answer honestly stay out.
- The sweep's `templated_questions` shows FAQs repeated across pages with only the tool name
  swapped. Templated questions are rarely the ones searchers ask: treat them as missing coverage on
  every page they fill, and fix them at the template.

**2b. Right.** Is each answer true, specific and direct?

- **True to the product.** Check every factual claim against the code or by using the tool in the
  browser: limits, formats, counts, what is stored or sent, how randomness is produced
  (`Math.random` is not "cryptographically secure"), what happens on reload. Quote the code
  location or the observed behaviour. A false or unverifiable claim is a fix before anything else.
- **Consistent.** Same facts as the rest of the page, the schema answer, other pages and the
  privacy policy.
- **Answers the question asked**, first sentence first, in the searcher's words. Marketing copy,
  "it depends" without the dependency, or an answer that only restates the question is a fix.
- **Specific to this page.** The same answer word for word on many pages (`same_answer_pages`) is a
  template, not an answer.
- **Current.** Numbers, tool counts, versions and dates match today's product.

**2c. Seen.** Can a visitor find the FAQ without hunting for it?

- The FAQ shows on load under its own heading, with questions styled apart from answers. A whole
  FAQ inside a closed `<details>` or "About this tool" block (`collapsed_questions`, sweep issue
  `faq_hidden`) is a fix; so is an FAQ that renders as undifferentiated text once opened.
- One accordion item per question is fine when every question shows on load and only the answers
  fold.
- Take a screenshot of the FAQ area as it loads (and opened, if it folds): raw HTML cannot show
  layout. Search engines index collapsed text, so report this as a visitor problem, not an
  indexing error.

Mechanics, for all three:

- `visible_questions` is every question-like text outside nav, header, footer and aside; drop demo
  text and headings that are not FAQ items. `schema_answer_not_visible` means the question shows
  but its answer is not in the server HTML (often an accordion that renders on click): a fix.
- Every answer is visible in the server HTML. Questions found only in `FAQPage` schema
  (`schema_only`) are a fix.
- Since 2023-08 Google shows FAQ rich results only for well-known government and health sites, so
  `FAQPage` markup is optional; visible questions and answers are what counts.

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
  site-plan. Drop advice that is generic or breaks rule 8.

## Report

First the sweep: URLs checked, issues by type and URL shape, what was fixed at the shared cause.
Then one table per picked page: check, result (pass / fix / unknown / MANUAL), evidence (quoted text, field
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
- 2c was added after the randtools FAQ fix shipped: every check passed, yet the owner could not
  find the FAQ, because it sat in a collapsed "About this tool" block and rendered as plain text.
  Crawler evidence alone is not acceptance.
- FAQ checks first run 2026-10-21 on randtools.com: the sweep found 3 templated questions on
  13–14 tool pages while each tool's specific FAQs sat unused in the code; a code reading suggested
  dates stop at day 28, but 400 dates generated on the live page covered 1–31, so behaviour wins
  over code reading. Pool matching is lexical: "how random number generator works" was marked
  `likely_answered` against "How do I use …?", so judge every pool hint yourself.
- Sweep first run 2026-10-21 on randtools.com: 39 URLs in 34 s; it confirmed the home FAQ answers missing from HTML and flagged 13 tool pages at 150–180 words. Not yet run in a fresh session; thresholds (`thin_server_html` below 200 words,
  question overlap 0.5 / 0.34) are uncalibrated.
