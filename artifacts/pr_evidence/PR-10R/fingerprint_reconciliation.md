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
- `current_head_at_review`: the final PR-10R HEAD observed by the independent
  review, after the PR-10R evidence metadata was finalized.

The Git-resolved PR-10R evidence payload commit is
`7db0696f4e687fe07c2f603ab37a24f620fd1281`. The PR-10R current HEAD at review is
`bffb95c3dc239219ec4c288eaa3c9991f7733f6c`. These are intentionally distinct:
the payload commit is an earlier evidence commit, while `bffb95c` is the final
PR-10R reviewed HEAD. The prior fingerprint incorrectly used an invalid SHA for
`7db0696` and incorrectly set `current_head_at_review` to the payload commit;
PR-10R2 corrects both fields.

The remediation range is derived directly from
`git diff --name-only 41a8863..9c5a87a` and contains exactly:

- `tests/integration/test_pr10_application.py`
- `tests/unit/domain/test_pr10_measurement.py`

The PR-10R `changed_files.txt` records this exact set. Evidence documents are
separately tracked payload files and are not misrepresented as implementation files.

The separate evidence-only range `7db0696..bffb95c` contains only the four
PR-10R evidence paths listed in `changed_files.txt`; it contains no source,
test, migration, or architecture file.

Result: PASS. `PR10-REV-004` is closed.
