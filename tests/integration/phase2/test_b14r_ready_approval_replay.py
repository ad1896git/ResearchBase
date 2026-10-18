"""Historical READY snapshots preserve saved material without read exclusion."""

# SQL assertions preserve the literal lock and guard protocol.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b14r_ready_approval import (
    b04_env,
    b05_env,
    conclusion_env,
    counts,
    create,
    decide,
    phase2_database_url,
    service,
    setup,
)
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def test_restart_exact_replay_changed_actor_material_and_terminal_collision(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    request = app.request_approval(env[2], cmd)
    command = decide(cmd)
    result = app.decide_approval(actor, command)
    app = service(env)
    assert app.request_approval(env[2], cmd).id == request.id
    assert app.decide_approval(actor, command) == result
    before = counts(env)
    for caller, changed, kind, code in (
        (
            env[2],
            replace(cmd, basis_decision_id=uuid4()),
            "request",
            ErrorCode.IDEMPOTENCY_CONFLICT,
        ),
        (env[3], cmd, "request", ErrorCode.FORBIDDEN),
        (env[2], replace(cmd, project_id=uuid4()), "request", ErrorCode.FORBIDDEN),
        (actor, replace(command, rationale="Changed"), "decision", ErrorCode.IDEMPOTENCY_CONFLICT),
        (env[3], command, "decision", ErrorCode.FORBIDDEN),
        (actor, decide(cmd), "decision", ErrorCode.IDEMPOTENCY_CONFLICT),
    ):
        with pytest.raises(ResearchBaseError) as error:
            getattr(app, "request_approval" if kind == "request" else "decide_approval")(
                caller, changed
            )
        assert error.value.code == code
    assert counts(env) == before


def test_all_exact_reads_replay_are_readonly_snapshots_without_hidden_locks(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    command = decide(cmd)
    result = app.decide_approval(actor, command)
    assert result.grant
    before = counts(env)
    statements = []

    def capture(conn, cursor, sql, params, context, many):
        statements.append(
            (sql, cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(env[5], "before_cursor_execute", capture)
    try:
        app.get_request(env[2], cmd.project_id, cmd.id)
        app.get_decision(env[2], cmd.project_id, result.id)
        grant = app.get_grant(env[2], cmd.project_id, result.grant.id)
        app.request_approval(env[2], cmd)
        app.decide_approval(actor, command)
        assert grant.usable and grant.unusable_code is None
        assert statements and all(i == "REPEATABLE_READ" and ro for _, i, ro in statements)
        assert not any(
            token in sql.upper()
            for sql, _, _ in statements
            for token in (
                "LOCK TABLE",
                "ADVISORY",
                "FOR SHARE",
                "FOR UPDATE",
                "FOR KEY SHARE",
                "INSERT ",
                "UPDATE ",
                "DELETE ",
            )
        )
    finally:
        event.remove(env[5], "before_cursor_execute", capture)
    assert counts(env) == before


@pytest.mark.parametrize("lock", ["tables", "scope", "rows"])
def test_history_and_replay_do_not_wait_for_exclusion(b05_env, lock):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    command = decide(cmd)
    result = app.decide_approval(actor, command)
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        if lock == "tables":
            holder.execute(
                text(
                    "LOCK TABLE publications,internal_review_records,review_issues IN ROW EXCLUSIVE MODE"
                )
            )
        elif lock == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                dict(key=f"pr216:scope:{cmd.project_id}:READY_FOR_SUBMISSION"),
            )
        else:
            holder.execute(
                text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
                dict(id=cmd.manuscript_version_id),
            )
            holder.execute(
                text("SELECT id FROM approval_requests WHERE id=:id FOR UPDATE"), dict(id=cmd.id)
            )
        try:
            assert (
                pool.submit(app.get_decision, env[2], cmd.project_id, result.id).result(timeout=5)
                == result
            )
            assert pool.submit(app.decide_approval, actor, command).result(timeout=5) == result
        finally:
            holder.rollback()


def test_history_after_later_blocker_and_approver_write_role_loss(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    command = decide(cmd)
    result = app.decide_approval(actor, command)
    create(
        env, recommendation="REJECT", issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Later"),)
    )
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            env[3], cmd.project_id, actor.actor_id, "VIEWER", "Retain history", uuid4()
        )
    )
    with env[5].connect() as conn:
        roles = (
            conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE actor_id=:id AND role IN ('APPROVER','OWNER') AND effective_until IS NULL"
                ),
                dict(id=actor.actor_id),
            )
            .scalars()
            .all()
        )
    for role in roles:
        identity.close_project_role(
            CloseProjectRole(env[3], cmd.project_id, role, "Role loss", uuid4())
        )
    before = counts(env)
    assert app.get_decision(actor, cmd.project_id, result.id).content_hash == result.content_hash
    assert app.decide_approval(actor, command).content_hash == result.content_hash
    assert counts(env) == before


