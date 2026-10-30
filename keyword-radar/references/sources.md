# 来源与预算

## 原则

- 先用免费路径。哥飞的新词、新站、网站发现批次属于数据服务，**不扣 SEO 积分**，算作免费入口。
- 付费工具只用于两件事：
  - 精评已经过了 G1/G2 的候选；
  - 免费入口产量明显不足时补充收集。
- 价格以工具当次描述为准，下表的数值只用于估预算。哥飞 MCP 的服务端规则优先：近 20 分钟花到 30 积分就停下来问。

## 入口一：新词抢先

| 路径 | 做法 | 成本 |
|---|---|---|
| 哥飞新词批次 | `keyword_batches` 取列表，再用 `keyword_batch(id)` 取整批 | 不扣积分 |
| Trends 网页 | trends.google.com 输入词根，看 7 天/30 天的 Rising 相关查询 | 免费 |
| 发布源 | Product Hunt、Hacker News、GitHub Trending、主流 AI/软件的官方 changelog 和博客 | 免费 |
| `trends_rising` | 一批词根的 Rising 合并结果，自带是否新词的判断 | 2 积分起；每实时抓取一个词根 4 积分 |
| `google_trends` | 单个词的曲线，自带“是否新词、处于什么时期、适不适合上站” | 2–4 积分；带 related 另加 4 积分 |

怎么判断是新词：12 个月曲线到最近 1–3 个月才起来，5 年图之前接近 0。

- Breakout 或涨幅只表示这个相关查询相对它自己涨了多少，不是搜索量。
- 发布源里出现的新名词，要在 autocomplete 或 Trends 里能查到才算观察。

## 入口二：新站反推

| 路径 | 做法 | 成本 |
|---|---|---|
| 哥飞新站批次 | `launch_batches`，再用 `launch_batch(id)` 取整批项目和已有分析 | 不扣积分 |
| 哥飞网站发现 | `hosted_batches`，再用 `hosted_batch(id)` | 不扣积分 |
| 手动 | SERP 里遇到陌生小站时，查域龄（whois 或 Wayback 首次快照） | 免费 |
| `site_keywords` | 看某个新站或某个页面靠哪些词排名 | 每 50 词 7.5 积分，最低 8；**每轮最多 2 次** |
| `domain_dr` | 批量给域名打 DR | 每 20 个域名 1.5 积分，缓存命中免费 |

- 只取域龄不到 12 个月、而且已经有自然流量的站。
- 它排上的词是 G3 的强证据，但你会是第二个进来的新站，仍然要按 serp-weakness.md 实看 SERP。

## 入口三：弱 SERP 长尾

| 路径 | 做法 | 成本 |
|---|---|---|
| autocomplete | 浏览器里输入，或请求 `https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=<词>`。用词根加修饰词：for、to、vs、online、free、without、how to、generator、checker、converter、calculator、template | 免费 |
| SERP 附带内容 | People Also Ask、相关搜索、Reddit/Quora 的问题标题 | 免费 |
| site-research 引擎 | 已关联项目且装了 site-research 时，可以复用它的 `suggest` 来批量补全 | 免费 |
| `keyword_ideas` | 用 `mode=suggestions` 取长尾，可带 `maxKd` 预筛 | 每 50 词 7.5 积分，最低 8 |

## SERP 和难度

| 路径 | 用途 | 成本 |
|---|---|---|
| 浏览器 SERP | `https://www.google.com/search?q=<词>&gl=us&hl=en&pws=0`，数弱页 | 免费，受登录状态和本机位置影响，要如实记录 |
| `serp` | 浏览器遇到验证码，或需要可复查的原始数据时用 | 2 积分，7 天缓存 |
| `bulk_keyword_difficulty` | 一次最多 200 词，只用来排序，不套阈值 | 5 积分/次 |
| `keyword_difficulty` | 哥飞版 KD，自带前 10 的 DR、流量、域龄，是 G3 的精评 | 2 积分/次 |
| `keyword_volume` | Planner 口径的月均量和 12 个月曲线，最多 50 词一批 | 2–5 积分/批；`gl=world` 另加 15 |

## 每轮默认预算（不超过 30 积分）

| 步骤 | 调用 | 约计 |
|---|---|---|
| 海选排序 | 1 次 `bulk_keyword_difficulty`，覆盖所有过了 G1/G2 的词 | 5 |
| 精评 | 前 5–8 个词各 1 次 `keyword_difficulty` | 10–16 |
| 核量 | 1 次 `keyword_volume`，覆盖进短名单的词 | 2–5 |
| 机动 | `serp`、`domain_dr` 或 1 次 `site_keywords` | 余下 |

- `keyword_ideas`、`site_keywords`、实时 `trends_rising` 都比较贵，一轮合计不超过 3 次，并计入这 30 积分。
- 调用被拒、余额不足或达到上限时，停止付费调用，用已有结果出短名单，并说明哪些项因此没有精评。

## 受阻处理

遇到验证码、需要登录或限额时：

- 记下受阻的来源，继续做其他能做的部分。
- 不用估出来的数据填空。
- 不代替用户登录，也不绕过验证码。
