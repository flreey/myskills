# branch-cleanup 演练记录

## 2026-11-10 首次演练

环境：macOS，git 2.46.2，Python 3.11。仓库由 `scripts/drill_setup.sh` 生成（bare `origin.git` + `repo` + 3 个 worktree），一个 `sleep` 进程的 cwd 在 `wt-done` 里。

| 步骤 | 结果 |
| --- | --- |
| 1 盘点 | 8 个分支状态全部识别正确：merged、ff×4（含两个 worktree 分支和 WIP 实验）、clean、conflict（列出 `app.txt`）、equivalent（cherry-pick 过）；worktree 标出 DIRTY（unstaged 1、untracked 1）、detached HEAD（+1）、cwd 进程 PID、两个指向主仓库的软链、会被删掉的 `.env`；远端 `origin/feat/remote-only`、stash 1 条。快照 14 个 tip。清理前 `verify` 报 detached HEAD 为 LOST，符合预期。 |
| 3 合并 | `feat/ff` 快进后重查，`feat/wt-done` 从 ff 变成 clean（`--ff-only` 被拒），改用 `--no-ff` 合并；`feat/clean` 合并。三者均为 main 的祖先。 |
| 4 测试 | 项目 `./test.sh` 通过。脏 worktree 提交时 pre-commit 钩子照常运行。 |
| 5 归档 | 5 个标签（`exp/wip`、`feat/conflict`、`feat/squashed`、`feat/wt-dirty`、detached HEAD），每个 sha 与 tip 一致。 |
| 6 删除 | 按 PID + cwd 确认后 `kill` 单个进程；3 个 worktree 均用无 `--force` 的 `git worktree remove` 删除；软链目标 `node_modules/pkg/index.js`、`data/catalog.json` 仍在；被忽略的 `.env` 被一并删除（未报错）——已写进 SKILL.md。8 个分支删除（4 个 `-d`，4 个核对标签后 `-D`）。 |
| 7 核对 | `verify`：14/14 可达，退出 0。负向测试：删掉一个归档标签后 `verify` 报 `LOST refs/heads/feat/conflict` 并退出 1，恢复标签后再次 ok。 |
| 8 汇报 | main 比 origin 超前 5、落后 0；未推送，远端分支和 stash 未动。 |

在 sfxmint 上只跑过只读 `inventory`（约 12 秒，主要是 `lsof`），没有执行清理。
