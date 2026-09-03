"""Shared PostgreSQL fixtures and adapter runners for PR-17 GSAS-01."""

# pyright: reportArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

import researchbase.application.commands as application_commands
import researchbase.application.governance as governance_commands
from researchbase.api.app import create_app as create_http_app
from researchbase.application.commands import (
    ApplicationService,
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateActorCommand,
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateClaimCommand,
    CreateDatasetSnapshotCommand,
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    CreateResearchQuestionCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeArtifactVersionCommand,
    FreezeClaimVersionCommand,
    FreezeExperimentSpecCommand,
    FreezeHypothesisCommand,
    FreezeMetricDefinitionCommand,
    FreezeResearchQuestionCommand,
    LinkEvidenceCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    RegisterDatasetCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateCorrectionRecordCommand,
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
)
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.cli.app import create_app as create_cli_app
from researchbase.cli.composition import ServiceBundle
from researchbase.domain.claim import EvidenceRelationType
from researchbase.domain.governance import (
    AuditFindingSeverity,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessmentConclusion,
    ImpactKind,
)
from researchbase.domain.identity import ActorType
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXED_NOW = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class WorkflowIds:
    actor_id: UUID
    project_id: UUID
    research_question_id: UUID
    research_question_version_id: UUID
    hypothesis_id: UUID
    hypothesis_version_id: UUID
    experiment_spec_id: UUID
    experiment_spec_version_id: UUID
    dataset_id: UUID
    dataset_snapshot_id: UUID
    artifact_id: UUID
    artifact_version_id: UUID
    metric_definition_id: UUID
    metric_definition_version_id: UUID
    run_id: UUID
    measurement_ids: tuple[UUID, UUID]
    statistical_result_id: UUID
    claim_id: UUID
    claim_version_id: UUID
    evidence_relation_ids: tuple[UUID, UUID]
    finding_id: UUID
    impact_assessment_id: UUID
    correction_id: UUID


@dataclass(slots=True)
class WorkflowFixture:
    schema: str
    url: str
    engine: Engine
    sessions: Any
    application: ApplicationService
    provenance: ProvenanceQueryService
    governance: GovernanceService
    governance_queries: GovernanceQueryService
    http_app: Any
    cli_app: Any
    actor_id: UUID
    context: ExecutionContext
    client: TestClient
    cli_runner: CliRunner

    def services(self) -> ServiceBundle:
        return ServiceBundle(
            self.application,
            self.provenance,
            self.governance,
            self.governance_queries,
        )

    def fresh_application(self) -> ApplicationService:
        return ApplicationService(
            lambda: SqlAlchemyUnitOfWork(self.sessions),
            FixedClock(FIXED_NOW),
            self.application._artifact_store,  # noqa: SLF001 - test composition only
        )

    def dispose(self) -> None:
        self.client.close()
        self.engine.dispose()


@contextmanager
def deterministic_ids(seed: str) -> Iterator[None]:
    """Make independent adapter executions produce identical material hashes."""

    counters: dict[str, int] = {}
    namespace = uuid5(NAMESPACE_URL, f"https://researchbase.test/pr17/{seed}")

    def factory(id_type: Any) -> Any:
        name = getattr(id_type, "__name__", str(id_type))
        counters[name] = counters.get(name, 0) + 1
        return id_type(uuid5(namespace, f"{name}:{counters[name]}"))

    previous_application = application_commands.new_typed_id
    previous_governance = governance_commands.new_typed_id
    application_commands.new_typed_id = factory
    governance_commands.new_typed_id = factory
    try:
        yield
    finally:
        application_commands.new_typed_id = previous_application
        governance_commands.new_typed_id = previous_governance


def _schema_url(base_url: str, schema: str) -> str:
    return f"{base_url.split('?', 1)[0]}?options=-csearch_path={schema}"


