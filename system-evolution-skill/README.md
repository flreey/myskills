# System Evolution Analyst Skill

A reusable local skill for analyzing complex problems using the framework:

> System → Information → Energy → Feedback → Evolution

It helps turn vague problems into system maps, failure diagnoses, feedback loops, and smallest useful experiments.

## What It Is For

Use it for:

- product validation
- customer acquisition
- paid web tools
- startup decisions
- strategy research
- learning systems
- workflow design
- AI agent design
- personal decision-making

## Folder Structure

```text
system-evolution-skill/
├── SKILL.md
├── AGENTS.md
├── README.md
├── templates/
│   ├── system-map.md
│   ├── feedback-loop.md
│   ├── experiment-plan.md
│   ├── failure-diagnosis.md
│   └── evolution-roadmap.md
├── examples/
│   ├── product-validation.md
│   ├── growth-system.md
│   ├── trading-research.md
│   └── learning-system.md
└── bin/
    └── system-skill.sh
```

## Simple Usage

Open `SKILL.md`, paste it into your AI tool as a skill/instruction, then ask:

```text
Use the System Evolution Analyst Skill to analyze this problem:
I want to validate whether my paid web tool has real demand.
```

## CLI Helper Usage

The included shell script prints a prompt wrapper that you can paste into Claude, ChatGPT, Codex, or another local AI workflow.

```bash
cd system-evolution-skill
chmod +x bin/system-skill.sh
./bin/system-skill.sh "I want to validate DutyLane's paid report feature"
```

It does not call any API. It simply formats the problem into a structured prompt.

## Recommended Workflow

1. Run the analysis with `SKILL.md`.
2. Fill out the relevant template in `templates/`.
3. Run the smallest useful experiment.
4. Record feedback.
5. Run the skill again using the observed data.
6. Keep, remove, amplify, or pivot based on feedback.

## Core Rule

Do not use this skill to generate big plans before validating the core loop.

Always prefer:

```text
small experiment → measurable feedback → next iteration
```

instead of:

```text
large plan → long build → vague result
```
