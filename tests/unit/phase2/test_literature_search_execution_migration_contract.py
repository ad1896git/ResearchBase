
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT
from datetime import UTC, datetime
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import Table

from researchbase.domain.literature_search_execution import (
    ExecutionStatus,
    LiteratureSearchExecution,
    SearchHit,
    SearchQueryRecord,
    SearchResponse,
)
from researchbase.persistence.literature_search_execution_repository import (
    SqlAlchemyLiteratureSearchExecutionRepository,
)
from researchbase.persistence.models import (
    LiteratureSearchExecutionModel,
    LiteratureSearchExecutionCommandReceiptModel,
    LiteratureSearchExecutionEventModel,
    LiteratureSearchProviderAttemptModel,
    LiteratureSearchQueryRecordModel,
    LiteratureSearchResultRecordModel,
)


MIGRATION = (
    Path(__file__).parents[3]
    / "migrations"
    / "versions"
    / "0024_literature_search_execution.py"
)


def test_execution_events_are_contiguous_and_match_durable_state() -> None:
    source = MIGRATION.read_text()

    assert "CREATE FUNCTION pr204_guard_execution_event_insert()" in source
    assert "NEW.sequence <> COALESCE(max_sequence + 1, 0)" in source
    assert "NEW.new_status IS DISTINCT FROM execution_status" in source
    assert "NEW.new_row_version <> execution_row_version" in source
    assert "NEW.prior_row_version <> NEW.new_row_version - 1" in source
    assert "NEW.kind <> 'FINISHED'" in source


def test_execution_mutations_require_matching_event_at_commit() -> None:
    source = MIGRATION.read_text()

    assert "CREATE FUNCTION pr204_require_execution_event()" in source
    assert "CREATE CONSTRAINT TRIGGER trg_pr204_execution_event_commit" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert "CREATE CONSTRAINT TRIGGER trg_pr204_execution_created_event_commit" in source


def test_terminal_receipts_are_limited_to_version_matched_recovery_noops() -> None:
    source = MIGRATION.read_text()
    receipt_table = cast(Table, LiteratureSearchExecutionCommandReceiptModel.__table__)
    model_constraint_names = {constraint.name for constraint in receipt_table.constraints}

    assert "CREATE FUNCTION pr204_validate_terminal_receipt()" in source
    assert "NEW.command_name <> 'RECOVER_LITERATURE_SEARCH_EXECUTION'" in source
    assert "NEW.result_dto->>'accepted_row_version' <> execution_row_version::text" in source
    assert "CREATE CONSTRAINT TRIGGER trg_pr204_terminal_receipt_guard" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert 'name="ck_lse_receipt_admission_dto"' in source
    assert "ck_lse_receipt_admission_dto" in model_constraint_names


def test_child_insert_and_attempt_sealing_share_execution_lock() -> None:
    source = MIGRATION.read_text()

    assert re.search(r"WHERE id = target_execution_id\s+FOR UPDATE", source)
    assert len(re.findall(r"WHERE id = NEW\.execution_id\s+FOR UPDATE", source)) >= 2


def test_provider_outcome_constraints_validate_complete_tx_b_at_commit() -> None:
    source = MIGRATION.read_text()

    assert '"fk_lspa_query_record"' in source
    assert "deferrable=True" in source
    assert 'CREATE FUNCTION pr204_validate_attempt_provenance()' in source
    assert "CREATE CONSTRAINT TRIGGER trg_pr204_attempt_outcome_commit" in source
    assert "CREATE CONSTRAINT TRIGGER trg_pr204_query_outcome_commit" in source
    assert "CREATE CONSTRAINT TRIGGER trg_pr204_result_outcome_commit" in source
    assert "actual_result_count <> attempt_result_count" in source


def test_pr204_model_indexes_have_unique_names() -> None:
    models = (
        LiteratureSearchExecutionModel,
        LiteratureSearchProviderAttemptModel,
        LiteratureSearchQueryRecordModel,
        LiteratureSearchResultRecordModel,
        LiteratureSearchExecutionEventModel,
        LiteratureSearchExecutionCommandReceiptModel,
    )
    for model in models:
        table = cast(Any, model.__table__)
        names = [index.name for index in table.indexes]
        assert len(names) == len(set(names)), model.__tablename__


def test_query_record_storage_matches_frozen_schema_without_query_type_column() -> None:
    query_table = cast(Any, LiteratureSearchQueryRecordModel.__table__)

    assert "query_type" not in query_table.columns
    assert "query_type VARCHAR" not in MIGRATION.read_text()


def test_result_record_uses_frozen_search_query_record_id_column() -> None:
    result_table = cast(Any, LiteratureSearchResultRecordModel.__table__)

    assert "search_query_record_id" in result_table.columns
    assert "query_id" not in result_table.columns
    source = MIGRATION.read_text()
    assert "target_query_id := NEW.search_query_record_id" in source
    assert "target_query_id := NEW.query_id" not in source


