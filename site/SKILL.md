---
name: site
description: 建站和增长的总入口：不知道该用哪个 site-* skill、项目进行到哪一步、下一步做什么时用它。先分模式再分阶段——GEO（靠 AI 助手推荐和引用，任务驱动）：site-idea 需求地图、问题库和新页面空间验证 → site-batch 批量页面 → site-geo 已上线站点持续优化（已上线站点不被推荐时先用它诊断）；SEO（靠搜索排名，关键词驱动）：site-research 选词扩词 → site-plan 词到页面；两边共用：site-kit 建站、site-check 验收、site-measure 统计、site-offsite 站外、site-adsense 广告、site-stripe 收款。它只读项目文件，然后指向对应的 skill。Also for 建站流程、下一步做什么、用哪个 site skill、GEO 还是 SEO、上线前检查。
---

# site: stage router

One name to remember. First pick the mode, then the stage: find it from the project's files, say
which skill and command come next, then load that skill. This skill never writes project files.

## Pick the mode

| 模式 | 出发点 | 什么时候选 |
| --- | --- | --- |
| **GEO** | 用户的真实需求（谁、要完成什么、卡在哪、在哪里问）→ 用户交给 AI 的任务（人群 × 任务 × 限制条件）、AI 答案缺口和我们是否被推荐 | 靠 AI 助手推荐和引用获客；一个想法要批量做页面；已上线站点的流量主要来自 AI |
| **SEO** | 关键词、搜索量、SERP | 靠 Google 搜索排名获客；按关键词决定建哪些页 |

两种模式共用建站、验收的机械部分、统计和变现。一个站可以两者都做，但每个页面的规划只走一种：
批量生成的页面走 GEO（geo/），手写的关键词页走 SEO（seo/）。

## GEO route

先判断起点：

| 起点 | 先走 |
| --- | --- |
| 只有想法 | `site-idea` 第 0 步（需求地图，只有站外证据） |
| 已上线站点，AI 不推荐我们、不知道改哪个页 | `site-geo` optimize O1–O5：任务、问题类型和杠杆、基线（含我们是否出现）、来源诊断。诊断说瓶颈在站外，就走 `site-offsite`；说在现有页面，才用 `site-batch` 接管模式改页 |
| 已上线站点，要开一批新页面（长尾页、新模板） | `site-idea init --live`：一手数据（站内 / API / MCP 搜索、没找到留言、生成描述）打头画需求地图 |

| 顺序 | Skill | 做什么 | 典型说法 |
| --- | --- | --- | --- |
| 0 需求 | `site-idea` | 需求地图（`needs`）和问题库（`bank`）：真实数据里的需求、人群、在哪里问；每个需求从多个角度展开成问法，每条标依据；可选竞品反推 + 盲测 | 用户需求是什么、用户会怎么问 AI、竞品在什么问题下被推荐 |
| 1 想法 | `site-idea` | 任务空间、AI 答案缺口和我们是否出现、改写后的搜索词、杠杆提示，站长决定做、缩小或放弃；已验证维度补长尾取值用 `extend`（`geo/`） | 这个想法值不值得做、从 0 做 GEO |
| 2 页面 | `site-batch` | 资产（缺的先列待生成队列）、事实、模板（`--preview` 给站长看）、组合数据、质量门槛、kit 或 JSON 输出、分波次发布（`geo/`） | 批量做页面、补长尾页、发下一波 |
| 3 建站 | `site-kit` 或项目自己的技术栈 | 页面、基础设施、部署 | 建站、发布 |
| 4 验收 | `site-check` GEO 模式 + `site-geo` 访问检查 | 收录、服务端渲染、答案在前和追问可见；AI 爬虫放行 | 上线前检查 |
| 5 复盘 | `site-batch` review | 主结果是复测时我们是否出现、首推，以及改写搜索词下的排名；再按模板看抓取、收录、AI 抓取、引用，扩量、暂停或修剪 | 这波效果怎么样 |
| 6 持续优化 | `site-geo` optimize | 已上线站点：从真实日志找任务、限制条件矩阵、按问题类型选杠杆、来源诊断、对照实验 | AI 为什么推荐别人、改哪个页 |
| 站外 | `site-offsite` GEO 模式 | 进入 AI 实际引用的来源（榜单、社区、目录、工具渠道） | 让 AI 引用我们 |

