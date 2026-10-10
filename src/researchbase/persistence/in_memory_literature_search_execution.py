"""Deterministic repository used by PR2-04 unit/orchestration tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from researchbase.domain.literature_search_execution import (
    LiteratureSearchExecution,
    SearchQueryRecord,
    SearchResponse,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


class InMemoryLiteratureSearchExecutionRepository:
    def __init__(self) -> None:
        self.executions: dict[UUID, LiteratureSearchExecution] = {}
        self.execution_created_at: dict[UUID, datetime] = {}
        self.receipts: dict[tuple[str, UUID, UUID, str, UUID], dict[str, object]] = {}
        self.attempt_rows: dict[UUID, dict[str, object]] = {}
        self.queries: list[SearchQueryRecord] = []
        self.results: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []

    def validate_plan_version(
        self, project_id: UUID, version_id: UUID, *, lock: bool = False
    ) -> None:
        return None

    def database_now(self) -> datetime:
        return datetime.now(UTC)

    def plan_invocation(self, project_id: UUID, version_id: UUID) -> tuple[str, object]:
        return "unit-test-unverified", {
            "project_id": str(project_id),
            "version_id": str(version_id),
            "planned_providers": ["fake"],
            "source_scope": "BIBLIOGRAPHIC",
        }

    def create(self, execution: LiteratureSearchExecution, receipt: dict[str, object]) -> None:
        if any(
            e.project_id == execution.project_id
            and e.idempotency_key == execution.idempotency_key
            for e in self.executions.values()
        ):
            raise ResearchBaseError(
                ErrorCode.IDEMPOTENCY_CONFLICT, "execution idempotency key already exists"
            )
        self.executions[execution.id] = deepcopy(execution)
        self.execution_created_at[execution.id] = self.database_now()
        self.append_event(execution, "CREATED", execution.requested_by)

    def get(self, execution_id: UUID) -> LiteratureSearchExecution | None:
        execution = self.executions.get(execution_id)
        return deepcopy(execution) if execution else None

    def get_for_update(self, execution_id: UUID) -> LiteratureSearchExecution | None:
        return self.get(execution_id)

    def save(self, execution: LiteratureSearchExecution, expected_row_version: int) -> None:
        if execution.id not in self.executions:
            raise KeyError(execution.id)
        if self.executions[execution.id].row_version != expected_row_version:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "stale execution version")
        self.executions[execution.id] = deepcopy(execution)

    def receipt(self, key: tuple[str, UUID, UUID, str, UUID]) -> dict[str, object] | None:
        return self.receipts.get(key)

    def save_receipt(
        self, key: tuple[str, UUID, UUID, str, UUID], value: dict[str, object]
    ) -> None:
        self.receipts[key] = value

    def reserve(
        self,
        execution_id: UUID,
        query_index: int,
        actor_id: UUID,
        reserved_at: datetime | None = None,
    ) -> UUID:
        execution = self.executions[execution_id]
        now = reserved_at or self.database_now()
        if execution.status.value != "RUNNING":
            raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "execution is not RUNNING")
        if execution.started_at is not None and now + timedelta(seconds=1) > (
            execution.started_at
            + timedelta(seconds=int(execution.execution_context["execution_budget_seconds"]))
        ):
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION, "execution budget exhausted"
            )
        if any(
            row["execution_id"] == execution_id and row["status"] == "RESERVED"
            for row in self.attempt_rows.values()
        ):
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "attempt already reserved")
        attempt_id = uuid4()
        context = execution.execution_context
        deadline = min(
            now + timedelta(seconds=int(context.get("timeout_seconds", 30))),
            (execution.started_at or now)
            + timedelta(seconds=int(context.get("execution_budget_seconds", 300))),
        )
        all_prior = [
            row for row in self.attempt_rows.values() if row["execution_id"] == execution_id
        ]
        prior = [
            int(row["attempt_number"])  # type: ignore[arg-type]
            for row in self.attempt_rows.values()
            if row["execution_id"] == execution_id and row["query_index"] == query_index
        ]
        previous = max(
            (
                row
                for row in self.attempt_rows.values()
                if row["execution_id"] == execution_id and row["query_index"] == query_index
            ),
            key=lambda row: int(cast(int, row["attempt_number"])),
            default=None,
        )
        if previous is not None and previous.get("retry_after_seconds"):
            completed_at = previous.get("completed_at")
            retry_at = (
                completed_at
                + timedelta(seconds=int(cast(int, previous["retry_after_seconds"])))
                if isinstance(completed_at, datetime)
                else None
            )
            if retry_at is not None and now < retry_at:
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "provider Retry-After deadline has not elapsed",
                )
        self.attempt_rows[attempt_id] = {
            "id": attempt_id,
            "execution_id": execution_id,
            "query_index": query_index,
            "attempt_number": max(prior, default=0) + 1,
            "provider_request_key": attempt_id,
            "status": "RESERVED",
            "reserved_at": now,
            "deadline_at": deadline,
            "recovery_after": deadline + timedelta(seconds=30),
            "invoked_at": None,
            "row_version": 1,
            "created_by": actor_id,
        }
        if all_prior:
            self.append_event(execution, "ATTEMPT_RESERVED", actor_id, attempt_id)
        else:
            self.events.append(
                {
                    "execution_id": execution.id,
                    "sequence": sum(
                        event["execution_id"] == execution.id for event in self.events
                    ),
                    "kind": "ATTEMPT_RESERVED",
                    "prior_status": "PLANNED",
                    "new_status": "RUNNING",
                    "prior_row_version": 1,
                    "new_row_version": execution.row_version,
                    "created_by": actor_id,
                    "attempt_id": attempt_id,
                }
            )
        return attempt_id

    def attempts(self, execution_id: UUID) -> list[dict[str, object]]:
        return sorted(
            (row for row in self.attempt_rows.values() if row["execution_id"] == execution_id),
            key=lambda row: (
                int(cast(int, row["query_index"])),
                int(cast(int, row["attempt_number"])),
            ),
        )

    def reservation(self, attempt_id: UUID) -> dict[str, object] | None:
        row = self.attempt_rows.get(attempt_id)
        return None if row is None else row

    def seal(self, attempt_id: UUID, values: dict[str, object]) -> None:
        if self.attempt_rows[attempt_id]["status"] != "RESERVED":
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "provider attempt is sealed")
        self.attempt_rows[attempt_id].update(values)
        self.attempt_rows[attempt_id]["completed_at"] = datetime.now(UTC)
        self.attempt_rows[attempt_id]["row_version"] = int(
            cast(int, self.attempt_rows[attempt_id]["row_version"])
        ) + 1

    def append_query(self, record: SearchQueryRecord) -> None:
        self.queries.append(record)
        self.attempt_rows[record.attempt_id]["query_record_id"] = record.id

    def append_results(
        self, query_id: UUID, response: SearchResponse, retrieved_at: datetime
    ) -> None:
        query = next(record for record in self.queries if record.id == query_id)
        for rank, hit in enumerate(response.hits):
            self.results.append(
                {
                    "id": uuid4(),
                    "search_query_record_id": query_id,
                    "rank": rank,
                    "external_identifier": hit.external_identifier,
                    "title": hit.title,
                    "url": hit.url,
                    "snippet": hit.snippet,
                    "provider_score": hit.provider_score,
                    "content_hash": hit.result_hash(query.query_hash, rank),
                    "retrieved_at": retrieved_at,
                }
            )

    def append_event(
        self,
        execution: LiteratureSearchExecution,
        kind: str,
        actor_id: UUID,
        attempt_id: UUID | None = None,
    ) -> None:
        self.events.append(
            {
                "execution_id": execution.id,
                "sequence": sum(
                    event["execution_id"] == execution.id for event in self.events
                ),
                "kind": kind,
                "prior_status": (
                    None
                    if kind == "CREATED"
                    else "PLANNED"
                    if kind == "FINISHED" and execution.started_at is None
                    else "RUNNING"
                    if kind == "FINISHED"
                    else execution.status.value
                ),
                "new_status": execution.status.value,
                "prior_row_version": max(1, execution.row_version - 1),
                "new_row_version": execution.row_version,
                "created_by": actor_id,
                "attempt_id": attempt_id,
            }
        )

    def next_query_ordinal(self, execution_id: UUID) -> int:
        return sum(1 for query in self.queries if query.execution_id == execution_id)

    def provenance(self, execution_id: UUID) -> dict[str, object]:
        execution = self.get(execution_id)
        if execution is None:
            raise KeyError(execution_id)
        plan_hash, plan_material = self.plan_invocation(
            execution.project_id, execution.plan_version_id
        )
        queries = [q for q in self.queries if q.execution_id == execution_id]
        for query in queries:
            recomputed = SearchQueryRecord(
                query.id,
                query.execution_id,
                query.attempt_id,
                query.ordinal,
                query.query_text,
                query.provider_id,
                query.provider_version,
                query.executed_at,
                query.perspective,
            ).query_hash
            if query.query_hash != recomputed:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "query provenance digest mismatch"
                )
        query_by_id = {q.id: q for q in queries}
        for result in self.results:
            query = query_by_id.get(cast(UUID, result["search_query_record_id"]))
            if query is None:
                continue
            from researchbase.domain.literature_search_execution import SearchHit

            hit = SearchHit(
                cast(str | None, result.get("external_identifier")),
                str(result["title"]),
                cast(str | None, result.get("url")),
                cast(str | None, result.get("snippet")),
                cast(Any, result.get("provider_score")),
            )
            rank = cast(int, result["rank"])
            if hit.result_hash(query.query_hash, rank) != result["content_hash"]:
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
            "attempts": self.attempts(execution_id),
            "queries": queries,
            "results": [
                r
                for r in self.results
                if any(
                    q.id == r["search_query_record_id"]
                    for q in self.queries
                    if q.execution_id == execution_id
                )
            ],
            "events": sorted(
                [
                    deepcopy(event)
                    for event in self.events
                    if event["execution_id"] == execution_id
                ],
                key=lambda event: int(cast(int, event["sequence"])),
            ),
            "receipts": [
                {
                    "deployment_id": key[0],
                    "actor_id": str(key[1]),
                    "project_id": str(key[2]),
                    "command_name": key[3],
                    "request_id": str(key[4]),
                    "request_hash": str(sha256_canonical_json(value.get("payload", {}))),
                    "dto": value.get("dto"),
                }
                for key, value in self.receipts.items()
                if key[2] == execution.project_id
                and isinstance(value.get("dto"), dict)
                and cast(dict[str, object], value["dto"]).get("execution_id")
                == str(execution_id)
            ],
        }

    def list_executions(
        self, project_id: UUID, limit: int, after: UUID | None = None
    ) -> list[LiteratureSearchExecution]:
        rows = [row for row in self.executions.values() if row.project_id == project_id]
        ordered = sorted(
            rows,
            key=lambda row: (self.execution_created_at[row.id], row.id.int),
        )
        if after is not None:
            cursor = self.executions.get(after)
            if cursor is None or cursor.project_id != project_id:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "execution cursor not found")
            cursor_key = (self.execution_created_at[after], after.int)
            ordered = [
                row
                for row in ordered
                if (self.execution_created_at[row.id], row.id.int) > cursor_key
            ]
        return [deepcopy(row) for row in ordered[:limit]]


class InMemoryExecutionUnitOfWork:
    def __init__(self, repository: InMemoryLiteratureSearchExecutionRepository) -> None:
        self.literature_search_execution = repository
        self.literature_search_plan = _InMemoryProjectLockRepository()
        self.trace: list[str] = []
        self._snapshot: dict[str, object] | None = None
        self._committed = False

    def __enter__(self) -> InMemoryExecutionUnitOfWork:
        self.trace.append("TX_ENTER")
        self._snapshot = {
            name: deepcopy(getattr(self.literature_search_execution, name))
            for name in (
                "executions",
                "execution_created_at",
                "receipts",
                "attempt_rows",
                "queries",
                "results",
                "events",
            )
        }
        self._committed = False
        return self

    def begin_serializable(self) -> None:
        self.trace.append("TX_BEGIN")

    def commit(self) -> None:
        self.trace.append("TX_COMMIT")
        self._committed = True

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if (exc_type is not None or not self._committed) and self._snapshot is not None:
            for name, value in self._snapshot.items():
                setattr(self.literature_search_execution, name, value)
        self.trace.append("TX_EXIT")


class _InMemoryProjectLockRepository:
    def lock_project(self, project_id: UUID) -> None:
        return None

    def lock_literature_search_execution_command(
        self,
        deployment_id: str,
        actor_id: UUID,
        project_id: UUID,
        command_name: str,
        request_id: UUID,
    ) -> None:
        return None
