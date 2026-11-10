#!/usr/bin/env bash
# Build a throwaway repo that exercises every branch-cleanup case.
# Usage: drill_setup.sh <empty-dir>
# Creates <dir>/origin.git (bare remote) and <dir>/repo (main worktree) plus sibling worktrees.
set -euo pipefail
ROOT=${1:?usage: drill_setup.sh <empty-dir>}
mkdir -p "$ROOT"
[ -z "$(ls -A "$ROOT")" ] || { echo "$ROOT is not empty" >&2; exit 1; }
cd "$ROOT"
ROOT=$(pwd -P)
export GIT_AUTHOR_NAME=drill GIT_AUTHOR_EMAIL=drill@example.invalid
export GIT_COMMITTER_NAME=drill GIT_COMMITTER_EMAIL=drill@example.invalid

git init -q --bare origin.git
git init -q -b main repo
cd repo
c() { echo "$2" >> "$1"; git add "$1"; git commit -qm "$3"; }

# project test + pre-commit hook (the skill must run this after merging)
cat > test.sh <<'EOF'
#!/usr/bin/env bash
# fails if any file still contains a conflict marker or the word BROKEN
! grep -rIl --exclude-dir=.git --exclude=test.sh -e '^<<<<<<<' -e 'BROKEN' .
EOF
chmod +x test.sh
mkdir -p .githooks
printf '#!/usr/bin/env bash\nexec ./test.sh\n' > .githooks/pre-commit
chmod +x .githooks/pre-commit
printf 'node_modules\n.env\ndata/\n' > .gitignore
c README.md "drill repo" "init"
git add test.sh .githooks .gitignore && git commit -qm "chore: tests and hooks"
git config core.hooksPath .githooks
c app.txt "line1" "feat: app"
git remote add origin "$ROOT/origin.git"
git push -q -u origin main
# main-repo-only files that worktree symlinks will point at
mkdir -p node_modules/pkg data && echo "real module" > node_modules/pkg/index.js && echo '{"catalog":1}' > data/catalog.json

# 1 merged: merged with a merge commit
git switch -qc feat/merged
c merged.txt "merged work" "feat: merged work"
git switch -q main && git merge -q --no-ff --no-edit feat/merged

# 2 squashed: same content landed on main by cherry-pick -> equivalent
git switch -qc feat/squashed
c squash.txt "squash me" "feat: squashed work"
git switch -q main && git cherry-pick feat/squashed >/dev/null

# 3 conflict: edits app.txt line that main also edits
git switch -qc feat/conflict
sed -i.bak 's/line1/line1-from-branch/' app.txt && rm -f app.txt.bak && git commit -qam "feat: conflicting edit"
git switch -q main
sed -i.bak 's/line1/line1-from-main/' app.txt && rm -f app.txt.bak && git commit -qam "fix: main edits app"

# 4 clean: diverged, separate file
git switch -qc feat/clean main~1
c clean.txt "clean work" "feat: clean independent work"
git switch -q main

# 5 ff: strictly ahead of main
git switch -qc feat/ff main
c ff.txt "ff work" "feat: fast-forwardable work"
git switch -q main

# 6 experiment: clean merge but WIP -> should be archived, not merged
git switch -qc exp/wip main
c wip.txt "TODO half done" "wip: experiment"
git switch -q main
git push -q origin main

# 7 worktree on a finished ff branch, with symlinks into the main repo and an ignored .env
git worktree add -q -b feat/wt-done "$ROOT/wt-done" main
( cd "$ROOT/wt-done" && echo "done" > wt.txt && git add wt.txt && git commit -qm "feat: worktree work"
  ln -s "$ROOT/repo/node_modules" node_modules
  mkdir -p data && ln -s "$ROOT/repo/data/catalog.json" data/catalog.json
  echo "SECRET=1" > .env )

# 8 worktree with uncommitted changes
git worktree add -q -b feat/wt-dirty "$ROOT/wt-dirty" main
( cd "$ROOT/wt-dirty" && c dirty.txt "committed" "feat: dirty base" && echo "uncommitted" >> dirty.txt && echo new > untracked.txt )

# 9 detached worktree with a commit on no branch
git worktree add -q --detach "$ROOT/wt-detached" main
( cd "$ROOT/wt-detached" && c detached.txt "orphan" "feat: commit on detached head" )

# 10 remote-only branch with unmerged work
git switch -qc feat/remote-only main
c remote.txt "remote" "feat: remote only"
git push -q origin feat/remote-only
git switch -q main && git branch -qD feat/remote-only

# 11 a stash entry
echo stash >> README.md && git stash -q

echo "drill repo ready: $ROOT/repo"
