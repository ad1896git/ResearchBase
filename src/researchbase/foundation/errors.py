"""Stable, transport-neutral application/domain error model."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from researchbase.foundation.canonical_json import canonical_json_bytes


class ErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    VERSION_NOT_FROZEN = "VERSION_NOT_FROZEN"
    IMMUTABLE_RECORD = "IMMUTABLE_RECORD"
    FROZEN_REFERENCE_REQUIRED = "FROZEN_REFERENCE_REQUIRED"
    PROVENANCE_CLOSURE_VIOLATION = "PROVENANCE_CLOSURE_VIOLATION"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    DUPLICATE_CONTENT = "DUPLICATE_CONTENT"
    REFERENTIAL_INTEGRITY_ERROR = "REFERENTIAL_INTEGRITY_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    SUBJECT_BINDING_UNPROVEN = "SUBJECT_BINDING_UNPROVEN"
    SUBJECT_ALREADY_BOUND = "SUBJECT_ALREADY_BOUND"
    OWNER_COVERAGE_GAP = "OWNER_COVERAGE_GAP"
    OWNER_CREDENTIAL_UNAVAILABLE = "OWNER_CREDENTIAL_UNAVAILABLE"
    ENROLLMENT_CHALLENGE_EXPIRED = "ENROLLMENT_CHALLENGE_EXPIRED"
    BOOTSTRAP_CLOSED = "BOOTSTRAP_CLOSED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    LEGACY_STATE_INVALID = "LEGACY_STATE_INVALID"
    IDENTIFIER_INVALID = "IDENTIFIER_INVALID"
    SOURCE_IDENTITY_CONFLICT = "SOURCE_IDENTITY_CONFLICT"
    IDENTIFIER_ALREADY_BOUND = "IDENTIFIER_ALREADY_BOUND"
    IDENTIFIER_BASIS_NOT_FROZEN = "IDENTIFIER_BASIS_NOT_FROZEN"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SHARED_SOURCE_REJECTION_REQUIRES_REVIEW = "SHARED_SOURCE_REJECTION_REQUIRES_REVIEW"


class ResearchBaseError(Exception):
    """Base error with stable code and bounded diagnostic JSON details.

    Details are transport diagnostics, not canonical scientific state.
    """

    _MAX_DETAILS_BYTES = 64 * 1024

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        if not isinstance(code, ErrorCode):
            raise TypeError("code must be an ErrorCode")
        if not message:
            raise ValueError("message must not be empty")
        copied_details = dict(details) if details is not None else None
        if copied_details is not None:
            serialized = canonical_json_bytes(copied_details)
            if len(serialized) > self._MAX_DETAILS_BYTES:
                raise ValueError("error details exceed the maximum size")
            self.details = MappingProxyType(copied_details)
        else:
            self.details = None
        self.code = code
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": dict(self.details) if self.details is not None else None,
        }
