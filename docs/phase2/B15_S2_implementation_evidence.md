# B15 package preparation S2 implementation evidence

**Review follow-up status: BLOCKED — the required full check is not PASS.** The
owner-loop check reported 9,699 passed, 50 skipped and 2 failed. B07's table
inventory omission is fixed; the ownership race was not reproduced in isolation.
The current exact runner attempt passed static checks but was blocked by sandbox
writes to its shared lock path. See [full-check status](B15_S2_review_full_check.txt).
The original focused results below must not be read as an overall gate PASS.

Owner authorization: 2026-10-18. The proposal status was changed before source implementation.
Only preparation, direct GRANTED roots, exact history/preview/readback and OWNER package withdrawal are enabled.
No package freeze/send, consent successor/withdrawal, grant consumption, READY transition, transport adapter or new runtime dependency is enabled.

## Implementation and reconciliation

- Added one forward revision, `0060_b15_package_preparation`, after actual head `0059_b13_grant_consumption`. It adds exactly the four registered package/consent tables with concrete RESTRICT FKs, named checks/indexes, native-XID seals, preheld-inventory checks and deferred final-graph guards. Existing migration files remain unchanged. Empty downgrade works; retained package history blocks populated downgrade.
- Added pure occurrence projection and literal R2 consent/manifest material, closed frozen commands/readbacks, seven Application service methods, typed ports, persistence adapter and opt-in sanitized UoW errors. Repeated direct targets retain separate coordinates. Preview consent items and candidate hashes remain transient; stored package hashes/frozen_at remain NULL.
- Writes use READ COMMITTED and the literal lexically ordered inventory as FIRST SQL, then timeouts, request advisory exclusion and manuscript→Publication→package row order. Completed replay and ordinary reads use one REPEATABLE READ, READ ONLY snapshot with protected nested readers. Only SQLSTATE 40001/40P01 retry, at most three fresh write UoWs.
- Terminal event integrity uses an immediate AFTER UPDATE trigger ordered before immediate package constraint checks. The guarded update creates immutable transition evidence in the same statement; the Application append port verifies the exact saved actor/time/reason/attribution. Transaction-local command context is input only, never deferred authority. Rewriting that context cannot replace the event. Normal-role tests cover both deferred and already-IMMEDIATE modes.
- Retained reads recompute hashes/history while reporting unavailable bytes as diagnostics and suppressing candidate hashes. Fresh admission rejects unavailable bytes. Byte contradictions remain provenance failures. Readback instants normalize to UTC, including a non-UTC database session.

## Existing equivalents and compatibility updates

- Existing artifact placement discriminator is `artifact_role`; it supplies FIGURE/TABLE projection. OTHER fails closed.
- S1 authored ordinals are 1-based; transient consent ordinals are authored-order 0-based.
- Existing `UnitOfWork.begin_formal_read()` is the lock-free snapshot setup equivalent used by public reads/replay. The new repository also exposes separate prepare_read/prepare_write methods.
- Reused S1's plain in-UoW material verifier, never its public read services. Reused B04 closure verification with an opt-in `require_current=False` for retained exact context; B04's public/default current-pointer behavior is unchanged. Missing-byte handling is confined to B15 verifier subclasses.
- Updated head/inventory expectations by values/appended entries. S1's old assertion that the future prepared-submission module is absent now expects the authorized B15 module to exist; its four-method authorship boundary and no-transport assertions remain.

## Observed verification

Exact commands and captured outputs: [verification transcript](B15_S2_verification.txt).
Actual backend wait witnesses, R4 transaction/expiry/wait/acquisition/final-check instants and zero failed effects: [wait evidence](B15_S2_wait_evidence.txt).