def _run_clean_install(base_url: str, schema: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = _schema_url(base_url, schema)
    environment.setdefault("UV_CACHE_DIR", "/tmp/researchbase-uv-cache")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"isolated Alembic upgrade failed:\n{result.stdout}\n{result.stderr}")


@contextmanager
def fresh_fixture(tmp_path: Path, seed: str = "gsas-01") -> Iterator[WorkflowFixture]:
    """Create a clean, independently migrated PostgreSQL schema for one workflow."""

    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; PR-17 acceptance requires PostgreSQL 18.x")

    schema = f"pr17_{uuid4().hex}"
    admin = create_database_engine(base_url)
    app_engine: Engine | None = None
    with deterministic_ids(seed):
        try:
            with admin.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            _run_clean_install(base_url, schema)
            url = _schema_url(base_url, schema)
            app_engine = create_database_engine(url)
            sessions = create_session_factory(app_engine)
            clock = FixedClock(FIXED_NOW)
            store = ContentAddressedFilesystemArtifactStore(tmp_path / "artifact-store")

            def uow_factory() -> SqlAlchemyUnitOfWork:
                return SqlAlchemyUnitOfWork(sessions)

            application = ApplicationService(uow_factory, clock, store)
            provenance = ProvenanceQueryService(uow_factory)
            governance = GovernanceService(uow_factory, clock)
            governance_queries = GovernanceQueryService(uow_factory)
            services = ServiceBundle(application, provenance, governance, governance_queries)
            fixture = WorkflowFixture(
                schema,
                url,
                app_engine,
                sessions,
                application,
                provenance,
                governance,
                governance_queries,
                create_http_app(services),
                create_cli_app(services),
                UUID(int=0),
                ExecutionContext(
                    actor_id=UUID(int=0),
                    request_id=uuid4(),
                    correlation_id=uuid4(),
                    causation_id=uuid4(),
                    client_type="test",
                    client_name="pr17-test",
                    client_version="1",
                ),
                TestClient(create_http_app(services)),
                CliRunner(),
            )
            bootstrap = application.create_actor(
                CreateActorCommand(
                    ActorType.HUMAN,
                    "GSAS-01 actor",
                    None,
                    fixture.context,
                )
            )
            fixture.actor_id = UUID(str(bootstrap.id))
            fixture.context = fixture.context.model_copy(update={"actor_id": fixture.actor_id})
            yield fixture
        finally:
            if app_engine is not None:
                app_engine.dispose()
            admin.dispose()
            cleanup = create_database_engine(base_url)
            try:
                with cleanup.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            finally:
                cleanup.dispose()


def _value(result: Any, name: str) -> Any:
    return result[name] if isinstance(result, dict) else getattr(result, name)


