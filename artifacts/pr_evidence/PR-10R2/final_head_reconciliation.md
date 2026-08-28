# Final-head reconciliation

The reviewed PR-10R baseline for this evidence-only remediation is:

```text
PR-10R current_head_at_review = bffb95c3dc239219ec4c288eaa3c9991f7733f6c
```

This is not the PR-10R evidence payload commit. The payload commit is:

```text
PR-10R evidence_payload_commit = 7db0696f4e687fe07c2f603ab37a24f620fd1281
```

The distinction is preserved in `artifacts/pr_evidence/PR-10R/` and is the
specific correction required by `PR10R-REV-004-001`.

PR-10R2 evidence commits, if created after this reviewed baseline, are
post-review evidence payloads. They must not replace the corrected PR-10R
`current_head_at_review` value or be described as part of the prior PR-10R
implementation review. The first PR-10R2 evidence payload commit is
`686402e3082424260c9a52b5636c45fbc00e38a5`; any later metadata-only commit is
the post-PR-10R2 current HEAD and is reported separately by the final Git
verification to avoid a self-referential SHA.
