# Final HEAD verification

Starting reviewed HEAD:

```text
git rev-parse HEAD
602f22478c6919f2611ff436b4199a81fa6b8297
```

The PR-09R4 final HEAD is exactly `602f22478c6919f2611ff436b4199a81fa6b8297`.
The range `044c72a..602f224` is independently generated from Git and contains
only five evidence/reporting files. Therefore `602f224` is evidence-only,
not a production/test/migration commit.

R5 has a distinct evidence payload commit after the preserved R4 baseline.
The R5 fingerprint distinguishes `review_baseline_head`,
`evidence_payload_commit`, and `current_head_at_review`; it does not falsely
claim that the R5 commit is the historical PR-09R4 final HEAD.

The R5 evidence payload commit is
`9c35e6a26bf0cdecf69081aa609f3a1aa54778ce`. Its post-baseline range is
evidence-only. At the R5 independent review, the actual repository HEAD was
`ecb9adaf6aebef73fb45d344197ea9e18ad37d9c`; this is the value recorded as
`current_head_at_review` in the R5 fingerprint. The final response reports the
final Git HEAD after any later evidence-only metadata follow-up.
