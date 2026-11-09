# Validation (2026-10-01)

How site-measure was checked before release, and what changed because of it. Site IDs, traffic
numbers and private commit hashes are left out on purpose.

## Pilot: Release 1 on a real site

randtools (Next.js App Router on Cloudflare Workers) went through Release 1 with this skill, committed
locally: [references/example-randtools.md](references/example-randtools.md). It has not been deployed, so
the production proof (a real visit and a custom event in Umami) and the parallel check are still open.

## Light A/B, expectations registered before any run

Task: a read-only GA → Umami plan for a second Next.js App Router site (a travel tool) with GA guards,
custom events, a CSP, a privacy page and GA4 report scripts. A negative prompt asked only how to run that
site's GA4 report script.

| Expectation (with skill) | A: Claude, no skill | B: Claude, with skill | B: Codex, with skill |
| --- | --- | --- | --- |
| Scan first; plan names files per category | Read the code directly; covered most categories | `scan.py` first; every category | `scan.py` first |
| Two releases; GA out only after a parallel check | Yes (7 days) | Yes (14 days, with a gap threshold) | Yes (14 days, GA property time zone, gap threshold) |
| GA guards ported to before-send, each named | Yes | Yes, as a GA rule → Umami table | Yes, as a GA rule → Umami table |
| Real registration path, no placeholder ID | `add-website.py`; skipped umami-connect for lack of a query exclusion | umami-connect dry run; flagged the same gap | umami-connect dry run; final command with the new exclusion flags |
| GA4 report scripts left to the user | Kept them and proposed a new script without asking | Asked, with a recommendation per script | Recommended a split and listed it for confirmation |
| Approval before commit and deploy; no writes | Yes | Yes | Yes; the project's git status was unchanged |

- **Negative prompt (B):** answered directly how to run the script and which variables it reads, and
  noted that the question is outside the skill. It also ran the read-only scan, which was not needed.
- **Trigger wording:** the description covers "replace GA with Umami" and excludes "only reading existing
  GA4 reports".
- **Codex:** the first run used maximum reasoning effort and hit the 25-minute limit after steps 0 and 1.
  The repeat on the final skill, with high effort, finished in about 16 minutes and met every expectation.
  It also applied the rules added below:
  - the exclusion flags;
  - no `data-umami-event` on router links and no `window.umami` stub;
  - private event fields fixed at the source, and the early-event loss fixed in Release 1;
  - the server-log sentence;
  - the GA property's time zone.
  Its sandbox had no network, so it listed the GA stored-data check and the live-site checks as steps to
  run before Release 1.

**Reading:** the baseline was strong. It read the user's Umami tool and earlier integration notes, then
arrived at two releases and ported guards without the skill. The skill added a full inventory, explicit
user decisions and a parity test list. The with-skill run also found three problems the site already had:
GA storing query strings after client-side navigation, an event field carrying form values, and early
events lost before the GA loader ran. It found them by reading what GA had stored (counts only), which
the skill now asks for.

## Changes made because of the validation

1. umami-connect gained `--exclude-search` and `--exclude-hash`. Both arms found that the generated tag
   could not drop query strings, and before-send cannot stop query-only history changes from counting.
2. Premises checked in the Umami 3.4.0 tracker source:
   - `window.umami` is installed only when it is undefined;
   - `data-umami-event` links are replayed with `location.href`, which breaks client-side routing;
   - without `data-exclude-search`, query-only history changes count as pageviews.
3. Rule 4: private GA fields are fixed at the source for both tools; an existing early-event loss in the
   GA path is fixed in Release 1; no `data-umami-event` on router links.
4. Scan step: a read-only check of what GA actually stored, as counts only.
5. Parallel check in the GA property's time zone; `report.py --timezone`.
6. Privacy text checked against the analytics server:
   - Umami also stores the page title, screen size, language, region and city.
   - Its database keeps no IP addresses, but the Nginx access log records them.
   - The event-field wording now depends on what events carry.
   - site-kit 1.2.2 carries the same correction.
7. Delivery report: how the owner excludes their own visits (`localStorage` `umami.disabled`).

## Not yet verified

- Production behaviour: Release 1 has not shipped anywhere yet.
- Release 2 and the parallel check have not run on a real site.

# Validation: tracking plans, audit and funnels (2026-11-09)

Added `references/tracking-plans.md` (+ `.json`), `scripts/audit.py` and `scripts/funnel.py`, and the
"Tracking plan, audit and funnels" workflow. Checked on ToHD (tohd.video, site-kit 2.5.1, type `app`
with a free browser tool; code read-only at commit 86dbd80, deployed version e035c9cb). Website and
session IDs and the owner's location and screen are left out here; the full outputs are in the
session notes, outside the repo.

## Umami 3.4 API, probed before writing the scripts

- `/events` and `/sessions` page with `page` and `pageSize` (500 worked) and return
  `{data, count, page, pageSize, isCapped}`.
- Events carry `sessionId`, `eventType` (1 page view, 2 custom), `eventName`, `urlPath`, `hasData`.
  They also carry `city` and `device`, but not the screen size: exclusions are matched on sessions.
- `/event-data/:eventId` returns that event's rows (`dataKey`, `stringValue` or `numberValue`, `dataType`).
- `/event-data/properties`, `/event-data/fields?event=` and `/event-data/values?event=&propertyName=`
  aggregate over every session. For an event that never fired, they return `[]`, not an error.
  `funnel.py` therefore reads values per event when it excludes sessions, and falls back to these
  totals (saying so) only above `--max-event-data`.
