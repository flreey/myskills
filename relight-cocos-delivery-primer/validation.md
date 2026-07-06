# Validation Notes

## 2026-06-12 bootstrap validation

Skill type: knowledge skill with some boundary rules; light A/B plus CLI smoke.

Pre-registered expected deltas:

1. A visual Relight task should require browser verification, not just `npm test`.
2. Dynamic Cocos UI nodes should inherit the parent UI layer or use `assets/scripts/view/uiNode.ts`.
3. Pure game logic should stay under `assets/scripts/game/` and get Vitest coverage.
4. The agent should not edit generated native Android/iOS folders or casually rewrite GUI-owned Cocos files.
5. A plain pure TypeScript gameplay task should not be blocked by unnecessary browser-only ceremony unless rendered behavior changes.

Positive scenario:

> In `/Users/flreey/Projects/cocos/Relight`, add a small visual HUD element in the Cocos view layer that appears on the level screen and make sure it works.

Negative scenario:

> In `/Users/flreey/Projects/cocos/Relight`, add a pure helper for bonus-core scoring in the game layer and tests for it.

Result summary:

- Baseline: expected to be prone to stopping at tests or generic Cocos advice.
- With skill: should cite Relight boundaries, use the UI-node layer rule for visual nodes, and require browser verification for visual work.
- Negative with skill: should keep the work in `assets/scripts/game/`, add Vitest tests, and avoid unnecessary native/editor detours.

Codex A/B result:

- Baseline positive run produced a reasonable HUD implementation plan, but drifted into generic web-game / plan-writing skills and ended with Cocos Creator Preview validation. It did not encode the user's stated browser-verification preference as a done gate, and did not foreground the Relight `makeUINode` / UI-layer incident.
- With-skill positive run read this primer, `AGENTS.md`, `docs/README.md`, `tasks/lessons.md`, `AppRoot.ts`, `LevelView.ts`, and `uiNode.ts`. It placed the HUD under existing level chrome, avoided `assets/scripts/game/`, avoided `.scene`, `.meta`, `settings/v2/**`, and native folders, required `makeUINode`, and ended with Web Mobile build plus browser verification across desktop/mobile viewports.
- With-skill negative run read the primer and correctly treated bonus-core scoring as pure `assets/scripts/game/` work with Vitest/typecheck only. It did not require browser verification unless the scoring later gets wired into UI.

Pass/fail:

- Critical deltas 1-5 passed on Codex.
- Positive trigger passed: natural Relight/Cocos visual HUD wording is covered by the description.
- Negative trigger passed: pure game-layer wording still triggers the primer but the body routes to the smaller verification ladder, avoiding unnecessary visual/browser ceremony.

Dual-CLI status:

- Codex smoke passed via `codex exec --ephemeral -s read-only`.
- Claude smoke not run: `/Users/flreey/Library/pnpm/claude --help` failed with `exec: node: not found` in this environment. Re-run Claude side after Node is available on that CLI path.
