# skill-forge 构建计划

计划文件：~/.claude/plans/declarative-knitting-lerdorf.md

## Checklist

- [x] RED：baseline 测试（场景 A forge 类 / 场景 B bootstrap 类，不带 skill），逐字记录失败模式 → tasks/baseline-notes.md
- [x] GREEN：写 SKILL.md + 4 个 references/（针对 baseline 暴露的失败）
- [x] 验证：同场景带 skill 重跑，预登记 delta 全部命中（两场景均含访谈门禁/搜索/分诊/自主验证）
- [x] Codex 冒烟：codex exec 读 skill 后停在访谈门禁、列 6 问、自研先行 → 通过
- [x] REFACTOR：把"非交互时显式假设表"固化进 forge-protocol Step 2
- [x] 注册：README 表格 + 一键安装段；自检通过（description 444 字符、目录名==name、工具名零泄漏）
- [x] git commit

## 结果回顾

- 交付：skill-forge/（SKILL.md + 4 references + VALIDATION.md），已注册进 README
- 全程按 writing-skills 的 RED-GREEN-REFACTOR 跑，skill-forge 用自己的 validation-protocol 验证了自己
- baseline 最有价值的发现：agent 明知验证方法论也会原话绕过（"社区已验证""以后踩坑再补"）→ 这两条原话进了 rationalization 表
- 意外发现 1：codex exec 新版已无 -a 参数，cross-cli-review skill 的调用模板过时（另开任务处理）
- 意外发现 2：用户机器上有真实 Cocos 工程 ../cocos/Relight（Creator 3.8.8），场景 A 产出的 cocos-serialized-asset-guard 草案可直接用 forge 模式正式落地
- 已知局限：测试环境带 superpowers 上下文（对照组相同，比较有效），裸环境合规性未测
