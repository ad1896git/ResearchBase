"""Explicit SQLAlchemy repository adapters for PR-02 domain models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
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
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import CANONICAL_JSON_HASH_SCHEME, ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.models import (
    ActorModel,
    ArtifactModel,
    ArtifactVersionModel,
    DatasetModel,
    DatasetSnapshotModel,
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
    WorkspaceModel,
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
                scope=version.scope,
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
                scope=version.scope,
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
                success_criteria=version.success_criteria,
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
                success_criteria=version.success_criteria,
                rationale=version.rationale,
                content_hash=str(version.content_hash) if version.content_hash else None,
                frozen_at=version.frozen_at,
                row_version=HypothesisVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "hypothesis version", version.id)


class SqlAlchemyExperimentSpecRepository:
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
                protocol=version.protocol,
                planned_metrics=version.planned_metrics,
                seed_policy=version.seed_policy,
                analysis_plan=version.analysis_plan,
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
                protocol=version.protocol,
                planned_metrics=version.planned_metrics,
                seed_policy=version.seed_policy,
                analysis_plan=version.analysis_plan,
                content_hash=str(version.content_hash) if version.content_hash else None,
                frozen_at=version.frozen_at,
                row_version=ExperimentSpecVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "experiment spec version", version.id)


class SqlAlchemyDatasetRepository:
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
                selection_definition=snapshot.selection_definition,
                manifest_locator=snapshot.manifest_locator,
                content_hash=str(snapshot.content_hash),
                created_by=snapshot.created_by,
                created_at=snapshot.created_at,
            )
        )

    def get(self, snapshot_id: DatasetSnapshotId) -> DatasetSnapshot | None:
        model = self._session.get(DatasetSnapshotModel, snapshot_id)
        return _dataset_snapshot_from_model(model) if model is not None else None

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
                metadata_json=version.metadata,
                created_by=version.created_by,
                created_at=version.created_at,
                frozen_at=version.frozen_at,
                row_version=version.row_version,
            )
        )

    def get(self, version_id: ArtifactVersionId) -> ArtifactVersion | None:
        model = self._session.get(ArtifactVersionModel, version_id)
        return _artifact_version_from_model(model) if model is not None else None

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
                metadata_json=version.metadata,
                frozen_at=version.frozen_at,
                row_version=ArtifactVersionModel.row_version + 1,
            )
        )
        result_any: Any = result
        _require_one_row(result_any.rowcount, "artifact version", version.id)


class SqlAlchemyMetricDefinitionRepository:
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
                definition=version.definition,
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
                definition=version.definition,
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
                structured_value=measurement.structured_value,
                unit=measurement.unit,
                evaluation_scope=measurement.evaluation_scope,
                content_hash=str(measurement.content_hash),
                created_by=measurement.created_by,
                created_at=measurement.created_at,
            )
        )

    def get(self, measurement_id: MeasurementId) -> Measurement | None:
        model = self._session.get(MeasurementModel, measurement_id)
        return _measurement_from_model(model) if model is not None else None

    def list_by_run(self, run_id: RunId) -> list[Measurement]:
        models = self._session.scalars(
            select(MeasurementModel)
            .where(MeasurementModel.run_id == run_id)
            .order_by(MeasurementModel.created_at, MeasurementModel.id)
        ).all()
        return [_measurement_from_model(model) for model in models]


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
