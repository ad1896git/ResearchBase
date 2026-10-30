# Pipeline safety patch (separate from controller redesign)

Scope: non-destructive `prepare_lane()` and kernel file locks only. No scientific
code, schema, database provisioning, commander loop or merge policy changes.

The legacy `.pipeline` runtime is local and untracked. `scripts/pipeline_safety.py`
contains the reviewed implementations. `scripts/install_pipeline_safety.py` patches
only the SHA-256-pinned known legacy driver and loop; preview is the default.
Unrecognized versions require review, never a best-effort rewrite.

Lane creation runs Git without a shell. Existing lanes must match the source,
branch and expected base ancestor; dirty files and later commits are preserved.
Incomplete, conflicting and symlink lanes stop without deletion or reset. Database
creation/cleanup is deliberately removed from preparation: provisioning must be a
separate explicitly authorized action. No existing DB is dropped or queried here.

The outer loop holds `runner.lock` throughout its lifetime. Direct autopilot calls
hold `autopilot.lock` before reading or resetting state. Locks are nonblocking OS
locks; PID contents are diagnostic. Files remain on disk after release. Kernel
locks release on process death; subprocess exec does not inherit the descriptors.
The control directory and lock inodes must not be replaced while running.

## Verification

Use the existing locked environment, without dependency synchronization:

```sh
python -m pytest tests/pipeline/test_pipeline_safety.py
python -m scripts.install_pipeline_safety --root /path/to/runtime
```

The second command only previews, and requires the exact pinned legacy files.
The tests use real Git repositories and concurrent child processes, including
crash recovery, rather than simulated lock ownership. They never access Postgres.

## Installation after review and human merge approval

1. Preserve runtime source, queue/state and all lanes. Verify and stop every legacy
   loop and active gate using the operating runbook. Do not stop other projects.
2. Preview against the actual runtime. Review the generated source and hashes.
3. Run `python -m scripts.install_pipeline_safety --root /path/to/runtime --apply`.
   It refuses recorded live processes or held locks, and retains original files
   under `.pipeline/logs/safety-backup`. A partial/unknown installation fails closed
   for operator reconciliation; do not delete backups or rerun blindly.
4. Start exactly one loop and verify lock contention from a second invocation.

This PR does not activate the new controller protocol or automatically merge PRs.
Per-PR human confirmation through `approved-merge` is the approved next protocol.
