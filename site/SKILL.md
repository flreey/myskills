---
name: site
description: 建站和增长的总入口：不知道该用哪个 site-* skill、想知道一个网站项目进行到哪一步、下一步做什么时用它。它只读项目文件判断阶段，然后指向对应的 skill：新想法验证（site-idea）、新站选词（site-radar）、扩词（site-research）、词到页面（site-plan）、批量页面（site-batch）、建站发布（site-kit）、SEO 验收（site-check）、AI 可见度（site-geo）、统计（site-measure）、外链（site-backlinks）、AdSense（site-adsense）、Stripe 收款（site-stripe）。Also for 建站流程、下一步做什么、用哪个 site skill、页面 SEO 验收、上线前 SEO 检查。
---

# site: stage router

One name to remember. Find the project's stage from its files, say which skill and command come
next, then load that skill. This skill never writes project files.

| 阶段 | Skill | 做什么 | 典型说法 |
| --- | --- | --- | --- |
| 0 想法 | `site-idea` | 新想法要批量做页面前：任务空间、AI 答案缺口，站长决定做不做（`geo/`）；已验证维度补长尾取值用 `extend` | 这个想法值不值得做、从 0 做 GEO |
| 1 选词 | `site-radar` | 新站 1–2 个月能排上去的词和同类站（`seo/radar/`） | 新站做什么词、找同类站 |
| 1 扩词 | `site-research` | 方向定了以后扩大关键词池（`seo/discovery/`） | 找关键词、扩词 |
| 2 规划 | `site-plan` | 需求簇、页面归属、页面需求单（`seo/mapper/`） | 要不要建页、归簇、拆页合页 |
| 2 批量页面 | `site-batch` | 模板、组合数据、质量门槛、分波次发布、按模板复盘（`geo/`） | 批量做页面、补长尾页、发下一波 |
| 3 建站 | `site-kit`（kit 站）或项目自己的技术栈 | 页面、SEO 基础设施、检查、部署 | 建站、改页面、发布 |
| 4 验收 | `site-check`，见 [Page SEO check](#page-seo-check) | 关键词文案、FAQ、服务端 HTML、结构、内链和模板 | 页面 SEO 验收 |
| 4 验收（AI） | `site-geo` | AI 爬虫、llms.txt、ChatGPT 能否打开和推荐 | GPT 能不能访问、会不会推荐 |
| 5 统计 | `site-measure` | Umami 接入、埋点方案和审计、流量和漏斗报表 | 接入 Umami、看流量、漏斗 |
| 6 复盘 | `site-plan` review 模式 | GSC 回看 → 充实、拆、合、下线；未归类查询回到第 1 阶段 | 拆页合页、GSC 回看 |
| 增长 | `site-backlinks` | 新站外链：目录、竞品外链缺口、投稿和核验 | 找外链、提交目录 |
| 变现 | `site-adsense` | AdSense 过审预检 | 能不能挂广告 |
| 变现 | `site-stripe` | Stripe 从沙盒切到正式收款 | Stripe 切正式、开始收钱 |

两条路线：按关键词建页走 1 → 2 site-plan → 3；从想法批量建页走 0 site-idea → 2 site-batch → 3。

## Find the stage

Read only what exists under the project root:

| Evidence | Means |
| --- | --- |
| no `seo/boundary.json` | stage 1 has not started |
| `seo/discovery/observations.jsonl`, but no `seo/mapper/pages.jsonl` | stage 2 next |
| `seo/mapper/pages.jsonl` | registry exists; pages planned |
| `.sitekit.json` | kit site: build, check and release go through `site-kit` |
| `geo/project.json` | batch flow: its `stage` (`idea` → `space` → `gap` → `decided` → `blueprint` → `pages`) names the step; up to `decided` is site-idea, after it site-batch |
| `seo/radar/` | site-radar has run; its similar-site list feeds site-research and site-backlinks |
| `seo/work/sync-check.json` older than the last deploy, or missing | stage 4 is due |
| `umami.config.json` | Umami wired |
| `seo/mapper/evidence/gsc/*.jsonl` | GSC windows imported; newest file name gives the window |

Report the stage in one line, the next command, and anything blocking it. Then load the named skill
and follow it; its own rules and approvals apply.

## Page SEO check

Every site: `site-check` — a sitemap sweep for mechanical and site-wide issues (templates, near
duplicates, internal links, structured data) on every URL, then page checks on picked pages
(keywords in the copy, FAQ coverage, server rendering, indexability, structure). AI search
visibility (AI crawlers, llms.txt, ChatGPT probes) runs separately in `site-geo`. Then by site type:

| Site | Technical gates | Registry |
| --- | --- | --- |
| kit site | `npm run check` (rules in site-kit `references/seo-gates.md`) and `npm run kit:shots` | `mapper.py --root <site> sync-check --sitemap .sitekit/reports/sitemap-urls.txt --pages .sitekit/reports/pages.json` |
| other site | the `site-check` skill (it also covers non-kit sites) | `mapper.py --root <project> sync-check --sitemap <sitemap URL>`; add `--pages` when the project can export `[{url, title, …}]` |

`sync-check` reports live URLs missing from the registry and, with `--pages`, title, page-type and
indexability drift.

## Ownership

Each fact has one owner: idea, gap check and decision → site-idea (`geo/project.json`, `geo/gap/`); templates, page data and waves → site-batch (`geo/`); similar sites → site-radar; keyword evidence → site-research; clusters, page ownership, briefs and GSC
data → site-plan; what the built pages actually say → the site build (site-kit reports for kit
sites); traffic → site-measure. site-check and site-geo own no data: they report.
