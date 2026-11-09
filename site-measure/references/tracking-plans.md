# Tracking plans by site type

Which events a site needs, what they may carry, and which funnel answers the site's core question.
The types are site-kit's (`tool`, `landing`, `directory`, `app`) plus content sites. A site that is
two things at once (ToHD: a free tool plus a paid app) takes both plans. The machine-readable half,
with the alias patterns, lives in [tracking-plans.json](tracking-plans.json); `scripts/audit.py`
checks a project against it and `scripts/funnel.py --plan <type>` builds the standard funnel from it.

## Rules for every plan

- **Name events `<area>_<what happened>`** in snake_case, past or present but the same across the site:
  `tool_start`, `tool_done`, `checkout_start`. One name per thing: if the free tool and the app both
  "start", they are `tool_start` and `cloud_start`, not `start` with a `where` field.
- **Fields carry bands and numbers only.** Resolution band (`480p`), length band (`30s to 2m`), mode,
  output size, counts, credits, milliseconds, an error category. Never a file name, a typed input, a
  search query, an email, a URL with its query, a page title (the page URL is already on the event),
  a free-text error message, or any ID that points at a person.
- **Name what a number measures.** `seconds` on a done event is how long the work took (wall clock from
  start to result). The input's own length is a band in `length`, or `inputSeconds` if it has to be a
  number. Never use one key for both across events.
- **Every attempt has an end.** A start without a done, error or cancel event leaves you guessing
  whether people waited, gave up or hit a bug.
- **The result has a take-away event.** Download, copy, share, export: the moment the visitor got
  value. Without it the funnel stops at "the tool worked", which is not "the visitor used it".
- **Placement goes in `from`.** Several buttons leading to the same place send one event name with
  `from=<placement>` (`tool_hint`, `app_bar`), not one event name per button.
- **Disclose what runs.** The privacy text lists what events carry (site-kit: `modules.legal.analyticsEvents`;
  the kit adds its own paid-funnel sentence on sites that sell). New field, new disclosure.
- **Router links:** send the event from code, never with `data-umami-event` on a client-side router
  link (SKILL.md rule 4). Plain `<a>` to another page or a new tab is fine.

## tool: browser tools

**Core question:** do visitors who land on a tool page give it an input, get a result and take the
result away? Where do they drop, and how slow is it on their device?

| Role | Example names | Fields |
| --- | --- | --- |
| input given | `tool_file`, `tool_input` | input bands (`res`, `length`, `size`), settings (`mode`, `out`) |
| run started | `tool_start` (and `tool_full` for a second, longer run) | settings at start |
| result ready | `tool_done`, `tool_preview` | `seconds` (processing wall clock), speed (`msPerFrame`), `backend` |
| failed | `tool_error` | `reason` category from a fixed list |
| take-away | `tool_download`, `tool_copy` | settings of the result |
| cancelled (opt.) | `tool_cancel` | settings |
| rejected input or device (opt.) | `tool_too_long`, `tool_device` | `length` band, `state` |
| upsell click (opt.) | `cloud_click` | `from` |

**Funnel:** tool page view → input → start → result → take-away. Read it per input band: a drop at
"result" that only hits `1080p+` is a speed problem, not a copy problem.

**Common misses:** no take-away event (the result link is a plain `<a download>` nobody tracks); no
done event, only start; `seconds` filled with the input's length; errors sent with the raw message;
the device check fired on every page view and read as usage.

## landing: product or extension marketing

**Core question:** does the page get visitors to take its one main action (install, start, buy, join
the waitlist), and which placement earns the click?

| Role | Example names | Fields |
| --- | --- | --- |
| main CTA | `cta_click`, `install_click`, `store_click` | `from` (hero, pricing, footer) |
| waitlist (opt.) | `waitlist_submit` | `from` |
| pricing buy (kit) | `pricing_buy` | `product`, `plan` |
| checkout (kit) | `checkout_start`, `checkout_cancel`, `checkout_error` | `product`, `status`, `error` code |
| paid (kit) | `purchase` | `product`, `amount` (minor units), `currency` |

**Funnel:** home view → main CTA → pricing buy → checkout start → purchase (or home → waitlist).

**Common misses:** store and install links leave the site untracked; one event per button instead of
`from`; the waitlist form counts page views of `/thanks` but not failed submits.

## directory: hub, group and item pages

**Core question:** do visitors find an item (search, filter or browse) and leave to it? Which hubs and
items send the clicks out?

| Role | Example names | Fields |
| --- | --- | --- |
| search or filter (opt.) | `search`, `filter_set` | result-count band, filter kind; never the query text |
| outbound click | `outbound_click`, `visit_site` | `from` (card, item page), `category`, `position` |
| submit (opt.) | `submit_item` | `category` |

**Funnel:** hub view → item view (`path:` steps) → outbound click.

