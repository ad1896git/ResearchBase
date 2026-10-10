"""Real PostgreSQL transaction boundaries and per-phase retry observations.

SQLSTATE injection uses PostgreSQL RAISE, not synthetic driver exceptions. It
tests normalization/retry, not a claim that an actual deadlock was induced.
"""

from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

from typing import Any
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class ObservedTransactions:
    def __init__(self, engine, recorder: FactRecorder):
        self.engine = engine
        self.recorder = recorder
        self.active = 0
        self.events: list[dict[str, Any]] = []
        self.pids: set[int] = set()
        self.target: str | None = None
        self.sqlstate = "40001"
        self.failures_remaining = 0
        self.injections = 0

    def fact(self, **values):
        self.events.append(values)
        self.recorder.record(**values)

    def factory(self):
        real = SqlAlchemyUnitOfWork(
            sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=False),
            pr204_error_normalization=True,
        )
        return ObservedUow(real, self)

    def inject(self, phase: str, session):
        if self.target == phase and self.failures_remaining:
            self.failures_remaining -= 1
            self.injections += 1
            # Allowlisted test SQLSTATE only; no interpolated user/provider input.
            assert self.sqlstate in {"40001", "40P01"}
            try:
                session.execute(text(f"DO $$ BEGIN RAISE SQLSTATE '{self.sqlstate}'; END $$"))
            except DBAPIError as error:
                self.fact(
                    phase=phase,
                    injected_sqlstate=getattr(error.orig, "sqlstate", None),
                    injection_number=self.injections,
                )
                raise

    def observe_no_transaction(self, point: str):
        checked_out = self.engine.pool.checkedout()
        assert self.active == 0 and checked_out == 0
        with self.engine.connect() as observer:
            observer_pid = observer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            rows = [
                dict(row)
                for row in observer.execute(
                    text(
                        "SELECT pid,state,xact_start FROM pg_stat_activity "
                        "WHERE pid=ANY(:pids) AND pid<>:observer"
                    ),
                    {"pids": sorted(self.pids), "observer": observer_pid},
                ).mappings()
            ]
            locks = observer.execute(
                text(
                    "SELECT count(*) FROM pg_locks WHERE pid=ANY(:pids) AND pid<>:observer "
                    "AND locktype IN ('advisory','transactionid','tuple','relation')"
                ),
                {"pids": sorted(self.pids), "observer": observer_pid},
            ).scalar_one()
        self.fact(
            point=point,
            active_application_uows=self.active,
            checked_out_before_observer=checked_out,
            postgres_backends=rows,
            postgres_service_locks=locks,
        )
        assert all(row["xact_start"] is None for row in rows)
        assert locks == 0


class ObservedRepository:
    def __init__(self, real, session, observations):
        self.real = real
        self.session = session
        self.observations = observations

    def __getattr__(self, name):
        return getattr(self.real, name)

    def create(self, *args, **kwargs):
        self.observations.inject("admission", self.session)
        return self.real.create(*args, **kwargs)

    def append_query(self, *args, **kwargs):
        self.observations.inject("outcome", self.session)
        return self.real.append_query(*args, **kwargs)

    def save(self, execution, expected_row_version):
        if execution.status.value in {"SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"}:
            self.observations.inject("finalization", self.session)
        return self.real.save(execution, expected_row_version)


class ObservedUow:
    def __init__(self, real, observations):
        self.real = real
        self.observations = observations
        self.number = 0

    def __getattr__(self, name):
        return getattr(self.real, name)

    def __enter__(self):
        self.real.__enter__()
        self.observations.active += 1
        self.number = (
            sum(event.get("point") == "TX_ENTER" for event in self.observations.events) + 1
        )
        self.observations.fact(point="TX_ENTER", db_attempt=self.number)
        self.literature_search_execution = ObservedRepository(
            self.real.literature_search_execution, self.real._require_session(), self.observations
        )
        return self

    def begin_serializable(self):
        self.real.begin_serializable()
        pid, xid, isolation = (
            self.real._require_session()
            .execute(
                text(
                    "SELECT pg_backend_pid(),txid_current(),"
                    "current_setting('transaction_isolation')"
                )
            )
            .one()
        )
        self.observations.pids.add(pid)
        self.observations.fact(
            point="TX_BEGIN",
            db_attempt=self.number,
            backend_pid=pid,
            transaction_id=xid,
            isolation=isolation,
        )
        assert isolation == "serializable"

    def commit(self):
        self.real.commit()
        self.observations.fact(point="TX_COMMIT", db_attempt=self.number)

    def __exit__(self, *args):
        try:
            return self.real.__exit__(*args)
        except Exception as error:
            self.observations.fact(
                point="TX_ERROR",
                db_attempt=self.number,
                canonical_error=error.code.value if isinstance(error, ResearchBaseError) else None,
                error_type=type(error).__name__,
            )
            raise
        finally:
            self.observations.active -= 1
            self.observations.fact(point="TX_EXIT", db_attempt=self.number)


