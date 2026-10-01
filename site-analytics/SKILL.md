---
name: site-analytics
description: Use when an existing website project (not a site-kit site) should start using the self-hosted Umami analytics, replace or remove Google Analytics (GA4, gtag.js, Google Tag Manager) in favor of Umami, finish a GA-to-Umami cutover after a parallel period, or pull Umami traffic and event reports. Also for 接入 Umami、用 Umami 替换 GA、去掉 GA、GA 迁移、统计迁移、Umami 报表. NOT for site-kit sites (their analytics live in site.config.ts) or for only reading existing GA4 reports.
---

# Site Analytics

Move existing sites from Google Analytics to the user's self-hosted Umami without losing visits,
events or truthful privacy text. It takes two releases: Umami next to GA first, GA out later.
Questions about running or reading GA4 reports when nothing is being migrated are out of scope:
answer them directly, without a scan or migration advice.

Scripts (Python 3.9+ stdlib, read-only):

- `python3 <skill-dir>/scripts/scan.py --project <dir> [--domain <host>] [--format json]`: inventory with
  file:line evidence, framework, phase, and a ready `umami-connect --dry-run` command when the layout is unambiguous.
- `python3 <skill-dir>/scripts/report.py --domain <host> [--days 7 | --start D --end D] [--daily] [--format json]`:
  Umami totals with the previous period, top pages, referrers, channels, events, countries.

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

## Delivery report

- Phase and release completed; files changed per category: loader, guards, events, CSP, privacy, tests,
  env names, reports.
- Each guard translation: GA rule → Umami behavior.
- Each verification step with its result: checks, commit, push, deploy, production evidence.
- What comes next (parallel end date or leftovers) and any decision the user still owes (report scripts,
  period length).
- How the owner keeps their own visits out: on the site, run `localStorage.setItem('umami.disabled', '1')`
  in the browser console once per browser.

## References

- [references/frameworks.md](references/frameworks.md): tracker and before-send placement per stack,
  plus the event queue.
- [references/privacy.md](references/privacy.md): disclosure paragraphs for both releases.
- [references/example-randtools.md](references/example-randtools.md): the first pilot (Next.js App Router).
