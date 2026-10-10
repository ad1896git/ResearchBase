"""Application orchestration for bounded literature-search execution."""

from __future__ import annotations

import random
import re
import time
import unicodedata
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Event, Lock
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

from researchbase.application.literature_search_provider import (
    ProviderError,
    ProviderFailureKind,
    SearchCallContext,
    SearchCapability,
    SearchCapabilityRegistry,
    SearchRequest,
)
from researchbase.domain.literature_search_execution import (
    AttemptStatus,
    DeliveryCertainty,
    ExecutionStatus,
    LiteratureSearchExecution,
    SearchHit,
    SearchQueryRecord,
    SearchResponse,
)
from researchbase.domain.phase2_identity import CredentialVerifier, VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

# Private transport context: a disconnect owns only its current request signal.
_http_disconnect: ContextVar[Event | None] = ContextVar("literature_http_disconnect", default=None)


@dataclass(frozen=True, slots=True)
class SearchQueryInput:
    query_text: str
    perspective: str | None = None
    query_type: str = "TEXT"


@dataclass(frozen=True, slots=True)
class CreateLiteratureSearchExecution:
    project_id: UUID
    plan_version_id: UUID
    actor_id: UUID
    deployment_id: str
    request_id: UUID
    provider_id: str
    provider_version: str
    queries: tuple[str | SearchQueryInput, ...]
    max_results: int = 20
    max_provider_attempts: int = 3
    timeout_seconds: int = 30
    execution_budget_seconds: int = 300
    principal: VerifiedPrincipal | None = None


@dataclass(frozen=True, slots=True)
class ExecuteLiteratureSearchExecution:
    execution_id: UUID
    actor_id: UUID
    deployment_id: str
    request_id: UUID
    project_id: UUID | None = None
    principal: VerifiedPrincipal | None = None


@dataclass(frozen=True, slots=True)
class CancelLiteratureSearchExecution:
    execution_id: UUID
    actor_id: UUID
    deployment_id: str
    request_id: UUID
    project_id: UUID | None = None
    principal: VerifiedPrincipal | None = None


@dataclass(frozen=True, slots=True)
class RecoverLiteratureSearchExecution:
    execution_id: UUID
    actor_id: UUID
    deployment_id: str
    request_id: UUID
    project_id: UUID | None = None
    principal: VerifiedPrincipal | None = None


class ExecutionRepository(Protocol):
    def database_now(self) -> datetime: ...
    def validate_plan_version(self, project_id: UUID, version_id: UUID) -> None: ...
    def plan_invocation(self, project_id: UUID, version_id: UUID) -> tuple[str, object]: ...
    def create(self, execution: LiteratureSearchExecution, receipt: dict[str, Any]) -> None: ...
    def get(self, execution_id: UUID) -> LiteratureSearchExecution | None: ...
    def get_for_update(self, execution_id: UUID) -> LiteratureSearchExecution | None: ...
    def save(self, execution: LiteratureSearchExecution, expected_row_version: int) -> None: ...
    def receipt(self, key: tuple[str, UUID, UUID, str, UUID]) -> dict[str, Any] | None: ...
    def save_receipt(
        self, key: tuple[str, UUID, UUID, str, UUID], value: dict[str, Any]
    ) -> None: ...
    def reserve(
        self,
        execution_id: UUID,
        query_index: int,
        actor_id: UUID,
        reserved_at: datetime | None = None,
    ) -> UUID: ...
    def reservation(self, attempt_id: UUID) -> dict[str, Any] | None: ...
    def attempts(self, execution_id: UUID) -> list[dict[str, Any]]: ...
    def seal(self, attempt_id: UUID, values: dict[str, Any]) -> None: ...
    def append_query(self, record: SearchQueryRecord) -> None: ...
    def append_results(
        self, query_id: UUID, response: SearchResponse, retrieved_at: datetime
    ) -> None: ...

    def append_event(
        self,
        execution: LiteratureSearchExecution,
        kind: str,
        actor_id: UUID,
        attempt_id: UUID | None = None,
    ) -> None: ...
    def next_query_ordinal(self, execution_id: UUID) -> int: ...

    def provenance(self, execution_id: UUID) -> dict[str, Any]: ...
    def list_executions(
        self, project_id: UUID, limit: int, after: UUID | None = None
    ) -> list[LiteratureSearchExecution]: ...


