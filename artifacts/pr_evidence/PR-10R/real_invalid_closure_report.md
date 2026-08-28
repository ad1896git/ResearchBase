# Real invalid closure report

The remediation no longer monkeypatches `ProvenanceClosureValidator`. It creates a
real DRAFT ExperimentSpecVersion through the application, then uses a direct
PostgreSQL update to point an already SUCCEEDED Run at that valid DRAFT version. The
foreign key remains valid while the frozen-provenance closure becomes invalid.

The test calls the real `validate_run_closure` path from a fresh service/UoW and
asserts `complete is False` with a `VERSION_NOT_FROZEN` violation. It then calls the
real `record_measurement` command, which returns the stable
`PROVENANCE_CLOSURE_VIOLATION` error. A new UoW lists zero Measurements for the Run,
proving rejection has no insert side effect.

Result: PASS. `PR10-REV-002` is closed.
