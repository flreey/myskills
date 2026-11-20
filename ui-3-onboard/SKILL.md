---
name: ui-3-onboard
description: "【3 修改】首次使用体验：欢迎页、空状态、新手引导，让新用户尽快拿到结果。等于 /impeccable onboard；完整顺序看 /ui。"
argument-hint: "[页面或流程]"
disable-model-invocation: true
---

# /ui-3-onboard → /impeccable onboard

这是 `/impeccable onboard` 的中文快捷入口，阶段：3 修改。完整顺序见 `/ui`。

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: onboard $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `onboard` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。本文件不增加、不改变 impeccable 的任何规则。
3. 结束时用一句话提示下一步可用的 `/ui-*` 命令，顺序：0 准备 → 1 体检 → 2 规划 → 3 修改 → 4 收尾 → 5 沉淀。
