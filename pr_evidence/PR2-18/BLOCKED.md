> Historical stop report. Director decision 3 (2026-10-14) supersedes this blocker; see VERIFICATION.md for the current implementation evidence.

# PR2-18 first slice — stopped on guide contradiction

Date: 2026-10-14. Implementation is **blocked**, not accepted or complete.

The owner approval status and the earlier director-approved §4 exact-ID readback
correction are preserved. No implementation files or migration were retained.
No existing migration, other PR table/file, branch, or commit was changed.
Read-only sub-agents investigated existing equivalents and reviewed this finding;
the primary agent was the only writer.

## P1 MAJOR — direct-SQL coverage guard cannot provide the prescribed snapshot order

Target: `docs/proposals/PR2-18_Novelty_PriorArt_Contract_DRAFT.md`,
§7 (post-wait validity), §12.1 parent/child guard inventory, and §12.2
(pre-snapshot N SHARE lock requirement).

The Application protocol can lock N before its first snapshot-producing SELECT.
The guide also requires direct-SQL guards to coordinate locks and validate current
same-project/access/validity inputs. A bare SERIALIZABLE INSERT establishes its
transaction snapshot **before** its BEFORE INSERT trigger acquires those locks.
If a concurrent validity writer holds ROW EXCLUSIVE, the trigger waits, the writer
commits, and the trigger then validates against its older snapshot. Subsequent
SELECTs and clock_timestamp() cannot refresh that serializable snapshot.
SSI may legally serialize capture before the overlapping writer; a serialization
error is not guaranteed.

The guide supplies no direct-SQL prelock prerequisite or enforcement design.
Adding one, changing isolation/lock order, or weakening direct-SQL validity
admission would change behavior rather than substitute an equivalent file name.
The implementer therefore stopped as instructed. A director-approved correction
to the direct-SQL capture protocol is required. Checking lock ownership at trigger
entry alone would not prove locks preceded the transaction snapshot.

## Reproduction

`snapshot_probe.py` creates and drops one disposable database through
RB_TEST_ADMIN_URL. It is a minimal PostgreSQL mechanism reproduction, **not** a
PR2-18 migration or integration acceptance test. It creates a mutable validity
row, an INSERT guard that locks its table SHARE and rejects false validity,
and two independent transaction backends plus an observer. It witnesses the
capture backend blocked by the writer using pg_blocking_pids(), commits the
writer, and observes the capture commit without an SSI error.

Command:

```sh
UV_CACHE_DIR="$PWD/.data/uv-cache" uv run python pr_evidence/PR2-18/snapshot_probe.py
```

Observed output (exit 0):

```text
server_version: 18.6 (Homebrew)
lock witness: capture backend blocked by validity writer: True
capture errors: []
current validity: False
persisted capture: [(1, True)]
```

The guard admitted stale validity after the witnessed wait. This confirms the
contradiction; exit 0 is reproduction success, not scientific admission success.

## Verification of the preserved tree

Exact final commands and results:

```sh
UV_CACHE_DIR="$PWD/.data/uv-cache" uv run pyright
# 0 errors, 0 warnings, 0 informations; exit 0.

UV_CACHE_DIR="$PWD/.data/uv-cache" uv run ruff format --check .
# 483 files already formatted; exit 0.

UV_CACHE_DIR="$PWD/.data/uv-cache" uv run ruff check .
# All checks passed; exit 0.

UV_CACHE_DIR="$PWD/.data/uv-cache" uv run pytest tests/unit tests/architecture
# 1901 passed, 5 warnings in 34.08s; exit 0; 0 failures/errors/skips.

UV_CACHE_DIR="$PWD/.data/uv-cache" uv run pytest -o addopts='' --collect-only -q tests/unit | tail -3
# 1841 tests collected.

UV_CACHE_DIR="$PWD/.data/uv-cache" uv run pytest -o addopts='' --collect-only -q tests/architecture | tail -3
# 60 tests collected.

git diff --check
# No output; exit 0.
```

The 1,901 passing combined run contains 1,841 unit and 60 architecture tests;
the separate counts above are collection evidence, not additional execution runs.
The five pytest warnings are inherited Alembic path_separator deprecations.
Pyright also printed an available-version notice; it reported zero diagnostic
warnings. No dependency was changed.

The first uv calls could not initialize the default external cache. Subsequent
commands used the repository-local UV_CACHE_DIR shown above. The first lint run
found one long line in the reproduction; it was corrected before final checks.

PR2-18 unit/integration/architecture suites: **not created or run**, because
implementation stopped on the P1 contradiction. Other PostgreSQL integration
suites: **not run**, since no persistence implementation was retained.
Full suite: **not run**, as expressly reserved for the loop by the latest user
instruction; no loop result is claimed here. There is no bounded acceptance or
zero-failure PR2-18 integration claim.
