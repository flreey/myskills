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

### 外链差距批量挖掘（Semrush 订阅有效时首选）

一次比较自己和 2–4 个对照站，直接列出“对照站有、我们没有”的引荐域名。新站批量模式就从这里起步。Semrush 的入口、页数上限和遇到即停的规则见 keyword-radar 的 `references/semrush-similarweb.md`。

1. **打开报告**：`https://sem.3ue.co/analytics/gap/backlinks/report/?q=<自己域名>&searchType=domain&compareWith=<对照站1>%3Adomain%7C<对照站2>%3Adomain`
   - 多个对照站之间用 `|`（编码后是 `%7C`）分隔；用逗号分隔，只会读到第一个对照站。
   - 新站自己还没有外链时也能跑，结果就是对照站的全部引荐域名。
2. **读表**：这页的表格用 `tr` / `td`，不是 `[role="row"]`。每行依次是：引荐域名（带分类）、AS、月访问量、匹配数、自己的外链数、各对照站的外链数。
   - 匹配数 `x/N` 的分母 N 包含自己：3 个对照站时显示 `x/4`，`3/4` 就是三个对照站都有。
   - 每页 100 行。默认按匹配数、再按 AS 排序，三个对照站时第 1 页往往全是 `3/4`，后半页 AS 已经降到个位数。
   - **读法**：先读默认排序的第 1 页；再打开网址末尾加上 `&sort_field=domain_ascore` 的版本，按 AS 读 1–2 页。翻页用 `&page=2`。合计不超过 3 页。
   - 点表头排序时，网址会变，但行不刷新。排序要靠重新打开网址，每打开一次算一页。
3. **先按规则直接排除**，这一步不用打开页面：
   - 搜索引擎和门户：yahoo、bing、yandex、google、baidu 等。它们出现在列表里，通常是因为搜索结果页被收录了；
   - 分类为“大众媒体”“成人”的域名；
   - 社交网络的根域名：这类位置只在 T3 里按社区规则做；
   - 网站估值和统计页（如 getwebsiteworth、bestwebstats、websiterace）、短链服务、域名交易站（如 domraider 一类）、外链农场和 guest post 站、搜索结果抓取站、AI 问答自动生成页；
   - 明显的垃圾域名，比如大量 `.shop`、`.site`、`.xyz`、`.online` 的随机名字；
   - 对照站自己的其他站点：同一个运营方的姊妹站常常带上万条外链；
   - **兜底**：AS ≤ 10、分类为空、名字和产品领域无关的，直接排除。
   - 2026-11-08 在 sfxmint 上实测：第 1 页 100 个域名，排除后只剩 2 个。剩下很少是正常的。
4. **展开看位置类型**：排除后排在前面的，以及匹配数最高的 3–5 个，先看清链接放在什么位置，再决定进不进投稿队列。
   - **行内展开**：外链数单元格（`aria-label="显示 <对照站> 的 N 个反向链接"`）点开后，在行下方列出最多 5 条明细：来源页、锚文本、目标 URL、`rel`、链接位置、首次和最近发现日期。展开不换页，但每轮最多展开 20 次。
   - **完整列表**：`https://sem.3ue.co/analytics/backlinks/backlinks/?q=<对照站>&searchType=domain&filter=%2B%7Crefdomain%7CEq%7C<引荐域名>`，算一页。
   - 不用再去 Google 搜 `site:`。
5. **区分署名类和编辑类**：
   - **署名类**：用户用了对照站的东西之后，在自己的作品里注明来源。比如游戏页或 devlog 的 credits、mod 页、播客节目说明、论文和代码仓库、教学课件、个人站的书签页。
     - 这类不能投稿，不进投稿队列，在台账里记为“使用后自然产生的链接”。
     - 应对办法在产品侧：在 itch.io、GitHub 发布自己的素材页，或在下载页引导用户署名。这些写进轮次总结，交给用户决定。
     - 音效、图片、字体这类内容库，几个对照站共有的高匹配来源大多是署名类（2026-11-08 sfxmint 实测：对照站约 290 条外链明细里，能争取的编辑型位置约 15 个）。
   - **编辑类**：目录、发布平台、alternatives 页、资源页、清单文、awesome 列表、FMHY 这类社区维护的索引。只有这类进入下面的分层和快筛。
6. **编辑类按类型归到渠道层**：
   - 目录、发布平台、alternatives 归 T1；
   - 资源页、清单、awesome 列表、社区维护的索引归 T2；
   - 创作者平台的作品页，比如 itch.io 的素材页、GitHub 仓库、ArtStation、neocities：本身是在发布作品，可以作为 T1 的“发布平台”。只做有真实内容的作品页，不做空资料页。
7. **补读对照站的外链明细**（可选，编辑类太少时用）：
   - 网址：`https://sem.3ue.co/analytics/backlinks/backlinks/?q=<对照站>&searchType=domain`，每个对照站读第 1 页。
   - **默认排除 yahoo.com、bing.com**：只排一个时，加 `&filter=-%7Crefdomain%7CEq%7Cyahoo.com`；排多个时，用 `ba_adv=[["-","refdomain","Eq","yahoo.com"],["-","refdomain","Eq","bing.com"]]`，URL 编码后加在网址后面。
   - 不加排除时，sounddino 的第 1 页 100 条里有 98 条是 Yahoo 搜索页。
8. **写进台账**：编辑类候选写进候选总表，状态是 `candidate`，另记下 AS、匹配数和来源 `semrush_gap:<日期>`，然后按 SKILL.md 第 3 步快筛。署名类只在轮次文件里记数量和例子。

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
| awesome 列表 | GitHub 搜 `awesome <主题>`。先读 CONTRIBUTING 里的收录标准（项目满几个月、要多少星或第三方报道），再看最近合并的 PR；不满足的记进观察表，写明哪天可以再看 |
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
