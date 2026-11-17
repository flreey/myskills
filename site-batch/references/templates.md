# Template spec (`geo/templates/<id>.json`)

One template = one task type = one site-kit directory collection. 2–5 per project. Two templates
never answer the same task.

```json
{
  "id": "convert",
  "task": "convert {source} to {target} when the user needs {need}",
  "dimensions": ["source", "target", "need"],
  "collection": {
    "basePath": "/convert",
    "label": {"singular": "Conversion", "plural": "Conversions"},
    "hub": {"title": "All file conversions", "h1": "File conversions",
            "description": "Every conversion we cover, with what is kept, what is lost and a tool to do it.",
            "intro": "Pick the format you have."},
    "groups": {"by": "source", "basePath": "/convert/from", "label": "Source format", "minItems": 3,
               "intro": "{count} ways to convert {name} files."},
    "itemType": "Thing",
    "pageSize": 100
  },
  "patterns": {
    "slug": "{source}-to-{target}-{need}",
    "name": "{source.label} to {target.label}",
    "title": "{source.label} to {target.label} ({need.label}): {headline}",
    "h1": "Convert {source.label} to {target.label} — {need.label}",
    "description": "Convert {source.label} to {target.label} {need.label}: what is kept, what is lost, and a free tool that does it in the browser."
  },
  "field_sources": {
    "core_answer": "own conversion tests + format facts",
    "constraint_results": "product capabilities (facts f1-f9)",
    "key_facts": "test runs: size change, metadata kept",
    "resource": "the tool page for this pair",
    "follow_ups": "follow-ups from geo/gap/samples.jsonl and signals"
  },
  "title_source": "item openings c003, c017, c021 and two Reddit threads say 'convert … to JPG without uploading'",
  "labels": {"chooser": "Which one fits", "alternatives": "Other ways to do it"},
  "question_slots": [
    {"id": "keeps-dates", "question": "Will my photos keep their dates?", "kind": "constraint"},
    {"id": "quality", "question": "Will I lose quality?", "kind": "why"}
  ],
  "required": ["core_answer", "constraint_results", "resource"],
  "optional": ["key_facts", "follow_ups", "alternatives"],
  "facts_fields": [],
  "min_unique_ratio": 0.6,
  "allow_numbers": [],
  "experiment": null,
  "approved": null,
  "version": 1
}
```

| Field | Rule |
| --- | --- |
| `adopt` | `true` for a family of existing pages: rows carry `url`, collection and item patterns become optional, output is always JSON. See [adopt.md](adopt.md). |
| `dimensions` | Generating dimensions from `dimensions.json`; the combination of their values is the page. |
| `collection.*` | Goes into `site.config.ts` through `geo_engine.py scaffold`. `itemType` is one of the kit's: `Thing`, `CreativeWork`, `Product`, `Place`, `Dataset`, `SoftwareApplication`, `DefinedTerm`. `groups.by` is one of the template's dimensions; `groups.intro` may use `{count}` and `{name}`. |
| `patterns` | `{dim}` = value id, `{dim.label}` = value label, `{field}` = a row field (e.g. `{headline}`). `slug` must contain every dimension. The rendered description must be 50–155 characters or the row fails. |
| `field_sources` | Where each answer field comes from. A field with no real source is a field the template cannot require. |
| `title_source` | One line: which real openings and signals the title and H1 patterns follow (`questions` lists them). |
| `labels` | Optional headings for the two sections the geo overrides add: `chooser` (group page) and `alternatives` (item page). Write them in the site's language (`{"chooser": "怎么选", "alternatives": "其他做法"}`); the English defaults apply otherwise. The kit's own headings follow its i18n messages. |
| `question_slots` | 5–8 follow-ups every row answers, generalised from the sampled conversations ([question-mapping.md](question-mapping.md) §3). Rows tag answers with `slot`; unanswered required slots fail the gate. |
| `required` | Must include `core_answer`. A row missing any required field never becomes a page. |
| `facts_fields` | Extra row fields shown as fact rows: `[{"label": "Quality loss", "field": "loss_note"}]`. |
| `min_unique_ratio` | Share of a row's 3-word shingles found in no other row of the template. Start at 0.6. |
| `allow_numbers` | Numbers allowed in prose without a fact (step numbers, "1 page"). Keep it short. |
| `experiment` | `{"name": "...", "arms": ["a", "b"]}`: arms are assigned per combination by hash; rows carry `variants.b` with the fields that differ. |
| `approved` | `{"by": "user", "date": "YYYY-MM-DD"}` once the owner approved this spec and one rendered example. |
| `version` | Bump when patterns or required fields change; scaffold writes it into the module header. |

## From the gap report to required fields

The gaps the assistants left are what the page must fill:

| Dominant gap in `geo/gap/report.md` | Make required |
| --- | --- |
| `no_resource` | `resource` (a tool, file, dataset or exact steps for this combination) |
| `unmet_constraint` | `constraint_results` covering the constraints people state, including `unmet` |
| `generic` | `key_facts` specific to the combination (measured, computed or looked up) |
| `outdated` | facts with a recent `checked` date; `updated` on every row |
| `weak_sources` | facts with first-hand sources (own tests, official docs) |

## Kit page layout (what the template feeds)

Which page a question lands on (item, group, hub) and which section each turn fills:
[question-mapping.md](question-mapping.md).

The geo override of the kit's item page shows, top to bottom: eyebrow (group), h1, the answer
paragraph (`core_answer`, inline markdown), the resource button, the details table (constraint
results, key facts, `facts_fields`), the follow-up questions (visible FAQ + FAQPage), alternatives
and related pages (siblings that differ in one dimension, then group neighbours). Write fields for
that order: the answer must stand alone, because it is what assistants quote.

The geo group page (override `DirectoryGroup.astro`) shows the group intro, the group answer, a "Which
one fits" chooser to item pages, the item list and the group's FAQ, from
`geo/combos/<template>.groups.jsonl` (format in question-mapping.md §5).
