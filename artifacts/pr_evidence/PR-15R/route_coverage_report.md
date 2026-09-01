# Route Coverage Report

The canonical table below is asserted against live FastAPI OpenAPI plus route-function source in
`tests/unit/test_pr15r_route_contract.py`. Count: 35/35; operation IDs: 35 unique.

| Method | Path | Request schema | Application handler/query | Response schema | Operation ID |
|---|---|---|---|---|---|
| POST | `/v1/projects` | ProjectIn | create_project | ProjectReadModelResponse | create_project |
| POST | `/v1/research-questions` | ResearchQuestionIn | create_research_question | ResearchQuestionReadModelResponse | create_research_question |
| POST | `/v1/research-questions/{id}/versions` | ReviseResearchQuestionIn | revise_research_question | ResearchQuestionReadModelResponse | revise_research_question |
| POST | `/v1/research-question-versions/{id}:freeze` | FreezeResearchQuestionIn | freeze_research_question | ResearchQuestionVersionReadModelResponse | freeze_research_question_version |
| POST | `/v1/hypotheses` | HypothesisIn | create_hypothesis | HypothesisReadModelResponse | create_hypothesis |
| POST | `/v1/hypotheses/{id}/versions` | ReviseHypothesisIn | revise_hypothesis | HypothesisReadModelResponse | revise_hypothesis |
| POST | `/v1/hypothesis-versions/{id}:freeze` | FreezeHypothesisIn | freeze_hypothesis | HypothesisVersionReadModelResponse | freeze_hypothesis_version |
| POST | `/v1/experiment-specs` | ExperimentSpecIn | create_experiment_spec | ExperimentSpecReadModelResponse | create_experiment_spec |
| POST | `/v1/experiment-specs/{id}/versions` | ReviseExperimentSpecIn | revise_experiment_spec | ExperimentSpecReadModelResponse | revise_experiment_spec |
| POST | `/v1/experiment-spec-versions/{id}:freeze` | FreezeExperimentSpecIn | freeze_experiment_spec | ExperimentSpecVersionReadModelResponse | freeze_experiment_spec_version |
| POST | `/v1/datasets` | DatasetIn | register_dataset | DatasetReadModelResponse | register_dataset |
| POST | `/v1/datasets/{id}/snapshots` | DatasetSnapshotIn | create_dataset_snapshot | DatasetSnapshotReadModelResponse | create_dataset_snapshot |
| POST | `/v1/artifacts` | ArtifactIn | create_artifact | ArtifactReadModelResponse | create_artifact |
| POST | `/v1/artifacts/{id}/versions` | ArtifactVersionIn | create_artifact_version | ArtifactVersionReadModelResponse | create_artifact_version |
| POST | `/v1/artifact-versions/{id}:freeze` | FreezeArtifactIn | freeze_artifact_version | ArtifactVersionReadModelResponse | freeze_artifact_version |
| POST | `/v1/metric-definitions` | MetricDefinitionIn | create_metric_definition | MetricDefinitionReadModelResponse | create_metric_definition |
| POST | `/v1/metric-definitions/{id}/versions` | ReviseMetricDefinitionIn | revise_metric_definition | MetricDefinitionReadModelResponse | revise_metric_definition |
| POST | `/v1/metric-definition-versions/{id}:freeze` | FreezeMetricDefinitionIn | freeze_metric_definition | MetricDefinitionVersionReadModelResponse | freeze_metric_definition_version |
| POST | `/v1/runs` | RunIn | create_run | RunReadModelResponse | create_run |
| POST | `/v1/runs/{id}/dataset-inputs` | DatasetInputIn | attach_run_dataset_input | RunReadModelResponse | attach_run_dataset_input |
| POST | `/v1/runs/{id}/artifact-inputs` | ArtifactInputIn | attach_run_artifact_input | RunReadModelResponse | attach_run_artifact_input |
| POST | `/v1/runs/{id}:start` | TransitionIn | start_run | RunReadModelResponse | start_run |
| POST | `/v1/runs/{id}:finish` | FinishRunIn | finish_run | RunReadModelResponse | finish_run |
| GET | `/v1/runs/{id}/provenance` | none | get_run_provenance | RunProvenanceDTOResponse | get_run_provenance |
| POST | `/v1/measurements` | MeasurementIn | record_measurement | MeasurementReadModelResponse | record_measurement |
| POST | `/v1/statistical-results` | StatisticalResultIn | record_statistical_result | StatisticalResultReadModelResponse | record_statistical_result |
| POST | `/v1/claims` | ClaimIn | create_claim | ClaimReadModelResponse | create_claim |
| POST | `/v1/claims/{id}/versions` | ReviseClaimIn | revise_claim | ClaimReadModelResponse | revise_claim |
| POST | `/v1/claim-versions/{id}/evidence` | EvidenceIn | link_evidence | EvidenceRelationReadModelResponse | link_evidence |
| POST | `/v1/claim-versions/{id}:freeze` | FreezeClaimIn | freeze_claim_version | ClaimVersionReadModelResponse | freeze_claim_version |
| GET | `/v1/claim-versions/{id}/trace` | none | trace_claim_to_runs | ClaimToRunsTraceDTOResponse | trace_claim_to_runs |
| POST | `/v1/audit-findings` | AuditFindingIn | create_audit_finding | AuditFindingResponse | create_audit_finding |
| POST | `/v1/impact-assessments` | ImpactAssessmentIn | create_impact_assessment | ImpactAssessmentResponse | create_impact_assessment |
| POST | `/v1/corrections` | CorrectionIn | create_correction_record | CorrectionRecordResponse | create_correction |
| GET | `/v1/impact/{target_type}/{target_id}` | none | downstream_impact | DownstreamImpactTargetResponse[] | get_downstream_impact |

Runtime families: Project, ResearchQuestion, Hypothesis, ExperimentSpec, Dataset, Artifact,
MetricDefinition, Run, Measurement, StatisticalResult, Claim, Claim Evidence, Governance, and all
three Query routes. Each family has success-schema and normalized-error execution; POST families
assert exact body/path UUID forwarding and all accepted ExecutionContext header fields. Success probes
return actual Application dataclass DTOs, not schema-shaped dictionaries.
