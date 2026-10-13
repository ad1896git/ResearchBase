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
    ErrorCode.AUTHENTICATION_REQUIRED: 3,
    ErrorCode.FORBIDDEN: 3,
    # Both review mappings are provisional: planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md.
    ErrorCode.REVIEW_TARGET_NOT_FROZEN: 4,
    ErrorCode.CONFLICT_OF_INTEREST: 3,
    ErrorCode.SUBJECT_BINDING_UNPROVEN: 3,
    ErrorCode.INVALID_STATE_TRANSITION: 4,
    ErrorCode.VERSION_NOT_FROZEN: 4,
    ErrorCode.IMMUTABLE_RECORD: 4,
    ErrorCode.CONCURRENT_MODIFICATION: 4,
    ErrorCode.DUPLICATE_CONTENT: 4,
    ErrorCode.FROZEN_REFERENCE_REQUIRED: 5,
    ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 5,
    ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 5,
    ErrorCode.SUBJECT_ALREADY_BOUND: 4,
    ErrorCode.OWNER_COVERAGE_GAP: 4,
    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE: 4,
    ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED: 4,
    ErrorCode.BOOTSTRAP_CLOSED: 4,
    ErrorCode.IDEMPOTENCY_CONFLICT: 4,
    ErrorCode.LEGACY_STATE_INVALID: 4,
    ErrorCode.IDENTIFIER_INVALID: 2,
    ErrorCode.SOURCE_IDENTITY_CONFLICT: 4,
    ErrorCode.IDENTIFIER_ALREADY_BOUND: 4,
    ErrorCode.IDENTIFIER_BASIS_NOT_FROZEN: 4,
    ErrorCode.SOURCE_NOT_FOUND: 3,
    ErrorCode.SHARED_SOURCE_REJECTION_REQUIRES_REVIEW: 4,
    ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND: 3,
    ErrorCode.SOURCE_MERGE_PROPOSAL_STALE: 4,
    ErrorCode.SOURCE_MERGE_APPROVAL_MISSING: 4,
    ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN: 3,
    ErrorCode.SOURCE_MERGE_REJECTED: 4,
    ErrorCode.SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED: 4,
    ErrorCode.SOURCE_MERGE_BASIS_CONFLICT: 4,
    ErrorCode.SOURCE_NOT_MERGEABLE: 4,
    ErrorCode.SOURCE_MERGE_IDENTIFIER_CONFLICT: 4,
    ErrorCode.SOURCE_VERSION_NOT_FOUND: 3,
    ErrorCode.SOURCE_VERSION_NOT_FREEZABLE: 4,
    ErrorCode.SOURCE_VERSION_ALREADY_FROZEN: 4,
    ErrorCode.SOURCE_VERSION_IMMUTABLE: 4,
    ErrorCode.INVALID_SOURCE_VERSION_LINEAGE: 4,
    ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED: 2,
    ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED: 2,
    ErrorCode.SEARCH_PLAN_QUESTION_INVALID: 2,
    ErrorCode.SEARCH_PLAN_QUESTION_SCOPE_MISMATCH: 3,
    ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE: 4,
    ErrorCode.SEARCH_PLAN_NOT_FROZEN: 4,
    ErrorCode.ADAPTER_UNAVAILABLE: 5,
    ErrorCode.ADAPTER_VERSION_MISMATCH: 4,
}


def cli_exit_code(error: ResearchBaseError | CliTransportError) -> int:
    return CLI_EXIT_CODES[error.code]


def error_details(error: ResearchBaseError | CliTransportError) -> dict[str, object] | None:
    if isinstance(error, CliTransportError):
        return error.details
    return dict(error.details) if error.details is not None else None


def error_code(error: ResearchBaseError | CliTransportError) -> str:
    return error.code.value
