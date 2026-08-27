# Unresolved findings

The original PR-06 package incorrectly stated that no findings remained. Independent review recorded:

- PR06-REV-001 (P1): Application hash lacked independent black-box proof.
- PR06-REV-002 (P1): atomicity test did not observe a real INSERT before failure.
- PR06-REV-003 (P1): evidence overclaimed closure.
- PR06-REV-004 through PR06-REV-007 (P2): missing behavioral FK, trigger breadth, key-order, and missing-Dataset proofs.

PR-06R supplies fresh evidence for all seven findings. Their final dispositions are recorded in `artifacts/pr_evidence/PR-06R/finding_disposition.md`; no P0/P1/P2/P3 findings remain open after the remediation gates pass.

PR-07 remains out of scope and unauthorized by this execution.
