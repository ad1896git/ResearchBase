# PR3-03 evidence

## S1 — A1 retry (2026-10-22)

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

Baseline: `codex/phase3-wave3-base`, HEAD `93df5bb`. Initial working tree was clean.
Scope: owner-approved A1, literal forward-only 0080 migration, Appendix H mechanical
head maintenance, and this evidence. S2 and later steps are not implemented.

A1 wraps 13 previously unparenthesised CASE expressions in conditions across 17
physical lines in §§4.4–4.5. §4.1 triggers contain no CASE condition requiring a
change. Existing parenthesised expressions, assignments and other statements are
unchanged. Pack §13 lists every changed original line, function, before and after.
The remainder of the original pack is byte-for-byte unchanged. No G stop condition
was observed. SQL literals equal the amended pack statement text; only Python
literal boundaries wrap long lines. All 78 statements retain their SQL whitespace,
including long SQL lines; Python physical lines are at most 100 characters. There
are seven new functions, six replacements, nine new triggers, and no new deferred
trigger. Existing trigger identities remain in place. Ancestor migrations,
pyproject.toml and uv.lock are unchanged.

Environment setup before the first uv command (and inherited or explicitly set
for every subsequent uv command):

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
```

`RB_TEST_ADMIN_URL` was already explicitly selected by the runner. It names the
local PostgreSQL `postgres` admin database with role `researchbase`. The supplied
compile probe created and dropped a random disposable database. The metadata
query below confirms PostgreSQL 18.6 (server_version_num 180006), role researchbase
and UTF8; the compile probe independently asserts UTF8 on its disposable database.
No application database was used.

Console output below is the exact combined stdout/stderr; exit status is recorded
separately. Raw logs and helper scripts remain under ignored `tmp/pr3-03/`.

### uv sync --locked --group dev

```sh
uv sync --locked --group dev
```

Exit: `0`. Output:

```text
Resolved 38 packages in 10ms
Checked 34 packages in 3ms
```

### git diff --check HEAD

```sh
git diff --check HEAD
```

Exit: `0`. Output:

```text
```

### uv run ruff check .

```sh
uv run ruff check .
```

Exit: `0`. Output:

```text
All checks passed!
```

### uv run ruff format --check .

```sh
uv run ruff format --check .
```

Exit: `0`. Output:

```text
889 files already formatted
```

### uv run pyright

```sh
uv run pyright
```

Exit: `0`. Output:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

### uv run alembic heads

```sh
uv run alembic heads
```

Exit: `0`. Output:

```text
0080_capability_gateway (head)
```

### PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py

```sh
PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py
```

Exit: `0`. Output:

```text
COMPILED pr303_immutable
COMPILED pr303_policy_insert_guard
COMPILED pr303_permission_insert_guard
COMPILED pr303_invocation_guard
COMPILED pr303_ref_insert_guard
COMPILED pr303_event_insert_guard
COMPILED pr303_validate_gateway
COMPILED pr301_task_guard
COMPILED pr301_receipt_insert_guard
COMPILED pr304_child_guard
COMPILED pr304_validate_safety
COMPILED pr301_graph_final_guard
COMPILED pr301_receipt_complete
COMPILE_GATE 13/13
```

[Long output trimmed; commands, exit codes and counts retained.]


### uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Exit: `0`. Output:

```text
collected 351 items
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 351 passed, 50 warnings in 20.00s =======================
```

[Long output trimmed; commands, exit codes and counts retained.]


### uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py

```sh
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 3 items

tests/unit/test_ci_migration_head.py .                                   [ 33%]
tests/unit/test_batch_c_migration_history.py .                           [ 66%]
tests/unit/test_task12_migration_history.py .                            [100%]

=============================== warnings summary ===============================
tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql
tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 3 warnings in 0.10s =========================
```

### uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py

```sh
uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 15 items

tests/unit/phase2/test_pr2_04_r8a_host_topology.py ........              [ 53%]
tests/unit/phase2/test_pr2_20_inventory.py ......                        [ 93%]
tests/unit/phase2/test_pr2_04_static_acceptance.py .                     [100%]

=============================== warnings summary ===============================
tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 15 passed, 2 warnings in 8.10s ========================
```

### uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 14 items

tests/integration/phase3/test_pr3_00_bootstrap.py ......                 [ 42%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [ 64%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 78%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_00_bootstrap.py: 14 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 14 passed, 42 warnings in 11.03s =======================
```

### uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py

```sh
uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 145 items

tests/integration/phase2/test_pr2_03_review_guards.py .................. [ 12%]
...............                                                          [ 22%]
tests/integration/phase2/test_pr2_04_execution_migration.py .....        [ 26%]
tests/integration/phase2/test_pr2_04_migration_coverage.py ...........   [ 33%]
tests/integration/phase2/test_pr2_15_decision_schema.py ...              [ 35%]
tests/integration/phase2/test_revision_action.py ....................... [ 51%]
................................                                         [ 73%]
tests/integration/phase2/test_pr2_17_authorship_schema.py .............. [ 83%]
........................                                                 [100%]

=============================== warnings summary ===============================
tests/integration/phase2/test_pr2_03_review_guards.py: 42 warnings
tests/integration/phase2/test_pr2_04_execution_migration.py: 11 warnings
tests/integration/phase2/test_pr2_04_migration_coverage.py: 24 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 13 warnings
tests/integration/phase2/test_revision_action.py: 173 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 51 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 145 passed, 314 warnings in 121.47s (0:02:01) =================
```

### PostgreSQL metadata

Exact command:

```sh
uv run python tmp/pr3-03/pg_metadata.py
```

The helper reads `RB_TEST_ADMIN_URL` and executes `SHOW server_version`,
`SELECT current_user` and `SHOW server_encoding` through SQLAlchemy, then disposes
its engine. Exit: `0`. Exact output:

```text
SERVER_VERSION 18.6 (Homebrew)
DATABASE_ROLE researchbase
SERVER_ENCODING UTF8
```

### Pack and SQL literal audit

Exact command:

```sh
.venv/bin/python tmp/pr3-03/audit.py
```

The helper compares original pack lines from `git show HEAD:...` against the
amended original portion, allowing only inserted parentheses at the 17 listed
lines. It extracts every authoritative statement from §§2/2.1/3/4.4/4.5/4.1 and
compares it to the migration's evaluated SQL constants in execution order. It
also checks physical source length and absence of noqa. Exit: `0`. Exact output:

```text
PACK_A1_ONLY 17 changed lines; 13 CASE expressions; original remainder unchanged
SQL_LITERAL_PARITY 78/78 statements exactly equal
MIGRATION_MAX_PHYSICAL_LINE 100
NO_NOQA true; lint configuration unchanged
```

### Formatting correction during preparation

The first ordered gate attempt stopped at `uv run ruff format --check .` with
exit `1`, before Pyright, heads or the probe ran. Exact output:

```text
Would reformat: tests/integration/phase3/test_pr3_01_migration.py
Would reformat: tests/integration/phase3/test_pr3_02_s1_migration.py
2 files would be reformatted, 887 files already formatted
```

The preceding diff and lint commands had exits 0 (empty diff output and
`All checks passed!`). Exact correction command:

```sh
uv run ruff format tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
```

Exit `0`; output `2 files reformatted`. Only the changed head assertions were
collapsed by Ruff. The complete ordered static gate was then rerun with the
passing outputs above. No lint configuration or exclusion was changed.

### Appendix H PostgreSQL setup

Exact wrapper invocation:

```sh
PYTHONPATH=. uv run python tmp/pr3-03/run_h_postgres.py
```

The wrapper uses the existing `disposable_database("researchbase_pr212_test_")`
helper, exports its yielded URL as DATABASE_URL only for the focused pytest
subprocess above, and drops that runtime database afterwards. Each phase2 fixture
creates its own isolated test database using the existing plumbing. RB_TEST_ADMIN_URL
continues to name postgres. The wrapper's complete exact output:

```text
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_a99402429530431fb059f346edfab6e6
$ uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 145 items

tests/integration/phase2/test_pr2_03_review_guards.py .................. [ 12%]
...............                                                          [ 22%]
tests/integration/phase2/test_pr2_04_execution_migration.py .....        [ 26%]
tests/integration/phase2/test_pr2_04_migration_coverage.py ...........   [ 33%]
tests/integration/phase2/test_pr2_15_decision_schema.py ...              [ 35%]
tests/integration/phase2/test_revision_action.py ....................... [ 51%]
................................                                         [ 73%]
tests/integration/phase2/test_pr2_17_authorship_schema.py .............. [ 83%]
........................                                                 [100%]

=============================== warnings summary ===============================
tests/integration/phase2/test_pr2_03_review_guards.py: 42 warnings
tests/integration/phase2/test_pr2_04_execution_migration.py: 11 warnings
tests/integration/phase2/test_pr2_04_migration_coverage.py: 24 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 13 warnings
tests/integration/phase2/test_revision_action.py: 173 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 51 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 145 passed, 314 warnings in 121.47s (0:02:01) =================

EXIT 0
DISPOSABLE_DROPPED: researchbase_pr212_test_a99402429530431fb059f346edfab6e6
```

### Counts and disposition

- `uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`: `collected 351 items`; `====================== 351 passed, 50 warnings in 20.00s =======================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py`: `collected 3 items`; `======================== 3 passed, 3 warnings in 0.10s =========================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py`: `collected 15 items`; `======================== 15 passed, 2 warnings in 8.10s ========================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py`: `collected 14 items`; `======================= 14 passed, 42 warnings in 11.03s =======================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py`: `collected 145 items`; `================ 145 passed, 314 warnings in 121.47s (0:02:01) =================`; exit `0`.

The required S1 gate commands and the additional Appendix H PostgreSQL regressions
are recorded above. There are no failures or skips in the final focused runs.
Existing Alembic deprecation warnings and Pyright's version notice are retained
verbatim. Full suite/six shards: NOT RUN; owned by the external check loop.
Overall PR3-03 acceptance and independent review remain PENDING. No commit, push,
branch creation, later implementation or .git write was performed. Git commands
reported no lock or sandbox error.

### Exact changed paths

```text
 M .github/workflows/ci.yml
 M docs/phase3/PR3-03-contract-freeze.md
 M tests/architecture/test_b02_strategy_promotion_boundaries.py
 M tests/architecture/test_b04_boundaries.py
 M tests/architecture/test_b05_review_boundaries.py
 M tests/architecture/test_b20_screening_boundaries.py
 M tests/architecture/test_basic_approval.py
 M tests/architecture/test_import_boundaries.py
 M tests/architecture/test_pr3_02_s1_boundaries.py
 M tests/fixtures/phase2_static_baseline.json
 M tests/integration/phase2/test_pr2_03_review_guards.py
 M tests/integration/phase2/test_pr2_04_execution_migration.py
 M tests/integration/phase2/test_pr2_04_migration_coverage.py
 M tests/integration/phase2/test_pr2_15_decision_schema.py
 M tests/integration/phase2/test_pr2_17_authorship_schema.py
 M tests/integration/phase2/test_revision_action.py
 M tests/integration/phase3/test_pr3_00_bootstrap.py
 M tests/integration/phase3/test_pr3_01_migration.py
 M tests/integration/phase3/test_pr3_02_s1_migration.py
 M tests/integration/phase3/test_pr3_04_migration.py
 M tests/unit/phase2/test_pr2_04_r8a_host_topology.py
 M tests/unit/phase2/test_pr2_20_inventory.py
 M tests/unit/test_batch_c_migration_history.py
 M tests/unit/test_task12_migration_history.py
?? docs/phase3/PR3-03-evidence.md
?? migrations/versions/0080_capability_gateway.py
```

Final check after evidence generation: `git diff --check HEAD`, exit `0`,
stdout empty, stderr empty.

### S1 independent verification at HEAD 43cae25 (2026-10-22)

Verification only; starting HEAD `43cae2575d665a6512577d93985db01a1c6c38bc`.
Initial `git status --short` exited `0` with no output (clean working tree).
The following cache setting was applied before every uv command:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
```

Commands below ran in the requested order. Output blocks contain the observed
combined command output; empty output is stated explicitly.

#### `uv sync --locked --group dev`

Exit code: `0`.

```text
Resolved 38 packages in 2ms
Checked 34 packages in 0.70ms
```

#### `git diff --check 93df5bb HEAD`

Exit code: `0`.

Output: empty.

#### `uv run ruff check .`

Exit code: `0`.

```text
All checks passed!
```

#### `uv run ruff format --check .`

Exit code: `0`.

```text
889 files already formatted
```

#### `uv run pyright`

Exit code: `0`.

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### `uv run alembic heads`

Exit code: `0`.

```text
0080_capability_gateway (head)
```

#### `PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py`

Exit code: `1`.

```text
Traceback (most recent call last):
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py", line 11, in <module>
    with disposable_database("researchbase_pr212_test_") as url:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/contextlib.py", line 137, in __enter__
    return next(self.gen)
           ^^^^^^^^^^^^^^
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/tests/disposable_postgres.py", line 57, in disposable_database
    url = admin_url(*aliases)
          ^^^^^^^^^^^^^^^^^^^
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/tests/disposable_postgres.py", line 34, in admin_url
    pytest.fail("Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL")
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/_pytest/outcomes.py", line 177, in fail
    raise Failed(msg=reason, pytrace=pytrace)
Failed: Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL
```

Verification stopped at the compile probe's first failure, as required. The probe
failed before opening a disposable database. PostgreSQL version, role and encoding
were not observed. No `COMPILED` lines or `COMPILE_GATE 13/13` were produced.
This run does not establish PostgreSQL compilation success.

The following requested commands were NOT RUN after that failure:

- `uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`

- `uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py`

- `uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py`

- `uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py`

Test counts: no pytest command ran; passed/failed/skipped counts are unavailable.
AST literal-equivalence script and comparison: NOT RUN because verification stopped
at the compile-probe failure. The reported regex mismatches remain unverified;
no MATCH/MISMATCH result is claimed. No six-shard or whole-suite run was performed.
No product, migration, pack or test file was changed. No commit, push or branch
creation was performed. This verification is incomplete; S1 gate success is not claimed.

Changed path for this verification: `docs/phase3/PR3-03-evidence.md` only.


### S1 independent verification follow-up after reviewer findings (2026-10-22)

This follow-up supplies the results missing from the preceding stopped attempt.
That attempt's failure remains recorded above; its NOT RUN statements describe
that attempt only. HEAD remains `43cae2575d665a6512577d93985db01a1c6c38bc`.
Only this S1 evidence section is edited. No product, migration, pack or test
file was changed. The helper script is under ignored `tmp/`.

README.md lines 113–126 and compose.yaml identify the local disposable PostgreSQL
admin selector. The following settings were applied before every uv command:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export RB_TEST_ADMIN_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres"
```

The supplied compile probe exited 0, compiled all thirteen bodies and printed
`COMPILE_GATE 13/13`. It observed server_version_num `180006` and role
`researchbase`, and its UTF8 assertion passed. Because the supplied probe does
not print encoding, the separate disposable-database metadata query below
records the explicit `SERVER_ENCODING UTF8` output on the same server identity.

The phase2 group's first run below failed (14 passed, 1 failed, 0 skipped) because
this evidence addition had an extra blank line at EOF. That evidence-only defect
was removed, and the exact group was rerun successfully. Both outputs are retained.

Final pytest results for the four requested groups:

| Group | Passed | Failed | Skipped | Exit code |
| --- | ---: | ---: | ---: | ---: |
| Architecture and unit architecture | 351 | 0 | 0 | 0 |
| Migration history | 3 | 0 | 0 | 0 |
| Phase2 (rerun after evidence whitespace correction) | 15 | 0 | 0 | 0 |
| Phase3 PostgreSQL integration | 14 | 0 | 0 | 0 |

The AST script `tmp/pr303_s1_ast_equivalence.py` parses module-level SQL constants
with `ast.parse` and evaluates string literals with `ast.literal_eval`; tuple
references resolve only to those evaluated constants. It never executes/imports
the migration. It extracts every CREATE [OR REPLACE] FUNCTION from SQL fences in
the contract and splits SQL statements outside quoted strings and dollar bodies.
Normalization removes SQL comments and whitespace only: no case folding,
punctuation replacement or semantic rewriting. SQL comments use a quote-aware
scanner with nested block-comment support. It checks all thirteen function names
and all other DDL/index/extension/trigger statements as a multiset, including
duplicate cardinality, against the frozen §§2–4.5 inventory. The later attachment
audit and amendment before/after excerpts are not additional migration statements.

Observed equivalence: 13/13 function bodies MATCH; all 78/78 SQL statements MATCH;
zero MISMATCH results. The director's reported 8-of-8 regex mismatches are not real
literal differences under the requested normalization. No correction was made to
SQL or the pack. There is no differing position to report.

Exact combined stdout/stderr and exit codes follow, in execution order.

#### Follow-up command 1

```sh
PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py
```

Exit code: `0`.

```text
COMPILED pr303_immutable
COMPILED pr303_policy_insert_guard
COMPILED pr303_permission_insert_guard
COMPILED pr303_invocation_guard
COMPILED pr303_ref_insert_guard
COMPILED pr303_event_insert_guard
COMPILED pr303_validate_gateway
COMPILED pr301_task_guard
COMPILED pr301_receipt_insert_guard
COMPILED pr304_child_guard
COMPILED pr304_validate_safety
COMPILED pr301_graph_final_guard
COMPILED pr301_receipt_complete
COMPILE_GATE 13/13
```

[Long output trimmed; commands, exit codes and counts retained.]


#### Follow-up command 2

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Exit code: `0`.

```text
collected 351 items
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 351 passed, 50 warnings in 18.10s =======================
```

[Long output trimmed; commands, exit codes and counts retained.]


#### Follow-up command 3

```sh
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 3 items

tests/unit/test_ci_migration_head.py .                                   [ 33%]
tests/unit/test_batch_c_migration_history.py .                           [ 66%]
tests/unit/test_task12_migration_history.py .                            [100%]

=============================== warnings summary ===============================
tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql
tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 3 warnings in 0.10s =========================
```

#### Follow-up command 4

