# JSON output for sites that are not site-kit

`geo_engine.py build` picks the target from `--target`, then `project.json.output.target`, then
`kit` when `.sitekit.json` exists, otherwise `json`. The JSON target writes to `--out`,
`project.json.output.dir`, or `geo/out/`:

| File | Holds |
| --- | --- |
| `<template>.json` | one template: collection settings, groups and the released items |
| `index.json` | every template: file, basePath, released item count, pending count |
| `urls.txt` | released item URLs, one per line, for the site's sitemap |

## `<template>.json`

```json
{
  "template": "convert", "version": 1, "generated": "2026-11-17",
  "collection": {"basePath": "/convert", "label": {"singular": "Conversion", "plural": "Conversions"},
                 "hub": {"title": "...", "description": "..."}, "itemType": "Thing",
                 "groups": {"basePath": "/convert/from", "label": "Source", "minItems": 3}},
  "groups": [{"key": "heic", "name": "HEIC", "count": 12, "url": "/convert/from/heic", "indexable": true,
              "content": {"answer": "...", "chooser": [{"when": "...", "why": "...", "slug": "heic-to-jpg", "name": "...", "url": "/convert/heic-to-jpg"}],
                          "follow_ups": [{"q": "...", "a": "..."}]}}],
  "items": [{
    "slug": "heic-to-jpg", "url": "/convert/heic-to-jpg", "combo_id": "heic__jpg",
    "name": "HEIC to JPG", "title": "...", "h1": "...", "description": "...",
    "answer": "inline markdown, the answer-first paragraph",
    "facts": [{"label": "No upload", "value": "Yes — files stay on your device"}],
    "group": {"key": "heic", "name": "HEIC"}, "related": ["webp-to-jpg"],
    "follow_ups": [{"q": "...", "a": "..."}], "resource": {"label": "...", "url": "/tools/heic-to-jpg"},
    "alternatives": [{"name": "...", "note": "..."}], "updated": "2026-11-17", "arm": "a"
  }],
  "pending": 40
}
```

- `items` holds released pages only; `pending` counts gated rows waiting for a wave. Build every item,
  nothing else from this file.
- `related` lists only released slugs, so links never point at unbuilt pages.
- `title` is the raw title: apply the site's own title template.

## What the page must render

Render in this order, all in the server HTML (no client-only content):

1. `h1`, then `answer` as the first paragraph (inline markdown).
2. `resource` as a visible link or button when present.
3. `facts` as a two-column table.
4. `follow_ups` as visible questions and answers, plus a `FAQPage` JSON-LD with the same text.
5. `alternatives` as a list when present.
6. `related` as links to `<basePath>/<slug>`.

Section headings for the chooser and alternatives are in `collection.labels` (the template's `labels`,
English defaults otherwise).

Group pages: `content.answer` under the H1, then `content.chooser` as a two-column table (condition →
link), then the item list, then `content.follow_ups` as visible Q&A with a FAQPage JSON-LD. Groups
without `content` are plain lists.

Page meta: `<title>` from `title`, meta description from `description`, a self canonical, indexable.
Hub at `collection.basePath` listing items; group pages at `groups[].url`, `noindex` when `indexable`
is false. Add `urls.txt` and the hub and indexable group URLs to the sitemap, one sitemap per template
when the stack allows it, so indexing can be read per template. Rebuild and redeploy after every
`build`; a page whose row left `items` should return 410 or redirect to its group page.
