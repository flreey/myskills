# Retrofitting existing pages for GEO

Turn a live page into one assistants can find, quote and recommend, without losing what it already
earns in search. Two cases:

| Case | Tool |
| --- | --- |
| A few hand-made pages (home, pricing, a guide, a category page) | this file, one page at a time |
| A family of similar pages built from one template (hundreds of sound pages, product pages, city pages) | site-batch **adopt** mode (`site-batch/references/adopt.md`): rows keep the live URLs, content blocks come from data, retrofit in waves with a control group |

## What the page should become

| Part | Target |
| --- | --- |
| Title and H1 | The task in the words people use with assistants (brief `answer_first`), plus the product or object |
| First paragraph | Answers the task in its first sentence; stands alone when quoted; names the product, not "we" or "it" |
| Conditions | One sentence or table row per condition people state, including the unmet ones |
| Facts | Numbers with units, a date on changing facts, same values as the product and every other channel |
| Next step | A usable resource above the fold: tool, file, download, steps |
| Questions | The brief's questions answered once each, visible on load, in the section the mapping gives them |
| Comparison | Honest: when another option is the better choice |
| Technical | In the server HTML, indexable, AI search and user crawlers allowed (G1), FAQ not hidden behind a click |

## Keep what search already earns

Many pages that need GEO work already rank. Before changing one, read its search data (site-plan GSC
window or Search Console for the URL) and keep:

- **The URL.** Never change it for GEO. If two pages answer one task, merge with a redirect as a
  separate, approved decision.
- **Words with impressions.** Queries that bring impressions stay in the title or H1 and the opening.
  A GEO title leads with the task and keeps the ranking words.
- **Sections that rank.** Add above or around them; rewrite only what is wrong or vague. Do not delete
  long-tail paragraphs that bring clicks.
- **Structured data and internal links** that exist today, updated, not removed.

## Steps

1. **Brief.** Optimize mode O1–O4 assign the page as `primary_page` of its clusters; then
   `geo_optimize.py brief --page <path>` and edit it (references/optimize.md O4b).
2. **Before.** Save the current page: `page_check.py --url <live url> --format json > geo/optimize/before/<page>.json`
   (site-check engine) and the search baseline (GSC clicks and impressions for the URL, last 28 days).
3. **Gap.** `page_check.py --url <live url> --geo-brief geo/optimize/briefs/<page>.json`: which
   openings the first paragraph does not answer, which brief questions and conditions the server HTML
   lacks. It is a lexical pre-sort; read each line against the page.
4. **Change plan.** One table per page, section by section: keep / add / rewrite / remove, the brief
   item it serves, and the fact it rests on (product source of truth, live behaviour). Show the owner;
   unknown conditions stay off the page until checked.
5. **Change.** Through the project's own workflow (site-kit content rules on kit sites, the codebase
   on others). One kind of change per batch.
6. **Accept.** site-check on the changed page in GEO mode (check 1G, questions in their place) **and**
   SEO mode when the page has search traffic; `page_check.py --geo-brief` again to confirm coverage;
   G1 for crawler access.
7. **Experiment.** Register it before shipping (`experiments.jsonl`, O6): treatment clusters, control
   clusters of similar pages left unchanged, `shipped`, then `recrawled` once the page was fetched.
8. **Review** after the window (O7): `experiment --id`, holdout report, AI referrals and conversions
   for the page, and the GSC window for the URL against step 2. A GEO gain that costs search clicks is
   reported as such; the owner decides.

## What not to do

- Paste target questions as FAQ entries, or answer one question in three places.
- Add claims, numbers or "best" language the product cannot back.
- Show crawlers different content from visitors.
- Change many pages and kinds of change on one day: nothing can be credited.
