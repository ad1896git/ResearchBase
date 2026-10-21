"""B22 shares the trusted Application boundary, envelopes and pinned errors."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from researchbase.api.routes import PriorArtIn
from researchbase.application.novelty import (
    CurrentValidity,
    PriorArtChainHead,
    PriorArtSelectionReadback,
)
from researchbase.domain.novelty import HashRef, PriorArtSelectionState
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def path(e):
    return f"/v1/projects/{e.project}/prior-art-relations/selection"


def params(e):
    return {"claim_version_id": str(uuid4()), "source_version_id": str(uuid4())}


def cli_args(e, ids):
    return [
        "literature",
        "select-prior-art-relation",
        "--project-id",
        str(e.project),
        "--claim-version-id",
        ids["claim_version_id"],
        "--source-version-id",
        ids["source_version_id"],
        "--json",
    ]


@pytest.mark.parametrize(
    "state,count",
    [
        (PriorArtSelectionState.EMPTY, 0),
        (PriorArtSelectionState.UNIQUE, 1),
        (PriorArtSelectionState.AMBIGUOUS, 2),
    ],
)
def test_selection_static_route_200_and_cli(novelty_transports, state, count):
    e = novelty_transports
    ids = params(e)
    now = datetime.now(UTC)
    chains = tuple(
        PriorArtChainHead(
            uuid4(), HashRef("PriorArtRelation", uuid4(), "a" * 64), CurrentValidity(now, False, ())
        )
        for _ in range(count)
    )
    from uuid import UUID

    e.service.select_prior_art_relation.return_value = PriorArtSelectionReadback(
        e.project,
        UUID(ids["claim_version_id"]),
        UUID(ids["source_version_id"]),
        now,
        state,
        chains,
        chains[0].terminal.id if count == 1 else None,
    )
    response = e.client.get(path(e), params=ids)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == state.value
    assert response.json()["selected_prior_art_relation_id"] == (
        str(chains[0].terminal.id) if count == 1 else None
    )
    assert e.service.select_prior_art_relation.call_args.args[0] is e.principal
    result = CliRunner().invoke(e.cli, cli_args(e, ids))
    assert result.exit_code == 0, (result.stderr, result.exception)
    assert json.loads(result.stdout)["state"] == state.value
    assert e.service.select_prior_art_relation.call_args.args[0] is e.principal


@pytest.mark.parametrize(
    "code,status,exit_code",
    [
        (ErrorCode.VALIDATION_ERROR, 422, 2),
        (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
        (ErrorCode.FORBIDDEN, 403, 3),
        (ErrorCode.NOT_FOUND, 404, 3),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 409, 5),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
        (ErrorCode.INVALID_STATE_TRANSITION, 409, 4),
        (ErrorCode.IDEMPOTENCY_CONFLICT, 409, 4),
        (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
        (ErrorCode.IMMUTABLE_RECORD, 409, 4),
        (ErrorCode.REFERENTIAL_INTEGRITY_ERROR, 409, 5),
    ],
)
def test_all_pinned_errors_no_partial_results(novelty_transports, code, status, exit_code):
    e = novelty_transports
    e.service.select_prior_art_relation.side_effect = ResearchBaseError(code, "bounded diagnostic")
    ids = params(e)
    response = e.client.get(path(e), params=ids)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code.value
    assert "chains" not in response.json()
    result = CliRunner().invoke(e.cli, cli_args(e, ids))
    assert result.exit_code == exit_code
    assert json.loads(result.stderr)["error"]["code"] == code.value


def test_optional_predecessor_closed_request_and_cli_flag(novelty_transports):
    e = novelty_transports
    body = e.bodies[1]
    assert PriorArtIn.model_validate(body).supersedes_prior_art_relation_id is None
    previous = str(uuid4())
    correction = {**body, "supersedes_prior_art_relation_id": previous}
    assert (
        e.client.post(f"/v1/projects/{e.project}/prior-art-relations", json=correction).status_code
        == 200
    )
    assert (
        str(e.service.record_prior_art_relation.call_args.args[1].supersedes_prior_art_relation_id)
        == previous
    )
    for field in ["material_version", "assessed_by", "content_hash", "current_validity"]:
        with pytest.raises(ValidationError):
            PriorArtIn.model_validate({**correction, field: "untrusted"})
    for invalid in [True, 1, uuid4().hex, previous.upper()]:
        if invalid == previous:
            continue
        with pytest.raises(ValidationError):
            PriorArtIn.model_validate({**correction, "supersedes_prior_art_relation_id": invalid})
    args = [
        "literature",
        "record-prior-art-relation",
        "--project-id",
        str(e.project),
        "--material-json",
        json.dumps(body),
        "--supersedes-prior-art-relation-id",
        previous,
        "--json",
    ]
    result = CliRunner().invoke(e.cli, args)
    assert result.exit_code == 0, (result.stderr, result.exception)
    assert (
        str(e.service.record_prior_art_relation.call_args.args[1].supersedes_prior_art_relation_id)
        == previous
    )
    args[args.index("--material-json") + 1] = json.dumps(correction)
    assert CliRunner().invoke(e.cli, args).exit_code == 0
    args[args.index("--supersedes-prior-art-relation-id") + 1] = str(uuid4())
    assert CliRunner().invoke(e.cli, args).exit_code == 2


def test_invalid_selection_uuid_and_sanitized_fallback(novelty_transports):
    e = novelty_transports
    ids = params(e)
    assert e.client.get(path(e), params={**ids, "claim_version_id": uuid4().hex}).status_code == 422
    assert e.client.get(path(e), params={**ids, "root_ids": str(uuid4())}).status_code == 422
    e.service.select_prior_art_relation.side_effect = RuntimeError("private-sql-credential")
    response = e.client.get(path(e), params=ids)
    assert response.status_code == 500 and "private-sql" not in response.text
    result = CliRunner().invoke(e.cli, cli_args(e, ids))
    assert result.exit_code == 1 and "private-sql" not in result.stderr
    assert json.loads(result.stderr)["error"]["code"] == "INTERNAL_ERROR"
