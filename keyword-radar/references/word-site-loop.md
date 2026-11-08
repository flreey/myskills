# 词站互找（新站反推的做法）

从种子词找到在排的同类小站，再从这些站找到它们靠哪些词起量，新词过关后再去找站。目的是多拿“新站能排”的证据，同时攒下一张同类站名单，给 site-research 和 backlink-outreach 复用。

```
种子词 ──SERP / 批次──▶ 同类站 ──筛站──▶ 新站 ──站找词──▶ 新词 ──G1──▶ 下一层种子（深度 +1）
                         └──────────────── 全部记进 sites.md ────────────────┘
```

## 一层怎么做

1. **词找站**：
   - 对本层种子实看 SERP 前 10（浏览器免费；验证码或要可复查时用 `serp`）。核心词的首页常常全是老站，再看第 2 页，或换 1–2 个长尾变体。
   - 哥飞新站批次、网站发现批次里与种子同类的项目（不扣积分）。批次文件很大，落盘后只按 site、title、top_keywords 过滤，别对整条记录做正则。
   - 只记**同类站**：做同一件事、面对同一类读者。
     - 不记：多品类综合平台（素材、图库、模板什么都卖的）、应用商店、视频站、论坛和社区、媒体、官方站。
     - 只做本类内容的垂直老站照记，类型写“对照站”，规模再大也算。
2. **筛站**：
   - `domain_dr` 一次批量打 DR；域龄用 whois 或 Wayback 首次快照。
   - **平台子域名站**（`*.pages.dev`、`*.github.io`、`*.vercel.app`、`*.netlify.app` 这类）：DR 和 whois 只能查到根域，不能用。
     - DR 写“不适用（共享根域）”，不去查。
     - 域龄取批次里的首次出现时间（如 `first_period`），没有就用这个子域名自己的 Wayback 首次快照。
   - Semrush/Similarweb 订阅有效时，看 Similarweb 网站表现的访问趋势，或 Semrush 自然排名的趋势，确认是不是最近起量（[用法](semrush-similarweb.md)）。小站的 Similarweb 数值只看方向。
   - 域龄不到 12 个月、而且已有自然流量的，标为“新站”，进入下一步。
   - 其余同类站照样记进 sites.md，用途写“对照站”，不查词。
3. **站找词**：
   - Semrush 订阅有效时，优先用 Semrush 自然排名：每个新站读第 1 页，品牌词不算起量词。受每轮 15 页上限约束，不受“2 次”限制。
   - 不可用时用 `site_keywords`：每轮最多 2 次，优先查 DR 最低、流量最近起来的新站。
   - 免费替代：用户已登录 Keyword Planner 时，用 “Start with a website” 输入新站域名。
   - 竞品 sitemap 和导航里的词只能当种子，见到观察后才算数。
   - 每次 `site_keywords` 的原始结果另存一份，见下面“原始结果”。
4. **回到筛选**：新词先过 G1 意图。过关的成为下一层种子，记下父站和深度。G2、G3 照常在主流程里做。

## 什么时候停

- 默认只做一层（种子 → 站 → 词）。用户要求“继续滚”或本层产出好时，再做第二层。深度上限 2，更深的写进观察表。
- 本层新找到的同类站不到 2 个，或新词过 G1 的不到 5 个，就停。这是默认线，按 `radar-log.md` 的回收结果再调。
- 付费调用计入本轮 30 积分，`site_keywords` 一轮最多 2 次的上限不变。Semrush 和 Similarweb 按各自每轮的页数上限算。要多查，先问用户。

## sites.md（同类站名单）

- **位置**：关联项目时 `<项目>/seo/radar/sites.md`，否则 `keyword-radar/sites.md`。跨轮追加，同一域名只占一行，复查时更新这一行并改日期。
- **归属**：只由本技能写。site-research 和 backlink-outreach 只读。

| 列 | 写什么 |
|---|---|
| 域名 | 不带协议 |
| 发现路径 | `种子词 → 站` 或 `父站 → 词 → 站`，附批次 id 或 SERP 查询 |
| 类型 | 新站 / 对照站 |
| DR | 数值和查询日期；平台子域名写“不适用（共享根域）” |
| 域龄 | 注册日期、批次首次出现时间或首次快照，写明是哪一种 |
| 自然流量 | 数值、来源、日期；没查到写 unknown |
| 起量词 | 前几个带流量的词；没查写“未查” |
| site_keywords | 查询日期、工具（哥飞或 Semrush 加国家库）和原始结果文件；没查留空 |
| 备注 | 例如“上一轮已查，30 天内不重查” |

- 30 天内查过出词的站不重查（不管用的是哥飞还是 Semrush），直接读原始结果。
- 没返回不等于没流量，写 unknown。

## 原始结果

每次 `site_keywords` 存成 site-research 可以直接导入的 JSON，免得重复付费：

- **位置**：`<项目>/seo/radar/site-keywords/<域名>-YYYY-MM-DD.json`
- **格式**：

```json
[{"keyword": "…", "kind": "external_reference",
  "metrics": {"position": 4, "volume_unperiodized": 320, "url": "https://…"},
  "market": {"country": "US", "language": "en"},
  "source_ref": "site_keywords:<域名>:YYYY-MM-DD"}]
```

- 搜索量是快照，没有统计周期，只放 `volume_unperiodized`，不写成 `historical_volume`。
- 在 seo.web.cafe/chat 网页对话里查的：把返回的表格逐行转成上面的格式，`source_ref` 写 `web_chat:<对话链接>:YYYY-MM-DD`。存完核对行数和表格一致。
- 用 Semrush 自然排名查的：
  - 文件名用 `<域名>-YYYY-MM-DD-semrush.json`；
  - `source_ref` 写 `semrush_positions:<域名>:<db>:<数据日期>`；
  - `metrics` 里另记 `traffic` 和 `semrush_kd`；
  - `market` 按 `db` 填；
  - 存完核对行数和页面显示的条数一致。
- 查到 0 行也存一个 `[]`，sites.md 的 site_keywords 列写“0 行”和日期。快照库更新慢，新站常常查不到；0 行不等于没流量，30 天内同样不重查。
- 本技能不把这些词写进 site-research 的词池；要扩进词池，由 site-research 导入。
