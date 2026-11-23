---
name: site-measure
description: 统计与衡量和运营闭环：所有站的数据接入核对（Umami、Search Console、Bing、Cloudflare）、每日快照和守护提醒（核心事件归零、流量断崖、5xx）、组合周报（每站阶段、北极星、卡在哪一层、下周最多 3 个改动）、实验队列和到期复查、打法库，数据放在 ~/Projects/growth；已有网站（非 site-kit）接入自建 Umami、用 Umami 替换或移除 Google Analytics（GA4、gtag.js、GTM）、完成 GA 到 Umami 的并行切换时用；也用于按站点类型（工具、落地页、目录、应用、内容站）决定该埋哪些事件、对照埋点方案和隐私文案审计代码里的埋点、排除站长自测流量后读漏斗、转化率和事件字段分布、功能完成后建立衡量体系（Umami 漏斗和目标写进经过审核的配置文件），以及给任何站（含 site-kit 站）拉流量和事件报表。Also for 周报、运营复盘、数据闭环、北极星指标、看哪些数据、数据接入是否完整、站点阶段、该下线哪个站、实验复查、接入 Umami、用 Umami 替换 GA、去掉 GA、GA 迁移、Umami 报表、埋点方案、埋点审计、漏斗、转化率、衡量体系。不用于：给 site-kit 站接入统计代码（kit 从 site.config.ts 自动加载，方案、审计和报表仍适用），或只读现有 GA4 报表。
---

# site-measure: Umami analytics

Move existing sites from Google Analytics to the user's self-hosted Umami without losing visits,
events or truthful privacy text. It takes two releases: Umami next to GA first, GA out later.
It also decides which events a site should send for its type, audits the tracking calls a project
has, reads funnels and event fields from Umami, and keeps each site's saved Umami funnels and goals
in a spec file it syncs (any site, site-kit sites included). Across all sites it runs the operating
loop: a data-sources check, daily snapshots and guard alerts, the weekly portfolio review, and the
experiment queue ([references/operating-loop.md](references/operating-loop.md)).
Questions about running or reading GA4 reports when nothing is being migrated are out of scope:
answer them directly, without a scan or migration advice.

Scripts (Python 3.9+ stdlib; read-only toward every source except `umami_reports.py sync --apply`):

- `python3 <skill-dir>/scripts/ops.py init | check | collect | guard | weekly | schedule`: the operating loop
  over `~/Projects/growth/portfolio.json`. `check [--site host]` lists, per site, Umami (website, 7-day
  pageviews, the north-star and core events), Search Console (property, sitemap read), Bing and Cloudflare
  (or a missing credential); `collect [--days N]` upserts daily numbers into `data/snapshots.sqlite`
  (a first backfill of 60 days takes several minutes); `guard` collects, checks and alerts;
  `weekly [--date D] [--write]` writes `weekly/<year>-W<nn>.md`; `schedule [--install]` sets up launchd.

- `python3 <skill-dir>/scripts/scan.py --project <dir> [--domain <host>] [--format json]`: inventory with
  file:line evidence, framework, phase, and a ready `umami-connect --dry-run` command when the layout is unambiguous.
- `python3 <skill-dir>/scripts/report.py --domain <host> [--days 7 | --start D --end D] [--daily] [--format json]`:
  Umami totals with the previous period, top pages, referrers, channels, events, countries. It reads any
  website registered in Umami, site-kit sites included; only the migration steps are limited to non-kit sites.
- `python3 <skill-dir>/scripts/audit.py --project <dir> [--type tool --type app] [--privacy <file>] [--format json]`:
  the project's `track(` / `umami.track(` / `data-umami-event` call sites against the plan for its type
  (from `.sitekit.json`, or `--type`, repeatable): missing required events, naming problems (style,
  near-duplicates, a time key that means processing time in one event and the input's length in
  another), private-looking or non-allowlisted fields, and the fields the privacy text never mentions.
