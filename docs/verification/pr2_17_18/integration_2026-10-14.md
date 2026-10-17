# PR2-17 and PR2-18 first-slice integration

Current restart evidence appears in the final section. Earlier check results and
handoff restrictions below are historical. The current task reserves the full
suite for the loop; no current full-suite result is inferred from older runs.

Scope: integrate the already-present slices only. No slice behavior, DDL,
dependency, architecture, commit, push, or branch change.

The migration chain is now:

```text
0045_pr2_16_basic_approval
-> 0046_pr2_17_authorship
-> 0047_pr2_18_novelty_prior_art (sole head)
```

PR2-18's file is `migrations/versions/0047_pr2_18_novelty_prior_art.py`.
Its bytes were compared against the staged cherry-picked original: replacing
exactly the `revision` and `down_revision` assignments produces the new file
byte-for-byte. The SHA-256 of the bytes starting at `def upgrade()` (including both migration
functions) is
`b17c281b0805b9ccb85ad8bbba588bba817597421b37d115a7aba8199106f5ab`.
The PR2-17 migration remains byte-identical to HEAD.

Conflict resolution preserves both repository protocols, both UoW repositories,
and each slice's error normalization. Updated head/parent expectations, CI,
static baseline, migration inventories, migration path references, PR2-17's
rollback head assertion, and documentation. Historical first-slice command
results retain their original observed revision names and are labeled historical.

## Environment and exact commands

PostgreSQL reports `18.6 (Homebrew)`; all database checks use disposable databases.
Commands below use these environment variables:

```sh
export UV_CACHE_DIR="$PWD/.data/uv-cache"
export DATABASE_URL='postgresql+psycopg://fengwang@localhost/postgres'
export RB_TEST_ADMIN_URL='postgresql+psycopg://fengwang@localhost/postgres'
```

| Command | Observed final result |
| --- | --- |
| `uv run alembic heads` | `0047_pr2_18_novelty_prior_art (head)`; exit 0 |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0 |
| `uv run ruff check .` | All checks passed; exit 0 |
| `uv run ruff format --check .` | 507 files already formatted; exit 0 |
| `uv run pytest tests/unit tests/architecture tests/test_architecture.py` | 2,056 passed, 5 warnings in 38.20s; exit 0 |
| `uv run pytest tests/integration/phase2/test_pr2_17_authorship_schema.py` | 38 passed, 51 warnings in 17.08s; exit 0 |
| `git diff --check HEAD` | No output; exit 0 |

The affected PostgreSQL regression command is:

```sh
uv run pytest tests/integration/phase2/test_pr2_17_*.py \
  tests/integration/phase2/test_pr2_18_*.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_revision_action.py
```

Final result of that command: **255 passed, 420 warnings in 159.42s
(0:02:39); exit 0; 0 failures, 0 errors, 0 skips**. Warnings are inherited
Alembic `path_separator` deprecations. Pyright printed an available-version
notice separately from its zero diagnostic warning count.

## Empty database round trip

The following `uv run python -` check passed, exit 0. It verifies upgrade from
empty, downgrade of PR2-18 while retaining PR2-17, re-upgrade, and complete
empty-history downgrade to base. Five assertions verify revisions and catalog.

```python
import os
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database

with disposable_database("researchbase_pr212_test_") as url:
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0047_pr2_18_novelty_prior_art"
    command.downgrade(cfg, "0046_pr2_17_authorship")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0046_pr2_17_authorship"
        assert conn.execute(text("SELECT to_regclass('authorship_snapshots') IS NOT NULL AND to_regclass('novelty_assessments') IS NULL")).scalar_one()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM alembic_version")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename<>'alembic_version'")).scalar_one() == 0
    engine.dispose()
```

## Earlier failures and handoff limits

Earlier unit/architecture checks reported 2 failed / 2,054 passed (stale parent
expectations), then 1 failed / 2,055 passed (formatting those corrected assertions).
The final 2,056-pass run supersedes them. An initial conflict-resolution script
matched beyond marker lines; its damaged output was restored from the original
merge stages and resolved again before the passing checks.

