# B32 first-slice evidence — 2026-10-19

Owner authorization: B32 proposal first slice, tests only. The proposal status now
reads `APPROVED by owner 2026-10-19 — first slice authorized for implementation`.
No production source, dependency, schema, migration, branch or commit was changed.

The new unit file independently pins the three purpose/target/capability/receipt/
result mappings, closed DTO and decoder behavior, request material, unchanged R3
vectors, review bounds, and both transport error mappings including the sanitized
unexpected-error fallback. The new architecture file pins literal lock inventories,
transaction modes, shared Application delegates and bounded absence of transport
imports/calls and explicit locks/writes from formal read roots.

B13/B14/B17 additions use existing owning Application fixtures. They check approval
without effects, ACTIVE manuscript grant substitution into release, PREPARE grant
substitution into READY, local READY receipt/event links without package creation,
separate PREPARE consumption preserving READY history, cross-owner key conflict,
release/READY completed replay after actual DB expiry, and B17 exact reads/replay
using read-only REPEATABLE READ with no explicit locks or writes. Existing schema,
race, rollback, manifest, consent and replay suites supply the remaining witnesses.

Inventory: actual head `0068_b21_unresolved_capture`; PostgreSQL **18.6 (Homebrew)**.
`catalog.txt` records read-only inspection of an existing disposable test database
at that head, including concrete receipt FKs/XOR and the named deferred graph
triggers. No migration inventory/head update was needed.

Naming/location reconciliation: all guide owner and test paths exist. Publication's
existing domain material lives in `domain/manuscript.py`; the bounded import check
uses that file alongside `application/publication.py`. READY lifecycle links use
`publication_lifecycle_events.basis_grant_consumption_id`; package receipt linkage
uses `approval_grant_consumptions.result_prepared_submission_version_id`. Tests join
these existing concrete FKs, rather than assuming receipt columns on the package.

All commands below ran from the repository root with this environment prefix:

```sh
export UV_CACHE_DIR=/private/tmp/rb-b32-uv-cache
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane48'
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
```

The installed canonical uv environment was reused with `--no-sync`; dependency
files were untouched. Pyright's explicit environment path matches that environment.

| Exact command | Observed result | Evidence |
| --- | --- | --- |
| `uv run --no-sync ruff check .` | PASS: All checks passed | `ruff-check.txt` |
| `uv run --no-sync ruff format --check .` | PASS: 738 files already formatted | `ruff-format.txt` |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS: 0 errors, 0 warnings, 0 informations | `pyright.txt` |
| `uv run --no-sync pytest tests/unit tests/architecture` | PASS: 5,805 passed, 49 warnings in 76.20s | `unit-architecture.txt` |
| `uv run --no-sync pytest tests/unit/phase2/test_b32_approval_separation.py tests/architecture/test_b32_boundaries.py` | PASS: 168 passed in 0.80s | `new-unit-architecture.txt` |
| `uv run --no-sync pytest tests/integration/phase2/test_b13_grant_consumption.py -k b32_manuscript` | PASS: 2 passed, 10 deselected, 8 warnings in 3.58s | `active-grant-substitution.txt` |
| `git diff --check` | PASS: exit 0, no output | observed directly |

The final two focused commands verify the minor review refinements made while the
broader runs were active: purpose case checks use their matching target type, and
both manuscript substitution cases use ACTIVE grants. Earlier focused runs found
new-test construction/source-location mistakes; those tests were corrected without
production repairs. The seven-case initial PostgreSQL run in `new-postgresql.txt`
passed before the additional two expiry tests were added; the owner run below is
the comprehensive bounded PostgreSQL evidence.

Focused PostgreSQL owner command (execution, not collection):

```sh
uv run --no-sync pytest tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_b13_grant_*.py tests/integration/phase2/test_b14r_*.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b14_ready_*.py tests/integration/phase2/test_b17_*.py
```

Result: **PASS — 412 passed, 1,554 warnings in 918.26s (0:15:18)**;
see `postgresql-owners.txt`. The warnings are Alembic configuration deprecations
and the existing fixture-path SQLAlchemy isolation-option warning; no test failed
or skipped. The consuming-effect SQL/isolation witnesses passed unchanged.

Read-only sub-agent review found no open P0/P1 in the additions. The identified
case-sensitivity weakness and consumed-grant fixture limitation were corrected and
rerun. Source inspection is a bounded boundary check; actual SQL/isolation evidence
comes from the PostgreSQL suites. The full suite was deliberately not run: the
surrounding loop owns it. This evidence does not claim full Phase 2 acceptance or
external submission/delivery. Stop after this slice.
