# geo/ state contract

One folder, `<project>/geo/`, carries a new GEO project from idea to pages. Every skill of the batch flow (site-idea, site-batch) reads it
first, checks the preconditions of its stage, writes only the files it owns, and names the next step.
Chaining is through these files, not through conversation memory.

Schema version: 1 (`project.json.schema`). All files below are implemented: site-idea
(`geo_idea.py`), site-batch (`site-batch/scripts/geo_engine.py`). Fields added on 2026-11-17 (demand
map, question bank, presence, assets, deploy dates) are optional, so earlier folders stay valid.

Both engines take `--geo-dir <folder>` (default `geo`) when one repository holds several GEO projects,
for example `geo/` for a new page space and `geo-families/` for a retrofit; every path below is then
under that folder.

## Where the folder lives

- Idea stage: any project folder, e.g. `~/Projects/<name>/geo/`.
- When the site is created: `sitekit new` needs an empty directory, so create the site in a new
  directory and move the folder in (`mv ~/Projects/<name>/geo <site>/geo`), then commit it with the
  site. From then on `<project>` is the site root.

## Files and owners

| File | Owner | Status | Holds |
| --- | --- | --- | --- |
| `project.json` | all (each writes its own fields) | implemented | idea, audience, market, platforms, north star, stage, decision, log |
| `needs.jsonl`, `needs.md` | site-idea | implemented | demand map: needs, personas, pains, where asked, evidence ([demand-map.md](demand-map.md)) |
| `questions.jsonl`, `bank.md` | site-idea | implemented | question bank: questions per need and angle with evidence level ([question-bank.md](question-bank.md)) |
| `competitors.jsonl` | site-idea | implemented | competitors for reverse-engineered questions ([competitor-probes.md](competitor-probes.md)) |
| `dimensions.json` | site-idea | implemented | task-space dimensions, values, `changes_answer`, excludes |
| `gap/samples.jsonl` | site-idea | implemented | sampled combinations with conversation paths and outside signals |
| `gap/raw/*.md` | site-idea (user pastes) | implemented | full AI answers, one file per run |
| `gap/runs.jsonl` | site-idea | implemented | one row per AI run with the gap judgement |
| `gap/probes.md`, `gap/report.json`, `gap/report.md` | site-idea (generated) | implemented | probe sheet and gap report |
| `gap/channels.md` | site-idea (written with the owner) | convention | need × channel table: evidence or "not measured", who wins, whether we appear, what only we have, lever (pages, off-site, product and docs, not now) |
| `goal.md` | site (written with the owner) | convention | goal card: goal, north star, needs and audiences served, channels, levers, not doing, current state, constraints |
| `facts.jsonl` | site-batch | implemented | product facts with source and checked date |
| `assets/` | site-batch | implemented | test outputs and data the facts cite |
| `templates/<id>.json` | site-batch | implemented | template spec = one site-kit directory collection |
| `combos/<template>.jsonl` | site-batch | implemented | one row per combination: the page's answer data (the engine never writes it) |
| `combos/<template>.groups.jsonl` | site-batch | implemented | group page content: answer, chooser to item pages, group follow-ups |
| `instances.jsonl` | geo_engine.py build (generated) | implemented | per row: template, combo, URL, gate result, unique ratio, wave, released, arm |
| `waves.json` | geo_engine.py wave-plan / wave-release | implemented | waves, dates, which combinations each holds |
| `measure/snapshots.jsonl` | site-batch | implemented | crawl, index, AI fetch, citation and referral snapshots by URL and date |
| `<site>/data/<template>.jsonl` | geo_engine.py build, kit target (generated) | implemented | kit collection data: gated rows rendered for the page |
| `snapshots/<template>/` (`<date>/*.html`, `index.jsonl`) | geo_engine.py snapshot | implemented | adopt templates: live HTML of existing pages before a retrofit |
| `<site>/data/<template>.groups.json` | geo_engine.py build, kit target (generated) | implemented | group content read by the group page override |
| `out/` (`<template>.json`, `index.json`, `urls.txt`) | geo_engine.py build, json target (generated) | implemented | released pages for sites that are not site-kit (site-batch `references/json-output.md`) |
| `out/preview/<template>.json` | geo_engine.py build --preview (generated) | implemented | one row rendered as if released, for template approval; delete after |

## Stages

`project.json.stage` moves forward only: `idea` → `needs` → `space` → `gap` → `decided` → `blueprint` → `pages`.

