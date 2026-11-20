---
name: ui-0-init
description: "【0 准备】建产品档案：几轮问答写 PRODUCT.md（用户、产品目的、品牌、原则），之后所有 ui 命令都会读它。新项目第一步，每个项目做一次；已有 PRODUCT.md 不用再跑。等于 /impeccable init；完整顺序看 /ui。"
argument-hint: "[可选：项目说明]"
disable-model-invocation: true
---

# /ui-0-init → /impeccable init

这是 `/impeccable init` 的中文快捷入口，阶段：0 准备。完整顺序见 `/ui`。

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: init $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `init` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。本文件不增加、不改变 impeccable 的任何规则。
3. 结束时用一句话提示下一步可用的 `/ui-*` 命令，顺序：0 准备 → 1 体检 → 2 规划 → 3 修改 → 4 收尾 → 5 沉淀。
