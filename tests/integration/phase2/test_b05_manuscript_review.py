"""B05 uses real Application-frozen manuscripts and disposable PostgreSQL."""

# ruff: noqa: E501
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.internal_review_repository import SqlAlchemyInternalReviewRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_b04_manuscript_freeze import b04_env as _b04_env
from tests.integration.phase2.test_b04_manuscript_freeze import freeze
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)

conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url
b04_env = _b04_env
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.fixture
def b05_env(b04_env, phase2_database_url):
    b04, q, author, _, _, credentials, store, claim, base = b04_env
    engine = create_database_engine(phase2_database_url, b05_write_timeouts=True)
    sf = create_session_factory(engine)

    def factory():
        return SqlAlchemyUnitOfWork(sf)

    service = InternalReviewService(
        factory, credentials, LiteratureEvidenceService(factory, credentials, store)
    )
    yield service, q, author, base[4], factory, engine, b04, store, claim, credentials, base
    engine.dispose()


def create(
    env,
    *,
    principal=None,
    target=None,
    summary="Independent review",
    issues=(),
    request=None,
    review_type="SCIENTIFIC",
    recommendation="ACCEPT",
):
    service, q, _, reviewer, *_ = env
    return service.create(
        principal or reviewer,
        q.project_id,
        "MANUSCRIPT_VERSION",
        target or q.manuscript_version_id,
        review_type,
        recommendation,
        summary,
        issues,
        request or uuid4(),
    )


def collect(env):
    service, q, _, reviewer, factory, *_ = env
    with factory() as uow:
        uow.enable_internal_review_error_normalization()
        uow.internal_review.prepare_write()
        uow.internal_review.lock_manuscript(q.manuscript_version_id)
        uow.literature_search_plan.lock_project(q.project_id)
        uow.internal_review.lock_publication(q.manuscript_version_id, q.project_id)
        service._authorize_snapshot(uow, reviewer, q.project_id)
        result = service.collect_manuscript_review_basis(uow, q.project_id, q.manuscript_version_id)
        service._authorize_snapshot(uow, reviewer, q.project_id)
        return result


def seal(env):
    return freeze(env[6], env[2], env[1])


def test_create_reconnect_replay_and_preserved_lifecycle(b05_env):
    env = b05_env
    seal(env)
    request = uuid4()
    issue = ReviewIssueRequest("MAJOR", "WRITING", "Check wording")
    result = create(env, issues=(issue,), request=request)
    assert result.target_kind == "MANUSCRIPT_VERSION"
    assert result.issues[0].status == "OPEN"
    restarted = InternalReviewService(
        env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7])
    )
    assert restarted.read(env[3], env[1].project_id, result.id) == result
    assert create(env, issues=(issue,), request=request) == result
    changes_list: tuple[dict[str, Any], ...] = (
        {"summary": "Different"},
        {"issues": ()},
        {"target": uuid4()},
    )
    for changes in changes_list:
        with pytest.raises(ResearchBaseError) as exc:
            create(
                env,
                request=request,
                issues=(issue,),
                **{k: v for k, v in changes.items() if k != "issues"},
            ) if "issues" not in changes else create(env, request=request, **changes)
        assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                {"id": env[1].publication_id},
            ).scalar_one()
            == "DRAFTING"
        )
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1


@pytest.mark.parametrize(
    "kind", ["draft", "missing", "author", "unauthenticated", "credential", "wrong_project"]
)
def test_reject_invalid_target_or_authority(b05_env, kind):
    env = b05_env
    if kind != "draft":
        seal(env)
    principal = env[2] if kind == "author" else env[3]
    if kind == "unauthenticated":
        principal = object()
    if kind == "credential":
        principal = replace(env[3], credential_id=str(uuid4()))
    args = {}
    if kind == "missing":
        args["target"] = uuid4()
    expected = {
        "author": ErrorCode.CONFLICT_OF_INTEREST,
        "unauthenticated": ErrorCode.AUTHENTICATION_REQUIRED,
        "credential": ErrorCode.FORBIDDEN,
        "wrong_project": ErrorCode.FORBIDDEN,
    }.get(kind, ErrorCode.REVIEW_TARGET_NOT_FROZEN)
    with pytest.raises(ResearchBaseError) as exc:
        if kind == "wrong_project":
            env[0].create(
                principal,
                uuid4(),
                "MANUSCRIPT_VERSION",
                env[1].manuscript_version_id,
                "SCIENTIFIC",
                "ACCEPT",
                "Review",
                (),
                uuid4(),
            )
        else:
            create(env, principal=principal, **args)
    assert exc.value.code == expected
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