## SEO route

| 顺序 | Skill | 做什么 | 典型说法 |
| --- | --- | --- | --- |
| 1 选词 | `site-research` | 新站选词模式（能排上去的词、同类站，`seo/radar/`）；扩词模式（关键词池，`seo/discovery/`） | 新站做什么词、找关键词、扩词 |
| 2 规划 | `site-plan` | 需求簇、页面归属、页面需求单（`seo/mapper/`） | 要不要建页、拆页合页 |
| 3 建站 | `site-kit` 或项目自己的技术栈 | 页面、基础设施、部署 | 建站、发布 |
| 4 验收 | `site-check`（完整，含关键词文案）+ `site-geo` 访问检查 | 页面 SEO 验收 | 页面 SEO 验收 |
| 5 复盘 | `site-plan` review | GSC 回看 → 充实、拆、合、下线 | GSC 回看 |
| 站外 | `site-offsite` SEO 模式 | 外链：目录、竞品外链缺口、投稿和核验 | 找外链 |

## Shared

| Skill | 做什么 |
| --- | --- |
| `site-kit` | 用 kit 建站、检查、发布、升级 |
| `site-measure` | Umami 接入、埋点方案和审计、流量和漏斗报表 |
| `site-adsense` | AdSense 过审预检 |
| `site-stripe` | Stripe 从沙盒切到正式收款 |

## Find the stage

Read only what exists under the project root:

| Evidence | Means |
| --- | --- |
| `geo/project.json` (or another folder passed as `--geo-dir`, e.g. `geo-families/`) | GEO mode: its `stage` (`idea` → `needs` → `space` → `gap` → `decided` → `blueprint` → `pages`) names the step; up to `decided` is site-idea, after it site-batch. `site.live: true` marks a new page space on a live site |
| `geo/optimize/` | site-geo optimize has run on a live site |
| no `seo/boundary.json` and no `geo/` | no mode started: ask which mode, or read the traffic sources (site-measure) |
| `seo/discovery/observations.jsonl`, but no `seo/mapper/pages.jsonl` | SEO stage 2 next |
| `seo/mapper/pages.jsonl` | registry exists; pages planned |
| `.sitekit.json` | kit site: build, check and release go through `site-kit` |
| `seo/radar/` | site-research new-site mode has run; its similar-site list feeds keyword expansion and site-offsite |
| `seo/work/sync-check.json` older than the last deploy, or missing | stage 4 is due |
| `umami.config.json` | Umami wired |
| `seo/mapper/evidence/gsc/*.jsonl` | GSC windows imported; newest file name gives the window |

Report the stage in one line, the next command, and anything blocking it. Then load the named skill
and follow it; its own rules and approvals apply.

## Page SEO check

Every site: `site-check` — a sitemap sweep for mechanical and site-wide issues (templates, near
duplicates, internal links, structured data) on every URL, then page checks on picked pages. SEO mode
checks keywords in the copy; GEO mode checks answer-first, constraints and visible follow-ups instead. AI search
visibility (AI crawlers, llms.txt, ChatGPT probes) runs separately in `site-geo`. Then by site type:

| Site | Technical gates | Registry |
| --- | --- | --- |
| kit site | `npm run check` (rules in site-kit `references/seo-gates.md`) and `npm run kit:shots` | `mapper.py --root <site> sync-check --sitemap .sitekit/reports/sitemap-urls.txt --pages .sitekit/reports/pages.json` |
| other site | the `site-check` skill (it also covers non-kit sites) | `mapper.py --root <project> sync-check --sitemap <sitemap URL>`; add `--pages` when the project can export `[{url, title, …}]` |

`sync-check` reports live URLs missing from the registry and, with `--pages`, title, page-type and
indexability drift.

## Ownership

Each fact has one owner: demand map, question bank, idea, gap check and decision → site-idea (`geo/project.json`, `geo/needs.jsonl`, `geo/questions.jsonl`, `geo/gap/`); templates, page data and waves → site-batch (`geo/`); similar sites and keyword evidence → site-research; live-site GEO findings and experiments → site-geo (`geo/optimize/`); off-site ledger → site-offsite; clusters, page ownership, briefs and GSC
data → site-plan; what the built pages actually say → the site build (site-kit reports for kit
sites); traffic → site-measure. site-check owns no data: it reports.
