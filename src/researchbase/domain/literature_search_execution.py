"""Domain values for bounded literature-search execution provenance."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from researchbase.foundation.hashing import sha256_canonical_json


class ExecutionStatus(StrEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class AttemptStatus(StrEnum):
    RESERVED = "RESERVED"
    SUCCEEDED = "SUCCEEDED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class DeliveryCertainty(StrEnum):
    NOT_SENT = "NOT_SENT"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    MAY_HAVE_BEEN_SENT = "MAY_HAVE_BEEN_SENT"


def _text(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    value = unicodedata.normalize("NFC", value).strip()
    if not value or len(value) > maximum:
        raise ValueError(f"{name} must be nonblank and at most {maximum} characters")
    return value


def _nfc_text(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized.strip() or len(normalized) > maximum:
        raise ValueError(f"{name} must be nonblank and at most {maximum} characters")
    return normalized


def _optional_nfc_text(value: str | None, name: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized.strip():
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{name} must be at most {maximum} characters")
    return normalized


def _canonical_decimal(value: Decimal) -> str:
    if value.is_zero():
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@dataclass(slots=True)
class LiteratureSearchExecution:
    id: UUID
    project_id: UUID
    plan_version_id: UUID
    requested_by: UUID
    idempotency_key: UUID
    execution_context: dict[str, Any]
    status: ExecutionStatus = ExecutionStatus.PLANNED
    executed_by: UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    row_version: int = 1
    cancellation_requested: bool = False
    failure_code: str | None = None

    @classmethod
    def create(
        cls,
        *,
        project_id: UUID,
        plan_version_id: UUID,
        requested_by: UUID,
        idempotency_key: UUID,
        execution_context: dict[str, Any],
    ) -> LiteratureSearchExecution:
        if not isinstance(project_id, UUID) or not isinstance(plan_version_id, UUID):
            raise TypeError("project and plan version IDs must be UUIDs")
        if not isinstance(requested_by, UUID):
            raise TypeError("requested_by must be a UUID")
        if not isinstance(idempotency_key, UUID):
            raise TypeError("idempotency_key must be a UUID")
        if not isinstance(execution_context, dict):
            raise TypeError("execution_context must be an object")
        return cls(
            uuid4(),
            project_id,
            plan_version_id,
            requested_by,
            idempotency_key,
            dict(execution_context),
        )

    def _require_open(self) -> None:
        if self.status in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.UNKNOWN,
        }:
            raise ValueError("terminal execution is immutable")

    def start(self, actor_id: UUID, at: datetime) -> None:
        self._require_open()
        if self.status is not ExecutionStatus.PLANNED:
            raise ValueError("execution is not PLANNED")
        if not isinstance(actor_id, UUID):
            raise TypeError("actor_id must be a UUID")
        self.status = ExecutionStatus.RUNNING
        self.executed_by = actor_id
        self.started_at = at
        self.row_version += 1

    def request_cancellation(self) -> None:
        self._require_open()
        self.cancellation_requested = True
        self.row_version += 1

    def cancel(self, at: datetime) -> None:
        self._require_open()
        if self.status not in {ExecutionStatus.PLANNED, ExecutionStatus.RUNNING}:
            raise ValueError("only an active execution can be cancelled")
        self.status = ExecutionStatus.CANCELLED
        self.failure_code = "CANCELLED"
        self.finished_at = at
        self.row_version += 1

    def finish(
        self, status: ExecutionStatus, at: datetime, failure_code: str | None = None
    ) -> None:
        self._require_open()
        if self.status is not ExecutionStatus.RUNNING:
            raise ValueError("only a RUNNING execution can be finalized")
        if status not in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.UNKNOWN,
        }:
            raise ValueError("final status must be terminal")
        self.status = status
        self.failure_code = failure_code
        self.finished_at = at
        self.row_version += 1


@dataclass(frozen=True, slots=True)
class SearchQueryRecord:
    id: UUID
    execution_id: UUID
    attempt_id: UUID
    ordinal: int
    query_text: str
    provider_id: str
    provider_version: str | None
    executed_at: datetime
    perspective: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int):
            raise ValueError("ordinal must be an integer")
        if self.ordinal < 0:
            raise ValueError("ordinal must be non-negative")
        normalized_query = re.sub(
            r"\s+", " ", unicodedata.normalize("NFC", self.query_text)
        ).strip()
        object.__setattr__(self, "query_text", _text(normalized_query, "query_text", 4096))
        object.__setattr__(self, "provider_id", _text(self.provider_id, "provider_id", 128))
        if self.provider_version is not None:
            object.__setattr__(
                self, "provider_version", _text(self.provider_version, "provider_version", 128)
            )
        if self.perspective is not None:
            object.__setattr__(
                self,
                "perspective",
                _optional_nfc_text(self.perspective, "perspective", 256),
            )

    @property
    def query_hash(self) -> str:
        return str(
            sha256_canonical_json(
                {
                    "type": "SearchQueryRecord",
                    "material_version": 1,
                    "literature_search_execution_id": str(self.execution_id),
                    "provider_id": self.provider_id,
                    "provider_version": self.provider_version,
                    "query_text": self.query_text,
                    "ordinal": self.ordinal,
                }
            )
        )


@dataclass(frozen=True, slots=True)
class SearchHit:
    external_identifier: str | None
    title: str
    url: str | None
    snippet: str | None
    provider_score: Decimal | float | int | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _nfc_text(self.title, "title", 2048))
        object.__setattr__(
            self,
            "external_identifier",
            _optional_nfc_text(self.external_identifier, "external_identifier", 1024),
        )
        object.__setattr__(self, "url", _optional_nfc_text(self.url, "url", 4096))
        if self.url is not None:
            from urllib.parse import urlsplit

            parsed = urlsplit(self.url)
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("url must be a valid http or https URL without userinfo")
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("url must be a valid http or https URL") from exc
            if port is not None and not 1 <= port <= 65535:
                raise ValueError("url must be a valid http or https URL")
        object.__setattr__(self, "snippet", _optional_nfc_text(self.snippet, "snippet", 4096))
        if self.provider_score is not None:
            try:
                score = Decimal(str(self.provider_score))
            except InvalidOperation as exc:
                raise ValueError("provider_score must be a finite decimal") from exc
            if not score.is_finite():
                raise ValueError("provider_score must be a finite decimal")
            object.__setattr__(self, "provider_score", score)

    def result_hash(self, query_hash: str, rank: int) -> str:
        if isinstance(rank, bool) or not isinstance(rank, int):
            raise ValueError("rank must be an integer")
        if rank < 0:
            raise ValueError("rank must be non-negative")
        return str(
            sha256_canonical_json(
                {
                    "type": "SearchResultRecord",
                    "material_version": 1,
                    "query_hash": query_hash,
                    "rank": rank,
                    "external_identifier": self.external_identifier,
                    "title": self.title,
                    "url": self.url,
                    "snippet": self.snippet,
                    "provider_score": (
                        _canonical_decimal(self.provider_score)
                        if isinstance(self.provider_score, Decimal)
                        else str(self.provider_score)
                        if self.provider_score is not None
                        else None
                    ),
                }
            )
        )


@dataclass(frozen=True, slots=True)
class SearchResponse:
    provider_id: str
    provider_version: str
    normalized_query: str
    provider_request_id: str | None
    delivery_certainty: DeliveryCertainty
    hits: tuple[SearchHit, ...] = field(default_factory=tuple)
    warning_codes: tuple[str, ...] = ()
    retry_after_seconds: int | None = None
    failure_code: str | None = None
    retrieved_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _text(self.provider_id, "provider_id", 128))
        object.__setattr__(
            self,
            "provider_version",
            _text(self.provider_version, "provider_version", 128),
        )
        normalized_query = re.sub(
            r"\s+", " ", unicodedata.normalize("NFC", self.normalized_query)
        ).strip()
        object.__setattr__(
            self, "normalized_query", _text(normalized_query, "normalized_query", 4096)
        )
        object.__setattr__(
            self,
            "provider_request_id",
            self._provider_request_id(),
        )
        if (
            not isinstance(self.provider_id, str)
            or not self.provider_id.strip()
            or len(self.provider_id) > 128
        ):
            raise ValueError("provider_id must be nonblank text of at most 128 characters")
        if (
            not isinstance(self.provider_version, str)
            or not self.provider_version.strip()
            or len(self.provider_version) > 128
        ):
            raise ValueError("provider_version must be nonblank text of at most 128 characters")
        if (
            not isinstance(self.normalized_query, str)
            or not self.normalized_query.strip()
            or len(self.normalized_query) > 4096
        ):
            raise ValueError("normalized_query must be nonblank text of at most 4096 characters")
        if self.provider_request_id is not None and (
            not isinstance(self.provider_request_id, str)
            or not self.provider_request_id.strip()
            or len(self.provider_request_id) > 256
        ):
            raise ValueError("provider_request_id must be nonblank text of at most 256 characters")
        if not isinstance(self.delivery_certainty, DeliveryCertainty):
            raise ValueError("delivery_certainty is invalid")
        if not isinstance(self.hits, tuple) or any(
            not isinstance(hit, SearchHit) for hit in self.hits
        ):
            raise ValueError("hits must be a tuple of SearchHit values")
        if not isinstance(self.warning_codes, tuple) or any(
            not isinstance(code, str) for code in self.warning_codes
        ):
            raise ValueError("warning_codes must be a tuple of text codes")
        allowed_warnings = {"RESULTS_TRUNCATED", "PARTIAL_COVERAGE", "RATE_LIMITED"}
        if len(self.warning_codes) != len(set(self.warning_codes)) or not set(
            self.warning_codes
        ).issubset(allowed_warnings):
            raise ValueError("provider warning code is not allowed")
        if self.retry_after_seconds is not None and (
            isinstance(self.retry_after_seconds, bool)
            or not isinstance(self.retry_after_seconds, int)
            or not 0 <= self.retry_after_seconds <= 2_147_483_647
        ):
            raise ValueError("retry_after_seconds must be between 0 and 2147483647 seconds")
        allowed_failures = {
            "PROVIDER_TIMEOUT",
            "PROVIDER_RATE_LIMIT",
            "PROVIDER_TRANSIENT",
            "PROVIDER_PERMANENT",
            "PROVIDER_CANCELLED",
            "PROVIDER_MALFORMED",
            "PROVIDER_OUTCOME_UNKNOWN",
            "RECOVERY_OUTCOME_UNKNOWN",
        }
        if self.failure_code is not None and (
            not isinstance(self.failure_code, str) or self.failure_code not in allowed_failures
        ):
            raise ValueError("provider failure code is not allowed")
        successful = (
            self.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED
            and self.failure_code is None
        )
        if successful:
            if (
                not isinstance(self.retrieved_at, datetime)
                or self.retrieved_at.tzinfo is None
                or self.retrieved_at.utcoffset() is None
            ):
                raise ValueError("successful response retrieved_at must be an aware datetime")
            object.__setattr__(self, "retrieved_at", self.retrieved_at.astimezone(UTC))
        elif self.retrieved_at is not None:
            raise ValueError("non-success response retrieved_at must be absent")
        if self.failure_code is not None and self.hits:
            raise ValueError("provider failures cannot contain result hits")
        if (
            self.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT
            and self.failure_code
            not in {None, "PROVIDER_OUTCOME_UNKNOWN", "RECOVERY_OUTCOME_UNKNOWN"}
        ):
            raise ValueError("uncertain delivery cannot carry a known failure classification")
        if (
            self.failure_code in {"PROVIDER_OUTCOME_UNKNOWN", "RECOVERY_OUTCOME_UNKNOWN"}
            and self.delivery_certainty is not DeliveryCertainty.MAY_HAVE_BEEN_SENT
        ):
            raise ValueError("uncertain outcome failure requires uncertain delivery")

    def _provider_request_id(self) -> str | None:
        if self.provider_request_id is None:
            return None
        if not isinstance(self.provider_request_id, str):
            raise TypeError("provider_request_id must be text")
        if not self.provider_request_id.strip():
            return None
        return _text(self.provider_request_id, "provider_request_id", 256)

    @classmethod
    def success(
        cls,
        *,
        provider_id: str,
        provider_version: str,
        normalized_query: str,
        provider_request_id: str | None,
        hits: tuple[SearchHit, ...] = (),
        retrieved_at: datetime,
    ) -> SearchResponse:
        return cls(
            provider_id,
            provider_version,
            normalized_query,
            provider_request_id,
            DeliveryCertainty.RESPONSE_RECEIVED,
            hits,
            retrieved_at=retrieved_at,
        )

    @classmethod
    def uncertain(
        cls,
        *,
        provider_id: str,
        provider_version: str,
        normalized_query: str,
        provider_request_id: str | None,
    ) -> SearchResponse:
        return cls(
            provider_id,
            provider_version,
            normalized_query,
            provider_request_id,
            DeliveryCertainty.MAY_HAVE_BEEN_SENT,
        )

    @classmethod
    def not_sent(
        cls,
        *,
        provider_id: str,
        provider_version: str,
        normalized_query: str,
    ) -> SearchResponse:
        return cls(
            provider_id,
            provider_version,
            normalized_query,
            None,
            DeliveryCertainty.NOT_SENT,
            failure_code="PROVIDER_TRANSIENT",
        )

    def require_success(self) -> tuple[SearchHit, ...]:
        if self.delivery_certainty is not DeliveryCertainty.RESPONSE_RECEIVED:
            raise ValueError("uncertain provider response cannot be treated as success")
        return self.hits
