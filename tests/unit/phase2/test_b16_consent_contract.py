"""Closed consent commands and iterative complete alternating graphs."""

from dataclasses import fields, replace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.application.prepared_submission import (
    GetOwnAuthorConsentQuery,
    RecordAuthorConsentCommand,
)
from researchbase.domain.prepared_submission import consent_chain
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command():
    return RecordAuthorConsentCommand(
        uuid4(), uuid4(), uuid4(), "GRANTED", "PREPARED_PACKAGE", uuid4(), None
    )


@pytest.mark.parametrize(
    "state,prior", [("GRANTED", None), ("GRANTED", uuid4()), ("WITHDRAWN", uuid4())]
)
def test_closed_consent_states_and_uuid_fields(state, prior):
    cmd = replace(command(), consent_state=state, prior_consent_id=prior)
    for field in (
        "id",
        "project_id",
        "prepared_submission_version_id",
        "evidence_artifact_version_id",
        "prior_consent_id",
    ):
        with pytest.raises(ResearchBaseError) as exc:
            replace(cmd, **{field: str(uuid4())})
        assert exc.value.code == ErrorCode.VALIDATION_ERROR
    for extra in ("actor_id", "proxy", "captured_at", "hash", "grants"):
        with pytest.raises(TypeError):
            RecordAuthorConsentCommand(
                **{**{f.name: getattr(cmd, f.name) for f in fields(cmd)}, extra: uuid4()}
            )
    assert not hasattr(cmd, "__dict__")


@pytest.mark.parametrize(
    "field,value", [("consent_state", "OTHER"), ("consent_state", True), ("consent_scope", "OTHER")]
)
def test_invalid_enum_is_validation(field, value):
    with pytest.raises(ResearchBaseError) as exc:
        replace(command(), **{field: value})
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_withdrawal_root_is_invalid_transition():
    with pytest.raises(ResearchBaseError) as exc:
        replace(command(), consent_state="WITHDRAWN")
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


def rows(n=3):
    package, actor = uuid4(), uuid4()
    result = []
    for i in range(n):
        result.append(
            dict(
                id=UUID(int=i + 1),
                prepared_submission_version_id=package,
                actor_id=actor,
                consent_scope="PREPARED_PACKAGE",
                consent_state="GRANTED" if i % 2 == 0 else "WITHDRAWN",
                prior_consent_id=UUID(int=i) if i else None,
            )
        )
    return result


@pytest.mark.parametrize(
    "defect",
    ["fork", "self", "cycle", "wrong_actor", "wrong_package", "same_state", "absent_prior"],
)
def test_chain_rejects_invalid_graph(defect):
    chain = rows()
    if defect == "fork":
        chain[2]["prior_consent_id"] = chain[0]["id"]
    elif defect == "self":
        chain[1]["prior_consent_id"] = chain[1]["id"]
    elif defect == "cycle":
        chain[1]["prior_consent_id"] = chain[2]["id"]
    elif defect == "wrong_actor":
        chain[1]["actor_id"] = uuid4()
    elif defect == "wrong_package":
        chain[1]["prepared_submission_version_id"] = uuid4()
    elif defect == "same_state":
        chain[1]["consent_state"] = "GRANTED"
    else:
        chain[1]["prior_consent_id"] = uuid4()
    with pytest.raises(ValueError):
        consent_chain(chain)


def test_iterative_chain_has_no_history_cap_or_time_order():
    chain = rows(12000)
    assert consent_chain(tuple(reversed(chain))) == tuple(chain)
    assert consent_chain(()) == ()


def test_own_query_strict_and_minimal():
    query = GetOwnAuthorConsentQuery(uuid4(), uuid4(), uuid4())
    assert tuple(f.name for f in fields(query)) == (
        "project_id",
        "prepared_submission_version_id",
        "id",
    )
    with pytest.raises(ResearchBaseError):
        GetOwnAuthorConsentQuery(
            query.project_id, query.prepared_submission_version_id, cast(Any, True)
        )
