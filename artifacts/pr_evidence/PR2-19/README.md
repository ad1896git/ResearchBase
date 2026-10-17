# PR2-19 first-slice evidence

Implemented the owner-approved 2026-10-14 first slice in the plan's build order. This is a bounded test slice, not full PR2-19 or Phase 2 acceptance. Production code, dependencies, canonical schema, existing migrations, migration expectations, governing files and the approved proposal are unchanged. No commit, push or branch was created.

The tests add head-upgraded shared fixtures, a fixed two-source corpus, closed frozen report records, candidate rejection/admission, independent evidence verification, source correction/retraction, citation-only tracing, discussion transcript binding, minimal Decision governance, finite rollback faults, exact replay, lost responses, bounded retries, observed races and the thirteen named architecture checks. The approval architecture check verifies the BLOCKED inventory only; its behavioral obligation has not passed.

All listed fixture/helper names had an existing equivalent at the guide's paths, so no naming/location substitution was required. Wrappers upgrade the pinned m3/discussion fixtures after their original setup/preflight. The existing disposable PostgreSQL fixture from PR2-11 supplies the evidence, decision and trace database lifecycle. Agent discussion writes are denied by the current HUMAN-only owning policy; the tests assert FORBIDDEN and zero writes, then use a Human control for close/binding. Evidence self-verification and new SUPPORTS snapshots over invalid source history also use the existing FORBIDDEN code; invalid conclusion admission uses PROVENANCE_CLOSURE_VIOLATION.

PostgreSQL was **18.6 (Homebrew)**, local port 5432, system identifier `7696072587520791948`. Database-derived expiry evidence is normalized to UTC in [observations.json](observations.json); raw JUnit output retains the server's America/New_York offset. The recorded 82 created wrapper databases all have matching drop observations and none remains. Four other cluster databases could not be attributed to these recorded fixtures and were left untouched; their names are recorded in the cleanup section of [verification.json](verification.json).

Verification ran with `UV_CACHE_DIR=tmp/pr219-uv`, an inherited `DATABASE_URL`, and `RB_TEST_ADMIN_URL` explicitly selecting the local PostgreSQL `postgres` admin database. Credentials are omitted here. Commands below are the actual invocations; the environment-only prefix is factored out for readability.

| Command | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS, All checks passed |
| `uv run --no-sync ruff format --check .` | PASS, 522 files already formatted |
| `uv run --no-sync pyright` | PASS, 0 errors, 0 warnings, 0 informations |
| Unit/architecture command below | **2,105 passed**, 0 failed/errors/skipped; 2,012 unit and 93 architecture cases |
| Focused command below | **71 passed**, 0 failed/errors/skipped |
| Regression command below | **152 passed**, 0 failed/errors/skipped |
| `git diff --check` | PASS |

```sh
uv run --no-sync pytest tests/unit tests/architecture -o addopts='' -q --junitxml=artifacts/pr_evidence/PR2-19/unit-architecture.xml -o junit_logging=all

uv run --no-sync pytest tests/integration/phase2/test_pr2_19_*.py -o addopts='' -q --junitxml=artifacts/pr_evidence/PR2-19/focused.xml -o junit_logging=all

uv run --no-sync pytest tests/e2e/test_phase1_golden_scientific_workflow.py tests/integration/phase2/test_pr2_10*.py tests/integration/phase2/test_pr2_11*.py tests/integration/phase2/test_pr2_12*.py tests/integration/phase2/test_pr2_13*.py tests/integration/phase2/test_pr2_14*.py tests/integration/phase2/test_pr2_15*.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_m3_evidence.py -o addopts='' -q --junitxml=artifacts/pr_evidence/PR2-19/regressions.xml
```

The whole suite was not run. JUnit artifacts record every executed node ID and outcome: [unit/architecture](unit-architecture.xml), [focused PostgreSQL](focused.xml), [regressions](regressions.xml). The focused artifact contains the actual lock witnesses, five-timestamp first/second-wait expiry proofs and operational report observation. Final runs retain existing Alembic deprecation warnings (39, 209 and 407 respectively). Earlier development runs exposed incorrect test oracles and formatting violations; the final results above supersede them after corrections.

[verification.json](verification.json) records the exact source revision, approved-plan commit/hash, new-file hashes, all executed node IDs, matrix-to-evidence mapping and blocked dependencies. [observations.json](observations.json) records exact IDs/count deltas, the independently checked fixture-byte hash and UTC expiry proofs. [review.md](review.md) records the read-only review findings and their resolution.

The full gate remains **BLOCKED**: 14 matrix rows, 20 prerequisite contracts and `test_approval_does_not_override_invalid_fact`'s behavioral obligation. The seven RUNNABLE NOW rows have passing evidence; runnable prefixes do not change their parent row's BLOCKED status. Revision/grant-consumption module names are reserved, with no blocked-only modules, skips or expected failures added.
