# PR2-10 conditional slice 02 evidence

Base `d765db625c45ccafa855b1996906bd337978b33b`; implementation
`1cf74d9dc9423b7d557df4370ec88e4f80dc08ee`; reviewed remediation
`780d0ca27b0a902cdaf247f794680abb67d8b480`. Branch
`feature/pr2-10-persistence` in worktree `worktrees/pr2-10-persistence`.
The separate evidence commit is recorded in the run index, avoiding a
self-referential SHA.

## Scope and verification

The scope is frozen in `PR2-10-conditional-slice-02.md`. Migration 0032
adds the admitted typed discussion aggregate, exact version references,
immutable turns/citations and durable command receipts. Authenticated
Application commands create, append, close and read. Derived transcript and
concept-map candidates are rebuilt on readback; promotion always rejects.
No ArtifactVersion or ResearchSummary is persisted by this slice.

The test cluster was PostgreSQL 18 on port 55442, PGDATA
`/private/tmp/rb-m3-postgres`, system ID `7695073913076924777`, socket
`/private/tmp`, peer user `onephone`. Before testing it contained only the
default databases. The fixture checked this server and the admin database,
created a unique empty `researchbase_pr210_test_<uuid>` database per test,
upgraded it to `0032_pr2_10_discussion`, and dropped it in `finally`.

Command: `RB_PR210_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -s -p no:cacheprovider tests/integration/phase2/test_pr2_10_discussion_persistence.py`.
Final exit 0: nine test dots, nine database creates, nine installed 0032
revisions, nine drops. The after-test database list was again exactly
`postgres`, `template0`, `template1`. The tests cover durable readback and
restart, exact frozen references, deterministic artifact candidate hashes,
idempotency and concurrent append, unauthorized access and promotion denial,
rollback, immutable history, citation sealing and close time validity.

Full raw logs and SHA-256:

| Log | SHA-256 | Result |
|---|---|---|
| `PR2-10-slice-02-pg-output-initial.txt` | `a28f2e70c0b367247d25d66d1a5318fd168395d9d0a593bdaf960f43af8c9813` | Initial focused run |
| `PR2-10-slice-02-pg-output-final.txt` | `37a56fc386aeefd4d0c0baa4a093d07c1eefee5246242ec87715675f0b4af17a` | Initial 7-test candidate, exit 0 |
| `PR2-10-slice-02-pg-output-remediation.txt` | `be33d7a38f60eb0dde1c7319ca79866faee57e008ea0e095efa777e9a66f5606` | Intermediate trigger failure, exit 1; preserved |
| `PR2-10-slice-02-pg-output-remediation-final.txt` | `0deac6956f504282fa5772c69eeca6a4e0045851373e7e4355e5bafa07cab510` | Final 9-test run, exit 0 |

The two new P1 regression tests were run before the remediation and both
failed as expected (exit 1), proving the original defects. An intermediate
trigger revision then failed because PL/pgSQL referenced `NEW.turn_id` on a
non-citation table; nested trigger branching corrected that failure.

Focused unit/architecture/M2/M3 registration regression command:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_06_transport_boundary.py tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'`.
Result: 115 passed, exit 0. Ruff on changed Python files: all checks
passed. Pyright with the shared Python 3.12.14 interpreter explicitly set
as `--pythonpath`: 0 errors, 0 warnings. The two established
execution-service cancellation failures and one stale migration-list
assertion remain failures, excluded from the pass count.

Read-only retained M3 `pg_dump --data-only --no-owner --no-privileges`
excluding only random restrict/unrestrict lines yielded SHA-256
`667463cbab78976953066e11f8ccebe432a4aa7c0bc2489c2b3fab3aff9ad589`,
equal to the accepted baseline. Its CAS has zero files. Four retained M2
databases remain at `0029_metadata_observations`; retained M3 remains at
`0031_m3_snapshot_relation_cardinality`. No retained writes occurred.

## Independent review

First independent read-only reviewer BLOCKED `1cf74d9` with two P1s:
late direct citation insertion could mutate a committed turn; direct close
could use a timestamp before its latest turn and break readback. Both were
fixed in `780d0ca` with database guards and PostgreSQL regression tests.
The fresh independent read-only remediation reviewer reported PASS with no
open P0/P1. This is conditional technical development only; formal PR2-10
admission requires separately authorized derived ArtifactVersion persistence,
ResearchSummary and the applicable blocked upstream gates.

M3 Human Gate BLOCKED; M3 Final Acceptance NOT APPROVED; TDG2 formal
activation NOT AUTHORIZED; formal PR2-06 acceptance NOT APPROVED; formal M4
acceptance NOT AUTHORIZED. No provider contact or retained deployment change.