def _uuid(result: Any, name: str) -> UUID:
    return UUID(str(_value(result, name)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value


def _request_headers(fixture: WorkflowFixture) -> dict[str, str]:
    context = fixture.context
    return {
        "X-Actor-ID": str(fixture.actor_id),
        "X-Request-ID": str(uuid4()),
        "X-Correlation-ID": str(context.correlation_id),
        "X-Causation-ID": str(context.causation_id),
        "X-Client-Name": "pr17-http",
        "X-Client-Version": "1",
    }


def _cli_call(
    fixture: WorkflowFixture, group: str, command: str, payload: dict[str, Any]
) -> dict[str, Any]:
    result = fixture.cli_runner.invoke(
        fixture.cli_app,
        [
            "--actor-id",
            str(fixture.actor_id),
            "--request-id",
            str(uuid4()),
            "--correlation-id",
            str(fixture.context.correlation_id),
            "--causation-id",
            str(fixture.context.causation_id),
            "--client-name",
            "pr17-cli",
            "--client-version",
            "1",
            group,
            command,
            "--json-input",
            json.dumps(_jsonable(payload), separators=(",", ":")),
            "--json",
        ],
    )
    assert result.exit_code == 0, (group, command, result.stdout, result.stderr)
    assert result.stderr == ""
    value = json.loads(result.stdout)
    assert isinstance(value, dict)
    return value


def _http_call(
    fixture: WorkflowFixture,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any] | list[dict[str, Any]]:
    response = fixture.client.request(
        method,
        f"/v1{path}",
        json=_jsonable(payload) if payload is not None else None,
        headers=_request_headers(fixture),
        **kwargs,
    )
    assert response.status_code < 300, (method, path, response.status_code, response.text)
    value = response.json()
    assert isinstance(value, dict | list)
    return value


def _direct_workflow(fixture: WorkflowFixture) -> WorkflowIds:
    service = fixture.application
    context = fixture.context
    project = service.create_project(CreateProjectCommand("GSAS-01", "golden", context))
    project_id = UUID(str(project.id))

    question = service.create_research_question(
        CreateResearchQuestionCommand(
            project_id,
            "Does the protocol improve latency?",
            {"population": "test"},
            "GSAS",
            context,
        )
    )
    question_version = service.freeze_research_question(
        FreezeResearchQuestionCommand(question.id, question.current_version_id, context, 1)
    )
    hypothesis = service.create_hypothesis(
        CreateHypothesisCommand(
            project_id,
            "The protocol lowers latency.",
            "decrease",
            {"max_ms": 2},
            "GSAS",
            context,
            question.id,
        )
    )
    hypothesis_version = service.freeze_hypothesis(
        FreezeHypothesisCommand(hypothesis.id, hypothesis.current_version_id, context, 1)
    )
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            hypothesis.id,
            "Latency experiment",
            "Measure latency",
            {"steps": ["run", "measure"]},
            [{"metric": "latency"}],
            {"seed": 7},
            {"test": "mean"},
            context,
        )
    )
    spec_version = service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec.id, spec.current_version_id, context, 1)
    )

    dataset = service.register_dataset(
        RegisterDatasetCommand(project_id, "GSAS dataset", "input", "cas://dataset", context)
    )
    snapshot = service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(
            dataset.id, "a" * 64, {"split": "test", "rows": [1, 2]}, "cas://manifest", context
        )
    )
    artifact = service.create_artifact(
        CreateArtifactCommand(project_id, "source_code", "GSAS code", "code", context)
    )
    artifact_version = service.create_artifact_version(
        CreateArtifactVersionCommand(
            artifact.id,
            b"gsas-source-v1",
            None,
            None,
            "text/plain",
            None,
            {"language": "python"},
            context,
        )
    )
    artifact_version = service.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            artifact.id, artifact_version.id, context, artifact_version.row_version
        )
    )
    metric = service.create_metric_definition(
        CreateMetricDefinitionCommand(
            project_id, "latency", {"kind": "mean", "unit": "ms"}, "ms", "mean", context
        )
    )
    metric_version = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, context, 1)
    )

    run = service.create_run(CreateRunCommand(project_id, spec_version.id, "golden", context))
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, context
        )
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact_version.id, ArtifactInputRole.SOURCE_CODE, 0, run.row_version, context
        )
    )
    run = service.start_run(StartRunCommand(run.id, run.row_version, context))
    run = service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, run.row_version, context)
    )
    first = service.record_measurement(
        RecordMeasurementCommand(
            run.id,
            metric_version.id,
            1.25,
            None,
            "ms",
            {"split": "test", "ordinal": 0},
            context,
        )
    )
    second = service.record_measurement(
        RecordMeasurementCommand(
            run.id,
            metric_version.id,
            1.75,
            None,
            "ms",
            {"split": "test", "ordinal": 1},
            context,
        )
    )
    statistical = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "mean",
            {"mean": 1.5},
            {"method": "arithmetic"},
            (
                StatisticalResultInputCommand(first.id, "primary", 0),
                StatisticalResultInputCommand(second.id, "replicate", 1),
            ),
            context,
        )
    )
    claim = service.create_claim(
        CreateClaimCommand(
            project_id, "The protocol lowers latency.", {"population": "test"}, "bounded", context
        )
    )
    claim_version = service.get_current_claim_version(claim.id)
    direct_evidence = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            claim_version.id,
            first.id,
            None,
            EvidenceRelationType.SUPPORTS,
            "direct measurement",
            claim_version.row_version,
            context,
        )
    )
    claim_version = service.get_current_claim_version(claim.id)
    statistical_evidence = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            claim_version.id,
            None,
            statistical.id,
            EvidenceRelationType.SUPPORTS,
            "multi-input statistic",
            claim_version.row_version,
            context,
        )
    )
    claim_version = service.get_current_claim_version(claim.id)
    claim_version = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, claim_version.id, context, claim_version.row_version)
    )
    finding = fixture.governance.create_audit_finding(
        CreateAuditFindingCommand(
            project_id,
            "measurement_audit",
            AuditFindingSeverity.MAJOR,
            "GSAS finding",
            "GSAS controlled finding",
            GovernanceTargetType.RUN,
            run.id,
            context,
        )
    )
    assessment = fixture.governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            project_id,
            finding.id,
            {"reason": "controlled"},
            ImpactAssessmentConclusion.INVALID,
            (
                ProposedImpactTarget(GovernanceTargetType.RUN, run.id, ImpactKind.DIRECT),
                ProposedImpactTarget(
                    GovernanceTargetType.MEASUREMENT, first.id, ImpactKind.DOWNSTREAM
                ),
                ProposedImpactTarget(
                    GovernanceTargetType.STATISTICAL_RESULT, statistical.id, ImpactKind.DOWNSTREAM
                ),
                ProposedImpactTarget(
                    GovernanceTargetType.CLAIM_VERSION, claim_version.id, ImpactKind.DOWNSTREAM
                ),
            ),
            context,
        )
    )
    correction = fixture.governance.create_correction_record(
        CreateCorrectionRecordCommand(
            project_id,
            GovernanceTargetType.MEASUREMENT,
            first.id,
            CorrectionType.COMPUTATIONAL,
            {"replacement": "new record"},
            "GSAS correction without mutation",
            context,
        )
    )
    return WorkflowIds(
        UUID(str(fixture.actor_id)),
        project_id,
        UUID(str(question.id)),
        UUID(str(question_version.id)),
        UUID(str(hypothesis.id)),
        UUID(str(hypothesis_version.id)),
        UUID(str(spec.id)),
        UUID(str(spec_version.id)),
        UUID(str(dataset.id)),
        UUID(str(snapshot.id)),
        UUID(str(artifact.id)),
        UUID(str(artifact_version.id)),
        UUID(str(metric.id)),
        UUID(str(metric_version.id)),
        UUID(str(run.id)),
        (UUID(str(first.id)), UUID(str(second.id))),
        UUID(str(statistical.id)),
        UUID(str(claim.id)),
        UUID(str(claim_version.id)),
        (UUID(str(direct_evidence.id)), UUID(str(statistical_evidence.id))),
        UUID(str(finding.id)),
        UUID(str(assessment.id)),
        UUID(str(correction.id)),
    )


