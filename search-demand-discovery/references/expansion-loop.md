# Expansion loop, concepts, yield

## Why the loop exists

A pool built from a handful of seeds stays shallow. Most demand sits in entities you did not think
of: neighbours of inventory, competitor categories, and phrasings only autocomplete knows. The loop
finds new entities (concepts), turns the ones that fit into seeds, expands them, and stops once new
keywords mostly repeat known concepts.

```
seeds ──suggest/import──▶ observations ──concepts──▶ triage ──seed──▶ seeds (depth+1)
                                                   └─modifier/out/adjacent──▶ boundary
round close: yield = new reviewed seeds / new keywords  →  CONTINUE | STOP
```

## Levels and cost

Per seed per engine: quick sends 1–2 queries. Standard adds `prefixes + suffixes +
question_templates`, about 9 queries in total by default. Deep adds 26 alphabet queries.

Hosts run in parallel lanes: Google and YouTube share one lane because they share a host; Bing has
its own. Each lane keeps its own 1–2 s delay, so the delay per host never drops. Network errors
back off (5, 15, 45, 120, 300 s) before a source pauses; blocks pause at once. A budget stop is not
saturation: rerun `suggest` in the same round and the cache skips everything already fetched.

**Modifier gate.** When a seed's base queries return fewer than `modifier_gate_min_base` (5)
distinct suggestions on an engine, its modifier queries are skipped for that engine. The seed is
recorded as `gated` and counts as expanded; `--no-gate` overrides this. On SFXMint (66 seeds,
2026-09-29) the gate skipped 21% of queries and lost 1.4% of unique keywords, almost all of them
off-topic.

Deep expansion goes only to the `alpha_top_seeds` (default 20) seeds with the highest
new-keywords-per-request after standard. The alphabet is where volume comes from, but it is also
where budget is wasted on unproductive seeds.

## Concept extraction

For each observed keyword, the extractor first locates known seeds and their aliases, so a
modifier inside a seed name ("game" in "game over") survives. It then removes head terms,
modifiers, generic words (`free`, `download`, `best`…), stopwords and numbers from the remaining
words:

- If the rest contains a seed, the extra words become a **term** candidate. For example,
  "button click sound id roblox" leaves `id roblox`, so the question is modifier, out, or adjacent.
- If the rest contains no seed, it becomes a **phrase** candidate: a possible new entity, such as
  "mouse click".
- Competitor slugs become **hypothesis** candidates.

A phrase that contains another pending phrase is listed as a `variant` under it. Phrases that
contain a newly accepted seed are marked `subsumed` automatically and re-extracted as terms next
time. Candidates need at least `concept_min_count` keywords (default 2), unless they come from GSC,
Planner or on-site requests.

## Triage heuristics

- **Seed** only if it points to a different result set that users want and the product could
  plausibly serve. "Mouse click" versus "button click" differs because the sound source differs.
- **Platforms and usage contexts are modifiers** ("discord", "for video editing", "minecraft"),
  unless the job changes. "Roblox id" changes the job to looking up an ID, so it is `out`.
- **Duration and continuous formats** ("1 hour", "loop 10 hours") are `adjacent`: a different
  delivery from a short asset.
- **How-to fragments** ("make", "add", "get … windows 10") are `adjacent`, or `out` when they are
  about configuring someone else's software.
- **Misspellings and inflections** of a seed are `noise`.

## Round verdicts

| Verdict | Meaning | Next |
| --- | --- | --- |
| `TRIAGE_FIRST` (exit 4) | Pending concepts would understate yield | Triage, or `round --force` with a stated reason |
| `CONTINUE` | Some in-boundary seeds have not finished the configured level on every engine, and yield is above the threshold | Next round |
| `STOP` | The frontier is exhausted (every seed within `max_depth` finished the configured level), or yield stayed below `stop_yield` (0.02) for `stop_rounds` (2) rounds | Hand off to the mapper |

Yield ignores budget: a round cut short by `max_requests` is not evidence of saturation. Keep
expanding within the round.

## Coverage

`status --coverage` counts pool keywords per inventory category. A category with zero keywords
means one of three things:

1. its seed has not been expanded;
2. users call it something else (add an alias);
3. there is no search demand.

Check 1 and 2 before concluding 3. Also compare with top-down sources: many competitor categories
without matching seeds point to gaps in the product boundary or inventory, not in keywords.

## Cadence

- **First build:** 3–6 rounds; stop on the verdict.
- **Maintenance:** once a month, import GSC, run a quick `suggest` refresh (the cache expires after
  7 days) and triage. The mapper's review mode handles the rest.
