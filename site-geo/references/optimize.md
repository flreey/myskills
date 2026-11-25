# Optimize mode: continuous GEO for a live site

For a live site that wants AI assistants to recommend and quote it. The unit is the task a person
hands to an assistant, not a keyword. Full method: `~/Projects/GEO/geo-methodology.md`. Data lives in
`<project>/geo/optimize/`; `geo_optimize.py` assigns question sets and counts, the model does the rest.

## The loop

| Step | Does | Writes |
| --- | --- | --- |
| O1 Tasks | Find the tasks people bring, from real sources first | `clusters.jsonl` |
| O2 Constraints | Every hard condition people state, and the product's status on each | `constraints.jsonl` |
| O3 Conversations | 3–5 conversation paths per cluster: opening with context, follow-ups, end | `conversations.jsonl` |
| O4 Route | Query type → lever; page status and primary page for on-site clusters | `clusters.jsonl` (`query_type`, `lever`, `page_status`, `primary_page`) |
| O4b Brief | Per primary page: which clusters it owns, which turns it answers where, which conditions it states | `briefs/<page>.json` |
| O5 Baseline | Probe before changing anything; classify cited sources | `runs.jsonl` |
| O6 Change | One batch at a time, with control clusters | `experiments.jsonl` |
| O7 Measure | After the window: holdout set for results, experiment for the change | report output |
| O8 Feed back | Rules below; update priorities and evidence | `clusters.jsonl` |

### O1 Tasks

A cluster is "who × doing what × under which conditions × wanting what". Sources, in this order:

1. User-crawler fetches by page (`ChatGPT-User`, `Claude-User`, `Perplexity-User`) and AI-referred
   landing pages: tasks the assistants already route here.
2. Site, API and MCP search misses and "not found" messages: tasks the site fails.
3. Support mail, reviews, forum and community posts in the person's own words.
4. Bing AI Performance grounding queries: topic-level, supporting evidence only.
5. Model brainstorming: hypotheses, `evidence_level: hypothesis` until a real source shows the same task.

Sources and windows as in [ai-demand.md](ai-demand.md). Keyword volume is not a source here. When
site-idea already wrote a demand map (`geo/needs.jsonl`, with first-party and off-site evidence), turn
its needs into clusters instead of collecting again, and its question bank (`geo/questions.jsonl`)
into O3 conversations; the same evidence rules apply.

```json
{"id": "k-ui-clicks-mobile", "task": "find subtle tap and click sounds for a mobile app that won't annoy users",
 "persona": "indie app developer", "constraints": ["c-commercial", "c-short", "c-free"],
 "decision_stage": "solution_research", "evidence_level": "validated",
 "sources": ["site search misses 2026-11 (41)", "https://www.reddit.com/r/..."],
 "query_type": "problem", "lever": "onsite", "page_status": "OPTIMIZE", "primary_page": "/sounds/ui-click",
 "priority": 3, "set": "optimize"}
```

### O2 Constraints

```json
{"id": "c-commercial", "constraint": "can be used in a commercial app", "status": "met",
 "note": "CC0, no attribution", "source": "/license", "checked": "2026-11-17"}
```

`unknown` is a to-do, never a page claim. `unmet` stays in the table: it decides `NOT_FIT` and
whether an assistant's reason for excluding the product was true.

### O3 Conversations

Same rules as site-idea `references/conversations.md`: no brand in the opening, variation comes from
persona, conditions and follow-up order, wording close to real quotes. 3–5 per cluster.

### O4 Route

| `query_type` | Typical opening | `lever` |
| --- | --- | --- |
| `recommend` | "what's a good …", "alternative to …" | `offsite` ([offsite-sources](offsite-sources.md)), page facts second |
| `problem` | "my players say … what should I do" | `onsite` |
| `constraint` | "can I use … for …", "does … work offline" | `onsite` (fact pages: pricing, license, docs) |
| `compare` | "A or B for …" | `onsite` comparison page + `offsite` reviews |
| `howto` | "how do I … in …" | `docs` (guides, examples) |
| `integrate` | "make my agent …" | `tools` (API, MCP, plugin listings) |

