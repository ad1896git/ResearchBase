# Fingerprint and Git inventory reconciliation

The accepted PR-10 baseline is `41a8863` (`41a886344f277e84c7d63891c5b4351262329e30`).
The reviewed PR-10R implementation/test head is `9c5a87a`
(`9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d`). The remediation commits created
directly on that baseline are `35efe3d` and `9c5a87a`. No prior PR-10 commit was
amended, rebased, or rewritten.

The final fingerprint records three distinct meanings:

- `reviewed_implementation_head`: the PR-10R code/test commit reviewed for behavior;
- `evidence_payload_commit`: the commit that first contains the complete PR-10R
  evidence payload;
- `current_head_at_review`: the HEAD observed when the evidence payload was reviewed.
  In this package, the evidence payload commit is also that reviewed current head
  (`7db0696e0be713b38d5627f1a1072f7d95d88f0c`); the final evidence-only metadata
  commit that follows is reported as the ending repository HEAD, not falsely folded
  into the implementation head.

The remediation range is derived directly from
`git diff --name-only 41a8863..9c5a87a` and contains exactly:

- `tests/integration/test_pr10_application.py`
- `tests/unit/domain/test_pr10_measurement.py`

The PR-10R `changed_files.txt` records this exact set. Evidence documents are
separately tracked payload files and are not misrepresented as implementation files.

Result: PASS. `PR10-REV-004` is closed.
