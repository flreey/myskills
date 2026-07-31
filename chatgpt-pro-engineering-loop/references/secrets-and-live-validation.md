# Secrets And Live Validation

Use this protocol before the external brief whenever implementation or
acceptance mentions a key, token, password, certificate, OAuth credential,
database URL, signing material, private endpoint, or production account.

## Non-Negotiable Boundary

Secret values never enter:

- ChatGPT messages or attachments;
- Git files, commits, branches, Issues, PRs, comments, or review evidence;
- `.env.example`, screenshots, copied logs, test fixtures, or run ledgers;
- command-line arguments when an environment variable or standard input is
  available.

ChatGPT Pro receives the interface, not the value: variable name, required
format, public endpoint, sanitized response schema, and safe fixtures.

## Classification

Classify each credential requirement before dispatch.

| Class | Meaning | Standard handling |
|---|---|---|
| `none` | no credential is required | normal GitHub flow |
| `interface-only` | implementation needs the configuration contract, not a live value | send names, types, public docs, and sanitized fixtures |
| `local-test` | authoritative integration needs a development or sandbox value | Pro writes the code; Codex injects the value locally after full diff review |
| `ci-test` | a reviewed CI job needs a development or sandbox secret | requires separate provisioning authority and a gated workflow/environment |
| `production` | production credential, production data, or production action is required | block the standard loop and require a new execution contract |

Client IDs, tenant IDs, public endpoints, and project identifiers are not
automatically public. Classify them according to the provider and repository
policy before including them in a brief.

## Implementation Without A Secret

For `interface-only`, require Pro to:

- read credentials from an environment or injected configuration interface;
- fail clearly when required configuration is absent;
- never log the value or serialize it into diagnostics;
- use dependency injection, a fake server, mocks, or sanitized fixtures for
  deterministic tests;
- document only placeholder names such as `PAYMENT_API_KEY`.

If Pro says a real value is required to write the code, separate protocol
knowledge from live verification. Supply official public documentation and
sanitized input/output shapes. Keep live execution with Codex.

## Local Credentialed Validation

For `local-test`:

1. use a development or sandbox credential with minimum scope, quota, and
   lifetime;
2. review the complete executable diff before injection;
3. load the value from the existing local environment or secret manager into
   an isolated process with an allowlisted environment; do not pass the
   developer command the full inherited shell environment;
4. avoid revealing, printing, inspecting, copying, or recording the value;
5. keep the value out of command arguments when environment or standard input
   is supported;
6. capture only redacted results, status codes, timings, and safe response
   fields;
7. send Pro a redacted failure packet when correction is required.

Do not convert a missing credential into a fake pass. Report the live
integration as `not run` when the safe value or environment is unavailable.

## CI Credentialed Validation

For `ci-test`:

- provisioning or changing GitHub Secrets or Environments requires explicit
  authority outside the normal code-edit loop;
- Pro may write a reference such as `${{ secrets.PAYMENT_API_KEY }}` but never
  receives the value;
- review every workflow, action pin, script, dependency, and executable path
  before a secret-bearing job runs;
- grant the workflow token and secret the minimum scope;
- prefer an environment secret with approval and branch restrictions;
- prefer OIDC and short-lived cloud tokens over long-lived cloud keys;
- avoid privileged `pull_request_target` or `workflow_run` execution of
  untrusted branch content;
- treat self-hosted runners as non-isolated infrastructure.

A same-repository branch is not automatically trusted. Code on that branch can
still export environment values if the workflow permits it.

## Production Boundary

Production credentials, deployments, migrations, production configuration,
and real user data are outside the standard engineering loop.

When production access is genuinely required:

1. stop before exposing or using the value;
2. state the exact missing production evidence;
3. propose a sandbox or local substitute;
4. require a separate contract that names the environment, operation, data
   scope, rollback, verification, and human approval.

Do not let Pro recommend a production command and then treat that recommendation
as authority to execute it.

## Repository And Push Protection

Before publishing a handoff branch or bundle:

- scan the exact bytes;
- exclude `.env`, credentials, private keys, certificates, databases, browser
  state, and secret-bearing fixtures;
- never bypass a secret-scanning block merely to continue;
- rely on existing GitHub push protection when available; enabling or changing
  it requires separate repository-settings authority;
- keep workflow changes visibly separated and subject to manager review.

## Leak Response

If a secret reaches ChatGPT, GitHub, an attachment, or a log:

1. stop the task and prevent further propagation;
2. revoke or rotate the credential immediately;
3. preserve only redacted incident evidence;
4. remove the secret from the current content and repository history as
   required;
5. inspect relevant access and workflow logs;
6. rerun secret scanning before resuming;
7. create a new credential with the smallest practical scope.

Deleting the current file or commit alone does not make an exposed credential
safe.
