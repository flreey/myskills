# Agent / Automation System Template

## Vague input
> "I want an agent that triages my GitHub issues."

## Questions to ask (≤3)
1. What "triage" outcome? (label + assignee / auto-close obvious dupes / draft a response / "choose for me" → label + assignee + draft response)
2. How autonomous? (agent acts directly / agent drafts and you approve / read-only suggestions / "choose for me" → drafts, you approve)
3. Trigger? (every new issue / nightly batch / on-demand / "choose for me" → every new issue, with a 10-min debounce)

## Final prompt

```text
Agent goal:
Triage every new GitHub issue in <repo> within 10 minutes of creation by (1) suggesting labels, (2) suggesting an assignee, (3) drafting a response — all as a single comment posted to the issue, awaiting human approval.

Trigger:
- GitHub webhook: issues.opened
- Debounced: if multiple events for the same issue arrive within 10 min, only the latest runs
- Manual re-run: a maintainer comments `/triage-again` to force re-run

State model:
- Stateless per run, but reads:
  - Issue body + title + opener's history in this repo
  - Last 50 closed issues for label/assignee patterns
  - CONTRIBUTING.md and any ISSUE_TEMPLATE.md
- Writes a single comment with a structured body (see Outputs)

Tools available:
- GitHub REST API (read: issues, contributors, files; write: comments, labels — labels gated behind approval)
- An LLM (Claude Sonnet 4.6) for classification + drafting
- A vector store of past closed issues (for similarity-based "is this a dup?" check)
- Logging: structured JSON to stdout (captured by the platform)

Decision policy:
1. Classify: bug / feature / question / docs / dup / spam
2. If similarity > 0.85 with a closed issue → flag as likely dup, link the closed issue, do NOT auto-close
3. Suggest 1-3 labels from the repo's existing label set (never invent new labels)
4. Suggest assignee from contributors who have closed similar issues in the last 90 days
5. Draft a response:
   - For bug: ask for repro steps if missing
   - For feature: thank, link to roadmap policy
   - For dup: link to the existing issue, ask if it covers their case
   - For spam: do nothing (escalate to maintainer-only channel)
6. If confidence in any field is low, mark it `uncertain — please review`

Termination rule:
- One pass per trigger. No loops. No self-retries within a run.
- Max wall-clock 60s per run; if exceeded, log timeout and post a minimal "triage skipped: timeout" comment.

Error / retry policy:
- Transient API errors (5xx, rate limit): retry 3x with exponential backoff (2s / 8s / 32s)
- Permanent errors (4xx other than 429): log and abort, post no comment
- LLM call failure: fall back to "labels: needs-triage" only
- Never silently fail — every run produces either a comment or a logged abort

Logging requirements:
- One JSON line per run: { run_id, issue_url, classification, confidence, action_taken, latency_ms, errors[] }
- Sensitive: do NOT log issue body content, only metadata + classifications

Escalation path:
- If classification == spam → no action, log only
- If similarity > 0.85 → human review tag (do not close)
- If LLM detects security-sensitive content (CVE references, secrets) → tag `security`, ping @security-team via mention, do NOT post the LLM-drafted body publicly

Outputs (the comment posted on the issue):

```markdown
**Triage suggestion** _(automated, please review)_

**Classification:** bug
**Likely dup of:** #1234 _(similarity 0.91)_ — please confirm
**Suggested labels:** `bug`, `needs-repro`
**Suggested assignee:** @alice
**Draft response:**
> Thanks for reporting this. To help us reproduce, could you share: ...

_Confidence: classification high, dup high, assignee medium. /triage-again to re-run._
```

Acceptance criteria:
- 10 sample issues processed, ≥7 of the labels/assignees match what a maintainer would have chosen
- No issue is auto-closed; no labels are auto-applied without approval
- p50 latency from webhook to comment < 30s; p95 < 60s
- Logs allow reconstructing every decision after the fact
- Spam never receives a public comment

Avoid:
- No autonomous closing, labeling, or assigning in v1
- No fine-tuning the LLM in v1
- No multi-turn agent loops — single pass only
- No fancy queue infrastructure — a webhook + a stateless function is enough
- Don't repeat boilerplate ("we appreciate your contribution") in every draft response
```

## Notes
- The single most important field is "Termination rule" — it prevents agents from looping silently forever.
- "Outputs" with a literal example structure is what makes this checkable.
- "Avoid" prevents agentic-system over-engineering (queues, fine-tunes, loops).
- Confidence labels in the comment let humans triage *the triage*.