The first PostgreSQL regression command used Unix socket URLs instead of the TCP
URLs above: 3 failed, 133 passed, 119 errors, 235 warnings in 92.12s. Existing
fixtures percent-encode `/tmp` and pass it unescaped to ConfigParser, producing
invalid-interpolation setup errors. No fixture behavior was changed; final runs
use TCP. The first TCP regression reported 1 failed, 254 passed, 420 warnings in
160.50s: the stale PR2-17 rollback-head assertion. A focused reproduction
reported 1 failed / 4 passed, and the corrected schema suite then passed all
38 tests. The affected PostgreSQL command above was rerun after correction.

Conflict markers are removed from working files. Staging the resolved files and
migration rename failed because the sandbox forbids `.git/index.lock` writes:
`fatal: Unable to create .../.git/index.lock: Operation not permitted`.
Consequently the Git status still lists 14 `DA` files (staged deletions with
working-tree re-additions), and the migration rename is present only in the
working tree. `git ls-files -u` is empty. No commit, push, or branch was created.

The initial handoff deliberately did not run the full suite, per the original
instruction. The reviewer subsequently authorized a full run. The loop's first
full run failed: **8 failed, 2,545 passed, 447 skipped, 2,461 errors**, 7 warnings
in 58.08s. The focused results above never established full-suite success.
See the remediation below for the actual root cause and subsequent full result.


## Reviewer remediation

The loop's first error was `test_approval_atomic_history_and_replay`, through
`conclusion_env -> phase2_database_url -> disposable_database -> admin_url`:

```text
tests/disposable_postgres.py:34
value = None
pytest.fail("Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL")
```

The check's inline `DATABASE_URL=... RB_TEST_ADMIN_URL=...` assignments applied
only to `uv run pyright`. They did not apply to subsequent commands after `&&`.
The pytest process had no exported database variables. Its integration setup
errors were missing `RB_TEST_ADMIN_URL` or `KeyError: 'DATABASE_URL'`, rather than
migration, role, or connectivity failures. PostgreSQL 18.6 was reachable using
the requested `researchbase` credentials.

Reproduction without the exports:
`uv run pytest -o addopts='' -q -rfE -p no:cacheprovider -x`:
**82 passed, 18 skipped, 2 warnings, 1 error in 4.17s; exit 1**.
The first trace is preserved in `.data/pr21718-missing-env-first-error.txt`.
An earlier diagnostic with both variables set was interrupted after **131 passed,
99 warnings in 61.05s; exit 2**, to avoid duplicating the entire long full run;
that interruption is not a passing suite result.

Each of the eight reported failures has the same environment root cause:

| Failed test | Exception in loop log |
| --- | --- |
| `test_phase2_command_transaction_uses_serializable_isolation` | `KeyError: 'DATABASE_URL'` |
| `test_upgrade_to_pr212_and_empty_downgrade[base]` | missing `RB_TEST_ADMIN_URL` |
| `test_upgrade_to_pr212_and_empty_downgrade[0018_current_pointer_same_parent_integrity]` | missing `RB_TEST_ADMIN_URL` |
| `test_database_is_dropped_after_setup_failure` | missing `RB_TEST_ADMIN_URL` |
| `test_optional_identity_mismatch_fails_before_database_creation[RB_TEST_ADMIN_USER]` | missing `RB_TEST_ADMIN_URL` |
| `test_optional_identity_mismatch_fails_before_database_creation[RB_TEST_ADMIN_PORT]` | missing `RB_TEST_ADMIN_URL` |
| `test_optional_identity_mismatch_fails_before_database_creation[RB_TEST_ADMIN_DATA_DIRECTORY]` | missing `RB_TEST_ADMIN_URL` |
| `test_optional_identity_mismatch_fails_before_database_creation[RB_TEST_ADMIN_SYSTEM_ID]` | missing `RB_TEST_ADMIN_URL` |

Added `RB_TEST_ADMIN_URL` beside `DATABASE_URL` in CI's job-level environment,
so both reach pytest. Kept the fixtures' explicit local-admin opt-in intact.

