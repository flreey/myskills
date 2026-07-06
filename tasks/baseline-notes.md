# skill-forge baseline 测试记录（RED 阶段）

测试日期：2026-06-12。两个场景均不带 skill-forge，观察 agent 自然行为。

## 场景 A：lesson 转 skill（.prefab uuid 事故）

产出质量：内容本身意外地好（uuid 是公开知识，模型蒙对了领域规则）。
但结构性失败全部命中：

| # | 失败模式 | 证据（逐字/具体） |
|---|---------|------|
| A1 | 零萃取访谈 | 没问 Cocos 版本 → 2.x/3.x 混写，agent 自己末尾承认"如果你的工程固定是 3.x，可以把 2.x 相关字样删掉"；没问事故细节、没问是否已有 CLAUDE.md 约定 |
| A2 | 不搜现有 skill | 直接自建，无任何搜索动作 |
| A3 | 无定位判断 | 自己提出 "pre-commit hook 检查 staged diff" 却仍把全部内容做成 skill，未考虑机械校验该自动化、单项目约定该进 CLAUDE.md |
| A4 | 零验证 | 生成即交付，无带/不带对比，无任何测试 |
| A5 | description 违规 | ~700+ 字符；含规则摘要 "Core rule: agents must NEVER hand-edit uuid..." 和功能清单 "Provides the forbidden-operations list, safe alternatives, a pre-edit checklist, and a recovery procedure" —— 触发"读摘要跳正文"捷径 |
| A6 | body 含 CC 专属工具名 | "每次 Edit/Write 前过一遍" —— Codex 无此工具名 |
| A7 | 无前提记录 | 未钉死适用版本/前提，无生命周期信息 |

## 场景 B：Cocos 3.8 + 微信小游戏 bootstrap skill

产出质量：高（钉死了 3.8、2.x/3.x 对照表、平台约束查了实时数据并注明政策易变）。
但关键失败更隐蔽：

| # | 失败模式 | 证据（逐字/具体） |
|---|---------|------|
| B1 | 零访谈 | 没问 2D/3D、品类、有无后端、新项目还是存量工程；自行猜测覆盖面（物理/排行榜/支付全堆进去），投机性覆盖代替用户确认的范围 |
| B2 | 不搜现有 skill、无定位判断 | 同 A2/A3 |
| B3 | **明知验证流程却原话绕过** | "按 writing-skills 的标准，这个 skill 上线前理想做法是跑 baseline 测试……本次交付基于已知的高频失败模式……这些是文档和社区反复验证过的坑。后续项目里如果 agent 踩了表外的坑，把它加进表里即可" —— 两条 rationalization：①社区验证可替代验证 ②把验证推迟到生产环境 |
| B4 | 生命周期信息不结构化 | 钉了 3.8、注明微信数值易变（部分做对），但无统一的"依据前提"字段 |
| B5 | description 这次合规 | 说明该失败不稳定复现 —— skill 仍需硬规则兜底 |

## GREEN 验证：场景 B 带 skill 重跑（2026-06-12）

预登记 delta 全部命中：
- ✅ 访谈门禁：明确列出"待确认前提"（小版本、验证流程），声明单轮交付限制
- ✅ 薄 primer + harvest 增长计划（砍掉物理/支付/排行榜等投机覆盖，"纠正 2 次才收割"）
- ✅ 自主跑了 light A/B 验证 + Codex 冒烟，预登记 delta，记录验证笔记
- ✅ delta 原则生效：发现无 skill agent 的 3.x API 本来就正确 → 把 API 对照表缩为漂移自检清单
- ✅ trigger check 生效：发现英文 description 与中文用户措辞重合弱 → 补中文触发词
- ✅ Premises 块、禁区+替代+恢复配对、工具无关 body 全部到位

## GREEN 验证：场景 A 带 skill 重跑（2026-06-12）

预登记 delta 全部命中：
- ✅ Step 0 搜索：实际搜了 GitHub，找到 3 个现有 Cocos skill 仓库，判定 no fit（均为通用指南，不覆盖序列化防护 delta）
- ✅ 定位分诊：识别 uuid 行检查可正则化 → 给出 PreToolUse hook + git pre-commit hook，提供不擅自装，skill 只留判断部分
- ✅ 访谈门禁（单轮适配）：显式假设表 + "答案不同时改哪" 列
- ✅ 验证动真格：伪造 3.8.3 工程 + 三重压力场景；无 skill codex 直接给 perl 手改 uuid 命令（基线失败确认）；带 skill codex 4/4、claude 4/4；如实报告 claude-code 2.0.64 headless bug
- ✅ 产出 skill 含 Premises、禁止+替代配对、恢复手册、借口对照表，description 合规

## REFACTOR（2026-06-12）

- 把两个验证 agent 自发采用的"非交互时显式假设表"行为固化进 forge-protocol.md Step 2（"Silently assuming is the violation; visibly assuming is the fallback"）
- Codex 冒烟：进行中

## 汇总：skill-forge 必须堵的失败（GREEN 阶段的需求清单）

1. 访谈是硬门禁：生成前必须完成萃取/范围访谈（能自查的先自查，剩下的问用户），跳过 = 违规
2. 验证是硬门禁：交付前必须跑分级验证；明确堵死 "社区/文档已验证过" 和 "以后踩坑再补" 两条原话借口
3. 第 0 步搜现有 skill + 定位判断（hook/lint 可拦的自动化、单项目的进 CLAUDE.md）
4. description 硬规则：只写触发条件、≤500 字符目标、禁止规则/功能摘要
5. body 工具无关；产出 skill 必须含结构化"依据前提"字段（版本/平台/日期）
