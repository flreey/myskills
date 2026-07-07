---
name: ai-feature-delivery
description: Use when the user asks an AI agent to implement or modify an existing codebase from a business/product request, especially workflow, permissions, status, finance, export, API, UI, or data behavior, and the impact surface is not fully known. NOT for pure explanations, code review only, greenfield brainstorming, or already-scoped tiny technical edits where the user explicitly asks to edit directly.
---

# AI Feature Delivery

## Purpose

Turn a business-level request into a controlled implementation workflow that makes the AI own impact discovery, acceptance framing, verification, and residual-risk reporting.

Use this skill to prevent "changed A, broke B" drift without asking the user to enumerate repository modules, files, or hidden dependencies.

## Core Rule

Do not start editing code from the user's first sentence unless they explicitly say to skip planning or directly edit.

First produce a short delivery brief from read-only discovery. The user should judge business intent and risk, not repository internals.

## Phase 1: Read-Only Discovery

Inspect only what is needed to understand the likely impact:

1. Read project guidance such as `AGENTS.md`, `PROJECT_INDEX.md`, package scripts, route maps, schema files, tests, and nearby domain code.
2. Identify business entities, permissions, statuses, API contracts, UI entry points, background jobs, import/export flows, and tests that may be touched.
3. Prefer existing project maps and `rg` over broad manual browsing.
4. Treat stale docs and stale tests as risk signals, not as truth by themselves.
5. Do not run state-changing commands, formatters with `--write`, migrations, service restarts, commits, pushes, or deployments during this phase.

## Phase 2: Pre-Change Brief

Before implementation, present this structure in Chinese:

```markdown
业务目标:
- <用业务语言描述用户真正想完成什么>

AI 自动识别的影响面:
- <领域/模块/页面/API/权限/状态/数据/测试/外部流程>

验收场景:
- <用户可理解的 happy path>
- <关键边界或反例>
- <角色/权限/状态相关场景，如适用>

不会改动的范围:
- <明确的 non-goals，防止 AI 顺手重构或扩大范围>

验证计划:
- <要跑的测试、类型检查、构建、脚本、人工检查点>
- <哪些验证可能因为环境缺失只能做静态检查>
```

Keep the brief concise. If the request is small, each section can be one bullet. If uncertainty remains, state the assumption and choose the lowest-risk default only for purely technical, local, reversible choices. Do not default business behavior, data semantics, external contracts, or irreversible operations.

## Phase 3: Implementation Guardrails

After the user confirms:

1. Keep edits within the approved impact surface unless discovery during implementation reveals a direct dependency.
2. Reuse existing components, DTOs, services, hooks, tests, and naming conventions before creating new abstractions.
3. For any feature, bugfix, refactor, or behavior change, use `superpowers:test-driven-development` before writing production code. Do not copy TDD rules here; invoke and follow that existing skill's RED-GREEN-REFACTOR workflow.
4. TDD exceptions require explicit user approval or a clearly stated reason in the final evidence: throwaway prototype, generated code, configuration-only change, docs-only change, or copy-only change.
5. Avoid opportunistic formatting, unrelated cleanup, dependency churn, schema churn, or broad refactors.
6. If the implementation reveals a materially larger impact than the brief predicted, stop and produce a revised brief before continuing.
7. Protect user changes in a dirty worktree; never revert unrelated edits.

## Phase 4: Post-Change Evidence

When finished, report in Chinese:

```markdown
实现结果:
- <改了什么，按业务能力而不是只列文件>

验证结果:
- <实际运行的命令和结果>
- <行为改动的 RED/GREEN 证据；若未使用 TDD，说明批准的例外或原因>
- <未能运行的验证及原因>

剩余风险:
- <仍可能漂移/未覆盖/依赖人工确认的地方>
- <没有剩余风险时也明确说“未发现明显剩余风险”>
```

Mention important changed files only when useful. Do not paste noisy logs unless the user asks.

## Impact Discovery Checklist

Use this checklist as prompts, not as a mandatory long report:

- Domain model: Prisma/schema/types/enums/status machines.
- Backend: controllers, services, DTOs, guards, permissions, schedulers, imports/exports.
- Frontend: routes, pages, shared components, forms, tables, filters, status badges, API clients.
- Data: migrations, seeds, fixtures, demo users, report/export columns.
- Contracts: API response shape, validation rules, pagination/sorting, error codes.
- Tests: nearby unit tests, integration/e2e, stale assertions, missing coverage around the acceptance path.
- Operations: env vars, Docker/CI/deploy scripts, background jobs, external credentials.

## ASK vs Proceed

Ask the user when the answer changes business behavior, data meaning, external behavior, or operational risk:

- Which role may perform an action.
- Which status transition should be legal.
- Whether historical data should be migrated.
- Whether an export/report/API contract may change.
- Whether an outward-facing deployment, database change, or destructive command is allowed.

Proceed with a stated default when the choice is purely technical and local:

- File placement follows existing project structure.
- Component/service naming follows nearby code.
- Tests target the closest existing test harness.
- Validation uses the narrowest command that covers the changed behavior.

## Quality Bar

A good run of this skill lets a non-code-aware user answer:

1. "Is this the business outcome I asked for?"
2. "Did the AI notice the likely places this can break?"
3. "What exactly is intentionally out of scope?"
4. "How will we know the change works?"
5. "What risk remains after implementation?"

If any answer is unclear, tighten the brief or evidence summary before moving on.
