"""Real PostgreSQL counterparts; collection is not runtime acceptance."""

from __future__ import annotations

from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

import json
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_provenance import _execution_service
from tests.unit.phase2.test_pr2_04_provider_coverage import (
    CANARY,
    RETRY_CASES,
    ScriptedProvider,
    success,
)

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    SearchHit,
    SearchResponse,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

QUERY = "normalization evidence"


def _scientific_rows(engine):
    """Snapshot every scientific table outside the six admitted execution tables.

    Catalog names are quoted by the dialect; no provider text enters SQL.
    Complete rows detect edits/deletes as well as accidental ingestion.
    """
    allowed = {
        "literature_search_executions",
        "literature_search_provider_attempts",
        "literature_search_execution_events",
        "literature_search_execution_command_receipts",
        "search_query_records",
        "search_result_records",
    }
    with engine.connect() as connection:
        tables = (
            connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            )
            .scalars()
            .all()
        )
        return {
            table: connection.execute(
                text(
                    "SELECT row_to_json(t)::text FROM "
                    + engine.dialect.identifier_preparer.quote(table)
                    + " t ORDER BY row_to_json(t)::text"
                )
            )
            .scalars()
            .all()
            for table in tables
            if table not in allowed
        }


def setup_case(database_url: str, script: Sequence[object], queries: tuple[str, ...] = (QUERY,)):
    engine, plans, principal, project, plan, version = _setup(database_url)
    frozen = _freeze(engine, plans, principal, project, plan, version)
    provider = ScriptedProvider(script, "provider-a")
    service = _execution_service(engine, provider)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            queries,
            principal=principal,
        )
    )
    command = ExecuteLiteratureSearchExecution(
        UUID(created["execution_id"]),
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=project,
        principal=principal,
    )
    return engine, provider, service, principal, project, command, frozen


@pytest.mark.pr204_requirements("PR204-PROV-01", "PR204-DOM-02", "PR204-TRACE-02")
@pytest.mark.parametrize("name,code,certainty", RETRY_CASES, ids=[c[0] for c in RETRY_CASES])
def test_pg_safe_failure_commits_before_retry(
    phase2_database_url: str,
    name: str,
    code: str,
    certainty: DeliveryCertainty,
    pr204_trace: FactRecorder,
) -> None:
    engine, provider, service, principal, project, command, _ = setup_case(
        phase2_database_url,
        [
            ProviderError(
                ProviderFailureKind.RETRYABLE,
                code,
                delivery_certainty=certainty,
                retry_after_seconds=0,
            ),
            success(QUERY, "provider-a"),
        ],
    )
    causal = []

    def observe(request):
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT status FROM literature_search_provider_attempts "
                        "WHERE execution_id=:id ORDER BY attempt_number"
                    ),
                    {"id": command.execution_id},
                )
                .scalars()
                .all()
            )
        assert rows == (["RESERVED"] if not causal else ["RETRYABLE_FAILURE", "RESERVED"])
        causal.append({"attempt_id": str(request.attempt_id), "durable_statuses_at_entry": rows})

    provider.observer = observe
    service.execute(command)
    provenance = service.get_provenance(principal, project, command.execution_id)
    assert len(provider.calls) == 2
    assert [a["status"] for a in provenance["attempts"]] == ["RETRYABLE_FAILURE", "SUCCEEDED"]
    assert provenance["attempts"][0]["failure_code"] == code
    assert provenance["attempts"][0]["delivery_certainty"] == certainty.value
    assert [q["ordinal"] for q in provenance["queries"]] == [0, 1]
    assert len({q["query_hash"] for q in provenance["queries"]}) == 2
    assert provenance["execution"]["status"] == "SUCCEEDED"
    pr204_trace.record(
        case=name, causal_provider_entry=causal, provider_calls=2, provenance=provenance
    )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-SUCCESS-01", "PR204-SUCCESS-02", "PR204-TRACE-04")
