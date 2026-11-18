# Writing conversation paths and finding signals

A sample is one combination of dimension values, one question-bank row (`sample --from-questions`) or
one candidate page (`sample --pool`). Turn it into the conversation a real person would have with an
assistant, then look for evidence that people actually ask it.

Samples from the question bank arrive with `opening`, `persona` and `follow_ups` filled, plus
`need_id`, `angle` and `evidence_level`; check them, do not rewrite them. Samples from a pool carry the
page `url` and its `stratum`; write their conversations from the demand map and the site's own data.

## Conversation path

| Field | Write |
| --- | --- |
| `persona` | Who, in what situation, in one line: "parent with 400 iPhone photos for a school yearbook" |
| `opening` | What they type first, in the market's language, 1–3 sentences, with their situation |
| `opening_scope` | The dimension ids the opening already fixes. Often fewer than the combination: "my iPhone photos won't upload" fixes only the source |
| `follow_ups` | 1–3 later turns, each `{"q": "...", "kind": "...", "adds": ["need"]}`: the question, what it asks, and the dimensions it brings in |

`kind` is one of `constraint` (can it, does it, is it allowed), `howto` (steps), `why` (reason,
explanation), `compare` (versus another option), `resource` (where to get it, a file, a tool),
`other`. Kinds and scope decide later where a page answers the turn: site-batch
`references/question-mapping.md`.

Rules:

- Every generating dimension value of the combination appears somewhere in the path. A constraint can
  arrive in a follow-up rather than the opening; that is how people talk.
- Do not name the idea, the product or any brand. The probe measures what the assistant does on its own.
- Openings follow the sample's `angle`. `sample` marks about a third of the combinations
  `recommend` (`--tool-share`): their opening asks for a tool, site or app under the combination's
  conditions ("is there a free site that can fix a blurry WhatsApp video on my phone?"). The rest are
  `problem`: they start from the situation ("the yearbook site rejects my photos") and never ask for a
  tool. Both are needed: problem openings show whether the answer is good, recommend openings show
  whether the assistant searches and picks a tool, and which. On ToHD (2026-11-18) 70 problem
  openings searched 28 times and never named the site; 15 tool openings searched every time and named
  it 7 times.
- Match real wording when a signal has it: length, words, level of detail. Do not polish it.
- Persona is a dimension marked `changes_answer: false` or a plausible person; it adds realism, never
  a new combination.

## Signals

Two kinds, both in `signals`:

- **First-party** (live sites): the site's own records that people ask this, in the evidence format
  of [demand-map.md](demand-map.md): `{"source": "site_search", "ref": "search_log 2026-09-18..11-17",
  "q": "pistol gunshot", "n": 20}`. Sources: site, API and MCP search, misses, feedback, product logs,
  support, surveys, AI fetches and referrals. Older samples may carry them as `site_signals`; both count.
- **Off-site**: for each sample, spend a few searches looking for people asking this combination:
  forums, Reddit, Q&A sites, product reviews, support communities, GitHub issues. Use the session's
  web search tool.

Off-site rules:

- Keep only real posts: URL, a short quote (under 25 words), date if shown.
- Search in the market's language. Two or three queries per sample; stop when one good signal is found.
- None found is a result: leave `signals` empty. Do not write an invented or paraphrased quote.
- Signals do not change the gap label. They decide confidence: a high-opportunity value with no
  signals anywhere is a hypothesis, said so in the report.

## How many

Default 40 samples (`sample --n 40`), at least as many as the widest dimension so every value is
sampled once. For one wide dimension (hundreds of existing pages, one value each), sample a pool by
strata instead: per-value results mean nothing with one run each, per-stratum results do. Each sample needs at least one run per target platform; two runs on the main platform
when time allows.
