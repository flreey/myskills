# Browser Dispatch And Recovery Protocol

Use this protocol only after transport selection and the task brief have passed
local checks. The retained blank task tab must already have passed
[model-gate-protocol.md](model-gate-protocol.md) before transport selection.

## Authorization Closure

The confirmed execution contract is the task-specific action-time approval for
every listed browser and source-transmission operation. Before opening or
recovering a task conversation, uploading, sending, commenting, or
downloading, compare the repository, ChatGPT account, conversation destination,
artifact or source scope, and operation with the active authority ledger.

- An exact match proceeds immediately without another agent-generated
  permission question.
- Dispatch, recovery, correction messages, and replacement downloads for the
  same task remain inside the closure.
- An authorized `auto` fallback from GitHub to the exact sanitized bundle does
  not require reconfirmation.
- A different account or destination, broader source or sensitive data, an
  unlisted operation, or changed acceptance/product scope requires a revised
  contract before action.
- A browser or connector may display a mandatory native confirmation control
  that a skill cannot suppress. Hand that control to the user without asking
  them to reconfirm the execution contract.

ChatGPT's connected-app permission mode is a separate product setting. During
read-only preparation, record the visible mode as `always-ask`,
`before-changes`, `important-only`, or `unknown`. The current product exposes
this under Settings > Apps with choices to always ask, ask before making
changes, or only ask before important changes. Do not change that account
setting automatically. If it remains `always-ask`, native GitHub/app prompts
may continue even though the execution-contract closure is active.

## Dispatch

1. Reuse the retained blank, model-gated task tab for this independent task. If
   it was lost before dispatch, open a replacement blank tab and rerun the
   complete model gate.
2. Verify that the pre-dispatch ledger still has `conversation_url: null`; do
   not invent a stable URL before the first message.
3. Rerun the model gate and record the selected surface, visible picker label,
   mapped underlying model, official mapping source, and verification time. Do
   not infer the model from subscription alone.
4. For GitHub transport, provide the Issue URL, repository identity, and exact
   baseline SHA. Do not upload a duplicate source archive.
5. For bundle transport, upload the exact ZIP recorded in the brief. Verify the
   visible attachment filename before sending. Verify the size when the UI
   displays it; otherwise record `attachment_size_visible_in_ui: false` and
   retain the locally measured size.
6. Send the filled task brief once.
7. Wait for the resulting stable conversation URL and save it immediately.
8. Record dispatch time, conversation URL, selected transport, source identity,
   and passed model check in `run.json`.

If a bundle attachment fails, inspect the visible error. Rebuild or narrow the
archive only when the error requires it. Do not silently substitute a different
archive without updating the manifest and brief.
Regenerating the same approved source scope and updating its recorded identity
stays inside the closure; adding source or sensitive data does not.

If GitHub access fails, record whether the live capability is `none`, `read`,
or `write`, rerun transport selection, and use only an authorized fallback.

## Observation Cadence

- Do not poll more often than every two minutes.
- Generation activity, research indicators, streamed text, or changing status counts as progress.
- Long duration is not itself a failure.
- Do not click stop, refresh, or resend while progress is visible.

After two unchanged observations spanning at least ten minutes:

1. inspect for a visible error, stopped generation, reconnect control, or continue control;
2. use the supported continue/reconnect action if it preserves the conversation;
3. if the tab is gone, reopen the saved URL;
4. ask ChatGPT to continue from the last completed heading only when generation has actually stopped;
5. never paste the full original task a second time into the same conversation.

## Context Or Connection Recovery

When context appears truncated:

1. rerun the model gate; stop without sending a continuation if it fails;
2. identify the last complete artifact or heading;
3. restate only the task ID, immutable source identity (GitHub base/head SHA or
   bundle SHA-256), remaining deliverables, and unresolved acceptance criteria;
4. ask for continuation rather than a restart;
5. preserve earlier artifacts, hashes, and model checks in the ledger.

When the saved URL no longer loads:

- confirm whether authentication is required;
- if authentication is required, pause for the user;
- otherwise create a replacement conversation only after recording the failed URL and recovery reason;
- pass the model gate in the replacement conversation before sending any task
  context or source identity;
- provide the replacement with the task brief, selected source identity, and a
  concise continuation state;
- link the old and new URLs in the ledger.

## Authentication Boundary

Pause for the user when the page requests:

- sign-in or account selection;
- password;
- CAPTCHA;
- Passkey;
- two-step verification;
- verification or recovery code.

Never inspect or export browser authentication state. Never ask the user to send credentials through chat.
Authentication is a user-only handoff, not a new permission decision. After
successful authentication, resume the active closure only when the same
account, destination, source scope, and operations still match.

## Deliverable Collection

Before leaving the conversation:

1. confirm the report is complete;
2. for `github-pr`, require the Draft PR URL, base and head SHAs, commit
   inventory, and changed-file inventory;
3. for artifact modes, require a patch or changed-files archive plus attachment
   sizes and SHA-256 values;
4. download each required attachment once and record the local hash;
5. record any stated test limitations and open assumptions.

If an artifact mode displays only a code block, request a downloadable
machine-usable artifact in the same conversation. In `github-pr`, require the
Draft PR and exact head SHA instead.

## Minimal Run Ledger

```json
{
  "schema_version": 2,
  "task_id": "task-001",
  "repo": "example",
  "execution_contract": {
    "version": 1,
    "confirmed_at": "<UTC>",
    "contract_sha256": "<sha256>",
    "authorization_closure": {
      "status": "active|superseded|blocked",
      "repo": "<owner/name or local identity>",
      "external_account": "<non-secret account label>",
      "destinations": [],
      "connected_app_permission_mode": "always-ask|before-changes|important-only|unknown",
      "approved_data_scope": [],
      "approved_edit_scope": [],
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
    "requested": "auto",
    "selected": "github-pr|github-issue-patch|bundle",
    "authority": {}
  },
  "source_identity": {
    "github": {
      "issue_url": "https://github.com/.../issues/...",
      "base_sha": "<sha>",
      "head_sha": "<sha>",
      "diff_bytes": 0,
      "diff_sha256": "<sha256>"
    },
    "bundle": {
      "name": "example-source-<sha>.zip",
      "bytes": 0,
      "sha256": "<sha256>"
    }
  },
  "conversations": [
    {
      "url": null,
      "pre_dispatch_opened_at": "<UTC>",
      "dispatched_at": "<UTC>",
      "model_checks": [
        {
          "event": "conversation-created|pre-dispatch|recovery",
          "surface": "Chat",
          "picker_label": "Pro Extended",
          "mapped_underlying_model": "GPT-5.6 Sol Pro",
          "official_mapping_url": "https://help.openai.com/...",
          "verified_at": "<UTC>",
          "result": "passed|blocked"
        }
      ],
      "status": "running|delivered|recovered|blocked"
    }
  ],
  "artifacts": [],
  "verification": [],
  "state": "prepared|dispatched|reviewing|correcting|passed|blocked"
}
```

Replace `url: null` with the stable conversation URL immediately after the
first task message creates it. The ledger may contain private conversation URLs
and local repository metadata. Keep it in the persistent run directory, not in
a public repository.
