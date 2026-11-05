# ChatGPT probes (checks G3 and G4)

Run in ChatGPT with web search available. Use a temporary chat, or a fresh chat with memory off,
so earlier conversations do not steer the answer. Ask in the language of the site's market.
Repeat each probe three times in fresh chats; record every run.

Record per run: date (UTC), model name shown in ChatGPT, thinking effort, temporary chat yes/no,
whether it searched (sources shown), the prompt exactly, the full answer, and for probe B the
search queries it ran, or "not captured" (section D).

## A. Can it open the page (check G3)

```text
Open <URL> and tell me, quoting the page itself:
1. the page title,
2. the first heading,
3. the first two sentences of the main text,
4. the questions in its FAQ section.
If you cannot open the page, say so and say what error you got. Do not guess from other sources.
```

- Pass: the quotes match the raw HTML from `page_check.py`.
- Fail: it cannot open the page, quotes a different or older version, or the answer only paraphrases
  search snippets. Compare with the robots.txt and probe results to find which layer blocks it.
- A newly published or changed page may need time before ChatGPT search reflects it; a failed
  open of a live, unblocked URL is still a fail.

## B. Unbranded recommendation (check G4)

Use the page's target query as a user would ask it; two or three variants.

```text
I want to <the user's task, e.g. generate a strong random password without installing anything>.
Which websites or tools would you recommend? Give me the top 5 with one line each on why.
```

Record: is the site named, is it linked (a clickable link, not just the name), is it the first
recommendation, what is said about it, which sites appear instead and why they were chosen.

Report named, linked and first as counts over runs in one mode, such as linked 3/9, with the dates.
Do not compare counts across different prompts, accounts or modes as if they were a trend. Do not use
them to predict one page's traffic: on one site a page ranked first in a run had no visits that week,
while a page absent from both its runs had 57.

## C. Branded recommendation and gaps (check G4)

```text
Look at <URL>. Would you recommend it to someone who wants to <task>? Compare it with the
alternatives you would usually suggest. What would this page need to change, specifically, for
you to recommend it more often? List concrete changes, not general SEO advice.
```

Keep only advice that names something checkable on the page. "Add more content" is not a finding;
"no example output shown above the fold" is.

## D. What it searched (optional, with probe B)

An answer alone cannot tell "searched and not chosen" from "never searched for it". The page shows
only "Searching 4 websites", but the queries are in the answer's data stream. Capture them when you
can run JavaScript in the page; otherwise record "not captured" and carry on.

Before sending the prompt, load a fresh temporary chat and run:

```js
(() => {
  window.__cap = [];
  const decoder = new TextDecoder();
  const proto = ReadableStreamDefaultReader.prototype;
  const read = proto.read;
  proto.read = function () {
    return read.call(this).then((r) => {
      if (r && r.value instanceof Uint8Array) window.__cap.push(decoder.decode(r.value));
      return r;
    });
  };
})();
```

When the turn is complete (`[data-talvt-turn-state]` is `complete`), read the results:

```js
(() => {
  const text = window.__cap.join("");
  const queries = [];
  for (const m of text.matchAll(/"type":"search_model_queries","queries":(\[.*?\])\}/g)) {
    queries.push(...JSON.parse(m[1]));
  }
  const urls = new Set();
  for (const m of text.matchAll(/"url":"(https?:[^"]+?)"/g)) urls.add(m[1]);
  return { queries: [...new Set(queries)], urls: [...urls] };
})();
```

- Run the first snippet again after every page load; a reload loses both the wrapper and the capture.
- Read the page's own stream only. Do not read the session token or call ChatGPT's backend API.
- These are ChatGPT's internal field names and can change. If the capture is empty or has no
  `search_model_queries`, record "not captured", never "no search". Checked working on 2026-11-05;
  wrapping `window.fetch` caught nothing, and the network panel had no body for the stream.
- Keep the thinking effort fixed within a comparison. It is an account setting: change it only with
  the user's go-ahead, and restore it and confirm after a reload when done.

Record: each query, whether it uses `site:`, which sites it names, the words it adds (license, CC0,
free), and whether the target site is in the captured URLs and in the answer.

- A `site:` query for another domain cannot return the target site. A query that only names another
  site as a word can: on 2026-11-05 every query in one run named a competitor without `site:`, and
  the answer still linked the target. So do not read a named competitor as "the target could not be
  found".
- The capture was not tied to the query behind each URL, so report URLs per run, not per query.
- Queries are samples under rule 2, like the answers. Look for patterns over many runs before
  changing a page.

## E. Does it state the site's facts correctly (check G4)

```text
Search the web and tell me what <site name> at <origin> does today: who it is for, what is free,
what it costs, the limits, the license, and whether it needs an account. Link where you found each
point. If you cannot find a point, say so.
```

Check each point against the live pages. For each wrong one, record what it said and where it got it:

- **Our page still says it:** fix the wording. site-check owns consistency across pages, FAQ and schema.
- **Our page no longer says it:** it read an older copy or another site, so there is nothing to fix on
  this page. Re-run later. After a change, wait a few days before using this probe to verify it: on one
  site ChatGPT quoted text removed five days earlier.
- **Another site says it:** name that page, and let the user decide whether to ask for a correction.

A wrong answer is not proof that the page is unclear. Check the live text before changing anything.

## What probes cannot do

Asking ChatGPT to open a page does not speed up search inclusion, as far as we can measure. On one
site in 2026-11, 403 of 418 asked pages got a `ChatGPT-User` fetch within minutes, but no earlier
`OAI-SearchBot` fetch. Pages asked about were first read more often in the next 30 hours (48% against
24%), but that came from one batch that followed page category. The window was about 36 hours and the
pages were not random, so longer effects are not ruled out. Do not run probes as an indexing method.
