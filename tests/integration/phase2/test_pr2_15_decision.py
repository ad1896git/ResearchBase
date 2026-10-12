"""TEST ONLY frozen PR2-15 contract adversarial PostgreSQL acceptance tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import phase2_database_url as _database_url
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

from researchbase.application.decision import DecisionService, RecordDecisionCommand
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
)
from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
from researchbase.application.scientific_conclusion import ClaimInputRequest
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import SystemClock

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
conclusion_env = _conclusion_env
phase2_database_url = _database_url


@pytest.fixture
def decision_env(conclusion_env, phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    scientific, factory, evidence, author, actor, project, claim, _, _, credentials = conclusion_env
    target = scientific.create(
        author,
        project,
        "TEST ONLY claim-only conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    return (
        DecisionService(factory, credentials, evidence),
        InternalReviewService(factory, credentials, evidence),
        actor,
        target,
        conclusion_env,
    )


def _command(env, **changes):
    return replace(
        RecordDecisionCommand(
            uuid4(),
            env[-1][5],
            env[3].version_id,
            "TEST ONLY proceed?",
            "TEST ONLY review complete.",
        ),
        **changes,
    )


def _review(env, recommendation="ACCEPT", issues=(), review_type="SCIENTIFIC"):
    return env[1].create(
        env[2],
        env[-1][5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        env[3].version_id,
        review_type,
        recommendation,
        "TEST ONLY independent review",
        issues,
        uuid4(),
    )


def _counts(engine):
    with engine.connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in (
                "decision_records",
                "decision_basis_conclusions",
                "decision_basis_reviews",
            )
        )


def _stale(env):
    base = env[-1]
    context = ExecutionContext(actor_id=base[3].actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(base[1], SystemClock())
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            base[5],
            "code_bug",
            "major",
            "TEST ONLY later input problem",
            "Recheck claim",
            "claim_version",
            base[6],
            context,
        )
    )
    governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            base[5],
            finding.id,
            {"basis": "TEST ONLY"},
            "stale",
            (ProposedImpactTarget("claim_version", base[6], "stale"),),
            context,
        )
    )


def _issue(conn, review_id):
    conn.execute(
        text("""INSERT INTO review_issues
      (id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
      VALUES (:id,:review,'BLOCKING','OVERCLAIM','TEST ONLY later blocker',
              'OPEN',clock_timestamp(),0)"""),
        {"id": uuid4(), "review": review_id},
    )


def test_complete_basis_every_type_unfavorable_review_r2_and_restart(decision_env):
    service, _, actor, target, base = decision_env
    reviews = [
        _review(decision_env, rec, review_type=kind)
        for kind, rec in (
            ("SCIENTIFIC", "ACCEPT"),
            ("STATISTICAL", "MINOR_REVISION"),
            ("LITERATURE", "MAJOR_REVISION"),
            ("REPRODUCIBILITY", "REJECT"),
            ("EDITORIAL", "UNCERTAIN"),
            ("COMPREHENSIVE", "REJECT"),
        )
    ]
    request = _command(decision_env, question="Cafe\u0301?", rationale="TEST ONLY reason e\u0301")
    result = service.record_decision(actor, request)
    assert result.id == request.id and result.project_id == base[5]
    assert result.decision_type == "INTERNAL_SCIENTIFIC_RELEASE" and result.decision == "PROCEED"
    assert result.decided_by == actor.actor_id
    assert result.question == "Café?" and result.rationale == "TEST ONLY reason é"
    with base[8].connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM scientific_conclusion_versions WHERE id=:id"),
            {"id": target.version_id},
        ).scalar_one()
        stored = conn.execute(
            text(
                "SELECT scientific_conclusion_version_id,ordinal "
                "FROM decision_basis_conclusions WHERE decision_id=:id"
            ),
            {"id": result.id},
        ).one()
        saved = conn.execute(
            text(
                "SELECT internal_review_record_id,ordinal "
                "FROM decision_basis_reviews WHERE decision_id=:id"
            ),
            {"id": result.id},
        ).all()
    refs = [("ScientificConclusionVersion", target.version_id, digest)]
    refs += [("InternalReviewRecord", r.id, r.content_hash) for r in reviews]
    refs.sort(key=lambda item: (item[0], str(item[1]), item[2]))
    basis = {
        "type": "DecisionRecordBasisSet",
        "material_version": 1,
        "basis": [
            {"target": {"type": kind, "id": str(id_), "content_hash": h}, "ordinal": ordinal}
            for ordinal, (kind, id_, h) in enumerate(refs)
        ],
    }
    assert result.basis_set_hash == str(sha256_canonical_json(basis))
    assert tuple(stored) == (target.version_id, len(reviews))
    assert {(r[0], r[1]) for r in saved} == {
        (id_, ordinal)
        for ordinal, (kind, id_, _) in enumerate(refs)
        if kind == "InternalReviewRecord"
    }
    assert [(r.type, r.id, r.content_hash, r.ordinal) for r in result.basis] == [
        (kind, id_, h, ordinal) for ordinal, (kind, id_, h) in enumerate(refs)
    ]
    content = {
        "type": "DecisionRecord",
        "material_version": 1,
        "project_id": str(base[5]),
        "decision_type": "INTERNAL_SCIENTIFIC_RELEASE",
        "question": "Café?",
        "decision": "PROCEED",
        "rationale": "TEST ONLY reason é",
        "decided_by": {"type": "ActorIdentity", "id": str(actor.actor_id)},
        "supersedes_decision_id": None,
        "basis_set_hash": result.basis_set_hash,
    }
    assert result.content_hash == str(sha256_canonical_json(content))
    restarted = DecisionService(base[1], base[9], base[2])
    assert restarted.record_decision(actor, replace(request, question="Café?")) == result
    assert _counts(base[8]) == (1, 1, 6)


@pytest.mark.parametrize(
    "severity,allowed", [("INFO", True), ("MINOR", True), ("MAJOR", True), ("BLOCKING", False)]
)
def test_exact_open_blocking_predicate(decision_env, severity, allowed):
    service, _, actor, _, base = decision_env
    _review(decision_env, "REJECT", (ReviewIssueRequest(severity, "OVERCLAIM", "TEST ONLY issue"),))
    request = _command(decision_env)
    if allowed:
        assert service.record_decision(actor, request).id == request.id
        assert _counts(base[8]) == (1, 1, 1)
    else:
        with pytest.raises(ResearchBaseError):
            service.record_decision(actor, request)
        assert _counts(base[8]) == (0, 0, 0)


def test_shared_claim_other_conclusion_blocker_does_not_apply(decision_env):
    service, review, actor, _, base = decision_env
    _review(decision_env)
    other = base[0].create(
        base[3],
        base[5],
        "TEST ONLY other conclusion",
        SCOPE,
        "WEAK",
        None,
        (ClaimInputRequest(base[6], "SUPPORTS"),),
        (),
        uuid4(),
    )
    base[0].freeze(base[3], base[5], other.conclusion_id, other.version_id, uuid4())
    review.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        other.version_id,
        "SCIENTIFIC",
        "REJECT",
        "TEST ONLY unrelated",
        (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "Other"),),
        uuid4(),
    )
    assert service.record_decision(actor, _command(decision_env)).decision == "PROCEED"
    assert _counts(base[8]) == (1, 1, 1)


def test_zero_reviews_author_conflict_missing_draft_cross_project_atomic(decision_env):
    service, _, actor, _, base = decision_env
    with pytest.raises(ResearchBaseError):
        service.record_decision(actor, _command(decision_env))
    _review(decision_env)
    draft = base[0].create(
        base[3],
        base[5],
        "TEST ONLY draft",
        SCOPE,
        "WEAK",
        None,
        (ClaimInputRequest(base[6], "SUPPORTS"),),
        (),
        uuid4(),
    )
    for principal, changes in (
        (base[3], {}),
        (actor, {"scientific_conclusion_version_id": uuid4()}),
        (actor, {"scientific_conclusion_version_id": draft.version_id}),
        (actor, {"project_id": uuid4()}),
    ):
        with pytest.raises(ResearchBaseError):
            service.record_decision(principal, _command(decision_env, **changes))
    assert _counts(base[8]) == (0, 0, 0)


@pytest.mark.parametrize(
    "changes",
    [
        {"decision_type": "PUBLICATION"},
        {"decision": "REJECT"},
        {"question": " "},
        {"rationale": ""},
    ],
)
def test_closed_command_rejects_unsupported_material(decision_env, changes):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    with pytest.raises(ResearchBaseError) as denied:
        service.record_decision(actor, _command(decision_env, **changes))
    assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert _counts(base[8]) == (0, 0, 0)
    with pytest.raises(TypeError):
        RecordDecisionCommand(
            uuid4(), base[5], decision_env[3].version_id, "Q", "R", decided_by=base[3].actor_id
        )


def test_stale_saved_replay_survives_but_unknown_uuid_denies(decision_env):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)
    result = service.record_decision(actor, request)
    _stale(decision_env)
    assert service.record_decision(actor, request) == result
    with pytest.raises(ResearchBaseError):
        service.record_decision(actor, replace(request, id=uuid4()))
    assert _counts(base[8]) == (1, 1, 1)


def test_stale_first_creation_denies(decision_env):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    _stale(decision_env)
    with pytest.raises(ResearchBaseError):
        service.record_decision(actor, _command(decision_env))
    assert _counts(base[8]) == (0, 0, 0)


def test_uuid_conflict_new_uuid_and_concurrent_duplicates(decision_env):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.record_decision(actor, request), range(2)))
    assert results[0] == results[1]
    for changed in (replace(request, rationale="Changed"), replace(request, id=uuid4())):
        with pytest.raises(ResearchBaseError) as conflict:
            service.record_decision(actor, changed)
        assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError):
        service.record_decision(base[3], request)
    assert service.record_decision(actor, request) == results[0]
    assert _counts(base[8]) == (1, 1, 1)


def test_concurrent_new_uuids_cannot_replace(decision_env):
    service, _, actor, _, base = decision_env
    _review(decision_env)

    def create(_):
        try:
            return service.record_decision(actor, _command(decision_env))
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert sum(not isinstance(item, ErrorCode) for item in results) == 1
    assert results.count(ErrorCode.IDEMPOTENCY_CONFLICT) == 1
    assert _counts(base[8]) == (1, 1, 1)


def test_replay_current_read_authority_survives_write_role_loss(decision_env):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)
    result = service.record_decision(actor, request)
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(
            base[3], base[5], actor.actor_id, "VIEWER", "TEST ONLY historical read", uuid4()
        )
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                "AND project_id=:project AND role='OWNER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(base[3], base[5], role, "TEST ONLY write authority removed", uuid4())
    )
    assert service.record_decision(actor, request) == result
    with pytest.raises(ResearchBaseError):
        service.record_decision(actor, replace(request, id=uuid4()))
    with base[8].connect() as conn:
        viewer = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                "AND project_id=:project AND role='VIEWER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(base[3], base[5], viewer, "TEST ONLY read authority removed", uuid4())
    )
    with pytest.raises(ResearchBaseError) as no_read:
        service.record_decision(actor, request)
    assert no_read.value.code is ErrorCode.FORBIDDEN
    base[9].enabled = False
    for candidate in (
        request,
        replace(request, rationale="conflict"),
        replace(request, id=uuid4()),
    ):
        with pytest.raises(ResearchBaseError) as denied:
            service.record_decision(actor, candidate)
        assert denied.value.code in {ErrorCode.FORBIDDEN, ErrorCode.AUTHENTICATION_REQUIRED}
        assert str(request.id) not in str(denied.value.to_dict())
    assert _counts(base[8]) == (1, 1, 1)


def test_credential_revoked_after_observed_target_wait_denies(decision_env):
    service, _, actor, target, base = decision_env
    _review(decision_env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": target.version_id},
            ).one()
            pending = pool.submit(service.record_decision, actor, _command(decision_env))
            witness = _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert "scientific_conclusion_versions" in witness["query"]
            base[9].enabled = False
            assert not pending.done()
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    assert _counts(base[8]) == (0, 0, 0)


def test_issue_first_observed_wait_refreshes_blockers(decision_env):
    service, _, actor, _, base = decision_env
    review = _review(decision_env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as writer:
            pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            _issue(writer, review.id)
            pending = pool.submit(service.record_decision, actor, _command(decision_env))
            _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert not pending.done()
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    assert _counts(base[8]) == (0, 0, 0)


@pytest.fixture
def normal_sql_role(decision_env):
    """Uniquely owned ephemeral NOLOGIN role; no superuser bypass in SQL tests."""
    engine = decision_env[-1][8]
    role = f"pr215_c_sql_{uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(
            text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
    try:
        yield role
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))


def _normal(conn, role):
    conn.execute(text(f'SET LOCAL ROLE "{role}"'))
    conn.execute(text("SET LOCAL statement_timeout='12s'"))
    assert not conn.execute(
        text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
    ).scalar_one()


def _copy_review(conn, review_id, new_id):
    # Own-content material excludes id/time: identical exact material is valid
    # distinct immutable history, with no Issue children on the new record.
    conn.execute(
        text("""INSERT INTO internal_review_records
      (id,project_id,scientific_conclusion_version_id,target_content_hash,
       reviewer_actor_id,review_type,recommendation,summary,created_at,content_hash,hash_scheme)
      SELECT :new_id,project_id,scientific_conclusion_version_id,target_content_hash,
       reviewer_actor_id,review_type,recommendation,summary,clock_timestamp(),content_hash,hash_scheme
      FROM internal_review_records WHERE id=:id"""),
        {"id": review_id, "new_id": new_id},
    )


def test_zero_issue_review_first_observed_wait_includes_committed_review(
    decision_env, normal_sql_role
):
    service, _, actor, _, base = decision_env
    review = _review(decision_env, "REJECT")
    added = uuid4()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as writer:
            _normal(writer, normal_sql_role)
            pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            _copy_review(writer, review.id, added)
            pending = pool.submit(service.record_decision, actor, _command(decision_env))
            _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert not pending.done()
        result = pending.result(timeout=10)
    assert {ref.id for ref in result.basis if ref.type == "InternalReviewRecord"} == {
        review.id,
        added,
    }
    assert _counts(base[8]) == (1, 1, 2)


@pytest.mark.parametrize("writer_kind", ["issue", "zero_issue_review"])
def test_decision_first_real_writer_wait_preserves_original_basis(
    decision_env, normal_sql_role, writer_kind
):
    service, _, actor, _, base = decision_env
    review = _review(decision_env)
    request = _command(decision_env)
    held, release = Event(), Event()
    holder_pid = []

    def pause_after_insert(conn, cursor, statement, parameters, context, executemany):
        if (
            statement.lstrip().upper().startswith("INSERT INTO DECISION_RECORDS")
            and not held.is_set()
        ):
            holder_pid.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(15), "test did not release Decision transaction"

    def writer():
        with base[8].begin() as conn:
            _normal(conn, normal_sql_role)
            if writer_kind == "issue":
                _issue(conn, review.id)
            else:
                _copy_review(conn, review.id, uuid4())

    event.listen(base[8], "after_cursor_execute", pause_after_insert)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            decision = pool.submit(service.record_decision, actor, request)
            try:
                assert held.wait(10), "Decision did not reach INSERT"
                pending = pool.submit(writer)
                witness = _wait_for_pg_blocker(base[8], holder_pid[0], "transactionid")
                assert (
                    "review_issues" in witness["query"]
                    or "internal_review_records" in witness["query"]
                )
                assert not pending.done()
            finally:
                release.set()
            result = decision.result(timeout=10)
            pending.result(timeout=10)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause_after_insert)
    assert {ref.id for ref in result.basis if ref.type == "InternalReviewRecord"} == {review.id}
    assert service.record_decision(actor, request) == result
    assert _counts(base[8]) == (1, 1, 1)


def test_normal_role_issue_first_wait_refreshes_blockers(decision_env, normal_sql_role):
    service, _, actor, _, base = decision_env
    review = _review(decision_env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as writer:
            _normal(writer, normal_sql_role)
            pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            _issue(writer, review.id)
            pending = pool.submit(service.record_decision, actor, _command(decision_env))
            _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert not pending.done()
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    assert _counts(base[8]) == (0, 0, 0)


def test_database_failure_mid_basis_rolls_back_then_same_uuid_recovers(decision_env):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)

    def fail_basis(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO DECISION_BASIS_REVIEWS"):
            # A genuine PostgreSQL error in the command's existing transaction.
            conn.execute(text("SELECT 1/0"))

    event.listen(base[8], "before_cursor_execute", fail_basis)
    try:
        with pytest.raises(ResearchBaseError) as failed:
            service.record_decision(actor, request)
        assert "division by zero" not in str(failed.value.to_dict()).lower()
        assert _counts(base[8]) == (0, 0, 0)
    finally:
        event.remove(base[8], "before_cursor_execute", fail_basis)
    result = service.record_decision(actor, request)
    assert service.record_decision(actor, request) == result
    assert _counts(base[8]) == (1, 1, 1)


def test_normal_role_cannot_mutate_decision_basis_reviews_or_issues(decision_env, normal_sql_role):
    service, _, actor, _, base = decision_env
    review = _review(decision_env, issues=(ReviewIssueRequest("MINOR", "OVERCLAIM", "TEST ONLY"),))
    result = service.record_decision(actor, _command(decision_env))
    cases = (
        ("UPDATE decision_records SET rationale='tamper' WHERE id=:id", result.id),
        ("DELETE FROM decision_records WHERE id=:id", result.id),
        ("DELETE FROM decision_basis_conclusions WHERE decision_id=:id", result.id),
        ("DELETE FROM decision_basis_reviews WHERE decision_id=:id", result.id),
        ("UPDATE internal_review_records SET summary='tamper' WHERE id=:id", review.id),
        ("DELETE FROM internal_review_records WHERE id=:id", review.id),
        ("UPDATE review_issues SET status='DISMISSED' WHERE id=:id", review.issues[0].id),
        ("DELETE FROM review_issues WHERE id=:id", review.issues[0].id),
    )
    for sql, identifier in cases:
        with pytest.raises(DBAPIError), base[8].begin() as conn:
            _normal(conn, normal_sql_role)
            conn.execute(text(sql), {"id": identifier})
    assert _counts(base[8]) == (1, 1, 1)


@pytest.mark.parametrize(
    "table,id_column", [("internal_review_records", "id"), ("scientific_conclusion_versions", "id")]
)
def test_corrupt_matching_review_or_target_hash_fails_closed(decision_env, table, id_column):
    service, _, actor, target, base = decision_env
    review = _review(decision_env)
    identifier = review.id if table == "internal_review_records" else target.version_id
    # TEST ONLY administrative corruption injection, never an application write.
    # Restore guards in the same transaction; normal-role paths remain tested separately.
    with base[8].begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
        conn.execute(
            text(f"UPDATE {table} SET content_hash=:hash WHERE {id_column}=:id"),
            {"hash": "0" * 64, "id": identifier},
        )
        conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as denied:
        service.record_decision(actor, _command(decision_env))
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert _counts(base[8]) == (0, 0, 0)


def test_scheduled_write_role_expiry_during_observed_wait_denies(decision_env):
    service, _, actor, target, base = decision_env
    _review(decision_env)
    with base[8].begin() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                "AND project_id=:project AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
        until = conn.execute(
            text(
                "UPDATE project_role_assignments SET "
                "effective_until=clock_timestamp()+interval '8 seconds', row_version=row_version+1 "
                "WHERE id=:id RETURNING effective_until"
            ),
            {"id": role},
        ).scalar_one()
        conn.execute(
            text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          VALUES (:id,:role,:actor,'CLOSED',:until,'TEST ONLY expiry',:request)"""),
            {
                "id": uuid4(),
                "role": role,
                "actor": actor.actor_id,
                "until": until,
                "request": uuid4(),
            },
        )
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": target.version_id},
            ).one()
            pending = pool.submit(service.record_decision, actor, _command(decision_env))
            before = _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert before["observed_at"] < until
            holder.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0, "
                    "EXTRACT(EPOCH FROM (:until-clock_timestamp()))+0.1))"
                ),
                {"until": until},
            )
            after = _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert before["pid"] == after["pid"] and after["observed_at"] >= until
            assert not pending.done()
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    assert _counts(base[8]) == (0, 0, 0)