The lineage filename is exactly
`migrations/versions/0046_pr2_17_authorship_preparation.py`; its revision is
`0046_pr2_17_authorship`. The PR2-18 filename is exactly
`migrations/versions/0047_pr2_18_novelty_prior_art.py`.
`uv run pytest -o addopts='' -q tests/architecture/test_import_boundaries.py -k migration_lineage`
reported **1 passed, 12 deselected in 0.01s; exit 0**. A prior mistyped node
selector matched no tests; it was not counted as PASS.

Retried `git add` on all 14 resolved paths and the new migration filename:
**exit 128**, `.git/index.lock: Operation not permitted`. The current sandbox
makes `.git` read-only and disallows permission escalation. `git ls-files -u`
has no output (no unmerged index entries); `git status --short` still contains
14 `DA` paths (staged deletion plus unstaged re-addition). This index finding
remains open: a caller with Git write permission must stage the resolved files.

The requested full check is run with explicit shell-wide exports before the
otherwise unchanged check:

```sh
export UV_CACHE_DIR="$PWD/.data/uv-cache"
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
! git grep -nE '^(<<<<<<<|>>>>>>>) ' -- . ':!.pipeline' && test $(uv run alembic heads | wc -l) -eq 1 && DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Static portion observed: no conflict-marker matches, one Alembic head,
Pyright 0 errors/warnings/informations, Ruff format 507 files already formatted,
Ruff lint all checks passed. Full pytest output is preserved at
`.data/pr21718-full-pytest.txt`. **The full check exited 0**.
Full pytest: **5,460 passed, 1 skipped, 3,106 warnings in 5,126.80s
(1:25:26); 0 failures, 0 errors**. All eight formerly failing tests are included
in this passing run. The remaining skip is the explicitly opt-in HG1 live check;
no database suites were skipped for missing environment variables. Warnings are
the inherited Alembic `path_separator` deprecations and existing
`TestOwnedInterruption` collection warning.

This is a passing verification command with the URLs exported to the whole shell;
the bare inline assignments in the reviewer's original chain still only scope
those URLs to Pyright. A caller must preserve the exports shown above, as CI now
does through its job-level environment. Git staging remains blocked, so the
integration's index finding is not declared resolved and no overall gate success
is claimed.

## Raw evidence for the second reviewer follow-up

This follow-up changes evidence documentation only. The following full-suite tail
is copied verbatim from the actual completed exported check in the preceding
turn, `.data/pr21718-full-pytest.txt`; it is not a new full-suite run. The full
command was the exported chain shown above. Its process completion was observed
through tool session `10461`, which returned `exit_code: 0` after pytest finished.
Both database variables were exported before running the entire chain. No test
code or implementation changed after that successful run.

### Captured full-suite output tail

```text
tests/integration/phase2/test_pr2_15_decision.py: 108 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 13 warnings
tests/integration/phase2/test_pr2_17_authorship.py: 8 warnings
tests/integration/phase2/test_pr2_17_authorship_concurrency.py: 26 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 51 warnings
tests/integration/phase2/test_pr2_18_concurrency.py: 22 warnings
tests/integration/phase2/test_pr2_18_novelty.py: 4 warnings
tests/integration/phase2/test_pr2_18_prior_art.py: 13 warnings
tests/integration/phase2/test_pr2_18_replay.py: 4 warnings
tests/integration/phase2/test_pr2_18_schema.py: 29 warnings
tests/integration/phase2/test_pr2_18_search_coverage.py: 9 warnings
tests/integration/phase2/test_revision_action.py: 157 warnings
tests/integration/phase2/test_task12_schema_migration.py: 29 warnings
tests/integration/test_pr11r2_migration.py: 2 warnings
tests/integration/test_pr18_hardening.py: 2 warnings
tests/unit/phase2/test_pr2_04_r8a_host_topology.py: 1 warning
tests/unit/phase2/test_pr2_04_static_acceptance.py: 1 warning
tests/unit/test_ci_migration_head.py: 1 warning
tests/unit/test_task12_migration_history.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
5460 passed, 1 skipped, 3106 warnings in 5126.80s (1:25:26)
```

Captured command-process completion (tool metadata, not inferred from the summary):

```json
{"exit_code": 0, "output": ""}
```

### Original PR2-18 migration versus integrated migration

The original migration bytes were recovered from the existing Git blob
`e612c01ed64f0a556dccf79e8162c5a39631d7b3` with `git cat-file blob`.
The comparison input is an original Git object, not a newly invented baseline:

```sh
git cat-file blob e612c01ed64f0a556dccf79e8162c5a39631d7b3 > .data/original-0046_pr2_18_novelty_prior_art.py
git diff --no-index .data/original-0046_pr2_18_novelty_prior_art.py migrations/versions/0047_pr2_18_novelty_prior_art.py
```

Actual output (exit 1 is the expected `git diff` result when differences exist).
Blank context-line trailing spaces are omitted in this Markdown rendering;
`.data/pr21718-migration.diff` preserves the exact raw output:

```diff
diff --git a/.data/original-0046_pr2_18_novelty_prior_art.py b/migrations/versions/0047_pr2_18_novelty_prior_art.py
index e612c01..bceb4a8 100644
--- a/.data/original-0046_pr2_18_novelty_prior_art.py
+++ b/migrations/versions/0047_pr2_18_novelty_prior_art.py
@@ -3,8 +3,8 @@
 # ruff: noqa: E501
 from alembic import op