```sh
uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit code: `1`.

The failing run's output is encoded as a JSON string so traceback whitespace
is preserved exactly without introducing trailing whitespace into this file.

```text
collected 15 items
                command=arguments,
                exit_code=result.returncode,
        # Exact file/rule/message multisets cap inherited debt; new or duplicated errors fail.
        assert not (Counter(lint_diagnostics) - Counter(map(tuple, baseline.get(\"ruff\", []))))
        assert not (Counter(type_diagnostics) - Counter(map(tuple, baseline[\"pyright\"])))
E       AssertionError: assert 2 == 0
tests/unit/phase2/test_pr2_04_static_acceptance.py:81: AssertionError
=============================== warnings summary ===============================
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
FAILED tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
=================== 1 failed, 14 passed, 2 warnings in 7.62s ===================
```

[Long output trimmed; commands, exit codes and counts retained.]


#### Follow-up command 5

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 14 items

tests/integration/phase3/test_pr3_00_bootstrap.py ......                 [ 42%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [ 64%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 78%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_00_bootstrap.py: 14 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 14 passed, 42 warnings in 10.83s =======================
```

#### Follow-up command 6

```sh
uv run python tmp/pr303_s1_ast_equivalence.py
```

Exit code: `0`.



[Long output trimmed; commands, exit codes and counts retained.]


#### Follow-up command 7

```sh
uv run python - <<'PY'
import os
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database
with disposable_database('researchbase_pr212_test_') as url:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            for label, query in [('SERVER_VERSION', 'SHOW server_version'), ('SERVER_VERSION_NUM', 'SHOW server_version_num'), ('DATABASE_ROLE', 'SELECT current_user'), ('SERVER_ENCODING', 'SHOW server_encoding')]:
                print(label, connection.execute(text(query)).scalar_one())
    finally:
        engine.dispose()
PY
```

Exit code: `0`.

```text
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_5517cdf713094ca092ded65a3f90ea04
SERVER_VERSION 18.6 (Homebrew)
SERVER_VERSION_NUM 180006
DATABASE_ROLE researchbase
SERVER_ENCODING UTF8
DISPOSABLE_DROPPED: researchbase_pr212_test_5517cdf713094ca092ded65a3f90ea04
```

#### Follow-up command 8

```sh
uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 15 items

tests/unit/phase2/test_pr2_04_r8a_host_topology.py ........              [ 53%]
tests/unit/phase2/test_pr2_20_inventory.py ......                        [ 93%]
tests/unit/phase2/test_pr2_04_static_acceptance.py .                     [100%]

=============================== warnings summary ===============================
tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 15 passed, 2 warnings in 7.91s ========================
```

#### Follow-up command 9 — historical combined capture withdrawn

The original chain did not retain independent command exit codes. Its combined
result is not independent evidence for either command. Separate S8 executions
below supersede it. No historical per-command output has been invented.
No six-shard or full-suite run was performed in that handoff.

Changed tracked path: `docs/phase3/PR3-03-evidence.md` only.
Ignored verification helper: `tmp/pr303_s1_ast_equivalence.py`.

## S2 — Repository ports, composed locks and stored-row reads

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

Date: 2026-10-22. Baseline HEAD: `52d984ab8c5c1cd424656e6da3a1000fae06b70b`
(S1 evidence baseline supplied by the owner). **S2 focused checks passed.**
S3 has not started. Overall PR3-03 acceptance, independent review and the external
six-shard check remain **PENDING**; no full suite or shard was launched here.
No commit, branch creation or push was performed. Work remains uncommitted.

The gateway adapter composes the delivered safety prefix and task-row phase.
Its first statement is the literal eighteen-parent SHARE; project, pr301 command,
pr301 task, target pr302 actor and target pr302 version keys precede row locking.
Version-to-actor resolution is unlocked after the prefix, and version is reread
under both target keys after availability locking. Registration omits both target
keys, availability locking and version reads. Eleven blocking acquisitions each
have an immediately following callback; registration has eight. A callback may
terminate the recipe before any subsequent SQL. Existing safety `lock_write`
retains its combined recipe and callbacks. No gateway command admission,
accounting, dispatch, S3 DTOs, execution identity or write operation is added.

Closed TypedDict stored rows cover all five new tables and every stored receipt
and task-event column. SQL adapters return detached dictionaries/lists with UTC
normalization; no Session, ORM entity or result cursor crosses the port.
Permissions use canonical tuple order; refs use direction/family/version UUID;
events use sequence; receipt lookup uses project/authenticated actor/command.
The UoW and adapters construct without SQL, including entering an unbound Session
UoW. Metadata includes new columns, relationships, unique keys, indexes and CHECKs;
accepted migrations and the frozen pack were not edited.

### Changed paths and Deviations

Every changed or new nonignored path:

- `src/researchbase/agent_runtime/ports/gateway_repository.py` (new)
- `src/researchbase/agent_runtime/ports/task_safety_repository.py`
- `src/researchbase/persistence/capability_gateway_repository.py` (new)
- `src/researchbase/persistence/task_safety_repository.py`
- `src/researchbase/persistence/models.py`
- `src/researchbase/persistence/uow.py`
- `tests/unit/phase3/test_capability_gateway_repository.py` (new)
- `src/researchbase/persistence/research_task_repository.py` (Deviation S2-D1)
- `docs/phase3/PR3-03-evidence.md` (Deviation S2-D2)

**Deviation S2-D1 — resolved compatibility defect, extra read-adapter file.**
Scope: `research_task_repository.py`, explicit existing task-event column projection.
Evidence: frozen pack §3 adds nullable `result_tool_policy_id`,
`result_capability_invocation_id`, `result_capability_event_id` to task events;
S2 completion requires “existing ports/callers remain type-compatible.” Delivered
`research_task_repository.py:99–103` selected `SELECT * FROM {table}` while
`agent_runtime/application/research_task.py:450` constructs
`TaskEventRead(**r)`. The first extra PostgreSQL behavior run collected 33:
19 passed, 14 failed, 0 skipped, all failures reporting
`TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'`.
Action: current `research_task_repository.py:50/105` explicitly selects the existing
17-column planning event shape; the gateway's separate stored read includes all
20 columns. The command API/DTO and write behavior remain unchanged. The added
unit regression compares the projection against TaskEventRead's actual fields.
Disposition: fixed; the same PostgreSQL command now passes all 33, and the additional
planning Application/safety-query command passes 9. No architecture gap or waiver
is claimed. No S3 vocabulary was introduced to fix this.

**Deviation S2-D2 — owner-required evidence and ignored verification files.**
The task explicitly requires an S2 section in this evidence file, although the
plan lists that file under S8. Its change records only S2 work and does not start
S8 implementation. All supporting scripts, raw command output, diff and traces
are under ignored `tmp/pr3-03/`; uv's ignored cache is
`tmp/pr3-03-uv-cache/`. These are local verification artifacts, not runtime files.
The helper scripts are enumerated below. Disposition: recorded within the owner's
explicit evidence authorization; no contract/dependency/configuration changes.

### Observed checks and counts

Before every uv command, `UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"` was set
(the capture helper sets the equivalent absolute path in its subprocess environment).
Setup `uv sync --locked --group dev` exited 0, stdout exactly:

```text
Resolved 38 packages in 3ms
Checked 34 packages in 4ms
```

Setup stderr was empty. `pyproject.toml` and `uv.lock` are unchanged.
`command -v pg_dump` returned `/opt/homebrew/bin/pg_dump`; `pg_dump --version`
returned `pg_dump (PostgreSQL) 18.6 (Homebrew)`. PostgreSQL runs used the already
explicitly selected `RB_TEST_ADMIN_URL` for the local disposable admin database.
No application database or SQLite was used.

| Final distinct check group | Collected | Passed | Failed | Skipped | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| S2 repository unit tests | 29 | 29 | 0 | 0 | 0 |
| Required safety transport + PR3-04/S1 architecture | 14 | 14 | 0 | 0 | 0 |
| PostgreSQL bootstrap + PR3-01/04/S1 migrations | 14 | 14 | 0 | 0 | 0 |
| PostgreSQL safety Application + concurrency + replay | 33 | 33 | 0 | 0 | 0 |
| PostgreSQL planning Application + safety queries | 9 | 9 | 0 | 0 | 0 |
| **Total distinct final tests** | **99** | **99** | **0** | **0** | **0** |

The final required commands ran in the owner's prescribed order. Static checks
all exited 0: whitespace, Ruff, format (892 files), Pyright (0 errors), sole
Alembic head `0080_capability_gateway (head)`. Counts for non-pytest probes are
not pytest counts. The disposable metadata probe verifies 5/5 new tables and
7/7 nullable extensions and all six receipt/event extension indexes on PostgreSQL 18.6, role `researchbase`, UTF8: exact column
names/types/nullability, FK tuples/delete rules, unique tuples, index names/columns/
uniqueness and CHECK counts. It does not claim exhaustive trigger or lock behavior.

Earlier failures are retained below, not relabeled PASS: preliminary Pyright had
33 metadata typing errors, then 12 test-double typing errors; preliminary Ruff had
2 errors; preliminary unit runs had 25 passed/1 failed (26 collected, 0 skipped).
Metadata declaration/type fixes and the test-double casts resolved these. The
unit failure tried to resolve the existing raw-SQL-owned `source_versions` table
through incomplete historical ORM metadata; the corrected assertion checks the
actual FK target specifications, and real catalog parity independently verifies
all concrete targets. The first helper launch lacked the repository on PYTHONPATH
and exited 1 before DB access; the explicit `PYTHONPATH=.` rerun passed. The
19-pass/14-fail PostgreSQL run is S2-D1 above. A self-review added the six
receipt/event extension indexes to metadata. The expanded catalog probe initially
counted a PostgreSQL supporting UNIQUE constraint as an explicit index and failed
its helper assertion; filtering SQLAlchemy inspector `duplicates_constraint`
entries fixed that probe, whose subsequent exit-0 output is retained below. Later successful repeated gates
had 28 then 29 repository tests; those repeated counts are not added to 99.

### Exact command output archive

Each JSON record below preserves the exact command, exit code, stdout and stderr
(including trailing newlines/traceback whitespace). Empty strings mean no output.
This encoding avoids adding traceback trailing whitespace to this Markdown file.
No unrun command is marked PASS.

Initial metadata Pyright run, command `uv run pyright`, exit 1:

```text
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3234:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3240:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3244:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3248:69 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3250:52 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3252:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3264:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3268:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3272:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3276:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3280:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3291:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3306:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3321:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3340:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3342:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3344:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3346:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3348:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3350:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3352:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3354:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3356:35 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3360:35 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3364:35 - error: Cannot access attribute \"append_column\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3368:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3377:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3386:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3395:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3407:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3425:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3437:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3447:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"
33 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-preliminary.json`:

```text
    "command": "uv run ruff check .",
    "exit_code": 1,
  9 | | from sqlalchemy.exc import DBAPIError
 39 | | from researchbase.foundation.errors import ErrorCode, ResearchBaseError
Found 2 errors.
    "command": "uv run pyright",
    "exit_code": 1,
    "stdout": "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:183:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:190:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:196:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:203:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:215:36 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:218:38 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:235:37 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:245:46 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:323:26 - error: Argument of type \"() -> RecordingSession\" cannot be assigned to parameter \"session_factory\" of type \"(() -> Session) | sessionmaker[Session]\" in function \"__init__\"\n    Type \"() -> RecordingSession\" is not assignable to type \"(() -> Session) | sessionmaker[Session]\"\n      Type \"() -> RecordingSession\" is not assignable to type \"() -> Session\"\n        Function return type \"RecordingSession\" is incompatible with type \"Session\"\n          \"RecordingSession\" is not assignable to \"Session\"\n      \"FunctionType\" is not assignable to \"sessionmaker[Session]\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:325:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:326:36 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:375:32 - error: Cannot access attribute \"startswith\" for class \"_NoneName\"\n    Attribute \"startswith\" is unknown (reportAttributeAccessIssue)\n12 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 1,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 26 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 61%]\n.....F....                                                               [100%]\n\n=================================== FAILURES ===================================\n_ test_closed_stored_columns_match_inert_metadata[capability_invocation_refs-StoredInvocationRef] _\n\ntable = 'capability_invocation_refs'\nstored = <class 'researchbase.agent_runtime.ports.gateway_repository.StoredInvocationRef'>\n\n    @pytest.mark.parametrize(\n        \"table,stored\",\n        [\n            (\"agent_tool_policies\", port.StoredToolPolicy),\n            (\"agent_tool_policy_permissions\", port.StoredPermission),\n            (\"capability_invocations\", port.StoredInvocation),\n            (\"capability_invocation_refs\", port.StoredInvocationRef),\n            (\"capability_invocation_events\", port.StoredInvocationEvent),\n            (\"research_task_command_receipts\", port.StoredGatewayReceipt),\n            (\"research_task_events\", port.StoredTaskEvent),\n        ],\n    )\n    def test_closed_stored_columns_match_inert_metadata(table, stored):\n        mapped = Base.metadata.tables[table]\n        assert set(get_type_hints(stored)) == set(mapped.columns.keys())\n        assert stored.__required_keys__ == frozenset(mapped.columns.keys())\n        for fk in mapped.foreign_key_constraints:\n            assert fk.ondelete == \"RESTRICT\"\n>           assert fk.referred_table is not None\n                   ^^^^^^^^^^^^^^^^^\n\ntests/unit/phase3/test_capability_gateway_repository.py:349: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n.venv/lib/python3.12/site-packages/sqlalchemy/sql/schema.py:4797: in referred_table\n    return self.elements[0].column.table\n           ^^^^^^^^^^^^^^^^^^^^^^^\n.venv/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py:1122: in __get__\n    obj.__dict__[self.__name__] = result = self.fget(obj)\n                                           ^^^^^^^^^^^^^^\n.venv/lib/python3.12/site-packages/sqlalchemy/sql/schema.py:3202: in column\n    return self._resolve_column()\n           ^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\nself = ForeignKey('source_versions.id')\n\n    def _resolve_column(\n        self, *, raiseerr: bool = True\n    ) -> Optional[Column[Any]]:\n        _column: Column[Any]\n    \n        if isinstance(self._colspec, str):\n            parenttable, tablekey, colname = self._resolve_col_tokens()\n    \n            if self._unresolvable or tablekey not in parenttable.metadata:\n                if not raiseerr:\n                    return None\n>               raise exc.NoReferencedTableError(\n                    f\"Foreign key associated with column \"\n                    f\"'{self.parent}' could not find \"\n                    f\"table '{tablekey}' with which to generate a \"\n                    f\"foreign key to target column '{colname}'\",\n                    tablekey,\nE                   sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column 'capability_invocation_refs.source_version_id' could not find table 'source_versions' with which to generate a foreign key to target column 'id'\n\n.venv/lib/python3.12/site-packages/sqlalchemy/sql/schema.py:3225: NoReferencedTableError\n=========================== short test summary info ============================\nFAILED tests/unit/phase3/test_capability_gateway_repository.py::test_closed_stored_columns_match_inert_metadata[capability_invocation_refs-StoredInvocationRef]\n========================= 1 failed, 25 passed in 0.19s =========================\n",
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-required.json`:

```text
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "command": "uv run alembic heads",
    "exit_code": 0,
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 28 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 57%]\n............                                                             [100%]\n\n============================== 28 passed in 0.18s ==============================\n",
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.60s =========================\n",
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-required-final.json`:

```text
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "command": "uv run alembic heads",
    "exit_code": 0,
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 29 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 55%]\n.............                                                            [100%]\n\n============================== 29 passed in 0.17s ==============================\n",
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.20s =========================\n",
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-postgres.json`:

```text
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/integration/phase3/test_pr3_00_bootstrap.py ......                 [ 42%]\ntests/integration/phase3/test_pr3_01_migration.py ...                    [ 64%]\ntests/integration/phase3/test_pr3_04_migration.py ..                     [ 78%]\ntests/integration/phase3/test_pr3_02_s1_migration.py ...                 [100%]\n\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_00_bootstrap.py: 14 warnings\ntests/integration/phase3/test_pr3_01_migration.py: 11 warnings\ntests/integration/phase3/test_pr3_04_migration.py: 9 warnings\ntests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================= 14 passed, 42 warnings in 12.44s =======================\n",
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_replay.py",
    "exit_code": 1,
collected 33 items
            p.service.execute(p.principal, p.command(\"seal_task_plan\", task, revision))
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.695282+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.695282+00:00\"}
            p.service.execute(p.principal, p.command(\"seal_task_plan\", task, revision))
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.745280+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.745280+00:00\"}
        with pytest.raises(ResearchBaseError) as exc:
        assert exc.value.code == ErrorCode.FORBIDDEN
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"FORBIDDEN\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.760264+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.761571+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"FORBIDDEN\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.760264+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.761571+00:00\"}
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.820753+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.820753+00:00\"}
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.831403+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.831403+00:00\"}
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.852410+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.852410+00:00\"}
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.862360+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.862360+00:00\"}
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.872731+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.872731+00:00\"}
            command(
        response = command(
            with pytest.raises(ResearchBaseError) as exc:
        assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"INVALID_STATE_TRANSITION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.305315+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.313620+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.317688+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"INVALID_STATE_TRANSITION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.305315+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.313620+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.317688+00:00\"}
_________ test_shared_old_new_command_keys_converge[response_response] _________
    def test_shared_old_new_command_keys_converge(planning, race):
                command_id=new_uuid7(),
            old = p.command(
                c = command(
                    command(
                c = command(
                c = command(
                except ResearchBaseError as exc:
                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.478224+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.480613+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.478224+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.480613+00:00\"}
__________ test_shared_old_new_command_keys_converge[stop_admission] ___________
    def test_shared_old_new_command_keys_converge(planning, race):
                command_id=new_uuid7(),
            old = p.command(
                c = command(
                    command(
                c = command(
                c = command(
                except ResearchBaseError as exc:
                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.571392+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.572812+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.571392+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.572812+00:00\"}
__________ test_shared_old_new_command_keys_converge[settlement_stop] __________
    def test_shared_old_new_command_keys_converge(planning, race):
                command_id=new_uuid7(),
            old = p.command(
                c = command(
                    command(
                c = command(
                c = command(
                except ResearchBaseError as exc:
                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.648700+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.650314+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.648700+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.650314+00:00\"}
_____________ test_shared_old_new_command_keys_converge[bind_seal] _____________
    def test_shared_old_new_command_keys_converge(planning, race):
                command_id=new_uuid7(),
            old = p.command(
                c = command(
                    command(
                c = command(
                c = command(
                except ResearchBaseError as exc:
                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.707031+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.708336+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.707031+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.708336+00:00\"}
____________ test_shared_old_new_command_keys_converge[bind_cancel] ____________
    def test_shared_old_new_command_keys_converge(planning, race):
                command_id=new_uuid7(),
            old = p.command(
                c = command(
                    command(
                c = command(
                c = command(
                except ResearchBaseError as exc:
                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION
E   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'
src/researchbase/agent_runtime/application/research_task.py:450: TypeError
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.762439+00:00\"}
ERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.763694+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.762439+00:00\"}
ERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.763694+00:00\"}
=============================== warnings summary ===============================
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
FAILED tests/integration/phase3/test_pr3_04_application.py::test_binding_preserves_plan_and_cancel_bookkeeping[False]
FAILED tests/integration/phase3/test_pr3_04_application.py::test_binding_preserves_plan_and_cancel_bookkeeping[True]
FAILED tests/integration/phase3/test_pr3_04_application.py::test_public_reserve_denies_without_effects
FAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[execution_budgets]
FAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[checkpoint_policies]
FAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[human_checkpoints]
FAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[research_task_events]
FAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[research_task_receipt_events]
FAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_response_waits_through_expiry_and_denies_without_effects
FAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[response_response]
FAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[stop_admission]
FAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[settlement_stop]
FAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[bind_seal]
FAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[bind_cancel]
================== 14 failed, 19 passed, 2 warnings in 4.00s ===================
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-postgres-final.json`:

```json
[
  {
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_replay.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 33 items\n\ntests/integration/phase3/test_pr3_04_application.py .................... [ 60%]\n..                                                                       [ 66%]\ntests/integration/phase3/test_pr3_04_concurrency.py .......              [ 87%]\ntests/integration/phase3/test_pr3_04_replay.py ....                      [100%]\n\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read\ntests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 33 passed, 2 warnings in 4.40s ========================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_application.py tests/integration/phase3/test_pr3_04_queries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 9 items\n\ntests/integration/phase3/test_pr3_01_application.py .......              [ 77%]\ntests/integration/phase3/test_pr3_04_queries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_01_application.py::test_task_plan_seal_cancel_and_snapshot\ntests/integration/phase3/test_pr3_01_application.py::test_task_plan_seal_cancel_and_snapshot\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 9 passed, 2 warnings in 2.47s =========================\n",
    "stderr": ""
  }
]
```

Capture `tmp/pr3-03/s2-metadata.json`:

```json
[
  {
    "command": "uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 1,
    "stdout": "",
    "stderr": "Traceback (most recent call last):\n  File \"/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tmp/pr3-03/s2_metadata_probe.py\", line 7, in <module>\n    from tests.disposable_postgres import disposable_database\nModuleNotFoundError: No module named 'tests'\n"
  }
]
```

Capture `tmp/pr3-03/s2-metadata-retry.json`:

```text
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 0,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_18ef7a885c3c49e689365f54ac3bb3b9\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nNULLABLE_EXTENSIONS_MATCH research_task_command_receipts 4\nNULLABLE_EXTENSIONS_MATCH research_task_events 3\nMETADATA_GATE 5/5 tables 7/7 nullable extensions\nDISPOSABLE_DROPPED: researchbase_pr212_test_18ef7a885c3c49e689365f54ac3bb3b9\n",
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-before-index-review.json`:

```text
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "command": "uv run alembic heads",
    "exit_code": 0,
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 29 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 55%]\n.............                                                            [100%]\n\n============================== 29 passed in 0.17s ==============================\n",
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.20s =========================\n",
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 0,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_2494e012137a4822bcdcde1b0fe39405\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nNULLABLE_EXTENSIONS_MATCH research_task_command_receipts 4\nNULLABLE_EXTENSIONS_MATCH research_task_events 3\nMETADATA_GATE 5/5 tables 7/7 nullable extensions\nDISPOSABLE_DROPPED: researchbase_pr212_test_2494e012137a4822bcdcde1b0fe39405\n",
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-final.json`:

```text
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "command": "uv run alembic heads",
    "exit_code": 0,
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 29 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 55%]\n.............                                                            [100%]\n\n============================== 29 passed in 0.18s ==============================\n",
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.21s =========================\n",
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 1,
AssertionError
```

[Long output trimmed; commands, exit codes and counts retained.]


Capture `tmp/pr3-03/s2-extension-index-probe.json`:

```text
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 0,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_354f15b55ad24b52a89ac73eb56d7274\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nEXTENSION_INDEXES_MATCH research_task_command_receipts 3\nNULLABLE_EXTENSIONS_MATCH research_task_command_receipts 4\nEXTENSION_INDEXES_MATCH research_task_events 3\nNULLABLE_EXTENSIONS_MATCH research_task_events 3\nMETADATA_GATE 5/5 tables 7/7 nullable extensions\nDISPOSABLE_DROPPED: researchbase_pr212_test_354f15b55ad24b52a89ac73eb56d7274\n",
```

[Long output trimmed; commands, exit codes and counts retained.]


### Recording-session evidence: expected versus actual

These are recordings, **not live gateway lock evidence**. Full SQL and callback
sequences with bound UUIDs are retained below and in their raw JSON files. UUIDs
1–6 respectively identify project, authenticated actor, command, task, target
version and target actor. Tests compare the full traces, not only SQL substrings.

| Required behavior | Test node suffix | Raw expected/actual trace |
| --- | --- | --- |
| Literal first 18-table SHARE | `test_first_statement_is_literal_eighteen_parent_share` | `s2-trace-first-statement.json` |
| Registration omits target keys/version/availability | `test_registration_omits_target_actor_version_and_availability` | `s2-trace-registration.json` |
| Exact complete key/row/table order | `test_exact_advisory_row_and_table_order` | `s2-trace-complete-order.json` |
| Callback after every blocking acquisition | `test_callback_after_every_blocking_acquisition[False/True]` | `s2-trace-callbacks-False.json`, `s2-trace-callbacks-True.json` |
| Original safety combined recipe | `test_existing_safety_combined_recipe_unchanged` | `s2-trace-safety-compatibility.json` |
| Receipt/scoped reads and ordering, detached rows | `test_receipt_and_scoped_reads_have_deterministic_order_and_detached_rows` | `s2-trace-scoped-reads.json` |
| No SQL at construction | `test_no_sql_at_uow_or_adapter_construction` | `s2-trace-construction.json` |
| No SQL when UoW enters and installs adapters | `test_entering_uow_constructs_gateway_without_sql` | `s2-trace-uow-entry.json` |

All node IDs are in `tests/unit/phase3/test_capability_gateway_repository.py`.
Eleven additional parameter cases raise at each callback position and assert
execution stops before the next SQL. Seven metadata cases match closed stored
field sets, and the nullable-extension test checks mapped attributes and deferred
receipt relationships. The extra legacy-projection case covers S2-D1.

The existing safety PostgreSQL concurrency suite passed seven cases. That evidence
belongs to existing safety compatibility; it does not establish gateway contention,
expiry/revocation races or availability-writer ordering. Gateway live concurrency,
command semantics and later S3–S8 acceptance remain unrun here by scope.

`tmp/pr3-03/s2-trace-callback-stop-1.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-10.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-callback-stop-11.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-callback-stop-2.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-3.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-4.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-5.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-6.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-7.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-8.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-9.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-callbacks-False.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-callbacks-True.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-complete-order.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-construction.json`:

```json
{"expected":[],"actual":[]}
```

`tmp/pr3-03/s2-trace-first-statement.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}]]}
```

`tmp/pr3-03/s2-trace-registration.json`:

```text
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

[Long output trimmed; commands, exit codes and counts retained.]


`tmp/pr3-03/s2-trace-safety-compatibility.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-scoped-reads.json`:

```json
{"expected":[["SELECT * FROM research_task_command_receipts WHERE project_id=:project AND actor_id=:actor AND command_id=:command",{"project":"00000000-0000-0000-0000-000000000001","actor":"00000000-0000-0000-0000-000000000002","command":"00000000-0000-0000-0000-000000000003"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project AND policy_id=:id ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version, parameter_schema_hash,effect",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY direction, CASE WHEN research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION' WHEN hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' WHEN claim_version_id IS NOT NULL THEN 'CLAIM_VERSION' WHEN source_version_id IS NOT NULL THEN 'SOURCE_VERSION' WHEN artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' WHEN manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT_VERSION' END, coalesce(research_question_version_id,hypothesis_version_id,claim_version_id, source_version_id,artifact_version_id,manuscript_version_id)",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY sequence",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM research_task_events WHERE research_task_id=:task ORDER BY sequence",{"task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["SELECT * FROM research_task_command_receipts WHERE project_id=:project AND actor_id=:actor AND command_id=:command",{"project":"00000000-0000-0000-0000-000000000001","actor":"00000000-0000-0000-0000-000000000002","command":"00000000-0000-0000-0000-000000000003"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project AND policy_id=:id ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version, parameter_schema_hash,effect",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY direction, CASE WHEN research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION' WHEN hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' WHEN claim_version_id IS NOT NULL THEN 'CLAIM_VERSION' WHEN source_version_id IS NOT NULL THEN 'SOURCE_VERSION' WHEN artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' WHEN manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT_VERSION' END, coalesce(research_question_version_id,hypothesis_version_id,claim_version_id, source_version_id,artifact_version_id,manuscript_version_id)",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY sequence",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM research_task_events WHERE research_task_id=:task ORDER BY sequence",{"task":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-uow-entry.json`:

```json
{"expected":[],"actual":[]}
```

### Ignored helpers and reproducibility

- `tmp/pr3-03/add_extension_indexes.py` — SHA-256 `06bbb763e46249a6b9cb73ea5ea82998825541f14d77880de950621c7fe494bf`
- `tmp/pr3-03/edit_safety.py` — SHA-256 `291061f7d5889dec73a25f4116646763e8a940ad8ca762cbd8b8f672d5e7aec7`
- `tmp/pr3-03/fix_event_projection.py` — SHA-256 `07493dbfb7d689d89ecd73303aaf6ee748bdff7f7af4f37fedf26788dfcdeacb`
- `tmp/pr3-03/fix_tests.py` — SHA-256 `619f433d34179d0c56fa8299bb20ce7c8b6bcf8ed782943db0807fdb04f3f977`
- `tmp/pr3-03/generate_metadata.py` — SHA-256 `a87a957f4dcbeb693b2e65b4ea4a0bb02a3f319f3eae153acd3b7f3fb3308a65`
- `tmp/pr3-03/integrate_metadata.py` — SHA-256 `1f89589dd720b3d8d985c2e000234a5d887bde93b2db1efd89dd7b9e9ecab23d`
- `tmp/pr3-03/readable_checks.py` — SHA-256 `a46d9568d6f10a0888f0f0ae6848f9d1b98b7de9d71d9447d05f519133e0009c`
- `tmp/pr3-03/run_checks.py` — SHA-256 `ad86dbf011374dc53438d58f2067200a5530b828377256433b559682b424904a`
- `tmp/pr3-03/s2_metadata_probe.py` — SHA-256 `1cd73bd03cd81a43cc7e2a9f60a1caa7c24c68779c8d12ccbb99b454088d7278`
- `tmp/pr3-03/stored_fields.py` — SHA-256 `5d28d179977602a8ab6ad8f24408c48a14de032f1f2f9fe042bacf1687701b31`
- `tmp/pr3-03/wrap_model_literals.py` — SHA-256 `194432a1a9395ebfa320577299d52c34e2dd0e54d6d7620c9e215d3d135b1f73`
- `tmp/pr3-03/write_s2_evidence.py` — SHA-256 `890e734609f79dd95df132cb6bd32c5b11bbfff711eede5c06c70dd9b6dc2cd9`

Disposable catalog probe source used by the exact commands above:

```python
"""Read-only catalog parity of inert mappings after a disposable 0080 upgrade."""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from tests.disposable_postgres import disposable_database

from researchbase.persistence import models

TABLES = (
    'agent_tool_policies',
    'agent_tool_policy_permissions',
    'capability_invocations',
    'capability_invocation_refs',
    'capability_invocation_events',
)
with disposable_database('researchbase_pr212_test_') as url:
    config = Config('alembic.ini')
    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
    os.environ['DATABASE_URL'] = url
    command.upgrade(config, '0080_capability_gateway')
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            version = int(connection.execute(text('SHOW server_version_num')).scalar_one())
            assert version // 10000 == 18
            print('SERVER_VERSION_NUM', version)
            print('DATABASE_ROLE', connection.execute(text('SELECT current_user')).scalar_one())
            encoding = connection.execute(text('SHOW server_encoding')).scalar_one()
            assert encoding == 'UTF8'
            print('SERVER_ENCODING', encoding)
            catalog = inspect(connection)
            for name in TABLES:
                mapped = models.Base.metadata.tables[name]
                columns = catalog.get_columns(name)
                assert set(mapped.columns.keys()) == {c['name'] for c in columns}
                for column in columns:
                    candidate = mapped.c[column['name']]
                    assert candidate.nullable == column['nullable'], (name, column['name'])
                    assert str(candidate.type.compile(engine.dialect)) == str(
                        column['type'].compile(engine.dialect)
                    ), (name, column['name'])
                    assert column['default'] is None
                actual_fks = {
                    (tuple(fk['constrained_columns']), fk['referred_table'],
                     tuple(fk['referred_columns']), fk['options'].get('ondelete'))
                    for fk in catalog.get_foreign_keys(name)
                }
                expected_fks = {
                    (tuple(fk.column_keys), next(iter(fk.elements)).target_fullname.split('.')[0],
                     tuple(e.target_fullname.split('.')[1] for e in fk.elements), fk.ondelete)
                    for fk in mapped.foreign_key_constraints
                }
                assert actual_fks == expected_fks, name
                actual_unique = {tuple(u['column_names']) for u in catalog.get_unique_constraints(name)}
                expected_unique = {
                    tuple(c.name for c in u.columns)
                    for u in mapped.constraints if u.__class__.__name__ == 'UniqueConstraint'
                }
                assert actual_unique == expected_unique, name
                indexes = {
                    (i['name'], tuple(i['column_names']), bool(i['unique']))
                    for i in catalog.get_indexes(name)
                    if i['name'].startswith('pr303_') and not i.get('duplicates_constraint')
                }
                expected_indexes = {
                    (i.name, tuple(c.name for c in i.columns), bool(i.unique))
                    for i in mapped.indexes
                }
                assert indexes == expected_indexes, name
                checks = catalog.get_check_constraints(name)
                expected_checks = [c for c in mapped.constraints
                                   if c.__class__.__name__ == 'CheckConstraint']
                assert len(checks) == len(expected_checks), name
                print('METADATA_MATCH', name, 'columns', len(columns), 'foreign_keys', len(actual_fks),
                      'unique', len(actual_unique), 'indexes', len(indexes), 'checks', len(checks))
            for name in ('research_task_command_receipts', 'research_task_events'):
                columns = {c['name']: c for c in catalog.get_columns(name)}
                pointers = ['result_tool_policy_id', 'result_capability_invocation_id',
                            'result_capability_event_id']
                if name.endswith('receipts'):
                    pointers.append('resulting_invocation_revision')
                mapped = models.Base.metadata.tables[name]
                for pointer in pointers:
                    assert columns[pointer]['nullable'] and mapped.c[pointer].nullable
                actual_indexes = {
                    (i['name'], tuple(i['column_names']), bool(i['unique']))
                    for i in catalog.get_indexes(name)
                    if i['name'].startswith('pr303_') and not i.get('duplicates_constraint')
                }
                mapped_indexes = {
                    (i.name, tuple(c.name for c in i.columns), bool(i.unique))
                    for i in mapped.indexes if i.name.startswith('pr303_')
                }
                assert actual_indexes == mapped_indexes
                assert len(actual_indexes) == 3
                print('EXTENSION_INDEXES_MATCH', name, len(actual_indexes))
                print('NULLABLE_EXTENSIONS_MATCH', name, len(pointers))
            print('METADATA_GATE 5/5 tables 7/7 nullable extensions')
    finally:
        engine.dispose()
```

### Handoff and stop

All required S2 checks and touched PostgreSQL compatibility checks have passing
observed final results. S2-D1 is fixed and verified; S2-D2 documents the evidence
scope. No unresolved S2 P0/P1 finding is identified by these checks; independent
review remains pending. The next authorized plan step would be S3, but it was not
started. Overall PR3-03 gate success is not declared. STOP at S2.

Post-evidence verification: `git diff --check HEAD` exited 0 with empty stdout
and stderr. The working tree has exactly the nine nonignored paths listed above.
The complete tracked/new-file diff is retained at `tmp/pr3-03/s2-working-tree.diff`.


### S2 review carry-over for S3

Missing target AgentVersion intentionally omits the actor key: no actor identity can
be derived from an absent immutable row. The version key is still acquired, and no
actor key is acquired after row locks. S3 routing requires an existing stored
AgentVersion before relying on this lock composition; S4 admission must use that
validation with its under-lock stored read.

Step 0 removes the tautological foreign-key target assertion (the independent
RESTRICT assertion remains), anchors trace output to the repository root, and
documents the missing-version branch in the adapter. Verification follows below.

## S3 — Closed values, hashes and pure routing (2026-10-22)

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

Baseline HEAD: `bd89082cc3015805bdaa0b7155d8dfed32cc7eec` (S2).
Initial working tree was clean. Only S3 and the explicitly requested Step 0
carry-over fixes are implemented. No commands, UoWs, persistence writes, fake
dispatch, adapter discovery, network/process execution, or scientific promotion
are added. S4 has NOT STARTED. Overall PR3-03 acceptance remains PENDING.

### Changed paths and Deviations

All changed paths (eight new S3 files, two Step 0 files, one evidence file):

- `src/researchbase/agent_runtime/domain/capability_invocation.py`
- `src/researchbase/agent_runtime/domain/tool_policy.py`
- `src/researchbase/agent_runtime/application/gateway_contracts.py`
- `src/researchbase/agent_runtime/application/routing.py`
- `src/researchbase/agent_runtime/ports/capability_gateway.py`
- `tests/unit/phase3/test_capability_gateway_contracts.py`
- `tests/unit/phase3/test_agent_tool_policy.py`
- `tests/unit/phase3/test_capability_routing.py`
- `tests/unit/phase3/test_capability_gateway_repository.py` (S3-D1)
- `src/researchbase/persistence/capability_gateway_repository.py` (S3-D1)
- `docs/phase3/PR3-03-evidence.md` (S3-D2)

**Deviation S3-D1 — authorized S2 review carry-over outside S3's file list.**
Scope: the two S2 test/adapter paths above. Evidence: the vacuous FK target
assertion is deleted as expressly permitted; ON DELETE RESTRICT and column
shape assertions remain. `record()` resolves its output directory from
`Path(__file__).resolve().parents[3]`, independent of process cwd.
The adapter now documents the intended missing-version branch without changing
SQL or lock behavior: no actor can be derived from absence, the version key is
still taken, and no actor key may be added after row locking.
`SkillRouter.select` checks version existence first and returns NOT_FOUND on
absence; `test_pins_phase_and_reference_only[no-version]` exercises this.
Impact: no changed SQL/transaction semantics. Disposition: resolved as explicitly
authorized by the owner; S4 must apply the predicate to its under-lock stored read.

**Deviation S3-D2 — owner-required evidence outside S3's file list.**
Scope: this document and ignored `tmp/pr3-03/s3-*.txt` verification logs.
Impact: evidence only. Disposition: authorized by the task. No frozen pack,
accepted migration, dependency definition, lockfile, or governing Harness file
changed. No architecture conflict requiring stop rule G was found; SQL rule L
requires no new SQL in this pure-value step.

### Contract coverage

The complete §8 vocabulary is represented by frozen, slotted dataclasses and
recursive exact-type decoding. The public command decoder accepts only its
closed variant, rejects unknown/missing fields and receives finish observations
through a separately supplied trusted value. AgentExecutionContext has no public
decoder, cannot enter command material, and rejects pickle serialization.
Hashes include authenticated actor, exact command identity, every default and
NULL, normalized refs, and six-place ResourceVector strings; old envelopes are
untouched. Owning parameter content hash and canonical parameter digest remain
separate fields. Retained-parameter verification compares supplied bytes literally
and checks owning hash/size separately.

Six independently fixed §7.2 inputs are literal UTF-8 expectations in
`test_frozen_literal_vectors`, with the exact frozen digests:
schema `79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f`;
empty-set `2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1`;
fake-set `2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9`;
empty-policy `dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c`;
allow-deny-policy `725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b`;
Café parameters `a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3`.
Expected bytes/digests are literals in tests, never generated at test runtime.

Tests cover all four command round-trips, read/result round-trips and complete
stored column vocabulary; lifecycle, pre-dispatch cancellation, immutable unknown
reconciliation and retry eligibility; nested extras, duplicate refs/permissions/
registry entries, aliases/patterns, bool-as-int, decimal scale, nonfinite values,
UTF-8 summary/message limits, combined 256-ref bound, and distinct invoke IDs.
Policy tests prove exact case-sensitive matching, absent ALLOW denial, DENY
precedence, defaults 50/1, and below/equal/above task-wide counts surviving a
policy version change.

The supplied-byte loader uses a local 1,048,576-byte ceiling (callers may tighten
it), 256-entry ceiling, duplicate JSON key rejection and literal canonical-byte
comparison after normalization. This is a bounded local admission choice; it
does not add a persistence constraint. Routing checks current phase, explicit
authority/disclosure/safety results, exact policy/version/harness/registry/intake
pins, current availability, reference-only entries, and self-modification
exclusions. The no-I/O test blocks file opening and dynamic module discovery.

### Verification results

Every uv command used `export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.
Setup: `uv sync --locked --group dev`, exit 0, exact output:

```text
Resolved 38 packages in 2ms
Checked 34 packages in 3ms
```

Final ordered verification follows. Combined stdout/stderr is copied verbatim;
raw copies are in ignored `tmp/pr3-03/s3-final-N.txt`. Each pytest run had zero
failures, errors or skips.

### git diff --check HEAD

Exit: `0`. Exact combined output: empty.

```text
```

### uv run ruff check .

Exit: `0`. Exact combined output.

```text
All checks passed!
```

### uv run ruff format --check .

Exit: `0`. Exact combined output.

```text
900 files already formatted
```

### uv run pyright

Exit: `0`. Exact combined output.

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

### uv run alembic heads

Exit: `0`. Exact combined output.

```text
0080_capability_gateway (head)
```

### uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_contracts.py tests/unit/phase3/test_agent_tool_policy.py tests/unit/phase3/test_capability_routing.py

Exit: `0`. Exact combined output.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane115
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 138 items

tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 12%]
.............................................                            [ 44%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [ 65%]
......                                                                   [ 69%]
tests/unit/phase3/test_capability_routing.py ........................... [ 89%]
...............                                                          [100%]

============================= 138 passed in 0.16s ==============================
```

### uv run pytest -o addopts='' -ra tests/unit/phase3/test_research_task_contracts.py tests/unit/phase3/test_task_safety_contracts.py tests/unit/phase3/test_agent_version_contracts.py tests/unit/phase3/test_harness_manifest.py

Exit: `0`. Exact combined output.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane115
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 203 items

tests/unit/phase3/test_research_task_contracts.py ...................... [ 10%]
....................................................                     [ 36%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 44%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [ 55%]
........................................................................ [ 90%]
....                                                                     [ 92%]
tests/unit/phase3/test_harness_manifest.py ...............               [100%]

============================= 203 passed in 0.14s ==============================
```

### uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py

Exit: `0`. Exact combined output.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane115
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 43 items

tests/unit/phase3/test_capability_gateway_repository.py ................ [ 37%]
.............                                                            [ 67%]
tests/unit/phase3/test_task_safety_transports.py ..........              [ 90%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 95%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]

=============================== warnings summary ===============================
tests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane115/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 43 passed, 1 warning in 1.75s =========================
```

### Earlier development attempts and limits

Before implementation, `python - <<'PY' ...` exited 127 with
`zsh:1: command not found: python`; no edits occurred in that attempt.
The same Step 0 edit script was rerun successfully with python3.
The first local Ruff fix pass reported three E501 findings, then formatting
resolved them. The later test-authoring Ruff fix pass reported twelve findings
(eight fixed and four remaining E501); formatting resolved the remaining four.
The first development `uv run pyright` reported
`106 errors, 0 warnings, 0 informations` (exit 1), from inferred heterogeneous
JSON dictionary types and optional narrowing. Explicit boundary annotations and
NoReturn narrowing resolved these. One attempted output redirection did not
execute pyright because the ignored log directory had not yet been created:

```text
zsh:18: no such file or directory: tmp/pr3-03/s3-pyright-development.txt
cat: tmp/pr3-03/s3-pyright-development.txt: No such file or directory
```

After mkdir, development pyright reported one remaining DataclassInstance
callability error (raw output in `s3-pyright-development.txt`), fixed by an
explicit cast at the validated class-construction boundary.
The first ordered gate then passed with 124/124 new tests; after read/result
validation was expanded, a development focused run passed 138/138.
The final ordered runs above supersede these attempts. No pytest failure or
skip occurred. No git/uv lock or sandbox failure occurred.

Final counts: S3 138 collected / 138 passed / 0 failed / 0 skipped;
old contracts/vectors 203 collected / 203 passed / 0 failed / 0 skipped;
S2/transport/architecture 43 collected / 43 passed / 0 failed / 0 skipped,
with the single Alembic path_separator deprecation warning shown above.
Total across the three final focused runs: 384 passed, 0 failed, 0 skipped.

PostgreSQL suites: NOT RUN in S3. No SQL, migration, database constraint or
adapter behavior changed; the sole adapter edit is a comment. These pure tests
do not establish PostgreSQL lock correctness. SQL/Python parity and all new
gateway PostgreSQL behavior remain reserved for S8. Six-shard/full suite:
NOT RUN, owned by the external check loop. S4–S8: NOT STARTED by this task;
overall gate/independent review: PENDING. No commit, push or branch creation.
Stop after this S3 handoff.

Post-evidence whitespace check: `git diff --check HEAD` initially exited 2:

```text
docs/phase3/PR3-03-evidence.md:2227: new blank line at EOF.
```

Removed the extra EOF blank line. Repeated `git diff --check HEAD`: exit 0,
stdout/stderr empty. Only evidence text changed after the ordered checks above.

## S4 — Register/request commands and reserve_in_uow (2026-10-22)

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

Scope: S4 only. No start, finish, reconciliation, invoke/dispatch, transport or
query implementation is added. Frozen pack and accepted migrations, pyproject.toml
and uv.lock are unchanged. S5 has NOT STARTED. Gateway PostgreSQL atomicity and
contention are PENDING S8; recording doubles do not establish database atomicity.

### Step 0

Every uv command in S4 sets `UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.
The required old-vector run was the first uv command. Exact command:

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_research_task_contracts.py tests/unit/phase3/test_task_safety_contracts.py tests/unit/phase3/test_agent_version_contracts.py tests/unit/phase3/test_harness_manifest.py
```

Exit 0; 203 collected, 203 passed, 0 failed, 0 skipped. Exact output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 203 items

tests/unit/phase3/test_research_task_contracts.py ...................... [ 10%]
....................................................                     [ 36%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 44%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [ 55%]
........................................................................ [ 90%]
....                                                                     [ 92%]
tests/unit/phase3/test_harness_manifest.py ...............               [100%]

============================= 203 passed ==============================
```

Step 0b: confirmed the existing **S2 review carry-over for S3** paragraph, before
S3, states the intended missing-version behavior: absence yields no derivable
actor key, the version key remains acquired, no actor key follows row locks, and
S4 must reject missing stored AgentVersion under locks. No S2 paragraph addition
was needed. S4's `no_version` test exercises that admission denial.

Step 0c: `git check-ignore -v tmp/pr3-03/x`, exit 0. Exact output (tab separator):

```text
.gitignore:32:tmp/	tmp/pr3-03/x
```

Setup: `uv sync --locked --group dev`, exit 0. Exact output:

```text
Resolved 38 packages in 3ms
Checked 34 packages in 0.90ms
```

### Changed paths and Deviation

- `src/researchbase/agent_runtime/application/capability_gateway.py` (new)
- `src/researchbase/agent_runtime/application/gateway_accounting.py` (created in S4; removed by the correction below)
- `src/researchbase/agent_runtime/application/task_safety.py`
- `src/researchbase/agent_runtime/ports/gateway_repository.py`
- `src/researchbase/persistence/capability_gateway_repository.py`
- `src/researchbase/persistence/uow.py`
- `tests/unit/phase3/test_capability_gateway.py` (new)
- `tests/unit/phase3/gateway_fixtures.py` (new)
- `tests/unit/phase3/test_capability_gateway_repository.py`
- `docs/phase3/PR3-03-evidence.md`

**Deviation S4-D1 — owner-required evidence outside the S4 production/test file
list.** Scope: this document and ignored `tmp/pr3-03/s4-*` traces/logs. Evidence:
the task explicitly requires this S4 evidence section and exact outputs. Impact:
evidence only; no architecture or frozen-contract change. Disposition: authorized
by the task. No stop rule G architecture conflict is claimed. SQL rule L applies
to all new parameterized adapter constants; no new exclusion/noqa is added.

### Implementation and limits

The command service verifies retained registry/intake/harness/parameter bytes in
a preliminary formal read before the write transaction, retaining hashes/sizes
and typed values. Preflight failure is held until entitled committed-receipt
lookup. The write UoW begins with S2's exact first SHARE/composed lock recipe.
After every acquisition, current credentials/read entitlement and committed
receipt lookup precede fresh admission. Own current-xmin receipt is excluded.
All DML and constraint forcing are followed by the same checks, rechecking write
authority, pins, safety and advancing time. One observed DB provenance timestamp
is copied to all newly timestamped rows; final checks do not use that saved time
as their clock. Stable generated receipt/reservation/event/permission/ref IDs are
allocated before the bounded three-attempt runner. Only the existing transient
40001/40P01 marker retries; timeout and other denials do not.

Registration checks an active HUMAN OWNER row. Request binds the caller/context,
consumer object identity, enrolled live Agent, availability, exact policy/version,
registry/intake/harness pins, exact inputs, full safety bundle, latest checkpoints,
autonomy, task-wide call/occupancy caps, gauges and historical stops. It writes
one task revision/receipt/reservation/invocation/request event/task event/link,
with concrete exact input refs. Registration has no reservation/invocation.
No public safety command or nested safety UoW is called.

The original PR3-04 reservation calculation was moved, without a second ledger,
into `reservation_values`/`reservation_gauges` in task_safety.py. Both the public
safety reserve branch and GatewayAccounting call those functions; balances,
causes, gates and saved-policy verification remain shared. The fixed §6 vector
is used verbatim. An exact-cap reservation adds the existing budget-stop flag;
rechecking the current command excludes only its own uncommitted accounting/event
to avoid double-counting. Earlier flags remain disqualifying and are never reset.
Saved command results use receipt-linked event IDs and charges, never a newer
invocation projection. Narrow gateway uniqueness mappings leave old commands
and unrelated uniqueness errors unchanged.

Transaction/lock/byte-order trace: pytest `tmp_path / "s4-no-io-trace.json"`
(the original run used `tmp/pr3-03/s4-no-io-trace.json`). The byte
store asserts it is never opened after lock entry. The test asserts credential,
entitlement and committed-receipt ordering after every recorded acquisition.
The S2 SQL recording traces remain under `tmp/pr3-03/s2-trace-*` and are rerun by
the required adapter test file. These traces are orchestration evidence only.

### Final ordered verification

All commands below exited 0 after the diagnostic-name and exact-event-exclusion
corrections. Exact combined stdout/stderr follows. Raw output and exit records
are in `tmp/pr3-03/s4-final.json` and `s4-final-1.txt` through `s4-final-7.txt`.
`addopts=''` below is the shell spelling of the empty value passed directly to
subprocess in the recording runner.

#### git diff --check HEAD

Exit: `0`. Exact combined output:

```text
```

#### uv run ruff check .

Exit: `0`. Exact combined output:

```text
All checks passed!
```

#### uv run ruff format --check .

Exit: `0`. Exact combined output:

```text
904 files already formatted
```

#### uv run pyright

Exit: `0`. Exact combined output:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### uv run alembic heads

Exit: `0`. Exact combined output:

```text
0080_capability_gateway (head)
```

#### uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py

Exit: `0`. Exact combined output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 116 items

tests/unit/phase3/test_capability_gateway.py ........................... [ 23%]
.............................................                            [ 62%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 75%]
............................                                             [100%]

============================= 116 passed ==============================
```

#### uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_budget_accounting.py tests/unit/phase3/test_task_safety_contracts.py tests/unit/phase3/test_task_safety_transports.py

Exit: `0`. Exact combined output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 39 items

tests/unit/phase3/test_task_budget_accounting.py .............           [ 33%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 74%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================== 39 passed ==============================
```

Final required unit counts: gateway/adapter 116 collected / 116 passed / 0 failed /
0 skipped; safety regression 39 collected / 39 passed / 0 failed / 0 skipped.
This includes 72 gateway transaction/admission tests and 44 adapter tests.

### Focused architecture and touched PostgreSQL regressions

These commands were rerun after both final corrections; both exited 0.
The PostgreSQL fixtures explicitly create/drop random disposable databases on the
selected local admin cluster and assert PostgreSQL 18. They upgrade to 0080 and
exercise existing public safety accounting/application/replay/fake behavior after
the shared calculation refactor; they do not prove new gateway PostgreSQL
atomicity, guards or races. Those remain PENDING S8. No SQLite is used.

#### uv run pytest -o addopts='' -ra tests/architecture/test_pr3_01_boundaries.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py

Exit: `0`. Counts: 8 collected / 8 passed / 0 failed / 0 skipped; 1 warning. Exact combined output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 8 items

tests/architecture/test_pr3_01_boundaries.py ....                        [ 50%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 75%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]

=============================== warnings summary ===============================
tests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 8 passed, 1 warning =========================
```

#### uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_04_fake_consumer.py

Exit: `0`. Counts: 39 collected / 39 passed / 0 failed / 0 skipped; 2 warnings. Exact combined output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 39 items

tests/integration/phase3/test_pr3_04_application.py .................... [ 51%]
..                                                                       [ 56%]
tests/integration/phase3/test_pr3_04_accounting.py ...........           [ 84%]
tests/integration/phase3/test_pr3_04_replay.py ....                      [ 94%]
tests/integration/phase3/test_pr3_04_fake_consumer.py ..                 [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read
tests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 39 passed, 2 warnings ========================
```

### Exact constraint diagnostic probe

Final review found the 65-character unconstrained spelling of the original
receipt uniqueness name would not match PostgreSQL's generated diagnostic.
A disposable 0080 catalog probe observed the exact name
`research_task_command_receipt_project_id_actor_id_command_i_key`. The mapping
now uses that exact diagnostic, with a test for gateway IDEMPOTENCY_CONFLICT and
unchanged old-command VALIDATION_ERROR. No exception message parsing is used.
No migration changed. The complete ordered verification above and both focused
regressions were rerun after this correction.

Exact command (exit 0):

```sh
UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache" PYTHONPATH=. uv run python tmp/pr3-03/s4-diagnostic-probe.py
```

The ignored script creates a random disposable DB using the accepted helper,
upgrades through Alembic to head, reads version/role/encoding/head and the receipt
UNIQUE catalog names, and disposes/drops in finally. Exact combined output:

```text
RECEIPT_UNIQUE research_task_command_receipt_project_id_actor_id_command_i_key
RECEIPT_UNIQUE research_task_command_receipt_research_task_id_actor_id_com_key
RECEIPT_UNIQUE research_task_command_receipt_research_task_id_resulting_ro_key
RECEIPT_UNIQUE research_task_command_receipts_research_task_id_id_key
```

[Long output trimmed; commands, exit codes and counts retained.]


### Development attempts and scope of claims

The first command-test development run collected 57 and failed all 57 (0 passed,
0 skipped) at fixture manifest serialization: canonical JSON rejects tuples.
Both fixture and production manifest byte comparison now use normalized material.
The next two `-x` runs each collected 57 and observed 1 passed / 1 failed /
0 skipped before stopping: first the fixture omitted owning-domain repository
attributes, then its checkpoint policy hash used conceptual scope-ID names rather
than stored exact-scope material. These fixture omissions were corrected.
The fourth `-x` run collected 57 and observed 10 passed / 1 failed / 0 skipped:
the policy-switch fixture still occupied its only safety parallel slot, so it
could not isolate the tool-call cap. It now seeds a prior final charge and uses
a distinct AgentVersion to check the new policy while retaining the admitted call.

Exact outputs are retained in `s4-development-pytest.txt`, `s4-development2.txt`,
`s4-development3.txt`, and `s4-development4.txt`. Subsequent observed development
runs: `s4-development5.txt` 57/57 passed; `s4-development6.txt` 99/99 passed;
`s4-development7.txt` 113/113 passed (each 0 failed, 0 skipped). The first ordered
verification passed with 113 gateway/adapter tests and 39 safety tests; the final
run with 115/115 passing followed the catalog-name correction. Final review
then found command UUID alone was too broad an exclusion for the current event:
commands from different actors may share a UUID. The calculation now excludes
only the preallocated event ID, and a cross-actor UUID collision cannot hide a
prior stop. A new passing regression raises the final gateway/adapter count to
116. The ordered checks and architecture/PostgreSQL runs above were repeated
after that correction.

Development Pyright observed 15 errors (heterogeneous dictionary inference),
then 6 errors (fixture optional/callback annotations), then 3 errors (test exception
attributes and optional details). Final Pyright reports 0 errors. Saved intermediate
outputs are `s4-dev-pyright.txt` and `s4-dev-pyright2.txt`. Development Ruff reported
12 findings (2 fixed) and later 21 findings (1 fixed), primarily lines awaiting
formatting; formatting/import cleanup resolved them. Final repository-wide lint
and format checks pass without config changes, exclusions or new noqa.
These development failures are not counted as passing verification.

No git/uv lock or sandbox failure occurred. No whole-suite/six-shard run,
commit, push or branch creation occurred. External full-suite check and independent
review remain PENDING. No S4 architecture gap is claimed and no known P0/P1 is
left by the focused checks; this is not an overall PR3-03 acceptance declaration.
S5–S8 are not implemented by this task. STOP at the S4 handoff.

### S4 review correction — preserve the approved ADR scope (2026-10-22)

This section supersedes earlier S4 guard-exception dispositions and verification
claims for the current working tree. ADR-0025 admits only the seven runtime
source files named as new in frozen pack §8 and the two DTO class names there
containing "agent": AgentExecutionContext and AgentToolPolicyRead.

GatewayAccounting and its constants moved unchanged into capability_gateway.py;
gateway_accounting.py was deleted and test imports were updated. An AST
comparison against HEAD confirmed the moved constants and class are identical.
The policy ORM classes are now ToolPolicyRowModel and ToolPolicyPermissionRowModel;
only their Python names changed, with table names, columns and constraints unchanged.
The negative architecture test also rejects both former ORM names.
The entry-state timedelta import and pytest tmp_path fixes are retained.

All commands below ran separately in this continuation, in the listed order.
Before every uv invocation:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
```

```sh
git diff --check HEAD
```

Exit code: `0`. Raw combined stdout/stderr:

```text
```

```sh
uv run ruff check .
```

Exit code: `0`. Raw combined stdout/stderr:

```text
All checks passed!
```

```sh
uv run ruff format --check .
```

Exit code: `0`. Raw combined stdout/stderr:

```text
903 files already formatted
```

```sh
uv run pyright
```

Exit code: `0`. Raw combined stdout/stderr:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

```sh
uv run alembic heads
```

Exit code: `0`. Raw combined stdout/stderr:

```text
0080_capability_gateway (head)
```

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -q tests/architecture tests/unit/architecture tests/unit/phase3
```

Exit code: `0`. Raw combined stdout/stderr:

```text
........................................................................ [  6%]
........................................................................ [ 13%]
........................................................................ [ 20%]
........................................................................ [ 27%]
........................................................................ [ 34%]
........................................................................ [ 41%]
........................................................................ [ 48%]
........................................................................ [ 55%]
........................................................................ [ 62%]
........................................................................ [ 69%]
........................................................................ [ 76%]
........................................................................ [ 83%]
........................................................................ [ 90%]
........................................................................ [ 97%]
..........................                                               [100%]
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1034 passed, 50 warnings in 25.45s
```

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -q tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_04_fake_consumer.py
```

Exit code: `0`. Raw combined stdout/stderr:

```text
.......................................                                  [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read
tests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane116/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
39 passed, 2 warnings in 3.18s
```

Current counts: architecture/unit selection 1034 passed, 0 failed, 0 errors,
0 skipped, 50 warnings in 25.45s; focused PostgreSQL safety selection 39 passed,
0 failed, 0 errors, 0 skipped, 2 warnings in 3.18s.
These timings are copied from the same runs printed above. Historical S4 pytest
timings are omitted from the earlier runs rather than reused for these runs.

After updating this evidence, `git diff --check HEAD` exited 2:

```text
docs/phase3/PR3-03-evidence.md:2823: new blank line at EOF.
```

The trailing blank line was removed. The final `git diff --check HEAD` rerun
exited 0 with empty output.

Every changed path relative to HEAD, including entry-state partial changes:

- `docs/architecture/adr/ADR-0025-pr3-03-architecture-guard-exception.md`
- `docs/phase3/PR3-03-evidence.md`
- `src/researchbase/agent_runtime/application/capability_gateway.py`
- `src/researchbase/agent_runtime/application/gateway_accounting.py` (deleted)
- `src/researchbase/persistence/models.py`
- `tests/architecture/test_pr17_agent_ready_architecture.py`
- `tests/architecture/test_pr3_00_boundaries.py`
- `tests/unit/phase3/gateway_fixtures.py`
- `tests/unit/phase3/test_capability_gateway.py`

Frozen pack, accepted migrations, pyproject.toml and uv.lock are unchanged.
No S5 work, full-suite/six-shard run, commit, push or branch creation occurred.
Overall PR3-03 acceptance and gateway PostgreSQL atomicity/race evidence remain
PENDING; this is focused S4 verification only.

## S5 — Start, finish, reconciliation and durable replay

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

Small fix round baseline: S5 commit `5c826b3`. S6 NOT STARTED. No frozen pack,
accepted migration, dependency definition or architecture exception changed.
No commit, push, branch creation or full-suite/six-shard run performed.

### Authorization and finish authority

The S5 requirement is "current entitlement checked before conflict disclosure"
(the plan's verification paragraph says "current entitlement before conflict disclosure").
Trusted lifecycle context is checked before preflight invocation reads, and again
on fresh checks before receipt/conflict disclosure or invocation lookup. Unknown
invocations return FORBIDDEN for public/untrusted or unauthorized callers and
NOT_FOUND for authorized trusted callers. Tests:
`test_unknown_invocation_requires_authorization_before_disclosure` and
`test_public_self_supplied_observation_is_forbidden`.

Plan S5: "Finish after stop/CANCELLED requires current read entitlement
and trusted observation, not availability or fresh-spend authority."
Pack §6.1: "Finish/reconciliation are attributable
bookkeeping after stop/cancellation and do not require active availability or
fresh spend authority; they still require current read entitlement, trusted
consumer context, exact charge ownership and no prior final settlement."
Both specify the after-stop/cancellation exception. Normal new finish therefore
requires write authority; after-stop/cancellation bookkeeping retains read
entitlement plus injected trusted context. Fresh checks exclude this command's
own newly written stop event from the exception. Saved receipt replay retains
its existing current-read-entitlement rule. Tests: `test_finish_authority_split`
(VIEWER denied normal finish; RESEARCHER allowed; both allowed after stop or
cancellation), `test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent`,
and `test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability`.

Removed unused parser `observation=`; all callers now use the two-argument parser.
Public finish parsing still denies trust. Reconciliation tests use valid
ADAPTER_UNAVAILABLE and complete trace pins, assert VALIDATION_ERROR and the
exact diagnostic "reconciliation preserves the original observation".

### Deviations outside the S5 file list

| File | Reason | Proving test |
| --- | --- | --- |
| `src/researchbase/agent_runtime/application/gateway_contracts.py` | Step 0b required public observation trust denial; remove its dead observation parameter without changing trust semantics. | `test_public_self_supplied_observation_is_forbidden`; `test_four_command_roundtrips_and_actor_material` |
| `tests/unit/phase3/test_capability_gateway_contracts.py` | Step 0b parser contract tests must use the closed public signature. | `test_four_command_roundtrips_and_actor_material`; `test_public_finish_and_trusted_context_cannot_be_deserialized` |

### Evidence limits

Unit/recording-session assertions establish orchestration only. PostgreSQL
`update_invocation` CAS/immutability behavior: **unverified until S8**.
PostgreSQL `lock_gateway` ordering/contention: **unverified until S8**.
PostgreSQL receipt writes/visibility/atomicity/durability: **unverified until S8**.
All other PostgreSQL-dependent gateway claims, including exactly-once settlement,
SQL guards, rollback, advancing expiry, replay and uncertain-commit recovery:
**unverified until S8**. Existing safety PostgreSQL tests prove compatibility only;
gateway PostgreSQL acceptance remains **unverified until S8**.

### Development verification

Initial four-file focused run: exit 1, 278 collected / 272 passed / 6 failed /
0 skipped. The six new unknown-invocation tests failed in fixture setup
(StopIteration), before entering the service. Corrected setup constructs the
command against the existing fixture row then replaces its invocation ID.

### Separate raw verification runs

Every uv command uses `export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.
Outputs below are independent command runs, never a combined suite attributed
to multiple commands. Overall PR acceptance and gateway PostgreSQL behavior
remain pending S8 and the external loop.
### Run 1

```sh
git diff --check HEAD
```

Exit code: `0`. Raw stdout/stderr:

```text
```

### Run 2

```sh
uv run ruff check .
```

Exit code: `0`. Raw stdout/stderr:

```text
All checks passed!
```

### Run 3

```sh
uv run ruff format --check .
```

Exit code: `0`. Raw stdout/stderr:

```text
903 files already formatted
```

### Run 4

```sh
uv run pyright
```

Exit code: `0`. Raw stdout/stderr:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

### Run 5

```sh
uv run alembic heads
```

Exit code: `0`. Raw stdout/stderr:

```text
0080_capability_gateway (head)
```

### Run 6

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py
```

Exit code: `0`. Raw stdout/stderr:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane118
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 249 items

tests/unit/phase3/test_capability_gateway.py ........................... [ 10%]
........................................................................ [ 39%]
........................................................................ [ 68%]
............................                                             [ 79%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 86%]
..................................                                       [100%]

============================= 249 passed in 2.08s ==============================
```

### Run 7

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Exit code: `0`. Raw stdout/stderr:

```text
tests/architecture/test_import_boundaries.py .............               [ 32%]
tests/architecture/test_m1_boundaries.py ...                             [ 33%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 38%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 41%]
tests/architecture/test_pr12_boundaries.py ....                          [ 42%]
tests/architecture/test_pr13_boundaries.py ..                            [ 42%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 43%]
tests/architecture/test_pr14_boundaries.py ..                            [ 44%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 45%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 46%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 48%]
tests/architecture/test_pr18_boundaries.py .......                       [ 50%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 56%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 62%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 63%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 71%]
................................                                         [ 80%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 81%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane118/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 352 passed, 50 warnings in 20.17s =======================
```

### Run 8

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_task_budget_accounting.py tests/unit/phase3/test_task_checkpoints.py
```

Exit code: `0`. Raw stdout/stderr:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane118
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 278 items

tests/unit/phase3/test_capability_gateway.py ........................... [  9%]
........................................................................ [ 35%]
........................................................................ [ 61%]
............................                                             [ 71%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 77%]
..................................                                       [ 89%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 94%]
tests/unit/phase3/test_task_checkpoints.py ................              [100%]

============================= 278 passed in 2.04s ==============================
```

### Run 9

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_contracts.py
```

Exit code: `0`. Raw stdout/stderr:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane118
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 62 items

tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 27%]
.............................................                            [100%]

============================== 62 passed in 0.08s ==============================
```

### Run 10

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_04_fake_consumer.py
```

Exit code: `0`. Raw stdout/stderr:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane118
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 39 items

tests/integration/phase3/test_pr3_04_application.py .................... [ 51%]
..                                                                       [ 56%]
tests/integration/phase3/test_pr3_04_accounting.py ...........           [ 84%]
tests/integration/phase3/test_pr3_04_replay.py ....                      [ 94%]
tests/integration/phase3/test_pr3_04_fake_consumer.py ..                 [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read
tests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane118/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 39 passed, 2 warnings in 3.13s ========================
```

### Final counts and changed paths

All final commands above exited 0. Two-file gateway run: 249 collected / 249
passed / 0 failed / 0 skipped. Four-file S5 run: 278 collected / 278 passed /
0 failed / 0 skipped. Parser: 62 collected / 62 passed / 0 failed / 0 skipped.
Architecture: 352 collected / 352 passed / 0 failed / 0 skipped, 50 warnings.
Existing safety PostgreSQL regressions: 39 collected / 39 passed / 0 failed /
0 skipped, 2 warnings. No gateway PostgreSQL acceptance is claimed:
**unverified until S8**. No full suite or six-shard run. S6 NOT STARTED.

Changed paths for this small fix round:

```text
docs/phase3/PR3-03-evidence.md
src/researchbase/agent_runtime/application/capability_gateway.py
src/researchbase/agent_runtime/application/gateway_contracts.py
tests/unit/phase3/test_capability_gateway.py
tests/unit/phase3/test_capability_gateway_contracts.py
```

Post-evidence whitespace check `git diff --check HEAD` initially exited 2:

```text
docs/phase3/PR3-03-evidence.md:2831: new blank line at EOF.
```

Removed the extra EOF blank line. Final `git diff --check HEAD`: exit 0,
empty stdout/stderr. Final `git status --short`: exit 0, five modified paths
listed above, no staged files.

## S6 — Snapshot queries and finite fake invoke

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

### Step 0 — prerequisite evidence repair

Step 0a: raw history search from the S6 small-fix baseline `1194dbb`.

```sh
git log --oneline -- docs/phase3/PR3-03-evidence.md
```

```text
1194dbb PR3-03 sub-task S6 — snapshot queries and CapabilityGateway.invoke (finite fake, no real adapter)
653cea2 PR3-03 sub-task S5 — start, finish, reconciliation and durable replay (no dispatch)
cdf2160 PR3-03 sub-task S4 — register/request commands and reserve_in_uow (no start, finish or dispatch)
1c44def PR3-03 sub-task S3 — closed domain/Application values, hashes and routing predicates (no commands)
bd89082 PR3-03 sub-task S2 — repository ports, composed locks and stored-row reads (no command behaviour)
52d984a Record PR3-03 S1 evidence (documentation only)
ae50409 S1 retry with owner-approved amendment A1 (syntax-only parenthesisation)
```

Exit code: 0.

```sh
git grep -n "S5 requirement" $(git rev-list 653cea2 -n 5) -- docs/phase3/PR3-03-evidence.md
```

```text
653cea2966a8b78b1321d1b2d655ecead40be16e:docs/phase3/PR3-03-evidence.md:2496:The S5 requirement is "current entitlement checked before conflict disclosure"
```

Exit code: 0.

The match is an authorization sentence, not an earlier S5 requirement table.
Inspected the evidence file at each earlier file-history revision: `653cea2`,
`cdf2160`, `1c44def`, `bd89082`, `52d984a`, and `ae50409`. Only `653cea2`
has an S5 section; it has no S5 requirement table. The table cannot be recovered
from earlier history. Deviation S6-E1: the following is a reconstruction of S5
requirements covered by current tests, not a verbatim historical restoration.
All cited tests are in `tests/unit/phase3/test_capability_gateway.py`; these
unit fixtures do not establish PostgreSQL acceptance.

| S5 requirement | Existing test in tests/unit/phase3/test_capability_gateway.py |
| --- | --- |
| Public observation trust denied | test_public_self_supplied_observation_is_forbidden |
| Authorization before existence disclosure | test_unknown_invocation_requires_authorization_before_disclosure |
| Start without new accounting; pre-start cancel | test_start_zero_new_accounting_and_prestart_cancel_retains_counts |
| Four outcomes and finish after stop | test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent |
| Finish authority split | test_finish_authority_split |
| Append-only reconciliation and saved results | test_reconciliation_append_only_and_saved_event_results |
| Lifecycle edges | test_lifecycle_edge_matrix |
| Own first attributable exact-cap stop | test_exact_cap_start_only_own_first_attributable_stop |
| CAS and saved replay | test_lifecycle_cas_and_saved_receipt_precedes_stale_revisions |
| Success-only outputs; immutable observation | test_output_refs_success_and_reconciliation_preserves_observation; test_reconciliation_rejects_changed_observation; test_output_refs_rejected_for_every_non_success |
| Retry-parent eligibility | test_retry_parent_requires_failure_or_final_reconciled_unknown |
| Rollback at finish writes | test_finish_rolls_back_every_write_stage |
| Uncertain commit formal receipt lookup | test_finish_uncertain_commit_uses_formal_receipt_lookup |
| Entitlement/replay after every wait | test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability |
| Fresh checks after DML waits | test_fresh_lifecycle_checks_after_dml_wait_roll_back |
| Stable retries, single settlement | test_lifecycle_retry_ids_stable_and_single_settlement |
| Unknown retains occupancy/full budget | test_unknown_reservation_still_occupies_slot_and_full_budget |
| Charge ownership | test_finish_exact_charge_ownership_is_required |
| Unknown preserves final failure streak | test_unknown_does_not_advance_final_failure_streak_until_reconciliation |

Step 0b: replace the inline calculation with shared `task_stopped`, retaining
exclusion of this command's own task event. Existing finish-authority tests cover
its behavior. No availability requirement is introduced for finish bookkeeping.

Step 0c: verbatim raw output of the requested plan command:

```sh
grep -n -A12 '^### S6' docs/phase3/PR3-03-implementation-plan.md
```

```text
451:### S6 — Snapshot queries and CapabilityGateway.invoke
452-
453-Goal: expose the three entitled read operations and implement the finite fake
454-gateway: request commit → start commit → one pure echo outside UoW → finish
455-commit. Saved command results drive subsequent revisions. Completed replay returns
456-the saved finish result with zero fake calls; an uncertain prior start never
457-grants permission to redispatch. No persistent recovery or real adapter activation.
458-
459-**Files:** create
460-`src/researchbase/persistence/capability_gateway_queries.py`; change
461-`src/researchbase/agent_runtime/application/capability_gateway.py`,
462-`src/researchbase/agent_runtime/application/routing.py`,
463-`src/researchbase/agent_runtime/ports/gateway_repository.py`,
```

Exit code: 0.

The plan explicitly says that completed replay returns the saved finish result
with zero fake calls and an uncertain prior start never grants permission to
redispatch. The exact wording "A committed start is the only permission for
one finite fake call outside the transaction; a lost start response must be
reconciled, not interpreted as permission to redispatch." occurs only in pack
§5, not in the S6 plan section. The plan expresses the same redispatch restriction
in the different wording quoted verbatim above.

All PostgreSQL-dependent gateway claims: **unverified until S8**.
S7 and S8 are not started by this task.

### S6 implementation and evidence limits

The three reads use one `begin_formal_read` snapshot for entitlement and nested
rows. `current_availability`, `effective_outcome`, and
`effective_usage_record_id` are labeled snapshot projections in the Application
read docstrings; the frozen §8 DTO vocabulary is unchanged (no timestamp field
is invented). Keyset SQL is parameterized, scoped by project/task, ascending
`(created_at,id)`, fetches limit+1, and uses typed NULL cursor casts.
Owning-domain `_resolve` supplies validity warnings with saved-seal reads and no
byte acquisition. Stored UNKNOWN_OUTCOME remains separate from reconciliation.

`CapabilityGateway.invoke` uses saved request/start revisions, stable IDs,
identity-based injected consumer trust, and a single pure finite echo only after
a fresh acknowledged committed start. A recovered/replayed start can only look
for a saved finish; absent completion yields INVALID_STATE_TRANSITION with
`Prior start unresolved; explicit reconciliation required.` No new recovery,
transport, real adapter, execution identity, dependency, or scientific promotion.
The immutable FINISHED event and its usage/ref receipt own replayed results,
including UNKNOWN_OUTCOME after a later final reconciliation. Output refs and
trace default empty. Fixture artifacts remain retained candidate inputs; no
scientific validity is inferred from the fake result.

| S6 requirement | Test node name (tests/unit/phase3/) |
| --- | --- |
| Three reads; snapshot authorization; archived/disabled reads; no byte I/O | test_capability_gateway.py::test_snapshot_queries_exact_policy_invocation_and_no_io |
| Empty/tied/keyset pages and exact boundary; limits 1–256 | test_capability_gateway.py::test_snapshot_paging_empty_ties_boundaries_and_no_offset; test_query_limit_rejects_outside_closed_bounds |
| Authorization before existence and denied project scope | test_capability_gateway.py::test_snapshot_query_authorization_precedes_missing_objects; test_query_denied_scope_never_looks_up_existence |
| Canonical refs with owning warnings | test_capability_gateway.py::test_query_refs_use_owning_snapshot_warnings_and_canonical_order |
| One read-only repeatable snapshot; no write/lock SQL or second session | test_capability_gateway_repository.py::test_formal_read_selects_one_readonly_repeatable_snapshot_before_sql; test_queries_use_one_session_for_authority_and_all_nested_rows_without_write_sql |
| Parameterized SQL, scoped tuple order, lookahead boundary | test_capability_gateway_repository.py::test_snapshot_page_sql_scopes_orders_and_fetches_one_lookahead |
| Four outcomes, exact summary/errors, three commits/one call; terminal replay | test_capability_gateway.py::test_invoke_three_commits_one_outside_call_and_saved_terminal_replay; test_capability_routing.py::test_finite_fake_echo_closed_exact_outcomes |
| Lost responses at request/start/finish commits | test_capability_gateway.py::test_invoke_response_loss_at_each_commit |
| Prior start unresolved or no visible commit receipt: no dispatch | test_capability_gateway.py::test_invoke_unresolved_start_without_saved_finish_never_calls_fake; test_invoke_unresolved_commit_with_no_visible_receipt_never_dispatches |
| Arbitrary capability/context/request/echo objects denied | test_capability_gateway.py::test_invoke_arbitrary_capability_is_denied_before_disclosure; test_invoke_rejects_arbitrary_request_without_dispatch; test_capability_routing.py::test_finite_fake_rejects_arbitrary_objects |
| Saved finish remains original after reconciliation; current entitlement on replay | test_capability_gateway.py::test_invoke_saved_unknown_finish_survives_final_reconciliation; test_invoke_replay_rechecks_current_entitlement |

These are unit/recording-session assertions only. Every PostgreSQL-dependent
claim, including query snapshot coherence, SQL parameter typing on PostgreSQL,
lock freedom, visibility, durability, guard/CAS behavior and exactly-once
settlement, is **unverified until S8**. No gateway PostgreSQL suite exists yet;
creating those suites belongs to S8 and is not part of this task.

Deviation S6-E2: `docs/phase3/PR3-03-evidence.md` is outside S6's production/test
file list but explicitly required by this task's Step 0 and verification evidence.
Scope: evidence only. Impact: none on contracts. Disposition: authorized here.
No other outside-file change, frozen-pack change, accepted-migration change,
architecture exception, pyproject.toml or uv.lock change.

Development setup: `python` was unavailable (`zsh:1: command not found: python`);
no Step 0 edits from that failed interpreter invocation ran. Re-executed the
script using python3 successfully. `export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`
preceded every uv command. `uv sync --locked --group dev` exited 0:

```text
Resolved 38 packages in 3ms
Checked 34 packages in 3ms
```

Initial development focused run: exit 1, 325 collected, 324 passed, 1 failed,
0 skipped. Failure: `test_invoke_arbitrary_capability_is_denied_before_disclosure[bad0]`
constructed an invalid context outside its raises block, so ClosedValue validation
raised `VALIDATION_ERROR: injected trusted context required` before invoke.
Corrected the adversarial setup to tamper a constructed context. Subsequent
focused run: exit 0, 328 collected / 328 passed / 0 failed / 0 skipped in 2.34s.
Additional snapshot/entitlement/reconciliation evidence was added afterward.
Ruff formatting was applied to the nine Python paths; `ruff check --fix` corrected
one import-order diagnostic (`Found 1 error (1 fixed, 0 remaining).`).

### S6 separate final verification runs

Every command below runs separately, in the required order. Raw combined
stdout/stderr and exit status are copied below and retained in ignored
`tmp/pr3-03/s6/`. PostgreSQL-dependent gateway behavior remains
**unverified until S8**; these commands do not constitute overall PR acceptance.

#### Interrupted verification attempts (corrected)

```sh
git diff --check HEAD
```

Exit code: `0`. Raw combined stdout/stderr:

```text
```

```sh
uv run ruff check .
```

Exit code: `1`. Raw combined stdout/stderr:

```text
I001 [*] Import block is un-sorted or un-formatted
   --> tests/unit/phase3/test_capability_gateway_repository.py:658:5
    |
656 |       monkeypatch, operation
657 |   ):
658 | /     from contextlib import contextmanager
659 | |
660 | |     from tests.unit.phase3.gateway_fixtures import Fixture, NOW
    | |_______________________________________________________________^
661 |
662 |       f = Fixture()
    |
help: Organize imports

Found 1 error.
[*] 1 fixable with the `--fix` option.
```

```sh
git diff --check HEAD
```

Exit code: `0`. Raw combined stdout/stderr:

```text
```

```sh
uv run ruff check .
```

Exit code: `0`. Raw combined stdout/stderr:

```text
All checks passed!
```

```sh
uv run ruff format --check .
```

Exit code: `0`. Raw combined stdout/stderr:

```text
904 files already formatted
```

```sh
uv run pyright
```

Exit code: `1`. Raw combined stdout/stderr:

```text
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/tests/unit/phase3/test_capability_gateway.py
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/tests/unit/phase3/test_capability_gateway.py:1164:35 - error: Argument of type "AgentExecutionContext | object" cannot be assigned to parameter "context" of type "AgentExecutionContext" in function "invoke"
    Type "AgentExecutionContext | object" is not assignable to type "AgentExecutionContext"
      "object" is not assignable to "AgentExecutionContext" (reportArgumentType)
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/tests/unit/phase3/test_capability_gateway.py:1362:26 - error: Argument of type "object" cannot be assigned to parameter "request" of type "CapabilityRequest" in function "invoke"
    "object" is not assignable to "CapabilityRequest" (reportArgumentType)
2 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### Final required sequence

```sh
git diff --check HEAD
```

Exit code: `0`. Raw combined stdout/stderr:

```text
```

```sh
uv run ruff check .
```

Exit code: `0`. Raw combined stdout/stderr:

```text
All checks passed!
```

```sh
uv run ruff format --check .
```

Exit code: `0`. Raw combined stdout/stderr:

```text
904 files already formatted
```

```sh
uv run pyright
```

Exit code: `0`. Raw combined stdout/stderr:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

```sh
uv run alembic heads
```

Exit code: `0`. Raw combined stdout/stderr:

```text
0080_capability_gateway (head)
```

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_capability_routing.py
```

Exit code: `0`. Raw combined stdout/stderr:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 335 items

tests/unit/phase3/test_capability_gateway.py ........................... [  8%]
........................................................................ [ 29%]
........................................................................ [ 51%]
............................................................             [ 68%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 73%]
.......................................                                  [ 85%]
tests/unit/phase3/test_capability_routing.py ........................... [ 93%]
......................                                                   [100%]

============================= 335 passed in 2.35s ==============================
```

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Exit code: `0`. Raw combined stdout/stderr:

```text
tests/architecture/test_import_boundaries.py .............               [ 32%]
tests/architecture/test_m1_boundaries.py ...                             [ 33%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 38%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 41%]
tests/architecture/test_pr12_boundaries.py ....                          [ 42%]
tests/architecture/test_pr13_boundaries.py ..                            [ 42%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 43%]
tests/architecture/test_pr14_boundaries.py ..                            [ 44%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 45%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 46%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 48%]
tests/architecture/test_pr18_boundaries.py .......                       [ 50%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 56%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 62%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 63%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 71%]
................................                                         [ 80%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 81%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 352 passed, 50 warnings in 22.06s =======================
```

### S6 result and stop

Final required sequence: all seven commands exited 0. Focused unit selection:
335 collected / 335 passed / 0 failed / 0 errors / 0 skipped in 2.35s.
Architecture selection: 352 collected / 352 passed / 0 failed / 0 errors /
0 skipped, 50 warnings in 22.06s. Pyright: 0 errors, 0 warnings, 0 informations
(the tool also prints its version-update notice). Ruff: clean; 904 files formatted.
Alembic sole head: `0080_capability_gateway (head)`.

The earlier static attempt's Pyright failures were deliberately invalid test
arguments crossing a typed boundary; explicit Any casts now express adversarial
runtime tests. The earlier lint failure was an import-order diagnostic in the
new recording-session test. Both failures and subsequent clean results are
retained above, not relabeled PASS. Additional development focused selection
before the final sequence: 335 collected / 335 passed in 2.44s.

No new live PostgreSQL behavior/migration suite was run: those suites belong to
S8. Every PostgreSQL-dependent gateway claim remains **unverified until S8**.
The unit suite's admin environment selector does not turn recording sessions
into database evidence. Overall PR3-03 acceptance and external six-shard gate
remain PENDING. S7 was not started. No full suite/six-shard run, commit, push,
branch creation, accepted-migration edit or dependency edit occurred.

Changed paths (relative to HEAD, including the new untracked query module):

```text
docs/phase3/PR3-03-evidence.md
src/researchbase/agent_runtime/application/capability_gateway.py
src/researchbase/agent_runtime/application/routing.py
src/researchbase/agent_runtime/ports/gateway_repository.py
src/researchbase/persistence/capability_gateway_queries.py
src/researchbase/persistence/capability_gateway_repository.py
tests/unit/phase3/gateway_fixtures.py
tests/unit/phase3/test_capability_gateway.py
tests/unit/phase3/test_capability_gateway_repository.py
tests/unit/phase3/test_capability_routing.py
```

Ignored raw verification logs remain in `tmp/pr3-03/s6/`; pytest trace artifacts
are generated by `test_invoke_three_commits_one_outside_call_and_saved_terminal_replay`
in its per-case tmp_path. The four final focused-run traces were also copied to
`tmp/pr3-03/s6/test_invoke_three_commits_one_{0,1,2,3}.json`; each contains
exactly three commits and one fake call. Deviations S6-E1/E2 above accompany
this handoff.
STOP at S6; next sub-task is S7 under separate authorization.


### S6 small fix — missing saved usage (2026-10-22)

Baseline: `1194dbb`; S6 only. `_saved_completion` now supplies `None` to
`next` and reports `PROVENANCE_CLOSURE_VIOLATION` with
`saved finish usage unavailable` when the FINISHED event's usage row is absent.
`test_invoke_saved_finish_missing_usage_reports_provenance_violation` removes
that exact usage row after a completed invoke, asserts the domain error rather
than StopIteration, and checks zero extra dispatches, commits or table changes.

Source inspection confirms that `SqlAlchemyGatewayRepository`
(`src/researchbase/persistence/capability_gateway_repository.py:88`) inherits
`SqlAlchemyTaskSafetyRepository.rows`
(`src/researchbase/persistence/task_safety_repository.py:92`). Its `SAFETY_TABLES`
allowlist includes `budget_usage_records` (line 18), and `rows` selects by
`research_task_id` ordered by `id`. Real adapter support for this replay lookup:
**unverified until S8**; unit fixtures do not prove it. No gateway PostgreSQL
suite exists in this S6 baseline; adding/running gateway acceptance belongs to S8.
No persistence implementation or SQL changed, so no existing PostgreSQL suite
is touched by this fix. S7/S8 and the six-shard full suite were not run.

Changed paths (no commit, push or branch creation):

```text
docs/phase3/PR3-03-evidence.md
src/researchbase/agent_runtime/application/capability_gateway.py
tests/unit/phase3/test_capability_gateway.py
```

The following checks are separate executions. Before every uv command:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
```

### S6 small-fix raw verification output

Runs 1–4 include the initial Pyright failure in the new test. Corrected the test
to read the saved invocation's usage ID; runs 5–11 verify the corrected source.
All output below is raw combined stdout/stderr; empty output is shown as an empty
code block. Every command was executed separately.

#### Small-fix run 1

```sh
git diff --check HEAD
```

```text
```

Exit code: 0.

#### Small-fix run 2

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run ruff check .
```

```text
All checks passed!
```

Exit code: 0.

#### Small-fix run 3

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run ruff format --check .
```

```text
904 files already formatted
```

Exit code: 0.

#### Small-fix run 4

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run pyright
```

```text
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/tests/unit/phase3/test_capability_gateway.py
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/tests/unit/phase3/test_capability_gateway.py:1162:80 - error: Cannot access attribute "usage_record_id" for class "CapabilityResult"
    Attribute "usage_record_id" is unknown (reportAttributeAccessIssue)
1 error, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

Exit code: 1.

#### Small-fix run 5

```sh
git diff --check HEAD
```

```text
```

Exit code: 0.

#### Small-fix run 6

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run ruff check .
```

```text
All checks passed!
```

Exit code: 0.

#### Small-fix run 7

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run ruff format --check .
```

```text
904 files already formatted
```

Exit code: 0.

#### Small-fix run 8

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run pyright
```

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

Exit code: 0.

#### Small-fix run 9

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run alembic heads
```

```text
0080_capability_gateway (head)
```

Exit code: 0.

#### Small-fix run 10

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_capability_routing.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 336 items

tests/unit/phase3/test_capability_gateway.py ........................... [  8%]
........................................................................ [ 29%]
........................................................................ [ 50%]
.............................................................            [ 69%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 73%]
.......................................                                  [ 85%]
tests/unit/phase3/test_capability_routing.py ........................... [ 93%]
......................                                                   [100%]

============================= 336 passed in 2.41s ==============================
```

Exit code: 0.

#### Small-fix run 11

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

```text
tests/architecture/test_import_boundaries.py .............               [ 32%]
tests/architecture/test_m1_boundaries.py ...                             [ 33%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 38%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 41%]
tests/architecture/test_pr12_boundaries.py ....                          [ 42%]
tests/architecture/test_pr13_boundaries.py ..                            [ 42%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 43%]
tests/architecture/test_pr14_boundaries.py ..                            [ 44%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 45%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 46%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 48%]
tests/architecture/test_pr18_boundaries.py .......                       [ 50%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 56%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 62%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 63%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 71%]
................................                                         [ 80%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 81%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane119/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 352 passed, 50 warnings in 20.13s =======================
```

Exit code: 0.

Final counts: focused unit run 336 collected / 336 passed / 0 failed / 0 skipped;
architecture run 352 collected / 352 passed / 0 failed / 0 skipped, 50 warnings.
Final static checks exit 0; Ruff format reports 904 files already formatted;
Pyright reports 0 errors / 0 warnings / 0 informations; Alembic reports
`0080_capability_gateway (head)`. The initial failed Pyright run is not PASS.
PostgreSQL tests: NOT RUN (no persistence/SQL change or existing gateway PG suite
at S6); real gateway repository behavior remains **unverified until S8**.
No full suite, six-shard run, S7/S8 work or overall PR acceptance is claimed.

Post-evidence whitespace verification (separate execution):

```sh
git diff --check HEAD
```

```text
docs/phase3/PR3-03-evidence.md:3601: new blank line at EOF.
```

Exit code: 2. Removed the extra blank line at EOF.

Repeated post-evidence whitespace verification (separate execution):

```sh
git diff --check HEAD
```

```text
```

Exit code: 0 (empty output).

## S7 — Complete unit and architecture boundary evidence

PostgreSQL evidence status for this historical section: **not run** in this review. The results below belong to the original run; current reruns are quoted in S8.

Scope: S7 only. Tests and this evidence changed; no production defect was found.
No frozen pack, accepted migration, dependency manifest/lock or architecture
exception was edited. ADR-0025 admissions are unchanged. No S8 or six-shard/full
suite run was started. No commit, push or branch creation was performed.

The recording UoW now rejects nesting, and retry tests inject failures through
the repository port instead of a private service method. New regressions cover
all tuple pins, changed-policy cap boundaries, unreviewed intake and metadata,
self-weakening, inert tool injection, trust-object identity, closed repository
writes and common Human/Agent execution. The AST scanner checks actual import
dependencies (including aliases and relative imports); deliberate violations
prove detection. The private AST call-count assertion for `finite_fake_echo`
has been removed. The existing Human/Agent runtime spy
`test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects` checks
`builtins.open`, `importlib.import_module`, `socket.socket`, `subprocess.Popen`
and nested `TaskSafetyService.execute`, plus transaction counts and allowed writes.

**PostgreSQL-dependent claims: unverified until S8.** Recording-session traces,
rollback doubles and ORM metadata establish unit/structural evidence only.
PostgreSQL lock correctness, contention, durable atomicity, SQL hash parity,
normal-role DML and migration/guard behavior remain **unverified until S8**.
Setting RB_TEST_ADMIN_URL on the required commands does not turn these suites
into PostgreSQL integration evidence. PostgreSQL suites: NOT RUN in S7; no SQL
or persistence implementation changed and S8 owns those suites.

### S7 Deviations and limits

- **S7-D1 — required evidence path:** `docs/phase3/PR3-03-evidence.md` is outside
  the seven named test paths. Scope: append this mandatory S7 checklist, raw
  verification output and handoff. Evidence: the task explicitly requires the
  checklist here. Impact: documentation only; no contract change. Disposition:
  within the user's explicit evidence authorization; no other path exception.
- Review rejected the previous evidence mapping and its unsupported audit claim
  (P1-1/P1-2). This correction adds explicit behavioral mappings and a reproducible
  audit; it makes no independent-review or overall gate-success claim.
- A valid 65536-byte parameter payload is unreachable under the frozen closed
  1024-character message schema. Tests admit the largest escaped message and
  reject padded bytes/declared sizes at 65535, 65536 and 65537. The 8192-byte
  summary boundary and +1 rejection are reachable and exercised after NFC.

Scanner boundary choice: **document the existing limits; do not narrow INTERNAL**.
`INTERNAL` allows the entire `researchbase.application` and
`researchbase.foundation` trees (alongside the other listed internal packages);
it does not inspect those dependencies transitively. Call-effect checks cover
only `ast.Name` calls (`__import__`, `eval`, `exec`, `open`, `compile`). Attribute
calls such as `builtins.open` and `os.system` are not checked by that rule.
Imports of `builtins`/`os` are separately rejected, but that is not a general
attribute-call or dynamic-attribute guard. The runtime spies cover the named
effect points above on the exercised paths; neither scanner nor spies establish
a complete dynamic call graph or sandbox guarantee.

### S7 §9.1 case-to-passing-node checklist

Each listed node was collected and passed in the final unit or architecture
run below; no required node skipped. Parameterized nodes are expanded literally,
not inferred from a function name. Existing TaskCommand/SafetyCommand/S1 vectors
retain their original expected hashes. Duplicate node listings have been removed;
each node appears once. The two common-boundary runtime-spy cases are mapped
explicitly under no-nested-UoW (HUMAN) and disabled-execution (AGENT). Both cases
also assert common caller behavior and absence of hidden effects. The
summary-boundary helper also covers NFC and parameter bytes.

- [x] Closed DTOs, missing/unknown nested fields and defaults:

```text
tests/unit/phase3/test_agent_tool_policy.py::test_policy_set_order_defaults_and_duplicates
tests/unit/phase3/test_capability_gateway_contracts.py::test_read_nested_extras_and_projection_literals
tests/unit/phase3/test_capability_gateway_contracts.py::test_nested_extras_and_missing_fields[<lambda>0]
tests/unit/phase3/test_capability_gateway_contracts.py::test_nested_extras_and_missing_fields[<lambda>1]
tests/unit/phase3/test_capability_gateway_contracts.py::test_nested_extras_and_missing_fields[<lambda>2]
tests/unit/phase3/test_capability_gateway_contracts.py::test_nested_extras_and_missing_fields[<lambda>3]
tests/unit/phase3/test_capability_gateway_contracts.py::test_resources_material_is_fixed_six_place_and_nulls_expand
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[0]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[1]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[2]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[3]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[4]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[5]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[6]
tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips[7]
```

- [x] NFC, lowercase UUID decoding and command set order:

```text
tests/unit/phase3/test_agent_tool_policy.py::test_permission_normalization_and_projection
tests/unit/phase3/test_capability_gateway_contracts.py::test_command_reference_order_and_uuid_normalization
```

- [x] UUID, integer/bool, deadline and parameter declaration rejection:

```text
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates0]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates1]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates2]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates3]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates4]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates5]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates6]
tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy[updates7]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[deadline_seconds-True]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[parameters_byte_size-True]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[deadline_seconds-61]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[parameters_byte_size-65537]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[requested_parameters_hash-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[step_id-latest]
tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields[invocation_id-value6]
tests/unit/phase3/test_capability_gateway_contracts.py::test_capability_request_command_ids_must_be_distinct
```

- [x] Exact decimal scale, finite values and fixed six-place material:

```text
tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources[0.0000001]
tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources[NaN]
tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources[Infinity]
tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources[-Infinity]
tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources[0.5]
tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources[True]
```

- [x] Six frozen literal byte/hash vectors (all six nodes):

```text
tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[schema]
tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[empty-set]
tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[fake-set]
tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[empty-policy]
tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[allow-deny-policy]
tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[cafe-parameters]
```

- [x] All four GatewayCommand variants; authenticated actor material and public finish denial:

```text
tests/unit/phase3/test_capability_gateway_contracts.py::test_four_command_roundtrips_and_actor_material[register_agent_tool_policy-args0]
tests/unit/phase3/test_capability_gateway_contracts.py::test_four_command_roundtrips_and_actor_material[request_capability_invocation-args1]
tests/unit/phase3/test_capability_gateway_contracts.py::test_four_command_roundtrips_and_actor_material[start_capability_invocation-args2]
tests/unit/phase3/test_capability_gateway_contracts.py::test_four_command_roundtrips_and_actor_material[finish_capability_invocation-args3]
tests/unit/phase3/test_capability_gateway_contracts.py::test_public_finish_and_trusted_context_cannot_be_deserialized
tests/unit/phase3/test_capability_gateway_contracts.py::test_trusted_context_has_no_material_or_public_decoder
```

- [x] Old TaskCommand vectors and normalization unchanged:

```text
tests/unit/phase3/test_research_task_contracts.py::test_fixed_vectors[{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"autonomy_level":"A0","inputs":[],"objective":"Caf\xe9 replication","strategy_id":"human_guided_research","strategy_version":"1.0.0","task_type":"LITERATURE_RESEARCH"},"command_id":"01900000-0000-7000-8000-000000000004","command_name":"create_research_task","expected_row_version":null,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}-643ae964496ab90b75b5e20140a3ddafa962a542f80d31598fcd10db313615b8]
tests/unit/phase3/test_research_task_contracts.py::test_fixed_vectors[{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"edges":[{"dependent_id":"01900000-0000-7000-8000-000000000011","predecessor_id":"01900000-0000-7000-8000-000000000010"}],"nodes":[{"agent_role":null,"capability_id":null,"inputs":[],"ordinal":2,"parent_step_id":null,"step_id":"01900000-0000-7000-8000-000000000010","step_type":"PLAN"},{"agent_role":"research","capability_id":null,"inputs":[{"id":"01900000-0000-7000-8000-000000000020","type":"ARTIFACT_VERSION"},{"id":"01900000-0000-7000-8000-000000000021","type":"SOURCE_VERSION"}],"ordinal":1,"parent_step_id":"01900000-0000-7000-8000-000000000010","step_id":"01900000-0000-7000-8000-000000000011","step_type":"RESEARCH"}]},"command_id":"01900000-0000-7000-8000-000000000005","command_name":"create_task_plan","expected_row_version":1,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}-9213a547322e6ea8d35c04f3046af0b034afc8fe3c8c83c05bbeb0d2148d6eed]
tests/unit/phase3/test_research_task_contracts.py::test_fixed_vectors[{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"reason":"Planning withdrawn."},"command_id":"01900000-0000-7000-8000-000000000006","command_name":"cancel_research_task","expected_row_version":2,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}-743c2a1084f9a7c8c1cdcf74a470b48fe191f166708ec2f0fca3aafcfc4a5067]
tests/unit/phase3/test_research_task_contracts.py::test_order_independence_and_nfc
```

- [x] Old SafetyCommand vectors unchanged:

```text
tests/unit/phase3/test_task_safety_contracts.py::test_fixed_hash_vectors[{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"budget":{"currency":"USD","hard_stop":true,"max_agent_steps":50,"max_code_iterations":3,"max_experiment_runs":5,"max_gpu_hours":"0.000000","max_llm_calls":50,"max_parallel_branches":1,"max_search_calls":20,"max_token_cost":"5.000000","max_tree_depth":3,"max_tree_nodes":10,"max_wall_time_seconds":1800,"pricing_basis":"fake-usd-v1"},"budget_id":"01900000-0000-7000-8000-000000000010","checkpoint":{"a3_authorized":false,"allowed_code_paths":[],"allowed_dataset_snapshot_ids":[],"allowed_metric_version_ids":[],"allowed_network_hosts":[],"maximum_autonomy":"A2","network_mode":"DENY","required_types":["plan_review"],"timeout_seconds":86400},"checkpoint_policy_id":"01900000-0000-7000-8000-000000000012","reason":"Caf\xe9 pilot limits.","termination":{"budget_stop":true,"confidence_stop_enabled":false,"confidence_stop_threshold":null,"duplicate_hypothesis_enabled":false,"duplicate_hypothesis_threshold":null,"evaluator_version":null,"human_stop":true,"max_no_improvement_iterations":2,"min_progress_enabled":false,"min_progress_score":null,"policy_stop":true,"repeated_failure_threshold":2,"score_direction":null,"score_metric_version_id":null,"success_condition":null,"success_condition_enabled":false},"termination_policy_id":"01900000-0000-7000-8000-000000000011"},"command_id":"01900000-0000-7000-8000-000000000004","command_name":"bind_task_policies","expected_row_version":1,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}\n-89dd196e873985a5caffb868135bf79efc841f387d1b8836fa5b7e27fc19313e]
tests/unit/phase3/test_task_safety_contracts.py::test_fixed_hash_vectors[{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"deadline_seconds":60,"observed_depth":0,"observed_parallel_branches":1,"operation_id":"01900000-0000-7000-8000-000000000020","reason":"Bounded fake call.","resources":{"agent_steps":1,"code_iterations":0,"experiment_runs":0,"gpu_hours":"0.000000","llm_calls":1,"search_calls":0,"token_cost":"0.125000","tree_nodes":0,"wall_time_seconds":60},"step_id":"01900000-0000-7000-8000-000000000021"},"command_id":"01900000-0000-7000-8000-000000000005","command_name":"reserve_task_budget","expected_row_version":4,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}\n-10710e357af6f0e4ec592ba079aae570a60e78b2b26e85b82259a74ba935c0ab]
tests/unit/phase3/test_task_safety_contracts.py::test_fixed_hash_vectors[{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"checkpoint_id":"01900000-0000-7000-8000-000000000030","expected_checkpoint_row_version":1,"reason":"Extension intent only; new task required.","response":"APPROVED"},"command_id":"01900000-0000-7000-8000-000000000006","command_name":"respond_human_checkpoint","expected_row_version":7,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}\n-a364746081f6cfe74e4102f9efd1f2da2751311a05228f748d06dd4853df687e]
tests/unit/phase3/test_task_safety_contracts.py::test_complete_extension_request_material
```

- [x] Old S1 vectors and HarnessManifest material unchanged:

```text
tests/unit/phase3/test_agent_version_contracts.py::test_literal_vectors[material0-4cc1af5312be685ea559d09e0f2e6ff459e920b03fb7ba82218172346278d3d7]
tests/unit/phase3/test_agent_version_contracts.py::test_literal_vectors[material1-19b7537803f35a6c1395c4b48abf8af8e2eb85b5da6d7b804c9881bb548224a8]
tests/unit/phase3/test_agent_version_contracts.py::test_literal_vectors[material2-b9c60b8b598d025aab9f0fceaeabfc1f11173eb58f8084e2043fb1a224359416]
tests/unit/phase3/test_harness_manifest.py::test_order_and_material[skills]
tests/unit/phase3/test_harness_manifest.py::test_order_and_material[plugins]
tests/unit/phase3/test_harness_manifest.py::test_order_and_material[adapters]
tests/unit/phase3/test_harness_manifest.py::test_order_and_material[hooks]
tests/unit/phase3/test_harness_manifest.py::test_order_and_material[mcp_capabilities]
tests/unit/phase3/test_harness_manifest.py::test_order_and_material[reference_libraries]
tests/unit/phase3/test_harness_manifest.py::test_closed_and_byte_hash_distinction
```

- [x] Reference set sorting, duplicate rejection, combined bound and all six families:

```text
tests/unit/phase3/test_capability_gateway_contracts.py::test_refs_sort_duplicate_and_combined_bound
tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip[RESEARCH_QUESTION_VERSION]
tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip[HYPOTHESIS_VERSION]
tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip[CLAIM_VERSION]
tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip[SOURCE_VERSION]
tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip[ARTIFACT_VERSION]
tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip[MANUSCRIPT_VERSION]
```

- [x] Parameter UTF-8 bytes, retained owning hash, 65535/65536/65537 declaration/byte rejection and message limit:

```text
tests/unit/phase3/test_capability_gateway_contracts.py::test_retained_parameters_have_separate_owning_hash
tests/unit/phase3/test_capability_gateway_contracts.py::test_parameters_message_limits_and_scale
tests/unit/phase3/test_capability_gateway_contracts.py::test_parameter_byte_ceiling_does_not_bypass_closed_schema[65535]
tests/unit/phase3/test_capability_gateway_contracts.py::test_parameter_byte_ceiling_does_not_bypass_closed_schema[65536]
tests/unit/phase3/test_capability_gateway_contracts.py::test_parameter_byte_ceiling_does_not_bypass_closed_schema[65537]
```

- [x] Summary UTF-8 boundary, NFC before byte count, exact 8192 and +1 rejection:

```text
tests/unit/phase3/test_capability_gateway_contracts.py::test_summary_utf8_byte_bound[at-byte-limit]
tests/unit/phase3/test_capability_gateway_contracts.py::test_summary_utf8_byte_bound[over-byte-limit]
tests/unit/phase3/test_capability_gateway_contracts.py::test_largest_escaped_parameters_and_nfc_summary_boundaries
```

- [x] Exact six-key permission match; absence/empty policy and DENY precedence:

```text
tests/unit/phase3/test_agent_tool_policy.py::test_exact_effects[effects0-False]
tests/unit/phase3/test_agent_tool_policy.py::test_exact_effects[effects1-True]
tests/unit/phase3/test_agent_tool_policy.py::test_exact_effects[effects2-False]
tests/unit/phase3/test_agent_tool_policy.py::test_exact_effects[effects3-False]
tests/unit/phase3/test_agent_tool_policy.py::test_exact_effects[effects4-False]
tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback[capability_id]
tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback[capability_version]
tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback[operation]
tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback[adapter_id]
tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback[adapter_version]
tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback[parameter_schema_hash]
```

- [x] Pins/schema mismatch and alias/pattern/whitespace rejection:

```text
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[latest]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[CURRENT]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[main]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[master]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[x/latest]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[echo*]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[echo?]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[^echo$]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[echo.*]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[(echo)]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[echo[0]]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[ echo]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[echo ]
tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny[]
```

- [x] Tool/parallel caps below/equal/above across changed policies, full cross product, no counter reset:

```text
tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes[0-0-True]
tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes[49-0-True]
tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes[50-0-False]
tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes[51-0-False]
tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes[0-1-False]
tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes[0-2-False]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-below-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-below-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-below-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-equal-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-equal-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-equal-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-above-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-above-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-below-calls-above-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-below-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-below-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-below-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-equal-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-equal-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-equal-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-above-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-above-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-equal-calls-above-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-below-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-below-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-below-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-equal-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-equal-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-equal-last]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-above-default]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-above-reduced]
tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch[slots-above-calls-above-last]
tests/unit/phase3/test_capability_gateway.py::test_policy_switch_retains_task_wide_call_count
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[below-task_total_calls-limits0]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[below-task_total_calls-limits1]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[below-task_parallel_invocations-limits0]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[below-task_parallel_invocations-limits1]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[equal-task_total_calls-limits0]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[equal-task_total_calls-limits1]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[equal-task_parallel_invocations-limits0]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[equal-task_parallel_invocations-limits1]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[above-task_total_calls-limits0]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[above-task_total_calls-limits1]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[above-task_parallel_invocations-limits0]
tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts[above-task_parallel_invocations-limits1]
```

- [x] Phase, authority, project disclosure and task-safety intersection:

```text
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes0]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes1]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes2]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes3]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes4]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes5]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes6]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes7]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes8]
tests/unit/phase3/test_capability_routing.py::test_routing_exclusions[changes9]
```

- [x] Self-weakening and self-install remain forbidden despite injected instructions:

```text
tests/unit/phase3/test_capability_routing.py::test_injected_message_never_overrides_self_weakening_exclusion[self_install]
tests/unit/phase3/test_capability_routing.py::test_injected_message_never_overrides_self_weakening_exclusion[governing_file_edits]
tests/unit/phase3/test_capability_routing.py::test_injected_message_never_overrides_self_weakening_exclusion[changing_pins]
tests/unit/phase3/test_capability_routing.py::test_injected_message_never_overrides_self_weakening_exclusion[same_execution_weakening]
```

- [x] Reference-only and missing policy/version; exact registry, manifest and availability pins:

```text
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[reference-only]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[entry-phase]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[missing-entry]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[no-version]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[no-policy]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[wrong-consumer]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[foreign-registry]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[unfrozen-intake]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[wrong-harness]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[availability]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[policy-version]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[capability-set]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[manifest-skill]
tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only[manifest-adapter]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[missing-intake]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[foreign-intake]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[intake-hash]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[duplicate-intake]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[unfrozen-registry]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[registry-hash]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[policy-id]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[policy-digest]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[step]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[strategy]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[model]
tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required[prompt]
```

- [x] Unreviewed intake/scripts/transitive capability and descriptive authority injection denial:

```text
tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution[description]
tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution[scripts]
tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution[transitive_capabilities]
tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution[approved]
tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution[role]
tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution[popularity]
```

- [x] Supplied canonical registry bytes only, bounded/closed schema, no discovery/IO:

```text
tests/unit/phase3/test_capability_routing.py::test_exact_route_and_supplied_byte_loader
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw0]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw1]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw2]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw3]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw4]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw5]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw6]
tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative[raw7]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[{"schema_version":1,"schema_version":1,"entries":[]}]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[{"schema_version":NaN,"entries":[]}]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[{}]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[\xff]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[[]]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[{ "entries":[],"schema_version":1}]
tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[]
tests/unit/phase3/test_capability_routing.py::test_registry_byte_limit_and_non_executable_tuple
tests/unit/phase3/test_capability_routing.py::test_loader_does_no_discovery_or_io
```

- [x] Only finite pure fake executes; arbitrary objects denied; all four exact outcomes:

```text
tests/unit/phase3/test_capability_routing.py::test_finite_fake_echo_closed_exact_outcomes[SUCCEEDED-echo-None]
tests/unit/phase3/test_capability_routing.py::test_finite_fake_echo_closed_exact_outcomes[FAILED-Fake failure.-ADAPTER_UNAVAILABLE]
tests/unit/phase3/test_capability_routing.py::test_finite_fake_echo_closed_exact_outcomes[UNKNOWN_OUTCOME-Fake outcome unknown.-INVALID_STATE_TRANSITION]
tests/unit/phase3/test_capability_routing.py::test_finite_fake_echo_closed_exact_outcomes[CANCELLED-Fake cancelled.-None]
tests/unit/phase3/test_capability_routing.py::test_finite_fake_rejects_arbitrary_objects[value0]
tests/unit/phase3/test_capability_routing.py::test_finite_fake_rejects_arbitrary_objects[value1]
tests/unit/phase3/test_capability_routing.py::test_finite_fake_rejects_arbitrary_objects[None]
```

- [x] Recorded request/start/finish three transactions, fake outside every UoW and lock, stable command identities (PostgreSQL transactions/locks unverified until S8):

```text
tests/unit/phase3/test_capability_gateway.py::test_stable_ids_across_fresh_whole_transaction_retry
tests/unit/phase3/test_capability_gateway.py::test_lifecycle_retry_ids_stable_and_single_settlement
tests/unit/phase3/test_capability_gateway.py::test_invoke_three_commits_one_outside_call_and_saved_terminal_replay[SUCCEEDED-Finite \xe9cho.-None]
tests/unit/phase3/test_capability_gateway.py::test_invoke_three_commits_one_outside_call_and_saved_terminal_replay[FAILED-Fake failure.-ADAPTER_UNAVAILABLE]
tests/unit/phase3/test_capability_gateway.py::test_invoke_three_commits_one_outside_call_and_saved_terminal_replay[UNKNOWN_OUTCOME-Fake outcome unknown.-INVALID_STATE_TRANSITION]
tests/unit/phase3/test_capability_gateway.py::test_invoke_three_commits_one_outside_call_and_saved_terminal_replay[CANCELLED-Fake cancelled.-None]
```

- [x] Human/Agent same Application boundary; Human OWNER registration:

```text
tests/unit/phase3/test_capability_gateway.py::test_registration_requires_current_human_owner[AGENT-OWNER]
tests/unit/phase3/test_capability_gateway.py::test_registration_requires_current_human_owner[HUMAN-RESEARCHER]
tests/unit/phase3/test_capability_gateway.py::test_registration_requires_current_human_owner[HUMAN-VIEWER]
tests/unit/phase3/test_capability_gateway.py::test_entitled_agent_request_uses_same_application_command
```

- [x] Registration single transaction, complete immutable policy and no reservation:

```text
tests/unit/phase3/test_capability_gateway.py::test_registration_one_transaction_no_reservation_and_complete_policy
tests/unit/phase3/test_capability_gateway.py::test_registration_rollback[agent_tool_policies]
tests/unit/phase3/test_capability_gateway.py::test_registration_rollback[agent_tool_policy_permissions]
```

- [x] Recording-UoW atomic reserve/request and settlement/finish, rollback injection at every write stage (PostgreSQL atomicity unverified until S8):

```text
tests/unit/phase3/test_capability_gateway.py::test_request_atomic_effects_exact_vector_refs_and_no_nested_safety
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[task]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[research_task_command_receipts]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[budget_reservations]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[capability_invocations]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[capability_invocation_events]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[capability_invocation_refs]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[research_task_events]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[research_task_receipt_events]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[constraints]
tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage[commit]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[task]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[research_task_command_receipts]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[budget_usage_records]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[invocation_update]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[capability_invocation_events]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[research_task_events]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[research_task_receipt_events]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[constraints]
tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage[commit]
```

- [x] Failure/unknown/cancellation and reconciliation preserve old unknown history:

```text
tests/unit/phase3/test_capability_gateway.py::test_start_zero_new_accounting_and_prestart_cancel_retains_counts
tests/unit/phase3/test_capability_gateway.py::test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent[SUCCEEDED]
tests/unit/phase3/test_capability_gateway.py::test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent[FAILED]
tests/unit/phase3/test_capability_gateway.py::test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent[UNKNOWN_OUTCOME]
tests/unit/phase3/test_capability_gateway.py::test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent[CANCELLED]
tests/unit/phase3/test_capability_gateway.py::test_reconciliation_append_only_and_saved_event_results[SUCCEEDED]
tests/unit/phase3/test_capability_gateway.py::test_reconciliation_append_only_and_saved_event_results[FAILED]
tests/unit/phase3/test_capability_gateway.py::test_reconciliation_append_only_and_saved_event_results[CANCELLED]
tests/unit/phase3/test_capability_gateway.py::test_unknown_reservation_still_occupies_slot_and_full_budget
tests/unit/phase3/test_capability_gateway.py::test_unknown_does_not_advance_final_failure_streak_until_reconciliation
```

- [x] Replay never calls fake, lost response at each commit, unresolved start denies redispatch:

```text
tests/unit/phase3/test_capability_gateway.py::test_invoke_response_loss_at_each_commit[1]
tests/unit/phase3/test_capability_gateway.py::test_invoke_response_loss_at_each_commit[2]
tests/unit/phase3/test_capability_gateway.py::test_invoke_response_loss_at_each_commit[3]
tests/unit/phase3/test_capability_gateway.py::test_invoke_unresolved_start_without_saved_finish_never_calls_fake
tests/unit/phase3/test_capability_gateway.py::test_invoke_unresolved_commit_with_no_visible_receipt_never_dispatches
tests/unit/phase3/test_capability_gateway.py::test_invoke_saved_unknown_finish_survives_final_reconciliation
```

- [x] Replay precedes stale state/CAS after simulated waits and still requires current entitlement (PostgreSQL replay/waits unverified until S8):

```text
tests/unit/phase3/test_capability_gateway.py::test_saved_replay_precedes_stale_cas_role_availability_and_preflight_failure[False]
tests/unit/phase3/test_capability_gateway.py::test_saved_replay_precedes_stale_cas_role_availability_and_preflight_failure[True]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[share]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[project]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[command]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[task_key]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[agent_key]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[version_key]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[task_row]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[steps]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[checkpoints]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[availability]
tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics[invocations]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[share-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[share-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[project-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[project-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[command-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[command-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[task_key-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[task_key-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[agent_key-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[agent_key-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[version_key-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[version_key-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[task_row-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[task_row-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[steps-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[steps-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[checkpoints-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[checkpoints-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[availability-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[availability-False]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[invocations-True]
tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability[invocations-False]
tests/unit/phase3/test_capability_gateway.py::test_invoke_replay_rechecks_current_entitlement
```

- [x] Trusted capability/context identity and identical-but-distinct observation denial:

```text
tests/unit/phase3/test_capability_gateway.py::test_identity_trust_and_context_binding[new_instance]
tests/unit/phase3/test_capability_gateway.py::test_identity_trust_and_context_binding[no_context]
tests/unit/phase3/test_capability_gateway.py::test_identity_trust_and_context_binding[wrong_scope]
tests/unit/phase3/test_capability_gateway.py::test_identity_trust_and_context_binding[wrong_principal]
tests/unit/phase3/test_capability_gateway.py::test_public_self_supplied_observation_is_forbidden
tests/unit/phase3/test_capability_gateway.py::test_equal_but_distinct_finish_observation_is_untrusted
```

- [x] No-nested-UoW or nested safety command; runtime effect spies and exactly three recorded transactions (PostgreSQL transaction correctness unverified until S8):

```text
tests/unit/phase3/test_capability_gateway.py::test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects[HUMAN]
```

- [x] Tool injection is inert text, no authority/policy/scientific promotion or hidden dispatch:

```text
tests/unit/phase3/test_capability_gateway.py::test_injected_tool_text_is_inert_and_replay_never_dispatches
```

- [x] Planning execution stays disabled after runtime invocation; read.execution_enabled is False and no stored execution_id:

```text
tests/unit/phase3/test_capability_gateway.py::test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects[AGENT]
```

- [x] Repository cannot write scientific/governance/execution tables or generic JSON refs:

```text
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_repository_cannot_promote_or_write_scientific_tables[claims]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_repository_cannot_promote_or_write_scientific_tables[measurements]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_repository_cannot_promote_or_write_scientific_tables[runs]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_repository_cannot_promote_or_write_scientific_tables[artifact_versions]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_repository_cannot_promote_or_write_scientific_tables[approval_decisions]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_repository_cannot_promote_or_write_scientific_tables[agent_executions]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_ref_insert_cannot_smuggle_generic_or_execution_state[target_type]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_ref_insert_cannot_smuggle_generic_or_execution_state[target_id]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_ref_insert_cannot_smuggle_generic_or_execution_state[payload]
tests/unit/phase3/test_capability_gateway_repository.py::test_gateway_ref_insert_cannot_smuggle_generic_or_execution_state[execution_id]
```

- [x] Recorded repository lock/callback sequencing and construction only (PostgreSQL correctness unverified until S8):

```text
tests/unit/phase3/test_capability_gateway_repository.py::test_no_sql_at_uow_or_adapter_construction
tests/unit/phase3/test_capability_gateway_repository.py::test_entering_uow_constructs_gateway_without_sql
tests/unit/phase3/test_capability_gateway_repository.py::test_lifecycle_invocation_identity_resolved_after_prefix_before_agent_keys
```

- [x] Architecture: no domain ORM/transport/SDK imports, no direct Agent persistence/credentials or process/network/filesystem/provider/queue dependencies:

```text
tests/architecture/test_pr3_03_boundaries.py::test_runtime_import_dependencies_exclude_persistence_transport_sdk_and_effects
tests/architecture/test_pr3_03_boundaries.py::test_public_port_and_values_do_not_admit_credentials_execution_or_promotion
```

- [x] Architecture: deliberate violations detected by scanner, including aliases and relative imports:

```text
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[import sqlalchemy as innocent]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[from fastapi import FastAPI]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[from researchbase.persistence import uow]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[from ...persistence import models]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[import unknown_provider_sdk]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[import subprocess as runner]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[from pathlib import Path]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[__import__('researchbase.persistence')]
tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation[open('credentials')]
tests/architecture/test_pr3_03_boundaries.py::test_domain_scanner_rejects_application_and_ports
```

- [x] Architecture: no new dependencies, concrete FK refs and no scientific JSON ownership:

```text
tests/architecture/test_pr3_03_boundaries.py::test_gateway_tables_use_concrete_refs_and_own_no_scientific_json_state
tests/architecture/test_pr3_03_boundaries.py::test_runtime_dependencies_remain_the_accepted_set
```

- [x] Existing disabled-execution transition regressions:

```text
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[resume_research_task-CREATED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[resume_research_task-CREATED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[resume_research_task-PLANNING-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[resume_research_task-PLANNING-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[resume_research_task-CANCELLED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[resume_research_task-CANCELLED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_task_step-CREATED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_task_step-CREATED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_task_step-PLANNING-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_task_step-PLANNING-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_task_step-CANCELLED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_task_step-CANCELLED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[fail_task_step-CREATED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[fail_task_step-CREATED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[fail_task_step-PLANNING-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[fail_task_step-PLANNING-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[fail_task_step-CANCELLED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[fail_task_step-CANCELLED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[finish_task_step-CREATED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[finish_task_step-CREATED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[finish_task_step-PLANNING-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[finish_task_step-PLANNING-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[finish_task_step-CANCELLED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[finish_task_step-CANCELLED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_research_task-CREATED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_research_task-CREATED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_research_task-PLANNING-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_research_task-PLANNING-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_research_task-CANCELLED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[start_research_task-CANCELLED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[pause_research_task-CREATED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[pause_research_task-CREATED-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[pause_research_task-PLANNING-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[pause_research_task-PLANNING-True]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[pause_research_task-CANCELLED-False]
tests/unit/phase3/test_research_task_graph.py::test_transition_matrix[pause_research_task-CANCELLED-True]
```

The explicit no-nested-UoW and disabled-execution bullets map to runtime
assertions in `test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects`:
the former uses its HUMAN node and the latter its AGENT node. The DTO projection
node is back under Closed DTOs. All four injected self-weakening cases are listed
once under Self-weakening. The six `test_each_permission_pin_is_required_without_fallback`
nodes remain under Exact six-key permission match, and
`test_registry_byte_limit_and_non_executable_tuple` remains under Supplied canonical
registry bytes. The reproducible audit below checks these locations, every node's
presence in the inventory, duplicates and empty checklist entries.

### S7 exact verification commands and raw output

Evidence-quality correction on baseline `6e9cdf0`. This sequence supersedes the
previous S7 verification transcript. Each command ran separately after
`export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`. Combined stdout/stderr is
pasted raw below, with each observed exit code. This seven-command transcript records separate runs; the reviewer-requested
combined capture is withdrawn below. Raw captures are retained under ignored `tmp/pr3-03/s7-fix-*.txt`.

```sh
git diff --check HEAD
```

```text
```

Exit code: 0.

```sh
uv run ruff check .
```

```text
All checks passed!
```

Exit code: 0.

```sh
uv run ruff format --check .
```

```text
905 files already formatted
```

Exit code: 0.

```sh
uv run pyright
```

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

Exit code: 0.

```sh
uv run alembic heads
```

```text
0080_capability_gateway (head)
```

Exit code: 0.

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/unit/phase3
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane120
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 953 items

tests/unit/phase3/test_agent_identity_contracts.py .                     [  0%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [  3%]
........................................                                 [  7%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [  9%]
........................................................................ [ 17%]
....                                                                     [ 17%]
tests/unit/phase3/test_agent_version_transports.py ..................    [ 19%]
tests/unit/phase3/test_capability_gateway.py ........................... [ 22%]
........................................................................ [ 29%]
........................................................................ [ 37%]
.................................................................        [ 44%]
tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 45%]
........................................................                 [ 51%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 53%]
.................................................                        [ 58%]
tests/unit/phase3/test_capability_routing.py ........................... [ 61%]
........................................................                 [ 67%]
tests/unit/phase3/test_harness_manifest.py ...............               [ 68%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 71%]
....................................................                     [ 76%]
tests/unit/phase3/test_research_task_graph.py .......................... [ 79%]
........................................................................ [ 86%]
.                                                                        [ 87%]
tests/unit/phase3/test_research_task_transports.py ....................  [ 89%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 90%]
tests/unit/phase3/test_task_checkpoints.py ................              [ 92%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 93%]
tests/unit/phase3/test_task_safety_policies.py ......................... [ 96%]
.......................                                                  [ 98%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================= 953 passed in 7.14s ==============================
```

Exit code: 0.

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

```text
tests/architecture/test_m1_boundaries.py ...                             [ 32%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 36%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 39%]
tests/architecture/test_pr12_boundaries.py ....                          [ 40%]
tests/architecture/test_pr13_boundaries.py ..                            [ 41%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 42%]
tests/architecture/test_pr14_boundaries.py ..                            [ 42%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 43%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 44%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 46%]
tests/architecture/test_pr18_boundaries.py .......                       [ 48%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 49%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 50%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 54%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 60%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 61%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 68%]
................................                                         [ 77%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 78%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 79%]
tests/architecture/test_pr3_03_boundaries.py ..............              [ 83%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 83%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane120/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 366 passed, 50 warnings in 18.86s =======================
```

Exit code: 0.

Observed counts: unit 953 collected / 953 passed / 0 failed / 0 skipped;
architecture 366 collected / 366 passed / 0 failed / 0 skipped, with 50 existing
Alembic deprecation warnings. The removed private AST call-count test accounts
for the architecture count changing from 367 to 366. Pyright reported 0 errors,
0 warnings and 0 informations, followed by a version-update notice. Ruff reported
905 files already formatted. Alembic reported the sole head
`0080_capability_gateway (head)`; live PostgreSQL migration/guard correctness is
**unverified until S8**.

Additional inventory command (collection only, not another test run):

```sh
uv run pytest -o addopts='' --collect-only -q tests/unit/phase3 tests/architecture/test_pr3_03_boundaries.py > tmp/pr3-03/s7-fix-node-ids.txt
```

Raw stdout/stderr: empty (node inventory redirected to the named file).
Exit code: 0. The redirected inventory ends with:

```text
967 tests collected in 0.47s
```

### S7 review correction — reproducible checklist and capture audit

P1-1: explicit self-weakening and no-nested-UoW entries now own their behavioral
nodes. Disabled-execution maps to the AGENT runtime-spy node, which asserts
`read.execution_enabled is False` and no persisted `execution_id`. The HUMAN
runtime-spy node maps to no-nested-UoW. The Human/Agent bullet retains its
registration-role and common Application request tests. The tool-injection
bullet retains the inert-text/replay test. No runtime assertion was replaced
with a DTO projection assertion.

P1-2: the six permission-pin nodes remain under Exact six-key permission match;
the registry byte-limit node remains under Supplied canonical registry bytes.
The script below checks each location, every checklist node against
`tmp/pr3-03/s7-fix-node-ids.txt`, duplicates and empty entries. It checks inventory
membership; the recorded pytest executions establish that these nodes passed.

P2-1: the seven raw outputs above came from actual separate tool executions in
the preceding turn. The saved captures were displayed in full during this
review correction. The script compares each pasted output to its named capture.
Only terminal blank lines are ignored: the capture-file writer added a final
newline, including for empty output. The separate-run transcript is retained;
the historical combined capture is withdrawn below.

The source of `tmp/pr3-03/s7-checklist-audit.py` is reproduced in full:

```python
from collections import Counter
from pathlib import Path

text = Path('docs/phase3/PR3-03-evidence.md').read_text()
section = text.split('### S7 §9.1 case-to-passing-node checklist', 1)[1]
section = section.split('### S7 exact verification commands and raw output', 1)[0]
blocks = section.split('- [x] ')[1:]
locations = {}
empty = []
for block in blocks:
    title = block.splitlines()[0]
    nodes = [line for line in block.splitlines() if line.startswith('tests/')]
    if not nodes:
        empty.append(title)
    for node in nodes:
        locations.setdefault(node, []).append(title)
counts = Counter(
    line for block in blocks for line in block.splitlines()
    if line.startswith('tests/')
)
inventory = set(Path('tmp/pr3-03/s7-fix-node-ids.txt').read_text().splitlines())
missing = sorted(set(counts) - inventory)
duplicates = sorted(node for node, count in counts.items() if count > 1)
print(f'checklist_entries={len(blocks)}')
print(f'mapped_nodes={sum(counts.values())}; unique_nodes={len(counts)}')
print(f'missing_count={len(missing)}; duplicate_count={len(duplicates)}; empty_entry_count={len(empty)}')
print(f'missing={missing}; duplicates={duplicates}; empty_entries={empty}')

required = {
    'reference-only': ('test_pins_phase_and_reference_only[reference-only]', 'Reference-only', 1),
    'injection': ('test_injected_tool_text_is_inert_and_replay_never_dispatches', 'Tool injection', 1),
    'self-weakening': ('test_injected_message_never_overrides_self_weakening_exclusion[', 'Self-weakening', 4),
    'no-nested-UoW': ('test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects[HUMAN]', 'No-nested-UoW', 1),
    'disabled-execution': ('test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects[AGENT]', 'Planning execution stays disabled', 1),
    'six permission pins': ('test_each_permission_pin_is_required_without_fallback[', 'Exact six-key permission match', 6),
    'registry byte limit': ('test_registry_byte_limit_and_non_executable_tuple', 'Supplied canonical registry bytes', 1),
}
for label, (needle, prefix, expected) in required.items():
    matched = [node for node in counts if needle in node]
    assert len(matched) == expected, (label, matched)
    assert all(locations[node][0].startswith(prefix) for node in matched)
    print(f'{label}: {len(matched)} node(s) under {prefix}')
assert not missing and not duplicates and not empty
print('CHECKLIST_AUDIT PASS (inventory membership; passing execution is evidenced by pytest)')

import re

transcript = text.split('### S7 exact verification commands and raw output', 1)[1]
transcript = transcript.split('Additional inventory command', 1)[0]
runs = re.findall(
    r'```sh\n(.*?)\n```\n\n```text\n(.*?)```\n\nExit code: (\d+)\.',
    transcript,
    flags=re.DOTALL,
)
names = ('diff', 'lint', 'format', 'types', 'heads', 'unit', 'arch')
assert len(runs) == len(names), len(runs)
for name, (command, output, exit_code) in zip(names, runs):
    path = Path(f'tmp/pr3-03/s7-fix-{name}.txt')
    captured = path.read_text()
    assert captured.rstrip('\n') == output.rstrip('\n'), path
    assert exit_code == '0', (command, exit_code)
    print(f'{path}: content matches pasted output; recorded exit={exit_code}')
print('CAPTURE_AUDIT PASS (only trailing blank lines ignored)')
```

Exact command:

```sh
python3 tmp/pr3-03/s7-checklist-audit.py
```

Raw output:

```text
checklist_entries=38
mapped_nodes=383; unique_nodes=383
missing_count=0; duplicate_count=0; empty_entry_count=0
missing=[]; duplicates=[]; empty_entries=[]
reference-only: 1 node(s) under Reference-only
injection: 1 node(s) under Tool injection
self-weakening: 4 node(s) under Self-weakening
no-nested-UoW: 1 node(s) under No-nested-UoW
disabled-execution: 1 node(s) under Planning execution stays disabled
six permission pins: 6 node(s) under Exact six-key permission match
registry byte limit: 1 node(s) under Supplied canonical registry bytes
CHECKLIST_AUDIT PASS (inventory membership; passing execution is evidenced by pytest)
tmp/pr3-03/s7-fix-diff.txt: content matches pasted output; recorded exit=0
tmp/pr3-03/s7-fix-lint.txt: content matches pasted output; recorded exit=0
tmp/pr3-03/s7-fix-format.txt: content matches pasted output; recorded exit=0
tmp/pr3-03/s7-fix-types.txt: content matches pasted output; recorded exit=0
tmp/pr3-03/s7-fix-heads.txt: content matches pasted output; recorded exit=0
tmp/pr3-03/s7-fix-unit.txt: content matches pasted output; recorded exit=0
tmp/pr3-03/s7-fix-arch.txt: content matches pasted output; recorded exit=0
CAPTURE_AUDIT PASS (only trailing blank lines ignored)
```

Exit code: 0. Observed: 38 entries, 383 mapped nodes, 383 unique nodes,
0 missing, 0 duplicate and 0 empty entries. Each required behavioral mapping is
checked explicitly above.

An initial capture-audit attempt exited 1 on the system Python's unsupported
`zip(..., strict=True)` argument:

```text
TypeError: zip() takes no keyword arguments
```

The final source above removes that optional argument; its rerun exited 0.
The initial full output is retained in
`tmp/pr3-03/s7-checklist-audit-initial.txt` and is not PASS.

### S7 combined capture withdrawn

The historical combined check is withdrawn as per-command acceptance evidence:
individual exit codes were not captured. The seven separate S7 executions above
remain historical evidence; S8 records new independent executions below.

### S7 handoff and changed paths

PostgreSQL-dependent claims remain **unverified until S8**. S8 and the six-shard
full suite are not started; no overall PR or PostgreSQL gate is declared.

Changed paths for this evidence-quality correction:

- `docs/phase3/PR3-03-evidence.md`
- `tests/architecture/test_pr3_03_boundaries.py`
- `tests/unit/phase3/test_capability_gateway_contracts.py`

## S8 — review fixes at 9246daf

This run changes tests and evidence only; production behavior is unchanged.
PostgreSQL-dependent claims in S1–S7 are historical, **not run** in this review unless explicitly covered by the current command transcripts below. Historical transcripts retain their original results and are not current PASS claims.

### Step 0a–c — evidence provenance

**0a:** Historical combined command-chain captures were withdrawn from S1/S7,
and the previous S8 transcripts are replaced here by one current transcript per
required command. Each command runs separately, has its own raw stdout/stderr
and exit code, and appears once in the verification matrix. The reviewer's
additional combined check is not used as evidence for those individual commands
and its aggregate output is not pasted into this document.

**0b:** `tmp/pr3-03/` is ignored by git and local-only. The original S7
capture-audit and inventory-file membership claims depend on those local files.
Current S8 console captures, JUnit files, development logs and runner scripts
are also local-only. The complete before-fix command context, raw reviewer
combined transcript, and recomputation of JUnit membership depend on those local
captures (or rerunning the documented commands). Failing node IDs/diagnostics,
current raw per-command output, observations and passing node IDs are pasted below;
the reported focused results remain readable in a fresh checkout. `git check-ignore tmp/pr3-03/probe.txt`
exited 0 and printed `tmp/pr3-03/probe.txt`.

**0c:** The history command was rerun (exit 0):

```sh
git log --format='%h %s' -- docs/phase3/PR3-03-evidence.md
```

```text
9246daf PR3-03 sub-task S8 — PostgreSQL behaviour, races, replay and acceptance evidence
5ba2844 PR3-03 sub-task S7 — complete unit and architecture boundary evidence (test-only)
57f47a0 PR3-03 sub-task S6 — snapshot queries and CapabilityGateway.invoke (finite fake, no real adapter)
653cea2 PR3-03 sub-task S5 — start, finish, reconciliation and durable replay (no dispatch)
cdf2160 PR3-03 sub-task S4 — register/request commands and reserve_in_uow (no start, finish or dispatch)
1c44def PR3-03 sub-task S3 — closed domain/Application values, hashes and routing predicates (no commands)
bd89082 PR3-03 sub-task S2 — repository ports, composed locks and stored-row reads (no command behaviour)
52d984a Record PR3-03 S1 evidence (documentation only)
ae50409 S1 retry with owner-approved amendment A1 (syntax-only parenthesisation)
```

Inspection of each revision's evidence via `git show <revision>:docs/phase3/PR3-03-evidence.md`
found no original S5 requirement table in `653cea2` or its ancestors. S6's
`57f47a0` adds a labeled reconstruction, which remains in S7. Thus the original
S5 table cannot be recovered from history; the reconstruction is not presented
as a recovered historical table. No claim is made that S6/S7 lack that table. This review reran the history command (exit 0) and inspected the six S1–S5 evidence revisions: all have zero `| S5 requirement` headers; S6 `57f47a0` has one.

### Deviations and reviewer dispositions

**S8-D1 (S5 production correction):** The previous exact-cap PostgreSQL case
`tests/integration/phase3/test_pr3_03_application.py::test_exact_cap_own_stop_start_and_later_stops[own-gateway0]`
failed with `ResearchBaseError: task stopped` at original S5 line 1056. The
failing invocation appears in `tmp/pr3-03/development-caps.txt` (exit 1).
Pack §6.1 allows disregarding only the first stop_budget attributable to that
request's own receipt. S5 read `repo.events` and `repo.receipt_history`, whose
projections omit the needed result pointers (`research_task_repository.py:50–55`
and `task_safety_repository.py:157–163`). The correction uses already existing
`gateway_task_events` and `gateway_receipt`, and retains explicit saved receipt
ID equality. No repository capability was added: the two methods are present
in base S2 `bd89082` in `persistence/capability_gateway_repository.py` and its
port, and remain unchanged in this diff. The recording fixture now exposes the
existing gateway port. The new unit node
`test_exact_cap_start_reads_complete_gateway_provenance` rejects fallback to
the generic receipt projection. Final execution disposition is recorded below.

The S2 source-history checks were rerun, separately (exit 0 each):

```sh
git show bd89082:src/researchbase/persistence/capability_gateway_repository.py | rg -n 'def gateway_receipt|def gateway_task_events'
```

```text
155:    def gateway_receipt(
161:    def gateway_task_events(self, task: UUID) -> list[StoredTaskEvent]:
```

Exit code: `0`.

```sh
git show bd89082:src/researchbase/agent_runtime/ports/gateway_repository.py | rg -n 'def gateway_receipt|def gateway_task_events'
```

```text
184:    def gateway_receipt(
187:    def gateway_task_events(self, task: UUID) -> list[StoredTaskEvent]: ...
```

Exit code: `0`.

**S8-D2 (historical test correction):** The first compatibility run found
`test_pr3_04_migration.py::test_forward_upgrade_and_refusal[True]` failing before
its 0077→0078 upgrade: `psycopg.errors.UndefinedColumn: column "stop_human" does
not exist` (1 failed, 318 passed). In that test only, the historical read now
projects the six false flags introduced by 0078. The post-upgrade reader stays
unpatched, exact graph equality is retained, and all-table/all-old-column raw
row equality remains. No migration or stored row changed. This extra test file
is explicitly outside S8's new-file list. Its own two cases and compatibility
rerun are included in final validation.

**S8-D3 (S4 write-order correction):** The new PostgreSQL callback-order case
`test_entitlement_and_saved_replay_after_each_blocking_stage[request-share]`
failed before the correction: `At index 15 diff: 'event_insert' != 'refs_insert'`
(exit 1, `tmp/pr3-03/review-waits-replay.txt`). Pack §5 prescribes
“reservation then invocation+inputs … → capability event”. S4 `_once` inserted
the REQUESTED event at original lines 861–884, then input refs at 885–901.
The smallest correction moves that existing input-ref loop before the existing
event insert; IDs, hashes, transactions and fields are unchanged. A new unit
node `test_request_refs_precede_request_event_in_frozen_write_recipe` and all
request callback-order cases enforce the recipe. No new architecture exception,
repository method, migration or dependency is introduced.


### Review-fix scope and measurement

Commit and fake-call measurements wrap `SqlAlchemyUnitOfWork.commit` and the real
`routing.finite_fake_echo` dispatch point, after fixture setup. Assertions enforce
four commits/zero calls for the command slice and three commits/one call plus zero
additional replay commits for invoke. Scientific and legacy replay row changes
are computed from database snapshots. Unsupported literal duplicate-effect/refund
counts were removed; existing exact row/accounting assertions remain.
All S8 test files were searched for `gateway_commits=`, `fake_calls=`,
`scientific_writes=` and `>= 0`; the only nonnegative tautology was replaced by
exact final token cost zero, matching `fake_measurement` for all final outcomes.

The finding's `harness_hash` case actually lives in
`test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[harness_hash]`.
The probe observed `PROVENANCE_CLOSURE_VIOLATION`; the assertion now permits only
that code. There is no harness-hash case in `test_pr3_03_replay.py`.
The capacity race already asserts one code per scenario at baseline 9246daf:
`test_last_capacity_race_no_over_admission[last-budget-unit]` expects
`INVALID_STATE_TRANSITION`, `[last-tool-call]` and `[last-parallel-slot]` each
expect `FORBIDDEN`. All three matched those expectations in the probe; no
multi-code set remains in these cases and no production behavior was changed.

**Deviation verification (existing S8-D1 / S8-D3):** Inspected the S7-to-9246daf
production diff and the retained local failure captures. The ref-before-event
failure is the full node
`tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-share]`:
`At index 15 diff: 'event_insert' != 'refs_insert'`.
The complete-provenance read failure is
`tests/integration/phase3/test_pr3_03_application.py::test_exact_cap_own_stop_start_and_later_stops[own-gateway0]`:
`ResearchBaseError: task stopped`. The latter reads occur in own-stop start
admission (`_start_admission`), rather than the reconciliation command itself.
The smallest-change reasons and originating step ownership remain recorded in
S8-D1/S8-D3 above. These are inherited production deviations, not new edits in
this task. The current Phase 3 unit command passed **955 tests**, including the
S4/S5/S6/S7 unit files `test_capability_gateway.py`,
`test_capability_gateway_repository.py`, `test_capability_gateway_contracts.py`,
`test_capability_routing.py`, and `test_agent_tool_policy.py`, as well as the
budget/safety unit files in that directory. Both added regression nodes
`test_request_refs_precede_request_event_in_frozen_write_recipe` and
`test_exact_cap_start_reads_complete_gateway_provenance` passed in that run.

### Current verification — separate commands (2026-10-22 local)

Every uv command below inherited `UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`,
set before invocation. Each command was executed separately; outputs are raw
combined stdout/stderr (last 40 lines for pytest), with its actual exit code.
Ignored captures and JUnit files remain local-only. No full suite, six-shard
suite or S9 was run. PostgreSQL-dependent claims below are **passed in this run**
only for the quoted schema, behavior and compatibility commands. Historical
standalone metadata/probe commands and per-file captures are **not run** here.

#### 01-diff

`git diff --check HEAD`

Exit code: `0`.

```text

```

#### 02-lint

`uv run ruff check .`

Exit code: `0`.

```text
All checks passed!
```

#### 03-format

`uv run ruff format --check .`

Exit code: `0`.

```text
912 files already formatted
```

#### 04-types

`uv run pyright`

Exit code: `0`.

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### 05-heads

`uv run alembic heads`

Exit code: `0`.

```text
0080_capability_gateway (head)
```

#### 06-unit

`RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/unit/phase3`

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 955 items

tests/unit/phase3/test_agent_identity_contracts.py .                     [  0%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [  3%]
........................................                                 [  7%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [  9%]
........................................................................ [ 17%]
....                                                                     [ 17%]
tests/unit/phase3/test_agent_version_transports.py ..................    [ 19%]
tests/unit/phase3/test_capability_gateway.py ........................... [ 22%]
........................................................................ [ 29%]
........................................................................ [ 37%]
...................................................................      [ 44%]
tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 46%]
........................................................                 [ 51%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 53%]
.................................................                        [ 58%]
tests/unit/phase3/test_capability_routing.py ........................... [ 61%]
........................................................                 [ 67%]
tests/unit/phase3/test_harness_manifest.py ...............               [ 69%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 71%]
....................................................                     [ 76%]
tests/unit/phase3/test_research_task_graph.py .......................... [ 79%]
........................................................................ [ 87%]
.                                                                        [ 87%]
tests/unit/phase3/test_research_task_transports.py ....................  [ 89%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 90%]
tests/unit/phase3/test_task_checkpoints.py ................              [ 92%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 93%]
tests/unit/phase3/test_task_safety_policies.py ......................... [ 96%]
.......................                                                  [ 98%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================= 955 passed in 6.98s ==============================
```

#### 07-architecture

`RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`

Exit code: `0`.

```text
tests/architecture/test_m1_boundaries.py ...                             [ 32%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 36%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 39%]
tests/architecture/test_pr12_boundaries.py ....                          [ 40%]
tests/architecture/test_pr13_boundaries.py ..                            [ 41%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 42%]
tests/architecture/test_pr14_boundaries.py ..                            [ 42%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 43%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 44%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 46%]
tests/architecture/test_pr18_boundaries.py .......                       [ 48%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 49%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 50%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 54%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 60%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 61%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 68%]
................................                                         [ 77%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 78%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 79%]
tests/architecture/test_pr3_03_boundaries.py ..............              [ 83%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 83%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 366 passed, 50 warnings in 21.94s =======================
```

#### 08-schema

`RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra --junitxml=tmp/pr3-03/schema.xml tests/integration/phase3/test_pr3_03_schema.py tests/integration/phase3/test_pr3_03_guards.py tests/integration/phase3/test_pr3_03_migration.py`

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 79 items

tests/integration/phase3/test_pr3_03_schema.py ......................... [ 31%]
.....                                                                    [ 37%]
tests/integration/phase3/test_pr3_03_guards.py ......................... [ 69%]
.....................                                                    [ 96%]
tests/integration/phase3/test_pr3_03_migration.py ...                    [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_03_schema.py: 30 warnings
tests/integration/phase3/test_pr3_03_guards.py: 92 warnings
tests/integration/phase3/test_pr3_03_migration.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
- generated xml file: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/tmp/pr3-03/schema.xml -
================= 79 passed, 130 warnings in 170.44s (0:02:50) =================
```

#### 09-behavior

`RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra -s --junitxml=tmp/pr3-03/behavior.xml tests/integration/phase3/test_pr3_03_application.py tests/integration/phase3/test_pr3_03_concurrency.py tests/integration/phase3/test_pr3_03_replay.py`

Exit code: `0`.

```text
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.272004+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.318, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T01:08:02.272028+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.336, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a1664c-f65e-745b-bf43-04510b5bacd6", "timestamp": "2026-10-23T01:08:02.272042+00:00"}
INFO  [researchbase.commands] {"actor_id": "381d6e5d-0007-413f-9374-2f613943b75e", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.352, "error_code": null, "level": "INFO", "project_id": null, "request_id": "a3482a6c-3cf7-4f09-9a3c-4087d7268f29", "result": "success", "rollback": false, "target_id": "01a1664c-f65e-745b-bf43-04510b5bacd6", "timestamp": "2026-10-23T01:08:02.273410+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.273728+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.316, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T01:08:02.273752+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.331, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a1664c-f65e-745b-bf43-04510b5bacd6", "timestamp": "2026-10-23T01:08:02.273763+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.274953+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.276388+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.303957+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.306101+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.378090+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.381202+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.441064+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.469323+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.532203+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.559324+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.594311+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:02.622831+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:04.327443+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:04.408620+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T01:08:04.412009+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_64531f4d33c7437cb8b923cbaf0efc8f
DB_WAIT [{'pid': 58966, 'locktype': 'advisory', 'mode': 'ExclusiveLock', 'relation': None, 'waitstart': datetime.datetime(2026, 10, 22, 21, 8, 2, 516837, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'xact_start': datetime.datetime(2026, 10, 22, 21, 8, 2, 469515, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': '\nSELECT pg_advisory_xact_lock(hashtextextended($1,0))\n', 'observed_at': datetime.datetime(2026, 10, 22, 21, 8, 2, 531396, tzinfo=zoneinfo.ZoneInfo(key='America/New_York'))}]
DB_WAIT [{'pid': 58966, 'locktype': 'relation', 'mode': 'ShareLock', 'relation': 'actor_subject_bindings', 'waitstart': datetime.datetime(2026, 10, 22, 21, 8, 2, 623045, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'xact_start': datetime.datetime(2026, 10, 22, 21, 8, 2, 623006, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE', 'observed_at': datetime.datetime(2026, 10, 22, 21, 8, 2, 625354, tzinfo=zoneinfo.ZoneInfo(key='America/New_York'))}]
FRESH_CALLBACK finish constraints waiter_pid 58966 wait_started_at 2026-10-22 21:08:02.516837-04:00 acquired_at 2026-10-22 21:08:02.531726-04:00 authorization_before_disclosure=True current_xmin_replay=False saved_replay_before_CAS_state_expiry_availability=True replay_waiter_pid 58966
.DISPOSABLE_DROPPED: researchbase_pr212_test_64531f4d33c7437cb8b923cbaf0efc8f


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_03_application.py: 126 warnings
tests/integration/phase3/test_pr3_03_concurrency.py: 46 warnings
tests/integration/phase3/test_pr3_03_replay.py: 146 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
- generated xml file: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/tmp/pr3-03/behavior.xml -
================ 159 passed, 318 warnings in 309.71s (0:05:09) =================
```

#### 10-compatibility

`RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_04_*.py tests/integration/phase3/test_pr3_02_s1_*.py`

Exit code: `0`.

```text
tests/integration/phase3/test_pr3_01_concurrency.py ................     [  7%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [  8%]
tests/integration/phase3/test_pr3_01_replay.py ...............           [ 12%]
tests/integration/phase3/test_pr3_01_schema.py ......................... [ 20%]
........................................................................ [ 43%]
..................................                                       [ 53%]
tests/integration/phase3/test_pr3_04_accounting.py ...........           [ 57%]
tests/integration/phase3/test_pr3_04_application.py .................... [ 63%]
..                                                                       [ 64%]
tests/integration/phase3/test_pr3_04_concurrency.py .......              [ 66%]
tests/integration/phase3/test_pr3_04_fake_consumer.py ..                 [ 67%]
tests/integration/phase3/test_pr3_04_guards.py ..................        [ 72%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 73%]
tests/integration/phase3/test_pr3_04_queries.py ..                       [ 73%]
tests/integration/phase3/test_pr3_04_replay.py ....                      [ 75%]
tests/integration/phase3/test_pr3_04_schema.py ....                      [ 76%]
tests/integration/phase3/test_pr3_02_s1_application.py ..............    [ 80%]
tests/integration/phase3/test_pr3_02_s1_b02_agent.py .                   [ 81%]
tests/integration/phase3/test_pr3_02_s1_concurrency.py .......           [ 83%]
tests/integration/phase3/test_pr3_02_s1_identity.py ...................  [ 89%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [ 90%]
tests/integration/phase3/test_pr3_02_s1_replay.py ..........             [ 93%]
tests/integration/phase3/test_pr3_02_s1_schema.py .....................  [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_01_application.py: 2 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_b02_agent.py: 1 warning
tests/integration/phase3/test_pr3_02_s1_concurrency.py: 7 warnings
tests/integration/phase3/test_pr3_02_s1_identity.py: 19 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
tests/integration/phase3/test_pr3_02_s1_schema.py: 21 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 319 passed, 102 warnings in 85.96s (0:01:25) =================
```

#### Pre-fix deterministic-code probe

Passed in this run: `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects tests/integration/phase3/test_pr3_03_concurrency.py::test_last_capacity_race_no_over_admission`

Exit code: `0`. Raw final summary:

```text
CAPACITY_RACE 5 6 FORBIDDEN policy denies or task-wide cap reached
.DISPOSABLE_DROPPED: researchbase_pr212_test_611907acb3254adbab6a28b8ce5644b2


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_03_application.py: 20 warnings
tests/integration/phase3/test_pr3_03_concurrency.py: 6 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 13 passed, 26 warnings in 14.99s =======================
```

### Measured observations from the current behavior command

- `09-behavior` (passed in this run): `RUNTIME_ROLE pr302_01a1664848737e00bad5c28dc221cac0 encoding UTF8 version 18.6 (Homebrew)`
- `09-behavior` (passed in this run): `normal-role effects {'agent_tool_policies': 1, 'agent_tool_policy_permissions': 1, 'capability_invocations': 1, 'capability_invocation_refs': 1, 'capability_invocation_events': 3, 'budget_reservations': 1, 'budget_usage_records': 1} scientific_writes=0 {'gateway_commits': 4, 'fake_calls': 0}`
- `09-behavior` (passed in this run): `invoke {'gateway_commits': 3, 'fake_calls': 1} replay_commits=0`
- `09-behavior` (passed in this run): `uncertain-commit request {'gateway_commits': 1, 'fake_calls': 0}`
- `09-behavior` (passed in this run): `uncertain-commit start {'gateway_commits': 1, 'fake_calls': 0}`
- `09-behavior` (passed in this run): `uncertain-commit finish {'gateway_commits': 1, 'fake_calls': 0}`
- `09-behavior` (passed in this run): `UNKNOWN_REPLAY fake_calls=1`
- `09-behavior` (passed in this run): `CAPACITY_RACE 5 6 INVALID_STATE_TRANSITION task stopped`
- `09-behavior` (passed in this run): `CAPACITY_RACE 8 9 FORBIDDEN policy denies or task-wide cap reached`
- `09-behavior` (passed in this run): `CAPACITY_RACE 5 6 FORBIDDEN policy denies or task-wide cap reached`

### Closure of the 17 former open S8 items — current passing node IDs

Each listed node passed in this run; the evidence capture names refer to the exact PostgreSQL commands quoted above. All parameter instances are listed.

1. **PASS**, `08-schema`: `test_receipt_and_task_event_full_check_and_fk_catalog`

   - `tests/integration/phase3/test_pr3_03_schema.py::test_receipt_and_task_event_full_check_and_fk_catalog`

2. **PASS**, `08-schema`: `test_all_composite_local_scope_mismatch_writes`

   - `tests/integration/phase3/test_pr3_03_schema.py::test_all_composite_local_scope_mismatch_writes`

3. **PASS**, `08-schema`: `test_output_ref_lifecycle_scope_freeze_and_hash_errors`

   - `tests/integration/phase3/test_pr3_03_schema.py::test_output_ref_lifecycle_scope_freeze_and_hash_errors`

4. **PASS**, `08-schema`: `test_all_invalid_invocation_and_reconciliation_edges`

   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_invalid_invocation_and_reconciliation_edges[CANCELLED]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_invalid_invocation_and_reconciliation_edges[FAILED]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_invalid_invocation_and_reconciliation_edges[REQUESTED]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_invalid_invocation_and_reconciliation_edges[RUNNING]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_invalid_invocation_and_reconciliation_edges[SUCCEEDED]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_invalid_invocation_and_reconciliation_edges[UNKNOWN_OUTCOME]`

5. **PASS**, `08-schema`: `test_all_immediate_guards_across_independent_flushes`

   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_immediate_guards_across_independent_flushes[agent_tool_policies]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_immediate_guards_across_independent_flushes[agent_tool_policy_permissions]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_immediate_guards_across_independent_flushes[capability_invocation_events]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_immediate_guards_across_independent_flushes[capability_invocation_refs]`
   - `tests/integration/phase3/test_pr3_03_guards.py::test_all_immediate_guards_across_independent_flushes[capability_invocations]`

6. **PASS**, `08-schema`: `test_all_original_planning_safety_s1_saved_results_after_upgrade`

   - `tests/integration/phase3/test_pr3_03_migration.py::test_all_original_planning_safety_s1_saved_results_after_upgrade`

7. **PASS**, `09-behavior`: `test_each_gate_cap_version_and_manifest_denial_without_effects`

   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[availability]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[checkpoint]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[harness_hash]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[manifest_skill]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[manifest_strategy]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[missing_version]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[parameters_hash]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[policy_hash]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[policy_version]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_each_gate_cap_version_and_manifest_denial_without_effects[registry_bytes]`

8. **PASS**, `09-behavior`: `test_reconciliation_all_final_outcomes_preserves_unknown_and_no_refund`

   - `tests/integration/phase3/test_pr3_03_application.py::test_reconciliation_all_final_outcomes_preserves_unknown_and_no_refund[CANCELLED]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_reconciliation_all_final_outcomes_preserves_unknown_and_no_refund[FAILED]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_reconciliation_all_final_outcomes_preserves_unknown_and_no_refund[SUCCEEDED]`

9. **PASS**, `09-behavior`: `test_finish_output_and_invocation_update_rollback`

   - `tests/integration/phase3/test_pr3_03_application.py::test_finish_output_and_invocation_update_rollback[commit]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_finish_output_and_invocation_update_rollback[constraints]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_finish_output_and_invocation_update_rollback[invocation_update]`
   - `tests/integration/phase3/test_pr3_03_application.py::test_finish_output_and_invocation_update_rollback[output_ref]`

10. **PASS**, `09-behavior`: `test_each_row_wait_and_complete_db_lock_order`

   - `tests/integration/phase3/test_pr3_03_concurrency.py::test_each_row_wait_and_complete_db_lock_order`

11. **PASS**, `09-behavior`: `test_stop_change_during_observed_wait`

   - `tests/integration/phase3/test_pr3_03_concurrency.py::test_stop_change_during_observed_wait`

12. **PASS**, `09-behavior`: `test_checkpoint_change_during_observed_wait`

   - `tests/integration/phase3/test_pr3_03_concurrency.py::test_checkpoint_change_during_observed_wait`

13. **PASS**, `09-behavior`: `test_exact_cap_start_with_prior_and_additional_stops`

   - `tests/integration/phase3/test_pr3_03_concurrency.py::test_exact_cap_start_with_prior_and_additional_stops[additional-gateway0]`
   - `tests/integration/phase3/test_pr3_03_concurrency.py::test_exact_cap_start_with_prior_and_additional_stops[prior-gateway0]`

14. **PASS**, `09-behavior`: `test_entitlement_and_saved_replay_after_each_blocking_stage`

   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-actor]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-availability_row]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-checkpoint_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-command]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-constraints]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-event_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-invocation_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-invocation_update]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-link_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-project]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-receipt_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-refs_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-share]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-step_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-task]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-task_event_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-task_row]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-task_update]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-usage_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[finish-version]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-actor]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-availability_row]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-checkpoint_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-command]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-constraints]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-event_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-invocation_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-invocation_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-link_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-project]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-receipt_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-refs_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-reservation_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-share]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-step_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-task]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-task_event_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-task_row]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-task_update]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[request-version]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-actor]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-availability_row]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-checkpoint_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-command]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-constraints]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-event_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-invocation_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-invocation_update]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-link_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-project]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-receipt_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-share]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-step_rows]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-task]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-task_event_insert]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-task_row]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-task_update]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_entitlement_and_saved_replay_after_each_blocking_stage[start-version]`

15. **PASS**, `09-behavior`: `test_invoke_lost_responses_each_commit_never_duplicates_fake`

   - `tests/integration/phase3/test_pr3_03_replay.py::test_invoke_lost_responses_each_commit_never_duplicates_fake[1]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_invoke_lost_responses_each_commit_never_duplicates_fake[2]`
   - `tests/integration/phase3/test_pr3_03_replay.py::test_invoke_lost_responses_each_commit_never_duplicates_fake[3]`

16. **PASS**, `09-behavior`: `test_unknown_replay_never_refunds_or_redispatches`

   - `tests/integration/phase3/test_pr3_03_replay.py::test_unknown_replay_never_refunds_or_redispatches`

17. **PASS**, `09-behavior`: `test_list_snapshot_coherence_under_writer`

   - `tests/integration/phase3/test_pr3_03_replay.py::test_list_snapshot_coherence_under_writer`

### Retained contract coverage map

PostgreSQL-dependent rows in this map passed in this run under `08-schema` or
`09-behavior` above; unit rows passed under `06-unit`. This retains the frozen
vector IDs, requirement mapping and guard expectations from S8 without repeating
historical console dumps.

### Six frozen vector IDs and parity

| Pack vector ID | Exact expected/observed digest | Passing node |
| --- | --- | --- |
| schema_vector | `79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f` | `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[schema]`; `tests/integration/phase3/test_pr3_03_schema.py::test_six_sql_python_vectors[schema_vector]` |
| empty_capability_set | `2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1` | `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[empty-set]`; `tests/integration/phase3/test_pr3_03_schema.py::test_six_sql_python_vectors[empty_capability_set]` |
| fake_capability_set | `2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9` | `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[fake-set]`; `tests/integration/phase3/test_pr3_03_schema.py::test_six_sql_python_vectors[fake_capability_set]` |
| empty_policy | `dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c` | `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[empty-policy]`; `tests/integration/phase3/test_pr3_03_schema.py::test_six_sql_python_vectors[empty_policy]` |
| allow_and_deny_policy | `725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b` | `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[allow-deny-policy]`; `tests/integration/phase3/test_pr3_03_schema.py::test_six_sql_python_vectors[allow_and_deny_policy]` |
| parameters_vector | `a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3` | `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors[cafe-parameters]`; `tests/integration/phase3/test_pr3_03_schema.py::test_six_sql_python_vectors[parameters_vector]` |

The two policy vectors and their derived capability-set hashes additionally pass
PostgreSQL exact-text and SQL SHA-256 assertions in all four original/reordered
`test_fixed_policy_vectors_from_typed_rows` nodes. These literal fixed identities
use session-local typed serializer inputs with the real column types; canonical
persisted policy parity is separately checked through owning commands in
`test_typed_row_reconstruction_matches_saved_policy`. No
privileged insertion of canonical vector owners is used.

### Pack §9.1 requirement map

The full literal PostgreSQL node inventory follows this map. Each item under a
file is executed by the required grouped run and its independent per-file run;
those JUnit node unions are identical with no duplication. Parameterized nodes
are expanded literally there. Unit/architecture function selections below are
covered by the complete passing directory runs; no collect-only result is used
as execution evidence. Historical S7 evidence retains the original unit matrix.

| Required suite | Requirement coverage and passing selections |
| --- | --- |
| schema | Complete §2/§3 catalog/eleven target keys; all six frozen ref families; XOR/duplicate/local scope/old hash/draft failures; both typed policy/capability-set vectors with exact SQL reconstruction; reverse insertion/non-ASCII/fixed resource/fractional-number parity; permissions/refs/parameter/summary limits, byte size and no CASCADE/semantic JSON. All schema nodes below. |
| guards | All nine immediate triggers mapped below; immutable no-op/update/delete and current-xmin/committed-receipt child append; missing/extra effects, wrong reservation/usage/nullable step, independent flush tampering; six initial invocation states cover all 30 invalid status edges plus invalid reconciliation sources/fields/second final. Maximum sets measure one task-final, receipt-completeness and gateway helper. All guard nodes below. |
| migration | Clean base→0080, populated 0079→0080, every old table/column/scientific hash/trace/graph preserved, only nullable old-table additions, no UPDATE/backfill/dummy execution; all six planning/six safety/three S1 command results replay after upgrade; unchanged old trigger OIDs/attachments; both downgrade refusals before catalog/rows/revision change, CHECK replacements and sole head. All migration nodes below plus schema catalog nodes. |
| application | Human/eligible Agent same boundary, Human Owner registration, trusted consumer identity, every command rollback stage, exact effects/no scientific rows, all gate/cap/pin/manifest denials; cancel before start, all finite outcomes, unknown and final reconciliation, post-stop finite bookkeeping. All application nodes below. |
| concurrency | First SHARE, ordered advisory and all five row-lock stages observed by backend/expected blocker/query; two tasks sharing version vs availability writer; last budget/call/slot loser reaches capacity under contention; real waits across expiry, revocation, stop and checkpoint; exact-cap own-stop/prior/later/additional-stop distinctions; finite finish after stop; three fresh transactions for 40001/40P01, one for timeout. All concurrency nodes below. |
| replay | Each request/start/finish blocking callback rechecks entitlement then committed replay before diagnostics; lost responses/uncertain commits at each invoke transaction; saved IDs/material conflicts, no duplicate call/ledger/event, no unknown refund/redispatch; three query surfaces use a single read-only repeatable-read snapshot without writes/locks/second connection, coherent get/list under concurrent writer. All replay nodes below. |

The unit and architecture selections complete the other five §9.1 rows:

**`tests/unit/phase3/test_capability_gateway_contracts.py`:**

- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_frozen_literal_vectors`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_four_command_roundtrips_and_actor_material`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_request_fields`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_nested_extras_and_missing_fields`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_exact_six_place_resources`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_resources_material_is_fixed_six_place_and_nulls_expand`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_public_finish_and_trusted_context_cannot_be_deserialized`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_retained_parameters_have_separate_owning_hash`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_refs_sort_duplicate_and_combined_bound`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_summary_utf8_byte_bound`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_lifecycle_edges`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_invalid_lifecycle`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_reconciliation_and_retry`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_complete_stored_read_vocabulary`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_capability_request_command_ids_must_be_distinct`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_closed_read_and_result_roundtrips`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_read_nested_extras_and_projection_literals`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_trusted_context_has_no_material_or_public_decoder`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_cursor_requires_aware_timestamp`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_parameters_message_limits_and_scale`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_parameter_byte_ceiling_does_not_bypass_closed_schema`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_largest_escaped_parameters_and_nfc_summary_boundaries`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_six_reference_families_closed_roundtrip`
- [x] `tests/unit/phase3/test_capability_gateway_contracts.py::test_command_reference_order_and_uuid_normalization`

**`tests/unit/phase3/test_agent_tool_policy.py`:**

- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_exact_effects`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_task_wide_counts_survive_policy_changes`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_invalid_policy`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_aliases_patterns_and_whitespace_deny`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_permission_normalization_and_projection`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_each_permission_pin_is_required_without_fallback`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_caps_cross_product_across_policy_switch`
- [x] `tests/unit/phase3/test_agent_tool_policy.py::test_policy_set_order_defaults_and_duplicates`

**`tests/unit/phase3/test_capability_routing.py`:**

- [x] `tests/unit/phase3/test_capability_routing.py::test_exact_route_and_supplied_byte_loader`
- [x] `tests/unit/phase3/test_capability_routing.py::test_routing_exclusions`
- [x] `tests/unit/phase3/test_capability_routing.py::test_pins_phase_and_reference_only`
- [x] `tests/unit/phase3/test_capability_routing.py::test_closed_registry_negative`
- [x] `tests/unit/phase3/test_capability_routing.py::test_malformed_noncanonical_and_nonfinite_bytes`
- [x] `tests/unit/phase3/test_capability_routing.py::test_registry_byte_limit_and_non_executable_tuple`
- [x] `tests/unit/phase3/test_capability_routing.py::test_loader_does_no_discovery_or_io`
- [x] `tests/unit/phase3/test_capability_routing.py::test_finite_fake_echo_closed_exact_outcomes`
- [x] `tests/unit/phase3/test_capability_routing.py::test_finite_fake_rejects_arbitrary_objects`
- [x] `tests/unit/phase3/test_capability_routing.py::test_reviewed_intake_and_all_retained_pins_required`
- [x] `tests/unit/phase3/test_capability_routing.py::test_unreviewed_registry_metadata_cannot_grant_execution`
- [x] `tests/unit/phase3/test_capability_routing.py::test_injected_message_never_overrides_self_weakening_exclusion`
- [x] `tests/unit/phase3/test_capability_routing.py::test_router_applies_changed_policy_caps_to_existing_task_counts`

**`tests/unit/phase3/test_capability_gateway.py`:**

- [x] `tests/unit/phase3/test_capability_gateway.py::test_registration_one_transaction_no_reservation_and_complete_policy`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_request_atomic_effects_exact_vector_refs_and_no_nested_safety`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_registration_requires_current_human_owner`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_identity_trust_and_context_binding`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_exact_final_unit_sets_sticky_stop_and_denies_next_request`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_policy_switch_retains_task_wide_call_count`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_request_rollback_at_every_write_stage`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_registration_rollback`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_saved_replay_precedes_stale_cas_role_availability_and_preflight_failure`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_after_every_wait_authentication_and_receipt_precede_diagnostics`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_after_write_wait_revocation_rolls_back`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_stable_ids_across_fresh_whole_transaction_retry`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_request_denials_have_zero_effects`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_constraint_wait_advancing_time_does_not_use_provenance_timestamp`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_three_attempt_limit_and_timeout_never_retries`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_uncertain_commit_reconciles_original_saved_receipt`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_entitled_agent_request_uses_same_application_command`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_reused_command_uuid_from_another_actor_cannot_hide_a_prior_stop`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_public_self_supplied_observation_is_forbidden`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_start_zero_new_accounting_and_prestart_cancel_retains_counts`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_running_outcomes_and_finish_after_cancel_stop_and_disabled_agent`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_reconciliation_append_only_and_saved_event_results`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_lifecycle_edge_matrix`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_exact_cap_start_only_own_first_attributable_stop`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_lifecycle_cas_and_saved_receipt_precedes_stale_revisions`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_output_refs_success_and_reconciliation_preserves_observation`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_reconciliation_rejects_changed_observation`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_retry_parent_requires_failure_or_final_reconciled_unknown`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_finish_rolls_back_every_write_stage`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_finish_uncertain_commit_uses_formal_receipt_lookup`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_saved_lifecycle_receipt_after_each_wait_precedes_cas_and_availability`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_fresh_lifecycle_checks_after_dml_wait_roll_back`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_lifecycle_retry_ids_stable_and_single_settlement`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_output_refs_rejected_for_every_non_success`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_unknown_reservation_still_occupies_slot_and_full_budget`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_finish_exact_charge_ownership_is_required`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_unknown_does_not_advance_final_failure_streak_until_reconciliation`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_unknown_invocation_requires_authorization_before_disclosure`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_finish_authority_split`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_three_commits_one_outside_call_and_saved_terminal_replay`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_response_loss_at_each_commit`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_saved_finish_missing_usage_reports_provenance_violation`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_arbitrary_capability_is_denied_before_disclosure`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_unresolved_start_without_saved_finish_never_calls_fake`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_unresolved_commit_with_no_visible_receipt_never_dispatches`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_snapshot_queries_exact_policy_invocation_and_no_io`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_snapshot_query_authorization_precedes_missing_objects`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_snapshot_paging_empty_ties_boundaries_and_no_offset`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_query_limit_rejects_outside_closed_bounds`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_query_refs_use_owning_snapshot_warnings_and_canonical_order`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_rejects_arbitrary_request_without_dispatch`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_replay_rechecks_current_entitlement`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_saved_unknown_finish_survives_final_reconciliation`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_query_denied_scope_never_looks_up_existence`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_invoke_common_boundary_has_no_nested_safety_or_scientific_effects`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_equal_but_distinct_finish_observation_is_untrusted`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_injected_tool_text_is_inert_and_replay_never_dispatches`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_exact_cap_start_reads_complete_gateway_provenance`
- [x] `tests/unit/phase3/test_capability_gateway.py::test_request_refs_precede_request_event_in_frozen_write_recipe`

**`tests/architecture/test_pr3_03_boundaries.py`:**

- [x] `tests/architecture/test_pr3_03_boundaries.py::test_runtime_import_dependencies_exclude_persistence_transport_sdk_and_effects`
- [x] `tests/architecture/test_pr3_03_boundaries.py::test_boundary_scanner_detects_deliberate_violation`
- [x] `tests/architecture/test_pr3_03_boundaries.py::test_domain_scanner_rejects_application_and_ports`
- [x] `tests/architecture/test_pr3_03_boundaries.py::test_gateway_tables_use_concrete_refs_and_own_no_scientific_json_state`
- [x] `tests/architecture/test_pr3_03_boundaries.py::test_public_port_and_values_do_not_admit_credentials_execution_or_promotion`
- [x] `tests/architecture/test_pr3_03_boundaries.py::test_runtime_dependencies_remain_the_accepted_set`

The unchanged original vectors also execute in the 955-case unit run:

- [x] `tests/unit/phase3/test_research_task_contracts.py::test_fixed_vectors`
- [x] `tests/unit/phase3/test_task_safety_contracts.py::test_fixed_hash_vectors`
- [x] `tests/unit/phase3/test_agent_version_contracts.py::test_literal_vectors`

### Immediate guards, retained attachments and invalid edges

All nine new trigger attachments are asserted as an exact name/table/function
inventory, row-level and nondeferrable, in every
`test_all_immediate_guards_across_independent_flushes` case. Each table case
performs a valid insertion in the real command, flushes, then attempts a second
invalid INSERT, no-op UPDATE and DELETE; each denial must have SQLSTATE 23514
and the entire transaction's rows must equal the prior snapshot.

| Trigger | Passing node (under `tests/integration/phase3/test_pr3_03_guards.py::`) |
| --- | --- |
| `pr303_policy_insert` | `test_all_immediate_guards_across_independent_flushes[agent_tool_policies]` |
| `pr303_policy_immutable` | `test_all_immediate_guards_across_independent_flushes[agent_tool_policies]` |
| `pr303_permission_insert` | `test_all_immediate_guards_across_independent_flushes[agent_tool_policy_permissions]` |
| `pr303_permission_immutable` | `test_all_immediate_guards_across_independent_flushes[agent_tool_policy_permissions]` |
| `pr303_invocation_write` | `test_all_immediate_guards_across_independent_flushes[capability_invocations]` |
| `pr303_ref_insert` | `test_all_immediate_guards_across_independent_flushes[capability_invocation_refs]` |
| `pr303_ref_immutable` | `test_all_immediate_guards_across_independent_flushes[capability_invocation_refs]` |
| `pr303_event_insert` | `test_all_immediate_guards_across_independent_flushes[capability_invocation_events]` |
| `pr303_event_immutable` | `test_all_immediate_guards_across_independent_flushes[capability_invocation_events]` |

`test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade`
compares every pre-upgrade trigger OID, relation, function attachment, trigger
kind and deferral flags against 0080. No old attachment is replaced or dropped.
`test_all_invalid_invocation_and_reconciliation_edges[REQUESTED]`, `[RUNNING]`,
`[SUCCEEDED]`, `[FAILED]`, `[UNKNOWN_OUTCOME]` and `[CANCELLED]` exercise every
invalid status edge (including terminal mutation), start/reconcile wrong sources,
and malformed reconciliation sequence/revision/prior/new/outcome/missing or
wrong usage. The UNKNOWN case also rejects a second final reconciliation.
`test_legacy_receipt_event_and_settlement_immutable_after_gateway_finish`
additionally attempts no-op UPDATE, real UPDATE and DELETE against the old
receipt, task-event and settlement tables after a complete gateway lifecycle at
0080. All nine mutations must fail with pr301_immutable and preserve all rows.
`test_maximum_sets_exactly_once_deferred_guards[maximum]` measures the three
required counters. The current schema run passed these nodes.

### Handoff boundary

Independent review and the external six-shard/full-suite gate are **PENDING**.
No overall PR3-03 acceptance is claimed. No branch, commit or push was created.
Production, frozen pack, accepted migrations, dependency files, and architecture
exceptions are unchanged in this task.

Every changed tracked path:

- `docs/phase3/PR3-03-evidence.md`
- `tests/integration/phase3/gateway_fixtures.py`
- `tests/integration/phase3/test_pr3_03_application.py`
- `tests/integration/phase3/test_pr3_03_migration.py`
- `tests/integration/phase3/test_pr3_03_replay.py`

### t241 replay_writes fix

Reviewed the uncommitted t240 diff and continued from it. The only additional
test edit is in `test_pr3_03_migration.py`: capture `replay_rows` before the
legacy planning/safety/identity replay loops, capture `after_replay` afterward,
and assert the measured symmetric row difference is zero before comparing the
post-replay rows with the post-upgrade snapshot. All saved-result, graph, safety
and replay-count assertions are retained. The baseline is after the first writes
and the schema upgrade, so nullable migration columns do not count as replay writes.

The grep audit used `rg -n '>=\s*0|==\s*0' tests/integration/phase3/test_pr3_03_*.py`
and inspected the surrounding operations and snapshot assignments. Each match
was checked below (line numbers refer to this working tree). No `>= 0` matches
remain in these files. Only the legacy replay measurement had the timing defect.

| File and line | Check reviewed | Disposition |
| --- | --- | --- |
| migration.py:396 | `replay_writes == 0` | Fixed: snapshots now bracket all legacy replays; measurement asserts before the existing row-equality guard. |
| application.py:74 | `scientific_writes == 0` | Retained: baseline at line 27 precedes request/start/finish; snapshot at line 61 follows them. The earlier equality assertion is redundant validation, but does not create the baseline. |
| application.py:149 | `replay_commits == 0` | Retained: commit counter saved at line 146 before invoke replay at line 147. |
| application.py:488 | `safety.consumed.llm_calls == 0` | Retained: actual safety query after UNKNOWN_OUTCOME, before replay. |
| application.py:518 | `final.reserved.llm_calls == 0` | Retained: actual safety query after final reconciliation. |
| application.py:519 | `final.parallel_branches == 0` | Retained: same queried final accounting state. |
| application.py:520 | `final.consumed.token_cost == 0` | Retained: same queried state; explicit fake observation has zero cost. |
| replay.py:269 | `current.consumed.llm_calls == 0` | Retained: queries accounting state after each unknown replay; baseline rows at line 262 precede replay. |
| schema.py:147 | zero JSON/JSONB semantic columns | Retained: direct information_schema SQL count. |
| schema.py:712 | zero obsolete constraints | Retained: direct pg_constraint SQL count. |
| concurrency.py:150 | zero invocations after expiry denial | Retained: direct SQL count after blocked operation. |
| concurrency.py:256 | zero invocations after bounded retries | Retained: direct SQL count after exhausted attempts. |
| concurrency.py:287 | zero invocations after membership revocation | Retained: direct SQL count after waiter completes. |
| concurrency.py:353 | zero invocations after availability writer | Retained: direct SQL count after both jobs complete. |
| concurrency.py:762 | zero STARTED events after stop denial | Retained: direct SQL count after attempted operation; row baseline precedes attempt. |

The filenames above have prefix `tests/integration/phase3/test_pr3_03_`.
The guards file contains no matching zero comparison.

Each required command below was run separately. Before every uv command:
`export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.
Console blocks contain raw combined stdout/stderr, with the actual exit code
recorded separately. An empty block means no output.

#### `git diff --check HEAD`

Exit code: 0

```text
```

#### `uv run ruff check .`

Exit code: 0

```text
All checks passed!
```

#### `uv run ruff format --check .`

Exit code: 0

```text
912 files already formatted
```

#### `uv run pyright`

Exit code: 0

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### `uv run alembic heads`

Exit code: 0

```text
0080_capability_gateway (head)
```

#### `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_03_migration.py`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 3 items

tests/integration/phase3/test_pr3_03_migration.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0080_capability_gateway -> 0079_agent_identity_versions, Frozen PR3-03 capability gateway; forward-only migration.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_4e8da413600f42e9be1acdfffbfdb1fc
clean-0080 tables 158 rows 0 sha256 b108387906bb7867eeedf350b1491633e856a67ae5293939bfabeb8fe0209315
POSTGRES 18.6 (Homebrew) role researchbase encoding UTF8
DISPOSABLE_DROPPED: researchbase_pr212_test_4e8da413600f42e9be1acdfffbfdb1fc
.INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 76.444, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "6199be88-3f9f-4711-a713-d8ea37b43b22", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.026361+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.027265+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.834, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.027304+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.864, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.027324+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.281, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6199be88-3f9f-4711-a713-d8ea37b43b22", "result": "success", "rollback": false, "target_id": "01a16796-78e0-7e47-9aee-70a6dbead254", "timestamp": "2026-10-23T07:07:57.033632+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.034159+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.505, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.034190+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.53, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-78e5-704c-900b-293126521bce", "timestamp": "2026-10-23T07:07:57.034207+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.02, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6199be88-3f9f-4711-a713-d8ea37b43b22", "result": "success", "rollback": false, "target_id": "01a16796-78e5-704c-900b-293126521bce", "timestamp": "2026-10-23T07:07:57.037253+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.037742+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.477, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.037774+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.5, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-78e5-704c-900b-293126521bce", "timestamp": "2026-10-23T07:07:57.037790+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_research_question", "correlation_id": null, "duration_ms": 4.315, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.082085+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.083004+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question", "correlation_id": null, "duration_ms": 0.884, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.083050+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.915, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7917-7ec9-a411-dc814b8e9e5a", "timestamp": "2026-10-23T07:07:57.083074+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_research_question", "correlation_id": null, "duration_ms": 2.91, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7917-7ec9-a411-dc814b8e9e5a", "timestamp": "2026-10-23T07:07:57.086016+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.086538+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question_version", "correlation_id": null, "duration_ms": 0.512, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.086575+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.538, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7917-7ec9-a411-dc814b8e9e5a", "timestamp": "2026-10-23T07:07:57.086595+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_hypothesis", "correlation_id": null, "duration_ms": 3.692, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.090318+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.091002+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis", "correlation_id": null, "duration_ms": 0.67, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.091037+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.694, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-791f-700c-b999-a426c619e886", "timestamp": "2026-10-23T07:07:57.091056+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_hypothesis", "correlation_id": null, "duration_ms": 2.729, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-791f-700c-b999-a426c619e886", "timestamp": "2026-10-23T07:07:57.093814+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.094308+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis_version", "correlation_id": null, "duration_ms": 0.482, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.094343+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.506, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-791f-700c-b999-a426c619e886", "timestamp": "2026-10-23T07:07:57.094362+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_metric_definition", "correlation_id": null, "duration_ms": 3.233, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.097637+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.098326+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition", "correlation_id": null, "duration_ms": 0.679, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.098361+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.703, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7926-79d9-b3ee-1b2a5d18e48d", "timestamp": "2026-10-23T07:07:57.098380+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_metric_definition", "correlation_id": null, "duration_ms": 2.765, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7926-79d9-b3ee-1b2a5d18e48d", "timestamp": "2026-10-23T07:07:57.101175+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.101749+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition_version", "correlation_id": null, "duration_ms": 0.564, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.101786+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.588, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7926-79d9-b3ee-1b2a5d18e48d", "timestamp": "2026-10-23T07:07:57.101805+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_experiment_spec", "correlation_id": null, "duration_ms": 3.757, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.105599+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.106358+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec", "correlation_id": null, "duration_ms": 0.744, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.106392+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.773, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-792e-7d1d-8659-eb72c4c416ef", "timestamp": "2026-10-23T07:07:57.106416+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_experiment_spec", "correlation_id": null, "duration_ms": 2.83, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-792e-7d1d-8659-eb72c4c416ef", "timestamp": "2026-10-23T07:07:57.109279+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.109790+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec_version", "correlation_id": null, "duration_ms": 0.502, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.109825+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.525, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-792e-7d1d-8659-eb72c4c416ef", "timestamp": "2026-10-23T07:07:57.109844+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_run", "correlation_id": null, "duration_ms": 1.974, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.111850+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.112686+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0.817, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.112722+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.842, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.112742+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "start_run", "correlation_id": null, "duration_ms": 3.425, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7936-7f36-bbe0-7726610d71fe", "timestamp": "2026-10-23T07:07:57.116193+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.116690+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.116724+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.499, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.116743+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "finish_run", "correlation_id": null, "duration_ms": 1.127, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7936-7f36-bbe0-7726610d71fe", "timestamp": "2026-10-23T07:07:57.117898+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.118378+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0.458, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.118411+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.481, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.118429+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "record_measurement", "correlation_id": null, "duration_ms": 3.108, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7936-7f36-bbe0-7726610d71fe", "timestamp": "2026-10-23T07:07:57.121568+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_measurement", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.122495+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_measurement", "correlation_id": null, "duration_ms": 0.909, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.122533+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.937, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.122554+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_claim", "correlation_id": null, "duration_ms": 3.39, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.125981+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.126763+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim", "correlation_id": null, "duration_ms": 0.767, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.126798+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.794, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7943-7508-a097-f04cb361e181", "timestamp": "2026-10-23T07:07:57.126818+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.128021+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 1.207, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.128056+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "link_evidence", "correlation_id": null, "duration_ms": 3.465, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7943-7508-a097-f04cb361e181", "timestamp": "2026-10-23T07:07:57.131555+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_evidence_relation", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.132307+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_evidence_relation", "correlation_id": null, "duration_ms": 0.734, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.132339+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.758, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.132357+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.133414+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 1.069, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.133445+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_claim_version", "correlation_id": null, "duration_ms": 3.377, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a16796-7915-7e67-a926-ed765a12ad6f", "result": "success", "rollback": false, "target_id": "01a16796-7943-7508-a097-f04cb361e181", "timestamp": "2026-10-23T07:07:57.136849+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.137434+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim_version", "correlation_id": null, "duration_ms": 0.577, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.137471+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.603, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7943-7508-a097-f04cb361e181", "timestamp": "2026-10-23T07:07:57.137492+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.986, "error_code": null, "level": "INFO", "project_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "request_id": "3036e3c3-a721-4722-8ff2-2d17d1915cd3", "result": "success", "rollback": false, "target_id": "0c576d27-b5ba-4d59-8c85-a6ec051b6b70", "timestamp": "2026-10-23T07:07:57.138528+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.138987+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.139030+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.139050+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 3.607, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3036e3c3-a721-4722-8ff2-2d17d1915cd3", "result": "success", "rollback": false, "target_id": "01a16796-7952-73be-b357-a3d437b78390", "timestamp": "2026-10-23T07:07:57.142685+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.143179+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.483, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.143213+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.508, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7954-7103-86ec-fa3c71c2456a", "timestamp": "2026-10-23T07:07:57.143232+00:00"}
INFO  [researchbase.commands] {"actor_id": "1b129921-d4f3-4f08-8e0a-611180d58498", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.374, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3036e3c3-a721-4722-8ff2-2d17d1915cd3", "result": "success", "rollback": false, "target_id": "01a16796-7954-7103-86ec-fa3c71c2456a", "timestamp": "2026-10-23T07:07:57.145634+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.146108+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.465, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:57.146141+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7954-7103-86ec-fa3c71c2456a", "timestamp": "2026-10-23T07:07:57.146160+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.163427+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.173849+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.177205+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.257720+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.368565+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.370450+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.371935+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:57.378873+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0080_capability_gateway -> 0079_agent_identity_versions, Frozen PR3-03 capability gateway; forward-only migration.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_0e4f2f621cd4439a973fb5e076319d82
populated-0079 tables 153 rows 65 sha256 94838fd9e71df46a61a747183189949beed97a743a6348fcd65dfce8e0ebde1a
populated-0080 tables 158 rows 65 sha256 602e25a2c3db0b987f420c90998e551461622a74b9e331cdc0d67f29ca0dadb0
retained trigger OIDs/attachments 426 legacy result replays=3 UPDATE=0
.DISPOSABLE_DROPPED: researchbase_pr212_test_0e4f2f621cd4439a973fb5e076319d82
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "49f08bfd-1303-4e21-a8f1-78d874a934f2", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 8.267, "error_code": null, "level": "INFO", "project_id": "7c6b6e25-585b-45b6-97f4-f6b251f5eb3c", "request_id": "05ee6f2a-68f0-4a47-9f11-c097e61a806d", "result": "success", "rollback": false, "target_id": "7c6b6e25-585b-45b6-97f4-f6b251f5eb3c", "timestamp": "2026-10-23T07:07:58.274533+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.277153+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.37, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:58.277296+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.505, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:58.277379+00:00"}
INFO  [researchbase.commands] {"actor_id": "49f08bfd-1303-4e21-a8f1-78d874a934f2", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 13.804, "error_code": null, "level": "INFO", "project_id": null, "request_id": "05ee6f2a-68f0-4a47-9f11-c097e61a806d", "result": "success", "rollback": false, "target_id": "01a16796-7dbf-76da-a8e3-a2d9467d1016", "timestamp": "2026-10-23T07:07:58.291316+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.292813+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.413, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:58.292896+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7dcd-7d97-a2be-b88b9f51ad2f", "timestamp": "2026-10-23T07:07:58.292944+00:00"}
INFO  [researchbase.commands] {"actor_id": "49f08bfd-1303-4e21-a8f1-78d874a934f2", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.842, "error_code": null, "level": "INFO", "project_id": null, "request_id": "05ee6f2a-68f0-4a47-9f11-c097e61a806d", "result": "success", "rollback": false, "target_id": "01a16796-7dcd-7d97-a2be-b88b9f51ad2f", "timestamp": "2026-10-23T07:07:58.298857+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.299743+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.852, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:07:58.299810+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.91, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a16796-7dcd-7d97-a2be-b88b9f51ad2f", "timestamp": "2026-10-23T07:07:58.299853+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.585472+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.588842+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.695186+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.697340+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.699658+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.701378+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.703068+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.704761+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.710928+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.715234+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.719539+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.723989+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.728306+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.732504+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.733857+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.734920+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.736106+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.737135+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:07:58.738607+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_e2746d8db62945fa8e08b2c9100ba4b3
ALL_LEGACY_REPLAY 6 6 3 replay_writes=0
.DISPOSABLE_DROPPED: researchbase_pr212_test_e2746d8db62945fa8e08b2c9100ba4b3


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal
tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal
tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal
tests/integration/phase3/test_pr3_03_migration.py::test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade
tests/integration/phase3/test_pr3_03_migration.py::test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade
tests/integration/phase3/test_pr3_03_migration.py::test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade
tests/integration/phase3/test_pr3_03_migration.py::test_all_original_planning_safety_s1_saved_results_after_upgrade
tests/integration/phase3/test_pr3_03_migration.py::test_all_original_planning_safety_s1_saved_results_after_upgrade
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 8 warnings in 3.88s =========================
```

#### `uv run pytest -o addopts='' -ra tests/unit/phase3`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 955 items

tests/unit/phase3/test_agent_identity_contracts.py .                     [  0%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [  3%]
........................................                                 [  7%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [  9%]
........................................................................ [ 17%]
....                                                                     [ 17%]
tests/unit/phase3/test_agent_version_transports.py ..................    [ 19%]
tests/unit/phase3/test_capability_gateway.py ........................... [ 22%]
........................................................................ [ 29%]
........................................................................ [ 37%]
...................................................................      [ 44%]
tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 46%]
........................................................                 [ 51%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 53%]
.................................................                        [ 58%]
tests/unit/phase3/test_capability_routing.py ........................... [ 61%]
........................................................                 [ 67%]
tests/unit/phase3/test_harness_manifest.py ...............               [ 69%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 71%]
....................................................                     [ 76%]
tests/unit/phase3/test_research_task_graph.py .......................... [ 79%]
........................................................................ [ 87%]
.                                                                        [ 87%]
tests/unit/phase3/test_research_task_transports.py ....................  [ 89%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 90%]
tests/unit/phase3/test_task_checkpoints.py ................              [ 92%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 93%]
tests/unit/phase3/test_task_safety_policies.py ......................... [ 96%]
.......................                                                  [ 98%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================= 955 passed in 6.97s ==============================
```

Printed legacy replay measurement (quoted from the migration run):

> ALL_LEGACY_REPLAY 6 6 3 replay_writes=0

#### Architecture check — initial missing database selector

Command: `uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`

Exit code: 1. Collected 366; 351 passed, 15 setup errors, 7 warnings in 5.69s.
The command omitted the PostgreSQL selector required by the inherited Phase 2
architecture fixtures. This attempt is not PASS. Diagnostic and summary excerpts:

```text
E           Failed: Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL
================== 351 passed, 7 warnings, 15 errors in 5.69s ==================
```

#### Architecture check — rerun with explicit disposable admin selector

Command: `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 366 items

tests/architecture/test_b01_resolution_boundaries.py ...                 [  0%]
tests/architecture/test_b02_strategy_promotion_boundaries.py ....        [  1%]
tests/architecture/test_b03_discussion_hypothesis_boundaries.py ....     [  3%]
tests/architecture/test_b04_boundaries.py ....                           [  4%]
tests/architecture/test_b05_review_boundaries.py ....                    [  5%]
tests/architecture/test_b06_revision_action.py ...                       [  6%]
tests/architecture/test_b07_revision_decisions.py ...                    [  6%]
tests/architecture/test_b08_issue_disposition.py ...                     [  7%]
tests/architecture/test_b10_reconsideration.py ...                       [  8%]
tests/architecture/test_b11_readiness_boundaries.py ...                  [  9%]
tests/architecture/test_b12_prepare_boundaries.py ....                   [ 10%]
tests/architecture/test_b13_grant_boundaries.py ....                     [ 11%]
tests/architecture/test_b14_ready_boundaries.py .....                    [ 12%]
tests/architecture/test_b14a_entry_boundaries.py ..                      [ 13%]
tests/architecture/test_b14r_ready_approval_boundaries.py ...            [ 14%]
tests/architecture/test_b15_package_boundaries.py ....                   [ 15%]
tests/architecture/test_b16_boundaries.py ...                            [ 16%]
tests/architecture/test_b17_boundaries.py ...                            [ 16%]
tests/architecture/test_b19_close_prior_art_boundaries.py ..             [ 17%]
tests/architecture/test_b20_screening_boundaries.py ...                  [ 18%]
tests/architecture/test_b21_capture_boundaries.py ..                     [ 18%]
tests/architecture/test_b22_prior_art_boundaries.py ...                  [ 19%]
tests/architecture/test_b23_novelty_boundaries.py ...                    [ 20%]
tests/architecture/test_b25_boundaries.py ...                            [ 21%]
tests/architecture/test_b26_boundaries.py ...                            [ 22%]
tests/architecture/test_b27_defensive_closure_read.py ...                [ 22%]
tests/architecture/test_b32_boundaries.py ................               [ 27%]
tests/architecture/test_basic_approval.py ...                            [ 28%]
tests/architecture/test_import_boundaries.py .............               [ 31%]
tests/architecture/test_m1_boundaries.py ...                             [ 32%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 36%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 39%]
tests/architecture/test_pr12_boundaries.py ....                          [ 40%]
tests/architecture/test_pr13_boundaries.py ..                            [ 41%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 42%]
tests/architecture/test_pr14_boundaries.py ..                            [ 42%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 43%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 44%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 46%]
tests/architecture/test_pr18_boundaries.py .......                       [ 48%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 49%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 50%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 54%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 60%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 61%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 68%]
................................                                         [ 77%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 78%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 79%]
tests/architecture/test_pr3_03_boundaries.py ..............              [ 83%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 83%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 366 passed, 50 warnings in 21.70s =======================
```

All six requested verification commands exited 0. Focused pytest results:
migration 3 passed (8 warnings); Phase 3 unit 955 passed; architecture rerun
366 passed (50 warnings). No tests failed or skipped in these successful runs.
The first architecture attempt's 15 setup errors are recorded above.

This t241 edit adds only this evidence subsection and the migration-test snapshot
fix to the inherited t240 working tree. No other audited assertion changed.
Other PostgreSQL suites were not rerun for this snapshot-only change. S9,
six-shard/full-suite execution, and overall PR acceptance remain outside this task.
No frozen pack, accepted migration, dependency file, architecture exception,
branch, commit, or push was changed or created.

Final evidence whitespace check: `git diff --check HEAD` initially exited 2
with the following output after appending the transcripts; removed the extra
blank line at EOF before the final rerun.

```text
docs/phase3/PR3-03-evidence.md:6025: new blank line at EOF.
```

Final rerun: `git diff --check HEAD`, exit code 0, raw output:

```text
```

### t242 scientific_writes fix

Continued from the inherited uncommitted t240/t241 changes. Removed only the
redundant `assert all(before[t] == after[t] for t in scientific)` from the normal-role
application test. The retained `before` snapshot precedes request/start/finish;
`after` follows finish. `scientific_writes` is computed from their symmetric row
differences, asserted zero, and printed using the measured variable.

Audited `rg -n '==\s*0' tests/integration/phase3/test_pr3_03_*.py` and inspected
all 15 matches and their surrounding snapshot/query/counter ordering. Each check
is listed below; no other real tautology was found. Filenames have prefix
`tests/integration/phase3/test_pr3_03_`; line numbers reflect this t242 tree.

| File:line | Assertion reviewed | Result |
| --- | --- | --- |
| application.py:73 | `scientific_writes == 0` | Removed preceding redundant equality guard; actual snapshots bracket the operations. |
| application.py:148 | `replay_commits == 0` | Counter baseline saved before invoke replay; delta computed before assertion. Retained. |
| application.py:487 | `safety.consumed.llm_calls == 0` | Queried safety state after unknown finish, before assertion. Retained. |
| application.py:517 | `final.reserved.llm_calls == 0` | Queried final safety state after reconciliation. Retained. |
| application.py:518 | `final.parallel_branches == 0` | Same previously queried final safety state. Retained. |
| application.py:519 | `final.consumed.token_cost == 0` | Same previously queried state, explicit zero-cost fake observation. Retained. |
| migration.py:396 | `replay_writes == 0` | t241 snapshots bracket legacy replay loops; delta computed before assertion and before row-equality guard. Retained. |
| replay.py:269 | `current.consumed.llm_calls == 0` | Safety query follows each unknown replay, precedes assertion. Retained. |
| schema.py:147 | zero JSON/JSONB semantic columns | Direct SQL count evaluated in assertion. Retained. |
| schema.py:712 | zero obsolete constraints | Direct SQL count evaluated in assertion. Retained. |
| concurrency.py:150 | zero invocations after expiry denial | Direct SQL count after denied operation. Retained. |
| concurrency.py:256 | zero invocations after retry exhaustion | Direct SQL count after attempts complete. Retained. |
| concurrency.py:287 | zero invocations after membership revocation | Direct SQL count after waiter completes. Retained. |
| concurrency.py:353 | zero invocations after availability change | Direct SQL count after both jobs complete. Retained. |
| concurrency.py:762 | zero STARTED events after stop denial | Direct SQL count after attempted operation. Retained. |

The guards file has no matching assertion. No other test assertion was changed.

Each command below ran separately. Before every uv command:
`export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.
Raw combined stdout/stderr is pasted without trimming; empty blocks mean no output.

#### `git diff --check HEAD`

Exit code: 0

```text
```

#### `uv run ruff check .`

Exit code: 0

```text
All checks passed!
```

#### `uv run ruff format --check .`

Exit code: 0

```text
912 files already formatted
```

#### `uv run pyright`

Exit code: 0

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### `uv run alembic heads`

Exit code: 0

```text
0080_capability_gateway (head)
```

#### `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_03_application.py -k test_normal_role_request_start_finish_and_effect_counts`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 63 items / 62 deselected / 1 selected

tests/integration/phase3/test_pr3_03_application.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 38.841, "error_code": null, "level": "INFO", "project_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "request_id": "323a281f-e601-4133-99a8-606bc7dbdb15", "result": "success", "rollback": false, "target_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "timestamp": "2026-10-23T07:46:12.544769+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.546189+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.126, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.546232+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.161, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.546255+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 7.056, "error_code": null, "level": "INFO", "project_id": null, "request_id": "323a281f-e601-4133-99a8-606bc7dbdb15", "result": "success", "rollback": false, "target_id": "01a167b9-7fbf-7802-9fa8-7e7c4dcdcbae", "timestamp": "2026-10-23T07:46:12.553346+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.553904+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.536, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.553937+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.563, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-7fc5-79be-8963-c7ace8f872af", "timestamp": "2026-10-23T07:46:12.553955+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.024, "error_code": null, "level": "INFO", "project_id": null, "request_id": "323a281f-e601-4133-99a8-606bc7dbdb15", "result": "success", "rollback": false, "target_id": "01a167b9-7fc5-79be-8963-c7ace8f872af", "timestamp": "2026-10-23T07:46:12.557006+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.557490+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.473, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.557521+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.497, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-7fc5-79be-8963-c7ace8f872af", "timestamp": "2026-10-23T07:46:12.557540+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.027, "error_code": null, "level": "INFO", "project_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "request_id": "26f8d3a0-2c84-45b2-91b2-2a8b7485d2e0", "result": "success", "rollback": false, "target_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "timestamp": "2026-10-23T07:46:12.706629+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.707087+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.428, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.707119+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.707135+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.935, "error_code": null, "level": "INFO", "project_id": null, "request_id": "26f8d3a0-2c84-45b2-91b2-2a8b7485d2e0", "result": "success", "rollback": false, "target_id": "01a167b9-8062-7da2-a585-bba8f18f6681", "timestamp": "2026-10-23T07:46:12.710090+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.710471+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.37, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.710493+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.387, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-8064-7c42-86f2-dcbdc06d379a", "timestamp": "2026-10-23T07:46:12.710507+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.801, "error_code": null, "level": "INFO", "project_id": null, "request_id": "26f8d3a0-2c84-45b2-91b2-2a8b7485d2e0", "result": "success", "rollback": false, "target_id": "01a167b9-8064-7c42-86f2-dcbdc06d379a", "timestamp": "2026-10-23T07:46:12.712327+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.712696+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.359, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.712717+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.375, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-8064-7c42-86f2-dcbdc06d379a", "timestamp": "2026-10-23T07:46:12.712729+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.743, "error_code": null, "level": "INFO", "project_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "request_id": "d2801f7f-2f91-4ff3-8289-14efaf473c42", "result": "success", "rollback": false, "target_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "timestamp": "2026-10-23T07:46:12.713621+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.713968+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.336, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.713987+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.351, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.714000+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.288, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d2801f7f-2f91-4ff3-8289-14efaf473c42", "result": "success", "rollback": false, "target_id": "01a167b9-8069-71d3-9505-d6ae66ae3fd6", "timestamp": "2026-10-23T07:46:12.716305+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.716678+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.378, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.716711+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.399, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-806b-7ec4-9c45-e04709cbbebf", "timestamp": "2026-10-23T07:46:12.716729+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.655, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d2801f7f-2f91-4ff3-8289-14efaf473c42", "result": "success", "rollback": false, "target_id": "01a167b9-806b-7ec4-9c45-e04709cbbebf", "timestamp": "2026-10-23T07:46:12.718410+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.718778+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.358, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.718801+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.379, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-806b-7ec4-9c45-e04709cbbebf", "timestamp": "2026-10-23T07:46:12.718818+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.702, "error_code": null, "level": "INFO", "project_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "request_id": "3caf96d9-0eaf-4706-8d89-9c1618d0ef1a", "result": "success", "rollback": false, "target_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "timestamp": "2026-10-23T07:46:12.719698+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.720039+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.328, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.720059+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.344, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.720071+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 1.971, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3caf96d9-0eaf-4706-8d89-9c1618d0ef1a", "result": "success", "rollback": false, "target_id": "01a167b9-806f-7c65-9992-0c6e5e80fc31", "timestamp": "2026-10-23T07:46:12.722059+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.722414+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.348, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.722435+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.364, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-8071-7ca5-991e-3a26c7809d1a", "timestamp": "2026-10-23T07:46:12.722448+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.729, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3caf96d9-0eaf-4706-8d89-9c1618d0ef1a", "result": "success", "rollback": false, "target_id": "01a167b9-8071-7ca5-991e-3a26c7809d1a", "timestamp": "2026-10-23T07:46:12.724194+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.724570+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.372, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.724593+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.389, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-8071-7ca5-991e-3a26c7809d1a", "timestamp": "2026-10-23T07:46:12.724606+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.838, "error_code": null, "level": "INFO", "project_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "request_id": "f4d37f89-6dbc-45ed-af83-898a7dc6faba", "result": "success", "rollback": false, "target_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "timestamp": "2026-10-23T07:46:12.732495+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.732863+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.354, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.732889+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.371, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.732903+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.178, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f4d37f89-6dbc-45ed-af83-898a7dc6faba", "result": "success", "rollback": false, "target_id": "01a167b9-807c-7664-9794-a8ff0344ee3d", "timestamp": "2026-10-23T07:46:12.735101+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.735454+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.34, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.735476+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.358, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-807e-71f9-a646-80405dd5f3e1", "timestamp": "2026-10-23T07:46:12.735489+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.455, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f4d37f89-6dbc-45ed-af83-898a7dc6faba", "result": "success", "rollback": false, "target_id": "01a167b9-807e-71f9-a646-80405dd5f3e1", "timestamp": "2026-10-23T07:46:12.736965+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.737318+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.35, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.737343+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.366, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-807e-71f9-a646-80405dd5f3e1", "timestamp": "2026-10-23T07:46:12.737355+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.688, "error_code": null, "level": "INFO", "project_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "request_id": "52ab27f7-30b0-47a3-a0ea-93811801c34a", "result": "success", "rollback": false, "target_id": "7e8f65e6-73f8-4d1d-8de7-486108273894", "timestamp": "2026-10-23T07:46:12.738072+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.738409+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.325, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.738429+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.339, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.738440+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 1.916, "error_code": null, "level": "INFO", "project_id": null, "request_id": "52ab27f7-30b0-47a3-a0ea-93811801c34a", "result": "success", "rollback": false, "target_id": "01a167b9-8081-752a-b9d8-af258d3bdd6f", "timestamp": "2026-10-23T07:46:12.740373+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.740707+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.327, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.740727+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.344, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-8083-7643-a53f-d611c25eac26", "timestamp": "2026-10-23T07:46:12.740741+00:00"}
INFO  [researchbase.commands] {"actor_id": "792f642a-0c73-473a-aa70-297e6ec7566b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.384, "error_code": null, "level": "INFO", "project_id": null, "request_id": "52ab27f7-30b0-47a3-a0ea-93811801c34a", "result": "success", "rollback": false, "target_id": "01a167b9-8083-7643-a53f-d611c25eac26", "timestamp": "2026-10-23T07:46:12.742140+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.742483+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.338, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:12.742501+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.352, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-8083-7643-a53f-d611c25eac26", "timestamp": "2026-10-23T07:46:12.742513+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.743732+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.777529+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.805072+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.807269+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.882567+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.886051+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.942011+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.942808+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:12.972924+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_7e9d7abbed6e48e88907f628961b30b1
RUNTIME_ROLE pr302_01a167b97fcd7c5392b3c6ec4f324185 encoding UTF8 version 18.6 (Homebrew)
normal-role effects {'agent_tool_policies': 1, 'agent_tool_policy_permissions': 1, 'capability_invocations': 1, 'capability_invocation_refs': 1, 'capability_invocation_events': 3, 'budget_reservations': 1, 'budget_usage_records': 1} scientific_writes=0 {'gateway_commits': 4, 'fake_calls': 0}
.DISPOSABLE_DROPPED: researchbase_pr212_test_7e9d7abbed6e48e88907f628961b30b1


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_03_application.py::test_normal_role_request_start_finish_and_effect_counts
tests/integration/phase3/test_pr3_03_application.py::test_normal_role_request_start_finish_and_effect_counts
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 1 passed, 62 deselected, 2 warnings in 1.24s =================
```

Requested printed line, quoted verbatim:

> normal-role effects {'agent_tool_policies': 1, 'agent_tool_policy_permissions': 1, 'capability_invocations': 1, 'capability_invocation_refs': 1, 'capability_invocation_events': 3, 'budget_reservations': 1, 'budget_usage_records': 1} scientific_writes=0 {'gateway_commits': 4, 'fake_calls': 0}

#### `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_03_migration.py`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 3 items

tests/integration/phase3/test_pr3_03_migration.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0080_capability_gateway -> 0079_agent_identity_versions, Frozen PR3-03 capability gateway; forward-only migration.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_8853d9f88bd14ca18e3f328dc7adc3e0
clean-0080 tables 158 rows 0 sha256 b108387906bb7867eeedf350b1491633e856a67ae5293939bfabeb8fe0209315
POSTGRES 18.6 (Homebrew) role researchbase encoding UTF8
DISPOSABLE_DROPPED: researchbase_pr212_test_8853d9f88bd14ca18e3f328dc7adc3e0
.INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 39.76, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "0a16cf18-83a8-462c-9b5a-d112ad991235", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.853867+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.854852+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.922, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.854894+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.956, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.854916+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.691, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0a16cf18-83a8-462c-9b5a-d112ad991235", "result": "success", "rollback": false, "target_id": "01a167b9-d2fc-7ad7-ae58-5f7de44b6a5d", "timestamp": "2026-10-23T07:46:33.861641+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.862179+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.529, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.862217+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.555, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d301-793b-abe3-ba9a92fc3a00", "timestamp": "2026-10-23T07:46:33.862236+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.098, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0a16cf18-83a8-462c-9b5a-d112ad991235", "result": "success", "rollback": false, "target_id": "01a167b9-d301-793b-abe3-ba9a92fc3a00", "timestamp": "2026-10-23T07:46:33.865360+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.865857+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.485, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.865890+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.51, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d301-793b-abe3-ba9a92fc3a00", "timestamp": "2026-10-23T07:46:33.865909+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_research_question", "correlation_id": null, "duration_ms": 6.477, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.912452+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.914873+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question", "correlation_id": null, "duration_ms": 2.317, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.914947+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.368, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d334-7eab-9d4b-165eff178066", "timestamp": "2026-10-23T07:46:33.914986+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_research_question", "correlation_id": null, "duration_ms": 42.565, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d334-7eab-9d4b-165eff178066", "timestamp": "2026-10-23T07:46:33.957614+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.958219+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_research_question_version", "correlation_id": null, "duration_ms": 0.562, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.958261+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.594, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d334-7eab-9d4b-165eff178066", "timestamp": "2026-10-23T07:46:33.958287+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_hypothesis", "correlation_id": null, "duration_ms": 3.826, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.962146+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.962834+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis", "correlation_id": null, "duration_ms": 0.673, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.962876+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.702, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d367-7980-83a8-995a3d3b8373", "timestamp": "2026-10-23T07:46:33.962898+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_hypothesis", "correlation_id": null, "duration_ms": 2.593, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d367-7980-83a8-995a3d3b8373", "timestamp": "2026-10-23T07:46:33.965525+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.965995+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_hypothesis_version", "correlation_id": null, "duration_ms": 0.459, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.966031+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d367-7980-83a8-995a3d3b8373", "timestamp": "2026-10-23T07:46:33.966055+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_metric_definition", "correlation_id": null, "duration_ms": 3.034, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.969131+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.969783+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition", "correlation_id": null, "duration_ms": 0.642, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.969819+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.668, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d36e-7dba-8824-b2a083dc12af", "timestamp": "2026-10-23T07:46:33.969839+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_metric_definition", "correlation_id": null, "duration_ms": 2.623, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d36e-7dba-8824-b2a083dc12af", "timestamp": "2026-10-23T07:46:33.972492+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.973022+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_metric_definition_version", "correlation_id": null, "duration_ms": 0.519, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.973057+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.544, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d36e-7dba-8824-b2a083dc12af", "timestamp": "2026-10-23T07:46:33.973078+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_experiment_spec", "correlation_id": null, "duration_ms": 3.117, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.976230+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.976968+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec", "correlation_id": null, "duration_ms": 0.721, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.977004+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.749, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d375-7f3f-8a83-7fba69bfa0c2", "timestamp": "2026-10-23T07:46:33.977027+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_experiment_spec", "correlation_id": null, "duration_ms": 2.691, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d375-7f3f-8a83-7fba69bfa0c2", "timestamp": "2026-10-23T07:46:33.979750+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.980248+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_experiment_spec_version", "correlation_id": null, "duration_ms": 0.487, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.980284+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.512, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d375-7f3f-8a83-7fba69bfa0c2", "timestamp": "2026-10-23T07:46:33.980304+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_run", "correlation_id": null, "duration_ms": 1.898, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.982231+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.983001+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0.75, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.983034+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.775, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.983054+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "start_run", "correlation_id": null, "duration_ms": 3.63, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d37d-7512-a1cf-fa7b6b7aabce", "timestamp": "2026-10-23T07:46:33.986714+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.987199+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0.467, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.987235+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.492, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.987255+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "finish_run", "correlation_id": null, "duration_ms": 1.105, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d37d-7512-a1cf-fa7b6b7aabce", "timestamp": "2026-10-23T07:46:33.988388+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.988848+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_run", "correlation_id": null, "duration_ms": 0.438, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.988880+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.461, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.988899+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "record_measurement", "correlation_id": null, "duration_ms": 2.862, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d37d-7512-a1cf-fa7b6b7aabce", "timestamp": "2026-10-23T07:46:33.991791+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_measurement", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.992634+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_measurement", "correlation_id": null, "duration_ms": 0.826, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.992670+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.853, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.992692+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_claim", "correlation_id": null, "duration_ms": 3.015, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:33.995741+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.996602+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim", "correlation_id": null, "duration_ms": 0.834, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.996639+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.861, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d389-7729-af48-b4eaba857568", "timestamp": "2026-10-23T07:46:33.996659+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:33.997820+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 1.167, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:33.997857+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "link_evidence", "correlation_id": null, "duration_ms": 3.186, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d389-7729-af48-b4eaba857568", "timestamp": "2026-10-23T07:46:34.001079+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_evidence_relation", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.001866+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_evidence_relation", "correlation_id": null, "duration_ms": 0.769, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.001902+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.796, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.001922+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.002989+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_current_claim_version", "correlation_id": null, "duration_ms": 1.076, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.003022+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_claim_version", "correlation_id": null, "duration_ms": 3.191, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01a167b9-d331-7cdc-b93f-c211d9539617", "result": "success", "rollback": false, "target_id": "01a167b9-d389-7729-af48-b4eaba857568", "timestamp": "2026-10-23T07:46:34.006241+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.006787+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_claim_version", "correlation_id": null, "duration_ms": 0.536, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.006822+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.563, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d389-7729-af48-b4eaba857568", "timestamp": "2026-10-23T07:46:34.006843+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.92, "error_code": null, "level": "INFO", "project_id": "a8660438-84be-48ef-abbd-a6211a690835", "request_id": "00a8bd3f-bdf5-48f7-83aa-63e55fd5b49a", "result": "success", "rollback": false, "target_id": "a8660438-84be-48ef-abbd-a6211a690835", "timestamp": "2026-10-23T07:46:34.007806+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.008229+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.413, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.008269+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.438, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.008288+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 3.45, "error_code": null, "level": "INFO", "project_id": null, "request_id": "00a8bd3f-bdf5-48f7-83aa-63e55fd5b49a", "result": "success", "rollback": false, "target_id": "01a167b9-d397-72b9-8ec5-0d937ef34545", "timestamp": "2026-10-23T07:46:34.011766+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.012230+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.012262+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.472, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d399-7230-94b6-3573766c2d09", "timestamp": "2026-10-23T07:46:34.012279+00:00"}
INFO  [researchbase.commands] {"actor_id": "e2849cae-5b34-49f6-8608-e494785d5a54", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.132, "error_code": null, "level": "INFO", "project_id": null, "request_id": "00a8bd3f-bdf5-48f7-83aa-63e55fd5b49a", "result": "success", "rollback": false, "target_id": "01a167b9-d399-7230-94b6-3573766c2d09", "timestamp": "2026-10-23T07:46:34.014436+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.014874+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.43, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:34.014906+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.452, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d399-7230-94b6-3573766c2d09", "timestamp": "2026-10-23T07:46:34.014924+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.029980+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.039218+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.042575+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.114567+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.225627+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.227543+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.229008+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:34.236153+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0080_capability_gateway -> 0079_agent_identity_versions, Frozen PR3-03 capability gateway; forward-only migration.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_ee7cb17618174ce1b988a06ca0602a14
populated-0079 tables 153 rows 65 sha256 2c5cfb58b0f2be23f8763243823d5d960e67e2428edd75bd81b5fdff2b851d17
populated-0080 tables 158 rows 65 sha256 9cf003541a90fcc31be0eb502f2f343c99474248fc516c3e0e7acd248ae6a18f
retained trigger OIDs/attachments 426 legacy result replays=3 UPDATE=0
.DISPOSABLE_DROPPED: researchbase_pr212_test_ee7cb17618174ce1b988a06ca0602a14
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "5ddfa64a-7281-4877-8aec-4c2586f64f06", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 8.089, "error_code": null, "level": "INFO", "project_id": "c0c9f209-f07c-4e8c-bbed-410d0e49b91d", "request_id": "3443515f-21e8-4a48-a27a-53695c9ba20b", "result": "success", "rollback": false, "target_id": "c0c9f209-f07c-4e8c-bbed-410d0e49b91d", "timestamp": "2026-10-23T07:46:35.140060+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.142669+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.354, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:35.142811+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.49, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:35.142894+00:00"}
INFO  [researchbase.commands] {"actor_id": "5ddfa64a-7281-4877-8aec-4c2586f64f06", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.457, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3443515f-21e8-4a48-a27a-53695c9ba20b", "result": "success", "rollback": false, "target_id": "01a167b9-d801-7fe1-b00a-969225868dba", "timestamp": "2026-10-23T07:46:35.155470+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.156697+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.197, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:35.156810+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.29, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d80d-7eda-9991-98db1ee3becd", "timestamp": "2026-10-23T07:46:35.156886+00:00"}
INFO  [researchbase.commands] {"actor_id": "5ddfa64a-7281-4877-8aec-4c2586f64f06", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 6.39, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3443515f-21e8-4a48-a27a-53695c9ba20b", "result": "success", "rollback": false, "target_id": "01a167b9-d80d-7eda-9991-98db1ee3becd", "timestamp": "2026-10-23T07:46:35.163378+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.164252+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.849, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-23T07:46:35.164330+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.912, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a167b9-d80d-7eda-9991-98db1ee3becd", "timestamp": "2026-10-23T07:46:35.164379+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.379253+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.382303+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.489581+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.491219+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.492545+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.493900+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.495195+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.496381+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.501288+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.505572+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.509668+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.513919+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.518105+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.522250+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.523628+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.524775+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.526133+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.527216+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-23T07:46:35.528692+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_f15ebb1c68cf408ab55af166a7c2ef32
ALL_LEGACY_REPLAY 6 6 3 replay_writes=0
.DISPOSABLE_DROPPED: researchbase_pr212_test_f15ebb1c68cf408ab55af166a7c2ef32


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal
tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal
tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal
tests/integration/phase3/test_pr3_03_migration.py::test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade
tests/integration/phase3/test_pr3_03_migration.py::test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade
tests/integration/phase3/test_pr3_03_migration.py::test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade
tests/integration/phase3/test_pr3_03_migration.py::test_all_original_planning_safety_s1_saved_results_after_upgrade
tests/integration/phase3/test_pr3_03_migration.py::test_all_original_planning_safety_s1_saved_results_after_upgrade
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 8 warnings in 3.34s =========================
```

Requested printed line, quoted verbatim:

> ALL_LEGACY_REPLAY 6 6 3 replay_writes=0

#### `uv run pytest -o addopts='' -ra tests/unit/phase3`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 955 items

tests/unit/phase3/test_agent_identity_contracts.py .                     [  0%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [  3%]
........................................                                 [  7%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [  9%]
........................................................................ [ 17%]
....                                                                     [ 17%]
tests/unit/phase3/test_agent_version_transports.py ..................    [ 19%]
tests/unit/phase3/test_capability_gateway.py ........................... [ 22%]
........................................................................ [ 29%]
........................................................................ [ 37%]
...................................................................      [ 44%]
tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 46%]
........................................................                 [ 51%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 53%]
.................................................                        [ 58%]
tests/unit/phase3/test_capability_routing.py ........................... [ 61%]
........................................................                 [ 67%]
tests/unit/phase3/test_harness_manifest.py ...............               [ 69%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 71%]
....................................................                     [ 76%]
tests/unit/phase3/test_research_task_graph.py .......................... [ 79%]
........................................................................ [ 87%]
.                                                                        [ 87%]
tests/unit/phase3/test_research_task_transports.py ....................  [ 89%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 90%]
tests/unit/phase3/test_task_checkpoints.py ................              [ 92%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 93%]
tests/unit/phase3/test_task_safety_policies.py ......................... [ 96%]
.......................                                                  [ 98%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================= 955 passed in 6.95s ==============================
```

#### `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`

Exit code: 0

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 366 items

tests/architecture/test_b01_resolution_boundaries.py ...                 [  0%]
tests/architecture/test_b02_strategy_promotion_boundaries.py ....        [  1%]
tests/architecture/test_b03_discussion_hypothesis_boundaries.py ....     [  3%]
tests/architecture/test_b04_boundaries.py ....                           [  4%]
tests/architecture/test_b05_review_boundaries.py ....                    [  5%]
tests/architecture/test_b06_revision_action.py ...                       [  6%]
tests/architecture/test_b07_revision_decisions.py ...                    [  6%]
tests/architecture/test_b08_issue_disposition.py ...                     [  7%]
tests/architecture/test_b10_reconsideration.py ...                       [  8%]
tests/architecture/test_b11_readiness_boundaries.py ...                  [  9%]
tests/architecture/test_b12_prepare_boundaries.py ....                   [ 10%]
tests/architecture/test_b13_grant_boundaries.py ....                     [ 11%]
tests/architecture/test_b14_ready_boundaries.py .....                    [ 12%]
tests/architecture/test_b14a_entry_boundaries.py ..                      [ 13%]
tests/architecture/test_b14r_ready_approval_boundaries.py ...            [ 14%]
tests/architecture/test_b15_package_boundaries.py ....                   [ 15%]
tests/architecture/test_b16_boundaries.py ...                            [ 16%]
tests/architecture/test_b17_boundaries.py ...                            [ 16%]
tests/architecture/test_b19_close_prior_art_boundaries.py ..             [ 17%]
tests/architecture/test_b20_screening_boundaries.py ...                  [ 18%]
tests/architecture/test_b21_capture_boundaries.py ..                     [ 18%]
tests/architecture/test_b22_prior_art_boundaries.py ...                  [ 19%]
tests/architecture/test_b23_novelty_boundaries.py ...                    [ 20%]
tests/architecture/test_b25_boundaries.py ...                            [ 21%]
tests/architecture/test_b26_boundaries.py ...                            [ 22%]
tests/architecture/test_b27_defensive_closure_read.py ...                [ 22%]
tests/architecture/test_b32_boundaries.py ................               [ 27%]
tests/architecture/test_basic_approval.py ...                            [ 28%]
tests/architecture/test_import_boundaries.py .............               [ 31%]
tests/architecture/test_m1_boundaries.py ...                             [ 32%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 36%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 39%]
tests/architecture/test_pr12_boundaries.py ....                          [ 40%]
tests/architecture/test_pr13_boundaries.py ..                            [ 41%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 42%]
tests/architecture/test_pr14_boundaries.py ..                            [ 42%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 43%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 44%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 46%]
tests/architecture/test_pr18_boundaries.py .......                       [ 48%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 49%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 50%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 54%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 60%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 61%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 68%]
................................                                         [ 77%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 78%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 79%]
tests/architecture/test_pr3_03_boundaries.py ..............              [ 83%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 83%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane121/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 366 passed, 50 warnings in 21.31s =======================
```

All nine commands exited 0. Application: 63 collected, 1 passed, 62 deselected,
2 warnings. Migration: 3 collected, 3 passed, 8 warnings. Phase 3 unit: 955
collected, 955 passed. Architecture: 366 collected, 366 passed, 50 warnings.
No failures, errors or skips were reported in these runs. Pyright reported
0 errors and 0 warnings, plus the quoted newer-version notice.

The t240/t241 changes remain in the working tree. This t242 change touches only
the one redundant test assertion and this evidence subsection. Frozen pack,
accepted migrations, pyproject.toml, uv.lock and architecture exceptions were
not edited. No commit, push or branch was created. S9 and the whole/six-shard
suite were not run; overall PR acceptance remains with independent review and
the external check loop.

Final evidence whitespace check: `git diff --check HEAD`, exit code 0. Raw output:

```text
```
