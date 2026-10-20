"""B23 request identity and historical authority are independent of admission."""

from collections.abc import Callable
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.application.revision_action import (
    RecordNoveltyRevisionCommand,
    RevisionActionService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b23_novelty_review import _review, _root


def test_review_order_conflicts_and_author_denial(novelty_env):
    e = novelty_env
    _, root = _root(e)
    request = uuid4()
    issues = (
        ReviewIssueRequest("MINOR", "NOVELTY", "One"),
        ReviewIssueRequest("MAJOR", "OTHER", "Two"),
    )
    service, view = _review(e, root, request, issues)
    with pytest.raises(ResearchBaseError) as error:
        _review(e, root, request, tuple(reversed(issues)))
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as error:
        service.create(
            e["author"],
            e["project"],
            "NOVELTY_ASSESSMENT",
            root.id,
            "LITERATURE",
            "ACCEPT",
            "Author review",
            (),
            uuid4(),
        )
    assert error.value.code is ErrorCode.CONFLICT_OF_INTEREST
    restarted = InternalReviewService(e["factory"], e["credentials"], e["literature"])
    assert restarted.read(e["reviewer"], e["project"], view.id).content_hash == view.content_hash


def test_action_replay_after_supersession(novelty_env):
    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    service = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    command = RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result.id)
    action = service.record_novelty_revision(e["author"], command)
    e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=result.id)
    )
    replay = service.record_novelty_revision(e["author"], command)
    assert replay.content_hash == action.content_hash
    assert replay.result.superseded_by_assessment_id is not None
    with pytest.raises(ResearchBaseError) as error:
        service.record_novelty_revision(
            e["author"], replace(command, result_novelty_assessment_id=root.id)
        )
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 1


@pytest.mark.parametrize(
    "corruption",
    [
        "issue_time",
        "target_locator",
        "related_claim_version_id",
        "related_source_version_id",
        "related_run_id",
        "event_edge",
        "review_hash",
        "target_hash",
        "unknown_version",
    ],
)
def test_saved_review_corruption_denies_read_and_replay(novelty_env, monkeypatch, corruption):
    from datetime import timedelta

    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )

    e = novelty_env
    _, root = _root(e)
    request = uuid4()
    service, saved = _review(e, root, request)
    issues = SqlAlchemyInternalReviewRepository.issues
    events = SqlAlchemyInternalReviewRepository.issue_events
    review = SqlAlchemyInternalReviewRepository.review

    def broken_issues(repo, identity):
        rows = issues(repo, identity)
        if identity == saved.id:
            for row in rows:
                if corruption == "issue_time":
                    row["created_at"] += timedelta(microseconds=1)
                elif corruption in {
                    "target_locator",
                    "related_claim_version_id",
                    "related_source_version_id",
                    "related_run_id",
                }:
                    row[corruption] = "hidden" if corruption == "target_locator" else uuid4()
        return rows

    def broken_events(repo, identity):
        rows = events(repo, identity)
        if identity == saved.id:
            for row in rows:
                if corruption == "issue_time":
                    row["occurred_at"] += timedelta(microseconds=1)
                if corruption == "event_edge":
                    row["revision_action_id"] = uuid4()
        return rows

    def broken_review(repo, identity, project):
        row = review(repo, identity, project)
        if row is not None and identity == saved.id:
            key = {
                "review_hash": "content_hash",
                "target_hash": "target_content_hash",
                "unknown_version": "material_version",
            }.get(corruption)
            if key:
                row[key] = 99 if key == "material_version" else "f" * 64
        return row

    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "issues", broken_issues)
    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "issue_events", broken_events)
    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "review", broken_review)
    for operation in (
        lambda: service.read(e["reviewer"], e["project"], saved.id),
        lambda: _review(e, root, request),
    ):
        with pytest.raises(ResearchBaseError) as error:
            operation()
        assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1


