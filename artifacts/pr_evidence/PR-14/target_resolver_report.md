# TargetResolver report

Closed set: experiment_spec_version, dataset_snapshot, artifact_version, run, metric_definition_version, measurement, statistical_result, claim_version. Missing IDs return `NOT_FOUND`; unsupported strings, cross-project targets, and caller-supplied target hashes are rejected. Canonical stored hashes are derived by explicit typed reads; no arbitrary table lookup, dynamic SQL, import-string registry, or generic graph resolver exists. Batch resolution uses one typed read per supported target type.
