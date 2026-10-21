"""Explicit SQLAlchemy repository adapters for PR-02 domain models."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from uuid import UUID

from sqlalchemy import case, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.claim import (
    Claim,
    ClaimId,
    ClaimVersion,
    ClaimVersionId,
    EvidenceRelation,
    EvidenceRelationId,
    EvidenceRelationType,
)
from researchbase.domain.evidence import Dataset, DatasetId, DatasetSnapshot, DatasetSnapshotId
from researchbase.domain.experiment import (
    ExperimentSpec,
    ExperimentSpecId,
    ExperimentSpecVersion,
    ExperimentSpecVersionId,
)
from researchbase.domain.identity import Actor, ActorType
from researchbase.domain.measurement import Measurement, MeasurementId
from researchbase.domain.metric import (
    MetricDefinition,
    MetricDefinitionId,
    MetricDefinitionVersion,
    MetricDefinitionVersionId,
)
from researchbase.domain.organization import (
    LifecycleStatus,
    Project,
    ProjectId,
    Workspace,
    WorkspaceId,
)
from researchbase.domain.research import (
    Hypothesis,
    HypothesisId,
    HypothesisVersion,
    HypothesisVersionId,
    ResearchQuestion,
    ResearchQuestionId,
    ResearchQuestionVersion,
    ResearchQuestionVersionId,
)
from researchbase.domain.run import (
    ArtifactInputRole,
    DatasetInputRole,
    Run,
    RunArtifactInput,
    RunDatasetInput,
    RunId,
    RunStatus,
)
from researchbase.domain.statistical_result import (
    StatisticalResult,
    StatisticalResultId,
    StatisticalResultInput,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import thaw_json
from researchbase.foundation.hashing import CANONICAL_JSON_HASH_SCHEME, ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.models import (
    ActorModel,
    ArtifactModel,
    ArtifactVersionModel,
    ClaimModel,
    ClaimVersionModel,
    DatasetModel,
    DatasetSnapshotModel,
    EvidenceRelationModel,
    ExperimentSpecModel,
    ExperimentSpecVersionModel,
    HypothesisModel,
    HypothesisVersionModel,
    MeasurementModel,
    MetricDefinitionModel,
    MetricDefinitionVersionModel,
    ProjectModel,
    ResearchQuestionModel,
    ResearchQuestionVersionModel,
    RunArtifactInputModel,
    RunDatasetInputModel,
    RunModel,
    StatisticalResultInputModel,
    StatisticalResultModel,
    WorkspaceModel,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")


def _verified_persisted(record_type: str) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Normalize invalid persisted canonical state without changing caller validation."""

    def decorate(converter: Callable[_P, _T]) -> Callable[_P, _T]:
        @wraps(converter)
        def converted(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            try:
                return converter(*args, **kwargs)
            except ResearchBaseError as exc:
                if exc.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR:
                    raise
                cause: Exception = exc
            except (TypeError, ValueError) as exc:
                cause = exc
            source = args[0] if args else None
            identifier = getattr(source, "id", None)
            if identifier is None and source is not None:
                try:
                    identifier = source["id"]  # type: ignore[index]
                except (KeyError, TypeError):
                    identifier = None
            details = {"object_type": record_type}
            if identifier is not None:
                details["object_id"] = str(identifier)
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "persisted canonical record failed integrity verification",
                details,
            ) from cause

        return converted

    return decorate


def _ensure_current_pointer_parent(
    session: Session,
    identity_id: UUID,
    current_version_id: UUID | None,
    version_model: type[Any],
    parent_column: str,
    resource: str,
) -> None:
    if current_version_id is None:
        return
    parent_id = session.scalar(
        select(getattr(version_model, parent_column)).where(version_model.id == current_version_id)
    )
    if parent_id != identity_id:
        raise ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            f"{resource} current version must belong to the {resource}",
            {"id": str(identity_id), "current_version_id": str(current_version_id)},
        )


class SqlAlchemyActorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, actor: Actor) -> None:
        self._session.add(
            ActorModel(
                id=actor.id,
                actor_type=actor.actor_type.value,
                display_name=actor.display_name,
                external_key=actor.external_key,
                created_at=actor.created_at,
                retired_at=actor.retired_at,
                row_version=actor.row_version,
            )
        )

    def get(self, actor_id: ActorId) -> Actor | None:
        model = self._session.get(ActorModel, actor_id)
        return _actor_from_model(model) if model is not None else None

    def get_by_external_key(self, external_key: str) -> Actor | None:
        model = self._session.scalar(
            select(ActorModel).where(ActorModel.external_key == external_key)
        )
        return _actor_from_model(model) if model is not None else None


class SqlAlchemyProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: Project) -> None:
        self._session.add(
            ProjectModel(
                id=project.id,
                name=project.name,
                description=project.description,
                lifecycle_status=project.lifecycle_status.value,
                created_by=project.created_by,
                created_at=project.created_at,
                row_version=project.row_version,
            )
        )

    def get(self, project_id: ProjectId) -> Project | None:
        model = self._session.get(ProjectModel, project_id)
        return _project_from_model(model) if model is not None else None


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, workspace: Workspace) -> None:
        self._session.add(
            WorkspaceModel(
                id=workspace.id,
                project_id=workspace.project_id,
                name=workspace.name,
                locator=workspace.locator,
                lifecycle_status=workspace.lifecycle_status.value,
                created_by=workspace.created_by,
                created_at=workspace.created_at,
                row_version=workspace.row_version,
            )
        )

    def get(self, workspace_id: WorkspaceId) -> Workspace | None:
        model = self._session.get(WorkspaceModel, workspace_id)
        return _workspace_from_model(model) if model is not None else None


class SqlAlchemyResearchQuestionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, question: ResearchQuestion) -> None:
        self._session.add(
            ResearchQuestionModel(
                id=question.id,
                project_id=question.project_id,
                current_version_id=question.current_version_id,
                created_by=question.created_by,
                created_at=question.created_at,
                row_version=question.row_version,
            )
        )

    def add_version(self, version: ResearchQuestionVersion) -> None:
        self._session.add(
            ResearchQuestionVersionModel(
                id=version.id,
                research_question_id=version.research_question_id,
                version_number=version.version_number,
                status=version.status.value,
                question_text=version.question_text,
                scope=thaw_json(version.scope) if version.scope is not None else None,
                rationale=version.rationale,
                content_hash=str(version.content_hash) if version.content_hash else None,
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, question_id: ResearchQuestionId) -> ResearchQuestion | None:
        model = self._session.get(ResearchQuestionModel, question_id)
        return _research_question_from_model(model) if model is not None else None

    def get_for_update(self, question_id: ResearchQuestionId) -> ResearchQuestion | None:
        model = self._session.scalar(
            select(ResearchQuestionModel)
            .where(ResearchQuestionModel.id == question_id)
            .with_for_update()
        )
        return _research_question_from_model(model) if model is not None else None

    def get_version(self, version_id: ResearchQuestionVersionId) -> ResearchQuestionVersion | None:
        model = self._session.get(ResearchQuestionVersionModel, version_id)
        return _research_question_version_from_model(model) if model is not None else None

    def get_version_for_update(
        self, version_id: ResearchQuestionVersionId
    ) -> ResearchQuestionVersion | None:
        model = self._session.scalar(
            select(ResearchQuestionVersionModel)
            .where(ResearchQuestionVersionModel.id == version_id)
            .with_for_update()
        )
        return _research_question_version_from_model(model) if model is not None else None

    def get_current_version(
        self, question_id: ResearchQuestionId
    ) -> ResearchQuestionVersion | None:
        question = self.get(question_id)
        if question is None or question.current_version_id is None:
            return None
        _ensure_current_pointer_parent(
            self._session,
            question.id,
            question.current_version_id,
            ResearchQuestionVersionModel,
            "research_question_id",
            "research question",
        )
        return self.get_version(question.current_version_id)

    def list_history(self, question_id: ResearchQuestionId) -> list[ResearchQuestionVersion]:
        models = self._session.scalars(
            select(ResearchQuestionVersionModel)
            .where(ResearchQuestionVersionModel.research_question_id == question_id)
            .order_by(ResearchQuestionVersionModel.version_number)
        ).all()
        return [_research_question_version_from_model(model) for model in models]

    def max_version_number(self, question_id: ResearchQuestionId) -> int:
        value = self._session.scalar(
            select(func.coalesce(func.max(ResearchQuestionVersionModel.version_number), 0)).where(
                ResearchQuestionVersionModel.research_question_id == question_id
            )
        )
        return int(value or 0)

    def update_current_version(
        self,
        question_id: ResearchQuestionId,
        version_id: ResearchQuestionVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None:
        self._session.flush()
        version = self._session.get(ResearchQuestionVersionModel, version_id)
        if version is None:
            raise _not_found("research question version", version_id)
        if version.research_question_id != question_id:
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "current version must belong to the research question",
            )
        values: dict[str, object] = {"current_version_id": version_id}
        if increment:
            values["row_version"] = ResearchQuestionModel.row_version + 1
        result = self._session.execute(
            update(ResearchQuestionModel)
            .where(
                ResearchQuestionModel.id == question_id,
                ResearchQuestionModel.row_version == expected_row_version,
            )
            .values(**values)
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "research question", question_id)

    def update_version(self, version: ResearchQuestionVersion, expected_row_version: int) -> None:
        result = self._session.execute(
            update(ResearchQuestionVersionModel)
            .where(
                ResearchQuestionVersionModel.id == version.id,
                ResearchQuestionVersionModel.row_version == expected_row_version,
            )
            .values(
                status=version.status.value,
                question_text=version.question_text,
                scope=thaw_json(version.scope) if version.scope is not None else None,
                rationale=version.rationale,
                content_hash=str(version.content_hash) if version.content_hash else None,
                frozen_at=version.frozen_at,
                row_version=ResearchQuestionVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "research question version", version.id)


class SqlAlchemyHypothesisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, hypothesis: Hypothesis) -> None:
        self._session.add(
            HypothesisModel(
                id=hypothesis.id,
                project_id=hypothesis.project_id,
                research_question_id=hypothesis.research_question_id,
                current_version_id=hypothesis.current_version_id,
                created_by=hypothesis.created_by,
                created_at=hypothesis.created_at,
                row_version=hypothesis.row_version,
            )
        )

    def add_version(self, version: HypothesisVersion) -> None:
        self._session.add(
            HypothesisVersionModel(
                id=version.id,
                hypothesis_id=version.hypothesis_id,
                version_number=version.version_number,
                status=version.status.value,
                statement=version.statement,
                expected_direction=version.expected_direction,
                success_criteria=(
                    thaw_json(version.success_criteria)
                    if version.success_criteria is not None
                    else None
                ),
                rationale=version.rationale,
                content_hash=str(version.content_hash) if version.content_hash else None,
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, hypothesis_id: HypothesisId) -> Hypothesis | None:
        model = self._session.get(HypothesisModel, hypothesis_id)
        return _hypothesis_from_model(model) if model is not None else None

    def get_for_update(self, hypothesis_id: HypothesisId) -> Hypothesis | None:
        model = self._session.scalar(
            select(HypothesisModel).where(HypothesisModel.id == hypothesis_id).with_for_update()
        )
        return _hypothesis_from_model(model) if model is not None else None

    def get_version(self, version_id: HypothesisVersionId) -> HypothesisVersion | None:
        model = self._session.get(HypothesisVersionModel, version_id)
        return _hypothesis_version_from_model(model) if model is not None else None

    def get_version_for_update(self, version_id: HypothesisVersionId) -> HypothesisVersion | None:
        model = self._session.scalar(
            select(HypothesisVersionModel)
            .where(HypothesisVersionModel.id == version_id)
            .with_for_update()
        )
        return _hypothesis_version_from_model(model) if model is not None else None

    def get_current_version(self, hypothesis_id: HypothesisId) -> HypothesisVersion | None:
        hypothesis = self.get(hypothesis_id)
        if hypothesis is None or hypothesis.current_version_id is None:
            return None
        _ensure_current_pointer_parent(
            self._session,
            hypothesis.id,
            hypothesis.current_version_id,
            HypothesisVersionModel,
            "hypothesis_id",
            "hypothesis",
        )
        return self.get_version(hypothesis.current_version_id)

    def list_history(self, hypothesis_id: HypothesisId) -> list[HypothesisVersion]:
        models = self._session.scalars(
            select(HypothesisVersionModel)
            .where(HypothesisVersionModel.hypothesis_id == hypothesis_id)
            .order_by(HypothesisVersionModel.version_number)
        ).all()
        return [_hypothesis_version_from_model(model) for model in models]

    def max_version_number(self, hypothesis_id: HypothesisId) -> int:
        value = self._session.scalar(
            select(func.coalesce(func.max(HypothesisVersionModel.version_number), 0)).where(
                HypothesisVersionModel.hypothesis_id == hypothesis_id
            )
        )
        return int(value or 0)

    def update_current_version(
        self,
        hypothesis_id: HypothesisId,
        version_id: HypothesisVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None:
        self._session.flush()
        version = self._session.get(HypothesisVersionModel, version_id)
        if version is None:
            raise _not_found("hypothesis version", version_id)
        if version.hypothesis_id != hypothesis_id:
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "current version must belong to the hypothesis",
            )
        values: dict[str, object] = {"current_version_id": version_id}
        if increment:
            values["row_version"] = HypothesisModel.row_version + 1
        result = self._session.execute(
            update(HypothesisModel)
            .where(
                HypothesisModel.id == hypothesis_id,
                HypothesisModel.row_version == expected_row_version,
            )
            .values(**values)
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "hypothesis", hypothesis_id)

    def update_version(self, version: HypothesisVersion, expected_row_version: int) -> None:
        result = self._session.execute(
            update(HypothesisVersionModel)
            .where(
                HypothesisVersionModel.id == version.id,
                HypothesisVersionModel.row_version == expected_row_version,
            )
            .values(
                status=version.status.value,
                statement=version.statement,
                expected_direction=version.expected_direction,
                success_criteria=(
                    thaw_json(version.success_criteria)
                    if version.success_criteria is not None
                    else None
                ),
                rationale=version.rationale,
                content_hash=str(version.content_hash) if version.content_hash else None,
                frozen_at=version.frozen_at,
                row_version=HypothesisVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "hypothesis version", version.id)


class SqlAlchemyExperimentSpecRepository:
    def get_many(self, identities: set[ExperimentSpecId]) -> list[ExperimentSpec]:
        if not identities:
            return []
        rows = self._session.scalars(
            select(ExperimentSpecModel).where(ExperimentSpecModel.id.in_(identities))
        ).all()
        return [_experiment_spec_from_model(row) for row in rows]

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, aggregate: ExperimentSpec) -> None:
        self._session.add(
            ExperimentSpecModel(
                id=aggregate.id,
                project_id=aggregate.project_id,
                hypothesis_id=aggregate.hypothesis_id,
                current_version_id=aggregate.current_version_id,
                created_by=aggregate.created_by,
                created_at=aggregate.created_at,
                row_version=aggregate.row_version,
            )
        )

    def add_version(self, version: ExperimentSpecVersion) -> None:
        self._session.add(
            ExperimentSpecVersionModel(
                id=version.id,
                experiment_spec_id=version.experiment_spec_id,
                version_number=version.version_number,
                status=version.status.value,
                title=version.title,
                objective=version.objective,
                protocol=thaw_json(version.protocol),
                planned_metrics=(
                    thaw_json(version.planned_metrics)
                    if version.planned_metrics is not None
                    else None
                ),
                seed_policy=(
                    thaw_json(version.seed_policy) if version.seed_policy is not None else None
                ),
                analysis_plan=(
                    thaw_json(version.analysis_plan) if version.analysis_plan is not None else None
                ),
                content_hash=str(version.content_hash) if version.content_hash else None,
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, spec_id: ExperimentSpecId) -> ExperimentSpec | None:
        model = self._session.get(ExperimentSpecModel, spec_id)
        return _experiment_spec_from_model(model) if model is not None else None

    def get_for_update(self, spec_id: ExperimentSpecId) -> ExperimentSpec | None:
        model = self._session.scalar(
            select(ExperimentSpecModel).where(ExperimentSpecModel.id == spec_id).with_for_update()
        )
        return _experiment_spec_from_model(model) if model is not None else None

    def get_version(self, version_id: ExperimentSpecVersionId) -> ExperimentSpecVersion | None:
        model = self._session.get(ExperimentSpecVersionModel, version_id)
        return _experiment_spec_version_from_model(model) if model is not None else None

    def get_versions(
        self, version_ids: set[ExperimentSpecVersionId]
    ) -> list[ExperimentSpecVersion]:
        if not version_ids:
            return []
        models = self._session.scalars(
            select(ExperimentSpecVersionModel).where(ExperimentSpecVersionModel.id.in_(version_ids))
        ).all()
        return [_experiment_spec_version_from_model(model) for model in models]

    def get_version_for_update(
        self, version_id: ExperimentSpecVersionId
    ) -> ExperimentSpecVersion | None:
        model = self._session.scalar(
            select(ExperimentSpecVersionModel)
            .where(ExperimentSpecVersionModel.id == version_id)
            .with_for_update()
        )
        return _experiment_spec_version_from_model(model) if model is not None else None

    def get_current_version(self, spec_id: ExperimentSpecId) -> ExperimentSpecVersion | None:
        spec = self.get(spec_id)
        if spec is None or spec.current_version_id is None:
            return None
        _ensure_current_pointer_parent(
            self._session,
            spec.id,
            spec.current_version_id,
            ExperimentSpecVersionModel,
            "experiment_spec_id",
            "experiment spec",
        )
        return self.get_version(spec.current_version_id)

    def list_history(self, spec_id: ExperimentSpecId) -> list[ExperimentSpecVersion]:
        models = self._session.scalars(
            select(ExperimentSpecVersionModel)
            .where(ExperimentSpecVersionModel.experiment_spec_id == spec_id)
            .order_by(ExperimentSpecVersionModel.version_number)
        ).all()
        return [_experiment_spec_version_from_model(model) for model in models]

    def max_version_number(self, spec_id: ExperimentSpecId) -> int:
        value = self._session.scalar(
            select(func.coalesce(func.max(ExperimentSpecVersionModel.version_number), 0)).where(
                ExperimentSpecVersionModel.experiment_spec_id == spec_id
            )
        )
        return int(value or 0)

    def update_current_version(
        self,
        spec_id: ExperimentSpecId,
        version_id: ExperimentSpecVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None:
        self._session.flush()
        version = self._session.get(ExperimentSpecVersionModel, version_id)
        if version is None:
            raise _not_found("experiment spec version", version_id)
        if version.experiment_spec_id != spec_id:
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "current version must belong to the experiment spec",
            )
        values: dict[str, object] = {"current_version_id": version_id}
        if increment:
            values["row_version"] = ExperimentSpecModel.row_version + 1
        result = self._session.execute(
            update(ExperimentSpecModel)
            .where(
                ExperimentSpecModel.id == spec_id,
                ExperimentSpecModel.row_version == expected_row_version,
            )
            .values(**values)
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "experiment spec", spec_id)

    def update_version(self, version: ExperimentSpecVersion, expected_row_version: int) -> None:
        result = self._session.execute(
            update(ExperimentSpecVersionModel)
            .where(
                ExperimentSpecVersionModel.id == version.id,
                ExperimentSpecVersionModel.row_version == expected_row_version,
            )
            .values(
                status=version.status.value,
                title=version.title,
                objective=version.objective,
                protocol=thaw_json(version.protocol),
                planned_metrics=(
                    thaw_json(version.planned_metrics)
                    if version.planned_metrics is not None
                    else None
                ),
                seed_policy=(
                    thaw_json(version.seed_policy) if version.seed_policy is not None else None
                ),
                analysis_plan=(
                    thaw_json(version.analysis_plan) if version.analysis_plan is not None else None
                ),
                content_hash=str(version.content_hash) if version.content_hash else None,
                frozen_at=version.frozen_at,
                row_version=ExperimentSpecVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "experiment spec version", version.id)


class SqlAlchemyDatasetRepository:
    def get_many(self, identities: set[DatasetId]) -> list[Dataset]:
        if not identities:
            return []
        rows = self._session.scalars(
            select(DatasetModel).where(DatasetModel.id.in_(identities))
        ).all()
        return [_dataset_from_model(row) for row in rows]

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, dataset: Dataset) -> None:
        self._session.add(
            DatasetModel(
                id=dataset.id,
                project_id=dataset.project_id,
                name=dataset.name,
                description=dataset.description,
                source_locator=dataset.source_locator,
                lifecycle_status=dataset.lifecycle_status.value,
                created_by=dataset.created_by,
                created_at=dataset.created_at,
                row_version=dataset.row_version,
            )
        )

    def get(self, dataset_id: DatasetId) -> Dataset | None:
        model = self._session.get(DatasetModel, dataset_id)
        return _dataset_from_model(model) if model is not None else None


class SqlAlchemyDatasetSnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, snapshot: DatasetSnapshot) -> None:
        self._session.add(
            DatasetSnapshotModel(
                id=snapshot.id,
                dataset_id=snapshot.dataset_id,
                manifest_hash=str(snapshot.manifest_hash),
                selection_definition=thaw_json(snapshot.selection_definition),
                manifest_locator=snapshot.manifest_locator,
                content_hash=str(snapshot.content_hash),
                created_by=snapshot.created_by,
                created_at=snapshot.created_at,
            )
        )

    def get(self, snapshot_id: DatasetSnapshotId) -> DatasetSnapshot | None:
        model = self._session.get(DatasetSnapshotModel, snapshot_id)
        return _dataset_snapshot_from_model(model) if model is not None else None

    def get_many(self, snapshot_ids: set[DatasetSnapshotId]) -> list[DatasetSnapshot]:
        if not snapshot_ids:
            return []
        models = self._session.scalars(
            select(DatasetSnapshotModel).where(DatasetSnapshotModel.id.in_(snapshot_ids))
        ).all()
        return [_dataset_snapshot_from_model(model) for model in models]

    def find_by_dataset_and_content_hash(
        self, dataset_id: DatasetId, content_hash: str
    ) -> DatasetSnapshot | None:
        model = self._session.scalar(
            select(DatasetSnapshotModel).where(
                DatasetSnapshotModel.dataset_id == dataset_id,
                DatasetSnapshotModel.content_hash == content_hash,
            )
        )
        return _dataset_snapshot_from_model(model) if model is not None else None


class SqlAlchemyArtifactRepository:
    def get_many(self, identities: set[ArtifactId]) -> list[Artifact]:
        if not identities:
            return []
        rows = self._session.scalars(
            select(ArtifactModel).where(ArtifactModel.id.in_(identities))
        ).all()
        return [_artifact_from_model(row) for row in rows]

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, artifact: Artifact) -> None:
        self._session.add(
            ArtifactModel(
                id=artifact.id,
                project_id=artifact.project_id,
                artifact_type=artifact.artifact_type,
                name=artifact.name,
                description=artifact.description,
                current_version_id=artifact.current_version_id,
                created_by=artifact.created_by,
                created_at=artifact.created_at,
                row_version=artifact.row_version,
            )
        )

    def get(self, artifact_id: ArtifactId) -> Artifact | None:
        model = self._session.get(ArtifactModel, artifact_id)
        return _artifact_from_model(model) if model is not None else None

    def get_for_update(self, artifact_id: ArtifactId) -> Artifact | None:
        model = self._session.scalar(
            select(ArtifactModel).where(ArtifactModel.id == artifact_id).with_for_update()
        )
        return _artifact_from_model(model) if model is not None else None

    def update_current_version(
        self,
        artifact_id: ArtifactId,
        version_id: ArtifactVersionId,
        expected_row_version: int,
    ) -> None:
        self._session.flush()
        version = self._session.get(ArtifactVersionModel, version_id)
        if version is None:
            raise _not_found("artifact version", version_id)
        if version.artifact_id != artifact_id:
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "current version must belong to the artifact",
            )
        result = self._session.execute(
            update(ArtifactModel)
            .where(
                ArtifactModel.id == artifact_id,
                ArtifactModel.row_version == expected_row_version,
            )
            .values(
                current_version_id=version_id,
                row_version=ArtifactModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "artifact", artifact_id)


class SqlAlchemyArtifactVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, version: ArtifactVersion) -> None:
        self._session.add(
            ArtifactVersionModel(
                id=version.id,
                artifact_id=version.artifact_id,
                version_number=version.version_number,
                status=version.status.value,
                locator=version.locator,
                media_type=version.media_type,
                byte_size=version.byte_size,
                content_hash=str(version.content_hash),
                metadata_json=(
                    thaw_json(version.metadata) if version.metadata is not None else None
                ),
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, version_id: ArtifactVersionId) -> ArtifactVersion | None:
        model = self._session.get(ArtifactVersionModel, version_id)
        return _artifact_version_from_model(model) if model is not None else None

    def get_many(self, version_ids: set[ArtifactVersionId]) -> list[ArtifactVersion]:
        if not version_ids:
            return []
        models = self._session.scalars(
            select(ArtifactVersionModel).where(ArtifactVersionModel.id.in_(version_ids))
        ).all()
        return [_artifact_version_from_model(model) for model in models]

    def get_for_update(self, version_id: ArtifactVersionId) -> ArtifactVersion | None:
        model = self._session.scalar(
            select(ArtifactVersionModel)
            .where(ArtifactVersionModel.id == version_id)
            .with_for_update()
        )
        return _artifact_version_from_model(model) if model is not None else None

    def find_by_artifact_and_content_hash(
        self, artifact_id: ArtifactId, content_hash: str
    ) -> ArtifactVersion | None:
        model = self._session.scalar(
            select(ArtifactVersionModel).where(
                ArtifactVersionModel.artifact_id == artifact_id,
                ArtifactVersionModel.content_hash == content_hash,
            )
        )
        return _artifact_version_from_model(model) if model is not None else None

    def max_version_number(self, artifact_id: ArtifactId) -> int:
        value = self._session.scalar(
            select(func.coalesce(func.max(ArtifactVersionModel.version_number), 0)).where(
                ArtifactVersionModel.artifact_id == artifact_id
            )
        )
        return int(value or 0)

    def list_history(self, artifact_id: ArtifactId) -> list[ArtifactVersion]:
        models = self._session.scalars(
            select(ArtifactVersionModel)
            .where(ArtifactVersionModel.artifact_id == artifact_id)
            .order_by(ArtifactVersionModel.version_number)
        ).all()
        return [_artifact_version_from_model(model) for model in models]

    def update(self, version: ArtifactVersion, expected_row_version: int) -> None:
        result = self._session.execute(
            update(ArtifactVersionModel)
            .where(
                ArtifactVersionModel.id == version.id,
                ArtifactVersionModel.row_version == expected_row_version,
            )
            .values(
                status=version.status.value,
                locator=version.locator,
                media_type=version.media_type,
                byte_size=version.byte_size,
                content_hash=str(version.content_hash),
                metadata_json=(
                    thaw_json(version.metadata) if version.metadata is not None else None
                ),
                frozen_at=version.frozen_at,
                row_version=ArtifactVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "artifact version", version.id)


class SqlAlchemyMetricDefinitionRepository:
    def get_many(self, identities: set[MetricDefinitionId]) -> list[MetricDefinition]:
        if not identities:
            return []
        rows = self._session.scalars(
            select(MetricDefinitionModel).where(MetricDefinitionModel.id.in_(identities))
        ).all()
        return [_metric_definition_from_model(row) for row in rows]

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, aggregate: MetricDefinition) -> None:
        self._session.add(
            MetricDefinitionModel(
                id=aggregate.id,
                project_id=aggregate.project_id,
                name=aggregate.name,
                current_version_id=aggregate.current_version_id,
                created_by=aggregate.created_by,
                created_at=aggregate.created_at,
                row_version=aggregate.row_version,
            )
        )

    def get(self, metric_id: MetricDefinitionId) -> MetricDefinition | None:
        model = self._session.get(MetricDefinitionModel, metric_id)
        return _metric_definition_from_model(model) if model is not None else None

    def get_for_update(self, metric_id: MetricDefinitionId) -> MetricDefinition | None:
        model = self._session.scalar(
            select(MetricDefinitionModel)
            .where(MetricDefinitionModel.id == metric_id)
            .with_for_update()
        )
        return _metric_definition_from_model(model) if model is not None else None

    def update_current_version(
        self,
        metric_id: MetricDefinitionId,
        version_id: MetricDefinitionVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None:
        self._session.flush()
        version = self._session.get(MetricDefinitionVersionModel, version_id)
        if version is None:
            raise _not_found("metric definition version", version_id)
        if version.metric_definition_id != metric_id:
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "current version must belong to the metric definition",
            )
        values: dict[str, object] = {"current_version_id": version_id}
        if increment:
            values["row_version"] = MetricDefinitionModel.row_version + 1
        result = self._session.execute(
            update(MetricDefinitionModel)
            .where(
                MetricDefinitionModel.id == metric_id,
                MetricDefinitionModel.row_version == expected_row_version,
            )
            .values(**values)
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "metric definition", metric_id)


class SqlAlchemyMetricDefinitionVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, version: MetricDefinitionVersion) -> None:
        self._session.add(
            MetricDefinitionVersionModel(
                id=version.id,
                metric_definition_id=version.metric_definition_id,
                version_number=version.version_number,
                status=version.status.value,
                definition=thaw_json(version.definition),
                unit=version.unit,
                aggregation=version.aggregation,
                content_hash=str(version.content_hash) if version.content_hash else None,
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, version_id: MetricDefinitionVersionId) -> MetricDefinitionVersion | None:
        model = self._session.get(MetricDefinitionVersionModel, version_id)
        return _metric_definition_version_from_model(model) if model is not None else None

    def get_many(
        self, version_ids: set[MetricDefinitionVersionId]
    ) -> list[MetricDefinitionVersion]:
        if not version_ids:
            return []
        models = self._session.scalars(
            select(MetricDefinitionVersionModel).where(
                MetricDefinitionVersionModel.id.in_(version_ids)
            )
        ).all()
        return [_metric_definition_version_from_model(model) for model in models]

    def get_for_update(
        self, version_id: MetricDefinitionVersionId
    ) -> MetricDefinitionVersion | None:
        model = self._session.scalar(
            select(MetricDefinitionVersionModel)
            .where(MetricDefinitionVersionModel.id == version_id)
            .with_for_update()
        )
        return _metric_definition_version_from_model(model) if model is not None else None

    def max_version_number(self, metric_id: MetricDefinitionId) -> int:
        value = self._session.scalar(
            select(func.coalesce(func.max(MetricDefinitionVersionModel.version_number), 0)).where(
                MetricDefinitionVersionModel.metric_definition_id == metric_id
            )
        )
        return int(value or 0)

    def list_history(self, metric_id: MetricDefinitionId) -> list[MetricDefinitionVersion]:
        models = self._session.scalars(
            select(MetricDefinitionVersionModel)
            .where(MetricDefinitionVersionModel.metric_definition_id == metric_id)
            .order_by(MetricDefinitionVersionModel.version_number)
        ).all()
        return [_metric_definition_version_from_model(model) for model in models]

    def update(self, version: MetricDefinitionVersion, expected_row_version: int) -> None:
        result = self._session.execute(
            update(MetricDefinitionVersionModel)
            .where(
                MetricDefinitionVersionModel.id == version.id,
                MetricDefinitionVersionModel.row_version == expected_row_version,
            )
            .values(
                status=version.status.value,
                definition=thaw_json(version.definition),
                unit=version.unit,
                aggregation=version.aggregation,
                content_hash=str(version.content_hash) if version.content_hash else None,
                frozen_at=version.frozen_at,
                row_version=MetricDefinitionVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "metric definition version", version.id)


class SqlAlchemyRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: Run) -> None:
        self._session.add(
            RunModel(
                id=run.id,
                project_id=run.project_id,
                experiment_spec_version_id=run.experiment_spec_version_id,
                run_type=run.run_type,
                status=run.status.value,
                inputs_sealed_at=run.inputs_sealed_at,
                started_at=run.started_at,
                finished_at=run.finished_at,
                exit_code=run.exit_code,
                failure_reason=run.failure_reason,
                created_by=run.created_by,
                created_at=run.created_at,
                row_version=run.row_version,
            )
        )

    def get(self, run_id: RunId) -> Run | None:
        model = self._session.get(RunModel, run_id)
        return _run_from_model(model) if model is not None else None

    def get_many(self, run_ids: set[RunId]) -> list[Run]:
        if not run_ids:
            return []
        models = self._session.scalars(select(RunModel).where(RunModel.id.in_(run_ids))).all()
        return [_run_from_model(model) for model in models]

    def get_for_update(self, run_id: RunId) -> Run | None:
        model = self._session.scalar(
            select(RunModel).where(RunModel.id == run_id).with_for_update()
        )
        return _run_from_model(model) if model is not None else None

    def update(self, run: Run, expected_row_version: int) -> None:
        result = self._session.execute(
            update(RunModel)
            .where(RunModel.id == run.id, RunModel.row_version == expected_row_version)
            .values(
                status=run.status.value,
                inputs_sealed_at=run.inputs_sealed_at,
                started_at=run.started_at,
                finished_at=run.finished_at,
                exit_code=run.exit_code,
                failure_reason=run.failure_reason,
                row_version=RunModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "run", run.id)

    def add_dataset_input(self, input: RunDatasetInput) -> None:
        self._session.add(
            RunDatasetInputModel(
                run_id=input.run_id,
                dataset_snapshot_id=input.dataset_snapshot_id,
                role=input.role.value,
                ordinal=input.ordinal,
            )
        )

    def add_artifact_input(self, input: RunArtifactInput) -> None:
        self._session.add(
            RunArtifactInputModel(
                run_id=input.run_id,
                artifact_version_id=input.artifact_version_id,
                role=input.role.value,
                ordinal=input.ordinal,
            )
        )

    def list_dataset_inputs(self, run_id: RunId) -> list[RunDatasetInput]:
        models = self._session.scalars(
            select(RunDatasetInputModel)
            .where(RunDatasetInputModel.run_id == run_id)
            .order_by(RunDatasetInputModel.dataset_snapshot_id, RunDatasetInputModel.role)
        ).all()
        return [_run_dataset_input_from_model(model) for model in models]

    def list_artifact_inputs(self, run_id: RunId) -> list[RunArtifactInput]:
        models = self._session.scalars(
            select(RunArtifactInputModel)
            .where(RunArtifactInputModel.run_id == run_id)
            .order_by(RunArtifactInputModel.artifact_version_id, RunArtifactInputModel.role)
        ).all()
        return [_run_artifact_input_from_model(model) for model in models]

    def list_dataset_inputs_for_runs(self, run_ids: set[RunId]) -> list[RunDatasetInput]:
        if not run_ids:
            return []
        models = self._session.scalars(
            select(RunDatasetInputModel).where(RunDatasetInputModel.run_id.in_(run_ids))
        ).all()
        return [_run_dataset_input_from_model(model) for model in models]

    def list_artifact_inputs_for_runs(self, run_ids: set[RunId]) -> list[RunArtifactInput]:
        if not run_ids:
            return []
        models = self._session.scalars(
            select(RunArtifactInputModel).where(RunArtifactInputModel.run_id.in_(run_ids))
        ).all()
        return [_run_artifact_input_from_model(model) for model in models]


class SqlAlchemyMeasurementRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, measurement: Measurement) -> None:
        self._session.add(
            MeasurementModel(
                id=measurement.id,
                run_id=measurement.run_id,
                metric_definition_version_id=measurement.metric_definition_version_id,
                numeric_value=measurement.numeric_value,
                structured_value=(
                    thaw_json(measurement.structured_value)
                    if measurement.structured_value is not None
                    else None
                ),
                unit=measurement.unit,
                evaluation_scope=(
                    thaw_json(measurement.evaluation_scope)
                    if measurement.evaluation_scope is not None
                    else None
                ),
                content_hash=str(measurement.content_hash),
                created_by=measurement.created_by,
                created_at=measurement.created_at,
            )
        )

    def get(self, measurement_id: MeasurementId) -> Measurement | None:
        model = self._session.get(MeasurementModel, measurement_id)
        return _measurement_from_model(model) if model is not None else None

    def get_many(self, measurement_ids: set[MeasurementId]) -> list[Measurement]:
        if not measurement_ids:
            return []
        models = self._session.scalars(
            select(MeasurementModel).where(MeasurementModel.id.in_(measurement_ids))
        ).all()
        return [_measurement_from_model(model) for model in models]

    def list_by_run(self, run_id: RunId) -> list[Measurement]:
        models = self._session.scalars(
            select(MeasurementModel)
            .where(MeasurementModel.run_id == run_id)
            .order_by(MeasurementModel.created_at, MeasurementModel.id)
        ).all()
        return [_measurement_from_model(model) for model in models]

    def list_by_runs(self, run_ids: set[RunId]) -> list[Measurement]:
        if not run_ids:
            return []
        models = self._session.scalars(
            select(MeasurementModel).where(MeasurementModel.run_id.in_(run_ids))
        ).all()
        return [_measurement_from_model(model) for model in models]


class SqlAlchemyStatisticalResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, result: StatisticalResult) -> None:
        self._session.add(
            StatisticalResultModel(
                id=result.id,
                project_id=result.project_id,
                analysis_type=result.analysis_type,
                result_payload=thaw_json(result.result_payload),
                analysis_definition=thaw_json(result.analysis_definition),
                content_hash=result.content_hash,
                created_by=result.created_by,
                created_at=result.created_at,
            )
        )

    def add_input(self, input: StatisticalResultInput) -> None:
        self._session.flush()
        try:
            self._session.execute(
                insert(StatisticalResultInputModel.__table__).values(  # type: ignore[arg-type]
                    statistical_result_id=input.statistical_result_id,
                    measurement_id=input.measurement_id,
                    input_role=input.input_role,
                    ordinal=input.ordinal,
                )
            )
        except IntegrityError as exc:
            if "statistical_result_inputs_pkey" not in str(exc.orig):
                raise
            self._session.rollback()
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "statistical result input is already attached",
                {"field": "input"},
            ) from exc

    def get(self, result_id: StatisticalResultId) -> StatisticalResult | None:
        table = StatisticalResultModel.__table__
        row = self._session.execute(select(table).where(table.c.id == result_id)).mappings().first()
        return _statistical_result_from_row(row) if row is not None else None

    def get_many(self, result_ids: set[StatisticalResultId]) -> list[StatisticalResult]:
        if not result_ids:
            return []
        table = StatisticalResultModel.__table__
        rows = self._session.execute(select(table).where(table.c.id.in_(result_ids))).mappings()
        return [_statistical_result_from_row(row) for row in rows]

    def list_by_project(self, project_id: ProjectId) -> list[StatisticalResult]:
        table = StatisticalResultModel.__table__
        rows = self._session.execute(
            select(table)
            .where(table.c.project_id == project_id)
            .order_by(table.c.created_at, table.c.id)
        ).mappings()
        return [_statistical_result_from_row(row) for row in rows]

    def list_inputs(self, result_id: StatisticalResultId) -> list[StatisticalResultInput]:
        table = StatisticalResultInputModel.__table__
        rows = self._session.execute(
            select(table)
            .where(table.c.statistical_result_id == result_id)
            .order_by(table.c.ordinal, table.c.input_role, table.c.measurement_id)
        ).mappings()
        return [_statistical_result_input_from_row(row) for row in rows]

    def list_inputs_for_results(
        self, result_ids: set[StatisticalResultId]
    ) -> list[StatisticalResultInput]:
        if not result_ids:
            return []
        table = StatisticalResultInputModel.__table__
        rows = self._session.execute(
            select(table).where(table.c.statistical_result_id.in_(result_ids))
        ).mappings()
        return [_statistical_result_input_from_row(row) for row in rows]


class SqlAlchemyClaimRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, claim: Claim) -> None:
        self._session.add(
            ClaimModel(
                id=claim.id,
                project_id=claim.project_id,
                current_version_id=claim.current_version_id,
                created_by=claim.created_by,
                created_at=claim.created_at,
                row_version=claim.row_version,
            )
        )

    def add_version(self, version: ClaimVersion) -> None:
        self._session.add(
            ClaimVersionModel(
                id=version.id,
                claim_id=version.claim_id,
                version_number=version.version_number,
                status=version.status.value,
                statement=version.statement,
                scope=thaw_json(version.scope) if version.scope is not None else None,
                qualification=version.qualification,
                support_set_hash=(
                    str(version.support_set_hash) if version.support_set_hash is not None else None
                ),
                content_hash=str(version.content_hash)
                if version.content_hash is not None
                else None,
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, claim_id: ClaimId) -> Claim | None:
        model = self._session.get(ClaimModel, claim_id)
        return _claim_from_model(model) if model is not None else None

    def get_for_update(self, claim_id: ClaimId) -> Claim | None:
        model = self._session.scalar(
            select(ClaimModel).where(ClaimModel.id == claim_id).with_for_update()
        )
        return _claim_from_model(model) if model is not None else None

    def get_version(self, version_id: ClaimVersionId) -> ClaimVersion | None:
        model = self._session.get(ClaimVersionModel, version_id)
        return _claim_version_from_model(model) if model is not None else None

    def get_version_for_update(self, version_id: ClaimVersionId) -> ClaimVersion | None:
        model = self._session.scalar(
            select(ClaimVersionModel).where(ClaimVersionModel.id == version_id).with_for_update()
        )
        return _claim_version_from_model(model) if model is not None else None

    def get_current_version(self, claim_id: ClaimId) -> ClaimVersion | None:
        claim = self.get(claim_id)
        if claim is None or claim.current_version_id is None:
            return None
        _ensure_current_pointer_parent(
            self._session,
            claim.id,
            claim.current_version_id,
            ClaimVersionModel,
            "claim_id",
            "claim",
        )
        return self.get_version(claim.current_version_id)

    def list_history(self, claim_id: ClaimId) -> list[ClaimVersion]:
        models = self._session.scalars(
            select(ClaimVersionModel)
            .where(ClaimVersionModel.claim_id == claim_id)
            .order_by(ClaimVersionModel.version_number)
        ).all()
        return [_claim_version_from_model(model) for model in models]

    def max_version_number(self, claim_id: ClaimId) -> int:
        value = self._session.scalar(
            select(func.coalesce(func.max(ClaimVersionModel.version_number), 0)).where(
                ClaimVersionModel.claim_id == claim_id
            )
        )
        return int(value or 0)

    def update_current_version(
        self,
        claim_id: ClaimId,
        version_id: ClaimVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None:
        self._session.flush()
        version = self._session.get(ClaimVersionModel, version_id)
        if version is None:
            raise _not_found("claim version", version_id)
        if version.claim_id != claim_id:
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "current version must belong to the claim",
            )
        values: dict[str, object] = {"current_version_id": version_id}
        if increment:
            values["row_version"] = ClaimModel.row_version + 1
        result = self._session.execute(
            update(ClaimModel)
            .where(
                ClaimModel.id == claim_id,
                ClaimModel.row_version == expected_row_version,
            )
            .values(**values)
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "claim", claim_id)

    def update_version(self, version: ClaimVersion, expected_row_version: int) -> None:
        result = self._session.execute(
            update(ClaimVersionModel)
            .where(
                ClaimVersionModel.id == version.id,
                ClaimVersionModel.row_version == expected_row_version,
            )
            .values(
                status=version.status.value,
                statement=version.statement,
                scope=thaw_json(version.scope) if version.scope is not None else None,
                qualification=version.qualification,
                support_set_hash=(
                    str(version.support_set_hash) if version.support_set_hash is not None else None
                ),
                content_hash=str(version.content_hash)
                if version.content_hash is not None
                else None,
                frozen_at=version.frozen_at,
                row_version=ClaimVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "claim version", version.id)

    def add_evidence(self, relation: EvidenceRelation) -> None:
        self._session.add(
            EvidenceRelationModel(
                id=relation.id,
                claim_version_id=relation.claim_version_id,
                measurement_id=relation.measurement_id,
                statistical_result_id=relation.statistical_result_id,
                relation_type=relation.relation_type.value,
                qualification=relation.qualification,
                created_by=relation.created_by,
                created_at=relation.created_at,
            )
        )

    def remove_evidence(self, relation_id: EvidenceRelationId) -> None:
        result = self._session.execute(
            delete(EvidenceRelationModel).where(EvidenceRelationModel.id == relation_id)
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "evidence relation", relation_id)

    def get_evidence(self, relation_id: EvidenceRelationId) -> EvidenceRelation | None:
        model = self._session.get(EvidenceRelationModel, relation_id)
        return _evidence_relation_from_model(model) if model is not None else None

    def list_evidence(self, version_id: ClaimVersionId) -> list[EvidenceRelation]:
        table = EvidenceRelationModel.__table__
        source_type = case(
            (table.c.measurement_id.is_not(None), "measurement"),
            else_="statistical_result",
        )
        source_id = func.coalesce(table.c.measurement_id, table.c.statistical_result_id)
        rows = self._session.execute(
            select(table)
            .where(table.c.claim_version_id == version_id)
            .order_by(
                source_type,
                source_id,
                table.c.relation_type,
                table.c.qualification.asc().nullsfirst(),
                table.c.id,
            )
        ).mappings()
        return [_evidence_relation_from_row(row) for row in rows]


def _actor_from_model(model: ActorModel) -> Actor:
    return Actor(
        id=ActorId(model.id),
        actor_type=ActorType(model.actor_type),
        display_name=model.display_name,
        external_key=model.external_key,
        created_at=model.created_at,
        retired_at=model.retired_at,
        row_version=model.row_version,
    )


def _claim_from_model(model: ClaimModel) -> Claim:
    return Claim(
        id=ClaimId(model.id),
        project_id=ProjectId(model.project_id),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        current_version_id=(
            ClaimVersionId(model.current_version_id)
            if model.current_version_id is not None
            else None
        ),
        row_version=model.row_version,
    )


@_verified_persisted("ClaimVersion")
def _claim_version_from_model(model: ClaimVersionModel) -> ClaimVersion:
    return ClaimVersion(
        id=ClaimVersionId(model.id),
        claim_id=ClaimId(model.claim_id),
        version_number=model.version_number,
        status=VersionStatus(model.status),
        statement=model.statement,
        scope=model.scope,
        qualification=model.qualification,
        support_set_hash=(ContentHash(model.support_set_hash) if model.support_set_hash else None),
        content_hash=ContentHash(model.content_hash) if model.content_hash else None,
        hash_scheme=CANONICAL_JSON_HASH_SCHEME if model.content_hash else None,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        frozen_at=model.frozen_at,
        row_version=model.row_version,
    )


def _evidence_relation_from_model(model: EvidenceRelationModel) -> EvidenceRelation:
    return EvidenceRelation(
        id=EvidenceRelationId(model.id),
        claim_version_id=ClaimVersionId(model.claim_version_id),
        measurement_id=MeasurementId(model.measurement_id) if model.measurement_id else None,
        statistical_result_id=(
            StatisticalResultId(model.statistical_result_id)
            if model.statistical_result_id
            else None
        ),
        relation_type=EvidenceRelationType(model.relation_type),
        qualification=model.qualification,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
    )


def _evidence_relation_from_row(row: Any) -> EvidenceRelation:
    return EvidenceRelation(
        id=EvidenceRelationId(row["id"]),
        claim_version_id=ClaimVersionId(row["claim_version_id"]),
        measurement_id=MeasurementId(row["measurement_id"]) if row["measurement_id"] else None,
        statistical_result_id=(
            StatisticalResultId(row["statistical_result_id"])
            if row["statistical_result_id"]
            else None
        ),
        relation_type=EvidenceRelationType(row["relation_type"]),
        qualification=row["qualification"],
        created_by=ActorId(row["created_by"]),
        created_at=row["created_at"],
    )


def _artifact_from_model(model: ArtifactModel) -> Artifact:
    return Artifact(
        id=ArtifactId(model.id),
        project_id=ProjectId(model.project_id) if model.project_id is not None else None,
        artifact_type=model.artifact_type,
        name=model.name,
        description=model.description,
        current_version_id=(
            ArtifactVersionId(model.current_version_id)
            if model.current_version_id is not None
            else None
        ),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )


def _artifact_version_from_model(model: ArtifactVersionModel) -> ArtifactVersion:
    return ArtifactVersion(
        id=ArtifactVersionId(model.id),
        artifact_id=ArtifactId(model.artifact_id),
        version_number=model.version_number,
        status=VersionStatus(model.status),
        locator=model.locator,
        media_type=model.media_type,
        byte_size=model.byte_size,
        content_hash=ContentHash(model.content_hash),
        metadata=model.metadata_json,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        frozen_at=model.frozen_at,
        row_version=model.row_version,
    )


def _metric_definition_from_model(model: MetricDefinitionModel) -> MetricDefinition:
    return MetricDefinition(
        id=MetricDefinitionId(model.id),
        project_id=ProjectId(model.project_id) if model.project_id is not None else None,
        name=model.name,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        current_version_id=(
            MetricDefinitionVersionId(model.current_version_id)
            if model.current_version_id is not None
            else None
        ),
        row_version=model.row_version,
    )


@_verified_persisted("MetricDefinitionVersion")
def _metric_definition_version_from_model(
    model: MetricDefinitionVersionModel,
) -> MetricDefinitionVersion:
    return MetricDefinitionVersion(
        id=MetricDefinitionVersionId(model.id),
        metric_definition_id=MetricDefinitionId(model.metric_definition_id),
        version_number=model.version_number,
        status=VersionStatus(model.status),
        definition=model.definition,
        unit=model.unit,
        aggregation=model.aggregation,
        content_hash=ContentHash(model.content_hash) if model.content_hash else None,
        hash_scheme=CANONICAL_JSON_HASH_SCHEME if model.content_hash else None,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        frozen_at=model.frozen_at,
        row_version=model.row_version,
    )


def _run_from_model(model: RunModel) -> Run:
    return Run(
        id=RunId(model.id),
        project_id=ProjectId(model.project_id),
        experiment_spec_version_id=ExperimentSpecVersionId(model.experiment_spec_version_id),
        run_type=model.run_type,
        status=RunStatus(model.status),
        inputs_sealed_at=model.inputs_sealed_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
        exit_code=model.exit_code,
        failure_reason=model.failure_reason,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )


def _run_dataset_input_from_model(model: RunDatasetInputModel) -> RunDatasetInput:
    return RunDatasetInput(
        run_id=RunId(model.run_id),
        dataset_snapshot_id=DatasetSnapshotId(model.dataset_snapshot_id),
        role=DatasetInputRole(model.role),
        ordinal=model.ordinal,
    )


def _run_artifact_input_from_model(model: RunArtifactInputModel) -> RunArtifactInput:
    return RunArtifactInput(
        run_id=RunId(model.run_id),
        artifact_version_id=ArtifactVersionId(model.artifact_version_id),
        role=ArtifactInputRole(model.role),
        ordinal=model.ordinal,
    )


@_verified_persisted("Measurement")
def _measurement_from_model(model: MeasurementModel) -> Measurement:
    return Measurement(
        id=MeasurementId(model.id),
        run_id=RunId(model.run_id),
        metric_definition_version_id=MetricDefinitionVersionId(model.metric_definition_version_id),
        numeric_value=model.numeric_value,
        structured_value=model.structured_value,
        unit=model.unit,
        evaluation_scope=model.evaluation_scope,
        content_hash=ContentHash(model.content_hash),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
    )


@_verified_persisted("StatisticalResult")
def _statistical_result_from_row(row: Any) -> StatisticalResult:
    return StatisticalResult(
        id=StatisticalResultId(row["id"]),
        project_id=ProjectId(row["project_id"]),
        analysis_type=row["analysis_type"],
        result_payload=row["result_payload"],
        analysis_definition=row["analysis_definition"],
        content_hash=ContentHash(row["content_hash"]),
        created_by=ActorId(row["created_by"]),
        created_at=row["created_at"],
    )


def _statistical_result_input_from_row(row: Any) -> StatisticalResultInput:
    return StatisticalResultInput(
        statistical_result_id=StatisticalResultId(row["statistical_result_id"]),
        measurement_id=MeasurementId(row["measurement_id"]),
        input_role=row["input_role"],
        ordinal=row["ordinal"],
    )


def _dataset_from_model(model: DatasetModel) -> Dataset:
    return Dataset(
        id=DatasetId(model.id),
        project_id=ProjectId(model.project_id) if model.project_id is not None else None,
        name=model.name,
        description=model.description,
        source_locator=model.source_locator,
        lifecycle_status=LifecycleStatus(model.lifecycle_status),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )


@_verified_persisted("DatasetSnapshot")
def _dataset_snapshot_from_model(model: DatasetSnapshotModel) -> DatasetSnapshot:
    return DatasetSnapshot(
        id=DatasetSnapshotId(model.id),
        dataset_id=DatasetId(model.dataset_id),
        manifest_hash=ContentHash(model.manifest_hash),
        selection_definition=model.selection_definition,
        manifest_locator=model.manifest_locator,
        content_hash=ContentHash(model.content_hash),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
    )


def _project_from_model(model: ProjectModel) -> Project:
    return Project(
        id=ProjectId(model.id),
        name=model.name,
        description=model.description,
        lifecycle_status=LifecycleStatus(model.lifecycle_status),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )


def _workspace_from_model(model: WorkspaceModel) -> Workspace:
    return Workspace(
        id=WorkspaceId(model.id),
        project_id=ProjectId(model.project_id),
        name=model.name,
        locator=model.locator,
        lifecycle_status=LifecycleStatus(model.lifecycle_status),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )


def _research_question_from_model(model: ResearchQuestionModel) -> ResearchQuestion:
    return ResearchQuestion(
        id=ResearchQuestionId(model.id),
        project_id=ProjectId(model.project_id),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        current_version_id=(
            ResearchQuestionVersionId(model.current_version_id)
            if model.current_version_id is not None
            else None
        ),
        row_version=model.row_version,
    )


@_verified_persisted("ResearchQuestionVersion")
def _research_question_version_from_model(
    model: ResearchQuestionVersionModel,
) -> ResearchQuestionVersion:
    return ResearchQuestionVersion(
        id=ResearchQuestionVersionId(model.id),
        research_question_id=ResearchQuestionId(model.research_question_id),
        version_number=model.version_number,
        status=VersionStatus(model.status),
        question_text=model.question_text,
        scope=model.scope,
        rationale=model.rationale,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        content_hash=ContentHash(model.content_hash) if model.content_hash else None,
        hash_scheme=CANONICAL_JSON_HASH_SCHEME if model.content_hash else None,
        frozen_at=model.frozen_at,
        row_version=model.row_version,
    )


def _hypothesis_from_model(model: HypothesisModel) -> Hypothesis:
    return Hypothesis(
        id=HypothesisId(model.id),
        project_id=ProjectId(model.project_id),
        research_question_id=(
            ResearchQuestionId(model.research_question_id)
            if model.research_question_id is not None
            else None
        ),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        current_version_id=(
            HypothesisVersionId(model.current_version_id)
            if model.current_version_id is not None
            else None
        ),
        row_version=model.row_version,
    )


@_verified_persisted("HypothesisVersion")
def _hypothesis_version_from_model(model: HypothesisVersionModel) -> HypothesisVersion:
    return HypothesisVersion(
        id=HypothesisVersionId(model.id),
        hypothesis_id=HypothesisId(model.hypothesis_id),
        version_number=model.version_number,
        status=VersionStatus(model.status),
        statement=model.statement,
        expected_direction=model.expected_direction,
        success_criteria=model.success_criteria,
        rationale=model.rationale,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        content_hash=ContentHash(model.content_hash) if model.content_hash else None,
        hash_scheme=CANONICAL_JSON_HASH_SCHEME if model.content_hash else None,
        frozen_at=model.frozen_at,
        row_version=model.row_version,
    )


def _experiment_spec_from_model(model: ExperimentSpecModel) -> ExperimentSpec:
    return ExperimentSpec(
        id=ExperimentSpecId(model.id),
        project_id=ProjectId(model.project_id),
        hypothesis_id=HypothesisId(model.hypothesis_id) if model.hypothesis_id else None,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        current_version_id=(
            ExperimentSpecVersionId(model.current_version_id)
            if model.current_version_id is not None
            else None
        ),
        row_version=model.row_version,
    )


@_verified_persisted("ExperimentSpecVersion")
def _experiment_spec_version_from_model(
    model: ExperimentSpecVersionModel,
) -> ExperimentSpecVersion:
    return ExperimentSpecVersion(
        id=ExperimentSpecVersionId(model.id),
        experiment_spec_id=ExperimentSpecId(model.experiment_spec_id),
        version_number=model.version_number,
        status=VersionStatus(model.status),
        title=model.title,
        objective=model.objective,
        protocol=model.protocol,
        planned_metrics=model.planned_metrics,
        seed_policy=model.seed_policy,
        analysis_plan=model.analysis_plan,
        content_hash=ContentHash(model.content_hash) if model.content_hash else None,
        hash_scheme=CANONICAL_JSON_HASH_SCHEME if model.content_hash else None,
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        frozen_at=model.frozen_at,
        row_version=model.row_version,
    )


def _require_one_row(rowcount: int, resource: str, identifier: object) -> None:
    if rowcount != 1:
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            f"{resource} was modified concurrently",
            {"id": str(identifier)},
        )


def _not_found(resource: str, identifier: object) -> ResearchBaseError:
    return ResearchBaseError(
        ErrorCode.NOT_FOUND, f"{resource} was not found", {"id": str(identifier)}
    )
