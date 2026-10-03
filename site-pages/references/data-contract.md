# Data contract (mapper side)

Paths are relative to `<project>/seo/`. The mapper reads `config.json` (`market`, `mapper.*`),
`boundary.json` (`product.url` is required when the registry uses path URLs) and
`discovery/observations.jsonl` (owned by site-keywords). It writes only under `mapper/`
and `work/`.

| File | Kind | Notes |
| --- | --- | --- |
| `mapper/clusters.jsonl` | append-only versions | The current row per `id` is the last one |
| `mapper/decisions.jsonl` | append-only | The current row per `keyword_id` is the last one; actor `model`, `human` or `lineage` |
| `mapper/reviews/<id>/` | per batch | `input.json`, `output.json`, `applied.json` (output sha) |
| `mapper/inventory.json` | written by the agent from project data | `{"as_of", "source", "clusters": {"<cluster_id>": {"items": 38, "attrs": {"style=retro": 4}}}}`. On tool pages an attr counts the modes that do it; 0 records "does not do it", a missing key means "not counted" |
| `mapper/pages.jsonl` | current registry | Rewritten only by `apply-changes` |
| `mapper/mappings.jsonl` | current registry | Rewritten only by `apply-changes` |
| `mapper/changesets/<id>.json` | append-only history | Each applied change set with `approved_by` and `applied_at` |
| `mapper/site-urls.json` | snapshot | Written by `sync-check`: `{source, captured_at, host, urls[], lastmod{url: date}, titles{url: title}}`; `analyze` and `validate` compare the registry with it |
| `mapper/evidence/serp.jsonl` | append-only | Captures (normalized top-N URLs, result types, market, date, `served_host`, `localized`) |
| `mapper/evidence/serp-compare.jsonl` | append-only | Pair overlaps and verdicts |
| `mapper/evidence/gsc/<start>_<end>.jsonl` | per window | Query, page, clicks, impressions, CTR (percent), position; git-ignored. The only GSC store once a registry exists; `analyze`, `brief` and `gsc review` read the latest window(s) |
| `work/analysis.json`, `work/gsc-review.json`, `work/sync-check.json` | derived | Regenerate at any time. `analysis.json` carries `registry_coverage`; `sync-check.json` carries `drift` |
| `work/briefs/<slug>.json` | derived | `brief@1`, one per page (`home` for `/`) |
| `work/unmapped-queries.json` | derived | Written by `gsc review`: `{observations: [{keyword, kind: gsc_impression, source, market, period, metrics{impressions}}]}`, the shape `discovery.py import --format json` reads |
| `work/sync-refresh.json` | draft change set | Title snapshots from the built site; fill `approved_by` before applying. Each `sync-check` rewrites or removes it |

Every derived file carries `inputs`: `{latest_changeset, registry (hash of pages + mappings),
clusters, decisions (line counts), pool (bytes), inventory {as_of, sha}, gsc_windows[], serp}`.
`status` compares it with the current state: `analysis.json` and briefs depend on all of it,
`gsc-review.json` on registry, decisions and GSC windows, `sync-check.json` on the registry.

`keyword_id = "kw_" + sha1(normalized keyword)[:12]`. The keyword's `evidence_hash` is a hash of
its sorted observation ids; a change re-queues the keyword.

## cluster@1

`{id, version, status: active|hold|ignored|retired, label, intent{task, delivery}, entity, page_type, expected_result_set, parent, promoted_attrs{axis: value}, successors[], definition{summary, includes[], excludes[], representative_keywords[], evidence_ids[], neighbor_distinction}, review_id|changeset, updated_at}`

## decision@1

`{keyword_id, keyword, status, cluster_id, cluster_version, language, intent{task, job, delivery: {value, basis, quote?, reason}}, entity, attributes{axis: [values]}, reason, evidence_ids[], evidence_hash, actor, review_id, group_id, seed, reason_source, decided_at}`

`group_id` is set when a group decision produced the row; `seed` is the discovery seed the
keyword was grouped under. The mapper also reads `discovery/seeds.jsonl` (`text`, `aliases`,
`status`) to form review groups.

## page@1

`{url, page_type, status: planned|published|noindex|redirected|gone, indexable, canonical, redirect_to, parent, title, covered_attributes{axis: [values]}, published_at, experiment, notes, created_at, updated_at}`

Page types come from `mapper.page_types` in `config.json`. Defaults: `resource` (min 8 items),
`collection` (3), `tool` (1), `article` (0), `filter` (3), and two types that need no cluster:
`asset` (a one-item detail page) and `info` (about, legal, docs). A type with
`needs_cluster: false` is not asked to own a cluster by `validate`.

`title` is a snapshot of what the built site renders (`sync-check --pages` reports drift).
`covered_attributes` is the record of which sub-needs the page states today, in the same
`axis: [values]` form as decision attributes; `brief` reads it.

## brief@1

`{page, page_type, page_status, generated_at, inputs, covered_attributes, clusters[{cluster_id, role, decision, label, entity, intent, page_type, expected_result_set, summary, excludes[], neighbor_distinction, members, phrasings[{keyword, planner_high}], subneeds[{attribute, status, members, planner_high, gsc_impressions, examples[], inventory, inventory_need, covered}], competitors[{name, members, examples[]}], questions[], neighbors[{cluster_id, label, primary_page, named_in_definition, serp[{a, b, shared, verdict}]}]}], gsc{window, queries[{query, impressions, clicks, position, cluster_id, owned_here}]}|null, statuses{}, notes[]}`

`status` is one of `covered`, `write_it`, `feature_candidate`, `unbacked_claim`, `unknown`.
`planner_high` is the largest Planner upper bound among the members; it is never summed.

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

Warnings (not errors): indexable pages that own no cluster (unless their type has
`needs_cluster: false`), live URLs missing from the registry, published indexable registry pages
missing from the live snapshot, and no snapshot at all ("completeness unknown").
