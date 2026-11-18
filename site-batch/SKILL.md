---
name: site-batch
description: 批量页面（程序化 GEO / 长尾页）：site-idea 定下“做”或“缩小范围”之后，把任务空间变成大量页面——盘点每个组合的独特资产（缺的资产先列成待生成 / 待采集队列，补齐才放行）、写有来源的事实库、设计 2–5 个页面模板（站长批准）、填组合数据并过质量门槛、接入 site-kit directory 站或输出通用 JSON 给其他技术栈，然后分波次发布、按模板看抓取/收录/AI 抓取/引用漏斗、扩量、暂停或修剪；已验证模板里补长尾取值也用它。Also for programmatic pages, long-tail pages, 批量页面、长尾页面、模板页、组合答案表、分波次发布、按模板复盘、修剪页面。不用于：想法是否值得做（site-idea）、单个关键词要不要建页（site-plan）、普通建站与部署（site-kit）、已上线站点的 AI 可见度检查（site-geo）。
---

# site-batch: many pages from data, released in waves

Decided task space → assets → facts → templates (owner approves) → combination rows → quality gate
→ site data → waves → funnel per template → expand, hold, fix or prune. Pages are generated from
data, so each one must hold an answer the assistants cannot give on their own; new domains index
slowly and punish thin bulk, so pages ship in waves and each template earns the next one.

The number of pages comes from dimensions × assets, never from the number of questions: probes
validate a template's question pattern on a sample, and every page still needs its own files, data or
results. A product that can make assets (a generator, a converter, a measurement) can fill missing
combinations first and then publish them; rows say which assets they wait for.

Engine (Python stdlib): `python3 <skill-dir>/scripts/geo_engine.py --root <project> [--geo-dir geo] <command>` with
`lint`, `build` (`--preview T:COMBO`), `status`, `assets`, `questions`, `snapshot`, `scaffold`, `wave-plan`,
`wave-release`, `wave-deployed`, `funnel`, `prune`. State
contract: [../site-idea/references/state.md](../site-idea/references/state.md). References:
[templates](references/templates.md), [questions to pages](references/question-mapping.md), [facts and rows](references/combos.md),
[non-kit output](references/json-output.md), [adopting existing pages](references/adopt.md), [measuring waves](references/measure.md).

## Iron rules

0. **The site skill's rules apply** (goal card first, per-channel decisions, dropping is the owner's
   call, small first, tools get one hour). Read `geo-goal.md` at the project root first; pages serve
   only the needs whose Lever in `gap/channels.md` includes `pages`. End every report with what this
   step dropped compared with the card, or "nothing".
1. **No decision, no pages.** `project.json.decision.verdict` must be `go` or `narrow`; rows stay in
   the decided subspace and use only dimensions the gap check covered (`lint` and the gate enforce it).
   More values of a covered dimension: the owner runs site-idea `extend`. A new dimension or task
   type goes back to site-idea.
2. **Facts have sources.** Every number and claim on a page traces to `geo/facts.jsonl` (a re-checkable
   source and a date) or to a computed key fact. Not the model's memory, not a search snippet.
3. **Missing data means no page.** A combination without the assets for its required fields is left
   out, or kept as a row whose `assets` say what it waits for (`to_generate`, `to_collect`): it fails
   the gate until each one is `ready`. Each row also needs evidence of its own (`min_own_evidence`,
   default 1): a fact, key fact, asset or file that no sibling has and that is not just one
   dimension's parent-page fact. A combination whose evidence is all shared is a section of its
   parent page, not a page. The gate is never loosened to let thin rows through.
4. **The owner approves each template** after seeing the spec and one rendered row (`approved`), and
   each wave before release. `wave-plan` and `wave-release` refuse templates without `approved`. Pattern or required-field changes bump `version` and need approval again.
5. **Waves, never everything at once.** Seed wave 50–200 pages across templates; later waves grow only
   for templates whose pages got crawled and indexed. No verdict before the 3–4 week window.
6. **Generated files are not edited by hand.** `data/*.jsonl`, `geo/out/*` and `geo/instances.jsonl`
   come from `build`; fix rows or templates and rebuild.
7. **The site's own rules hold.** Kit sites: kit files read-only, modules and the item override live
   in `src/site/`, check and deploy through site-kit with its approvals. Other stacks: their own
   workflow. Owner accounts (Search Console, Bing, Cloudflare, AI assistants) are used only with their
   go-ahead; missing data is reported as missing.

## Modes

