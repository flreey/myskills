# Browser Dispatch And Recovery Protocol

Use resume discovery under an existing confirmed contract. Use dispatch only
after a new execution contract is confirmed and a blank task conversation
passes the exact model gate.

## Browser Role

The in-app browser is the communication and native-approval surface. It is not
the code synchronization layer.

- The ChatGPT conversation ID, not the physical browser tab, is the recovery
  identity.
- Send the engineering brief and correction evidence through the conversation.
- Observe model, authentication, generation, and native approval state.
- Track branch, commit, PR, and CI state through GitHub when possible.
- Never move code between local and Pro by copying browser-rendered code when a
  GitHub commit or verified artifact exists.

## Authorization Closure

The confirmed contract is the task-specific action-time approval for every
listed browser and source-transmission operation.

- An exact match proceeds without another agent-generated permission question.
- Dispatch, recovery, correction messages, and declared downloads remain
  inside the closure.
- Switching to an already authorized fallback does not require reconfirmation.
- A different account, destination, source scope, secret class, or unlisted
  operation requires a revised contract.
- A mandatory native ChatGPT/GitHub confirmation is a user handoff, not a new
  contract confirmation.

ChatGPT connected-app permissions are separate from Codex Full Access and the
execution contract. Record the observed state as `unknown`, `ready`, `prompt`,
or `blocked`. Never promise to suppress prompts or change the user's account
setting.

For a personal workflow, recommend `Allow GitHub for this conversation` when
the native prompt appears. It normally avoids repeated prompts inside that
task while limiting persistent authority. Do not choose `Always allow` on the
user's behalf.

## Resume-First Entry

Before opening a blank conversation, run `scripts/run_state.py resume` against
the current repository when the user is continuing an existing task.

- `RESUME`: acquire the lease and navigate to the saved canonical URL. Focus
  the matching physical tab when it exists; otherwise open the URL in a new
  tab. Both continue the same conversation.
- `NEW_TASK`: continue to contract preparation and initialize a new run only
  after confirmation.
- `AMBIGUOUS`: select by task ID or task branch. Do not infer from a duplicated
  conversation title.
- `LOCKED`: do not message the conversation. An explicit user statement that
  the previous Codex task was interrupted may authorize `--takeover`; record
  the takeover in the run.

After `RESUME`, verify the account and exact model, compare the recorded and
current GitHub head, then continue from `last_phase`. Do not send the original
brief again.

## Dispatch

1. Reuse the retained blank, model-gated task tab.
2. Verify that `conversation_url` is still null before the first message.
3. Rerun the model gate and record surface, picker, mapped model, official
   source, and time.
4. For GitHub, provide repository, exact base SHA, assigned task branch, and
   actor boundaries. Do not upload a duplicate bundle.
5. For bundle, upload the exact recorded archive and verify the visible
   filename and size when the UI exposes it.
6. Send the brief once.
7. Wait until the route is `/c/<conversation-id>`. A root `/` URL means the
   stable conversation has not been created yet.
8. Remove query and fragment components, then persist both the conversation ID
   and canonical `https://chatgpt.com/c/<conversation-id>` URL with
   `scripts/run_state.py bind-conversation`.
9. Record dispatch time, model check, transport, source identity, secret class,
   and native approval state.

If a native GitHub prompt appears, stop generation progress at the product
boundary and ask the user to approve or deny the exact displayed action. Resume
the same conversation after approval; do not resend the task. Persist
`awaiting-auth` and release the lease before handing control to the user.

If GitHub access fails, record the native error, rerun fast transport
selection, and use only an already authorized fallback.

## Observation Cadence

- Do not poll more often than every two minutes.
- Streaming text, research indicators, tool activity, or changing status is
  progress.
- Long duration alone is not failure.
- Do not stop, refresh, or resend while progress is visible.
- Renew the current task lease while acting. Release it before yielding to the
  user or when the current manager turn has no immediate action.

After two unchanged observations spanning at least ten minutes:

1. inspect for a visible error, stopped generation, reconnect control, native
   approval, or authentication requirement;
2. use the supported continue or reconnect action when it preserves context;
3. reopen the saved URL if the tab is lost;
4. ask Pro to continue from the last completed heading only when generation
   actually stopped;
5. never paste the full original brief twice into one conversation.

## Multiple Active Tasks

One engineering task maps to exactly one conversation ID, task branch, Draft
PR, isolated worktree, and run file. Default to no more than two active
code-changing tasks per repository.

- Pro generations may continue concurrently in separate conversations.
- Browser navigation, native approvals, correction sends, and exact-head
  acceptance are serialized per manager action, not by holding a global lock.