def test_normal_role_new_uuid_direct_sql_scope_substitution_denied(decision_env, normal_sql_role):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    original = service.record_decision(actor, _command(decision_env))
    replacement = uuid4()
    with pytest.raises(DBAPIError), base[8].begin() as conn:
        _normal(conn, normal_sql_role)
        conn.execute(
            text("""INSERT INTO decision_records
          (id,project_id,decision_type,question,decision,rationale,decided_by,decided_at,
           supersedes_decision_id,basis_set_hash,content_hash,hash_scheme)
          SELECT :new_id,project_id,decision_type,question,decision,rationale,decided_by,
           clock_timestamp(),NULL,basis_set_hash,content_hash,hash_scheme
          FROM decision_records WHERE id=:id"""),
            {"new_id": replacement, "id": original.id},
        )
        conn.execute(
            text("""INSERT INTO decision_basis_conclusions
          (decision_id,scientific_conclusion_version_id,ordinal)
          SELECT :new_id,scientific_conclusion_version_id,ordinal
          FROM decision_basis_conclusions WHERE decision_id=:id"""),
            {"new_id": replacement, "id": original.id},
        )
        conn.execute(
            text("""INSERT INTO decision_basis_reviews
          (decision_id,internal_review_record_id,ordinal)
          SELECT :new_id,internal_review_record_id,ordinal
          FROM decision_basis_reviews WHERE decision_id=:id"""),
            {"new_id": replacement, "id": original.id},
        )
    assert _counts(base[8]) == (1, 1, 1)


