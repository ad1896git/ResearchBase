from __future__ import annotations

from collections.abc import Callable, Iterator
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select

from researchbase.application.commands import (
    CreateArtifactVersionCommand,
    CreateClaimCommand,
    CreateDatasetSnapshotCommand,
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    CreateResearchQuestionCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
)
from researchbase.application.governance import (
    CreateCorrectionRecordCommand,
    CreateImpactAssessmentCommand,
)
from researchbase.domain.artifact import ArtifactId
from researchbase.domain.claim import ClaimVersionId
from researchbase.domain.evidence import DatasetId, DatasetSnapshot, DatasetSnapshotId
from researchbase.domain.experiment import ExperimentSpecVersionId
from researchbase.domain.governance import (
    CorrectionRecord,
    CorrectionRecordId,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessment,
    ImpactAssessmentConclusion,
    ImpactAssessmentId,
    calculate_correction_record_hash,
    calculate_impact_assessment_hash,
)
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.metric import MetricDefinitionVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisVersionId, ResearchQuestionVersionId
from researchbase.domain.run import RunId
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.frozen_json import thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.persistence.governance_repository import (
    SqlAlchemyGovernanceRepository,
    _correction_record_from_model,
    _impact_assessment_from_models,
)
from researchbase.persistence.models import (
    ArtifactVersionModel,
    ClaimVersionModel,
    CorrectionRecordModel,
    DatasetSnapshotModel,
    ExperimentSpecVersionModel,
    HypothesisVersionModel,
    ImpactAssessmentModel,
    MeasurementModel,
    MetricDefinitionVersionModel,
    ResearchQuestionVersionModel,
    StatisticalResultModel,
)
from researchbase.persistence.repositories import (
    SqlAlchemyArtifactVersionRepository,
    SqlAlchemyClaimRepository,
    SqlAlchemyDatasetSnapshotRepository,
    SqlAlchemyExperimentSpecRepository,
    SqlAlchemyHypothesisRepository,
    SqlAlchemyMeasurementRepository,
    SqlAlchemyMetricDefinitionVersionRepository,
    SqlAlchemyResearchQuestionRepository,
    SqlAlchemyStatisticalResultRepository,
    _artifact_version_from_model,
    _claim_version_from_model,
    _dataset_snapshot_from_model,
    _experiment_spec_version_from_model,
    _hypothesis_version_from_model,
    _measurement_from_model,
    _metric_definition_version_from_model,
    _research_question_version_from_model,
    _statistical_result_from_row,
)
from tests.e2e.support import WorkflowFixture, WorkflowIds, fresh_fixture, run_workflow
from tests.unit.domain.test_pr04_research import (
    _hypothesis_version,
    _research_question_version,
)
from tests.unit.domain.test_pr05_experiment import _version as experiment_version
from tests.unit.domain.test_pr07_artifact import version as artifact_version
from tests.unit.domain.test_pr08_metric import _version as metric_version
from tests.unit.domain.test_pr10_measurement import _measurement
from tests.unit.domain.test_pr11_statistical_result import make_result
from tests.unit.domain.test_pr12_claim import claim_version
from tests.unit.domain.test_pr14_governance import ACTOR_ID, NOW, PROJECT_ID

JsonFactory = Callable[[], object]
DtoFactory = Callable[[object], object]
DomainFactory = Callable[[object], Any]


def nested_json() -> dict[str, object]:
    return {"outer": {"items": [1, {"inner": {"value": "original"}}]}}


def mutation_names() -> tuple[str, ...]:
    return (
        "nested_scalar",
        "nested_dict",
        "list_append",
        "list_clear",
        "outer_replace",
        "nested_delete",
    )


