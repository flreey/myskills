# Semrush 与 Similarweb（3ue.co 拼车账号，浏览器操作）

站长在 3ue.co 订了拼车版 **Semrush GURU**（sem.3ue.co）和 **Similarweb PRO 全球版**（sim.3ue.co）。2026-11-08 首次实测，订阅到 2026-12-07；是否还在有效期，以 dash.3ue.co 首页“我的订阅”为准。

**订阅有效时：** 查竞品出词和外链，优先用这两个工具，不扣哥飞积分。
**以下情况回到哥飞流程：** 订阅到期、页面打不开、出现限额提示，或用户没在浏览器里登录 3ue。

## 风险与操作规则

3ue 平台公告禁止用脚本或自动化工具访问 Semrush 和 Similarweb，违规可能被封号。站长 2026-11-08 决定接受这个风险，让 Claude 用浏览器操作。操作时尽量像一个人在用，遵守以下规则：

- **只在网页上读。**
  - 打开报告页，等页面渲染完再读表格。
  - 不调用平台接口，不写脚本连续翻页抓取，不同时开多个标签页查询。
  - 不点“导出”：导出会下载文件，需要另外征得用户同意。
- **每轮上限：** Semrush 报告页最多打开 15 次，Similarweb 最多 10 次。要多查，先问用户。
- **一页读完再开下一页。** 每页至少等 5–8 秒，让它加载完。
- **遇到以下情况立即停：** 验证码、限流、额度提示、被登出、节点不可用。把已读到的结果整理好交给用户。不自己换节点重试，换不换由用户决定。
- **不动共享账号的东西：** 不建项目（Position Tracking、Backlink Audit、Site Audit 都会占共享账号的额度），不改账号设置和语言。

## 入口（2026-11-08 实测可用）

**第一次进入：** 每次会话先打开 dash.3ue.co，在首页点对应工具的“打开”。之后可以直接访问下面的网址，平台会自动带上会话参数。

| 用途 | 网址 | 读到什么 |
|---|---|---|
| 站找词（自然排名） | `https://sem.3ue.co/analytics/organic/positions/?db=us&q=<域名>&searchType=domain` | 排名词总数、各国词数、数据日期；每页 100 行：关键词、意图、排名、流量、流量%、搜索量、KD%、URL |
| 拓词 | `https://sem.3ue.co/analytics/keywordmagic/?q=<词>&db=us` | 全部匹配词数、主题分组；每页 100 行：关键词、意图、搜索量、KD、CPC、竞争度 |
| 外链概览 | `https://sem.3ue.co/analytics/backlinks/overview/?q=<域名>&searchType=domain` | Authority Score、引荐域名数、外链数及趋势 |
| 外链明细 | `https://sem.3ue.co/analytics/backlinks/backlinks/?q=<域名>&searchType=domain` | 每页 100 行：页面 AS、来源页标题和 URL、锚文本、目标 URL、首次和最近发现日期 |
| 外链差距 | `https://sem.3ue.co/analytics/gap/backlinks/report/?q=<自己域名>&searchType=domain&compareWith=<站1>%3Adomain%7C<站2>%3Adomain` | “对照站有、自己没有”的引荐域名：分类、AS、月访问量、匹配数、各站外链数；每页 100 行。多个站用 `|` 分隔，用逗号只会读到第一个；表格是 `tr`/`td` |
| 网站表现 | `https://sim.3ue.co/#/digitalsuite/websiteanalysis/overview/website-performance/*/999/3m?webSource=Total&key=<域名>` | 近 3 个月访问量和环比、月访问量、独立访客、渠道变化、国家分布、设备、排名、访问时长、相似站 |

- `db` 是 Semrush 的国家数据库，默认用 `us`，换市场时改 `db` 并记录下来。
- `/analytics/backlinks/refdomains/` 会跳回概览页；看引荐域名时，在概览页里切换标签。
- 外链差距的空白表单（`/analytics/gap/backlinks/`）在页面上填域名容易出错：带 `q` 参数时会预先填入，手动再输入的字会拼进同一个框里。直接打开上表里的报告网址更稳。
- 菜单里还有关键词差距、Similarweb 的“流量来源渠道”和“外链”，这些还没实测。第一次用时，把实际网址和读法补进上表。

## 怎么读表

报告表格的每一行是 `[role="row"]`，单元格是 `[role="cell"]` 或 `[role="gridcell"]`，第一行是表头。外链差距是例外，要读 `tr` 和 `td`。读完先核对行数和页面显示的条数一致。

```js
[...document.querySelectorAll('[role="row"]')].map(r =>
  [...r.querySelectorAll('[role="cell"],[role="gridcell"],[role="columnheader"]')]
    .map(c => c.innerText.replace(/\s+/g, " ").trim()))
```

- 搜索量会显示成 `1K`、`4.4K`、`12.1K`，按千换算，记下来时注明是 Semrush 的取整值。
- Keyword Magic 每行的第一个单元格是勾选框，里面带着关键词文本，表头比数据列多一列；按表头名称对齐，不要按位置对齐。
- 外链明细里会混入搜索结果页（如 `search.yahoo.com/...`）、垃圾域名，以及对方自己的其他站点。挑选位置前先筛掉这些。

## 口径

- **Semrush 的“流量”**：只是所选国家数据库里的 Google 自然搜索估算，不包括其他国家、直接访问和 AI 助手带来的流量。
  - 例：同一天，sounddino.com 的 Semrush 美国自然流量是 437，Similarweb 显示全球月访问量约 14.8 万。两者口径不同，不能放进同一张表比较。
- **Semrush 的 KD%** 和哥飞版 KD 不是同一个口径：
  - Semrush KD% 只用来排序和预筛，不套 serp-weakness.md 的阈值；
  - 进短名单前，照常用哥飞 `keyword_difficulty` 精评。
- **搜索量**：Semrush 的数值没有明确的统计周期，只记成 `volume_unperiodized`。
- **Authority Score** 和哥飞 DR 不是同一个分数。sites.md 的 DR 列照旧填哥飞 DR；如果用到 AS，另外注明“Semrush AS”。
- **Similarweb 对小站不准**：月访问几万以下的站，只看方向（在涨还是在跌、主要渠道是什么），不引用绝对数。数据面板显示的是估算值，引用时注明“Similarweb 估算”和时间窗。
- **品牌词**：对方的站名、域名这类词，不算“起量词”，也不当成种子。

## 在流程里的位置

| 步骤 | 订阅有效时 | 不可用时 |
|---|---|---|
| 筛站：判断是不是最近起量 | 看 Similarweb 网站表现的访问趋势，或 Semrush 自然排名页的趋势（1 个月 / 6 个月 / 1 年） | 用批次里的首次出现时间和域龄 |
| 站找词 | 用 Semrush 自然排名，每个站读第 1 页（按流量排序的 100 行）；需要更深时最多读到第 3 页 | 用哥飞 `site_keywords`，每轮最多 2 次 |
| 拓词 | 用 Semrush Keyword Magic，读第 1 页 | 用哥飞 `keyword_ideas` |
| 精评 | 照常用哥飞版 KD | 同左 |
| 新词抢先 | 不用 Semrush（新词的搜索量要几个月后才有） | 同左 |

**原始结果的存法：**
- 格式同 [词站互找](word-site-loop.md) 的“原始结果”；
- `source_ref` 写 `semrush_positions:<域名>:<db>:<数据日期>` 或 `semrush_kmt:<词>:<db>:<数据日期>`；
- 文件名带工具名，如 `<域名>-YYYY-MM-DD-semrush.json`；
- 30 天内查过的站不重查。
