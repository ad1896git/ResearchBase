"""FastAPI composition root for the Phase 1 HTTP adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI

from researchbase import __version__
from researchbase.application.commands import ApplicationService
from researchbase.application.governance import GovernanceService
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.structured_logging import configure_logging
from researchbase.foundation.time import SystemClock
from researchbase.persistence.config import load_settings
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


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


def build_services() -> ServiceBundle:
    settings = load_settings()
    configure_logging(settings.log_level, settings.application_env)
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    clock = SystemClock()
    store = ContentAddressedFilesystemArtifactStore(Path(settings.artifact_store_root))
    return ServiceBundle(
        ApplicationService(uow_factory, clock, store),
        ProvenanceQueryService(uow_factory),
        GovernanceService(uow_factory, clock),
        GovernanceQueryService(uow_factory),
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