def mutate(value: object, operation: str) -> None:
    root = value  # narrow once; every registry value uses this contract.
    assert isinstance(root, dict)
    outer = root["outer"]
    assert isinstance(outer, dict)
    items = outer["items"]
    assert isinstance(items, list)
    if operation == "nested_scalar":
        inner = items[1]["inner"]
        inner["value"] = "changed"
    elif operation == "nested_dict":
        items[1]["inner"] = {"value": "changed"}
    elif operation == "list_append":
        items.append({"new": True})
    elif operation == "list_clear":
        items.clear()
    elif operation == "outer_replace":
        root["outer"] = {"items": []}
    elif operation == "nested_delete":
        del items[1]["inner"]["value"]
    else:  # pragma: no cover - registry controls the operation set
        raise AssertionError(operation)


def context() -> ExecutionContext:
    return ExecutionContext(actor_id=uuid4(), request_id=uuid4(), client_type="test")


def dto_factories() -> dict[tuple[str, str], DtoFactory]:
    project_id = ProjectId(uuid4())
    return {
        ("ResearchQuestionVersion", "scope"): lambda value: CreateResearchQuestionCommand(
            project_id, "Question?", value, None, context()
        ),
        ("HypothesisVersion", "success_criteria"): lambda value: CreateHypothesisCommand(
            project_id, "Statement", None, value, None, context()
        ),
        ("ExperimentSpecVersion", "protocol"): lambda value: CreateExperimentSpecCommand(
            project_id, None, "Title", "Objective", value, None, None, None, context()
        ),
        ("ExperimentSpecVersion", "planned_metrics"): lambda value: CreateExperimentSpecCommand(
            project_id, None, "Title", "Objective", {}, value, None, None, context()
        ),
        ("ExperimentSpecVersion", "seed_policy"): lambda value: CreateExperimentSpecCommand(
            project_id, None, "Title", "Objective", {}, None, value, None, context()
        ),
        ("ExperimentSpecVersion", "analysis_plan"): lambda value: CreateExperimentSpecCommand(
            project_id, None, "Title", "Objective", {}, None, None, value, context()
        ),
        ("DatasetSnapshot", "selection_definition"): lambda value: CreateDatasetSnapshotCommand(
            DatasetId(uuid4()), "a" * 64, value, None, context()
        ),
        ("ArtifactVersion", "metadata"): lambda value: CreateArtifactVersionCommand(
            ArtifactId(uuid4()), b"bytes", None, None, "text/plain", None, value, context()
        ),
        ("MetricDefinitionVersion", "definition"): lambda value: CreateMetricDefinitionCommand(
            project_id, "metric", value, None, None, context()
        ),
        ("Measurement", "structured_value"): lambda value: RecordMeasurementCommand(
            RunId(uuid4()), MetricDefinitionVersionId(uuid4()), None, value, None, {}, context()
        ),
        ("Measurement", "evaluation_scope"): lambda value: RecordMeasurementCommand(
            RunId(uuid4()), MetricDefinitionVersionId(uuid4()), 1.0, None, None, value, context()
        ),
        ("StatisticalResult", "result_payload"): lambda value: RecordStatisticalResultCommand(
            project_id, "test", value, {}, (), context()
        ),
        ("StatisticalResult", "analysis_definition"): lambda value: RecordStatisticalResultCommand(
            project_id, "test", {}, value, (), context()
        ),
        ("ClaimVersion", "scope"): lambda value: CreateClaimCommand(
            project_id, "Claim", value, None, context()
        ),
        ("ImpactAssessment", "assessment_payload"): lambda value: CreateImpactAssessmentCommand(
            project_id, None, value, ImpactAssessmentConclusion.NO_IMPACT, (), context()
        ),
        ("CorrectionRecord", "corrected_assertion"): lambda value: CreateCorrectionRecordCommand(
            project_id,
            GovernanceTargetType.MEASUREMENT,
            uuid4(),
            CorrectionType.COMPUTATIONAL,
            value,
            "reason",
            context(),
        ),
    }


def dataset_snapshot(value: object) -> DatasetSnapshot:
    material = {"manifest_hash": "a" * 64, "selection_definition": value}
    return DatasetSnapshot(
        id=DatasetSnapshotId(uuid4()),
        dataset_id=DatasetId(uuid4()),
        manifest_hash=ContentHash("a" * 64),
        selection_definition=value,
        manifest_locator=None,
        content_hash=sha256_canonical_json(material),
        created_by=ActorId(uuid4()),
        created_at=NOW,
    )


