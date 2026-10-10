"""Proposed spawned-process owner-loss and saved-response cases; runtime NOT_RUN."""

from __future__ import annotations

import json
import multiprocessing
import os
from dataclasses import replace
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _provision
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _snapshot,
)
from tests.integration.phase2.test_pr2_04_ownership_races import _sqlstates
from tests.unit.phase2.test_pr2_04_provider_coverage import success

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def process_case(phase2_database_url):
    # Existing helper bootstraps persisted HUMAN, subject binding, OWNER role and frozen plan.
    # Child gets this exact immutable VerifiedPrincipal via spawn; no synthetic actor identity.
    yield from _execution_setup(phase2_database_url)


def _journal_append(path, point, **facts):
    # External fake-provider journal survives forced process termination. Never canonical state.
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"point": point, "process_pid": os.getpid(), **facts}) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _journal_read(path):
    p = Path(path)
    return [] if not p.exists() else [json.loads(line) for line in p.read_text().splitlines()]


def _process_worker(url, principal, project, execution_id, request_id, mode, journal, pipe):
    """Spawn target: reconstruct only infrastructure, never bootstrap or fabricate identity."""
    engine = create_engine(url, pool_size=2, max_overflow=1)
    events: list[dict[str, Any]] = []
    db_attempt = 0

    accepted_principal = principal

    class CurrentCredential:
        valid = True

        def is_valid(self, principal, at):
            assert principal == accepted_principal
            events.append({"point": "CURRENT_CREDENTIAL", "database_time": at, "valid": self.valid})
            return self.valid

    credential = CurrentCredential()

    class Uow(SqlAlchemyUnitOfWork):
        def __enter__(self):
            nonlocal db_attempt
            super().__enter__()
            db_attempt += 1
            self.attempt = db_attempt
            events.append({"point": "TX_ENTER", "db_attempt": self.attempt})
            return self

        def begin_serializable(self):
            super().begin_serializable()
            pid, xid = (
                self._require_session()
                .execute(text("SELECT pg_backend_pid(),txid_current()"))
                .one()
            )
            events.append(
                {
                    "point": "TX_BEGIN",
                    "db_attempt": self.attempt,
                    "backend_pid": pid,
                    "transaction_id": xid,
                }
            )

        def commit(self):
            super().commit()
            events.append({"point": "TX_COMMIT", "db_attempt": self.attempt})

        def __exit__(self, *args):
            error = args[1] if len(args) > 1 else None
            try:
                return super().__exit__(*args)
            except BaseException as caught:
                error = caught
                raise
            finally:
                events.append(
                    {
                        "point": "TX_EXIT",
                        "db_attempt": self.attempt,
                        "closed": self._session is None,
                        "sqlstates": _sqlstates(error),
                        "error_code": error.code.value
                        if isinstance(error, ResearchBaseError)
                        else None,
                    }
                )

    def pause(point):
        assert cast(QueuePool, engine.pool).checkedout() == 0
        pipe.send(
            {
                "point": point,
                "process_pid": os.getpid(),
                "events": list(events),
                "rows": _snapshot(engine, project),
                "pool_checked_out": cast(QueuePool, engine.pool).checkedout(),
            }
        )
        assert pipe.poll(90), "parent did not release owner barrier"
        action = pipe.recv()
        assert action in {"continue", "deny_credential"}
        if action == "deny_credential":
            credential.valid = False

    class JournalProvider(FakeSearchCapability):
        def search(self, request, context=None):
            assert cast(QueuePool, engine.pool).checkedout() == 0
            _journal_append(
                journal,
                "PROVIDER_ENTRY",
                execution_id=str(request.execution_id),
                attempt_id=str(request.attempt_id),
                provider_request_key=str(request.provider_request_key),
                query_index=request.query_index,
            )
            if mode == "during_call":
                pause("during_call")
            response = success(request.query_text, "provider-a", hits=2)
            _journal_append(journal, "PROVIDER_RETURN", attempt_id=str(request.attempt_id))
            return response

    class Owner(LiteratureSearchExecutionService):
        def _drive(self, *args, **kwargs):
            if mode == "before_call":
                pause("before_call")
            return super()._drive(*args, **kwargs)

        def _persist_outcome(self, *args, **kwargs):
            if mode == "saved_response":
                # Real provider response and observed invocation/return timestamps remain in owner.
                pause("saved_response")
            return super()._persist_outcome(*args, **kwargs)

    provider = JournalProvider(capability_id="provider-a")
    service = Owner(
        lambda: Uow(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False),
            pr204_error_normalization=True,
        ),
        provider,
        credential_verifier=credential,
    )
    try:
        # Persisted role/binding/project authority is checked afresh inside child application read.
        observed = service.get(principal, project, execution_id)
        events.append(
            {"point": "PERSISTED_PRINCIPAL_AUTHORIZED", "execution_id": observed["execution_id"]}
        )
        if mode == "contender":
            original = _command("execute", principal, project, execution_id, request_id)
            before = _snapshot(engine, project)
            replay = service.execute(original)
            after_replay = _snapshot(engine, project)
            assert after_replay == before
            next_command = _command("execute", principal, project, execution_id)
            admission = service.execute(next_command)
            after = _snapshot(engine, project)
            assert len(after["receipts"]) == len(before["receipts"]) + 1
            assert {k: v for k, v in after.items() if k != "receipts"} == {
                k: v for k, v in before.items() if k != "receipts"
            }
            pipe.send(
                {
                    "point": "DONE",
                    "process_pid": os.getpid(),
                    "events": events,
                    "before": before,
                    "after_replay": after_replay,
                    "rows": after,
                    "original_admission": replay,
                    "new_admission": admission,
                    "new_request_id": next_command.request_id,
                }
            )
        elif mode == "recover":
            admission = service.recover(
                _command("recover", principal, project, execution_id, request_id)
            )
            pipe.send(
                {
                    "point": "DONE",
                    "process_pid": os.getpid(),
                    "events": events,
                    "rows": _snapshot(engine, project),
                    "admission": admission,
                }
            )
        else:
            admission = service.execute(
                _command("execute", principal, project, execution_id, request_id)
            )
            pipe.send(
                {
                    "point": "DONE",
                    "process_pid": os.getpid(),
                    "events": events,
                    "rows": _snapshot(engine, project),
                    "admission": admission,
                }
            )
    except ResearchBaseError as error:
        pipe.send(
            {
                "point": "ERROR",
                "process_pid": os.getpid(),
                "error_code": error.code.value,
                "events": events,
                "rows": _snapshot(engine, project),
            }
        )
    except BaseException as error:
        # Unexpected fixture faults are explicit test failures; avoid dumping credential/DSN.
        pipe.send(
            {
                "point": "WORKER_FAILURE",
                "process_pid": os.getpid(),
                "error_type": type(error).__name__,
                "events": events,
            }
        )
        raise
    finally:
        engine.dispose()
        pipe.close()


