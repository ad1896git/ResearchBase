"""B15 closed inputs, bounded roots and finite manifest coordinates."""

from dataclasses import FrozenInstanceError, replace
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.application.prepared_submission import (
    GetAuthorConsentQuery,
    GetPreparedSubmissionQuery,
    PrepareSubmissionCommand,
    RecordAuthorConsentCommand,
    WithdrawPreparedSubmissionCommand,
)
from researchbase.domain.authorship import ExactReference
from researchbase.domain.prepared_submission import ManifestItemReadback, project_occurrences
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def test_closed_frozen_commands():
    cmd = PrepareSubmissionCommand(*(uuid4() for _ in range(5)))
    with pytest.raises(FrozenInstanceError):
        cast(Any, cmd).id = uuid4()
    with pytest.raises(TypeError):
        PrepareSubmissionCommand(
            **{**{f: getattr(cmd, f) for f in cmd.__slots__}, "status": "FROZEN"}
        )
    for field in cmd.__slots__:
        with pytest.raises(ResearchBaseError) as exc:
            replace(cmd, **{field: str(uuid4())})
        assert exc.value.code == ErrorCode.VALIDATION_ERROR
    for cls in (GetAuthorConsentQuery, GetPreparedSubmissionQuery):
        with pytest.raises(ResearchBaseError):
            cls(uuid4(), cast(Any, True))


@pytest.mark.parametrize("reason", ["", "  \t", "a\0b", "\ud800", "\udfff", "a" * 10001, None, 5])
def test_reason_rejects_malformed(reason):
    with pytest.raises(ResearchBaseError) as exc:
        WithdrawPreparedSubmissionCommand(uuid4(), uuid4(), reason)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_reason_normalizes_and_preserves_whitespace():
    assert WithdrawPreparedSubmissionCommand(uuid4(), uuid4(), " e\u0301 \n").reason == " é \n"
    assert len(WithdrawPreparedSubmissionCommand(uuid4(), uuid4(), "x" * 10000).reason) == 10000


@pytest.mark.parametrize(
    "field,value",
    [
        ("consent_state", "WITHDRAWN"),
        ("consent_scope", "OTHER"),
        ("prior_consent_id", uuid4()),
        ("consent_state", None),
    ],
)
def test_only_direct_root_granted(field, value):
    cmd = RecordAuthorConsentCommand(
        uuid4(), uuid4(), uuid4(), "GRANTED", "PREPARED_PACKAGE", uuid4(), None
    )
    with pytest.raises(ResearchBaseError) as exc:
        replace(cmd, **{field: value})
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize("ordinal", [True, -1, 10000, "1", None])
def test_strict_manifest_ordinal(ordinal):
    with pytest.raises(ValueError):
        ManifestItemReadback(
            uuid4(), "FIGURE", ordinal, ExactReference("ArtifactVersion", uuid4(), "a" * 64)
        )


def test_projection_capacity_and_no_deduplication():
    ref = ExactReference("ArtifactVersion", uuid4(), "a" * 64)
    placement = ("FIGURE", "A", 0, ref)
    assert len(project_occurrences([placement] * 9900, 100)) == 9900
    with pytest.raises(ValueError):
        project_occurrences([placement] * 9901, 100)
    for author_count in (0, 101, True):
        with pytest.raises(ValueError):
            project_occurrences([], author_count)
    with pytest.raises(ValueError):
        project_occurrences([("OTHER", "A", 0, ref)], 1)


def test_existing_transport_pairs_are_unchanged():
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    expected = {
        "VALIDATION_ERROR": (422, 2),
        "AUTHENTICATION_REQUIRED": (401, 3),
        "FORBIDDEN": (403, 3),
        "NOT_FOUND": (404, 3),
        "VERSION_NOT_FROZEN": (409, 4),
        "FROZEN_REFERENCE_REQUIRED": (409, 5),
        "INVALID_STATE_TRANSITION": (409, 4),
        "IMMUTABLE_RECORD": (409, 4),
        "IDEMPOTENCY_CONFLICT": (409, 4),
        "CONCURRENT_MODIFICATION": (409, 4),
        "REFERENTIAL_INTEGRITY_ERROR": (409, 5),
        "PROVENANCE_CLOSURE_VIOLATION": (409, 5),
    }
    assert {
        code: (_STATUS[ErrorCode(code)], CLI_EXIT_CODES[ErrorCode(code)]) for code in expected
    } == expected