-revision = "0046_pr2_18_novelty_prior_art"
-down_revision = "0045_pr2_16_basic_approval"
+revision = "0047_pr2_18_novelty_prior_art"
+down_revision = "0046_pr2_17_authorship"
 branch_labels = None
 depends_on = None


```

Only the two revision assignments differ. The module docstring, imports, DDL,
upgrade function, downgrade function and all other bytes are unchanged.

### Fresh CLI migration cycle against empty PostgreSQL

This cycle was executed in this follow-up, using the supplied `researchbase`
credentials through `RB_TEST_ADMIN_URL` and a random disposable database.
An SQLAlchemy catalog inspection asserted the database initially had no tables;
PostgreSQL reported `18.6 (Homebrew)`. Each displayed command is the actual CLI
invocation. After the PR2-18 downgrade, SQL checks verified the PR2-17 revision
and authorship tables remained, while the novelty tables were absent. After the
final base downgrade, only an empty `alembic_version` table remained.
The entire wrapper returned `CYCLE_EXIT_CODE=0`.

Full captured output:

```text
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_1ebd1ae356684863a1bc12a35be2d566
Initial database: empty; PostgreSQL 18.6 (Homebrew)
$ uv run alembic heads
0047_pr2_18_novelty_prior_art (head)
EXIT_CODE=0
$ uv run alembic upgrade head
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
EXIT_CODE=0
$ uv run alembic current
0047_pr2_18_novelty_prior_art (head)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
EXIT_CODE=0
$ uv run alembic downgrade 0046_pr2_17_authorship
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0047_pr2_18_novelty_prior_art -> 0046_pr2_17_authorship, Immutable first-slice coverage, prior art and inconclusive assessments.
EXIT_CODE=0
$ uv run alembic current
0046_pr2_17_authorship
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
EXIT_CODE=0
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
EXIT_CODE=0
$ uv run alembic current
0047_pr2_18_novelty_prior_art (head)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
EXIT_CODE=0
$ uv run alembic downgrade base
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0047_pr2_18_novelty_prior_art -> 0046_pr2_17_authorship, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running downgrade 0046_pr2_17_authorship -> 0045_pr2_16_basic_approval, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running downgrade 0045_pr2_16_basic_approval -> 0044_pr2_15_revision_action, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running downgrade 0044_pr2_15_revision_action -> 0043_pr2_04_schema_contract, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running downgrade 0043_pr2_04_schema_contract -> 0042_pr2_15_minimal_decision, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running downgrade 0042_pr2_15_minimal_decision -> 0041_pr2_15_review_coordination, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running downgrade 0041_pr2_15_review_coordination -> 0040_pr2_14_initial_internal_review, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running downgrade 0040_pr2_14_initial_internal_review -> 0039_pr2_13_citation_rebinding_guard, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running downgrade 0039_pr2_13_citation_rebinding_guard -> 0038_pr2_13_artifact_placement, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running downgrade 0038_pr2_13_artifact_placement -> 0037_pr2_13_claim_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running downgrade 0037_pr2_13_claim_placement -> 0036_pr2_13_citation_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running downgrade 0036_pr2_13_citation_placement -> 0035_pr2_12_publication_draft, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running downgrade 0035_pr2_12_publication_draft -> 0034_pr2_10_exact_transcript_binding, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running downgrade 0034_pr2_10_exact_transcript_binding -> 0033_pr2_11_r2_scientific_conclusion, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running downgrade 0033_pr2_11_r2_scientific_conclusion -> 0032_pr2_10_discussion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running downgrade 0032_pr2_10_discussion -> 0031_m3_snapshot_relation_cardinality, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running downgrade 0031_m3_snapshot_relation_cardinality -> 0030_literature_evidence, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running downgrade 0030_literature_evidence -> 0029_metadata_observations, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running downgrade 0029_metadata_observations -> 0028_provider_cancellation, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running downgrade 0028_provider_cancellation -> 0027_pr2_04_hash_scheme_guards, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running downgrade 0027_pr2_04_hash_scheme_guards -> 0026_pr2_04_p1_contract_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running downgrade 0026_pr2_04_p1_contract_guards -> 0025_pr2_04_reservation_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running downgrade 0025_pr2_04_reservation_guards -> 0024_literature_search_execution, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running downgrade 0024_literature_search_execution -> 0023a_search_plan_review_guards, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running downgrade 0023a_search_plan_review_guards -> 0023_literature_search_plan, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running downgrade 0023_literature_search_plan -> 0022_source_version_and_merge_lineage, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running downgrade 0022_source_version_and_merge_lineage -> 0021a_source_merge_gov_guards, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running downgrade 0021a_source_merge_gov_guards -> 0021_source_merge_governance_bridge, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running downgrade 0021_source_merge_governance_bridge -> 0020_literature_source_identity, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running downgrade 0020_literature_source_identity -> 0019_phase2_bootstrap_membership, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running downgrade 0019_phase2_bootstrap_membership -> 0018_current_pointer_same_parent_integrity, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running downgrade 0018_current_pointer_same_parent_integrity -> 0017_persisted_canonical_enum_normalization, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running downgrade 0017_persisted_canonical_enum_normalization -> 0016_pr17d_history_protection, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running downgrade 0016_pr17d_history_protection -> 0015_governance_audit, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running downgrade 0015_governance_audit -> 0014_claim_evidence, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running downgrade 0014_claim_evidence -> 0013_statistical_result_legacy_input_precheck, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running downgrade 0013_statistical_result_legacy_input_precheck -> 0012_statistical_result_input_guard, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running downgrade 0012_statistical_result_input_guard -> 0011_statistical_result, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running downgrade 0011_statistical_result -> 0010_measurement, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running downgrade 0010_measurement -> 0009_run_input_seal_fix, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running downgrade 0009_run_input_seal_fix -> 0008_run_core, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running downgrade 0008_run_core -> 0007_metric_definition, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running downgrade 0007_metric_definition -> 0006_artifact_version, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running downgrade 0006_artifact_version -> 0005_dataset_snapshot, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running downgrade 0005_dataset_snapshot -> 0004_experiment_spec, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running downgrade 0004_experiment_spec -> 0003_research_question_hypothesis, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running downgrade 0003_research_question_hypothesis -> 0002_actor_project_workspace, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running downgrade 0002_actor_project_workspace -> 0001_empty, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running downgrade 0001_empty -> , Empty PR-00 migration proving Alembic connectivity.
EXIT_CODE=0
$ uv run alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
EXIT_CODE=0
PASS: empty -> head -> PR2-17 -> head -> base; all CLI commands exited 0
DISPOSABLE_DROPPED: researchbase_pr212_test_1ebd1ae356684863a1bc12a35be2d566

