# ChatGPT Pro Engineering Loop

让 Codex Desktop 把复杂仓库任务交给已登录的 ChatGPT Pro 外部工程师。
默认优先使用 GitHub Issue + Draft PR；基线未推送、任务依赖本地未提交源码或
GitHub 权限不足时，回退到安全 ZIP。Codex 始终负责权限、恢复和独立验收。

外部工程师强制使用底层模型 `GPT-5.6 Sol Pro`。账号显示 Pro、普通
GPT-5.6 Sol、`5.6 Sol Light`、Medium、High 或 Extra High 都不能替代该门禁。
若当前无法选择或确认 `GPT-5.6 Sol Pro`，流程会在源码打包、上传、任务发送和
GitHub 任务操作前阻塞，不会自动降级。

## 适用场景

- 明确要求“让 ChatGPT Pro 深入研究并实现这个仓库任务”
- 希望用 GitHub Issue、任务分支和 Draft PR 保留完整交付历史
- 需要在 GitHub 不可用时把源码安全打包后交给 ChatGPT Pro
- 需要保存对话链接、长时间监控、持续纠错
- 需要在本地隔离应用外部补丁并运行完整门禁

不适用于普通本地开发、简单 review、一般网页研究或登录操作。

## 安全边界

- 只有用户在初始请求中明确授权，或确认了 Codex 生成的执行契约，才允许
  ChatGPT 访问 GitHub 源码或上传源码。
- GitHub 操作按 Issue、分支、commit、push、Draft PR、评论分别列入执行契约。
- 每个 ZIP 都经过路径过滤、凭据扫描、大小检查和 SHA-256 记录。
- 每个 Draft PR 都按不可变 Base/Head SHA 和本地 diff SHA-256 验收。
- ChatGPT Pro 的结论和测试声明不直接算通过。
- 不自动 merge、force-push、删除远程分支、发布、部署、迁移、修改仓库设置
  或触碰生产数据。
- 登录、验证码、Passkey 和两步验证必须由用户亲自完成。
- 每个独立任务先建立空白对话，并依据当前 OpenAI 官方映射选择和确认
  `GPT-5.6 Sol Pro`；发送前及恢复后都会重新检查。

## 使用

```text
使用 $chatgpt-pro-engineering-loop

需求：
<用自然语言说明要实现或修复什么>
```

这就够了。Codex 会先只读检查仓库，自动补全范围、非目标、验收标准、测试、
`auto` 传输方式和本次操作权限，输出一份简洁的执行契约。此时不会修改代码、
上传源码或操作 GitHub。

确认契约没有问题后，只需回复：

```text
确认执行
```

确认只授权契约中明确列出的操作；没有列出的 merge、部署、迁移、force-push
或生产操作仍然禁止。这一次确认会建立本任务的“授权闭包”：契约内的源码打包、
ChatGPT 上传/发送/纠错/下载、Issue/分支/commit/普通 push/Draft PR/评论、
隔离验收和本地落地不再逐步询问权限。`auto` 同时预授权 GitHub 和安全 ZIP
回退时，两者之间按能力切换也不再询问。

只有仓库、账号或外部目标变化，源码暴露或修改范围扩大，引入敏感数据，产品行为、
验收标准、模型或操作权限变化，或者要执行未列出的破坏性/生产操作时，Codex 才
生成新契约并重新确认。纠错轮次、同范围重新打包、替换附件、追加提交、普通 push、
恢复原对话和重复测试不属于权限扩大。

Codex 的 Full Access 只控制本机工具的文件系统和命令沙箱，并不等于外部源码或
GitHub 授权；但执行契约一旦确认，Full Access 也不会触发第二套询问。浏览器、
GitHub 或连接器自身强制显示的原生确认框无法由 Skill 关闭；登录、验证码、
Passkey 和两步验证也仍需用户亲自完成。这些是产品或认证交接，不是重新确认契约。