def _spawn(ctx, url, principal, project, execution_id, request_id, mode, journal):
    parent, child = ctx.Pipe(duplex=True)
    process = ctx.Process(
        target=_process_worker,
        args=(url, principal, project, execution_id, request_id, mode, str(journal), child),
    )
    process.start()
    child.close()
    return process, parent


def _receive(process, pipe, timeout=15):
    assert pipe.poll(timeout), f"worker {process.pid} did not reach causal barrier"
    message = pipe.recv()
    assert message["point"] != "WORKER_FAILURE", message
    assert message["process_pid"] == process.pid
    return message


def _join(process):
    process.join(10)
    assert not process.is_alive()
    assert process.exitcode == 0


def _kill(process):
    process.terminate()
    process.join(10)
    assert not process.is_alive() and process.exitcode != 0


def _finish_cleanup(process, pipe):
    if process.is_alive():
        process.terminate()
        process.join(10)
    pipe.close()


def _deadline_wait(engine, deadline, trace):
    limit = monotonic() + 40
    while True:
        with engine.connect() as observer:
            at = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at >= deadline:
            break
        assert monotonic() < limit
        Event().wait(min(0.25, (deadline - at).total_seconds()))
    trace.record(point="REAL_POSTGRES_RECOVERY_DEADLINE", deadline=deadline, database_time=at)