def test_transitive_author_excluded(b05_env):
    env = b05_env
    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        env[1].project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        env[8],
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    seal(env)
    with env[4]() as uow:
        authors = uow.internal_review.material_authors(env[1].manuscript_version_id)
    assert env[2].actor_id in authors
    result = create(env)
    assert result.target_id == env[1].manuscript_version_id


@pytest.mark.parametrize("failure", ["review", "issue0", "issue1", "constraints", "commit"])
def test_atomic_failure(b05_env, monkeypatch, failure):
    env = b05_env
    seal(env)
    original_review = SqlAlchemyInternalReviewRepository.insert_review
    original_issue = SqlAlchemyInternalReviewRepository.insert_issue

    def insert_review(self, values):
        original_review(self, values)
        if failure == "review":
            raise RuntimeError("injected after review")

    def insert_issue(self, values):
        original_issue(self, values)
        if failure == f"issue{values['ordinal']}":
            raise RuntimeError("injected after issue/event")

    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "insert_review", insert_review)
    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "insert_issue", insert_issue)

    def fail(*args):
        raise RuntimeError("injected boundary failure")

    if failure == "constraints":
        monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "force_constraints", fail)
    if failure == "commit":
        monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail)
    with pytest.raises(RuntimeError):
        create(
            env,
            issues=(
                ReviewIssueRequest("MINOR", "OTHER", "one"),
                ReviewIssueRequest("MAJOR", "WRITING", "two"),
            ),
        )
    with env[5].connect() as conn:
        for table in ("internal_review_records", "review_issues", "review_issue_events"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_insert_reservation_precedes_share_and_reads_have_no_explicit_locks(b05_env):
    env = b05_env
    seal(env)
    statements = []
    read_settings = {}
    reading = False

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        if reading and not read_settings:
            read_settings["captured"] = True
            read_settings["isolation"] = conn.execute(
                text("SHOW transaction_isolation")
            ).scalar_one()
            read_settings["readonly"] = conn.execute(
                text("SHOW transaction_read_only")
            ).scalar_one()

    event.listen(env[5], "before_cursor_execute", capture)
    try:
        result = create(env)
        assert statements[0] == "LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"
        assert statements[1].startswith("LOCK TABLE actor_subject_bindings,")
        statements.clear()
        reading = True
        assert env[0].read(env[3], env[1].project_id, result.id) == result
        assert read_settings["isolation"] == "repeatable read"
        assert read_settings["readonly"] == "on"
        assert not any(
            any(
                token in sql.upper()
                for token in ("LOCK TABLE", "FOR UPDATE", "FOR SHARE", "ADVISORY")
            )
            for sql in statements
        )
    finally:
        event.remove(env[5], "before_cursor_execute", capture)


@pytest.mark.skip(
    reason="B04 only creates DRAFT/FROZEN; exact SUPERSEDED history awaits the later supersession contract"
)
def test_superseded_manuscript_review():
    pass


def test_hash_and_cas_tampering_fail_closed(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    result = create(env)
    original = env[7].verify
    monkeypatch.setattr(env[7], "verify", lambda identity: False)
    with pytest.raises(ResearchBaseError):
        env[0].read(env[3], env[1].project_id, result.id)
    with pytest.raises(ResearchBaseError):
        create(env)
    monkeypatch.setattr(env[7], "verify", original)
    with env[5].begin() as conn:
        conn.execute(text("ALTER TABLE manuscript_versions DISABLE TRIGGER USER"))
        conn.execute(
            text("UPDATE manuscript_versions SET content_hash=repeat('0',64) WHERE id=:id"),
            {"id": env[1].manuscript_version_id},
        )
        conn.execute(text("ALTER TABLE manuscript_versions ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as exc:
        env[0].read(env[3], env[1].project_id, result.id)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("first", ["manuscript", "claim"])
def test_request_namespace_shared_across_target_kinds(b05_env, first):
    env = b05_env
    seal(env)
    request = uuid4()

    def claim():
        return env[0].create(
            env[3],
            env[1].project_id,
            "CLAIM_VERSION",
            env[8],
            "SCIENTIFIC",
            "ACCEPT",
            "Independent review",
            (),
            request,
        )

    if first == "manuscript":
        create(env, request=request)
    else:
        claim()
    with pytest.raises(ResearchBaseError) as exc:
        if first == "manuscript":
            claim()
        else:
            create(env, request=request)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_historical_read_replay_after_target_stales(b05_env):
    from researchbase.application.governance import (
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    env = b05_env
    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        env[1].project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        env[8],
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    seal(env)
    request = uuid4()
    result = create(env, request=request)
    GovernanceService(env[4], SystemClock()).create_impact_assessment(
        CreateImpactAssessmentCommand(
            env[1].project_id,
            None,
            {"test": "later invalidity"},
            "invalid",
            (ProposedImpactTarget("claim_version", env[8], "invalid"),),
            ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test"),
        )
    )
    assert env[0].read(env[3], env[1].project_id, result.id) == result
    assert create(env, request=request) == result
    with pytest.raises(ResearchBaseError) as exc:
        create(env)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_initial_limit_and_unbounded_historical_issue_read(b05_env):
    env = b05_env
    seal(env)
    issues = tuple(ReviewIssueRequest("MINOR", "OTHER", str(i)) for i in range(100))
    result = create(env, issues=issues)
    assert len(result.issues) == 100
    with env[4]() as uow:
        uow.internal_review.insert_issue(
            {
                "id": uuid4(),
                "review_record_id": result.id,
                "severity": "MAJOR",
                "issue_type": "OTHER",
                "description": "101st appended issue",
                "ordinal": 100,
                "created_at": uow.manuscript_freeze.at(),
            }
        )
        uow.commit()
    assert len(env[0].read(env[3], env[1].project_id, result.id).issues) == 101


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
def test_transitive_placement_creator_and_agent_cannot_review(b05_env, actor_type):
    from datetime import UTC, datetime

    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    env = b05_env
    identity = uuid4()
    at = datetime.now(UTC)
    with env[5].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at,row_version) VALUES (:id,:type,'Additional test actor',:at,1)"
            ),
            {"id": identity, "type": actor_type, "at": at},
        )
        if actor_type == "HUMAN":
            _add_owner(
                conn,
                actor_id=identity,
                project_id=env[1].project_id,
                now=at,
                event_kind="ACTIVATED",
                request_id=uuid4(),
                create_actor=False,
            )
    principal = replace(
        env[3],
        actor_id=identity,
        subject_value=str(identity.int % 1_000_000),
        credential_id=f"uid:{identity.int}",
    )
    env[9].principals[identity] = principal
    if actor_type == "HUMAN":
        ClaimPlacementService(env[4], env[9]).add(
            principal,
            env[1].project_id,
            env[1].publication_id,
            env[1].manuscript_version_id,
            env[8],
            None,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": "p1"},
            "SUPPORTED",
            0,
            uuid4(),
        )
    seal(env)
    with pytest.raises(ResearchBaseError) as exc:
        create(env, principal=principal)
    assert exc.value.code == (
        ErrorCode.CONFLICT_OF_INTEREST if actor_type == "HUMAN" else ErrorCode.FORBIDDEN
    )
