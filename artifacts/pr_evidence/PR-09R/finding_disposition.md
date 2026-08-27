# Finding disposition

- PR09-REV-001: CLOSED. The 0009 trigger checks OLD and NEW Run rows and requires PLANNED/unsealed state for every input mutation operation.
- PR09-REV-002: CLOSED. A real PostgreSQL attach-vs-start test uses independent sessions and a barrier at the Run lock path.
- PR09-REV-003: CLOSED. Create and artifact attach failures are injected after real SQL flush and verified with fresh UoWs.
- PR09-REV-004: CLOSED. The complete six-target FK/RESTRICT behavioral matrix is exercised.
- PR09-REV-005: CLOSED. Multiple closure violations and DTO fields/order are asserted repeatedly.
- PR09-REV-006: CLOSED. Git-derived ownership is 14 PR-09 Python files and 15 files including the new PR-09R migration.
- PR09-REV-007: CLOSED. Original race/atomicity evidence overclaims are explicitly corrected in PR-09 evidence and replaced with measured results here.
