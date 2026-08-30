# Fingerprint reconciliation

All listed commit IDs were resolved with `git rev-parse` and all resolved objects are commits.

- PR-11 final baseline: `18fb4138e7ccb57809ea54b916f52d8b801b8bec`.
- PR-12 reviewed HEAD: `9244ac1ca920c2a7d8777e7f1fbbdcab0fda27e2`.
- PR-12R remediation implementation/test commit: `054fb27f7007abf38a42b8dc674996e86b8038eb`.
- PR-12 original evidence payload commit: `4454fe6f2afed551e076e25a7bd75020200e3e7f`.

The PR-12R evidence payload, inventory, and fingerprint commits are recorded separately in `harness_fingerprint.json` after each is resolved from Git. The final report records the post-evidence current HEAD separately. The reviewed PR-12 HEAD remains the historical 9244ac1 commit and is not rewritten to a later evidence HEAD.
