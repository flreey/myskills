# Operating loop: from data to the next change, across every site

The owner runs many small sites alone. The loop answers one question each week: which site gets the
next hour, and on what. It is built on `scripts/ops.py` and the growth home `~/Projects/growth`
(override with `GROWTH_HOME`).

## The five layers

| Layer | When | Who | What |
| --- | --- | --- | --- |
| L0 data | daily, automatic | `ops.py collect` (inside `guard`) | Umami, Search Console, Bing, Cloudflare into `data/snapshots.sqlite`, one row per site, day, source and metric; re-reads the last days so late data lands |
| L1 guard | daily, automatic | `ops.py guard` | alerts only on breakage: a core event at zero after days of traffic, a traffic cliff, 5xx above 2%, a check that went from ok to fail |
| L2 weekly | Monday, automatic | `ops.py weekly --write`, then the agent | one table for all sites (stage, north star and trend, visitors, search impressions, where it is stuck, stage suggestion), then per-site detail; the agent adds at most 3 proposed changes |
| L3 experiments | weekly | the owner picks, the agent executes | `experiments.json`, one queue for all sites; each change has a hypothesis, a metric, an expected result, a review date and a stop rule |
| L4 playbook | when a result is in | the agent | `playbook.md`: what worked (and whether it moved into the kit), what did not and why |

The agent never picks experiments, changes prices, deploys or retires a site on its own. It proposes,
executes approved changes with the skill that owns them, and reviews them on their date.

## Growth home files

| File | Holds | Who edits |
| --- | --- | --- |
| `portfolio.json` | sites (domain, project, types, stage, since, sells), thresholds, `notify.command` | the agent, after the owner confirms a stage change |
| `experiments.json` | `items`: `id`, `site`, `hypothesis`, `change`, `metric`, `expect`, `start`, `review`, `stop`, `status` (`proposed`, `running`, `done`, `dropped`), `result` | the agent |
| `playbook.md` | results worth keeping | the agent |
| `weekly/<year>-W<nn>.md` | the weekly report | `ops.py weekly --write`, then the agent appends the proposals |
| `alerts.md` | every guard alert | `ops.py guard` |
| `data/`, `logs/`, `credentials.local.json` | snapshots, launchd logs, Bing key and Cloudflare token | never committed |

The growth home is a local git repository with no remote. Site repositories keep only what changes
with their code: `umami-reports.json` (saved funnels plus `standard` and `northStar`) and `docs/flow.md`.

## Standard events and the north star

Every site maps its own event names to five standard ones, so sites compare and the guard knows what
"core" means. Keep the site's names; never rename an event to fit (renaming breaks its history).

| Standard | Meaning | tool | app | directory | landing |
| --- | --- | --- | --- | --- | --- |
| `core_start` | started the core action | `tool_start` | `job_start` | `search` | `cta_click` |
| `core_done` | the core action produced a result | `tool_done` | `job_end` | `outbound_click` | `checkout_start` |
| `takeaway` | took the result away | `tool_takeaway` | `result_download` | `outbound_click` | `cta_click` |
| `error` | the core action failed | `tool_error` | `job_error` | | `checkout_error` |
| `paid` | paid | `purchase` | `purchase` | | `purchase` |

The columns are plan roles; `ops.py` matches the site's observed events against each role's aliases
and labels the result a guess. Confirm it in the site's `umami-reports.json`:

```json
{"standard": {"core_start": ["generate"], "core_done": ["generate"], "takeaway": ["copy_success"]},
 "northStar": "takeaway"}
```

Names are plain event names (the daily snapshots count events by name, so field filters do not apply
here; put a filtered step in a funnel instead). A `*` stands for every observed event it matches, for
sites that send one event per tool (`"core_start": ["*-roll", "*-make"]`).

Default north star: `takeaway` for tool, directory, landing and content sites; `core_done` (a first real
job finished) for app sites. Counts are events, not people, and include the owner's own visits.

## Stages

| Stage | Look at | Move on when (defaults in `portfolio.json` → `thresholds`) | Main skills |
| --- | --- | --- | --- |
| validate (first 8 weeks) | search impressions, indexed pages, any completed core action | visitors ≥ 100 in 7 days and the north star grew 3 weeks running → growth | `site-research`, `site-geo`, `site-check` |
| growth | north star per week, use and takeaway rates, return visits, sources | visitors ≥ 300 for 3 weeks → monetize | `site-batch`, `site-offsite`, `/site` |
| monetize | revenue per visitor, paywall conversion | | `site-stripe`, ads |
| maintain | guard alerts only | | none |

