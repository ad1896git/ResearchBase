# PR10R-REV-004-001 disposition

Finding: `PR10R-REV-004-001` — P2 — the PR-10R fingerprint contained an
invalid full SHA for `7db0696` and recorded `current_head_at_review`
incorrectly.

Disposition: CLOSED.

Independent Git resolution at execution time produced:

- `7db0696` → `7db0696f4e687fe07c2f603ab37a24f620fd1281`
- PR-10R `current_head_at_review` →
  `bffb95c3dc239219ec4c288eaa3c9991f7733f6c`

The corrected PR-10R fingerprint now preserves the semantic distinction:

- reviewed implementation head: `9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d`;
- evidence payload commit: `7db0696f4e687fe07c2f603ab37a24f620fd1281`;
- PR-10R current HEAD at review: `bffb95c3dc239219ec4c288eaa3c9991f7733f6c`.

The `7db0696..bffb95c` range is evidence-only, and no new P0 or P1 finding
was introduced. PR-11 remains unauthorized.
