# Prompt Builder Agent Skill

Turns vague, casual, or incomplete requests into clear, copy-ready prompts — through guided choices, sensible defaults, self-critique, and model-aware adaptation.

## What it covers

Image, product, writing, code, business, research, agent/automation, learning, and general tasks. Each type has a dedicated reference template under `references/templates/` showing a vague input → final prompt.

## 📋 一键安装（复制下面整段粘给你的 agent）

````text
请帮我从 GitHub 安装并启用 prompt-builder-agent-skill 这个 skill。仓库地址 https://github.com/flreey/myskills

请按以下步骤执行（你需要自动判断当前是 Claude Code 还是 Codex CLI 或其他 agent，并选用对应路径）：

1. 确定目标安装目录：
   - Claude Code → ~/.claude/skills/prompt-builder-agent-skill/
   - Codex CLI   → ~/.codex/skills/prompt-builder-agent-skill/
   - 其他 agent  → 询问我目标目录
   父目录不存在就 mkdir -p。如果目标目录已存在，备份成 <name>.bak.<timestamp> 再继续。

2. 用 git sparse-checkout 只拉这一个 skill 子目录（避免下载整仓库）：
   - 创建一个临时目录（mktemp -d）
   - 在临时目录里：git clone --depth=1 --filter=blob:none --sparse https://github.com/flreey/myskills.git
   - cd myskills && git sparse-checkout set prompt-builder-agent-skill
   - 把 prompt-builder-agent-skill/ 完整 cp -R 到第 1 步确定的目标目录
   - 删掉临时目录

3. 校验：
   - <目标目录>/SKILL.md 存在
   - YAML frontmatter 含 name 和 description 字段
   - references/templates/ 下有 7 个 .md 模板文件

4. 安装完成后，告诉我：
   - 实际安装路径
   - 这个 skill 的触发条件（哪些请求会激活它）
   - 是否需要重启会话才能识别

如果任何一步失败，停下来报告错误，不要静默继续。
````

## 手动安装

This skill follows the universal `SKILL.md` standard, so the same folder works for both Claude Code and Codex CLI. Just put it in the right place.

### Claude Code

```bash
mkdir -p ~/.claude/skills
cp -R prompt-builder-agent-skill ~/.claude/skills/
```

### Codex CLI

```bash
mkdir -p ~/.codex/skills
cp -R prompt-builder-agent-skill ~/.codex/skills/
```

For project-scoped use, drop it under `.claude/skills/` or `.codex/skills/` (or `.agents/skills/`) inside your repo.

After install, start a new session — the agent will auto-discover the skill from `SKILL.md`'s frontmatter.

## Trigger

Anything vague that benefits from being turned into a structured prompt. Examples:

- "I want to build a tariff calculator"
- "Make a depressing image"
- "Help me write something about anxiety"
- "Research what's happening with small modular reactors"
- "I want an agent that triages my GitHub issues"

You can also just say `/prompt-builder` (Claude Code) or invoke by name in Codex.

## What you get back

A copy-ready prompt with:

- Goal / Context / Audience / Inputs / Outputs / Constraints / Structure / Mechanism / Quality bar / Avoid / Acceptance criteria
- Self-critique on specificity, actionability, robustness — issues fixed inline
- Adapted to your target model (Claude / GPT / portable) if specified

## Files

```
prompt-builder-agent-skill/
├── SKILL.md                    # main skill instructions (auto-loaded)
├── AGENTS.md                   # Codex-style usage hint
├── README.md                   # this file
└── references/
    └── templates/
        ├── image.md
        ├── product.md
        ├── writing.md
        ├── code.md
        ├── business.md
        ├── research.md
        └── agent.md
```

## License

MIT
