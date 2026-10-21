---
name: site
description: Use as the entry point for the site-* skills when the user asks where a website project stands or what comes next across keyword research, page planning, building, SEO checks, launch and analytics — or does not remember which site-* skill to use. Also for 建站流程、下一步做什么、用哪个 site skill、页面 SEO 验收、上线前 SEO 检查. It only reads project files and routes; the work happens in site-research, site-plan, site-kit, site-check and site-measure.
---

# site: stage router

One name to remember. Find the project's stage from its files, say which skill and command come
next, then load that skill. This skill never writes project files.

| Stage | Skill | Does | Typical ask |
| --- | --- | --- | --- |
| 1 research | `site-research` | keyword pool from external evidence (`seo/discovery/`) | 找关键词、扩词 |
| 2 plan | `site-plan` | demand clusters, page registry, page briefs (`seo/mapper/`) | 要不要建页、归簇、页面需求单 |
| 3 build | `site-kit` (kit sites) or the project's own stack | pages, SEO plumbing, checks, deploy | 建站、改页面、发布 |
| 4 verify | `site-check`, then see [Page SEO check](#page-seo-check) | keyword copy, FAQ, server HTML, ChatGPT access and recommendation; registry matches the built site | 页面 SEO 验收、GPT 能不能访问 |
| 5 measure | `site-measure` | Umami wiring and traffic reports | 接入 Umami、看流量 |
| 6 review | `site-plan` review mode | GSC windows → enrich, split, merge, retire; unmapped queries back to stage 1 | 拆页合页、GSC 回看 |

## Find the stage

Read only what exists under the project root:

| Evidence | Means |
| --- | --- |
| no `seo/boundary.json` | stage 1 has not started |
| `seo/discovery/observations.jsonl`, but no `seo/mapper/pages.jsonl` | stage 2 next |
| `seo/mapper/pages.jsonl` | registry exists; pages planned |
| `.sitekit.json` | kit site: build, check and release go through `site-kit` |
| `seo/work/sync-check.json` older than the last deploy, or missing | stage 4 is due |
| `umami.config.json` | Umami wired |
| `seo/mapper/evidence/gsc/*.jsonl` | GSC windows imported; newest file name gives the window |

Report the stage in one line, the next command, and anything blocking it. Then load the named skill
and follow it; its own rules and approvals apply.

## Page SEO check

Every site: `site-check` — a sitemap sweep for mechanical issues on every URL, then page checks on
picked pages (keywords in the copy, FAQ coverage, server rendering, ChatGPT crawler access) and
ChatGPT recommendation probes per target query. Then by site type:

| Site | Technical gates | Registry |
| --- | --- | --- |
| kit site | `npm run check` (rules in site-kit `references/seo-gates.md`) and `npm run kit:shots` | `mapper.py --root <site> sync-check --sitemap .sitekit/reports/sitemap-urls.txt --pages .sitekit/reports/pages.json` |
| other site | optionally the `seo-page` skill for meta, canonical, schema and images | `mapper.py --root <project> sync-check --sitemap <sitemap URL>`; add `--pages` when the project can export `[{url, title, …}]` |

`sync-check` reports live URLs missing from the registry and, with `--pages`, title, page-type and
indexability drift.

## Ownership

Each fact has one owner: keyword evidence → site-research; clusters, page ownership, briefs and GSC
data → site-plan; what the built pages actually say → the site build (site-kit reports for kit
sites); traffic → site-measure. site-check owns no data: it reports.
