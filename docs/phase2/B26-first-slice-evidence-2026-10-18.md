# B26 first-slice implementation evidence — 2026-10-18

Owner authorization is recorded in the proposal's status line. This slice adds
`FindingImpactService.get_finding_manuscript_impact` and the three closed DTOs at
the prescribed Application path. It explains one Finding against one exact frozen
manuscript, including every linked assessment and every matching B25 occurrence.
The embedded validity remains B25's overall current validity; matches assert exact
reachability, including historical paths, rather than causation or support.

B25 now exposes a same-UoW builder. The outer reader prepares the existing bounded
REPEATABLE READ, READ ONLY Session once, scopes roots after reader authorization,
verifies all saved governance bindings and literal assessment hashes, builds B25
validity, checks combined response ceilings, and reauthorizes with fresh database
time immediately before returning. The existing closed decorator permits the
existing domain ContentHash value type while retaining strict/frozen/closed DTO
validation. The new repository methods provide a nonhydrating scoped Finding
header and a complete bounded linked-assessment inventory; empty target sets
retain their existing accepted hash semantics.

No naming/location substitution was needed. No migrations, schema, dependencies,
API/CLI routes, write commands, write lock inventories, or governing Harness files
were changed. No commit, push, or branch was created.

New tests cover the closed contracts, eight mappings, historical statuses and
conclusions, conflicting assessments/corrections, other validity sources,
experimental and literature-bound paths, repeated placements, artifact/citation
and retained-predecessor occurrences, saved corruption and missing roots, fixed
bounds, unchanged counts/hashes, and final credential expiry. Barrier-controlled
separate-connection races observe old/new snapshots while dismissal, assessment,
correction, retraction and dispute writers complete before the reader is released.
SQL capture checks first-statement snapshot setup and absence of explicit locks
and DML. The shared visitor's node/depth guards are exercised directly; combined
response budgets are isolated by expanding the verified builder's returned paths
on a real prepared PostgreSQL Session.

The read-only independent review reported no remaining concrete P0/P1/P2 finding.
This evidence does not claim Phase 2 exit or project-wide/automated propagation.

## Verification environment and commands

PostgreSQL probe: 18.6 (Homebrew). `DATABASE_URL` used the configured lane database.
`RB_TEST_ADMIN_URL` was derived from that same URL with database `postgres`, enabling
the existing disposable PostgreSQL fixtures. Credentials were not printed.
All uv commands used `UV_CACHE_DIR=/private/tmp/rb-lane27-uv`; the default cache is
outside the writable sandbox and initially failed initialization (exit 2).

All focused pytest commands used these exact trailing arguments:

```text
-o addopts= -q -rfE -p no:cacheprovider --tb=short --show-capture=no
```

The whole test suite was not run; its subsequent check belongs to the outer loop.

## Final results

```text
uv run --frozen ruff format --check .
  645 files already formatted; exit 0.
uv run --frozen ruff check .
  All checks passed; exit 0.
uv run --frozen pyright
  0 errors, 0 warnings, 0 informations; exit 0.
git diff --check
  No whitespace findings; exit 0.

uv run --frozen pytest tests/unit tests/architecture -o addopts= -q -rfE -p no:cacheprovider --tb=short --show-capture=no
  5182 passed, 42 warnings in 122.06s; exit 0; zero skipped.

uv run --frozen pytest tests/integration/test_pr14_governance_integration.py tests/integration/test_pr14_schema.py tests/integration/phase2/test_b25_manuscript_validity.py tests/integration/phase2/test_b25_manuscript_audit.py tests/integration/phase2/test_b25_manuscript_read_races.py -o addopts= -q -rfE -p no:cacheprovider --tb=short --show-capture=no
  105 passed, 291 warnings in 242.30s; exit 0; zero skipped.

uv run --frozen pytest tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b26_finding_impact_races.py -o addopts= -q -rfE -p no:cacheprovider --tb=short --show-capture=no
  52 passed, 156 warnings in 122.57s; exit 0; zero skipped.

uv run --frozen pytest tests/integration/phase2/test_b26_finding_impact.py -k 'citation_artifact or selected_history' -o addopts= -q -rfE -p no:cacheprovider --tb=short --show-capture=no
  4 passed, 45 deselected, 12 warnings in 8.89s; exit 0; zero skipped.
```

The last targeted selection verifies the strengthened predecessor-path assertion
and three subsequently added independent-validity/empty-target cases. It repeats
one of the preceding 52 cases: together these runs cover 55 distinct B26
PostgreSQL tests. Warnings were Alembic's existing `path_separator` deprecation
and, in the B25 regressions, the existing SQLAlchemy connection execution-options
warning. Pyright also printed its version-update notice; no dependency was changed.

## Resolved development failures

The first B26 PostgreSQL run had 20 failed and 26 passed (109.59s), because the test
helper assigned ordinal 2 to the first Conclusion placement in a different section.
Changing that test placement to section ordinal 0 fixed the fixture. A subsequent
intermediate integration-file run passed all 44 then-collected tests (129.39s).

An initial DTO collection attempt failed because Pydantic lacked a schema for the
existing ContentHash domain type; the shared closed decorator now explicitly
permits such existing value types. Test-only type diagnostics were corrected.
The first broad unit/architecture run consequently had 5180 passed and 1 failed
(122.16s), at its embedded static gate. After those corrections, a second run had
5181 passed and 1 failed (121.31s): the existing PR2-20 test repeatedly fingerprints
the dirty checkout, and writing this evidence document during that test produced
`mixed evidence subjects`. The final run above held repository contents steady
and passed all 5182. No test or governing Harness rule was weakened for either
failure. Final results, rather than the failed attempts, establish verification.

`git diff --name-only -- migrations pyproject.toml uv.lock` returned no paths.
All changes remain uncommitted. Stop at this authorized first slice; no whole-suite
or Phase 2 gate result is claimed here.
