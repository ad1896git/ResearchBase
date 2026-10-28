# PR3-16 evidence: partial storage/session-create/formal-read slice

Snapshot: 2026-10-28. Reviewed source publication: `91fe951f1cb038dde9b55bbd2bdead3c7f4969c9` ([PR 28](https://github.com/ad1896git/ResearchBase/pull/28)), based on `d273ba3eecda61bf859b0e2167811969f6b72847`. Merging main did not change the reviewed `bc0dbb1` file tree. This is a partial acceptance record under [accepted ADR-0029](../architecture/adr/ADR-0029-pr3-16-minimal-storage-scope.md), not complete historical PR3-16 acceptance or production autonomous search.

The slice comprises four immutable tables in [migration 0082](../../migrations/versions/0082_experiment_search_core.py), following 0081 without rewriting old migrations; ports, mappings, adapters and UoW; pure contracts and vectors; bounded session creation; and formal tree, lineage and budget reads. The legacy ACL regression was corrected before S1 merge. The [domain contracts](../../src/researchbase/agent_runtime/domain/experiment_search.py), [Application boundary](../../src/researchbase/agent_runtime/application/experiment_search.py), [repository](../../src/researchbase/persistence/experiment_search_repository.py), and [queries](../../src/researchbase/persistence/experiment_search_queries.py) provide traceable implementation nodes.

Reads use one current-entitled repeatable-read, read-only snapshot, project the immutable owning task objective, and return the complete bounded response without locks, writes, truncation or pagination. Human and Agent callers share the Application boundary; AgentVersion execution is not a prerequisite. Exact frozen request literals and scientific hashes and history remain unchanged. No objective Artifact, Unicode table or new objective schema was added. The accepted initial read profile is node 10, depth 3, event 11 and link 0; parallel 1 means task-wide outstanding reservation occupancy 1, not measured ten-node production capacity. No scoring, execution, Run creation or promotion is included.

## Captured gates

These are externally captured commander records. Focused captures had zero failures, errors and skips. Counts overlap and **must not be summed**; S1 counts are scoped gates, not total full-suite counts. Independent final reviews passed without P0/P1. The original combined `44e0f38` P2 and later recorded precedence P2/P1 findings were repaired in reviewed S6 `aec36b5`, not left open.

| Gate and captured subject | Result and publication |
| --- | --- |
| S1 schema/constraint/migration at `b66f89cd2918d96bd51e32ca7fdedb7194f3f28d`; old schema assertion maintenance at `76d5a31a0833c9b9b28b48a13e24af68c45395ef` | 424 passed; 206 passed. [PR 24](https://github.com/ad1896git/ResearchBase/pull/24): all 12 expected pre-optimization Linux jobs SUCCESS; merged `171005d2a67728f77857274884278e8ef5de56af`. |
| S2 ports/adapters/mappings/UoW at `f1865ad807fdb3b700c385c3fdcad5ad449cdca1` | 753 focused passed. [PR 25](https://github.com/ad1896git/ResearchBase/pull/25): all 12 expected old-CI jobs SUCCESS; merged `0f608f09df0872d2f4fee49d8a0d9e07533f42dd`. |
| S3 pure contracts/vectors at `84d763c05d1260a20783aa19c4e89194ed53dc9e`; S4 session-create at `db5f5928ea6112ef634c38aec764eba3705e9e20` | 511 and 865 focused passed, respectively. Combined actual PostgreSQL Application regression: 684 passed at `44e0f38d0a895e6a2baa899ea9e4244a839db034`. |
| S6 reads and fresh reference/CAS/status/hash/lifecycle precedence repair at `aec36b5740cab0b9b946ff71e819a85512bd04b7` | 768 passed. [PR 27](https://github.com/ad1896git/ResearchBase/pull/27): all 7 new-CI jobs SUCCESS at this head; merged `d273ba3eecda61bf859b0e2167811969f6b72847`. |
| S7 at `b4ea82fa2d0e298d308751940969ad86f3ef8f74` | 1,963 passed, 99 warnings, 60.77s: 1,884 related Phase 3 unit/architecture cases and 79 PostgreSQL cases. |
| S8-A at `bc0dbb1765c87b2f247e533d902a5c598ddaa247` | 478 passed, 53 warnings, 79.78s, including 34 new actual PostgreSQL concurrency/replay cases. Final S8 review found no P0/P1/P2/P3; the reviewer did not independently rerun PostgreSQL tests. |

S7 root external gate included `uv sync --locked --group dev`, `git diff --check HEAD`, Ruff check/format and Pyright. Its exact captured test command was:

```sh
uv run pytest -o addopts= --junitxml=tmp/s7_354_junit.xml -ra tests/unit/phase3 tests/architecture tests/unit/architecture tests/integration/phase3/test_pr3_16_schema.py tests/integration/phase3/test_pr3_16_migration.py tests/integration/phase3/test_pr3_16_repository.py tests/integration/phase3/test_pr3_16_application.py tests/integration/phase3/test_pr3_16_queries.py
```

S8-A captured locked sync, whitespace, Ruff check/format and Pyright, plus:

```sh
uv run pytest -o addopts= --junitxml=tmp/s8a_355_junit.xml -ra tests/integration/phase3/test_pr3_16_concurrency.py tests/integration/phase3/test_pr3_16_replay.py tests/integration/phase3/test_pr3_16_application.py tests/integration/phase3/test_pr3_16_queries.py tests/integration/phase3/test_pr3_16_schema.py tests/integration/phase3/test_pr3_16_migration.py tests/integration/phase3/test_pr3_16_repository.py tests/architecture/test_pr3_16_boundaries.py tests/unit/phase3/test_experiment_search.py tests/unit/phase3/test_experiment_search_queries.py tests/unit/phase3/test_experiment_search_contracts.py
```

The supplied records do not include exact command lines for S1–S6 or the individual Ruff/Pyright invocations; their results above are not claims that those commands were reconstructed or rerun here. Canonical runtime is `uv` + `pyproject.toml` + `uv.lock`, Python 3.12 and real PostgreSQL 18. Focused local environments used an explicit `RB_TEST_ADMIN_URL` for a disposable local admin database and `PGOPTIONS=-c jit=off` where provided; local PostgreSQL timing settings are not asserted to match Linux CI.

The five [architecture test nodes](../../tests/architecture/test_pr3_16_boundaries.py), including deliberate forbidden and legitimate fixtures, are bounded static checks, not proof against arbitrary Python reflection. S8's [concurrency](../../tests/integration/phase3/test_pr3_16_concurrency.py) and [replay](../../tests/integration/phase3/test_pr3_16_replay.py) cases used an ordinary DML role with guards enabled and canonical fixture data created through owning Application commands, without inherited raw search/actor seeding. Older S1 raw SQL attack fixtures remain separate legitimate guard tests.

Captured waits observed SHARE, project, command, task and Agent actor keys through `pg_locks`, `pg_stat_activity` and blocking PIDs; competing CAS writers; same-key exact replay, hash conflict and own-xmin exclusion; expiry and entitlement checks after observed waits; and recovery after actual commit followed by lost-response injection. Real database deadlock and lock timeout were separated from injected SQLSTATE classification probes. Retries were bounded, without timeout retry or deadline widening.

As of **2026-10-28**, [PR 28](https://github.com/ad1896git/ResearchBase/pull/28) had static SUCCESS and six Linux test shards still RUNNING. Final seven-job acceptance and merge are **PENDING**, not PASS; the commander will finalize after actual results. This document task triggers no cloud run.

## Unfulfilled obligations

- Production D1 node-budget amendment and activation remain unaccepted: ADR-0027 is PROPOSED and append was denied.
- S5 Run links and failure, prune and close writers remain unfulfilled; production bounded no-I/O verifier integration remains unfulfilled.
- Exhaustive row/DML/FK/constraint wait coverage and S8 performance/full node-bound production capacity remain unfulfilled.
- Complete historical PR3-16 acceptance remains outstanding. Phase 3 work beyond authorized PR3-16 is excluded.