| Check | Observed result |
| --- | --- |
| Ruff | All checks passed |
| Ruff format | 654 files already formatted |
| Pyright | 0 errors, 0 warnings, 0 informations |
| Unit + architecture | 5,148 passed; 43 warnings |
| B15 six PostgreSQL suites | 72 passed; 149 warnings |
| B15 non-UTC session follow-up | 1 passed; 2 warnings |
| B15 item/consent rollback and direct-SQL root follow-up | 5 passed; 10 warnings |
| S1/B04/B12/B13 PostgreSQL regressions | 250 passed; 632 warnings |
| Updated migration expectation checks | 14 passed; 46 warnings |
| Repeated R4/deadlock witness selection | 4 passed, 28 deselected; 8 warnings |

The B15 runs cover 78 distinct PostgreSQL cases (72 + 1 + 5); the witness selection repeats existing cases. PostgreSQL 18 is checked by the clean migration test. Warnings include existing Alembic path_separator deprecations and a prerequisite internal-review execution_options warning. No whole-suite run was performed.

Development iterations found and corrected missing test imports, an incorrect expected lock-wait kind, version-overflow handling, unavailable-byte race replay and a caller-writable transition observation. Earlier failures are not reported as passing runs. Final results above are actual focused run outputs.

Read-only Application and migration reviews found no remaining P0/P1 after fixes. No branch, commit or push was created. This is S2 implementation evidence, not full PR2-17/Phase-2 acceptance or a freeze/send gate.

## Reviewer follow-up

- B07 failed at the table-set assertion **before downgrade ran**. Its expected
  inventory now appends exactly the four B15 tables. The upgrade/downgrade
  assertions, FK checks and trigger checks are preserved. The corrected case and
  B15 clean/populated downgrade tests: **3 passed, 12 warnings**.
- The requested CLI sequence `uv run alembic upgrade head && uv run alembic
  downgrade -1 && uv run alembic upgrade head` completed with **exit 0** against a
  disposable PostgreSQL **18.6** test database. [Complete output](B15_S2_review_roundtrip.txt).
  `test_populated_downgrade_refuses` in `test_b15_package_schema.py:165` verifies
  that package rows remain after refusal. No existing migration was edited.
- The cited ownership node passed **three isolated working-tree runs**, each
  **1 passed, 1 warning**, before its controller was changed. A separate archive
  of base `fa9c43eac6ebdd59fc4684faafb7be5871c2dde5`, importing its own source and
  using migration head 0059, passed **31 isolated runs**. The original failure
  remains unreproduced; this is not proof of a pre-existing flake.
- The race controller now optionally pauses the winner **after durable admission
  commit** until competing admission finishes, following the existing sibling
  race helper. Only the competing-execute test opts in. This controls incidental
  overlap with later dispatch transactions without changing production code,
  SQLSTATE retry limits, observed PostgreSQL wait assertions, or expected results.
  The complete ownership-race file: **50 passed, 50 warnings**.
- Removed `_write`'s replay `pass` branch. Race replay still leaves the writer UoW
  before its final read snapshot. Admission checks precede material inspection;
  separate checks immediately before effects and after deferred constraints are
  intentional under guide §12.2, since closure/CAS inspection can outlive a credential.
  Focused service/replay suites: **61 passed, 124 warnings**.
- FIRST-SQL/isolation tests now cover **prepare, consent and withdrawal** separately
  (`test_write_first_sql_inventory_and_read_committed`, concurrency test line 103;
  the first-statement assertion is line 142). Seven read/replay modes are checked
  for SQL exclusion locks/writes at line 63. The snapshot test at line 618 asserts
  REPEATABLE READ / READ ONLY and queries **pg_locks at line 658**, then proves a
  concurrently committed phantom is invisible in the retained snapshot. The
  combined proof selection: **11 passed, 22 warnings**.
- Persistence inventory/read setup is in
  `src/researchbase/persistence/prepared_submission_repository.py`; protected
  snapshot setup and opt-in error mappings are in `src/researchbase/persistence/uow.py`.
  These are included in the repository diff and the executable lock tests above.

[Exact commands and captured focused/base outputs](B15_S2_review_verification.txt).
Static checks pass: Pyright **0 errors/warnings/informations**, Ruff format
**654 files already formatted**, Ruff **all checks passed**. The required full
runner remains blocked by the environment and is explicitly **not PASS**.
