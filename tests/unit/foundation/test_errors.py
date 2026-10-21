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
        "REVIEW_TARGET_NOT_FROZEN",
        "CONFLICT_OF_INTEREST",
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
        "SOURCE_MERGE_PROPOSAL_NOT_FOUND",
        "SOURCE_MERGE_PROPOSAL_STALE",
        "SOURCE_MERGE_APPROVAL_MISSING",
        "SOURCE_MERGE_APPROVAL_FORBIDDEN",
        "SOURCE_MERGE_REJECTED",
        "SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED",
        "SOURCE_MERGE_BASIS_CONFLICT",
        "SOURCE_NOT_MERGEABLE",
        "SOURCE_MERGE_IDENTIFIER_CONFLICT",
        "SOURCE_VERSION_NOT_FOUND",
        "SOURCE_VERSION_NOT_FREEZABLE",
        "SOURCE_VERSION_ALREADY_FROZEN",
        "SOURCE_VERSION_IMMUTABLE",
        "INVALID_SOURCE_VERSION_LINEAGE",
        "SEARCH_PLAN_QUESTION_REQUIRED",
        "SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED",
        "SEARCH_PLAN_QUESTION_INVALID",
        "SEARCH_PLAN_QUESTION_SCOPE_MISMATCH",
        "SEARCH_PLAN_VERSION_IMMUTABLE",
        "SEARCH_PLAN_NOT_FROZEN",
        "ADAPTER_UNAVAILABLE",
        "ADAPTER_VERSION_MISMATCH",
        "APPROVAL_PURPOSE_TARGET_COMMAND_INVALID",
        "APPROVAL_GATE_FAILED",
        "DECISION_BASIS_INVALID",
        "APPROVAL_TARGET_STALE",
        "REJECTION_RECONSIDERATION_REQUIRED",
        "GRANT_INVALID",
        "GRANT_STALE",
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
