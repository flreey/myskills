# Question bank: how each need is asked, from several angles

Step 1, after the demand map. The bank turns needs into the questions people would type into an
assistant, so probes and page titles start from situations, not keywords. A model may write most of
the bank, but every question says what it rests on, and model-only questions stay hypotheses.

Asking a model to "generate 100 questions users ask about X" without data gives fluent questions
with no weight: it cannot tell a need behind 35% of complaints from one behind 2%, and its "how
likely to recommend" score is a guess about itself. So the model gets the demand map and its
evidence, and the questions are checked against real wording and, for a sample, by probes.

## Angles and stages

| `angle` | Typical opening |
| --- | --- |
| `recommend` | "where can I get …", "what should I use for …" |
| `compare` | "A or B for …", "is a CC0 library safer than a subscription" |
| `problem` | "my trailer got a claim on a royalty-free sound, what now" |
| `howto` | "how do I make a footstep loop cleanly in Godot" |
| `purchase` | "is it worth paying for a sound pack for my first game" |
| `alternative` | "something like … but without a subscription" |
| `constraint` | "can I use … in a game I sell on Steam without credit" |
| `integrate` | "make my coding agent add sound effects to the game" |

`stage`: `exploring` (does not know the options), `choosing` (comparing), `using` (has a file or tool,
fitting it in), `troubleshooting` (something went wrong). `angle` maps to site-geo's query types and
levers (references/optimize.md, O4).

## Prompt for the model

Pass the demand map with its evidence ids (`geo/needs.jsonl`, or the raw quotes and queries), then:

```text
You are a user-needs researcher. Below are real data rows, each with an id: forum quotes, site and
agent search queries, "not found" messages and project descriptions.

For each need in the map, write 8–12 questions a person in that situation might ask an AI assistant.
Work on 3–5 needs per batch.
- Cover at least 4 angles per need: recommend, compare, problem, howto, purchase, alternative,
  constraint, integrate.
- Personas must really differ in wording: a beginner does not say "one-shot" or "LUFS"; a sound
  designer does. Do not reword the same question.
- Most openings describe the situation, not "what is the best …". At most a third use best, free or AI.
- Name no brand or product. Platforms whose name changes the answer (Steam, YouTube, Godot) are
  fine; list them in the project's `allowed_names`.
- Every question names the data ids it rests on: `<need_id>#e<N>` for the Nth evidence row of a need
  (1-based, in needs.jsonl order), or the URL or search-log ref of what it was checked against. A
  question with none is a hypothesis.
- Do not present these as real users' questions.

Output one JSON object per line:
{"id": "...", "need_id": "...", "question": "...", "persona": "...",
 "stage": "exploring|choosing|using|troubleshooting",
 "angle": "recommend|compare|problem|howto|purchase|alternative|constraint|integrate",
 "conditions": ["conditions that change the answer, e.g. sold on Steam, must loop, under 0.5 s"],
 "follow_ups": [{"q": "...", "kind": "constraint|howto|why|compare|resource|other"}],
 "evidence": ["data ids"], "evidence_level": "quoted|derived|hypothesis",
 "names_sites_likely": true, "origin": "model"}
```

`evidence_level`: `quoted` when the question is close to a real quote or query, `derived` when it
rests on evidence but the wording is the model's, `hypothesis` with no evidence. `names_sites_likely`
is the writer's guess and is replaced by probe results.

Questions reverse-engineered from competitors (references/competitor-probes.md) join the same file
with `origin: "competitor"` and `competitor: "<id>"`; questions copied from a real source take
`origin: "real"`.

## Check and raise evidence

1. `geo_idea.py bank` checks the file and writes `geo/bank.md` (needs × angles, evidence levels). It
   warns about questions that name a brand, near-duplicates within a need, needs with fewer than four
   angles, hypotheses that carry evidence, and a bank leaning on best/free/AI; a `<need_id>#e<N>` that
   points at no evidence row is an error. Brand words come from the project name, the site domain,
   project `brands` (our other spellings, e.g. "sfx mint"), each competitor's name, the name part of
   its domain (app.cinevva.com → cinevva) and its `aliases`, minus project `allowed_names`.
2. Compare a sample with real wording: search suggestions and "People also ask", Reddit search, the
   site's own search log. A match raises `hypothesis` to `derived`, or `derived` to `quoted`, with the
   source added to `evidence`.
3. `sample --from-questions --n <n>` turns the bank into probe samples, spread over needs and angles,
   real wording first; hypotheses only with `--include-hypothesis`. Options:
   - `--weight NEED=W` (repeatable): seats per need in proportion to W, unnamed needs weigh 1; use it
     when a need's bank is much larger, or matters more, than an even spread gives it.
   - `--origin competitor|model|real`: only questions of that origin.
   - `--ids a,b,c`: take these questions as named, hypotheses included (a pilot).
   - `--append`: add to `samples.jsonl`, skipping questions already in it, e.g. a pilot first and the
     main sample after it, so both land in one report.

## What the bank is for

- Probes (gap and presence), with the assistants' rewritten search queries captured.
- Titles, H1s, first paragraphs and FAQs of the pages that will answer these needs (site-batch
  `title_source` and `question_slots`).
- The page count is not the question count: one page answers a task and its follow-ups, and the
  number of pages comes from dimensions × assets (site-batch).
