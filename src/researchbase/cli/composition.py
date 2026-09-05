"""CLI composition root; command modules receive only Application services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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


class CliServices(Protocol):
    application: object
    provenance: object
    governance: object
    governance_queries: object


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
