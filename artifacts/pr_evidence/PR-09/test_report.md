# Test report

The original PR-09 suite collected 300 tests and passed with real PostgreSQL, but its evidence overstated deterministic race, create/artifact atomicity, and FK matrix coverage. PR-09R adds the missing synchronized races, complete flush-after-INSERT rollback checks, full FK delete matrix, retarget attacks, multiple-violation closure DTO checks, and fresh-state assertions. The final PR-09R suite is reported in `artifacts/pr_evidence/PR-09R/test_report.md`.
