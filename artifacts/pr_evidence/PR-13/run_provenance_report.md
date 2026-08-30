# Run provenance report

PostgreSQL tests observed exact ExperimentSpecVersion, DatasetSnapshot, and ArtifactVersion IDs,
including role and ordinal. Dataset and Artifact collections are explicitly ordered. Run closure is
obtained from `ProvenanceClosureValidator.validate_run_in_uow`. The query never resolves identity
current pointers.

