"""Provider-neutral literature-search boundary and deterministic fake."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    SearchResponse,
)


class ProviderFailureKind(StrEnum):
    RETRYABLE = "RETRYABLE"
    PERMANENT = "PERMANENT"
    UNCERTAIN = "UNCERTAIN"
    CANCELLED = "CANCELLED"


class ProviderError(Exception):
    """Normalized adapter failure; secrets/details never cross this boundary."""

    def __init__(
        self,
        kind: ProviderFailureKind,
        code: str,
        *,
        delivery_certainty: DeliveryCertainty | None = None,
        provider_request_id: str | None = None,
        retry_after_seconds: int | None = None,
        warning_codes: tuple[str, ...] = (),
    ) -> None:
        self.kind = kind
        self.code = code
        self.delivery_certainty = delivery_certainty or (
            DeliveryCertainty.MAY_HAVE_BEEN_SENT
            if kind is ProviderFailureKind.UNCERTAIN
            else DeliveryCertainty.NOT_SENT
        )
        self.provider_request_id = provider_request_id
        self.retry_after_seconds = retry_after_seconds
        self.warning_codes = warning_codes
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SearchRequest:
    execution_id: UUID
    attempt_id: UUID
    provider_request_key: UUID
    plan_version_id: UUID
    plan_content_hash: str
    plan_material: object
    query_index: int
    query_text: str
    perspective: str | None
    query_type: str
    provider_id: str
    provider_version: str
    max_results: int


@dataclass(frozen=True, slots=True)
class SearchCallContext:
    correlation_id: UUID
    deadline: datetime
    remaining_timeout_seconds: float
    cancellation_requested: Callable[[], bool]


class SearchCapability(Protocol):
    """Trusted, configured invocation boundary.

    Confirmed cancellations return SearchResponse with execution/attempt/request
    key echoes. Exceptions and local cancellation tokens are not confirmation.
    """

    capability_id: str
    version: str
    supported_source_scopes: frozenset[str]

    def search(self, request: SearchRequest, context: SearchCallContext) -> SearchResponse: ...


class SearchCapabilityRegistry(Protocol):
    """Resolve an explicitly configured, version-pinned provider capability."""

    def resolve(self, capability_id: str, version: str) -> SearchCapability | None: ...

    def versions(self, capability_id: str) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class StaticSearchCapabilityRegistry:
    """Small immutable registry; live adapter activation remains deployment-owned."""

    capabilities: tuple[SearchCapability, ...] = ()

    def resolve(self, capability_id: str, version: str) -> SearchCapability | None:
        return next(
            (
                capability
                for capability in self.capabilities
                if capability.capability_id == capability_id and capability.version == version
            ),
            None,
        )

    def versions(self, capability_id: str) -> tuple[str, ...]:
        return tuple(
            capability.version
            for capability in self.capabilities
            if capability.capability_id == capability_id
        )


@dataclass(slots=True)
class FakeSearchCapability:
    capability_id: str = "fake"
    version: str = "1"
    supported_source_scopes: frozenset[str] = frozenset(
        {"BIBLIOGRAPHIC", "WEB", "LOCAL_CORPUS", "MIXED"}
    )
    responses: list[SearchResponse] = field(default_factory=list)
    calls: list[SearchRequest] = field(default_factory=list)
    observer: Callable[[SearchRequest], None] | None = None

    def search(
        self, request: SearchRequest, context: SearchCallContext | None = None
    ) -> SearchResponse:
        if self.observer is not None:
            self.observer(request)
        self.calls.append(request)
        if not self.responses:
            return SearchResponse.success(
                provider_id=self.capability_id,
                provider_version=self.version,
                normalized_query=request.query_text,
                provider_request_id=str(request.provider_request_key),
                hits=(),
                retrieved_at=datetime.now(UTC),
            )
        return self.responses.pop(0)


def response_is_success(response: SearchResponse) -> bool:
    return response.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED
