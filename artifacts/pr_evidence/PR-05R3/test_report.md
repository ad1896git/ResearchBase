# Test report

PR-05R3 fresh verification passed:

- full pytest: `193 passed`;
- PR-05 domain unit file: `29 passed`;
- targeted material/hash proof: `19 passed, 10 deselected`;
- architecture tests: `27 passed`;
- PostgreSQL integration: `47 passed, 146 deselected`;
- Ruff: PASS;
- Pyright: PASS.

The test diff contains no production changes. The targeted proof covers six material-field sensitivity cases and ten excluded/context-field stability cases from one deterministic baseline.
