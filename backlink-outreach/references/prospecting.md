# 找入口

## 1 竞品外链缺口（产出最高）

**选对照站**：3–5 个与你产品类别和读者相同的站。优先近期起量的新站，因为它们拿到的外链，新站大多也能拿到。

- **找对照站**：
  - 先读 `seo/radar/sites.md`（keyword-radar 的同类站名单，已带 DR、域龄、流量和发现路径），从里面挑，不重新找、不重查已有数据；
  - 名单没有或不够 3 个时，再看目标词 SERP 里的同类小站、哥飞的新站批次和网站发现批次（不扣积分）；
  - 本技能只读 `sites.md`，不往里写。
- **查对照站**：哥飞 `domain_overview` 可以看 DR、流量、域龄，2 积分/次。只在 `sites.md` 里没有这个站、又需要从候选里挑对照站时用。

**看它们的外链**（哥飞工具箱没有外链列表工具）：

| 来源 | 做法 | 限制 |
|---|---|---|
| Semrush 外链（站长的 3ue.co 拼车账号，订阅有效时优先用） | 先打开外链概览 `https://sem.3ue.co/analytics/backlinks/overview/?q=<对照站>&searchType=domain`，看引荐域名数和趋势；再打开外链明细 `/analytics/backlinks/backlinks/?q=<对照站>&searchType=domain`，读第 1 页 100 行，按页面 AS 从高往低挑 | 平台禁止自动化，站长已接受风险。每轮 Semrush 最多打开 15 页，不点导出、不建项目，遇到验证码或额度提示就停。详见 keyword-radar 的 `references/semrush-similarweb.md`。明细里混有搜索结果页和垃圾域名，先筛掉 |
| Similarweb 网站表现（同一账号） | 目标里有“带引荐流量”时，看对照站的流量来源渠道和引荐站，找真正在送访问的站 | 每轮最多 10 页；小站的数值只看方向；“流量来源渠道”页的实际网址第一次用时补记 |
| Ahrefs 免费外链查询 | ahrefs.com/backlink-checker，输入对照站域名 | 只显示部分外链；有验证码时交给用户 |
| Bing Webmaster Tools | 外链功能里可以查看其他站点的外链 | 需要用户已登录的 BWT 账号 |
| 搜索提及 | `"对照站域名" -site:对照站域名` | 提及不一定带链接，要打开确认 |
| seo-backlinks 技能 | 已安装时，可以用它的 Moz、Bing、Common Crawl 数据源 | 按该技能自己的配置 |

**怎么挑**：

- 只留**可复制**的位置：目录条目、资源页、清单文章、awesome 列表、alternatives 页、社区发布帖。
- 排除：对照站自己的其他站点、媒体报道、合作伙伴页、付费位置。
- 两个以上对照站都有的来源，优先级最高。

## 2 已知类别

按 channels.md 的 T1 类别，结合你的产品类别去搜当前还在收录的目录：

- `<类别> tools directory submit`
- `submit your <类别> tool`
- `<类别> alternatives`

结果先过快筛的“活着”和“有链接”两项，不要直接整批投。

## 3 搜索指令（用来找 T2）

| 目的 | 指令示例 |
|---|---|
| 清单文章 | `intitle:"best <主题> tools"`、`"<主题> tools" intitle:<今年>` |
| 资源页 | `inurl:resources <主题>`、`intitle:"useful resources" <主题>` |
| alternatives | `"alternatives to <竞品>"`、`"<竞品> alternatives"` |
| awesome 列表 | GitHub 搜 `awesome <主题>`，看 CONTRIBUTING 和最近合并的 PR |
| 征集页 | `"<主题>" "submit a tool"`、`"<主题>" "suggest a resource"` |

清单文章的作者如果近半年更新过，加分；如果三年没动过，基本没人回复。

## 预算

- **免费路径优先。** 每个候选快筛 2–3 分钟；提交过程中出故障，最多花 5 分钟排查，超过就记为受阻，转下一个。
- **哥飞积分**：每轮默认不超过 10 积分。
  - `domain_overview` 用来挑对照站；
  - `domain_dr` 用来批量给候选打 DR，每 20 个域名 1.5 积分，缓存命中免费。
- **Semrush / Similarweb**：不扣积分，按页数计算，每轮 Semrush 最多 15 页、Similarweb 最多 10 页。轮次记录里写明各打开了几页。
- **超出预算或调用被拒时**：停下，用已有结果继续，不换接口重试。
- 时间预算到了，只说明这个候选要后续处理，不说明整轮完成。还有授权范围内能做的，就继续做。
