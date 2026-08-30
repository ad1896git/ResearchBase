# Fingerprint reconciliation

All listed commit IDs were resolved with `git rev-parse` and all resolved objects are commits.

- PR-11 final baseline: `18fb4138e7ccb57809ea54b916f52d8b801b8bec`.
- PR-12 reviewed HEAD: `9244ac1ca920c2a7d8777e7f1fbbdcab0fda27e2`.
- PR-12R remediation implementation/test commit: `054fb27f7007abf38a42b8dc674996e86b8038eb`.
- PR-12 original evidence payload commit: `4454fe6f2afed551e076e25a7bd75020200e3e7f`.
- PR-12R evidence payload commit: `298594d0c988fd0d19b05aadddff60ac027d98bf`.
- PR-12R changed-files inventory commit: `2aa939be55c1fdaed326b9888a5bb966b88e9aa9`.
- PR-12R fingerprint commit: `a92ad0186266248ae4d1f9f91da8eb33b5d7bd26`.
- HEAD after the fingerprint commit: `a92ad0186266248ae4d1f9f91da8eb33b5d7bd26`.
- PR-12R evidence metadata commit: `de00596817269fd10cad27fc00cb998318ce73ef`.
- PR-12R architecture evidence commit: `4e0155731a0f3f681aef1eec77b438fbad843f9e`.
- PR-12R inventory reconciliation commit: `069938e7cd2f3072d83fff6630902be5d3a768d0`.
- Current HEAD immediately before the final fingerprint metadata commit: `069938e7cd2f3072d83fff6630902be5d3a768d0`.

The final fingerprint metadata commit follows that snapshot; the final status report records its resulting current HEAD separately. The reviewed PR-12 HEAD remains the historical 9244ac1 commit and is not rewritten to a later evidence HEAD.

## PR-12R2 reviewed-head reconciliation

- PR-12R final fingerprint reconciliation commit: `3564361bb3b80a9302b48ed61b1b0b1fa773de26`.
- Independently reviewed PR-12R HEAD: `3564361bb3b80a9302b48ed61b1b0b1fa773de26`.
- PR-12R2 implementation/test commit: `e95fee5e59c97d78cf4ebe6c86f195c86b3ab759`.
- PR-12R2 evidence payload commit: `0d9f78ce5055987f448ef64c4b43fb8c635f0465`.

The historical PR-12 and PR-12R reviewed HEADs remain distinct from later PR-12R2 commits. The PR-12R2 fingerprint and final status record later evidence commits and the post-evidence current HEAD separately.
