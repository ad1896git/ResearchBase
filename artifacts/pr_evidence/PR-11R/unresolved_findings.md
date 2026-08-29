# Unresolved findings

P0: none.

P1: none.

P2: none.

P3: inherited repository-wide Ruff formatting debt remains in eight files
outside PR-11R and predates PR-11. It is non-blocking because no inherited file
was modified and all PR-11R-owned files pass the scoped formatting check.

## Subsequent independent review

At reviewed PR-11R HEAD `6675a7444cdb897d1bf810a55b32b6d88015ea15`, the
independent review found `PR11R-MIG-001` and `PR11R-EVID-001`. They were not
resolved by the historical PR-11R evidence. PR-11R2 closes both findings; the
fresh evidence is in `artifacts/pr_evidence/PR-11R2/`.
