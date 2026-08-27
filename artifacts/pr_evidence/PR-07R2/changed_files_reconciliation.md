# Changed-files reconciliation

Git range used for the PR-07R remediation inventory:

```text
52a962a..8219672
git diff --name-only 52a962a..8219672
```

Exact changed-file count: 29.

The prior PR-07R `changed_files.txt` listed 12 files and omitted 17 files: the PR-07R
touches to `migrations/versions/0006_artifact_version.py`,
`src/researchbase/persistence/models.py`, and
`src/researchbase/persistence/repositories.py`, plus the 14 files in
`artifacts/pr_evidence/PR-07R/`. They were omitted because the prior inventory was manually
curated and treated formatting-only and evidence files as out of scope. The corrected
PR-07R inventory is now the exact 29-file Git output.

The R2 implementation/test range is separately:

```text
8219672..b7e7a53
```

and contains exactly `tests/contracts/version_contract.py` and
`tests/integration/test_pr07_application.py`; R2 evidence is generated after that commit.
