# PR-07R test report

The byte-size test proves a store-derived 24-byte oracle, rejects 25, and verifies a fresh
database read remains unchanged. The valid-size path is accepted. The ArtifactVersion
adapter test executes the shared PR-03 lifecycle and immutability contract.

Results: full suite `264 passed`; PR-07 PostgreSQL subset `22 passed`; focused
contract/architecture/store subset `78 passed`.
