"""SQLAlchemy persistence adapter for PR2-04 execution provenance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.orm import Session

from researchbase.domain.literature_search_execution import (
    AttemptStatus,
    ExecutionStatus,
    LiteratureSearchExecution,
    SearchQueryRecord,
    SearchResponse,
)
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.models import (
    LiteratureSearchExecutionCommandReceiptModel,
    LiteratureSearchExecutionEventModel,
    LiteratureSearchExecutionModel,
    LiteratureSearchProviderAttemptModel,
    LiteratureSearchQueryRecordModel,
    LiteratureSearchResultRecordModel,
)


class SqlAlchemyLiteratureSearchExecutionRepository:
    """Narrow adapter; transaction ownership remains with the enclosing UoW."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def _database_now(self) -> datetime:
        return self._session.scalar(select(func.clock_timestamp())) or self._now()

    def database_now(self) -> datetime:
        return self._database_now()

    def validate_plan_version(
        self, project_id: UUID, version_id: UUID, *, lock: bool = False
    ) -> None:
        from researchbase.persistence.models import (
            LiteratureSearchPlanModel,
            LiteratureSearchPlanVersionModel,
        )

        statement = (
            select(LiteratureSearchPlanVersionModel, LiteratureSearchPlanModel.project_id)
            .join(
                LiteratureSearchPlanModel,
                LiteratureSearchPlanModel.id == LiteratureSearchPlanVersionModel.plan_id,
            )
            .where(LiteratureSearchPlanVersionModel.id == version_id)
        )
        if lock:
            statement = statement.with_for_update()
        row = self._session.execute(statement).first()
        if row is None or row[1] != project_id:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "literature search plan version not found")
        version = row[0]
        if version.status != "FROZEN":
            raise ResearchBaseError(
                ErrorCode.SEARCH_PLAN_NOT_FROZEN, "search plan version is not frozen"
            )

    def plan_invocation(self, project_id: UUID, version_id: UUID) -> tuple[str, dict[str, Any]]:
        from researchbase.persistence.models import (
            LiteratureSearchPlanModel,
            LiteratureSearchPlanVersionModel,
            ResearchQuestionModel,
            ResearchQuestionVersionModel,
            SearchPlanQuestionInputModel,
        )

        row = self._session.execute(
            select(LiteratureSearchPlanVersionModel, LiteratureSearchPlanModel.project_id)
            .join(
                LiteratureSearchPlanModel,
                LiteratureSearchPlanModel.id == LiteratureSearchPlanVersionModel.plan_id,
            )
            .where(LiteratureSearchPlanVersionModel.id == version_id)
        ).first()
        if row is None or row[1] != project_id or row[0].status not in {"FROZEN", "SUPERSEDED"}:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "frozen plan version not found")
        version = row[0]
        questions = self._session.execute(
            select(
                ResearchQuestionModel.id,
                ResearchQuestionVersionModel.id,
                ResearchQuestionVersionModel.content_hash,
            )
            .join(
                SearchPlanQuestionInputModel,
                SearchPlanQuestionInputModel.research_question_version_id
                == ResearchQuestionVersionModel.id,
            )
            .join(
                ResearchQuestionModel,
                ResearchQuestionModel.id == ResearchQuestionVersionModel.research_question_id,
            )
            .where(SearchPlanQuestionInputModel.plan_version_id == version_id)
            .order_by(SearchPlanQuestionInputModel.ordinal)
        ).all()
        material = {
            "type": "LiteratureSearchPlanVersion",
            "material_version": 1,
            "plan_id": str(version.plan_id),
            "research_question_refs": sorted(
                [
                    {
                        "type": "ResearchQuestionVersion",
                        "id": str(qv_id),
                        "content_hash": str(q_hash),
                    }
                    for _qid, qv_id, q_hash in questions
                ],
                key=lambda ref: (ref["type"], ref["id"], ref["content_hash"]),
            ),
            "objective": version.objective,
            "source_scope": version.source_scope,
            "inclusion_criteria": version.inclusion_criteria,
            "exclusion_criteria": version.exclusion_criteria,
            "time_range": version.time_range,
            "language_scope": version.language_scope,
            "search_strategy": version.search_strategy,
            "planned_providers": version.planned_providers,
            "stopping_rule": version.stopping_rule,
        }
        digest = str(sha256_canonical_json(material))
        if digest != version.content_hash:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "frozen plan hash mismatch"
            )
        return digest, material

    def _execution(self, model: LiteratureSearchExecutionModel) -> LiteratureSearchExecution:
        context = cast(dict[str, Any], model.execution_context)
        cancellation_requested = (
            self._session.scalar(
                select(LiteratureSearchExecutionEventModel.id).where(
                    LiteratureSearchExecutionEventModel.execution_id == model.id,
                    LiteratureSearchExecutionEventModel.kind == "CANCEL_REQUESTED",
                )
            )
            is not None
        )
        return LiteratureSearchExecution(
            id=model.id,
            project_id=model.project_id,
            plan_version_id=model.search_plan_version_id,
            requested_by=model.requested_by,
            idempotency_key=model.idempotency_key,
            execution_context=dict(context),
            status=ExecutionStatus(model.status),
            executed_by=model.executed_by,
            started_at=model.started_at,
            finished_at=model.finished_at,
            row_version=model.row_version,
            cancellation_requested=cancellation_requested,
            failure_code=model.failure_code,
        )

    def create(self, execution: LiteratureSearchExecution, receipt: dict[str, Any]) -> None:
        context = dict(execution.execution_context)
        model = LiteratureSearchExecutionModel(
            id=execution.id,
            project_id=execution.project_id,
            search_plan_version_id=execution.plan_version_id,
            strategy_id="explicit_queries",
            strategy_version="1",
            status=execution.status.value,
            requested_by=execution.requested_by,
            executed_by=execution.executed_by,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            execution_context=context,
            idempotency_key=execution.idempotency_key,
            row_version=execution.row_version,
            created_by=execution.requested_by,
            created_at=self._database_now(),
        )
        self._session.add(model)
        # Establish the immediate FK parent before queuing dependent events/receipts.
        # This flush stays inside TX A-create; the UoW alone owns its commit.
        self._session.flush([model])
        self._event(model, "CREATED", None, execution.status.value, execution.requested_by)

    def get(self, execution_id: UUID) -> LiteratureSearchExecution | None:
        model = self._session.get(LiteratureSearchExecutionModel, execution_id)
        return None if model is None else self._execution(model)

    def get_for_update(self, execution_id: UUID) -> LiteratureSearchExecution | None:
        model = self._session.get(
            LiteratureSearchExecutionModel, execution_id, with_for_update=True
        )
        return None if model is None else self._execution(model)

    def save(self, execution: LiteratureSearchExecution, expected_row_version: int) -> None:
        model = self._session.get(
            LiteratureSearchExecutionModel, execution.id, with_for_update=True
        )
        if model is None:
            raise KeyError(execution.id)
        if model.row_version != expected_row_version:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "stale execution version")
        model.status = execution.status.value
        model.executed_by = execution.executed_by
        model.started_at = execution.started_at
        model.finished_at = execution.finished_at
        model.failure_code = execution.failure_code
        model.row_version = execution.row_version

    def receipt(self, key: tuple[str, UUID, UUID, str, UUID]) -> dict[str, Any] | None:
        deployment_id, actor_id, project_id, command_name, request_id = key
        row = self._session.scalar(
            select(LiteratureSearchExecutionCommandReceiptModel).where(
                LiteratureSearchExecutionCommandReceiptModel.deployment_id == deployment_id,
                LiteratureSearchExecutionCommandReceiptModel.actor_id == actor_id,
                LiteratureSearchExecutionCommandReceiptModel.project_id == project_id,
                LiteratureSearchExecutionCommandReceiptModel.command_name == command_name,
                LiteratureSearchExecutionCommandReceiptModel.request_id == request_id,
            )
        )
        if row is None:
            return None
        return {"request_hash": row.request_hash, "dto": row.result_dto}

    def save_receipt(self, key: tuple[str, UUID, UUID, str, UUID], value: dict[str, Any]) -> None:
        deployment_id, actor_id, project_id, command_name, request_id = key
        payload = value.get("payload", {})
        request_hash = str(sha256_canonical_json(payload))
        execution_id = UUID(str(value["dto"]["execution_id"]))
        now = self._database_now()
        self._session.add(
            LiteratureSearchExecutionCommandReceiptModel(
                id=uuid4(),
                deployment_id=deployment_id,
                actor_id=actor_id,
                project_id=project_id,
                command_name=command_name,
                request_id=request_id,
                request_hash=request_hash,
                result_execution_id=execution_id,
                result_dto_version=1,
                result_dto=value["dto"],
                completed_at=now,
                created_by=actor_id,
                created_at=now,
            )
        )

    def reserve(
        self,
        execution_id: UUID,
        query_index: int,
        actor_id: UUID,
        reserved_at: datetime | None = None,
    ) -> UUID:
        execution = self._session.get(
            LiteratureSearchExecutionModel, execution_id, with_for_update=True
        )
        if execution is None:
            raise KeyError(execution_id)
        prior = self._session.scalars(
            select(LiteratureSearchProviderAttemptModel.attempt_number).where(
                LiteratureSearchProviderAttemptModel.execution_id == execution_id,
                LiteratureSearchProviderAttemptModel.query_index == query_index,
            )
        ).all()
        attempt_number = max(prior, default=0) + 1
        attempt_id = uuid4()
        now = reserved_at or self._database_now()
        if execution.status != ExecutionStatus.RUNNING.value or execution.started_at is None:
            raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "execution is not RUNNING")
        context = cast(dict[str, Any], execution.execution_context)
        if (
            self._session.scalar(
                select(LiteratureSearchProviderAttemptModel.id).where(
                    LiteratureSearchProviderAttemptModel.execution_id == execution_id,
                    LiteratureSearchProviderAttemptModel.status == AttemptStatus.RESERVED.value,
                )
            )
            is not None
        ):
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION, "attempt is already reserved"
            )
        all_attempts = self._session.scalars(
            select(LiteratureSearchProviderAttemptModel).where(
                LiteratureSearchProviderAttemptModel.execution_id == execution_id
            )
        ).all()
        query_attempts = [row for row in all_attempts if row.query_index == query_index]
        previous = max(query_attempts, key=lambda row: row.attempt_number, default=None)
        if (
            previous is not None
            and previous.status == AttemptStatus.RETRYABLE_FAILURE.value
            and previous.retry_after_seconds is not None
            and previous.completed_at is not None
            and now < previous.completed_at + timedelta(seconds=previous.retry_after_seconds)
        ):
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION,
                "provider Retry-After deadline has not elapsed",
            )
        if len(all_attempts) >= 96 or len(query_attempts) >= int(context["max_provider_attempts"]):
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION, "provider attempt budget exhausted"
            )
        if now + timedelta(seconds=1) > execution.started_at + timedelta(
            seconds=int(context["execution_budget_seconds"])
        ):
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION, "execution budget exhausted"
            )
        deadline_at = min(
            now + timedelta(seconds=int(context["timeout_seconds"])),
            execution.started_at
            + timedelta(seconds=int(context["execution_budget_seconds"])),
        )
        self._session.add(
            LiteratureSearchProviderAttemptModel(
                id=attempt_id,
                execution_id=execution_id,
                query_index=query_index,
                attempt_number=attempt_number,
                provider_request_key=attempt_id,
                reserved_at=now,
                deadline_at=deadline_at,
                recovery_after=deadline_at + timedelta(seconds=30),
                status=AttemptStatus.RESERVED.value,
                row_version=1,
                created_by=actor_id,
                created_at=now,
            )
        )
        if all_attempts:
            self._event(
                execution,
                "ATTEMPT_RESERVED",
                execution.status,
                execution.status,
                actor_id,
                attempt_id,
            )
        else:
            self._event(
                execution,
                "ATTEMPT_RESERVED",
                ExecutionStatus.PLANNED.value,
                ExecutionStatus.RUNNING.value,
                actor_id,
                attempt_id,
                prior_row_version=1,
            )
        return attempt_id

    def attempts(self, execution_id: UUID) -> list[dict[str, Any]]:
        rows = self._session.scalars(
            select(LiteratureSearchProviderAttemptModel)
            .where(LiteratureSearchProviderAttemptModel.execution_id == execution_id)
            .order_by(
                LiteratureSearchProviderAttemptModel.query_index,
                LiteratureSearchProviderAttemptModel.attempt_number,
            )
        ).all()
        return [
            {
                "id": row.id,
                "execution_id": row.execution_id,
                "query_index": row.query_index,
                "attempt_number": row.attempt_number,
                "provider_request_key": row.provider_request_key,
                "status": row.status,
                "failure_code": row.failure_code,
                "reserved_at": row.reserved_at,
                "deadline_at": row.deadline_at,
                "recovery_after": row.recovery_after,
                "invoked_at": row.invoked_at,
                "returned_at": row.returned_at,
                "completed_at": row.completed_at,
                "query_record_id": row.query_record_id,
                "delivery_certainty": row.delivery_certainty,
                "provider_request_id": row.provider_request_id,
                "retry_after_seconds": row.retry_after_seconds,
                "warning_codes": (
                    list(cast(list[str], row.warning_codes))
                    if row.warning_codes is not None
                    else None
                ),
                "result_count": row.result_count,
                "row_version": row.row_version,
            }
            for row in rows
        ]

    def reservation(self, attempt_id: UUID) -> dict[str, Any] | None:
        row = next(
            (
                pending
                for pending in self._session.new
                if isinstance(pending, LiteratureSearchProviderAttemptModel)
                and pending.id == attempt_id
            ),
            None,
        )
        if row is None:
            row = self._session.get(LiteratureSearchProviderAttemptModel, attempt_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "status": row.status,
            "reserved_at": row.reserved_at,
            "deadline_at": row.deadline_at,
            "recovery_after": row.recovery_after,
        }

    def seal(self, attempt_id: UUID, values: dict[str, Any]) -> None:
        row = self._session.get(
            LiteratureSearchProviderAttemptModel, attempt_id, with_for_update=True
        )
        if row is None:
            raise KeyError(attempt_id)
        if row.status != AttemptStatus.RESERVED.value:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "provider attempt is sealed")
        for key, value in values.items():
            if hasattr(row, key):
                setattr(row, key, value)
        row.completed_at = self._database_now()
        row.row_version += 1

    def append_query(self, record: SearchQueryRecord) -> None:
        execution = self._session.get(LiteratureSearchExecutionModel, record.execution_id)
        if execution is None:
            raise KeyError(record.execution_id)
        attempt = self._session.get(LiteratureSearchProviderAttemptModel, record.attempt_id)
        if attempt is None or attempt.execution_id != record.execution_id:
            raise KeyError(record.attempt_id)
        self._session.add(
            LiteratureSearchQueryRecordModel(
                id=record.id,
                literature_search_execution_id=record.execution_id,
                provider_attempt_id=record.attempt_id,
                query_text=record.query_text,
                perspective=record.perspective,
                provider_id=record.provider_id,
                provider_version=record.provider_version,
                ordinal=record.ordinal,
                executed_at=record.executed_at,
                query_hash=record.query_hash,
                created_by=attempt.created_by,
                created_at=self._database_now(),
            )
        )

    def append_results(
        self, query_id: UUID, response: SearchResponse, retrieved_at: datetime
    ) -> None:
        query = next(
            (
                candidate
                for candidate in self._session.new
                if getattr(candidate, "id", None) == query_id
                and hasattr(candidate, "query_hash")
            ),
            None,
        )
        if query is None:
            query = self._session.get(LiteratureSearchQueryRecordModel, query_id)
        if query is None:
            raise KeyError(query_id)
        for rank, hit in enumerate(response.hits):
            self._session.add(
                LiteratureSearchResultRecordModel(
                    id=uuid4(),
                    search_query_record_id=query_id,
                    external_identifier=hit.external_identifier,
                    rank=rank,
                    title=hit.title,
                    url=hit.url,
                    snippet=hit.snippet,
                    provider_score=hit.provider_score,
                    retrieved_at=retrieved_at,
                    content_hash=hit.result_hash(query.query_hash, rank),
                    created_by=query.created_by,
                    created_at=self._database_now(),
                )
            )

    def append_event(
        self,
        execution: LiteratureSearchExecution,
        kind: str,
        actor_id: UUID,
        attempt_id: UUID | None = None,
        prior_row_version: int | None = None,
    ) -> None:
        model = self._session.get(LiteratureSearchExecutionModel, execution.id)
        if model is None:
            raise KeyError(execution.id)
        prior_status = model.status
        if kind == "FINISHED":
            prior_status = (
                ExecutionStatus.PLANNED.value
                if execution.started_at is None
                else ExecutionStatus.RUNNING.value
            )
        self._event(
            model,
            kind,
            prior_status,
            execution.status.value,
            actor_id,
            attempt_id,
            prior_row_version,
        )

    def next_query_ordinal(self, execution_id: UUID) -> int:
        value = self._session.scalar(
            select(func.count())
            .select_from(LiteratureSearchQueryRecordModel)
            .where(LiteratureSearchQueryRecordModel.literature_search_execution_id == execution_id)
        )
        return int(value or 0)

    def provenance(self, execution_id: UUID) -> dict[str, Any]:
        execution = self.get(execution_id)
        if execution is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution not found")
        attempts = self.attempts(execution_id)
        plan_hash, plan_material = self.plan_invocation(
            execution.project_id, execution.plan_version_id
        )
        queries = self._session.scalars(
            select(LiteratureSearchQueryRecordModel)
            .where(LiteratureSearchQueryRecordModel.literature_search_execution_id == execution_id)
            .order_by(LiteratureSearchQueryRecordModel.ordinal)
        ).all()
        results = self._session.scalars(
            select(LiteratureSearchResultRecordModel)
            .join(
                LiteratureSearchQueryRecordModel,
                LiteratureSearchResultRecordModel.search_query_record_id
                == LiteratureSearchQueryRecordModel.id,
            )
            .where(LiteratureSearchQueryRecordModel.literature_search_execution_id == execution_id)
            .order_by(
                LiteratureSearchQueryRecordModel.ordinal,
                LiteratureSearchResultRecordModel.rank,
            )
        ).all()
        events = self._session.scalars(
            select(LiteratureSearchExecutionEventModel)
            .where(LiteratureSearchExecutionEventModel.execution_id == execution_id)
            .order_by(LiteratureSearchExecutionEventModel.sequence)
        ).all()
        receipts = self._session.scalars(
            select(LiteratureSearchExecutionCommandReceiptModel)
            .where(LiteratureSearchExecutionCommandReceiptModel.result_execution_id == execution_id)
            .order_by(
                LiteratureSearchExecutionCommandReceiptModel.created_at,
                LiteratureSearchExecutionCommandReceiptModel.id,
            )
        ).all()
        query_by_id = {query.id: query for query in queries}
        for query in queries:
            value = SearchQueryRecord(
                query.id,
                query.literature_search_execution_id,
                query.provider_attempt_id,
                query.ordinal,
                query.query_text,
                query.provider_id,
                query.provider_version,
                query.executed_at,
                query.perspective,
            )
            if value.query_hash != query.query_hash:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "query provenance digest mismatch"
                )
        from researchbase.domain.literature_search_execution import SearchHit

        for result in results:
            query = query_by_id[result.search_query_record_id]
            hit = SearchHit(
                result.external_identifier,
                result.title,
                result.url,
                result.snippet,
                cast(Any, result.provider_score),
            )
            if hit.result_hash(query.query_hash, result.rank) != result.content_hash:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "result provenance digest mismatch"
                )
        return {
            "plan": {
                "plan_version_id": execution.plan_version_id,
                "content_hash": plan_hash,
                "material": plan_material,
            },
            "execution": execution,
            "attempts": attempts,
            "queries": queries,
            "results": results,
            "events": events,
            "receipts": receipts,
        }

    def list_executions(
        self, project_id: UUID, limit: int, after: UUID | None = None
    ) -> list[LiteratureSearchExecution]:
        statement = select(LiteratureSearchExecutionModel).where(
            LiteratureSearchExecutionModel.project_id == project_id
        )
        if after is not None:
            cursor_created_at = self._session.scalar(
                select(LiteratureSearchExecutionModel.created_at).where(
                    LiteratureSearchExecutionModel.id == after,
                    LiteratureSearchExecutionModel.project_id == project_id,
                )
            )
            if cursor_created_at is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution cursor not found")
            statement = statement.where(
                tuple_(LiteratureSearchExecutionModel.created_at, LiteratureSearchExecutionModel.id)
                > tuple_(literal(cursor_created_at), literal(after))
            )
        rows = self._session.scalars(
            statement.order_by(
                LiteratureSearchExecutionModel.created_at,
                LiteratureSearchExecutionModel.id,
            ).limit(limit)
        ).all()
        return [self._execution(row) for row in rows]

    def _event(
        self,
        model: LiteratureSearchExecutionModel,
        kind: str,
        prior_status: str | None,
        new_status: str,
        actor_id: UUID,
        attempt_id: UUID | None = None,
        prior_row_version: int | None = None,
    ) -> None:
        # Immediate event guards/FKs require these coordinates and parent first.
        # Deferred complete-transaction guards still run at the UoW commit.
        self._session.flush([model])
        if attempt_id is not None:
            for pending in list(self._session.new):
                if (
                    isinstance(pending, LiteratureSearchProviderAttemptModel)
                    and pending.id == attempt_id
                ):
                    self._session.flush([pending])
        sequence = self._session.scalar(
            select(LiteratureSearchExecutionEventModel.sequence)
            .where(LiteratureSearchExecutionEventModel.execution_id == model.id)
            .order_by(LiteratureSearchExecutionEventModel.sequence.desc())
            .limit(1)
        )
        self._session.add(
            LiteratureSearchExecutionEventModel(
                id=uuid4(),
                execution_id=model.id,
                sequence=(sequence if sequence is not None else -1) + 1,
                kind=kind,
                attempt_id=attempt_id,
                prior_status=prior_status,
                new_status=new_status,
                prior_row_version=(
                    None
                    if kind == "CREATED"
                    else prior_row_version
                    if prior_row_version is not None
                    else max(1, model.row_version - 1)
                ),
                new_row_version=model.row_version,
                occurred_at=self._database_now(),
                created_by=actor_id,
                created_at=self._database_now(),
            )
        )
