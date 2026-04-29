---
name: prompt-builder
description: Use this skill when the user gives a vague, short, casual, or incomplete request and wants help turning it into a high-quality prompt through guided questions, options, defaults, and iterative refinement. Useful for product ideas, image prompts, writing prompts, coding tasks, business analysis, and general AI task design.
---

# Prompt Builder Skill

## Purpose

Turn a vague user idea into a clear, structured, high-quality prompt.

The user may say something casual like:

- "I want to build a tariff calculator"
- "Make a depressing image"
- "Help me write something about anxiety"
- "I want to build a website"
- "I need a prompt for Codex"
- "I don't know how to describe it"

Do not assume the user already knows the structure. Help them discover it.

## Core behavior

When this skill is relevant:

1. Identify the task type.
2. Restate the user's likely goal in simple language.
3. Ask a small number of guided questions.
4. Prefer choices over open-ended questions.
5. Always include an option like "Not sure, choose for me."
6. If the user is unsure, choose a reasonable default and continue.
7. Generate a final copy-ready prompt.
8. Optionally provide 2-3 alternative directions.

## Do not

- Do not ask too many questions at once.
- Do not use heavy jargon unless the user asks for it.
- Do not output a huge final prompt before the task is clear.
- Do not get stuck waiting for perfect information.
- Do not produce generic prompts with only style words.
- Do not ignore constraints, audience, inputs, outputs, or success criteria.

## Universal prompt structure

The final prompt should usually contain:

- Goal
- Context
- Target user or audience
- Inputs
- Outputs
- Constraints
- Structure
- Key mechanism
- Quality bar
- Prohibited mistakes
- Acceptance criteria

## Interaction pattern

### Step 1: Classify

Classify the request into one of:

- Image / visual
- Product / tool
- Writing / copy
- Code / automation
- Business / strategy
- Learning / explanation
- General task

Say:

> I think this is a [type] task. You probably want: [plain-language goal].

### Step 2: Ask choices

Ask no more than 3 questions at a time.

Each question should be easy to answer.

Example:

```text
Which direction is closest?

A. Basic tool: solve one clear problem
B. Decision tool: compare options and recommend the best one
C. Commercial tool: designed for paying users
D. Not sure, choose for me
```

### Step 3: Build defaults

If the user chooses "not sure" or gives a vague answer, pick a default and explain it briefly.

Example:

> I'll default to B because it creates more value than a simple calculator.

### Step 4: Produce final prompt

Create a clean, copy-ready prompt.

Use this format:

```text
Goal:
...

Context:
...

User / audience:
...

Inputs:
...

Outputs:
...

Constraints:
...

Structure:
...

Key mechanism:
...

Quality bar:
...

Avoid:
...

Acceptance criteria:
...
```

## Type-specific guidance

### Image / visual

Clarify:

- Core concept
- Emotion
- Subject
- Space
- Action
- Conflict
- Visual metaphor
- Style
- Forbidden elements

Final prompt must include:

- Concept sentence
- Subject relationship
- Moment
- Visual metaphor
- Composition
- Color
- Style
- Negative prompt

### Product / tool

Clarify:

- Target user
- Use case
- MVP scope
- Inputs
- Outputs
- Data source
- Technical constraints
- Monetization if relevant

Final prompt must include:

- Product goal
- User profile
- Core workflow
- MVP features
- Page structure
- Data model
- Tech stack
- Edge cases
- Acceptance criteria

### Writing / copy

Clarify:

- Reader
- Purpose
- Tone
- Length
- Structure
- What to avoid

Final prompt must include:

- Writing goal
- Audience
- Main thesis
- Outline
- Tone
- Examples if needed
- Avoid list

### Code / automation

Clarify:

- Runtime environment
- Language
- Inputs and outputs
- Dependencies
- Error handling
- Tests
- File structure

Final prompt must include:

- Development goal
- Environment
- Requirements
- Files
- Implementation details
- Test plan
- Run commands

### Business / strategy

Clarify:

- Decision to make
- Market or object
- Time horizon
- Data available
- Risk tolerance
- Output format

Final prompt must include:

- Analysis goal
- Background
- Questions to answer
- Framework
- Data needed
- Assumptions
- Risks
- Recommendation format

## Quality check

Before giving the final prompt, check:

- Is the goal specific?
- Are inputs and outputs clear?
- Are constraints explicit?
- Is there a mechanism, not just decoration?
- Could another AI act on this without guessing too much?

If not, ask one more focused question or make a reasonable default.
