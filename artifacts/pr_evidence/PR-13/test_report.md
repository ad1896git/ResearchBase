# Test report

Full pytest completed with exit 0 against PostgreSQL 18.6; output showed two existing skips and no
failure. PR-13 focused suite: 8 passed before final SQL-count commit; the SQL-count test was rerun and
passed after the exact count assertion. Coverage includes DTO boundary, missing roots, direct evidence,
three-input StatisticalResult traversal, Run dedup/path cardinality, DRAFT empty evidence, exact Run
inputs, SELECT-only SQL, persisted Run-state equality, full V1/D1/A1/M1/C1 later-state contamination,
two-project exact-FK isolation, and architecture guards.
