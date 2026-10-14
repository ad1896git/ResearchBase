# Task 5: PostgreSQL schema blockers

Status: **APPROVED**, implemented in **0043**; final verification: **4974 passed,
0 failed, 0 errors, 0 skipped** (see [Task 12](../task12/REPORT.md)).

The Task 5 findings were **P1 MAJOR / (a) production database contract gaps**, not environment
limitations or NOT_RUN items. Tests remain enabled and their expectations remain
unchanged. `schema-investigation.log` records their failures; the independent
read-only catalog in `schema-live-catalog.json` identifies PostgreSQL 18.6,
revision `0042_pr2_15_minimal_decision`, and the actual constraints/types/indexes.

## Concrete targets and evidence

| Target | Frozen requirement | Actual database | Required repair |
|---|---|---|---|
| `literature_search_provider_attempts.query_record_id` | PR2-04 pack §13.5: UNIQUE | No single-column unique constraint | Add UNIQUE; ordinary NULL semantics retain unsealed reservations |
| `search_query_records.(literature_search_execution_id,id)` | PR2-04 pack §13.3: composite UNIQUE | Missing | Add composite UNIQUE |
| `literature_search_execution_command_receipts.result_dto_version` | PR2-04 pack §13.7: SMALLINT | INTEGER | Change physical type to SMALLINT without changing values |
| Execution actor FKs | PR204-DB-02 / pack §13: leading unconditional B-tree indexes | Missing for `requested_by`, `executed_by` | Add each index |
| Query same-parent FK | Same | Missing for `(literature_search_execution_id,provider_attempt_id)` | Add composite index |
| Event FKs | Same | Missing for `(execution_id,attempt_id)` and `created_by` | Add indexes |
| Receipt FKs | Same | Missing for `(project_id,result_execution_id)` and `created_by` | Add indexes |
| Attempt query FK | Same | Missing for `query_record_id` | New UNIQUE above provides its index |
| Execution listing | Pack §13.1 / PR204-DB-02: `(project_id,status,created_at,id)` | Existing index omits status | Add exact required index |

The affected tests are three parameters of
`test_live_column_pk_nullability_and_fk_restrict_inventory` (attempts, queries,
receipts) and five parameters of `test_every_fk_has_unconditional_leading_btree_index`
(executions, attempts, queries, events, receipts), in
`tests/integration/phase2/test_pr2_04_schema_coverage.py`. The ninth failure is
`test_pr2_04_structural_guard_repair.py::test_exact_scoped_query_key_supports_concrete_fk`: PostgreSQL refuses a real dependent composite FK because the required scoped UNIQUE target is missing.

## Decision: APPROVED — implemented in 0043

Owner approval: **2026-10-14**, Task 12. Implemented in
`migrations/versions/0043_pr2_04_schema_contract.py`, one child after 0042 containing
only these existing-contract repairs. Preserve every historical migration byte;
add no canonical objects, fields, dependencies or new command behavior. Preflight
existing duplicate keys and SMALLINT range; fail closed rather than rewriting
history. Assert that populated scientific/provenance rows and receipts remain
identical, that indexes cover the exact FK leading columns, and that the chain has
one head. Update current-head test expectations while retaining historical target
revision checks. Run migration/constraint/regression suites and the full suite.

The governed forward migration applies these repairs. Implementing schema changes in
`src/` at application startup would bypass the governed migration path and is not
an acceptable workaround.

The earlier Task 5 restriction on modifying `migrations/` is superseded only for
this owner-approved forward migration. Historical migration bytes remain unchanged.
Upgrade locks all affected tables before checking duplicate non-NULL query keys,
duplicate scoped query keys, and SMALLINT range. Failure aborts the transaction
without changing rows or revision. Downgrade restores INTEGER and removes only
0043's constraints/indexes, without CASCADE. Historical evidence above describes
the pre-repair database; Task 12 verification is recorded in
[the verification report](../task12/REPORT.md).
