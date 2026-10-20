"""Real PostgreSQL terminal disposition and exact scientific basis."""

# SQL literals retain exact role predicates.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b08_support import (
    conclusion_env,
    decision_env,
    disposition_case,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


@pytest.mark.parametrize("dismiss", [False, True])
def test_exact_terminal_transition_and_event_only_projection(revision_env, dismiss):
    service, actor, cmd, base, _ = disposition_case(revision_env, dismiss=dismiss)
    before = service.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert before.status == "OPEN" and len(before.events) == 1
    saved = service.record_issue_disposition(actor, cmd)
    assert saved.new_status == cmd.disposition
    history = service.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert history.events[0] == before.events[0]
    assert history.description == before.description and history.created_at == before.created_at
    assert len(history.events) == 2 and history.status == cmd.disposition
    assert history.disposition == saved
    assert service.get_issue_disposition(actor, base[5], cmd.id) == saved
    assert service.record_issue_disposition(actor, cmd) == saved
    assert (
        service.read(actor, base[5], history.original_review_id).issues[0].status == cmd.disposition
    )


@pytest.mark.parametrize("recommendation", ["REJECT", "UNCERTAIN", "MAJOR_REVISION"])
def test_unfavorable_exact_link_is_history_not_permission(revision_env, recommendation):
    service, actor, cmd, base, _ = disposition_case(revision_env, recommendation=recommendation)
    with pytest.raises(ResearchBaseError) as caught:
        service.record_issue_disposition(actor, cmd)
    assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"


@pytest.mark.parametrize("severity", ["MAJOR", "BLOCKING"])
def test_selected_review_open_concern_denies(revision_env, severity):
    service, actor, cmd, base, _ = disposition_case(
        revision_env, issues=(ReviewIssueRequest(severity, "OTHER", "Still unresolved"),)
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_issue_disposition(actor, cmd)
    assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert len(service.get_issue_history(actor, base[5], cmd.review_issue_id).events) == 1


def test_wrong_actor_changed_payload_and_terminal_new_uuid(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    saved = service.record_issue_disposition(actor, cmd)
    for principal, changed, code in (
        (base[3], cmd, ErrorCode.FORBIDDEN),
        (actor, replace(cmd, rationale="Different"), ErrorCode.IDEMPOTENCY_CONFLICT),
        (actor, replace(cmd, id=uuid4()), ErrorCode.INVALID_STATE_TRANSITION),
    ):
        with pytest.raises(ResearchBaseError) as caught:
            service.record_issue_disposition(principal, changed)
        assert caught.value.code == code
    assert service.get_issue_disposition(actor, base[5], saved.id) == saved


@pytest.mark.parametrize("change", ["decision", "action", "unlinked", "no_change"])
def test_mismatched_basis_denies_atomically(revision_env, change):
    service, actor, cmd, base, _ = disposition_case(revision_env, dismiss=change == "no_change")
    if change == "decision":
        cmd = replace(cmd, decision_id=None)
    elif change == "action":
        cmd = replace(cmd, revision_action_id=uuid4())
    elif change == "unlinked":
        review = service.create(
            actor,
            base[5],
            "SCIENTIFIC_CONCLUSION_VERSION",
            revision_env[4].version_id,
            "SCIENTIFIC",
            "ACCEPT",
            "Unlinked",
            (),
            uuid4(),
        )
        cmd = replace(cmd, re_review_record_id=review.id)
    else:
        cmd = replace(cmd, disposition="ADDRESSED")
    with pytest.raises(ResearchBaseError):
        service.record_issue_disposition(actor, cmd)
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"


@pytest.mark.parametrize(
    "kind",
    ["NEW_EXPERIMENT", "ANALYSIS_CHANGE", "CLAIM_CHANGE", "CONCLUSION_CHANGE", "SOURCE_CHANGE"],
)
def test_all_five_changed_shapes_bind_exact_independent_re_review(revision_env, kind):
    from tests.integration.phase2.b08_support import changed_case

    service, actor, cmd, base, _ = changed_case(revision_env, kind)
    saved = service.record_issue_disposition(actor, cmd)
    assert saved.new_status == "ADDRESSED" and saved.re_review_target_validity == "VALID"
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).disposition == saved


@pytest.mark.parametrize("severity", ["INFO", "MINOR", "MAJOR", "BLOCKING"])
@pytest.mark.parametrize("dismiss", [False, True])
def test_transition_at_each_severity_retains_explicit_decision(revision_env, severity, dismiss):
    revisions, action, env, _, revised = revision_env
    base = env[-1]
    old = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        env[3].version_id,
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "Exact concern",
        (ReviewIssueRequest(severity, "OTHER", "Concern"),),
        uuid4(),
    )
    prepared = (revisions, replace(action, review_issue_id=old.issues[0].id), env, old, revised)
    service, actor, cmd, base, _ = disposition_case(prepared, dismiss=dismiss)
    assert service.record_issue_disposition(actor, cmd).new_status == cmd.disposition


