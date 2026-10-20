"""M1-S1 immutable manuscript revision through Application commands on PostgreSQL."""

from contextlib import contextmanager
from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import event, text

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
    TransitionPublicationReadyCommand,
)
from researchbase.application.revision_action import (
    ConcernReReviewReadback,
    RecordConcernReReviewCommand,
    RecordRevisionActionCommand,
    RevisionActionService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b04_manuscript_freeze import freeze
from tests.integration.phase2.test_b05_manuscript_review import (
    b04_env,
    b05_env,
    conclusion_env,
    create,
    phase2_database_url,
    seal,
)
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url)


@contextmanager
def observe_transaction_modes(engine):
    """Probe after SQL so the observer cannot precede a required first lock."""
    observed = []

    def after(conn, cursor, sql, parameters, context, many):
        # A separate DBAPI cursor avoids recursive SQLAlchemy event callbacks.
        with conn.connection.cursor() as probe:
            probe.execute("SHOW transaction_isolation")
            isolation = probe.fetchone()[0]
            probe.execute("SHOW transaction_read_only")
            readonly = probe.fetchone()[0]
        observed.append((sql, isolation, readonly))

    event.listen(engine, "after_cursor_execute", after)
    try:
        yield observed
    finally:
        event.remove(engine, "after_cursor_execute", after)


def successor(env, *, request=None, title="Revised manuscript", change="EDITORIAL"):
    _, q, author, _, factory, _, _, store, _, credentials, _ = env
    document = _artifact(
        factory, store, author, q.project_id, b"Immutable revised manuscript", "manuscript"
    )
    service = PublicationService(factory, credentials, store)
    args: dict[str, Any] = dict(
        principal=author,
        project=q.project_id,
        publication_id=q.publication_id,
        document_id=document,
        title=title,
        abstract=None,
        change_class=change,
        request_id=request or uuid4(),
    )
    return service, args, service.create_draft(**args)