- `python3 <skill-dir>/scripts/funnel.py --domain <host> [--days 14] [--steps 'path:/,a,b|c,d'] [--plan <type>]
  [--fields | --field event.key] [--exclude-session ID] [--exclude-screen WxH] [--exclude-city C]
  [--exclude-country CC] [--exclude-device D] [--list-sessions N] [--format json]`: per-session ordered
  funnels with step and overall conversion, event counts, string-field value counts and number spreads
  (`seconds`, `msPerFrame`), all with the matching sessions left out.
- `python3 <skill-dir>/scripts/umami_reports.py draft --project <dir> [--type t]...`, then
  `sync --spec <project>/umami-reports.json [--apply]` and `status (--spec <file> | --domain <host>) [--days 14]`:
  drafts the site's saved funnels and goals from its plan and the events its code sends (choices it cannot
  make go into `todo`), creates or updates them in Umami by name (preview unless `--apply`; never deletes),
  and reads their numbers. Step syntax: `path:/x`, `event`, `event[key=value;key!=value]`, `*` at either end.

The user's Umami tool does registration and layout wiring: `~/Projects/umami` (override with `UMAMI_TOOL_ROOT`).

- `umami-connect <domain> --project <dir> --name "<Site>" [--framework next|astro|html] [--entry <layout>]...
  [--allow-domain www.<domain>] [--before-send <fn>] [--exclude-search] [--exclude-hash] [--dry-run]`: creates
  or reuses the Umami website, writes the public `umami.config.json`, and inserts the tracker into the shared
  layout. It stops instead of guessing when it cannot pick one layout. Re-running it is idempotent, and
  `--before-send` and the exclusions stay on once set.
- `scripts/add-website.py <domain> --format id`: the website ID only, for stacks you wire by hand.
- Credentials: `credentials.local.txt` in that folder or `UMAMI_API_KEY`. They never go into a project, page or commit.

## Premises (checked 2026-10-01)

- Umami 3.4.0 at `https://analytics.plugxai.com`. Tracker attributes: `data-website-id`, `data-domains`,
  `data-before-send`, `data-tag`, `data-exclude-search`, `data-exclude-hash`, `data-do-not-track`, `data-auto-track`.
- The tracker skips only hosts outside `data-domains`, browsers with `localStorage['umami.disabled']`, and
  Do Not Track when `data-do-not-track="true"`. It has no QA, internal-traffic or `navigator.webdriver`
  filter; the server drops bot user agents only. Project rules belong in a before-send function.
- `data-before-send` names a global function looked up at every send. It receives `(type, payload)`;
  a falsy return cancels the send. It must exist before the first pageview, which the tracker sends
  once the document has loaded.
- `window.umami` exists only after the tracker script runs, so events fired earlier are lost unless queued.
  `umami.track(name, data)` takes string, number and boolean values. The tracker installs `window.umami`
  only when it is undefined: never define it yourself as a stub or queue.
- `data-exclude-search` and `data-exclude-hash` strip the query string or fragment from both the page URL
  and the referrer. Without `data-exclude-search`, every history change that only edits the query (filters,
  tabs, variants via `replaceState`) sends another pageview.
- Clicks on a link with `data-umami-event` are cancelled, then replayed with `location.href` after the send.
  On client-side router links (Next.js `<Link>`, React Router) that turns navigation into a full page load.
- The server stores the page URL with its query string, the page title, referrer, browser, OS, device,
  screen size, language, and country, region and city from an IP lookup. Its database keeps no IP addresses,
  but the Nginx access log on the analytics host records visitor IPs (the host is DNS-only, not proxied).
- Report API: `/stats` returns pageviews, visitors, visits, bounces, totaltime and a `comparison` period;
  `/metrics?type=path|referrer|channel|event|country` returns `[{x, y}]`. `type=url` is gone (HTTP 400).
- Event API (checked 2026-11-09): `/events` and `/sessions` page with `page`/`pageSize` and return
  `{data, count, isCapped}`; an event has `sessionId`, `createdAt`, `eventType` (1 page view, 2 custom),
  `eventName`, `urlPath`, `hasData`; a session has `screen`, `city`, `country`, `device`, `visits`.
  `/event-data/:eventId` returns one event's fields; `/event-data/properties`, `/event-data/fields?event=`
  and `/event-data/values?event=&propertyName=` are server totals over every session (no exclusions).
  A Umami session can span several visits and days.
