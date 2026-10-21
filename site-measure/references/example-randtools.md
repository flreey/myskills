# Pilot: randtools, Release 1 (2026-10-01)

A Next.js 16 App Router tool site on Cloudflare Workers (OpenNext). This records how Release 1 was
done and checked; it is not a deployment record.

## Scan

- Phase `ga-only`; `umami-connect` auto entry `src/app/layout.tsx`; domain `randtools.com`.
- GA in four places: `components/GoogleAnalytics.tsx` (gtag.js), `lib/analytics-bootstrap.ts`
  (gtag config, host check, QA flag), `lib/analytics.ts` (`send()` → `gtag('event')`), root layout.
- Guards: production hosts `randtools.com` and `www.randtools.com`; `?qa=1` sticky per tab in
  sessionStorage, which GA labels (`traffic_origin=qa`, `debug_mode`) instead of dropping.
- No CSP. Privacy and about pages name GA. Tests: `scripts/verify-analytics.mjs` (own GA behavior)
  and `scripts/verify-growth.mjs`, which was already failing: it called `trackGuideEvent`, removed in an
  earlier commit. A separate commit moved that check to `trackTaskEvent` and made it cover GA and Umami.
  No GA4 report scripts.
- Query strings hold only fixed option values (count, country, scene) and browser-local item IDs, never
  text people type.

## Decisions

| GA rule | Umami behavior |
| --- | --- |
| Hosts randtools.com, www.randtools.com | `data-domains="randtools.com"`; www is 301-redirected on the server before any HTML, so it is not listed |
| QA flag labels traffic | `randtoolsUmamiBeforeSend` returns `false` for QA sessions (Umami has no debug view) |
| Events from `send()` with an allowlist | Same call site sends to Umami: same names and fields, minus `traffic_origin`, `debug_mode`, `measurement_version` |
| Early events queued by the gtag stub | `src/lib/umami.ts` queues up to 50 events for about 10 s until `window.umami` exists |
| GA keeps full page URLs (no `page_location` rewrite) | No `--exclude-search`: Umami keeps the query strings too, which hold no personal data |

- The before-send function is registered at module scope in `analytics-bootstrap.ts`, which
  `GoogleAnalytics.tsx` imports in the root layout. Module code runs before hydration; the
  `afterInteractive` tracker is injected after it.
- `SiteInfo` showed one hard-coded "Updated" date on about, privacy, terms and guides. It now takes
  a per-page `updated` prop, so only the pages whose text changed show the new date.
- The first privacy paragraph listed too few fields. After checking the server it names the page title,
  screen size, language, region and city as well, and the analytics server's access log.
- Mode switches inside one tool page change only the query, with `history.pushState`. Umami counts each
  switch as a pageview; GA does so only when enhanced measurement's browser-history setting is on. Check
  that setting before reading the parallel numbers.

## Verification

- `verify-analytics.mjs`: five new checks, 15 in total.
  - The strongest check compares each Umami payload with the GA parameters minus the GA-only labels.
  - The other four cover: localhost sends nothing; QA is cancelled for the whole tab and resumes with
    `?qa=0`; a throwing tracker doesn't break a copy; the queue gives up after its wait window.
- `verify-growth.mjs` passes again: guide copies and downloads reach GA and Umami with exact payloads
  and no example content. Two seeded faults (analytics on localhost, an extra event field) make it fail.
- `next build`, `tsc --noEmit` and ESLint on the changed files were clean.
- Browser check on `next start`:
  - exactly one tracker tag, with the right ID, domains and before-send name;
  - `window.randtoolsUmamiBeforeSend` is a function;
  - no `/api/send` requests from localhost;
  - QA handling behaved as in the tests;
  - no console errors;
  - the server HTML holds only a preload link for `script.js`, not an executing tag, which proves the
    tracker runs after client module evaluation.

## Release 2 checklist for this site

1. Delete `GoogleAnalytics.tsx` and the GA parts of `analytics-bootstrap.ts` (`GA_ID`, gtag stub,
   `config`). Keep a client component in the root layout that imports the module registering
   `randtoolsUmamiBeforeSend`, and keep `analyticsAudience()` for the QA rule.
2. In `send()`, drop the gtag call; keep `sendUmami(action, context)`.
3. Remove `NEXT_PUBLIC_GA_ID` from `.env.example`.
4. Privacy page: delete the GA section and the Google opt-out link; keep Umami, Cloudflare,
   Google Fonts and the AdSense paragraph. About page: drop "Google Analytics".
5. Rewrite the dataLayer-based checks in `verify-analytics.mjs` and the GA half of `verify-growth.mjs`
   against the Umami bridge.