- One Umami session spanned 7 visits over two days, so funnels are per visitor, not per visit.

## Audit on ToHD

`audit.py --project ~/Projects/tohd.video --type tool --type app` (the `.sitekit.json` type alone gives `app`):

- 26 event names: 19 from the site, 7 from the kit. Spreads like `...ctx.current` were resolved
  from the `useRef<{...}>` type and assignments in the same file. Both arms of
  `full ? 'tool_full' : 'tool_start'` were found, and so was the kit's
  `{ 'data-umami-event': 'pricing_buy', ... }` object.
- Every required role of both plans was filled. `tool_download` was added that morning; one commit
  earlier, `tool.tool_takeaway` would have been `MISS`.
- Naming: `'seconds' means two things`. On `tool_done` and `tool_preview` it is processing time
  (`elapsed()`); on `cloud_job_end` it is `Math.round(j.seconds)`, the job record's video length.
  This is the mistake found earlier, still present in the app's event.
- Fields: none private, none outside the allowlist.
- Privacy (`modules.legal.analyticsEvents`): no words in the text match `state` (the `tool_device`
  check), `from` (which link was clicked), `fits` or `partial`. Reading the text confirms the device
  check and the click placement are not disclosed. Fixing this is the site's job.
- Outside the plan: `cloud_uploaded` (fine). Non-literal call site: the kit's own `track` wrapper, as
  expected.

## Funnel report on ToHD, 2026-11-08 to 2026-11-09 (UTC)

`--list-sessions 10` showed one session with 68 page views and 40 events, plus a second one with the
same screen and city: the owner's testing. All runs used
`--steps 'path:/,tool_file,tool_start,tool_preview,tool_done,tool_download' --plan tool --plan app --fields`.

| | All sessions | Owner excluded (`--exclude-screen`, `--exclude-city`) |
| --- | --- | --- |
| Sessions | 20 | 18 (2 excluded) |
| Events | 152 (99 page views) | 28 (17 page views) |
| `path:/` | 18 | 16 |
| `tool_file` → `tool_start` → `tool_preview` | 1 → 1 → 1 | 0 |
| `tool_done`, `tool_download` | 0 | 0 |
| `tool_device.state` | ok 33, bad 11 | bad 11 (11 sessions) |
| `cloud_click` | 2 (`from` = `tool_4k_option`, `tool_4k_pricing`; the other fields empty) | 0 |

What this showed:

- Every tool use, every `cloud_click` and every `nav_account` in the first two days came from the owner.
- The other visitors' only events were 11 `tool_device` with `state=bad`. Those sessions are one page
  view each, often within the same minute, with screens such as 800x600 and 1024x1024. They look like
  automated previews passing the kit loader's bot filter, a lead to check in site-kit, not proof.
- `cloud_click` sent empty `res`, `length`, `mode` and `out`. The value counts make this visible as
  `(empty)`; the audit cannot see it, because the keys exist.
- The median time from step 1 was about 3.4 hours: the owner's first home-page view was in an
  earlier visit of the same session.
- `--plan tool` mapped `tool_done` to `tool_preview` (no `tool_done` had fired yet) and reported
  `tool_takeaway (no events seen)`. `--plan app` found no `/app` page view after the exclusion.
- With `--max-event-data 5`, `--field tool_device.state` fell back to the server totals
  (`ok 33, bad 11`, exclusions not applied) and said so.

## Checks

- `python3 -m unittest test_report test_scan test_audit test_funnel` in `scripts/`: 30 tests passed at release; 32 after the follow-up below.
  They cover synthetic projects (spreads, ternaries, attributes, kit events, private keys and values,
  a time key with two meanings, missing roles, the disclosure check) and a fake Umami (paging, ordered
  and any-order funnels, exclusion rules, plan alias mapping, per-event fields, server fallback).
- Credentials are read through the Umami tool only. No output prints a token, a username or a password.

## Not yet verified

- No A/B run of the new workflow with and without the skill. The ToHD session that asked for it
  serves as the baseline: the download event was missing, `seconds` meant the video length, the
  owner's session was mixed in, and `report.py` could not read fields.
- The audit has run on site-kit sites only. On other stacks it depends on literal event names; GA-style
  `gtag('event', ...)` calls are `scan.py`'s job, not the audit's.

## Follow-up: fixing ToHD with the skill (2026-11-09)

The owner approved the three code fixes from the audit; ToHD commit 0a06905, not deployed:

- `cloud_job_end` now sends `length` (band) and `seconds` (GPU time, `finished_at - started_at`);
- `cloud_click` sends file bands only when a file is loaded;
- `analyticsEvents` names the device check, the clicked cloud link, missing credits, partial
  batches and cloud processing time.

`npm run check` passed (types, build, astro check, 170 Workers tests, kit:check). The first run failed
in `astro check` on a spread of an optional `seconds` into `track()`'s data type, which was fixed with
a plain object. The re-audit reported no missing roles, no naming or field issues, no unresolved
spreads and no fields missing from the disclosure. That needed two audit fixes: spreads of helper
calls (`...fileCtx()`), and variables with a type annotation whose keys are added later
(`data.seconds = ...`). The kit's single `legal.effectiveDate` (shared by privacy and terms) was left
unchanged. Production proof (a `cloud_job_end` with GPU `seconds` in Umami) waits for a deploy and a
real cloud job.
