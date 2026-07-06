# hook-template-builder

`hook-template-builder` scans a project, recommends Codex/Claude agent hooks, and either generates templates or installs usable project hooks after the user confirms what should be enabled.

It is intentionally conservative:

- scan first, do not install first
- installed means loaded: scripts must be referenced by a Codex/Claude hook config that the target agent reads
- existing hooks must be audited and merged, never overwritten
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
4. If the user chooses template-only, generate hook config, scripts, sample payloads, and install/uninstall commands.
5. If the user chooses project install, write scripts into `.codex/hooks/` or `.claude/hooks/`, merge config into the project hook settings, and preserve existing hooks.
6. Dry-run every installed script with a match and non-match payload.
7. Verify activation: config parses, commands reference existing scripts, duplicates were not added, and any new-session/trust caveat is reported.

## Default Bias

Default to Codex project-local reminder behavior. If the user explicitly asks for usable hooks or installation, project-install the selected reminder hooks and verify activation. If the user asks for preview/templates only, do not modify project config.

Do not modify `~/.codex`, `~/.claude`, or shell startup files unless the user explicitly asks for global installation and confirms the second warning.
