# Page decisions, gates, change sets

## Decision vocabulary (per cluster)

| Decision | When | Registry effect |
| --- | --- | --- |
| `keep` | An existing page completes the same job with no material gap | `map` primary, decision keep |
| `improve_existing` | Same job and result set are served, but content, selection or actions have gaps. Also used for a section on the parent page | `map` primary (or secondary on the parent) |
| `filter` | The difference is only a constraint (style, format, duration, license) that can be chosen on the page | `map` role filter + `conditions`; filter URLs stay noindex |
| `create` | Independent job or result set, no suitable page, inventory can fill it, gate passed | `page_upsert` (status planned) + `map` primary |
| `defer` | Definition, ambiguity, evidence or inventory is insufficient | `map` decision defer, or `cluster_status` hold, with the missing item and the condition that resumes it |

One page may serve several compatible clusters, and one cluster may have several entrances. A
cluster has exactly one **primary** page, its owner for ranking purposes. Stable URLs are
preferred: the URL does not need to match a keyword.

## Evidence flags

`analyze` reports three flags per cluster; they are not a ladder:

- **external**: observed demand outside the site (suggestions, Planner, Trends, SERP lists);
- **serp**: a captured SERP for a member query, showing the page type and, with a pair, overlap;
- **gsc**: impressions on the site itself.

## Create gate

Propose `create` only if all of these hold:

1. **Independent demand.** Enough members (`gate.min_keywords`, default 2) or one strong signal
   (Planner high ≥ 100 or GSC impressions ≥ 50).
2. **Independent result set.** It is a distinct entity in the reviewed definitions. For
   near-synonyms or attribute splits, it also needs a SERP comparison verdict
   `different_result_set`.
3. **Page type confirmed.** A SERP capture shows that the natural answer is this page type
   (`require_serp_for_create`).
4. **Inventory or content depth.** Counted items ≥ `page_types.<type>.min_items`
   (resource 8, collection 3, tool 1, article 0).
5. **No existing page can absorb it.** Otherwise use `improve_existing` or `filter`.
6. **Fits the product boundary** (in ring) and adds user value beyond a template swap.

Failing any of 1–5 means `defer`, or `improve_existing` on the parent (as a section). Volume > 0 is
never enough.

## Attribute promotion (filter → own cluster/page)

`analyze` lists attributes with at least `promotion.min_keywords` (3) member keywords, except on
the axes in `promotion.exclude_axes` (default `license` and `format`: "free", "no copyright", "mp3"
and "wav" narrow every result set but are not a page of their own). Promote only with all of the
following:

- distinct phrasings of the attribute demand, from the pool or GSC;
- a SERP pair (parent representative versus attribute query) with verdict `different_result_set`;
- inventory for that attribute ≥ `promotion.min_items` (8);
- after launch: a confirmed `promotion_signal` in `gsc review` (the attribute's queries on the
  parent page above `split_min_impressions` in 2 consecutive windows).

Apply it with a `promote` change: the new cluster gets `parent` and `promoted_attrs`, and members
carrying that attribute move to it with `lineage`. Until promotion, it stays a filter or a
subsection.

## Priority

Structure answers "what should exist". Priority answers "what goes first".

- `analyze` gives an evidence tier:
  - **P0**: Planner high ≥ 1,000 or GSC ≥ 100;
  - **P1**: Planner ≥ 100, or any GSC, or ≥ 5 members;
  - **P2**: everything else.
- Adjust the tier by product fit, SERP opportunity (thin, mixed or off-task results the product
  can beat by completing the task directly) and effort.
- State the reason. Do not invent a numeric score, and never add volumes across sources or
  synonyms.

## Requirement–inventory matrix (before `create` or `improve_existing`)

List each keyword's requirements: core (entity and job), format, price or license, context,
duration. Assess each candidate item as `met`, `not_met` or `unknown`, with evidence. A keyword is
fully matched only when **one item** meets all its requirements. Unknown is neither met nor
failed. Zero full matches is a gap to report; it does not authorize creating assets. Naming or
model-generated labels do not prove that an item fits; human review evidence does.

At page level, `brief` computes this per attribute: inventory `attrs` against the page's
`covered_attributes` (statuses in SKILL.md, Brief mode). Use it before building or rewriting the
page; the per-keyword matrix above still applies to asset-level fit.

## Change set

```json
{
  "id": "cs_20260929_button_click",
  "approved_by": "user in chat 2026-09-29",
  "reason": "map button_click; register filter view",
  "changes": [
    {"kind": "page_upsert", "url": "/sounds/button-click", "page_type": "resource", "status": "published", "indexable": true, "published_at": "2026-09-08", "notes": "published_at = sitemap lastmod", "reason": "existing owner page"},
    {"kind": "map", "cluster_id": "button_click", "page": "/sounds/button-click", "role": "primary", "decision": "improve_existing", "reason": "…"},
    {"kind": "map", "cluster_id": "button_click", "page": "/sounds/button-click?style=retro", "role": "filter", "decision": "filter", "conditions": {"style": "retro"}, "reason": "attribute, 1 member"},
    {"kind": "redirect", "from": "/sounds/ui-click", "to": "/sounds/button-click", "reason": "cannibalization confirmed in 2 windows"},
    {"kind": "cluster_status", "cluster_id": "underwater_click", "status": "hold", "reason": "3 keywords, 1 item"},
    {"kind": "promote", "parent": "button_click", "attribute": {"style": "retro"}, "cluster": {"...full cluster definition"}, "reason": "…"}
  ]
}
```

`published_at` comes from a project record (deploy log, CMS field, sitemap lastmod) and says which;
it drives the cooldown and retire checks, so it is never guessed. `apply-changes --dry-run` runs
every check on a proposal (no `approved_by` needed) and writes nothing.

`apply-changes` validates the whole set before writing and rejects it on any error:

- more than one primary page for a cluster;
- an indexable filter URL that owns no cluster;
- redirect chains;
- a non-canonical page marked indexable;
- orphan mappings.

## Site integration contract

The project's build reads the registry. The skill does not build pages. The registry records what
the site must do:

- **Sitemap** = `mapper.py sitemap`: published ∧ indexable ∧ self-canonical. Candidate, planned,
  filter and hold URLs never enter it.
- **Filters**: noindex, with canonical pointing to the parent, until promoted.
- **Merges**: a permanent redirect to the surviving page (target returns 200, no chains or
  loops). Update internal links, the sitemap and the canonical, and keep the metric history
  attached.
- **Retire**: redirect to the closest parent when it exists, otherwise 410. Never leave a soft 404.

## Anti-patterns

- 1 keyword = 1 page; long tail = new page; modifier = new page.
- Publishing every discovered cluster. 5,000 clusters do not justify 5,000 pages.
- Combinatorial template pages with near-zero user value.
- Structure decided by volume or KD alone.
- Copy that stuffs every member keyword instead of expressing the demand structure: entities,
  attributes, sub-needs and actions.
- Claims the inventory cannot back ("no reverb", "for all games") on the page.
