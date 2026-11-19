# Goal card (`geo-goal.md`)

One page per site, written at step 0 with the owner and kept at the project root as `geo-goal.md`,
outside every GEO folder: a site can run several (`geo/`, `geo-longtail/`, …, one per need space),
and they all serve the same goal. Every later step reads it first; every brief to another thread or
agent includes it as written. Change it only with the owner, and keep a dated line in "Changes" for
each change. It is the source of truth for the goal, north star, audiences and channels:
`project.json` copies (`north_star`, `audience`, `platforms`) follow it, and `geo_idea.py check` warns
when they differ.

## How to write it

1. Ask the owner for the goal in their words, and what they would count as success. Fill the rest
   from the project's files and data; ask only for what is missing and changes the work.
2. Fill "Current state" from facts, each with a source and date: existing pages and their traffic by
   channel, AI referrals, agent/API/MCP usage, what assistants say today (if probes exist), and
   experiments still running (their pages, window and read date). Missing data is written as missing.
3. Show the card to the owner and get a yes before step 1. A card the owner has not seen is a draft.

## Template

```markdown
# Goal card: <project>

Updated <date> · confirmed by owner <date>

## Goal
<one or two sentences in the owner's words: who should be recommended by whom, for what>

## Main bet
<the approach this round tests, in the owner's words, e.g. "pages built from real demand, one per
specific need, with the real wording in title, H1, text and FAQ">
Stop or change it when: <the result that would show it does not work, and by when>
Setting the main bet aside (no pages this round, a different lever as the main one) is a drop: it goes
to the owner as its own question, never as a row in a table.

## North star
<one measurable outcome, e.g. "sessions from AI referrals that end in a download, per week">
Secondary: <presence and first-pick rate in retests; index and rank under the assistants' rewritten queries>

## Capabilities (what the product does, under which conditions, with proof)
| Capability | Conditions met (free tier, no upload, devices, limits, licence, …) | Proof (test, file, measurement, date) | Where stated publicly (URLs) |
Write it before any page space: assistants pick by "capability + conditions" and check them on our
pages. A capability without proof is not claimed on a page. The card is for us; assistants read only
the site. The last column names the pages that state each row's conditions in plain text, by mode or
device where they differ: at least the capability's own page, and home and pricing when the row says
free or paid. site-check 1G (`--capabilities`) compares those pages with this table. New products: write it before the site
exists, and prefer capabilities whose conditions set the product apart.

## Who and what we serve
| Audience | Needs (ids once the demand map exists) | Why |

## Channels
| Channel | In scope? | How we will see it |
| Assistant chat (ChatGPT, Claude, Perplexity, Gemini) | yes/no | probes, AI referrals |
| Search engines (assistants search before answering) | yes/no | index, rank under rewritten queries |
| Agents, API, MCP, tool directories | yes/no | API/MCP search logs, installs |

## Levers allowed
Pages / off-site / product and docs / generating missing assets: <which, with limits such as budget>

## Not doing
| What | Cost of dropping it | Owner's yes (date) |

## Current state (facts, each with source and date)
- Pages: <count by type, what each serves>
- Traffic by channel: <search, AI referral, agent/API>
- AI-referred landings by page type: <home / core tool pages / long-tail pages / guides, with counts and window>
- What assistants do today: <presence, who they pick; or "not probed">
- Running experiments: <name, pages, window, read date> — do not overlap them
- GEO folders: <folder, need space, stage, decision date>
- Assets: <what we have that others do not>

## Constraints
<budget, time, accounts the owner allows, site rules (e.g. docs/page-rules.md)>

## Changes
- <date>: <what changed, why, owner's yes>
```

## At each hand-off

End every step's report with: "Compared with the goal card, this step dropped: …" (needs,
audiences, channels, levers, or any part of the main bet), or "nothing". A step that leaves the main
bet without work says so in that line, even when no need was dropped. Anything dropped goes to the owner before the next step
(rule 3 in the site skill).
