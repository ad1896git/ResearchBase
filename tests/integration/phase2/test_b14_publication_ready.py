"""B14 concrete publication effect, built only through accepted Application fixtures."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.publication import (
    GetPublicationReadyTransitionQuery,
    PublicationService,
    TransitionPublicationReadyCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b14r_ready_approval import (
    b04_env,
    b05_env,
    conclusion_env,
    create,
    decide,
    decision_env,
    phase2_database_url,
    revision_env,
    setup,
)

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def issued(env, *, lifetime=None):
    # This provider normally compares an entire test attestation by equality. A live
    # credential recheck compares subject/credential identity, independent of the
    # fresh verification timestamp supplied by the consumer.
    provider = env[9]

    def credential_live(principal, at):
        saved = provider.principals.get(principal.actor_id)
        return (
            provider.enabled
            and saved is not None
            and saved.verified_at <= at
            and replace(principal, verified_at=saved.verified_at) == saved
        )

    provider.is_valid = credential_live
    approval, request, approver = setup(env)
    approval.request_approval(env[2], request)
    if lifetime is None:
        approval_command = decide(request)
    else:
        with env[5].connect() as conn:
            expiry = conn.execute(
                text("SELECT clock_timestamp()+(:seconds * interval '1 second')"),
                {"seconds": lifetime},
            ).scalar_one()
        approval_command = decide(request, "APPROVE_WITH_CONDITIONS", valid_until=expiry)
    grant = approval.decide_approval(approver, approval_command).grant
    assert grant is not None
    app = PublicationService(env[4], env[9], env[7])
    return (
        app,
        TransitionPublicationReadyCommand(
            uuid4(), request.project_id, grant.id, env[1].publication_id, request.review_ids
        ),
        approval,
        approver,
    )


def counts(env):
    with env[5].connect() as conn:
        return tuple(
            conn.execute(text("SELECT count(*) FROM " + t)).scalar_one()
            for t in (
                "approval_grant_consumptions",
                "publication_lifecycle_events",
                "approval_grant_events",
            )
        )


def test_atomic_ready_and_exact_history(b05_env):
    env = b05_env
    app, cmd, approval, _ = issued(env)
    result = app.transition_publication_ready(env[2], cmd)
    assert result.result_publication_id == cmd.result_id
    from researchbase.domain.approval import PublicationReadyResult

    assert isinstance(result.result, PublicationReadyResult)
    assert result.result.publication_id == cmd.result_id
    assert result.result.consumption_id == result.id
    assert counts(env) == (1, 3, 2)
    view = app.get_publication_ready_transition(
        env[2], GetPublicationReadyTransitionQuery(cmd.project_id, result.id)
    )
    assert view.consumption == result
    assert view.prior_status == "INTERNAL_REVIEW" and view.new_status == "READY"
    assert view.current.publication_status == "READY" and view.current.target_validity == "VALID"
    assert view.current.blocking_issue_ids == ()
    assert approval.get_grant_consumption(env[2], cmd.project_id, cmd.command_key) == result
    assert app.transition_publication_ready(env[2], cmd) == result
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT row_version FROM publications WHERE id=:id"), {"id": cmd.result_id}
            ).scalar_one()
            == 4
        )


@pytest.mark.parametrize(
    "field,code",
    [
        ("result_id", ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID),
        ("checked_review_ids", ErrorCode.DECISION_BASIS_INVALID),
    ],
)
def test_material_substitution_leaves_no_effect(b05_env, field, code):
    env = b05_env
    app, cmd, _, _ = issued(env)
    changed = (uuid4(),) if field == "checked_review_ids" else uuid4()
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], replace(cmd, **{field: changed}))
    assert error.value.code == code
    assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize(
    "recommendation", ["ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT", "UNCERTAIN"]
)
def test_later_recommendations_do_not_rewrite_saved_basis(b05_env, recommendation):
    env = b05_env
    app, cmd, _, _ = issued(env)
    later = create(env, recommendation=recommendation)
    result = app.transition_publication_ready(env[2], cmd)
    assert result.checked_review_ids == cmd.checked_review_ids
    assert later.id not in result.checked_review_ids


@pytest.mark.parametrize(
    "stage", ["transition_ready", "insert_consumption", "terminalize", "force_constraints"]
)
def test_failure_injection_rolls_back_all_writes(b05_env, monkeypatch, stage):
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
    from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository

    env = b05_env
    app, cmd, _, _ = issued(env)
    cls = (
        SqlAlchemyPublicationRepository
        if stage == "transition_ready"
        else SqlAlchemyApprovalRepository
    )
    original = getattr(cls, stage)

    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected after effect/check")

    monkeypatch.setattr(cls, stage, fail)
    with pytest.raises(RuntimeError, match="injected"):
        app.transition_publication_ready(env[2], cmd)
    assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize("case", ["bytes", "blocker", "issuer_credential", "wrong_tuple"])
def test_first_use_rechecks_after_permission(b05_env, case):
    from researchbase.application.internal_review import ReviewIssueRequest

    env = b05_env
    app, cmd, _, approver = issued(env)
    code = ErrorCode.APPROVAL_GATE_FAILED
    if case == "bytes":
        with env[5].connect() as conn:
            digest = conn.execute(
                text(
                    "SELECT a.content_hash FROM artifact_versions a JOIN manuscript_versions m "
                    "ON m.document_artifact_version_id=a.id WHERE m.id=:id"
                ),
                {"id": env[1].manuscript_version_id},
            ).scalar_one()
        env[7]._path_for(digest).write_bytes(b"later altered bytes")
        code = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    elif case == "blocker":
        create(env, issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Later concern"),))
    elif case == "issuer_credential":
        del env[9].principals[approver.actor_id]
        code = ErrorCode.GRANT_STALE
    else:
        # The separately owned release fixture supplies a real finite wrong-purpose
        # grant in its own suite. Here an absent grant is an exact NOT_FOUND.
        cmd = replace(cmd, grant_id=uuid4())
        code = ErrorCode.NOT_FOUND
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], cmd)
    assert error.value.code == code and counts(env) == (0, 2, 1)


@pytest.mark.parametrize("state", ["STALE", "INVALID"])
@pytest.mark.parametrize("completed", [False, True])
def test_current_validity_denies_first_use_but_is_replay_diagnostics(b05_env, state, completed):
    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.integration.phase2.test_b11_readiness_decision import place_claim

    env = b05_env
    place_claim(env)
    app, cmd, _, _ = issued(env)
    saved = app.transition_publication_ready(env[2], cmd) if completed else None
    context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(env[4], SystemClock())
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            cmd.project_id,
            "code_bug",
            "major",
            "Later problem",
            "Recheck",
            "claim_version",
            env[8],
            context,
        )
    )
    governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            cmd.project_id,
            finding.id,
            {"basis": "TEST"},
            state.lower(),
            (ProposedImpactTarget("claim_version", env[8], state.lower()),),
            context,
        )
    )
    if completed:
        assert app.transition_publication_ready(env[2], cmd) == saved
        assert saved is not None
        view = app.get_publication_ready_transition(
            env[2], GetPublicationReadyTransitionQuery(cmd.project_id, saved.id)
        )
        assert view.current.target_validity == state and view.consumption == saved
        assert counts(env) == (1, 3, 2)
    else:
        with pytest.raises(ResearchBaseError) as error:
            app.transition_publication_ready(env[2], cmd)
        assert error.value.code == ErrorCode.APPROVAL_TARGET_STALE
        assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
def test_human_and_agent_share_same_ready_boundary(b05_env, actor_type):
    from tests.integration.phase2.test_approval import _actor

    env = b05_env
    app, cmd, _, _ = issued(env)
    if actor_type == "HUMAN":
        caller = _actor((None, None, env[3], env[10]))
        assert app.transition_publication_ready(caller, cmd).actor_id == caller.actor_id
    else:
        # Agent enrollment remains owned by its separately reviewed adapter. The
        # common boundary rejects an unbound Agent without a parallel write path.
        aid = uuid4()
        with env[5].begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO actors(id,actor_type,display_name,created_at) "
                    "VALUES (:id,'AGENT','Unbound caller',clock_timestamp())"
                ),
                {"id": aid},
            )
        caller = replace(env[2], actor_id=aid)
        env[9].principals[aid] = caller
        with pytest.raises(ResearchBaseError) as error:
            app.transition_publication_ready(caller, cmd)
        assert error.value.code == ErrorCode.FORBIDDEN
        assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE PUBLICATIONS",
        "INSERT INTO PUBLICATION_LIFECYCLE_EVENTS",
        "INSERT INTO APPROVAL_GRANT_CONSUMPTIONS",
        "INSERT INTO APPROVAL_GRANT_EVENTS",
        "UPDATE APPROVAL_GRANTS",
    ],
)
def test_failure_after_each_individual_sql_write_is_atomic(b05_env, statement):
    from sqlalchemy import event

    env = b05_env
    app, cmd, _, _ = issued(env)

    def fail_after_write(conn, cursor, sql, params, context, many):
        if sql.lstrip().upper().startswith(statement):
            raise RuntimeError("injected after individual write")

    event.listen(env[5], "after_cursor_execute", fail_after_write)
    try:
        with pytest.raises(RuntimeError, match="individual write"):
            app.transition_publication_ready(env[2], cmd)
    finally:
        event.remove(env[5], "after_cursor_execute", fail_after_write)
    assert counts(env) == (0, 2, 1)
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                {"id": cmd.result_id},
            ).scalar_one()
            == "INTERNAL_REVIEW"
        )
        assert (
            conn.execute(
                text("SELECT status FROM approval_grants WHERE id=:id"), {"id": cmd.grant_id}
            ).scalar_one()
            == "ACTIVE"
        )
