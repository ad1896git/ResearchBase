# Test report

Fresh full suite: 527 passed, 2 skipped. PR-14 targeted: 13 passed across domain/hash, schema, resolver/commands, golden downstream paths, validity, correction invariance, direct DB immutability, lifecycle concurrency, FK/RESTRICT, scaled SQL counts, batch resolution, and three post-flush atomicity cases. Migration-only legacy tests account for the two environment-gated skips.
