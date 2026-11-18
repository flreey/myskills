# Choosing the dimensions of a page space

The dimensions are not designed up front. They are already in the words people and assistants search
with; this step finds them, sorts them, and tests each one before it multiplies into pages.

"One sound × one variant" (SFXMint) and "one operation × one condition" (ToHD) are the same shape
(site-idea SKILL.md, "Two shapes of page space"): the first slot is what the product lets people get or
do, the second is what changes which result qualifies. What differs between products is which words
fill the slots, and that comes from their searches.

## 1. Split real searches into slots

Sources, strongest first: the site's own search and zero-result searches (web, API, MCP), the
assistants' captured searches (`search_queries` in the runs), the titles of pages that get AI-referred
landings, the demand map's search records and off-site quotes. Not model-written questions.

`slots` does the counting:

```
python3 <skill-dir>/scripts/geo_idea.py --root <project> [--geo-dir geo] slots --from <export.csv> [--from …]
```

The export is CSV or JSONL with a query column (`q`, `query`, `term`, `search`, `keyword`) and an
optional count (`n`, `count`, `searches`, `volume`, `hits`), or text with one query per line. It also
reads the runs' captured searches and the demand map's search records and quotes (not its analytics
rows). It writes `gap/slots.md` and `gap/slots.json`:

- per dimension: the share of searches naming any of its values, the values most searched, and the
  values never searched;
- the frequent words no dimension holds yet, with the dimension values they come with;
- the names in the searches (sites and products the assistant checks: a shortlist, not a slot).

Two examples of splitting by hand:

| Search | Slots |
| --- | --- |
| `free online AI video upscaler 1080p browser no install` (ToHD, ChatGPT's rewrite) | do: upscale video · target: 1080p · conditions: free, browser, no install · wording: online, AI |
| `wooden door creak sound effect cc0 wav` (SFXMint) | get: door · variant: wooden, creak · conditions: CC0, WAV |

On ToHD (2026-11-18), the frequent words outside its situation dimensions were capability words
(upscale, upscaler, 4k, enhancer, 1080p, deinterlace, frame) and condition words (pricing, limits,
credits): the missing capability dimension showed up in the counts.

## 2. Sort each slot

| The word | Becomes | Examples |
| --- | --- | --- |
| What the person wants to get or do | the main dimension (`kind: capability`, or `entity` / `task`) | upscale, restore; door, dog bark |
| Changes the result or the steps when swapped (different files, output, procedure) | a generating dimension, or a variant inside the main value | 1080p vs 4K; wooden vs metal door; iPhone vs computer |
| True on every page | a fact every page states (facts.jsonl `scope: all`), not a dimension | free, CC0, no watermark |
| Changes nothing when swapped | wording for titles and text only | online, best, 2026, AI |
| A site or product name | the assistant's shortlist: site-offsite, not a dimension | Topaz, Freesound |

This is the `changes_answer` test, answered from real words instead of imagination.

## 3. Test each candidate dimension

A dimension generates pages only when all five hold; otherwise it is a section of the parent page or
a fact.

| Test | Question | Where it shows |
| --- | --- | --- |
| Changes the answer | Does another value give different files, output or steps? | `changes_answer` + `why` |
| People ask | Do its values appear in real searches, and how often? | `slots` (share, never-searched values), `queries`, AI landings |
| Own evidence | Does each value have its own files, tests or data? | `assets`; site-batch `min_own_evidence` |
| Dedicated pages win | For these searches, do pages made for them win, or broad pages? | `queries` `rank.winners_kind` |
| We deliver it | Can the product serve each value, with proof? | tests, real files |

A combination of two dimensions repeats the tests on the combination: site-batch's demand and
dedicated-winner gates check the last three per row.

## 4. The main dimension follows the product's inventory

| Product | Main dimension, usually | Example |
| --- | --- | --- |
| Tool | operation | upscale, restore, interpolate |
| Asset library | item × variant | sound × variant |
| SaaS | feature × integration | sync × Notion |
| Data site | entity × attribute | model × spec |
| Service | service × place | moving × city |

A starting point only: the counts in step 1 decide. A slot that fills a large share of real searches
(ToHD's capability words, SFXMint's variants) is a dimension the space needs.

## 5. When two cuts both look right

Ship a few pages of each (a small wave per template) and compare AI landings and retests; grow the
one that wins. Do not build both in full first.
