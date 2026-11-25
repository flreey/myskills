# Gap scan: where a live site misses AI traffic, from its URL alone

Use when a live site wants more visits from AI assistants and the question is *what to change*:
which needs it loses, why, and what kind of fix each one needs. It needs only the site's URL; first-party
data (site search, AI landings, Search Console) is used when it exists, to rank and to check. Measuring
a change over weeks is optimize mode (optimize.md); a new idea with no site is site-idea.

Engine: `python3 -I <skill-dir>/scripts/gap_scan.py` (`inventory`, `pool`, `probe`, `verdicts`,
`volume`). `probe` and `volume` call the `glasser` CLI (Glasser skill), which bills per call; name the
price and get the owner's go-ahead before a batch (site skill rule on paid tools). Keep everything in
the project's `geo/scan-<date>/` (or the GEO workspace for a site that is not a project).

## How a visit happens

One AI visit passes four gates: someone asks the question → the assistant decides to search instead of
answering from memory → the site's page is among the results → the answer names or links it and the
person clicks. The scan finds, per need, which gate the site fails at.

Two kinds of question behave differently:

| | Category ("best free X site") | Specific task ("free wooden door creak sound", "tool to unblur a video") |
| --- | --- | --- |
| Who wins | Brands the model remembers: its first search query often lists them before it has read anything | A site with a page made for that task (asset sites) or a home page that covers it (tool sites) |
| Small site's chance | Low; off-site mentions over months | High; dedicated pages were retrieved about 2 days after launch |

## Steps