def test_proceed_creates_no_approval_release_disposition_or_scientific_transition(decision_env):
    service, _, actor, target, base = decision_env
    review = _review(decision_env, issues=(ReviewIssueRequest("MINOR", "OVERCLAIM", "TEST ONLY"),))
    tables = (
        "approval_requests",
        "approval_decisions",
        "approval_grants",
        "revision_actions",
        "approval_grant_consumptions",
        "external_effects",
        "manuscript_versions",
        "prepared_submission_versions",
        "review_issue_events",
        "literature_evidence_review_events",
    )

    def effects():
        with base[8].connect() as conn:
            counts = {
                table: conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                for table in tables
                if conn.execute(
                    text("SELECT to_regclass(:table)"), {"table": f"public.{table}"}
                ).scalar_one()
                is not None
            }
            issue = tuple(
                conn.execute(
                    text("SELECT status,severity FROM review_issues WHERE id=:id"),
                    {"id": review.issues[0].id},
                ).one()
            )
            conclusion = tuple(
                conn.execute(
                    text(
                        "SELECT status,content_hash FROM "
                        "scientific_conclusion_versions WHERE id=:id"
                    ),
                    {"id": target.version_id},
                ).one()
            )
        return counts, issue, conclusion

    before = effects()
    request = _command(decision_env)
    service.record_decision(actor, request)
    service.record_decision(actor, request)
    assert effects() == before


