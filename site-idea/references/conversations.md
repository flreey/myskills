# Writing conversation paths and finding signals

A sample is one combination of dimension values. Turn it into the conversation a real person would
have with an assistant, then look for evidence that people actually ask it.

## Conversation path

| Field | Write |
| --- | --- |
| `persona` | Who, in what situation, in one line: "parent with 400 iPhone photos for a school yearbook" |
| `opening` | What they type first, in the market's language, 1–3 sentences, with their situation |
| `follow_ups` | 1–3 later turns that bring in the remaining conditions or push back on the answer |

Rules:

- Every generating dimension value of the combination appears somewhere in the path. A constraint can
  arrive in a follow-up rather than the opening; that is how people talk.
- Do not name the idea, the product or any brand. The probe measures what the assistant does on its own.
- Openings vary: many start from the problem ("the yearbook site rejects my photos"), not from a
  request for a tool. Write at most a third of them as "what is the best tool for …".
- Match real wording when a signal has it: length, words, level of detail. Do not polish it.
- Persona is a dimension marked `changes_answer: false` or a plausible person; it adds realism, never
  a new combination.

## Signals

For each sample, spend a few searches looking for people asking this combination: forums, Reddit,
Q&A sites, product reviews, support communities, GitHub issues. Use the session's web search tool.

- Keep only real posts: URL, a short quote (under 25 words), date if shown.
- Search in the market's language. Two or three queries per sample; stop when one good signal is found.
- None found is a result: leave `signals` empty. Do not write an invented or paraphrased quote.
- Signals do not change the gap label. They decide confidence: a high-opportunity value with no
  signals anywhere is a hypothesis, said so in the report.

## How many

Default 40 samples (`sample --n 40`), at least as many as the widest dimension so every value is
sampled once. Each sample needs at least one run per target platform; two runs on the main platform
when time allows.
