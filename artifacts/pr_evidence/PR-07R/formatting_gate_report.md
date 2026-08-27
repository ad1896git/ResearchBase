# Formatting gate report

The PR-07R remediation diff is the Git range `52a962a..8219672`. Its changed Python files
are owned for this gate, including files changed only by formatting. `tests/contracts/
version_contract.py` was modified by PR-07R and is therefore owned; it has now been
formatted and passes.

The current repository-wide `uv run ruff format --check .` reports these eight files:

```text
migrations/versions/0004_experiment_spec.py       PR-07 NO / PR-07R NO / owned NO / FAIL
tests/integration/test_pr04_application.py        PR-07 NO / PR-07R NO / owned NO / FAIL
tests/integration/test_pr04_schema.py             PR-07 NO / PR-07R NO / owned NO / FAIL
tests/integration/test_pr05_application.py        PR-07 NO / PR-07R NO / owned NO / FAIL
tests/integration/test_pr05_schema.py             PR-07 NO / PR-07R NO / owned NO / FAIL
tests/integration/test_pr06_application.py        PR-07 NO / PR-07R NO / owned NO / FAIL
tests/integration/test_pr06_schema.py             PR-07 NO / PR-07R NO / owned NO / FAIL
tests/unit/domain/test_pr05_experiment.py         PR-07 NO / PR-07R NO / owned NO / FAIL
```

The explicitly owned `tests/contracts/version_contract.py` classification is
PR-07 NO / PR-07R YES / owned YES / PASS. The other changed PR-07/PR-07R Python files
(`0006_artifact_version.py`, `commands.py`, `models.py`, `repositories.py`, and the PR-07
tests) also pass. The scoped result is `8 files already formatted`. The remaining eight
repository-wide failures are genuinely untouched baseline files. The prior statement that
the contract helper was inherited unchanged has been corrected.
