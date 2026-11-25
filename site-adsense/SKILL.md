---
name: site-adsense
description: 一键评估网站能不能过 Google AdSense 审核、上广告前还差什么：用自己的只读审计（事实核对脚本 + 源码和页面原文），用户贴来外部报告时逐条查证，只留下真问题。用于 AdSense 检查、过审预检、广告合规、能不能申请 AdSense、上广告前检查、核对别人给的 AdSense 审计报告或拒审原因，即使用户只说“看看这个站能不能挂广告”也要用。不用于广告收益估算、普通 SEO 验收（site-check）或 AI 搜索可见度（site-geo）。
---

# AdSense 一键评估

输出一份查证过的结论：这个站现在能不能申请、哪些是真问题、哪些是误报、上广告前还差什么。

审计只用自己的检查，不调用哥飞 `adsense_audit` 或其他付费预检工具。用户贴来的外部报告是线索，不是判定。Google 没有公开的预审接口，所以“必被拒”只是工具的推断；工具常把“没抓到”当成“没有”。每条结论都要有自己查到的证据，这个 skill 的价值就在这一步。

默认只评估，不改文件、不部署。用户明确要求修复时再动手，部署仍需单独授权。

## 流程

**1. 确定站点。** 用户没给域名时，从当前项目的配置推断；推断不出再问。

**2. 跑事实核对**（免费、只读，需要 Python 3）：

```bash
python3 <skill-dir>/scripts/adsense_facts.py example.com
```

返回 JSON：广告代码状态、`ads.txt`、完整 sitemap、信任页、隐私政策关键词、CMP、sitemap 内外的抽样页字数（`main_words` 是 `<main>` 内的正文）、带参数 URL 的 noindex/canonical/robots、下载链接、首页按钮。另有一组“站点形态”事实：

- `crawlers`：用 Mediapartners-Google 和 Googlebot 访问首页的状态，以及有没有被 Cloudflare 拦截。`redirects`：http、www 各变体最后跳到哪里。
- `domain`：RDAP 查到的注册日期和天数。
- `footer`、`footer_share`：页脚的链接数、词数、外部域名，以及页脚在每个抽样页里占多少字。
- `template.shares`：每个抽样页的 `<main>` 正文中，有多少字落在“半数以上抽样页都有的句子”里，用来区分真模板和只是句式相同。
- `sitemap_sections`：sitemap 按第一段路径分组（看下载/列表页和文章页的比例），以及语言前缀（`/es/`）各有多少页。
- `sensitive_terms.shared`：首页开头和页脚里的武器、暴力、成人、赌博类词。
- `policy_history`：信任页里“plan to”、“retired”、“what changed”、“before 某日期”、“without consent”这类措辞。

`flags` 只是需要看的线索。

脚本只看原始 HTML，不执行 JavaScript：页面靠 JavaScript 渲染时字数会偏低，`file_links` 为空也不代表没有下载按钮，`ads.state` 为 `none` 也可能是广告由第三方脚本加载。这些情况要用浏览器或源码确认后再下结论。

**3. 外部报告（可选）。** 用户贴了外部审计报告或 AdSense 后台的拒审原因，就把它的每条说法当作待查线索，进入第 4 步；没贴就不找，直接用第 2 步的事实和第 5 步的自查出结论。

**4. 逐条查证。** 对脚本的每条 `flags`，以及外部报告（有的话）里的每个 Fail、Blocker、High、Medium 和具体说法，判成一种，并写明证据：

- **属实**：自己查到了，且确实影响审核或合规。
- **部分属实**：现象存在，但工具夸大了或开错了方子。
- **误报**：证据相反。
- **现在不适用**：只有上广告后才成立。
- **无法查证**：说明谁、怎么才能查。

优先用脚本结果；不够时读页面原文。如果当前目录就是该站源码，也查代码和配置：广告开关、广告位组件、过期文案、最近改动。

常见误报：

| 工具的说法 | 怎么核对 |
|---|---|
| sitemap 只有很少 URL | 它可能只读了索引里的第一个子 sitemap，看 `sitemap.total_urls` |
| 已埋广告代码 | 可能只是 `google-adsense-account` 验证标记，看 `ads.state` |
| 没有来源、授权或关于页 | 页面可能叫别的名字（如 `/license`），看 `trust_pages` 并读原文 |
| 隐私政策没提广告 Cookie | 看 `privacy.mentions` 并读原文 |
| 筛选页会形成薄内容 | 看 `query_pages` 是否已 noindex |
| 缺 CMP 所以不合规 | 没有广告脚本时只是“现在不适用”，上广告前必须解决 |
| 广告遮挡、标签、位置无法判断 | 没有广告时都归“现在不适用” |