@pytest.mark.parametrize("case", ["zero-hit", "one-query", "multiple-query", "later-failure"])
def test_pg_success_partial_results_and_duplicate_order(
    phase2_database_url: str, case: str, pr204_trace: FactRecorder
) -> None:
    multiple = case in {"multiple-query", "later-failure"}
    script: list[object] = [success(QUERY, "provider-a", 0 if case == "zero-hit" else 2)]
    if multiple:
        script.append(
            ProviderError(ProviderFailureKind.PERMANENT, "AUTH_FAILED")
            if case == "later-failure"
            else success("second query", "provider-a", 2)
        )
    engine, provider, service, principal, project, command, frozen = setup_case(
        phase2_database_url, script, (QUERY, "second query") if multiple else (QUERY,)
    )
    scientific_before = _scientific_rows(engine)
    with engine.connect() as connection:
        before = connection.execute(text("SELECT count(*) FROM evidence_relations")).scalar_one()
        claims_before = connection.execute(text("SELECT count(*) FROM claims")).scalar_one()

    def observe(request):
        if request.query_index == 1:
            with engine.connect() as connection:
                assert (
                    connection.execute(
                        text(
                            "SELECT status FROM literature_search_provider_attempts "
                            "WHERE execution_id=:id AND query_index=0"
                        ),
                        {"id": command.execution_id},
                    ).scalar_one()
                    == "SUCCEEDED"
                )

    provider.observer = observe
    admission = service.execute(command)
    provenance = service.get_provenance(principal, project, command.execution_id)
    assert admission["accepted_row_version"] == 2
    assert provenance["plan"]["content_hash"] == frozen["content_hash"]
    assert provenance["execution"]["status"] == (
        "FAILED" if case == "later-failure" else "SUCCEEDED"
    )
    assert len(provider.calls) == (2 if multiple else 1)
    assert [r.query_index for r in provider.calls] == ([0, 1] if multiple else [0])
    assert [q["ordinal"] for q in provenance["queries"]] == list(range(len(provider.calls)))
    assert len(provenance["results"]) == (
        0 if case == "zero-hit" else 4 if case == "multiple-query" else 2
    )
    assert all(r["external_identifier"] == "duplicate" for r in provenance["results"])
    for query in provenance["queries"]:
        results = [r for r in provenance["results"] if r["search_query_record_id"] == query["id"]]
        assert [r["rank"] for r in results] == list(range(len(results)))
    events = provenance["events"]
    assert [e["sequence"] for e in events] == list(range(len(events)))
    assert sum(e["kind"] == "FINISHED" for e in events) == 1
    with engine.connect() as connection:
        started, finished = connection.execute(
            text("SELECT started_at,finished_at FROM literature_search_executions WHERE id=:id"),
            {"id": command.execution_id},
        ).one()
        assert (
            isinstance(started, datetime) and isinstance(finished, datetime) and started <= finished
        )
        assert (
            connection.execute(text("SELECT count(*) FROM evidence_relations")).scalar_one()
            == before
        )
        assert connection.execute(text("SELECT count(*) FROM claims")).scalar_one() == claims_before
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_command_receipts "
                    "WHERE result_execution_id=:id"
                ),
                {"id": command.execution_id},
            ).scalar_one()
            == 2
        )
    scientific_after = _scientific_rows(engine)
    assert scientific_after == scientific_before
    pr204_trace.record(
        scientific_rows_before=scientific_before,
        scientific_rows_after=scientific_after,
        case=case,
        admission=admission,
        provenance=provenance,
        provider_calls=len(provider.calls),
        unchanged_claim_count=claims_before,
        unchanged_evidence_count=before,
    )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-PROV-03", "PR204-UNKNOWN-01", "PR204-SEC-01")
@pytest.mark.parametrize(
    "kind", ["auth", "validation", "permanent", "timeout-exhaustion", "transient-exhaustion"]
)
def test_pg_failure_taxonomy_and_secret_redaction(
    phase2_database_url: str, kind: str, pr204_trace: FactRecorder, caplog: pytest.LogCaptureFixture
) -> None:
    retry = kind.endswith("exhaustion")
    code = (
        "PROVIDER_TIMEOUT"
        if kind == "timeout-exhaustion"
        else "PROVIDER_TRANSIENT"
        if retry
        else kind + CANARY
    )
    script = [
        ProviderError(
            ProviderFailureKind.RETRYABLE if retry else ProviderFailureKind.PERMANENT, code
        )
    ] * (3 if retry else 1)
    engine, provider, service, principal, project, command, _ = setup_case(
        phase2_database_url, script
    )
    admission = service.execute(command)
    provenance = service.get_provenance(principal, project, command.execution_id)
    assert len(provider.calls) == (3 if retry else 1)
    assert provenance["execution"]["status"] == "FAILED"
    assert provenance["execution"]["failure_code"] == (
        "PROVIDER_RETRY_EXHAUSTED" if retry else "PROVIDER_PERMANENT"
    )
    assert [a["attempt_number"] for a in provenance["attempts"]] == list(
        range(1, len(provider.calls) + 1)
    )
    assert all(
        a["failure_code"] == (code if retry else "PROVIDER_PERMANENT")
        for a in provenance["attempts"]
    )
    assert provenance["results"] == []
    assert CANARY not in json.dumps(provenance, default=str) + json.dumps(admission) + caplog.text
    with engine.connect() as connection:
        for table in (
            "literature_search_executions",
            "literature_search_provider_attempts",
            "literature_search_execution_command_receipts",
            "literature_search_execution_events",
            "search_query_records",
            "search_result_records",
        ):
            assert not connection.execute(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM {table} t "
                    "WHERE row_to_json(t)::text LIKE :canary)"
                ),
                {"canary": f"%{CANARY}%"},
            ).scalar_one()
    pr204_trace.record(
        kind=kind,
        provider_calls=len(provider.calls),
        provenance=provenance,
        canary_absent_from_rows_logs_receipts=True,
    )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-UNKNOWN-02", "PR204-UNKNOWN-04")
