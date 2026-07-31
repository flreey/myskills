# ChatGPT Pro Engineering Loop

让 Codex Desktop 管理仓库和验收，让已登录的 ChatGPT Pro 负责开发，并通过
GitHub 任务分支交换代码。

默认分工：

- Codex：检查本地仓库、补全验收标准、创建任务分支和 Draft PR、监控 head、
  独立测试、反馈缺陷和最终报告。
- ChatGPT Pro：读取指定仓库，研究、设计并向指定任务分支提交代码。
- GitHub：保存基线、任务 commit、Draft PR、CI 和审查证据。
- 用户：确认一次执行方案，并处理登录、GitHub 原生授权以及任何生产权限。

2026-07-31 已在 `flreey/myskills` 真实验证：ChatGPT 的 Chat/Pro
（底层 `GPT-5.6 Sol Pro`）通过 GitHub 插件创建了独立分支和普通 commit；
Codex 随后独立回读并核对了分支、commit、文件和主分支状态。该证明不能自动
外推到另一个账号或仓库，但后续任务不需要重复创建烟雾分支。

## 使用

```text
使用 $chatgpt-pro-engineering-loop

需求：
修复支付回调的幂等问题
```

用户不需要自己填写测试、权限矩阵或完整验收标准。Codex 会先只读检查仓库，
生成一份 20–35 行的执行契约。确认后回复：

```text
确认执行
```

这一次确认覆盖契约内的分支、任务 commit、Draft PR、浏览器沟通、纠错、
fetch、隔离验收和测试，不再逐步重复询问。不同仓库、数据或修改范围、产品行为、
密钥等级、模型、权限或生产操作仍需重新确认。

Codex Full Access 只影响本地沙箱。ChatGPT/GitHub 的原生确认是独立的产品
权限。个人使用建议在每个任务会话第一次提示时选择
`Allow GitHub for this conversation`，既避免同一任务反复提示，也不自动扩大为
长期全局授权。Skill 不会代替用户选择账号级权限。

## 正常 GitHub 流程

1. Codex 读取仓库规则、源码、测试和本地 Git 状态。
2. 用户确认一次执行契约。
3. Codex 在空白 Chat 会话中确认模型为 `GPT-5.6 Sol Pro`。
4. 快速预检本地基线、目标仓库权限和 Pro 写能力。
5. Codex 从精确 base SHA 创建 `codex/chatgpt-pro/<task-id>`。
6. Pro 只向该分支追加任务 commit。
7. 第一个有效 commit 出现后，Codex 创建 Draft PR。
8. Codex fetch 精确 head，在 detached worktree 审查和测试。
9. 缺陷证据发回同一 Pro 对话，Pro 追加修正 commit。
10. 全部通过后停在已验证 Draft PR；默认不 merge、不部署。

Issue 默认不创建。只有任务追踪确实有价值且执行契约明确列出时才使用。

## 快速传输判断

```bash
python3 scripts/select_transport.py \
  --repo /path/to/repo \
  --requested auto \
  --pro-github-access write \
  --manager-github-access write \
  --native-auth-state ready \
  --allow-github-collaboration \
  --allow-handoff-branch \
  --allow-bundle-upload
```

输出决策：

- `READY_GITHUB`：远端基线可用，直接 GitHub 协作；
- `READY_HANDOFF_BRANCH`：任务需要本地 dirty 源码，且精确范围已通过扫描并允许发布；
- `READY_BUNDLE`：使用脱敏 ZIP/patch；
- `BLOCKED_AUTH`：等待用户处理原生 GitHub 授权；
- `BLOCKED`：没有安全且已授权的通道。

旧参数 `--chatgpt-github-access` 仍是 `--pro-github-access` 的兼容别名；
旧 transport 名 `github-pr` 暂时映射为 `github`；已经废弃的
`github-issue-patch` 安全降级为 `bundle`，不再隐式创建 Issue。

## 本地未提交源码

无关 dirty 文件不会阻止 GitHub 正常路径。

任务确实依赖 dirty 源码时：

- 允许发布到 GitHub：先用 bundle scanner 扫描精确路径，再在隔离 worktree
  中按 manifest 重建和校验，提交到 handoff 分支；不改当前 dirty worktree。
- 不允许发布：上传经过扫描的最小 ZIP/patch。

禁止为了方便直接在用户当前分支创建 WIP commit。

## Key、Token 和真实服务

密钥值永远不能进入 ChatGPT、Git、Issue、PR、评论、附件或证据日志。

任务先分级：

| 等级 | 处理 |
|---|---|
| `none` | 正常开发 |
| `interface-only` | 只给 Pro 环境变量名、类型、公开文档和脱敏 fixture |
| `local-test` | Pro 写代码，Codex 在完整 diff 审查后本地注入开发/沙箱 Key |
| `ci-test` | 需要额外授权的 GitHub Secret/Environment 和受保护 CI |
| `production` | 标准流程阻塞，必须建立新的生产执行契约 |

Pro 不需要真实 Key 才能实现配置接口、mock 和大多数单元测试。真实集成由 Codex
在本地或受控 CI 中完成，失败时只向 Pro 返回脱敏证据。

若 Pro 修改 workflow、脚本或任何可执行路径，在完整审查前不得让该 head 获得
Secrets。云服务支持时优先使用 OIDC 短期凭据。

详细规则见
[secrets-and-live-validation.md](./references/secrets-and-live-validation.md)。

## Bundle

只有 GitHub/hand-off 不适用时才运行：

```bash
python3 scripts/prepare_bundle.py \
  --repo /path/to/repo \
  --output-dir ~/.codex/chatgpt-pro-runs/example/run-id/source \
  --task-id task-001 \
  --include src \
  --include tests
```

脚本生成 deterministic ZIP、manifest 和 SHA-256。发现疑似凭据、危险路径、
非授权二进制或超过默认 50 MiB 软上限时失败关闭。

## 验证

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 -m unittest discover -s chatgpt-pro-engineering-loop/tests -v
```

行为验证记录见 [VALIDATION.md](./VALIDATION.md)。
