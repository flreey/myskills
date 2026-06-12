---
name: skill-forge
description: Use when the user wants to create or improve an agent skill — turn an incident, lesson, or repeated correction into a skill; bootstrap a primer skill for a new domain or tech stack (game engine, framework, platform) the user is starting; distill entries from lessons.md into reusable rules; or fix an existing skill that misfires, never triggers, or reads like generic advice. Also use when the user asks "what skills does this project need".
---

# Skill Forge

## Overview

Builds domain-specific, validated skills instead of generic ones. Two principles:

1. **Delta principle.** A skill is only worth what the model does NOT already know: the user's thresholds, hard constraints, forbidden operations, version pins, counter-examples. If official docs or model knowledge already cover it, it does not go in the skill.
2. **A skill is not done when it is written. It is done when a test showed it changes agent behavior.**

## Mode Routing

| Situation | Mode | Protocol |
|---|---|---|
| Specific lesson/incident/need to turn into a skill | forge | [references/forge-protocol.md](references/forge-protocol.md) |
| New domain or stack, user doesn't know what skills they need | bootstrap | [references/bootstrap-protocol.md](references/bootstrap-protocol.md) |
| Repeated corrections in lessons.md / sessions to crystallize | harvest | [references/harvest-protocol.md](references/harvest-protocol.md) |

Every mode ends with [references/validation-protocol.md](references/validation-protocol.md). No exceptions.

## Iron Rules (all modes)

1. **Interview before generation.** Self-research first (scan the project, read lessons.md, check docs), then ask the user what only they know. Generating a skill without completing the interview step is a violation — even if you are confident you know the domain.
2. **Validation before delivery.** Run the tiered validation in validation-protocol.md before presenting the skill as done. Delivering an untested skill is a violation.
3. **Search before build.** Look for an existing open-source skill first. If one scores 80%, adapt it instead of writing from scratch.
4. **Placement triage before writing.** Mechanically checkable rule → lint/hook/CI, not prose. Single-project convention → that project's CLAUDE.md. Model already knows it / docs cover it → leave it out. Only what remains becomes skill content.
5. **Tool-agnostic body.** Never name host-specific tools (Task, TodoWrite, Edit, AskUserQuestion, subagent types) in a generated skill's body. Write the intent ("before any file edit", "run the scenario in a fresh agent session") so the same skill works in Claude Code and Codex.
6. **Premises block.** Every generated skill records what it depends on: versions, platforms, policy numbers, date checked. When a premise changes, the skill is due for review, not trust.
7. **Description = triggers only.** Starts with "Use when", third person, target under 500 characters, hard cap 1024. Never summarize the skill's rules or workflow in it — agents follow the summary and skip the body.

## Rationalization Table

These exact excuses were observed in baseline tests. They are all violations:

| Excuse | Reality |
|---|---|
| "These pitfalls are well-documented by the community, no interview needed" | Community knowledge is the part the model already has. The interview extracts the user's delta — version, scope, private incidents. Skipping it produced a 2.x/3.x mix-up in testing. |
| "Known failure modes are community-verified, that replaces validation" | Validation tests whether THIS skill changes agent behavior, not whether the facts are true. True facts in a skill that never triggers or gets skipped are worth nothing. |
| "If the agent hits an uncovered pitfall later, just add it to the table" | That is deferring validation to production — using the user's real project as the test environment. |
| "I'm confident about this domain, generating directly is faster" | Confidence is what produced speculative coverage (physics, payments, leaderboards nobody asked for) in baseline. Ask first. |
| "It's just a small reference skill, testing is overkill" | Light A/B validation costs minutes. An untested skill that misfires costs every future session. |

## Red Flags — STOP

- About to output a SKILL.md and you have asked the user zero questions
- About to say "done" / "可以保存了" and no validation has run
- The description contains "Core rule:", "Provides...", or any list of what the skill contains
- The body says Edit/Write/Task/TodoWrite or any host tool name
- You cannot name the version/premise the skill depends on
