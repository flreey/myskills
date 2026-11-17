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
- Never raise a label because the product would answer better. The gap is in the answer, not in a
  comparison with the idea.
- When unsure between two labels, pick the lower level and say why in `gap_note`.