| Stage | Set by | Precondition for the next skill |
| --- | --- | --- |
| `idea` | `geo_idea.py init` | — |
| `needs` | `needs` with no errors and a validated need | demand map agreed with the owner |
| `space` | `space` with no errors | dimensions valid |
| `gap` | `report` with at least one judged run | gap report exists |
| `decided` | `decide --by user` (or `--without-probes` on validated needs) | verdict `go` or `narrow` lets site-batch start; `stop` ends the project |
| `blueprint` | `geo_engine.py build` with at least one gated row | templates approved, rows for the seed wave gated |
| `pages` | `geo_engine.py wave-release` | first wave released |

## project.json

```json
{
  "schema": 1,
  "name": "Convert",
  "idea": "Tell people how to convert one file format to another under their constraints, and do it in the browser.",
  "audience": ["people with photos from an iPhone", "office workers"],
  "market": {"countries": ["US"], "languages": ["en"]},
  "platforms": ["ChatGPT", "Perplexity", "Google AI Mode"],
  "probe_platforms": ["ChatGPT"],
  "north_star": "AI-referred visits that finish a conversion",
  "site": {"live": false, "origin": ""},
  "brands": ["file convert"],
  "allowed_names": ["iPhone", "Windows"],
  "output": {"target": "kit", "dir": "geo/out"},
  "stage": "decided",
  "decision": {"verdict": "narrow", "date": "2026-11-20", "by": "user",
               "subspace": {"source": ["heic", "webp"]}, "note": "",
               "evidence": {"probed": 40, "share_high": 0.28, "hint": "narrow",
                            "in_answer_share": 0.1, "lever_hint": "offsite"}},
  "log": [{"date": "2026-11-17", "stage": "idea", "note": "initialised"}]
}
```

`brands` (optional): other spellings of our name that probe questions must not carry; the project
name and the site domain's name part count already. `allowed_names` (optional): platforms or
products whose name changes the answer (Steam, YouTube, Godot, itch.io), so the brand check lets them
through.

`platforms` are the target platforms and may be free text. `probe_platforms` (optional) are the ones
probed this round; `probes` uses it, else `platforms`, and turns each name into a safe file-name slug.

## dimensions.json

```json
{
  "dimensions": [
    {"id": "source", "kind": "entity", "label": "Source format", "changes_answer": true,
     "why": "conversion method, loss and tool support differ by format",
     "source": "formats the converter supports",
     "values": [{"id": "heic", "label": "HEIC"}, {"id": "png", "label": "PNG"}]},
    {"id": "need", "kind": "constraint", "label": "Constraint", "changes_answer": true,
     "why": "batch and offline rule out different tools",
     "source": "recurring constraints in forum threads",
     "values": [{"id": "batch", "label": "many files at once"}, {"id": "offline", "label": "no upload"}]},
    {"id": "persona", "kind": "entity", "label": "Who asks", "changes_answer": false,
     "source": "audience", "values": [{"id": "student", "label": "student"}]}
  ],
  "exclude": [
    {"same": ["source", "target"], "why": "converting a format to itself"},
    {"when": {"source": "pdf", "need": "offline"}, "why": "not supported by the product"}
  ]
}
```

- `kind`: `entity` (object, format, product, place), `task` (what is done), `constraint` (condition).
- `changes_answer: true` makes the dimension generate pages and requires `why`. A dimension that does
  not change the answer is kept for wording only (`described_only` in `space`).
- Value ids are slugs without `__` (the combination id joins them with `__` in dimension order).
- `exclude`: `same` drops combinations where two dimensions share a value id; `when` drops
  combinations matching every listed dimension (a value or a list of values).

## gap/samples.jsonl

```json
{"combo_id": "heic__jpg__batch", "combo": {"source": "heic", "target": "jpg", "need": "batch"},
 "persona": "parent with 400 iPhone photos for a school yearbook",
 "opening": "I have about 400 photos from my iPhone and the yearbook site only takes JPG...",
 "opening_scope": ["source", "target"],
 "follow_ups": [{"q": "Can I do it without uploading them anywhere?", "kind": "constraint", "adds": ["need"]},
                {"q": "Will I lose quality?", "kind": "why", "adds": []}],
 "signals": [{"url": "https://www.reddit.com/r/...", "quote": "is there any way to batch convert heic", "date": "2026-10-02"}]}
```

`signals` are evidence that people ask this: off-site (real URL, short quote, date) or first-party
(`source`, `ref`, `q` or `quote`, `n`), as in [demand-map.md](demand-map.md). Empty when none was found.
Older samples may carry first-party rows as `site_signals`.

`sample --from-questions` fills `signals` from the question's `evidence`: a `<need_id>#e<N>` reference
copies that evidence row from `needs.jsonl`; a URL or search-log string becomes `{"ref": "<string>"}`.

Samples from the question bank also carry `question_id`, `need_id`, `angle`, `conditions` and
`evidence_level`, and use the question id as `combo_id`; samples from a pool carry `url` and `stratum`.
The report groups results by each of these when present.

