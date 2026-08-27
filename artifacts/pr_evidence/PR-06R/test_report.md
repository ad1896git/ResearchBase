# PR-06R test report

The remediation-focused PostgreSQL suite passed **27 tests**. It includes the independent hash oracle, material sensitivity, Application key-order equivalence, observed-INSERT rollback, missing Dataset, stable error paths, seven-field trigger breadth, behavioral Dataset/Actor/Project RESTRICT deletion, and the pre-existing concurrency/idempotency/schema tests.

Final gates passed: full pytest **234 passed**, targeted PostgreSQL suite **27 passed**, architecture/unit subset **41 passed**, Ruff passed, Pyright reported **0 errors, 0 warnings, 0 informations**, PostgreSQL reported **18.6**, and the disposable `0005 → 0004 → 0005` migration roundtrip passed.
