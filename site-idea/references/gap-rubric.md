# Gap rubric

Judge each run against the conversation's opening and follow-ups, not against the product. The
question is: did the assistant give this person, with these conditions, a specific and usable answer?

Pick the first label that applies, top to bottom.

| Label | Level | Applies when | Example |
| --- | --- | --- | --- |
| `unmet_constraint` | high | The recommended way or tool breaks a condition the user stated, or the answer ignores it | User said "no upload"; every tool named is an upload site |
| `outdated` | high | A method, price, version, availability or limit is wrong as of the run date | Recommends an app that was discontinued |
| `no_resource` | high | Explains what to do but gives nothing to use directly: no tool, file, data, code or exact steps for this case | "Use a converter that supports batch mode" |
| `generic` | high | Advice would read the same for most neighbouring combinations; nothing specific to this entity, task and condition | Same five tips it gives for any format |
| `weak_sources` | medium | Specific and usable, but rests on thin or unverifiable sources (one old forum post, a spammy list) or none | Correct steps citing a 2019 thread |
| `self_made` | medium | The assistant made the thing itself instead of pointing to a resource (code that synthesizes the sound, a generated file, a script) | Writes a Web Audio snippet for a "coin pickup" beep |
| `good` | low | Specific, correct, meets the conditions, names usable resources, and cites strong sources | — |

Rules:

- Check facts you can check (a tool exists, supports the condition, price) with a quick look; an
  unchecked claim is not `outdated`.
- Judge the whole conversation: an opening answered generically but fixed after the follow-up counts
  by the final state, noted in `gap_note`.
- `gap_note`: one sentence naming what is missing or wrong, specific enough to become a page field
  ("no answer on quality loss for batch HEIC → JPG").
- Record `cited` (URL and type) and `recommended` (names) even when the label is `good`: those sources
  are the off-site targets later.
- When the opening deliberately names no brand, do not mark an answer down for not naming a competitor.
- Never raise a label because the product would answer better. The gap is in the answer, not in a
  comparison with the idea.
- When unsure between two labels, pick the lower level and say why in `gap_note`.
- `self_made` is competition, not a gap to fill with the same thing: a page beats it only with
  something the assistant cannot make (real recordings, a consistent set, a licence, proof).

## Presence and sources (every run)

The gap says whether the answer is good. These fields say whether the site would be the one people
are sent to, and why not:

| Field | Write |
| --- | --- |
| `own` | `absent`, `mentioned` (named in passing), `listed` (offered as an option), `first` (the main recommendation), `excluded` (named and ruled out; say why in `gap_note`) |
| `cited_own`, `own_urls` | whether a page of the site was opened or linked, and which |
| `recommended` | names in the order given, the site included |
| `cited[]` | every source URL with its type: `brand` (the site), `competitor`, `list`, `forum`, `video`, `docs`, `news`, `other` |
| `web_search` | `true` when the assistant searched; `false` answers come from the model alone |
| `search_queries` | the queries it ran (site-geo references/chatgpt-probes.md, section D), or `null` when not captured; never `[]` for "not captured" |
| `outcome` | competitor probes only: `competitor_page`, `constraint_unmet`, `lists_forums`, `no_search`, `own_recommended`, `generic_rules`, `other` ([competitor-probes.md](competitor-probes.md)) |

`report` turns these into the presence section: share of answers with the site, first
recommendations, the source mix behind answers without it and a lever hint.
