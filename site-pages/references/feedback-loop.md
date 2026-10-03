# Feedback loop (Search Console)

Launch is the start of measurement. Search Console shows which queries Google actually matches to
each page. That is the evidence for enrich, split, merge and retire.

## Collecting windows

- Export per page: Performance → Search results → Page filter = the page → Queries → Export. Then
  run `gsc import --file <zip> --period START..END`. The page comes from `Filters.csv` or `--page`.
  API or Looker exports with a Page column also work.
- Use equal windows (28 days). Data lags about 3 days, so end each window 3 or more days before
  the export date.
- Before a launch or major change, save a **baseline** window for the affected pages.
- Anonymized queries are missing. Page totals exceed the sum of their query rows, so use each
  page's own total for page-level trends.

## Flags and responses (`gsc review`)

A flag is `confirmed` when present in all of the last `windows_required` (2) windows, `watch`
when present in fewer, and `cooldown` when a page involved was published less than
`cooldown_days` (28) ago. Do not split or merge during cooldown.

| Flag | Condition | Response |
| --- | --- | --- |
| `cannibalization` | One cluster's impressions split across ≥ 2 own pages, each ≥ 20% | Check the mapping first. If the intent really is the same, merge (redirect, canonical, internal links). If the intents differ, sharpen each page's job and interlink with stated reasons |
| `wrong_owner` | The cluster's top page is not its primary | Either the mapping is wrong (change the primary) or the owner page lacks the content. Improve the owner before redirecting |
| `unowned_cluster` | Impressions for a cluster with no primary page | Map it to the page Google already chose, if that page fits |
| `promotion_signal` | An attribute's queries on the parent page ≥ 100 impressions per window | Run the promotion gate (SERP pair and inventory). Otherwise enrich the section or filter |
| `retire_candidates` | Published ≥ 120 days, ≤ 10 impressions in the latest window | Check indexing and content first. If demand is truly absent, redirect to the parent or return 410 |
| `unmapped_queries` | Queries with no included decision | Import `seo/work/unmapped-queries.json` into the pool (discovery, `--format json`), review them, then enrich or map |

**Enrich** is the default response to new member queries: add the sub-need, attribute section,
FAQ or selection guidance to the owner page. It needs no new URL. Regenerate the page's brief
first: with a GSC window imported it shows the page's queries next to the sub-needs, and the
`write_it` rows are the enrich list. Record what the page now covers in `covered_attributes`.

## Hysteresis

Split needs stronger evidence than keeping. Merge needs repeated overlap, not one noisy window.
Never reverse a split or merge within 2 windows of making it unless something is technically
broken.

## Observation schedule

- **First 7 days:** technical checks only (indexing, status codes, canonical, sitemap).
- **First full 28-day window:** impressions, clicks, queries per page.
- **4–8 weeks:** review decisions with enough sample.

A before/after comparison is not an experiment. Keep experiment cohorts intact, and say when
data is insufficient.
