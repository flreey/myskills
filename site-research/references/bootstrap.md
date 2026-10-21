# Bootstrap: research first, ask once

Goal: produce `seo/boundary.json`, `seo/config.json` and the first seeds with minimal user effort.
Only the questions that research cannot answer reach the user, as one batch of choices.

## 1. Read-only research

| Question | Where to look |
| --- | --- |
| What does the product let users do? | README, landing copy, docs, app routes |
| What does it already have? | Inventory source: DB, catalog file, CMS or API. Count items per category; use the words users would search for, not internal IDs |
| Which landing pages exist? | Router config, `sitemap.xml`, static build output |
| Which market does it serve? | Site language, GSC country split, pricing currency |
| What real demand is already visible? | GSC (with access), site search or request logs, support tickets |
| Who ranks for the core seeds? | Search 3–5 core seeds in the target market; note recurring domains and the page types that rank |
| Is there an industry taxonomy? | Sound effects: UCS categories. Commerce: the catalog taxonomy. Trade: HS chapters. Apps: store categories |

Record open questions instead of guessing. A site's age, launch date or traffic state is never
inferred from commit history; check the deployment record or ask.

## 2. Draft the boundary

```json
{
  "product": {"name": "", "summary": "one sentence of what users can do", "url": "https://..."},
  "rings": {
    "in": ["jobs the product completes directly"],
    "adjacent": ["related jobs it could serve with a different page type"],
    "out": ["jobs it should never chase"]
  },
  "head_terms": ["the product's own nouns"],
  "expression_templates": ["{seed} <head term>"],
  "question_templates": [],
  "modifiers": {"format": [], "license": [], "style": [], "context": []},
  "adjacent_terms": [],
  "out_terms": [],
  "inventory": [{"name": "user-facing category", "aliases": [], "count": 0}],
  "competitors": ["https://..."],
  "taxonomies": [{"name": "", "ref": ""}],
  "open_questions": []
}
```

- `expression_templates` turn a bare seed ("button click") into how people search for it
  ("button click sound effect"). If a seed already contains a head term, it is used as is.
- `question_templates` are optional product-specific question forms (`"how to make {seed} sound"`).
  Generic prefixes such as "how to" applied to a noun produce junk queries.
- Keep modifier axes short; triage grows them from real data.

## 3. Draft seeds

| Origin | Source | Depth |
| --- | --- | --- |
| `inventory` | One seed per inventory category or family, in user language | 0 |
| `gsc` / `onsite` | Top queries' core things (import the export too) | 0 |
| `topdown` | Competitor sitemap categories after triage (`sitemap` then `triage` as `seed`) | 0 |
| `taxonomy` | Industry taxonomy leaves that fit the boundary | 0 |
| `user` | Anything the user names | 0 |

