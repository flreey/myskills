# Competitor probes: when do assistants recommend the others, and why

An optional probe design for crowded markets. Start from the products assistants already recommend,
work back to the situations they are recommended in, then test those situations blind. It finds the
questions where the recommendation is decided, and why the winner wins.

## Three traps it avoids

1. **What a model says about itself is not what it does.** "When would you recommend Mixkit?" returns
   a product summary. In a fresh chat with web search, what it recommends depends on what the search
   returned. Reverse-engineered questions count only after a blind run.
2. **It finds the competitors' ground, not the gaps.** Questions where the recommended product fails
   the person's condition (asks for credit when they said no credit, gets Content ID claims) are the
   opening, and they show only when the answer is judged against the conditions.
3. **Being recommended is often not about a page.** A library recommended through its search-result
   pages and its age wins on scale and consensus; a page with the same question will not win the
   same way. Classify every blind run by the sources behind it before deciding to build.

## Steps

1. **List 10–15 competitors** in `geo/competitors.jsonl`, by kind:

   ```json
   {"id": "pixabay", "name": "Pixabay", "domain": "pixabay.com", "kind": "library", "note": "free stock, own licence"}
   ```

   `kind`: `library`, `video`, `game`, `generator`, `list` (rankings and aggregators), `marketplace`,
   `tool`, `other`.
2. **Reverse-engineer candidate questions**, 5–10 per competitor, from two places: its own landing
   and use-case pages (which situations it targets), and an assistant asked who it suits and when.
   Write them into `geo/questions.jsonl` with `origin: "competitor"`, `competitor: "<id>"`, and no brand
   in the question text. Mark what came from the assistant's self-description as `hypothesis`.
3. **Line them up with the demand map.** Attach each to a `need_id`; questions that match no need stay
   hypotheses and go last. Remove near-duplicates (`bank` warns).
4. **Blind runs.** `sample --from-questions`, then probes as usual (probe-runs.md): fresh temporary
   chat, web search on, no brand in the opening. Record per run `recommended`, `cited` with types,
   `own`, `search_queries` (site-geo references/chatgpt-probes.md, section D) and the condition check.
5. **Classify** each run with `outcome`:

| `outcome` | Seen in the run | Move |
| --- | --- | --- |
| `competitor_page` | a competitor's own page was opened and answers well | build only where the site's answer is better on the conditions (licence, format, set, loop) |
| `constraint_unmet` | a competitor is recommended but fails a stated condition | **first in line**: a page whose title and first paragraph answer that condition |
| `lists_forums` | the answer rests on rankings, articles or forum threads | off-site: enter those sources (site-offsite GEO mode) |
| `no_search` | no web search; the answer comes from the model's memory | long-term consensus; no page credit in the short term |
| `own_recommended` | the site is recommended already | keep it; check whether a follow-up drops it |
| `other` | none of these | say what happened in `gap_note` |

6. **Report.** `geo_idea.py report` counts outcomes, presence, the source mix behind answers without
   the site, and the captured search queries. The queries are the strongest page input: the title,
   H1 and first sentence of a page should match how the assistant rewrote the question.

## Cost

About 15 competitors × 5 questions, one run each, is 70–80 conversations: about 1.5–2 hours in a
browser run as probe-runs.md describes. Pilot with 3 competitors × 5 questions first and confirm the
query capture works before the full run.
