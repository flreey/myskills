# Worked example: SFXMint decisions

These are real decisions from the SFXMint project (2026-09), restated with this skill's
vocabulary.

## Clusters and neighbours

| Cluster | Includes | Excludes / neighbour distinction |
| --- | --- | --- |
| `button_click` | Button click, press and tap feedback; soft, retro, MP3 and free variants | Physical mouse clicks (`mouse_click`), sound generators, packs, UI hover |
| `mouse_click` | Computer mouse click sounds | UI feedback. The "physical mouse" wording does not claim a real recording or hardware model |
| `door_knock` | Knock patterns and loudness | Door opening, lock and doorbell are different actions, so they are adjacent entrances |
| `call_end` | Hang-up / call-ended feedback | Call-failure diagnosis, branded original tones |

- "Button click" and "button press" share one cluster: same sound set.
- "Button click mp3" is not its own page.
- "Rain sound effects for sleeping" stays `pending`: short assets versus continuous listening is
  unresolved.

## Page decisions that followed

| Situation | Decision |
| --- | --- |
| `/sounds/door-knock` already served knocks | `improve_existing` (stable URL, per-item facts, selection guidance) |
| `/sounds/short-ui-error` overlapped `/sounds/feedback-error` | Merge: 301 to the owner; no duplicate page |
| `door locked` could mean locking or trying a locked door | Keep the requirement `unknown`; do not certify with the general lock sound |
| Level Up had 1 keyword (Planner 170/month, US) | Keep the existing page; the volume is historical and not summed with variants; ad "Low" is not SEO difficulty |
| Keyboard Typing was in the frozen experiment cohort B | Defer: cohort and index groups are checked before any page work |
| Soft, retro and bright labels without listening evidence | Not used as certified filters; the file facts (duration, channels, review status) are the filters |

## What the gates would say

`button_click` with 38 items has a primary page mapped, so the suggestion is
`keep_or_improve_existing`. "Retro button click" with 1 member, 4 retro items and no SERP pair
stays a `filter`. Promotion would need at least 3 phrasings, 8 or more retro items, a SERP pair
with `different_result_set`, and later a confirmed `promotion_signal`.

## Full review of the 17,408-keyword pool (2026-09-29)

`prepare-review --plan` sized the queue at 63 batches. Reviewing one kind at a time kept each
decision simple:

| Order | Units | Keywords | Batches |
| --- | --- | --- | --- |
| Variants (`--only variants`), clusters defined here | 591 groups | 6,009 | 11 |
| Facets (`@seed` plus exceptions) | 384 groups | 2,932 | 5 |
| Boundary groups (exclude, except in-scope members) | 205 groups | 2,622 | 5 |
| Singles (the last third had no seed) | 4,674 | 4,674 | 31 |

Outcome: 10,916 included, 5,475 excluded, 1,017 pending, 412 active clusters. After inventory,
`analyze` suggested `keep_or_improve_existing` for the 25 clusters with live pages. 170 clusters
lacked only a SERP check; 211 had demand but no matching catalog items. Live searches of the
SFXMint API confirmed several gaps (no air horn, fire alarm, dinosaur or coin toss sounds).

Lessons:

- **`@seed` follows the longest seed match, not the meaning.** "gun fire sound effect" matched
  the seed "fire"; "funny scream" matched "funny". Show each member's resolved cluster before
  approving a facet group, and use a fixed cluster when the facet word is the entity.
- **Broad boundary terms cost review time.** "music", "spell" and "curtains" swept in "music box",
  "magic spell" and "curtain opening"; exceptions fixed them, and discovery should narrow them.
- **Collection hubs need their own inventory rule.** Count them from catalog categories or child
  clusters; leave them out when neither applies.
- Pending keywords are mostly franchise clips (Free Fire, Star Wars, Mario), named memes and sets
  for streamers. They are real demand, but not for asset pages until rights and page type are
  decided.
