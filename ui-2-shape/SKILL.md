---
name: ui-2-shape
description: "【2 规划】动手前先规划：理清任务、状态、信息和约束，再决定界面怎么改。改流程、做新页面时用。等于 /impeccable shape；完整顺序看 /ui。"
argument-hint: "[功能或流程]"
disable-model-invocation: true
---

# /ui-2-shape → /impeccable shape

这是 `/impeccable shape` 的中文快捷入口，阶段：2 规划。完整顺序见 `/ui`。

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: shape $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `shape` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。本文件不增加、不改变 impeccable 的任何规则。
3. 结束时用一句话提示下一步可用的 `/ui-*` 命令，顺序：0 准备 → 1 体检 → 2 规划 → 3 修改 → 4 收尾 → 5 沉淀。
