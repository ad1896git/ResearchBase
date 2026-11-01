"""G6/F6 exact manuscript result, independent disposition and new-target permission."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.approval import DecideApprovalCommand, RequestApprovalCommand
from researchbase.application.decision import (
    DecisionService,
    RecordReadyForSubmissionDecisionCommand,
    RecordRevisionDecisionCommand,
)
from researchbase.application.internal_review import (
    RecordIssueDispositionCommand,
    ReviewIssueRequest,
)
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.publication import (
    PublicationService,
    TransitionPublicationInternalReviewCommand,
)
from researchbase.application.revision_action import (
    ConcernReReviewReadback,
    RecordConcernReReviewCommand,
    RecordRevisionActionCommand,
    RevisionActionService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.test_b04_manuscript_freeze import freeze
from tests.integration.phase2.test_b05_manuscript_review import (
    b04_env,
    b05_env,
    conclusion_env,
    create,
    phase2_database_url,
    seal,
)
from tests.integration.phase2.test_b14r_ready_approval import approver
from tests.integration.phase2.test_b14r_ready_approval import service as approvals
from tests.integration.phase2.test_m1_manuscript_revision import successor

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url)
pytestmark = pytest.mark.integration


def test_manuscript_completed_result_keeps_issue_open_until_independent_disposition(b05_env):
    env = b05_env
    reviews, q, author, reviewer, factory, engine, manuscripts, store, _, credentials, _ = env
    v1 = seal(env)
    publication = PublicationService(factory, credentials, store)
    publication.transition_publication_internal_review(
        author,
        TransitionPublicationInternalReviewCommand(
            uuid4(), q.project_id, q.publication_id, q.manuscript_version_id, v1.content_hash
        ),
    )
    with engine.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        retained_v1 = dict(
            conn.execute(
                text("SELECT * FROM manuscript_versions WHERE id=:id"),
                dict(id=q.manuscript_version_id),
            )
            .mappings()
            .one()
        )
    original = create(
        env,
        issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Correct the exact wording"),),
        recommendation="MAJOR_REVISION",
    )
    issue = original.issues[0]
    old_history = reviews.get_issue_history(reviewer, q.project_id, issue.id)
    literature = LiteratureEvidenceService(factory, credentials, store)
    decisions = DecisionService(factory, credentials, literature)
    revisions = RevisionActionService(factory, credentials, literature)
    decision = decisions.record_revision_decision(
        reviewer,
        RecordRevisionDecisionCommand(
            uuid4(), q.project_id, issue.id, "Revise?", "Exact manuscript concern", "REQUIRE_CHANGE"
        ),
    )
    assert decision.manuscript_version_id == v1.manuscript_version_id
    _, _, draft = successor(env)
    result_query = replace(q, manuscript_version_id=draft.id)
    v2 = freeze(manuscripts, author, result_query)
    assert v2.version_number == v1.version_number + 1
    assert v2.publication_id == v1.publication_id == q.publication_id
    command = RecordRevisionActionCommand(
        uuid4(),
        q.project_id,
        "MANUSCRIPT_CHANGE",
        decision_record_id=decision.id,
        result_manuscript_version_id=v2.manuscript_version_id,
    )
    before = counts(engine)
    with pytest.raises(ResearchBaseError) as denied:
        revisions.record_revision_action(
            author, replace(command, result_manuscript_version_id=v1.manuscript_version_id)
        )
    assert denied.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert counts(engine) == before
    assert reviews.get_issue_history(reviewer, q.project_id, issue.id) == old_history

    action = revisions.record_revision_action(author, command)
    assert action.action_type == "MANUSCRIPT_CHANGE" and action.result_validity == "VALID"
    assert action.effective_review_issue_id == issue.id and action.decision_record_id == decision.id
    assert action.result_manuscript_version_id == v2.manuscript_version_id
    assert all(
        getattr(action, field) is None
        for field in (
            "result_experiment_spec_version_id",
            "result_run_id",
            "result_statistical_result_id",
            "result_claim_version_id",
            "result_scientific_conclusion_version_id",
            "result_source_version_id",
        )
    )
    assert reviews.get_issue_history(reviewer, q.project_id, issue.id) == old_history
    fresh_review = create(
        env, target=v2.manuscript_version_id, summary="Independent exact v2 review"
    )
    ready_command = RecordReadyForSubmissionDecisionCommand(
        uuid4(), q.project_id, v2.manuscript_version_id, "Ready?", "Exact revised target"
    )
    before = counts(engine)
    with pytest.raises(ResearchBaseError) as blocked:
        decisions.record_ready_for_submission_decision(reviewer, ready_command)
    assert blocked.value.code is ErrorCode.DECISION_BASIS_INVALID
    assert counts(engine) == before

    assert reviewer.actor_id != author.actor_id
    link = revisions.record_concern_re_review(
        reviewer, RecordConcernReReviewCommand(q.project_id, action.id, fresh_review.id)
    )
    assert isinstance(link, ConcernReReviewReadback)
    assert link.manuscript_version_id == v2.manuscript_version_id
    assert reviews.get_issue_history(reviewer, q.project_id, issue.id) == old_history
    disposition_command = RecordIssueDispositionCommand(
        uuid4(),
        q.project_id,
        issue.id,
        "ADDRESSED",
        action.id,
        fresh_review.id,
        "Exact v2 response resolves the original wording concern",
        decision.id,
    )
    disposition = reviews.record_issue_disposition(reviewer, disposition_command)
    history = reviews.get_issue_history(reviewer, q.project_id, issue.id)
    assert history.status == "ADDRESSED" and history.disposition == disposition
    assert len(history.events) == 2 and history.events[0] == old_history.events[0]
    assert (
        history.original_review_id,
        history.manuscript_version_id,
        history.target_content_hash,
    ) == (
        original.id,
        v1.manuscript_version_id,
        old_history.target_content_hash,
    )
    ready = decisions.record_ready_for_submission_decision(reviewer, ready_command)
    assert ready.manuscript_version_id == v2.manuscript_version_id
    exact_reviews = tuple(r.id for r in ready.basis if r.type == "InternalReviewRecord")
    assert fresh_review.id in exact_reviews and original.id not in exact_reviews
    approval = approvals(env)
    request = approval.request_approval(
        author,
        RequestApprovalCommand(
            uuid4(),
            q.project_id,
            None,
            ready.id,
            exact_reviews,
            approval_purpose="READY_FOR_SUBMISSION",
            manuscript_version_id=v2.manuscript_version_id,
        ),
    )
    independent = approver(env)
    assert independent.actor_id not in {author.actor_id, reviewer.actor_id}
    approved = approval.decide_approval(
        independent,
        DecideApprovalCommand(
            uuid4(), q.project_id, request.id, "APPROVE", "Separate v2 permission"
        ),
    )
    assert approved.grant is not None and approved.grant.usable
    before = counts(engine)
    with sql_protocol(engine) as observed:
        assert manuscripts.get_manuscript_version(reviewer, q) == v1
        assert manuscripts.get_manuscript_version(reviewer, result_query) == v2
        assert decisions.get_revision_decision(reviewer, q.project_id, decision.id) == decision
        assert revisions.read_revision_action(reviewer, q.project_id, action.id) == action
        assert (
            reviews.read(reviewer, q.project_id, original.id).content_hash == original.content_hash
        )
        assert reviews.get_issue_history(reviewer, q.project_id, issue.id) == history
        assert approval.get_grant(author, q.project_id, approved.grant.id) == approved.grant
    assert_snapshot_read(observed)
    assert counts(engine) == before
    with engine.connect() as conn:
        assert (
            dict(
                conn.execute(
                    text("SELECT * FROM manuscript_versions WHERE id=:id"),
                    dict(id=v1.manuscript_version_id),
                )
                .mappings()
                .one()
            )
            == retained_v1
        )
    before = counts(engine)
    with pytest.raises(ResearchBaseError) as duplicate:
        reviews.record_issue_disposition(reviewer, replace(disposition_command, id=uuid4()))
    assert duplicate.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert counts(engine) == before
    assert reviews.get_issue_history(reviewer, q.project_id, issue.id) == history
    print(
        "R01_MANUSCRIPT_SCENARIO",
        dict(
            publication_id=str(q.publication_id),
            original_target=str(v1.manuscript_version_id),
            result_target=str(v2.manuscript_version_id),
            issue_id=str(issue.id),
            action_id=str(action.id),
            disposition_id=str(disposition.id),
            grant_id=str(approved.grant.id),
            original_event_preserved=True,
            completed_action_did_not_dispose=True,
        ),
    )
