# Prompt Builder Agent Skill

This package is structured as a standard agent skill folder.

## Claude / Claude Code

A skill is a folder containing `SKILL.md` with YAML frontmatter.  
Place this folder in your Claude skills directory, for example:

```bash
mkdir -p ~/.claude/skills
cp -R prompt-builder-agent-skill ~/.claude/skills/
```

Then in Claude Code you can use:

```text
/prompt-builder
```

or simply ask something vague like:

```text
I want to build a tariff calculator. Help me turn it into a strong prompt.
```

## Codex

Codex Agent Skills also use a folder with `SKILL.md`, plus optional `scripts/`, `references/`, and `assets/`.

Install location may depend on your Codex setup. If your Codex environment supports skills, copy this folder into the configured skills directory.

For a normal project repo, you can also add an `AGENTS.md` file that tells Codex when to use this skill or to read this folder.

## Optional helper

`scripts/prompt_builder_helper.py` is a small CLI helper. It is optional.

Run:

```bash
python scripts/prompt_builder_helper.py
```

## What this skill does

It turns rough ideas into structured prompts through guided choices and reasonable defaults.
