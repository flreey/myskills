# Demand map: what people are trying to get done

Step 0, before any dimension. The map says who has which need, what gets in their way and where
they bring it, with the evidence behind each line. Dimensions, questions and pages are derived from
it; a dimension that no need asks for is not a dimension.

Written after the first live run (SFXMint, 2026-11-17): a wave of retrofitted pages was planned from
the page type that already existed, and the questions were found afterwards. The real data showed
the largest need (rights and safety, 35% of forum quotes) was asked of assistants and forums, not
in site search, and the page change did not touch it.

## Sources, first-party first

| Source | What it shows | Typical ref |
| --- | --- | --- |
| Site, API and MCP search (`site_search`, `api_search`, `mcp_search`) | what people and their agents ask the product for, in their words | `search_log 2026-09-18..11-17` |
| Zero-result searches and "not found" messages (`search_miss`, `feedback`) | needs the product fails today | `feedback table, all rows` |
| Generation prompts, chat or project descriptions (`product_log`) | the whole job in the person's words: project, event list, constraints | `kit_chats, last 150` |
| Support mail, purchase surveys (`support`, `survey`) | doubts before paying, why they paid | `purchase_source_feedback` |
| AI user-crawler fetches and AI referrals by page (`ai_fetch`, `ai_referral`) | tasks assistants already route to the site | `Cloudflare AI crawl, 28d` |
| Forums, Q&A, reviews, social, video comments (`forum`, `qa`, `review`, `social`, `video`) | needs before people reach any product; complaints about competitors | a URL per quote |
| Competitor pages (`competitor_page`) | which needs competitors serve with dedicated pages | a URL |

A new idea has only the off-site rows; a live site has both, and its own rows usually carry most of
the volume (on SFXMint, 84% of site searches came from AI agents through the API and MCP).

## Steps

1. **Collect.** Read-only queries and exports for the first-party sources (state the window), and a
   few searches per audience for off-site quotes (real URL, a short verbatim quote, the date). Keep the
   raw pulls outside the repository or under `geo/assets/` when they hold no personal data.
2. **Group into needs.** A need is a job, not a keyword: "use sounds in a commercial game without
   claims or credit", not "cc0 sounds". Usually 5–10 needs per audience. For each: the people who
   have it, the pains that block it, where it is asked (`where_asked`), and a count of the evidence rows
   behind it.
3. **Write `geo/needs.jsonl`** (one need per line, format below), then `geo_idea.py needs --quotes
   <collected posts>` (CSV or JSONL with `url` and `quote`). It checks every evidence item, checks that
   each off-site quote appears verbatim in the collected post at that URL, and writes `geo/needs.md`,
   the table to show the owner.
4. **Read the map with the owner** before dimensions: which needs to serve, which audiences, and
   where each need is asked. That last column decides the lever later:
   - asked in site search or by agents → library and search quality, item pages, the API;
   - asked of assistants and on forums → the pages and sources assistants read (question bank,
     probes, off-site);
   - asked nowhere yet → a hypothesis; it ranks last.

## Format

```json
{"id": "n-safe-to-ship", "need": "use sounds in a commercial game or video without claims or credit trouble",
 "personas": ["indie game developer", "YouTube creator"],
 "pains": ["royalty-free vs copyright-free confusion", "Content ID claims despite a licence", "AI disclosure on Steam"],
 "where_asked": ["assistant", "forum"], "count": 111, "count_by_source": {"forum": 104, "feedback": 7},
 "volume": [{"ref": "search_log 2026-09-18..11-17, web+api+mcp", "what": "licence words", "n": 23}],
 "evidence_level": "validated",
 "evidence": [
   {"source": "forum", "url": "https://www.reddit.com/r/gamedev/comments/…", "quote": "100% copyright free sounds to use as effects in my games", "date": "2025-12-14"},
   {"source": "site_search", "ref": "search_log 2026-09-18..11-17", "q": "free cc0 cat sound effects", "n": 9}
 ]}
```

| Field | Rule |
| --- | --- |
| `evidence_level` | `validated`: real evidence from at least one source; `derived`: inferred from evidence of a neighbouring need, evidence listed; `hypothesis`: no evidence yet |
| `evidence[]` | Off-site: `url` and a verbatim `quote`. First-party: `ref` (table or export and window) and `q` (the query) or `quote`; `n` when counted. A counted answer option (a survey choice) is `value` and `n`. Never a paraphrase presented as a quote |
| `count` | Evidence rows behind the need (quotes, messages, descriptions). Not market size. One row may sit under two needs, so counts are never summed into shares |
| `count_by_source` | Optional split of `count` by source, e.g. `{"forum": 104, "feedback": 7}` |
| `volume` | Optional request counts, a different measure from `count`: `[{"ref": "search_log 60d, api+mcp", "what": "3+ word queries", "n": 38384}]`. Requests are not people; never added to `count` |
| `where_asked` | `assistant`, `search_engine`, `site_search`, `agent`, `product` (inside the product: generator prompts, project chats), `forum`, `support`, `other` |

## Pulling first-party data

Aggregate in SQL: whole-table exports of request logs can exceed the database's response limit (D1
caps a result at about 50 MB). Check each table's time unit before filtering: on SFXMint
`search_log.created_at` is in seconds and other tables in milliseconds. Exclude the owner's own test
clients and internal sources, and say how. Shapes that worked (D1 / SQLite, `:since` in the table's
unit):

```sql
-- volume by source, and distinct queries
SELECT source, count(*) n, count(DISTINCT lower(q)) uq FROM search_log WHERE created_at > :since GROUP BY source;
-- long queries (3+ words): where situations and conditions show up
SELECT lower(q) q, source, count(*) n, max(n_exact) exact_hits FROM search_log
 WHERE created_at > :since AND source != 'internal' AND length(q) - length(replace(q, ' ', '')) >= 2
 GROUP BY lower(q), source ORDER BY n DESC LIMIT 1500;
-- misses: zero exact results
SELECT lower(q) q, count(*) n FROM search_log WHERE created_at > :since AND source != 'internal' AND n_exact = 0
 GROUP BY lower(q) ORDER BY n DESC LIMIT 500;
-- a burst from one integration: one query, one day, far above the rest
SELECT date(created_at, 'unixepoch') d, lower(q) q, count(*) n FROM search_log WHERE created_at > :since
 GROUP BY d, lower(q) HAVING n > 200 ORDER BY n DESC;
-- agent constraints: count requests per constraint, never export the JSON column whole
SELECT source, sum(json_extract(constraints_json, '$.max_duration_ms') IS NOT NULL) with_max_duration,
       sum(json_extract(constraints_json, '$.explicit_loop') = 1) with_loop, count(*) n
  FROM ready_search_requests WHERE created_at > :since_ms GROUP BY source;
```

Free-text tables (feedback, generator prompts, chats) are read in full but stay outside the
repository; the map keeps short quotes and counts only.

## Limits to state in the report

- Search logs without a client id can be dominated by one integration; say so when one query is far
  above the rest.
- Repeated identical descriptions may be one person or a test.
- Off-site quotes lean to the communities that could be fetched; name the ones that were not.