For `onsite` clusters set `page_status`: `COVERED` (the main page answers the task and its
follow-ups, every condition stated), `OPTIMIZE`, `NEW_PAGE` (no page can take it and the answer is
different, not just reworded), `MERGE`, `NOT_FIT` (a hard condition is unmet). Many template-shaped
`NEW_PAGE` clusters are a site-batch job; a few are the project's own page workflow.

### O4b Page brief

Many conversations, few pages: route them with the same rules as site-batch
`references/question-mapping.md`. A cluster's opening scope picks the page (`primary_page`; a broad
opening goes to a hub or category page, a recommendation opening mostly off-site); each turn's `kind`
picks the section. Conversations follow site-idea's format, follow-ups as
`{"q": "...", "kind": "constraint|howto|why|compare|resource|other"}`.

`geo_optimize.py brief --page /sounds/ui-click` writes the skeleton `briefs/sounds--ui-click.json`:

| Section | Filled from | On the page |
| --- | --- | --- |
| `answer_first` | the openings of the owned clusters | the first paragraph answers them all, in their words |
| `conditions` | `constraint` turns and the clusters' constraints with status | one sentence or table row each, including unmet |
| `faq`, `faq_or_resource` | `why` and `howto` turns | visible Q&A; a tool, file or steps where one does the job |
| `alternatives` | `compare` turns | honest comparison, when the other option is better too |
| `resource` | `resource` turns | the link or button |
| `review` | `other` and unlabelled turns | decide by hand; may belong to another page |
| `unknown_constraints` | conditions still `unknown` | find out before writing; never guess on the page |
| `not_this_page` | owned clusters with a non-onsite lever | the page states facts; the work is off-site, docs or tools |

Edit the brief (merge near-duplicate questions, drop what belongs elsewhere), then hand it to the
project's page workflow. The brief is also what site-check GEO mode checks the page against. One
question lives in one section; target wordings are not pasted in as FAQ variants.

### O5 Baseline

