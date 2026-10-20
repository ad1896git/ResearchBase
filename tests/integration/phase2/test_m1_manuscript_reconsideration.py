"""M1-S2: real frozen manuscript correction and separate successor permission."""
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command as alembic
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.approval import RequestApprovalCommand
from researchbase.application.decision import RecordManuscriptRejectionReconsiderationCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B09_SHARE_SQL
from tests.integration.phase2.test_b11_readiness_decision import service as decisions
from tests.integration.phase2.test_b12_prepare_decision import prepare_command
from tests.integration.phase2.test_b14_publication_ready import issued
from tests.integration.phase2.test_b14r_ready_approval import (
    approver,
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
from tests.integration.phase2.test_m1_schema import config

_FIXTURES = (b04_env, b05_env, conclusion_env, decision_env, phase2_database_url, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def correction(env, purpose):
    if purpose == "READY_FOR_SUBMISSION":
        approval, request, rejector = setup(env)
    else:
        publication, ready, approval, _ = issued(env)
        publication.transition_publication_ready(env[2], ready)
        basis = decisions(env).record_prepare_submission_decision(env[3], prepare_command(env))
        review_ids = tuple(r.id for r in basis.basis if r.type == "InternalReviewRecord")
        request = RequestApprovalCommand(
            uuid4(),
            env[1].project_id,
            None,
            basis.id,
            review_ids,
            approval_purpose=purpose,
            manuscript_version_id=env[1].manuscript_version_id,
        )
        rejector = approver(env)
    approval.request_approval(env[2], request)
    rejection = approval.decide_approval(rejector, decide(request, "REJECT"))
    fresh_actor = approver(env)  # fixture actors have OWNER/REVIEWER in addition to this role
    fresh = create(
        env,
        principal=fresh_actor,
        summary=f"Correction of review {request.review_ids[0]}: the earlier assessment misread the frozen population; exact evidence supports this manuscript.",
    )
    actor = approver(env)
    assert request.manuscript_version_id is not None
    cmd = RecordManuscriptRejectionReconsiderationCommand(
        uuid4(),
        request.project_id,
        request.manuscript_version_id,
        purpose,
        "CORRECTED_REVIEW",
        (rejection.id,),
        (fresh.id,),
        f"Rejection {rejection.id} relied on review {request.review_ids[0]}; the fresh independent review explains the specific population error.",
        request.review_ids,
    )
    return decisions(env), cmd, actor, approval, request, rejection, rejector, fresh_actor


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_correction_successor_separate_approve_and_lock_free_replay(b05_env, purpose):
    env = b05_env
    app, cmd, actor, approval, request, _, _, _ = correction(env, purpose)
    statements = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(
            (statement, cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    def diagnose(context):
        print("S2 SQL failure", context.original_exception)

    event.listen(env[5], "handle_error", diagnose)
    event.listen(env[5], "before_cursor_execute", capture)
    try:
        saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
        start = [i for i, r in enumerate(statements) if r[0] == B09_SHARE_SQL]
        assert len(start) == 1 and statements[start[0]][1:] == ("READ_COMMITTED", False)
        assert all(r[1:] == ("REPEATABLE_READ", True) for r in statements[: start[0]])
        assert saved.manuscript_version_id == cmd.manuscript_version_id
        assert saved.scientific_conclusion_version_id is None and saved.current_coverage_complete
        assert saved.approval_purpose == purpose
        statements.clear()
        assert app.record_manuscript_rejection_reconsideration(cmd, actor) == saved
        assert app.get_manuscript_rejection_reconsideration(cmd.project_id, cmd.id, actor) == saved
        assert all(r[1:] == ("REPEATABLE_READ", True) for r in statements)
        assert not any(
            any(
                word in r[0].upper()
                for word in ("LOCK TABLE", "ADVISORY", "FOR SHARE", "FOR UPDATE", "SET CONSTRAINTS")
            )
            for r in statements
        )
    finally:
        event.remove(env[5], "before_cursor_execute", capture)
        event.remove(env[5], "handle_error", diagnose)
    successor = replace(
        request,
        id=uuid4(),
        prior_rejected_request_id=request.id,
        reconsideration_decision_id=saved.id,
    )
    result = approval.request_approval(env[2], successor)
    assert result.reconsideration and result.reconsideration.id == saved.id
    approval_command = decide(successor)
    if purpose == "PREPARE_SUBMISSION":
        with env[5].connect() as conn:
            expiry = conn.execute(text("SELECT clock_timestamp()+interval '1 hour'")).scalar_one()
        approval_command = decide(
            successor,
            "APPROVE_WITH_CONDITIONS",
            valid_until=expiry,
            requires_current_author_consent=True,
        )
    approved = approval.decide_approval(approver(env), approval_command)
    assert approved.grant and approved.grant.usable
    assert (
        app.get_manuscript_rejection_reconsideration(
            cmd.project_id, cmd.id, actor
        ).successor_request_id
        == successor.id
    )
    if purpose == "READY_FOR_SUBMISSION":
        from researchbase.application.publication import (
            PublicationService,
            TransitionPublicationReadyCommand,
        )

        provider = env[9]

        def live(principal, at):
            original = provider.principals.get(principal.actor_id)
            return (
                provider.enabled
                and original is not None
                and original.verified_at <= at
                and replace(principal, verified_at=original.verified_at) == original
            )

        provider.is_valid = live
        transition = PublicationService(env[4], env[9], env[7]).transition_publication_ready(
            env[2],
            TransitionPublicationReadyCommand(
                uuid4(),
                cmd.project_id,
                approved.grant.id,
                env[1].publication_id,
                successor.review_ids,
            ),
        )
        assert transition.result_publication_id == env[1].publication_id
    # Downgrade must refuse without changing the committed history.
    with pytest.raises(DBAPIError) as error:
        alembic.downgrade(config(env[5]), "0074_m1_manuscript_revision")
    assert getattr(error.value.orig, "sqlstate", None) == "P17F1"
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": cmd.id}
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
@pytest.mark.parametrize(
    "change", ["rejection", "fresh", "corrected", "rationale", "rejector", "reviewer", "author"]
)
def test_invalid_evidence_and_conflicts_rollback(b05_env, purpose, change):
    env = b05_env
    app, cmd, actor, _, _, _, rejector, fresh_actor = correction(env, purpose)
    if change in {"rejector", "reviewer", "author"}:
        actor = {"rejector": rejector, "reviewer": fresh_actor, "author": env[2]}[change]
    else:
        changes = {
            "rejection": {"rejected_approval_decision_ids": (uuid4(),)},
            "fresh": {"fresh_review_ids": (uuid4(),)},
            "corrected": {"corrected_review_ids": (uuid4(),)},
            "rationale": {"rationale": "Accept"},
        }[change]
        cmd = replace(cmd, **changes)
    with pytest.raises(ResearchBaseError):
        app.record_manuscript_rejection_reconsideration(cmd, actor)
    with env[5].connect() as conn:
        for table, column in (
            ("decision_records", "id"),
            ("decision_basis_manuscripts", "decision_id"),
            ("decision_basis_reviews", "decision_id"),
            ("decision_basis_approval_decisions", "decision_id"),
        ):
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE {column}=:id"), {"id": cmd.id}
                ).scalar_one()
                == 0
            )


def test_s2_upgrade_downgrade_restores_exact_0074_catalog(monkeypatch):
    from sqlalchemy import create_engine

    from tests.disposable_postgres import disposable_database
    from tests.integration.phase2.test_b14a_entry_schema import catalog_inventory

    # Start from an untouched 0074, rather than capturing a baseline after an S2
    # downgrade. This detects corruption of the predecessor constraint literals.
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        engine = create_engine(url)
        try:
            c = config(engine)
            alembic.upgrade(c, "0074_m1_manuscript_revision")

            def catalog():
                with engine.connect() as conn:
                    return (
                        catalog_inventory(conn),
                        conn.execute(
                            text("SELECT pg_get_viewdef('b10_edges'::regclass,true)")
                        ).scalar_one(),
                    )

            before = catalog()
            alembic.upgrade(c, "0075_m1_reconsideration")
            after = catalog()
            assert before[0]["columns"] == after[0]["columns"]
            with engine.connect() as conn:
                triggers = conn.execute(
                    text(
                        "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgrelid='decision_basis_manuscripts'::regclass AND tgname IN ('m1_complete_manuscript','b10_no_basis_cycle') ORDER BY tgname"
                    )
                ).all()
                assert triggers == [
                    ("b10_no_basis_cycle", True, True),
                    ("m1_complete_manuscript", True, True),
                ]
                assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
            alembic.downgrade(c, "0074_m1_manuscript_revision")
            assert catalog() == before
            alembic.upgrade(c, "0075_m1_reconsideration")
            assert catalog() == after
        finally:
            engine.dispose()


@pytest.mark.parametrize(
    "defect",
    [
        "empty",
        "missing_review",
        "missing_rejection",
        "wrong_purpose",
        "revised_target",
        "wrong_hash",
        "mixed_target",
    ],
)
def test_direct_sql_bypass_denied_atomically(b05_env, defect):
    env = b05_env
    app, cmd, actor, *_ = correction(env, "READY_FOR_SUBMISSION")
    saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
    identity = uuid4()
    with pytest.raises(DBAPIError), env[5].begin() as conn:
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(
            text(
                """INSERT INTO decision_records (id,project_id,decision_type,question,decision,rationale,decided_by,decided_at,supersedes_decision_id,basis_set_hash,content_hash,hash_scheme) SELECT :id,project_id,decision_type,CASE WHEN :defect='wrong_purpose' THEN 'Reconsider rejection for PREPARE_SUBMISSION' ELSE question END,CASE WHEN :defect='revised_target' THEN 'REVISED_TARGET' ELSE decision END,rationale,decided_by,decided_at,supersedes_decision_id,basis_set_hash,CASE WHEN :defect='wrong_hash' THEN repeat('0',64) ELSE content_hash END,hash_scheme FROM decision_records WHERE id=:old"""
            ),
            {"id": identity, "old": saved.id, "defect": defect},
        )
        if defect != "empty":
            for table, column in (
                ("decision_basis_manuscripts", "manuscript_version_id"),
                ("decision_basis_reviews", "internal_review_record_id"),
                ("decision_basis_approval_decisions", "approval_decision_id"),
            ):
                if (defect == "missing_review" and column == "internal_review_record_id") or (
                    defect == "missing_rejection" and column == "approval_decision_id"
                ):
                    continue
                conn.execute(
                    text(
                        f"INSERT INTO {table}(decision_id,{column},ordinal) SELECT :id,{column},ordinal FROM {table} WHERE decision_id=:old"
                    ),
                    {"id": identity, "old": saved.id},
                )
        if defect == "mixed_target":
            conn.execute(
                text(
                    "INSERT INTO decision_basis_claims (decision_id,claim_version_id,ordinal) VALUES (:id,:target,20)"
                ),
                {"id": identity, "target": env[8]},
            )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": identity}
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_exact_replay_after_write_role_loss_and_changed_scope_denials(b05_env, purpose):
    from researchbase.application.phase2_identity import CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service

    env = b05_env
    app, cmd, actor, *_ = correction(env, purpose)
    saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
    with env[5].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND role='APPROVER'"
            ),
            {"actor": actor.actor_id},
        ).scalar_one()
    identity, _, _ = _service(str(env[5].url))
    identity.close_project_role(
        CloseProjectRole(env[3], cmd.project_id, role, "Close write role", uuid4())
    )
    assert app.record_manuscript_rejection_reconsideration(cmd, actor) == saved
    for change, code in (
        ({"rationale": cmd.rationale + " Changed"}, ErrorCode.IDEMPOTENCY_CONFLICT),
        ({"manuscript_version_id": uuid4()}, ErrorCode.IDEMPOTENCY_CONFLICT),
        (
            {
                "approval_purpose": "PREPARE_SUBMISSION"
                if purpose == "READY_FOR_SUBMISSION"
                else "READY_FOR_SUBMISSION"
            },
            ErrorCode.IDEMPOTENCY_CONFLICT,
        ),
        ({"project_id": uuid4()}, ErrorCode.FORBIDDEN),
    ):
        with pytest.raises(ResearchBaseError) as error:
            app.record_manuscript_rejection_reconsideration(replace(cmd, **change), actor)
        assert error.value.code == code
    env[9].principals.pop(actor.actor_id)
    with pytest.raises(ResearchBaseError) as error:
        app.get_manuscript_rejection_reconsideration(cmd.project_id, cmd.id, actor)
    assert error.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_successor_reuse_and_actor_independence(b05_env, purpose):
    env = b05_env
    app, cmd, actor, approval, old, _, _, fresh_actor = correction(env, purpose)
    saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
    successor = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    for requester in (actor, fresh_actor):
        with pytest.raises(ResearchBaseError) as error:
            approval.request_approval(requester, successor)
        assert error.value.code == ErrorCode.CONFLICT_OF_INTEREST
    approval.request_approval(env[2], successor)
    with pytest.raises(ResearchBaseError) as error:
        approval.request_approval(env[2], replace(successor, id=uuid4()))
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    for decider in (actor, fresh_actor):
        with pytest.raises(ResearchBaseError) as error:
            approval.decide_approval(decider, decide(successor))
        assert error.value.code == ErrorCode.CONFLICT_OF_INTEREST


