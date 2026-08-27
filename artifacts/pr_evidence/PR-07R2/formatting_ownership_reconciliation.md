# Formatting ownership reconciliation

The exact current repository-wide result is `8 files would be reformatted`:

| Path | PR-07 | PR-07R | Owned | Result | Classification |
|---|---|---|---|---|---|
| `migrations/versions/0004_experiment_spec.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/integration/test_pr04_application.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/integration/test_pr04_schema.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/integration/test_pr05_application.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/integration/test_pr05_schema.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/integration/test_pr06_application.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/integration/test_pr06_schema.py` | NO | NO | NO | FAIL | untouched baseline |
| `tests/unit/domain/test_pr05_experiment.py` | NO | NO | NO | FAIL | untouched baseline |

Explicit correction: `tests/contracts/version_contract.py` is PR-07 NO / PR-07R YES /
owned YES / PASS. It was modified by PR-07R and was formatted during R2. The other
PR-07/PR-07R-owned Python files—0006 migration, commands, models, repositories, and PR-07
tests—also pass the scoped check. The scoped command reports `8 files already formatted`.

The prior claim that the contract helper was inherited unchanged is corrected. No
unrelated historical file was reformatted by R2.