- Saved reports API (checked 2026-11-09 against the v3.4.0 source): `/api/websites/:id/funnels` and `/goals`
  list (GET) and create (POST `{name, description, parameters}`); POST `/:reportId` updates, DELETE removes;
  `/:reportId/stats?startAt&endAt` computes. Funnel parameters `{window, steps}`: `window` is minutes between
  consecutive steps, 2 to 8 steps of `{type: path|event, value, filters?}`, `filters` (events only) are
  `{property, operator: eq|neq|c|dnc, value}`. Goal parameters `{type: path|event, value}`, no filters.
  A value starting or ending with `*` becomes SQL `like`; otherwise it matches exactly. One value per step:
  no alternatives. Saved reports count every session, the owner's too.
- site-kit sites switch with `analytics.umami` in `site.config.ts` and `sitekit.py --root <site> umami --apply`.
  Never run umami-connect on them; it edits layouts the kit owns.

## Iron rules

1. **Scan first.** Run `scan.py` before planning or editing. The plan names the files in every category
   it lists, and you read each flagged file before changing it. Uncommitted changes in files you need:
   stop and ask.
2. **Two releases.** Release 1 adds Umami while GA keeps running and sends every custom event to both.
   GA comes out only in Release 2, after the parallel period the user chose (default 1–2 weeks) and a
   numbers check. Replace in one release only when the user asks for it after hearing what is lost: the
   comparison window that catches lost events, broken guards and uncovered layouts.
3. **Port the guards; never invent them.** Every rule the GA code applies (production hosts, QA flags,
   opt-outs, internal-traffic switches, automation filters, URL scrubbing) gets an Umami equivalent in the
   before-send function or a `data-*` attribute. A GA label with no Umami equivalent (`debug_mode`,
   `traffic_origin`, `traffic_type`) becomes an exclusion only for explicit signals: a QA flag, an internal
   flag, `navigator.webdriver`. Heuristic "candidates" keep counting. URL scrubbing that drops every query
   string or fragment maps to `--exclude-search` / `--exclude-hash`; dropping only some parameters maps to
   rewriting `payload.url` and `payload.referrer` in before-send. Report every translation, and add no
   filter the project never had without asking.
4. **One event path.** Bridge inside the project's existing analytics entry point: same event names, same
   allowlisted fields, no generated content, no GA-only fields. Queue events fired before `window.umami`
   exists (bounded, a few seconds) and flush them in order. An analytics failure never breaks the feature.
   - A GA field that carries private data (a URL with its query, dates, free text, IDs) is not copied:
     fix it at the source for both tools, with the user's approval.
   - If the GA path already drops early events (they fire before its loader defines the entry point),
     fix that in Release 1 and note the expected jump in GA counts.
   - Never put `data-umami-event` on client-side router links; send those events from the entry point.
5. **Privacy text matches what runs.** Release 1 discloses GA and Umami; Release 2 removes the GA wording.
   Describe what Umami really records ([references/privacy.md](references/privacy.md)). Ads and other
   analytics stay disclosed: never write "no cookies" while ads or other cookie-setting scripts run.
   Change the "last updated" date only on pages whose text changed; if several pages share one hard-coded
   date, make it per page first.
6. **Keep GA history and reports honest.** Never delete the GA property or its data. Each GA4 report
   script moves to `report.py` or retires, and the user decides which. Never leave a script silently
   reading a property that stopped receiving data.
7. **Approvals and evidence.** Commits, pushes and deploys need the user's approval. Report local checks,
   commit, push, deploy and production verification separately. Production proof is a real visit and a
   custom event showing up in Umami, not a passing build.

## Workflow

### 0. Scan

| `phase` | Meaning | Next |
| --- | --- | --- |
| `ga-only` | GA runs, no Umami | Release 1 |
| `parallel` | Both are in the code (`scan.py` shows the commit date; production starts at the deploy) | Parallel check, then Release 2 |
| `umami-only` | GA gone | Remove the leftovers it lists (env names, CSP, privacy text, reports, checks) |
| `none` | No GA | Release 1 without the event bridge |

When the project has read-only GA4 report access, also check what GA actually stored, as counts only and
never printing values: page locations or referrers with query strings, site-search terms, and event
parameters holding URLs or dates. Some leaks happen only after client-side navigation, where a code scan
cannot see them.

### 1. Release 1: Umami next to GA

1. **Where the tracker goes.** Use the scan's preview command, or pick entries per
   [references/frameworks.md](references/frameworks.md). Many HTML pages or a shared partial: wire the
   shared include or script instead of listing every page. Add `--allow-domain www.<domain>` only if the
   site serves pages on www, and `--exclude-search` / `--exclude-hash` when rule 3 calls for them.
2. **Guards.** Write `<site>UmamiBeforeSend(type, payload)` with the ported rules (rule 3). Define it
   somewhere that runs before the tracker loads ([references/frameworks.md](references/frameworks.md)),
   then pass `--before-send <name>`.
3. **Connect.** Run `umami-connect` without `--dry-run` (creates or reuses the website). Commit
   `umami.config.json`; it holds only public values.
4. **Events.** Bridge them in the analytics entry point with the bounded queue (rule 4;
   [references/frameworks.md](references/frameworks.md) has the code).
5. **CSP.** Wherever a CSP exists (headers file, framework config, Worker, meta tag), add
   `https://analytics.plugxai.com` to `script-src` and `connect-src`.
6. **Privacy.** Add the Umami paragraph and keep GA ([references/privacy.md](references/privacy.md)).
7. **Tests.** Extend the project's analytics tests:
   - each Umami payload equals the GA parameters minus the GA-only labels (the strongest parity check);
   - non-production hosts send nothing;
   - early events are queued and flushed once, in order;
   - before-send cancels QA and automation sessions;
   - payloads carry no private fields.
   Update checks that assert the old setup. A check that was already failing before your change is
   reported with its cause, not silently fixed or skipped.
8. **Local verification.** Run the build and the project's checks. Then open the local build in a real
   browser and confirm:
   - exactly one tracker tag with the right `data-website-id` and `data-domains`;
   - the before-send function exists, and the server HTML holds no executing tracker tag (Next.js
     renders only a preload link for `afterInteractive` scripts), so the tracker runs after it;
   - no `/api/send` requests from localhost;
   - no console errors.
9. **Release.** Commit and deploy, each with the user's approval. In production, open a page in the user's
   normal browser (the ported guards may drop automated browsers), trigger one custom event, and confirm
   both with `report.py --days 1`. Record the parallel start date in the project's notes.

### 2. Parallel check (before Release 2)

Run `report.py --start <day> --end <day> --daily --timezone <zone>` and the project's GA report for the
same days. GA counts days in the property's time zone (Admin → Property details), so pass that zone;
UTC days match only a UTC property. Compare pageviews, visitors and the main events. Umami usually counts
more (fewer blockers, no consent mode). Explain any gap above about 30% before removing GA. Usual causes:
missing or late before-send, lost early events, wrong `data-domains`, layouts the tracker does not cover,
query-only URL changes counted as pageviews.

### 3. Release 2: remove GA

1. Delete GA loaders, components and snippets, measurement IDs and GA env names (`scan.py` lists them).
   Keep the module that registers the before-send function loaded on every page.
2. Drop GA-only fields from events; keep the Umami bridge and the queue.
3. Remove Google Analytics and Tag Manager domains from the CSP. Keep the domains ads still need.
4. Privacy and about text: remove the GA wording; keep Umami, ads and other analytics.
5. Checks and tests: rewrite GA assertions; delete only tests of code that is gone.
6. Report scripts: switch each one to `report.py` or remove it, as the user decided.
7. Re-run `scan.py`: it should report `umami-only` with no leftovers, except approved exceptions you list.
8. Commit and deploy with approval. In production, confirm there are no requests to
   google-analytics.com or googletagmanager.com, and that Umami still records pageviews and events.

