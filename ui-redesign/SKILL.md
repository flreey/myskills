---
name: ui-redesign
description: "要大胆、要全新视觉世界时才用：走 impeccable 的新设计流程（按页面类型选模式，随机抽方向、出视觉稿，再实现），替换现有外观。适合品牌活动页、发布页、想看完全不同方向找灵感。日常建站和换配色不用它。不用于：选一套顺眼的配色字体（/ui-style）、定交互（/ui-flow）、修具体问题（/ui）。"
argument-hint: "[页面或界面 + 想要的感觉，如：首页重做，要更有冲击力]"
disable-model-invocation: true
---

# /ui-redesign → /impeccable（新设计流程）

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`；其他宿主加载同名 skill），`args` 写成：`新设计（替换视觉世界）：$ARGUMENTS。站长要求替换 PRODUCT.md Brand Commitments 里现有的视觉方向，旧方向作为证据和反面参考。` 没有参数时写成 `为这个项目做新设计（替换视觉世界）`。
2. 用户原话里的“重做 / 更酷 / 更有冲击力”等字眼原样保留。完全按 impeccable 的指令执行，包括 Setup、提问、`concept-seed`、方向选择页和视觉稿。
3. 定稿后，把 PRODUCT.md `## Brand Commitments` 的视觉方向改成新方向（写明日期和“via /ui-redesign”），DESIGN.md 由 impeccable 更新。
4. 结束时一句话提示下一步：`/ui-critique` 看效果；要更有冲击力用 `/impeccable bolder`、`animate`、`overdrive`；上线前 `/ui-polish`。
