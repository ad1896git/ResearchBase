"""Historical replay, restart, read authority and honest current validity."""

# SQL literals retain the reviewed relational predicates.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.internal_review import InternalReviewService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b08_support import (
    conclusion_env,
    decision_env,
    disposition_case,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.test_pr2_15_decision import _stale

pytestmark = pytest.mark.integration
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


@pytest.mark.parametrize("dismiss", [False, True])
def test_restart_lost_acknowledgment_and_later_invalidity_never_rewrites_history(
    revision_env, dismiss
):
    service, actor, cmd, base, action = disposition_case(revision_env, dismiss=dismiss)
    saved = service.record_issue_disposition(actor, cmd)
    _stale(revision_env[2])
    restarted = InternalReviewService(base[1], base[-1], base[2])
    replay = restarted.record_issue_disposition(actor, cmd)
    assert replay is not None
    assert replay.id == saved.id and replay.occurred_at == saved.occurred_at
    assert replay.old_target_validity != "VALID"
    assert replay.re_review_target_validity != "VALID"
    history = restarted.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert history.status == cmd.disposition and history.target_validity != "VALID"
    assert len(history.events) == 2
    assert (
        service.read(actor, base[5], history.original_review_id).issues[0].status == cmd.disposition
    )


def test_historical_replay_does_not_require_still_terminal_action(revision_env):
    service, actor, cmd, base, action = disposition_case(revision_env)
    saved = service.record_issue_disposition(actor, cmd)
    correction = revision_env[0].record_revision_action(
        base[3], replace(action, id=uuid4(), supersedes_revision_action_id=cmd.revision_action_id)
    )
    replay = service.record_issue_disposition(actor, cmd)
    assert replay.has_superseding_action and replay.id == saved.id
    assert correction.supersedes_revision_action_id == cmd.revision_action_id


def test_replay_after_writer_role_loss_requires_current_read_entitlement(revision_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, actor, cmd, base, _ = disposition_case(revision_env)
    saved = service.record_issue_disposition(actor, cmd)
    identity, _, _ = identity_service(base[8].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(actor, base[5], actor.actor_id, "VIEWER", "History", uuid4())
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND project_id=:project AND role='OWNER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(CloseProjectRole(base[3], base[5], role, "Writer closed", uuid4()))
    assert service.record_issue_disposition(actor, cmd) == saved
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).disposition == saved
    with base[8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND project_id=:project AND role='VIEWER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(CloseProjectRole(base[3], base[5], role, "Read closed", uuid4()))
    for read in (
        lambda: service.record_issue_disposition(actor, cmd),
        lambda: service.get_issue_history(actor, base[5], cmd.review_issue_id),
        lambda: service.get_issue_disposition(actor, base[5], cmd.id),
    ):
        with pytest.raises(ResearchBaseError) as caught:
            read()
        assert caught.value.code == ErrorCode.FORBIDDEN


def test_dismissal_of_historical_invalid_target_does_not_restore_validity(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env, dismiss=True)
    _stale(revision_env[2])
    saved = service.record_issue_disposition(actor, cmd)
    assert saved.old_target_validity != "VALID" and saved.re_review_target_validity != "VALID"
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).target_validity != "VALID"


def test_unknown_commit_acknowledgment_recovers_original_event_uuid(revision_env):
    from psycopg import OperationalError
    from sqlalchemy.exc import OperationalError as SqlOperationalError

    service, actor, cmd, base, _ = disposition_case(revision_env)

    def factory():
        uow = base[1]()
        commit = uow.commit

        def uncertain_commit():
            commit()
            raise SqlOperationalError(
                None, None, OperationalError("TEST SECRET lost acknowledgment")
            )

        uow.commit = uncertain_commit
        return uow

    uncertain = InternalReviewService(factory, base[-1], base[2])
    with pytest.raises(ResearchBaseError) as caught:
        uncertain.record_issue_disposition(actor, cmd)
    assert "SECRET" not in str(caught.value.to_dict())
    assert service.record_issue_disposition(actor, cmd).id == cmd.id
    assert len(service.get_issue_history(actor, base[5], cmd.review_issue_id).events) == 2
