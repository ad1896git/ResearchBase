"""Explicit SQLAlchemy repository adapters for PR-02 domain models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from researchbase.domain.experiment import (
    ExperimentSpec,
    ExperimentSpecId,
    ExperimentSpecVersion,
    ExperimentSpecVersionId,
)
from researchbase.domain.identity import Actor, ActorType
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
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import CANONICAL_JSON_HASH_SCHEME, ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.models import (
    ActorModel,
    ExperimentSpecModel,
    ExperimentSpecVersionModel,
    HypothesisModel,
    HypothesisVersionModel,
    ProjectModel,
    ResearchQuestionModel,
    ResearchQuestionVersionModel,
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

    def update_version(
        self, version: ResearchQuestionVersion, expected_row_version: int
    ) -> None:
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
            select(HypothesisModel)
            .where(HypothesisModel.id == hypothesis_id)
            .with_for_update()
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
            select(ExperimentSpecModel)
            .where(ExperimentSpecModel.id == spec_id)
            .with_for_update()
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
