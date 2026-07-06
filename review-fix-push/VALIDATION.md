# Validation - review-fix-push

Date: 2026-07-06
Classification: Discipline skill. The discipline pressure is to skip review, stage everything, or push before fresh verification.

## Pre-Registered Deltas

1. Without the skill, an agent may run `git add -A && git commit && git push`; with the skill, it must inspect staged, unstaged, untracked, and unpushed commits first.
2. With the skill, clear findings are auto-fixed, but product/API/migration/security judgment calls become ASK blockers.
3. With the skill, suspicious files such as real `.env`, keys, DBs, logs, archives, and large files are not staged blindly.
4. With the skill, verification must be fresh after fixes and before commit/push.
5. With the skill, non-fast-forward push failures stop for confirmation; no force push or automatic rebase/pull.

## Smoke Validation

Checks run:

- `bash -n review-fix-push/scripts/preflight.sh` - PASS.
- Temporary clean git repo - PASS; reports clean status, no tracked/untracked changes, no upstream.
- Temporary repo with staged `new.txt`, unstaged `README.md`, untracked `.env`, and untracked `app.log` - PASS; reports all three change buckets and flags `.env` / `app.log` as suspicious.
- Temporary repo cloned from a bare remote with one unpushed commit - PASS; reports upstream, remote URL, ahead/behind counts, and the unpushed commit.

## Result

Deliverable for initial use. The skill enforces whole-scope review before staging, protects suspicious artifacts, requires fresh verification, and refuses force-push / automatic history reconciliation. Full A/B validation is still recommended before treating it as a hardened public release.
