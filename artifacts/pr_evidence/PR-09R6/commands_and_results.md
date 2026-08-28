# PR-09R6 commands and results

All commands below were run from the ResearchBase repository.

## Baseline and scope

```text
git rev-parse HEAD
ecb9adaf6aebef73fb45d344197ea9e18ad37d9c

git diff --name-status 602f224..ecb9ada
M	artifacts/pr_evidence/PR-09R4/changed_files.txt
M	artifacts/pr_evidence/PR-09R4/changed_files_reconciliation.md
M	artifacts/pr_evidence/PR-09R4/final_head_fingerprint_report.md
M	artifacts/pr_evidence/PR-09R4/harness_fingerprint.json
A	artifacts/pr_evidence/PR-09R5/changed_files.txt
A	artifacts/pr_evidence/PR-09R5/code_review.md
A	artifacts/pr_evidence/PR-09R5/commands_and_results.md
A	artifacts/pr_evidence/PR-09R5/evidence_only_classification.md
A	artifacts/pr_evidence/PR-09R5/evidence_reconciliation.md
A	artifacts/pr_evidence/PR-09R5/final_head_verification.md
A	artifacts/pr_evidence/PR-09R5/final_range_inventory.md
A	artifacts/pr_evidence/PR-09R5/finding_disposition.md
A	artifacts/pr_evidence/PR-09R5/harness_fingerprint.json
A	artifacts/pr_evidence/PR-09R5/remediation_summary.md
A	artifacts/pr_evidence/PR-09R5/unresolved_findings.md

git diff -- src tests migrations
[empty]
```

The baseline range from the preserved R4 final HEAD to the reviewed R5 HEAD
contains evidence files only. The source/tests/migrations path diff is empty.

## Metadata checks

```text
python JSON parse of artifacts/pr_evidence/PR-09R5/harness_fingerprint.json
PASS

R4 final HEAD = 602f22478c6919f2611ff436b4199a81fa6b8297
R5 payload commit = 9c35e6a26bf0cdecf69081aa609f3a1aa54778ce
R5 current_head_at_review = ecb9adaf6aebef73fb45d344197ea9e18ad37d9c
PASS — semantic distinction preserved
```

The R6 evidence payload commit and final post-evidence HEAD are recorded by
the final Git verification in this package's completion report. The R5
`current_head_at_review` value remains the reviewed `ecb9ada` and is never
changed to a self-referential R6 commit.

## Repository checks

```text
git diff --check
PASS

uv run alembic current
PASS — 0009_run_input_seal_fix (head)
```
