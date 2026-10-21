"""Closed HTTP/CLI screening input and trusted principal/error parity."""

import json
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from researchbase.api.routes import NoveltyAssessmentIn
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def body(e) -> dict[str, Any]:
    return dict(
        e.bodies[2],
        scope_statement="All visible exact-plan executions",
        closeness_criteria={"statements": ["Method"]},
        screening_basis={
            "probes": [
                {
                    "search_execution_id": str(uuid4()),
                    "query_index": 0,
                    "disposition": "NO_HITS",
                    "rationale": "Completed empty query",
                }
            ],
            "results": [],
        },
    )


def cli(e, value):
    return [
        "literature",
        "record-novelty-assessment",
        "--project-id",
        str(e.project),
        "--material-json",
        json.dumps(value),
        "--json",
    ]


def test_screening_first_replay_read_200_and_principal(novelty_transports):
    e = novelty_transports
    value = body(e)
    base = f"/v1/projects/{e.project}/novelty-assessments"
    for _ in range(2):
        response = e.client.post(base, json=value)
        assert response.status_code == 200, response.text
        command = e.service.record_novelty_assessment.call_args.args[1]
        assert command.screening_basis.probes[0].query_index == 0
        assert e.service.record_novelty_assessment.call_args.args[0] is e.principal
    assert e.client.get(base + "/" + str(e.id)).status_code == 200
    response = CliRunner().invoke(e.cli, cli(e, value))
    assert response.exit_code == 0, (response.stderr, response.exception)
    assert e.service.record_novelty_assessment.call_args.args[1] == command
    assert e.service.record_novelty_assessment.call_args.args[0] is e.principal


@pytest.mark.parametrize(
    "field,value",
    [
        ("query_index", True),
        ("query_index", "0"),
        ("extra", 1),
        ("search_execution_id", "bad"),
        ("disposition", "SUCCESS"),
    ],
)
def test_nested_strict_parity(novelty_transports, field, value):
    e = novelty_transports
    data = body(e)
    data["screening_basis"]["probes"][0][field] = value
    with pytest.raises(ValidationError):
        NoveltyAssessmentIn.model_validate(data)
    response = e.client.post(f"/v1/projects/{e.project}/novelty-assessments", json=data)
    assert response.status_code == 422
    assert CliRunner().invoke(e.cli, cli(e, data)).exit_code == 2
    e.service.record_novelty_assessment.assert_not_called()


@pytest.mark.parametrize(
    "code,status,exit_code",
    [
        (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
        (ErrorCode.FORBIDDEN, 403, 3),
        (ErrorCode.VALIDATION_ERROR, 422, 2),
        (ErrorCode.NOT_FOUND, 404, 3),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 409, 5),
        (ErrorCode.INVALID_STATE_TRANSITION, 409, 4),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
        (ErrorCode.IDEMPOTENCY_CONFLICT, 409, 4),
        (ErrorCode.IMMUTABLE_RECORD, 409, 4),
        (ErrorCode.REFERENTIAL_INTEGRITY_ERROR, 409, 5),
        (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
        (None, 500, 1),
    ],
)
def test_error_mapping_and_sanitized_fallback(novelty_transports, code, status, exit_code):
    e = novelty_transports
    e.service.record_novelty_assessment.side_effect = (
        ResearchBaseError(code, "Safe failure")
        if code
        else RuntimeError("private database details")
    )
    data = body(e)
    response = e.client.post(f"/v1/projects/{e.project}/novelty-assessments", json=data)
    assert response.status_code == status
    result = CliRunner().invoke(e.cli, cli(e, data))
    assert result.exit_code == exit_code
    if code is None:
        assert "private database details" not in response.text + result.stdout + result.stderr


@pytest.mark.parametrize(
    "field,value",
    [
        ("extra", 1),
        ("search_result_record_id", "bad"),
        ("search_result_record_id", "00000000-0000-0000-0000-00000000000A"),
        ("disposition", "SUCCESS"),
        ("criteria_ordinals", [True]),
        ("criteria_ordinals", ["0"]),
        ("criteria_ordinals", [0, 0]),
        ("criteria_ordinals", [1]),
        ("prior_art_relation_id", str(uuid4())),
        ("rationale", " "),
    ],
)
def test_nested_result_strict_parity(novelty_transports, field, value):
    e = novelty_transports
    data = body(e)
    row = dict(
        search_result_record_id=str(uuid4()),
        disposition="UNRESOLVED",
        criteria_ordinals=[0],
        rationale="Retained unresolved hit",
    )
    row[field] = value
    data["screening_basis"]["results"] = [row]
    response = e.client.post(f"/v1/projects/{e.project}/novelty-assessments", json=data)
    assert response.status_code == 422
    assert CliRunner().invoke(e.cli, cli(e, data)).exit_code == 2
    e.service.record_novelty_assessment.assert_not_called()
