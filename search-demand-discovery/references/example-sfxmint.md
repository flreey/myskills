# Worked example: SFXMint

SFXMint is a free CC0 sound effects library (MP3/WAV, about 6,100 assets in 24 families) with an
API and MCP for developers. The real project runs its own engine (`npm run keywords`, SQLite). By
the adapter rule, this skill's rules apply through that engine there. The run below used the
generic engine on a scratch copy on 2026-09-29, with live autocomplete.

## Boundary (abridged)

```json
{
  "product": {"name": "SFXMint", "summary": "Free CC0 sound effects (MP3/WAV) plus API/MCP", "url": "https://sfxmint.com"},
  "rings": {
    "in": ["find, preview and download a specific sound effect or sound pack"],
    "adjacent": ["how to make or use a sound in a game/app", "sound effects API for developers", "continuous listening (1 hour, sleep)"],
    "out": ["music, songs, ringtones", "platform sound ID lookups (roblox id)", "audio hardware"]
  },
  "head_terms": ["sound effect", "sound effects", "sound", "sounds", "sfx", "audio", "noise"],
  "expression_templates": ["{seed} sound effect", "{seed} sound"],
  "question_templates": ["how to make {seed} sound", "{seed} sound for"],
  "modifiers": {"format": ["mp3", "wav", "ogg"], "license": ["free", "royalty free", "no copyright", "cc0"],
                "style": ["soft", "retro", "8 bit"], "context": ["game", "ui"]},
  "inventory": [{"name": "button click", "aliases": ["button press"], "count": 38}, {"name": "door knock", "count": 36}]
}
```

Inventory seeds come from family names users would type ("button click", "door knock"), not
internal family IDs ("feedback", "ui").

## Round 1 (live)

| Step | Result |
| --- | --- |
| `suggest --level quick --engine google --engine bing` (2 seeds) | 8 requests, 47 new keywords |
| `suggest --level standard --engine google --max-requests 12` | 36 new keywords, stopped by budget (not saturation) |
| imports (Planner, GSC, Trends, Ahrefs fixtures) | periods kept; the Ahrefs volume without a period stays `volume_unperiodized` |
| `sitemap --url https://sfxmint.com` | 578 URLs, 49 hypothesis concepts (own site, as a smoke test) |
| `concepts` | phrases: `mouse click` (7), `click`, `button press`; terms: `discord`, `loud`, `windows`, `soundboard`, `video editing` |

Triage used:

```json
{"decisions": [
  {"text": "mouse click", "decision": "seed", "reason": "hardware mouse source, different result set from UI button click"},
  {"text": "button press", "decision": "seed", "reason": "possible synonym of button click; the mapper decides merge via SERP overlap"},
  {"text": "discord", "decision": "modifier", "axis": "context", "reason": "platform context, same knock sounds"},
  {"text": "loud", "decision": "modifier", "axis": "style", "reason": "loudness attribute"},
  {"text": "button", "decision": "noise", "reason": "covered by button click / button press"}
]}
```

Once `mouse click` became a seed, `mouse click windows` and `mouse click video editing` were
marked `subsumed`. The next extraction produced the terms `windows` and `video editing` instead:

- `windows` means configuring the OS click sound: `adjacent` or `out`.
- `video editing` is a usage context: `modifier`.

## Lessons carried over from SFXMint's own engine

- Recursion was capped at depth 2, and new seeds had to cite observations. Model guesses never
  entered the observed pool.
- GSC query and query+page views, on-site requests and historical Planner volume were kept apart
  and never added together.
- Language judgement is separate from the request's `hl`/`gl` parameters. GSC queries stay `und`
  until judged.
- The earlier engine deliberately used one or two expressions per seed and no alphabet
  enumeration. That kept it stable but capped breadth. This skill adds standard and deep levels
  with a yield-based stop, so breadth can grow without spending budget blindly.

## Standard run vs the old engine (same 66 seeds, 2026-09-29)

