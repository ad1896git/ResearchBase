# Batched query architecture

Typed readers: Measurement `get_many/list_by_runs`; StatisticalResult `get_many/list_inputs_for_results`;
Run `get_many/list_*_inputs_for_runs`; exact Spec, DatasetSnapshot, ArtifactVersion, and MetricVersion
batch readers. IDs are deduplicated before SQL. DTO assembly loops use dictionaries/lists only. One
UoW/session is used per trace. No generic graph abstraction or persistent cache exists.
