# myskills

我的 Claude Code / Codex CLI Skills 集合。每一个子目录都是一个独立的 skill，遵循通用的 `SKILL.md` 标准（YAML frontmatter + 自然语言指令 + 可选 `scripts/` / `references/` / `assets/`）。同一个 skill 包，Claude Code 和 Codex CLI 都能直接用。

## 当前 Skills

| Skill | 描述 |
| --- | --- |
| [prompt-builder-agent-skill](./prompt-builder-agent-skill) | 把模糊、随意、不完整的需求，通过引导式提问 + 合理默认值 + 自评 + 模型适配，转换为高质量的结构化 prompt。覆盖 image / product / writing / code / business / research / agent 七大类型。 |

## 一键安装（推荐：让你的 agent 自己装）

把下面这段 prompt 粘给 Claude Code **或** Codex CLI（两边都能用），把 `<SKILL_NAME>` 换成上表里的 skill 目录名：

```text
请帮我安装这个 Skill：

- 仓库：https://github.com/flreey/myskills
- Skill 名：<SKILL_NAME>

请按以下步骤执行（自动判断当前是 Claude Code 还是 Codex CLI）：

1. 确定目标安装目录：
   - 如果你是 Claude Code，目标是 ~/.claude/skills/<SKILL_NAME>/
   - 如果你是 Codex CLI，目标是 ~/.codex/skills/<SKILL_NAME>/
   - 父目录不存在则创建（mkdir -p）

2. 用 git sparse-checkout 只下载这一个 skill 子目录，避免拉整仓库：
   - mktemp -d 一个临时目录
   - cd 进去，git clone --filter=blob:none --sparse https://github.com/flreey/myskills.git
   - cd myskills && git sparse-checkout set <SKILL_NAME>
   - 把 <SKILL_NAME>/ 完整 cp -R 到上一步的目标目录
   - 清理临时目录

3. 校验 <目标目录>/SKILL.md 存在，且 YAML frontmatter 含 name + description 字段。

4. 安装完成后，告诉我：
   - 安装到了哪个路径
   - 这个 skill 的触发条件（即什么样的请求会激活它）
   - 是否需要重启会话才能识别
```

## 手动安装

```bash
# 方式 1：克隆整仓库再复制
git clone https://github.com/flreey/myskills.git
cp -R myskills/<SKILL_NAME> ~/.claude/skills/   # Claude Code
cp -R myskills/<SKILL_NAME> ~/.codex/skills/    # Codex CLI

# 方式 2：sparse-checkout 只拉一个 skill
git clone --filter=blob:none --sparse https://github.com/flreey/myskills.git
cd myskills
git sparse-checkout set <SKILL_NAME>
cp -R <SKILL_NAME> ~/.claude/skills/   # 或 ~/.codex/skills/
```

项目级安装：把 skill 目录复制到仓库的 `.claude/skills/` 或 `.codex/skills/`（Codex 也支持 `.agents/skills/`）。

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

1. 在仓库根目录新建 `<skill-name>/`
2. 至少放一个带 frontmatter 的 `SKILL.md`
3. 在本 README 的 "当前 Skills" 表格中加一行
4. push（或开 PR）

## License

MIT
