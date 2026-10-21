# M2-R1 Narrow Defect Remediation

Verdict: **M2_R1_READY_FOR_CLOSURE**.

- Starting SHA: `85835502c14e4bf393e92673c68a5126dbe3d07a`.
- Final verified implementation SHA: `a7b3131cfdabd5978fd824679c66953ffc13d37c`.
- Branch/worktree: `feature/m2-live-literature`, existing `worktrees/m2-live-literature`.
- A report-only delivery commit follows the implementation; its exact SHA is obtained with `git log -1 --format=%H -- planning/M2_R1_REMEDIATION.md` and is supplied in the delivery message. A commit cannot embed its own hash.

## Repairs

**F1 / P1 repaired.** `metadata_journal.py` follows the existing CAS directory-sync pattern: create required directories; fsync the journal directory, then each ancestor through the filesystem root; acquire the existing invocation lock; write/flush/fsync intent bytes; atomically rename intent; fsync the journal directory; only then invoke the provider. The completed-response write retains its existing fsync/rename/directory-sync sequence. Repeating the ancestor barrier for existing paths also covers directories left present by an earlier failed sync. Creation/open/fsync errors propagate before dispatch. Fingerprints, local locking, completed-response replay and intent-only refusal are unchanged. CAS implementation, schemas and migrations are unchanged.

**F2 / P2 repaired.** `metadata_observation.py` now applies the existing `normalize_source_title()` (NFC + surrounding-whitespace stripping) to the provider title used for identity comparison and source/version command inputs. Stored provider observation/evidence bytes are untouched. Genuine identity conflicts remain rejected; authorization and frozen-version rules are unchanged.

## Verification

Used the existing neighboring M1 uv environment (`../m1-identity-onboarding/.venv/bin/python`), `PYTHONPATH=src`, and real PostgreSQL **18.6 (Homebrew)** at `127.0.0.1:55440`. DB tests created/dropped isolated disposable databases through the `/postgres` maintenance URL. Offline provider fixtures were used for regressions; they are not fresh live-provider acceptance.

| Check | Actual result | Evidence |
|---|---|---|
| New regressions before production edits | 8 failed for the two reported defects, 3 passed; exit 1 | `/private/tmp/rb-m2-r1-red.xml` |
| Final new regression selection | 11 passed, 18 deselected; exit 0 | `/private/tmp/rb-m2-r1-focused.xml` |
| Full M2 acceptance selection | 49 passed, 0 failed/errors/skipped; exit 0 (original 38 + 11 new) | `/private/tmp/rb-m2-r1-acceptance.xml` |
| Focused M0/M1 selection | 83 passed, 1 historical diagnostic deselected; exit 0 | `/private/tmp/rb-m2-r1-regressions.xml` |
| Ruff on four modified Python files | All checks passed; exit 0 | `ruff check --no-cache` |
| Formatter on those files | 4 files already formatted; exit 0 | `ruff format --check` |
| Pyright on those files | 0 errors, 0 warnings, 0 informations; exit 0 | Explicit `--pythonpath ../m1-identity-onboarding/.venv/bin/python` |
| Diff whitespace / preserved review checksum | PASS | `git diff --check`; checksum below |

New journal tests instrument real `fsync` calls using directory inode identities and record rename/dispatch ordering. They cover first creation with missing ancestors, existing directories, parent sync failures at two levels, retry after failure, intent-file sync failure, creation failure and completed replay. The existing concurrent replay and intent-only recovery tests also pass. No physical power-loss test was performed.

New PostgreSQL tests cover trailing whitespace and NFC-equivalent Unicode titles, first resolution, exact replay, fresh authenticated CLI process replay, interruption after durable draft creation, preservation of raw evidence, genuine title-conflict refusal, and exactly one SourceVersion/Resolution after recovery. No duplicate versions or resolutions are produced.

Reproduction (from this worktree; set `DATABASE_URL=postgresql+psycopg://onephone@127.0.0.1:55440/postgres` and `PYTHONPATH=src`):

```bash
RB_PYTHON=../m1-identity-onboarding/.venv/bin/python
"$RB_PYTHON" -m pytest tests/unit/test_m2_journal.py tests/integration/phase2/test_m2_metadata.py -k 'directory_chain or parent_sync or intent_file_sync or directory_creation or normalized_title or genuine_title' -o addopts='' -q -p no:cacheprovider
"$RB_PYTHON" -m pytest tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/test_m2_journal.py tests/unit/test_m2_cli_output.py tests/unit/test_m2_artifact_durability.py tests/integration/phase2/test_m2_metadata.py -o addopts='' -q -p no:cacheprovider
"$RB_PYTHON" -m pytest tests/architecture/test_pr2_00_boundaries.py tests/integration/phase2/test_m0_provider_cancellation.py tests/integration/phase2/test_m1_local_onboarding.py tests/integration/phase2/test_pr2_04_authority_coverage.py tests/integration/phase2/test_pr2_04_cancellation_coverage.py tests/integration/phase2/test_pr2_04_commit_fault_coverage.py tests/integration/phase2/test_pr2_04_restart_completion.py tests/unit/test_local_identity.py -o addopts='' -q -p no:cacheprovider -k 'not test_pg_equal_created_at_cursor_uses_uuid_tiebreak_without_duplicates_or_omissions'
```

An initial Pyright check found two test-double protocol signature errors; the signature was corrected and the final focused tests and static checks above passed. Existing Alembic `path_separator` deprecation warnings and Pyright's missing local `.venv` notice remain. No new dependency or environment definition was introduced.

## Remaining debt and recommendation

No known open **P0/P1** remains in this narrow remediation; F1 and F2 are repaired. Existing **P2** debt remains: historical cursor evidence-recorder serialization failure; dormant confirmed-C1 Retry-After response-reuse normalization; and slow-stream transport without a hard wall-clock deadline. Five inherited M1 retry-count assertions remain deferred and were not rerun. The full historical suite and physical crash/backup-restore drills were not run or represented as passing.

OpenAlex/Crossref adapter behavior is unchanged. Reuse the existing real-provider evidence `/private/tmp/rb-m2-live-final.json`, independently checked by the prior review, including its recommendation classified OTHER rather than a research paper. No fresh external request was issued. Bibliographic MATCH remains distinct from LiteratureEvidence or Claim support.

Recommend **M3_GO for bounded further development after final M2 closure**. This is readiness advice, not production certification or permission exercised to start M3. No further architecture review procedure is introduced.

## Delivery and preservation

The independent report remains untracked and byte-for-byte unchanged: `planning/M2_FINAL_INDEPENDENT_REVIEW.md`, SHA-256 `e9af86fcf854f3a29371c8c3bb977d17bb70bd5d9f6d2dd3d8a3402a9d92fd0c`. It is intentionally excluded from commits and the Git bundle; no user change was reset or cleaned. The tracked worktree is expected clean after the report-only commit, with only that preexisting untracked file disclosed.

One new milestone bundle is delivered at `/Users/onephone/Documents/Codex/ResearchBaseProject/backups/m2-r1-remediation-milestone.bundle`. Final delivery verifies it with `git bundle verify` and confirms its branch head equals the delivery HEAD. Existing bundles are preserved. The bundle contains code/history, not PostgreSQL, CAS, dispatch journal or local identity installation state; those still require coordinated operational backups. Temporary demo data remains disposable.

No push, merge, new worktree, schema, migration, framework, unrelated repair or M3 implementation. Stop after delivery.