CYCLE_EXIT_CODE=0
```

Existing pytest coverage also includes:

- `tests/integration/phase2/test_pr2_17_authorship_schema.py::test_install_upgrade_exact_catalog_and_one_head` (parameterized empty and predecessor upgrades).
- `tests/integration/phase2/test_pr2_17_authorship_schema.py::test_empty_downgrade_roundtrip`.
- `tests/integration/phase2/test_pr2_17_authorship_schema.py::test_nonempty_downgrade_refuses`.
- `tests/integration/phase2/test_pr2_18_schema.py::test_catalog_and_empty_downgrade`.
- `tests/integration/phase2/test_pr2_18_schema.py::test_populated_upgrade_cannot_be_lost_during_downgrade`.

### Staging remains blocked; actual status is not clean

Retried the requested `git add -A -- <the 14 paths>` in this follow-up. Actual
output, with command exit 128:

```text
fatal: Unable to create '/Users/fengwang/Documents/ResearchBaseProject/.git/index.lock': Operation not permitted
```

The sandbox declares `.git` read-only; permission escalation is unavailable.
`git ls-files -u` prints nothing, but the requested status filter still prints:

```sh
git status --short | grep -E '^(DA|AD|UU|DU|UD)'
```

```text
DA .github/workflows/ci.yml
DA src/researchbase/application/ports.py
DA src/researchbase/persistence/uow.py
DA tests/architecture/test_basic_approval.py
DA tests/architecture/test_import_boundaries.py
DA tests/fixtures/phase2_static_baseline.json
DA tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py
DA tests/integration/phase2/test_pr2_03_review_guards.py
DA tests/integration/phase2/test_pr2_04_execution_migration.py
DA tests/integration/phase2/test_pr2_04_migration_coverage.py
DA tests/integration/phase2/test_pr2_15_decision_schema.py
DA tests/integration/phase2/test_revision_action.py
DA tests/unit/phase2/test_pr2_04_r8a_host_topology.py
DA tests/unit/test_task12_migration_history.py
```

This P1 finding remains open. A terminal with Git write access must run the
requested staging command; a clean index or overall acceptance is not claimed.
No commit, push, or branch was created.


## Latest reviewer follow-up: original-slice provenance and fresh check

The latest supplied loop log, `.pipeline/runs/t29_merge_lanes/20261014-184151/r3_check.txt`,
again has `RB_TEST_ADMIN_URL` absent in the first failing fixture. Its first
error is `test_approval_atomic_history_and_replay`; `tests/disposable_postgres.py:34`
reports `value = None` and `Set RB_TEST_ADMIN_URL explicitly to a disposable local
PostgreSQL admin URL`. The command-local assignments before Pyright do not set
pytest's environment. The fixture's explicit admin opt-in is retained. The fresh
check below exports both supplied URLs to the shell before executing the exact
check chain; the same exports must reach any subsequent loop invocation.

### Shared-code provenance

The original PR2-18 commit is available in the original lane checkout:

```sh
git -C .pipeline/work/lane2 show -s --format='%H%n%s' dd3d4b4
```

```text
dd3d4b445ecb9d5ee71903c02c90961e13c6fa27
Implement the PR2-18 first slice (owner-approved 2026-10-14)
```

For each of the four questioned files, the bytes obtained by
`git -C .pipeline/work/lane2 show dd3d4b445ecb9d5ee71903c02c90961e13c6fa27:<path>`
were compared with the working file using a Python `assert current == original`.
All four assertions passed (exit 0). The original commit's blob IDs are:

```text
BYTE_IDENTICAL src/researchbase/cli/common.py original_blob=986c796ab493d252e89828926098534021d52d73
BYTE_IDENTICAL src/researchbase/cli/errors.py original_blob=f137e523fdc2d893dbcf6f0ff8109f4b311aa1ad
BYTE_IDENTICAL src/researchbase/cli/output.py original_blob=e0b492504aff02c68b0f0b68f407a104a726be59
BYTE_IDENTICAL src/researchbase/api/routes.py original_blob=d191438b9b9458870275e754a48e18e4b7c8e360
```

Thus the optional invocation parameter, novelty-only exit 1 selection, and
`TimeScope` serialization are original PR2-18 implementation, not integration
edits. The invocation default stays 70, and only the novelty command helpers
explicitly pass `INTERNAL_ERROR_EXIT_CODE`. Contract §11.2 requests novelty's
sanitized exit-1 fallback; §11.3 pins the `TimeScope` JSON keys `from` and `through`.

PR2-17 S1 has no CLI transport or PR2-17 CLI exit-code tests. Its
`test_exact_four_methods_and_no_future_transport` architecture test explicitly
requires that omission. The existing CLI exit-70 tests and the PR2-18 exit-1
transport tests were run together with PR2-17 unit and boundary coverage:

```sh
UV_CACHE_DIR="$PWD/.data/uv-cache" uv run pytest -o addopts='' -q -rfE -p no:cacheprovider tests/unit/test_pr16_cli_errors.py tests/unit/test_pr16_cli_transport_matrix.py tests/unit/phase2/test_pr2_18_transports.py tests/unit/phase2/test_pr2_17_authorship.py tests/architecture/test_pr2_17_boundaries.py
```

```text
........................................................................ [ 72%]
............................                                             [100%]
100 passed in 2.92s

