# PR-18 commands and results

The canonical command tokens and SHA-256 fingerprints are stored in
`implementation_verification.json`. The 19 current commands were executed
against the implementation subject before evidence generation. Their JUnit
outputs are preserved under `junit/`.

| Group | Result |
| --- | --- |
| Full suite | 755 discovered, 753 passed, 2 skipped, 0 failed |
| PostgreSQL integration | 755 discovered, 334 selected, 332 passed, 2 skipped, 421 deselected, 0 failed |
| PR-18 focused/evidence tooling | 39 passed |
| WriteResult/API/CLI | 44 passed |
| Direct-SQL adversarial | 22 passed |
| Concurrency | 1 passed |
| Migration lifecycle | 6 passed |
| Rollback snapshot | 1 passed |
| Database invariants | 113 passed |
| Catalog and EXPLAIN | 4 passed |
| Architecture | 51 passed |
| Atomicity | 5 passed |
| Historical exactness | 4 passed |
| Hash invariance | 117 passed |
| Provenance | 25 passed |
| Adapter equivalence | 17 passed |
| Ruff, Pyright, git diff check | PASS |

The full-suite increase from the accepted 739-test baseline is exactly 16 new
PR-18 tests: 14 non-integration tests and 2 PostgreSQL integration tests. The
two skips are inherited PR11R2 migration tests and are not PR-18-specific.
