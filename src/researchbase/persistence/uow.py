"""Synchronous SQLAlchemy UnitOfWork for one application transaction."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from researchbase.application.ports import (
    ActorRepository,
    ExperimentSpecRepository,
    HypothesisRepository,
    ProjectRepository,
    ResearchQuestionRepository,
    WorkspaceRepository,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.repositories import (
    SqlAlchemyActorRepository,
    SqlAlchemyExperimentSpecRepository,
    SqlAlchemyHypothesisRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyResearchQuestionRepository,
    SqlAlchemyWorkspaceRepository,
)


class SqlAlchemyUnitOfWork:
    actors: ActorRepository
    projects: ProjectRepository
    workspaces: WorkspaceRepository
    research_questions: ResearchQuestionRepository
    hypotheses: HypothesisRepository
    experiment_specs: ExperimentSpecRepository

    def __init__(self, session_factory: Callable[[], Session] | sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

        self._committed = False

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self._session.begin()
        self.actors = SqlAlchemyActorRepository(self._session)
        self.projects = SqlAlchemyProjectRepository(self._session)
        self.workspaces = SqlAlchemyWorkspaceRepository(self._session)
        self.research_questions = SqlAlchemyResearchQuestionRepository(self._session)
        self.hypotheses = SqlAlchemyHypothesisRepository(self._session)
        self.experiment_specs = SqlAlchemyExperimentSpecRepository(self._session)
        return self

    def commit(self) -> None:
        try:
            self._require_session().commit()
        except IntegrityError as exc:
            if "uq_actors_external_key" in str(exc.orig):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "external_key is already in use",
                    {"field": "external_key"},
                ) from exc
            if (
                "uq_research_question_versions_parent_version" in str(exc.orig)
                or "uq_hypothesis_versions_parent_version" in str(exc.orig)
                or "uq_experiment_spec_versions_parent_version" in str(exc.orig)
            ):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "version_number is already in use for this parent",
                    {"field": "version_number"},
                ) from exc
            raise
        self._committed = True

    def rollback(self) -> None:
        self._require_session().rollback()
        self._committed = False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None or not self._committed:
            self._session.rollback()
        self._session.close()
        self._session = None

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork must be entered before use")
        return self._session