- Code tasks require non-overlapping edit scopes. Parent/child path overlap is
  a conflict even when the branch names differ.
- Review-only runs do not consume code-task capacity.
- A task must never send corrections to another task's conversation or advance
  another task's branch.

## Context Or Connection Recovery

When context appears truncated:

1. rerun the model gate;
2. stop without sending if the gate fails;
3. identify the last complete commit, artifact, or heading;
4. restate only task ID, immutable base/head or bundle identity, remaining
   deliverables, and unresolved acceptance criteria;
5. ask for continuation, not restart;
6. preserve earlier URLs, commits, hashes, and model checks.

When the URL no longer loads:

- inspect whether authentication is required;
- if so, pause for the user;
- otherwise create a replacement conversation only after recording the failed
  URL and recovery reason;
- pass the model gate again before sending repository context;
- link old and replacement URLs in the private ledger.

## Authentication Boundary

Pause for the user when the page requests:

- sign-in or account selection;
- password;
- CAPTCHA;
- Passkey;
- two-step verification;
- verification or recovery code.

Never inspect or export browser authentication state and never ask the user to
send credentials through chat. Resume the same authorization closure only
when account, destination, source scope, secret class, and operations are
unchanged.

## Deliverable Collection

For GitHub:

1. read the task branch and latest head from GitHub;
2. require Pro's head, commit, changed-file, test, and risk inventory;
3. compare the claimed inventory with GitHub;
4. let Codex create or update the Draft PR after the first valid commit;
5. use the exact head SHA as the deliverable identity.

For artifacts:

1. record filename and reported size;
2. download once;
3. calculate local byte size and SHA-256;
4. compare the declared and local identities;
5. reject traversal, absolute paths, symlinks, device files, unexpected
   binaries, credentials, or out-of-scope files.

## Persistent Run Registry

The deterministic registry implementation is `scripts/run_state.py`. Its
default private location is:

```text
~/.codex/chatgpt-pro-runs/
  index.json
  runs/<repo-hash>/<task-id>/run.json
```

The index supports discovery; each `run.json` is the authoritative task state.
Writes are atomic and guarded by a registry lock. The registry contains no
credentials, cookies, browser state, source archives, or conversation text.

Essential commands:

```bash
python3 scripts/run_state.py init ...
python3 scripts/run_state.py resume --repo-root <repo> --owner <codex-task> ...
python3 scripts/run_state.py bind-conversation --url <chatgpt-url> ...
python3 scripts/run_state.py record-model ...
python3 scripts/run_state.py update ...
python3 scripts/run_state.py release ...
python3 scripts/run_state.py finish --status completed ...
```

The persisted schema is version 4 and includes:

```json
{
  "schema_version": 4,
  "task_id": "task-001",
  "mode": "code|review",
  "repo": {"root": "<absolute path>", "github": "owner/name"},
  "execution_contract_sha256": "<sha256>",
  "authorization": {
    "secret_class": "none|interface-only|local-test|ci-test|production",
    "allowed_operations": []
  },
  "baseline_commit": "<sha>",
  "edit_scope": ["src/payments"],
  "model_policy": {
    "required": "GPT-5.6 Sol Pro",
    "fallback_allowed": false
  },
  "model_checks": [
    {
      "event": "pre-dispatch|recovery",
      "surface": "Chat",
      "picker_label": "Pro",
      "mapped_underlying_model": "GPT-5.6 Sol Pro",
      "official_mapping_url": "https://help.openai.com/...",
      "verified_at": "<UTC>",
      "result": "passed|blocked"
    }
  ],
  "transport": {
    "decision": "READY_GITHUB|READY_HANDOFF_BRANCH|READY_BUNDLE|BLOCKED_AUTH|BLOCKED",
    "selected": "github|handoff-branch|bundle|null",
    "native_auth_state": "unknown|ready|prompt|blocked"
  },
  "github": {
    "task_branch": "codex/chatgpt-pro/<task-id>",
    "latest_head": null,
    "draft_pr_url": null
  },
  "conversation": {
    "id": "<conversation-id|null>",
    "canonical_url": "https://chatgpt.com/c/<conversation-id>"
  },
  "status": "prepared|awaiting-auth|running|reviewing|correcting|validated-draft",
  "last_phase": "<phase>",
  "remaining_acceptance": [],
  "lease": {"owner": "<codex-task>", "expires_at": "<UTC>"}
}
```

Keep the registry outside the public repository because it contains private
conversation URLs and local metadata. Mark terminal runs `completed`,
`abandoned`, or `superseded`; retain them for audit but exclude them from
automatic recovery.