def impact_assessment(value: object) -> ImpactAssessment:
    material: dict[str, Any] = dict(
        project_id=ProjectId(PROJECT_ID),
        audit_finding_id=None,
        assessment_payload=value,
        conclusion=ImpactAssessmentConclusion.NO_IMPACT,
        targets=(),
    )
    return ImpactAssessment(
        id=ImpactAssessmentId(uuid4()),
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
        content_hash=calculate_impact_assessment_hash(**material),
        **material,
    )


def correction_record(value: object) -> CorrectionRecord:
    material: dict[str, Any] = dict(
        project_id=ProjectId(PROJECT_ID),
        target_type=GovernanceTargetType.MEASUREMENT,
        target_id=uuid4(),
        target_content_hash=None,
        correction_type=CorrectionType.COMPUTATIONAL,
        corrected_assertion=value,
        reason="reason",
    )
    return CorrectionRecord(
        id=CorrectionRecordId(uuid4()),
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
        content_hash=calculate_correction_record_hash(**material),
        **material,
    )


def domain_factories() -> dict[tuple[str, str], DomainFactory]:
    return {
        ("ResearchQuestionVersion", "scope"): lambda value: replace(
            _research_question_version(), scope=value
        ),
        ("HypothesisVersion", "success_criteria"): lambda value: replace(
            _hypothesis_version(), success_criteria=value
        ),
        ("ExperimentSpecVersion", "protocol"): lambda value: experiment_version(protocol=value),
        ("ExperimentSpecVersion", "planned_metrics"): lambda value: experiment_version(
            planned_metrics=value
        ),
        ("ExperimentSpecVersion", "seed_policy"): lambda value: experiment_version(
            seed_policy=value
        ),
        ("ExperimentSpecVersion", "analysis_plan"): lambda value: experiment_version(
            analysis_plan=value
        ),
        ("DatasetSnapshot", "selection_definition"): dataset_snapshot,
        ("ArtifactVersion", "metadata"): lambda value: artifact_version(metadata=value),
        ("MetricDefinitionVersion", "definition"): lambda value: metric_version(definition=value),
        ("Measurement", "structured_value"): lambda value: _measurement(
            numeric_value=None, structured_value=value
        ),
        ("Measurement", "evaluation_scope"): lambda value: _measurement(evaluation_scope=value),
        ("StatisticalResult", "result_payload"): lambda value: make_result(result_payload=value),
        ("StatisticalResult", "analysis_definition"): lambda value: make_result(
            analysis_definition=value
        ),
        ("ClaimVersion", "scope"): lambda value: claim_version(scope=value),
        ("ImpactAssessment", "assessment_payload"): impact_assessment,
        ("CorrectionRecord", "corrected_assertion"): correction_record,
    }


@dataclass(frozen=True, slots=True)
class FieldCase:
    model: str
    field: str
    classification: str
    persistence_family: str
    dto_factory: DtoFactory
    domain_factory: DomainFactory
    has_material_payload: bool

    @property
    def id(self) -> str:
        return f"{self.model}.{self.field}"