@pytest.mark.parametrize("dismiss", [False, True])
def test_manuscript_revision_decision_action_re_review_disposition(b05_env, dismiss, monkeypatch):
    env = b05_env
    reviews, q, author, reviewer, factory, engine, manuscripts, store, _, credentials, _ = env

    def credential_live(principal, at):
        saved = credentials.principals.get(principal.actor_id)
        return (
            credentials.enabled
            and saved is not None
            and saved.verified_at <= at
            and replace(principal, verified_at=saved.verified_at) == saved
        )

    monkeypatch.setattr(credentials, "is_valid", credential_live)
    v1 = seal(env)
    PublicationService(factory, credentials, store).transition_publication_internal_review(
        author,
        TransitionPublicationInternalReviewCommand(
            uuid4(), q.project_id, q.publication_id, q.manuscript_version_id, v1.content_hash
        ),
    )
    with engine.connect() as c:
        before = dict(
            c.execute(
                text("SELECT * FROM manuscript_versions WHERE id=:id"),
                {"id": v1.manuscript_version_id},
            )
            .mappings()
            .one()
        )
    original = create(
        env,
        issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Correct this wording"),),
        recommendation="MAJOR_REVISION",
    )
    literature = LiteratureEvidenceService(factory, credentials, store)
    decisions = DecisionService(factory, credentials, literature)
    revisions = RevisionActionService(factory, credentials, literature)
    decision = decisions.record_revision_decision(
        reviewer,
        RecordRevisionDecisionCommand(
            uuid4(),
            q.project_id,
            original.issues[0].id,
            "Respond?",
            "Exact wording concern",
            "ACCEPT_NO_CHANGE" if dismiss else "REQUIRE_CHANGE",
        ),
    )
    assert decision.manuscript_version_id == v1.manuscript_version_id
    if dismiss:
        result = q
    else:
        pubs, args, draft = successor(env)
        result = replace(q, manuscript_version_id=draft.id)
        v2 = freeze(manuscripts, author, result)
        assert v2.version_number == 2
        assert pubs.create_draft(**args).content_hash == v2.content_hash
        with pytest.raises(ResearchBaseError) as stale:
            decisions.record_ready_for_submission_decision(
                reviewer,
                RecordReadyForSubmissionDecisionCommand(
                    uuid4(),
                    q.project_id,
                    q.manuscript_version_id,
                    "Ready?",
                    "Historical version cannot authorize current readiness",
                ),
            )
        assert stale.value.code == ErrorCode.APPROVAL_TARGET_STALE
        with factory() as uow:
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            assert original.issues[0].id in decisions._readiness_blockers(
                uow, q.project_id, draft.id
            )
            assert uow.decision.applicable_manuscript_reviews(draft.id, q.project_id) == []
    action = revisions.record_revision_action(
        author,
        RecordRevisionActionCommand(
            uuid4(),
            q.project_id,
            "NO_CHANGE" if dismiss else "MANUSCRIPT_CHANGE",
            decision_record_id=decision.id,
            result_manuscript_version_id=None if dismiss else result.manuscript_version_id,
        ),
    )
    # Exercise the installed manuscript arm and its shared correction-chain tail.
    from sqlalchemy.exc import DBAPIError

    with engine.connect() as conn:
        conn.execute(
            text("SELECT b07_validate_revision(a) FROM revision_actions a WHERE a.id=:id"),
            {"id": action.id},
        )
    for mutation, message in (
        (
            "a.action_type := 'CLAIM_CHANGE';",
            "exact revision choice required" if dismiss else "exact manuscript concern required",
        ),
        ("a.supersedes_revision_action_id := a.id;", "revision correction cycle"),
    ):
        with pytest.raises(DBAPIError) as caught, engine.begin() as conn:
            conn.execute(
                text(
                    "DO $$ DECLARE a revision_actions; BEGIN SELECT * INTO STRICT a "
                    f"FROM revision_actions WHERE id='{action.id}'::uuid; "
                    + mutation
                    + " PERFORM b07_validate_revision(a); END $$"
                )
            )
        assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
        assert message in getattr(getattr(caught.value.orig, "diag", None), "message_primary", "")
    assert reviews.get_issue_history(reviewer, q.project_id, original.issues[0].id).status == "OPEN"
    fresh = create(env, target=result.manuscript_version_id, summary="Exact independent re-review")
    link = revisions.record_concern_re_review(
        reviewer, RecordConcernReReviewCommand(q.project_id, action.id, fresh.id)
    )
    assert isinstance(link, ConcernReReviewReadback)
    assert link.manuscript_version_id == result.manuscript_version_id
    command = RecordIssueDispositionCommand(
        uuid4(),
        q.project_id,
        original.issues[0].id,
        "DISMISSED" if dismiss else "ADDRESSED",
        action.id,
        fresh.id,
        "This response resolves the exact concern",
        decision.id,
    )
    saved = reviews.record_issue_disposition(reviewer, command)
    assert saved.new_status == command.disposition
    ready = decisions.record_ready_for_submission_decision(
        reviewer,
        RecordReadyForSubmissionDecisionCommand(
            uuid4(),
            q.project_id,
            result.manuscript_version_id,
            "Ready?",
            "Issue disposition and exact re-review",
        ),
    )
    assert ready.manuscript_version_id == result.manuscript_version_id
    if not dismiss:
        assert original.id not in {r.id for r in ready.basis}
    from researchbase.application.approval import DecideApprovalCommand, RequestApprovalCommand
    from tests.integration.phase2.test_b14r_ready_approval import approver
    from tests.integration.phase2.test_b14r_ready_approval import service as approvals

    app = approvals(env)
    exact_reviews = tuple(r.id for r in ready.basis if r.type == "InternalReviewRecord")
    request = app.request_approval(
        author,
        RequestApprovalCommand(
            uuid4(),
            q.project_id,
            None,
            ready.id,
            exact_reviews,
            approval_purpose="READY_FOR_SUBMISSION",
            manuscript_version_id=result.manuscript_version_id,
        ),
    )
    approved = app.decide_approval(
        approver(env),
        DecideApprovalCommand(
            uuid4(), q.project_id, request.id, "APPROVE", "Independent manuscript permission"
        ),
    )
    assert approved.grant is not None and approved.grant.usable
    with observe_transaction_modes(engine) as consumption_modes:
        PublicationService(factory, credentials, store).transition_publication_ready(
            author,
            TransitionPublicationReadyCommand(
                uuid4(), q.project_id, approved.grant.id, q.publication_id, exact_reviews
            ),
        )
    writer_modes = [
        (mode, readonly)
        for sql, mode, readonly in consumption_modes
        if sql.startswith("LOCK TABLE")
    ]
    assert writer_modes and set(writer_modes) == {("serializable", "off")}
    with pytest.raises(ResearchBaseError) as denied:
        successor(env)
    assert denied.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert decisions.get_revision_decision(reviewer, q.project_id, decision.id) == decision
    assert revisions.read_revision_action(reviewer, q.project_id, action.id) == action
    with engine.connect() as c:
        assert (
            dict(
                c.execute(
                    text("SELECT * FROM manuscript_versions WHERE id=:id"),
                    {"id": v1.manuscript_version_id},
                )
                .mappings()
                .one()
            )
            == before
        )
    statements = []

    def capture(conn, cursor, sql, parameters, context, many):
        statements.append(sql)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        with observe_transaction_modes(engine) as read_modes:
            assert manuscripts.get_manuscript_version(reviewer, q) == v1
            assert (
                reviews.read(reviewer, q.project_id, original.id).issues[0].status
                == command.disposition
            )
            reviews.get_issue_history(reviewer, q.project_id, original.issues[0].id)
            decisions.get_revision_decision(reviewer, q.project_id, decision.id)
            revisions.read_revision_action(reviewer, q.project_id, action.id)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert read_modes and {(mode, readonly) for _, mode, readonly in read_modes} == {
        ("repeatable read", "on")
    }
    assert not any(
        "LOCK TABLE" in s.upper()
        or "FOR UPDATE" in s.upper()
        or "FOR SHARE" in s.upper()
        or "PG_ADVISORY" in s.upper()
        for s in statements
    )


