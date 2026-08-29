# Evidence reconciliation

The original PR-11R evidence is retained and corrected in place only where
the later review exposed historical metadata or claim scope problems.

- `artifacts/pr_evidence/PR-11R/harness_fingerprint.json` now separates the
  reviewed PR-11R HEAD from PR-11R2 implementation/test and evidence commits.
- `artifacts/pr_evidence/PR-11R/migration_report.md` now records that `0012`
  was historically insufficient for legacy rows and points to the `0013`
  proof.
- `artifacts/pr_evidence/PR-11R/finding_disposition.md` and
  `unresolved_findings.md` preserve the later independent findings instead of
  erasing them.
- `artifacts/pr_evidence/PR-11R/changed_files.txt` was checked against the
  exact historical `9592b66..6675a744` Git diff.
- `artifacts/pr_evidence/PR-11R2/changed_files.txt` is checked against the
  exact `6675a744..HEAD` Git diff after evidence finalization.

No placeholder or invented SHA is used. The final evidence fingerprint
explicitly distinguishes payload commit, finalization commit, reviewed HEAD,
and post-evidence current HEAD.
