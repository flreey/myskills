# Facts and combination rows

## `geo/facts.jsonl`

```json
{"id": "f1", "value": "The converter handles up to 500 files per batch in the browser.", "source": "/docs/limits", "checked": "2026-11-17", "scope": "all"}
{"id": "f7", "value": "HEIC to JPG at quality 92: median size 1.8 MB from 2.4 MB over 50 test photos.", "source": "geo/assets/heic-jpg-test.csv", "checked": "2026-11-16", "scope": "source=heic"}
```

- `value` is one checkable statement with its numbers and units.
- `source` is where it can be re-checked: a page that was opened, a file in the repo, a test output
  under `geo/assets/`, product code. Never the model's memory, never a search snippet.
- `scope` says what the fact is about: `all` (every page), `<dim>=<value>[,<value>]` (one dimension's
  values, e.g. `source=vhs`: it belongs to that value's parent page too), several dimensions joined
  by `;` (`source=vhs;goal=instagram`: only this combination), or `combo=<combo_id>`. Free text is
  allowed but never marks a fact as belonging to a parent page. The own-evidence gate
  (templates.md `min_own_evidence`) reads it.
- `checked` is the date it was last confirmed. A fact that changes (price, limit, version) is
  re-checked before every wave.
- Facts about competitors or alternatives follow the same rule and are phrased neutrally.

## `geo/combos/<template>.jsonl`

One row per combination in the decided subspace that has assets. Rows without the assets are left
out, not filled with guesses.

```json
{"combo_id": "heic__jpg__batch", "combo": {"source": "heic", "target": "jpg", "need": "batch"},
 "headline": "batch convert, dates kept",
 "core_answer": "HEIC photos convert to JPG in the browser, up to 500 at a time, without uploading them; at quality 92 a photo goes from about 2.4 MB to 1.8 MB and keeps its EXIF date.",
 "constraint_results": [
   {"constraint": "No upload", "status": "met", "note": "files are converted on your device", "slot": "offline"},
   {"constraint": "Keeps photo dates", "status": "met", "note": "EXIF date and orientation are kept", "slot": "keeps-dates"},
   {"constraint": "Keeps Live Photo motion", "status": "unmet", "note": "only the still image is converted"}],
 "key_facts": [{"label": "Typical size", "value": "2.4 MB → 1.8 MB", "fact_id": "f7"}],
 "follow_ups": [{"slot": "quality", "q": "Will I lose quality?", "a": "At quality 92 the difference is hard to see; size drops about a quarter."}],
 "resource": {"label": "Convert HEIC to JPG", "url": "/tools/heic-to-jpg"},
 "alternatives": [{"name": "Photos app export", "note": "works on a Mac one album at a time"}],
 "fact_ids": ["f1", "f7"], "priority": 3, "updated": "2026-11-17"}
```

| Field | Rule |
| --- | --- |
| `combo_id`, `combo` | Value ids joined with `__` in the template's dimension order. |
| `core_answer` | The first paragraph: yes/no or how, the key number, the main limit. One to three sentences, inline markdown, stands alone. |
| `constraint_results` | `status` is `met`, `conditional` or `unmet`; `conditional` names the mode or device that meets it (the assistant's `pick` turn checks exactly this). `unknown` fails the gate: find out or drop the constraint. A row may carry `slot` to answer a `constraint` question slot here instead of in the FAQ. |
| `key_facts` | Each has `fact_id` (from facts.jsonl) or `source` (e.g. `"computed from test run 12"`). |
| `follow_ups` | One entry per required question slot (`slot`), plus row-specific questions without a slot. Answers are specific to the combination and follow the same fact rule. |
| `resource` | `url` is a site path or URL that exists when the wave ships (kit:check reports broken links). |
| `fact_ids` | Every fact the prose relies on. Numbers in prose that appear in no cited fact or key fact fail the gate. |
| `key_facts[].hidden` | `true` sources a number in the prose (a count, a named file's length) without showing it as a fact row. |
| `assets` | What the answer needs that may not exist yet: `[{"id": "a1", "kind": "sound", "status": "to_generate", "brief": "metal footsteps running up stairs, 4–8 takes"}]`. `status`: `ready`, `to_generate`, `to_collect`, `missing`. Any status other than `ready` fails the gate; `geo_engine.py assets` lists the queue by priority. |
| `demand` | Who asks for this page: a list of `{"need_ref": "<need_id>#e<N>"}` (an evidence row of needs.jsonl), `{"query": "<cluster id or key>"}` (gap/queries.jsonl; a find cluster with `rank.winners_kind: dedicated` also passes the dedicated-winner gate), `{"source", "ref", "q" or "n"}` (first-party record) or `{"url", "quote"}` (off-site). `baseline` numbers on search, landing, fetch, referral, download or play keys above 0 also count. |
| `related` | Optional list of combo ids to link instead of the automatic siblings (one-dimension templates have none). |
| `baseline` | Optional numbers for the control split, e.g. `{"ai_fetch": 30, "ai_landings": 12}` over the last 28 days; `wave-plan --control-ratio` sums them per side. |
| `priority` | Higher ships in an earlier wave. Start from the gap level of the nearest sampled combination. |
| `variants` | Only with a template experiment: `{"b": {"core_answer": "..."}}` replaces those fields for arm b. |

## `geo/combos/<template>.groups.jsonl`

Group pages for templates with `collection.groups`: answer, chooser and follow-ups per group value.
Format and rules: [question-mapping.md](question-mapping.md) §5. Failures show in `build` as
`group_failures`; a failing group renders without the extra content.

## Rows from demand, assets made to order

When the product can make the asset (generate a sound, run a conversion, take a measurement), the
long tail grows from demand instead of from a word list:

1. Take needs and values with evidence: site and agent searches, zero results, "not found" messages,
   the question bank (site-idea `geo/needs.jsonl`, `geo/questions.jsonl`).
2. For each combination an existing page cannot answer, write the row with `assets` marked
   `to_generate` and a `brief` in the person's words.
3. Make the assets through the product's own pipeline, within the owner's budget and approvals
   (generation can cost money), store them, cite them, and set `ready`.
4. The row passes the gate only then, and still needs its own answer and facts.

## Writing rows at scale

- Compute what can be computed (run the tool, measure, query the dataset) and store the outputs
  under `geo/assets/`; cite them as facts.
- The model writes sentences around the data. It may not add numbers, claims, tools or prices that
  are not in the facts. When the data for a field is missing, the row is not written.
- Write a batch, run `geo_engine.py lint` and `status`, read the failure reasons, fix the data, not
  the gate.
- Read 5–10 rendered rows per template per batch as a person would. If they read the same apart from
  the nouns, the template lacks combination-specific data: go back to `field_sources`.
