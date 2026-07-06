# hook-template-builder

`hook-template-builder` scans a project, recommends Codex/Claude agent hooks, and generates templates only after the user confirms what should be enabled.

It is intentionally conservative:

- scan first, do not install first
- reminder hooks are the default
- blocking/global/network hooks require explicit confirmation
- Codex and Claude templates stay separate
- deterministic commit/merge checks are routed to git hooks or CI

## Quick Scan

```bash
./scripts/scan-project-hooks.sh /path/to/project
```

The script is read-only and emits a Markdown decision table covering default recommendations, project-specific candidates, high-risk hooks, and rules better handled outside agent hooks.

## Typical Flow

1. Run the scan against the target repo.
2. Present the decision table to the user.
3. Confirm platform and install mode.
4. Generate hook config, scripts, sample payloads, and install/uninstall commands.
5. Dry-run every generated script with a match and non-match payload.

## Default Bias

Default to Codex project-local templates and reminder behavior. Do not modify `~/.codex`, `~/.claude`, project hook config, or shell startup files unless the user explicitly asks for installation.
