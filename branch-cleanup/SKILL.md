---
name: branch-cleanup
description: 把当前 git 项目收拢到只剩 main：盘点本地分支、远端分支和 worktree，已合并的删掉，能快进或无冲突合并且是完成的工作就合进本地 main，合不了或拿不准的打 archive/<branch> 标签再删，删 worktree，最后核对没有丢提交并汇报是否需要推送。用于“清理分支”“合并所有分支”“只留 main / 只保留 main”“删 worktree / 清 worktree”“收拾一下分支和会话”。不用于单个分支的普通合并、发 PR、改写历史或清理远端仓库。
---

# Branch Cleanup

目标状态：本地只剩 base 分支（通常是 `main`）和它所在的主 worktree；每个原来的提交仍能从 `main` 或某个 tag 找到；不推送、不碰远端。

脚本 `scripts/branch_cleanup.py` 只读，提供 `inventory`、`snapshot`、`verify` 三个子命令。下面用 `BC` 指代 `python3 <本 skill 目录>/scripts/branch_cleanup.py`。

## 安全边界（每一步都适用）

- **不推送、不删远端。** 不 `git push`、不 `push --force`、不 `push --delete`、不推 tag，除非用户在本轮明确要求。远端分支只汇报。
- **只用 git 删 worktree。** 用 `git worktree remove <path>`（不加 `--force`）和 `git worktree prune`。不对 worktree 目录 `rm -rf`；有的项目把 `rm` 别名成 `echo`，看似删了其实没删。worktree 里的 `node_modules`、`data/*.json`、`.env`、`.venv` 常是指向主仓库的软链：不在 worktree 里跑 `npm ci` / `npm install` / `pip install`，不 `rm -r` 任何软链或软链所在目录；要单独去掉一个软链用 `unlink <path>`，先 `ls -l` 确认它是链接。
- **不用宽泛的 `pkill` / `killall`。** 要停的进程按 PID 逐个确认：`ps -o pid,command -p <PID>` 加 `lsof -a -p <PID> -d cwd` 看 cwd 在要删的 worktree 里，再 `kill <PID>`。Claude / Codex 会话的进程不由本 skill 停，交给用户。
- **不跳过钩子。** 提交、合并、推送都不加 `--no-verify`。
- **破坏性动作前有快照。** 第 1 步的快照在整个任务中保留，第 7 步用它核对。

## 步骤

### 1. 盘点并留快照

在主 worktree（base 分支所在目录）里执行：

```bash
git fetch origin --quiet || echo "fetch failed, using cached origin refs"
BC snapshot --out "<scratchpad>/branch-cleanup-snapshot.json"
BC inventory            # 加 --json 拿结构化结果
```

`inventory` 给出每个本地分支相对 base 的状态：

| state | 含义 | 默认动作 |
| --- | --- | --- |
| `merged` | 提交已全部在 base 里 | `git branch -d` |
| `ff` | base 落后、分支只领先，可快进 | 是完成的工作就 `merge --ff-only`，否则归档 |
| `clean` | 双方都有新提交，`git merge-tree` 预演无冲突 | 是完成的工作就 `merge --no-ff`，否则归档 |
| `equivalent` | 提交不在 base 里，但合并后内容不变（已 squash/cherry-pick 过） | 归档标签后删除 |
| `conflict` | 预演有冲突（列出冲突文件） | 归档标签后删除，不在本 skill 里解冲突 |

每个 worktree 会标出：`DIRTY`（staged / unstaged / untracked 计数）、`LOCKED`、`PRUNABLE`、`DETACHED` 及其 HEAD 状态、`CURRENT SHELL IS HERE`、是否像 agent 会话 worktree（路径含 `/.claude/worktrees/` 或有 claude 进程）、cwd 在里面的进程、指向外部的软链、会随 worktree 一起删掉的被忽略文件（`.env`、私有数据等，不含 `node_modules` 这类可重建缓存）、最近一次 git 活动时间。还会列出远端分支状态、stash 数量、已有的 `archive/*` 标签，以及 base 相对 `origin/<base>` 的超前/落后。