def _prepared(url, trace, *, retry=False):
    engine, plans, principal, project, plan, version = _setup(url)
    _freeze(engine, plans, principal, project, plan, version)
    observations = ObservedTransactions(engine, trace)

    class Provider(FakeSearchCapability):
        def search(self, request, context=None):
            observations.observe_no_transaction("PROVIDER_ENTRY")
            observations.fact(point="PROVIDER_WAIT", attempt_id=request.attempt_id)
            observations.observe_no_transaction("PROVIDER_WAIT")
            response = super().search(request, context)
            observations.fact(
                point="PROVIDER_RETURN", provider_request_id=response.provider_request_id
            )
            return response

    responses = [
        SearchResponse.success(
            provider_id="provider-a",
            provider_version="1",
            normalized_query="normalization evidence",
            provider_request_id="observed-response", retrieved_at=PROVIDER_RETRIEVED_AT,
)
    ]
    if retry:
        responses.insert(
            0,
            SearchResponse(
                "provider-a",
                "1",
                "normalization evidence",
                "known-rate-limit",
                DeliveryCertainty.RESPONSE_RECEIVED,
                retry_after_seconds=0,
                failure_code="PROVIDER_RATE_LIMIT",
            ),
        )
    provider = Provider(capability_id="provider-a", responses=responses)
    service = LiteratureSearchExecutionService(
        observations.factory,
        provider,
        credential_verifier=_AlwaysValidCredential(),
        sleep=lambda delay: observations.observe_no_transaction("BACKOFF"),
    )
    command = CreateLiteratureSearchExecution(
        project,
        version,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        "provider-a",
        "1",
        ("normalization evidence",),
        principal=principal,
    )
    return engine, observations, provider, service, command


