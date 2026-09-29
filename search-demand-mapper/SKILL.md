---
name: search-demand-mapper
description: Use when deciding which search demand a site should serve and where — grouping keywords into demand clusters, deciding whether a keyword, modifier or cluster deserves its own page, a section, a filter or nothing, planning SEO information architecture from keyword data, reviewing Search Console data to enrich, split, merge or retire pages, or diagnosing keyword cannibalization. Also for 需求簇、关键词归类、要不要建页、拆页合页.
---

# Search Demand Mapper

Search query → user need → demand cluster → page, section, filter or nothing → Search Console
feedback.

Operating stance: cluster aggressively, publish conservatively, split only with evidence, merge
when overlap appears.

Engine (Python stdlib): `python3 <skill-dir>/scripts/mapper.py --root <project> <command>`. It reads
the observation pool from `search-demand-discovery` (`<project>/seo/discovery/`). To start from an
existing keyword export, import it with discovery first. Otherwise evidence ids have nothing to
point at.

## Iron rules

1. **Cluster ≠ page.** A cluster is a demand object. Pages are separate registry decisions:
   many-to-many, with at most one `primary` owner page per cluster.
2. **Modifiers are attributes by default.** Free, MP3, soft, retro and "for games" narrow a result
   set; they do not create one. A longer or different wording never creates a cluster by itself.
3. **The model does the semantic judgement**, in reviewed batches. Lexical hints, rules and
   embeddings only pre-sort. When unclear, mark `pending`.
4. **Identity is fixed.** Cluster identity = intent (task + delivery) + entity + expected result
   set + page type. To change any of these, create a new id and merge or split with lineage.
5. **Human decisions stand.** The model never overwrites them. It proposes changes to the user.
6. **Default merge, evidence to split.** The gates in
   [references/page-decisions.md](references/page-decisions.md) decide create, split and promote.
   Volume, KD and CPC set priority only, never structure.
7. **Requests are not capabilities.** "Free", "wav" and "retro" are what users ask for. Whether the
   inventory satisfies a request is assessed separately. Unknown counts as neither met nor failed,
   and zero matches do not authorize production.
8. **Registry changes need approval.** They take effect only through a change set the user
   approved. That approval does not cover building pages, redirects, commits, deploys or
   publishing, which follow the project's own workflow and permissions.

## Modes

| Situation | Mode | Path |
| --- | --- | --- |
| Pool exists, need clusters and a page plan | **map** | review loop → inventory → `analyze` → SERP → decisions → change set |
| Search Console data after launch | **review** | `gsc import` → `gsc review` → decisions → change set |
| A question about a few keywords ("does X need its own page?") | **decide** | Answer the ten questions below, read-only, with whatever evidence exists |
| Existing site whose registry does not cover every live URL | **sync** | `sync-check` → ownership review → change set, before trusting any page plan |

## Map mode

1. `init`, then `sync-check --sitemap <sitemap file or URL>`. If any live URL is unregistered, run
   **sync** first: a registry that is not empty but incomplete makes `analyze` propose pages the
   site already has. Read the router, sitemap and experiment/cohort config so live experiments are
   not disturbed.
2. **Review loop.** `prepare-review` builds a batch of review units: boundary groups, per-seed
   variant groups, cross-seed facet groups and single keywords (up to 100 units / 600 keywords).
   `--plan` sizes the whole queue first. Read `input.json`, write `output.json` (shorthand
   allowed) following
   [references/review-protocol.md](references/review-protocol.md), then run `apply-review`. Decide
   every group, and use `except` for members that differ. Repeat until the queue is empty or the
   batch budget is spent. The engine rejects outputs whose evidence changed since
   `prepare-review`, that skip or double-cover keywords, that change identity, that use `@seed`
   before a seed is clustered, or that overwrite human decisions.
3. **Inventory.** Write `seo/mapper/inventory.json` from project data: items per cluster and per
   `axis=value`. Count; never estimate. If items cannot be counted, leave them out; the gate then
   reads "inventory unknown".
4. **Analyze.** `analyze` writes `seo/work/analysis.json` with evidence flags, a demand tier,
   suggestions (`keep_or_improve_existing`, `check_existing_page`, `create_candidate`,
   `improve_parent_or_defer`, `defer`, `hold`), attribute candidates, `needs_serp` and
   `registry_coverage`. `check_existing_page` means an unregistered live URL names the cluster:
   sync before planning a new page.