A validate site with 8 weeks of data, fewer than 500 Search Console impressions and fewer than 10
north-star events in the last 7 days gets a "→ maintain" suggestion. Suggestions are printed in the
weekly report; the stage changes only when the owner says so (edit `stage` and `since`).

## Where it is stuck, and what to use

`ops.py weekly` names the first layer that looks broken, top of the funnel first. It is a heuristic
and prints its reason; read the numbers before acting.

| Stuck at | Signal | Lever |
| --- | --- | --- |
| data | the north star has no event behind it, or a check fails | fix tracking first (audit, `umami-reports.json`), registration, Search Console |
| demand | fewer than 100 visitors in 7 days | `site-research`, `site-geo`, `site-offsite`, `site-batch` |
| use | `core_start / visitors` below 20% | `ui-flow` (the path), `/ui` (first screen, copy) |
| finish | errors above 10% of starts, or `core_done / core_start` below 60% | the engine; read the error `reason` distribution with `funnel.py --field` |
| take away | `takeaway / core_done` below 30% | `/ui` on the result area and its actions |
| pay | a selling site with no payment in 7 days | pricing, paywall placement, `site-stripe` |

A rate is computed only when its base is at least 30; below that the report shows "-".

## Weekly review (what the agent does after the script)

1. Run `ops.py check` and `ops.py weekly --write` (launchd may already have written the file).
2. Read the data problems first: a failing check makes the site's numbers untrustworthy.
3. Review every experiment past its review date: compare the metric for the same length before and
   after the change, say whether search changes, seasonality or a deploy could explain it, then set
   `status` to `done` with `result`, and add a line to `playbook.md` when the result is clear.
4. Propose at most 3 changes for the coming week, across all sites, ranked by expected impact,
   confidence and cost. Each names the site, the stuck layer, the change, the metric, the expected
   result, the review date (2 to 4 weeks out; longer for sites under 100 visitors a week) and the stop
   rule. Append them to the weekly file and to `experiments.json` as `proposed`.
5. Stage suggestions: list them for the owner; change `portfolio.json` only after a yes.

Small sites: below about 100 visitors a week a before/after comparison is noise. Prefer changes big
enough to show in absolute counts, or a leading signal (indexed pages, impressions), and say so.
A/B tests need a variant field on the events and enough traffic (about 1,000 visitors a week per arm).

## Measuring during development, not after

- Stage 1 (site-kit): PRODUCT.md names the north star and the core action.
- Stage 2: `docs/flow.md` gives every state its event and fields; the events ship with the feature,
  and clicking through each state also confirms its event arrives.
- Stage 5 launch gate: `ops.py check --site <domain>` passes for Umami (website, pageviews, the
  north-star and core events), Search Console (property, sitemap read) and Bing (site added); the
  site's `umami-reports.json` is synced; the site is in `portfolio.json` as `validate`.
- After launch: a feature change updates its events and `umami-reports.json` in the same change.
  Events added to see one stuck step more clearly come after a weekly report found it.

## Data sources

| Source | Answers | Access | Notes |
| --- | --- | --- | --- |
| Umami | what visitors do | Umami tool credentials | the visit numbers of record |
| Search Console | demand and rank on Google | local gcloud application-default credentials, `webmasters.readonly` | about 3 days late; kept 16 months, so the snapshot keeps history |
| Bing Webmaster | Bing (and the index behind several AI search products) | API key in `credentials.local.json` (`bing_api_key`) | shapes follow Microsoft's reference; first real run pending |
| Cloudflare | health and crawlers | read-only Analytics token (`cloudflare_api_token`) | requests include bots and assets: never a visitor count |
| Stripe | money | per-account restricted read key | not connected yet |

Never add visits across sources. Search clicks and Umami search visits differ (blockers, early exits):
compare trends, not totals.

## Automation

`ops.py schedule` previews two launchd jobs; `--install` loads them (`--uninstall` removes them):
guard daily at 09:00 and the weekly file on Mondays at 09:30, local time, logs in `logs/`. Alerts go
to `alerts.md`; `weekly --write` also sends a one-line-per-site summary. Both go through `notify.command`
in `portfolio.json`, a shell command that reads Markdown on stdin; without it (or when it fails) a macOS
notification is shown. The owner's setup (2026-11-23) is the Feishu bot sending a direct message:
`<lark-cli binary> im +messages-send --as bot --user-id <owner open_id> --markdown -`. Use the Go binary
under `node_modules/@larksuite/cli/bin/` by absolute path: launchd has no `node` on its PATH. The launchd run has no agent: the weekly file then has numbers
and no proposals until the owner runs `/site-measure 周报`.