Isolated copy; the old SQLite was opened read-only. Both runs used Google and Bing autocomplete,
with base expressions identical to the old engine ("X sound effect", "free X sound effect
download").

| | Old engine | Standard level |
| --- | --- | --- |
| Queries | 200 | 1,148 (910 with the modifier gate) |
| Distinct keywords | 1,095 | 2,446 |
| Keywords per query | 5.5 | 2.1 overall; about 1.2 for each extra modifier query |
| Old keywords also found | — | 1,040 of 1,095 (95%) |
| Keywords absent from the whole old DB (3,976, all sources) | — | 1,316 (54% of the new pool) |

- Autocomplete results for the same queries were nearly identical across runs (mean Jaccard 0.975
  over 129 queries). The gain comes from the extra patterns, not from drift.
- Every modifier pattern added keywords. `free`, `for`, `best` and `without` added about 270–280
  new keywords each; `like` and `vs` about 160–180.
- New entities surfaced: metal pipe, camera (shutter), thunder, buzzing light, cartoon bounce,
  fade out, metal clanging. So did useful contexts ("for game developers", "for video editing")
  and app/site-seeking intents (adjacent).
- Noise came mostly from set-name seeds: 116 of their 158 new keywords (73%) contained no sound
  word ("best ai coding agent", "gamification in adult learning"). The modifier gate removes most
  of them because those seeds' base queries return almost nothing.

Throughput (same machine and network, fresh seeds, no cache):

| Version | Requests per second |
| --- | --- |
| Sequential | 0.73–0.77 |
| Parallel lanes, delay measured end-to-start | 0.73 (no gain) |
| Parallel lanes, delay measured start-to-start | 1.07 (about 1.4×) |

Each host is still limited to one request per 1–2 s. The politeness delay, not the code, sets the
ceiling: at about 1 request per second, 1,000 seeds at standard level (about 18,000 queries) take
about 5 hours. Clean seeds to entity level and use Keyword Planner for breadth before scaling
autocomplete.

## Seed consolidation (2026-09-29)

The input was the old engine's 8,042 seeds, exported read-only as 533 groups (sound families),
1,218 names (roles, use cases, set names) and 6,109 leaves (asset titles, 74% of which carried an
index number or ran past 4 words).

| Stage | Result |
| --- | --- |
| Mechanical consolidation | 669 candidate entities (519 family, 69 multi-family names, 81 standalone); 1,484 names merged as aliases; 2,715 leaves folded into their family |
| Inferred modifier words | fast, slow, long, bright, metallic, muffled, muted, rapid, smooth, warm… The looping, heavy, distant and gentle axes were added to the boundary |
| Probe | About 2,000 entity names and leaf samples × 2 engines; about 45 min through a flaky proxy; every network error recovered with backoff |
| Signal (relevance rule) | 380 with signal, 289 without |
| Model review (`seed review` / `seed apply-review`, every row decided explicitly) | **340 active seeds (1 promoted), 45 rows merged as aliases, 284 parked, 1 out** |
| Alias review from usage evidence (2 passes) | 84 one-word aliases dropped (hit, game, door, click, tap…), 27 confirmed as true synonyms; the widest remaining alias fell from 83 seeds to 10 |
| Standard expansion cost | 6,116 queries (about 4,800 after the gate), about 1 hour, instead of about 145,000 queries (about 40 h) for the raw list |

Review decisions that recur in any catalog:

- **Leaf names reveal user phrasing.** "closed hi-hat — single hit" became the seed "closed hi
  hat", not "acoustic drum kit closed hat".
- **Multi-family role names become one umbrella seed with aliases.** "enemy defeated" collects
  "defeat enemy", "enemy killed", "mob death" and "monster death".
- **Marketing set names and unsearched use cases are parked.** All 15 set names and 55 of the 60
  use-case names had no signal.
- **Single generic words ("gold", "sale", "incoming", "flag") are parked.** They would expand into
  unrelated demand.

- **Validation caught folded umbrellas.** "footsteps" and "notification" had been folded into
  one family each as aliases. The reviewer promoted "footsteps" and renamed "notification chime"
  to "notification" instead of hard-coding extra seeds.