此时跑一次 `BC verify --snapshot ...` 也有用：它列出的 `LOST` 项就是只靠 worktree HEAD 或即将删除的分支持有的提交，第 5 步必须给它们打标签。

完成条件：每个本地分支、每个 worktree、每个远端分支都在盘点里出现，并有状态。

### 2. 定计划，一次确认

逐个分支给出动作，写成一张表给用户：`分支 | 状态 | 最后提交 | 动作（删 / 快进 / 合并 / 归档） | 理由`，worktree 另列 `路径 | 分支 | 情况 | 动作`。

判断“是不是完成的工作、该不该合”：

- 读 `git log --oneline <base>..<branch>` 和 `git diff --stat <base>...<branch>`。提交信息像完成的功能或修复、改动范围和它说的一致、没有 WIP / 实验 / 临时脚本 → 可合。
- 以下任一情况算“拿不准”，归档不合：分支落后 base 很多且动到了 base 之后被改过的文件；看起来是实验、草稿、已被别的方案取代；提交里混有大文件、密钥、生成物；用户或项目文档说过它在等某个日期再决定。
- 合进 main 会触发部署的项目（push main 即上线），合并本身不推送，但要在计划里写明“推送后会部署哪些改动”。

需要用户先决定的情况，在同一次确认里一起问，不分批：

- **worktree 有未提交改动（DIRTY）**：停下来问。选项：在该 worktree 里提交到它的分支后按分支规则处理 / 保留这个 worktree 不动 / 用户明确同意后丢弃。未得到答复前，不动这个 worktree 和它的分支。
- **worktree 正被使用**：有 cwd 在里面的进程、是 agent 会话 worktree、最近几小时内有 git 活动、或 `LOCKED`。问用户这个会话是否已结束；能查会话列表时（如 Claude 桌面端的会话管理工具）先查它对应哪个会话。没确认就跳过。
- **当前 shell 就在要删的 worktree 里**：先回到主 worktree（Claude Code 用 `EnterWorktree` 进入的会话要先退出 worktree），否则跳过。
- **主 worktree 不在 base 分支上，或主 worktree 有未提交改动**：不在脏的主 worktree 上合并。问用户：先由用户处理 / 只做删除和归档、不做合并。
- **base 落后 `origin/<base>`**：计划里先 `git merge --ff-only origin/<base>`；若 base 和 origin 已分叉，停下来问，不 rebase、不 reset。
- **被忽略但有价值的文件**（`.env`、`private/`、实验产物）会随 worktree 删除：列出来，问是否先挪到主仓库（挪的位置用 `.git/info/exclude` 排除，不进 git）。

用户已经说了“直接执行”“不用问”时，只对上面这些需要决定的项提问，其余照计划执行。确认覆盖表里所列的全部动作；执行中出现表外情况（意外冲突、测试失败、新的脏 worktree）再停。

完成条件：每一行都有用户认可的动作，或因无答复标为“跳过”。

### 3. 合并到本地 main

在主 worktree 里、base 分支上、工作区干净时执行。每合一个就重新看下一个的状态（前一个合进去后，原本 `ff` 的可能变成 `clean` 或 `conflict`）：

```bash
git -C <main-worktree> switch <base>
git merge --ff-only <branch>                 # state=ff
git merge --no-ff --no-edit <branch>         # state=clean
```

意外冲突时 `git merge --abort`，该分支改为归档。合并让 pre-merge-commit 等钩子照常运行。

**永远先合进本地 main，再从 main 推送；不从 worktree 直推 `HEAD:main`。**

完成条件：计划中要合的分支都满足 `git merge-base --is-ancestor <branch> <base>`，或已改为归档并记录原因。

### 4. 跑项目要求的测试

有合并（包括快进）时，在主 worktree 跑一次项目规定的检查：按 `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING` / `package.json` / `Makefile` / `.githooks` 或 `core.hooksPath` 里的 pre-commit 钩子确定命令；项目要求提交前跑什么就跑什么，不额外扩大。只跑一次最终状态，不每合一个跑一次。依赖缺失时只在主 worktree 安装，安装前确认 `node_modules` 等不是软链（`[ -L node_modules ]`）。

