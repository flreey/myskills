# myskills

我的 Claude Code / Codex CLI Skills 集合。每一个子目录都是一个独立的 skill，遵循通用的 `SKILL.md` 标准（YAML frontmatter + 自然语言指令 + 可选 `scripts/` / `references/` / `assets/`）。大多数 skill 包可以在两侧直接使用；依赖特定宿主能力的 skill 会在自己的 README 中明确平台限制。

> **目录命名约定**：skill 子目录名必须等于 `SKILL.md` 里 `name:` 字段（这样 `/skill-name` slash 命令才能直接触发）。

## 当前 Skills

| Skill | 描述 |
| --- | --- |
| [prompt-builder](./prompt-builder) | 把模糊、随意、不完整的需求，通过引导式提问 + 合理默认值 + 自评 + 模型适配，转换为高质量的结构化 prompt。覆盖 image / product / writing / code / business / research / agent 七大类型。 |
| [system-evolution-skill](./system-evolution-skill) | 用 "System → Information → Energy → Feedback → Evolution" 框架做系统级分析。把模糊的复杂问题（产品/获客/策略/学习/工作流/AI agent 设计）拆成系统边界、失败点、可度量反馈，再给出最小可验证实验。配套 templates 和 examples。 |
| [cross-cli-review](./cross-cli-review) | 让 Claude Code 调用 Codex CLI 做 review，或反过来。把每次都做不好的跨 CLI review 固化成模板：正确的命令（sandbox / cwd / reasoning effort / base branch）+ 正确的 prompt（文件系统边界 / 焦点 / 输出格式 / DO NOT）+ 输出原样呈现。覆盖 general / security / performance / architecture / plan / challenge 六种 review 类型。 |
| [overseas-micro-product-scout](./overseas-micro-product-scout) | 挖掘和评估海外微型产品机会的硬过滤器：先查付费/免费竞品，再找未满足的小动作，只保留数据源可见、业务浅、能 7-10 天验证的工具站 / 插件 / 平台 app / QA preflight / converter / report generator。 |
| [skill-forge](./skill-forge) | 构建"效果经过验证"的领域 skill，而不是通用货。三模式：bootstrap（新领域薄引导 skill）/ forge（完整构建：搜现有 → 定位分诊 → 萃取访谈 → 生成 → 验证）/ harvest（从 lessons.md 把重复纠正结晶成 skill）。两道硬门禁：生成前必须访谈，交付前必须跑分级 A/B 验证；产出 skill 工具无关，Claude Code / Codex 双侧可用。 |
| [steelman-deliberation](./steelman-deliberation) | 显式触发的双向钢人决策流程：第一轮强化真实问题与正反最强论证，定位分歧和关键变量，只问一个决定性问题；收到回答后才给明确判断与下一步。 |
| [loop-spec-author](./loop-spec-author) | 把“反复做到符合预期”的模糊目标逼成可执行 loop spec：先定义 runnable DONE、进度信号、不变量和三种出口，再交给执行器；明确不负责执行 loop。 |
| [relight-cocos-delivery-primer](./relight-cocos-delivery-primer) | Relight Cocos Creator 项目的工程交付 primer：固定 Cocos 3.8.8、TypeScript、Web/Android/iOS 边界，区分纯玩法逻辑与 Cocos view 层，并要求视觉/交互改动做浏览器验证。 |
| [relight-game-design-guardrails](./relight-game-design-guardrails) | Relight 玩法设计护栏：任何新机制/章节/关卡批量规划先回答“连线后恢复了什么意义”，避免为了连线而连线，强调 star-chart/world-state 的可见回报。 |
| [hook-template-builder](./hook-template-builder) | 扫描项目并推荐 Codex/Claude agent hooks：先识别语言、测试命令、CI、AGENTS/CLAUDE、已有 hooks，再输出候选表；默认只生成提醒型项目模板，阻断型、全局安装、网络通知必须用户确认。 |
| [review-fix-push](./review-fix-push) | 轻量交付编排：当用户说“review 没问题就提交 push，有问题修到完成”时，先审查 staged/unstaged/untracked/未 push commits，全量修可判定问题并复验，再 commit + regular push；判断型问题才停下来问。 |
| [branch-cleanup](./branch-cleanup) | 把当前 git 项目收拢到只剩 main：只读盘点本地/远端分支和 worktree（已合并、可快进、无冲突分叉、冲突、squash 过；脏改动、正在用的进程、软链、会被删的忽略文件），完成的工作合进本地 main 并跑项目测试，其余打 `archive/<branch>` 标签再删，用快照核对没丢提交；不推送、不删远端。 |
| [ai-feature-delivery](./ai-feature-delivery) | 把业务级功能修改请求变成受控交付流程：先只读识别影响面、验收场景、non-goals 和验证计划，确认后再实现，最后输出验证证据与剩余风险。 |
| [chatgpt-pro-engineering-loop](./chatgpt-pro-engineering-loop) | Codex Desktop 通过已登录的 ChatGPT Pro 委派复杂仓库任务：优先用独立 GitHub 任务分支 + Draft PR 交换代码，以持久 conversation ID 恢复中断任务，并在本地隔离验收；GitHub 不可用或源码不能发布时回退到安全源码包。 |
| [project-truth](./project-truth) | 让 AI 从经过校验的 Capability、Receipt 和 Git 状态驱动实现：只读获取紧凑真相上下文，通过固定版本 CLI 记录真实证据，重建离线 Dashboard，并停在人工验收和外部动作边界。 |
| [site](./site) | GEO 总入口：和站长写目标卡（`geo-goal.md`：目标、北极星、服务的需求和人群、渠道、不做什么、现状），判断项目在 GEO 循环的哪一步（0 目标卡 → 1 需求和问法 → 2 需求 × 渠道的机会 → 3 先做一小批改动 → 4 复测），说明下一步用哪个 skill；规定目标卡随每次交接传递、按渠道分别决定、放下任何需求或渠道要站长确认。关键词 SEO 不经过这里，直接用 site-research → site-plan。 |
| [site-idea](./site-idea) | GEO 需求和机会：从真实数据画需求地图、展开问题库（每条标依据）、拆任务空间（能做多少页、每页要什么资产）、在 ChatGPT 等助手上探测答案缺口和我们是否出现、补搜索引擎和 agent/API 两个渠道的证据，写“需求 × 渠道”表，由站长决定哪些格子做页面、哪些走站外或产品文档；之后用 `extend` 给已验证维度补长尾取值。状态在项目的 `geo/`（`scripts/geo_idea.py`）。 |
| [site-offsite](./site-offsite) | 外链入口：所有项目的外链都走 bl 外链池（`~/Projects/backlink`），按 `bl guide` 和 `bl project onboard` 做（新项目接入、Common Crawl 海量挖掘、复审、领单投稿、核验）；不在项目里另建台账。GEO 站外（进入 AI 引用的来源）在 site-geo 的 offsite-sources。默认不做付费买链和博客评论。 |
| [site-batch](./site-batch) | 批量页面（程序化 GEO / 长尾页）：盘点资产、写有来源的事实库、设计 2–5 个页面模板（站长批准）、填组合数据，过质量门槛（必填字段、数字必须来自事实、不重复度）后输出 site-kit directory 数据或通用 JSON；分波次发布，按模板看抓取、收录、AI 抓取、引用漏斗，扩量、暂停或修剪（`scripts/geo_engine.py`）。 |
| [site-research](./site-research) | 选词和扩词（SEO 路线），两种模式：新站选词（原 keyword-radar / site-radar：新词抢先、新站反推、弱 SERP 长尾三入口，意图、需求、可排名三关快筛，词站互找并把同类站记进 `seo/radar/sites.md`，输出新域名 1–2 个月能排上去的短名单和 GSC 第 7/14/28 天回收规则）；扩词（从联想词、Keyword Planner、Trends、Search Console、SERP、竞品 sitemap 等免费来源建证据化的关键词池，`scripts/discovery.py`，按产出判断饱和）。 |
| [site-plan](./site-plan) | 把关键词池变成需求簇和页面决策：模型分批做语义归簇（稳定 ID、定义版本、合并/拆分谱系），修饰词默认是属性，按证据门槛决定 keep / improve / filter / create / defer，变更集经批准才写入页面注册表；建页或改版前为每页生成需求单（细分需求对照库存和页面已写到的内容），并用 GSC 窗口复盘互抢排名、属性升级与下线。 |
| [site-check](./site-check) | 页面验收，SEO 和 GEO 两种模式：先按 sitemap 全站扫描机械问题和模板级问题（`scripts/page_check.py`），再抽页检查；SEO 模式看文案是否围绕目标词，GEO 模式看答案是否在前、限制条件是否写明、追问是否可见、数字是否与事实库一致；两种模式都查 FAQ、服务端渲染、可收录和结构化数据。 |
| [site-geo](./site-geo) | 已上线站点的 GEO，三种模式：缺口扫描（只给网址，公开来源建需求池、按站型校准问法、经 Glasser 批量问 ChatGPT 网页版，分五类给改法，`scripts/gap_scan.py`）；检查（robots.txt 对各 AI 爬虫的规则、AI user-agent 实际拿到什么、llms.txt 是否与线上一致、ChatGPT 能否打开引用和推荐，`scripts/geo_check.py`）；持续优化（从 AI 抓取、引荐落地页、站内/API/MCP 搜索落空等真实来源找任务，限制条件矩阵、多轮对话、按问题类型选杠杆、基线和来源诊断，留出集、哨兵集、对照组实验，`scripts/geo_optimize.py`）。 |
| [site-adsense](./site-adsense) | AdSense 过审预检，只用自己的审计：只读脚本核对广告代码、ads.txt、完整 sitemap、信任页、隐私政策、CMP、抽样页字数、带参数 URL、页脚与模板占比、sitemap 构成和语言版本、敏感词、政策页措辞、域名年龄和爬虫访问，逐条判定（属实 / 部分属实 / 误报 / 现在不适用 / 无法查证）；用户贴来外部报告或拒审原因时一并查证，并核对页面承诺与实际行为；默认只评估不改文件。 |
| [site-measure](./site-measure) | 把已有网站从 Google Analytics 迁到自建 Umami：先只读盘点（加载代码、事件、排除规则、CSP、隐私文字、测试、GA4 报表脚本），再分两次发布：先和 GA 并行、事件两边都发并补等待队列，对完数再删 GA；另带只读的 Umami 报表脚本；按网站类型（tool / landing / directory / app / 内容站）给出埋点方案和标准漏斗，用只读审计脚本对照项目里的 `track(` 调用（缺失事件、命名、字段白名单、隐私说明覆盖），用漏斗脚本按会话算转化率和事件字段分布，并排除站长自测会话。开发完成后，把埋点方案里的漏斗和目标写成项目里的 `umami-reports.json`，同步成 Umami 后台保存的漏斗和目标（默认只预览，`--apply` 才写入，不删除），作为站点的衡量体系。依赖本机 `~/Projects/umami` 的 umami-connect 和自建 Umami 服务；迁移不用于 site-kit 建的站；报表脚本能读任何站点，包括 site-kit 站点。 |
| [site-stripe](./site-stripe) | 站长自己的 Stripe 上线标准（site-kit app 站为主，也兼容非 kit 站）：每个站在组织下建独立的香港账户、沿用已验证的共享主体，按统一配置表（美元、不含税、税码、欧盟/英国走 Managed Payments、Radar Lite、账单显示名、美元结算）从沙盒走到正式收款；先上线不卖、再激活和切 live；附带一个站长在自己终端运行的通用脚本，用来建价格、转移 lookup key、重建 webhook 和写入密钥，密钥不经过 AI。 |
| [family-story-kit-design](./family-story-kit-design) | 设计和审查交付给家庭的可打印亲子场景游戏（寻宝、生日冒险、跨日节庆故事套装）：先写体验承诺，把剧情转成孩子真正要做的动作，闭合线索链与谜题唯一解，从玩法推导材料，再按家长布置与孩子游玩两条视角走查；纸面模拟、PDF 渲染与真实试玩分开记录。不负责生成器代码、网站或支付。 |
| [ui](./ui) | UI 设计的中文入口，6 个：`/ui-flow` 定交互流程和状态（`docs/flow.md`）、`/ui-style` 从 site-kit preset 和 ui-ux-pro-max 出候选让站长挑并锁定外观（写进主题、PRODUCT.md Brand Commitments 和 DESIGN.md，之后 impeccable 不再随机抽方向）、`/ui-critique` 评审、`/ui-polish` 打磨、`/ui-redesign` 明确要大胆时走 impeccable 新设计流程、`/ui 描述问题` 自动选 impeccable 命令。site-kit 新站第 2、3 阶段自动加载 `ui-flow` 和 `ui-style`。依赖已安装的 impeccable 和 ui-ux-pro-max。 |

