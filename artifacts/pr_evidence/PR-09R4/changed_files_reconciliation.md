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

## `0feba30..044c72a` — 21 files

Classification: production 0; tests 1; migration 0; evidence 20.

```text
M	artifacts/pr_evidence/PR-09R3/commands_and_results.md
M	artifacts/pr_evidence/PR-09R3/concurrent_start_finish_report.md
M	artifacts/pr_evidence/PR-09R3/evidence_reconciliation.md
M	artifacts/pr_evidence/PR-09R3/finding_disposition.md
M	artifacts/pr_evidence/PR-09R3/harness_fingerprint.json
M	artifacts/pr_evidence/PR-09R3/test_report.md
M	artifacts/pr_evidence/PR-09R3/unresolved_findings.md
A	artifacts/pr_evidence/PR-09R4/architecture_review.md
A	artifacts/pr_evidence/PR-09R4/changed_files.txt
A	artifacts/pr_evidence/PR-09R4/changed_files_reconciliation.md
A	artifacts/pr_evidence/PR-09R4/code_review.md
A	artifacts/pr_evidence/PR-09R4/commands_and_results.md
A	artifacts/pr_evidence/PR-09R4/concurrent_finish_winner_report.md
A	artifacts/pr_evidence/PR-09R4/evidence_reconciliation.md
A	artifacts/pr_evidence/PR-09R4/final_head_fingerprint_report.md
A	artifacts/pr_evidence/PR-09R4/finding_disposition.md
A	artifacts/pr_evidence/PR-09R4/harness_fingerprint.json
A	artifacts/pr_evidence/PR-09R4/remediation_summary.md
A	artifacts/pr_evidence/PR-09R4/test_report.md
A	artifacts/pr_evidence/PR-09R4/unresolved_findings.md
M	tests/integration/test_pr09_application.py
```

This is the complete R4 range at the evidence-package commit. Any later
fingerprint-only metadata commit is classified as evidence-only in the final
Git-derived inventory.

The actual final R4 commit is `602f224`. The final metadata correction range
is `044c72a..602f224`, exactly five evidence-only files:

```text
M	artifacts/pr_evidence/PR-09R4/changed_files.txt
M	artifacts/pr_evidence/PR-09R4/changed_files_reconciliation.md
M	artifacts/pr_evidence/PR-09R4/commands_and_results.md
M	artifacts/pr_evidence/PR-09R4/final_head_fingerprint_report.md
M	artifacts/pr_evidence/PR-09R4/harness_fingerprint.json
```

Therefore the complete `0feba30..602f224` range is 21 files: one test and 20
evidence/reporting files, with zero production and zero migration files. The
complete `9c47381..602f224` range is 45 files: one production, two tests, zero
migrations, and 42 evidence/reporting files. These counts and lists are
set-equal to the direct Git commands recorded in the R5 package.
