# Tracker, before-send and event bridge per stack

The before-send function must be defined before the tracker sends its first pageview (when the
document has finished loading). The tracker is `defer`/`afterInteractive`, so any code that runs during
HTML parsing or JavaScript module evaluation is early enough. A React effect is not guaranteed to be.

| Stack | Tracker | Before-send registration | Notes |
| --- | --- | --- | --- |
| Next.js App Router | `umami-connect` generates `components/UmamiAnalytics.tsx` (`next/script`, `afterInteractive`) and inserts it before `</body>` of the root layout | At module scope in a client module that a root-layout component imports: `if (typeof window !== 'undefined') window.siteUmamiBeforeSend = fn`. Module code runs before hydration; `afterInteractive` scripts load after it | Do not edit the generated component (the connector checks its hash); change attributes with the connector's flags. Keep that client import after GA is removed |
| Next.js Pages Router | Manual: `<Script strategy="afterInteractive" …>` in `pages/_app` or the tag in `pages/_document` | Module scope of a module imported by `pages/_app` | Pass `--website-id` only if you use the connector's HTML mode for something else |
| Astro | `umami-connect` generates `UmamiAnalytics.astro` (`is:inline defer`) before `</head>` | An `is:inline` script placed before the tracker in the same `<head>` | Several layouts: pass each with `--entry` |
| Vite or plain HTML, one `index.html` | `umami-connect` inserts the tag before `</head>` | Inline `<script>` before the tracker tag | Multi-page Vite: each page's HTML is an entry |
| Many static HTML pages loading one shared script | Add the tracker from the shared script (below). `umami-connect` cannot see it | Top of the shared script, before the tracker is appended | Listing 30 `--entry` files duplicates the tag 30 times |
| HTML partials included by a build plugin | Put the tag in the shared partial (umami-connect cannot target files without `</head>`); use `add-website.py --format id` for the ID | Inline script in the same partial, before the tag | Check the built HTML: exactly one tag per page |
| Worker SSR (string or JSX templates) | Manual: the shared `<head>` template; ID from `add-website.py` | Inline script before the tag | Update the CSP the Worker sends |

Add `www.<domain>` to `data-domains` (`--allow-domain`) only when pages are served on www. If www
redirects to the apex before any HTML loads, the apex is enough.

## Adding the tracker from a shared script

The tracker reads its settings from `document.currentScript`, so set the attributes before appending:

```js
var s = document.createElement('script');
s.defer = true;
s.src = 'https://analytics.plugxai.com/script.js';
s.setAttribute('data-website-id', '<website id>');
s.setAttribute('data-domains', 'example.com');
s.setAttribute('data-before-send', 'siteUmamiBeforeSend');
// Only when GA dropped every query string or fragment (SKILL.md rule 3):
// s.setAttribute('data-exclude-search', 'true');
// s.setAttribute('data-exclude-hash', 'true');
document.head.appendChild(s);
```

## Before-send template

```js
window.siteUmamiBeforeSend = function (type, payload) {
  try {
    if (isQaSession()) return false;        // ported from the GA QA flag (GA labelled it; Umami has no debug view)
    if (navigator.webdriver) return false;  // only if the GA code already excluded automation
    // URL scrubbing ported from GA: when GA dropped every query string or fragment, use the tracker's
    // exclusions (umami-connect --exclude-search / --exclude-hash) instead. Rewrite payload.url and
    // payload.referrer here only to remove some parameters.
    return payload;
  } catch (error) {
    return payload;                          // a broken rule must not silently stop all counting
  }
};
```

`type` is `event` for pageviews and custom events, plus `identify` and `performance` when those features are on.

## Event bridge with a bounded queue (TypeScript)

Call `sendUmami(name, params)` from the same function that calls `gtag('event', …)`, after the same
allowlisting, and pass only the fields Umami should store. The queue lives in a private variable: the
tracker installs `window.umami` only when it is undefined, so a stub there would keep the real API out.

```ts
type UmamiData = Record<string, string | number | boolean>;
declare global {
  interface Window { umami?: { track: (name: string, data?: UmamiData) => unknown } }
}

const umamiQueue: Array<[string, UmamiData]> = [];
let umamiWaiting = false;

function drainUmami(attempt: number) {
  const tracker = window.umami;
  if (tracker) {
    umamiWaiting = false;
    for (const [name, data] of umamiQueue.splice(0)) {
      try { tracker.track(name, data); } catch { /* analytics must never break the feature */ }
    }
  } else if (attempt < 50) {
    window.setTimeout(() => drainUmami(attempt + 1), 200);   // up to ~10 s for the deferred tracker
  } else {
    umamiWaiting = false;
    umamiQueue.length = 0;                                     // blocked tracker or non-production host
  }
}

export function sendUmami(name: string, params: Record<string, unknown>) {
  const data = Object.fromEntries(
    Object.entries(params).filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value)),
  ) as UmamiData;
  if (umamiQueue.length < 50) umamiQueue.push([name, data]);
  if (!umamiWaiting) { umamiWaiting = true; drainUmami(0); }
}
```

Production-host and QA checks stay where the project already applies them (the entry point and the
before-send function), so the queue never fills on localhost. GA4 event names are at most 40
characters, so bridged names fit Umami unchanged.

## Link clicks in single-page apps

The tracker's `data-umami-event` click handler cancels a link click and navigates with `location.href`
after sending. That is harmless on plain multi-page sites, but on client-side router links (Next.js
`<Link>`, React Router, Astro view transitions) every tracked click becomes a full page load. Keep the
project's own delegated click handler (for example a `data-event` attribute read by the analytics entry
point) and bridge from there. `data-umami-event` is fine on buttons.
