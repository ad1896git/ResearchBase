# Historical Exactness Report

`tests/e2e/test_phase1_historical_exactness.py::test_historical_advancement_preserves_original_exact_ids_hashes_and_closure`
passed on PostgreSQL.

After the original GSAS-01 workflow, the test legally creates later ResearchQuestion, ExperimentSpec,
ArtifactVersion, MetricDefinitionVersion, and DatasetSnapshot records, then runs a separate later Run with a
later Measurement and StatisticalResult. Fresh Application reads re-query the original Run, Measurements,
StatisticalResult, frozen ClaimVersion, EvidenceRelation set, closure, trace, and impact.

Original IDs, material fields, hashes, evidence relations, Run row version, and original normalized projection
remain unchanged. Original provenance retains its exact frozen input references; the later Run is not substituted
by a latest/current shortcut.
