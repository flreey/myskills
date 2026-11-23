---
name: ui-critique
description: "做完后的体验评审：视觉层级、信息结构、认知负担，按用户画像走一遍，列出优先问题和改法。不知道哪里不好时用它。等于 /impeccable critique；完整菜单看 /ui。不用于：技术体检（/ui 无障碍、性能）、直接修改（/ui-polish 或 /ui）。"
argument-hint: "[页面或组件]"
disable-model-invocation: true
---

# /ui-critique → /impeccable critique

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: critique $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `critique` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。PRODUCT.md 的 Brand Commitments 里有站长锁定的视觉方向时，评审以它为准，不建议换掉它。
3. 结束时一句话提示下一步：站长挑出要修的问题后用 `/ui-polish`，单个问题用 `/ui <描述>`。
