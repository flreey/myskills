---
name: ui-style
description: "定外观（配色、字体、圆角、密度、首屏布局）：从 site-kit preset 和 ui-ux-pro-max 出 3–4 套候选，放在站点真实页面上给站长挑，选定后写进主题、PRODUCT.md 的 Brand Commitments 和 DESIGN.md，之后的 impeccable 按它做、不再随机抽方向。site-kit 新站第 3 阶段自动加载；已有站点想重新选一套配色字体也用它。Also for 选风格、选配色、选字体、定视觉、换个顺眼的样式。不用于：想要大胆或全新视觉世界（/ui-redesign）、定交互流程（ui-flow）、修具体页面问题（/ui）。"
argument-hint: "[站点或页面，可附偏好：如 更克制 / 参考 linear.app]"
---

# /ui-style：从候选里挑外观

外观由站长从看得见的候选里挑，不靠 impeccable 的随机抽签（`concept-seed`）。本 skill 只定外观；交互在 `ui-flow`，页面实现在 site-kit 第 4 阶段或 impeccable。

## 1. 读现状

- 读项目根目录的 `PRODUCT.md`（用户、站点类型、首批页面）、`docs/flow.md`、`docs/samples/`，有 `.sitekit.json` 就是 site-kit 站。
- `PRODUCT.md` 的 `## Brand Commitments` 已有站长锁定的视觉方向，且这次不是要换：说明已定，停下。
- 站长这次给了偏好（喜欢的网站、“更克制”“要深色”）：作为硬约束，候选都要满足。

## 2. 出候选（3–4 套，不多给）

**site-kit 站**：`npm run kit:gallery -- --presets calm,precise,bold`，用站点自己的页面截三种 preset（`.sitekit/shots/gallery/index.html`）。

**ui-ux-pro-max 变体（1–2 套）**：

```bash
python3 ~/.agents/skills/ui-ux-pro-max/scripts/search.py "<产品类型> <用户> <关键词>" --design-system -p "<站名>"
python3 ~/.agents/skills/ui-ux-pro-max/scripts/search.py "<气质关键词>" --domain color -n 5
python3 ~/.agents/skills/ui-ux-pro-max/scripts/search.py "<气质关键词>" --domain typography -n 5
```

它按关键词检索，不懂审美，结果要筛：

- 工具、应用界面用浅色或站长指定的明暗，颜色克制（中性底 + 一个强调色，强调色只用在主操作、焦点、选中、状态）。
- 去掉它标 `Accessibility: risk:high` 的风格（如 Neumorphism）、正文对比度低于 4.5:1 的配色、只为营销页设计的花哨效果。
- 字体必须有 `@fontsource` 包（kit 构建不联网取字体）。
- 每套写清：名字、底色/正文/强调色 hex、标题和正文字体、圆角、密度、阴影或描边。

**landing 和 app 站**另给 2–3 种首页首屏布局（ui-ux-pro-max `--domain landing` 可参考），每种一句话：主操作在哪、产品截图或工具在哪、第一屏之下接什么。

**放到真实页面上**：

- site-kit 站：每套变体临时写进 `site.config.ts` 的 `theme.accent` / `theme.radius` / `theme.fonts` 和 `src/site/theme.css`，`npm run kit:shots`，把截图复制到 `.sitekit/shots/style/<变体名>/`，再还原。gallery 不带字体和强调色覆盖，变体只能这样截。
- 其他项目：做一个对比页，每套候选画主页面的第一屏，用真实站名和内容，不用占位文字。

## 3. 给站长挑

把截图（gallery、各变体）发给站长，站长常在手机上看。每套一行说明差别。站长可以混搭（“A 的配色 + B 的字体”）；混搭后再截一次确认。两轮都不满意，就问站长贴 2–3 个喜欢的网站，按它们重出。

## 4. 写进项目

1. **主题**：site-kit 站写 `theme.preset`、`theme.accent`、`theme.radius`、`theme.fonts`（并 `npm install` 对应 `@fontsource` 包），其余 token 写 `src/site/theme.css`；其他项目写进它自己的 CSS 变量或主题文件。
2. **PRODUCT.md `## Brand Commitments`**，让之后的 impeccable 照做、不抽签：

   ```markdown
   ## Brand Commitments
   Visual direction (owner-pinned <YYYY-MM-DD> via /ui-style; binding: build this, no concept roll):
   - World: <一句话，如 calm tool：白底、浅灰分区、细描边、克制配色>
   - Colour: strategy Restrained; ground #…, ink #…, accent #… (primary action, focus, selection, state only)
   - Type: display <字体>, body <字体>, mono <字体> (owner's pick)
   - Shape and density: radius …, density …, borders or shadows …
   - First viewport (landing/app home): <选定的首屏布局>
   - Rejected: <站长否掉的方向，一行>
   ```

3. **DESIGN.md**：调用 `impeccable` skill，`args: document`，从写好的代码生成 `DESIGN.md`。
4. **验证**：site-kit 站 `npm run check`，打开 `.sitekit/shots/` 看首页和工具页；其他项目打开主页面看一眼。确认 kit 页和首页是同一套外观。

## 结束

一句话说明定了哪套、写在哪些文件。下一步：site-kit 新站进入第 4 阶段实现；已有站点用 `/ui-critique` 看效果。
