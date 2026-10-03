from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def test_normative_error_codes_are_stable() -> None:
    assert [code.value for code in ErrorCode][:10] == [
        "NOT_FOUND",
        "INVALID_STATE_TRANSITION",
        "VERSION_NOT_FROZEN",
        "IMMUTABLE_RECORD",
        "FROZEN_REFERENCE_REQUIRED",
        "PROVENANCE_CLOSURE_VIOLATION",
        "CONCURRENT_MODIFICATION",
        "DUPLICATE_CONTENT",
        "REFERENTIAL_INTEGRITY_ERROR",
        "VALIDATION_ERROR",
    ]
    assert [code.value for code in ErrorCode][10:] == [
        "AUTHENTICATION_REQUIRED",
        "FORBIDDEN",
        "SUBJECT_BINDING_UNPROVEN",
        "SUBJECT_ALREADY_BOUND",
        "OWNER_COVERAGE_GAP",
        "OWNER_CREDENTIAL_UNAVAILABLE",
        "ENROLLMENT_CHALLENGE_EXPIRED",
        "BOOTSTRAP_CLOSED",
        "IDEMPOTENCY_CONFLICT",
        "LEGACY_STATE_INVALID",
        "IDENTIFIER_INVALID",
        "SOURCE_IDENTITY_CONFLICT",
        "IDENTIFIER_ALREADY_BOUND",
        "IDENTIFIER_BASIS_NOT_FROZEN",
        "SOURCE_NOT_FOUND",
        "SHARED_SOURCE_REJECTION_REQUIRES_REVIEW",
    ]


def test_error_has_machine_code_separate_from_message_and_structured_details() -> None:
    error = ResearchBaseError(
        ErrorCode.VALIDATION_ERROR,
        "Input is invalid",
        {"field": "actor_id"},
    )

    assert error.code is ErrorCode.VALIDATION_ERROR
    assert error.message == "Input is invalid"
    assert error.details == {"field": "actor_id"}
    assert error.to_dict() == {
        "code": "VALIDATION_ERROR",
        "message": "Input is invalid",
        "details": {"field": "actor_id"},
    }
