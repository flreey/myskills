# Adopt mode: retrofitting a family of existing pages

For a site that already has many pages of one kind (sound family pages, product pages, place pages)
and wants them GEO-ready without rebuilding them one by one.

## Before choosing it

Adopting changes what a page says once an assistant opens it. It does not make assistants find the
page. Use it when the evidence says the pages are the bottleneck, and write that evidence into the
template's `diagnosis` (lint warns without it):

- site-geo optimize O4–O5 (or a site-idea report with presence) shows these tasks are `onsite`: the
  assistant opens competitor pages, or our page, and the answer fails on content;
- the site is already fetched and cited for some of these pages (AI user-crawler fetches, AI
  referrals), so better content has a reader;
- no other experiment is running on the same pages: list the URLs of running experiments and keep
  them out of the candidate rows (the first run collided with a FAQ experiment on 544 of 716 pages).

When the site is mostly absent from answers that rest on lists, forums or big libraries, adopting
will not move recommendations; plan site-offsite (GEO mode) first, and new pages through site-idea.

Written after the first run (SFXMint, 2026-11-17): 20 family pages were retrofitted on a 40% gap share
while the site appeared in 4 of 25 answers; the expected effect was small from the start. The family becomes an **adopt template**:
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

- `adopt: true`; `collection` and the item patterns are optional (`scaffold` refuses adopt templates:
  the site's own page template reads the JSON). A pattern, or the row's own
  `title`, `h1`, `description`, `name`, is used only when the page should change that field; empty means
  keep the page's current one. Check every title change against search data first (site-geo
  `references/retrofit.md`, "Keep what search already earns").
- Groups are not generated: the site keeps its own category pages (retrofit them as single pages).
- `diagnosis`: one or two lines naming the evidence above and the experiments the rows avoid.
- `shared_text`: sentences every page states on purpose (licence, format), left out of the unique
  ratio so rows need not squeeze them; the ratio then measures what is specific to each page.
- Slots that apply to some rows only take `when` (`{"family": ["rain", "wind"]}` for a loop question).

## Rows

Same fields as generated rows (references/combos.md), plus `"url": "/sounds/coin-platformer"`, the
existing path. Rows usually start from the site's own data (database, catalog, sitemap): map each
existing URL to its combination, then fill answers from facts and assets. Duplicate URLs or rows
without a URL fail the gate.

## Flow

1. Map the family: URL → combination, one row each (`combo_id`, `combo`, `url`). For the gap check, a
   one-dimension family (one value per page) is sampled as a pool by strata (site-idea `sample
   --pool`, strata such as traffic tiers), not by values: per-value results with one run each say
   nothing. Rows may name `related` combinations; a one-dimension template gets no automatic siblings.
2. Before anything ships: `snapshot --template <id> --base https://<site>` saves each page's live HTML
   with title, H1, word count and hash under `geo/snapshots/<id>/<date>/`, indexed in
   `geo/snapshots/<id>/index.jsonl`. It is the before state and the rollback reference. Record the GSC
   baseline for the family too. Each page is indexed as soon as it is saved. If a run is cut off,
   run the same command again that day and it fetches only the missing pages.
3. Questions, slots, facts and rows as in the blueprint, then `lint` and `status`.
4. Plan with a control group: `wave-plan --per-template <n> --control-ratio 0.5`. Rows are paired in
   priority order and a hash picks which of each pair is held back, so neither side gets the higher
   row of every pair. Give rows a `baseline` (e.g. `{"ai_fetch": 30, "ai_landings": 12}` over the last 28
   days): the plan prints both sides' sums; re-plan or move outliers when they differ a lot. Held-back
   rows keep their current page until the review; later waves skip them unless `--include-control`.
   Seasonal pages (holidays) go in neither side, or are excluded at the review.
5. Before approval: `build --preview <template>:<combo>` renders one row as if released into
   `geo/out/preview/`, for a local render of the real page. Release: `wave-release`, `build`, deploy,
   then `wave-deployed --wave <k> --date <day>` and `build`. Adopt templates always write plain JSON (`geo/out/<id>.json`,
   released rows only, each with `url`, `related_urls` and the content blocks); the site's own page
   template reads it and renders the blocks for those URLs, as `references/json-output.md` describes.
   On a kit site, the same file is read by the site's own code: kit collections are for generated pages.
6. Review: `funnel` shows each wave and its `control` side by side (crawl, index, AI fetch, citation,
   referrals); site-geo's experiment and the GSC window for both groups decide expand, fix or roll back.
   Rolling back a row: drop it from the released wave (or unrelease the wave), rebuild, redeploy; the
   snapshot shows what the page said before.

## What changes on the page

Only what the template and row carry: answer paragraph, resource, conditions table, slot answers,
alternatives, and the fields the row or patterns set. The page's other content stays, apart from what
the owner approved removing. Put the answer near the top in the server HTML; the other blocks may sit
where the existing page has room ([json-output.md](json-output.md), "Existing pages"). Numbers the
answer needs a source for but the page should not show as a fact row go into `key_facts` with
`hidden: true`.
