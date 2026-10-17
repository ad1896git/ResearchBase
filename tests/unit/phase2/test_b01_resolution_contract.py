"""Closed B01 values and independent literal M2 hash compatibility vectors."""

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from researchbase.application.search_result_resolution import (
    ExactResolutionQuery,
    RecordSearchResultResolutionCommand,
    SearchResultResolutionReadback,
)
from researchbase.domain.search_result_resolution import (
    normalize_basis,
    resolution_hash,
    result_doi,
    titles_match,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command():
    return RecordSearchResultResolutionCommand(
        uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), "  DOI basis  "
    )


def test_closed_frozen_values():
    value = command()
    assert value.basis == "DOI basis"
    with pytest.raises(FrozenInstanceError):
        value.basis = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        RecordSearchResultResolutionCommand(**asdict(value), extra=True)  # type: ignore[call-arg]
    with pytest.raises((AttributeError, TypeError)):
        value.extra = True  # type: ignore[attr-defined]
    assert ExactResolutionQuery(value.project_id, value.id).id == value.id


@pytest.mark.parametrize(
    "field", ["id", "project_id", "search_result_record_id", "source_id", "source_version_id"]
)
@pytest.mark.parametrize("value", [True, False, None, "00000000-0000-0000-0000-000000000001", 1])
def test_uuid_types_are_strict(field, value):
    with pytest.raises(ResearchBaseError) as error:
        replace(command(), **{field: value})
    assert error.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("value", ["", "  ", "x\x00y", "x\ny", "x\ud800y", "a" * 4097, True, None])
def test_basis_denies(value):
    with pytest.raises(ResearchBaseError) as error:
        normalize_basis(value)
    assert error.value.code is ErrorCode.VALIDATION_ERROR


def test_basis_nfc_boundary_and_interior_whitespace():
    assert normalize_basis(" e\u0301  x ") == "é  x"
    assert len(normalize_basis(" e\u0301" + "a" * 4095 + " ")) == 4096


@pytest.mark.parametrize(
    "value",
    [
        None,
        "10.1234/abc",
        "http://dx.doi.org/10.1234/abc",
        "https://DOI.org/10.1234/abc",
        "https://doi.org/invalid",
        "https://doi.org/10.1234/a?x=1",
    ],
)
def test_only_exact_valid_doi_hit_wrapper(value):
    with pytest.raises(ResearchBaseError) as error:
        result_doi(value)
    assert error.value.code is ErrorCode.IDENTIFIER_INVALID


def test_doi_and_exact_title_policy():
    assert result_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
    assert titles_match(" e\u0301 ", "é")
    assert not titles_match("Title", "title")
    assert not titles_match("A  B", "A B")


@pytest.mark.parametrize("nullable", [False, True])
def test_literal_hash_independent_of_m2_implementation(nullable):
    values = [UUID(int=i) for i in range(1, 6)]
    row: dict[str, Any] = dict(
        id=values[0],
        search_result_record_id=values[1],
        source_id=values[2],
        source_version_id=None if nullable else values[3],
        resolved_by=values[4],
        resolved_at=datetime(2026, 10, 15, 8, 1, 2, 123456, tzinfo=timezone(timedelta(hours=-4))),
        basis="DOI basis",
        hash_scheme="sha256-cjson-v1",
    )
    literal = dict(
        id=str(values[0]),
        search_result_record_id=str(values[1]),
        source_id=str(values[2]),
        source_version_id=None if nullable else str(values[3]),
        resolved_by=str(values[4]),
        resolved_at="2026-10-15T12:01:02.123456+00:00",
        basis="DOI basis",
        hash_scheme="sha256-cjson-v1",
    )
    expected = hashlib.sha256(
        json.dumps(literal, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert resolution_hash(row) == expected
    from researchbase.application.metadata_observation import _hash

    assert _hash(row) == expected
    row["content_hash"] = expected
    dto = SearchResultResolutionReadback(
        project_id=uuid4(), **dict(row, resolved_at=row["resolved_at"].astimezone(UTC))
    )
    assert dto.source_version_id == row["source_version_id"]


def test_no_error_enum_or_transport_drift():
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    assert "RESOLUTION_INVALID" not in ErrorCode.__members__
    assert "HASH_MISMATCH" not in ErrorCode.__members__
    assert _STATUS[ErrorCode.DUPLICATE_CONTENT] == 409
    assert CLI_EXIT_CODES[ErrorCode.DUPLICATE_CONTENT] == 4
