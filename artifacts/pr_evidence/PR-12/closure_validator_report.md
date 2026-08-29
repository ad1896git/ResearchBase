# Closure validator report

`validate_claim_version` returns a deterministic `ClosureReport`. A valid finalized ClaimVersion completed with `complete=True`. The validator checks support_set_hash and content_hash, exact historical evidence, same-project source ownership, StatisticalResult inputs, Measurement -> exact Run, Run -> exact ExperimentSpecVersion/DatasetSnapshot/ArtifactVersion closure, and finalized MetricDefinitionVersion status.

The mixed historical closure integration test passed for exact frozen/superseded dependencies. Newer current pointers are not consulted as replacements for persisted references. Missing source, non-final MetricDefinitionVersion, and malformed closure cases produce stable ordered violations.