测试失败：停下，不删任何东西。报告失败输出，问用户是修复，还是把 base 退回第 1 步快照里的 `base_sha`（`git reset --keep <base_sha>`，需用户明确同意）。

完成条件：测试通过，或已按用户决定处理。

### 5. 给保留不了的提交打归档标签

对每个不会成为 base 祖先的分支（`equivalent`、`conflict`、拿不准的 `ff`/`clean`）和每个 HEAD 不在 base 里的 detached worktree：

```bash
git tag -a "archive/<branch>" <branch> -m "archived by branch-cleanup <YYYY-MM-DD>: <state>, <reason>"
# 已有同名且指向别处的标签时用 archive/<branch>-<短sha>
# detached worktree：archive/detached-<worktree目录名>-<短sha>
git rev-parse "archive/<branch>^{commit}"     # 必须等于分支 tip
```

完成条件：每个要删除的非祖先分支都有一个标签，且标签指向的提交与分支 tip 相同。

### 6. 删 worktree，再删分支

按计划逐个处理 worktree：

```bash
git worktree list --porcelain                 # 再看一眼：仍不是 DIRTY、没被锁
git -C <wt> status --porcelain                # 必须为空
git worktree remove <wt>                      # 不加 --force；报错就停下看原因
```

`git worktree remove` 只删链接本身，不会跟着软链删主仓库的文件；删前后可以 `ls -l` 软链指向的目标确认它还在。它**不会**因为被忽略的文件（`.env`、`data/`、私有产物）拒绝，会直接删掉，所以第 2 步列出的这类文件必须在这一步之前处理完。删除报“contains modified or untracked files”说明出现了新改动，回到第 2 步问用户。被 `LOCKED` 的只有用户同意后才 `git worktree unlock`。最后 `git worktree prune`。

然后删分支（在主 worktree、base 分支上）：

```bash
git branch -d <branch>     # merged / 已合入的分支
git branch -D <branch>     # 仅限已在第 5 步打好标签、且标签 sha 等于 tip 的分支
```

完成条件：`git branch` 只剩 base（加上用户决定保留的），`git worktree list` 只剩主 worktree（加上用户决定保留的）。

### 7. 核对没有丢提交

```bash
BC verify --snapshot "<scratchpad>/branch-cleanup-snapshot.json"
```

输出 `ok` 才算完成。出现 `LOST` 时，用快照里的 sha 立刻补一个 `archive/...` 标签（提交对象还在 reflog 和对象库里），再跑一次 verify。

### 8. 汇报

用中文，结论先行：

- **合进 main**：分支 → 合并方式（快进 / 合并提交）→ 新 main sha。
- **删除**：分支名 + 删除前 tip sha；worktree 路径。
- **归档标签**：`archive/*` 名称、sha、理由；提醒用户旧代码用 `git tag -l 'archive/*'` 找回，标签只在本地。
- **跳过 / 保留**：项目和原因（脏改动、会话在用、用户未答复）。
- **远端**：列出远端分支状态，说明没删；如有仅在远端、未合并的分支要特别指出。
- **测试**：跑了什么命令、结果。
- **推送**：`git rev-list --left-right --count origin/<base>...<base>` 的超前/落后数；超前时说明“需要推送才会同步（以及是否触发部署）”，但不推送。用户要求推送时，从主 worktree 普通 `git push origin <base>`，让 pre-push 钩子照常运行。
- `verify` 的结果。

## 演练

改动本 skill 后，用 `scripts/drill_setup.sh <空目录>` 建一个覆盖全部情况的临时仓库（已合并、可快进、无冲突分叉、冲突、squash 过、WIP 实验、带软链和 `.env` 的 worktree、脏 worktree、detached worktree、仅远端分支、stash、pre-commit 钩子），按上面步骤走一遍；记录见 `VALIDATION.md`。
