# Code review

Review focus was the PR-06 attack surface:

- `manifest_hash` and derived `content_hash` remain distinct and validated;
- only AD-PR06-001 material participates in the bare hash;
- locator retries cannot mutate immutable state;
- idempotency is scoped by dataset identity and survives the unique-race path;
- late failure rolls back after a real flush;
- Snapshot repositories expose no generic mutation method;
- no DatasetVersion or PR-07 implementation is present.

No P0, P1, P2, or P3 findings remain for PR-06.