def test_sql_event_records_actual_preterminal_state_and_version() -> None:
    now = datetime.now(UTC)
    execution_id, project_id, plan_id, actor_id = (uuid4() for _ in range(4))
    model = SimpleNamespace(id=execution_id, status="CANCELLED", row_version=3)
    session = Mock()
    session.get.return_value = model
    session.scalar.side_effect = [1, now, now]
    repository = SqlAlchemyLiteratureSearchExecutionRepository(session)
    execution = LiteratureSearchExecution(
        id=execution_id,
        project_id=project_id,
        plan_version_id=plan_id,
        requested_by=actor_id,
        executed_by=actor_id,
        idempotency_key=uuid4(),
        execution_context={},
        status=ExecutionStatus.CANCELLED,
        finished_at=now,
        row_version=3,
    )

    repository.append_event(execution, "FINISHED", actor_id)

    event = session.add.call_args.args[0]
    assert event.prior_status == "PLANNED"
    assert event.new_status == "CANCELLED"
    assert event.prior_row_version == 2
    assert event.new_row_version == 3


def test_tx_b_result_append_can_read_query_pending_in_same_unit_of_work() -> None:
    now = datetime.now(UTC)
    query_id, execution_id, attempt_id, actor_id = (uuid4() for _ in range(4))
    pending_query = SimpleNamespace(
        id=query_id,
        literature_search_execution_id=execution_id,
        provider_attempt_id=attempt_id,
        query_hash="a" * 64,
        created_by=actor_id,
    )
    session = Mock()
    session.new = [pending_query]
    session.get.return_value = None
    session.scalar.return_value = now
    repository = SqlAlchemyLiteratureSearchExecutionRepository(session)
    response = SearchResponse.success(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id="request-1",
        hits=(SearchHit("doi:1", "Paper", None, None, None),), retrieved_at=PROVIDER_RETRIEVED_AT,
)

    repository.append_results(query_id, response, now)

    result = session.add.call_args.args[0]
    assert result.search_query_record_id == query_id
    assert result.created_by == actor_id
    assert result.rank == 0


def test_attempt_read_preserves_complete_provider_outcome_provenance() -> None:
    execution_id, attempt_id = uuid4(), uuid4()
    reserved_at = datetime.now(UTC)
    returned_at = reserved_at
    row = SimpleNamespace(
        id=attempt_id,
        execution_id=execution_id,
        query_index=0,
        attempt_number=1,
        provider_request_key=attempt_id,
        status="SUCCEEDED",
        failure_code=None,
        reserved_at=reserved_at,
        deadline_at=reserved_at,
        recovery_after=reserved_at,
        invoked_at=reserved_at,
        returned_at=returned_at,
        retrieved_at=PROVIDER_RETRIEVED_AT,
        completed_at=returned_at,
        query_record_id=uuid4(),
        delivery_certainty="RESPONSE_RECEIVED",
        provider_request_id="provider-request-7",
        retry_after_seconds=None,
        warning_codes=["PARTIAL_COVERAGE"],
        result_count=2,
        row_version=2,
    )
    session = Mock()
    session.scalars.return_value.all.return_value = [row]
    repository = SqlAlchemyLiteratureSearchExecutionRepository(session)

    actual = repository.attempts(execution_id)[0]

    assert actual == {
        "id": attempt_id,
        "execution_id": execution_id,
        "query_index": 0,
        "attempt_number": 1,
        "provider_request_key": attempt_id,
        "status": "SUCCEEDED",
        "failure_code": None,
        "reserved_at": reserved_at,
        "deadline_at": reserved_at,
        "recovery_after": reserved_at,
        "invoked_at": reserved_at,
        "returned_at": returned_at,
        "retrieved_at": PROVIDER_RETRIEVED_AT,
        "completed_at": returned_at,
        "query_record_id": row.query_record_id,
        "delivery_certainty": "RESPONSE_RECEIVED",
        "provider_request_id": "provider-request-7",
        "retry_after_seconds": None,
        "warning_codes": ["PARTIAL_COVERAGE"],
        "result_count": 2,
        "row_version": 2,
    }


def test_query_and_result_creator_attribution_follows_provider_attempt_actor() -> None:
    now = datetime.now(UTC)
    query_id, execution_id, attempt_id = (uuid4() for _ in range(3))
    requested_by, executed_by = uuid4(), uuid4()
    execution = SimpleNamespace(id=execution_id, requested_by=requested_by)
    attempt = SimpleNamespace(
        id=attempt_id, execution_id=execution_id, created_by=executed_by
    )
    session = Mock()
    session.get.side_effect = [execution, attempt]
    session.scalar.return_value = now
    repository = SqlAlchemyLiteratureSearchExecutionRepository(session)
    query = SearchQueryRecord(
        query_id,
        execution_id,
        attempt_id,
        0,
        "cortex",
        "fake",
        "1",
        now,
    )

    repository.append_query(query)

    persisted = session.add.call_args.args[0]
    assert persisted.created_by == executed_by
    assert persisted.created_by != requested_by