| Situation | Mode |
| --- | --- |
| Decision recorded, no templates yet | [Blueprint](#blueprint) |
| Templates approved, gated rows ready, or a wave due | [Release](#release) |
| A released wave is past its window | [Review](#review) |
| Adding long-tail values to an approved template | site-idea `extend` (owner) → rows for the new values → `lint` → [Release](#release) |
| A family of existing pages should become GEO pages (keep URLs) | only after site-geo optimize (O4–O5) shows these pages are the bottleneck; then an adopt template ([references/adopt.md](references/adopt.md)): `snapshot` first, then blueprint steps 3–5, release with `--control-ratio` |

## Blueprint

1. **Read the decision.** `geo-goal.md`, `geo/gap/channels.md` (which need × channel cells the pages
   are for, and which cells another lever owns), `geo/project.json` (verdict, subspace), `geo/gap/report.md` (which gaps
   dominate, whether the site is in the answers, the lever hint and the captured search queries),
   `geo/needs.md` and `geo/bank.md` when present, `geo/gap/samples.jsonl` (follow-ups, signals, what
   assistants recommend). When the report's notes say the answers rest on lists, forums or no search,
   tell the owner the pages need site-offsite work beside them before planning a large wave.
2. **Assets.** For the subspace, list what can supply each answer: product capabilities, own tests or
   measurements, structured public data, tool outputs, files people can use. Generated outputs go
   under `geo/assets/`. Show which combinations have assets. Combinations with a real need but no asset
   yet get rows with `assets` marked `to_generate` or `to_collect` ([references/combos.md](references/combos.md));
   `assets` lists that work queue by priority. Making the assets (paid generation, collection) follows
   the project's own approvals; the rows pass the gate only when every asset is `ready`.
3. **Facts.** Write `geo/facts.jsonl` ([references/combos.md](references/combos.md)).
4. **Templates.** One per task type, 2–5 in all, each `geo/templates/<id>.json`
   ([references/templates.md](references/templates.md)); `required` follows the dominant gaps. In a
   capability space (`project.json.space.shape`), one template per capability family, and every page
   opens with the capability and the conditions the assistant checks (free tier and when it is paid,
   limits, upload or not, signup, watermark, devices), each from `facts.jsonl`, with the captured find
   queries (`gap/queries.md`) as the wording for titles. Then
   `questions --template <id>` and map the questions
   ([references/question-mapping.md](references/question-mapping.md)): openings routed to item, group
   or hub by scope; follow-ups merged into 5–8 `question_slots`; `title_source` from item-level
   openings and the captured search queries; group-level openings into group content. Fill two or
   three rows (and one group), `build --preview <template>:<combo>` (renders one row as if released,
   without a wave), show the owner the spec, one rendered item page and one group page, record
   `approved`, then delete `<geo-dir>/out/preview/`. On the question-bank route, `questions` matches
   samples by need (the template's `needs`, else the decision's need subspace) instead of by dimensions.
5. **Rows.** Fill `geo/combos/<id>.jsonl` for at least the seed wave, every required question slot
   answered for that combination, and `geo/combos/<id>.groups.jsonl` for the groups the wave touches;
   `lint`, `status`, fix data until the failure reasons (and `group_failures`) are understood.
6. **Wire the site.**
   - Kit site (`.sitekit.json` present; or create one with site-kit `new --type directory` in a new
     directory and move `geo/` into it): `scaffold --template <id>` per template (writes the module and
     the item and group page overrides), paste the printed
     `site_config_entry` into `modules.directory.collections` (remove the starter `items` collection,
     module and data, point home and nav at the new collections), set `seo.registry.mode` to
     `'advisory'`, `build`, `npm run check`, look at the screenshots.
   - Any other stack: `build` writes `<geo-dir>/out/` (or `project.json.output.dir`); the site renders those
     files following [references/json-output.md](references/json-output.md).
   Nothing is released yet, so no item page is built until the first wave.

## Release

1. `lint` (no errors, templates approved) and `status` (enough gated rows).
2. `wave-plan --per-template <n>` (seed: total 50–200; `--template` for one). Show sizes and sample
   URLs; adjust `geo/waves.json` with the owner.
   With `--control-ratio`, read the printed `baseline` (rows' `baseline` fields summed per side) and
   re-plan if the two sides differ a lot.
3. After the owner's yes: `wave-release --wave <k>`, `build`, the site's checks (kit: `npm run check`
   and a screenshot of a new item page per template), commit, then the site's release (kit: site-kit
   release, which submits new URLs to IndexNow). When the pages are live, `wave-deployed --wave <k>
   --date <day>` and `build`: windows and pruning count from that day. First wave: the owner submits the
   sitemap in Search Console and Bing Webmaster (MANUAL).

## Review

1. One week after a release, then every 1–2 weeks, append rows to `geo/measure/snapshots.jsonl`
   ([references/measure.md](references/measure.md)).
2. After the window (from the `deployed` day): re-run the baseline probes for a sample of the wave and
   its control (presence: in the answer, first, cited) and check the captured search queries; this
   is the primary result ([references/measure.md](references/measure.md)). Then `funnel`; per template decide with the owner — expand (larger next wave), hold
   (fix the step that drops first), fix (rows or template, re-approval for template changes), prune
   (`prune --min-days 28` candidates, handled as references/measure.md says). Write the decision into
   the wave's `note`.
3. When AI referrals arrive weekly and real questions accumulate (site search, feedback, logs), move
   the site to the full GEO method (`~/Projects/GEO/geo-methodology.md`) and keep waves for the rest.

## Report

Mode and stage → templates (task, required fields, approval) and facts (count, oldest `checked`) →
rows per template: total, gated, top failure reasons, rows waiting for assets → waves (planned, released, sizes) → checks and
deploy stages, each separately → funnel per template with page counts and window → decisions → MANUAL
items for the owner → what was not verified → what this step dropped compared with the goal card.

## Premises

The own-evidence gate was added 2026-11-18 after ToHD's first `/fix` wave passed the text-uniqueness
gate by rewording while every row combined its source page's and destination page's facts (14 of 16
rows fail it); SFXMint's released rows (files and computed key facts per row) all still pass.

Written 2026-11-17 against site-kit 2.15 (directory collections from `data/<id>.jsonl`,
`defineCollection`, `gate`, `ungated: 'omit'`, overrides in `src/site/overrides/templates/`). Verified
that day on a scratch directory site: scaffold output built with `astro build`; released rows became
pages with answer, resource button, details, FAQ and FAQPage; unreleased rows were neither built nor
in the sitemap. After a kit upgrade, compare `src/site/overrides/templates/DirectoryItem.astro` with
the kit original; the same for `DirectoryGroup.astro`. The JSON target was tested by unit tests only. Seed size, window and the 28-day prune
age are starting values: recalibrate after the first two waves. AI crawler fetches on kit sites are not
in Worker logs (static assets); Cloudflare's AI crawler reporting is the assumed source, not verified
on a live zone.
