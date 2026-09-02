"""Deterministic CLI error normalization for transport and Application failures."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@dataclass(frozen=True, slots=True)
class CliTransportError(Exception):
    message: str
    request_id: UUID
    details: dict[str, object] | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    @property
    def code(self) -> ErrorCode:
        return ErrorCode.VALIDATION_ERROR


CLI_EXIT_CODES: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 2,
    ErrorCode.NOT_FOUND: 3,
    ErrorCode.INVALID_STATE_TRANSITION: 4,
    ErrorCode.VERSION_NOT_FROZEN: 4,
    ErrorCode.IMMUTABLE_RECORD: 4,
    ErrorCode.CONCURRENT_MODIFICATION: 4,
    ErrorCode.DUPLICATE_CONTENT: 4,
    ErrorCode.FROZEN_REFERENCE_REQUIRED: 5,
    ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 5,
    ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 5,
}


def cli_exit_code(error: ResearchBaseError | CliTransportError) -> int:
    return CLI_EXIT_CODES[error.code]


def error_details(error: ResearchBaseError | CliTransportError) -> dict[str, object] | None:
    if isinstance(error, CliTransportError):
        return error.details
    return dict(error.details) if error.details is not None else None


def error_code(error: ResearchBaseError | CliTransportError) -> str:
    return error.code.value