CLI_CHECK_EXIT_CODE=0
```

Exit-70 assertions passed in
`test_unexpected_application_error_is_controlled_and_does_not_leak_details` and
`test_cli_invocation_recovers_after_success_error_transport_and_internal_error`.
Novelty's `test_unexpected_failures_are_sanitized` asserted exit 1 and
`INTERNAL_ERROR`, and passed.

### Migration comparison against the original commit

This comparison extracts the migration directly from that PR2-18 commit:

```sh
git -C .pipeline/work/lane2 show dd3d4b445ecb9d5ee71903c02c90961e13c6fa27:migrations/versions/0046_pr2_18_novelty_prior_art.py > .data/original-0046_pr2_18_novelty_prior_art.py
git diff --no-index .data/original-0046_pr2_18_novelty_prior_art.py migrations/versions/0047_pr2_18_novelty_prior_art.py
```

```diff
diff --git a/.data/original-0046_pr2_18_novelty_prior_art.py b/migrations/versions/0047_pr2_18_novelty_prior_art.py
index e612c01..bceb4a8 100644
--- a/.data/original-0046_pr2_18_novelty_prior_art.py
+++ b/migrations/versions/0047_pr2_18_novelty_prior_art.py
@@ -3,8 +3,8 @@
 # ruff: noqa: E501
 from alembic import op

