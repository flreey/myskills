# Measuring waves

New domains have little traffic, so the unit is the template (and the wave and arm inside it), not
the page. `geo_engine.py funnel` reads `geo/measure/snapshots.jsonl`; this file says how to fill it.

## What counts as the result

The goal is that assistants send people here. The page-side funnel (crawled → indexed → AI fetch →
cited → referrals) shows where pages drop, but its later steps say what happens after a page is
opened. Read each wave against two results as well:

1. **Presence:** re-run the site-idea probes for a sample of the wave's combinations (and the control)
   with the same questions as the baseline: share of answers with the site, first recommendations,
   own pages cited. This is the primary result.
2. **Retrieval:** for the search queries captured in the baseline, where the wave's pages rank (Search
   Console and Bing for the owner's site, or a quick check of the query). A page that does not show up
   for the rewritten query will not be opened, whatever it says.

AI referrals and the site's core action per landing page (site-measure) come next. "Referrals ÷ AI
fetch" and take-rate are secondary: they move only for pages that are already found.

Windows count from the wave's `deployed` day (`wave-deployed`); without it, from `released`, and the
funnel says so.

## Snapshot rows

```json
{"date": "2026-12-01", "url": "/convert/heic-to-jpg-batch", "crawled": true, "indexed": false,
 "ai_fetch": true, "cited": null, "referrals": 2, "source": "gsc-pages-export+cf-ai-crawl+umami"}
```

`null` means not measured; it is left out of that rate, never counted as false. One row per URL per
collection date; the funnel uses the newest row per URL.

| Field | Where it comes from | Who |
| --- | --- | --- |
| `crawled` | Search Console Pages report or URL Inspection ("Crawled" / last crawl date); Bing Webmaster URL inspection | owner exports, or reads it to you (MANUAL: their accounts) |
| `indexed` | Same reports: "Indexed" vs "Crawled – currently not indexed" / "Discovered – not indexed" | owner |
| `ai_fetch` | Requests from AI search or user crawlers (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot…). Kit pages are static assets, so the Worker does not log them: use Cloudflare AI Crawl Control or Logpush for the zone | owner (dashboard), MANUAL |
| `cited` | AI samples: run the site-idea probe for a few released combinations per template (same rules: their accounts need their go-ahead) and mark whether the page was cited | model + owner |
| `referrals` | Umami (site-measure): visits with an AI assistant referrer, by landing URL | model, via site-measure |

Collect a first snapshot one week after a release, then every 1–2 weeks. Do not judge a wave before
its observation window (default 3–4 weeks after release).

## Reading the funnel

The funnel prints, per template, per wave and per arm: released pages, measured pages and the rates.
Find the first step that drops:

| Drop at | Usual cause | Move |
| --- | --- | --- |
| crawled | not discovered: few links in, no outside signal, sitemap not submitted | hubs and groups linked from the home, submit the sitemap, off-site work |
| indexed | judged duplicate or thin | raise combination-specific data, merge near-duplicates, stop expanding this template |
| ai_fetch | assistants do not retrieve it for these tasks | titles and answers closer to how people ask, check the AI crawlers are allowed (site-geo) |
| cited | retrieved but not chosen | answer first and more specific, constraint results complete |
| referrals | cited but not visited or not acted on | resource button, landing on the task, not on a hub |

Compare templates only on pages of similar age. A template whose indexed rate stays far below the
others after its window is held: no new wave for it until the cause is fixed.

## Experiments

With `experiment` in a template, arms split its pages by hash. Compare arms on the same step within
the same wave. Small counts decide nothing: say how many pages each rate rests on.

## Pruning

`prune --min-days 28` lists released pages whose newest snapshot says not indexed after the window,
counted from the deploy day when it is recorded.
For each: check links and content first; then merge it into a sibling or the group page (the row
leaves the combos file; add a redirect through site-plan's registry or the kit's redirect config) or
keep it unreleased. Removing pages is the owner's call and ships through the site-kit release.