@pytest.mark.parametrize("disposer", ["independent_owner", "opener_reviewer", "material_author"])
def test_disposer_authority_and_independence(revision_env, disposer):
    from sqlalchemy import text

    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_approval import _actor
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, actor, cmd, base, _ = disposition_case(revision_env)
    if disposer == "independent_owner":
        actor = _actor(revision_env[2])
    elif disposer == "opener_reviewer":
        identity, _, _ = identity_service(str(base[8].url))
        identity.assign_project_role(
            AssignProjectRole(
                actor, base[5], actor.actor_id, "REVIEWER", "Original reviewer", uuid4()
            )
        )
        with base[8].connect() as conn:
            role = conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND project_id=:project AND role='OWNER' AND effective_until IS NULL"
                ),
                {"actor": actor.actor_id, "project": base[5]},
            ).scalar_one()
        identity.close_project_role(
            CloseProjectRole(base[3], base[5], role, "Reviewer only", uuid4())
        )
    else:
        with pytest.raises(ResearchBaseError) as caught:
            service.record_issue_disposition(base[3], cmd)
        assert caught.value.code == ErrorCode.CONFLICT_OF_INTEREST
        return
    assert service.record_issue_disposition(actor, cmd).actor_id == actor.actor_id


def test_blocking_issue_only_changed_action_is_insufficient(revision_env):
    from researchbase.application.internal_review import RecordIssueDispositionCommand
    from researchbase.application.revision_action import RecordConcernReReviewCommand

    revisions, action, env, old, revised = revision_env
    base = env[-1]
    saved = revisions.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "Exact response",
        (),
        uuid4(),
    )
    revisions.record_concern_re_review(
        env[2], RecordConcernReReviewCommand(base[5], saved.id, review.id)
    )
    cmd = RecordIssueDispositionCommand(
        uuid4(), base[5], old.issues[0].id, "ADDRESSED", saved.id, review.id, "Attested"
    )
    with pytest.raises(ResearchBaseError) as caught:
        env[1].record_issue_disposition(env[2], cmd)
    assert caught.value.code == ErrorCode.DECISION_BASIS_INVALID


def test_disposition_preserves_other_blockers_and_creates_no_other_governance_records(revision_env):
    from sqlalchemy import text

    from researchbase.application.decision import RecordDecisionCommand
    from tests.integration.phase2.b08_support import current_disposition_case

    service, actor, cmd, base, _ = current_disposition_case(revision_env, dismiss=True)
    other = service.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revision_env[4].version_id,
        "SCIENTIFIC",
        "REJECT",
        "Separate concern",
        (ReviewIssueRequest("BLOCKING", "OTHER", "Still open"),),
        uuid4(),
    )
    tables = (
        "decision_records",
        "revision_actions",
        "internal_review_records",
        "approval_requests",
        "approval_decisions",
        "approval_grants",
    )

    def counts():
        with base[8].connect() as conn:
            return tuple(
                conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() for table in tables
            )

    before = counts()
    service.record_issue_disposition(actor, cmd)
    assert counts() == before
    assert service.get_issue_history(actor, base[5], other.issues[0].id).status == "OPEN"
    with pytest.raises(ResearchBaseError) as caught:
        revision_env[2][0].record_decision(
            actor,
            RecordDecisionCommand(
                uuid4(), base[5], revision_env[4].version_id, "Proceed?", "Other blocker remains"
            ),
        )
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_same_result_link_for_another_action_is_not_correspondence(revision_env):
    from researchbase.application.revision_action import RecordConcernReReviewCommand

    service, actor, cmd, base, action = disposition_case(revision_env)
    other = revision_env[0].record_revision_action(base[3], replace(action, id=uuid4()))
    review = service.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revision_env[4].version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "Same result, another completed response",
        (),
        uuid4(),
    )
    revision_env[0].record_concern_re_review(
        actor, RecordConcernReReviewCommand(base[5], other.id, review.id)
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_issue_disposition(actor, replace(cmd, re_review_record_id=review.id))
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"


def test_new_changed_disposition_denies_invalid_result_in_application_and_sql(revision_env):
    from dataclasses import asdict

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from tests.integration.phase2.revision_support import normal_role
    from tests.integration.phase2.test_pr2_15_decision import _stale

    service, actor, cmd, base, _ = disposition_case(revision_env)
    _stale(revision_env[2])
    with pytest.raises(ResearchBaseError) as caught:
        service.record_issue_disposition(actor, cmd)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with pytest.raises(DBAPIError), normal_role(base[8]) as conn:
        conn.execute(
            text("""INSERT INTO review_issue_events(id,issue_id,actor_id,prior_status,new_status,
          revision_action_id,re_review_record_id,decision_id,rationale,occurred_at)
          VALUES (:id,:review_issue_id,:actor,'OPEN',:disposition,:revision_action_id,:re_review_record_id,:decision_id,:rationale,clock_timestamp())"""),
            {**asdict(cmd), "actor": actor.actor_id},
        )
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"


def test_exact_reads_authenticate_before_absence_and_foreign_scope_disclosure(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    for read, code in (
        (
            lambda: service.get_issue_history(None, base[5], uuid4()),  # type: ignore[arg-type]
            ErrorCode.AUTHENTICATION_REQUIRED,
        ),
        (lambda: service.get_issue_history(actor, base[5], uuid4()), ErrorCode.NOT_FOUND),
        (lambda: service.get_issue_disposition(actor, base[5], uuid4()), ErrorCode.NOT_FOUND),
        (
            lambda: service.get_issue_history(actor, uuid4(), cmd.review_issue_id),
            ErrorCode.FORBIDDEN,
        ),
    ):
        with pytest.raises(ResearchBaseError) as caught:
            read()
        assert caught.value.code == code
