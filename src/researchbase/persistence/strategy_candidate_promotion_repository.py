"""B02 SHARE-first writes and lock-free protected snapshot reads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

S = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "hypotheses",
    "hypothesis_versions",
    "literature_source_project_links",
    "literature_sources",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "research_question_versions",
    "research_questions",
    "source_versions",
    "strategy_candidate_captures",
    "strategy_candidate_sources",
    "strategy_hypothesis_admissions",
    "strategy_question_admissions",
)
TABLES = {
    "capture": "strategy_candidate_captures",
    "question": "strategy_question_admissions",
    "hypothesis": "strategy_hypothesis_admissions",
}


class SqlAlchemyStrategyCandidatePromotionRepository(SqlAlchemyNoveltyRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def prepare_write(self, kind: str, identity: UUID) -> None:
        self._session.execute(text("LOCK TABLE " + ",".join(S) + " IN SHARE MODE"))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b02:{kind}:{identity}"},
        )

    def exact(self, kind: str, identity: UUID, project: UUID) -> dict[str, Any] | None:
        row = self.one(
            f"SELECT * FROM {TABLES[kind]} WHERE id=:id AND project_id=:project",
            {"id": identity, "project": project},
        )
        if row:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.astimezone(UTC)
        return row

    def id_exists(self, kind: str, identity: UUID) -> bool:
        return self.one(f"SELECT id FROM {TABLES[kind]} WHERE id=:id", {"id": identity}) is not None

    def duplicate(self, kind: str, capture: UUID, index: int) -> bool:
        return (
            self.one(
                f"SELECT id FROM {TABLES[kind]} "
                "WHERE capture_id=:capture AND candidate_index=:index",
                {"capture": capture, "index": index},
            )
            is not None
        )

    def sources(self, identity: UUID) -> tuple[UUID, ...]:
        return tuple(
            row["source_version_id"]
            for row in self.many(
                "SELECT source_version_id FROM strategy_candidate_sources "
                "WHERE capture_id=:id ORDER BY source_version_id",
                {"id": identity},
            )
        )

    def insert(self, kind: str, row: dict[str, Any]) -> None:
        values = {k: v for k, v in row.items() if k != "source_version_ids"}
        self._session.execute(
            text(
                f"INSERT INTO {TABLES[kind]} ({','.join(values)}) "
                f"VALUES ({','.join(':' + k for k in values)})"
            ),
            values,
        )
        if kind == "capture":
            for source in row["source_version_ids"]:
                self._session.execute(
                    text("INSERT INTO strategy_candidate_sources VALUES (:capture,:source)"),
                    {"capture": row["id"], "source": source},
                )

    def artifact(self, identity: UUID) -> dict[str, Any] | None:
        return self.one(
            """SELECT v.*,a.project_id,a.artifact_type,a.created_by AS artifact_created_by,
            a.created_at AS artifact_created_at FROM artifact_versions v
            JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=:id""",
            {"id": identity},
        )

    def target(self, kind: str, version: UUID, identity: UUID, project: UUID) -> bool:
        table, versions, fk = (
            ("research_questions", "research_question_versions", "research_question_id")
            if kind == "question"
            else ("hypotheses", "hypothesis_versions", "hypothesis_id")
        )
        return (
            self.one(
                f"SELECT v.id FROM {versions} v JOIN {table} p ON p.id=v.{fk} "
                "WHERE v.id=:version AND p.id=:id AND p.project_id=:project",
                {"version": version, "id": identity, "project": project},
            )
            is not None
        )