def test_read_entitlement_rechecked_after_nested_verification(b05_env, monkeypatch):
    env = b05_env
    app, cmd, _ = setup(env)
    app.request_approval(env[2], cmd)
    original = app._request_view

    def view(uow, row):
        result = original(uow, row)
        env[9].enabled = False
        return result

    monkeypatch.setattr(app, "_request_view", view)
    try:
        with pytest.raises(ResearchBaseError) as error:
            app.get_request(env[2], cmd.project_id, cmd.id)
        assert error.value.code == ErrorCode.FORBIDDEN
    finally:
        env[9].enabled = True


def test_backend_read_locks_and_expired_terminal_history(b05_env, monkeypatch):
    from researchbase.application.approval import EvaluateApprovalGrantCommand

    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    with env[5].connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '2 seconds'")).scalar_one()
    command = decide(cmd, "APPROVE_WITH_CONDITIONS", valid_until=expiry)
    result = app.decide_approval(actor, command)
    assert result.grant is not None
    original = app._request_view
    observed = []

    def view(uow, row):
        result = original(uow, row)
        locks = uow._session.execute(
            text("SELECT locktype,mode FROM pg_locks WHERE pid=pg_backend_pid() AND granted")
        ).all()
        assert not any(
            kind in {"advisory", "tuple"} or (kind == "relation" and mode != "AccessShareLock")
            for kind, mode in locks
        )
        observed.extend(locks)
        return result

    monkeypatch.setattr(app, "_request_view", view)
    app.get_grant(env[2], cmd.project_id, result.grant.id)
    assert observed
    monkeypatch.setattr(app, "_request_view", original)
    with env[5].connect() as conn:
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"
            ),
            dict(expiry=expiry),
        )
    before = counts(env)
    grant = app.get_grant(env[2], cmd.project_id, result.grant.id)
    assert grant.status == "ACTIVE" and not grant.usable and grant.unusable_code == "GRANT_INVALID"
    assert counts(env) == before
    terminal = app.evaluate_approval_grant(
        env[2], EvaluateApprovalGrantCommand(cmd.project_id, grant.id)
    )
    assert terminal.grant.status == "EXPIRED"
    saved = counts(env)
    assert app.decide_approval(actor, command).content_hash == result.content_hash
    assert app.get_grant(env[2], cmd.project_id, grant.id).status == "EXPIRED"
    assert counts(env) == saved


def test_history_uses_saved_target_when_navigation_changes(b05_env, monkeypatch):
    from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository

    env = b05_env
    app, cmd, actor = setup(env)
    saved = app.request_approval(env[2], cmd)
    original = SqlAlchemyPublicationRepository.publication

    def parent(self, *args):
        row = original(self, *args)
        return None if row is None else {**row, "current_manuscript_version_id": uuid4()}

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "publication", parent)
    assert app.get_request(env[2], cmd.project_id, cmd.id) == saved
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, decide(cmd))
    assert error.value.code == ErrorCode.APPROVAL_TARGET_STALE


@pytest.mark.parametrize(
    "kind", ["decision_hash", "review_hash", "entry_history", "request_reviews"]
)
def test_corrupt_retained_provenance_denies_history(b05_env, monkeypatch, kind):
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
    from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )
    from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository

    env = b05_env
    app, cmd, _ = setup(env)
    app.request_approval(env[2], cmd)
    if kind == "decision_hash":
        original = SqlAlchemyDecisionRepository.decision

        def changed(self, *args):
            row = original(self, *args)
            return None if row is None else {**row, "content_hash": "0" * 64}

        monkeypatch.setattr(SqlAlchemyDecisionRepository, "decision", changed)
    elif kind == "review_hash":
        original = SqlAlchemyInternalReviewRepository.review

        def changed(self, *args):
            row = original(self, *args)
            return None if row is None else {**row, "content_hash": "0" * 64}

        monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "review", changed)
    elif kind == "entry_history":
        monkeypatch.setattr(SqlAlchemyPublicationRepository, "entry_events", lambda *_: [])
    else:
        monkeypatch.setattr(SqlAlchemyApprovalRepository, "reviews", lambda *_: [])
    with pytest.raises(ResearchBaseError) as error:
        app.get_request(env[2], cmd.project_id, cmd.id)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