5. **SERP evidence.** Search the `needs_serp` queries in the target market, within the session
   budget (default 30): one query per page load, a human-paced pause between queries, and no
   parallel or scripted batches. At the first CAPTCHA or "unusual traffic" page, stop the whole
   SERP step for the session: never solve, bypass or retry it, and report how many were captured.
   Capture the top-10 organic URLs and result types into a captures file with `served_host` (the
   engine domain that actually answered, e.g. a redirect to google.com.hk) and `localized` (whether
   the target market's ranking was verified), then run `serp add` and `serp compare`. Rerun
   `analyze`.
6. **Decide** each cluster: keep / improve_existing / filter / create / defer, and promote an
   attribute only when its gate passes. Give each decision a reason, the evidence it rests on and
   a priority. Use [references/page-decisions.md](references/page-decisions.md).
7. **Propose.** Write the change set (JSON plus a short Markdown summary), check it with
   `apply-changes --dry-run`, and present it. After explicit approval, run `apply-changes` and
   `validate`. Page work itself is handed to the
   project's implementation workflow.

## Sync mode

1. `sync-check --sitemap <file|URL> [--pages facts.json]` snapshots the live URLs
   (`mapper/site-urls.json`) and writes `work/sync-check.json`: unregistered URLs with lexical
   cluster hints, registry pages missing from the sitemap, and clusters without a primary page.
   `--pages` adds page facts from the project (title, kind, item count) as JSON `[{url, title, …}]`.
2. **Ownership review** (model): for each live page, decide the clusters it owns (`primary`) or
   partly serves (`secondary`), and its page type. One primary page per cluster; the page whose
   result set best matches the cluster wins. Mark a thin or mixed owner `improve_existing`. When
   only several one-item pages name a cluster, leave it without a primary and report the gap.
   Pages that are not meant to own demand use `asset` or `info` (`needs_cluster: false`).
3. Write every live URL as `page_upsert` (published_at from the project's own record, such as the
   sitemap lastmod or a deploy log, labelled as such; never invented) plus the `map` changes.
   Check it with `apply-changes --dry-run`, present it, and apply only after approval.

## Review mode

1. Export per-page query data from Search Console for every primary page. Include at least the
   last `windows_required` (2) windows of 28 days each. Run
   `gsc import --file <zip> --period START..END` for each export.
2. `gsc review` writes `seo/work/gsc-review.json`, which flags:
   - `cannibalization`, `wrong_owner` and `unowned_cluster`;
   - `promotion_signal` (an attribute's queries growing on its parent page);
   - `retire_candidates`;
   - `unmapped_queries`.
3. Act on `confirmed` flags; keep watching `watch` flags; leave `cooldown` alone. Decide per
   [references/feedback-loop.md](references/feedback-loop.md). Unmapped queries go back through
   discovery import and review, never straight onto a page.

## Decide mode — the ten questions

1. What job is the user trying to complete?
2. What is the core entity?
3. Which words are only attributes?
4. Which queries deserve the same result set?
5. Does it belong to an existing cluster?
6. Does an existing page already satisfy it fully?
7. Should it be a page, a section, a filter or nothing?
8. If it should be a new page, is the evidence enough (which gate fails)?
9. What is the priority, and on which signals?
10. After launch, which Search Console signals confirm or reverse the decision?

## Report

Each run reports:

- keywords reviewed, pending and excluded;
- clusters created, merged or split, with lineage;
- per-cluster decisions with evidence flags and missing checks;
- SERP comparisons, with dates;
- the proposed change set;
- **next data needed**: SERP captures, inventory counts, GSC windows, pending keywords.

Keep six verdicts apart and never collapse them into one "verified": `semantic_fit`, `page_plan`,
`local_functionality`, `asset_fit`, `production`, `traffic`.

## Data and premises

The file contract is in [references/data-contract.md](references/data-contract.md). The worked
example is in [references/example-sfxmint.md](references/example-sfxmint.md).

- Checked 2026-09-29. Google's spam policies treat many near-duplicate pages made to rank for
  similar queries as doorway or scaled content abuse; the publish gate exists because of this.
- Thresholds are defaults, not truths. Tune them in `seo/config.json` (`mapper.*`) once a site has
  its own GSC history.
