# PR2-20 focused verification

Subject `1ae0036344c26057b1e70c7bbd3daf4e5d3b2d51`; authored dirty diff `f01f97fc03bf5cff9f3bfccfce2d46e7d2ef6121b0e820b363c8f6f8d336e47e`. Generated reports/evidence are excluded from their own digest.

[Machine commands and logs](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/verification.json). The verifier never runs the whole suite. Static checks have no pytest counts. Skipped large cases are BLOCKED timing evidence, not passes.

| Command | Exit | Passed | Failed | Errors | Skipped |
| --- | --- | --- | --- | --- | --- |
| `uv sync --locked --group dev` | 0 | — | — | — | — |
| `uv run ruff check .` | 0 | — | — | — | — |
| `uv run ruff format --check .` | 0 | — | — | — | — |
| `uv run pyright` | 0 | — | — | — | — |
| `uv run alembic heads` | 0 | — | — | — | — |
| `uv run pytest tests/unit tests/architecture --junitxml tmp/pr220-verification/unit-architecture.xml` | 0 | 2156 | 0 | 0 | 0 |
| `uv run pytest tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_security.py tests/e2e/test_pr2_20_benchmark.py --junitxml tmp/pr220-verification/changed-postgres.xml` | 0 | 48 | 0 | 0 | 48 |
| `uv run pytest tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_19_citation_trace.py --junitxml tmp/pr220-verification/owning-postgres.xml` | 0 | 81 | 0 | 0 | 0 |
| `uv run pytest tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py --junitxml tmp/pr220-verification/phase1-golden.xml` | 0 | 20 | 0 | 0 | 0 |
| `RB_PR220_BENCHMARK=1 uv run pytest tests/e2e/test_pr2_20_benchmark.py --junitxml tmp/pr220-verification/large-benchmark.xml` | 0 | 3 | 0 | 0 | 48 |

Independent read-only review found subject exclusion, false exit-PASS, raw secret-validation and benchmark-attribution defects during authoring. Those were corrected and covered by focused tests. Follow-up read-only review confirmed those fixes and found no remaining semantic P0/P1 in that scope; a missing test import was corrected before this run. No reviewer or owner exit acceptance is inferred from this log. The existing transport destination finding remains P1 and prevents exit success. Host/profile prerequisites and real PaperQA2 intake remain BLOCKED. Owner dispositions for inherited contracts are not attached. STOP; wait for explicit Phase 3 GO.

Additional focused PostgreSQL expiry evidence: `uv run pytest -s tests/integration/phase2/test_pr2_19_races.py::test_cross_expiry_five_database_timestamps --junitxml tmp/pr220-verification/five-timestamps.xml` — exit 0; **1 passed, 0 failed, 0 errors, 0 skipped**. The [raw database timestamps](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/five-timestamps.txt) and [command record](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/five-timestamps.json) retain the five witnessed times and zero protected effects.
