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
