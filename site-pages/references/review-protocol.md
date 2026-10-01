# Review protocol (model semantic review)

`prepare-review` writes `seo/mapper/reviews/<review_id>/input.json`. The input contains:

- the market and the enums (tasks, deliveries, page types);
- the boundary;
- every active cluster, with its definition and member count;
- up to 100 keywords, each with its observations, previous decision, why it was queued, and
  lexical hints.

Answer with `output.json`, then run `apply-review --file output.json`.

## Output

```json
{
  "review_id": "<from input>",
  "clusters": [ { "...new clusters, or a definition update of an existing one (version + 1)" } ],
  "decisions": [ { "...exactly one per input keyword" } ],
  "operations": [ { "kind": "merge", "from": ["a"], "to": "b", "reason": "..." } ]
}
```

### Decision

```json
{
  "keyword_id": "kw_…",
  "status": "included | excluded | pending",
  "language": "en",
  "intent": {
    "task":     {"value": "acquire_asset", "basis": "inferred", "reason": "…"},
    "job":      {"value": null, "basis": "unknown", "reason": "no use case stated"},
    "delivery": {"value": "asset", "basis": "explicit", "quote": "mp3", "reason": "file format requested"}
  },
  "entity": "button click",
  "attributes": {"style": ["soft"], "format": ["mp3"], "license": ["free"]},
  "cluster_id": "button_click",
  "reason": "UI button feedback; soft and mp3 narrow the same set",
  "evidence_ids": ["obs_…"]
}
```

- `explicit` needs a `quote` that literally occurs in the keyword. `inferred` needs a reason.
  `unknown` has `value: null`. A seed name or source name is never a quote.
- `job` is the concrete use case ("add click feedback to a mobile game menu"). It is not the
  entity repeated.
- `language` is your judgement, not the request's `hl`. GSC queries arrive as `und`.
- Attributes are the constraints the user stated. Do not add attributes the query does not say.
- `excluded` and `pending` have `cluster_id: null`, but still record intent, reason and evidence.
  Record the task and delivery of out-of-scope queries before excluding them.

### Cluster

```json
{
  "id": "button_click",
  "label": "Button click sounds",
  "intent": {"task": "acquire_asset", "delivery": "asset"},
  "entity": "button click",
  "page_type": "resource",
  "expected_result_set": "UI button press and tap feedback sound assets",
  "version": 1,
  "parent": null,
  "definition": {
    "summary": "…",
    "includes": ["button click, press and tap feedback; style and format variants"],
    "excludes": ["physical mouse mechanism clicks", "sound generators", "sound packs"],
    "representative_keywords": ["button click sound"],
    "evidence_ids": ["obs_…"],
    "neighbor_distinction": "mouse_click is a hardware source; ui_hover is a different event"
  }
}
```

Representative keywords must be members of the cluster. Existing clusters appear in `clusters`
only for a definition update (with `version` + 1), and their identity fields must not change.

### Shorthand

Large pools make the full form expensive. `apply-review` expands these before validating, so
every decision still states its own status, cluster and reason:

- `"defaults": {"language": "en", "intent": "cluster"}` at the top of the output fills decisions
  and group decisions that leave those fields out.
- `"intent": "cluster"` on an included decision takes the cluster's task and delivery as
  `inferred` and the job as `unknown`. On excluded or pending decisions it is rejected.
- Compact intent: `{"task": "learn", "delivery": null}`. A string becomes `inferred` with the
  decision's reason; null or a missing dimension becomes `unknown`.
- `entity` left out on an included decision is the cluster's entity.
- `evidence_ids` left out are the keyword's observations from the input; `attributes` left out
  are its `attributes_detected`. Write `attributes` whenever the keyword states more.
- A new cluster's `definition.evidence_ids` left out are its representative keywords'
  observations. Summary, includes, excludes and the neighbor distinction stay required.

## Sizing the queue

`prepare-review --plan` counts every queued unit by kind and the batches the current limits
need, without writing a batch. Run it before a full review and after discovery changes (aliases,
boundary terms, new seeds), which move keywords from singles into groups.

