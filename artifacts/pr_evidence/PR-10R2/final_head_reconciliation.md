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
implementation review.
