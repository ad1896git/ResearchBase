"""Repository and transaction ports used by application commands."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.evidence import Dataset, DatasetId, DatasetSnapshot, DatasetSnapshotId
from researchbase.domain.experiment import (
    ExperimentSpec,
    ExperimentSpecId,
    ExperimentSpecVersion,
    ExperimentSpecVersionId,
)
from researchbase.domain.identity import Actor
from researchbase.domain.metric import (
    MetricDefinition,
    MetricDefinitionId,
    MetricDefinitionVersion,
    MetricDefinitionVersionId,
)
from researchbase.domain.organization import Project, ProjectId, Workspace, WorkspaceId
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
from researchbase.foundation.ids import ActorId


class ActorRepository(Protocol):
    def add(self, actor: Actor) -> None: ...

    def get(self, actor_id: ActorId) -> Actor | None: ...

    def get_by_external_key(self, external_key: str) -> Actor | None: ...


class ProjectRepository(Protocol):
    def add(self, project: Project) -> None: ...

    def get(self, project_id: ProjectId) -> Project | None: ...


class WorkspaceRepository(Protocol):
    def add(self, workspace: Workspace) -> None: ...

    def get(self, workspace_id: WorkspaceId) -> Workspace | None: ...


class ResearchQuestionRepository(Protocol):
    def add(self, question: ResearchQuestion) -> None: ...

    def add_version(self, version: ResearchQuestionVersion) -> None: ...

    def get(self, question_id: ResearchQuestionId) -> ResearchQuestion | None: ...

    def get_for_update(self, question_id: ResearchQuestionId) -> ResearchQuestion | None: ...

    def get_version(
        self, version_id: ResearchQuestionVersionId
    ) -> ResearchQuestionVersion | None: ...

    def get_version_for_update(
        self, version_id: ResearchQuestionVersionId
    ) -> ResearchQuestionVersion | None: ...

    def get_current_version(
        self, question_id: ResearchQuestionId
    ) -> ResearchQuestionVersion | None: ...

    def list_history(self, question_id: ResearchQuestionId) -> list[ResearchQuestionVersion]: ...

    def max_version_number(self, question_id: ResearchQuestionId) -> int: ...

    def update_current_version(
        self,
        question_id: ResearchQuestionId,
        version_id: ResearchQuestionVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None: ...

    def update_version(
        self, version: ResearchQuestionVersion, expected_row_version: int
    ) -> None: ...


class HypothesisRepository(Protocol):
    def add(self, hypothesis: Hypothesis) -> None: ...

    def add_version(self, version: HypothesisVersion) -> None: ...

    def get(self, hypothesis_id: HypothesisId) -> Hypothesis | None: ...

    def get_for_update(self, hypothesis_id: HypothesisId) -> Hypothesis | None: ...

    def get_version(self, version_id: HypothesisVersionId) -> HypothesisVersion | None: ...

    def get_version_for_update(
        self, version_id: HypothesisVersionId
    ) -> HypothesisVersion | None: ...

    def get_current_version(self, hypothesis_id: HypothesisId) -> HypothesisVersion | None: ...

    def list_history(self, hypothesis_id: HypothesisId) -> list[HypothesisVersion]: ...

    def max_version_number(self, hypothesis_id: HypothesisId) -> int: ...

    def update_current_version(
        self,
        hypothesis_id: HypothesisId,
        version_id: HypothesisVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None: ...

    def update_version(self, version: HypothesisVersion, expected_row_version: int) -> None: ...


class ExperimentSpecRepository(Protocol):
    def add(self, aggregate: ExperimentSpec) -> None: ...

    def add_version(self, version: ExperimentSpecVersion) -> None: ...

    def get(self, spec_id: ExperimentSpecId) -> ExperimentSpec | None: ...

    def get_for_update(self, spec_id: ExperimentSpecId) -> ExperimentSpec | None: ...

    def get_version(self, version_id: ExperimentSpecVersionId) -> ExperimentSpecVersion | None: ...

    def get_version_for_update(
        self, version_id: ExperimentSpecVersionId
    ) -> ExperimentSpecVersion | None: ...

    def get_current_version(self, spec_id: ExperimentSpecId) -> ExperimentSpecVersion | None: ...

    def list_history(self, spec_id: ExperimentSpecId) -> list[ExperimentSpecVersion]: ...

    def max_version_number(self, spec_id: ExperimentSpecId) -> int: ...

    def update_current_version(
        self,
        spec_id: ExperimentSpecId,
        version_id: ExperimentSpecVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None: ...

    def update_version(self, version: ExperimentSpecVersion, expected_row_version: int) -> None: ...


class DatasetRepository(Protocol):
    def add(self, dataset: Dataset) -> None: ...

    def get(self, dataset_id: DatasetId) -> Dataset | None: ...


class DatasetSnapshotRepository(Protocol):
    def add(self, snapshot: DatasetSnapshot) -> None: ...

    def get(self, snapshot_id: DatasetSnapshotId) -> DatasetSnapshot | None: ...

    def find_by_dataset_and_content_hash(
        self, dataset_id: DatasetId, content_hash: str
    ) -> DatasetSnapshot | None: ...


class ArtifactRepository(Protocol):
    def add(self, artifact: Artifact) -> None: ...

    def get(self, artifact_id: ArtifactId) -> Artifact | None: ...

    def get_for_update(self, artifact_id: ArtifactId) -> Artifact | None: ...

    def update_current_version(
        self,
        artifact_id: ArtifactId,
        version_id: ArtifactVersionId,
        expected_row_version: int,
    ) -> None: ...


class ArtifactVersionRepository(Protocol):
    def add(self, version: ArtifactVersion) -> None: ...

    def get(self, version_id: ArtifactVersionId) -> ArtifactVersion | None: ...

    def get_for_update(self, version_id: ArtifactVersionId) -> ArtifactVersion | None: ...

    def find_by_artifact_and_content_hash(
        self, artifact_id: ArtifactId, content_hash: str
    ) -> ArtifactVersion | None: ...

    def max_version_number(self, artifact_id: ArtifactId) -> int: ...

    def list_history(self, artifact_id: ArtifactId) -> list[ArtifactVersion]: ...

    def update(self, version: ArtifactVersion, expected_row_version: int) -> None: ...


class MetricDefinitionRepository(Protocol):
    def add(self, aggregate: MetricDefinition) -> None: ...

    def get(self, metric_id: MetricDefinitionId) -> MetricDefinition | None: ...

    def get_for_update(self, metric_id: MetricDefinitionId) -> MetricDefinition | None: ...

    def update_current_version(
        self,
        metric_id: MetricDefinitionId,
        version_id: MetricDefinitionVersionId,
        expected_row_version: int,
        *,
        increment: bool = True,
    ) -> None: ...


class MetricDefinitionVersionRepository(Protocol):
    def add(self, version: MetricDefinitionVersion) -> None: ...

    def get(self, version_id: MetricDefinitionVersionId) -> MetricDefinitionVersion | None: ...

    def get_for_update(
        self, version_id: MetricDefinitionVersionId
    ) -> MetricDefinitionVersion | None: ...

    def max_version_number(self, metric_id: MetricDefinitionId) -> int: ...

    def list_history(self, metric_id: MetricDefinitionId) -> list[MetricDefinitionVersion]: ...

    def update(self, version: MetricDefinitionVersion, expected_row_version: int) -> None: ...


class UnitOfWork(Protocol):
    actors: ActorRepository
    projects: ProjectRepository
    workspaces: WorkspaceRepository
    research_questions: ResearchQuestionRepository
    hypotheses: HypothesisRepository
    experiment_specs: ExperimentSpecRepository
    datasets: DatasetRepository
    dataset_snapshots: DatasetSnapshotRepository
    artifacts: ArtifactRepository
    artifact_versions: ArtifactVersionRepository
    metric_definitions: MetricDefinitionRepository
    metric_definition_versions: MetricDefinitionVersionRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
