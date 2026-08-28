# Evidence-only classification

The decisive range is `044c72a..602f224`.

```text
M	artifacts/pr_evidence/PR-09R4/changed_files.txt
M	artifacts/pr_evidence/PR-09R4/changed_files_reconciliation.md
M	artifacts/pr_evidence/PR-09R4/commands_and_results.md
M	artifacts/pr_evidence/PR-09R4/final_head_fingerprint_report.md
M	artifacts/pr_evidence/PR-09R4/harness_fingerprint.json
```

Classification:

- production files: 0
- test files: 0
- migration files: 0
- evidence/reporting files: 5

The same classification is obtained by filtering the direct
`git diff --name-only 044c72a..602f224` result by `src/`, `tests/`,
`migrations/`, and `artifacts/pr_evidence/`. No source/test/migration path is
present. The range is set-equal to Git's five-file result.
