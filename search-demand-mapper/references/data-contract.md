# Data contract (mapper side)

Paths are relative to `<project>/seo/`. The mapper reads `config.json` (`market`, `mapper.*`),
`boundary.json` (`product.url` is required when the registry uses path URLs) and
`discovery/observations.jsonl` (owned by search-demand-discovery). It writes only under `mapper/`
and `work/`.

| File | Kind | Notes |
| --- | --- | --- |
| `mapper/clusters.jsonl` | append-only versions | The current row per `id` is the last one |
| `mapper/decisions.jsonl` | append-only | The current row per `keyword_id` is the last one; actor `model`, `human` or `lineage` |
| `mapper/reviews/<id>/` | per batch | `input.json`, `output.json`, `applied.json` (output sha) |
| `mapper/inventory.json` | written by the agent from project data | `{"as_of", "source", "clusters": {"<cluster_id>": {"items": 38, "attrs": {"style=retro": 4}}}}` |
| `mapper/pages.jsonl` | current registry | Rewritten only by `apply-changes` |
| `mapper/mappings.jsonl` | current registry | Rewritten only by `apply-changes` |
| `mapper/changesets/<id>.json` | append-only history | Each applied change set with `approved_by` and `applied_at` |
| `mapper/evidence/serp.jsonl` | append-only | Captures (normalized top-N URLs, result types, market, date) |
| `mapper/evidence/serp-compare.jsonl` | append-only | Pair overlaps and verdicts |
| `mapper/evidence/gsc/<start>_<end>.jsonl` | per window | Query, page, clicks, impressions, CTR, position; git-ignored |
| `work/analysis.json`, `work/gsc-review.json` | derived | Regenerate at any time |

`keyword_id = "kw_" + sha1(normalized keyword)[:12]`. The keyword's `evidence_hash` is a hash of
its sorted observation ids; a change re-queues the keyword.

## cluster@1

`{id, version, status: active|hold|ignored|retired, label, intent{task, delivery}, entity, page_type, expected_result_set, parent, promoted_attrs{axis: value}, successors[], definition{summary, includes[], excludes[], representative_keywords[], evidence_ids[], neighbor_distinction}, review_id|changeset, updated_at}`

## decision@1

`{keyword_id, keyword, status, cluster_id, cluster_version, language, intent{task, job, delivery: {value, basis, quote?, reason}}, entity, attributes{axis: [values]}, reason, evidence_ids[], evidence_hash, actor, review_id, reason_source, decided_at}`

## page@1

`{url, page_type, status: planned|published|noindex|redirected|gone, indexable, canonical, redirect_to, parent, title, covered_attributes{axis: [values]}, published_at, experiment, notes, created_at, updated_at}`

## mapping@1

`{cluster_id, page, role: primary|secondary|filter, decision: keep|improve_existing|filter|create|defer, conditions{}, reason, changeset, updated_at}`

## Invariants (`validate`)

- A cluster has at most one primary page.
- Mapped pages exist in the registry.
- Filter mappings carry conditions.
- Indexable pages are self-canonical and neither redirected nor gone. Filter pages are indexable
  only when they own a cluster.
- Redirects point to existing pages, with no chains.
- Included decisions point to existing, non-retired clusters. Retired clusters list successors
  that exist.
