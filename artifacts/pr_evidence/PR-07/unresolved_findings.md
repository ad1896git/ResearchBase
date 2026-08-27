# Unresolved findings

PR07-REV-001: CLOSED in PR-07R commit `fe888f3`; DRAFT updates now derive and verify
byte_size from the ArtifactStore and reject mismatches before persistence.

PR07-REV-002: CLOSED in `fe888f3`; the real ArtifactVersion is exercised through the
shared PR-03 contract harness with an explicit raw-byte-hash adapter mode.

PR07-REV-003: CLOSED for all PR-07-owned files. Nine unrelated baseline files remain
reported by repository-wide `ruff format --check .` and are not part of this remediation.

P3: unreferenced content-addressed bytes after a failed DB transaction may remain until a
future garbage-collection policy; PR-07 explicitly permits this and does not require GC.
No PR-08 behavior is started.