Before any change: run every conversation at least 3 times per target platform, in fresh chats, with
the user's go-ahead for their accounts (iron rule 3). Browser runs follow
[site-idea's probe-runs.md](../../site-idea/references/probe-runs.md). One row per run:

```json
{"conversation_id": "v12", "cluster": "k-ui-clicks-mobile", "platform": "ChatGPT", "mode": "manual",
 "model": "as shown", "date": "2026-11-18", "web_search": true,
 "status": "listed", "role": "tool", "cited_own": true, "own_urls": ["https://example.com/sounds/ui-click"],
 "cited": [{"url": "https://...", "type": "list"}], "recommended": ["A", "B"],
 "accuracy": {"correct": 3, "wrong": 1, "stale": 0}, "accuracy_note": "says downloads need signup",
 "exclusion": null, "gap": "generic", "raw": "geo/optimize/raw/v12--chatgpt--1.md",
 "status_opening": "first", "own_read": ["https://example.com/pricing"], "read": ["https://list.example/best"]}
```

- `status_opening`: the same scale for the first answer, or null; a lower `status` at the end counts as
  "dropped after a follow-up".
- `own_read`, `read`: written by `geo_optimize.py reads --own <domain>` from the raw file's stream URLs:
  our pages the assistant opened, and every other page. `absent` with a non-empty `own_read` is a
  selection loss (it found us and chose another); `report` counts it as "Opened, not named".

- `status`: `absent`, `mentioned`, `listed` (offered as an option), `first` (the main recommendation),
  `excluded` (named and ruled out; then `exclusion: {"reason": "<its words>", "true_reason": true|false|null}`
  checked against `constraints.jsonl`).
- `role`: `tool`, `evidence` (quoted as a source), `step` (part of a procedure), `called` (an agent
  used the API or MCP), or null.
- `accuracy`: product facts in the answer checked against `constraints.jsonl` and the live site.
- `cited[].type`: `brand`, `competitor`, `list`, `forum`, `video`, `docs`, `news`, `other`.

Then source diagnosis per cluster where competitors win:

| Cited sources are mostly | Means | Move |
| --- | --- | --- |
| competitor sites | their page answers the task more directly | on-site: the cluster's page or a missing condition |
| lists and reviews | the contest is in consensus | [offsite-sources](offsite-sources.md) |
| forums | word of mouth | off-site community work ([offsite-sources](offsite-sources.md)); check the product itself |
| nothing, or no web search | the model answers from its own knowledge | long-term consensus; do not credit pages short term |
| our page, yet another product recommended | facts used, a condition failed or unclear | read the exclusion reason: wording or product |

`python3 <site-geo>/scripts/cited_sources.py --root <project> --own <domain>` lists the cited
domains across runs.

### O6 Change

`sets` assigns every cluster once: `holdout` (about 30%, never changed, used to report results),
`sentinel` (about 15%, never changed, detects platform and model drift) and `optimize`. Hypothesis
clusters always go to `optimize`. Then per batch:

```json
{"id": "e3", "change": "answer-first opening and conditions table on UI sound pages",
 "treatment": ["k-ui-clicks-mobile", "k-menu-sounds"], "control": ["k-notification-sounds"],
 "pages": ["/sounds/ui-click", "/sounds/menu"], "shipped": "2026-11-20", "recrawled": "2026-11-24",
 "window_days": 28, "falsified_if": "in-answer rate on treatment does not beat control by the review"}
```

How to change an existing page without losing its search traffic: [retrofit.md](retrofit.md).
Control clusters are similar `optimize` clusters left unchanged for the window. One kind of change
per batch; several kinds on one day cannot be told apart. Page and copy changes follow the project's
own workflow and approvals; this skill writes only `geo/optimize/`.

### O7 Measure

- `report --since <date>`: rates per set and cluster with 95% intervals. The **holdout** set is the
  result to report; the optimize set is biased by construction. Rates on fewer than 30 runs are thin.
- `experiment --id <id>` after the window (from `recrawled`, else `shipped`): difference in
  differences for in-answer and cited rates, with an interval, and the sentinel set's drift. A
  sentinel move of 15 points or more means no conclusion this round.
- Alongside: AI referrals and conversions per landing page (site-measure), Bing AI Performance
  citations, user-crawler fetches of the changed pages. North star: AI-referred visits that finish
  the site's core action.

### O8 Feed back

| Observed | Next |
| --- | --- |
| Page not crawled or not indexed | Technical fix first (site-check, G1); do not judge content this round |
| Assistant states product facts wrongly | Fix the source of truth and every channel's wording (listings: [offsite-sources](offsite-sources.md), records in bl) |
| Excluded for an untrue reason | State that condition plainly on the main page and fact pages |
| Excluded for a true reason | `NOT_FIT`, or a product request to the owner |
| Our page cited, another product recommended | Off-site: the consensus is lost ([offsite-sources](offsite-sources.md)) |
| Listed in the opening, dropped after a follow-up | Answer that follow-up on the pages it opened in that turn (often pricing or FAQ) |
| Absent, but it opened our pages (`own_read`) | Selection loss: compare those pages with the goal card's Capabilities and state the conditions it checks on their first screen (site-check 1G, verification pages); not a new page |
| Never present in answers without web search | Long-term consensus work; not a page problem |
| Recommended, few referrals | Brand landing and first screen; check referral tracking |
| Referrals, no action | Landing page versus the task; next step on the page |
| A hypothesis cluster now has a real source | Raise `evidence_level`; it can join the holdout or sentinel set at the next `sets --force` (owner's call) |

Rotate at most 20% of the holdout clusters per quarter, and never between a baseline and its review.
