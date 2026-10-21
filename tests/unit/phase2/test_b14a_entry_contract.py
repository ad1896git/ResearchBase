"""Closed entry DTOs and unchanged transport error contracts."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.publication import (
    GetPublicationInternalReviewEntryQuery as Query,
)
from researchbase.application.publication import (
    PublicationInternalReviewEntryReadback as Readback,
)
from researchbase.application.publication import (
    TransitionPublicationInternalReviewCommand as Command,
)
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def cmd():
    return Command(uuid4(), uuid4(), uuid4(), uuid4(), "a" * 64)


def view():
    c = cmd()
    return Readback(
        c.id,
        c.project_id,
        c.publication_id,
        c.manuscript_version_id,
        c.expected_content_hash,
        "sha256-cjson-v1",
        "DRAFTING",
        "INTERNAL_REVIEW",
        uuid4(),
        datetime.now(UTC),
    )


@pytest.mark.parametrize("make", [cmd, view, lambda: Query(uuid4(), uuid4())])
def test_closed_immutable_slotted(make):
    dto = make()
    assert not hasattr(dto, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        dto.id = uuid4()
    values = {f.name: getattr(dto, f.name) for f in fields(dto)}
    with pytest.raises(TypeError):
        type(dto)(**(values | {"extra": None}))
    for name in values:
        with pytest.raises(TypeError):
            type(dto)(**{k: v for k, v in values.items() if k != name})


@pytest.mark.parametrize("name", ["id", "project_id", "publication_id", "manuscript_version_id"])
@pytest.mark.parametrize("bad", [None, 1, "00000000-0000-0000-0000-000000000001", b"uuid"])
def test_strict_uuid(name, bad):
    with pytest.raises(ResearchBaseError) as error:
        replace(cmd(), **{name: bad})
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("bad", [None, 1, "A" * 64, "a" * 63, "a" * 65, "g" * 64, " a" * 32])
def test_strict_digest(bad):
    with pytest.raises(ResearchBaseError) as error:
        replace(cmd(), expected_content_hash=bad)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "name,bad",
    [
        ("hash_scheme", "other"),
        ("prior_status", "INTERNAL_REVIEW"),
        ("new_status", "READY"),
        ("occurred_at", datetime.now()),
        ("occurred_at", datetime.now(timezone(timedelta(hours=1)))),
        ("occurred_at", "infinity"),
        ("actor_id", str(uuid4())),
    ],
)
def test_literal_saved_output(name, bad):
    with pytest.raises(ResearchBaseError) as error:
        cast(Any, replace)(view(), **{name: bad})
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "code,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("IMMUTABLE_RECORD", 409, 4),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
    ],
)
def test_existing_error_pairs(code, http, cli):
    error = ErrorCode(code)
    assert _STATUS[error] == http and CLI_EXIT_CODES[error] == cli
