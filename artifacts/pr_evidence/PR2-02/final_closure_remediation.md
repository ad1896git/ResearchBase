# PR2-02 final closure remediation verification

## Subjects

- Starting subject: `cc0fcd6b63fdaba7ae4b9d9970c4b79c263a1d22`
- PR2-02 implementation: `a80ff23a0555b6f629dd40d68372b270dfd5fd61`
- Final remediation implementation: `3de5e897cc72de3e4c4f7b86d83ed8ae2b13fc93`
- Evidence: this file is committed as an evidence-only child and does not certify its own commit SHA.
- Migration head: `0022_source_version_and_merge_lineage`, parent `0021a_source_merge_gov_guards`.
- Frozen Phase 1 baseline: `d2400fbeca835c89bd802a4e9d647bda01cfd115`.

## Approval revocation finding and correction

The prior independent review reported a P2: a revoked approval could reach the deferred database event constraint and emerge as a generic validation/database-check error instead of the deterministic approval denial required by the PR2-02 failure contract.

Reproduction on PostgreSQL 18.6:

1. Create a submitted proposal and approve it as the effective Human Owner.
2. Revoke the approval; the immutable `APPROVAL_REVOKED` event commits.
3. Execute the merge.
4. The merge transaction locks the affected project, sources, proposal, approvals and events, then reads the event history. Before the remediation it checked for `PROPOSAL_CONSUMED` but did not reject `APPROVAL_REVOKED`.
5. The merge attempted its consumption event; the deferred event transition guard rejected it at commit. The repository surfaced `VALIDATION_ERROR` with “database check constraint violated.”

Primary root-cause classification: `APPROVAL_PREFLIGHT_MISSING`. The post-lock event reread already existed; the revoked-approval predicate was missing from the application preflight. The database rule is `ck_source_merge_event_transition` in the accepted governance migration. It remains unchanged as defense in depth.

The remediation checks the locked, freshly reread proposal event set before basis/approval processing. A prior `APPROVAL_REVOKED` event now returns the frozen canonical error `SOURCE_MERGE_APPROVAL_FORBIDDEN` (403). No broad `IntegrityError` translation was added; unrelated database failures remain visible through existing error handling.

## Revocation concurrency and atomicity

PostgreSQL tests use the shared project-row lock as the serialization point. The test holds the first command after acquiring the project lock, starts the competing command, and confirms the second is waiting in PostgreSQL before releasing the first.

| Interleaving | Result | Protected effects |
|---|---|---|
| Revocation commits first | Merge rereads the revoked event and raises `SOURCE_MERGE_APPROVAL_FORBIDDEN`. | No SourceMergeRecord; both sources remain ACTIVE with null merge pointers; no identifier rows; no `PROPOSAL_CONSUMED` event. The immutable revocation audit event remains. |
| Merge acquires the lock first | Merge commits; later revocation sees terminal consumption and returns `SOURCE_MERGE_BASIS_CONFLICT`. | Exactly one merge record and consumption event; later revocation does not retroactively alter the completed merge. |
| Direct database consumption attempt after revocation | Forcing `trg_source_merge_event_valid` immediate raises PostgreSQL IntegrityError, “source merge event violates terminal proposal state.” | Insert is rolled back. This confirms the accepted DB guard remains active. |

Tests:

```text
test_revoked_merge_approval_returns_canonical_denial_without_effects
test_merge_and_approval_revocation_serialize[revocation]
test_merge_and_approval_revocation_serialize[merge]
```

The tests were first run before the application fix. The revoked-before-execution test and revocation-wins race failed with the reproduced `VALIDATION_ERROR`; the merge-wins race passed. All three pass after the fix.

## PostgreSQL reviewer setup diagnosis and proof

The previous reviewer could not pull its image because its Docker context invoked the missing `docker-credential-desktop` helper. The current author environment was inspected without printing credential values: `DOCKER_CONFIG` was unset, `~/.docker/config.json` named `credsStore=desktop` and had no per-registry helpers, the active context was `colima`, and the daemon was Docker 29.5.2. The local `postgres:18-alpine` image was available.

