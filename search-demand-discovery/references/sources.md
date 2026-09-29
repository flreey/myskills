# Free sources: what each gives and how to capture it

| Source | Access | Evidence kind | Best for | Throughput |
| --- | --- | --- | --- | --- |
| Google, YouTube and Bing autocomplete | script (`suggest`) | `search_suggestion` | Raw breadth, long tail, real phrasing | High |
| Google Keyword Planner | browser, Google Ads sign-in | `historical_volume` | Volume ranges, competitor keyword space | Medium |
| Google Search Console | browser, verified property | `gsc_impression` | Demand already reaching the site | Medium |
| Google Trends | browser, no sign-in | `trend_related` | Rising and breakout entities, seasonality | Low |
| SERP "People also ask" and related searches | browser | `related_search` | Question forms, adjacent jobs | Low |
| Bing Webmaster Tools keyword research | browser, account | `external_reference` | Bing impressions, related keywords | Medium |
| Competitor sitemaps and navigation | script (`sitemap`) | concept `hypothesis` | Entity space you do not cover yet | High |
| Industry taxonomy | research | seed `taxonomy` | Systematic coverage | — |
| Site search and request logs | project data | `onsite_request` | Product demand (not search volume) | — |
| Paid exports (Ahrefs, Semrush) | user files | `external_reference` / `historical_volume` | Volume, parent topics | High |

## Autocomplete (script)

- `suggest --level quick|standard|deep`. Quick uses expression templates. Standard adds prefixes,
  suffixes and question templates. Deep adds `a–z` for the most productive seeds.
- YouTube suggestions skew towards media ("1 hour", "meme"). Triage those as `adjacent` or
  `modifier`; do not drop them silently.
- Endpoints are unofficial. On a pause, continue with other sources and retry the next day. The
  cache prevents repeat requests for 7 days.

## Google Keyword Planner

1. Tools → Keyword Planner. Set location and language to the target market before any request, and
   record them.
2. **Discover new keywords → Start with keywords.** Enter up to 10 related seeds per request, then
   download the keyword ideas.
3. **Discover new keywords → Start with a website.** Enter a competitor domain or category URL to
   get the keyword space it attracts. This is the strongest free top-down source.
4. **Get search volume and forecasts.** Upload the chunks from `export --format planner` to put
   ranges on pool keywords that have none.
5. Import each export with `import --format gkp --file <csv>`. The period comes from the monthly
   columns. Pass `--country/--language` when they differ from the config market.

Pitfalls: accounts without spend show ranges (`1K – 10K`), and they stay ranges. Planner groups
close variants and repeats the group's volume on each variant; never add up variants. Low
"Competition" is advertiser competition, not SEO difficulty.

## Google Search Console

1. Performance → Search results → Search type: Web. Set the date range (at most 16 months).
2. Queries tab → Export → download the CSV zip.
3. The table caps at 1,000 rows. When a site has more, slice the export: Query filter "contains
   <seed>", or one export per important page (Page filter).
4. Import with `import --format gsc --file <zip> --period YYYY-MM-DD..YYYY-MM-DD`. The UI range is
   relative ("Last 3 months"), so compute the absolute dates. Data lags about 3 days.
5. Per-page exports also feed `search-demand-mapper gsc import` for the page feedback loop.

Small properties can skip the download: set Rows per page to 500, read the table rows from the
page, save them as a CSV with the header `Top queries,Clicks,Impressions,CTR,Position`, and check
the saved rows against the page (row count, summed impressions, a hash of the rows) before
importing. The data is the same as the export.

Pitfalls: anonymized queries are missing, so missing does not mean no demand (in the SFXMint
trial the visible queries carried 22% of all impressions). Countries are global unless filtered.
Never add query exports to query+page exports. Expect GSC to surface demand autocomplete never
showed: 264 of SFXMint's 330 visible queries were not in a 17,408-keyword autocomplete pool.

## Google Trends

1. Explore a term. Set the market and a 12-month range.
2. Related queries: download the CSV (it contains the TOP and RISING sections).
3. `import --format trends --file <csv> --ref "<term>"`. Values are relative; `Breakout` marks a
   fast riser.

Use it for the top 5–10 seeds and for checking seasonality before prioritizing. It is not a
bulk source.

## SERP related searches and "People also ask"

Search a representative query in the target market. Copy the "People also ask" questions and
"Related searches" into a text file with one per line, then run
`import --format lines --source google_serp --kind related_search --ref "<query>"`.
Keep the result URLs and result types too: `search-demand-mapper` needs them as SERP evidence.
Budget about 30 searches per session; stop on a CAPTCHA.

## Bing Webmaster Tools

Keyword Research → enter seeds → export. Run
`import --format csv --source bing_webmaster --file <csv>`. Without `--period`, volume is kept as
`volume_unperiodized` and is never treated as historical volume.

## Competitor sitemaps

`sitemap --url https://competitor.example` reads robots.txt or `sitemap.xml`, follows up to 20
child sitemaps and keeps slug phrases up to URL depth 3. Phrases become `hypothesis` concepts.
Triage a phrase as `seed` only when it fits the boundary; it gains keywords only once a search
source observes them. When there is no sitemap, read the competitor's category navigation in the
browser and add the categories as `topdown` seeds.

## Structured JSON (anything else)

`import --format json --source <name>` accepts `[{"keyword", "kind", "metrics", "period",
"market", "source_ref"}]`. Use it for data captured by hand or by other tools. `historical_volume`
requires a period.
