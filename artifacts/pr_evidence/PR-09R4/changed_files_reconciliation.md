# Changed-files reconciliation

All inventories are generated with `git diff --name-status`.

## `9c47381..9e1bb85` — 31 files

Classification: production 1; tests 1; migration 0; evidence 29.

This is the PR-09R3 implementation plus evidence range. The exact list is
preserved in the prior R3 inventory and is regenerated in the R4 command log.

## `9e1bb85..0feba30` — 2 files

Classification: production 0; tests 0; migration 0; evidence 2.

```text
M	artifacts/pr_evidence/PR-09R3/changed_files.txt
M	artifacts/pr_evidence/PR-09R3/harness_fingerprint.json
```

This independently proves `0feba30` is evidence/reporting only.

## `0feba30..8a57413` — 1 file

Classification: production 0; tests 1; migration 0; evidence 0.

```text
M	tests/integration/test_pr09_application.py
```

## Cumulative `9c47381..0feba30` — 31 files

Classification: production 1; tests 1; migration 0; evidence 29. The exact
cumulative list is the union shown by the Git command in
`commands_and_results.md`; no migration is present.

The final `0feba30..PR-09R4_FINAL_HEAD` range is the R4 test file plus the R4
evidence/reconciliation files. Its exact post-commit list is recorded in
`changed_files.txt` and the final Git log.
