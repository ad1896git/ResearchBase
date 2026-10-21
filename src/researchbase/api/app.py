"""FastAPI composition root for the Phase 1 HTTP adapter."""

from __future__ import annotations

import os
import pwd
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI

from researchbase import __version__
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.agent_runtime.application.task_safety import TaskSafetyService
from researchbase.application.commands import ApplicationService
from researchbase.application.decision import DecisionService
from researchbase.application.governance import GovernanceService
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.internal_review import InternalReviewService
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_plan import LiteratureSearchPlanService
from researchbase.application.literature_search_provider import StaticSearchCapabilityRegistry
from researchbase.application.novelty import NoveltyService
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.application.revision_action import RevisionActionService
from researchbase.application.source_identity import SourceIdentityService
from researchbase.application.source_merge import SourceMergeGovernanceService
from researchbase.application.source_merge_execution import SourceMergeExecutionService
from researchbase.application.source_version import SourceVersionService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.structured_logging import configure_logging
from researchbase.foundation.time import SystemClock
from researchbase.local_identity import LocalIdentityAdapter, process_uid
from researchbase.persistence.config import load_settings
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork, research_task_uow_factory


class HttpServices(Protocol):
    @property
    def application(self) -> object: ...

    @property
    def provenance(self) -> object: ...

    @property
    def governance(self) -> object: ...

    @property
    def governance_queries(self) -> object: ...


@dataclass(frozen=True, slots=True)
class ServiceBundle:
    application: ApplicationService
    provenance: ProvenanceQueryService
    governance: GovernanceService
    governance_queries: GovernanceQueryService
    literature: SourceIdentityService | None = None
    source_merge: SourceMergeGovernanceService | None = None
    source_versions: SourceVersionService | None = None
    source_merge_execution: SourceMergeExecutionService | None = None
    literature_search_plans: LiteratureSearchPlanService | None = None
    literature_search_executions: LiteratureSearchExecutionService | None = None
    novelty: NoveltyService | None = None
    decisions: DecisionService | None = None
    internal_reviews: InternalReviewService | None = None
    revision_actions: RevisionActionService | None = None
    research_tasks: ResearchTaskService | None = None
    task_safety: TaskSafetyService | None = None


def build_services() -> ServiceBundle:
    settings = load_settings()
    configure_logging(settings.log_level, settings.application_env)
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    clock = SystemClock()
    store = ContentAddressedFilesystemArtifactStore(Path(settings.artifact_store_root))
    root = Path(
        os.environ.get(
            "RESEARCHBASE_LOCAL_ROOT",
            str(Path(pwd.getpwuid(process_uid()).pw_dir) / ".researchbase-local"),
        )
    )
    credentials = LocalIdentityAdapter(root)
    return ServiceBundle(
        ApplicationService(uow_factory, clock, store),
        ProvenanceQueryService(uow_factory),
        GovernanceService(uow_factory, clock),
        GovernanceQueryService(uow_factory),
        SourceIdentityService(uow_factory, credentials),
        SourceMergeGovernanceService(uow_factory, credentials),
        SourceVersionService(uow_factory, credentials),
        SourceMergeExecutionService(uow_factory, credentials),
        LiteratureSearchPlanService(uow_factory, credentials),
        LiteratureSearchExecutionService(
            literature_search_execution_uow_factory(session_factory),
            StaticSearchCapabilityRegistry(),
            credential_verifier=credentials,
        ),
        NoveltyService(
            uow_factory, credentials, LiteratureEvidenceService(uow_factory, credentials, store)
        ),
        internal_reviews=InternalReviewService(
            uow_factory, credentials, LiteratureEvidenceService(uow_factory, credentials, store)
        ),
        revision_actions=RevisionActionService(
            uow_factory, credentials, LiteratureEvidenceService(uow_factory, credentials, store)
        ),
        task_safety=TaskSafetyService(
            research_task_uow_factory(settings.database_url), credentials, store
        ),
        research_tasks=ResearchTaskService(
            research_task_uow_factory(settings.database_url), credentials, store
        ),
        decisions=DecisionService(
            uow_factory,
            credentials,
            LiteratureEvidenceService(uow_factory, credentials, store),
            store,
        ),
    )


def create_app(services: HttpServices | None = None) -> FastAPI:
    from researchbase.api.errors import install_error_handlers
    from researchbase.api.routes import router

    application = FastAPI(title="ResearchBase", version=__version__)
    application.state.services = services or build_services()
    install_error_handlers(application)
    application.include_router(router)

    @application.get("/health", operation_id="health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
