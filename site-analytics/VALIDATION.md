# Validation (2026-10-01)

How site-analytics was checked before release, and what changed because of it. Site IDs, traffic
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
