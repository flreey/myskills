# myskills

我的 Claude Code / Codex CLI Skills 集合。每一个子目录都是一个独立的 skill，遵循通用的 `SKILL.md` 标准（YAML frontmatter + 自然语言指令 + 可选 `scripts/` / `references/` / `assets/`）。同一个 skill 包，Claude Code 和 Codex CLI 都能直接用。

## 当前 Skills

| Skill | 描述 |
| --- | --- |
| [prompt-builder-agent-skill](./prompt-builder-agent-skill) | 把模糊、随意、不完整的需求，通过引导式提问 + 合理默认值 + 自评 + 模型适配，转换为高质量的结构化 prompt。覆盖 image / product / writing / code / business / research / agent 七大类型。 |

## 📋 一键安装（复制下面整段 prompt 粘给你的 agent 即可）

适用于 Claude Code、Codex CLI、以及任何能执行 shell 的 coding agent。**直接复制，不用改任何东西。**

### prompt-builder-agent-skill

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

> 要装到**项目内**而不是全局？把第 1 步路径改成 `<repo>/.claude/skills/` 或 `<repo>/.codex/skills/` 即可。

## 手动安装（不想让 agent 代劳）

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

安装后开新会话，agent 会通过 `SKILL.md` 的 frontmatter 自动发现。

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
2. 在本 README 的 "当前 Skills" 表格里加一行
3. 在 "📋 一键安装" 区里复制 `prompt-builder-agent-skill` 那段 prompt，把所有 `prompt-builder-agent-skill` 替换成新 skill 的目录名
4. push（或开 PR）

## License

MIT
