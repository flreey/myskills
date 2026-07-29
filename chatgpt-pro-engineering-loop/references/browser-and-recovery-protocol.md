# Browser Dispatch And Recovery Protocol

Use this protocol only after transport selection and the task brief have passed
local checks.

## Dispatch

1. Open a new ChatGPT conversation for one independent task.
2. Wait until the conversation has a stable URL and save it immediately.
3. Record the model or product surface label that is visibly selected. Do not infer it from subscription alone.
4. For GitHub transport, provide the Issue URL, repository identity, and exact
   baseline SHA. Do not upload a duplicate source archive.
5. For bundle transport, upload the exact ZIP recorded in the brief. Verify the
   visible attachment filename before sending. Verify the size when the UI
   displays it; otherwise record `attachment_size_visible_in_ui: false` and
   retain the locally measured size.
6. Send the filled task brief once.
7. Record dispatch time, conversation URL, selected transport, source identity,
   and visible surface label in `run.json`.

If a bundle attachment fails, inspect the visible error. Rebuild or narrow the
archive only when the error requires it. Do not silently substitute a different
archive without updating the manifest and brief.

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

1. identify the last complete artifact or heading;
2. restate only the task ID, immutable source identity (GitHub base/head SHA or
   bundle SHA-256), remaining deliverables, and unresolved acceptance criteria;
3. ask for continuation rather than a restart;
4. preserve earlier artifacts and hashes in the ledger.

When the saved URL no longer loads:

- confirm whether authentication is required;
- if authentication is required, pause for the user;
- otherwise create a replacement conversation only after recording the failed URL and recovery reason;
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
  "schema_version": 1,
  "task_id": "task-001",
  "repo": "example",
  "execution_contract": {
    "version": 1,
    "confirmed_at": "<UTC>",
    "contract_sha256": "<sha256>"
  },
  "baseline_commit": "<sha>",
  "baseline_status_sha256": "<sha256>",
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
      "url": "https://chatgpt.com/c/...",
      "dispatched_at": "<UTC>",
      "visible_surface": "<label>",
      "status": "running|delivered|recovered|blocked"
    }
  ],
  "artifacts": [],
  "verification": [],
  "state": "prepared|dispatched|reviewing|correcting|passed|blocked"
}
```

The ledger may contain private conversation URLs and local repository metadata. Keep it in the persistent run directory, not in a public repository.
