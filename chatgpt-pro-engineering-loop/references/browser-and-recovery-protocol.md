# Browser Dispatch And Recovery Protocol

Use this only after the execution contract is confirmed and a blank task
conversation passes the exact model gate.

## Browser Role

The in-app browser is the communication and native-approval surface. It is not
the code synchronization layer.

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
7. Save the stable conversation URL immediately after dispatch.
8. Record dispatch time, model check, transport, source identity, secret class,
   and native approval state.

If a native GitHub prompt appears, stop generation progress at the product
boundary and ask the user to approve or deny the exact displayed action. Resume
the same conversation after approval; do not resend the task.

If GitHub access fails, record the native error, rerun fast transport
selection, and use only an already authorized fallback.

## Observation Cadence

- Do not poll more often than every two minutes.
- Streaming text, research indicators, tool activity, or changing status is
  progress.
- Long duration alone is not failure.
- Do not stop, refresh, or resend while progress is visible.

After two unchanged observations spanning at least ten minutes:

1. inspect for a visible error, stopped generation, reconnect control, native
   approval, or authentication requirement;
2. use the supported continue or reconnect action when it preserves context;
3. reopen the saved URL if the tab is lost;
4. ask Pro to continue from the last completed heading only when generation
   actually stopped;
5. never paste the full original brief twice into one conversation.

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

## Minimal Run Ledger

```json
{
  "schema_version": 3,
  "task_id": "task-001",
  "repo": "owner/name",
  "execution_contract": {
    "version": 1,
    "contract_sha256": "<sha256>",
    "authorization_closure": {
      "status": "active|superseded|blocked",
      "external_account": "<non-secret label>",
      "approved_data_scope": [],
      "approved_edit_scope": [],
      "secret_class": "none|interface-only|local-test|ci-test|production",
      "allowed_operations": [],
      "reconfirmations": [],
      "redundant_agent_permission_prompts": 0
    }
  },
  "baseline_commit": "<sha>",
  "baseline_status_sha256": "<sha256>",
  "model_policy": {
    "required": "GPT-5.6 Sol Pro",
    "fallback_allowed": false
  },
  "transport": {
    "decision": "READY_GITHUB|READY_HANDOFF_BRANCH|READY_BUNDLE|BLOCKED_AUTH|BLOCKED",
    "selected": "github|handoff-branch|bundle|null",
    "native_auth_state": "unknown|ready|prompt|blocked"
  },
  "github": {
    "manager": "Codex",
    "developer": "ChatGPT Pro",
    "base_sha": "<sha>",
    "task_branch": "codex/chatgpt-pro/<task-id>",
    "head_sha": "<sha|null>",
    "draft_pr_url": null
  },
  "conversations": [
    {
      "url": null,
      "model_checks": [
        {
          "event": "conversation-created|pre-dispatch|recovery",
          "surface": "Chat",
          "picker_label": "Pro",
          "mapped_underlying_model": "GPT-5.6 Sol Pro",
          "official_mapping_url": "https://help.openai.com/...",
          "verified_at": "<UTC>",
          "result": "passed|blocked"
        }
      ],
      "status": "prepared|running|delivered|recovered|blocked"
    }
  ],
  "artifacts": [],
  "verification": [],
  "state": "prepared|dispatched|reviewing|correcting|validated-draft|blocked"
}
```

Replace the null conversation URL after the first message creates the stable
URL. Keep the ledger outside the public repository because it may contain a
private conversation URL and local metadata.