如果反复出现的是 ChatGPT 连接 GitHub 或其他 App 时的产品原生提示，请检查
ChatGPT 的 `Settings > Apps`。该设置可选择始终询问、修改前询问，或仅在重要
修改前询问；希望减少提示时可由用户一次性选择“仅在重要修改前询问”。Skill
只会读取并记录当前模式，不会擅自修改账号设置。

如果已经有完整验收标准，也可以一开始一并提供，但不是必填项。只有重大产品
方向、外部数据暴露、不可逆操作或权限扩大需要继续询问；普通实现选择由 Codex
提出推荐默认值。

使用前应已经在 Codex 内置浏览器中登录 ChatGPT Pro，并且账号当前能够选择
`GPT-5.6 Sol Pro`。界面可能显示 `Pro Extended`、`Pro Standard` 或 `Pro`；
只有当前 OpenAI 官方文档仍将该标签映射到 `GPT-5.6 Sol Pro` 时才可使用。
如果 Work 界面只提供 `5.6 Sol Extra High`，但 Chat 界面提供合规的 `Pro`，
应切换到 Chat/Pro；Extra High 不能因为位于 Work 界面而视为 Pro。

## 传输模式

默认 `auto`，按以下顺序选择：

1. `github-pr`：基线已在远程、任务不依赖本地脏源码、ChatGPT 写能力已验证，
   且 Issue/分支/commit/push/Draft PR/评论全部得到本次授权。
2. `github-issue-patch`：ChatGPT 只有 GitHub 读取能力，使用 Issue 作为任务合同，
   代码仍以补丁返回。
3. `bundle`：GitHub 条件不满足，但本次允许上传安全源码包。

```bash
python3 scripts/select_transport.py \
  --repo /path/to/repo \
  --requested auto \
  --chatgpt-github-access write \
  --allow-github-source-access \
  --allow-create-issue \
  --allow-create-branch \
  --allow-commit \
  --allow-push \
  --allow-create-pr \
  --allow-comment \
  --allow-bundle-upload
```

脚本只读取本地 Git 状态并输出 JSON 决策，不创建真实 GitHub 资源。运行前应先
更新远程跟踪引用；脚本不会把远程 URL 写入输出，避免泄露 credential-bearing
URL。

任务依赖本地未提交源码时，应传入 `--task-needs-local-dirty`，此时
`auto` 会回退到 `bundle`，不会擅自创建 WIP commit。

执行契约通常会建议以下 GitHub 权限；用户无需手工复制：

```text
允许：一个任务 Issue、codex/chatgpt-pro/<task-id> 分支、任务提交和普通 push、
一个 Draft PR、任务相关评论。

禁止：merge、force-push、删除远程分支、Release、部署、仓库设置、Actions、
Secrets、环境、迁移和生产数据。
```

GitHub 详细约束见
[github-transport-protocol.md](./references/github-transport-protocol.md)。

## 源码打包脚本

```bash
python3 scripts/prepare_bundle.py \
  --repo /path/to/repo \
  --output-dir ~/.codex/chatgpt-pro-runs/example/run-id/source \
  --task-id task-001 \
  --include src \
  --include tests \
  --include package.json \
  --include package-lock.json
```

成功后输出 JSON 摘要，并生成：

- `<repo>-<task>-source-<commit>.zip`
- 同名 `.manifest.json`
- 同名 `.sha256`

该脚本只用于 `bundle` 模式。发现疑似凭据或超过默认 50 MiB 软上限时不会生成 ZIP。默认还会排除
NUL-containing binary（包括图片和字体）；需要二进制资产的任务必须走单独、
窄范围且明确授权的交接流程。

## 验证

```bash
python3 -m unittest discover -s chatgpt-pro-engineering-loop/tests -v
```

行为验证记录见 [VALIDATION.md](./VALIDATION.md)。

真实浏览器冒烟使用无私有源码的临时 Git fixture：

```bash
python3 scripts/create_smoke_fixture.py --output-dir /persistent/run/fixture
```

自动化 GitHub 选择测试使用本地 bare remote，不创建真实 Issue、分支或 PR。
