# PR2-11 R2 recovery — conditional development evidence

Accepted base: `0498204bbef4faea390a8724038462ebfff3e901`.
Blocked prior candidate `845beaff49e8afcadec90e8e4e3230478c45c12b` was
diagnostic only; it is not in this branch ancestry. Contract matrix:
`docs/phase2/PR2-11-R2-contract-matrix.md`, frozen before production code.
Primary authority: Addendum A18; `14_Phase2_Design_Gap_Closure_R2_v1.0.md` §3;
`15_Phase2_Hash_Payload_Contract_R2_v1.0.md` ScientificConclusion clauses.

Implementation commits:

- Initial candidate: `18bfa8004de03aa88c2b61f22be68c0af0fa7f5e`.
- Reviewed remediation and final implementation:
  `aea8e270d8715c647fa24d131fcdfcfadb4d8728`.

The implementation adds exact typed Conclusion inputs, an optional
same-ClaimVersion literature snapshot FK, canonical R2 support/content hashes,
authenticated create/replace-inputs/freeze/revise/read commands, immutable
frozen material, a deferred current-pointer guard, idempotency receipts and
derived stale validity. The 0033 migration was used only in newly generated
disposable databases on PostgreSQL port 55442. It was not applied to retained
M2/M3 databases.

## Actual checks

| Check | Command / condition | Result |
| --- | --- | --- |
| R2 contract-first unit | `uv run pytest -q tests/unit/phase2/test_pr2_11_r2_contract.py` | 6 passed; exact R2 golden hashes |
| R2 disposable PostgreSQL | `RB_PR211_R2_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q --disable-warnings --log-cli-level=CRITICAL tests/integration/phase2/test_pr2_11_r2_persistence.py` | 14 passed, 29 warnings; every test verified server ID `7695073913076924777`, created and dropped only its new random database |
| M3 regression | `DATABASE_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q --disable-warnings --log-cli-level=CRITICAL tests/integration/phase2/test_m3_evidence.py` | 13 passed; disposable databases |
| PR2-10 regression | `RB_PR210_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q --disable-warnings --log-cli-level=CRITICAL tests/integration/phase2/test_pr2_10_discussion_persistence.py` | 9 passed; pinned legacy test setup to its own 0032 revision |
| Relevant unit/architecture | `uv run pytest --disable-warnings -ra tests/unit/phase2/test_pr2_11_r2_contract.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/architecture/test_import_boundaries.py tests/test_architecture.py -k 'not test_migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'` | 67 passed, 1 deselected |
| Ruff | `uv run ruff check` on changed Python files | PASS |
| Pyright | `uv run pyright` on new domain, service, repository and PG tests | 0 errors, 0 warnings |
| Disposable cleanup | Read-only `pg_control_system()` and `pg_database` query | Port 55442 / `/private/tmp/rb-m3-postgres` / ID `7695073913076924777`; zero `researchbase_pr211_r2_test_%` databases remained |

The unexcluded architecture run still fails its pre-existing migration-list
assertion ending at 0026. The two established execution-service cancellation
failures were not rerun and are not counted as passing. The initial PR2-10
regression attempt failed because its helper independently upgraded to the new
head 0033 while the test asserted 0032; pinning that test fixture to 0032
restored all nine tests. This was a test setup correction, not a product change.

## Raw evidence SHA-256

| Artifact | SHA-256 |
| --- | --- |
| `PR2-11-R2-pg-remediation1.txt` | `80eaac6038887e985d546699936d7bc9614b01128385d871095bfcad9c5e777a` |
| `PR2-11-PR210-regression.txt` | `8b1a71371e3de5f5f153e634d59e7c60656af9b76a3b28e3485db0f1232ca41b` |
| `PR2-11-M3-regression.txt` | `f7e5068088a20cba26ea8720a20151fb4868a7652ecc456020a4bea95eb7162e` |
| `PR2-11-unit-architecture.txt` | `e346a33b9cc2c22741e3733e34078f8e8d8c858ddf077a5f6d6dac4f3255dd5a` |
| `PR2-11-pointer-red.txt` | `77083bff9ca9b8b6c6cfb2247c30dbe76cde5dbe5cf04db057bf31f5dc8f94b6` |
| `PR2-11-draft-red.txt` | `aace634b3ddec5251118874efaf057ce33e53f0f818bd42e510b7453e95c8fa3` |

Tool versions: Python 3.12.14; uv 0.12.6. No live provider request.

## Independent review

First independent read-only review of `18bfa80`: BLOCKED, one confirmed P1
and two P2. The P1 allowed a raw FROZEN→SUPERSEDED update to leave a
non-FROZEN current pointer; a disposable PG RED test reproduced it. Remediation
added a deferred commit-time pointer invariant; 14 PG tests passed. One P2,
missing Application DRAFT input change, was closed by authenticated,
idempotent `replace_inputs`. Fresh independent read-only review of `aea8e27`:
**conditional PASS, zero confirmed P0/P1**.

Remaining P2: all direct/snapshot evidence overlap is rejected. R2 §3 permits
an acknowledged CONTRADICTS/QUALIFIES exception, but specifies no machine
acknowledgment grammar. This candidate fails closed and cannot claim support
for that permitted exception. It is follow-up contract work, not accepted
scientific evidence.

## Governance

PR2-11 conditional technical development: PASS. Formal PR2-11 acceptance:
NOT APPROVED. M3 Human Gate: BLOCKED. M3 Final Acceptance: NOT APPROVED.
TDG2 formal activation: NOT AUTHORIZED. No retained M2/M3 write, real HUMAN
verification, OpenAlex contact or protected deployment occurred.
