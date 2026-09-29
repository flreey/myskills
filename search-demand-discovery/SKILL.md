---
name: search-demand-discovery
description: Use when building or expanding the keyword pool for a product or site — finding many real search queries from free sources (autocomplete, Keyword Planner, Google Trends, Search Console, SERP related searches, competitor sitemaps), importing keyword exports, defining a product's search boundary and seeds, or judging whether keyword discovery is saturated. Also for 找关键词、扩词、关键词挖掘、需求发现.
---

# Search Demand Discovery

Collect broadly without inventing demand. The output is an evidence-backed observation pool in
`<project>/seo/`; `search-demand-mapper` turns it into clusters and page decisions.

Engine (Python stdlib, resumable): `python3 <skill-dir>/scripts/discovery.py --root <project> <command>`.
If the project already runs its own keyword engine, keep that engine as the state layer and apply
these rules through it instead of creating a second pool.

## Iron rules

1. **Every keyword comes from an external observation.** Model ideas, modifier combinations and
   competitor URL slugs are hypotheses. They may become seeds; they never enter the pool as keywords.
2. **Signals stay separate.** Keep source, market and period on every observation. Suggestion counts
   are not volume. GSC query and query+page rows describe the same impressions. Synonym volumes are
   not added. Nothing is summed into one demand score.
3. **Request parameters are not facts about users.** `gl=us` does not prove where searchers are or
   which language a query is in; GSC queries have language `und`.
4. **Failures stay visible.** Rate limits, consent pages and CAPTCHAs pause that source for the run.
   Never solve CAPTCHAs, rotate identities or disguise the client. Never record a failed fetch as
   "no demand".
5. **Recursion only through triage.** A new seed needs observation evidence and a parent seed.
   Depth is capped (`max_depth`, default 2); deeper candidates are kept as `deferred`.
6. **Stop on yield, not on fatigue.** Close each round and follow its verdict.
7. **Discovery ends at the pool.** It never creates clusters, pages or priorities.

## Workflow

### 0. Bootstrap (no `seo/boundary.json` yet)

Research first, then ask once. Follow [references/bootstrap.md](references/bootstrap.md): read the
project and live site, count inventory categories, sample competitors, draft `boundary.json` and
seeds, then ask one batch of multiple-choice questions, each with a recommended default. Do not ask
anything the research can answer, and do not run an open-ended interview.

When candidate seeds run to hundreds or thousands (catalog items, SKUs, aliases, a legacy seed
list), consolidate them first: `consolidate` → `probe` → `consolidate` → `seed review` →
`seed apply-review`. The scripts only prepare evidence and validate. You decide every row and
every ambiguous alias; there are no default actions. See "Consolidating raw candidates" in the
bootstrap reference. Never expand raw item titles directly.

### 1. Round loop

| Step | Command | Notes |
| --- | --- | --- |
| Expand | `suggest --level quick` then `--level standard` | `--dry-run` shows the query count. Use `deep` (alphabet) only after standard, and only for the most productive seeds |
| Add browser sources | `import --format gkp\|gsc\|trends\|csv\|json\|lines` | Planner, GSC, Trends, SERP related searches, Bing WMT. See [references/sources.md](references/sources.md) |
| Add top-down hypotheses | `sitemap --url <competitor>` | Slugs become `hypothesis` concepts, never keywords |
| Extract | `concepts` | Writes `seo/work/triage-input.json` |
| Triage | write decisions JSON, then `triage --file` | Rules below |
| Close | `round` | `TRIAGE_FIRST` means triage the rest; otherwise `CONTINUE` or `STOP` |

Budgets live in `seo/config.json`: `max_requests_per_run`, a 1–1.3 s delay per host (the floor
never drops below 1 s), a 7-day cache, and the modifier gate. Hosts run in parallel on persistent
connections. Seeds skip their remaining modifier queries when their base queries return almost
nothing, or when their first modifier queries add almost nothing new (`--no-gate` overrides
this). A budget stop is not
saturation: rerun `suggest` in the same round to continue.
[references/expansion-loop.md](references/expansion-loop.md) covers levels, the gate, concept
extraction, yield and coverage.

### 2. Hand-off

When the verdict is `STOP`, or the user's budget is spent, run `status --coverage` and report:

- the pool size and each source's contribution;
- yield per round;
- inventory categories that have no observed keywords (check the seed status before calling
  it "no demand");
- deferred seeds and paused sources.

Then hand off to `search-demand-mapper`.

## Triage decisions

Read every item's examples before deciding. Each decision needs a reason.

| Decision | Use when | Effect |
| --- | --- | --- |
| `seed` | A distinct thing users want that the product could serve (a new entity or result set) | Expanded next round at parent depth + 1 |
| `modifier` + `axis` | It narrows results without changing the job (style, format, license, platform, context) | Added to `boundary.modifiers` |
| `head_term` | The product's own noun ("sound effect", "template", "calculator") | Stripped from later extraction |
| `adjacent` | A related job the product might serve with a different page type (tutorial, how-to, API, continuous listening) | Kept, not expanded |
| `out` | Outside the product boundary (platform ID lookups, music, hardware, jobs) | Added to `boundary.out_terms`, filtered later |
| `noise` | Fragments or duplicates of existing seeds | Ignored |

When unsure between `seed` and `modifier`, choose `modifier`: the mapper can promote an attribute
later, but a wrong seed spends budget expanding the wrong thing.

## Browser sources

The user signs in to their own accounts: Google Ads Keyword Planner, Search Console, and optionally
Bing Webmaster Tools. Trends and SERP pages need no sign-in.

- Only read and export. Never change account, campaign, billing or property settings.
- File downloads follow the host's download confirmation rules.
- Prefer a tool's own export to scraping its table.
- Search result pages: at most about 30 queries per session. On a CAPTCHA, stop and tell the user.

Per-source steps and pitfalls are in [references/sources.md](references/sources.md).

## Data

Everything lives under `<project>/seo/`; the file contract is in
[references/data-contract.md](references/data-contract.md). `init` writes `seo/.gitignore` for
caches and raw exports. Before committing `seo/`, check whether the repository is public: data
derived from Search Console stays out of public repositories.

## Premises (review when they change)

- Checked 2026-09-29: the Google (`client=firefox`), YouTube (`ds=yt`) and Bing (`osjson`) suggest
  endpoints returned JSON without auth. They are unofficial and carry no SLA.
- Keyword Planner exports are UTF-16 TSV with `Searches: Mon YYYY` columns. Accounts without spend
  see volume ranges.
- Search Console UI exports are a zip containing `Queries.csv` and `Filters.csv`. The date range is
  often relative, so pass `--period`. Tables cap at 1,000 rows, so export in slices.
- Worked example: SFXMint (free CC0 sound effects). See
  [references/example-sfxmint.md](references/example-sfxmint.md).
