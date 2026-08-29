# Clean-upgrade fixture report

The strengthened test `test_clean_previous_head_upgrade_and_roundtrip_reaches_fail_closed_head`
resets a real PostgreSQL database to `0012_statistical_result_input_guard`.
At that revision it creates:

1. an Actor and Project through the existing Application boundary;
2. a valid Measurement with its existing Run/MetricDefinitionVersion and
   ExperimentSpecVersion provenance;
3. a StatisticalResult through `record_statistical_result` with one legitimate
   Measurement input edge.

Before migration, the test reads the database directly and asserts:

```text
parent count = 1
input count = 1
(statistical_result_id, measurement_id, input_role, ordinal)
 = (created result id, created measurement id, "input", 0)
```

It then runs `0012 -> 0013`, verifies the final head, and compares the full
StatisticalResult row and exact input-edge tuple before and after migration.
The test also runs `0013 -> 0012 -> 0013` on the populated state. This is not
an empty-database migration proof.

Observed result: PASS, 2 migration-matrix tests passed.
