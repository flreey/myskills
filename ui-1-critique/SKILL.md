---
name: ui-1-critique
description: "【1 体检】体验评审打分：视觉层级、信息结构、认知负担、情绪感受，按用户画像走一遍，列出优先问题和改法。不知道哪里不好时先用它。等于 /impeccable critique；完整顺序看 /ui。"
argument-hint: "[页面或组件]"
disable-model-invocation: true
---

# /ui-1-critique → /impeccable critique

这是 `/impeccable critique` 的中文快捷入口，阶段：1 体检。完整顺序见 `/ui`。

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: critique $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `critique` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。本文件不增加、不改变 impeccable 的任何规则。
3. 结束时用一句话提示下一步可用的 `/ui-*` 命令，顺序：0 准备 → 1 体检 → 2 规划 → 3 修改 → 4 收尾 → 5 沉淀。