def registry() -> tuple[FieldCase, ...]:
    dto = dto_factories()
    domain = domain_factories()
    specifications = (
        ("ResearchQuestionVersion", "scope", "ResearchQuestionVersion", True),
        ("HypothesisVersion", "success_criteria", "HypothesisVersion", True),
        ("ExperimentSpecVersion", "protocol", "ExperimentSpecVersion", True),
        ("ExperimentSpecVersion", "planned_metrics", "ExperimentSpecVersion", True),
        ("ExperimentSpecVersion", "seed_policy", "ExperimentSpecVersion", True),
        ("ExperimentSpecVersion", "analysis_plan", "ExperimentSpecVersion", True),
        ("DatasetSnapshot", "selection_definition", "DatasetSnapshot", True),
        ("ArtifactVersion", "metadata", "ArtifactVersion", False),
        ("MetricDefinitionVersion", "definition", "MetricDefinitionVersion", True),
        ("Measurement", "structured_value", "Measurement", True),
        ("Measurement", "evaluation_scope", "Measurement", True),
        ("StatisticalResult", "result_payload", "StatisticalResult", True),
        ("StatisticalResult", "analysis_definition", "StatisticalResult", True),
        ("ClaimVersion", "scope", "ClaimVersion", True),
        ("ImpactAssessment", "assessment_payload", "GovernanceStructured", False),
        ("CorrectionRecord", "corrected_assertion", "GovernanceStructured", False),
    )
    return tuple(
        FieldCase(
            model,
            field,
            "OPERATIONAL_IMMUTABLE_JSON"
            if model == "ArtifactVersion"
            else "CANONICAL_HASHED_MATERIAL",
            family,
            dto[(model, field)],
            domain[(model, field)],
            has_payload,
        )
        for model, field, family, has_payload in specifications
    )


CASES = registry()


def plain(value: object) -> object:
    return thaw_json(value)


def test_registry_is_complete_and_machine_counted() -> None:
    assert len(CASES) == 16
    assert sum(case.classification == "CANONICAL_HASHED_MATERIAL" for case in CASES) == 15
    assert sum(case.classification == "OPERATIONAL_IMMUTABLE_JSON" for case in CASES) == 1
    assert {case.persistence_family for case in CASES} == {
        "ResearchQuestionVersion",
        "HypothesisVersion",
        "ExperimentSpecVersion",
        "DatasetSnapshot",
        "ArtifactVersion",
        "MetricDefinitionVersion",
        "Measurement",
        "StatisticalResult",
        "ClaimVersion",
        "GovernanceStructured",
    }


@pytest.mark.parametrize("operation", mutation_names())
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_caller_to_dto_owns_nested_json(case: FieldCase, operation: str) -> None:
    source = nested_json()
    dto = case.dto_factory(source)
    expected = deepcopy(getattr(dto, case.field))
    mutate(source, operation)
    assert getattr(dto, case.field) == expected


@pytest.mark.parametrize("operation", mutation_names())
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_dto_to_domain_takes_second_nested_snapshot(case: FieldCase, operation: str) -> None:
    dto = case.dto_factory(nested_json())
    dto_value = getattr(dto, case.field)
    domain = case.domain_factory(dto_value)
    expected = plain(getattr(domain, case.field))
    mutate(dto_value, operation)
    assert plain(getattr(domain, case.field)) == expected


PAYLOAD_CASES = tuple(case for case in CASES if case.has_material_payload)


@pytest.mark.parametrize("operation", mutation_names())
@pytest.mark.parametrize("case", PAYLOAD_CASES, ids=lambda case: case.id)
def test_material_payload_is_fresh_nested_tree(case: FieldCase, operation: str) -> None:
    domain = case.domain_factory(nested_json())
    first = domain.material_payload()
    expected = deepcopy(first)
    mutate(first[case.field], operation)
    assert domain.material_payload() == expected
    assert plain(getattr(domain, case.field)) == expected[case.field]


@dataclass(frozen=True, slots=True)
class PersistenceFamily:
    name: str
    model: type[Any]
    id_getter: Callable[[WorkflowIds], object]
    reader: Callable[[WorkflowFixture, WorkflowIds], object]
    fields: tuple[str, ...]
    orm_fields: tuple[str, ...] | None = None

    def orm_field(self, field: str) -> str:
        if self.orm_fields is None:
            return field
        return self.orm_fields[self.fields.index(field)]


