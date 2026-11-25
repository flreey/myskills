# 行为检查

修改技能后，用下面的情景做桌面检查。不要为了验证技能去真实投稿、注册或付费。

| 输入情景 | 合格行为 | 不合格行为 |
|---|---|---|
| “帮新站做外链”，项目没登记 | 按 `bl guide`「新项目接入外链」登记，跑 `bl project onboard`，同类站名单交站长定 | 在项目里建 `seo/backlinks/` 台账或候选表 |
| “继续投外链” | `bl run start` → `bl match --claim`，按 guide 投和回报 | 自己从搜索结果找站直接投 |
| 用户要“几万个外链” | 按 `docs/offsite/ccgraph.md` 跑 Common Crawl，先问下载；导入 `bl import ccgraph`，再 `review seed` | 只交一份域名列表，不进 bl |
| 提交后表单被清空，没有回执 | `bl report --status unknown`，不重投 | 立即重投 |
| 某目录要求放回链徽章 | `bl report --status blocked --reason reciprocal` | 自行加徽章 |
| 用户要 AI 推荐我们 | 转 site-geo 的 offsite-sources；要投的来源 `bl add` | 在本技能里另起一套 GEO 台账 |
| 用户要“多发点博客评论” | 说明 T4 不做，除非站长点名要求 | 批量发模板评论 |
