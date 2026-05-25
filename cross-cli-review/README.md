# cross-cli-review

让 Claude Code 调用 Codex CLI 做 review，或反过来，**而且这次 review 真的有用**。

## 这个 skill 解决什么

跨 CLI review 经常做得很差，原因不是模型不行，是**机械问题**：

- CLI 参数错（漏 `--base`、漏 `-s read-only`、漏 `-C`、漏 `--permission-mode plan`）
- Reviewer 跑去读 `~/.claude/skills/`、`~/.codex/skills/` 里的 SKILL.md，浪费 5 分钟啥也没产出
- Prompt 是"帮我看下这段代码"，返回 30 条通用 checklist，没有一条能落地
- 没有 sandbox → reviewer 顺手把代码改了
- `xhigh` 默认开 → 23x token 成本，挂半小时

这个 skill 把这些坑全部固化成模板：**正确的命令 + 正确的 prompt + 正确的输出处理**。

## 触发时机

自然语言任意一种：

- "让 codex review 一下这个 PR"
- "用 claude 帮我看下这段代码"
- "second opinion from codex / 反向 review"
- "codex challenge 一下我这个改动"
- "我在 claude 里，叫 codex 看下这个 plan"
- "我在 codex 里，让 claude 审一下"

## 工作流

1. **检测方向** — 你在哪个 CLI 里 → reviewer 是另一个
2. **选 scope** — branch diff / 未提交 / 指定文件 / plan / 架构问题
3. **选 review type** — general / security / performance / architecture / plan / challenge
4. **构造命令** — 从 `references/<reviewer>-headless.md` 拷贝模板，只填占位符
5. **构造 prompt** — 文件系统边界 + 角色 + 范围 + 焦点 + 输出格式 + DO NOT
6. **执行 + 原样呈现** — verbatim block，不要总结掉
7. **决策下一步** — 给出 verdict + 推荐动作，让用户拍板

## 文件结构

```
cross-cli-review/
├── SKILL.md                          # 主入口，加载它即可
├── README.md                         # 本文件
└── references/
    ├── codex-headless.md             # Claude → Codex 的命令模板
    ├── claude-headless.md            # Codex → Claude 的命令模板
    ├── review-prompts.md             # 6 种 review type 的 prompt 模板
    └── pitfalls.md                   # 10 个常见坑 + 修复方案
```

`references/` 按需加载，不会一次性塞进 context。

## 安装

```bash
# Claude Code
cp -R cross-cli-review ~/.claude/skills/

# Codex CLI
cp -R cross-cli-review ~/.codex/skills/
```

或者用仓库根目录的一键 prompt 让 agent 自己装。

## 不适合用这个 skill 的场景

- 想让**当前** CLI review 自己 → 用 host 自带的 `/review`，不需要跨 CLI
- 想让人类 review → 直接开 PR
- pair programming（边写边讨论）→ 这是 review，不是 pair

## 设计原则

- **机械问题用模板兜底**：CLI flag、sandbox、cwd、reasoning effort 全部固定写死，避免每次现场拼
- **Prompt 强制结构化**：focus 必须具体编号、输出必须有严重级别、必须有 DO NOT
- **Reviewer 输出原样呈现**：不总结、不裁剪、不"提炼要点"——后面再加 host 的 synthesis
- **用户拍板**：reviewer 给 verdict，host 给建议，最终决策永远是用户

## License

MIT
