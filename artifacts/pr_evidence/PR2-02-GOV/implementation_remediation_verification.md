# PR2-02-GOV implementation remediation verification

## Subjects and lineage

- Original implementation subject reviewed: `c00efe323a48da063885377f073e2b14c691b330`.
- Original evidence subject: `451a779d785ac9becff8cd5f4104c473a7d81cf5`.
- Remediation implementation subject: `e24f5804ce1c851a7b88cc6f51cefeac4813b00d`.
- Starting migration: `0020_literature_source_identity`.
- Current migration: `0021_source_merge_governance_bridge`, parent `0020_literature_source_identity`.
- Design pack: `89bbad27f1e636182fcd5d9804a33612a755502f`.
- Frozen Phase 1 tag object: `63f6a1d28afa79ce8620fc9233793ab9c40a515d`.
- `phase1-final-v4^{commit}` and frozen baseline both resolve to `d2400fbeca835c89bd802a4e9d647bda01cfd115`.
- PostgreSQL 18.6, image `postgres:18-alpine`, temporary container `researchbase-pr2-review-postgres`, host port `55439`. Each test fixture creates and drops an isolated database. URL pattern: `postgresql+psycopg://researchbase_test:<container-password>@127.0.0.1:55439/researchbase_pr2_test`. The local test command reads the password from the container environment; no secret is recorded here. Stop the temporary container after review with `docker stop researchbase-pr2-review-postgres`.

## Remediation results

The fresh implementation reviewer reported two P1 gaps and one P2:

1. Missing durable database checks for complete proposal basis, frozen project set and allowed lifecycle events.
2. Missing frozen CLI command surface.
3. Duplicate evidence artifact IDs were silently collapsed.

The remediation adds PostgreSQL deferred validation for proposal completeness, source/project/link set matching, identifier snapshot equality, exactly two source-basis rows, one submission event, event-to-proposal basis matching, event-specific required fields, legal terminal transitions, and all-project approval before consumption. A before-insert guard seals project, identifier, source-version, and evidence basis rows after submission. Revocation events must refer to an existing approval and an effective Human Owner at the recorded event time; supersession events must reference a replacement proposal for the same source pair. Repeated stale decisions preserve one stale event.

The CLI now exposes `literature merge-proposal create|show|approve|reject|revoke|supersede`, with command-dispatch tests for typed create/supersede/show/approve/reject operations. The Application rejects duplicate evidence IDs with `VALIDATION_ERROR` before repository lookup or hashing.

## Final verification on remediation subject

| Check | Command | Result |
|---|---|---|
| Full regression | `DATABASE_URL=postgresql+psycopg://researchbase_test:<container-password>@127.0.0.1:55439/researchbase_pr2_test uv run pytest -o addopts=''` | **PASS** — 1,872 passed, 2 skipped, 0 failed, 1,874 collected, 80.88 s |
| Governance PostgreSQL integration | `uv run pytest -q tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_02_gov_application.py` (isolated PostgreSQL URL as above) | **PASS** — 5 passed before the final authority check tightening; final full suite passed both governance modules after that tightening |
| Governance application after final authority check tightening | `uv run pytest -q tests/integration/phase2/test_pr2_02_gov_application.py` (isolated PostgreSQL URL as above) | **PASS** — 2 passed |
| CLI contract | `uv run pytest -q tests/unit/test_pr16_cli_contract.py::test_literature_merge_proposal_help_lists_frozen_governance_commands tests/unit/test_pr16_cli_contract.py::test_literature_merge_proposal_commands_forward_typed_operations` | **PASS** — 2 passed |
| Lint | `uv run ruff check .` | **PASS** — all checks passed |
| Type check | `uv run pyright` | **PASS** — 0 errors, 0 warnings, 0 informations |
| Raw formatter | `uv run ruff format --check .` | **FAIL as raw command** — exactly nine frozen inherited files would be reformatted; 236 files already formatted |
| Formatter gate | Current formatter failure set minus accepted baseline set | **PASS_VIA_BASELINE_DELTA** — empty difference; the 26 changed Python files pass scoped formatting |
| Migration lineage | `.venv/bin/alembic heads`; `.venv/bin/alembic history -r '0020:0021'` | **PASS** — unique head 0021, parent 0020 |
| Whitespace | `git diff --check` and committed diff check | **PASS** |
| Phase 1 non-drift | frozen Phase 1 path inspection plus full regression | **NO DRIFT** — no frozen Phase 1 semantic source or migration changed; Phase 1 checks passed |

The nine raw formatter failures are identical to the accepted baseline:

```text
migrations/versions/0004_experiment_spec.py
scripts/pr17dr_evidence.py
tests/integration/test_pr04_application.py
tests/integration/test_pr04_schema.py
tests/integration/test_pr05_application.py
tests/integration/test_pr05_schema.py
tests/integration/test_pr06_application.py
tests/unit/domain/test_pr05_experiment.py
tests/unit/test_pr17dr2_evidence.py
```

## Failure history retained for review

Earlier full-suite attempts encountered two single failures in existing PR2-01 concurrency tests:

- `test_concurrent_rejection_and_corrected_rebinding_preserve_one_live_identity`.
- `test_concurrent_same_key_add_verify_and_reject_replay_one_result` (`CONCURRENT_MODIFICATION` in the first observed failure).

The exact cases passed on isolated PostgreSQL reruns and both passed in the final full suite. The first fresh reviewer classified them as operational P2 observations without confirming invalid state. The pre-remediation and final full-suite results remain recorded in `implementation_verification.md` and this document.

## Review history

- Fresh design review: P0=0, P1=0, P2=1, readiness YES. Its key-scope P2 was addressed with command-specific receipt uniqueness.
- First fresh implementation review of `c00efe3`: P0=0, P1=2, P2=1, FAIL. All three findings received the single authorized remediation described above.

This evidence references implementation subject `e24f5804ce1c851a7b88cc6f51cefeac4813b00d`; it does not certify its own Git subject. The one fresh post-remediation review result is pending.