def test_restart_replays_after_writer_role_loss_and_live_credential_denial(novelty_env):
    from datetime import UTC, datetime

    from researchbase.application.revision_action import RecordConcernReReviewCommand

    e = novelty_env
    c, root = _root(e)
    request = uuid4()
    reviews, original = _review(e, root, request)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], original.issues[0].id, result.id)
    action = actions.record_novelty_revision(e["researcher"], cmd)
    _, new_review = _review(e, result, issues=())
    link_cmd = RecordConcernReReviewCommand(e["project"], action.id, new_review.id)
    link = actions.record_concern_re_review(e["reviewer"], link_cmd, novelty=True)
    # Keep live membership/read entitlement, close only writer roles at a later instant.
    with e["engine"].begin() as conn:
        for actor, role in ((e["reviewer"], "REVIEWER"), (e["researcher"], "RESEARCHER")):
            at = datetime.now(UTC)
            role_id = conn.execute(
                text(
                    """UPDATE project_role_assignments
 SET effective_until=:at,row_version=row_version+1
 WHERE actor_id=:actor AND role=:role
 RETURNING id"""
                ),
                {"at": at, "actor": actor.actor_id, "role": role},
            ).scalar_one()
            conn.execute(
                text(
                    """INSERT INTO project_role_events(id,role_assignment_id,actor_id,
event_kind,occurred_at,reason,request_id)
 VALUES (:id,:role,:actor,'CLOSED',:at,'Test role loss',:request)"""
                ),
                {
                    "id": uuid4(),
                    "role": role_id,
                    "actor": actor.actor_id,
                    "at": at,
                    "request": uuid4(),
                },
            )
            viewer_id = uuid4()
            conn.execute(
                text(
                    """INSERT INTO project_role_assignments(id,membership_id,project_id,
actor_id,role,effective_from,
assigned_by,created_at,row_version)
 SELECT :id,membership_id,project_id,actor_id,'VIEWER',:at,actor_id,:at,1
 FROM project_role_assignments
 WHERE id=:prior"""
                ),
                {"id": viewer_id, "at": at, "prior": role_id},
            )
            conn.execute(
                text(
                    """INSERT INTO project_role_events(id,role_assignment_id,actor_id,
event_kind,occurred_at,reason,request_id)
 VALUES (:id,:role,:actor,'ASSIGNED',:at,'Read entitlement retained',:request)"""
                ),
                {
                    "id": uuid4(),
                    "role": viewer_id,
                    "actor": actor.actor_id,
                    "at": at,
                    "request": uuid4(),
                },
            )
    restarted = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    assert (
        restarted.record_novelty_revision(e["researcher"], cmd).content_hash == action.content_hash
    )
    assert (
        restarted.record_concern_re_review(e["reviewer"], link_cmd, novelty=True).recorded_at
        == link.recorded_at
    )
    assert _review(e, root, request)[1].content_hash == original.content_hash
    assert restarted.read_revision_action(e["viewer"], e["project"], action.id).id == action.id
    assert (
        restarted.read_novelty_re_review(
            e["viewer"], e["project"], action.id, new_review.id
        ).review.id
        == new_review.id
    )

    # Live credentials remain required for all three exact historical reads.
    e["credentials"].enabled = False
    for operation in (
        lambda: reviews.read(e["reviewer"], e["project"], original.id),
        lambda: restarted.read_revision_action(e["researcher"], e["project"], action.id),
        lambda: restarted.read_novelty_re_review(
            e["reviewer"], e["project"], action.id, new_review.id
        ),
    ):
        with pytest.raises(ResearchBaseError) as error:
            operation()
        assert error.value.code is ErrorCode.FORBIDDEN


def test_unavailable_selected_source_denies_whole_review(novelty_env, monkeypatch):
    from tests.integration.phase2.b19_basis_support import record, setup

    e = novelty_env
    cmd, _, _, _ = setup(e)
    root = record(e, cmd)
    service, review = _review(e, root)

    def unavailable(*args, **kwargs):
        raise ResearchBaseError(ErrorCode.FORBIDDEN, "nested document unavailable")

    monkeypatch.setattr(e["literature"], "_source", unavailable)
    with pytest.raises(ResearchBaseError) as error:
        service.read(e["reviewer"], e["project"], review.id)
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def _completed_history(e):
    from researchbase.application.revision_action import RecordConcernReReviewCommand

    c, root = _root(e)
    reviews, original = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], original.issues[0].id, result.id)
    action = actions.record_novelty_revision(e["researcher"], cmd)
    _, review = _review(e, result, issues=())
    pair = RecordConcernReReviewCommand(e["project"], action.id, review.id)
    actions.record_concern_re_review(e["reviewer"], pair, novelty=True)
    return root, reviews, original, actions, cmd, action, review, pair


