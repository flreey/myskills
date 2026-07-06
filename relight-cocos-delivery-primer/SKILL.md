---
name: relight-cocos-delivery-primer
description: Use when working in the Relight Cocos Creator project or planning changes for it, especially gameplay logic, level data, Cocos view code, visual polish, browser verification, or Web/Android/iOS delivery.
---

# Relight Cocos Delivery Primer

## Premises

- Project: `/Users/flreey/Projects/cocos/Relight`.
- Checked: 2026-06-12.
- Engine: Cocos Creator `3.8.8` from `package.json`.
- Stack: TypeScript, Cocos Creator components, Vitest for headless pure logic.
- Targets: Web, Android, and iOS. Avoid solutions that only work in a browser unless the task explicitly says Web-only.
- Owner preference: the agent handles straightforward verification; the user only does final human judgement for visual feel and player expectation.

Review this skill when Cocos version, target platforms, build workflow, or project ownership boundaries change.

## Current Source Of Truth

Before changing code, read the task-relevant local sources:

- `AGENTS.md` for standing project rules.
- `docs/README.md` for current roadmap and which plans are active.
- `tasks/lessons.md` before visual, Cocos, browser, or build work.
- Core puzzle contracts in `assets/scripts/game/`.
- View behavior in `assets/scripts/view/`.
- Level data in `assets/resources/levels/`.

Do not treat old plan text as stronger than current code. If roadmap text and code disagree, inspect current code and state the discrepancy.

## Boundary

Keep puzzle rules Cocos-free:

- Pure gameplay, validation, generation, save, hint, feedback, and level-contract logic belongs under `assets/scripts/game/`.
- Cocos nodes, components, rendering, audio, browser interaction, and layout belong under `assets/scripts/view/`.
- UI components may consume pure results but must not become the owner of puzzle rules.
- Add or update Vitest coverage when pure TypeScript behavior changes.

Keep v1 delivery lean:

- Do not introduce backend dependencies.
- Do not add platform-specific native behavior unless the task is explicitly a mobile packaging/release task.
- Prefer small, reviewable changes that can be verified in isolation.

## Cocos Creator Boundaries

Never hand-edit generated native Android/iOS folders unless the user explicitly asks for native packaging work.

Treat GUI-owned or serialized project files carefully:

- Do not casually rewrite `.scene`, `.prefab`, `.meta`, or `settings/v2/**`.
- In particular, do not modify `settings/v2/**` while Cocos Creator may be open. If engine module settings were changed behind the editor and preview shows contradictory class-missing/module-resurrected errors, recover by closing the editor, deleting `temp/programming`, and restarting the editor.
- If a task needs a GUI-only operation, give the user a short explicit checklist instead of pretending it was verified.

For runtime-created UI nodes:

- Visible nodes under Canvas must inherit the UI layer from their parent or use the local helper `assets/scripts/view/uiNode.ts`.
- Prefer the helper path for new UI nodes so the Cocos UI camera renders them.

## Visual And Browser Verification

For visual or interaction changes, browser verification is part of done. Unit tests alone are not enough.

Minimum browser pass:

- Build or serve the current Web target in the project-appropriate way.
- Open the built game in a browser.
- Exercise the changed screen or interaction manually or with automation.
- Check console warnings/errors.
- For responsive UI, inspect at least one portrait mobile-sized viewport and one desktop-sized viewport when layout can be affected.

For stateful visual objects, verify states, not just existence:

- Directional tiles must be checked across their logical orientations.
- Buttons or hotspots must be checked against the visible element they represent.
- Animations should be checked by observing state over time when screenshots are timing-sensitive.
- After navigation or modal changes, confirm the new state before sending the next synthetic click.

Browser-specific Relight lessons:

- If a rebuilt Web bundle appears stale, changing port is the safest cache reset because it creates a new origin.
- WebGL screenshot timing can miss transient effects; component-state sampling is often more reliable for animation verification.
- Transparent touch areas can steal clicks. Anchor interaction zones to visible controls or shared geometry, not independent screen ratios.

## Verification Ladder

Choose the smallest ladder that proves the change:

- Pure game logic or level contract: `npm test`; add `npm run typecheck` when types or exported contracts changed.
- View helper logic covered by tests: `npm test` plus browser verification when rendered behavior changes.
- Cocos component, layout, audio, animation, input, or visual polish: browser verification is required; run tests/typecheck when nearby pure helpers or contracts changed.
- Level generation/data changes: run generation if the generator changed, run tests that validate the level curve/contracts, and browser-check representative affected levels.
- Android/iOS release work: keep native changes explicit and separate; if final device verification cannot be performed by the agent, hand the user a concrete smoke checklist.

Report unverified GUI/device steps plainly. Do not imply that Cocos Editor, Android, or iOS behavior was verified when only Web/browser checks ran.

## Harvest Watch List

Promote these to separate skills only after they recur as real work or repeated corrections:

- `relight-level-content-validation`: level authoring, 51-72 chapter rules, difficulty curve, `par`, `moveLimit`, `solution`, color/prism contracts.
- `relight-visual-browser-qa`: visual state matrices, Cocos Web cache, WebGL capture, interaction hotspots, animation-state sampling.
- `relight-mobile-release-runbook`: Android/iOS packaging, store assets, privacy pages, signing, final device smoke.
