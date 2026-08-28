# PR-10R test report

The full PostgreSQL-backed suite passes with 356 tests. PR-10 schema/application
tests pass 20 tests, and the PR-10 domain hash tests pass 17 tests.

The targeted regressions cover the independent numeric/structured hash oracle,
one-variable material sensitivity and excluded-field stability, persisted invalid
closure rejection without monkeypatching, and complete historical Measurement row
stability after MetricDefinitionVersion supersession. Existing PR-10 gates for XOR,
Run and Metric eligibility, unit compatibility, duplicate material, immutability,
real SQL atomicity, FK/RESTRICT, and database constraints remain passing.

PostgreSQL 18.6 was used for persistence and migration proof. SQLite was not used as
a substitute for integration or constraint verification.
