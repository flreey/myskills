# overseas-micro-product-scout

挖海外微型产品机会的**硬过滤器**——不是脑暴机，是淘汰机。

## 这个 skill 解决什么

独立开发者找方向常见的三种翻车：

- **抽象 startup ideas**：听起来宏大，落不到一周能验证的输入/输出
- **本地行业 workflow**：税务、医保、法律、政府采购——看不见数据，做不出 demo
- **"免费版 X"**：只靠免费打 paid，第二天被对手免费一个功能就死

这个 skill 强制走一条路径：

> 竞品验证需求。机会是它们旁边那个被忽略的小动作。

固化的过滤器：

- 海外用户、非中国用户
- 数据源必须可见（URL / 当前网页 / 截图 / HTML / Markdown / CSV/XLSX / transcript / sitemap / 公开 export / 粘贴文本）
- 必须有付费或广泛使用的免费竞品验证需求
- wedge 必须是"更窄/更快/更便宜/更近数据源"，不是"同样的东西但免费"
- 7-10 天能做出 demo，4 周能做出可用 MVP，月成本 < $200
- 默认拒绝：通用 AI 写作 / SEO 审计 / CRM 克隆 / 依赖 LinkedIn/Twitter 抓取 / TOS 灰色地带 / 数据藏在客户私有系统里

## 触发时机

自然语言任意一种：

- "帮我找几个海外微型产品机会"
- "这个 idea 值不值得做"
- "X 这个 Chrome 插件能不能抄一个差异化版本"
- "tool site / 平台插件 / converter，哪个方向适合"
- "这个 paid tool 我能不能切一个 wedge 出来"

## 工作流

1. **复述边界** — 海外用户、可见数据源、竞品邻接、低本地知识、7-10 天验证
2. **竞品先扫** — 1-3 个付费 + 1-3 个免费/低价 + 1 个高端（如有），含 pricing / users / 最近 reviews
3. **挖抱怨与 workaround** — Reddit / HN / Product Hunt / Chrome Web Store / GitHub Issues 的真实语言
4. **写 wedge** — "Competitor does X. This product only does Y for Z user at W moment."
5. **验证数据源契合度** — 输入是什么？我们能不能自己造样本？V1 能不能不依赖 OAuth？
6. **按数据位置选产品形态** — 浏览器扩展 / tool site / 平台插件 / Sheets add-on / CLI / 轻 SaaS
7. **7 gate 评分** — competitor demand / wedge / visible data / low domain / distribution / pricing / 7-10 day demo
8. **DO / OBSERVE / KILL** — DO 必给 7-10 天验证 MVP + post 标题 + 渠道 + kill 信号

## 文件结构

```
overseas-micro-product-scout/
├── SKILL.md          # 主入口，加载它即可
├── README.md         # 本文件
└── AGENTS.md         # Codex CLI 专用补丁
```

## 安装

```bash
# Claude Code
cp -R overseas-micro-product-scout ~/.claude/skills/

# Codex CLI
cp -R overseas-micro-product-scout ~/.codex/skills/
```

或者用仓库根 README 的一键 prompt 让 agent 自己装。

## 不适合用这个 skill 的场景

- **想做中国市场产品** — 这个 skill 直接拒绝
- **想做面向本地行业的 SaaS**（税务/法律/医疗/政府/建筑估算）— 用户看不见数据，做不出 demo
- **想要"100 个 idea"** — 这个 skill 的目标是淘汰到 1-2 个 DO，不是堆量
- **已经决定做 X 想要架构建议** — 用 `system-evolution-skill` 或直接进 plan mode

## 设计原则

- **过滤优先于发散**：默认拒绝，证据通过才进入下一关
- **竞品邻接 > 蓝海**：没有竞品的赛道，对 solo 来说通常是没人要
- **数据源决定产品形态**：不要默认 Chrome 扩展，按数据在哪里选
- **不靠记忆要现网证据**：pricing / installs / reviews 必须是当前 web 数据，写不出来就标 partial
- **不是同样东西但免费**：差异化必须能用一句话说清"更窄/更快/更近"

## License

MIT
