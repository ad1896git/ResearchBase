"""Completed READY is entitled historical readback, independent of first-use gates."""

# SQL assertions retain the reviewed literal lock/guard protocol.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.approval import RecordInternalScientificReleaseCommand
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.publication import (
    GetPublicationReadyTransitionQuery,
    PublicationService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b14_publication_ready import (
    b04_env,
    b05_env,
    conclusion_env,
    counts,
    create,
    decision_env,
    issued,
    phase2_database_url,
    revision_env,
)

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("field", ["grant_id", "result_id", "checked_review_ids"])
def test_changed_material_conflicts_after_completion(b05_env, field):
    env = b05_env
    app, cmd, _, _ = issued(env)
    app.transition_publication_ready(env[2], cmd)
    changed = (uuid4(),) if field == "checked_review_ids" else uuid4()
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], replace(cmd, **{field: changed}))
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert counts(env) == (1, 3, 2)


def test_cross_command_receipt_cannot_be_replayed_as_release(b05_env):
    env = b05_env
    app, cmd, approval, _ = issued(env)
    app.transition_publication_ready(env[2], cmd)
    release = RecordInternalScientificReleaseCommand(
        cmd.command_key, cmd.project_id, cmd.grant_id, cmd.result_id, cmd.checked_review_ids
    )
    with pytest.raises(ResearchBaseError) as error:
        approval._release(env[2], release)
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_new_key_cannot_reuse_consumed_permission(b05_env):
    env = b05_env
    app, cmd, _, _ = issued(env)
    app.transition_publication_ready(env[2], cmd)
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], replace(cmd, command_key=uuid4()))
    assert error.value.code == ErrorCode.GRANT_INVALID


def test_restart_later_blocker_and_missing_bytes_do_not_readmit_history(b05_env):
    env = b05_env
    app, cmd, approval, _ = issued(env)
    saved = app.transition_publication_ready(env[2], cmd)
    create(env, issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Later concern"),))
    with env[5].connect() as conn:
        digest = conn.execute(
            text(
                "SELECT content_hash FROM artifact_versions WHERE id=(SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id)"
            ),
            {"id": env[1].manuscript_version_id},
        ).scalar_one()
    env[7]._path_for(digest).unlink()
    restarted = PublicationService(env[4], env[9], env[7])
    assert restarted.transition_publication_ready(env[2], cmd) == saved
    view = restarted.get_publication_ready_transition(
        env[2], GetPublicationReadyTransitionQuery(cmd.project_id, saved.id)
    )
    assert view.consumption == saved and len(view.current.blocking_issue_ids) == 1
    assert approval.get_grant_consumption(env[2], cmd.project_id, cmd.command_key) == saved


@pytest.mark.parametrize("who", ["other_actor", "other_project", "credential_loss"])
def test_replay_scope_is_nondisclosing(b05_env, who):
    env = b05_env
    app, cmd, _, approver = issued(env)
    app.transition_publication_ready(env[2], cmd)
    principal = approver if who == "other_actor" else env[2]
    if who == "other_project":
        cmd = replace(cmd, project_id=uuid4())
    if who == "credential_loss":
        env[9].enabled = False
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(principal, cmd)
    assert error.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "corruption", ["dto", "hash", "event_actor", "event_time", "review_basis", "approval_hash"]
)
def test_privileged_corruption_fails_closed(b05_env, corruption):
    env = b05_env
    app, cmd, _, approver = issued(env)
    app.transition_publication_ready(env[2], cmd)
    table = {
        "dto": "approval_grant_consumptions",
        "hash": "approval_grant_consumptions",
        "event_actor": "publication_lifecycle_events",
        "event_time": "publication_lifecycle_events",
        "review_basis": "approval_request_reviews",
        "approval_hash": "approval_decisions",
    }[corruption]
    with env[5].begin() as conn:
        conn.execute(text("ALTER TABLE " + table + " DISABLE TRIGGER ALL"))
        if corruption == "dto":
            conn.execute(text("UPDATE approval_grant_consumptions SET result_dto='{}'"))
        elif corruption == "hash":
            conn.execute(
                text("UPDATE approval_grant_consumptions SET request_hash=:hash"),
                {"hash": "0" * 64},
            )
        elif corruption == "event_actor":
            conn.execute(
                text(
                    "UPDATE publication_lifecycle_events SET actor_id=:actor WHERE new_status='READY'"
                ),
                {"actor": approver.actor_id},
            )
        elif corruption == "event_time":
            conn.execute(
                text(
                    "UPDATE publication_lifecycle_events SET occurred_at=occurred_at-interval '1 second' WHERE new_status='READY'"
                )
            )
        elif corruption == "approval_hash":
            conn.execute(
                text("UPDATE approval_decisions SET content_hash=:hash"), {"hash": "0" * 64}
            )
        else:
            conn.execute(text("DELETE FROM approval_request_reviews"))
        conn.execute(text("ALTER TABLE " + table + " ENABLE TRIGGER ALL"))
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], cmd)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_issuer_credential_loss_is_not_historical_replay_gate(b05_env):
    env = b05_env
    app, cmd, _, approver = issued(env)
    saved = app.transition_publication_ready(env[2], cmd)
    del env[9].principals[approver.actor_id]
    assert app.transition_publication_ready(env[2], cmd) == saved
    assert (
        app.get_publication_ready_transition(
            env[2], GetPublicationReadyTransitionQuery(cmd.project_id, saved.id)
        ).consumption
        == saved
    )


def test_uncertain_commit_recovers_exact_original_receipt(b05_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    app, cmd, _, _ = issued(env)
    original = SqlAlchemyUnitOfWork.commit

    def uncertain(self):
        original(self)
        raise RuntimeError("connection lost after commit")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    with pytest.raises(RuntimeError, match="after commit"):
        app.transition_publication_ready(env[2], cmd)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", original)
    saved = app.transition_publication_ready(env[2], cmd)
    assert app.transition_publication_ready(env[2], cmd) == saved
    assert counts(env) == (1, 3, 2)


def test_write_role_loss_preserves_entitled_replay_and_read_loss_denies(b05_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    env = b05_env
    app, cmd, _, consumer = issued(env)
    saved = app.transition_publication_ready(consumer, cmd)
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(env[3], cmd.project_id, consumer.actor_id, "VIEWER", "TEST ONLY", uuid4())
    )

    def close(roles):
        with env[5].connect() as conn:
            assignments = conn.execute(
                text(
                    "SELECT id,role FROM project_role_assignments WHERE actor_id=:actor AND effective_until IS NULL"
                ),
                {"actor": consumer.actor_id},
            ).all()
        for rid, role in assignments:
            if role in roles:
                identity.close_project_role(
                    CloseProjectRole(env[3], cmd.project_id, rid, "TEST ONLY", uuid4())
                )

    close({"OWNER", "RESEARCHER", "APPROVER"})
    assert app.transition_publication_ready(consumer, cmd) == saved
    close({"VIEWER", "REVIEWER"})
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(consumer, cmd)
    assert error.value.code == ErrorCode.FORBIDDEN