def test_successor_conflicts_and_invalid_change_class(b05_env):
    env = b05_env
    seal(env)
    with pytest.raises(ResearchBaseError) as caught:
        successor(env, change="INITIAL")
    assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    pubs, args, draft = successor(env)
    assert pubs.create_draft(**args) == draft
    with pytest.raises(ResearchBaseError) as caught:
        pubs.create_draft(**{**args, "request_id": uuid4()})
    assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_historical_placement_trace_and_replay_after_successor_are_lock_free(b05_env):
    from researchbase.application.manuscript_placement import (
        ArtifactPlacementService,
        CitationPlacementService,
        ClaimPlacementService,
    )

    env = b05_env
    _, q, author, _, factory, engine, manuscripts, store, claim, credentials, base = env
    claim_service = ClaimPlacementService(factory, credentials, store)
    citation_service = CitationPlacementService(factory, credentials, store)
    artifact_service = ArtifactPlacementService(factory, credentials, store)
    with engine.connect() as conn:
        doc = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": q.manuscript_version_id},
        ).scalar_one()
    common = (author, q.project_id, q.publication_id, q.manuscript_version_id)
    claim_args = (
        *common,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    citation_args = (
        *common,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    artifact_args = (
        *common,
        doc,
        "APPENDIX",
        {"kind": "ANCHOR", "value": "doc"},
        "OTHER",
        0,
        uuid4(),
    )
    expected = (
        claim_service.add(*claim_args),
        citation_service.add(*citation_args),
        artifact_service.add(*artifact_args),
    )
    seal(env)
    _, _, draft = successor(env)
    freeze(manuscripts, author, replace(q, manuscript_version_id=draft.id))
    from tests.integration.phase2.pr2_20_support import capture

    with capture(engine) as observed:
        cases: tuple[tuple[Any, tuple[Any, ...], Any], ...] = (
            (claim_service, claim_args, expected[0]),
            (citation_service, citation_args, expected[1]),
            (artifact_service, artifact_args, expected[2]),
        )
        for app, args, saved in cases:
            assert cast(Any, app).trace(*common) == (saved,)
            assert cast(Any, app).add(*args) == saved
        from researchbase.application.manuscript_scientific_trace import (
            ManuscriptScientificTraceService,
        )
        from tests.integration.phase2.b25_support import queries

        audit, validity_query, audit_query = queries(env)
        assert audit.get_manuscript_validity(author, validity_query).content_hash is not None
        audit.get_manuscript_audit(author, audit_query)
        ManuscriptScientificTraceService(factory, credentials, store).trace(*common)
    assert len(observed.transactions) == 9
    assert not any(
        "LOCK TABLE" in sql or "pg_advisory" in sql or "FOR UPDATE" in sql or "FOR SHARE" in sql
        for sql, _ in observed.statements
    )
