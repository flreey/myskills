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
`analyze` suggested `keep_or_improve_existing` for the 25 clusters with registered pages and
treated most others as page gaps. 211 had demand but no matching catalog items. Live searches of
the SFXMint API confirmed several gaps (no air horn, fire alarm, dinosaur or coin toss sounds).
The page gaps were wrong: the registry held 33 of 578 live URLs (next section).

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

## Registry sync (2026-09-29)

The trial registry was not empty, only incomplete, so nothing forced a sync, and `analyze` kept
proposing pages that already existed (`/sounds/animal-bird`, `/sounds/ambience-thunder`).
`sync-check` against the built sitemap found 545 of 578 live URLs unregistered: 202 family pages,
321 one-sound pages, 20 categories, 19 set pages, tools, guides and info pages. Counting pages by
URL prefix had put the families at 197; the built HTML (`CollectionPage` versus a single
`AudioObject`) gave the real split. With the snapshot in place, 233 clusters moved from
`defer`/`create_candidate` to `check_existing_page`.

The ownership review produced `cs_sfxmint_sync_2`: 578 `page_upsert` and 244 `map` changes
(212 primary, 32 secondary). Rules used:

- A family page named for the entity owns the cluster (`keep`, or `improve_existing` below 8
  items). A category, set or home page owns a cluster that matches its scope (`improve_existing`
  when the scope is mixed, such as Fire & Electricity).
- A one-sound page owns a cluster only when it is the only live page naming the entity
  (`improve_existing`). 29 clusters are named only by several one-sound pages (bite, breathing,
  scream, window, typewriter…). They were left without a primary and reported as gaps.
- Overlaps to watch go in as `secondary`: `/sounds/error` next to `/sounds/feedback-error`,
  `/sounds/frog-croak` next to `/sounds/animal-frog`, the fireplace and fire crackling families.
- `published_at` is the sitemap lastmod, labelled as such. The first trial had written an invented
  date, earlier than the site's launch.

`apply-changes --dry-run` passed with 0 errors. In a throwaway copy, `analyze` then reported 0
unregistered URLs: 235 clusters `keep_or_improve_existing`, 177 `defer`, 0 `create_candidate`.
80 indexable pages own no cluster (set pages, most categories, several families such as portal,
hologram and braam): live pages with no observed demand in the pool.

SERP: 6 captures succeeded; the 7th query hit a Google CAPTCHA. The batch did not stop at the
first CAPTCHA and made 7 more requests that all landed on it, which is why the SERP step now stops
at the first one. Google redirected the session to google.com.hk, so US ranking was not verified;
captures now record `served_host` and `localized`.

## Search Console and SERP round (2026-09-30)

GSC held one window (2026-08-30..09-27): 330 visible queries, 2.61K impressions, 127 clicks.
264 of the 330 queries were new to the 17,408-keyword pool. Reviewing them created 11 clusters
that live pages already served but no cluster named: `eight_bit_sound_generator` (/synth/8-bit),
`sound_effects_api` (/api/docs), `react_sound_library`, `text_blip`, four category-level
collections (animal, mechanical, office, water), `sci_fi_sound_effects`, an AI generator cluster
and the brand. Tool and integration demand hid behind discovery's `adjacent: generator` boundary:
adjacent for asset seeds, but a real job for a site that has the tool.

Page-level GSC data showed 534 variant URLs (`/sounds/<family>-NN`, canonical to the family)
carrying about 31% of page impressions, and only 218 of 578 registered URLs with any
impressions. Per-page review must fold canonicalized variants into their family page before
judging cannibalization or retirement.

SERP: 12 captures, one query per page load with pauses, `gl=us&hl=en&pws=0`; no CAPTCHA, every
answer from www.google.com (the earlier session had been redirected to google.com.hk). The
captures resolved senses more than page types: "drone" mixes UAV flying and ambient drones,
"whisper" means human whispers (SFXMint's whisper-like wind does not match), "warning" returns
alarm and alert pages, "cinematic", "fight" and "sound effects for games" return collections.
Pairs: warning vs alarm shared 3 of the top 10, click vs button click shared 2, both below the
merge line. Excluding `license`/`format` from promotion cut the promotion candidates with enough
inventory from 208 to 9 and the SERP queue from 670 to 351.