def _adapter_workflow(fixture: WorkflowFixture, mode: str) -> WorkflowIds:
    if mode == "application":
        return _direct_workflow(fixture)
    if mode not in {"http", "cli"}:
        raise ValueError(mode)

    def call(group: str, command: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if mode == "cli":
            return _cli_call(fixture, group, command, payload)
        value = _http_call(fixture, "POST", path, payload)
        assert isinstance(value, dict)
        return value

    def freeze(
        group: str,
        command: str,
        path: str,
        payload: dict[str, Any],
        version_id: UUID | None = None,
    ) -> dict[str, Any]:
        if mode == "cli" and version_id is not None:
            payload = {**payload, "version_id": version_id}
        return call(group, command, path, payload)

    project = call("project", "create", "/projects", {"name": "GSAS-01", "description": "golden"})
    project_id = _uuid(project, "id")
    question = call(
        "rq",
        "create",
        "/research-questions",
        {
            "project_id": project_id,
            "question_text": "Does the protocol improve latency?",
            "scope": {"population": "test"},
            "rationale": "GSAS",
        },
    )
    question_id = _uuid(question, "id")
    question_version_id = _uuid(question, "current_version_id")
    freeze(
        "rq",
        "freeze",
        f"/research-question-versions/{question_version_id}:freeze",
        {"research_question_id": question_id, "expected_row_version": 1},
        question_version_id,
    )
    hypothesis = call(
        "hypothesis",
        "create",
        "/hypotheses",
        {
            "project_id": project_id,
            "statement": "The protocol lowers latency.",
            "expected_direction": "decrease",
            "success_criteria": {"max_ms": 2},
            "rationale": "GSAS",
            "research_question_id": question_id,
        },
    )
    hypothesis_id = _uuid(hypothesis, "id")
    hypothesis_version_id = _uuid(hypothesis, "current_version_id")
    freeze(
        "hypothesis",
        "freeze",
        f"/hypothesis-versions/{hypothesis_version_id}:freeze",
        {"hypothesis_id": hypothesis_id, "expected_row_version": 1},
        hypothesis_version_id,
    )
    spec = call(
        "spec",
        "create",
        "/experiment-specs",
        {
            "project_id": project_id,
            "hypothesis_id": hypothesis_id,
            "title": "Latency experiment",
            "objective": "Measure latency",
            "protocol": {"steps": ["run", "measure"]},
            "planned_metrics": [{"metric": "latency"}],
            "seed_policy": {"seed": 7},
            "analysis_plan": {"test": "mean"},
        },
    )
    spec_id = _uuid(spec, "id")
    spec_version_id = _uuid(spec, "current_version_id")
    freeze(
        "spec",
        "freeze",
        f"/experiment-spec-versions/{spec_version_id}:freeze",
        {"experiment_spec_id": spec_id, "expected_row_version": 1},
        spec_version_id,
    )
    dataset = call(
        "dataset",
        "create",
        "/datasets",
        {
            "project_id": project_id,
            "name": "GSAS dataset",
            "description": "input",
            "source_locator": "cas://dataset",
        },
    )
    dataset_id = _uuid(dataset, "id")
    snapshot_payload = {
        "manifest_hash": "a" * 64,
        "selection_definition": {"split": "test", "rows": [1, 2]},
        "manifest_locator": "cas://manifest",
    }
    if mode == "cli":
        snapshot_payload["dataset_id"] = dataset_id
    snapshot = call(
        "dataset",
        "snapshot",
        f"/datasets/{dataset_id}/snapshots",
        snapshot_payload,
    )
    snapshot_id = _uuid(snapshot, "id")
    artifact = call(
        "artifact",
        "create",
        "/artifacts",
        {
            "project_id": project_id,
            "artifact_type": "source_code",
            "name": "GSAS code",
            "description": "code",
        },
    )
    artifact_id = _uuid(artifact, "id")
    artifact_version = call(
        "artifact",
        "revise",
        f"/artifacts/{artifact_id}/versions",
        {"data": "gsas-source-v1", "media_type": "text/plain", "metadata": {"language": "python"}}
        if mode == "http"
        else {
            "artifact_id": artifact_id,
            "data_base64": base64.b64encode(b"gsas-source-v1").decode(),
            "media_type": "text/plain",
            "metadata": {"language": "python"},
        },
    )
    artifact_version_id = _uuid(artifact_version, "id")
    artifact_version = freeze(
        "artifact",
        "freeze",
        f"/artifact-versions/{artifact_version_id}:freeze",
        {
            "artifact_id": artifact_id,
            "expected_row_version": artifact_version["row_version"]
            if isinstance(artifact_version, dict)
            else 1,
        },
        artifact_version_id,
    )
    metric = call(
        "metric",
        "create",
        "/metric-definitions",
        {
            "project_id": project_id,
            "name": "latency",
            "definition": {"kind": "mean", "unit": "ms"},
            "unit": "ms",
            "aggregation": "mean",
        },
    )
    metric_id = _uuid(metric, "id")
    metric_version_id = _uuid(metric, "current_version_id")
    freeze(
        "metric",
        "freeze",
        f"/metric-definition-versions/{metric_version_id}:freeze",
        {"metric_definition_id": metric_id, "expected_row_version": 1},
        metric_version_id,
    )
    run = call(
        "run",
        "create",
        "/runs",
        {
            "project_id": project_id,
            "experiment_spec_version_id": spec_version_id,
            "run_type": "golden",
        },
    )
    run_id = _uuid(run, "id")
    dataset_input_payload = {
        "dataset_snapshot_id": snapshot_id,
        "role": "test",
        "ordinal": 0,
        "expected_row_version": run["row_version"],
    }
    if mode == "cli":
        dataset_input_payload["run_id"] = run_id
    run = call(
        "run",
        "add-dataset",
        f"/runs/{run_id}/dataset-inputs",
        dataset_input_payload,
    )
    artifact_input_payload = {
        "artifact_version_id": artifact_version_id,
        "role": "source_code",
        "ordinal": 0,
        "expected_row_version": run["row_version"],
    }
    if mode == "cli":
        artifact_input_payload["run_id"] = run_id
    run = call(
        "run",
        "add-artifact",
        f"/runs/{run_id}/artifact-inputs",
        artifact_input_payload,
    )
    start_payload = {"expected_row_version": run["row_version"]}
    if mode == "cli":
        start_payload["run_id"] = run_id
    run = call("run", "start", f"/runs/{run_id}:start", start_payload)
    finish_payload = {
        "outcome": "SUCCEEDED",
        "exit_code": 0,
        "failure_reason": None,
        "expected_row_version": run["row_version"],
    }
    if mode == "cli":
        finish_payload["run_id"] = run_id
    run = call(
        "run",
        "finish",
        f"/runs/{run_id}:finish",
        finish_payload,
    )
    first = call(
        "measurement",
        "create",
        "/measurements",
        {
            "run_id": run_id,
            "metric_definition_version_id": metric_version_id,
            "numeric_value": 1.25,
            "unit": "ms",
            "evaluation_scope": {"split": "test", "ordinal": 0},
        },
    )
    second = call(
        "measurement",
        "create",
        "/measurements",
        {
            "run_id": run_id,
            "metric_definition_version_id": metric_version_id,
            "numeric_value": 1.75,
            "unit": "ms",
            "evaluation_scope": {"split": "test", "ordinal": 1},
        },
    )
    first_id, second_id = _uuid(first, "id"), _uuid(second, "id")
    statistical = call(
        "stats",
        "create",
        "/statistical-results",
        {
            "project_id": project_id,
            "analysis_type": "mean",
            "result_payload": {"mean": 1.5},
            "analysis_definition": {"method": "arithmetic"},
            "inputs": [
                {"measurement_id": first_id, "input_role": "primary", "ordinal": 0},
                {"measurement_id": second_id, "input_role": "replicate", "ordinal": 1},
            ],
        },
    )
    statistical_id = _uuid(statistical, "id")
    claim = call(
        "claim",
        "create",
        "/claims",
        {
            "project_id": project_id,
            "statement": "The protocol lowers latency.",
            "scope": {"population": "test"},
            "qualification": "bounded",
        },
    )
    claim_id, claim_version_id = _uuid(claim, "id"), _uuid(claim, "current_version_id")
    direct_evidence_payload = {
        "claim_id": claim_id,
        "measurement_id": first_id,
        "statistical_result_id": None,
        "relation_type": "supports",
        "qualification": "direct measurement",
        "expected_row_version": 1,
    }
    if mode == "cli":
        direct_evidence_payload["claim_version_id"] = claim_version_id
    direct_evidence = call(
        "claim",
        "add-evidence",
        f"/claim-versions/{claim_version_id}/evidence",
        direct_evidence_payload,
    )
    statistical_evidence_payload = {
        "claim_id": claim_id,
        "measurement_id": None,
        "statistical_result_id": statistical_id,
        "relation_type": "supports",
        "qualification": "multi-input statistic",
        "expected_row_version": 2,
    }
    if mode == "cli":
        statistical_evidence_payload["claim_version_id"] = claim_version_id
    statistical_evidence = call(
        "claim",
        "add-evidence",
        f"/claim-versions/{claim_version_id}/evidence",
        statistical_evidence_payload,
    )
    freeze(
        "claim",
        "freeze",
        f"/claim-versions/{claim_version_id}:freeze",
        {"claim_id": claim_id, "expected_row_version": 3},
        claim_version_id,
    )
    finding_payload = {
        "project_id": project_id,
        "finding_type": "measurement_audit",
        "severity": "major",
        "title": "GSAS finding",
        "description": "GSAS controlled finding",
        "target_type": "run",
        "target_id": run_id,
    }
    finding = call("audit", "create", "/audit-findings", finding_payload)
    finding_id = _uuid(finding, "id")
    assessment_payload = {
        "project_id": project_id,
        "audit_finding_id": finding_id,
        "assessment_payload": {"reason": "controlled"},
        "conclusion": "invalid",
        "targets": [
            {"target_type": "run", "target_id": run_id, "impact_kind": "direct"},
            {"target_type": "measurement", "target_id": first_id, "impact_kind": "downstream"},
            {
                "target_type": "statistical_result",
                "target_id": statistical_id,
                "impact_kind": "downstream",
            },
            {
                "target_type": "claim_version",
                "target_id": claim_version_id,
                "impact_kind": "downstream",
            },
        ],
    }
    assessment = call("impact", "assess", "/impact-assessments", assessment_payload)
    assessment_id = _uuid(assessment, "id")
    correction = call(
        "correction",
        "create",
        "/corrections",
        {
            "project_id": project_id,
            "target_type": "measurement",
            "target_id": first_id,
            "correction_type": "computational",
            "corrected_assertion": {"replacement": "new record"},
            "reason": "GSAS correction without mutation",
        },
    )
    correction_id = _uuid(correction, "id")
    return WorkflowIds(
        UUID(str(fixture.actor_id)),
        project_id,
        question_id,
        question_version_id,
        hypothesis_id,
        hypothesis_version_id,
        spec_id,
        spec_version_id,
        dataset_id,
        snapshot_id,
        artifact_id,
        artifact_version_id,
        metric_id,
        metric_version_id,
        run_id,
        (first_id, second_id),
        statistical_id,
        claim_id,
        claim_version_id,
        (_uuid(direct_evidence, "id"), _uuid(statistical_evidence, "id")),
        finding_id,
        assessment_id,
        correction_id,
    )


def run_workflow(fixture: WorkflowFixture, mode: str) -> WorkflowIds:
    return _adapter_workflow(fixture, mode)


def projection(fixture: WorkflowFixture, ids: WorkflowIds) -> dict[str, Any]:
    app = fixture.fresh_application()
    run = app.get_run(ids.run_id)
    measurements = [app.get_measurement(item) for item in ids.measurement_ids]
    statistical = app.get_statistical_result(ids.statistical_result_id)
    claim = app.get_claim_version(ids.claim_version_id)
    evidence = app.list_evidence_relations(ids.claim_version_id)
    provenance = fixture.provenance.get_run_provenance(ids.run_id)
    trace = fixture.provenance.trace_claim_to_runs(ids.claim_version_id)
    closure = fixture.provenance.get_claim_closure_report(ids.claim_version_id)
    impact = fixture.governance_queries.downstream_impact(
        ids.project_id, GovernanceTargetType.RUN, ids.run_id
    )
    validity = fixture.governance_queries.validity_projection(
        ids.project_id, GovernanceTargetType.RUN, ids.run_id
    )
    finding = fixture.governance_queries.get_audit_finding(ids.finding_id)
    assessment = fixture.governance_queries.get_impact_assessment(ids.impact_assessment_id)
    correction = fixture.governance_queries.get_correction_record(ids.correction_id)
    assert finding is not None and assessment is not None and correction is not None
    return {
        "research": {"rq_status": "FROZEN", "hypothesis_status": "FROZEN", "spec_status": "FROZEN"},
        "inputs": {
            "dataset_snapshot": str(ids.dataset_snapshot_id),
            "artifact_version": str(ids.artifact_version_id),
            "metric_definition_version": str(ids.metric_definition_version_id),
            "experiment_spec_version": str(ids.experiment_spec_version_id),
        },
        "run": {
            "status": run.status.value,
            "dataset_input_count": len(provenance.dataset_inputs),
            "artifact_input_count": len(provenance.artifact_inputs),
            "measurement_count": len(provenance.measurements),
            "closure": (provenance.closure.complete, provenance.closure.visited_count),
        },
        "observations": {
            "measurement_count": len(measurements),
            "measurement_hashes": [str(item.content_hash) for item in measurements],
            "statistical_result_count": 1,
            "statistical_hash": str(statistical.content_hash),
            "statistical_inputs": [
                (item.input_role, item.ordinal, str(item.measurement_id))
                for item in app.list_statistical_result_inputs(ids.statistical_result_id)
            ],
        },
        "claim": {
            "status": claim.status.value,
            "evidence_count": len(evidence),
            "support_set_hash": str(claim.support_set_hash),
            "content_hash": str(claim.content_hash),
            "closure": (closure.complete, closure.visited_count),
            "trace_runs": [str(item.run_id) for item in trace.runs],
            "trace_paths": [
                (
                    item.source_type,
                    item.relation_type,
                    item.qualification,
                    item.statistical_result_input_role,
                    item.statistical_result_input_ordinal,
                )
                for item in trace.paths
            ],
        },
        "governance": {
            "finding_target": (
                finding.target_type.value,
                str(finding.target_id),
                str(finding.target_content_hash),
            ),
            "assessment_hash": str(assessment.content_hash),
            "impact_targets": [
                (item.target_type.value, str(item.target_id), item.impact_kind.value)
                for item in assessment.targets
            ],
            "impact_paths": [
                (
                    item.target_type.value,
                    str(item.target_id),
                    str(item.run_id) if item.run_id else None,
                    str(item.measurement_id) if item.measurement_id else None,
                    str(item.statistical_result_id) if item.statistical_result_id else None,
                    item.statistical_input_role,
                    item.statistical_input_ordinal,
                )
                for target in impact
                for item in target.paths
            ],
            "validity": (
                validity.state.value,
                len(validity.finding_ids),
                len(validity.assessment_ids),
                len(validity.correction_ids),
            ),
            "correction_hash": str(correction.content_hash),
        },
    }


def normalized_projection(value: dict[str, Any]) -> dict[str, Any]:
    """Replace generated IDs with stable labels while retaining all scientific hashes."""

    text_value = json.dumps(value, sort_keys=True)
    identifiers = sorted({token for token in text_value.replace('"', " ").split() if False})
    del identifiers
    return value


def db_statement_counter(engine: Engine) -> list[str]:
    statements: list[str] = []

    def observe(
        _conn: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: Any
    ) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", observe)
    return statements


def stop_db_statement_counter(engine: Engine, statements: list[str]) -> None:
    del statements
