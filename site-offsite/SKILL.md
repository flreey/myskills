---
name: site-offsite
description: 外链（站外建设）入口：所有项目的外链都走 bl 外链池（~/Projects/backlink）——新项目接入（登记、同类站、Common Crawl / DataForSEO 观测、共引线索）、复审线索、领单投稿、回报、核验、看进度，都按 `bl guide` 和 `bl project onboard` 做，不在项目里另建台账。Also for 找外链、做外链、新站外链、提交目录、发布平台上新、资源页推荐、复查外链状态、外链进度、海量挖掘外链、Common Crawl 链接图、同类站外链、接入外链池。让 AI 助手引用我们的榜单和来源（GEO 站外）用 site-geo 的 offsite-sources；默认不做付费买链和博客评论；不做反向链接审计（有害链接、disavow）；站内验收用 site-check。
---

# 外链入口（site-offsite → bl）

外链只有一套流程：**bl 外链池**（`~/Projects/backlink`，命令 `bl`）。这个技能只负责把你带进去，具体怎么做全在 `bl guide` 里。
（2026-11-25 站长定：不留两套。原来的台账、候选总表、新站批量模式、Common Crawl 脚本和方法文档都并进了 bl。）

## 先做这三步

1. **确定项目**：项目目录里有 `.backlink.json` 就自动识别；否则命令前加 `-p <项目 slug>`。`bl project list` 看已登记的项目。
   没登记的新项目，按 `bl guide` 的「新项目接入外链」登记，**不在项目里建 `seo/backlinks/` 台账**。
2. **读协议**：`bl guide`。投稿、复审、回报、核验、授权、身份、每日上限都以它为准。
3. **看做到哪一步**：`bl -p <项目> project onboard`，按返回的 `next_step` 做；`bl -p <项目> board` 看进度。

## 按用户的话分流

| 用户说 | 做什么 |
|---|---|
| 新站 / 新项目要外链、尽快多找外链 | `project onboard` 逐步走：登记 → 同类站（站长定）→ 观测 → `review seed` → 复审 → 领单 |
| 要大量外链、几千几万个 | Common Crawl 链接图：`~/Projects/backlink/docs/offsite/ccgraph.md`（首次下载约 11 GB，先问站长） |
| 投稿 / 继续投 | `bl run start` → `bl match --claim` → 投 → `bl report` → `bl run finish`（见 guide） |
| 复审、补入口 | `bl review next` → `bl review accept/reject`；新入口 `bl add` |
| 外链状态、复查 | `bl board`、`bl verify --due`（live 只由核验器写） |
| 让 AI 推荐 / 引用我们（GEO 站外） | site-geo 的 `references/offsite-sources.md`；要投稿的来源照样进 bl |

## 不变的底线

- 只投授权范围内的；注册、付费、发信、回链、人机验证、发帖交给站长，不绕过。不做 T4（博客评论、论坛签名）和付费买链。
- 只算核验器确认过的链接。账号、密码、编辑链接不写进任何字段、文件或截图。
- 方法参考（选同类站、渠道分层、素材包）：`~/Projects/backlink/docs/offsite/`。
- 改这个技能时，用 [行为检查](references/behavior-checks.md) 做回归。
