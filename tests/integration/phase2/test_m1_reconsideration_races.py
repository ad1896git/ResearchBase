"""M1-S2 actual backend waits, fresh authorization and complete rejection scope."""
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
from tests.integration.phase2.test_b14r_ready_approval import (
    another_target,
    approver,
    create,
    decide,
)
from tests.integration.phase2.test_m1_manuscript_reconsideration import (
    b04_env,
    b05_env,
    conclusion_env,
    correction,
    decision_env,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

_FIXTURES = (b04_env, b05_env, conclusion_env, decision_env, phase2_database_url, revision_env)
pytestmark = pytest.mark.integration


def no_history(engine, identity):
    with engine.connect() as conn:
        for table, column in (
            ("decision_records", "id"),
            ("decision_basis_manuscripts", "decision_id"),
            ("decision_basis_reviews", "decision_id"),
            ("decision_basis_approval_decisions", "decision_id"),
        ):
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE {column}=:id"), {"id": identity}
                ).scalar_one()
                == 0
            )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
@pytest.mark.parametrize("lock", ["inventory", "scope", "target"])
def test_credential_expiry_after_observed_wait_denies_atomically(b05_env, purpose, lock):
    env = b05_env
    app, cmd, actor, *_ = correction(env, purpose)
    engine = env[5]
    checks = []
    original = env[9].is_valid
    with engine.connect() as observer:
        expiry = observer.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()

    def credential(principal, at):
        if principal.actor_id == actor.actor_id:
            checks.append(at)
            return at < expiry and original(principal, at)
        return original(principal, at)

    env[9].is_valid = credential
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        if lock == "inventory":
            holder.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
        elif lock == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr216:scope:{cmd.project_id}:{purpose}"},
            )
        else:
            holder.execute(
                text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
                {"id": cmd.manuscript_version_id},
            )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(app.record_manuscript_rejection_reconsideration, cmd, actor)
        try:
            witness = _wait_for_pg_blocker(
                engine,
                pid,
                {"inventory": "relation", "scope": "advisory", "target": "transactionid"}[lock],
            )
            with engine.connect() as observer:
                tx_started = observer.execute(
                    text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                    {"pid": witness["pid"]},
                ).scalar_one()
                assert tx_started < expiry and witness["observed_at"] < expiry
                # Wait only after witnessing the actual blocking backend; expiry is database-derived.
                observer.execute(
                    text(
                        "SELECT pg_sleep(greatest(0,extract(epoch FROM (CAST(:expiry AS timestamptz)-clock_timestamp())))+0.02)"
                    ),
                    {"expiry": expiry},
                )
                acquired_after = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
                assert acquired_after >= expiry
        finally:
            holder.commit()
        with pytest.raises(ResearchBaseError) as denied:
            future.result(timeout=15)
        assert denied.value.code == ErrorCode.FORBIDDEN
        assert checks[-1] >= acquired_after and checks[-1] > expiry
        print(
            "S2_EXPIRY_EVIDENCE",
            tx_started,
            witness["observed_at"],
            expiry,
            acquired_after,
            checks[-1],
            denied.value.code,
        )
    no_history(engine, cmd.id)


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
@pytest.mark.parametrize("reject_first", [False, True])
def test_reconsideration_vs_new_rejection_both_commit_orders(
    b05_env, monkeypatch, purpose, reject_first
):
    env = b05_env
    app, cmd, actor, approval, old, _, rejector, _ = correction(env, purpose)
    saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
    pending = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    approval.request_approval(env[2], pending)
    again = replace(cmd, id=uuid4())
    entered, release = Event(), Event()
    first_pid = []
    original = SqlAlchemyApprovalRepository.lock_snapshot

    def pause(repo, *, deciding=False):
        original(repo, deciding=deciding)
        if deciding == reject_first:
            first_pid.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(12)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_snapshot", pause)

    def reconsider():
        return app.record_manuscript_rejection_reconsideration(again, actor)

    def reject():
        return approval.decide_approval(rejector, decide(pending, "REJECT"))

    first, second = (reject, reconsider) if reject_first else (reconsider, reject)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ahead = pool.submit(first)
        assert entered.wait(5)
        behind = pool.submit(second)
        try:
            witness = _wait_for_pg_blocker(env[5], first_pid[0], "relation")
            assert witness["relation"] == "publications"
        finally:
            release.set()
        ahead.result(timeout=15)
        if reject_first:
            with pytest.raises(ResearchBaseError) as denied:
                behind.result(timeout=15)
            assert denied.value.code == ErrorCode.DECISION_BASIS_INVALID
            no_history(env[5], again.id)
        else:
            behind.result(timeout=15)
            audit = app.get_manuscript_rejection_reconsideration(cmd.project_id, again.id, actor)
            assert not audit.current_coverage_complete
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM approval_decisions WHERE approval_request_id=:id AND decision='REJECT'"
                ),
                {"id": pending.id},
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
@pytest.mark.parametrize("changed", [False, True])
def test_same_uuid_writers_wait_and_replay_or_conflict(b05_env, monkeypatch, purpose, changed):
    env = b05_env
    app, cmd, actor, *_ = correction(env, purpose)
    entered, release = Event(), Event()
    first_pid = []
    original = SqlAlchemyApprovalRepository.lock_scope

    def pause(repo, project, scope):
        original(repo, project, scope)
        if not entered.is_set():
            first_pid.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(12)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_scope", pause)
    other = (
        replace(cmd, rationale=cmd.rationale + " Additional reasoned correction.")
        if changed
        else cmd
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        ahead = pool.submit(app.record_manuscript_rejection_reconsideration, cmd, actor)
        assert entered.wait(5)
        behind = pool.submit(app.record_manuscript_rejection_reconsideration, other, actor)
        try:
            _wait_for_pg_blocker(env[5], first_pid[0], "advisory")
        finally:
            release.set()
        saved = ahead.result(timeout=15)
        if changed:
            with pytest.raises(ResearchBaseError) as denied:
                behind.result(timeout=15)
            assert denied.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
        else:
            assert behind.result(timeout=15) == saved


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_cross_publication_scope_and_corrected_old_review(b05_env, purpose):
    env = b05_env
    app, cmd, actor, approval, old, _, _, fresh_actor = correction(env, purpose)
    other, target_request = other_request(env, approval, purpose)
    fresh = create(
        other,
        principal=fresh_actor,
        summary="The prior review confused the population in frozen evidence; this independent correction explains that specific error.",
    )
    new_cmd = replace(
        cmd,
        manuscript_version_id=target_request.manuscript_version_id,
        fresh_review_ids=(fresh.id,),
    )
    saved = app.record_manuscript_rejection_reconsideration(new_cmd, actor)
    successor = replace(
        target_request, prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    approval.request_approval(env[2], successor)
    rejection = approval.decide_approval(approver(env), decide(successor, "REJECT"))
    newest = create(
        other,
        principal=fresh_actor,
        summary="The fresh evidence confirms the population correction against every rejected request.",
    )
    incomplete = replace(new_cmd, id=uuid4(), fresh_review_ids=(newest.id,))
    with pytest.raises(ResearchBaseError) as denied:
        app.record_manuscript_rejection_reconsideration(incomplete, actor)
    assert denied.value.code == ErrorCode.DECISION_BASIS_INVALID
    complete = replace(
        incomplete,
        rejected_approval_decision_ids=(cmd.rejected_approval_decision_ids[0], rejection.id),
        corrected_review_ids=(*cmd.corrected_review_ids, *target_request.review_ids),
        rationale=cmd.rationale
        + f" Rejection {rejection.id} also relied on review {target_request.review_ids[0]}; the population correction addresses this assessment error.",
    )
    result = app.record_manuscript_rejection_reconsideration(complete, actor)
    assert len(result.rejections) == 2 and result.current_coverage_complete


def other_request(env, approval, purpose):
    from researchbase.application.publication import (
        PublicationService,
        TransitionPublicationReadyCommand,
    )
    from tests.integration.phase2.test_b11_readiness_decision import service as decisions
    from tests.integration.phase2.test_b12_prepare_decision import prepare_command

    other, request = another_target(env)
    if purpose == "PREPARE_SUBMISSION":
        approval.request_approval(env[2], request)
        permission = approval.decide_approval(approver(env), decide(request)).grant
        assert permission is not None
        PublicationService(env[4], env[9], env[7]).transition_publication_ready(
            env[2],
            TransitionPublicationReadyCommand(
                uuid4(),
                request.project_id,
                permission.id,
                other[1].publication_id,
                request.review_ids,
            ),
        )
        basis = decisions(other).record_prepare_submission_decision(env[3], prepare_command(other))
        request = replace(
            request,
            id=uuid4(),
            approval_purpose=purpose,
            basis_decision_id=basis.id,
            review_ids=tuple(r.id for r in basis.basis if r.type == "InternalReviewRecord"),
        )
    return other, request


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
@pytest.mark.parametrize("reject_first", [False, True])
def test_successor_vs_new_rejection_both_commit_orders(b05_env, monkeypatch, purpose, reject_first):
    env = b05_env
    app, cmd, actor, approval, old, _, rejector, fresh_actor = correction(env, purpose)
    saved = app.record_manuscript_rejection_reconsideration(cmd, actor)
    pending = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    approval.request_approval(env[2], pending)
    other, next_request = other_request(env, approval, purpose)
    fresh = create(
        other,
        principal=fresh_actor,
        summary="Independent correction: the earlier review confused the frozen study population with the sample; exact evidence resolves that assessment error.",
    )
    next_cmd = replace(
        cmd,
        id=uuid4(),
        manuscript_version_id=next_request.manuscript_version_id,
        fresh_review_ids=(fresh.id,),
    )
    second = app.record_manuscript_rejection_reconsideration(next_cmd, actor)
    successor = replace(
        next_request, prior_rejected_request_id=old.id, reconsideration_decision_id=second.id
    )
    entered, release = Event(), Event()
    first_pid = []
    original = SqlAlchemyApprovalRepository.lock_snapshot

    def pause(repo, *, deciding=False):
        original(repo, deciding=deciding)
        if deciding == reject_first:
            first_pid.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(12)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_snapshot", pause)

    def request():
        return approval.request_approval(env[2], successor)

    def reject():
        return approval.decide_approval(rejector, decide(pending, "REJECT"))

    first, second_action = (reject, request) if reject_first else (request, reject)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ahead = pool.submit(first)
        assert entered.wait(5)
        behind = pool.submit(second_action)
        try:
            witness = _wait_for_pg_blocker(env[5], first_pid[0], "relation")
            assert witness["relation"] == "publications"
        finally:
            release.set()
        ahead.result(timeout=15)
        with pytest.raises(ResearchBaseError) as denied:
            behind.result(timeout=15)
        assert denied.value.code == (
            ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
            if reject_first
            else ErrorCode.APPROVAL_TARGET_STALE
        )
    with env[5].connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM approval_requests WHERE id=:id"), {"id": successor.id}
        ).scalar_one() == int(not reject_first)
        assert conn.execute(
            text("SELECT count(*) FROM approval_decisions WHERE approval_request_id=:id"),
            {"id": pending.id},
        ).scalar_one() == int(reject_first)


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_late_authorization_loss_rolls_back_complete_candidate_graph(b05_env, monkeypatch, purpose):
    from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository

    env = b05_env
    app, cmd, actor, *_ = correction(env, purpose)
    inserted = []
    original = SqlAlchemyDecisionRepository.insert_manuscript_basis

    def lose_credential(repo, row):
        original(repo, row)
        inserted.append(row["decision_id"])
        env[9].principals.pop(actor.actor_id)

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "insert_manuscript_basis", lose_credential)
    with pytest.raises(ResearchBaseError) as error:
        app.record_manuscript_rejection_reconsideration(cmd, actor)
    assert inserted == [cmd.id] and error.value.code == ErrorCode.FORBIDDEN
    no_history(env[5], cmd.id)
