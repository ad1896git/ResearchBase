# PR-09R3 evidence reconciliation

Baseline `9c47381` and all accepted prior commits are preserved. The R3
implementation/test commit is `197bd2d`. The R3 package supersedes the
historical R2 gate record for the remaining final-review questions.

The following prior overclaims are explicitly withdrawn or narrowed:

- PR-09R2's exact-provenance report proved pointer/identifier retention, but
  not closure after supersession; R3 supplies that closure proof.
- PR-09R2's attach/start report did not establish the real PostgreSQL lock
  boundary; R3 supplies exact lock SQL event ordering and blocked acquisition.
- PR-09R2's retry report did not expose exact role/ordinal identity; R3 adds
  exact tuple assertions.
- PR-09R2's finding and fingerprint metadata are historical; this package
  supplies corrected ID mapping and R3 commit inventory.

Fresh R3 evidence is consistent with the actual diff, test results, current
Git state, PostgreSQL 18.6, and Alembic `0009_run_input_seal_fix (head)`. No
new migration, PR-10 behavior, or later-phase implementation exists.

The R3 package was authoritative through `0feba30`. Its final narrow review
identified two P2 gaps: omission of `0feba30` from its own final chain and
insufficient concurrent-finish winner metadata assertions. PR-09R4 records
and closes both gaps; its package is authoritative for the final remediation.
