# PR-09R3 finding disposition

The following mapping is authoritative for this remediation. IDs are not
reused or reassigned.

## Carried PR-09R findings

- `PR09R-REV-008`: CLOSED and rerun. Exact SQL atomicity, same-transaction visibility, and fresh-UoW rollback are recorded in `atomicity_regression_report.md`.
- `PR09R-REV-009`: CLOSED and strengthened. Dataset/artifact retry edges now assert exact identity, role, ordinal, and count `== 1`.
- `PR09R-REV-010`: CLOSED by R3 replacement proof. The earlier pre-lock synchronization claim is withdrawn; the actual `SELECT ... FOR UPDATE` event proof is in `lock_boundary_race_report.md`.
- `PR09R-REV-011`: CLOSED by R3 replacement proof. Pointer retention is preserved and exact FROZEN/SUPERSEDED closure is now tested.
- `PR09R-REV-012`: CLOSED and rerun. Independent-UoW stale dataset attach, artifact attach, start, and finish tests prove no stale side effects.
- `PR09R-REV-013`: CLOSED as evidence reconciliation. Prior unsupported claims are explicitly withdrawn and replaced by R3 evidence.

## PR-09R3 findings

- `PR09R3-REV-001`: CLOSED. Both attach-first and start-first cases prove contention at the real Run lock boundary, with distinct active PostgreSQL transactions and blocked competitor acquisition.
- `PR09R3-REV-002`: CLOSED. `AD-PR09R3-001` is applied in the closure validator and covered by finalized-state and exact-provenance regressions.
- `PR09R3-REV-003`: CLOSED. Exact dataset and artifact edge tuples and retry cardinality are asserted.
- `PR09R3-REV-004`: CLOSED. This file supplies the corrected mapping.
- `PR09R3-REV-005`: CLOSED. The R3 fingerprint records baseline `9c47381`, implementation/test commit `197bd2d`, and the evidence commits; the non-self-referential final-HEAD convention is explained there.
- `PR09R3-REV-006`: ACCEPTED INHERITED P2. Eight repository-wide formatting failures are outside the PR-09R3-owned files; all owned Python files pass scoped format checking. No mass-formatting was performed.

Open P0: none. Open P1: none.