PERSISTENCE_FAMILIES = (
    PersistenceFamily(
        "ResearchQuestionVersion",
        ResearchQuestionVersionModel,
        lambda ids: ids.research_question_version_id,
        lambda fixture, ids: fixture.application.get_research_question_version(
            ResearchQuestionVersionId(ids.research_question_version_id)
        ),
        ("scope",),
    ),
    PersistenceFamily(
        "HypothesisVersion",
        HypothesisVersionModel,
        lambda ids: ids.hypothesis_version_id,
        lambda fixture, ids: fixture.application.get_hypothesis_version(
            HypothesisVersionId(ids.hypothesis_version_id)
        ),
        ("success_criteria",),
    ),
    PersistenceFamily(
        "ExperimentSpecVersion",
        ExperimentSpecVersionModel,
        lambda ids: ids.experiment_spec_version_id,
        lambda fixture, ids: fixture.application.get_experiment_spec_version(
            ExperimentSpecVersionId(ids.experiment_spec_version_id)
        ),
        ("protocol", "planned_metrics", "seed_policy", "analysis_plan"),
    ),
    PersistenceFamily(
        "DatasetSnapshot",
        DatasetSnapshotModel,
        lambda ids: ids.dataset_snapshot_id,
        lambda fixture, ids: fixture.application.get_dataset_snapshot(
            DatasetSnapshotId(ids.dataset_snapshot_id)
        ),
        ("selection_definition",),
    ),
    PersistenceFamily(
        "ArtifactVersion",
        ArtifactVersionModel,
        lambda ids: ids.artifact_version_id,
        lambda fixture, ids: fixture.application.get_artifact_version(ids.artifact_version_id),
        ("metadata",),
        ("metadata_json",),
    ),
    PersistenceFamily(
        "MetricDefinitionVersion",
        MetricDefinitionVersionModel,
        lambda ids: ids.metric_definition_version_id,
        lambda fixture, ids: fixture.application.get_metric_definition_version(
            MetricDefinitionVersionId(ids.metric_definition_version_id)
        ),
        ("definition",),
    ),
    PersistenceFamily(
        "Measurement",
        MeasurementModel,
        lambda ids: ids.measurement_ids[1],
        lambda fixture, ids: fixture.application.get_measurement(
            MeasurementId(ids.measurement_ids[1])
        ),
        ("structured_value", "evaluation_scope"),
    ),
    PersistenceFamily(
        "StatisticalResult",
        StatisticalResultModel,
        lambda ids: ids.statistical_result_id,
        lambda fixture, ids: fixture.application.get_statistical_result(
            StatisticalResultId(ids.statistical_result_id)
        ),
        ("result_payload", "analysis_definition"),
    ),
    PersistenceFamily(
        "ClaimVersion",
        ClaimVersionModel,
        lambda ids: ids.claim_version_id,
        lambda fixture, ids: fixture.application.get_claim_version(
            ClaimVersionId(ids.claim_version_id)
        ),
        ("scope",),
    ),
    PersistenceFamily(
        "GovernanceStructured",
        ImpactAssessmentModel,
        lambda ids: ids.impact_assessment_id,
        lambda fixture, ids: fixture.governance_queries.get_impact_assessment(
            ids.impact_assessment_id
        ),
        ("assessment_payload",),
    ),
)


@pytest.fixture(scope="module")
def ownership_workflow(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[WorkflowFixture, WorkflowIds]]:
    path = tmp_path_factory.mktemp("p1-fcr4-ownership")
    with fresh_fixture(path, "p1-fcr4-ownership") as fixture:
        ids = run_workflow(fixture, "application")
        structured = fixture.application.record_measurement(
            RecordMeasurementCommand(
                RunId(ids.run_id),
                MetricDefinitionVersionId(ids.metric_definition_version_id),
                None,
                nested_json(),
                None,
                nested_json(),
                fixture.context,
            )
        )
        yield fixture, replace(ids, measurement_ids=(ids.measurement_ids[0], structured.id))


def mutable_exposure(value: object) -> object:
    exposed = value if isinstance(value, dict | list) else thaw_json(value)
    if isinstance(exposed, dict):
        exposed["p1_fcr4_alias_attack"] = {"nested": [1, 2, 3]}
    elif isinstance(exposed, list):
        exposed.append({"p1_fcr4_alias_attack": True})
    else:  # pragma: no cover - registry fields are containers
        raise AssertionError(type(exposed))
    return exposed


