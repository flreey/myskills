# AI demand and citation share (check G5)

For an existing site whose visitors come mostly from AI assistants. It answers two questions:

- Which pages do the assistants actually use?
- Which existing pages lose citations they could win?

Google SERP and keyword difficulty measure a different channel. Use them as context only, not as the gate.

## When to run

- Run this when AI assistants bring at least half the visitors over the last 28 days.
- ChatGPT's web app often opens links with `noreferrer` and no `utm_source`, so analytics record many of its visitors as direct. Count direct visits that land on deep pages as part of that share.
- When Google and AI are both large, report the two channels in separate sections; never rank them in one table.

## Sources

Use at least two. For each, record the window, the date read and where it came from.

| Source | What to read | It shows | It does not show |
|---|---|---|---|
| **Search crawler fetches**: CDN or server logs for `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, with each page's first fetch date | Which pages the search crawler has read, which it has never read, and whether visits start after the first read | The pages a search index can hold. On one site, 486 of 539 pages with both a read and an AI visit were read first | A read is not inclusion, and it can follow demand. Fetches can arrive in large batches, so compare page groups within the same period and page category |
| **User crawler fetches**: CDN or server logs for `ChatGPT-User`, `Claude-User`, `Perplexity-User`, summed by path | Pages fetched while answering, merged by page type and family; file downloads counted apart from pages | What people ask the assistant for, and which pages it can already find | A fetch is not a click. Cloudflare's free plan keeps these logs about 8 days, so save them weekly to read longer windows |
| **Bing Webmaster Tools → AI Performance** (Microsoft Copilot and partners) | Grounding queries with citations and citation share; cited pages | The only per-query view of AI citations | It is sampled and Bing refines it later. It is Microsoft's data, not ChatGPT's |
| **Site, API or MCP search misses** | Queries with no exact match, by count; dedupe by client when there is a client field | Content the site lacks | One agent calling in a loop inflates counts; without a client field, treat counts as leads only |

Reading the CDN logs, Bing Webmaster Tools or the site's database uses the owner's accounts. Like rule 3, it needs their go-ahead in chat, unless the project already has a standing read-only method for it.

Tool output (logs, Bing exports, database rows) is a fact about the server or about Bing's sample. ChatGPT probe answers are samples (rule 2). Keep them apart.

## Classify the gap first

Name the gap before choosing a fix. Probe answers supply the first two rows and analytics the last two.

| Gap | Evidence | Look at |
|---|---|---|
| **Not mentioned** | The site is absent from answers on the target query | Whether the search crawler has read the page, what the assistant searched (probe D), and whether the site has a page for this task |
| **Mentioned, no link** | Named without a link to the site | A stable page for this exact task, and a clear name for the product or tool |
| **Linked, no visits** | Linked in answers, with few visits to that page | Whether the link goes to the right page, and an accurate title and description. Check the answers again first: one sampled link does not show how often it appears |
| **Visits, no action** | Visitors arrive and do not preview, download, sign up or buy | The first screen, speed, stated price and license, and the event tracking |

## What to do with them

| Finding | Test | Hand off |
|---|---|---|
| **Improve an existing page** | A page matches the query but its citation share is low, or it is fetched often and rarely visited | Name the facts to change: put the user's own wording in the title or first lines, state the files, lengths and license above the fold, and remove hedging copy that lowers confidence. Each change goes to site-check or the project's copy workflow |
| **New page** | The sources show demand and the site has no matching page | site-plan decides whether to build it. For new-domain Google keywords, use keyword-radar |
| **Missing content** | Searches miss and the site has nothing of that kind | The project's content workflow; not a page decision |

Often all three sources point at generic pages the site already has, and the new-page count is 0. Report that, and spend the effort on improving those pages. Do not go back to Google long-tail lists to fill a quota.

## Before changing a page

Write this down first, so the result can be read later:

- the pages changed, the change and its date;
- the baseline window and its numbers;
- the unchanged pages to compare with, when the change can leave some out;
- the review dates;
- the result that would show the idea was wrong.

Several changes on one day cannot be credited one by one, and a rise without comparison pages may come from the assistant itself. Do not change comparison pages while a test runs, and do not swap the prompt set before a planned re-test.

## Following up

- Re-read after 14 and 28 days:
  - fetches of the changed pages;
  - whether Bing lists them as cited;
  - the target queries' citation share against the value before the change;
  - the same probe set rerun (probes B and C) for the share of answers that link the site.
- Shares and probes move a lot. Do not call a change from one reading; use at least two.
