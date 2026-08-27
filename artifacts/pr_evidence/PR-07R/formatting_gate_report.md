# Formatting gate report

Initial repository-wide `uv run ruff format --check .` reported 15 files:

```text
migrations/versions/0004_experiment_spec.py       inherited baseline
migrations/versions/0006_artifact_version.py      PR-07-owned
src/researchbase/application/commands.py          PR-07-owned
src/researchbase/persistence/models.py            PR-07-owned
src/researchbase/persistence/repositories.py      PR-07-owned
tests/contracts/version_contract.py               inherited PR-03 baseline
tests/integration/test_pr04_application.py        inherited baseline
tests/integration/test_pr04_schema.py             inherited baseline
tests/integration/test_pr05_application.py        inherited baseline
tests/integration/test_pr05_schema.py             inherited baseline
tests/integration/test_pr06_application.py        inherited baseline
tests/integration/test_pr06_schema.py             inherited baseline
tests/integration/test_pr07_application.py         PR-07-owned
tests/integration/test_pr07_schema.py              PR-07-owned
tests/unit/domain/test_pr05_experiment.py         inherited baseline
```

After formatting only PR-07-owned files, the scoped result is `7 files already formatted`.
The repository-wide result is truthfully `9 files would be reformatted`, all inherited
baseline debt. No unrelated historical files were modified.
