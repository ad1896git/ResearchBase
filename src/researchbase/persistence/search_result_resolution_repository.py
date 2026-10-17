"""B01 protected reads and writes of the existing M2 resolution relation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.persistence.metadata_observation_repository import (
    SqlAlchemyMetadataObservationRepository,
)
from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

R = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "literature_search_execution_command_receipts",
    "literature_search_execution_events",
    "literature_search_executions",
    "literature_search_plan_versions",
    "literature_search_plans",
    "literature_search_provider_attempts",
    "literature_source_project_links",
    "literature_sources",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "research_question_versions",
    "research_questions",
    "search_query_records",
    "search_result_records",
    "search_result_resolutions",
    "source_identifier_verification_events",
    "source_identifiers",
    "source_versions",
)


class SqlAlchemySearchResultResolutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._m2 = SqlAlchemyMetadataObservationRepository(session)
        self._reads = SqlAlchemyNoveltyRepository(session)

    def prepare_write(self, identity: UUID) -> None:
        self._session.execute(text("LOCK TABLE " + ",".join(R) + " IN SHARE MODE"))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b01:resolution:{identity}"},
        )

    def at(self) -> datetime:
        return self._reads.at()

    def authority(self, principal: VerifiedPrincipal, project: UUID) -> list[dict[str, Any]]:
        return self._reads.authority(principal, project)

    def exact(self, identity: UUID, project: UUID) -> dict[str, Any] | None:
        return self._reads.one(
            """SELECT s.* FROM search_result_resolutions s
            JOIN search_result_records r ON r.id=s.search_result_record_id
            JOIN search_query_records q ON q.id=r.search_query_record_id
            JOIN literature_search_executions e ON e.id=q.literature_search_execution_id
            WHERE s.id=:id AND e.project_id=:project""",
            {"id": identity, "project": project},
        )

    def id_exists(self, identity: UUID) -> bool:
        return (
            self._reads.one(
                "SELECT id FROM search_result_resolutions WHERE id=:id", {"id": identity}
            )
            is not None
        )

    def duplicate(self, result: UUID, source: UUID, version: UUID) -> bool:
        return self._m2.resolution(result, source, version) is not None

    def insert(self, row: dict[str, Any]) -> None:
        self._m2.insert_resolution(row)

    def force_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    def identifiers(self, doi: str) -> list[dict[str, Any]]:
        return self._reads.many(
            """SELECT * FROM source_identifiers
            WHERE identifier_type='DOI' AND normalized_value=:doi
              AND verification_status='VERIFIED' ORDER BY id""",
            {"doi": doi},
        )

    def verification_events(self, identity: UUID) -> list[dict[str, Any]]:
        return self._reads.many(
            """SELECT * FROM source_identifier_verification_events
            WHERE source_identifier_id=:id ORDER BY id""",
            {"id": identity},
        )

    def artifact(self, identity: UUID) -> dict[str, Any] | None:
        return self._reads.one(
            """SELECT v.*, a.project_id FROM artifact_versions v
            JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=:id""",
            {"id": identity},
        )
