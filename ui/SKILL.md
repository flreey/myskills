---
name: ui
description: "UI 设计改进总入口（中文菜单）：列出 /ui-flow 定交互、/ui-style 选外观、/ui-critique 评审、/ui-polish 打磨、/ui-redesign 大胆重做，并按项目现状推荐下一步；也可以直接用中文描述具体问题（手机上挤、字太小、报错看不懂、卡），由它选 impeccable 命令执行。不用于：从零建站（site-kit 会自动调用 ui-flow 和 ui-style）、查配色字体资料（ui-ux-pro-max）。"
argument-hint: "[可选：用中文描述问题]"
disable-model-invocation: true
---

# /ui：UI 设计改进总入口

新站走 site-kit：它在第 2 阶段自动调用 `ui-flow`、第 3 阶段自动调用 `ui-style`，不用手动敲。下面的入口用于 site-kit 流程之外：已上线的站、老站加功能、想换风格。

## 菜单

| 命令 | 做什么 | 什么时候用 |
| --- | --- | --- |
| `/ui-flow` | 定交互流程和各种状态，写 `docs/flow.md` | 加新功能、改流程前 |
| `/ui-style` | 从 preset 和 ui-ux-pro-max 出候选，你挑，锁定外观 | 想重新选一套配色字体 |
| `/ui-critique` | 体验评审，列优先问题 | 不知道哪里不好 |
| `/ui-polish` | 上线前打磨，关掉评审问题 | 上线前 |
| `/ui-redesign` | impeccable 随机抽方向，替换视觉世界 | 明确要大胆、全新的样子 |
| `/ui 描述问题` | 自动选下面的命令执行 | 有具体问题 |

## 描述问题时选哪个 impeccable 命令

| 问题 | 命令 |
| --- | --- |
| 手机上不好用、多尺寸 | `adapt` |
| 文字看不懂、按钮和报错文案 | `clarify` |
| 报错、断网、超长内容、多语言等边界 | `harden` |
| 新用户不知道怎么开始、空状态 | `onboard` |
| 看着乱、挤、对齐 | `layout` |
| 太复杂、元素和步骤太多 | `distill` |
| 字体、字号、可读性 | `typeset` |
| 卡、慢、加载 | `optimize` |
| 无障碍、性能、响应式技术体检 | `audit` |
| 太花、太吵 | `quieter` |
| 太平淡（仍在现有风格内） | `bolder` |
| 重复样式要收成组件和 token | `extract` |
| 更新 DESIGN.md | `document` |

其他：`colorize` 加颜色、`animate` 加动效、`delight` 加点趣味、`live` 在浏览器里点选元素出变体，直接敲 `/impeccable <命令>`。

## 怎么执行

**没有参数**：原样输出上面两张表，再调用 `impeccable` skill（不带参数），让它按项目现状推荐 2–3 个下一步；有对应 `/ui-*` 的写 `/ui-*` 名字。不自动执行。

**有参数**：

- 交互或流程问题 → 按 `ui-flow` 执行；配色字体不顺眼 → 按 `ui-style` 执行；明确要大胆重做 → 告诉用户用 `/ui-redesign`（它会替换现有外观，由用户自己触发）。
- 其他具体问题：按第二张表选最贴切的一个命令，一句话说明选了哪个、为什么，调用 `impeccable` skill，`args: <命令> <用户描述里的目标>`，完全按它的指令执行。两个命令都贴切时问一次。
- 保持 PRODUCT.md `## Brand Commitments` 里站长锁定的视觉方向；修问题不借机换风格。