## 📋 一键安装（直接复制粘贴）

把下面任意一行粘给 Claude Code 或 Codex CLI，agent 会自动识别 skill 子目录、选对应平台路径、用 sparse-checkout 拉下来：

```text
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/prompt-builder
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/system-evolution-skill
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/cross-cli-review
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/overseas-micro-product-scout
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/skill-forge
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/steelman-deliberation
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/loop-spec-author
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/relight-cocos-delivery-primer
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/relight-game-design-guardrails
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/hook-template-builder
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/review-fix-push
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/ai-feature-delivery
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/chatgpt-pro-engineering-loop
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/project-truth
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site-research
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site-plan
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site-check
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site-geo
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site-measure
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/family-story-kit-design
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/site-stripe
```

> **就这一行。** 现代 coding agent 已经原生理解 GitHub `tree/main/<subdir>` 这种子目录 URL + `SKILL.md` 标准 + skills 目录约定，不需要手把手写步骤。
>
> 如果你的 agent 比较笨 / 是旧版本 / 在受限环境，用下面的[详细兜底版](#详细安装-prompt兜底版)。

### 装到项目内（不是全局）

```text
帮我把这个 skill 装到当前项目内（.claude/skills/ 或 .codex/skills/）：
https://github.com/flreey/myskills/tree/main/prompt-builder
```

## 装好后如何启动

1. **多数情况下即时识别** — Claude Code / Codex 通常会动态扫描 `~/.claude/skills/` 或 `~/.codex/skills/`，把每个 skill 的 `name + description` 注入到当前会话的系统上下文，无需重启。如果没出现，再开一个新会话。
2. **触发方式** — 任选其一：
   - **自然语言**：发出符合 description 的请求，例如：
     - "帮我把这个想法变成 prompt"
     - "我想做个 X，整理成可以发给 Claude 的 prompt"
     - "我要画一张画，帮我写图片 prompt"
   - **显式调用**：直接说 `用 prompt-builder skill ...` 或在 Claude Code 输入 `/prompt-builder`
3. **验证装好了** — 问 agent："你看到 prompt-builder 这个 skill 了吗？" 它能背出 description 就说明装对了。

## site-research + site-plan 快速上手

> 改名记录：2026-10-01 `search-demand-discovery` → `site-keywords`、`search-demand-mapper` → `site-pages`；2026-10-21 按建站阶段改为 `site-research`、`site-plan`，`site-analytics` → `site-measure`，并新增入口 `site`。项目里的 `seo/` 目录和数据格式不变；按旧链接装过的，用上面的新链接重新安装。

`site-research`（找词）和 `site-plan`（定页面）是一组，按顺序配合使用，共用项目根目录下的 `seo/`：site-research 写关键词池，site-plan 读它并写需求簇和页面注册表。平时只用两个斜杠命令或自然语言，引擎子命令由 agent 按流程调用。

site-* skill 以 GEO 为主：入口 `/site` 先写目标卡，再按 GEO 循环给下一步；关键词 SEO 是独立路线，直接用 `/site-research` → `/site-plan`，不经过 `/site`。每个事实只有一个主人。site-idea 管想法、答案缺口和做不做的决定，site-batch 管模板、组合数据和发布波次（两者共用项目根目录下的 `geo/`）；site-research 管外部需求证据（关键词池）；site-plan 管需求簇、页面归属、页面已覆盖的细分需求（`covered_attributes`）和 GSC 数据（唯一入口）；site-kit 的构建产物管页面实际状态（标题、可索引）；site-measure 管 Umami 报表；site-check 只做页面验收，不持有数据。同类站名单 `seo/radar/sites.md` 和 `site_keywords` 原始结果归 site-research 的新站选词模式；扩词模式导入这些结果、site-offsite 从名单挑对照站，两者只读。GEO 路线的 AI 回答记录在 `geo/`（site-idea 的 `gap/`、site-geo 的 `scan-<日期>/` 和 `optimize/`），site-offsite 的 GEO 模式只读。交接都落成文件：词池 → 注册表和需求单 → 建页 → `sync-check` 回读构建产物 → GSC 回看，未归类查询经 `seo/work/unmapped-queries.json` 回到词池。节奏、队列和授权留在各项目里。

```text
/site-research   给 ~/Projects/xxx 做关键词挖掘
（回答不超过 5 道选择题，或说"你定"；扩词在后台跑，可选在内置浏览器登录 GSC / Keyword Planner）
/site-plan       把 seo 关键词池归簇，给出页面方案
（审阅变更集，批准后才写入注册表；不包括改代码、建页或部署）
……上线满 28 天后……
/site-plan       我导出了 GSC，看看要不要拆页合页
```

| 项目情况 | 怎么用 |
| --- | --- |
| 新站（未上线、没有 GSC） | site-research 找词 → site-plan 规划页面，不需要同步 |
| 已上线的站 | 先让 site-plan 用 `sync-check --sitemap` 登记现有页面，并尽早导入 GSC：真实查询里常有大量补全扩词找不到的需求 |
| 已有自己的关键词引擎 | 只借用方法（种子收敛、分组审核、页面门槛），不另建第二套数据 |

| 阶段 | site-research 子命令（`scripts/discovery.py --root <项目>`） | site-plan 子命令（`scripts/mapper.py --root <项目>`） |
| --- | --- | --- |
| 建目录 | `init` | `init` |
| 种子 | `seed add/list/reject`；内容或 SKU 上千时先 `consolidate` → `probe` → `seed review` → `seed apply-review` | |
| 扩词与导入 | `suggest --level quick\|standard\|deep`、`import --format gkp\|gsc\|trends\|csv\|json\|lines`、`sitemap --url` | |
| 每轮整理 | `seed aliases`、`concepts`、`triage`、`boundary audit`、`round`（给出继续或停止） | |
| 同步现有页面 | | `sync-check --sitemap <文件或URL>` |
| 归簇审核 | | `prepare-review`（`--plan` 估批数）→ `apply-review` |
| 页面方案 | | `analyze`、`serp add/compare`、`apply-changes --dry-run` → 批准后 `apply-changes`、`validate` |
| 建页或改版前 | | `brief --page <url>` / `--all`（需求单）；部署后 `sync-check --pages .sitekit/reports/pages.json` |
| 上线后复盘 | `import --format json --file seo/work/unmapped-queries.json`（未归类查询） | `gsc import`（UI 导出或 API 行数据，GSC 只存这一处）、`gsc review` |
| 查看 | `status`、`export` | `status`（派生文件是否过期）、`sitemap` |

准备：项目路径和线上网址（已上线的站加 sitemap）、内容或库存数据来源（库存数由项目数据计数，不能估）、可选的 GSC / Planner 登录。建议 `.gitignore` 忽略 `seo/discovery/cache/`、`seo/discovery/raw/`、`seo/mapper/evidence/gsc/`；边界、种子、需求簇和注册表可以提交。参考规模（SFXMint 试跑）：300 个种子跑 standard 约 45 分钟，1.7 万词归簇审核约 50 批。已知限制见两个 SKILL.md 末尾。

## 与 superpowers 等其他 skill 共存

`prompt-builder` 跟 `superpowers:brainstorming` 这类 skill **职能不同**，理解清楚就不会混淆：

| Skill | 输入 | 输出 | 用途 |
| --- | --- | --- | --- |
| `superpowers:brainstorming` | 模糊想法 | **设计文档 + spec** | 探索需求 → 写代码 |
| `prompt-builder` (本仓库) | 模糊想法 | **可复制的 LLM prompt** | 发给另一个 LLM 执行 |

**冲突场景与处理**：
- 名字不会冲突（`prompt-builder` 没有 `superpowers:` 前缀，独立命名空间）。
- description 触发条件**有重叠**——都会接"模糊请求"。Agent 会自己选最匹配的；如果选错，**显式说**：
  - 想要 prompt：`用 prompt-builder 帮我...`
  - 想要 design doc：`用 brainstorming 帮我...`
- 想暂时禁用 superpowers 的某个 skill，可在 `~/.claude/settings.json` 或 `~/.codex/config.toml` 里 disable，无需卸载。

## 手动安装（不用 agent）

```bash
# 方式 1：克隆整仓库再复制
git clone https://github.com/flreey/myskills.git
cp -R myskills/prompt-builder ~/.claude/skills/   # Claude Code
cp -R myskills/prompt-builder ~/.codex/skills/    # Codex CLI

# 方式 2：sparse-checkout 只拉一个 skill
git clone --depth=1 --filter=blob:none --sparse https://github.com/flreey/myskills.git
cd myskills
git sparse-checkout set prompt-builder
cp -R prompt-builder ~/.claude/skills/   # 或 ~/.codex/skills/
```

## 平台对照

| 平台 | 个人路径 | 项目路径 | 配置文件 |
| --- | --- | --- | --- |
| Claude Code | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/skills/<name>/` | `.codex/skills/<name>/` 或 `.agents/skills/<name>/` | `~/.codex/AGENTS.md` |

## 目录结构约定

```
<skill-name>/                # 目录名必须 == SKILL.md frontmatter 里的 name
├── SKILL.md                 # 必需，YAML frontmatter（name + description）+ 指令正文
├── README.md                # 可选，给人看的说明
├── AGENTS.md                # 可选，给 Codex 的额外提示
├── scripts/                 # 可选，CLI 脚本
├── references/              # 可选，长文档 / 模板 / 参考资料（按需加载）
└── assets/                  # 可选，模板 / 图片
```

## 添加新 Skill

1. 在仓库根目录新建 `<skill-name>/`（**目录名 = SKILL.md 里的 `name:`**）
2. 至少放一个带 frontmatter 的 `SKILL.md`
3. 在 "当前 Skills" 表格加一行
4. 在 "📋 一键安装" 那段把 `prompt-builder` 替换成新 skill 名复制一份
5. push（或开 PR）

## 详细安装 Prompt（兜底版）

如果一行 URL 那种简洁 prompt 在你的 agent 上没起作用（比如 agent 不懂 GitHub URL 解析、或环境受限），用这一段把每一步写死：

````text
请帮我从 GitHub 安装并启用 prompt-builder 这个 skill。仓库地址 https://github.com/flreey/myskills

请按以下步骤执行（你需要自动判断当前是 Claude Code 还是 Codex CLI 或其他 agent，并选用对应路径）：

1. 确定目标安装目录：
   - Claude Code → ~/.claude/skills/prompt-builder/
   - Codex CLI   → ~/.codex/skills/prompt-builder/
   - 其他 agent  → 询问我目标目录
   父目录不存在就 mkdir -p。如果目标目录已存在，备份成 <name>.bak.<timestamp> 再继续。

2. 用 git sparse-checkout 只拉这一个 skill 子目录（避免下载整仓库）：
   - 创建一个临时目录（mktemp -d）
   - 在临时目录里：git clone --depth=1 --filter=blob:none --sparse https://github.com/flreey/myskills.git
   - cd myskills && git sparse-checkout set prompt-builder
   - 把 prompt-builder/ 完整 cp -R 到第 1 步确定的目标目录
   - 删掉临时目录

3. 校验：
   - <目标目录>/SKILL.md 存在
   - YAML frontmatter 含 name 和 description 字段
   - references/templates/ 下有 7 个 .md 模板文件

4. 安装完成后，告诉我：
   - 实际安装路径
   - 这个 skill 的触发条件（哪些请求会激活它）
   - 是否需要重启会话才能识别

如果任何一步失败，停下来报告错误，不要静默继续。
````

## License

MIT
