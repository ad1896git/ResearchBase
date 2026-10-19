"""CLI composition root; command modules receive only Application services."""

from __future__ import annotations

import os
import pwd
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy.engine import make_url

from researchbase.adapters.crossref import CrossrefVerifier
from researchbase.adapters.metadata_journal import MetadataDispatchJournal
from researchbase.adapters.openalex import OpenAlexSearchCapability
from researchbase.application.commands import ApplicationService
from researchbase.application.decision import DecisionService
from researchbase.application.governance import GovernanceService
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.internal_review import InternalReviewService
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_plan import LiteratureSearchPlanService
from researchbase.application.literature_search_provider import StaticSearchCapabilityRegistry
from researchbase.application.local_workbench import LocalWorkbenchService
from researchbase.application.metadata_observation import MetadataObservationService
from researchbase.application.novelty import NoveltyService
from researchbase.application.phase2_identity import Phase2IdentityService, VerifiedSubject
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.application.revision_action import RevisionActionService
from researchbase.application.search_result_resolution import SearchResultResolutionService
from researchbase.application.source_identity import SourceIdentityService
from researchbase.application.source_merge import SourceMergeGovernanceService
from researchbase.application.source_merge_execution import SourceMergeExecutionService
from researchbase.application.source_version import SourceVersionService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.structured_logging import configure_logging
from researchbase.foundation.time import SystemClock
from researchbase.local_identity import LocalIdentityAdapter, process_uid
from researchbase.persistence.config import load_settings
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork, search_result_resolution_uow_factory


class CliServices(Protocol):
    application: object
    provenance: object
    governance: object
    governance_queries: object


def _search_capabilities(
    database_url: str, openalex_api_key: str | None
) -> StaticSearchCapabilityRegistry:
    """Retained M3 cannot activate live retrieval before its separate TDG2 gate."""
    if make_url(database_url).database == "researchbase_m3_retained_20261011":
        return StaticSearchCapabilityRegistry()
    return StaticSearchCapabilityRegistry((OpenAlexSearchCapability(api_key=openalex_api_key),))


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
    verified_principal: VerifiedPrincipal | None = None
    local_identity: LocalWorkbenchService | None = None
    local_credentials: LocalIdentityAdapter | None = None
    metadata_observations: MetadataObservationService | None = None
    literature_evidence: LiteratureEvidenceService | None = None
    novelty: NoveltyService | None = None
    search_result_resolutions: SearchResultResolutionService | None = None
    decisions: DecisionService | None = None
    internal_reviews: InternalReviewService | None = None
    revision_actions: RevisionActionService | None = None


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
    identity = Phase2IdentityService(
        uow_factory,
        nonce_issuer=credentials,
        operator_policy=credentials,
        credential_verifier=credentials,
        subject_credential_verifier=LocalSubjectCredentials(credentials),
        attestation_verifier=UnavailableAttestations(),
        bootstrap_proof_verifier=credentials,
    )
    local = LocalWorkbenchService(uow_factory, credentials, identity)
    principal = None
    if root.exists():
        try:
            principal = local.authenticate()
        except ResearchBaseError:
            pass  # Bootstrap may legitimately have no canonical binding yet.
    sources = SourceIdentityService(uow_factory, credentials)
    versions = SourceVersionService(uow_factory, credentials)
    return ServiceBundle(
        ApplicationService(uow_factory, clock, store, project_authorizer=local.authorize),
        ProvenanceQueryService(uow_factory),
        GovernanceService(uow_factory, clock),
        GovernanceQueryService(uow_factory),
        sources,
        SourceMergeGovernanceService(uow_factory, credentials),
        versions,
        SourceMergeExecutionService(uow_factory, credentials),
        LiteratureSearchPlanService(uow_factory, credentials),
        LiteratureSearchExecutionService(
            literature_search_execution_uow_factory(session_factory),
            _search_capabilities(settings.database_url, os.environ.get("OPENALEX_API_KEY")),
            credential_verifier=credentials,
        ),
        principal,
        local,
        credentials,
        MetadataObservationService(
            uow_factory,
            credentials,
            store,
            MetadataDispatchJournal(
                Path(settings.artifact_store_root) / "metadata-invocations", CrossrefVerifier()
            ),
            sources,
            versions,
        ),
        LiteratureEvidenceService(uow_factory, credentials, store),
        NoveltyService(
            uow_factory, credentials, LiteratureEvidenceService(uow_factory, credentials, store)
        ),
        SearchResultResolutionService(
            search_result_resolution_uow_factory(settings.database_url), credentials, store
        ),
        internal_reviews=InternalReviewService(
            uow_factory, credentials, LiteratureEvidenceService(uow_factory, credentials, store)
        ),
        revision_actions=RevisionActionService(
            uow_factory, credentials, LiteratureEvidenceService(uow_factory, credentials, store)
        ),
        decisions=DecisionService(
            uow_factory,
            credentials,
            LiteratureEvidenceService(uow_factory, credentials, store),
            store,
        ),
    )


class UnavailableAttestations:
    """Local MVP does not authorize independent legacy/provisioning ceremonies."""

    def verify(self, attestation: object) -> bool:
        return False


class LocalSubjectCredentials:
    def __init__(self, adapter: LocalIdentityAdapter) -> None:
        self.adapter = adapter

    def is_valid(self, subject: VerifiedSubject, at: datetime) -> bool:
        return self.adapter.is_valid(subject, at)
