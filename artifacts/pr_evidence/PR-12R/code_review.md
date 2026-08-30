# Code review

The remediation was checked against the five independent findings and the PR-12 attack surface. F-001 now has deterministic finalizer isolation independent of stale PR-11 cleanup constants. F-003 uses literal expected rows and independent canonical hashing. F-004 breaks a later exact input, not the first input. F-005 attacks every requested FROZEN field/source combination and representative non-DRAFT states, with fresh reads and hash invariants.

Only test files are changed by the remediation commit. No production code or migration semantic change was necessary. Repository-wide formatting debt remains outside the authorized scope and is recorded as P3.