The pull fallback was separately exercised with a temporary Docker configuration containing only `{"auths":{}}`. The active Docker context was exported and imported into that temporary configuration, then `DOCKER_CONTEXT` selected it for `docker pull postgres:18-alpine`. The pull succeeded without the desktop credential helper. The archive and temporary configuration were removed afterward; the user’s permanent Docker configuration was not changed.

The committed self-contained runner is [scripts/pr2_02_review_postgres.sh](/Users/onephone/Documents/Codex/ResearchBase-phase2/scripts/pr2_02_review_postgres.sh). It:

- uses local `postgres:18-alpine` when available;
- otherwise pulls through a temporary no-helper Docker config containing only the active context;
- starts an isolated PostgreSQL container with local test-only credentials and a dynamically assigned localhost port;
- waits for readiness, prints PostgreSQL’s exact server version, initializes the base DB at frozen migration 0018, and records Alembic current;
- runs the focused PR2-02, governance, and PR2-01 PostgreSQL suites, then the full repository suite;
- removes only the container it created and its temporary files, including on failure.

Clean-room validation used no inherited database URL and no existing PostgreSQL container:

```bash
env -u DATABASE_URL bash scripts/pr2_02_review_postgres.sh
```

Result: `POSTGRES_REVIEW_SETUP_REPRODUCIBLE = YES`; PostgreSQL reported `18.6`; focused suite **31 passed**; full suite **1,892 passed, 2 skipped, 0 failed, 96 Alembic deprecation warnings**. Docker confirmed no helper container remained after exit.

If Docker is unavailable but an existing local PostgreSQL 18.x service is available, the integration fixture supports a caller-supplied `DATABASE_URL` for a role with `CREATEDB` on the `postgres` maintenance database. Set that URL explicitly, initialize its base database to `0018_current_pointer_same_parent_integrity`, and run the focused/full pytest commands from the runner. The version check must still report PostgreSQL 18.x.

### Preserved earlier environment failure

An earlier full run using an ad hoc empty base database reported **304 failed, 1,588 passed, 2 skipped, 96 warnings**. Database logs showed Phase 1 tests failing on `relation "actors" does not exist` and migration preflight failures because the base database had never been upgraded to the frozen Phase 1 head. This was a test setup error, not silently discarded: the setup helper now explicitly upgrades the base DB to migration 0018, and the clean-room rerun above passed.

## Author verification

| Gate | Command / result |
|---|---|
| Focused source-version, source-merge, governance and PR2-01 regressions | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_01_source_identity.py -q` — 31 passed, 36 warnings. |
| Full suite through clean-room helper | 1,892 passed, 2 skipped, 0 failed; 96 warnings. |
| Ruff | `uv run ruff check .` — PASS. |
| Pyright | `uv run pyright` — PASS; 0 errors, warnings or informations. |
| Changed Python formatting | `ruff format --check` on the two changed Python files — both already formatted. |
| Raw formatter command | `uv run ruff format --check .` — nonzero, accurately reported: same nine inherited Phase 1 files as the accepted baseline; 244 files already formatted. `NEW_FORMATTER_FAILURES = ∅`. |
| Shell helper syntax | `bash -n scripts/pr2_02_review_postgres.sh` — PASS. |
| Whitespace | `git diff --check` and `git diff --cached --check` before commit — PASS. |
| Migration | `uv run alembic heads` — unique head `0022_source_version_and_merge_lineage`. No migration was added or changed by this remediation. |
| Phase 1 freeze | Tag object `63f6a1d28afa79ce8620fc9233793ab9c40a515d`; peeled commit equals the frozen baseline. Historical migrations 0001–0018 diff is empty. |
| PR2-00 temporal regression | Included in the passing full suite; no post-expiry challenge success reproduced. |

This remediation changes only the source-merge application preflight, its PostgreSQL integration tests, and the reviewer PostgreSQL setup helper. No governance policy, accepted migration, source-version lifecycle, identifier policy, or Phase 1 behavior changed.

## Evidence boundary

This evidence describes implementation subject `3de5e897cc72de3e4c4f7b86d83ed8ae2b13fc93`. The evidence-only child SHA is intentionally not stated here.
