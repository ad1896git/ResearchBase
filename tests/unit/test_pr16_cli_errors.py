from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from typer.testing import CliRunner

from researchbase.application.commands import WriteProjectionTarget
from researchbase.application.dto import WriteResult
from researchbase.cli.app import create_app
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@dataclass
class ErrorApplication:
    error: ResearchBaseError | None = None
    unexpected: BaseException | None = None
    calls: int = 0

    def create_project(self, command: object) -> object:
        self.calls += 1
        if self.unexpected is not None:
            raise self.unexpected
        if self.error is not None:
            raise self.error
        return WriteResult(id=uuid4(), server_timestamp=datetime.now(UTC))

    def project_write_result(self, result: WriteResult, target: WriteProjectionTarget) -> object:
        assert target is WriteProjectionTarget.PROJECT
        return {"ok": True}


@dataclass
class Services:
    application: Any
    provenance: Any = None
    governance: Any = None
    governance_queries: Any = None


def _invoke(fake: ErrorApplication, *args: str):
    return CliRunner().invoke(
        create_app(Services(fake)),
        ["--actor-id", str(uuid4()), *args],
    )


def test_all_stable_error_codes_have_cli_exit_mapping() -> None:
    expected = {
        ErrorCode.VALIDATION_ERROR: 2,
        ErrorCode.NOT_FOUND: 3,
        ErrorCode.AUTHENTICATION_REQUIRED: 3,
        ErrorCode.FORBIDDEN: 3,
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
    }
    assert set(expected) == set(ErrorCode)

    for code, exit_code in expected.items():
        fake = ErrorApplication(ResearchBaseError(code, "safe"))
        request_id = uuid4()
        result = CliRunner().invoke(
            create_app(Services(fake)),
            [
                "--actor-id",
                str(uuid4()),
                "--request-id",
                str(request_id),
                "project",
                "create",
                "--name",
                "P",
            ],
        )
        assert result.exit_code == exit_code
        assert code.value in result.stderr
        assert str(request_id) in result.stderr
        assert "sqlalchemy" not in result.stderr.lower()
        assert "psycopg" not in result.stderr.lower()
        assert "traceback" not in result.stderr.lower()


def test_invalid_uuid_does_not_call_application_and_reports_generated_request_id() -> None:
    fake = ErrorApplication()
    result = CliRunner().invoke(
        create_app(Services(fake)),
        [
            "--actor-id",
            "not-a-uuid",
            "project",
            "create",
            "--name",
            "P",
        ],
    )
    assert result.exit_code == 2
    assert fake.calls == 0
    assert "request_id=" in result.stderr
    request_text = result.stderr.split("request_id=", 1)[1].splitlines()[0]
    UUID(request_text)


def test_invalid_actor_id_honors_json_error_mode() -> None:
    fake = ErrorApplication()
    result = CliRunner().invoke(
        create_app(Services(fake)),
        [
            "--actor-id",
            "not-a-uuid",
            "project",
            "create",
            "--name",
            "P",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1
    assert '"code":"VALIDATION_ERROR"' in result.stderr
    assert '"request_id"' in result.stderr
    assert fake.calls == 0


def test_unexpected_application_error_is_controlled_and_does_not_leak_details() -> None:
    fake = ErrorApplication(unexpected=RuntimeError("private psycopg details"))
    result = CliRunner().invoke(
        create_app(Services(fake)),
        [
            "--actor-id",
            str(uuid4()),
            "project",
            "create",
            "--name",
            "P",
        ],
    )
    assert result.exit_code == 70
    assert "unexpected internal error" in result.stderr.lower()
