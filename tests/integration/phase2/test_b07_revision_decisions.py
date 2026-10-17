"""B07 exact revision choices over disposable PostgreSQL history."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.decision import RecordRevisionDecisionCommand
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.revision_action import RecordRevisionActionCommand
from researchbase.domain.decision import RevisionChoice
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


def decision_command(env, issue, choice: RevisionChoice = "REQUIRE_CHANGE"):
    return RecordRevisionDecisionCommand(
        uuid4(), env[-1][5], issue, "Respond?", "Exact concern", choice
    )


@pytest.mark.parametrize("choice", ["REQUIRE_CHANGE", "ACCEPT_NO_CHANGE"])
@pytest.mark.parametrize("target", ["claim", "conclusion"])
def test_revision_decision_complete_adverse_snapshot_and_exact_concern(
    decision_env, choice, target
):
    env = decision_env
    base = env[-1]
    target_id = base[6] if target == "claim" else env[3].version_id
    kind = "CLAIM_VERSION" if target == "claim" else "SCIENTIFIC_CONCLUSION_VERSION"
    reviews = []
    for rec in ("REJECT", "UNCERTAIN", "ACCEPT"):
        reviews.append(
            env[1].create(
                env[2],
                base[5],
                kind,
                target_id,
                "SCIENTIFIC",
                rec,
                "Independent",
                (
                    ReviewIssueRequest("BLOCKING", "OTHER", "One"),
                    ReviewIssueRequest("MAJOR", "OTHER", "Two"),
                ),
                uuid4(),
            )
        )
    cmd = decision_command(env, reviews[0].issues[1].id, choice)
    result = env[0].record_revision_decision(env[2], cmd)
    assert result.review_issue_id == reviews[0].issues[1].id
    assert {r.id for r in result.basis if r.type == "InternalReviewRecord"} == {
        r.id for r in reviews
    }
    assert env[0].record_revision_decision(env[2], cmd) == result
    assert env[0].get_revision_decision(env[2], base[5], cmd.id) == result
    with pytest.raises(ResearchBaseError) as caught:
        env[0].record_revision_decision(env[2], replace(cmd, id=uuid4()))
    assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with base[8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 6
        assert (
            conn.execute(
                text("SELECT count(*) FROM review_issues WHERE status='OPEN'")
            ).scalar_one()
            == 6
        )


@pytest.mark.parametrize("basis", ["issue", "decision", "combined"])
@pytest.mark.parametrize(
    "shape",
    ["NEW_EXPERIMENT", "ANALYSIS_CHANGE", "CLAIM_CHANGE", "CONCLUSION_CHANGE", "SOURCE_CHANGE"],
)
def test_changed_action_three_exact_basis_forms(revision_env, basis, shape):
    service, action, env, _, _ = revision_env
    base = env[-1]
    from tests.integration.phase2.test_b06_revision_action import (
        _analysis,
        _claim_successor,
        _run,
        _source_response,
    )

    if shape == "SOURCE_CHANGE":
        action = _source_response(env, "conclusion", "CORRECTED")
    elif shape != "CONCLUSION_CHANGE":
        if shape == "NEW_EXPERIMENT":
            spec, run = _run(base)
            values = dict(result_experiment_spec_version_id=spec, result_run_id=run)
        elif shape == "ANALYSIS_CHANGE":
            values = dict(result_statistical_result_id=_analysis(base))
        else:
            values = dict(result_claim_version_id=_claim_successor(base))
        action = RecordRevisionActionCommand(
            uuid4(), base[5], shape, action.review_issue_id, **values
        )
    cmd = decision_command(env, action.review_issue_id)
    decision = env[0].record_revision_decision(env[2], cmd)
    action = replace(
        action,
        decision_record_id=decision.id if basis != "issue" else None,
        review_issue_id=action.review_issue_id if basis != "decision" else None,
    )
    result = service.record_revision_action(base[3], action)
    assert result.effective_review_issue_id == cmd.review_issue_id
    assert result.review_issue_id == action.review_issue_id
    assert service.read_revision_action(base[3], base[5], action.id) == result
    concern = service.get_concern_carry_forward(base[3], base[5], cmd.review_issue_id)
    assert concern.actions[0].action == result
    assert concern.actions[0].mapping_state == "PENDING_RE_REVIEW"


@pytest.mark.parametrize("combined", [False, True])
def test_no_change_has_no_result_or_disposition(revision_env, combined):
    service, action, env, _, _ = revision_env
    base = env[-1]
    decision = env[0].record_revision_decision(
        env[2], decision_command(env, action.review_issue_id, "ACCEPT_NO_CHANGE")
    )
    cmd = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "NO_CHANGE",
        review_issue_id=action.review_issue_id if combined else None,
        decision_record_id=decision.id,
    )
    result = service.record_revision_action(base[3], cmd)
    assert result.result_validity is None
    assert result.target_validity == "VALID"
    assert service.record_revision_action(base[3], cmd) == result
    with base[8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"),
                {"id": action.review_issue_id},
            ).scalar_one()
            == "OPEN"
        )
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1


@pytest.mark.parametrize("case", ["issue_only", "wrong_choice", "different_issue", "author"])
def test_ineligible_revision_basis_denies(revision_env, case):
    service, action, env, _, _ = revision_env
    base = env[-1]
    cmd = decision_command(env, action.review_issue_id)
    if case == "author":
        with pytest.raises(ResearchBaseError) as caught:
            env[0].record_revision_decision(base[3], cmd)
        assert caught.value.code == ErrorCode.CONFLICT_OF_INTEREST
        return
    d = env[0].record_revision_decision(env[2], cmd)
    if case == "issue_only":
        bad = RecordRevisionActionCommand(
            uuid4(), base[5], "NO_CHANGE", review_issue_id=action.review_issue_id
        )
    elif case == "wrong_choice":
        bad = RecordRevisionActionCommand(uuid4(), base[5], "NO_CHANGE", decision_record_id=d.id)
    else:
        other = env[1].create(
            env[2],
            base[5],
            "SCIENTIFIC_CONCLUSION_VERSION",
            env[3].version_id,
            "SCIENTIFIC",
            "REJECT",
            "Another concern",
            (ReviewIssueRequest("MAJOR", "OTHER", "Separate"),),
            uuid4(),
        )
        bad = replace(action, decision_record_id=d.id, review_issue_id=other.issues[0].id)
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], bad)
    assert caught.value.code == ErrorCode.DECISION_BASIS_INVALID


def test_release_proceed_is_never_no_change_basis(decision_env):
    from researchbase.application.revision_action import RevisionActionService
    from tests.integration.phase2.test_pr2_15_decision import _command, _review

    env = decision_env
    base = env[-1]
    _review(env)
    release = env[0].record_decision(env[2], _command(env))
    with pytest.raises(ResearchBaseError) as caught:
        RevisionActionService(base[1], base[-1], base[2]).record_revision_action(
            base[3],
            RecordRevisionActionCommand(
                uuid4(), base[5], "NO_CHANGE", decision_record_id=release.id
            ),
        )
    assert caught.value.code == ErrorCode.DECISION_BASIS_INVALID


def test_revision_response_is_never_approval_basis(decision_env):
    from researchbase.application.approval import ApprovalService, RequestApprovalCommand
    from tests.integration.phase2.test_approval import _actor
    from tests.integration.phase2.test_pr2_15_decision import _review

    env = decision_env
    base = env[-1]
    review = _review(env, "ACCEPT", (ReviewIssueRequest("MAJOR", "OTHER", "Exact concern"),))
    decision = env[0].record_revision_decision(env[2], decision_command(env, review.issues[0].id))
    requester = _actor(env)
    service = ApprovalService(base[1], base[-1], base[2])
    with pytest.raises(ResearchBaseError) as caught:
        service.request_approval(
            requester,
            RequestApprovalCommand(uuid4(), base[5], env[3].version_id, decision.id, (review.id,)),
        )
    assert caught.value.code == ErrorCode.DECISION_BASIS_INVALID


@pytest.mark.parametrize("foreign", [False, True])
def test_action_decision_reference_preserves_scope_and_absence_errors(revision_env, foreign):
    from researchbase.application.commands import CreateProjectCommand
    from tests.integration.phase2.pr2_18_fixtures import _add_member
    from tests.integration.phase2.test_b06_revision_action import _app, _context

    service, action, env, _, _ = revision_env
    base = env[-1]
    decision_id = uuid4()
    project = base[5]
    if foreign:
        decision_id = (
            env[0]
            .record_revision_decision(env[2], decision_command(env, action.review_issue_id))
            .id
        )
        project = (
            _app(base)
            .create_project(CreateProjectCommand("TEST ONLY other scope", None, _context(base)))
            .id
        )
        with base[8].begin() as conn:
            _add_member(
                conn,
                actor_id=base[3].actor_id,
                project_id=project,
                now=conn.execute(text("SELECT clock_timestamp()")).scalar_one(),
                event_kind="ACTIVATED",
                request_id=uuid4(),
                create_actor=False,
            )
    command = RecordRevisionActionCommand(
        uuid4(), project, "NO_CHANGE", decision_record_id=decision_id
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], command)
    assert caught.value.code == (ErrorCode.FORBIDDEN if foreign else ErrorCode.NOT_FOUND)
    with base[8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0


@pytest.mark.parametrize("kind", ["decision", "action", "link"])
def test_exact_read_graph_including_re_reviews_acquires_no_row_locks(revision_env, kind):
    from sqlalchemy import event

    from tests.integration.phase2.test_b07_concurrency import prepared

    write, read = prepared(revision_env, kind)
    write()
    engine = revision_env[2][-1][8]
    statements = []
    observed = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
        assert conn.get_isolation_level() == "REPEATABLE READ"
        # Inspect the actual read backend after authorization and every graph
        # query. A separate observer does not alter the read transaction itself.
        with observer_engine.connect() as observer:
            observed.extend(
                observer.execute(
                    text(
                        "SELECT locktype,mode FROM pg_locks WHERE pid=:pid "
                        "AND mode<>'SIReadLock' AND "
                        "(locktype IN ('tuple','advisory') OR "
                        "mode NOT IN ('AccessShareLock','ExclusiveLock'))"
                    ),
                    {"pid": conn.connection.driver_connection.info.backend_pid},
                ).all()
            )

    from sqlalchemy import create_engine

    observer_engine = create_engine(engine.url)
    event.listen(engine, "after_cursor_execute", capture)
    try:
        assert read()
        assert statements and not observed
        assert not any(
            token in statement.upper()
            for statement in statements
            for token in (
                "LOCK TABLE",
                "FOR UPDATE",
                "FOR SHARE",
                "FOR KEY SHARE",
                "FOR NO KEY UPDATE",
                "PG_ADVISORY",
                "B07_VALIDATE_",
            )
        )
    finally:
        event.remove(engine, "after_cursor_execute", capture)
        observer_engine.dispose()
