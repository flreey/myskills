# From questions to pages and sections

Many questions, few pages. A question never gets a page because of its wording; it lands on the page
whose scope matches what it fixes, and each turn of the conversation lands in one section of that page.
Inputs: `geo/gap/samples.jsonl` (openings with `opening_scope`, follow-ups with `kind`), real signals,
and for live sites site-geo's clusters and conversations. `geo_engine.py questions --template <id>`
lists the samples through one template's eyes.

## 1. Which page: route by scope

`opening_scope` lists the dimensions the opening fixes. Compare it with the template:

| The opening fixes | Lands on | Example (template: source × target × need) |
| --- | --- | --- |
| every template dimension | **item page** (one combination) | "batch convert 300 HEIC photos to JPG without uploading" |
| the group dimension, not all | **group page** (`groups.basePath/<value>`) | "my iPhone photos won't upload to the school site" (source only) |
| none of them | **hub page** and, for recommendation openings, **off-site** | "what's a good free file converter?" |
| a task the template does not cover | another template, or `NOT_FIT` | "how do I compress a video?" |

Follow-ups often add the missing dimensions (`adds`). The opening decides where the person lands; the
follow-ups decide what that page must also answer or link to. A group page therefore needs a chooser
that sends each condition to one item page, and an item page needs the answers its conversations ask
next.

Recommendation openings ("best", "alternative to", "worth paying for") are won mostly by third-party
consensus: the hub states plainly what the collection covers and how to choose, and the real work is
site-geo off-site work (references/offsite-sources.md). Do not build a page per "best X for Y" wording.

## 2. Which section: route each turn by kind

| Turn | Section on an item page | On a group page |
| --- | --- | --- |
| opening (the task) | title, H1 and the answer paragraph (`core_answer`) | the group answer |
| `constraint` (can it, does it, is it allowed) | the details table (`constraint_results`, tagged with the slot) | a chooser row when the answer differs by item |
| `howto` (steps) | FAQ entry, or `resource` when a tool or file does it | FAQ entry |
| `why` (reason, explanation) | FAQ entry | FAQ entry |
| `compare` (versus another option) | `alternatives`, honest about when the other is better | chooser |
| `resource` (where, which file, which tool) | the resource button | chooser rows to the items |
| `pick` (which would you choose, is it really free / does it really work on X) | the conditions block on the first screen, by mode or device, with the same numbers as the pricing and FAQ pages | the group answer's conditions line |
| `other` | decide case by case; often a different template or off-site | — |

One question, one place. The same question is never answered in the answer paragraph, the table and the
FAQ at once, and target wordings are not pasted in as FAQ variants.

## 3. Question slots: the follow-ups every page answers

Only 40–100 combinations were sampled; the template has hundreds. So the sampled follow-ups are
generalised per template:

1. `questions --template <id>` → follow-ups by kind across the template's samples.
2. Merge them by meaning into 5–8 `question_slots`, each with the canonical question in people's words,
   its `kind`, and `required` (default true). Keep a slot when it recurs across samples or signals, or
   when it is a hard condition from the gap answers (`unmet_constraint`).
3. Every row answers every required slot: a `follow_ups` entry with `"slot": "<id>"`, or a
   `constraint_results` entry with the slot for `constraint` kinds. The answer is specific to the
   combination; if it would read the same on every row, it belongs on the group or hub page, not in the
   slot. The gate fails rows with unanswered or unknown slots.
4. Row-specific follow-ups (asked only for that combination) are welcome without a slot.

```json
"question_slots": [
  {"id": "keeps-dates", "question": "Will my photos keep their dates?", "kind": "constraint"},
  {"id": "quality", "question": "Will I lose quality?", "kind": "why"},
  {"id": "offline", "question": "Can I do it without uploading?", "kind": "constraint"},
  {"id": "on-windows", "question": "How do I open the result on Windows?", "kind": "howto", "required": false}
]
```

## 4. Titles from real openings

Before writing `patterns.title` and `patterns.h1`, read the item-level openings and real signals for
the template and note the words people use for the task (`title_source` in the template, one line:
which phrasing, from which samples). Titles name the task the way it is asked, then the combination.
No keyword stuffing; one task per title.

## 5. Group content (`geo/combos/<template>.groups.jsonl`)

For templates with groups, one row per group value that has group-level openings or enough items:

```json
{"key": "heic", "answer": "iPhones save photos as HEIC; most upload forms want JPG. Convert them in the browser, up to 500 at a time.",
 "fact_ids": ["f1"],
 "chooser": [{"when": "a website or form only accepts JPG", "slug": "heic-to-jpg-batch", "why": "smallest files, dates kept"},
             {"when": "you need every pixel kept", "slug": "heic-to-png-offline"}],
 "follow_ups": [{"q": "Why are my iPhone photos HEIC?", "a": "..."}]}
```

The same fact rule applies: numbers must come from cited facts. Chooser slugs must be gated pages of
this group; unreleased ones are dropped from the output until their wave ships. The kit group page
(override `DirectoryGroup.astro`) shows the answer, a "Which one fits" table, the item list and the FAQ
with FAQPage; JSON output carries it as `groups[].content`.

## 6. Hub

The hub (`collection.hub`) gets one honest `intro`: what the collection covers, how to pick, what it
does not cover. Broad questions beyond that are off-site work or a single hand-made guide, not more
generated pages.

## 7. Existing pages on a live site

The same routing applies to site-geo optimize clusters: a cluster's opening scope picks the page, its
turns pick the sections. The per-page result is a page brief (site-geo `references/optimize.md`, O4b).
