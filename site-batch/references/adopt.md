# Adopt mode: retrofitting a family of existing pages

For a site that already has many pages of one kind (sound family pages, product pages, place pages)
and wants them GEO-ready without rebuilding them one by one. The family becomes an **adopt template**:
each existing page is one row, keeps its URL, and gets its answer-first paragraph, conditions,
question slots and resource from data, through the same gate as generated pages. Nothing new is
created; pages are retrofitted in waves with a control group.

## Template

```json
{"id": "families", "adopt": true, "task": "find {event} sounds for a {genre} game",
 "dimensions": ["event", "genre"],
 "patterns": {"title": "{event.label} sound effects for {genre.label} games: {headline}"},
 "title_source": "item openings c004, c018 and site search misses 'coin sound platformer'",
 "question_slots": [{"id": "commercial", "question": "Can I use them in a commercial game?", "kind": "constraint"}],
 "required": ["core_answer", "constraint_results", "resource"], "labels": {"alternatives": "Other options"},
 "min_unique_ratio": 0.5, "approved": null, "version": 1}
```

- `adopt: true`; `collection` and the item patterns are optional. A pattern, or the row's own
  `title`, `h1`, `description`, `name`, is used only when the page should change that field; empty means
  keep the page's current one. Check every title change against search data first (site-geo
  `references/retrofit.md`, "Keep what search already earns").
- Groups are not generated: the site keeps its own category pages (retrofit them as single pages).

## Rows

Same fields as generated rows (references/combos.md), plus `"url": "/sounds/coin-platformer"`, the
existing path. Rows usually start from the site's own data (database, catalog, sitemap): map each
existing URL to its combination, then fill answers from facts and assets. Duplicate URLs or rows
without a URL fail the gate.

## Flow

1. Map the family: URL → combination, one row each (`combo_id`, `combo`, `url`).
2. Before anything ships: `snapshot --template <id> --base https://<site>` saves each page's live HTML
   with title, H1, word count and hash under `geo/snapshots/<id>/<date>/`, indexed in
   `geo/snapshots/<id>/index.jsonl`. It is the before state and the rollback reference. Record the GSC
   baseline for the family too.
3. Questions, slots, facts and rows as in the blueprint, then `lint` and `status`.
4. Plan with a control group: `wave-plan --per-template <n> --control-ratio 0.5`. Rows are taken in
   priority order and every second one is held back, so both groups look alike. Held-back rows keep
   their current page until the review; later waves skip them unless `--include-control`.
5. Release: `wave-release`, `build`. Adopt templates always write plain JSON (`geo/out/<id>.json`,
   released rows only, each with `url`, `related_urls` and the content blocks); the site's own page
   template reads it and renders the blocks for those URLs, as `references/json-output.md` describes.
   On a kit site, the same file is read by the site's own code: kit collections are for generated pages.
6. Review: `funnel` shows each wave and its `control` side by side (crawl, index, AI fetch, citation,
   referrals); site-geo's experiment and the GSC window for both groups decide expand, fix or roll back.
   Rolling back a row: drop it from the released wave (or unrelease the wave), rebuild, redeploy; the
   snapshot shows what the page said before.

## What changes on the page

Only what the template and row carry: answer paragraph, resource, conditions table, slot answers,
alternatives, and the fields the row or patterns set. The page's other content stays. Render the new
blocks near the top (after the H1), in the order of `references/json-output.md`, in the server HTML.
