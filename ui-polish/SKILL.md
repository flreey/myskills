---
name: ui-polish
description: "上线前最后一遍打磨：把评审留下的问题逐条关掉，统一间距、字体、状态、浏览器默认样式等细节。等于 /impeccable polish；完整菜单看 /ui。不用于：换风格（/ui-style、/ui-redesign）、定交互（/ui-flow）。"
argument-hint: "[页面或组件，可附要修的评审问题]"
disable-model-invocation: true
---

# /ui-polish → /impeccable polish

1. 调用 `impeccable` skill（Claude Code：Skill 工具，`skill: impeccable`，`args: polish $ARGUMENTS`；其他宿主加载同名 skill 并运行它的 `polish` 命令），本次参数原样作为目标传过去。
2. 完全按 impeccable 的指令执行，包括它的 Setup。保持现有外观和 PRODUCT.md Brand Commitments，不借打磨换风格。
3. 结束时一句话提示下一步：site-kit 站跑 `npm run check` 看截图后可以上线；外观有变化时用 `/impeccable document` 更新 DESIGN.md。
