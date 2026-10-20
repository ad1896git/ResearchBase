"""Owner-approved Basic Approval PostgreSQL boundary and history tests."""

import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.approval import (
    ApprovalService,
    DecideApprovalCommand,
    RequestApprovalCommand,
)
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B09_SHARE_SQL
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_pr2_00_ownership import _add_owner
from tests.integration.phase2.test_pr2_15_decision import (
    _command,
    _review,
    _stale,
)
from tests.integration.phase2.test_pr2_15_decision import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_15_decision import (
    decision_env as _decision_env,
)
from tests.integration.phase2.test_pr2_15_decision import (
    phase2_database_url as _database_url,
)

conclusion_env = _conclusion_env
decision_env = _decision_env
phase2_database_url = _database_url

pytestmark = pytest.mark.integration


def _actor(env):
    base = env[-1]
    identity = uuid4()
    with base[8].begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        _add_owner(
            conn,
            actor_id=identity,
            project_id=base[5],
            now=now,
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    actor = replace(
        env[2],
        actor_id=identity,
        subject_value=str(identity.int % 1_000_000),
        credential_id=f"uid:{identity.int}",
    )
    base[9].principals[identity] = actor
    return actor


@pytest.fixture
def approval_env(decision_env):
    env = decision_env
    review = _review(env)
    basis = env[0].record_decision(env[2], _command(env))
    requester = _actor(env)
    approver = _actor(env)
    base = env[-1]
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(
            env[2], base[5], approver.actor_id, "APPROVER", "TEST ONLY approval authority", uuid4()
        )
    )
    service = ApprovalService(base[1], base[9], base[2])
    request = RequestApprovalCommand(uuid4(), base[5], env[3].version_id, basis.id, (review.id,))
    return service, requester, approver, request, env


def _decide(request, outcome="APPROVE", **changes):
    return DecideApprovalCommand(
        uuid4(),
        request.project_id,
        request.id,
        outcome,
        "TEST ONLY independent approval",
        **changes,
    )


def _counts(env):
    with env[-1][-1][8].connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
            for t in (
                "approval_requests",
                "approval_request_reviews",
                "approval_request_events",
                "approval_decisions",
                "approval_grants",
                "approval_grant_events",
            )
        )


def test_approval_atomic_history_and_replay(approval_env):
    service, requester, approver, command, _ = approval_env
    request = service.request_approval(requester, command)
    assert request.status == "PENDING" and len(request.event_ids) == 1
    assert service.request_approval(requester, command) == request
    decision_command = _decide(command)
    result = service.decide_approval(approver, decision_command)
    assert result.grant and result.grant.usable
    assert result.grant.valid_until == result.decided_at + timedelta(days=30)
    assert result.grant.max_uses == 1
    assert service.decide_approval(approver, decision_command) == result
    assert service.get_decision(requester, command.project_id, result.id) == result
    assert service.get_grant(requester, command.project_id, result.grant.id) == result.grant
    assert service.get_request(requester, command.project_id, command.id).status == "DECIDED"
    assert _counts(approval_env) == (1, 1, 2, 1, 1, 1)


def test_rejection_scope_and_pending_bypass(approval_env):
    service, requester, approver, command, _ = approval_env
    service.request_approval(requester, command)
    result = service.decide_approval(approver, _decide(command, "REJECT"))
    assert result.grant is None
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(requester, replace(command, id=uuid4()))
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    assert _counts(approval_env) == (1, 1, 2, 1, 0, 0)


def test_conflicts_and_independence(approval_env):
    service, requester, approver, command, env = approval_env
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(env[2], command)
    assert denied.value.code is ErrorCode.CONFLICT_OF_INTEREST
    service.request_approval(requester, command)
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(requester, replace(command, id=uuid4()))
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(requester, _decide(command))
    assert denied.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(approver, command)
    assert denied.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError):
        service.request_approval(requester, replace(command, basis_decision_id=uuid4()))
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def test_current_stale_gate_and_historical_replay(approval_env):
    service, requester, approver, command, env = approval_env
    saved = service.request_approval(requester, command)
    decision_command = _decide(command)
    result = service.decide_approval(approver, decision_command)
    _stale(env)
    assert service.request_approval(requester, command).id == saved.id
    replay = service.decide_approval(approver, decision_command)
    assert replay.content_hash == result.content_hash
    assert replay.grant and not replay.grant.usable
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(requester, replace(command, id=uuid4()))
    assert denied.value.code is ErrorCode.APPROVAL_TARGET_STALE
    assert _counts(approval_env) == (1, 1, 2, 1, 1, 1)