| 页脚/模板文字占页面 35%–65% | 先看 `footer_share`：多半是页脚链接撑出来的，不是正文模板；再看 `template.shares`，正文里整句重复通常不到一成 |
| 素材下载/工具站，原创文章太少 | 看 `sitemap_sections`。这是站点形态，属实，但 noindex 不会把页面藏起来：审核员照样能打开它们。只能补少量真实有用的文章，并让首页能直接点到 |
| 单项薄页应 noindex | 看页面是不是只有一个条目、正文很少。只处理确实单薄的那几类；先确认它们有没有 AI 搜索或 Bing 流量，必要时只对 Googlebot noindex |
| 全站出现敏感词（枪、刀、尖叫） | 看 `sensitive_terms.shared`。AdSense 禁止的是售卖武器和令人震惊的内容，不是游戏音效这类题材词，所以证据偏弱，算“有风险”；成本低的只改首页和页脚 |
| 域名太新（不足 3 个月） | 看 `domain.days`。公开政策只对部分地区写了时长要求，归“无法查证/有风险”，处理办法只有等，不要为此改站 |
| 多语言残缺像没做完 | 看 `sitemap_sections.locales`。页数很少的语言版本可以先对 Google noindex 并移出 sitemap，不必删页 |
| 政策页是改版流水账、写着 plan to | 看 `policy_history`。“plan to show ads”、“无同意弹窗”应改成现行表述；老客户的既得条款不能删，合并到一节“Earlier purchases”里 |
| 缺 `adsbygoogle.js` | `ads.state` 为 `verification-only` 时属实：重提前在 `<head>` 加 loader；先确认 CSP 允许 `pagead2.googlesyndication.com` |

工具提到的具体 URL 类型（如 `?duration=`）如果 `query_pages` 没抽到，就自己拼一个去查。

**5. 核对承诺与实际。** 工具只读文字，看不出页面说的和实际发生的是否一致，而这正是误导性内容的核心。把首页、下载按钮、定价和条款里的 free、no signup、unlimited、数量等承诺，与实际行为对比：额度、登录墙、付费墙、按钮去向。能读源码就读源码，否则用浏览器实测，但不要点购买。查到的问题写进“工具没报、自查发现”，并分清“明确违规”和“有风险”：有风险的按改动成本建议，不要说成必被拒。

**6. 判断建议值不值得做。** 工具的整改建议常常不针对审核本身，下面这些默认不采纳，并说明原因：

- 按字数扩写、批量生成详情页：只有页面确实空洞才补，补的内容要是真实有用的信息。字数不是政策要求，为过审注水反而像低价值内容。
- 没有依据的数字或“最佳实践”：写进页面前要能验证。
- 与用户已定方向冲突的建议：指出冲突，让用户决定。
- 伪造或夸大的信任信号：评价、数据、审核流程都要真实存在。
- 删除许可要求的署名：如 “Powered by Stability AI” 这类模型许可要求展示的文字，先查许可原文，不能为“看起来专业”就删。
- 大面积 noindex 或重写核心页来换审核：先看这些页带来的真实流量（含 ChatGPT、Bing），再决定。审核看的是站点整体，noindex 不会让审核员看不到页面。
- 为过审删掉站内导航的全部内链：只删成批的条目链接和不相关外链，栏目链接保留。目录站要求的回链放首页即可。

## 后台拒审原因对照

拿到 AdSense 后台给的原因后，先按这张表查对应事实，再定动作：

| 后台原因 | 先查 | 常见动作 |
|---|---|---|
| 低价值内容 | `sitemap_sections`、`template.shares`、`footer_share`、抽样页 `main_words` | 精简页脚、处理真正的单项薄页、首页加文章入口、补少量真实文章 |
| 找不到代码 / 无法访问网站 | `ads.state`、`crawlers`、`redirects`、`robots.blocks_google` | 加 `adsbygoogle.js`、放行 Mediapartners-Google、修跳转 |
| 网站导航问题 / 正在施工 | `sitemap_sections.locales`、`policy_history`、`footer` | 收起残缺语言版本、政策页改现行表述、页脚只留栏目 |
| 违反发布商政策 | `sensitive_terms`、隐私页 `privacy.mentions`、`cmp` | 首页和页脚避开敏感词、隐私页写清广告与同意、在 AdSense 后台 Privacy & messaging 开 GDPR 消息 |

重提前：改动上线后等 1–2 周，让 Google 重新抓取再提交，不要短时间内反复提交。

## 输出

用用户的语言，先给结论，不复述工具的完整清单：

```markdown
**结论：可以申请 / 修完 N 项再申请 / 暂不建议**，一句话说明最关键的原因。

## 外部报告核对（用户贴了报告时才有）
| 报告项 | 核对结果（属实/部分属实/误报/现在不适用/无法查证） | 证据 | 处理 |

## 工具没报、自查发现
| 问题 | 证据 | 明确违规还是有风险 |

## 申请前要修
按影响排序，写清页面或文件、具体怎么改，能给成品文案就给。

## 上广告前要做
（没有广告代码时才列）CMP、隐私政策、广告位、功能页、个人信息、多地区实测。

## 不建议做的
工具建议了但不采纳的，一句话说明原因。

## 需要你确认的
只列脚本和代码都查不到的项，合并同类，写明去哪里看。

## 复检清单
可逐项勾选；分“这次改完”和“上广告前”。
```

报告里写明本次依据：脚本运行时间、有没有外部报告及来源、哪些项没查。

## 政策依据

判断政策问题时读官方原文，页面可能更新，不要凭记忆引用：

- 资格要求：https://support.google.com/adsense/answer/9724
- AdSense 计划政策：https://support.google.com/adsense/answer/48182
- 发布商政策：https://support.google.com/publisherpolicies/answer/10502938
- EEA、英国、瑞士的 CMP 要求：https://support.google.com/adsense/answer/13554116
- 欧盟用户同意政策：https://www.google.com/about/company/user-consent-policy/
- Google 搜索垃圾内容政策（批量内容）：https://developers.google.com/search/docs/essentials/spam-policies