SCENARIOS = [
    "before_call_lost",
    "during_call_lost",
    "saved_response_lost",
    "saved_response_alive",
    "saved_response_credential_lost",
]


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.pr204_requirements(
    "PR204-CONC-02", "PR204-CRASH-03", "PR204-CRASH-04", "PR204-CONC-06"
)
def test_pg_spawned_restart_never_takes_over_and_surviving_owner_alone_can_seal_response(
    process_case, phase2_database_url, tmp_path, run, scenario, pr204_trace
):
    engine, service, _, principal, project, create = process_case
    recovery_principal = principal
    if scenario == "saved_response_credential_lost":
        identity, _, _ = _identity_service(phase2_database_url)
        recovery_principal, _ = _provision(identity, principal)
        identity.assign_project_role(
            AssignProjectRole(
                principal,
                project,
                recovery_principal.actor_id,
                "RESEARCHER",
                "spawned process authorized recovery",
                uuid4(),
            )
        )
    execution_id = UUID(service.create(replace(create, timeout_seconds=1))["execution_id"])
    request_id = uuid4()
    journal = tmp_path / "provider-invocations.jsonl"
    ctx = multiprocessing.get_context("spawn")
    mode = (
        "before_call"
        if scenario == "before_call_lost"
        else "during_call"
        if scenario == "during_call_lost"
        else "saved_response"
    )
    owner, owner_pipe = _spawn(
        ctx, phase2_database_url, principal, project, execution_id, request_id, mode, journal
    )
    children = [(owner, owner_pipe)]
    try:
        paused = _receive(owner, owner_pipe)
        assert paused["point"] == mode and paused["pool_checked_out"] == 0
        pending = paused["rows"]
        assert pending["executions"][0]["status"] == "RUNNING"
        assert len(pending["attempts"]) == 1 and pending["attempts"][0]["status"] == "RESERVED"
        assert pending["attempts"][0]["invoked_at"] is None
        assert pending["queries"] == pending["results"] == []
        initial_journal = _journal_read(journal)
        expected_calls = 0 if mode == "before_call" else 1
        assert (
            sum(entry["point"] == "PROVIDER_ENTRY" for entry in initial_journal) == expected_calls
        )
        assert owner.is_alive()
        process_lost = scenario.endswith("_lost") and scenario != "saved_response_credential_lost"
        if process_lost:
            _kill(owner)
        restarted, restart_pipe = _spawn(
            ctx,
            phase2_database_url,
            principal,
            project,
            execution_id,
            request_id,
            "contender",
            journal,
        )
        children.append((restarted, restart_pipe))
        contender = _receive(restarted, restart_pipe)
        _join(restarted)
        assert contender["point"] == "DONE"
        assert restarted.pid != owner.pid and restarted.pid != os.getpid()
        assert _journal_read(journal) == initial_journal
        assert contender["rows"]["attempts"] == pending["attempts"]
        assert contender["rows"]["queries"] == contender["rows"]["results"] == []
        pr204_trace.record(
            run=run,
            scenario=scenario,
            parent_process_pid=os.getpid(),
            owner_paused=paused,
            owner_exitcode=owner.exitcode,
            restart=contender,
            invocation_journal_before=initial_journal,
            invocation_journal_after_restart=_journal_read(journal),
        )

        # Separate fresh process with currently valid original principal, before recovery_after.
        early, early_pipe = _spawn(
            ctx, phase2_database_url, principal, project, execution_id, uuid4(), "recover", journal
        )
        children.append((early, early_pipe))
        denied = _receive(early, early_pipe)
        _join(early)
        assert (
            denied["point"] == "ERROR"
            and denied["error_code"] == ErrorCode.CONCURRENT_MODIFICATION.value
        )
        assert denied["rows"] == contender["rows"]
        pr204_trace.record(point="FRESH_PROCESS_RECOVERY_TOO_EARLY", outcome=denied)

        if scenario == "saved_response_alive":
            owner_pipe.send("continue")
            completed = _receive(owner, owner_pipe)
            _join(owner)
            assert completed["point"] == "DONE"
            final = completed["rows"]
            assert final["executions"][0]["status"] == "SUCCEEDED"
            assert len(final["queries"]) == 1 and len(final["results"]) == 2
            assert final["attempts"][0]["invoked_at"] is not None
            assert final["attempts"][0]["status"] == "SUCCEEDED"
            pr204_trace.record(point="SURVIVING_OWNER_SAVED_RESPONSE", owner_result=completed)
        else:
            if scenario == "saved_response_credential_lost":
                owner_pipe.send("deny_credential")
                rejected = _receive(owner, owner_pipe)
                _join(owner)
                assert (
                    rejected["point"] == "ERROR"
                    and rejected["error_code"] == ErrorCode.FORBIDDEN.value
                )
                assert rejected["rows"] == contender["rows"]
                assert any(
                    event["point"] == "CURRENT_CREDENTIAL" and not event["valid"]
                    for event in rejected["events"]
                )
                pr204_trace.record(
                    point="SURVIVING_OWNER_LOSES_CURRENT_CREDENTIAL", owner_result=rejected
                )
            _deadline_wait(engine, pending["attempts"][0]["recovery_after"], pr204_trace)
            recovery_id = uuid4()
            recovery, recovery_pipe = _spawn(
                ctx,
                phase2_database_url,
                recovery_principal,
                project,
                execution_id,
                recovery_id,
                "recover",
                journal,
            )
            children.append((recovery, recovery_pipe))
            recovered = _receive(recovery, recovery_pipe)
            _join(recovery)
            assert recovered["point"] == "DONE"
            final = recovered["rows"]
            assert final["executions"][0]["status"] == "UNKNOWN"
            assert final["attempts"][0]["status"] == "UNKNOWN"
            # An external invocation journal is not a canonical observed response. Lost owner
            # cannot authorize fabricating invoked_at, query, retrieved_at or result material.
            assert final["attempts"][0]["invoked_at"] is None
            assert final["attempts"][0]["returned_at"] is None
            assert final["attempts"][0]["query_record_id"] is None
            assert final["queries"] == final["results"] == []
            assert (
                service.recover(
                    _command("recover", recovery_principal, project, execution_id, recovery_id)
                )
                == recovered["admission"]
            )
            assert _snapshot(engine, project) == final
            pr204_trace.record(point="FRESH_PROCESS_EXPIRED_RECOVERY", recovered=recovered)
        assert final["attempts"][0]["id"] == pending["attempts"][0]["id"]
        assert len(final["attempts"]) == 1 and final["attempts"][0]["row_version"] == 2
        assert sum(event["kind"] == "FINISHED" for event in final["events"]) == 1
        assert _journal_read(journal) == initial_journal
        # Original command's immutable admission still replays after success/UNKNOWN.
        if scenario != "saved_response_credential_lost":
            assert (
                service.execute(_command("execute", principal, project, execution_id, request_id))
                == contender["original_admission"]
            )
            assert _snapshot(engine, project) == final
        else:
            assert final["executions"][0]["executed_by"] == principal.actor_id
            finished = [event for event in final["events"] if event["kind"] == "FINISHED"]
            assert finished[0]["created_by"] == recovery_principal.actor_id
        pr204_trace.record(
            point="FINAL_DURABLE_STATE",
            rows=final,
            provider_invocations=expected_calls,
            journal=initial_journal,
        )
    finally:
        for process, pipe in children:
            _finish_cleanup(process, pipe)
