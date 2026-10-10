"""Frozen pack §9, PR204-PROV-03: lower caps and preserve each prior reason."""

from dataclasses import replace
from uuid import UUID

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider

from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.domain.literature_search_execution import DeliveryCertainty


@pytest.fixture
def budget_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.pr204_requirements('PR204-PROV-03')
@pytest.mark.parametrize('cap', [1, 2, 3])
def test_pg_lowered_provider_cap_preserves_mixed_failure_history(budget_case, cap,
                                                               pr204_trace: FactRecorder):
    engine, _, _, principal, project, create = budget_case
    codes = ['PROVIDER_RATE_LIMIT', 'PROVIDER_TIMEOUT', 'PROVIDER_TRANSIENT']
    certainties = [DeliveryCertainty.RESPONSE_RECEIVED, DeliveryCertainty.NOT_SENT,
                   DeliveryCertainty.RESPONSE_RECEIVED]
    provider = ScriptedProvider([
        ProviderError(ProviderFailureKind.RETRYABLE, code, delivery_certainty=certainty,
                      retry_after_seconds=0)
        for code, certainty in zip(codes, certainties, strict=True)
    ], 'provider-a')
    service = _service(engine, provider)
    admission = service.create(replace(create, max_provider_attempts=cap))
    execution_id = UUID(admission['execution_id'])
    command = _command('execute', principal, project, execution_id)
    receipt = service.execute(command)
    rows = _snapshot(engine, project)
    attempts = sorted(rows['attempts'], key=lambda a: a['attempt_number'])
    queries = sorted(rows['queries'], key=lambda q: q['ordinal'])
    assert len(provider.calls) == len(attempts) == len(queries) == cap
    assert [a['attempt_number'] for a in attempts] == list(range(1, cap + 1))
    assert [a['failure_code'] for a in attempts] == codes[:cap]
    assert [a['delivery_certainty'] for a in attempts] == [c.value for c in certainties[:cap]]
    assert all(a['status'] == 'RETRYABLE_FAILURE' for a in attempts)
    assert all(a['query_record_id'] is not None and a['completed_at'] is not None for a in attempts)
    assert [q['ordinal'] for q in queries] == list(range(cap))
    assert len({q['query_hash'] for q in queries}) == cap
    assert rows['results'] == []
    assert rows['executions'][0]['status'] == 'FAILED'
    assert rows['executions'][0]['failure_code'] == 'PROVIDER_RETRY_EXHAUSTED'
    assert len(rows['receipts']) == 2
    assert len([e for e in rows['events'] if e['event_kind'] == 'OUTCOME_RECORDED']) == cap
    assert service.execute(command) == receipt
    assert _snapshot(engine, project) == rows
    assert len(provider.calls) == cap
    pr204_trace.record(cap=cap, prior_failure_codes=[a['failure_code'] for a in attempts],
                       prior_delivery_certainties=[a['delivery_certainty'] for a in attempts],
                       durable_attempt_count=len(attempts), durable_query_count=len(queries),
                       provider_calls=len(provider.calls), terminal_reason='PROVIDER_RETRY_EXHAUSTED',
                       receipt_count=len(rows['receipts']), exact_replay_unchanged=True)


@pytest.mark.pr204_requirements('PR204-CRASH-01', 'PR204-BOUND-01')
def test_pg_create_admission_commits_parent_receipt_and_event_atomically(budget_case,
                                                                      pr204_trace: FactRecorder):
    engine, service, provider, _, project, create = budget_case
    admission = service.create(create)
    rows = _snapshot(engine, project)
    assert len(rows['executions']) == len(rows['receipts']) == len(rows['events']) == 1
    assert rows['receipts'][0]['result_execution_id'] == rows['executions'][0]['id']
    assert rows['events'][0]['execution_id'] == rows['executions'][0]['id']
    assert rows['events'][0]['kind'] == 'CREATED'
    assert rows['executions'][0]['status'] == 'PLANNED'
    assert rows['executions'][0]['row_version'] == 1
    assert rows['attempts'] == rows['queries'] == rows['results'] == []
    assert provider.calls == []
    assert service.create(create) == admission
    assert _snapshot(engine, project) == rows
    pr204_trace.record(execution_id=admission['execution_id'], execution_count=1,
                       receipt_count=1, created_event_count=1, provider_calls=0,
                       exact_replay_unchanged=True)


