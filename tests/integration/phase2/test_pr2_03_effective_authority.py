# SQL counterexamples preserve literal statements for audit.
# ruff: noqa: E501
"""Current durable authority, not role-history row order, governs commands."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material,
)

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    LiteratureSearchPlanService,
)
from researchbase.application.phase2_identity import (
    AssignProjectRole,
    CloseProjectRole,
    ProvisionActor,
    ProvisioningAttestation,
    RevokeActorSubjectBinding,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def _provision(identity, owner):
    actor = uuid4()
    operator = VerifiedPrincipal(
        uuid4(),
        owner.deployment_id,
        "MTLS_URI",
        f"spiffe://researchbase.test/review-operator/{uuid4()}",
        f"review-operator-{uuid4()}",
        datetime.now(UTC),
    )
    subject = VerifiedSubject(
        owner.deployment_id, "OS_UID", str(uuid4().int), "review-target-credential"
    )
    identity.provision_actor(
        ProvisionActor(
            owner,
            subject,
            actor,
            "review target",
            ProvisioningAttestation(
                actor,
                owner.deployment_id,
                subject.subject_kind,
                subject.subject_value,
                subject.credential_id,
                operator,
                "a" * 64,
                "audit/review-target",
                "review regression",
            ),
            uuid4(),
        )
    )
    return (
        VerifiedPrincipal(
            actor,
            subject.deployment_id,
            subject.subject_kind,
            subject.subject_value,
            subject.credential_id,
            datetime.now(UTC),
        ),
        operator,
    )


def _authority_rows(engine, actor, project):
    with engine.connect() as connection:
        at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        rows = [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT role,effective_from,effective_until FROM project_role_assignments "
                    "WHERE actor_id=:actor AND project_id=:project ORDER BY id"
                ),
                {"actor": actor, "project": project},
            ).mappings()
        ]
    effective = [
        row["role"]
        for row in rows
        if row["effective_from"] <= at
        and (row["effective_until"] is None or at < row["effective_until"])
    ]
    return at, rows, effective


def _lose_owner_authority(engine, owner, project, url):
    identity, _, _ = _identity_service(url)
    target, _ = _provision(identity, owner)
    identity.assign_project_role(
        AssignProjectRole(
            owner, project, target.actor_id, "OWNER", "retain owner coverage", uuid4()
        )
    )
    with engine.connect() as c:
        role = c.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND project_id=:project AND role='OWNER' AND effective_until IS NULL"
            ),
            {"actor": owner.actor_id, "project": project},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(target, project, role, "authority loss regression", uuid4())
    )


@pytest.mark.parametrize(
    "historical,current,allowed",
    [("OWNER", "VIEWER", False), ("VIEWER", "RESEARCHER", True), ("RESEARCHER", "VIEWER", False)],
)
def test_historical_roles_do_not_determine_current_write_authority(
    phase2_database_url, historical, current, allowed, record_property
):
    engine, identity, _, owner, project = _authorized_service(phase2_database_url)
    target, provisioning_operator = _provision(identity, owner)
    old = identity.assign_project_role(
        AssignProjectRole(owner, project, target.actor_id, historical, "old role", uuid4())
    )
    identity.close_project_role(CloseProjectRole(owner, project, old, "close old role", uuid4()))
    identity.assign_project_role(
        AssignProjectRole(owner, project, target.actor_id, current, "current role", uuid4())
    )
    service = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    command = CreateLiteratureSearchPlan(
        target, project, _material(uuid4(), language_scope=()), uuid4()
    )
    if allowed:
        assert service.create(command)["status"] == "DRAFT"
        with engine.connect() as c:
            binding = c.execute(
                text(
                    "SELECT id FROM actor_subject_bindings WHERE actor_id=:actor AND status='ACTIVE'"
                ),
                {"actor": target.actor_id},
            ).scalar_one()
        identity.revoke_actor_subject_binding(
            RevokeActorSubjectBinding(
                provisioning_operator, binding, "revoke current binding", uuid4()
            )
        )
        with pytest.raises(ResearchBaseError) as error:
            service.create(command)
        assert error.value.code is ErrorCode.FORBIDDEN
    else:
        with pytest.raises(ResearchBaseError) as error:
            service.create(command)
        assert error.value.code is ErrorCode.FORBIDDEN
    at, rows, effective = _authority_rows(engine, target.actor_id, project)
    assert effective == [current]
    with engine.connect() as c:
        membership = dict(
            c.execute(
                text(
                    "SELECT id,status,started_at,ended_at FROM project_memberships "
                    "WHERE actor_id=:actor AND project_id=:project"
                ),
                {"actor": target.actor_id, "project": project},
            )
            .mappings()
            .one()
        )
        binding = dict(
            c.execute(
                text(
                    "SELECT id,status,bound_at,revoked_at,operator_credential_id "
                    "FROM actor_subject_bindings WHERE actor_id=:actor"
                ),
                {"actor": target.actor_id},
            )
            .mappings()
            .one()
        )
        binding_events = [
            dict(row)
            for row in c.execute(
                text(
                    "SELECT event_kind,operator_credential_id FROM actor_subject_binding_events "
                    "WHERE binding_id=:binding ORDER BY occurred_at,id"
                ),
                {"binding": binding["id"]},
            ).mappings()
        ]
        plan_count = c.execute(
            text(
                "SELECT count(*) FROM literature_search_plans WHERE project_id=:project AND created_by=:actor"
            ),
            {"project": project, "actor": target.actor_id},
        ).scalar_one()
        receipt_count = c.execute(
            text(
                "SELECT count(*) FROM literature_search_plan_command_receipts WHERE request_id=:request"
            ),
            {"request": command.request_id},
        ).scalar_one()
    assert membership["status"] == "ACTIVE"
    assert plan_count == (1 if allowed else 0)
    assert receipt_count == (1 if allowed else 0)
    record_property(
        "effective_authority",
        json.dumps(
            {
                "rows": rows,
                "effective_at": at,
                "effective_roles": effective,
                "authorization": "ALLOW" if allowed else "DENY",
                "target_actor": target.actor_id,
                "membership": membership,
                "binding": binding,
                "binding_events": binding_events,
                "provisioning_operator": provisioning_operator.actor_id,
                "plan_count": plan_count,
                "receipt_count": receipt_count,
            },
            default=str,
        ),
    )
    engine.dispose()


@pytest.mark.parametrize("attempt", range(1, 6), ids=lambda value: f"run-{value}")
def test_authority_loss_during_observed_project_lock_wait(
    phase2_database_url, record_property, attempt
):
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event
    from time import monotonic
    from unittest.mock import patch

    from researchbase.persistence.literature_search_plan_repository import (
        SqlAlchemyLiteratureSearchPlanRepository,
    )

    engine, identity, _, owner, project = _authorized_service(phase2_database_url)
    target, provisioning_operator = _provision(identity, owner)
    role = identity.assign_project_role(
        AssignProjectRole(
            owner, project, target.actor_id, "RESEARCHER", "current researcher", uuid4()
        )
    )
    service = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    command = CreateLiteratureSearchPlan(
        target, project, _material(uuid4(), language_scope=()), uuid4()
    )
    original = SqlAlchemyLiteratureSearchPlanRepository.lock_project
    original_attempt = service._create_once
    original_authorize = service._authorize
    attempts = []
    pids = Queue()

    def observed_attempt(command):
        trace = {
            "run": attempt,
            "attempt": len(attempts) + 1,
            "backend_pid": None,
            "project_lock_entered": False,
            "postgres_wait_observed": False,
            "blocked_by_pid": None,
            "retryable_error": None,
            "sqlstates": [],
            "terminal_result": None,
            "started_at_monotonic": monotonic(),
        }
        attempts.append(trace)
        try:
            result = original_attempt(command)
        except Exception as error:
            code = error.code if isinstance(error, ResearchBaseError) else type(error).__name__
            trace["exit_classification"] = "ERROR"
            trace["terminal_result"] = str(code)
            if code is ErrorCode.CONCURRENT_MODIFICATION:
                trace["retryable_error"] = str(code)
            cause = error
            seen = set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                sqlstate = getattr(cause, "sqlstate", None)
                if sqlstate is not None:
                    trace["sqlstates"].append(sqlstate)
                cause = getattr(cause, "orig", None) or cause.__cause__ or cause.__context__
            raise
        else:
            trace["exit_classification"] = "RETURNED"
            trace["terminal_result"] = "SUCCESS"
            return result
        finally:
            trace["exited_at_monotonic"] = monotonic()

    def observed(repo, project_id):
        trace = attempts[-1]
        trace["backend_pid"] = repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one()
        trace["session_transaction_identity"] = id(repo._session.get_transaction())
        trace["project_lock_entered"] = True
        pids.put(trace)
        original(repo, project_id)
        trace["project_lock_resumed_at_monotonic"] = monotonic()

    def observed_authorize(repo, *args, **kwargs):
        trace = attempts[-1]
        assert id(repo._session.get_transaction()) == trace["session_transaction_identity"]
        trace["authorization_entered_at_monotonic"] = monotonic()
        try:
            result = original_authorize(repo, *args, **kwargs)
        except ResearchBaseError as error:
            trace["authorization_result"] = str(error.code)
            raise
        else:
            trace["authorization_result"] = "ALLOWED"
            return result

    def worker():
        try:
            return service.create(command)
        except ResearchBaseError as error:
            return error.code

    with (
        patch.object(service, "_create_once", observed_attempt),
        patch.object(service, "_authorize", observed_authorize),
        patch.object(SqlAlchemyLiteratureSearchPlanRepository, "lock_project", observed),
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        with engine.connect() as winner:
            tx = winner.begin()
            winner_pid = winner.execute(text("SELECT pg_backend_pid()")).scalar_one()
            winner.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project})
            controller_locked_at = monotonic()
            future = pool.submit(worker)
            try:
                waiting_attempt = pids.get(timeout=10)
                pid = waiting_attempt["backend_pid"]
                waited = False
                blockers = []
                deadline = monotonic() + 10
                while monotonic() < deadline:
                    with engine.connect() as c:
                        wait_state = (
                            c.execute(
                                text(
                                    "SELECT wait_event_type='Lock' AS waited,pg_blocking_pids(pid) AS blockers,backend_start,xact_start "
                                    "FROM pg_stat_activity WHERE pid=:pid"
                                ),
                                {"pid": pid},
                            )
                            .mappings()
                            .one()
                        )
                        waited = wait_state["waited"]
                        blockers = wait_state["blockers"]
                    if waited:
                        break
                    Event().wait(0.01)
                assert waited
                assert winner_pid in blockers
                waiting_attempt.update(
                    postgres_wait_observed=True,
                    blocked_by_pid=winner_pid,
                    backend_start=wait_state["backend_start"],
                    transaction_start=wait_state["xact_start"],
                    wait_observed_at_monotonic=monotonic(),
                )
                ended = winner.execute(
                    text(
                        "UPDATE project_role_assignments SET effective_until=clock_timestamp(),row_version=row_version+1 WHERE id=:id RETURNING effective_until"
                    ),
                    {"id": role},
                ).scalar_one()
                winner.execute(
                    text(
                        "INSERT INTO project_role_events(id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) VALUES (:id,:role,:actor,'CLOSED',:at,'review race',:request)"
                    ),
                    {
                        "id": uuid4(),
                        "role": role,
                        "actor": target.actor_id,
                        "at": ended,
                        "request": uuid4(),
                    },
                )
            finally:
                commit_started_at = monotonic()
                tx.commit()
                commit_completed_at = monotonic()
                authority_loss_committed = True
            assert future.result(timeout=20) is ErrorCode.FORBIDDEN
    with engine.connect() as c:
        receipts = c.execute(
            text(
                "SELECT count(*) FROM literature_search_plan_command_receipts WHERE request_id=:id"
            ),
            {"id": command.request_id},
        ).scalar_one()
        plans = c.execute(
            text(
                "SELECT count(*) FROM literature_search_plans WHERE project_id=:project AND created_by=:actor"
            ),
            {"project": project, "actor": target.actor_id},
        ).scalar_one()
        assert receipts == 0
        assert plans == 0
    at, rows, effective = _authority_rows(engine, target.actor_id, project)
    assert effective == []
    record_property(
        "authority_race",
        json.dumps(
            {
                "postgres_lock_wait": waited,
                "repeat_attempt": attempt,
                "run": attempt,
                "attempt_count": len(attempts),
                "attempts": attempts,
                "retry_count": len(attempts) - 1,
                "retry_occurred": len(attempts) > 1,
                "wait_attempt": waiting_attempt["attempt"],
                "terminal_attempt": attempts[-1]["attempt"],
                "same_attempt": waiting_attempt is attempts[-1],
                "controller_locked_at_monotonic": controller_locked_at,
                "authority_loss_commit_started_at_monotonic": commit_started_at,
                "authority_loss_commit_completed_at_monotonic": commit_completed_at,
                "worker_pid": pid,
                "controlling_pid": winner_pid,
                "blocking_pids": blockers,
                "lock_order": "project advisory lock -> projects row lock",
                "authority_loss_committed": authority_loss_committed,
                "closed_at": ended,
                "effective_at": at,
                "rows": rows,
                "effective_roles": effective,
                "result": "FORBIDDEN",
                "target_actor": target.actor_id,
                "role_assignment": role,
                "binding_operator": provisioning_operator.actor_id,
                "receipts": receipts,
                "plans": plans,
            },
            default=str,
        ),
    )
    engine.dispose()
    assert [trace["attempt"] for trace in attempts] == list(range(1, len(attempts) + 1))
    assert all(trace["project_lock_entered"] for trace in attempts)
    assert waiting_attempt["attempt"] == 1
    assert waiting_attempt["postgres_wait_observed"] is True
    assert waiting_attempt["blocked_by_pid"] == winner_pid
    terminal_attempt = attempts[-1]
    if len(attempts) > 1:
        for retryable_attempt in attempts[:-1]:
            assert retryable_attempt["exit_classification"] == "ERROR"
            assert retryable_attempt["retryable_error"] == "CONCURRENT_MODIFICATION"
            assert retryable_attempt["terminal_result"] == "CONCURRENT_MODIFICATION"
            assert "40001" in retryable_attempt["sqlstates"]
        assert len({trace["backend_pid"] for trace in attempts}) == len(attempts)
        assert len({trace["session_transaction_identity"] for trace in attempts}) == len(attempts)
        assert terminal_attempt["started_at_monotonic"] > waiting_attempt["exited_at_monotonic"]
    assert terminal_attempt["authorization_entered_at_monotonic"] >= commit_completed_at
    assert terminal_attempt["authorization_result"] == "FORBIDDEN"
    assert terminal_attempt["exit_classification"] == "ERROR"
    assert terminal_attempt["retryable_error"] is None
    assert terminal_attempt["sqlstates"] == []
    assert terminal_attempt["terminal_result"] == "FORBIDDEN"
    assert (
        controller_locked_at
        <= waiting_attempt["started_at_monotonic"]
        <= waiting_attempt["wait_observed_at_monotonic"]
        <= commit_started_at
        <= waiting_attempt["project_lock_resumed_at_monotonic"]
        <= waiting_attempt["exited_at_monotonic"]
    )
    # Retain the complete trace in JUnit even when a production retry is detected.
    assert len(attempts) == 1, "AUTHORITY_RACE_RETRY_MASKING_CONFIRMED"
    assert waiting_attempt is attempts[-1]
    assert waiting_attempt["attempt"] == 1
    assert waiting_attempt["retryable_error"] is None
    assert waiting_attempt["sqlstates"] == []
    assert waiting_attempt["authorization_result"] == "FORBIDDEN"
    assert waiting_attempt["terminal_result"] == "FORBIDDEN"
    assert (
        controller_locked_at
        <= waiting_attempt["started_at_monotonic"]
        <= waiting_attempt["wait_observed_at_monotonic"]
        <= commit_started_at
        <= waiting_attempt["project_lock_resumed_at_monotonic"]
        <= waiting_attempt["authorization_entered_at_monotonic"]
        <= waiting_attempt["exited_at_monotonic"]
    )
