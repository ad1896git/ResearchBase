"""Normalized HTTP errors and request identity middleware."""

from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


class ErrorItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorItem


_STATUS = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.AUTHENTICATION_REQUIRED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.REVIEW_TARGET_NOT_FROZEN: 409,
    ErrorCode.CONFLICT_OF_INTEREST: 403,
    ErrorCode.SUBJECT_BINDING_UNPROVEN: 403,
    ErrorCode.INVALID_STATE_TRANSITION: 409,
    ErrorCode.VERSION_NOT_FROZEN: 409,
    ErrorCode.FROZEN_REFERENCE_REQUIRED: 409,
    ErrorCode.IMMUTABLE_RECORD: 409,
    ErrorCode.CONCURRENT_MODIFICATION: 409,
    ErrorCode.DUPLICATE_CONTENT: 409,
    ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 409,
    ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 409,
    ErrorCode.SUBJECT_ALREADY_BOUND: 409,
    ErrorCode.OWNER_COVERAGE_GAP: 409,
    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE: 409,
    ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED: 409,
    ErrorCode.BOOTSTRAP_CLOSED: 409,
    ErrorCode.IDEMPOTENCY_CONFLICT: 409,
    ErrorCode.LEGACY_STATE_INVALID: 409,
    ErrorCode.IDENTIFIER_INVALID: 422,
    ErrorCode.SOURCE_IDENTITY_CONFLICT: 409,
    ErrorCode.IDENTIFIER_ALREADY_BOUND: 409,
    ErrorCode.IDENTIFIER_BASIS_NOT_FROZEN: 409,
    ErrorCode.SOURCE_NOT_FOUND: 404,
    ErrorCode.SHARED_SOURCE_REJECTION_REQUIRES_REVIEW: 409,
    ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND: 404,
    ErrorCode.SOURCE_MERGE_PROPOSAL_STALE: 409,
    ErrorCode.SOURCE_MERGE_APPROVAL_MISSING: 409,
    ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN: 403,
    ErrorCode.SOURCE_MERGE_REJECTED: 409,
    ErrorCode.SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED: 409,
    ErrorCode.SOURCE_MERGE_BASIS_CONFLICT: 409,
    ErrorCode.SOURCE_NOT_MERGEABLE: 409,
    ErrorCode.SOURCE_MERGE_IDENTIFIER_CONFLICT: 409,
    ErrorCode.SOURCE_VERSION_NOT_FOUND: 404,
    ErrorCode.SOURCE_VERSION_NOT_FREEZABLE: 409,
    ErrorCode.SOURCE_VERSION_ALREADY_FROZEN: 409,
    ErrorCode.SOURCE_VERSION_IMMUTABLE: 409,
    ErrorCode.INVALID_SOURCE_VERSION_LINEAGE: 409,
    ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED: 422,
    ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED: 422,
    ErrorCode.SEARCH_PLAN_QUESTION_INVALID: 422,
    ErrorCode.SEARCH_PLAN_QUESTION_SCOPE_MISMATCH: 403,
    ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE: 409,
    ErrorCode.SEARCH_PLAN_NOT_FROZEN: 409,
    ErrorCode.ADAPTER_UNAVAILABLE: 503,
    ErrorCode.ADAPTER_VERSION_MISMATCH: 409,
}


def _response(request: Request, status: int, code: str, message: str, details: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=jsonable_encoder({"error": {"code": code, "message": message, "details": details}}),
        headers={"X-Request-ID": str(request.state.request_id)},
    )


def _violations(exc: RequestValidationError) -> list[dict[str, object]]:
    return sorted(
        (
            {
                "location": [str(part) for part in item["loc"]],
                "message": item["msg"],
                "type": item["type"],
            }
            for item in exc.errors()
        ),
        key=lambda item: (item["location"], item["type"], item["message"]),
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_identity(request: Request, call_next: Any):
        supplied = request.headers.get("X-Request-ID")
        try:
            request.state.request_id = UUID(supplied) if supplied is not None else new_uuid7()
            if supplied is not None and supplied != str(request.state.request_id):
                raise ValueError("request ID is not canonical")
        except ValueError:
            request.state.request_id = new_uuid7()
            return _response(
                request,
                422,
                ErrorCode.VALIDATION_ERROR.value,
                "Request validation failed.",
                {
                    "violations": [
                        {
                            "location": ["header", "X-Request-ID"],
                            "message": "Input should be a valid UUID",
                            "type": "uuid_parsing",
                        }
                    ]
                },
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(
            request,
            422,
            ErrorCode.VALIDATION_ERROR.value,
            "Request validation failed.",
            {"violations": _violations(exc)},
        )

    @app.exception_handler(ResearchBaseError)
    async def application_error(request: Request, exc: ResearchBaseError) -> JSONResponse:
        return _response(
            request,
            _STATUS[exc.code],
            exc.code.value,
            exc.message,
            dict(exc.details) if exc.details is not None else None,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        return _response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.", None)