## Tracking plan, audit and funnels

For any site, site-kit sites included, when the question is which events to send, whether the code
sends them, or where visitors drop. Plans per type: [references/tracking-plans.md](references/tracking-plans.md).

1. **Type.** Take it from `.sitekit.json` (`site.type`) or ask; a site that is two things (a free tool
   plus a paid app) takes both. Write the type's core question at the top of the plan.
2. **Audit.** Run `audit.py`. Read every `MISS`, naming and field line before proposing changes; open
   each flagged call site. The privacy section is keyword matching: read the disclosure against the
   event list and say which fields it does not cover.
3. **Plan the change.** Missing events, renamed keys and dropped private fields go in one list with the
   files to edit and the privacy sentence to add. Changing event code is a project edit (commit and deploy
   approval as usual). On site-kit sites edit only the site's own code and `modules.legal.analyticsEvents`;
   kit events (`src/kit/**`) change in the kit, and a generic event name moves into the kit only when a
   second site needs it. Renaming an event or key breaks its history: keep the old name unless it is wrong.
4. **Owner traffic.** Run `funnel.py --list-sessions 10` first. Agree with the owner which sessions are
   theirs (screen, city, device, one very busy session), then exclude them in every funnel reported. Tell
   them to set `umami.disabled` (Delivery report) so new visits stay out; old ones stay in Umami.
5. **Funnels.** Use the plan's funnel (`--plan <type>`) or the site's own steps (`--steps`). Report each
   step's sessions, conversion from the previous step and from the first, and the exclusions used. Small
   numbers (under about 30 sessions at a step) are anecdotes: say so instead of quoting rates.
6. **Fields.** `--fields` for distributions; numbers are only meaningful if the audit found the key means
   one thing. `report.py` does not read fields; use `funnel.py` for them.

## Measurement system (after the features are built)

When a site's features work and the owner wants to see, from then on, whether visitors use and pay for
them. It turns the tracking plan into saved Umami funnels and goals the owner can open in the Umami UI,
kept in one spec file in the project so they change with the code.

1. **Events first.** Run the audit (section above) and fix its `MISS` lines; a funnel step with no event
   behind it stays at zero. A step needs an event that has shipped: `sync` warns about steps not seen in
   the last 30 days.
2. **Draft.** `umami_reports.py draft --project <dir>` (both types for a two-sided site). Each plan funnel
   (`funnel`, `more_funnels`) and goal (`goals`) in `tracking-plans.json` becomes an entry. Write it to
   `umami-reports.json` at the repository root (next to `umami.config.json` on non-kit sites; on site-kit
   sites outside the kit-owned paths). Add `standard` (the site's event names for `core_start`,
   `core_done`, `takeaway`, `error`, `paid`) and `northStar`; the operating loop reads them and `sync`
   ignores them.
3. **Resolve `todo` from the code, not the names.** Umami takes one value per step, so for each role with
   several events read the flow: steps the UI forces in order become consecutive steps (ToHD: preview
   before the full run, so `tool_start` → `tool_preview` → `tool_full` → `tool_done`); alternatives that
   are not ordered get one funnel each or the main one. Replace path placeholders with real paths, add
   field filters where one value means success (`cloud_job_end[status=done]`), set `window` (default 1440
   minutes), and give names the owner reads in the Umami UI. Show the owner the funnels and goals and
   empty `todo`.
4. **Sync.** `sync --spec umami-reports.json` previews: `+` create, `~` update, `=` unchanged, `?` saved in
   Umami but not in the spec (left alone, never deleted). Writing to Umami needs the owner's approval; then
   `--apply`, and `status` to confirm each report computes. Commit the spec and note it in the project's
   notes (README or the site notes) with the usual commit approval.
5. **Keep it current.** An event rename, a new step or a new paid path changes the spec in the same change
   as the code; re-run `sync` after it ships. Renaming a saved report creates a new one and leaves the old
   one as `?`: remove that one in the Umami UI if the owner wants it gone.
