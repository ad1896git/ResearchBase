"""F8 separates aborted attempts from committed lost acknowledgements."""

from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.decision import DecisionService
from researchbase.application.discussion import DiscussionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import test_pr2_15_decision as cases
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.pr2_19_support import decision_env as _decision_env
from tests.integration.phase2.pr2_19_support import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.pr2_19_support import discussion_env as _discussion_env
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_decision_env as _pr219_decision_env
from tests.integration.phase2.pr2_19_support import pr219_discussion_env as _pr219_discussion_env
from tests.integration.phase2.test_pr2_10_discussion_persistence import _create
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    test_replay_concurrency_and_conflict as discussion_replay,
)

pytestmark = pytest.mark.integration


def test_decision_same_uuid_concurrent_changed_material_restart(pr219_decision_env):
    cases.test_uuid_conflict_new_uuid_and_concurrent_duplicates(pr219_decision_env)


def test_decision_lost_response(pr219_decision_env):
    cases.test_commit_uncertainty_recovers_by_exact_uuid_without_duplicate_history(
        pr219_decision_env
    )


def test_historical_replay_after_staleness(pr219_decision_env):
    cases.test_stale_saved_replay_survives_but_unknown_uuid_denies(pr219_decision_env)


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_three_whole_attempts_then_exact_recovery(pr219_decision_env, sqlstate, monkeypatch):
    env = pr219_decision_env
    service, _, actor, _, base = env
    cases._review(env)
    request = cases._command(env)
    identities = []
    fresh_reads = []
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository

    original_reviews = SqlAlchemyApprovalRepository.target_reviews

    def reviews(self, *args):
        result = original_reviews(self, *args)
        fresh_reads.append(
            (
                self._session.execute(text("SELECT txid_current()")).scalar_one(),
                tuple(row["id"] for row in result),
            )
        )
        return result

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "target_reviews", reviews)

    def inject(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO DECISION_BASIS_REVIEWS"):
            identities.append(conn.execute(text("SELECT txid_current()")).scalar_one())
            conn.execute(
                text(
                    "DO $$ BEGIN RAISE EXCEPTION 'PR219 transient' "
                    f"USING ERRCODE='{sqlstate}'; END $$"
                )
            )

    event.listen(base[8], "before_cursor_execute", inject)
    try:
        with pytest.raises(ResearchBaseError) as denied:
            service.record_decision(actor, request)
        assert denied.value.code is ErrorCode.CONCURRENT_MODIFICATION
    finally:
        event.remove(base[8], "before_cursor_execute", inject)
    assert len(identities) == len(set(identities)) == 3
    assert [row[0] for row in fresh_reads] == identities
    assert all(len(row[1]) == 1 for row in fresh_reads)
    assert cases._counts(base[8]) == (0, 0, 0)
    fresh = DecisionService(base[1], base[9], base[2])
    result = fresh.record_decision(actor, request)
    assert fresh.record_decision(actor, request) == result
    assert cases._counts(base[8]) == (1, 1, 1)


def test_permanent_denial_is_not_retried(pr219_decision_env):
    env = pr219_decision_env
    service, _, actor, _, base = env
    attempts = []

    def factory():
        attempts.append(True)
        return base[1]()

    from researchbase.persistence.approval_repository import B09_SHARE_SQL

    write_attempts = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement == B09_SHARE_SQL:
            write_attempts.append(True)

    before = counts(base[8])
    event.listen(base[8], "before_cursor_execute", capture)
    try:
        with pytest.raises(ResearchBaseError) as denied:
            DecisionService(factory, base[9], base[2]).record_decision(actor, cases._command(env))
    finally:
        event.remove(base[8], "before_cursor_execute", capture)
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    # One lock-free historical replay preflight and one write, with no retry.
    assert len(attempts) == 2
    assert len(write_attempts) == 1
    assert counts(base[8]) == before


def test_discussion_concurrent_exact_uuid_and_changed_material(pr219_discussion_env):
    discussion_replay(pr219_discussion_env)


def test_discussion_committed_lost_response_replays_without_extra_turn(pr219_discussion_env):
    env = pr219_discussion_env
    original, engine, credentials, actor, project, _, source = env
    session = _create(env).session_id
    request = uuid4()

    def factory():
        uow = original._factory()
        commit = uow.commit

        def lost():
            commit()
            raise RuntimeError("TEST ONLY lost response")

        uow.commit = lost
        return uow

    with pytest.raises(RuntimeError, match="lost response"):
        DiscussionService(factory, credentials).append(
            actor, project, session, "human", "Exact turn", (source,), (), request
        )
    assert counts(engine)["discussion_turns"] == 1
    fresh = DiscussionService(original._factory, credentials)
    saved = fresh.append(actor, project, session, "human", "Exact turn", (source,), (), request)
    assert (
        fresh.append(actor, project, session, "human", "Exact turn", (source,), (), request)
        == saved
    )
    assert len(fresh.read(actor, project, session).turns) == 1
    assert counts(engine)["discussion_turns"] == 1


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
decision_env = _decision_env
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_decision_env = _pr219_decision_env
pr219_discussion_env = _pr219_discussion_env


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_discussion_three_fresh_attempts_exhaust_then_replay(pr219_discussion_env, sqlstate):
    env = pr219_discussion_env
    before = counts(env[1])
    transactions, authority_reads = [], []
    request = uuid4()

    def inject(conn, cursor, statement, parameters, context, executemany):
        normalized = statement.lstrip().upper()
        if "FOR UPDATE OF A,M,R,B" in normalized:
            authority_reads.append(conn.execute(text("SELECT txid_current()")).scalar_one())
        if normalized.startswith("INSERT INTO DISCUSSION_SESSIONS"):
            transactions.append(conn.execute(text("SELECT txid_current()")).scalar_one())
            conn.execute(text(f"DO $$ BEGIN RAISE SQLSTATE '{sqlstate}'; END $$"))

    event.listen(env[1], "before_cursor_execute", inject)
    try:
        with pytest.raises(ResearchBaseError) as denied:
            _create(env, request)
        assert denied.value.code is ErrorCode.CONCURRENT_MODIFICATION
    finally:
        event.remove(env[1], "before_cursor_execute", inject)
    assert len(transactions) == len(set(transactions)) == 3
    assert authority_reads == transactions
    assert counts(env[1]) == before
    saved = _create(env, request)
    assert _create(env, request) == saved
    assert counts(env[1])["discussion_sessions"] == before["discussion_sessions"] + 1
