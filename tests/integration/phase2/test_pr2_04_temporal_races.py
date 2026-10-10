"""Real lock-wait/fresh-authority proof; original transaction retries are allowed."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from queue import Queue
from threading import Event
from time import monotonic
from unittest.mock import patch
from uuid import uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _authority_rows, _provision
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("loss", ["role", "credential"])
@pytest.mark.pr204_requirements("PR204-AUTH-02", "PR204-CONC-06")
def test_pg_contention_rechecks_db_time_and_authority_on_every_attempt(
    phase2_database_url, run, loss, pr204_trace: FactRecorder
):
    engine, plans, owner, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, owner, project, plan, version)
        identity, _, _ = _identity_service(phase2_database_url)
        with engine.connect() as c:
            assert (
                c.execute(
                    text("SELECT count(*) FROM projects WHERE id=:id"), {"id": project}
                ).scalar_one()
                == 1
            )
        target, _ = _provision(identity, owner)
        role = identity.assign_project_role(
            AssignProjectRole(
                owner,
                project,
                target.actor_id,
                "RESEARCHER",
                "temporal race",
                uuid4(),
            )
        )
        attempts, samples = [], []
        queue = Queue()

        class Credential:
            expires_at: datetime | None = None

            def is_valid(self, principal, at):
                valid = self.expires_at is None or at < self.expires_at
                samples.append({"at": at, "valid": valid, "attempt": len(attempts)})
                return valid

        verifier = Credential()
        provider = FakeSearchCapability(capability_id="provider-a")
        service = LiteratureSearchExecutionService(
            lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine), pr204_error_normalization=True),
            provider,
            credential_verifier=verifier,
        )
        command = CreateLiteratureSearchExecution(
            project,
            version,
            target.actor_id,
            target.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=target,
        )
        original_create = service._create_once
        original_lock = SqlAlchemyLiteratureSearchPlanRepository.lock_project

        def observed_create(command):
            attempt = {"attempt": len(attempts) + 1, "sqlstates": []}
            attempts.append(attempt)
            try:
                result = original_create(command)
            except Exception as error:
                from tests.integration.phase2.test_pr2_04_ownership_races import _sqlstates

                attempt.update(
                    error_code=error.code.value if isinstance(error, ResearchBaseError) else None,
                    sqlstates=_sqlstates(error),
                )
                raise
            else:
                attempt["result"] = result
                return result

        def observed_lock(repo, project_id):
            pid, xid = repo._session.execute(text("SELECT pg_backend_pid(),txid_current()")).one()
            attempts[-1].update(backend_pid=pid, transaction_id=xid, project_lock_entered=True)
            queue.put(attempts[-1])
            original_lock(repo, project_id)
            attempts[-1]["project_lock_resumed"] = True

        def worker():
            try:
                return service.create(command)
            except ResearchBaseError as error:
                return error.code

        with (
            patch.object(service, "_create_once", observed_create),
            patch.object(SqlAlchemyLiteratureSearchPlanRepository, "lock_project", observed_lock),
            ThreadPoolExecutor(max_workers=1) as pool,
        ):
            with engine.connect() as controller:
                tx = controller.begin()
                controller_pid = controller.execute(text("SELECT pg_backend_pid()")).scalar_one()
                controller.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project})
                if loss == "credential":
                    verifier.expires_at = controller.execute(
                        text("SELECT clock_timestamp()")
                    ).scalar_one() + timedelta(seconds=1)
                future = pool.submit(worker)
                try:
                    first = queue.get(timeout=10)
                    deadline = monotonic() + 10
                    wait = None
                    while monotonic() < deadline:
                        with engine.connect() as c:
                            wait = (
                                c.execute(
                                    text(
                                        "SELECT wait_event_type,pg_blocking_pids(pid) AS blockers "
                                        "FROM pg_stat_activity WHERE pid=:pid"
                                    ),
                                    {"pid": first["backend_pid"]},
                                )
                                .mappings()
                                .one()
                            )
                        if wait["wait_event_type"] == "Lock" and controller_pid in wait["blockers"]:
                            break
                        Event().wait(0.01)
                    assert (
                        wait is not None
                        and wait["wait_event_type"] == "Lock"
                        and controller_pid in wait["blockers"]
                    )
                    first.update(postgres_wait_observed=True, blocker_pid=controller_pid)
                    if loss == "role":
                        ended = controller.execute(
                            text(
                                "UPDATE project_role_assignments "
                                "SET effective_until=clock_timestamp(),"
                                "row_version=row_version+1 WHERE id=:id RETURNING effective_until"
                            ),
                            {"id": role},
                        ).scalar_one()
                        controller.execute(
                            text(
                                "INSERT INTO project_role_events(id,role_assignment_id,actor_id,"
                                "event_kind,occurred_at,reason,request_id) "
                                "VALUES (:id,:role,:actor,'CLOSED',:at,'temporal race',:request)"
                            ),
                            {
                                "id": uuid4(),
                                "role": role,
                                "actor": target.actor_id,
                                "at": ended,
                                "request": uuid4(),
                            },
                        )
                    else:
                        deadline = monotonic() + 5
                        assert verifier.expires_at is not None
                        while (
                            controller.execute(text("SELECT clock_timestamp()")).scalar_one()
                            < verifier.expires_at
                        ):
                            assert monotonic() < deadline
                            Event().wait(0.01)
                finally:
                    tx.commit()
                result = future.result(timeout=20)
        at, roles, effective = _authority_rows(engine, target.actor_id, project)
        with engine.connect() as c:
            counts = {
                table: c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                for table in (
                    "literature_search_executions",
                    "literature_search_provider_attempts",
                    "search_query_records",
                    "search_result_records",
                    "literature_search_execution_events",
                )
            }
            receipts = c.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_command_receipts "
                    "WHERE request_id=:id"
                ),
                {"id": command.request_id},
            ).scalar_one()
        pr204_trace.record(
            run=run,
            loss=loss,
            attempts=attempts,
            credential_samples=samples,
            credential_deadline=verifier.expires_at,
            controller_pid=controller_pid,
            authority_loss_committed=True,
            observed_at=at,
            roles=roles,
            effective_roles=effective,
            result=result.value if isinstance(result, ErrorCode) else result,
            counts=counts,
            receipts=receipts,
            provider_calls=len(provider.calls),
        )
        assert result is ErrorCode.FORBIDDEN
        assert 1 <= len(attempts) <= 3 and attempts[-1]["error_code"] == "FORBIDDEN"
        assert all(
            a["error_code"] == "CONCURRENT_MODIFICATION" and set(a["sqlstates"]) == {"40001"}
            for a in attempts[:-1]
        )
        assert len({a["transaction_id"] for a in attempts}) == len(attempts)
        assert samples and all(sample["at"] >= target.verified_at for sample in samples)
        if loss == "role":
            assert effective == []
        else:
            assert "RESEARCHER" in effective and all(not sample["valid"] for sample in samples)
        assert set(counts.values()) == {0} and receipts == 0 and provider.calls == []
    finally:
        engine.dispose()
