"""Local-first Application composition over the existing canonical services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from researchbase.application.phase2_identity import (
    BootstrapAuthority,
    Phase2IdentityService,
    VerifiedSubject,
)
from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class LocalCredentials(Protocol):
    def subject(self) -> VerifiedSubject: ...
    def is_valid(self, principal: VerifiedPrincipal | VerifiedSubject, at: datetime) -> bool: ...
    def bootstrap_authority(self) -> BootstrapAuthority: ...


class LocalWorkbenchService:
    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        credentials: LocalCredentials,
        identity: Phase2IdentityService,
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        self._identity = identity

    def authenticate(self) -> VerifiedPrincipal:
        subject = self._credentials.subject()
        with self._factory() as uow:
            facts = uow.phase2_identity.resolve_local_binding(subject)
            at = uow.phase2_identity.database_time()
            if (
                facts is None
                or facts["retired_at"] is not None
                or facts["bound_at"] > at
                or (facts["revoked_at"] is not None and facts["revoked_at"] <= at)
                or not self._credentials.is_valid(subject, at)
            ):
                raise ResearchBaseError(
                    ErrorCode.AUTHENTICATION_REQUIRED, "no active local actor binding is available"
                )
            return VerifiedPrincipal(
                facts["actor_id"],
                subject.deployment_id,
                subject.subject_kind,
                subject.subject_value,
                subject.credential_id,
                at,
            )

    def bootstrap(self, request_id: UUID, display_name: str, project_name: str):
        # Authenticate the host first, including for a closed bootstrap.
        self._credentials.subject()
        with self._factory() as uow:
            if not uow.phase2_identity.actors_and_projects_empty():
                raise ResearchBaseError(
                    ErrorCode.BOOTSTRAP_CLOSED, "first-owner bootstrap is closed"
                )
        return self._identity.bootstrap_first_owner(
            self._credentials.bootstrap_authority(),
            request_id=request_id,
            display_name=display_name,
            project_name=project_name,
        )

    def authorize(
        self, uow: UnitOfWork, project_id: UUID, write: bool, actor_id: UUID | None
    ) -> None:
        # Authenticate again inside the command transaction; never use a CLI actor flag.
        subject = self._credentials.subject()
        repo = uow.phase2_identity
        uow.literature_search_plan.lock_project(project_id)
        facts = repo.resolve_local_binding(subject)
        if facts is None:
            raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "local binding unavailable")
        if actor_id is not None and actor_id != facts["actor_id"]:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "actor does not match the local principal")
        at = repo.database_time()
        principal = VerifiedPrincipal(
            facts["actor_id"],
            subject.deployment_id,
            subject.subject_kind,
            subject.subject_value,
            subject.credential_id,
            at,
        )
        # Existing plan authorization locks actor/binding/membership/role rows first.
        candidates = uow.literature_search_plan.authorize(principal, project_id)
        if write and not uow.literature_search_plan.project_active(project_id):
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority is unavailable")
        at = repo.database_time()
        if self._credentials.is_valid(principal, at):
            for row in candidates:
                roles = (
                    {"OWNER", "RESEARCHER"}
                    if write
                    else {"OWNER", "RESEARCHER", "VIEWER", "REVIEWER", "APPROVER"}
                )
                if (
                    row["retired_at"] is None
                    and row["actor_type"] == "HUMAN"
                    and row["membership_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["binding_status"] == "ACTIVE"
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                ):
                    return
        raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority is unavailable")
