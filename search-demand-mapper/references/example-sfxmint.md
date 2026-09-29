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
