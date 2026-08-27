# Code review

Reviewed diff `9c47381..197bd2d` and every changed file.

- `src/researchbase/application/closure.py`: accepts only `FROZEN` and
  `SUPERSEDED` for exact ExperimentSpecVersion and ArtifactVersion closure;
  DRAFT/ABANDONED remain invalid. The change is the minimum implementation of
  AD-PR09R3-001.
- `tests/integration/test_pr09r2_proof.py`: adds adversarial finalized-state,
  authoring, and abandoned-reference tests; strengthens lock-boundary event
  proof and retry edge identity assertions.

No production schema or migration changed. Error ordering remains deterministic.
The implementation/test diff passes Ruff, Pyright, targeted checks, and the
full PostgreSQL-backed suite. No P0/P1 issue is open; the only reported P2 is
inherited repository formatting debt outside this diff.
