# myskills

我的 Claude Code / Codex Skills 集合。每一个子目录都是一个独立的 skill，遵循官方 skill 规范（包含 `SKILL.md` + 可选 `scripts/` / `references/` / `assets/`）。

## 当前 Skills

| Skill | 描述 |
| --- | --- |
| [prompt-builder-agent-skill](./prompt-builder-agent-skill) | 把模糊、随意、不完整的需求，通过引导式提问和合理默认值，转换为高质量的结构化 prompt |

## 一键安装（推荐：用 prompt 让 Claude Code 帮你装）

把下面这段 prompt 粘贴给 Claude Code（或任何能执行 shell 的 agent），把 `<SKILL_NAME>` 替换成上表里的 skill 目录名即可：

```text
请帮我安装这个 Claude Skill：

- 仓库：https://github.com/flreey/myskills
- Skill 名：<SKILL_NAME>

执行步骤：
1. 确保 ~/.claude/skills/ 目录存在（不存在则创建）
2. 把仓库中 <SKILL_NAME>/ 这个目录完整下载到 ~/.claude/skills/<SKILL_NAME>/
   推荐做法：用 git sparse-checkout 只拉取该子目录，避免下载整个仓库
3. 验证 ~/.claude/skills/<SKILL_NAME>/SKILL.md 存在，并且 YAML frontmatter 中的 name / description 字段完整
4. 安装完成后，告诉我这个 skill 的触发条件（即什么样的请求会激活它）
```

Claude Code 会按上述步骤自动完成下载、放置、校验。

## 手动安装

```bash
# 克隆整个仓库
git clone https://github.com/flreey/myskills.git
cp -R myskills/<SKILL_NAME> ~/.claude/skills/

# 或者只拉取某个 skill 目录（sparse-checkout）
git clone --filter=blob:none --sparse https://github.com/flreey/myskills.git
cd myskills
git sparse-checkout set <SKILL_NAME>
cp -R <SKILL_NAME> ~/.claude/skills/
```

安装完成后重启 Claude Code（或在新会话里）skill 即可被自动发现。

## 目录结构约定

```
<skill-name>/
├── SKILL.md          # 必需，包含 YAML frontmatter（name + description）
├── README.md         # 可选，给人看的说明
├── AGENTS.md         # 可选，给 Codex 等 agent 看的使用说明
├── scripts/          # 可选，本地脚本
├── references/       # 可选，长文档/参考资料
└── assets/           # 可选，模板/图片等
```

## 添加新 Skill

1. 在仓库根目录新建一个 `<skill-name>/` 文件夹
2. 至少放一个带 frontmatter 的 `SKILL.md`
3. 在本 README 的 "当前 Skills" 表格中添加一行
4. 提交 PR 或直接 push

## License

MIT
