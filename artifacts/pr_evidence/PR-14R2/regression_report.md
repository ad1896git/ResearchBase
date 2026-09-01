# Regression report

The independently accepted PR-14R regression set remains green:

- AuditFinding resolver/hash/lifecycle: PASS;
- ImpactAssessment immutability/hash/atomicity: PASS;
- downstream exact paths: PASS;
- validity projection: PASS;
- CorrectionRecord immutability/projection: PASS;
- historical invariance: PASS;
- PR-13 trace/query: 15 passed;
- PR-12 Claim/closure: 71 passed;
- PR-11 StatisticalResult: 50 passed;
- PR-10 Measurement: 39 passed;
- PR-09 Run: 32 passed.

Full PostgreSQL pytest: 527 passed, 2 explicitly environment-gated migration tests skipped.