def test_commit_uncertainty_recovers_by_exact_uuid_without_duplicate_history(decision_env):
    """Inject loss of acknowledgement after a real successful PostgreSQL commit."""
    from psycopg import OperationalError
    from sqlalchemy.exc import OperationalError as SqlOperationalError

    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)

    def uncertain_factory():
        uow = base[1]()
        commit = uow.commit

        def uncertain_commit():
            commit()
            raise SqlOperationalError(
                None, None, OperationalError("TEST ONLY lost acknowledgement")
            )

        uow.commit = uncertain_commit
        return uow

    uncertain = DecisionService(uncertain_factory, base[9], base[2])
    try:
        acknowledged = uncertain.record_decision(actor, request)
    except ResearchBaseError as failure:
        assert "lost acknowledgement" not in str(failure.to_dict())
        acknowledged = None
    assert _counts(base[8]) == (1, 1, 1)
    saved = service.record_decision(actor, request)
    assert acknowledged is None or acknowledged == saved
    assert saved.id == request.id
    assert service.record_decision(actor, request) == saved
    assert _counts(base[8]) == (1, 1, 1)


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_aborted_attempt_retry_starts_clean_transaction(decision_env, sqlstate):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)

    def inject(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO DECISION_BASIS_REVIEWS"):
            conn.execute(
                text(
                    f"DO $$ BEGIN RAISE EXCEPTION 'TEST ONLY abort' "
                    f"USING ERRCODE='{sqlstate}'; END $$"
                )
            )

    event.listen(base[8], "before_cursor_execute", inject)
    try:
        with pytest.raises(ResearchBaseError):
            service.record_decision(actor, request)
        assert _counts(base[8]) == (0, 0, 0)
    finally:
        event.remove(base[8], "before_cursor_execute", inject)
    result = service.record_decision(actor, request)
    assert result.id == request.id
    assert _counts(base[8]) == (1, 1, 1)


def test_different_independent_actor_cannot_replace_or_impersonate_replay(decision_env):
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    service, _, actor, _, base = decision_env
    _review(decision_env)
    other_id = uuid4()
    with base[8].begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        _add_owner(
            conn,
            actor_id=other_id,
            project_id=base[5],
            now=now,
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    other = replace(
        actor,
        actor_id=other_id,
        subject_value=str(other_id.int % 1_000_000),
        credential_id=f"uid:{other_id.int}",
    )
    base[9].principals[other_id] = other
    request = _command(decision_env)
    result = service.record_decision(actor, request)
    for candidate, code in (
        (request, ErrorCode.FORBIDDEN),
        (replace(request, id=uuid4()), ErrorCode.IDEMPOTENCY_CONFLICT),
    ):
        with pytest.raises(ResearchBaseError) as denied:
            service.record_decision(other, candidate)
        assert denied.value.code is code
    assert service.record_decision(actor, request) == result
    assert _counts(base[8]) == (1, 1, 1)


def test_authority_writer_first_real_table_wait_refreshes_role(decision_env, normal_sql_role):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as writer:
            _normal(writer, normal_sql_role)
            pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            row = writer.execute(
                text("""UPDATE project_role_assignments
              SET effective_until=clock_timestamp(),row_version=row_version+1
              WHERE actor_id=:actor AND project_id=:project AND effective_until IS NULL
              RETURNING id,effective_until"""),
                {"actor": actor.actor_id, "project": base[5]},
            ).one()
            writer.execute(
                text("""INSERT INTO project_role_events
              (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
              VALUES (:id,:role,:actor,'CLOSED',:until,'TEST ONLY concurrent closure',:request)"""),
                {
                    "id": uuid4(),
                    "role": row.id,
                    "actor": actor.actor_id,
                    "until": row.effective_until,
                    "request": uuid4(),
                },
            )
            pending = pool.submit(service.record_decision, actor, _command(decision_env))
            witness = _wait_for_pg_blocker(base[8], pid, "relation")
            assert "LOCK TABLE" in witness["query"]
            assert witness["relation"] in {"project_role_assignments", "projects"}
            assert not pending.done()
        with pytest.raises(ResearchBaseError) as denied:
            pending.result(timeout=10)
        assert denied.value.code is ErrorCode.FORBIDDEN
    assert _counts(base[8]) == (0, 0, 0)


@pytest.mark.parametrize("first", ["governance", "decision"])
def test_upstream_impact_writer_and_decision_actual_table_wait_both_orders(decision_env, first):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)
    held, release = Event(), Event()
    pids = []
    prefix = (
        "INSERT INTO IMPACT_TARGETS" if first == "governance" else "INSERT INTO DECISION_RECORDS"
    )

    def pause(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(prefix) and not held.is_set():
            pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(15)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            leading = (
                pool.submit(_stale, decision_env)
                if first == "governance"
                else pool.submit(service.record_decision, actor, request)
            )
            try:
                assert held.wait(10), "leading transaction did not write"
                following = (
                    pool.submit(service.record_decision, actor, request)
                    if first == "governance"
                    else pool.submit(_stale, decision_env)
                )
                witness = _wait_for_pg_blocker(base[8], pids[0], "relation")
                assert witness["relation"] in {
                    "audit_findings",
                    "impact_assessments",
                    "impact_targets",
                }
                assert not following.done()
            finally:
                release.set()
            if first == "governance":
                leading.result(timeout=10)
                with pytest.raises(ResearchBaseError) as denied:
                    following.result(timeout=10)
                assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
                assert _counts(base[8]) == (0, 0, 0)
            else:
                saved = leading.result(timeout=10)
                following.result(timeout=10)
                assert service.record_decision(actor, request) == saved
                assert _counts(base[8]) == (1, 1, 1)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)
