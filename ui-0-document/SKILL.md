---
name: ui-0-document
description: "【0 准备】从现有代码生成设计规范 DESIGN.md（颜色、字体、间距、圆角、组件）。接手老项目时先跑；大改版做完后再跑一次更新。等于 /impeccable document；完整顺序看 /ui。"
disable-model-invocation: true
---

# /ui-0-document → /impeccable document

这是 `/impeccable document` 的中文快捷入口，阶段：0 准备。完整顺序见 `/ui`。

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: document $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `document` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。本文件不增加、不改变 impeccable 的任何规则。
3. 结束时用一句话提示下一步可用的 `/ui-*` 命令，顺序：0 准备 → 1 体检 → 2 规划 → 3 修改 → 4 收尾 → 5 沉淀。
