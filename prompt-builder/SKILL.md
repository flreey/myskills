---
name: prompt-builder
description: Use this skill when the user gives a vague request AND specifically wants a copy-ready prompt to send to another LLM (Claude/GPT/Gemini/image models/etc.). Turns rough ideas into structured prompts via guided choices, sensible defaults, self-critique, and model-aware adaptation. Covers image, product, writing, code/automation, business, research, and agent/automation tasks. NOT for design/planning workflows that produce engineering specs or implementation plans — use brainstorming-style skills for those.
---

# Prompt Builder Skill

## Purpose

Turn a vague user idea into a clear, structured, high-quality prompt that another LLM (or human) can act on without guessing.

The user often says things like:

- "I want to build a tariff calculator"
- "Make a depressing image"
- "Help me write something about anxiety"
- "I want a research report on X"
- "I need an agent that does Y"
- "I don't know how to describe it"

Do not assume the user already knows the structure. Help them discover it.

## Core behavior

When this skill is relevant:

1. Identify the task type.
2. Restate the user's likely goal in plain language.
3. Ask a small number of guided questions (≤3 per turn).
4. Prefer multiple-choice over open-ended.
5. Always include "Not sure, choose for me."
6. If the user is unsure, pick a reasonable default and continue.
7. Generate a draft prompt using the universal structure.
8. **Self-critique the draft** (see "Self-critique" below). Fix issues inline.
9. **Adapt to the target model** if the user named one (Claude, GPT, Gemini, etc.).
10. Deliver the final copy-ready prompt. Optionally offer 2-3 alternative directions.

## Do not

- Do not ask too many questions at once.
- Do not use heavy jargon unless the user asks.
- Do not output a huge prompt before the task is clear.
- Do not get stuck waiting for perfect information.
- Do not produce generic prompts with only style words and no mechanism.
- Do not skip the self-critique step.

## Universal prompt structure

The final prompt should usually contain:

- Goal
- Context
- Target user / audience
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

Classify into one of these types (load the matching template from `references/templates/` if available):

- Image / visual
- Product / tool
- Writing / copy
- Code / automation
- Business / strategy
- Research / analysis
- Agent / automation system
- Learning / explanation
- General task

Say:

> I think this is a [type] task. You probably want: [plain-language goal].

### Step 2: Ask choices

Ask no more than 3 questions at a time. Each question should be easy to answer.

```text
Which direction is closest?

A. Basic tool: solve one clear problem
B. Decision tool: compare options and recommend
C. Commercial tool: designed for paying users
D. Not sure, choose for me
```

### Step 3: Build defaults

If the user picks "not sure" or gives a vague answer, pick a default and explain it briefly.

> I'll default to B because it creates more value than a basic calculator.

### Step 4: Draft the prompt

Produce a copy-ready draft using:

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

### Step 4.5: Self-critique

Before delivering, score the draft on three axes (1-5). If any axis < 4, fix inline.

- **Specificity** — Could a stranger execute this without DM-ing me back? Are inputs/outputs concrete (types, units, examples), not abstract nouns?
- **Actionability** — Is there a clear mechanism, not just decoration ("make it good", "be creative")? Is success checkable (acceptance criteria, examples)?
- **Robustness** — Could another model misinterpret any line? Are scope, audience, and forbidden moves unambiguous?

Common fixes when an axis is weak:
- Replace "good UI" → name the framework, breakpoints, accessibility level (WCAG AA), specific components.
- Replace "comprehensive analysis" → list the questions to answer, the framework to apply, sources to cite.
- Add 1 concrete example of the desired output style.

### Step 5: Adapt to the target model

Ask or infer the target model. Apply the matching style:

- **Claude (4.x / latest)** — Use XML tags (`<context>`, `<task>`, `<format>`) for sectioning. Put stable instructions/system info first (cache-friendly), variable user input last. Use explicit role framing only when needed.
- **GPT-5 / o-series** — Markdown headings work well. Be explicit about reasoning effort if applicable. JSON schema in `Outputs:` if structured output is needed.
- **Gemini / others** — Markdown + clear numbered steps. Avoid heavy XML.
- **Unknown / portable** — Markdown headings, plain language, no platform-specific tokens. This is the default.

If the user didn't specify a model, default to portable + offer to optimize for a specific model.

### Step 6: Deliver

Output the final prompt in a single fenced block (so it's copy-ready). Optionally append:

- 2-3 alternative directions (1 line each)
- A note on what to change if the user wants a tighter / broader version

## Type-specific guidance

For each type below, ask the listed clarifications, then ensure the final prompt covers the listed elements. For longer reference templates, see `references/templates/<type>.md`.

### Image / visual

**Clarify:** core concept, emotion, subject, space, action, conflict, visual metaphor, style, forbidden elements.
**Must include:** concept sentence, subject relationship, moment, visual metaphor, composition, color, style, negative prompt.

### Product / tool

**Clarify:** target user, use case, MVP scope, inputs, outputs, data source, technical constraints, monetization.
**Must include:** product goal, user profile, core workflow, MVP features, page structure, data model, tech stack, edge cases, acceptance criteria.

### Writing / copy

**Clarify:** reader, purpose, tone, length, structure, what to avoid.
**Must include:** writing goal, audience, main thesis, outline, tone, examples (if needed), avoid list.

### Code / automation

**Clarify:** runtime, language, inputs/outputs, dependencies, error handling, tests, file structure.
**Must include:** dev goal, environment, requirements, files, implementation details, test plan, run commands.

### Business / strategy

**Clarify:** decision to make, market/object, time horizon, data available, risk tolerance, output format.
**Must include:** analysis goal, background, questions, framework, data needed, assumptions, risks, recommendation format.

### Research / analysis

**Clarify:** core question, scope (geographic / temporal / domain), sources allowed, depth (overview vs deep dive), required citations, output format (report / table / brief).
**Must include:** research question, sub-questions, source policy (peer-reviewed / web / internal), method, deliverable structure, citation format, fact-checking standard, what's out of scope.

### Agent / automation system

**Clarify:** trigger, state, available tools, loop termination condition, error recovery, observability/logging, human-in-the-loop checkpoints.
**Must include:** agent goal, trigger conditions, state model, tool list with usage rules, decision policy, termination rule, error/retry policy, logging requirements, escalation path.

### Learning / explanation

**Clarify:** prior knowledge, goal (intuition vs exam-pass vs working ability), depth, examples needed.
**Must include:** learner profile, target understanding, scaffolding order, examples, check-for-understanding questions.

## Template library

Detailed examples for each type live in `references/templates/`. Load the relevant one when drafting:

- `references/templates/image.md`
- `references/templates/product.md`
- `references/templates/writing.md`
- `references/templates/code.md`
- `references/templates/business.md`
- `references/templates/research.md`
- `references/templates/agent.md`

Each template shows: a vague input → the questions asked → the final prompt. Use them as few-shot anchors, not rigid scaffolds.

## Quality checklist (fast version)

Before delivering, confirm:

- Goal is specific (a stranger can execute it).
- Inputs and outputs are concrete (types, examples).
- Constraints are explicit.
- There is a mechanism, not just decoration.
- Acceptance criteria are checkable.
- The prompt fits the target model's idioms (or is portable by design).

If any item fails, ask one more focused question or set a reasonable default — don't ship a weak prompt.
