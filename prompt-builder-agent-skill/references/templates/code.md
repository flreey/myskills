# Code / Automation Template

## Vague input
> "I need a script that watches a folder and uploads new files to S3."

## Questions to ask (≤3)
1. Runtime? (local dev machine / a Linux server / a container / "choose for me" → Linux server, systemd)
2. Language preference? (Python / Node / Go / "choose for me" → Python 3.12)
3. What happens on upload failure? (retry / move to error folder / alert / "choose for me" → retry 3x then move to error/)

## Final prompt

```text
Goal:
A Python 3.12 daemon that watches a local folder, uploads new files to an S3 bucket, and handles failures gracefully. Runs as a systemd service on Linux.

Environment:
- Python 3.12
- Linux (Ubuntu 22.04+)
- AWS credentials via environment (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION) or instance profile
- Single-host, single-process

Requirements:
1. Watch a configurable folder (default: /var/inbox) recursively for new files
2. On new file detected (write-complete, not write-in-progress):
   a. Upload to s3://<bucket>/<prefix>/<original-relative-path>
   b. On 200: move local file to /var/inbox/.uploaded/<original-relative-path>
   c. On failure: retry 3 times with exponential backoff (1s, 4s, 16s)
   d. On final failure: move to /var/inbox/.error/ with a sidecar .err file containing the exception
3. Idempotent: a file already at the S3 key (matching size + ETag) is skipped, not re-uploaded
4. Structured JSON logs to stdout (one line per event)

Files:
- watcher.py — entry point, argument parsing, main loop
- config.py — pydantic Settings model loaded from env + optional config.toml
- uploader.py — S3 upload + retry logic (boto3)
- detector.py — folder watcher (watchdog package), debounced for write-complete
- tests/test_uploader.py — uses moto for S3
- tests/test_detector.py — uses tmp_path
- pyproject.toml — uv-managed, deps: boto3, watchdog, pydantic-settings
- systemd/folder-watcher.service — service unit file

Implementation details:
- Write-complete detection: file size stable across two 500ms ticks
- Use boto3 transfer manager for files >8MB (multipart)
- ETag check uses HEAD before upload
- Don't follow symlinks (security)

Test plan:
- Unit: upload success / failure / idempotency / retry timing
- Integration: drop a 1MB and a 10MB file, verify upload + move
- All tests run via `uv run pytest`

Run commands:
- Dev: `uv run python -m watcher --folder ./inbox --bucket my-test-bucket`
- Service: `sudo systemctl enable --now folder-watcher`

Avoid:
- No threading-based concurrency in v1 (sequential uploads are fine for the throughput target)
- No DLQ / SQS in v1 (just .error/ folder)
- No metrics export (logs are enough)
- Don't swallow exceptions silently

Acceptance criteria:
- pytest passes with 100% coverage on uploader.py + detector.py
- Manual test: drop 5 files in inbox/, all 5 appear in S3 within 5s, all 5 moved to .uploaded/
- Failure injection (network off): file ends up in .error/ with an .err sidecar after ~21s
```

## Notes
- "Files:" with one-line responsibilities prevents the implementer from inventing layout.
- Test plan is part of the prompt — without it, models default to no tests or trivial ones.
- "Avoid" pre-empts common over-engineering (threading, queues, metrics).