def row_snapshot(row: Any, family: PersistenceFamily) -> tuple[dict[str, object], object]:
    return (
        {field: deepcopy(getattr(row, family.orm_field(field))) for field in family.fields},
        row.content_hash,
    )


@pytest.mark.parametrize("family", PERSISTENCE_FAMILIES, ids=lambda family: family.name)
def test_persistence_family_orm_and_read_boundaries(
    ownership_workflow: tuple[WorkflowFixture, WorkflowIds], family: PersistenceFamily
) -> None:
    fixture, ids = ownership_workflow
    read_value = family.reader(fixture, ids)
    read_snapshot = {field: plain(getattr(read_value, field)) for field in family.fields}
    with fixture.sessions() as session:
        row = session.get(family.model, family.id_getter(ids))
        assert row is not None
        for field in family.fields:
            orm_source = getattr(row, family.orm_field(field))
            domain_snapshot = deepcopy(read_snapshot[field])
            mutable_exposure(orm_source)
            assert plain(getattr(read_value, field)) == domain_snapshot
        session.rollback()

    with fixture.sessions() as session:
        row = session.get(family.model, family.id_getter(ids))
        assert row is not None
        original_orm = {
            field: deepcopy(getattr(row, family.orm_field(field))) for field in family.fields
        }
        for field in family.fields:
            mutable_exposure(getattr(read_value, field))
            assert getattr(row, family.orm_field(field)) == original_orm[field]
        session.rollback()

    fresh = family.reader(fixture, ids)
    assert {field: plain(getattr(fresh, field)) for field in family.fields} == read_snapshot


@pytest.mark.parametrize("family", PERSISTENCE_FAMILIES, ids=lambda family: family.name)
def test_persistence_family_autoflush_cannot_persist_external_alias(
    ownership_workflow: tuple[WorkflowFixture, WorkflowIds], family: PersistenceFamily
) -> None:
    fixture, ids = ownership_workflow
    exposed = family.reader(fixture, ids)
    for field in family.fields:
        mutable_exposure(getattr(exposed, field))

    with fixture.sessions() as session:
        before_row = session.get(family.model, family.id_getter(ids))
        assert before_row is not None
        before = row_snapshot(before_row, family)
        session.execute(select(family.model).limit(1)).scalar_one_or_none()
        session.flush()
        session.expire_all()
        after_row = session.get(family.model, family.id_getter(ids))
        assert after_row is not None
        assert row_snapshot(after_row, family) == before
        session.rollback()


@pytest.mark.parametrize("family", PERSISTENCE_FAMILIES, ids=lambda family: family.name)
def test_persistence_family_unrelated_commit_cannot_persist_external_alias(
    ownership_workflow: tuple[WorkflowFixture, WorkflowIds], family: PersistenceFamily
) -> None:
    fixture, ids = ownership_workflow
    with fixture.sessions() as session:
        before_row = session.get(family.model, family.id_getter(ids))
        assert before_row is not None
        before = row_snapshot(before_row, family)

    exposed = family.reader(fixture, ids)
    for field in family.fields:
        mutable_exposure(getattr(exposed, field))
    result = fixture.application.create_project(
        CreateProjectCommand(f"ownership-{family.name}-{uuid4()}", None, fixture.context)
    )
    assert result.id is not None

    with fixture.sessions() as session:
        after_row = session.get(family.model, family.id_getter(ids))
        assert after_row is not None
        assert row_snapshot(after_row, family) == before


