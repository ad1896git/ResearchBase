# PR-03R Test Report

## Results

- Full regression with PostgreSQL enabled: **124 passed**.
- PostgreSQL integration subset: **16 passed**.
- PR-03R version contract tests: **27 passed**.
- Architecture tests: **23 passed**.
- Ruff: **PASS**.
- Pyright: **PASS**, 0 errors, 0 warnings, 0 informations.
- Ruff format check: **PASS**.
- UV lock check: **PASS**.

## Remediation coverage

The tests independently encode the complete required lifecycle matrix, reject the adversarial
broken frozen-reversion fixture, cover DRAFT editing, FROZEN/SUPERSEDED immutability,
ABANDONED non-reactivation/freeze/supersede, explicit material selection with differing
non-material metadata, changed material, and stable validation errors with chained causes.
