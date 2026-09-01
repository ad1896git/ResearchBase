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
    ErrorCode.INVALID_STATE_TRANSITION: 409,
    ErrorCode.VERSION_NOT_FROZEN: 409,
    ErrorCode.FROZEN_REFERENCE_REQUIRED: 409,
    ErrorCode.IMMUTABLE_RECORD: 409,
    ErrorCode.CONCURRENT_MODIFICATION: 409,
    ErrorCode.DUPLICATE_CONTENT: 409,
    ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 409,
    ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 409,
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
