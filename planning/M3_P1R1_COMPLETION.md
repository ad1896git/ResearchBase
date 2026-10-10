# M3-P1R1 contract-aligned remediation evidence

## Identity and scope

- Worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m3-literature-evidence`
- Branch: `feature/m3-literature-evidence`
- Starting HEAD: `23557364c3e574a34fcbd412b37ae9b50f5ad145`; tracked tree clean.
- Accepted M2 baseline: `6d45d547a0c229e26c089d106d90a1793bf9b912`.
- Implementation commit: `58c97bb8ab1beb7b0caa4dab0f672fee8e6bf91b`.
- Executor count: one; subagents: zero. No push or merge.
- Disposable PostgreSQL 18.6 databases only for integration tests.

## Contract interpretation and obligation matrix

Frozen R2 `docs/architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md` lines 23–31 and `15_Phase2_Hash_Payload_Contract_R2_v1.0.md` lines 7–11, 69–79 control this repair. R2 explicitly permits empty `[]`, requires zero-based contiguous relation ordinals, and prohibits a second SQL canonical-json-v1 implementation. `RELATED` is outside the six permitted relation types.

| Frozen requirement | Enforcement layer | Existing mechanism | Gap and resolution |
| --- | --- | --- | --- |
| One target, project identity, frozen target/evidence, typed relations, digest format | PostgreSQL | 0030 FKs, checks, uniqueness, guards | No new gap established; preserved. |
| Complete relation set with zero-based contiguous ordinals at commit; empty set allowed | PostgreSQL | 0030 unique ordinal and nonnegative check | 0030 accepted a nonempty set starting at ordinal 1. 0031 adds deferred final-state cardinality triggers and a preexisting-row check. There is no separate declared relation-count field. |
| Immutable snapshot and relation rows after creation transaction | PostgreSQL | 0030 immutable triggers and relation insertion guard | Preserved; direct SQL mutation cases pass. |
| Canonical binding and own hash generation | Application | `digest(support_material(...))`, `digest(snapshot_material(...))` | Preserved; no SQL serializer added. |
| Canonical hash and closure verification | Formal application read | `get_snapshot`/snapshot material recomputation and closure checks | Preserved; forged syntactically valid digest is rejected at formal read. |
| Current validity derives from upstream evidence/source state | Application formal read | Existing SUPPORTS-only review/source stale condition | All six permitted relation kinds now stale on invalid source or DISPUTED/REJECTED review; stronger SUPPORTS rules remain. |

The prior prompt's blanket empty-snapshot rejection and database canonical-digest recomputation are withdrawn. A database transaction with a forged but syntactically valid digest may commit; the formal read must reject it. A contiguous prefix with an omitted trailing relation cannot be identified from a separate declared count because none exists; its changed canonical binding is detected by formal read. This division follows R2 rather than treating the SQL layer as a second hash implementation.

## RED reproductions and correction

Before production changes, focused regressions against 0030 produced four failures and one pass: CONTEXTUALIZES snapshots stayed VALID after DISPUTED, REJECTED, or retracted upstream source; a direct-SQL nonempty relation set with ordinal 1 committed. The direct-SQL test supplied a real target and hashes computed over its actual persisted relation, so the cardinality failure was independent of hash forgery. A correctly hashed empty application snapshot passed at 0030 and continues to pass at 0031.

The original arbitrary-digest empty snapshot observation is a database behavior, not by itself a database contract violation. The current test commits such a row and confirms that `get_snapshot` fails closed. `RELATED` remains rejected as an invalid relation type; the existing M3 test covers it. No status or authorization enum was added.

## Implementation

- `src/researchbase/application/literature_evidence.py`: derive STALE for any permitted relation when evidence source validity is non-VALID or review is DISPUTED/REJECTED; retain SUPPORTS verification and reviewer separation checks. Historical rows, relation IDs, ordered set, and hashes remain unchanged.
- `migrations/versions/0031_m3_snapshot_relation_cardinality.py`: lock both M3 tables during upgrade, reject preexisting nonempty ordinal gaps without rewriting them, and add initially deferred constraint triggers for commit-time 0..N-1 cardinality. Empty snapshots remain legal. Downgrade refuses populated scientific history and otherwise removes only the new guards.
- New eight-case PostgreSQL regression module; three older migration-head assertions and the architecture migration allowlist advance from 0030 to 0031. No frozen contract, Phase 1 hash, M2 behavior, identity profile, dependency, lockfile, or Harness file changed.

## PostgreSQL boundary results

| Case | Command / transaction boundary | Expected and actual | SQLSTATE / violation |
| --- | --- | --- | --- |
| Correctly hashed empty | Application `snapshot(..., [])`, one command transaction; then formal `get_snapshot` | Committed and read VALID | None; no violation |
| Correctly hashed nonempty | Application `snapshot(..., [CONTEXTUALIZES])`; formal read | Committed and read VALID | None; no violation |
| Nonempty set with ordinal 1 and computed hashes for that row | Direct SQL snapshot + relation INSERT in `engine.begin()`; commit | 0030 committed (RED); 0031 rolls back at commit | 23514; repaired structural violation |
| Contiguous prefix with omitted trailing relation | No declared count exists; compare persisted rows with binding hash at formal read | Formal read rejects when binding differs | Application error; no independently enforceable SQL count |
| Postseal insert/update/delete | Direct SQL in separate transactions after application seal | Rejected | DBAPIError; existing 0030 guards |
| Forged syntactically valid binding and own digests | Direct SQL empty snapshot INSERT in `engine.begin()`; commit | Commit accepted, as allowed by R2 layer split | None at commit; no DB violation |
| Formal read of forged digest | `get_snapshot` after commit | Rejected | `ResearchBaseError`; fail closed |
| 0030→0031 with valid empty row | Downgrade disposable DB to 0030, create valid row, upgrade | Upgrade succeeds, formal read succeeds | None |
| 0030→0031 with preexisting gap | Insert gap under 0030, then upgrade | Upgrade refuses; Alembic remains 0030 | 23514 |
| Populated 0031 downgrade | Alembic downgrade in disposable DB | Refused to preserve scientific history | P17D5 |

## Verification

The bounded regression command (exit 0) was:

```sh
DATABASE_URL='postgresql+psycopg://onephone@127.0.0.1:55442/postgres' PYTHONPATH='src:.' ../m1-identity-onboarding/.venv/bin/python -m pytest -q -c pyproject.toml tests/integration/phase2/test_m0_provider_cancellation.py tests/integration/phase2/test_m1_local_onboarding.py tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_m3_real_cli.py tests/integration/phase2/test_m3_p1r1.py tests/test_architecture.py tests/unit/test_local_identity.py tests/unit/test_m2_artifact_durability.py tests/unit/test_m2_cli_output.py tests/unit/test_m2_crossref.py tests/unit/test_m2_journal.py tests/unit/test_m2_openalex.py tests/unit/test_m3_localization.py --tb=short --disable-warnings --junitxml=planning/m3_p1r1_evidence/focused-tests.xml
```

Result: **135 passed, 0 failed, 0 errors, 0 skipped**, 145.243 s, recorded in `focused-tests.xml`. This includes M3 golden hash, real CLI, existing M3 security/closure tests, M2/M1, and architecture checks. The test module subsequently received an import-order-only change.

Final focused command (exit 0) after that import edit:

```sh
DATABASE_URL='postgresql+psycopg://onephone@127.0.0.1:55442/postgres' PYTHONPATH='src:.' ../m1-identity-onboarding/.venv/bin/python -m pytest -q -c pyproject.toml tests/integration/phase2/test_m3_p1r1.py --tb=short --disable-warnings --junitxml=planning/m3_p1r1_evidence/focused-p1r1-tests.xml
```

Result: **8 passed, 0 failed, 0 errors, 0 skipped**, 2.892 s. Ruff check of all seven changed Python files: exit 0, `All checks passed!`. Ruff format `--check --no-cache`: exit 0, `7 files already formatted`. Pyright of those files using the project Python path: exit 0, `0 errors, 0 warnings, 0 informations`. `git diff --check` and staged diff check: exit 0. Exact static commands, all exit 0:

```sh
../m1-identity-onboarding/.venv/bin/ruff check --no-cache src/researchbase/application/literature_evidence.py migrations/versions/0031_m3_snapshot_relation_cardinality.py tests/integration/phase2/test_m0_provider_cancellation.py tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_m3_p1r1.py tests/test_architecture.py
../m1-identity-onboarding/.venv/bin/ruff format --check --no-cache src/researchbase/application/literature_evidence.py migrations/versions/0031_m3_snapshot_relation_cardinality.py tests/integration/phase2/test_m0_provider_cancellation.py tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_m3_p1r1.py tests/test_architecture.py
../m1-identity-onboarding/.venv/bin/pyright --pythonpath ../m1-identity-onboarding/.venv/bin/python src/researchbase/application/literature_evidence.py migrations/versions/0031_m3_snapshot_relation_cardinality.py tests/integration/phase2/test_m0_provider_cancellation.py tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_m3_p1r1.py tests/test_architecture.py
git diff --check
```

An initial Ruff check without `--no-cache` exited 2 because the sandbox denied a temporary cache file; the cache-free retry passed. No full historical suite was run.

## Scope and review status

`git diff`/status inspection showed only the seven implementation files and this separate evidence namespace. Previous `planning/m3_evidence` records remain untouched. There are no known open P0/P1 findings from this bounded work. The final independent code review and real human verification remain outstanding; M3 acceptance is not approved, and M4 is not authorized.
