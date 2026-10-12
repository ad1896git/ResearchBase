# PR2-12 FIX1 conditional evidence

Accepted development base: `088bb8868648c853e8c321321f7aba799ef23c12`.
Previously blocked implementation: `b41e5c8461df8a821873295f42c75d76cf7327ed`.
Previously blocked evidence HEAD: `11c0519f569358e2ff596c8cac6f08d7ea16c407`.
Corrected implementation: `3b1da88b133de9b215d0c850af21d76ae6cf88f2`.
This evidence commit is identified by the subsequent Git HEAD, not by a self-reference.

The frozen shared physical-schema rule in
`docs/architecture/13_Phase2_Schema_Field_Contract_v1.0.md` requires a
B-tree index on each foreign-key column unless it leads a stated unique
index. The pre-correction disposable PostgreSQL 55442 catalog inspection at
revision `0035_pr2_12_publication_draft` showed no qualifying index for
`publications.created_by`, `manuscript_versions.created_by`, or
`publication_lifecycle_events.actor_id`. Existing PK/unique indexes led on
other columns. Test databases were created only after verifying user,
database, port, PGDATA and system identifier `7695073913076924777`.

Migration diff: three nonunique, nonpartial, single-column B-tree indexes:

| Table | Index | Column |
| --- | --- | --- |
| publications | ix_pr212_publications_created_by | created_by |
| manuscript_versions | ix_pr212_manuscript_created_by | created_by |
| publication_lifecycle_events | ix_pr212_publication_event_actor | actor_id |

No column, table, constraint, trigger or other index definition changed.
Dropping the three PR2-12 tables in the existing empty-history downgrade
removes these indexes; the test compares the full public table and index
inventories to revision `0034_pr2_10_exact_transcript_binding` afterward.
The index test also checks the three actor FKs remain present, exact index
definitions, access method, uniqueness and predicate.

Verification:

- Before the migration correction, the new catalog assertion failed on both
  base→head and 0018→head paths because `publications.created_by` had no
  matching index (2 expected failures; exit 1).
- With both `RB_PR210_TEST_ADMIN_URL` and `RB_PR211_R2_TEST_ADMIN_URL` set to
  `postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442`,
  `uv run pytest -q tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py --tb=short`:
  **27 passed, exit 0**. This covers both upgrade paths, empty downgrade,
  and existing PR2-10/11/12 behavior.
- `uv run pytest -q tests/unit/phase2/test_pr2_11_r2_contract.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py --tb=short`:
  **16 passed, exit 0**.
- `uv run ruff check migrations/versions/0035_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py`:
  **pass, exit 0**.
- `uv run pyright src/researchbase/application/publication.py src/researchbase/persistence/publication_repository.py src/researchbase/persistence/uow.py`:
  **0 errors, 0 warnings, exit 0**.
- `git diff --check`: **pass, exit 0**.
- Read-only post-test catalog query on port 55442 returned **0** leftover
  PR2-12/PR2-11 disposable databases.

An initial broader test command omitted `RB_PR211_R2_TEST_ADMIN_URL`; its
PR2-11 fixture reported 14 setup errors, not code failures. A global
`uv run pyright` reported 95 errors in files outside this FIX1 change; scoped
production Pyright passed. The prior run's four architecture failures were
reproduced on the accepted baseline and remain failures; this FIX1 did not
rerun that suite. Two historical cancellation tests were not run here.

Fresh independent read-only reviewer of the frozen implementation SHA found
no P0/P1 blocker and reported conditional technical PASS. The reviewer
checked the shared physical rule, exact three indexes, catalog assertions,
upgrade/downgrade inventory restoration, and cumulative PR2-12 boundary;
they did not independently rerun tests.

No retained M2/M3 deployment write, production scientific schema change
outside the authorized PR2-12 migration, live provider contact, or formal
milestone promotion occurred. PR2-12 formal acceptance remains unapproved;
M3 Human Gate remains blocked.
