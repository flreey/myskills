# Prompt Builder Skill

Turns vague, casual, or incomplete requests into clear, copy-ready prompts — through guided choices, sensible defaults, self-critique, and model-aware adaptation.

## What it covers

Image, product, writing, code, business, research, agent/automation, learning, and general tasks. Each type has a dedicated reference template under `references/templates/` showing a vague input → final prompt.

## 📋 一键安装（直接复制粘贴）

```text
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/prompt-builder
```

就这一行粘给 Claude Code 或 Codex CLI 即可。详细兜底版见仓库根目录 [README](../README.md#详细安装-prompt兜底版)。

## 与 superpowers / brainstorming 类 skill 的区别

| Skill | 输出 | 用途 |
| --- | --- | --- |
| `superpowers:brainstorming` | 设计文档 + spec | 探索需求，准备写代码 |
| `prompt-builder`（本 skill） | 可复制的 LLM prompt | 发给另一个 LLM 执行 |

如果想要 prompt 但被 brainstorming 抢走了，显式说：`用 prompt-builder 帮我把 X 整理成 prompt`。

## 手动安装

This skill follows the universal `SKILL.md` standard, so the same folder works for both Claude Code and Codex CLI. Just put it in the right place.

### Claude Code

```bash
mkdir -p ~/.claude/skills
cp -R prompt-builder ~/.claude/skills/
```

### Codex CLI

```bash
mkdir -p ~/.codex/skills
cp -R prompt-builder ~/.codex/skills/
```

For project-scoped use, drop it under `.claude/skills/` or `.codex/skills/` (or `.agents/skills/`) inside your repo.

Most modern agents auto-discover the skill immediately. If yours doesn't, start a new session.

## Trigger

Anything vague that benefits from being turned into a structured prompt. Examples:

- "I want to build a tariff calculator"
- "Make a depressing image"
- "Help me write something about anxiety"
- "Research what's happening with small modular reactors"
- "I want an agent that triages my GitHub issues"

You can also explicitly invoke: `/prompt-builder` (Claude Code) or `用 prompt-builder skill ...`

## What you get back

A copy-ready prompt with:

- Goal / Context / Audience / Inputs / Outputs / Constraints / Structure / Mechanism / Quality bar / Avoid / Acceptance criteria
- Self-critique on specificity, actionability, robustness — issues fixed inline
- Adapted to your target model (Claude / GPT / portable) if specified

## Files

```
prompt-builder/
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
