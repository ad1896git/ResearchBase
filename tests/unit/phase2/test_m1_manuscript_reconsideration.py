"""Closed S2 material and transport shapes; release ground remains separate."""

from dataclasses import asdict, replace
from typing import Literal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from researchbase.api.routes import ManuscriptReconsiderationIn
from researchbase.application.decision import RecordManuscriptRejectionReconsiderationCommand
from researchbase.cli.commands.governance import manuscript_reconsideration_command
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command(
    purpose: Literal["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"] = "READY_FOR_SUBMISSION",
):
    return RecordManuscriptRejectionReconsiderationCommand(
        uuid4(),
        uuid4(),
        uuid4(),
        purpose,
        "CORRECTED_REVIEW",
        (uuid4(),),
        (uuid4(),),
        "The earlier review misread the frozen population.",
        (uuid4(),),
    )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_both_purposes_closed_and_normalized(purpose):
    c = command(purpose)
    assert replace(c, rationale="e\u0301").rationale == "é"
    ids = (uuid4(), uuid4())
    assert replace(c, fresh_review_ids=ids).fresh_review_ids == tuple(sorted(ids, key=str))
    assert c.revision_action_ids == ()


@pytest.mark.parametrize(
    "change",
    [
        {"id": "invalid"},
        {"project_id": str(uuid4())},
        {"manuscript_version_id": None},
        {"approval_purpose": "INTERNAL_SCIENTIFIC_RELEASE"},
        {"approval_purpose": None},
        {"decision": "REVISED_TARGET"},
        {"decision": True},
        {"rationale": ""},
        {"rationale": "\u3000\t"},
        {"rationale": "x\x00y"},
        {"rationale": "x" * 16385},
        {"rejected_approval_decision_ids": ()},
        {"fresh_review_ids": ()},
        {"corrected_review_ids": ()},
        {"fresh_review_ids": [uuid4()]},
        {"corrected_review_ids": (str(uuid4()),)},
        {"revision_action_ids": (uuid4(),)},
        {"fresh_review_ids": tuple(uuid4() for _ in range(101))},
    ],
)
def test_strict_bounds_and_ground(change):
    with pytest.raises(ResearchBaseError) as error:
        replace(command(), **change)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


def test_duplicate_and_overlapping_review_sets():
    c = command()
    for change in (
        {"fresh_review_ids": c.corrected_review_ids},
        {"corrected_review_ids": c.corrected_review_ids * 2},
        {"rejected_approval_decision_ids": c.rejected_approval_decision_ids * 2},
    ):
        with pytest.raises(ResearchBaseError):
            replace(c, **change)


@pytest.mark.parametrize(
    "field", ["principal", "decided_at", "question", "scientific_conclusion_version_id"]
)
def test_api_forbids_trusted_or_other_target_fields(field):
    c = asdict(command())
    c.pop("project_id")
    c[field] = str(uuid4())
    with pytest.raises(ValidationError):
        ManuscriptReconsiderationIn.model_validate(c)


def test_cli_exact_arrays_and_no_extra_fields():
    import json

    c = command()
    body = json.loads(json.dumps(asdict(c), default=str))
    project = body.pop("project_id")
    assert manuscript_reconsideration_command(json.dumps(body), project) == c
    with pytest.raises(ResearchBaseError):
        manuscript_reconsideration_command(json.dumps(body | {"decided_at": "yesterday"}), project)


def test_readback_target_xor():
    from typing import get_type_hints

    from researchbase.application.decision import RejectionReconsiderationReadback

    annotations = get_type_hints(RejectionReconsiderationReadback)
    assert type(None) in annotations["manuscript_version_id"].__args__
    assert type(None) in annotations["scientific_conclusion_version_id"].__args__


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_api_and_cli_forward_closed_command_and_trusted_principal(monkeypatch, purpose):
    import json
    from types import SimpleNamespace
    from typing import Any, cast

    from researchbase.api import routes
    from researchbase.cli.commands import governance

    c = command(purpose)
    principal = object()
    calls = []

    class Decisions:
        def record_manuscript_rejection_reconsideration(self, cmd, actor):
            calls.append((cmd, actor))
            return {"id": str(cmd.id)}

        def get_manuscript_rejection_reconsideration(self, project, identity, actor):
            calls.append((project, identity, actor))
            return {"id": str(identity)}

    services = SimpleNamespace(decisions=Decisions())
    monkeypatch.setattr(routes, "_services", lambda request: services)
    monkeypatch.setattr(routes, "_verified_principal", lambda request: principal)
    body = asdict(c)
    body.pop("project_id")
    assert routes.record_manuscript_rejection_reconsideration(
        c.project_id, ManuscriptReconsiderationIn(**body), cast(Any, object())
    ) == {"id": str(c.id)}
    assert calls[-1] == (c, principal)
    routes.get_manuscript_rejection_reconsideration(c.project_id, c.id, cast(Any, object()))
    assert calls[-1] == (c.project_id, c.id, principal)
    monkeypatch.setattr(
        governance,
        "_b23_invoke",
        lambda ctx, json_mode, op: op(SimpleNamespace(services=services), principal),
    )
    governance.manuscript_reconsideration_record(
        cast(Any, object()), str(c.project_id), json.dumps(body, default=str), True
    )
    assert calls[-1] == (c, principal)
    governance.manuscript_reconsideration_show(
        cast(Any, object()), str(c.project_id), str(c.id), True
    )
    assert calls[-1] == (c.project_id, c.id, principal)


@pytest.mark.parametrize(
    "code,http,cli",
    [
        (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
        (ErrorCode.FORBIDDEN, 403, 3),
        (ErrorCode.CONFLICT_OF_INTEREST, 403, 3),
        (ErrorCode.NOT_FOUND, 404, 3),
        (ErrorCode.VALIDATION_ERROR, 422, 2),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 409, 5),
        (ErrorCode.REVIEW_TARGET_NOT_FROZEN, 409, 4),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
        (ErrorCode.REFERENTIAL_INTEGRITY_ERROR, 409, 5),
        (ErrorCode.IMMUTABLE_RECORD, 409, 4),
        (ErrorCode.INVALID_STATE_TRANSITION, 409, 4),
        (ErrorCode.DECISION_BASIS_INVALID, 409, 4),
        (ErrorCode.APPROVAL_TARGET_STALE, 409, 4),
        (ErrorCode.APPROVAL_GATE_FAILED, 409, 4),
        (ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, 409, 4),
        (ErrorCode.IDEMPOTENCY_CONFLICT, 409, 4),
        (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
    ],
)
def test_exact_contract_http_and_cli_error_table(code, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    assert _STATUS[code] == http
    assert CLI_EXIT_CODES[code] == cli
