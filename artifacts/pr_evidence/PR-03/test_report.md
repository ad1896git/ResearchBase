# PR-03 Test Report

## Results

- Full regression with PostgreSQL enabled: **121 passed**.
- PostgreSQL integration subset: **16 passed**.
- PR-03 version contract tests: **24 passed**.
- Architecture tests: **23 passed**.
- Ruff: **PASS**.
- Pyright: **PASS**, 0 errors, 0 warnings, 0 informations.
- Ruff format check: **PASS**.
- UV lock check: **PASS**.

## Coverage of the authorized contract

The tests cover exact enum values, all three allowed transitions, reverse and same-state
rejection, stable error codes, explicit material freeze, canonical hash scheme, injected aware
UTC clock, key-order stability, changed-material hashing, invalid material, non-material field
exclusion, frozen/superseded immutability, abandoned non-reactivation, frozen canonical policy,
and reuse across mapping- and sequence-shaped fixtures.
