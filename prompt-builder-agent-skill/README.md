# Prompt Builder Agent Skill

Turns vague, casual, or incomplete requests into clear, copy-ready prompts — through guided choices, sensible defaults, self-critique, and model-aware adaptation.

## What it covers

Image, product, writing, code, business, research, agent/automation, learning, and general tasks. Each type has a dedicated reference template under `references/templates/` showing a vague input → final prompt.

## Install

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