def test_governance_correction_record_persistence_boundaries(
    ownership_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = ownership_workflow
    original = fixture.governance_queries.get_correction_record(ids.correction_id)
    assert original is not None
    snapshot = plain(original.corrected_assertion)
    mutable_exposure(original.corrected_assertion)
    fresh = fixture.governance_queries.get_correction_record(ids.correction_id)
    assert fresh is not None
    assert plain(fresh.corrected_assertion) == snapshot
    with fixture.sessions() as session:
        row = session.get(CorrectionRecordModel, ids.correction_id)
        assert row is not None
        before = (
            {"corrected_assertion": deepcopy(row.corrected_assertion)},
            row.content_hash,
        )
        session.execute(select(CorrectionRecordModel).limit(1)).scalar_one_or_none()
        session.flush()
        session.expire_all()
        after = session.get(CorrectionRecordModel, ids.correction_id)
        assert after is not None
        assert (
            {"corrected_assertion": deepcopy(after.corrected_assertion)},
            after.content_hash,
        ) == before


DIRECT_ORM_CONVERTERS: dict[str, Callable[[Any, Any], Any]] = {
    "ResearchQuestionVersion": lambda row, _source: _research_question_version_from_model(row),
    "HypothesisVersion": lambda row, _source: _hypothesis_version_from_model(row),
    "ExperimentSpecVersion": lambda row, _source: _experiment_spec_version_from_model(row),
    "DatasetSnapshot": lambda row, _source: _dataset_snapshot_from_model(row),
    "ArtifactVersion": lambda row, _source: _artifact_version_from_model(row),
    "MetricDefinitionVersion": lambda row, _source: _metric_definition_version_from_model(row),
    "Measurement": lambda row, _source: _measurement_from_model(row),
    "StatisticalResult": lambda row, _source: _statistical_result_from_row(
        {
            "id": row.id,
            "project_id": row.project_id,
            "analysis_type": row.analysis_type,
            "result_payload": row.result_payload,
            "analysis_definition": row.analysis_definition,
            "content_hash": row.content_hash,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }
    ),
    "ClaimVersion": lambda row, _source: _claim_version_from_model(row),
    "GovernanceStructured": lambda row, source: _impact_assessment_from_models(row, source.targets),
    "CorrectionRecord": lambda row, _source: _correction_record_from_model(row),
}


DIRECT_ORM_CASES = tuple(
    (
        case,
        next(family for family in PERSISTENCE_FAMILIES if family.name == case.persistence_family),
    )
    for case in CASES
    if case.model != "CorrectionRecord"
) + (
    (
        next(case for case in CASES if case.model == "CorrectionRecord"),
        PersistenceFamily(
            "CorrectionRecord",
            CorrectionRecordModel,
            lambda ids: ids.correction_id,
            lambda fixture, ids: fixture.governance_queries.get_correction_record(
                ids.correction_id
            ),
            ("corrected_assertion",),
        ),
    ),
)


@pytest.mark.parametrize("operation", mutation_names())
@pytest.mark.parametrize(
    ("case", "family"), DIRECT_ORM_CASES, ids=lambda value: getattr(value, "id", None)
)
def test_exact_orm_json_object_is_not_retained_by_domain(
    case: FieldCase,
    family: PersistenceFamily,
    operation: str,
) -> None:
    source = case.domain_factory(nested_json())
    values: dict[str, object] = {}
    for mapped_attribute in family.model.__mapper__.column_attrs:
        column = mapped_attribute.columns[0]
        orm_attribute = mapped_attribute.key
        attribute = "metadata" if orm_attribute == "metadata_json" else orm_attribute
        value = getattr(source, attribute)
        if hasattr(value, "value"):
            value = value.value
        elif column.key.endswith("hash") and value is not None:
            value = str(value)
        elif isinstance(value, dict | list) or type(value).__name__.startswith("FrozenJSON"):
            value = thaw_json(value)
        values[orm_attribute] = value
    row = family.model(**values)
    orm_json = getattr(row, family.orm_field(case.field))
    assert isinstance(orm_json, dict)
    source_identity = id(orm_json)
    nested_identity = id(orm_json["outer"])
    domain = DIRECT_ORM_CONVERTERS[family.name](row, source)
    original = plain(getattr(domain, case.field))

    assert id(getattr(row, family.orm_field(case.field))) == source_identity
    assert id(orm_json["outer"]) == nested_identity
    mutate(orm_json, operation)

    assert plain(getattr(domain, case.field)) == original
    if case.model == "ArtifactVersion":
        assert str(domain.content_hash) == row.content_hash


class CapturingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, model: object) -> None:
        self.added.append(model)

    def flush(self) -> None:
        return None