@pytest.mark.parametrize("retry", [False, True], ids=["success", "safe-retry"])
@pytest.mark.pr204_requirements("PR204-BOUND-01", "PR204-BOUND-02", "PR204-CONC-06")
def test_pg_provider_entry_wait_and_backoff_hold_no_service_transaction(
    phase2_database_url, retry, pr204_trace: FactRecorder
):
    engine, observations, provider, service, command = _prepared(
        phase2_database_url, pr204_trace, retry=retry
    )
    try:
        admission = service.create(command)
        execution_id = UUID(admission["execution_id"])
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                command.actor_id,
                command.deployment_id,
                uuid4(),
                project_id=command.project_id,
                principal=command.principal,
            )
        )
        provenance = service.get_provenance(command.principal, command.project_id, execution_id)
        pr204_trace.record(provenance=provenance, provider_calls=len(provider.calls))
        assert provenance["execution"]["status"] == "SUCCEEDED"
        assert len(provider.calls) == 2 if retry else len(provider.calls) == 1
        events = observations.events
        provider_positions = [i for i, e in enumerate(events) if e.get("point") == "PROVIDER_ENTRY"]
        for i in provider_positions:
            assert events[i - 1]["point"] == "TX_EXIT"
            assert any(e.get("point") == "TX_COMMIT" for e in events[:i])
        kinds = [e["kind"] for e in provenance["events"]]
        assert kinds == (
            ["CREATED", "ATTEMPT_RESERVED", "OUTCOME_RECORDED"]
            + (["ATTEMPT_RESERVED", "OUTCOME_RECORDED"] if retry else [])
            + ["FINISHED"]
        )
        assert provenance["events"][0]["prior_row_version"] is None
        assert provenance["events"][0]["new_row_version"] == 1
        assert all(
            e["new_row_version"] == e["prior_row_version"] + 1
            for e in provenance["events"][1:]
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("phase", ["admission", "outcome", "finalization"])
@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
@pytest.mark.parametrize("exhausted", [False, True], ids=["retry", "exhaustion"])
@pytest.mark.pr204_requirements("PR204-CONC-05", "PR204-CONC-06")
def test_pg_sqlstate_retry_is_phase_local_and_never_reinvokes_provider(
    phase2_database_url, phase, sqlstate, exhausted, pr204_trace: FactRecorder
):
    engine, observations, provider, service, command = _prepared(phase2_database_url, pr204_trace)
    observations.target = phase
    observations.sqlstate = sqlstate
    observations.failures_remaining = 3 if exhausted else 1
    try:
        error = None
        admission = None
        try:
            admission = service.create(command)
            service.execute(
                ExecuteLiteratureSearchExecution(
                    UUID(admission["execution_id"]),
                    command.actor_id,
                    command.deployment_id,
                    uuid4(),
                    project_id=command.project_id,
                    principal=command.principal,
                )
            )
        except ResearchBaseError as caught:
            error = caught
        with engine.connect() as connection:
            counts = {
                table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                for table in (
                    "literature_search_executions",
                    "literature_search_provider_attempts",
                    "search_query_records",
                    "search_result_records",
                    "literature_search_execution_events",
                    "literature_search_execution_command_receipts",
                )
            }
        pr204_trace.record(
            phase=phase,
            sqlstate=sqlstate,
            exhausted=exhausted,
            error_code=error.code.value if error else None,
            counts=counts,
            provider_calls=len(provider.calls),
            db_fault_count=observations.injections,
        )
        assert observations.injections == (3 if exhausted else 1)
        assert (error.code if error else None) == (
            ErrorCode.CONCURRENT_MODIFICATION if exhausted else None
        )
        assert len(provider.calls) == (0 if exhausted and phase == "admission" else 1)
        if exhausted and phase == "admission":
            assert set(counts.values()) == {0}
        else:
            assert admission is not None
            provenance = service.get_provenance(
                command.principal, command.project_id, UUID(admission["execution_id"])
            )
            pr204_trace.record(provenance=provenance)
            assert len(provenance["attempts"]) == 1
            if exhausted:
                assert provenance["execution"]["status"] == "RUNNING"
                assert len(provenance["queries"]) == (0 if phase == "outcome" else 1)
                assert not any(e["kind"] == "FINISHED" for e in provenance["events"])
            else:
                assert provenance["execution"]["status"] == "SUCCEEDED"
                assert len(provenance["queries"]) == 1
                assert sum(e["kind"] == "OUTCOME_RECORDED" for e in provenance["events"]) == 1
                assert sum(e["kind"] == "FINISHED" for e in provenance["events"]) == 1
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-CONC-05")
def test_pg_historical_uow_does_not_adopt_pr204_deadlock_normalization(
    phase2_database_url, pr204_trace: FactRecorder
):
    engine, _, _, _, _, _ = _setup(phase2_database_url)
    try:
        with pytest.raises(DBAPIError) as caught:
            with SqlAlchemyUnitOfWork(sessionmaker(bind=engine)) as uow:
                uow.begin_serializable()
                uow._require_session().execute(text("DO $$ BEGIN RAISE SQLSTATE '40P01'; END $$"))
        pr204_trace.record(
            sqlstate=getattr(caught.value.orig, "sqlstate", None),
            error_type=type(caught.value).__name__,
        )
        assert getattr(caught.value.orig, "sqlstate", None) == "40P01"
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-BOUND-01", "PR204-BOUND-02")
def test_pg_outstanding_provider_barrier_releases_all_database_resources(
    phase2_database_url, pr204_trace: FactRecorder
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    engine, observations, provider, service, command = _prepared(phase2_database_url, pr204_trace)
    entered, release = Event(), Event()

    def outstanding(request):
        entered.set()
        assert release.wait(15), "test coordinator never released the provider"

    provider.observer = outstanding
    try:
        admission = service.create(command)
        execution_id = UUID(admission["execution_id"])
        execute = ExecuteLiteratureSearchExecution(
            execution_id, command.actor_id, command.deployment_id, uuid4(),
            project_id=command.project_id, principal=command.principal,
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(service.execute, execute)
            try:
                assert entered.wait(10), "provider never entered"
                assert not future.done()
                observations.observe_no_transaction("EXTERNALLY_OBSERVED_PROVIDER_WAIT")
                pending = service.get_provenance(command.principal, command.project_id, execution_id)
                pr204_trace.record(point="OUTSTANDING_CALL", provenance=pending,
                                   future_done=future.done())
                assert pending["execution"]["status"] == "RUNNING"
                assert [a["status"] for a in pending["attempts"]] == ["RESERVED"]
                assert pending["queries"] == [] and pending["results"] == []
                assert not any(e["kind"] == "FINISHED" for e in pending["events"])
            finally:
                release.set()
            result = future.result(timeout=10)
        after = service.get_provenance(command.principal, command.project_id, execution_id)
        pr204_trace.record(admission=result, provenance=after, provider_calls=len(provider.calls))
        assert after["execution"]["status"] == "SUCCEEDED" and len(provider.calls) == 1
        assert [e["kind"] for e in after["events"]] == [
            "CREATED", "ATTEMPT_RESERVED", "OUTCOME_RECORDED", "FINISHED"
        ]
    finally:
        release.set()
        engine.dispose()
