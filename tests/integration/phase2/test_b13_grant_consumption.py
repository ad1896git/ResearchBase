"""Concrete release receipt: atomic local effect and immutable grant history."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.approval import RecordInternalScientificReleaseCommand
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_approval import (
    _decide,
)
from tests.integration.phase2.test_approval import (
    approval_env as approval_env,
)
from tests.integration.phase2.test_approval import (
    conclusion_env as conclusion_env,
)
from tests.integration.phase2.test_approval import (
    decision_env as decision_env,
)
from tests.integration.phase2.test_approval import (
    phase2_database_url as phase2_database_url,
)
from tests.integration.phase2.test_b14r_ready_approval import (
    b04_env,
    b05_env,
    revision_env,
)

_FIXTURES = (
    approval_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    b04_env,
    b05_env,
    revision_env,
)
pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)


def issued(env, *, expiry=None):
    service, requester, approver, request, decision = env
    service.request_approval(requester, request)
    grant = service.decide_approval(
        approver,
        _decide(
            request,
            **({"outcome": "APPROVE_WITH_CONDITIONS", "valid_until": expiry} if expiry else {}),
        ),
    ).grant
    base = decision[-1]
    owner = ScientificConclusionService(base[1], base[9], base[2])
    assert grant is not None
    command = RecordInternalScientificReleaseCommand(
        uuid4(),
        request.project_id,
        grant.id,
        request.scientific_conclusion_version_id,
        request.review_ids,
    )
    return owner, requester, command, grant


def counts(env):
    with env[-1][-1][8].connect() as conn:
        return tuple(
            conn.execute(text("SELECT count(*) FROM " + t)).scalar_one()
            for t in (
                "approval_grant_consumptions",
                "approval_grant_events",
                "approval_request_reviews",
            )
        )


def test_release_receipt_is_atomic_result(approval_env):
    owner, actor, cmd, grant = issued(approval_env)
    result = owner.record_internal_scientific_release(actor, cmd)
    assert result.result.scientific_conclusion_version_id == cmd.result_id
    assert result.result.consumption_id == result.id
    assert result.grant_id == grant.id and result.checked_review_ids == cmd.checked_review_ids
    assert counts(approval_env) == (1, 2, 1)
    view = approval_env[0].get_grant(actor, cmd.project_id, grant.id)
    assert view.status == "CONSUMED" and view.unusable_code == "GRANT_INVALID"
    assert owner.record_internal_scientific_release(actor, cmd) == result
    assert approval_env[0].get_grant_consumption(actor, cmd.project_id, cmd.command_key) == result


@pytest.mark.parametrize("field", ["result_id", "checked_review_ids"])
def test_substitutions_leave_zero_receipts(approval_env, field):
    owner, actor, cmd, _ = issued(approval_env)
    change = uuid4() if field == "result_id" else (uuid4(),)
    with pytest.raises(ResearchBaseError):
        owner.record_internal_scientific_release(actor, replace(cmd, **{field: change}))
    assert counts(approval_env) == (0, 1, 1)


@pytest.mark.parametrize("stage", ["insert_consumption", "terminalize", "force_constraints"])
def test_failure_injection_rolls_back_every_write(approval_env, monkeypatch, stage):
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository

    owner, actor, cmd, _ = issued(approval_env)
    original = getattr(SqlAlchemyApprovalRepository, stage)

    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected after write/check")

    monkeypatch.setattr(SqlAlchemyApprovalRepository, stage, fail)
    with pytest.raises(RuntimeError):
        owner.record_internal_scientific_release(actor, cmd)
    assert counts(approval_env) == (0, 1, 1)


def test_invalid_closure_denies_without_terminal_maintenance(approval_env):
    from tests.integration.phase2.test_pr2_15_decision import _stale

    owner, actor, cmd, _ = issued(approval_env)
    _stale(approval_env[-1])
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(actor, cmd)
    assert error.value.code == ErrorCode.GRANT_STALE
    assert counts(approval_env) == (0, 1, 1)


def test_superseded_navigation_alone_does_not_deny_exact_release(approval_env):
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    owner, actor, cmd, _ = issued(approval_env)
    env = approval_env[-1]
    scientific, _, _, author, _, project, claim, _, _, _ = env[-1]
    successor = scientific.revise(
        author,
        project,
        env[3].conclusion_id,
        "New navigation",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, successor.conclusion_id, successor.version_id, uuid4())
    assert (
        owner.record_internal_scientific_release(actor, cmd).result.scientific_conclusion_version_id
        == cmd.result_id
    )


def test_b32_approval_alone_has_no_release_effect(approval_env):
    service, actor, approver, request, decision = approval_env
    engine = decision[-1][8]
    with engine.connect() as conn:
        before = conn.execute(
            text("SELECT status, content_hash FROM scientific_conclusion_versions WHERE id=:id"),
            {"id": request.scientific_conclusion_version_id},
        ).one()
    service.request_approval(actor, request)
    assert counts(approval_env)[0:2] == (0, 0)
    service.decide_approval(approver, _decide(request))
    assert counts(approval_env)[0:2] == (0, 1)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT status, content_hash FROM scientific_conclusion_versions WHERE id=:id"
                ),
                {"id": request.scientific_conclusion_version_id},
            ).one()
            == before
        )
        assert (
            conn.execute(text("SELECT count(*) FROM publication_lifecycle_events")).scalar_one()
            == 0
        )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_b32_manuscript_grants_cannot_release_conclusion(b05_env, purpose):
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.b17_fixtures import build
    from tests.integration.phase2.test_b14_publication_ready import issued as ready_issued
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    env = b05_env
    if purpose == "READY_FOR_SUBMISSION":
        _, ready, approval, _ = ready_issued(env)
        grant, reviews = ready.grant_id, ready.checked_review_ids
    else:
        package = build(env)
        approval = package.approval
        grant, reviews = package.command.grant_id, package.command.checked_review_ids
    scientific, _, _, author, _, project, claim, _, _, _ = env[10]
    target = scientific.create(
        author,
        project,
        "Exact release target",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    assert approval.get_grant(env[2], project, grant).status == "ACTIVE"
    command = RecordInternalScientificReleaseCommand(
        uuid4(), project, grant, target.version_id, reviews
    )
    tables = (
        "approval_grant_consumptions",
        "approval_grant_events",
        "publication_lifecycle_events",
    )
    with env[5].connect() as conn:
        before = tuple(
            conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() for table in tables
        )
    with pytest.raises(ResearchBaseError) as caught:
        scientific.record_internal_scientific_release(env[2], command)
    assert caught.value.code == ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID
    with env[5].connect() as conn:
        assert (
            tuple(
                conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() for table in tables
            )
            == before
        )


def test_b32_completed_release_replays_after_expiry(approval_env):
    from time import monotonic, sleep

    engine = approval_env[-1][-1][8]
    with engine.connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '5 seconds'")).scalar_one()
    owner, actor, command, _ = issued(approval_env, expiry=expiry)
    saved = owner.record_internal_scientific_release(actor, command)
    before = counts(approval_env)
    deadline = monotonic() + 10
    while True:
        with engine.connect() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at >= expiry:
            break
        assert monotonic() < deadline, "DB clock did not reach grant expiry"
        sleep(0.02)
    assert owner.record_internal_scientific_release(actor, command) == saved
    assert (
        approval_env[0].get_grant_consumption(actor, command.project_id, command.command_key)
        == saved
    )
    assert counts(approval_env) == before