def test_later_blocking_review_denies_pending_decision(approval_env):
    from researchbase.application.internal_review import ReviewIssueRequest

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    _review(env, "REJECT", (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "TEST ONLY blocker"),))
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(approver, _decide(command))
    assert denied.value.code is ErrorCode.APPROVAL_GATE_FAILED
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("outcome", ["APPROVE", "REJECT", "APPROVE_WITH_CONDITIONS"])
def test_all_outcomes_and_changed_replay(approval_env, outcome):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    with env[-1][8].connect() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    decision_command = _decide(
        command,
        outcome,
        valid_until=(now + timedelta(hours=1) if outcome == "APPROVE_WITH_CONDITIONS" else None),
    )
    result = service.decide_approval(approver, decision_command)
    assert (result.grant is None) == (outcome == "REJECT")
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(approver, replace(decision_command, rationale="changed"))
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(approver, replace(decision_command, id=uuid4()))
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.parametrize("delta", [timedelta(days=-1), timedelta(0), timedelta(days=31)])
def test_finite_expiry_gate(approval_env, delta):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    with env[-1][8].connect() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(
            approver, _decide(command, "APPROVE_WITH_CONDITIONS", valid_until=now + delta)
        )
    assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def test_saved_basis_and_later_unfavorable_review(approval_env):
    service, requester, approver, command, env = approval_env
    later = _review(env, "REJECT")
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(
            requester, replace(command, review_ids=command.review_ids + (later.id,))
        )
    assert denied.value.code is ErrorCode.DECISION_BASIS_INVALID
    result = service.request_approval(requester, command)
    assert tuple(ref.id for ref in result.reviews) == command.review_ids
    assert service.decide_approval(approver, _decide(command)).grant is not None


def test_live_authority_loss_stales_grant_atomically(approval_env):
    from researchbase.application.phase2_identity import CloseProjectRole

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    decision_command = _decide(command)
    result = service.decide_approval(approver, decision_command)
    identity, _, _ = identity_service(str(env[-1][8].url))
    with env[-1][8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND role='APPROVER'"
            ),
            {"actor": approver.actor_id},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(env[2], command.project_id, role, "TEST ONLY immediate loss", uuid4())
    )
    replay = service.decide_approval(approver, decision_command)
    assert replay.content_hash == result.content_hash
    assert replay.grant and replay.grant.status == "STALE" and not replay.grant.usable
    assert len(replay.grant.event_ids) == 2
    assert _counts(approval_env) == (1, 1, 2, 1, 1, 2)


@pytest.mark.parametrize(
    "table",
    [
        "approval_requests",
        "approval_request_reviews",
        "approval_request_events",
        "approval_decisions",
        "approval_grants",
        "approval_grant_events",
    ],
)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_normal_role_history_guards(approval_env, table, operation):
    from sqlalchemy.exc import DBAPIError

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    service.decide_approval(approver, _decide(command))
    engine = env[-1][8]
    role = "test_approval_" + uuid4().hex
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        key = "request_id" if table == "approval_request_reviews" else "id"
        statement = (
            f"DELETE FROM {table}" if operation == "DELETE" else (f"UPDATE {table} SET {key}={key}")
        )
        with pytest.raises(DBAPIError) as denied:
            conn.execute(text(statement))
        assert getattr(denied.value.orig, "sqlstate", None) == "P17F1"
        tx.rollback()
    assert _counts(approval_env) == (1, 1, 2, 1, 1, 1)


@pytest.mark.parametrize("failure_point", ["approval_decisions", "approval_grants"])
def test_failure_rolls_back_all_success_events(approval_env, failure_point):
    from sqlalchemy import event

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    engine = env[-1][8]

    def inject(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO " + failure_point):
            conn.execute(
                text("DO $$ BEGIN RAISE EXCEPTION 'test abort' USING ERRCODE='P17F2'; END $$")
            )

    event.listen(engine, "before_cursor_execute", inject)
    try:
        with pytest.raises(ResearchBaseError):
            service.decide_approval(approver, _decide(command))
    finally:
        event.remove(engine, "before_cursor_execute", inject)
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)
    assert service.decide_approval(approver, _decide(command)).grant


