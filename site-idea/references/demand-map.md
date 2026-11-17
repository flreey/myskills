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
3. **Write `geo/needs.jsonl`** (one need per line, format below), then `geo_idea.py needs`. It checks
   every evidence item and writes `geo/needs.md`, the table to show the owner.
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
 "where_asked": ["assistant", "forum"], "count": 111, "evidence_level": "validated",
 "evidence": [
   {"source": "forum", "url": "https://www.reddit.com/r/gamedev/comments/…", "quote": "100% copyright free sounds to use as effects in my games", "date": "2025-12-14"},
   {"source": "site_search", "ref": "search_log 2026-09-18..11-17", "q": "free cc0 cat sound effects", "n": 9}
 ]}
```

| Field | Rule |
| --- | --- |
| `evidence_level` | `validated`: real evidence from at least one source; `derived`: inferred from evidence of a neighbouring need, evidence listed; `hypothesis`: no evidence yet |
| `evidence[]` | Off-site: `url` and a verbatim `quote`. First-party: `ref` (table or export and window) and `q` (the query) or `quote`; `n` when counted. Never a paraphrase presented as a quote |
| `count` | Evidence rows behind the need. Not market size; counts from different sources are not added as if they were one measure |
| `where_asked` | `assistant`, `search_engine`, `site_search`, `agent`, `forum`, `support`, `other` |

## Limits to state in the report

- Search logs without a client id can be dominated by one integration; say so when one query is far
  above the rest.
- Repeated identical descriptions may be one person or a test.
- Off-site quotes lean to the communities that could be fetched; name the ones that were not.