class LiteratureSearchExecutionService:
    def __init__(
        self,
        uow_factory: Callable[[], Any],
        provider: SearchCapability | SearchCapabilityRegistry,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] | None = None,
        credential_verifier: CredentialVerifier | None = None,
        after_cancel_admission: Callable[[], None] | None = None,
        random_uniform: Callable[[float, float], float] | None = None,
        allow_unverified_principal: bool = False,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._providers = provider
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or time.sleep
        self._credential_verifier = credential_verifier
        self._after_cancel_admission = after_cancel_admission
        self._random_uniform = random_uniform or random.uniform
        self._allow_unverified_principal = allow_unverified_principal
        self._cancellation_events: dict[UUID, Event] = {}
        self._cancellation_events_lock = Lock()

    def create(self, command: CreateLiteratureSearchExecution) -> dict[str, Any]:
        return self._retry_db(lambda: self._create_once(command))

    def _create_once(self, command: CreateLiteratureSearchExecution) -> dict[str, Any]:
        self._validate_principal_scope(command.principal, command.actor_id, command.deployment_id)
        if not command.queries or len(command.queries) > 32:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "queries must contain 1 to 32 items"
            )
        provider_id = unicodedata.normalize("NFC", command.provider_id.strip())
        provider_version = unicodedata.normalize("NFC", command.provider_version.strip())
        if (
            not provider_id
            or len(provider_id) > 128
            or any(unicodedata.category(char).startswith("C") for char in provider_id)
        ):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "provider_id length is invalid")
        if (
            not provider_version
            or len(provider_version) > 128
            or any(unicodedata.category(char).startswith("C") for char in provider_version)
        ):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "provider_version length is invalid"
            )
        for name, value in (
            ("max_results", command.max_results),
            ("max_provider_attempts", command.max_provider_attempts),
            ("timeout_seconds", command.timeout_seconds),
            ("execution_budget_seconds", command.execution_budget_seconds),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, f"{name} must be an integer")
        if not 1 <= command.max_provider_attempts <= 3:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "max_provider_attempts must be between 1 and 3"
            )
        if not 1 <= command.max_results <= 100:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "max_results must be 1 to 100")
        if not 1 <= command.timeout_seconds <= 30:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "timeout_seconds must be 1 to 30")
        if not 1 <= command.execution_budget_seconds <= 600:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "execution_budget_seconds must be 1 to 600"
            )
        queries = [self._query_payload(item) for item in command.queries]
        payload = {
            "project_id": str(command.project_id),
            "search_plan_version_id": str(command.plan_version_id),
            "provider_id": provider_id,
            "provider_version": provider_version,
            "queries": queries,
            "max_results": command.max_results,
            "max_provider_attempts": command.max_provider_attempts,
            "timeout_seconds": command.timeout_seconds,
            "execution_budget_seconds": command.execution_budget_seconds,
        }
        key = self._key(
            command.deployment_id,
            command.actor_id,
            command.project_id,
            "CREATE_LITERATURE_SEARCH_EXECUTION",
            command.request_id,
        )
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            self._lock_project_command(uow, command.project_id, key)
            prior = repo.receipt(key)
            if prior is not None:
                self._authorize(uow, command.principal, command.project_id, locks_acquired=True)
                if not self._receipt_matches(prior, payload):
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "request key payload differs"
                    )
                return prior["dto"]
            validator = getattr(repo, "validate_plan_version", None)
            if validator is not None:
                validator(command.project_id, command.plan_version_id, lock=True)
            self._authorize(uow, command.principal, command.project_id, locks_acquired=True)
            selected_provider = self._provider_for(provider_id, provider_version)
            if selected_provider is None:
                versions = getattr(self._providers, "versions", None)
                if callable(versions) and versions(provider_id):
                    raise ResearchBaseError(
                        ErrorCode.ADAPTER_VERSION_MISMATCH,
                        "search adapter version mismatch",
                    )
                raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "search adapter unavailable")
            plan_invocation = getattr(repo, "plan_invocation", None)
            _plan_hash, plan_material = (
                plan_invocation(command.project_id, command.plan_version_id)
                if plan_invocation is not None
                else ("unit-test-unverified", {})
            )
            planned_providers = plan_material.get("planned_providers", ())  # type: ignore[union-attr]
            if provider_id not in planned_providers:
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR, "provider is not planned by the frozen plan"
                )
            source_scope = plan_material.get("source_scope")  # type: ignore[union-attr]
            if source_scope is not None and source_scope not in getattr(
                selected_provider, "supported_source_scopes", ()
            ):
                raise ResearchBaseError(
                    ErrorCode.ADAPTER_UNAVAILABLE, "provider does not support plan source scope"
                )
            execution = LiteratureSearchExecution.create(
                project_id=command.project_id,
                plan_version_id=command.plan_version_id,
                requested_by=command.actor_id,
                idempotency_key=command.request_id,
                execution_context={
                    "schema_version": 1,
                    "queries": queries,
                    "provider_id": provider_id,
                    "provider_version": provider_version,
                    "max_results": command.max_results,
                    "max_provider_attempts": command.max_provider_attempts,
                    "timeout_seconds": command.timeout_seconds,
                    "execution_budget_seconds": command.execution_budget_seconds,
                },
            )
            dto = self._dto(execution, "CREATE_LITERATURE_SEARCH_EXECUTION", repo.database_now())
            repo.create(execution, {"payload": payload, "dto": dto})
            repo.save_receipt(key, {"payload": payload, "dto": dto})
            uow.commit()
            return dto

    def execute(self, command: ExecuteLiteratureSearchExecution) -> dict[str, Any]:
        self._validate_principal_scope(command.principal, command.actor_id, command.deployment_id)
        dto, execution_id, reserved = self._retry_db(lambda: self._execute_admission(command))
        if reserved is not None:
            self._drive(
                execution_id,
                command.actor_id,
                command.principal,
                reserved,
                command.project_id,
            )
        self._retry_db(
            lambda: self._authorize_disclosure(execution_id, command.principal, command.project_id)
        )
        return dto

    def _execute_admission(
        self, command: ExecuteLiteratureSearchExecution
    ) -> tuple[dict[str, Any], UUID, tuple[UUID, int] | None]:
        reserved: tuple[UUID, int] | None = None
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            project_id = command.project_id
            if project_id is None:
                # Legacy/internal callers may omit scope. This lookup only discovers the lock
                # key; all decisions use the locked reread below.
                execution = repo.get(command.execution_id)
                project_id = execution.project_id if execution is not None else None
            if project_id is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if command.project_id is not None:
                key = self._key(
                    command.deployment_id,
                    command.actor_id,
                    project_id,
                    "EXECUTE_LITERATURE_SEARCH_EXECUTION",
                    command.request_id,
                )
                self._lock_project_command(uow, project_id, key)
                execution = repo.get(command.execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id != execution.project_id:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            key = self._key(
                command.deployment_id,
                command.actor_id,
                execution.project_id,
                "EXECUTE_LITERATURE_SEARCH_EXECUTION",
                command.request_id,
            )
            if command.project_id is None:
                self._lock_project_command(uow, execution.project_id, key)
            if execution.status is ExecutionStatus.PLANNED:
                plan_validator = getattr(repo, "validate_plan_version", None)
                if plan_validator is not None:
                    plan_validator(execution.project_id, execution.plan_version_id, lock=True)
                plan_invocation = getattr(repo, "plan_invocation", None)
                if plan_invocation is not None:
                    plan_invocation(execution.project_id, execution.plan_version_id)
            execution = repo.get_for_update(command.execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._authorize(uow, command.principal, execution.project_id, locks_acquired=True)
            prior = repo.receipt(key)
            if prior is not None:
                command_payload = {
                    "project_id": str(execution.project_id),
                    "execution_id": str(command.execution_id),
                }
                if not self._receipt_matches(prior, command_payload):
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "request key payload differs"
                    )
                uow.commit()
                return prior["dto"], execution.id, None
            if execution.cancellation_requested:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "execution has a durable cancellation request",
                )
            if execution.status not in {ExecutionStatus.PLANNED, ExecutionStatus.RUNNING}:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "execution is not resumable"
                )
            existing_attempts = repo.attempts(execution.id)
            active = any(
                row.get("status") == AttemptStatus.RESERVED.value for row in existing_attempts
            )
            if execution.status is ExecutionStatus.PLANNED:
                expected_version = execution.row_version
                reserved_at = repo.database_now()
                execution.start(command.actor_id, reserved_at)
                repo.save(execution, expected_version)
                attempt_id = repo.reserve(
                    execution.id, 0, command.actor_id, reserved_at=reserved_at
                )
                reserved = (attempt_id, 0)
            elif not active:
                if execution.cancellation_requested or any(
                    row.get("status")
                    in {
                        AttemptStatus.UNKNOWN.value,
                        AttemptStatus.PERMANENT_FAILURE.value,
                        AttemptStatus.CANCELLED.value,
                    }
                    for row in existing_attempts
                ):
                    raise ResearchBaseError(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "execution has a durable stop condition",
                    )
                successes = sum(
                    1
                    for row in existing_attempts
                    if row.get("status") == AttemptStatus.SUCCEEDED.value
                )
                query_index = successes
                if query_index >= len(execution.execution_context["queries"]):
                    raise ResearchBaseError(
                        ErrorCode.INVALID_STATE_TRANSITION, "execution has no remaining query"
                    )
                query_attempts = [
                    row for row in existing_attempts if row.get("query_index") == query_index
                ]
                if len(query_attempts) >= execution.execution_context["max_provider_attempts"]:
                    raise ResearchBaseError(
                        ErrorCode.INVALID_STATE_TRANSITION, "provider retry budget is exhausted"
                    )
                expected_version = execution.row_version
                execution.row_version += 1
                repo.save(execution, expected_version)
                attempt_id = repo.reserve(execution.id, query_index, command.actor_id)
                reserved = (attempt_id, query_index)
            dto = self._dto(execution, "EXECUTE_LITERATURE_SEARCH_EXECUTION", repo.database_now())
            repo.save_receipt(
                key,
                {
                    "payload": {
                        "project_id": str(execution.project_id),
                        "execution_id": str(command.execution_id),
                    },
                    "dto": dto,
                },
            )
            uow.commit()
        return dto, execution.id, reserved

    def cancel(self, command: CancelLiteratureSearchExecution) -> dict[str, Any]:
        dto, finalize = self._retry_db(
            lambda: self._cancel_or_recover(
                command.execution_id,
                command.actor_id,
                command.deployment_id,
                command.request_id,
                False,
                command.project_id,
                command.principal,
            )
        )
        self._cancellation_event(command.execution_id).set()
        if finalize and self._after_cancel_admission is not None:
            self._after_cancel_admission()
        if finalize:
            self._retry_db(
                lambda: self._finalize_cancel(
                    command.execution_id,
                    command.actor_id,
                    command.principal,
                    command.project_id,
                )
            )
        self._retry_db(
            lambda: self._authorize_disclosure(
                command.execution_id, command.principal, command.project_id
            )
        )
        return dto

    def recover(self, command: RecoverLiteratureSearchExecution) -> dict[str, Any]:
        dto, finalize = self._retry_db(
            lambda: self._cancel_or_recover(
                command.execution_id,
                command.actor_id,
                command.deployment_id,
                command.request_id,
                True,
                command.project_id,
                command.principal,
            )
        )
        if finalize:
            self._retry_db(
                lambda: self._finalize_recovery(
                    command.execution_id,
                    command.actor_id,
                    command.principal,
                    command.project_id,
                )
            )
        self._retry_db(
            lambda: self._authorize_disclosure(
                command.execution_id, command.principal, command.project_id
            )
        )
        return dto

    def _authorize_disclosure(
        self, execution_id: UUID, principal: VerifiedPrincipal | None, project_id: UUID | None
    ) -> None:
        if principal is None and self._allow_unverified_principal:
            return
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            if project_id is None:
                # Legacy scope discovery is not an authorization decision.
                discovered = repo.get(execution_id)
                project_id = discovered.project_id if discovered is not None else None
            if project_id is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._lock_project_command(uow, project_id)
            execution = repo.get_for_update(execution_id)
            if execution is None or execution.project_id != project_id:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._authorize(uow, principal, project_id, locks_acquired=True)
            uow.commit()

    def get(
        self, principal: VerifiedPrincipal | None, project_id: UUID, execution_id: UUID
    ) -> dict[str, Any]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project_id, require_writer=False)
            execution = uow.literature_search_execution.get(execution_id)
            if execution is None or execution.project_id != project_id:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            result = self._execution_read(execution)
            uow.commit()
            return result

    def list(
        self,
        principal: VerifiedPrincipal | None,
        project_id: UUID,
        limit: int = 50,
        after: UUID | None = None,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "limit must be between 1 and 100")
        with self._uow_factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project_id, require_writer=False)
            rows = uow.literature_search_execution.list_executions(project_id, limit, after)
            result = [self._execution_read(row) for row in rows]
            uow.commit()
            return result

    def get_provenance(
        self, principal: VerifiedPrincipal | None, project_id: UUID, execution_id: UUID
    ) -> dict[str, Any]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project_id, require_writer=False)
            execution = uow.literature_search_execution.get(execution_id)
            if execution is None or execution.project_id != project_id:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            data = uow.literature_search_execution.provenance(execution_id)
            result = self._provenance_read(data)
            uow.commit()
            return result

    def _cancel_or_recover(
        self,
        execution_id: UUID,
        actor_id: UUID,
        deployment_id: str,
        request_id: UUID,
        recovery: bool,
        project_id: UUID | None = None,
        principal: VerifiedPrincipal | None = None,
    ) -> tuple[dict[str, Any], bool]:
        self._validate_principal_scope(principal, actor_id, deployment_id)
        name = (
            "RECOVER_LITERATURE_SEARCH_EXECUTION"
            if recovery
            else "CANCEL_LITERATURE_SEARCH_EXECUTION"
        )
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            if project_id is not None:
                key = self._key(deployment_id, actor_id, project_id, name, request_id)
                self._lock_project_command(uow, project_id, key)
                execution = repo.get(execution_id)
            else:
                # Scope discovery is non-authoritative; all decisions use the locked reread.
                execution = repo.get(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id is not None and project_id != execution.project_id:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            key = self._key(deployment_id, actor_id, execution.project_id, name, request_id)
            if project_id is None:
                self._lock_project_command(uow, execution.project_id, key)
            execution = repo.get_for_update(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._validate_plan_binding(repo, execution)
            self._authorize(uow, principal, execution.project_id, locks_acquired=True)
            prior = repo.receipt(key)
            if prior is not None:
                command_payload = {
                    "project_id": str(execution.project_id),
                    "execution_id": str(execution_id),
                }
                if not self._receipt_matches(prior, command_payload):
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "request key payload differs"
                    )
                uow.commit()
                return prior["dto"], False
            if not recovery and execution.status in {
                ExecutionStatus.PLANNED,
                ExecutionStatus.RUNNING,
            }:
                if execution.cancellation_requested:
                    dto = self._dto(execution, name, repo.database_now())
                    repo.save_receipt(
                        key,
                        {
                            "payload": {
                                "project_id": str(execution.project_id),
                                "execution_id": str(execution_id),
                            },
                            "dto": dto,
                        },
                    )
                    uow.commit()
                    return dto, False
                execution.request_cancellation()
                expected_version = execution.row_version - 1
                repo.save(execution, expected_version)
                repo.append_event(execution, "CANCEL_REQUESTED", actor_id)
                dto = self._dto(execution, name, repo.database_now())
                repo.save_receipt(
                    key,
                    {
                        "payload": {
                            "project_id": str(execution.project_id),
                            "execution_id": str(execution_id),
                        },
                        "dto": dto,
                    },
                )
                uow.commit()
                return dto, True
            if not recovery:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "terminal execution cannot be cancelled"
                )
            finalize = False
            if (
                recovery
                and execution.status is ExecutionStatus.PLANNED
                and execution.cancellation_requested
            ):
                execution.cancel(repo.database_now())
                repo.save(execution, execution.row_version - 1)
                repo.append_event(execution, "FINISHED", actor_id)
            elif recovery and execution.status is ExecutionStatus.RUNNING:
                finalize = True
                attempts = repo.attempts(execution_id)
                reserved = [row for row in attempts if row.get("status") == "RESERVED"]
                if reserved:
                    attempt = reserved[0]
                    recovery_after = attempt.get("recovery_after")
                    if (
                        not isinstance(recovery_after, datetime)
                        or repo.database_now() < recovery_after
                    ):
                        raise ResearchBaseError(
                            ErrorCode.CONCURRENT_MODIFICATION,
                            "provider attempt remains within its recovery deadline",
                        )
                    repo.seal(
                        UUID(str(attempt["id"])),
                        {
                            "status": AttemptStatus.UNKNOWN.value,
                            "delivery_certainty": DeliveryCertainty.MAY_HAVE_BEEN_SENT.value,
                            "failure_code": "RECOVERY_OUTCOME_UNKNOWN",
                            "result_count": 0,
                            "warning_codes": [],
                            "invoked_at": attempt.get("invoked_at"),
                            "returned_at": None,
                            "query_record_id": attempt.get("query_record_id"),
                        },
                    )
                    expected_version = execution.row_version
                    execution.row_version += 1
                    repo.save(execution, expected_version)
                    repo.append_event(
                        execution,
                        "OUTCOME_RECORDED",
                        actor_id,
                        UUID(str(attempt["id"])),
                    )
            dto = self._dto(execution, name, repo.database_now())
            repo.save_receipt(
                key,
                {
                    "payload": {
                        "project_id": str(execution.project_id),
                        "execution_id": str(execution_id),
                    },
                    "dto": dto,
                },
            )
            uow.commit()
            return dto, finalize

    def _finalize_cancel(
        self,
        execution_id: UUID,
        actor_id: UUID,
        principal: VerifiedPrincipal | None = None,
        project_id: UUID | None = None,
    ) -> None:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            if project_id is not None:
                self._lock_project_command(uow, project_id)
                execution = repo.get(execution_id)
            else:
                execution = repo.get(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if execution.project_id != project_id and project_id is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id is None:
                self._lock_project_command(uow, execution.project_id)
            execution = repo.get_for_update(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._validate_plan_binding(repo, execution)
            self._authorize(uow, principal, execution.project_id, locks_acquired=True)
            if (
                execution.status is ExecutionStatus.PLANNED
                and execution.cancellation_requested
                and not repo.attempts(execution_id)
            ):
                execution.cancel(repo.database_now())
                repo.save(execution, execution.row_version - 1)
                repo.append_event(execution, "FINISHED", actor_id)
            elif execution.status is ExecutionStatus.RUNNING and execution.cancellation_requested:
                attempts = repo.attempts(execution_id)
                if not any(row.get("status") == AttemptStatus.RESERVED.value for row in attempts):
                    unknown = next(
                        (
                            row
                            for row in reversed(attempts)
                            if row.get("status") == AttemptStatus.UNKNOWN.value
                        ),
                        None,
                    )
                    terminal_status = (
                        ExecutionStatus.UNKNOWN
                        if unknown is not None
                        else (ExecutionStatus.CANCELLED)
                    )
                    terminal_reason = (
                        str(unknown.get("failure_code", "PROVIDER_OUTCOME_UNKNOWN"))
                        if unknown is not None
                        else "CANCELLED"
                    )
                    execution.finish(terminal_status, repo.database_now(), terminal_reason)
                    repo.save(execution, execution.row_version - 1)
                    repo.append_event(execution, "FINISHED", actor_id)
            uow.commit()

    def _finalize_recovery(
        self,
        execution_id: UUID,
        actor_id: UUID,
        principal: VerifiedPrincipal | None = None,
        project_id: UUID | None = None,
    ) -> None:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            if project_id is not None:
                self._lock_project_command(uow, project_id)
                execution = repo.get(execution_id)
            else:
                execution = repo.get(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if execution.project_id != project_id and project_id is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id is None:
                self._lock_project_command(uow, execution.project_id)
            execution = repo.get_for_update(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._validate_plan_binding(repo, execution)
            self._authorize(uow, principal, execution.project_id, locks_acquired=True)
            if execution.status in {
                ExecutionStatus.SUCCEEDED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.UNKNOWN,
            }:
                uow.commit()
                return
            attempts = repo.attempts(execution_id)
            if execution.status is ExecutionStatus.PLANNED:
                if execution.cancellation_requested and not attempts:
                    execution.cancel(repo.database_now())
                    repo.save(execution, execution.row_version - 1)
                    repo.append_event(execution, "FINISHED", actor_id)
                uow.commit()
                return
            if any(row.get("status") == AttemptStatus.RESERVED.value for row in attempts):
                uow.commit()
                return
            unknown = next(
                (row for row in attempts if row.get("status") == AttemptStatus.UNKNOWN.value), None
            )
            permanent_failure = next(
                (
                    row
                    for row in attempts
                    if row.get("status") == AttemptStatus.PERMANENT_FAILURE.value
                ),
                None,
            )
            if unknown is not None:
                status = ExecutionStatus.UNKNOWN
                failure_code = str(unknown["failure_code"])
            elif execution.cancellation_requested:
                status = ExecutionStatus.CANCELLED
                failure_code = "CANCELLED"
            elif permanent_failure is not None:
                status = ExecutionStatus.FAILED
                failure_code = str(permanent_failure["failure_code"])
            else:
                queries = execution.execution_context["queries"]
                successful_queries = {
                    int(row["query_index"])
                    for row in attempts
                    if row.get("status") == AttemptStatus.SUCCEEDED.value
                }
                status = (
                    ExecutionStatus.SUCCEEDED
                    if len(successful_queries) == len(queries)
                    else ExecutionStatus.FAILED
                )
                failure_code = (
                    None if status is ExecutionStatus.SUCCEEDED else "RECOVERY_INTERRUPTED"
                )
            execution.finish(status, repo.database_now(), failure_code)
            repo.save(execution, execution.row_version - 1)
            repo.append_event(execution, "FINISHED", actor_id)
            uow.commit()

    def _drive(
        self,
        execution_id: UUID,
        actor_id: UUID,
        principal: VerifiedPrincipal | None = None,
        reserved: tuple[UUID, int] | None = None,
        project_id: UUID | None = None,
    ) -> None:
        prepared = self._retry_db(
            lambda: self._prepare_attempt_tx(
                execution_id, actor_id, principal, reserved, project_id
            )
        )
        if prepared is None:
            return
        (
            execution,
            context,
            query_count,
            attempt_id,
            query_index,
            plan_hash,
            plan_material,
            deadline,
            monotonic_deadline,
        ) = prepared
        query_payload = context["queries"][query_index]
        remaining_timeout = max(0.0, monotonic_deadline - self._monotonic())
        invoked_at: datetime | None = None
        if remaining_timeout <= 0:
            response = SearchResponse(
                context["provider_id"],
                context["provider_version"],
                query_payload["query_text"],
                None,
                DeliveryCertainty.NOT_SENT,
                failure_code="PROVIDER_TIMEOUT",
            )
        else:
            invoked_at = self._clock()
            try:
                provider = self._provider_for(context["provider_id"], context["provider_version"])
                if provider is None:
                    raise ProviderError(
                        ProviderFailureKind.PERMANENT,
                        "PROVIDER_PERMANENT",
                        delivery_certainty=DeliveryCertainty.NOT_SENT,
                    )
                disconnected = _http_disconnect.get()
                durable_cancel = self._cancellation_event(execution_id)
                response = provider.search(
                    SearchRequest(
                        execution_id,
                        attempt_id,
                        attempt_id,
                        execution.plan_version_id,
                        plan_hash,
                        plan_material,
                        query_index,
                        query_payload["query_text"],
                        query_payload["perspective"],
                        query_payload["query_type"],
                        context["provider_id"],
                        context["provider_version"],
                        context["max_results"],
                    ),
                    SearchCallContext(
                        execution_id,
                        deadline,
                        remaining_timeout,
                        lambda: durable_cancel.is_set()
                        or (disconnected is not None and disconnected.is_set()),
                    ),
                )
            except ProviderError as exc:
                if (
                    exc.kind is ProviderFailureKind.UNCERTAIN
                    or exc.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT
                ):
                    response = SearchResponse.uncertain(
                        provider_id=context["provider_id"],
                        provider_version=context["provider_version"],
                        normalized_query=query_payload["query_text"],
                        provider_request_id=exc.provider_request_id,
                    )
                elif exc.kind is ProviderFailureKind.PERMANENT:
                    failure_code = (
                        "PROVIDER_MALFORMED"
                        if exc.code == "PROVIDER_MALFORMED"
                        else "PROVIDER_PERMANENT"
                    )
                    response = SearchResponse(
                        context["provider_id"],
                        context["provider_version"],
                        query_payload["query_text"],
                        exc.provider_request_id,
                        exc.delivery_certainty,
                        warning_codes=exc.warning_codes,
                        failure_code=failure_code,
                    )
                elif exc.kind is ProviderFailureKind.CANCELLED:
                    response = SearchResponse(
                        context["provider_id"],
                        context["provider_version"],
                        query_payload["query_text"],
                        exc.provider_request_id,
                        exc.delivery_certainty,
                        warning_codes=exc.warning_codes,
                        failure_code="PROVIDER_CANCELLED",
                    )
                else:
                    code = (
                        exc.code
                        if exc.code
                        in {
                            "PROVIDER_TIMEOUT",
                            "PROVIDER_RATE_LIMIT",
                            "PROVIDER_TRANSIENT",
                        }
                        else "PROVIDER_TRANSIENT"
                    )
                    response = SearchResponse(
                        context["provider_id"],
                        context["provider_version"],
                        query_payload["query_text"],
                        exc.provider_request_id,
                        exc.delivery_certainty,
                        warning_codes=exc.warning_codes,
                        retry_after_seconds=exc.retry_after_seconds,
                        failure_code=code,
                    )
            except Exception:
                response = SearchResponse.uncertain(
                    provider_id=context["provider_id"],
                    provider_version=context["provider_version"],
                    normalized_query=query_payload["query_text"],
                    provider_request_id=None,
                )
        if not isinstance(response, SearchResponse):
            response = SearchResponse(
                context["provider_id"],
                context["provider_version"],
                context["queries"][query_index]["query_text"],
                None,
                DeliveryCertainty.RESPONSE_RECEIVED,
                failure_code="PROVIDER_MALFORMED",
            )
        returned_at = self._clock()
        outcome = self._retry_db(
            lambda: self._persist_outcome(
                execution_id,
                attempt_id,
                actor_id,
                query_index,
                query_count,
                context,
                response,
                principal,
                invoked_at,
                returned_at,
                execution.project_id,
            )
        )
        terminal_status, retry_provider, continue_query, retry_delay = outcome
        if terminal_status is not None:
            self._retry_db(
                lambda: self._finalize_execution(
                    execution_id,
                    actor_id,
                    terminal_status,
                    principal,
                    execution.project_id,
                )
            )
        if retry_provider:
            self._sleep(retry_delay)
        if retry_provider or continue_query:
            self._drive(execution_id, actor_id, principal, project_id=execution.project_id)

    def _prepare_attempt_tx(
        self,
        execution_id: UUID,
        actor_id: UUID,
        principal: VerifiedPrincipal | None,
        reserved: tuple[UUID, int] | None,
        project_id: UUID | None = None,
    ) -> (
        tuple[
            LiteratureSearchExecution,
            dict[str, Any],
            int,
            UUID,
            int,
            str,
            object,
            datetime,
            float,
        ]
        | None
    ):
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            if project_id is not None:
                self._lock_project_command(uow, project_id)
                execution = repo.get(execution_id)
            else:
                execution = repo.get(execution_id)
            if execution is None or execution.status is not ExecutionStatus.RUNNING:
                uow.commit()
                return None
            if execution.project_id != project_id and project_id is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id is None:
                self._lock_project_command(uow, execution.project_id)
            execution = repo.get_for_update(execution_id)
            if execution is None or execution.status is not ExecutionStatus.RUNNING:
                uow.commit()
                return None
            self._validate_plan_binding(repo, execution)
            self._authorize(uow, principal, execution.project_id, locks_acquired=True)
            context = execution.execution_context
            query_count = len(context["queries"])
            plan_invocation = getattr(repo, "plan_invocation", None)
            if plan_invocation is None:
                plan_hash, plan_material = "unit-test-unverified", {}
            else:
                plan_hash, plan_material = plan_invocation(
                    execution.project_id, execution.plan_version_id
                )
            if reserved is None:
                attempts = repo.attempts(execution_id)
                if execution.cancellation_requested or any(
                    row.get("status")
                    in {
                        AttemptStatus.UNKNOWN.value,
                        AttemptStatus.PERMANENT_FAILURE.value,
                        AttemptStatus.CANCELLED.value,
                    }
                    for row in attempts
                ):
                    uow.commit()
                    return None
                query_index = len(
                    [a for a in attempts if a.get("status") == AttemptStatus.SUCCEEDED.value]
                )
                if query_index < query_count and execution.started_at is not None:
                    budget_remaining = (
                        execution.started_at
                        + timedelta(seconds=int(context["execution_budget_seconds"]))
                        - repo.database_now()
                    ).total_seconds()
                    if budget_remaining < 1.0:
                        expected_version = execution.row_version
                        execution.finish(
                            ExecutionStatus.FAILED,
                            repo.database_now(),
                            "PROVIDER_RETRY_EXHAUSTED",
                        )
                        repo.save(execution, expected_version)
                        repo.append_event(execution, "FINISHED", actor_id)
                        uow.commit()
                        return None
                if attempts:
                    expected_version = execution.row_version
                    execution.row_version += 1
                    repo.save(execution, expected_version)
                attempt_id = repo.reserve(execution_id, query_index, actor_id)
            else:
                attempt_id, query_index = reserved
            reservation = repo.reservation(attempt_id)
            if reservation is None or reservation.get("status") != AttemptStatus.RESERVED.value:
                uow.commit()
                return None
            deadline_at = reservation.get("deadline_at")
            if not isinstance(deadline_at, datetime):
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "reserved provider attempt has no deadline",
                )
            deadline = min(
                deadline_at,
                execution.started_at + timedelta(seconds=int(context["execution_budget_seconds"]))
                if execution.started_at is not None
                else deadline_at,
            )
            # Anchor before DB sampling, commit and closure; never add their latency back.
            sampled_at = self._monotonic()
            remaining = (deadline - repo.database_now()).total_seconds()
            monotonic_deadline = sampled_at + max(0.0, remaining)
            uow.commit()
            return (
                execution,
                context,
                query_count,
                attempt_id,
                query_index,
                plan_hash,
                plan_material,
                deadline,
                monotonic_deadline,
            )

    def _persist_outcome(
        self,
        execution_id: UUID,
        attempt_id: UUID,
        actor_id: UUID,
        query_index: int,
        query_count: int,
        context: dict[str, Any],
        response: SearchResponse,
        principal: VerifiedPrincipal | None = None,
        invoked_at: datetime | None = None,
        returned_at: datetime | None = None,
        project_id: UUID | None = None,
    ) -> tuple[ExecutionStatus | None, bool, bool, float]:
        terminal_status: ExecutionStatus | None = None
        retry_provider = False
        continue_query = False
        retry_delay = 0.0
        expected_query = context["queries"][query_index]["query_text"]
        malformed = response.delivery_certainty is not DeliveryCertainty.MAY_HAVE_BEEN_SENT and (
            response.provider_id != context["provider_id"]
            or response.provider_version != context["provider_version"]
            or response.normalized_query != expected_query
            or len(response.hits) > context["max_results"]
            or (response.failure_code is not None and bool(response.hits))
            or (
                response.delivery_certainty is DeliveryCertainty.NOT_SENT
                and (bool(response.hits) or response.failure_code is None)
            )
        )
        if malformed:
            response = SearchResponse(
                context["provider_id"],
                context["provider_version"],
                expected_query,
                response.provider_request_id,
                DeliveryCertainty.RESPONSE_RECEIVED,
                failure_code="PROVIDER_MALFORMED",
            )
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            if project_id is not None:
                self._lock_project_command(uow, project_id)
                execution = repo.get(execution_id)
            else:
                execution = repo.get(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if execution.project_id != project_id and project_id is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id is None:
                self._lock_project_command(uow, execution.project_id)
            execution = repo.get_for_update(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._validate_plan_binding(repo, execution)
            self._authorize(uow, principal, execution.project_id, locks_acquired=True)
            if execution.status is not ExecutionStatus.RUNNING:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "execution is not RUNNING"
                )
            if (
                response.failure_code == "PROVIDER_CANCELLED"
                and not execution.cancellation_requested
            ):
                # CANCELLED requires durable C1 intent. A provider claiming cancellation
                # without that intent is an invalid adapter outcome, not a system cancel.
                response = SearchResponse(
                    context["provider_id"],
                    context["provider_version"],
                    expected_query,
                    response.provider_request_id,
                    response.delivery_certainty,
                    warning_codes=response.warning_codes,
                    failure_code="PROVIDER_MALFORMED",
                )
            prior_attempt = next(
                (
                    row
                    for row in repo.attempts(execution_id)
                    if str(row.get("id")) == str(attempt_id)
                ),
                None,
            )
            if (
                prior_attempt is not None
                and prior_attempt.get("status") != AttemptStatus.RESERVED.value
            ):
                if not self._matches_sealed_outcome(
                    repo,
                    execution_id,
                    attempt_id,
                    query_index,
                    context,
                    response,
                    invoked_at,
                    returned_at,
                ):
                    raise ResearchBaseError(
                        ErrorCode.IMMUTABLE_RECORD,
                        "provider attempt is sealed with a different outcome",
                    )
                result = self._sealed_outcome_transition(
                    execution, prior_attempt, context, query_index, query_count, repo
                )
                uow.commit()
                return result
            query = None
            if invoked_at is not None:
                ordinal = repo.next_query_ordinal(execution_id)
                query = SearchQueryRecord(
                    uuid4(),
                    execution_id,
                    attempt_id,
                    ordinal,
                    expected_query,
                    context["provider_id"],
                    context["provider_version"],
                    invoked_at,
                    context["queries"][query_index]["perspective"],
                )
                repo.append_query(query)
            if response.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT:
                repo.seal(
                    attempt_id,
                    {
                        "status": AttemptStatus.UNKNOWN.value,
                        "delivery_certainty": response.delivery_certainty.value,
                        "failure_code": "PROVIDER_OUTCOME_UNKNOWN",
                        "result_count": 0,
                        "invoked_at": invoked_at,
                        "returned_at": returned_at,
                        "provider_request_id": response.provider_request_id,
                        "warning_codes": list(response.warning_codes),
                        "retry_after_seconds": response.retry_after_seconds,
                        "query_record_id": query.id if query is not None else None,
                    },
                )
                terminal_status = ExecutionStatus.UNKNOWN
            elif (
                response.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED
                and response.failure_code is None
            ):
                assert query is not None
                assert response.retrieved_at is not None
                repo.append_results(query.id, response, response.retrieved_at)
                repo.seal(
                    attempt_id,
                    {
                        "status": AttemptStatus.SUCCEEDED.value,
                        "retrieved_at": response.retrieved_at,
                        "delivery_certainty": response.delivery_certainty.value,
                        "query_record_id": query.id,
                        "provider_request_id": response.provider_request_id,
                        "warning_codes": list(response.warning_codes),
                        "retry_after_seconds": response.retry_after_seconds,
                        "result_count": len(response.hits),
                        "failure_code": None,
                        "invoked_at": invoked_at,
                        "returned_at": returned_at,
                    },
                )
                if execution.cancellation_requested:
                    terminal_status = ExecutionStatus.CANCELLED
                elif query_index + 1 >= query_count:
                    terminal_status = ExecutionStatus.SUCCEEDED
                else:
                    continue_query = True
            elif response.failure_code in {"PROVIDER_PERMANENT", "PROVIDER_MALFORMED"}:
                repo.seal(
                    attempt_id,
                    {
                        "status": AttemptStatus.PERMANENT_FAILURE.value,
                        "delivery_certainty": response.delivery_certainty.value,
                        "provider_request_id": response.provider_request_id,
                        "warning_codes": list(response.warning_codes),
                        "retry_after_seconds": response.retry_after_seconds,
                        "result_count": 0,
                        "failure_code": response.failure_code,
                        "invoked_at": invoked_at,
                        "returned_at": returned_at,
                        "query_record_id": query.id if query is not None else None,
                    },
                )
                terminal_status = (
                    ExecutionStatus.CANCELLED
                    if execution.cancellation_requested
                    else ExecutionStatus.FAILED
                )
            elif response.failure_code == "PROVIDER_CANCELLED":
                repo.seal(
                    attempt_id,
                    {
                        "status": AttemptStatus.CANCELLED.value,
                        "delivery_certainty": response.delivery_certainty.value,
                        "provider_request_id": response.provider_request_id,
                        "warning_codes": list(response.warning_codes),
                        "retry_after_seconds": None,
                        "result_count": 0,
                        "failure_code": "CANCELLED",
                        "invoked_at": invoked_at,
                        "returned_at": returned_at,
                        "query_record_id": query.id if query is not None else None,
                    },
                )
                terminal_status = ExecutionStatus.CANCELLED
            else:
                repo.seal(
                    attempt_id,
                    {
                        "status": AttemptStatus.RETRYABLE_FAILURE.value,
                        "delivery_certainty": response.delivery_certainty.value,
                        "provider_request_id": response.provider_request_id,
                        "warning_codes": list(response.warning_codes),
                        "retry_after_seconds": response.retry_after_seconds,
                        "result_count": 0,
                        "failure_code": response.failure_code or "PROVIDER_TRANSIENT",
                        "invoked_at": invoked_at,
                        "returned_at": returned_at,
                        "query_record_id": query.id if query is not None else None,
                    },
                )
                attempt_number = sum(
                    1
                    for row in repo.attempts(execution_id)
                    if row.get("query_index") == query_index
                )
                retry_provider = (
                    response.failure_code
                    in {
                        None,
                        "PROVIDER_TRANSIENT",
                        "PROVIDER_TIMEOUT",
                        "PROVIDER_RATE_LIMIT",
                    }
                    and attempt_number < context["max_provider_attempts"]
                )
                if not retry_provider:
                    terminal_status = ExecutionStatus.FAILED
                else:
                    if response.retry_after_seconds is not None:
                        retry_delay = float(response.retry_after_seconds)
                    else:
                        cap = min(8.0, float(2 ** max(0, attempt_number - 1)))
                        retry_delay = self._random_uniform(0.0, cap)
                    started = execution.started_at or repo.database_now()
                    remaining = (
                        started
                        + timedelta(seconds=context["execution_budget_seconds"])
                        - repo.database_now()
                    ).total_seconds()
                    if retry_delay + context["timeout_seconds"] > remaining:
                        retry_provider = False
                        terminal_status = ExecutionStatus.FAILED
                        retry_delay = 0.0
            if (
                execution.cancellation_requested
                and response.delivery_certainty is not DeliveryCertainty.MAY_HAVE_BEEN_SENT
            ):
                retry_provider = False
                terminal_status = ExecutionStatus.CANCELLED
                retry_delay = 0.0
            expected_version = execution.row_version
            execution.row_version += 1
            repo.save(execution, expected_version)
            repo.append_event(execution, "OUTCOME_RECORDED", actor_id, attempt_id)
            uow.commit()
        return terminal_status, retry_provider, continue_query, retry_delay

    def _matches_sealed_outcome(
        self,
        repo: ExecutionRepository,
        execution_id: UUID,
        attempt_id: UUID,
        query_index: int,
        context: dict[str, Any],
        response: SearchResponse,
        invoked_at: datetime | None,
        returned_at: datetime | None,
    ) -> bool:
        data = repo.provenance(execution_id)
        attempt = next(
            (
                row
                for row in data["attempts"]
                if str(self._record_value(row, "id")) == str(attempt_id)
            ),
            None,
        )
        if attempt is None:
            return False
        certainty = response.delivery_certainty.value
        if certainty == DeliveryCertainty.MAY_HAVE_BEEN_SENT.value:
            expected_status, expected_failure = (
                AttemptStatus.UNKNOWN.value,
                "PROVIDER_OUTCOME_UNKNOWN",
            )
            expected_count = 0
        elif (
            response.failure_code is None and certainty == DeliveryCertainty.RESPONSE_RECEIVED.value
        ):
            expected_status, expected_failure = AttemptStatus.SUCCEEDED.value, None
            expected_count = len(response.hits)
        elif response.failure_code in {"PROVIDER_PERMANENT", "PROVIDER_MALFORMED"}:
            expected_status, expected_failure = (
                AttemptStatus.PERMANENT_FAILURE.value,
                response.failure_code,
            )
            expected_count = 0
        elif response.failure_code == "PROVIDER_CANCELLED":
            expected_status, expected_failure = AttemptStatus.CANCELLED.value, "CANCELLED"
            expected_count = 0
        else:
            expected_status = AttemptStatus.RETRYABLE_FAILURE.value
            expected_failure = response.failure_code or "PROVIDER_TRANSIENT"
            expected_count = 0
        attempt_values = {
            "execution_id": execution_id,
            "query_index": query_index,
            "status": expected_status,
            "failure_code": expected_failure,
            "delivery_certainty": certainty,
            "provider_request_id": response.provider_request_id,
            "retry_after_seconds": response.retry_after_seconds,
            "warning_codes": list(response.warning_codes),
            "result_count": expected_count,
            "retrieved_at": response.retrieved_at,
            "invoked_at": invoked_at,
            "returned_at": returned_at,
        }
        if any(
            self._record_value(attempt, name) != expected
            for name, expected in attempt_values.items()
        ):
            return False
        query_id = self._record_value(attempt, "query_record_id")
        queries = data["queries"]
        matching_queries = (
            [row for row in queries if str(self._record_value(row, "id")) == str(query_id)]
            if query_id is not None
            else []
        )
        if invoked_at is None:
            if query_id is not None or any(
                str(self._record_value(row, "attempt_id", "provider_attempt_id")) == str(attempt_id)
                for row in queries
            ):
                return False
            query_hash = None
        else:
            if len(matching_queries) != 1:
                return False
            query = matching_queries[0]
            expected_query = context["queries"][query_index]
            if any(
                self._record_value(query, name, *aliases) != expected
                for name, aliases, expected in (
                    (
                        "literature_search_execution_id",
                        ("execution_id",),
                        execution_id,
                    ),
                    ("provider_attempt_id", ("attempt_id",), attempt_id),
                    ("query_text", (), expected_query["query_text"]),
                    ("provider_id", (), context["provider_id"]),
                    ("provider_version", (), context["provider_version"]),
                    ("executed_at", (), invoked_at),
                    ("perspective", (), expected_query["perspective"]),
                )
            ):
                return False
            query_hash = self._record_value(query, "query_hash")
            ordinal = self._record_value(query, "ordinal")
            verified_query = SearchQueryRecord(
                UUID(str(self._record_value(query, "id"))),
                execution_id,
                attempt_id,
                ordinal,
                expected_query["query_text"],
                context["provider_id"],
                context["provider_version"],
                invoked_at,
                expected_query["perspective"],
            )
            if query_hash != verified_query.query_hash:
                return False
        results = data["results"]
        matching_results = (
            sorted(
                (
                    row
                    for row in results
                    if str(self._record_value(row, "search_query_record_id")) == str(query_id)
                ),
                key=lambda row: int(self._record_value(row, "rank")),
            )
            if query_id is not None
            else []
        )
        if len(matching_results) != expected_count:
            return False
        for rank, (stored, hit) in enumerate(zip(matching_results, response.hits, strict=True)):
            stored_hit = SearchHit(
                self._record_value(stored, "external_identifier"),
                self._record_value(stored, "title"),
                self._record_value(stored, "url"),
                self._record_value(stored, "snippet"),
                self._record_value(stored, "provider_score"),
            )
            if (
                self._record_value(stored, "rank") != rank
                or stored_hit != hit
                or self._record_value(stored, "content_hash")
                != hit.result_hash(str(query_hash), rank)
                or self._record_value(stored, "retrieved_at") != response.retrieved_at
            ):
                return False
        return True

    def _sealed_outcome_transition(
        self,
        execution: LiteratureSearchExecution,
        attempt: dict[str, Any],
        context: dict[str, Any],
        query_index: int,
        query_count: int,
        repo: ExecutionRepository,
    ) -> tuple[ExecutionStatus | None, bool, bool, float]:
        status = str(attempt["status"])
        if status == AttemptStatus.UNKNOWN.value:
            return ExecutionStatus.UNKNOWN, False, False, 0.0
        if status == AttemptStatus.CANCELLED.value or execution.cancellation_requested:
            return ExecutionStatus.CANCELLED, False, False, 0.0
        if status == AttemptStatus.PERMANENT_FAILURE.value:
            return ExecutionStatus.FAILED, False, False, 0.0
        if status == AttemptStatus.SUCCEEDED.value:
            if query_index + 1 >= query_count:
                return ExecutionStatus.SUCCEEDED, False, False, 0.0
            return None, False, True, 0.0
        if status != AttemptStatus.RETRYABLE_FAILURE.value:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "sealed attempt status is invalid")
        attempt_number = int(attempt["attempt_number"])
        if attempt_number >= int(context["max_provider_attempts"]):
            return ExecutionStatus.FAILED, False, False, 0.0
        retry_after = attempt.get("retry_after_seconds")
        if retry_after is not None:
            retry_delay = float(retry_after)
        else:
            cap = min(8.0, float(2 ** max(0, attempt_number - 1)))
            retry_delay = self._random_uniform(0.0, cap)
        started = execution.started_at or repo.database_now()
        remaining = (
            started
            + timedelta(seconds=int(context["execution_budget_seconds"]))
            - repo.database_now()
        ).total_seconds()
        if retry_delay + int(context["timeout_seconds"]) > remaining:
            return ExecutionStatus.FAILED, False, False, 0.0
        return None, True, False, retry_delay

    @staticmethod
    def _record_value(record: Any, name: str, *aliases: str) -> Any:
        for candidate in (name, *aliases):
            if isinstance(record, dict) and candidate in record:
                return record[candidate]
            if hasattr(record, candidate):
                return getattr(record, candidate)
        return None

    def _finalize_execution(
        self,
        execution_id: UUID,
        actor_id: UUID,
        status: ExecutionStatus,
        principal: VerifiedPrincipal | None = None,
        project_id: UUID | None = None,
    ) -> None:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo: ExecutionRepository = uow.literature_search_execution
            execution = None
            if project_id is not None:
                self._lock_project_command(uow, project_id)
                execution = repo.get(execution_id)
            else:
                execution = repo.get(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if execution.project_id != project_id and project_id is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            if project_id is None:
                self._lock_project_command(uow, execution.project_id)
            execution = repo.get_for_update(execution_id)
            if execution is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
            self._validate_plan_binding(repo, execution)
            self._authorize(uow, principal, execution.project_id, locks_acquired=True)
            if execution.status in {
                ExecutionStatus.SUCCEEDED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.UNKNOWN,
            }:
                uow.commit()
                return
            attempts = repo.attempts(execution_id)
            if any(row.get("status") == AttemptStatus.UNKNOWN.value for row in attempts):
                status = ExecutionStatus.UNKNOWN
            elif execution.cancellation_requested:
                status = ExecutionStatus.CANCELLED
            elif any(
                row.get("status") == AttemptStatus.PERMANENT_FAILURE.value for row in attempts
            ):
                status = ExecutionStatus.FAILED
            elif status not in {ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}:
                query_count = len(execution.execution_context["queries"])
                successful_queries = {
                    int(row["query_index"])
                    for row in attempts
                    if row.get("status") == AttemptStatus.SUCCEEDED.value
                }
                if len(successful_queries) == query_count:
                    status = ExecutionStatus.SUCCEEDED
                else:
                    raise ResearchBaseError(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "durable provider outcomes do not permit finalization",
                    )
            failure_code: str | None = None
            if status is ExecutionStatus.CANCELLED:
                failure_code = "CANCELLED"
            elif status is ExecutionStatus.UNKNOWN:
                failure_code = next(
                    (
                        str(row["failure_code"])
                        for row in reversed(attempts)
                        if row.get("failure_code")
                    ),
                    "PROVIDER_OUTCOME_UNKNOWN",
                )
            elif status is ExecutionStatus.FAILED:
                last_attempt = next(
                    (row for row in reversed(attempts) if row.get("failure_code")), None
                )
                if (
                    last_attempt is not None
                    and last_attempt.get("status") == AttemptStatus.PERMANENT_FAILURE.value
                ):
                    failure_code = str(last_attempt["failure_code"])
                else:
                    failure_code = "PROVIDER_RETRY_EXHAUSTED"
            execution.finish(status, repo.database_now(), failure_code)
            repo.save(execution, execution.row_version - 1)
            repo.append_event(execution, "FINISHED", actor_id)
            uow.commit()

    def _retry_db[ResultT](self, call: Callable[[], ResultT]) -> ResultT:
        for attempt in range(3):
            try:
                return call()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                self._sleep(0.01 * (attempt + 1))
        raise AssertionError("database retry loop must return or raise")

    def _cancellation_event(self, execution_id: UUID) -> Event:
        with self._cancellation_events_lock:
            event = self._cancellation_events.get(execution_id)
            if event is None:
                event = Event()
                self._cancellation_events[execution_id] = event
            return event

    @staticmethod
    def _lock_project_command(
        uow: Any,
        project_id: UUID,
        command_key: tuple[str, UUID, UUID, str, UUID] | None = None,
    ) -> None:
        repo = uow.literature_search_plan
        repo.lock_project(project_id)
        if command_key is not None:
            repo.lock_literature_search_execution_command(*command_key)

    def _authorize(
        self,
        uow: Any,
        principal: VerifiedPrincipal | None,
        project_id: UUID,
        *,
        require_writer: bool = True,
        command_key: tuple[str, UUID, UUID, str, UUID] | None = None,
        locks_acquired: bool = False,
    ) -> None:
        if principal is None:
            if self._allow_unverified_principal:
                return
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "verified principal is required")
        repo = uow.literature_search_plan
        if not locks_acquired:
            self._lock_project_command(uow, project_id, command_key)
        project_active = getattr(repo, "project_active", None)
        if project_active is not None and not project_active(project_id):
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "project is not active")
        candidates = repo.authorize(principal, project_id)
        at = repo.at()
        verifier = self._credential_verifier
        try:
            credential_valid = bool(verifier and verifier.is_valid(principal, at))
        except Exception:
            credential_valid = False
        if credential_valid and principal.verified_at <= at:
            for facts in candidates:
                if (
                    facts["actor_type"] in {"HUMAN", "AGENT"}
                    and facts["retired_at"] is None
                    and facts["membership_status"] == "ACTIVE"
                    and facts["role"]
                    in (
                        {"OWNER", "RESEARCHER"}
                        if require_writer
                        else {"OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"}
                    )
                    and facts["effective_from"] <= at
                    and (facts["effective_until"] is None or at < facts["effective_until"])
                    and facts["binding_status"] == "ACTIVE"
                    and facts["bound_at"] <= at
                    and (facts["revoked_at"] is None or at < facts["revoked_at"])
                ):
                    return
        raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority is unavailable")

    @staticmethod
    def _validate_plan_binding(
        repo: ExecutionRepository, execution: LiteratureSearchExecution
    ) -> None:
        invocation = getattr(repo, "plan_invocation", None)
        if invocation is not None:
            invocation(execution.project_id, execution.plan_version_id)

    def _provider_for(self, capability_id: str, version: str) -> SearchCapability | None:
        resolver = getattr(self._providers, "resolve", None)
        if callable(resolver):
            capability = resolver(capability_id, version)
            return cast(SearchCapability | None, capability)
        if (
            getattr(self._providers, "capability_id", None) == capability_id
            and getattr(self._providers, "version", None) == version
        ):
            return cast(SearchCapability, self._providers)
        return None

    def _validate_principal_scope(
        self, principal: VerifiedPrincipal | None, actor_id: UUID, deployment_id: str
    ) -> None:
        if principal is None:
            if self._allow_unverified_principal:
                return
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "verified principal is required")
        if principal.actor_id != actor_id or principal.deployment_id != deployment_id:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "principal scope does not match command")

    @staticmethod
    def _key(
        deployment_id: str, actor_id: UUID, project_id: UUID, name: str, request_id: UUID
    ) -> tuple[str, UUID, UUID, str, UUID]:
        return deployment_id, actor_id, project_id, name, request_id

    @staticmethod
    def _receipt_matches(prior: dict[str, Any], payload: dict[str, Any]) -> bool:
        if "payload" in prior:
            return prior["payload"] == payload
        return prior.get("request_hash") == str(sha256_canonical_json(payload))

    @staticmethod
    def _query_payload(item: str | SearchQueryInput) -> dict[str, str | None]:
        if isinstance(item, str):
            value = SearchQueryInput(item)
        elif isinstance(item, SearchQueryInput):
            value = item
        else:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "query input is invalid")
        if not isinstance(value.query_text, str) or not isinstance(value.query_type, str):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "query input is invalid")
        if value.query_type != "TEXT" or not value.query_text.strip():
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "query must be nonblank TEXT")
        if value.perspective is not None and not isinstance(value.perspective, str):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "perspective must be text")
        perspective = (
            unicodedata.normalize("NFC", value.perspective) if value.perspective else None
        )
        if perspective is not None and not perspective.strip():
            perspective = None
        if perspective is not None and len(perspective) > 256:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "perspective is too long")
        query_text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", value.query_text)).strip()
        if not query_text or len(query_text) > 4096:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "query_text must be 1 to 4096 characters"
            )
        return {
            "query_type": value.query_type,
            "query_text": query_text,
            "perspective": perspective or None,
        }

    @staticmethod
    def _execution_read(execution: LiteratureSearchExecution) -> dict[str, Any]:
        return {
            "execution_id": str(execution.id),
            "project_id": str(execution.project_id),
            "search_plan_version_id": str(execution.plan_version_id),
            "status": execution.status.value,
            "requested_by": str(execution.requested_by),
            "executed_by": str(execution.executed_by) if execution.executed_by else None,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
            "row_version": execution.row_version,
            "failure_code": execution.failure_code,
        }

    @classmethod
    def _provenance_read(cls, data: dict[str, Any]) -> dict[str, Any]:
        execution = data["execution"]
        plan = data["plan"]
        return {
            "plan": {
                "plan_version_id": str(plan["plan_version_id"]),
                "content_hash": plan["content_hash"],
                "material": plan["material"],
            },
            "execution": cls._execution_read(execution),
            "attempts": [cls._attempt_read(row) for row in data["attempts"]],
            "queries": [cls._row_dict(row) for row in data["queries"]],
            "results": [cls._row_dict(row) for row in data["results"]],
            "events": [cls._row_dict(row) for row in data["events"]],
            "receipts": [cls._row_dict(row) for row in data["receipts"]],
        }

    @classmethod
    def _attempt_read(cls, row: Any) -> dict[str, Any]:
        # Frozen pack §15: ordered attempt times include the provider observation.
        # Keep this projection explicit so future persistence columns cannot leak.
        fields = (
            "id",
            "execution_id",
            "query_index",
            "attempt_number",
            "provider_request_key",
            "status",
            "failure_code",
            "reserved_at",
            "deadline_at",
            "recovery_after",
            "invoked_at",
            "returned_at",
            "retrieved_at",
            "completed_at",
            "query_record_id",
            "delivery_certainty",
            "provider_request_id",
            "retry_after_seconds",
            "warning_codes",
            "result_count",
            "row_version",
            "created_by",
        )
        values = cls._row_dict(row)
        return {name: values[name] for name in fields if name in values}

    @staticmethod
    def _row_dict(row: Any) -> dict[str, Any]:
        if isinstance(row, dict):
            return {
                key: str(value) if isinstance(value, UUID) else value for key, value in row.items()
            }
        fields = getattr(row, "__table__", None)
        if fields is not None:
            return {
                column.name: (
                    str(value) if isinstance((value := getattr(row, column.name)), UUID) else value
                )
                for column in fields.columns
            }
        slots = getattr(type(row), "__slots__", ())
        return {
            name: str(value) if isinstance((value := getattr(row, name)), UUID) else value
            for name in slots
        }

    @staticmethod
    def _dto(
        execution: LiteratureSearchExecution, command_name: str, accepted_at: datetime
    ) -> dict[str, Any]:
        return {
            "execution_id": str(execution.id),
            "command_name": command_name,
            "accepted_at": accepted_at.isoformat(),
            "accepted_row_version": execution.row_version,
        }