def test_foreign_scope_and_actor_replay_deny_without_disclosure(novelty_env):
    e = novelty_env
    root, reviews, original, actions, cmd, action, review, pair = _completed_history(e)
    for call in (
        lambda: reviews.read(e["reviewer"], e["other_project"], original.id),
        lambda: reviews.create(
            e["reviewer"],
            e["other_project"],
            "NOVELTY_ASSESSMENT",
            root.id,
            "LITERATURE",
            "UNCERTAIN",
            "Foreign scope",
            (),
            uuid4(),
        ),
        lambda: actions.read_revision_action(e["reviewer"], e["other_project"], action.id),
        lambda: actions.record_novelty_revision(e["owner"], cmd),
        lambda: actions.record_novelty_revision(
            e["researcher"], replace(cmd, project_id=e["other_project"])
        ),
        lambda: actions.record_concern_re_review(e["owner"], pair, novelty=True),
        lambda: actions.read_novelty_re_review(
            e["reviewer"], e["other_project"], action.id, review.id
        ),
    ):
        with pytest.raises(ResearchBaseError) as error:
            call()
        assert error.value.code is ErrorCode.FORBIDDEN
        assert str(root.id) not in error.value.message
    with pytest.raises(ResearchBaseError) as error:
        actions.record_novelty_revision(
            e["researcher"], replace(cmd, supersedes_revision_action_id=uuid4())
        )
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM revision_action_re_reviews")).scalar_one() == 1
        )


@pytest.mark.parametrize(
    "corruption", ["action_hash", "action_version", "result_edge", "link_author"]
)
def test_saved_action_and_link_corruption_denies_reads_and_replay(
    novelty_env, monkeypatch, corruption
):
    from researchbase.persistence.revision_action_repository import (
        SqlAlchemyRevisionActionRepository,
    )

    e = novelty_env
    root, _, _, actions, cmd, action, review, pair = _completed_history(e)
    original_action = SqlAlchemyRevisionActionRepository.action
    original_link = SqlAlchemyRevisionActionRepository.link

    def corrupt_action(repo, identity, project):
        row = original_action(repo, identity, project)
        if row is not None and identity == action.id:
            if corruption == "action_hash":
                row["content_hash"] = "f" * 64
            elif corruption == "action_version":
                row["material_version"] = 99
            elif corruption == "result_edge":
                row["result_novelty_assessment_id"] = root.id
        return row

    def corrupt_link(repo, action_id, review_id):
        row = original_link(repo, action_id, review_id)
        if row is not None and corruption == "link_author":
            row["recorded_by"] = e["owner"].actor_id
        return row

    monkeypatch.setattr(SqlAlchemyRevisionActionRepository, "action", corrupt_action)
    monkeypatch.setattr(SqlAlchemyRevisionActionRepository, "link", corrupt_link)
    calls: list[Callable[[], object]] = [
        lambda: actions.read_novelty_re_review(e["viewer"], e["project"], action.id, review.id)
    ]
    if corruption == "link_author":
        # Same recorded actor is checked before saved-closure disclosure on replay.
        with pytest.raises(ResearchBaseError) as error:
            actions.record_concern_re_review(e["reviewer"], pair, novelty=True)
        assert error.value.code is ErrorCode.FORBIDDEN
    else:
        calls.extend(
            (
                lambda: actions.read_revision_action(e["viewer"], e["project"], action.id),
                lambda: actions.record_novelty_revision(e["researcher"], cmd),
                lambda: actions.record_concern_re_review(e["reviewer"], pair, novelty=True),
            )
        )
    for call in calls:
        with pytest.raises(ResearchBaseError) as error:
            call()
        assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_normalized_summary_replay_preserves_meaningful_whitespace(novelty_env):
    e = novelty_env
    _, root = _root(e)
    reviews = InternalReviewService(e["factory"], e["credentials"], e["literature"])
    request = uuid4()

    def create(summary):
        return reviews.create(
            e["reviewer"],
            e["project"],
            "NOVELTY_ASSESSMENT",
            root.id,
            "LITERATURE",
            "UNCERTAIN",
            summary,
            (),
            request,
        )

    saved = create(" e\u0301 ")
    assert create(" é ").content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as error:
        create("é")
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