def test_concurrent_outcomes_one_decision_and_grant(approval_env):
    from concurrent.futures import ThreadPoolExecutor

    service, requester, approver, command, _ = approval_env
    service.request_approval(requester, command)

    def decide(outcome):
        try:
            return service.decide_approval(approver, _decide(command, outcome))
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, ["APPROVE", "REJECT"]))
    assert results.count(ErrorCode.IDEMPOTENCY_CONFLICT) == 1
    counts = _counts(approval_env)
    assert counts[:4] == (1, 1, 2, 1) and counts[4] in (0, 1) and counts[5] == counts[4]


def test_downgrade_preserves_history(approval_env):
    from alembic import command as alembic_command
    from alembic.config import Config
    from sqlalchemy.exc import DBAPIError

    service, requester, _, request, env = approval_env
    saved = service.request_approval(requester, request)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(env[-1][8].url))
    with pytest.raises(DBAPIError):
        alembic_command.downgrade(config, "0044_pr2_15_revision_action")
    assert service.get_request(requester, request.project_id, request.id) == saved


@pytest.mark.parametrize("expiry_kind", ["credential", "role"])
def test_actual_target_wait_crosses_expiry(approval_env, expiry_kind):
    from concurrent.futures import ThreadPoolExecutor
    from time import monotonic, sleep

    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    engine = env[-1][8]
    with engine.begin() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        if expiry_kind == "role":
            role = conn.execute(
                text(
                    "UPDATE project_role_assignments SET effective_until=:expiry, "
                    "row_version=row_version+1 WHERE actor_id=:actor AND role='APPROVER' "
                    "RETURNING id"
                ),
                {"expiry": expiry, "actor": approver.actor_id},
            ).scalar_one()
            conn.execute(
                text("""INSERT INTO project_role_events
                (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                VALUES (:id,:role,:actor,'CLOSED',:at,'TEST ONLY expiry',:request)"""),
                {
                    "id": uuid4(),
                    "role": role,
                    "actor": approver.actor_id,
                    "at": expiry,
                    "request": uuid4(),
                },
            )
    if expiry_kind == "credential":
        original = env[-1][9].is_valid
        env[-1][9].is_valid = lambda principal, at: original(principal, at) and (
            principal.actor_id != approver.actor_id or at < expiry
        )
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        tx = holder.begin()
        holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(
            text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
            {"id": command.scientific_conclusion_version_id},
        )
        future = pool.submit(service.decide_approval, approver, _decide(command))
        witness = _wait_for_pg_blocker(engine, holder_pid, "transactionid")
        assert witness["observed_at"] < expiry and witness["pid"] != holder_pid
        deadline = monotonic() + 5
        while holder.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
            assert monotonic() < deadline
            sleep(0.01)
        released = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
        assert released >= expiry
        tx.commit()
        with pytest.raises(ResearchBaseError) as denied:
            future.result(timeout=10)
        assert denied.value.code is ErrorCode.FORBIDDEN
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("approval_first", [False, True])
def test_review_insert_commit_orders_are_observed(approval_env, approval_first):
    from concurrent.futures import ThreadPoolExecutor

    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    engine = env[-1][8]
    if approval_first:
        saved = service.decide_approval(approver, _decide(command))
        _review(env, "REJECT", (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "TEST ONLY later"),))
        assert saved.grant
        current = service.get_grant(requester, command.project_id, saved.grant.id)
        assert not current.usable and current.unusable_code == ErrorCode.APPROVAL_GATE_FAILED.value
    else:
        # An actual uncommitted zero-Issue review INSERT participates in target coordination.
        reviewer = env[2]
        review_id = uuid4()
        with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
            tx = holder.begin()
            holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            digest = env[1]._hash(
                command.project_id,
                "ScientificConclusionVersion",
                command.scientific_conclusion_version_id,
                service.get_request(requester, command.project_id, command.id).target_content_hash,
                reviewer.actor_id,
                "SCIENTIFIC",
                "UNCERTAIN",
                "TEST ONLY zero issue",
            )
            holder.execute(
                text("""INSERT INTO internal_review_records
                (id,project_id,scientific_conclusion_version_id,target_content_hash,
                 reviewer_actor_id,review_type,recommendation,summary,created_at,content_hash,hash_scheme)
                 SELECT :id,project_id,scientific_conclusion_version_id,target_content_hash,
                   :actor,'SCIENTIFIC','UNCERTAIN','TEST ONLY zero issue',
                   clock_timestamp(),:hash,'sha256-cjson-v1'
                 FROM approval_requests WHERE id=:request"""),
                {
                    "id": review_id,
                    "actor": reviewer.actor_id,
                    "hash": digest,
                    "request": command.id,
                },
            )
            future = pool.submit(service.decide_approval, approver, _decide(command))
            witness = _wait_for_pg_blocker(engine, holder_pid, "relation")
            assert witness["pid"] != holder_pid
            tx.commit()
            result = future.result(timeout=10)
            assert result.grant and result.grant.usable
        # Later review remains outside the immutable saved Decision-backed set.
        assert (
            tuple(
                r.id for r in service.get_request(requester, command.project_id, command.id).reviews
            )
            == command.review_ids
        )