@pytest.mark.pr204_requirements('PR204-BOUND-03', 'PR204-CRASH-03')
def test_pg_reservation_event_matches_durable_parent_before_dispatch(budget_case,
                                                                   pr204_trace: FactRecorder):
    from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation

    engine, service, provider, principal, project, create = budget_case
    execution_id = UUID(service.create(create)['execution_id'])
    driver = _service(engine, provider, ReservedBeforeInvocation)
    driver.execute(_command('execute', principal, project, execution_id))
    rows = _snapshot(engine, project)
    assert rows['executions'][0]['status'] == 'RUNNING'
    assert rows['executions'][0]['row_version'] == 2
    assert len(rows['attempts']) == 1 and rows['attempts'][0]['status'] == 'RESERVED'
    reserved = [e for e in rows['events'] if e['kind'] == 'ATTEMPT_RESERVED']
    assert len(reserved) == 1
    assert reserved[0]['new_status'] == 'RUNNING' and reserved[0]['new_row_version'] == 2
    assert reserved[0]['attempt_id'] == rows['attempts'][0]['id']
    assert len(rows['receipts']) == 2
    assert rows['queries'] == rows['results'] == provider.calls == []
    pr204_trace.record(execution_status='RUNNING', row_version=2, reserved_attempts=1,
                       reservation_events=1, receipts=2, provider_calls=0)


@pytest.mark.pr204_requirements('PR204-DB-05', 'PR204-BOUND-03')
def test_pg_valid_direct_sql_reservation_passes_deferred_provenance_guard(budget_case, pr204_trace):
    from datetime import timedelta
    from uuid import uuid4

    from sqlalchemy import text

    engine, service, provider, principal, project, create = budget_case
    execution_id = UUID(service.create(create)['execution_id'])
    attempt_id = uuid4()
    with engine.begin() as connection:
        at = connection.execute(text('SELECT clock_timestamp()')).scalar_one()
        values = dict(execution=execution_id, attempt=attempt_id, actor=principal.actor_id,
                      at=at, deadline=at + timedelta(seconds=create.timeout_seconds),
                      recovery=at + timedelta(seconds=create.timeout_seconds + 30), event=uuid4())
        connection.execute(text('UPDATE literature_search_executions '
                                "SET status='RUNNING',started_at=:at,executed_by=:actor,row_version=2 "
                                'WHERE id=:execution'), values)
        connection.execute(text('INSERT INTO literature_search_provider_attempts '
                                '(id,execution_id,query_index,attempt_number,provider_request_key,'
                                'reserved_at,deadline_at,recovery_after,status,row_version,created_by,created_at) '
                                "VALUES (:attempt,:execution,0,1,:attempt,:at,:deadline,:recovery,'RESERVED',1,:actor,:at)"), values)
        connection.execute(text('INSERT INTO literature_search_execution_events '
                                '(id,execution_id,sequence,kind,attempt_id,prior_status,new_status,'
                                'prior_row_version,new_row_version,occurred_at,created_by,created_at) '
                                "VALUES (:event,:execution,1,'ATTEMPT_RESERVED',:attempt,'PLANNED','RUNNING',1,2,:at,:actor,:at)"), values)
        pr204_trace.record(reservation_statements_completed=True, attempt_id=attempt_id,
                           expected_deferred_commit='success', database_now=at)
    rows = _snapshot(engine, project)
    assert rows['executions'][0]['status'] == 'RUNNING'
    assert len(rows['attempts']) == 1 and rows['attempts'][0]['id'] == attempt_id
    assert rows['attempts'][0]['status'] == 'RESERVED'
    assert len(rows['events']) == 2
    assert rows['queries'] == rows['results'] == provider.calls == []
    pr204_trace.record(deferred_commit_completed=True, durable_reserved_attempts=1, provider_calls=0)
