# GPT-5.6 Sol Pro Model Gate

This is a fail-closed gate for every external task conversation. Pass it before
source packaging, source transmission, task-message dispatch, or GitHub task
mutation.

## Required Model

- Underlying model: `GPT-5.6 Sol Pro`
- Fallback allowed: `false`
- Account tier alone is not evidence.
- A generic GPT-5.6 label alone is not evidence.

The requirement is about the underlying model, not a remembered picker label.
Picker labels are accepted only while current official OpenAI documentation
maps them to `GPT-5.6 Sol Pro`.

## Current Official Mapping

Checked 2026-07-30:

- OpenAI's GPT-5.6 ChatGPT documentation maps the `Pro` picker choice to
  `GPT-5.6 Sol Pro`.
- The same documentation maps Medium, High, and Extra High to the base
  `GPT-5.6 Sol`, not `GPT-5.6 Sol Pro`.
- Current ChatGPT release notes may expose Pro variants such as
  `Pro Standard` and `Pro Extended`.
- Live Codex in-app-browser inspection found the Chat surface with a checked
  `Pro` picker choice and the Work surface with `5.6 Sol Extra High`. The Work
  label does not satisfy this gate; use the eligible Chat surface instead.

Primary sources:

- <https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt/>
- <https://help.openai.com/en/articles/6825453-chatgpt-release-notes/>
- <https://openai.com/index/gpt-5-6/>

Because product labels can change, re-open the current official documentation
for every run. Accept `Pro Extended`, `Pro Standard`, or `Pro` only when the
current documentation still maps the visible choice to `GPT-5.6 Sol Pro`.

Explicitly reject:

- `5.6 Sol Light`;
- Medium, High, or Extra High;
- Work with `5.6 Sol Extra High`;
- Instant;
- Terra, Luna, or another model family;
- an unavailable, disabled, ambiguous, or undocumented picker label.

## Gate Procedure

For each independent task:

1. Check the current official OpenAI model mapping and record its URL and check
   time.
2. Open and retain a new blank task tab. Before the first message, record
   `conversation_url: null`; do not invent a stable conversation URL.
3. Inspect every visible ChatGPT task surface that can host the conversation.
   If the current surface lacks an eligible Pro choice but another visible
   surface offers one, switch to the eligible surface before deciding the gate
   is blocked. Do not treat Work as mandatory.
4. Inspect the selected surface's model picker. Prefer `Pro Extended`, then
   `Pro Standard`, then `Pro`, but only when the checked mapping proves that
   choice uses `GPT-5.6 Sol Pro`.
5. Select the eligible choice and verify the visible selected label and
   surface.
6. Record the required model, selected surface, selected label, mapped
   underlying model, verification source, check time, and
   `fallback_allowed: false`.
7. Continue only when every field is present and the mapped underlying model is
   exactly `GPT-5.6 Sol Pro`.

Do not attach a bundle, mention a private repository, create an Issue or branch,
send the task brief, or otherwise expose task source before the gate passes.

## Fail-Closed Result

If no visible conversation surface offers an eligible choice, the picker is
ambiguous, current official documentation cannot be checked, or the selection
cannot be verified:

1. keep the task tab blank;
2. record the visible labels and exact blocker without including credentials or
   browser state;
3. set the task and run to `blocked`;
4. tell the user what availability or product-surface issue must be resolved.

Do not choose the nearest model. Do not ask a lower model to begin research. Do
not create remote task state to save time. Resume only after the same blank tab
or a freshly gated replacement passes the gate, or the user explicitly
approves a revised model contract.

Authentication, account selection, CAPTCHA, Passkey, and two-step verification
remain user-only actions.

## Recheck Events

Rerun steps 3–7:

- immediately before the first source attachment, repository reference, or
  task-message send;
- after reconnecting or reopening the saved conversation;
- after creating a replacement conversation;
- before sending a continuation after context recovery;
- whenever the picker label changes or the page reports a model availability,
  quota, or rate-limit condition.

A failed recheck freezes further external communication. Preserve the URL state
(`null` before dispatch), latest completed heading, artifact identities, and
prior model evidence, then apply the fail-closed result.

## Ledger Shape

```json
{
  "conversation_url": null,
  "model_policy": {
    "required": "GPT-5.6 Sol Pro",
    "fallback_allowed": false
  },
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
  ]
}
```

A stable conversation URL is recorded immediately after the first task message
creates it. Private conversation URLs remain in the persistent local run
ledger, not in a public validation report.