Seeds are the things users would type. Product marketing names ("AI agent & coding tool sound
set"), SKU titles and internal family IDs are not seeds. Autocomplete drifts from such names into
unrelated domains: on SFXMint, 73% of the new keywords from set-name seeds contained no sound word
at all. Name the underlying entity ("typing sound", "notification") instead.

Seeds are hypotheses. Add them with `seed add --file seeds.json`
(`[{"text": "...", "origin": "inventory", "aliases": ["..."], "note": "38 items"}]`).

## 3b. Consolidating raw candidates (large catalogs, legacy seed lists)

Use this when the candidates run to thousands: SKUs, asset titles, role aliases, marketing
names, or an older engine's seeds. The unit to reach is one entity users would type per distinct
result set. Probing, not a fixed rule, decides how fine the entities get.

1. **Export** the project's structure as `seed-candidates@1`:
   ```json
   {"groups": [{"id": "door-knock", "name": "door knock", "items": 36, "aliases": ["knock on door"]}],
    "names":  [{"text": "button press", "groups": ["button-click"], "origin": "role"},
               {"text": "sound effects for games", "groups": [], "origin": "use_case"}],
    "leaves": [{"text": "rapid knocking on door 28", "group": "door-knock"}]}
   ```
   - **groups** are the grouping layer: family, product type, feature or topic.
   - **names** are other names that point at 0–n groups.
   - **leaves** are the finest items.
2. **Run `consolidate --file candidates.json`.** Mechanically:
   - It strips variant suffixes and IDs.
   - It strips head terms and generic words only at the edges ("phone case for kids" keeps its
     "case").
   - Numbers stay in group names ("iphone 15"). In leaves, only numbers that the group also has
     survive.
   - Particles stay at the end of a name and in keys ("game over", "power on", "fade in"); only
     leading particles and pure function words are dropped. Dropping them once merged "8-bit game
     over" into "8 bit game" on SFXMint.
   - Names that point at one group become aliases; names that point at several become parent
     candidates.
   - A leaf minus its modifier words collapses into its group when nothing else remains.
   - Words that recur across many groups' leaves (`--spread`, default 8) are reported as
     `inferred_modifier_words`. Add the real ones to `boundary.modifiers` and rerun.
3. **Probe.** Run `probe --file seo/work/consolidation.json`, then `consolidate` again. Repeat until
   nothing is left to probe. Every entity gets one cheap query per engine. Leaves are sampled
   (`--leaf-sample`, default 2 per group); only groups whose sample shows signal get all their
   leaf variants probed. The rest fold into the group.

   **Signal** means suggestions that still contain every core word of the entity. Some engines
   answer anything with loosely related completions ("drum kit ride bell" → "bike bell"). On
   SFXMint, counting any suggestion would have marked 629 of 668 entities as demanded; the
   relevance rule marks 380. Review rows carry suggestion samples, so an entity can be renamed
   to the phrasing users actually type ("radio tuning sweep" → "radio tuning").
4. **Review. You decide every row; the command never decides.** Run `seed review --limit 80` to
   see undecided rows. Each row comes with evidence: signal per engine, raw suggestion samples,
   item count, aliases, children and signal leaves. Write a decisions file and apply it with
   `seed apply-review --file decisions.json`. Repeat until `undecided_rows` is 0.
   ```json
   {"review_hash": "<from seed review>", "decisions": [
     {"names": ["notification chime"], "action": "seed", "text": "notification",
      "drop_aliases": ["ding", "message"], "reason": "users search the broad term; samples show it"},
     {"names": ["footsteps on concrete"], "action": "seed", "drop_aliases": ["footsteps"],
      "promote": [{"text": "footsteps", "reason": "generic query users type"}], "reason": "..."},
     {"names": ["enemy die", "mob death"], "action": "alias", "target": "enemy defeated", "reason": "same result set"},
     {"names": ["crisp ui sound set", "gold"], "action": "park", "reason": "marketing name / generic word, no signal"},
     {"names": ["gen"], "action": "out", "reason": "not an entity name"}]}
   ```
   How to judge:
   - **seed**: a distinct result set users ask for. Take the text from how users phrase it in
     the samples; renames without sample evidence are fine, because the first base expansion
     verifies them.
   - **alias**: the same result set under another name.
   - **promote**: a leaf or alias that deserves its own seed.
   - **park**: no signal, a marketing name, or a word too generic to expand. Parked seeds stay
     known and are never expanded.
   - **out**: not an entity.
   - Rows without signal need a decision too. Group many rows with the same decision into one
     entry with a shared reason.
5. **Resolve ambiguity.** `apply-review` writes nothing while an alias belongs to several seeds or
   equals another seed; decide which side keeps it. It then lists one-word aliases with usage
   evidence: how many different seeds' searches each word appears under. For each, drop it
   (`drop_aliases`) or keep it (`confirm_aliases`, which removes it from later lists), using a
   `seed` decision with `--revise`. Stop when the remaining words are true synonyms. Otherwise a
   word like "hit" or "door" would pull unrelated keywords into one seed during concept
   extraction.

   Repeat the check after each expansion round with `seed aliases`: the pool is then much larger
   than at consolidation time, and multi-word aliases can be too broad as well ("car crash" on
   "debris crash"). Dropping an alias lets its keywords surface as concepts of their own.

6. **Re-consolidation keeps earlier work.** After a boundary or rule change, rerun `consolidate`.
   Decisions carry over by row name, so only new or renamed rows come back as undecided.
   `seed review` also lists `stale_seeds`: seeds whose source rows vanished because a renamed row
   now covers them. Keep them, or retire them with `seed reject --text ...`.

On SFXMint (2026-09-29), 8,042 legacy seeds consolidated to 668 candidate entities before probing.
The detailed numbers are in [example-sfxmint.md](example-sfxmint.md).

## 4. One batch of choices

Ask at most 5 questions at once. Each has options with the recommended default first, and a
one-line consequence per option. Typical set:

1. **Boundary edges** found during research, each as IN / ADJACENT / OUT. For example: "sound
   effect tutorials", "sound effects API", "ringtones".
2. **Market and language**. Default: the site's language plus the largest GSC country.
3. **Sources you are signed in to** (multi-select): Keyword Planner, Search Console, Bing Webmaster
   Tools. Trends and autocomplete need no account.
4. **Depth per round**. Choices: quick (about 200 requests), standard (about 600, the default), or
   deep (alphabet expansion for the most productive seeds, about 1,500).

Apply the answers, write the files, and list every default you chose silently in the summary so
the user can correct it later. If the user says "just decide", use the defaults and proceed.