def test_empty_downgrade_upgrade_and_catalog(approval_env):
    from alembic import command as alembic_command
    from alembic.config import Config

    service, requester, _, request, env = approval_env
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(env[-1][8].url))
    alembic_command.downgrade(config, "0044_pr2_15_revision_action")
    alembic_command.upgrade(config, "head")
    with env[-1][8].connect() as conn:
        fks = (
            conn.execute(
                text("""SELECT confdeltype FROM pg_constraint WHERE contype='f'
            AND conrelid IN ('approval_requests'::regclass,'approval_decisions'::regclass,
              'approval_grants'::regclass,'approval_request_reviews'::regclass,
              'approval_request_events'::regclass,'approval_grant_events'::regclass)""")
            )
            .scalars()
            .all()
        )
        assert fks and set(fks) == {"r"}
    assert service.request_approval(requester, request).id == request.id


@pytest.mark.parametrize(
    "invalid",
    [
        "stale",
        "review_hash",
        "decision_hash",
        "owner_only",
        "same_actor",
        "future_basis",
        "decider_author",
        "decider_later_actor",
    ],
)
def test_normal_sql_cannot_bypass_approval_gate(approval_env, invalid):
    from sqlalchemy.exc import DBAPIError

    from researchbase.domain.approval import approval_decision_material
    from researchbase.foundation.hashing import sha256_canonical_json

    service, requester, approver, command, env = approval_env
    saved = service.request_approval(requester, command)
    engine = env[-1][8]
    if invalid == "stale":
        _stale(env)
    elif invalid in {"review_hash", "decision_hash"}:
        table = "internal_review_records" if invalid == "review_hash" else "decision_records"
        identity = command.review_ids[0] if invalid == "review_hash" else command.basis_decision_id
        # Simulate preexisting corrupt history; SQL gate must detect it even as normal role.
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
            conn.execute(
                text(f"UPDATE {table} SET content_hash=:hash WHERE id=:id"),
                {"hash": "a" * 64, "id": identity},
            )
            conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    if invalid == "future_basis":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE decision_records DISABLE TRIGGER USER"))
            conn.execute(
                text("UPDATE decision_records SET decided_at=clock_timestamp()+interval '1 day'")
            )
            conn.execute(text("ALTER TABLE decision_records ENABLE TRIGGER USER"))
    if invalid in {"decider_author", "decider_later_actor"}:
        from researchbase.domain.decision import decision_content_material

        bad_actor = env[-1][3].actor_id if invalid == "decider_author" else requester.actor_id
        with engine.begin() as conn:
            row = dict(
                conn.execute(
                    text("SELECT * FROM decision_records WHERE id=:id"),
                    {"id": command.basis_decision_id},
                )
                .mappings()
                .one()
            )
            content = str(
                sha256_canonical_json(
                    decision_content_material(
                        row["project_id"],
                        row["decision_type"],
                        row["question"],
                        row["decision"],
                        row["rationale"],
                        bad_actor,
                        row["basis_set_hash"],
                    )
                )
            )
            conn.execute(text("ALTER TABLE decision_records DISABLE TRIGGER USER"))
            conn.execute(
                text(
                    "UPDATE decision_records SET decided_by=:actor,content_hash=:hash WHERE id=:id"
                ),
                {"actor": bad_actor, "hash": content, "id": command.basis_decision_id},
            )
            conn.execute(text("ALTER TABLE decision_records ENABLE TRIGGER USER"))
    candidate = requester if invalid in {"owner_only", "same_actor"} else approver
    if invalid == "same_actor":
        identity, _, _ = identity_service(str(engine.url))
        identity.assign_project_role(
            AssignProjectRole(
                env[2],
                command.project_id,
                requester.actor_id,
                "APPROVER",
                "TEST ONLY conflict",
                uuid4(),
            )
        )
    digest = str(
        sha256_canonical_json(
            approval_decision_material(
                command.id,
                command.scientific_conclusion_version_id,
                saved.target_content_hash,
                "APPROVE",
                None,
                False,
                "TEST ONLY SQL gate",
                candidate.actor_id,
            )
        )
    )
    role = "test_approval_" + uuid4().hex
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        with pytest.raises(DBAPIError) as denied:
            conn.execute(
                text("""INSERT INTO approval_decisions
                (id,approval_request_id,decision,valid_until,requires_current_author_consent,
                 rationale,decided_by,decided_at,content_hash,hash_scheme)
                VALUES (:id,:request,'APPROVE',NULL,FALSE,'TEST ONLY SQL gate',:actor,
                  '2100-01-01T00:00:00Z',:hash,'sha256-cjson-v1')"""),
                {"id": uuid4(), "request": command.id, "actor": candidate.actor_id, "hash": digest},
            )
        assert getattr(denied.value.orig, "sqlstate", None) in {
            "P16T1",
            "P17F2",
            "P16B1",
            "P16A1",
            "P16C1",
        }
        tx.rollback()
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def test_pending_other_target_cannot_bypass_rejection(approval_env):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    scientific, _, _, author, _, project, claim, _, _, _ = env[-1]
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    target = scientific.create(
        author,
        project,
        "TEST ONLY second conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    other_env = (env[0], env[1], env[2], target, env[-1])
    review = _review(other_env)
    basis = env[0].record_decision(env[2], _command(other_env))
    other = RequestApprovalCommand(uuid4(), project, target.version_id, basis.id, (review.id,))
    service.request_approval(requester, other)
    service.decide_approval(approver, _decide(other, "REJECT"))
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(approver, _decide(command))
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    assert _counts(approval_env) == (2, 2, 3, 1, 0, 0)


@pytest.mark.parametrize(
    "number", [-0.0, 0.0, 1.0, 1e-6, 1e-7, 1e15, 1.25e15, 1e16, 1.23456789012345]
)
def test_sql_float_spelling_preserves_python_canonical_hash(approval_env, number):
    engine = approval_env[-1][-1][8]
    with engine.connect() as conn:
        rendered = conn.execute(
            text("SELECT pr216_float(:number)"), {"number": number}
        ).scalar_one()
        serialized, stored = conn.execute(
            text("SELECT pr216_cjson(CAST(:payload AS jsonb)), CAST(:payload AS jsonb)"),
            {"payload": json.dumps({"z": [number], "é": number, "a": number})},
        ).one()
    assert rendered == repr(number)
    assert serialized == canonical_json_text(stored)


@pytest.mark.parametrize(
    "invalid", ["measurements", "metric_definition_versions", "experiment_spec_versions"]
)
def test_normal_sql_rejects_forged_frozen_leaf_hashes(approval_env, invalid):
    from sqlalchemy.exc import DBAPIError

    service, requester, _, command, env = approval_env
    service.request_approval(requester, command)
    engine = env[-1][8]
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {invalid} DISABLE TRIGGER USER"))
        conn.execute(text(f"UPDATE {invalid} SET content_hash=:hash"), {"hash": "a" * 64})
        conn.execute(text(f"ALTER TABLE {invalid} ENABLE TRIGGER USER"))
    role = "test_approval_" + uuid4().hex
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        with pytest.raises(DBAPIError) as denied:
            conn.execute(
                text("SELECT pr216_material_gate(r) FROM approval_requests r WHERE id=:id"),
                {"id": command.id},
            )
        assert getattr(denied.value.orig, "sqlstate", None) == "P17F2"
        tx.rollback()


@pytest.mark.parametrize("support", ["direct", "snapshot"])
def test_literature_closure_has_same_application_and_sql_gate(approval_env, support):
    from researchbase.application.scientific_conclusion import (
        ClaimInputRequest,
        LiteratureInputRequest,
    )
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, requester, approver, _, env = approval_env
    scientific, _, evidence, author, reviewer, project, claim, source, _, _ = env[-1]
    item = evidence.create(author, project, source, "improved recall", uuid4())
    from uuid import UUID

    evidence_id = UUID(item["id"])
    evidence.review(
        reviewer, project, evidence_id, "VERIFIED", "TEST ONLY independent support", uuid4()
    )
    if support == "snapshot":
        snapshot = evidence.snapshot(
            author,
            project,
            "ClaimVersion",
            claim,
            [
                {
                    "evidence_id": str(evidence_id),
                    "relation_type": "SUPPORTS",
                    "qualification": "TEST ONLY relevance",
                }
            ],
            uuid4(),
        )
        claims = (ClaimInputRequest(claim, "SUPPORTS", UUID(snapshot["id"])),)
        literature = ()
    else:
        claims = ()
        literature = (LiteratureInputRequest(evidence_id, "SUPPORTS"),)
    target = scientific.create(
        author,
        project,
        "TEST ONLY literature conclusion",
        SCOPE,
        "MODERATE",
        None,
        claims,
        literature,
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    updated = (env[0], env[1], env[2], target, env[-1])
    review = _review(updated)
    basis = env[0].record_decision(env[2], _command(updated))
    request = RequestApprovalCommand(uuid4(), project, target.version_id, basis.id, (review.id,))
    service.request_approval(requester, request)
    result = service.decide_approval(approver, _decide(request))
    assert result.grant and result.grant.usable


def test_navigation_supersession_preserves_grant_until_new_approval_target_selected(approval_env):
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    original = service.decide_approval(approver, _decide(command))
    scientific, _, _, author, _, project, claim, _, _, _ = env[-1]
    successor = scientific.revise(
        author,
        project,
        env[3].conclusion_id,
        "TEST ONLY newer navigation",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, successor.conclusion_id, successor.version_id, uuid4())
    assert original.grant
    current = service.get_grant(requester, project, original.grant.id)
    assert current.usable and current.target_content_hash == original.grant.target_content_hash
    updated = (env[0], env[1], env[2], successor, env[-1])
    review = _review(updated)
    basis = env[0].record_decision(env[2], _command(updated))
    request = RequestApprovalCommand(uuid4(), project, successor.version_id, basis.id, (review.id,))
    service.request_approval(requester, request)
    stale = service.get_grant(requester, project, original.grant.id)
    assert stale.status == "STALE" and not stale.usable and len(stale.event_ids) == 2


def test_archived_project_preserves_history_but_grant_is_unusable(approval_env):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    result = service.decide_approval(approver, _decide(command))
    assert result.grant
    with env[-1][8].begin() as conn:
        conn.execute(
            text(
                "UPDATE projects SET lifecycle_status='ARCHIVED',row_version=row_version+1 "
                "WHERE id=:id"
            ),
            {"id": command.project_id},
        )
    assert service.get_request(requester, command.project_id, command.id).status == "DECIDED"
    current = service.get_grant(requester, command.project_id, result.grant.id)
    assert not current.usable and current.unusable_code == ErrorCode.APPROVAL_GATE_FAILED.value
    assert current.target_content_hash == result.grant.target_content_hash


@pytest.mark.parametrize("attack", ["shadow_actor", "manual_stale", "nested_stale"])
def test_normal_sql_cannot_shadow_authority_or_invoke_uncontracted_lifecycle(approval_env, attack):
    from sqlalchemy.exc import DBAPIError

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    result = service.decide_approval(approver, _decide(command))
    assert result.grant
    role = "test_approval_" + uuid4().hex
    with env[-1][8].connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        if attack == "shadow_actor":
            conn.execute(text("CREATE TEMP TABLE actors AS SELECT * FROM public.actors"))
            conn.execute(
                text("UPDATE pg_temp.actors SET actor_type='AGENT' WHERE id=:id"),
                {"id": approver.actor_id},
            )
            conn.execute(
                text(
                    "CREATE TEMP TABLE project_role_assignments AS "
                    "SELECT * FROM public.project_role_assignments"
                )
            )
            conn.execute(
                text(
                    "UPDATE pg_temp.project_role_assignments SET role='APPROVER' WHERE actor_id=:id"
                ),
                {"id": requester.actor_id},
            )
            assert not conn.execute(
                text("SELECT public.pr216_approver_active(:actor,:project)"),
                {"actor": requester.actor_id, "project": command.project_id},
            ).scalar_one()
            # Canonical authority reads are anchored, independent of temporary shadows.
            assert conn.execute(
                text("SELECT public.pr216_approver_active(:actor,:project)"),
                {"actor": approver.actor_id, "project": command.project_id},
            ).scalar_one()
        else:
            if attack == "nested_stale":
                conn.execute(text("CREATE TEMP TABLE nested_grant_attempt(value INT)"))
                conn.execute(
                    text(f"""CREATE FUNCTION pg_temp.attempt_stale() RETURNS trigger
                    LANGUAGE plpgsql AS $$ BEGIN
                      UPDATE public.approval_grants SET status='STALE'
                        WHERE id='{result.grant.id}'; RETURN NULL;
                    END $$""")
                )
                conn.execute(
                    text(
                        "CREATE TRIGGER nested_stale AFTER INSERT ON "
                        "pg_temp.nested_grant_attempt FOR EACH ROW "
                        "EXECUTE FUNCTION pg_temp.attempt_stale()"
                    )
                )
                statement = "INSERT INTO pg_temp.nested_grant_attempt VALUES (1)"
            else:
                statement = (
                    f"UPDATE public.approval_grants SET status='STALE' WHERE id='{result.grant.id}'"
                )
            with pytest.raises(DBAPIError) as denied:
                conn.execute(text(statement))
            assert getattr(denied.value.orig, "sqlstate", None) == "P17F1"
        tx.rollback()
    assert _counts(approval_env) == (1, 1, 2, 1, 1, 1)


def test_grant_utc_thirty_days_is_independent_of_session_dst(approval_env):
    from sqlalchemy import event

    service, requester, approver, command, env = approval_env
    engine = env[-1][8]

    def timezone(raw, record, proxy):
        before = raw.autocommit
        raw.autocommit = True
        try:
            with raw.cursor() as cursor:
                cursor.execute("SET TIME ZONE 'America/New_York'")
        finally:
            raw.autocommit = before

    event.listen(engine, "checkout", timezone)
    try:
        service.request_approval(requester, command)
        result = service.decide_approval(approver, _decide(command))
        assert result.grant
        assert result.grant.valid_until - result.decided_at == timedelta(days=30)
        assert result.decided_at.utcoffset() == timedelta(0)
        assert result.grant.valid_until.utcoffset() == timedelta(0)
        assert service.get_grant(requester, command.project_id, result.grant.id) == result.grant
    finally:
        event.remove(engine, "checkout", timezone)


def _normal_sql_decision(conn, command, actor, rationale, digest):
    conn.execute(
        text("""INSERT INTO approval_decisions
        (id,approval_request_id,decision,valid_until,requires_current_author_consent,
         rationale,decided_by,decided_at,content_hash,hash_scheme)
        VALUES (:id,:request,'APPROVE',NULL,FALSE,:rationale,:actor,
          clock_timestamp(),:hash,'sha256-cjson-v1')"""),
        {
            "id": uuid4(),
            "request": command.id,
            "actor": actor,
            "rationale": rationale,
            "hash": digest,
        },
    )


def _normal_sql_role(conn):
    conn.execute(text(B09_SHARE_SQL))
    role = "test_approval_" + uuid4().hex
    conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER"))
    conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
    conn.execute(
        text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
    )
    conn.execute(text(f"SET LOCAL ROLE {role}"))


@pytest.mark.parametrize("rationale", ["Cafe\u0301", "\t\n", "\u0085\u2003\u3000"])
def test_normal_sql_denies_noncanonical_or_blank_rationale(approval_env, rationale):
    from sqlalchemy.exc import DBAPIError

    from researchbase.domain.approval import approval_decision_material

    service, requester, approver, command, env = approval_env
    saved = service.request_approval(requester, command)
    material = approval_decision_material(
        command.id,
        command.scientific_conclusion_version_id,
        saved.target_content_hash,
        "APPROVE",
        None,
        False,
        "TEST ONLY valid rationale",
        approver.actor_id,
    )
    material["rationale"] = rationale
    with env[-1][8].connect() as conn:
        tx = conn.begin()
        _normal_sql_role(conn)
        # Match the raw SQL hash: rejection must come from the text constraint,
        # rather than a mismatched digest or incomplete grant at commit.
        digest = conn.execute(
            text("SELECT pr216_hash(CAST(:material AS jsonb))"),
            {"material": json.dumps(material)},
        ).scalar_one()
        with pytest.raises(DBAPIError) as denied:
            _normal_sql_decision(conn, command, approver.actor_id, rationale, digest)
        assert getattr(denied.value.orig, "sqlstate", None) == "23514"
        tx.rollback()
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def test_normal_sql_request_denies_future_credential_binding(approval_env):
    from sqlalchemy.exc import DBAPIError

    service, requester, _, command, env = approval_env
    service.request_approval(requester, command)
    with env[-1][8].begin() as conn:
        # Simulate an unstarted persisted binding, independently of role validity.
        conn.execute(text("ALTER TABLE actor_subject_bindings DISABLE TRIGGER USER"))
        conn.execute(
            text(
                "UPDATE actor_subject_bindings SET bound_at=clock_timestamp()+interval '1 day' "
                "WHERE actor_id=:actor"
            ),
            {"actor": requester.actor_id},
        )
        conn.execute(text("ALTER TABLE actor_subject_bindings ENABLE TRIGGER USER"))
    with env[-1][8].connect() as conn:
        tx = conn.begin()
        _normal_sql_role(conn)
        with pytest.raises(DBAPIError) as denied:
            conn.execute(
                text("""INSERT INTO approval_requests
                SELECT :id,project_id,scientific_conclusion_version_id,manuscript_version_id,
                  target_content_hash,target_hash_scheme,approval_purpose,basis_decision_id,
                  requested_by,clock_timestamp(),'PENDING',NULL,NULL
                FROM approval_requests WHERE id=:request"""),
                {"id": uuid4(), "request": command.id},
            )
        assert getattr(denied.value.orig, "sqlstate", None) == "P16A1"
        tx.rollback()
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("caller", ["application", "sql"])
def test_new_target_selection_denies_late_approval_of_old_pending_request(approval_env, caller):
    from sqlalchemy.exc import DBAPIError

    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    scientific, _, _, author, _, project, claim, _, _, _ = env[-1]
    target = scientific.create(
        author,
        project,
        "TEST ONLY newer approval target",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    updated = (env[0], env[1], env[2], target, env[-1])
    review = _review(updated)
    basis = env[0].record_decision(env[2], _command(updated))
    other = RequestApprovalCommand(uuid4(), project, target.version_id, basis.id, (review.id,))
    service.request_approval(requester, other)
    if caller == "application":
        with pytest.raises(ResearchBaseError) as denied:
            service.decide_approval(approver, _decide(command))
        assert denied.value.code is ErrorCode.APPROVAL_TARGET_STALE
    else:
        with env[-1][8].connect() as conn:
            tx = conn.begin()
            _normal_sql_role(conn)
            with pytest.raises(DBAPIError) as sql_denied:
                _normal_sql_decision(
                    conn, command, approver.actor_id, "TEST ONLY old target", "a" * 64
                )
            assert getattr(sql_denied.value.orig, "sqlstate", None) == "P16T1"
            tx.rollback()
    assert _counts(approval_env) == (2, 2, 2, 0, 0, 0)
    current = service.decide_approval(approver, _decide(other))
    assert current.grant and current.grant.usable


def test_b09_rejection_fences_other_target_older_pending_request(approval_env):
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    scientific, _, _, author, _, project, claim, _, _, _ = env[-1]
    target = scientific.create(
        author,
        project,
        "TEST ONLY rejection fence target",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    updated = (env[0], env[1], env[2], target, env[-1])
    review = _review(updated)
    basis = env[0].record_decision(env[2], _command(updated))
    other = RequestApprovalCommand(uuid4(), project, target.version_id, basis.id, (review.id,))
    service.request_approval(requester, other)
    service.decide_approval(approver, _decide(other, "REJECT"))
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(approver, _decide(command))
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    assert service.get_request(requester, project, command.id).status == "PENDING"
    with env[-1][1]() as uow:
        uow.configure_approval_transaction(readonly=True)
        assert uow.approval.rejected(project, "INTERNAL_SCIENTIFIC_RELEASE")
        assert not uow.approval.rejected(project, "READY_FOR_SUBMISSION")
        assert not uow.approval.rejected(project, "PREPARE_SUBMISSION")
        assert not uow.approval.rejected(uuid4(), "INTERNAL_SCIENTIFIC_RELEASE")
