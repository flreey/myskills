# Data contract (discovery side)

All paths are relative to `<project>/seo/`. Schema tags use `search-demand/<type>@<version>`.
Discovery writes these files. `site-pages` only reads `config.json`, `boundary.json` and
`discovery/observations.jsonl`.

| File | Kind | Owner | Notes |
| --- | --- | --- | --- |
| `config.json` | JSON | shared | `market`, `discovery.*`, `mapper.*`; missing keys fall back to script defaults |
| `boundary.json` | JSON | discovery (triage appends) | Product, rings, head terms, templates, modifiers, adjacent/out terms, inventory, competitors; `version` increments on every triage |
| `discovery/state.json` | JSON | discovery | Current `run` number |
| `discovery/seeds.jsonl` | mutable JSONL | discovery | One row per seed |
| `discovery/observations.jsonl` | append-only JSONL | discovery | The pool |
| `discovery/concepts.jsonl` | mutable JSONL | discovery | Triage candidates and decisions |
| `discovery/runs.jsonl` | append-only JSONL | discovery | suggest/import/triage/round log |
| `discovery/cache/` | local | discovery | Suggest responses (7-day TTL), git-ignored |
| `discovery/raw/` | local | discovery | Verbatim copies of every imported file and sitemap snapshots, git-ignored |
| `work/` | derived | any | Safe to delete |

## observation@1

```json
{
  "schema": "search-demand/observation@1",
  "id": "obs_<sha1(keyword|source|source_ref|country|language|period)[:16]>",
  "keyword": "button click sound mp3",
  "raw": "Button click sound MP3",
  "source": "google_suggest | youtube_suggest | bing_suggest | google_keyword_planner | google_search_console | google_trends | google_serp | bing_webmaster | <name>",
  "kind": "search_suggestion | related_search | historical_volume | trend_related | gsc_impression | onsite_request | external_reference",
  "source_ref": "suggest:google:<query> | file:<sha8>[#ref]",
  "market": {"country": "US", "language": "en"},
  "period": {"start": "2025-08-01", "end": "2026-07-31"},
  "metrics": {"rank": 0},
  "via": {"seed_id": "seed_…", "seed": "button click", "query": "button click sound", "group": "base"},
  "run": 1,
  "observed_at": "2026-09-29T10:00:00Z"
}
```

Metrics by kind:

| Kind | Metrics |
| --- | --- |
| `historical_volume` | `avg_monthly_searches: {low, high}`, `monthly`, `competition`, `bid_low`/`bid_high` |
| `gsc_impression` | `clicks`, `impressions`, `ctr`, `position`, `page_filter` |
| `trend_related` | `section` (top/rising), `value` |

The same id is never written twice. A revised export gets a new file hash and therefore new
observations; readers take the latest period per source.

## seed@1

`{id, text, aliases[], origin, ring, depth, parent_seed_id, evidence[], note, status, expanded{engine: [groups]}, gated{engine: {group, reason: thin_base|early_stop, ...}}, stats{engine: {requests, suggestions, new_keywords, modifier_queries, modifier_new}}, added_run, added_at}`

- `origin`: gsc | onsite | inventory | reviewed_concept | topdown | taxonomy | user
- `status`: pending | active | exhausted | rejected | deferred | parked. `parked` seeds are known,
  so extraction does not propose them again, but they are never expanded.
- `aliases` count as the seed during concept extraction and mapper grouping. `aliases_confirmed`
  are aliases a reviewer kept on purpose; they leave later alias reports.
- `discovery/seed-review-decisions.jsonl` is append-only: every `seed apply-review` decision
  (`names`, `action`, `text`/`target`, `reason`), keyed by `review_hash`.

## seed-candidates@1 (input to `consolidate`)

`{groups: [{id, name, items, aliases[], origin}], names: [{text, groups[], origin}], leaves: [{text, group}]}`

`consolidate` writes `work/consolidation.json`: `needs_probe` while probes are missing, then
`status: complete`. After that it writes `work/seed-review.json`, where each row has `name`,
`kind` (group|parent|free), `probe` (distinct suggestions per engine), `items`, `aliases`,
`children`, `signal_leaves` and `collapsed_leaves`. Rows are split into `review` (signal) and
`no_signal`. Probe observations are normal `search_suggestion` observations with
`via.group = "probe"`.

## concept@1

`{key, text, kind, status, count, examples[], evidence[], parent_seed_ids[], origins[], first_run, decided_run, reason, axis}`

- `kind`: phrase | term | hypothesis
- `status`: pending | seed | modifier | head_term | adjacent | out | noise | subsumed | stale.
  `stale` means a later extraction no longer produces it (an alias or boundary edit covered its
  keywords); it returns to `pending` if it reappears.

## Triage input and output

`concepts` writes `work/triage-input.json`, which lists items with their examples and variants.
The triage file answers every item it decides:

```json
{"decisions": [
  {"text": "mouse click", "decision": "seed", "reason": "different sound source and result set"},
  {"text": "discord", "decision": "modifier", "axis": "context", "reason": "platform context, same sounds"},
  {"text": "id roblox", "decision": "out", "reason": "platform ID lookup, not an asset download"}
],
 "boundary": [
  {"op": "add", "field": "modifier", "axis": "license", "term": "free to use", "reason": "license request"},
  {"op": "remove", "field": "adjacent", "term": "text", "reason": "'text message sound' is in scope"}
]}
```

- Deciding an already decided concept again is a revision: its old boundary entry (modifier,
  head term, adjacent or out term) is withdrawn first. A `seed` concept is retired with
  `seed reject --text` instead.
- `boundary` ops edit phrases directly: a phrase narrower or wider than any concept ("how to
  use" instead of "use"), or a term set during bootstrap. `field` is modifier (with `axis`),
  head_term, adjacent or out. An added phrase must occur in at least one observed keyword.

## Alias review (`seed aliases`)

Without `--file` it reports every unconfirmed alias that other seeds' searches also produced
(`--alias-spread`, default 5) or that sits inside another seed's name, with foreign samples. The
decisions file is `{"decisions": [{"seed", "drop": [], "confirm": [], "reason"}]}`; it is logged
to `runs.jsonl` as `alias_review`.