6. **Read it honestly.** The Umami UI and `status` include the owner's sessions. Quote numbers from
   `funnel.py` with the exclusions (`status` prints the matching `--steps`; field filters are not in
   funnel.py), and treat steps under about 30 sessions as anecdotes.

## Operating loop (all sites)

When the owner asks what to look at, whether data is complete, for the weekly review, which site to
work on or retire, or to review an experiment. Rules: [references/operating-loop.md](references/operating-loop.md).

1. **Data before numbers.** Run `ops.py check`. A failing Umami or north-star line makes that site's
   numbers untrustworthy: list it first, with the fix (register, map `standard`, add the missing event,
   verify Search Console, add the site in Bing). Fixes that write to Umami, Search Console or Bing, or
   change and deploy a site, need the owner's approval.
2. **Weekly.** `ops.py weekly --write` (launchd may have written it already), then follow the review
   steps in the reference: due experiments first, then at most 3 proposed changes across all sites, then
   stage suggestions. Proposals go to the weekly file and `experiments.json` as `proposed`; the owner
   approves before anything runs. Executing a change belongs to the skill that owns it (`/ui`, `ui-flow`,
   `site-batch`, `site-offsite`, `site-geo`, `site-stripe`, the site's code).
3. **Guard.** An alert is checked against the site before anything else: a zero core event after a
   deploy is usually broken tracking, not lost users.
4. **New site.** At launch the site joins `portfolio.json` as `validate` (`ops.py init` adds new ones
   and keeps existing entries) and `ops.py check --site <domain>` passes; site-kit stage 5 requires it.
5. **Credentials.** Bing key and Cloudflare token live in `~/Projects/growth/credentials.local.json`
   (or `BING_API_KEY`, `CLOUDFLARE_API_TOKEN`); ask for them through the secret prompt, never in chat.

## Counting AI assistant visits

When a report needs AI traffic on its own:

- Match the referrer or `utm_source` against
  `chatgpt\.com|openai\.com|perplexity|claude\.ai|gemini\.google\.com|copilot\.microsoft\.com|copilot\.com|deepseek|grok\.com`.
  This list came from a third-party guide and is not vendor-documented, so check it against the site's
  own referrers first.
- This is a lower bound. ChatGPT's web app can open links with `noreferrer` and no `utm_source`, so
  those visits count as direct. Report direct visits to deep pages as a separate, unproven number.
- To tie later signups or purchases to the first source, keep the first visit's `utm_source` and
  referrer domain in first-party storage. Keep them only with the user's approval and disclose them
  (rule 5).
- Take each total from one source. The same visits seen in GA4, Umami and Cloudflare must not be added.

## Delivery report

- Phase and release completed; files changed per category: loader, guards, events, CSP, privacy, tests,
  env names, reports.
- Each guard translation: GA rule → Umami behavior.
- Each verification step with its result: checks, commit, push, deploy, production evidence.
- Measurement system: the spec file, each saved funnel and goal with its sync result (created, updated,
  unchanged, left alone), the steps `sync` warned about, and where the project notes record them.
- What comes next (parallel end date or leftovers) and any decision the user still owes (report scripts,
  period length).
- Operating loop: the check result (failing items first), the weekly file path, proposals waiting for
  approval, stage suggestions, and any alert with what it turned out to be.
- How the owner keeps their own visits out: on the site, run `localStorage.setItem('umami.disabled', '1')`
  in the browser console once per browser.

## References

- [references/frameworks.md](references/frameworks.md): tracker and before-send placement per stack,
  plus the event queue.
- [references/privacy.md](references/privacy.md): disclosure paragraphs for both releases.
- [references/example-randtools.md](references/example-randtools.md): the first pilot (Next.js App Router).
- [references/tracking-plans.md](references/tracking-plans.md): events, fields, funnels and common misses per
  site type, with ToHD as the tool + app example; [references/tracking-plans.json](references/tracking-plans.json)
  is the machine-readable half the scripts use (with each type's `standard` events and `north_star`).
- [references/operating-loop.md](references/operating-loop.md): layers, growth home files, standard events,
  stages and thresholds, stuck layer → lever, the weekly review, data sources and automation.
