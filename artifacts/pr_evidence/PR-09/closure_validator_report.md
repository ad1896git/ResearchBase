# Closure validator report

`ProvenanceClosureValidator` is framework-neutral and returns `ClosureReport(complete, visited_count, violations)`. It follows concrete Run → exact ExperimentSpecVersion, DatasetSnapshot, and ArtifactVersion edges; verifies the spec and every ArtifactVersion are frozen; verifies DatasetSnapshots exist; and requires sealed inputs for RUNNING/terminal Runs. Violations are sorted deterministically by path, object type, object ID, and code. A complete fixture visits 4 objects: Run, spec version, dataset snapshot, and artifact version.