DIRECT_DOMAIN_TO_ORM_WRITERS: dict[str, Callable[[Any, Any], None]] = {
    "ResearchQuestionVersion": lambda session, domain: SqlAlchemyResearchQuestionRepository(
        session
    ).add_version(domain),
    "HypothesisVersion": lambda session, domain: SqlAlchemyHypothesisRepository(
        session
    ).add_version(domain),
    "ExperimentSpecVersion": lambda session, domain: SqlAlchemyExperimentSpecRepository(
        session
    ).add_version(domain),
    "DatasetSnapshot": lambda session, domain: SqlAlchemyDatasetSnapshotRepository(session).add(
        domain
    ),
    "ArtifactVersion": lambda session, domain: SqlAlchemyArtifactVersionRepository(session).add(
        domain
    ),
    "MetricDefinitionVersion": lambda session, domain: SqlAlchemyMetricDefinitionVersionRepository(
        session
    ).add(domain),
    "Measurement": lambda session, domain: SqlAlchemyMeasurementRepository(session).add(domain),
    "StatisticalResult": lambda session, domain: SqlAlchemyStatisticalResultRepository(session).add(
        domain
    ),
    "ClaimVersion": lambda session, domain: SqlAlchemyClaimRepository(session).add_version(domain),
    "ImpactAssessment": lambda session, domain: SqlAlchemyGovernanceRepository(
        session
    ).add_impact_assessment(domain),
    "CorrectionRecord": lambda session, domain: SqlAlchemyGovernanceRepository(
        session
    ).add_correction_record(domain),
}


DIRECT_DOMAIN_TO_ORM_MODEL: dict[str, type[Any]] = {
    family.name: family.model for family in PERSISTENCE_FAMILIES
}
DIRECT_DOMAIN_TO_ORM_MODEL.update(
    {
        "ImpactAssessment": ImpactAssessmentModel,
        "CorrectionRecord": CorrectionRecordModel,
    }
)


@pytest.mark.parametrize("operation", mutation_names())
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_domain_to_orm_uses_fresh_mutable_json_tree_for_every_field(
    case: FieldCase,
    operation: str,
) -> None:
    domain = case.domain_factory(nested_json())
    original = plain(getattr(domain, case.field))
    session = CapturingSession()
    DIRECT_DOMAIN_TO_ORM_WRITERS[case.model](session, domain)
    model_type = DIRECT_DOMAIN_TO_ORM_MODEL[case.model]
    row = next(model for model in session.added if isinstance(model, model_type))
    orm_field = "metadata_json" if case.model == "ArtifactVersion" else case.field
    orm_json = getattr(row, orm_field)
    assert isinstance(orm_json, dict)

    mutate(orm_json, operation)

    assert plain(getattr(domain, case.field)) == original


@pytest.mark.parametrize("operation", mutation_names())
def test_domain_to_orm_uses_fresh_mutable_json_tree(operation: str) -> None:
    class CapturingSession:
        added: object | None = None

        def add(self, model: object) -> None:
            self.added = model

    domain = replace(_research_question_version(), scope=nested_json())
    original = domain.material_payload()
    session = CapturingSession()
    SqlAlchemyResearchQuestionRepository(session).add_version(domain)  # type: ignore[arg-type]
    row = session.added
    assert isinstance(row, ResearchQuestionVersionModel)
    assert isinstance(row.scope, dict)

    mutate(row.scope, operation)

    assert domain.material_payload() == original


def test_machine_derived_boundary_accounting() -> None:
    assert len(CASES) == 16
    assert len(PAYLOAD_CASES) == 13
    assert sum(len(family.fields) for family in PERSISTENCE_FAMILIES) == 15
    assert len(PERSISTENCE_FAMILIES) == 10
    assert len(DIRECT_ORM_CASES) == 16
    assert {family.name for _, family in DIRECT_ORM_CASES} == {
        *DIRECT_ORM_CONVERTERS,
    }