**Common misses:** outbound links are plain `target="_blank"` anchors with no event; the search box
sends what was typed; the item slug is sent as a field when the page URL already says it.

## app: sign-in, credits, payments

**Core question:** do visitors sign in, reach a first real job (activation), hit the paywall, pay, and
get their results out?

| Role | Example names | Fields |
| --- | --- | --- |
| account click (kit) | `nav_account` | none |
| job started | `cloud_start` | `tier`, `out`, `files`, `credits`, `partial` |
| job ended | `cloud_job_end` | `status`, `out`, processing `seconds` |
| job error | `cloud_start_error`, `cloud_upload_error` | `reason` code |
| result download | `cloud_download` | `out` |
| paywall hit | `cloud_short` | `tier`, `missing` credits, `fits` |
| buy clicks (kit) | `pricing_buy`, `billing_buy`, `buy_click` | `product`, `plan`, `from` |
| checkout and purchase (kit) | `checkout_start`, `checkout_cancel`, `checkout_error`, `purchase` | `product`, `amount`, `currency` |

**Funnels:** activation: `/app` view → job start → job end → download. Paid: paywall or pricing view →
buy click → checkout start → purchase.

**Common misses:** a job-end event whose `seconds` is the input's length (the job record's `seconds`
column often is); no download event for results fetched from storage; sign-up has no event because
the auth provider's pages are off-site (count the first `/app` view after `nav_account` instead).

## content: articles and guides

**Core question:** which articles bring readers who read on and then take the site's action (open the
tool, sign up, click an affiliate link)?

| Role | Example names | Fields |
| --- | --- | --- |
| read depth (opt.) | `read_75`, `read_complete` | `depth` band |
| CTA click | `cta_click`, `tool_click` | `from` (inline, end of article), `position` |
| outbound or affiliate (opt.) | `outbound_click`, `affiliate_click` | `from`, `category` |
| subscribe (opt.) | `subscribe` | `from` |

**Funnel:** article view → read depth → CTA click.

**Common misses:** average time on page read as reading (tabs left open); the article title sent as a
field; every link tracked, so the CTA drowns.

## Example: ToHD (tool + app, site-kit 2.5)

Site events go through `site/src/site/components/track.ts` (`track(name, data)`, numbers and bands only;
`resBucket` and `lengthBucket` make the bands). The kit adds its paid-funnel events in `src/kit/**`.

| Role | ToHD event | Source | Fields |
| --- | --- | --- | --- |
| device check | `tool_device` | `components/Upscaler.tsx` | `state` (ok, warn, bad) |
| input given | `tool_file` | Upscaler | `res`, `length`, `mode`, `out` |
| input rejected | `tool_too_long` | Upscaler | `length` |
| run started | `tool_start` (10-second preview), `tool_full` | Upscaler | `res`, `length`, `mode`, `out` |
| result ready | `tool_preview`, `tool_done` | Upscaler | + `msPerFrame`, `backend`, `seconds` (wall clock since start, model download included) |
| failed / cancelled | `tool_error` (`reason`), `tool_cancel` | Upscaler | settings |
| take-away | `tool_download` | Upscaler | settings (added 2026-11-09; before that, results were never counted) |
| upsell | `cloud_click` | Upscaler | `from` (`tool_hint`, `tool_4k_option`, `tool_4k_start`, `tool_4k_pricing`) + settings |
| paywall | `cloud_short` | `app/App.tsx` | `tier`, `files`, `missing`, `fits` |
| job | `cloud_start`, `cloud_uploaded`, `cloud_job_end`, `cloud_start_error`, `cloud_upload_error`, `cloud_download` | App.tsx | `tier`, `out`, `files`, `credits`, `partial`, `status`, `reason` |
| buy click | `buy_click` (`from=app_bar`, `app_short`) | App.tsx, `data-umami-event` | `from` |
| kit paid funnel | `pricing_buy`, `billing_buy`, `nav_account`, `checkout_*`, `purchase` | `src/kit/ui/**` | `product`, `plan`, `amount`, `currency`, `status`, `error` |

Funnels used for ToHD:

```text
python3 scripts/funnel.py --domain tohd.video --days 14 \
  --steps 'path:/,tool_file,tool_start,tool_preview,tool_done,tool_download' --exclude-screen <owner WxH>
python3 scripts/funnel.py --domain tohd.video --days 14 --plan tool --plan app --fields --exclude-city '<owner city>'
```

Lessons from ToHD, now in the rules above:

- The download of the result had no event, so "used the tool" could not be told from "watched it run".
- `seconds` first meant the video length; it now means processing time on `tool_preview` and
  `tool_done`. `cloud_job_end.seconds` still comes from the job record, which is the video length:
  the audit flags that key as meaning two things.
- The owner's own test session was most of the early events (one session, dozens of events); funnels
  are read with the owner's sessions excluded (`--exclude-session`, `--exclude-screen`, `--exclude-city`).