def test_saved_s2_basis_rederives_ordinals_without_admission(b05_env, monkeypatch):
    from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository

    env = b05_env
    app, cmd, actor, *_ = correction(env, "READY_FOR_SUBMISSION")
    saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
    original = SqlAlchemyDecisionRepository.reconsideration_basis

    def shuffled(repo, identity):
        return [r | {"ordinal": 999} for r in reversed(original(repo, identity))]

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "reconsideration_basis", shuffled)
    assert app.get_manuscript_rejection_reconsideration(cmd.project_id, cmd.id, actor) == saved


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_current_target_invalid_denies_but_old_corrected_target_may_be_stale(b05_env, purpose):
    from tests.integration.phase2.b25_support import impact
    from tests.integration.phase2.test_m1_reconsideration_races import other_request

    env = b05_env
    app, cmd, actor, approval, old, _, _, fresh_actor = correction(env, purpose)
    other, target_request = other_request(env, approval, purpose)
    with env[5].connect() as conn:
        document = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": cmd.manuscript_version_id},
        ).scalar_one()
    impact(env, "artifact_version", document, "invalid")
    with pytest.raises(ResearchBaseError) as error:
        app.record_manuscript_rejection_reconsideration(cmd, actor)
    assert error.value.code == ErrorCode.APPROVAL_TARGET_STALE
    fresh = create(
        other,
        principal=fresh_actor,
        summary="A specific correction of the prior review: the population and sample were confused; the independent frozen manuscript resolves that assessment error.",
    )
    replacement = replace(
        cmd,
        manuscript_version_id=target_request.manuscript_version_id,
        fresh_review_ids=(fresh.id,),
    )
    result = app.record_manuscript_rejection_reconsideration(replacement, actor)
    assert result.current_coverage_complete and result.cited_rejected_request_ids == (old.id,)
    assert app.get_manuscript_rejection_reconsideration(cmd.project_id, cmd.id, actor) == result