## Grouped review (default)

The pool is mostly the same demand said many ways, so `prepare-review` proposes review units
mechanically. It uses only the discovery contract: seeds with their aliases, and the boundary's
modifiers, head terms and adjacent/out terms. You still decide every unit.

| Unit | Formed from | Typical decision |
| --- | --- | --- |
| `boundary` group | Keywords containing an out or adjacent term ("wiki", "how to make") | Exclude as a group; `except` in-scope members ("free to use sound effects" inside "use") |
| `variants` group | A seed plus only modifiers, head terms and filler ("door knock sound effect mp3") | Include in the seed's cluster; `except` members with a different result set |
| `facet` group | The same extra words across ≥ `review_facet_min` (3) seeds ("… meme", "crowd …") | `cluster_id: "@seed"` puts each member in its own seed's cluster, plus `add_attributes`; or exclude ("what does X sound like") |
| single | Everything else, including keywords with no known seed | Decide one by one |

Order: boundary groups, then per seed its variants group and its singles, then unseeded
singles, and facet groups last. `@seed` needs every member's seed to be clustered already; the
command rejects members whose seed has no cluster, so `except` them. Use `--only
variants|facet|boundary|single` to work one kind at a time. `--no-groups` restores
one-keyword-per-item review. A group decision:

```json
{"group_id": "g_…", "status": "included", "language": "en", "intent": {…},
 "entity": "door knock", "cluster_id": "door_knock",
 "except": ["kw_…"], "reason": "same result set; modifiers only"}
```

- Members get `attributes_detected` (modifier values literally in the keyword).
  `add_attributes` applies a value only to members that literally contain it.
- Evidence ids come from each member's own observations.
- Every keyword in the batch is covered exactly once: by a group decision or by an entry in
  `decisions`, which is required for every `except` id.
- `explicit` intent bases must quote words present in every member, so groups normally use
  `inferred`.
- Group quality depends on seed alias hygiene. A generic alias ("reaction", "footsteps" on two
  seeds) sends keywords to the wrong group, so clean aliases in discovery first. Finishing
  discovery triage also shrinks review, because every term triaged as modifier, adjacent or out
  turns singles into group members.

## Grouping tests

Apply them in order. A cluster is a group of queries that the **same result set** satisfies.

1. **Result set.** Should both searchers ideally see essentially the same items? If yes, merge
   ("button click sound" and "button click mp3"). If no, they are split candidates ("button click"
   versus "mouse click").
2. **Job.** Are they completing the same task? Acquiring a sound differs from learning to make one.
3. **Page type.** Is the natural answer the same kind of page? A download or resource page differs
   from a tutorial, a tool, a comparison or a pack.
4. **SERP (tie-breaker).** When unsure, keep both `pending` or park them in the closer cluster.
   `analyze` then queues SERP captures, and `serp compare` gives overlap. At least 6 of the top 10
   shared means the same result set; at most 3 means different.

A more specific use case does not mean more clusters. One sound set can serve both games and
videos; keep the use case on the keyword. But short assets and continuous listening are
different deliveries, and so are single items and packs. Do not merge them just because the
entity matches.

## Operations

- **merge**: `from: [ids]` → `to: id`. Sources are retired with successors, and their members move
  (actor `lineage`).
- **split**: `from: id` → `to: [ids ≥ 2]`. The source is retired. Members not reassigned in this
  batch become `pending` and are reviewed again.
- Targets must exist or be defined in the same output.

## Human decisions

When the user states a decision in chat, write it in the same format without a `review_id`, add
`"reason_source": "chat <date>"`, and run `apply-review --actor human`. The model can no longer
overwrite that keyword. It can only propose a change for the user to confirm.

## Stale and repeat

- New evidence or a definition version bump puts a keyword back in the queue. Otherwise decided
  keywords are not reviewed again. Use `--pending` or `--id` to force a re-review.
- A second `apply-review` with identical output is a no-op. Different output for an applied
  review is rejected: prepare a new batch.