## gap/runs.jsonl

```json
{"combo_id": "heic__jpg__batch", "platform": "ChatGPT", "model": "as shown in the app", "mode": "manual",
 "date": "2026-11-18", "run": 1, "web_search": true, "raw": "geo/gap/raw/heic__jpg__batch--chatgpt--1.md",
 "cited": [{"url": "https://...", "type": "forum"}], "recommended": ["Tool A", "Tool B"],
 "own": "absent", "cited_own": false, "own_urls": [],
 "search_queries": ["batch convert heic to jpg without upload"], "outcome": null,
 "gap": "unmet_constraint", "gap_note": "both tools upload files; user asked for no upload",
 "judged_by": "model"}
```

- `slice`: optional string naming the model slice of the run, e.g. `chatgpt-instant`; `report --where
  slice=chatgpt-instant` reads only those runs. Any run field works with `--where KEY=VALUE`.
- Extra run sets: optional `gap/runs-*.jsonl` files (e.g. `runs-captured.jsonl`, search queries
  captured apart from the answers) use the same fields. `check` validates them; `report` lists them in
  their own section and adds them to the main numbers only with `--include-extra`.
- `mode`: `manual` (the user ran it and pasted), `browser` (driven in the user's logged-in browser with
  their go-ahead), `api`.
- `gap`: one of `generic`, `outdated`, `unmet_constraint`, `no_resource` (high opportunity),
  `weak_sources`, `self_made` (medium), `good` (low), or `null` before judging. Rubric: [gap-rubric.md](gap-rubric.md).
- `own`: `absent`, `mentioned`, `listed`, `first`, `excluded`, or `null` when not judged.
  `search_queries`: list, or `null` when not captured. `outcome`: competitor probes only
  ([competitor-probes.md](competitor-probes.md)): `competitor_page`, `constraint_unmet`, `lists_forums`,
  `no_search`, `own_recommended`, `generic_rules`, `other`.
- `cited[].type`: `brand`, `competitor`, `list`, `forum`, `video`, `docs`, `news`, `other`.

## Blueprint and pages files

Full field rules: site-batch `references/templates.md` (templates) and `references/combos.md`
(facts and rows); site-batch `references/measure.md` (snapshots).

### waves.json

```json
{"waves": [{"id": 1, "status": "released", "planned": "2026-11-20", "released": "2026-11-24",
            "deployed": "2026-11-25",
            "combos": {"convert": ["heic__jpg__batch", "heic__png__offline"]}, "note": "seed; expand convert next"}]}
```

A combination belongs to at most one wave. Only one wave is `planned` at a time. `released` is the day
the wave was marked in the data; `deployed` is the day the pages went live (`wave-deployed`), and
windows count from it. With `wave-plan --control-ratio`, a wave also lists `"control": {"<template>":
[combo ids]}`: rows held back for the review, one of each priority pair chosen by hash; later waves
skip them unless `--include-control`.

### data/<template>.jsonl (generated, read by the kit collection module)

```json
{"slug": "heic-to-jpg-batch", "name": "HEIC to JPG", "title": "...", "h1": "...", "description": "...",
 "combo_id": "heic__jpg__batch", "answer": "...", "facts": [{"label": "No upload", "value": "Yes — ..."}],
 "group": {"key": "heic", "name": "HEIC"}, "related": ["webp-to-jpg-batch"], "updated": "2026-11-17",
 "released": true, "arm": "a", "follow_ups": [{"q": "...", "a": "..."}],
 "resource": {"label": "...", "url": "/tools/heic-to-jpg"}, "alternatives": []}
```

Only rows that pass the gate are written; `released` decides whether the kit builds them.

### Mapping to a site-kit directory site

| geo | site-kit |
| --- | --- |
| template | `directory.collections[]` entry + `src/site/collections/<id>.ts` (wording functions, written once) |
| `combos/<template>.jsonl` | `data/<id>.jsonl` (`geo_engine.py build` writes it; the scaffolded module reads it) |
| `core_answer` | `answer()` |
| `constraint_results`, key data | `facts()` |
| hub / group dimension | `groups` + `group()` + `groupIntro()` |
| resource, follow-ups, alternatives | `src/site/overrides/templates/DirectoryItem.astro` (scaffolded): resource button, visible FAQ + FAQPage, alternatives |
| quality gate and wave release | failing rows are never written to `data/`; `gate()` returns `indexable: released`, and with `ungated: 'omit'` unreleased rows are not built at all |
| per-template sitemap and index watch | the kit's page index; one collection per template keeps them separable |
| SEO registry | `seo.registry.mode` stays `advisory` on geo sites: the geo state is the record for generated pages; site-plan's registry covers the hand-made pages |
