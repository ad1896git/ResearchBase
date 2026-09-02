# Command-to-Handler Map

| CLI command | Application handler/query | Input DTO | Output DTO/family |
|---|---|---|---|
| project create | `ApplicationService.create_project` | `CreateProjectCommand` | `ProjectReadModel` |
| rq create/revise/freeze | `create_research_question`, `revise_research_question`, `freeze_research_question` | corresponding research-question commands | research-question read models |
| hypothesis create/revise/freeze | `create_hypothesis`, `revise_hypothesis`, `freeze_hypothesis` | corresponding hypothesis commands | hypothesis read models |
| spec create/revise/freeze | `create_experiment_spec`, `revise_experiment_spec`, `freeze_experiment_spec` | corresponding experiment-spec commands | experiment-spec read models |
| dataset create/snapshot | `register_dataset`, `create_dataset_snapshot` | `RegisterDatasetCommand`, `CreateDatasetSnapshotCommand` | dataset read models |
| artifact create/revise/freeze | `create_artifact`, `create_artifact_version`, `freeze_artifact_version` | corresponding artifact commands | artifact read models |
| metric create/revise/freeze | `create_metric_definition`, `revise_metric_definition`, `freeze_metric_definition` | corresponding metric commands | metric read models |
| run create/add-dataset/add-artifact/start/finish | `create_run`, `attach_run_dataset_input`, `attach_run_artifact_input`, `start_run`, `finish_run` | corresponding run commands | `RunReadModel` |
| run provenance | `ProvenanceQueryService.get_run_provenance` | `run_id` UUID | `RunProvenanceDTO` |
| measurement create | `ApplicationService.record_measurement` | `RecordMeasurementCommand` | `MeasurementReadModel` |
| stats create | `ApplicationService.record_statistical_result` | `RecordStatisticalResultCommand` | `StatisticalResultReadModel` |
| claim create/revise/add-evidence/freeze | `create_claim`, `revise_claim`, `link_evidence`, `freeze_claim_version` | corresponding claim commands | claim/evidence read models |
| claim trace | `ProvenanceQueryService.trace_claim_to_runs` | `claim_version_id` UUID | `ClaimToRunsTraceDTO` |
| audit create | `GovernanceService.create_audit_finding` | `CreateAuditFindingCommand` | audit finding DTO |
| impact assess | `GovernanceService.create_impact_assessment` | `CreateImpactAssessmentCommand` | impact assessment DTO |
| impact show | `GovernanceQueryService.downstream_impact` | typed target UUID | downstream impact DTO tuple |
| correction create | `GovernanceService.create_correction_record` | `CreateCorrectionRecordCommand` | correction record DTO |

Human output is produced by the shared deterministic formatter. JSON output is produced by the recursive
ORM-free DTO serializer. Expected Application errors use the stable exit-code mapper; unexpected exceptions
use exit 70.
