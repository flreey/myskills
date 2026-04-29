# myskills

我的 Claude Code / Codex CLI Skills 集合。每一个子目录都是一个独立的 skill，遵循通用的 `SKILL.md` 标准（YAML frontmatter + 自然语言指令 + 可选 `scripts/` / `references/` / `assets/`）。同一个 skill 包，Claude Code 和 Codex CLI 都能直接用。

## 当前 Skills

| Skill | 描述 |
| --- | --- |
| [prompt-builder-agent-skill](./prompt-builder-agent-skill) | 把模糊、随意、不完整的需求，通过引导式提问 + 合理默认值 + 自评 + 模型适配，转换为高质量的结构化 prompt。覆盖 image / product / writing / code / business / research / agent 七大类型。 |

## 📋 一键安装（直接复制粘贴）

把下面这行粘给 Claude Code 或 Codex CLI，agent 会自动识别 skill 子目录、选对应平台路径、用 sparse-checkout 拉下来：

```text
帮我装这个 skill：https://github.com/flreey/myskills/tree/main/prompt-builder-agent-skill
```

> **就这一行。** 现代 coding agent 已经原生理解 GitHub `tree/main/<subdir>` 这种子目录 URL + `SKILL.md` 标准 + skills 目录约定，不需要手把手写步骤。
>
> 如果你的 agent 比较笨 / 是旧版本 / 在受限环境，用下面的[详细兜底版](#详细安装-prompt兜底版)。

### 装到项目内（不是全局）

```text
帮我把这个 skill 装到当前项目内（.claude/skills/ 或 .codex/skills/）：
https://github.com/flreey/myskills/tree/main/prompt-builder-agent-skill
```

## 装好后如何启动

1. **开新会话** — 当前会话不会重新扫描 skills 目录，必须新开。
2. **自动发现** — 新会话启动时，Claude Code / Codex 会扫描 `~/.claude/skills/` 或 `~/.codex/skills/`，把每个 skill 的 `name + description` 注入到系统上下文。
3. **触发方式** — 任选其一：
   - **自然语言**：发出符合 description 的请求，例如：
     - "帮我把这个想法变成 prompt"
     - "我想做个 X，整理成可以发给 Claude 的 prompt"
     - "我要画一张画，帮我写图片 prompt"
   - **显式调用**：直接说 `用 prompt-builder skill ...` 或在 Claude Code 输入 `/prompt-builder`
4. **验证装好了** — 新会话里问 agent："你看到 prompt-builder 这个 skill 了吗？" 它能回答出 description 就说明装对了。

## 与 superpowers 等其他 skill 共存

`prompt-builder` 跟 `superpowers:brainstorming` 这类 skill **职能不同**，理解清楚就不会混淆：

| Skill | 输入 | 输出 | 用途 |
| --- | --- | --- | --- |
| `superpowers:brainstorming` | 模糊想法 | **设计文档 + spec** | 探索需求 → 写代码 |
| `prompt-builder` (本仓库) | 模糊想法 | **可复制的 LLM prompt** | 发给另一个 LLM 执行 |

**冲突场景与处理**：
- 名字不会冲突（`prompt-builder` 没有 `superpowers:` 前缀，独立命名空间）。
- description 触发条件**有重叠**——都会接"模糊请求"。Agent 会自己选最匹配的；如果选错，**显式说**：
  - 想要 prompt：`用 prompt-builder 帮我...`
  - 想要 design doc：`用 brainstorming 帮我...`
- 想暂时禁用 superpowers 的某个 skill，可在 `~/.claude/settings.json` 或 `~/.codex/config.toml` 里 disable，无需卸载。

## 手动安装（不用 agent）

```bash
# 方式 1：克隆整仓库再复制
git clone https://github.com/flreey/myskills.git
cp -R myskills/prompt-builder-agent-skill ~/.claude/skills/   # Claude Code
cp -R myskills/prompt-builder-agent-skill ~/.codex/skills/    # Codex CLI

# 方式 2：sparse-checkout 只拉一个 skill
git clone --depth=1 --filter=blob:none --sparse https://github.com/flreey/myskills.git
cd myskills
git sparse-checkout set prompt-builder-agent-skill
cp -R prompt-builder-agent-skill ~/.claude/skills/   # 或 ~/.codex/skills/
```

## 平台对照

| 平台 | 个人路径 | 项目路径 | 配置文件 |
| --- | --- | --- | --- |
| Claude Code | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/skills/<name>/` | `.codex/skills/<name>/` 或 `.agents/skills/<name>/` | `~/.codex/AGENTS.md` |

## 目录结构约定

```
<skill-name>/
├── SKILL.md          # 必需，YAML frontmatter（name + description）+ 指令正文
├── README.md         # 可选，给人看的说明
├── AGENTS.md         # 可选，给 Codex 的额外提示
├── scripts/          # 可选，CLI 脚本
├── references/       # 可选，长文档 / 模板 / 参考资料（按需加载）
└── assets/           # 可选，模板 / 图片
```

## 添加新 Skill

1. 在仓库根目录新建 `<skill-name>/`，至少放一个带 frontmatter 的 `SKILL.md`
2. 在 "当前 Skills" 表格加一行
3. 在 "📋 一键安装" 那段把 `prompt-builder-agent-skill` 替换成新 skill 名复制一份
4. push（或开 PR）

## 详细安装 Prompt（兜底版）

如果一行 URL 那种简洁 prompt 在你的 agent 上没起作用（比如 agent 不懂 GitHub URL 解析、或环境受限），用这一段把每一步写死：

````text
请帮我从 GitHub 安装并启用 prompt-builder-agent-skill 这个 skill。仓库地址 https://github.com/flreey/myskills

请按以下步骤执行（你需要自动判断当前是 Claude Code 还是 Codex CLI 或其他 agent，并选用对应路径）：

1. 确定目标安装目录：
   - Claude Code → ~/.claude/skills/prompt-builder-agent-skill/
   - Codex CLI   → ~/.codex/skills/prompt-builder-agent-skill/
   - 其他 agent  → 询问我目标目录
   父目录不存在就 mkdir -p。如果目标目录已存在，备份成 <name>.bak.<timestamp> 再继续。

2. 用 git sparse-checkout 只拉这一个 skill 子目录（避免下载整仓库）：
   - 创建一个临时目录（mktemp -d）
   - 在临时目录里：git clone --depth=1 --filter=blob:none --sparse https://github.com/flreey/myskills.git
   - cd myskills && git sparse-checkout set prompt-builder-agent-skill
   - 把 prompt-builder-agent-skill/ 完整 cp -R 到第 1 步确定的目标目录
   - 删掉临时目录

3. 校验：
   - <目标目录>/SKILL.md 存在
   - YAML frontmatter 含 name 和 description 字段
   - references/templates/ 下有 7 个 .md 模板文件

4. 安装完成后，告诉我：
   - 实际安装路径
   - 这个 skill 的触发条件（哪些请求会激活它）
   - 是否需要重启会话才能识别

如果任何一步失败，停下来报告错误，不要静默继续。
````

## License

MIT
