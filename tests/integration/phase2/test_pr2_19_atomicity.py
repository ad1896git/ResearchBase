"""Finite faults abort one command and preserve committed predecessors."""

from uuid import uuid4

import pytest
from sqlalchemy import event

from researchbase.application.decision import DecisionService
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

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "prefix",
    [
        "INSERT INTO DISCUSSION_SESSIONS",
        "INSERT INTO DISCUSSION_SESSION_QUESTION_INPUTS",
        "INSERT INTO DISCUSSION_COMMAND_RECEIPTS",
    ],
)
def test_discussion_parent_relation_receipt_rollback(pr219_discussion_env, prefix):
    env = pr219_discussion_env
    engine = env[1]
    before = counts(engine)
    fired = []

    def inject(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(prefix):
            fired.append(True)
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "Test-only finite post-write abort")

    event.listen(engine, "after_cursor_execute", inject)
    try:
        with pytest.raises(ResearchBaseError):
            _create(env)
    finally:
        event.remove(engine, "after_cursor_execute", inject)
    assert fired
    assert counts(engine) == before
    result = _create(env)
    assert env[0].read(env[3], env[4], result.session_id).status == "OPEN"


@pytest.mark.parametrize("point", ["basis", "before_commit"])
def test_decision_rollback_keeps_predecessor_review(pr219_decision_env, point):
    env = pr219_decision_env
    if point == "basis":
        cases.test_database_failure_mid_basis_rolls_back_then_same_uuid_recovers(env)
        return
    _, _, actor, _, base = env
    review = cases._review(env)
    before = counts(base[8])

    def factory():
        uow = base[1]()

        def abort():
            raise ResearchBaseError(cases.ErrorCode.VALIDATION_ERROR, "Test-only pre-commit abort")

        uow.commit = abort
        return uow

    with pytest.raises(ResearchBaseError):
        DecisionService(factory, base[9], base[2]).record_decision(actor, cases._command(env))
    assert counts(base[8]) == before
    assert env[1].read(actor, base[5], review.id).id == review.id


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
decision_env = _decision_env
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_decision_env = _pr219_decision_env
pr219_discussion_env = _pr219_discussion_env


def test_review_event_abort_preserves_unreviewed_evidence(pr219_decision_env):
    base = pr219_decision_env[-1]
    service, author, reviewer, project = base[2], base[3], base[4], base[5]
    from uuid import UUID

    evidence = service.create(author, project, base[7], "improved recall", uuid4())
    before = counts(base[8])
    fired = []

    def inject(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO LITERATURE_EVIDENCE_REVIEW_EVENTS"):
            fired.append(True)
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "Test-only event abort")

    event.listen(base[8], "after_cursor_execute", inject)
    try:
        with pytest.raises(ResearchBaseError):
            service.review(
                reviewer,
                project,
                UUID(evidence["id"]),
                "VERIFIED",
                "Independent inspection",
                uuid4(),
            )
    finally:
        event.remove(base[8], "after_cursor_execute", inject)
    assert fired
    assert counts(base[8]) == before
    assert service.get(author, project, UUID(evidence["id"])) == evidence
