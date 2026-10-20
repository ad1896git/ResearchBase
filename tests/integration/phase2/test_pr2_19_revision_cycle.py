"""G6/F6 completed results and independent concern disposition, separate commits."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.internal_review import InternalReviewService
from researchbase.application.revision_action import RevisionActionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.revision_action_repository import REVISION_SNAPSHOT_TABLES
from tests.integration.phase2.b08_support import changed_case, disposition_case
from tests.integration.phase2.b30_observations import (
    assert_first_share,
    assert_snapshot_read,
    sql_protocol,
)
from tests.integration.phase2.pr2_19_support import (
    conclusion_env,
    counts,
    decision_env,
    phase2_database_url,
    revision_env,
)

_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "kind",
    [
        "NEW_EXPERIMENT",
        "ANALYSIS_CHANGE",
        "CLAIM_CHANGE",
        "CONCLUSION_CHANGE",
        "SOURCE_CHANGE",
        "NO_CHANGE",
    ],
)
def test_completed_result_does_not_dispose_until_independent_command(revision_env, kind):
    prepared = (
        disposition_case(revision_env, dismiss=True)
        if kind == "NO_CHANGE"
        else changed_case(revision_env, kind)
    )
    _, actor, cmd, base, action = prepared
    reviews = InternalReviewService(base[1], base[9], base[2])
    revisions = RevisionActionService(base[1], base[9], base[2])
    with sql_protocol(base[8]) as observed:
        old = reviews.get_issue_history(actor, base[5], cmd.review_issue_id)
        saved = revisions.read_revision_action(base[3], base[5], action.id)
    assert_snapshot_read(observed)
    assert old.status == "OPEN" and len(old.events) == 1
    assert saved.action_type == kind and saved.result_validity == (
        None if kind == "NO_CHANGE" else "VALID"
    )
    if kind == "NO_CHANGE":
        assert action.decision_record_id is not None
    with sql_protocol(base[8]) as observed:
        disposition = reviews.record_issue_disposition(actor, cmd)
    assert_first_share(
        observed, "LOCK TABLE " + ",".join(REVISION_SNAPSHOT_TABLES) + " IN SHARE MODE"
    )
    fresh = InternalReviewService(base[1], base[9], base[2])
    with sql_protocol(base[8]) as observed:
        history = fresh.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert_snapshot_read(observed)
    assert history.status == cmd.disposition and history.disposition == disposition
    assert history.events[0] == old.events[0] and len(history.events) == 2
    assert (history.description, history.created_at, history.original_review_id) == (
        old.description,
        old.created_at,
        old.original_review_id,
    )
    assert (
        revisions.read_revision_action(base[3], base[5], action.id).content_hash
        == saved.content_hash
    )
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        fresh.record_issue_disposition(actor, replace(cmd, id=uuid4()))
    assert denied.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert counts(base[8]) == before
    assert fresh.get_issue_history(actor, base[5], cmd.review_issue_id) == history


@pytest.mark.parametrize(
    "change,code",
    [
        ("old_result", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("wrong_project", ErrorCode.FORBIDDEN),
    ],
)
def test_wrong_result_cannot_resolve_original_concern(revision_env, change, code):
    service, command, env, review, _ = revision_env
    base = env[-1]
    command = (
        replace(command, result_scientific_conclusion_version_id=env[3].version_id)
        if change == "old_result"
        else replace(command, project_id=uuid4())
    )
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        service.record_revision_action(base[3], command)
    assert denied.value.code is code
    assert counts(base[8]) == before
    history = InternalReviewService(base[1], base[9], base[2]).get_issue_history(
        env[2], base[5], review.issues[0].id
    )
    assert history.status == "OPEN" and len(history.events) == 1


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("old_run", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("wrong_spec", ErrorCode.NOT_FOUND),
        ("planned", ErrorCode.FROZEN_REFERENCE_REQUIRED),
    ],
)
def test_completed_experiment_requires_exact_spec_run_pair(revision_env, mutation, code):
    from sqlalchemy import text

    from researchbase.application.commands import CreateRunCommand
    from researchbase.application.revision_action import RecordRevisionActionCommand
    from researchbase.domain.organization import ProjectId
    from tests.integration.phase2.test_b06_revision_action import _app, _context, _measurement, _run

    revisions, old, env, review, _ = revision_env
    base = env[-1]
    spec, run = _run(base)
    if mutation == "old_run":
        with base[8].connect() as conn:
            run = conn.execute(
                text("SELECT run_id FROM measurements WHERE id=:id"), {"id": _measurement(base)}
            ).scalar_one()
    elif mutation == "wrong_spec":
        spec = uuid4()
    else:
        run = (
            _app(base)
            .create_run(CreateRunCommand(ProjectId(base[5]), spec, None, _context(base)))
            .id
        )
    cmd = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "NEW_EXPERIMENT",
        old.review_issue_id,
        result_experiment_spec_version_id=spec,
        result_run_id=run,
    )
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        revisions.record_revision_action(base[3], cmd)
    assert denied.value.code is code
    assert counts(base[8]) == before
    assert env[1].get_issue_history(env[2], base[5], review.issues[0].id).status == "OPEN"


@pytest.mark.parametrize("kind", ["CONCLUSION_CHANGE", "CLAIM_CHANGE"])
def test_conclusion_cycle_new_target_proceed_request_decision_grant(revision_env, kind):
    from researchbase.application.approval import ApprovalService, RequestApprovalCommand
    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_approval import _actor, _decide
    from tests.integration.phase2.test_pr2_00_challenges import _service
    from tests.integration.phase2.test_pr2_15_decision import _command

    _, _, env, _, target = revision_env
    base = env[-1]
    old_exact = base[0].read(base[3], base[5], env[3].conclusion_id, env[3].version_id)
    _, actor, cmd, base, action = changed_case(revision_env, kind)
    fresh_reviews = InternalReviewService(base[1], base[9], base[2])
    old_history = fresh_reviews.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert old_history.status == "OPEN"
    fresh_reviews.record_issue_disposition(actor, cmd)
    review_id = cmd.re_review_record_id
    if kind == "CLAIM_CHANGE":
        from researchbase.application.scientific_conclusion import ClaimInputRequest
        from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
        from tests.integration.phase2.test_pr2_15_decision import _review

        assert action.result_claim_version_id is not None
        target = base[0].create(
            base[3],
            base[5],
            "Conclusion from corrected Claim",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(action.result_claim_version_id, "SUPPORTS"),),
            (),
            uuid4(),
        )
        base[0].freeze(base[3], base[5], target.conclusion_id, target.version_id, uuid4())
        updated = (env[0], env[1], env[2], target, base)
        review_id = _review(updated).id
    updated_env = (env[0], env[1], env[2], target, base)
    basis = env[0].record_decision(actor, _command(updated_env))
    requester, approver = _actor(env), _actor(env)
    identity, _, _ = _service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(
            actor, base[5], approver.actor_id, "APPROVER", "Independent cycle approver", uuid4()
        )
    )
    approvals = ApprovalService(base[1], base[9], base[2])
    request = RequestApprovalCommand(uuid4(), base[5], target.version_id, basis.id, (review_id,))
    approvals.request_approval(requester, request)
    approved = approvals.decide_approval(approver, _decide(request))
    assert approved.grant is not None and approved.grant.usable
    fresh = ApprovalService(base[1], base[9], base[2])
    assert fresh.get_grant(requester, base[5], approved.grant.id) == approved.grant
    history = fresh_reviews.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert history.events[0] == old_history.events[0] and history.status == "ADDRESSED"
    retained = base[0].read(base[3], base[5], env[3].conclusion_id, env[3].version_id)
    assert retained.content_hash == old_exact.content_hash
    assert retained.support_set_hash == old_exact.support_set_hash
    assert retained.status == old_exact.status


@pytest.mark.parametrize("frozen", [False, True])
def test_draft_or_unrelated_conclusion_does_not_resolve_issue(revision_env, frozen):
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, cmd, env, review, _ = revision_env
    base = env[-1]
    unrelated = base[0].create(
        base[3],
        base[5],
        "Unrelated conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(base[6], "SUPPORTS"),),
        (),
        uuid4(),
    )
    if frozen:
        base[0].freeze(base[3], base[5], unrelated.conclusion_id, unrelated.version_id, uuid4())
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        service.record_revision_action(
            base[3], replace(cmd, result_scientific_conclusion_version_id=unrelated.version_id)
        )
    assert denied.value.code is (
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION if frozen else ErrorCode.FROZEN_REFERENCE_REQUIRED
    )
    assert counts(base[8]) == before
    assert env[1].get_issue_history(env[2], base[5], review.issues[0].id).status == "OPEN"


def test_revision_successor_cannot_fork_saved_history(revision_env):
    service, cmd, env, review, _ = revision_env
    base = env[-1]
    first = service.record_revision_action(base[3], cmd)
    successor = service.record_revision_action(
        base[3], replace(cmd, id=uuid4(), supersedes_revision_action_id=first.id)
    )
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        service.record_revision_action(
            base[3], replace(cmd, id=uuid4(), supersedes_revision_action_id=first.id)
        )
    assert denied.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert counts(base[8]) == before
    reader = RevisionActionService(base[1], base[9], base[2])
    assert (
        reader.read_revision_action(base[3], base[5], successor.id).content_hash
        == successor.content_hash
    )
    assert env[1].get_issue_history(env[2], base[5], review.issues[0].id).status == "OPEN"