@pytest.mark.parametrize("kind", ["timeout", "disconnect", "unexpected"])
def test_pg_uncertain_delivery_suppresses_remaining_queries_and_new_execution_is_distinct(
    phase2_database_url: str, kind: str, pr204_trace: FactRecorder
) -> None:
    failure = (
        RuntimeError(CANARY)
        if kind == "unexpected"
        else ProviderError(
            ProviderFailureKind.RETRYABLE if kind == "timeout" else ProviderFailureKind.UNCERTAIN,
            "PROVIDER_TIMEOUT",
            delivery_certainty=DeliveryCertainty.MAY_HAVE_BEEN_SENT,
        )
    )
    engine, provider, service, principal, project, command, _ = setup_case(
        phase2_database_url, [failure], (QUERY, "second query")
    )
    admission = service.execute(command)
    before = service.get_provenance(principal, project, command.execution_id)
    assert service.execute(command) == admission
    assert service.get_provenance(principal, project, command.execution_id) == before
    with pytest.raises(ResearchBaseError) as caught:
        service.execute(
            ExecuteLiteratureSearchExecution(
                command.execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )
    assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
    attempt = before["attempts"][0]
    with engine.connect() as connection:
        context = connection.execute(
            text("SELECT execution_context FROM literature_search_executions WHERE id=:id"),
            {"id": command.execution_id},
        ).scalar_one()
    with pytest.raises(ResearchBaseError) as late:
        service._persist_outcome(
            command.execution_id,
            UUID(attempt["id"]),
            principal.actor_id,
            0,
            2,
            context,
            success(QUERY, "provider-a"),
            principal,
            project_id=project,
        )
    assert late.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert service.get_provenance(principal, project, command.execution_id) == before
    assert before["execution"]["status"] == "UNKNOWN"
    assert len(provider.calls) == len(before["queries"]) == len(before["attempts"]) == 1
    assert before["results"] == []
    new = service.create(
        CreateLiteratureSearchExecution(
            project,
            UUID(before["plan"]["plan_version_id"]),
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            (QUERY,),
            principal=principal,
        )
    )
    assert new["execution_id"] != str(command.execution_id)
    assert len(provider.calls) == 1
    pr204_trace.record(
        kind=kind,
        provenance=before,
        provider_calls=1,
        new_execution_id=new["execution_id"],
        late_response_error=late.value.code.value,
    )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-PROV-04")
@pytest.mark.parametrize("kind", ["provider", "version", "query", "oversized", "untyped"])
def test_pg_malformed_provider_batch_is_atomic(
    phase2_database_url: str, kind: str, pr204_trace: FactRecorder
) -> None:
    response = SearchResponse.success(
        provider_id="wrong" if kind == "provider" else "provider-a",
        provider_version="wrong" if kind == "version" else "1",
        normalized_query="wrong" if kind == "query" else QUERY,
        provider_request_id=None,
        hits=tuple(
            SearchHit("duplicate", "Paper", None, None, None)
            for _ in range(21 if kind == "oversized" else 2)
        ), retrieved_at=PROVIDER_RETRIEVED_AT,
)
    engine, provider, service, principal, project, command, _ = setup_case(
        phase2_database_url, [{} if kind == "untyped" else response]
    )
    service.execute(command)
    provenance = service.get_provenance(principal, project, command.execution_id)
    assert len(provider.calls) == len(provenance["queries"]) == len(provenance["attempts"]) == 1
    assert provenance["results"] == []
    assert provenance["execution"]["status"] == "FAILED"
    assert provenance["execution"]["failure_code"] == "PROVIDER_MALFORMED"
    assert provenance["queries"][0]["query_text"] == QUERY
    assert provenance["queries"][0]["provider_id"] == "provider-a"
    pr204_trace.record(kind=kind, provenance=provenance, provider_calls=1)
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-TRACE-03")
@pytest.mark.parametrize(
    "table,column",
    [("search_query_records", "query_hash"), ("search_result_records", "content_hash")],
    ids=["query-digest", "result-digest"],
)
def test_pg_provenance_read_fails_closed_on_corrupt_digest(
    phase2_database_url: str, table: str, column: str, pr204_trace: FactRecorder
) -> None:
    engine, provider, service, principal, project, command, _ = setup_case(
        phase2_database_url, [success(QUERY, "provider-a", 1)]
    )
    service.execute(command)
    # Test-only privileged corruption in this disposable database; normal writes remain guarded.
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
        connection.execute(text(f"UPDATE {table} SET {column}=:digest"), {"digest": "0" * 64})
        connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as caught:
        service.get_provenance(principal, project, command.execution_id)
    assert caught.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert len(provider.calls) == 1
    pr204_trace.record(
        corrupted_table=table,
        corrupted_column=column,
        error_code=caught.value.code.value,
        provider_calls=1,
    )
    engine.dispose()
