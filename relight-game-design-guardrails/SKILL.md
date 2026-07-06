---
name: relight-game-design-guardrails
description: Use when proposing or planning Relight gameplay changes, new mechanics, new chapters, large level batches, reward systems, playability fixes, or when the user says the game feels like connecting for its own sake. NOT for bug fixes, build issues, small visual polish, or post-implementation playtest review.
---

# Relight Game Design Guardrails

## Premises

- Project: `/Users/flreey/Projects/cocos/Relight`.
- Checked: 2026-06-12.
- Game: 2D Cocos Creator `3.8.8` + TypeScript puzzle game.
- Targets: Web, Android, and iOS.
- Current risk: the core action can collapse into "connect pipes because the level says so" unless connection creates a meaningful result.
- v1 stance: stay lean; deepen the existing light/star-chart fantasy before adding heavy new rule systems.

Review this skill when the theme, target audience, chapter structure, or core loop changes.

## First Reflex

Before proposing a gameplay feature, new mechanic, or level batch, answer this in one sentence:

> What player meaning does this create after the light connects?

If the answer is only "the puzzle is solved", stop. Redesign the idea before implementation.

## Core Promise

Relight is not about connecting lines. It is about:

1. reading a dark board,
2. making one deliberate rotation,
3. watching light reveal, restore, or awaken something.

Every gameplay addition must strengthen at least one of these experiences:

- **See:** the player understands a new structure in the board.
- **Choose:** the player makes a meaningful rotation, not random trial.
- **Light:** the connection produces an immediate satisfying response.
- **Restore:** the completed level changes a visible star-chart/world state.

If an idea only increases board size, path length, rule count, or move pressure, reject it or convert it into a short filler/reward beat.

## Meaning Return Gate

For each new level, mechanic, chapter, or reward idea, assign at least one meaning return:

- **Discovery:** connecting light reveals a new star, constellation stroke, background state, hidden core, or chapter motif.
- **Expression:** the solved path forms a readable shape, symmetry, split-beam burst, or visually satisfying route.
- **Understanding:** the level teaches a new way to read the board: main path, leak, color separation, splitter payoff, or optional optimization.
- **Relief:** the level intentionally lowers friction after pressure and gives the player a quick beautiful win.
- **Culmination:** the level combines prior ideas into a clear finale without adding a new rule.

No meaning return means no feature yet.

## Chapter Rhythm

Design chapters around one dominant player lesson. Do not introduce multiple major rules in one chapter.

Use this rhythm unless the current roadmap already defines a stricter one:

- 1-2 onboarding levels: make the new reading obvious.
- 3-5 practice levels: vary the same reading without adding another rule.
- 1 relief/reward level: lower friction, high payoff.
- 2-4 pressure levels: combine with older rules.
- 1 culmination level: memorable finish, not the hardest possible board.

Relight star-chart pages use 12-level groups. New chapter boundaries and new mechanic first appearances should align with visible page/constellation boundaries unless the task explicitly explores a transition chapter.

## Mechanic Admission Test

A new mechanic is allowed only if all are true:

- It creates a new way to read the board, not just more work.
- It can be taught with one clear visual situation.
- It has a satisfying success moment.
- It has a clear failure signal.
- It can be validated in pure TypeScript for rules and in browser for player-facing behavior.
- It does not require backend, large new art systems, or native platform work for v1.

If any item fails, choose a lower-risk alternative:

- tune level shape,
- improve feedback,
- add a reward beat,
- connect the result more strongly to the star chart,
- or deepen an existing mechanic such as color separation, splitter payoff, leak management, or optional bonus cores.

## Level Intent Gate

Every non-filler level should have one sentence of intent:

- "Teach that cyan and amber must stay separate."
- "Reward one rotation that lights three targets."
- "Make leak avoidance visible before it becomes punishing."
- "Give a low-friction constellation-restoration beat."
- "Ask the player to choose between a tempting leak and the sealed route."

If the intent cannot be written, do not generate or hand-tune the level yet.

## Anti-Patterns

Reject these by default:

- Bigger grid equals harder level.
- More decoys without a readable trap.
- New rule added because the last chapter feels stale.
- A chapter where every level has the same pressure profile.
- Bonus objective that blocks normal completion.
- Reward system that hides the board's own light-up payoff.
- UI copy explaining a mechanic that the board and feedback do not make visible.
- Visual spectacle that fires before the player understands what they caused.

Use these alternatives:

- make the trap visible,
- give the level a shape or restoration target,
- make the success/failure signal sharper,
- insert a relief beat,
- or remove the level.

## Pre-Design Output

Before writing an implementation plan for a gameplay/chapter/level-batch idea, produce a short guardrail check:

- **Player meaning:** one sentence.
- **Meaning return:** discovery / expression / understanding / relief / culmination.
- **Dominant lesson:** the one thing this content teaches or reinforces.
- **Success moment:** what the player sees/hears/understands when it works.
- **Failure signal:** how the player knows why it failed.
- **Scope decision:** deepen existing system, tune content, or admit a new mechanic.
- **Rejected temptation:** the easy but wrong version to avoid.

Only proceed if this check is concrete.

## Not For

Use a delivery or QA skill instead when:

- fixing a bug,
- changing layout, buttons, audio volume, or visual polish without gameplay meaning changes,
- validating an already implemented build through playtest,
- doing Android/iOS packaging,
- or reviewing code architecture.