| Step | Do | Cost |
| --- | --- | --- |
| 0 Visible | Ask “What is <domain>?” and “https://<domain>/ What does this website do?” twice each (`probe`). Different answers point at the index layer: title, description, brand name, structured data, OAI-SearchBot access (run G1–G2 too) | 4 calls |
| 1 Inventory | `inventory --site <origin> [--hub /path]`: sitemaps, hub pages linked from home, the links in `/llms.txt`, and the hubs found on a sample of sitemap pages, because pages kept out of sitemaps still exist (SFXMint's 91 long-tail pages are linked only from family pages and llms.txt, not from home: missing them turned real pages into “add content” gaps on 2026-11-21) | free |
| 1b Confirm | Propose a positioning card (what, for whom, main features, key conditions) and 2–3 competitors: the sites ChatGPT cites most in 3 category questions × 2 runs, not the owner's guess. Ask the category questions in the site type's “find a site or tool” form (asset: “where can I download free X, OK for commercial use?”; tool: “is there a free online tool to X?”), never “how do I X”: that gets tutorials and desktop software (ToHD got Topaz and DaVinci Resolve as competitors that way, 2026-11-21). The owner corrects both, and adds features that exist without their own page, so they are not read as missing features | 6 calls |
| 2 Demand pool | `pool`: confirmed competitors' category, tag and tool page slugs (`--competitors`, `--match` regex), Google and YouTube autocomplete for seeds (`--seeds`, `--alphabet`); plus the bullet lists in ChatGPT's answers to 20–30 scene questions (“I'm making X, what do I need”). Cap competitor pages per section, never by total count: Mixkit's 36,000 stock-video URLs crowd out its 276 sound categories. With first-party data, add site-search queries and misses and AI-referred landing pages | ~$0.1 for scene questions |
| 2b Price the pool | Before the noise step, `volume` for the whole pool (≤1,000 keywords per call: split the list). Give bare item names the category word first (“door creak” → “door creak sound effect”), or Google reads another intent. Sort the pool into tiers: ≥1,000 / 100–999 / 1–99 / no volume | $0.09 per 1,000 |
| 3 Noise | Drop brand, software and meme queries (minecraft, capcut, meme), app-download and language variants, wording no person would type, and needs outside the site's category and audience. Keep needs of the same category the product cannot serve today: they are the “add content” and “add the feature” gaps (a model told to drop “needs outside the positioning” dropped colorize, color grading and the like as unsupported features, 2026-11-21). A judgment step: do it with the model, ask for the full count, then show the cut. Also drop “category + adjective or licence” phrases (royalty-free sound effects, funny sound effects): they are category questions. Show the model a share of every volume tier and use volume as context only, never as the ranking key; then pick the needs to probe across tiers (about 25 / 30 / 30 / 15%: head / mid / tail / no volume) and list the kept-but-not-asked needs with volume for the next scan. Picking by volume probes only head terms, which small sites rarely win: SFXMint's wins fell from 14 to 3 of 60 that way, and came back to 15 with the tier quota (2026-11-21) | — |
| 4 Site type and probe style | Pick 2–3 candidate phrasings for the site type (below), run 10 needs × each × 2 runs, `verdicts`: keep the style with the highest search rate; agreement between runs only replaces the proven default when clearly better (2 or more of 10 pairs). Styles must be neutral, how a stranger asks: never build in the site's own pitch (its licence, “no attribution”, feature names). A style echoing SFXMint's “CC0, no attribution” won calibration on agreement 10/10 vs 9/10 and turned 45 of 50 needs into wins (2026-11-21) | 40–60 calls |
| 5 Screen | One run per need in the chosen style (`probe`, then `verdicts --inventory`); the calibration needs already have two runs in that style, so skip them | $0.004 per need |
| 6 Confirm | One more run for the needs about to get work, to drop chance verdicts | $0.004 per need |
| 7 Classify | Map every gap to one of the five kinds below, against the inventory (synonyms included: police siren ↔ mechanical-siren). A page whose name holds every word of the need is never “add content”: it is “check indexing” (camera shutter ↔ /sound-effects/rapid-camera-shutter) | — |
| 8 Rank | Reuse the volumes from step 2b (a reworded need keyword takes its source candidate's volume; another call for a few keywords is not worth it); with first-party data, site-search counts first | free after 2b |
| 9 Hand off, retest | Changes go through the project's own workflow; retest the same questions after launch, read AI landings after about 4 weeks | $0.004 per question |

A full site run cost about $1–2 in Glasser calls in November 2026.

Billing (checked 2026-11-20): every endpoint bills per call, and an empty result (`NO_RESULT`) is billed
too. The LLM Scraper takes one prompt per call, so cost scales only with the number of questions;
`volume` takes up to 1,000 keywords per $0.09 call, so pool every keyword into one call; Bing SERP
checks bill per 10 results, so keep the default depth unless the ranking depth is the question.
Glasser's price equals DataForSEO's Live price; DataForSEO's own Standard queue is about 70% cheaper
but needs a direct account ($50 minimum) and waits up to 45 minutes. It is worth it only at product
scale, and its answers have not been checked against Live. `probe` keeps money from leaking:
saved ids are skipped, the idempotency key is fixed per output file and payload (a retry returns the
earlier run instead of paying again; never add an attempt counter to the key after a timeout or a lost
answer, since Glasser may have run and billed the call: an automated version that did so paid 21 of 508
calls twice on 2026-11-21), it prints how many calls are deliberate repeats, and it stops
above `--max-cost` (default $1) unless `--yes` is passed. Repeats are a design choice, not waste:
screening runs once per need, calibration and confirmation run twice.

## Probe styles by site type

| Site type | Style that works | Notes |
| --- | --- | --- |
| Asset / file site | “Where can I download a free <X>? It needs to be OK for commercial use.” | 42/42 searched (SFXMint); chosen again by the automated calibration on 2026-11-21 (20/20 searched, kw 0/20) |
| Tool site | “Is there a free online tool to <task>? Ideally no watermark and no signup.” | 20/20 searched, 10/10 runs agree (ToHD) |
| Any | Keyword only (“<X> sound effect”) | Searched 7/42: mostly answered from memory. Use only to see how often keyword-style users trigger search |
| Any | “How can I <task> for free?” | Gives tutorials (HandBrake, Premiere); ToHD named 0/20. A separate question type, not a long-tail probe |
| Any | Scene (“I'm making a horror game…”) | Recommends whole sites (Pixabay, Mixkit), not pages; use for category and brand diagnosis |

## Verdicts and the five kinds of gap

`verdicts` gives per need: `wins` (named or linked), `retrieved-not-named` (our page among results, not
named), `gap` (searched, our site not among results), `no-search` (answered from memory; pages cannot
help that phrasing).

| Kind | Sign | Fix |
| --- | --- | --- |
| Same-name page not retrieved | Inventory has `/sounds/cow-moo`, the probe never retrieves it | Check search-crawler fetches and indexing first; test a discovery change (llms.txt, hub links) on half the pages |
| Content under another name | Content exists, page names it differently (mechanical-siren for “police siren”) | Retitle the page with the user's words, or a page in those words; avoid two pages for one wording |
| Retrieved, not named | Our page in the results, another site recommended | Say on the first screen what the page does and its limits (free, 4K, phone, signup) |
| No content | Nothing in the inventory or catalogue | Make the content, or drop it |
| No capability (tool sites) | The assistant recommends small single-purpose tools for a task the product cannot do | A product decision: check demand (`volume`) and fit first |

## Site type changes the lever

- Asset sites win with pages for one specific thing: SFXMint's long-tail pages appeared in 55% of
  answers to their questions; a third of its wins came through family pages.
- Tool sites are linked at the home page: ToHD's ChatGPT landings were 91% home page, and scenario
  pages (VHS, wedding, camcorder) got almost none. Their lever is how well the home page covers tasks,
  the capability gaps, and fixing tool pages that are retrieved but not named; scenario pages are second.

## Checks against reality

- The probe source: Glasser's DataForSEO ChatGPT LLM Scraper (`force_web_search=false`, en, US)
  matched a Pro account's ChatGPT on 14 of 16 long-tail pages (page retrieved or linked) and 17 of 20
  questions (site named). With `force_web_search=true` it searches every time and overstates presence
  (15/32 vs 4/36). It asks one turn only: no pick turn, no model choice.
- Search queries (`fan_out_queries`) look like ChatGPT's own (brand lists in about half the first
  queries) but the vendor does not say how they are made. They show how the assistant verifies and
  what it reads, not new needs: broad questions are searched as “category + conditions + brands”.
- Bing rank does not explain ChatGPT retrieval: SFXMint's `/sound-effects/bell-chime` was not in
  Bing's top 30 for its query yet ChatGPT retrieved it; `/sounds/cow-moo` was indexed by Bing but not
  retrieved.
- A public-sources-only scan of SFXMint found 30 gaps; 15 had ≥ 20 site searches in 60 days, 7 had
  fewer than 5. A data-driven scan (site search combos) found finer “sound + modifier” gaps; the two
  overlapped on 3 of 13 and complement each other.
- Google volume stands in for how often people ask an assistant; say so when ranking.
- Volume tiers and wins (sfxmint.com, 2026-11-21, needs named or retrieved / probed): head ≥1,000 3/22, mid 5/18,
  tail 2/11, no volume 5/9 (the earlier scan: 5/20, 5/22, 6/15, 2/3). No-volume needs are not noise: specific
  wording often has no Google volume and is where a small site wins. One run only; not yet checked on a tool site.
- Automating the owner's logged-in ChatGPT got the account logged out three times in a day (the last
  after 4 conversations). Use it only for a few spot checks and for pick turns.

## Premises

- Measured 2026-11-20 on sfxmint.com (asset site) and tohd.video (tool site); write-ups in the GEO
  workspace (`whypicked-plan.md`, `geo/blind-tohd-2026-11-20/`) and `sfxmint/geo-whypicked/step7–9`.
- Glasser prices on 2026-11-20: LLM Scraper live $0.004/call; Google Ads search volume $0.09/call;
  Bing SERP $0.002/page. Re-check with `glasser inspect` before a batch.
- Whether traffic rises after the fixes was not yet measured on that date (first reads mid-December).
- Automated end to end in MissedByAI (`~/Projects/missedbyai`, 2026-11-21): a full scan of 60 needs cost
  about $0.6–0.8 and took 20–40 minutes (one ChatGPT answer takes 30–120 s). Its runs on sfxmint.com and
  tohd.video and the comparison with the hand runs are in `reports/acceptance-2026-11-21/` there.
