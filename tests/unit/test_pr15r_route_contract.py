"""PR-15R exhaustive structural contract for the frozen HTTP surface."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from researchbase.api import routes
from researchbase.api.app import create_app


class EmptyServices:
    application = object()
    provenance = object()
    governance = object()
    governance_queries = object()


@dataclass(frozen=True, slots=True)
class RouteContract:
    method: str
    path: str
    endpoint: str
    handler: str
    request_schema: str | None
    response_schema: str
    operation_id: str


ROUTES = (
    RouteContract(
        "post",
        "/v1/literature/search-executions",
        "create_literature_search_execution",
        "create",
        "LiteratureSearchExecutionIn",
        "Response Create Literature Search Execution",
        "create_literature_search_execution",
    ),
    RouteContract(
        "get",
        "/v1/literature/search-executions",
        "list_literature_search_executions",
        "list",
        None,
        "Response List Literature Search Executions",
        "list_literature_search_executions",
    ),
    RouteContract(
        "post",
        "/v1/literature/search-executions/{execution_id}:execute",
        "execute_literature_search_execution",
        "_execution_command",
        "LiteratureSearchExecutionScopeIn",
        "Response Execute Literature Search Execution",
        "execute_literature_search_execution",
    ),
    RouteContract(
        "post",
        "/v1/literature/search-executions/{execution_id}:cancel",
        "cancel_literature_search_execution",
        "_execution_command",
        "LiteratureSearchExecutionScopeIn",
        "Response Cancel Literature Search Execution",
        "cancel_literature_search_execution",
    ),
    RouteContract(
        "post",
        "/v1/literature/search-executions/{execution_id}:recover",
        "recover_literature_search_execution",
        "_execution_command",
        "LiteratureSearchExecutionScopeIn",
        "Response Recover Literature Search Execution",
        "recover_literature_search_execution",
    ),
    RouteContract(
        "get",
        "/v1/literature/search-executions/{execution_id}",
        "get_literature_search_execution",
        "get",
        None,
        "Response Get Literature Search Execution",
        "get_literature_search_execution",
    ),
    RouteContract(
        "get",
        "/v1/literature/search-executions/{execution_id}/provenance",
        "get_literature_search_execution_provenance",
        "get_provenance",
        None,
        "Response Get Literature Search Execution Provenance",
        "get_literature_search_execution_provenance",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/search-plans",
        "create_literature_search_plan",
        "create",
        "LiteratureSearchPlanIn",
        "Response Create Literature Search Plan",
        "create_literature_search_plan",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/search-plans",
        "list_literature_search_plans",
        "list",
        None,
        "Response List Literature Search Plans",
        "list_literature_search_plans",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}",
        "get_literature_search_plan",
        "get",
        None,
        "Response Get Literature Search Plan",
        "get_literature_search_plan",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}:revise",
        "revise_literature_search_plan",
        "revise",
        None,
        "Response Revise Literature Search Plan",
        "revise_literature_search_plan",
    ),
    RouteContract(
        "put",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}",
        "update_literature_search_plan_draft",
        "update",
        "LiteratureSearchPlanIn",
        "Response Update Literature Search Plan Draft",
        "update_literature_search_plan_draft",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}/questions",
        "add_literature_search_plan_question",
        "add_question",
        None,
        "Response Add Literature Search Plan Question",
        "add_literature_search_plan_question",
    ),
    RouteContract(
        "delete",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}/questions/{research_question_id}",
        "remove_literature_search_plan_question",
        "remove_question",
        None,
        "Response Remove Literature Search Plan Question",
        "remove_literature_search_plan_question",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}:freeze",
        "freeze_literature_search_plan",
        "freeze",
        None,
        "Response Freeze Literature Search Plan",
        "freeze_literature_search_plan",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}:abandon",
        "abandon_literature_search_plan",
        "abandon",
        None,
        "Response Abandon Literature Search Plan",
        "abandon_literature_search_plan",
    ),
    RouteContract(
        "post",
        "/v1/projects",
        "create_project",
        "create_project",
        "ProjectIn",
        "ProjectReadModelResponse",
        "create_project",
    ),
    RouteContract(
        "post",
        "/v1/research-questions",
        "create_research_question",
        "create_research_question",
        "ResearchQuestionIn",
        "ResearchQuestionReadModelResponse",
        "create_research_question",
    ),
    RouteContract(
        "post",
        "/v1/research-questions/{id}/versions",
        "revise_research_question",
        "revise_research_question",
        "ReviseResearchQuestionIn",
        "ResearchQuestionReadModelResponse",
        "revise_research_question",
    ),
    RouteContract(
        "post",
        "/v1/research-question-versions/{id}:freeze",
        "freeze_research_question",
        "freeze_research_question",
        "FreezeResearchQuestionIn",
        "ResearchQuestionVersionReadModelResponse",
        "freeze_research_question_version",
    ),
    RouteContract(
        "post",
        "/v1/hypotheses",
        "create_hypothesis",
        "create_hypothesis",
        "HypothesisIn",
        "HypothesisReadModelResponse",
        "create_hypothesis",
    ),
    RouteContract(
        "post",
        "/v1/hypotheses/{id}/versions",
        "revise_hypothesis",
        "revise_hypothesis",
        "ReviseHypothesisIn",
        "HypothesisReadModelResponse",
        "revise_hypothesis",
    ),
    RouteContract(
        "post",
        "/v1/hypothesis-versions/{id}:freeze",
        "freeze_hypothesis",
        "freeze_hypothesis",
        "FreezeHypothesisIn",
        "HypothesisVersionReadModelResponse",
        "freeze_hypothesis_version",
    ),
    RouteContract(
        "post",
        "/v1/experiment-specs",
        "create_experiment_spec",
        "create_experiment_spec",
        "ExperimentSpecIn",
        "ExperimentSpecReadModelResponse",
        "create_experiment_spec",
    ),
    RouteContract(
        "post",
        "/v1/experiment-specs/{id}/versions",
        "revise_experiment_spec",
        "revise_experiment_spec",
        "ReviseExperimentSpecIn",
        "ExperimentSpecReadModelResponse",
        "revise_experiment_spec",
    ),
    RouteContract(
        "post",
        "/v1/experiment-spec-versions/{id}:freeze",
        "freeze_experiment_spec",
        "freeze_experiment_spec",
        "FreezeExperimentSpecIn",
        "ExperimentSpecVersionReadModelResponse",
        "freeze_experiment_spec_version",
    ),
    RouteContract(
        "post",
        "/v1/datasets",
        "register_dataset",
        "register_dataset",
        "DatasetIn",
        "DatasetReadModelResponse",
        "register_dataset",
    ),
    RouteContract(
        "post",
        "/v1/datasets/{id}/snapshots",
        "create_dataset_snapshot",
        "create_dataset_snapshot",
        "DatasetSnapshotIn",
        "DatasetSnapshotReadModelResponse",
        "create_dataset_snapshot",
    ),
    RouteContract(
        "post",
        "/v1/artifacts",
        "create_artifact",
        "create_artifact",
        "ArtifactIn",
        "ArtifactReadModelResponse",
        "create_artifact",
    ),
    RouteContract(
        "post",
        "/v1/artifacts/{id}/versions",
        "create_artifact_version",
        "create_artifact_version",
        "ArtifactVersionIn",
        "ArtifactVersionReadModelResponse",
        "create_artifact_version",
    ),
    RouteContract(
        "post",
        "/v1/artifact-versions/{id}:freeze",
        "freeze_artifact_version",
        "freeze_artifact_version",
        "FreezeArtifactIn",
        "ArtifactVersionReadModelResponse",
        "freeze_artifact_version",
    ),
    RouteContract(
        "post",
        "/v1/metric-definitions",
        "create_metric_definition",
        "create_metric_definition",
        "MetricDefinitionIn",
        "MetricDefinitionReadModelResponse",
        "create_metric_definition",
    ),
    RouteContract(
        "post",
        "/v1/metric-definitions/{id}/versions",
        "revise_metric_definition",
        "revise_metric_definition",
        "ReviseMetricDefinitionIn",
        "MetricDefinitionReadModelResponse",
        "revise_metric_definition",
    ),
    RouteContract(
        "post",
        "/v1/metric-definition-versions/{id}:freeze",
        "freeze_metric_definition",
        "freeze_metric_definition",
        "FreezeMetricDefinitionIn",
        "MetricDefinitionVersionReadModelResponse",
        "freeze_metric_definition_version",
    ),
    RouteContract(
        "post",
        "/v1/runs",
        "create_run",
        "create_run",
        "RunIn",
        "RunReadModelResponse",
        "create_run",
    ),
    RouteContract(
        "post",
        "/v1/runs/{id}/dataset-inputs",
        "attach_dataset",
        "attach_run_dataset_input",
        "DatasetInputIn",
        "RunReadModelResponse",
        "attach_run_dataset_input",
    ),
    RouteContract(
        "post",
        "/v1/runs/{id}/artifact-inputs",
        "attach_artifact",
        "attach_run_artifact_input",
        "ArtifactInputIn",
        "RunReadModelResponse",
        "attach_run_artifact_input",
    ),
    RouteContract(
        "post",
        "/v1/runs/{id}:start",
        "start_run",
        "start_run",
        "TransitionIn",
        "RunReadModelResponse",
        "start_run",
    ),
    RouteContract(
        "post",
        "/v1/runs/{id}:finish",
        "finish_run",
        "finish_run",
        "FinishRunIn",
        "RunReadModelResponse",
        "finish_run",
    ),
    RouteContract(
        "get",
        "/v1/runs/{id}/provenance",
        "run_provenance",
        "get_run_provenance",
        None,
        "RunProvenanceDTOResponse",
        "get_run_provenance",
    ),
    RouteContract(
        "post",
        "/v1/measurements",
        "record_measurement",
        "record_measurement",
        "MeasurementIn",
        "MeasurementReadModelResponse",
        "record_measurement",
    ),
    RouteContract(
        "post",
        "/v1/statistical-results",
        "record_statistical_result",
        "record_statistical_result",
        "StatisticalResultIn",
        "StatisticalResultReadModelResponse",
        "record_statistical_result",
    ),
    RouteContract(
        "post",
        "/v1/claims",
        "create_claim",
        "create_claim",
        "ClaimIn",
        "ClaimReadModelResponse",
        "create_claim",
    ),
    RouteContract(
        "post",
        "/v1/claims/{id}/versions",
        "revise_claim",
        "revise_claim",
        "ReviseClaimIn",
        "ClaimReadModelResponse",
        "revise_claim",
    ),
    RouteContract(
        "post",
        "/v1/claim-versions/{id}/evidence",
        "link_evidence",
        "link_evidence",
        "EvidenceIn",
        "EvidenceRelationReadModelResponse",
        "link_evidence",
    ),
    RouteContract(
        "post",
        "/v1/claim-versions/{id}:freeze",
        "freeze_claim",
        "freeze_claim_version",
        "FreezeClaimIn",
        "ClaimVersionReadModelResponse",
        "freeze_claim_version",
    ),
    RouteContract(
        "get",
        "/v1/claim-versions/{id}/trace",
        "claim_trace",
        "trace_claim_to_runs",
        None,
        "ClaimToRunsTraceDTOResponse",
        "trace_claim_to_runs",
    ),
    RouteContract(
        "post",
        "/v1/audit-findings",
        "create_audit_finding",
        "create_audit_finding",
        "AuditFindingIn",
        "AuditFindingResponse",
        "create_audit_finding",
    ),
    RouteContract(
        "post",
        "/v1/impact-assessments",
        "create_impact_assessment",
        "create_impact_assessment",
        "ImpactAssessmentIn",
        "ImpactAssessmentResponse",
        "create_impact_assessment",
    ),
    RouteContract(
        "post",
        "/v1/corrections",
        "create_correction",
        "create_correction_record",
        "CorrectionIn",
        "CorrectionRecordResponse",
        "create_correction",
    ),
    RouteContract(
        "get",
        "/v1/impact/{target_type}/{target_id}",
        "downstream_impact",
        "downstream_impact",
        None,
        "DownstreamImpactTargetResponse",
        "get_downstream_impact",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/sources",
        "register_literature_source",
        "register_literature_source",
        "LiteratureSourceIn",
        "Response Register Literature Source",
        "register_literature_source",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/sources/{source_id}/identifiers",
        "add_source_identifier",
        "add_source_identifier",
        "SourceIdentifierIn",
        "Response Add Source Identifier",
        "add_source_identifier",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/identifiers/{identifier_id}:verify",
        "verify_source_identifier",
        "verify_source_identifier",
        "IdentifierStatusIn",
        "Response Verify Source Identifier",
        "verify_source_identifier",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/identifiers/{identifier_id}:reject",
        "reject_source_identifier",
        "reject_source_identifier",
        "IdentifierStatusIn",
        "Response Reject Source Identifier",
        "reject_source_identifier",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/sources/{source_id}",
        "get_literature_source",
        "get_literature_source",
        None,
        "Response Get Literature Source",
        "get_literature_source",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/sources:resolve",
        "find_source_by_identifier",
        "find_source_by_identifier",
        None,
        "Response Find Source By Identifier",
        "find_source_by_identifier",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/sources/{source_id}/identifiers",
        "list_source_identifiers",
        "list_source_identifiers",
        None,
        "Response List Source Identifiers",
        "list_source_identifiers",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/sources/{source_id}/versions",
        "create_source_version",
        "create",
        "SourceVersionIn",
        "SourceVersionResult",
        "create_source_version",
    ),
    RouteContract(
        "patch",
        "/v1/projects/{project_id}/literature/source-versions/{source_version_id}",
        "update_source_version_draft",
        "update",
        "SourceVersionIn",
        "SourceVersionResult",
        "update_source_version_draft",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-versions/{source_version_id}:freeze",
        "freeze_source_version",
        "freeze",
        None,
        "SourceVersionResult",
        "freeze_source_version",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-versions/{source_version_id}:abandon",
        "abandon_source_version",
        "abandon",
        None,
        "SourceVersionResult",
        "abandon_source_version",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/sources/{source_id}/versions",
        "list_source_versions",
        "list",
        None,
        "SourceVersionReadResult",
        "list_source_versions",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/source-versions/{source_version_id}",
        "get_source_version",
        "get",
        None,
        "SourceVersionReadResult",
        "get_source_version",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-merge-proposals",
        "propose_source_merge",
        "propose",
        "SourceMergeProposalIn",
        "SourceMergeProposalResult",
        "propose_source_merge",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:approve",
        "approve_source_merge",
        "decide",
        None,
        "SourceMergeDecisionResult",
        "approve_source_merge",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:reject",
        "reject_source_merge",
        "decide",
        "SourceMergeDecisionIn",
        "SourceMergeDecisionResult",
        "reject_source_merge",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:revoke",
        "revoke_source_merge_approval",
        "revoke",
        "SourceMergeDecisionIn",
        "SourceMergeRevocationResult",
        "revoke_source_merge_approval",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}",
        "get_source_merge_proposal",
        "get",
        None,
        "SourceMergeProposalStatus",
        "get_source_merge_proposal",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:consume",
        "consume_source_merge_proposal",
        "consume",
        "SourceMergeConsumeIn",
        "SourceMergeRecordResult",
        "consume_source_merge_proposal",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/search-coverage",
        "record_search_coverage",
        "record_search_coverage",
        "SearchCoverageIn",
        "SearchCoverageReadbackResponse",
        "record_search_coverage",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/search-coverage/{id}",
        "read_search_coverage",
        "read_search_coverage",
        None,
        "SearchCoverageReadbackResponse",
        "read_search_coverage",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/prior-art-relations",
        "record_prior_art_relation",
        "record_prior_art_relation",
        "PriorArtIn",
        "PriorArtReadbackResponse",
        "record_prior_art_relation",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/prior-art-relations/{id}",
        "read_prior_art_relation",
        "read_prior_art_relation",
        None,
        "PriorArtReadbackResponse",
        "read_prior_art_relation",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/prior-art-relations/selection",
        "select_prior_art_relation",
        "select_prior_art_relation",
        None,
        "PriorArtSelectionReadbackResponse",
        "select_prior_art_relation",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/novelty-assessments",
        "record_novelty_assessment",
        "record_novelty_assessment",
        "NoveltyAssessmentIn",
        "NoveltyReadbackResponse",
        "record_novelty_assessment",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/novelty-assessments/{id}",
        "read_novelty_assessment",
        "read_novelty_assessment",
        None,
        "NoveltyReadbackResponse",
        "read_novelty_assessment",
    ),
)


ROUTES += (
    RouteContract(
        "post",
        "/v1/projects/{project_id}/novelty-reviews",
        "record_novelty_review",
        "create",
        "NoveltyReviewIn",
        "NoveltyReviewReadbackResponse",
        "record_novelty_review",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/novelty-reviews/{id}",
        "read_novelty_review",
        "read",
        None,
        "NoveltyReviewReadbackResponse",
        "read_novelty_review",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/novelty-revision-actions",
        "record_novelty_revision",
        "record_novelty_revision",
        "NoveltyRevisionIn",
        "NoveltyRevisionReadbackResponse",
        "record_novelty_revision",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/novelty-revision-actions/{id}",
        "read_novelty_revision",
        "read_revision_action",
        None,
        "NoveltyRevisionReadbackResponse",
        "read_novelty_revision",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/novelty-revision-actions/{id}/re-reviews/{review_id}",
        "link_novelty_re_review",
        "record_concern_re_review",
        None,
        "NoveltyReReviewReadbackResponse",
        "link_novelty_re_review",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/novelty-revision-actions/{id}/re-reviews/{review_id}",
        "read_novelty_re_review",
        "read_novelty_re_review",
        None,
        "NoveltyReReviewReadbackResponse",
        "read_novelty_re_review",
    ),
)


def _ref_name(schema: dict[str, object]) -> str:
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "items" in schema:
        return str(schema["items"]["$ref"]).rsplit("/", 1)[-1]  # type: ignore[index]
    if "title" in schema:
        return str(schema["title"])
    raise AssertionError(f"schema has no reference or title: {schema}")


ROUTES += (
    RouteContract(
        "post",
        "/v1/projects/{project_id}/revision-decisions",
        "record_revision_decision",
        "record_revision_decision",
        "RevisionDecisionIn",
        "RevisionDecisionReadbackResponse",
        "record_revision_decision",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/revision-decisions/{id}",
        "get_revision_decision",
        "get_revision_decision",
        None,
        "RevisionDecisionReadbackResponse",
        "get_revision_decision",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/revision-actions",
        "record_revision_action",
        "record_revision_action",
        "RevisionActionIn",
        "RevisionActionReadbackResponse",
        "record_revision_action",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/revision-actions/{id}",
        "get_revision_action",
        "read_revision_action",
        None,
        "RevisionActionReadbackResponse",
        "get_revision_action",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/revision-actions/{id}/re-reviews/{review_id}",
        "record_revision_re_review",
        "record_concern_re_review",
        None,
        "ConcernReReviewReadbackResponse",
        "record_revision_re_review",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/revision-actions/{id}/re-reviews/{review_id}",
        "get_revision_re_review",
        "get_concern_re_review",
        None,
        "ConcernReReviewReadbackResponse",
        "get_revision_re_review",
    ),
    RouteContract(
        "post",
        "/v1/projects/{project_id}/issue-dispositions",
        "record_issue_disposition",
        "record_issue_disposition",
        "IssueDispositionIn",
        "IssueDispositionReadbackResponse",
        "record_issue_disposition",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/issue-dispositions/{id}",
        "get_issue_disposition",
        "get_issue_disposition",
        None,
        "IssueDispositionReadbackResponse",
        "get_issue_disposition",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/review-issues/{id}/history",
        "get_issue_history",
        "get_issue_history",
        None,
        "IssueHistoryReadbackResponse",
        "get_issue_history",
    ),
)


ROUTES += (
    RouteContract(
        "post",
        "/v1/projects/{project_id}/manuscript-rejection-reconsiderations",
        "record_manuscript_rejection_reconsideration",
        "record_manuscript_rejection_reconsideration",
        "ManuscriptReconsiderationIn",
        "RejectionReconsiderationReadbackResponse",
        "record_manuscript_rejection_reconsideration",
    ),
    RouteContract(
        "get",
        "/v1/projects/{project_id}/manuscript-rejection-reconsiderations/{id}",
        "get_manuscript_rejection_reconsideration",
        "get_manuscript_rejection_reconsideration",
        None,
        "RejectionReconsiderationReadbackResponse",
        "get_manuscript_rejection_reconsideration",
    ),
)


def test_all_63_routes_have_exact_schema_operation_and_application_bindings() -> None:
    assert len(ROUTES) == 94
    schema = create_app(EmptyServices()).openapi()
    actual = {
        (method, path)
        for path, operations in schema["paths"].items()
        if path.startswith("/v1/")
        for method in operations
        if method in {"get", "post", "patch", "put", "delete"}
    }
    assert actual == {(item.method, item.path) for item in ROUTES}
    assert len({item.operation_id for item in ROUTES}) == 94

    for item in ROUTES:
        operation = schema["paths"][item.path][item.method]
        body = (
            operation.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema")
        )
        success = next(
            response
            for status, response in operation["responses"].items()
            if status.startswith("2")
        )
        response = success["content"]["application/json"]["schema"]
        assert (_ref_name(body) if body else None) == item.request_schema
        assert _ref_name(response) == item.response_schema
        assert operation["operationId"] == item.operation_id
        source = inspect.getsource(getattr(routes, item.endpoint))
        if item.handler == "_execution_command":
            assert "_execution_command(" in source
        else:
            assert f".{item.handler}(" in source


def test_pr204_execution_list_exposes_optional_after_cursor() -> None:
    schema = create_app(EmptyServices()).openapi()
    operation = schema["paths"]["/v1/literature/search-executions"]["get"]
    query_parameters = {
        parameter["name"] for parameter in operation["parameters"] if parameter["in"] == "query"
    }
    assert {"project_id", "limit", "after"} <= query_parameters