-revision = "0046_pr2_18_novelty_prior_art"
-down_revision = "0045_pr2_16_basic_approval"
+revision = "0047_pr2_18_novelty_prior_art"
+down_revision = "0046_pr2_17_authorship"
 branch_labels = None
 depends_on = None

```

The diff exits 1 because those two assignments differ; no DDL or docstring line
differs. Blank context lines above omit the diff's single trailing space to keep
Markdown whitespace checks clean. The migration blob in the source commit is
`e612c01ed64f0a556dccf79e8162c5a39631d7b3`, confirming the previous blob comparison.

### Head expectations and baseline origin

The PR2-17 schema test continues to upgrade explicitly to `REVISION` (`0046`)
and compare exactly the PR2-17 table delta. Its two `0047` assertions test the
repository's current sole head and the starting head preserved by a rejected
transactional downgrade. Replacing those assertions with `REVISION` would test
the wrong state after integration. Shared-head centralization is left as the
reviewer's optional follow-up; the explicit pinned expectations are retained.

`baseline_commit` intentionally remains
`b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` ("Fix the four failing architecture tests").
It is the historical static-debt/diff comparison origin, not a migration head.
`test_pr2_04_static_acceptance.py` pins that origin, verifies it is an ancestor,
and compares diagnostics and changed files against it. `git merge-base
--is-ancestor b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff HEAD` exited 0. Only the
separate `migration_head` field advances to `0047`; moving the baseline commit
would change the static regression scope.

### Index restriction remains open

The fresh `git add -A` attempt exited 128:

```text
fatal: Unable to create '/Users/fengwang/Documents/ResearchBaseProject/.git/index.lock': Operation not permitted
```

`ls -ld .git/index.lock` reports `No such file or directory`: there is no stale
lock to clear. This session's filesystem policy explicitly makes `.git`
read-only and disallows escalation. The required status filter
`git status --short | grep -E '^(DA|AA|UU|DU|UD)'` still prints the same 14 `DA`
paths listed above. This finding is not resolved; staging requires Git write
access outside this restricted session. No overall integration gate is claimed.

### Historical full-check handoff

The interrupted attempt started a full check whose partial output remains in
`.data/pr21718-review4-check.txt`. It contains no completed result and establishes
no PASS. The restart instruction supersedes that attempt: run only focused
checks here, and use the loop's subsequent check as current full-suite evidence.


## Current restart verification — 2026-10-14

Reviewed and retained the existing working-tree integration. No runtime or test
behavior changes were needed in this restart. Corrected the migration-function
checksum description/value above and marked the interrupted full-check handoff
and older PR2-18 evidence as historical. There are no unresolved Git index
entries (`git ls-files -u` returned no output) or conflict markers in source,
tests, migrations or CI. Existing staged/unstaged changes remain in place;
no staging, branch creation, commit or push was performed in this restart.

All commands used the repository-local uv cache. `DATABASE_URL` was already
exported by the environment; `RB_TEST_ADMIN_URL` was explicitly exported for
focused pytest and migration verification:

```sh
export UV_CACHE_DIR="$PWD/.data/uv-cache"
export DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase'
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
```

| Exact command | Observed result |
| --- | --- |
| `uv run alembic heads` | `0047_pr2_18_novelty_prior_art (head)`; one head; exit 0 |
| `uv run ruff check .` | All checks passed; exit 0 |
| `uv run ruff format --check .` | 507 files already formatted; exit 0 |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0 |
| `uv run pytest tests/unit tests/architecture tests/test_architecture.py` | 2,056 passed, 5 warnings in 39.86s; exit 0 |
| Affected PostgreSQL command below | 255 passed, 420 warnings in 166.01s (0:02:46); exit 0 |
| `git diff --check HEAD` | No output; exit 0 |

Exact affected PostgreSQL command:

```sh
uv run pytest tests/integration/phase2/test_pr2_17_*.py \
  tests/integration/phase2/test_pr2_18_*.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_revision_action.py
```

Both pytest runs had **0 failures, 0 errors, 0 skips**. Warnings were inherited
Alembic `path_separator` deprecations. Pyright's available-version notice is
separate from its zero diagnostic warnings. Raw results are retained in
`.data/pr21718-restart-unit-architecture.txt` and
`.data/pr21718-restart-postgres.txt`.

Re-executed the five-assertion `uv run python -` empty-database round trip printed
in the earlier “Empty database round trip” section, with an additional server
version read. It reported PostgreSQL **18.6 (Homebrew)** and passed upgrade from
empty to head, downgrade to PR2-17 preserving authorship tables, re-upgrade, and
complete downgrade to base with no remaining business tables. The random
disposable database was dropped. Exit 0; output is retained in
`.data/pr21718-restart-migration.txt`.

A fresh byte comparison against original PR2-18 blob
`e612c01ed64f0a556dccf79e8162c5a39631d7b3` passed: replacing only the two revision
assignments reproduces the current migration byte-for-byte. PR2-17's migration
is unchanged from HEAD. Four shared CLI/API transport files also passed byte
comparison against the original slice blobs listed in the historical review
section above. Both Python verification commands exited 0.

**Full suite: not run in this restart**, as explicitly instructed. The loop's
subsequent PostgreSQL check supplies current full-suite evidence; no gate success
is claimed from older results or incomplete logs.
