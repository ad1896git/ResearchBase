"""Synchronous, typed PostgreSQL operations for the PR2-10 discussion aggregate."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_INPUT_TABLES = {
    "question": "discussion_session_question_inputs",
    "claim": "discussion_session_claim_inputs",
    "source": "discussion_session_source_inputs",
}
_CITATION_TABLES = {
    "claim": "discussion_turn_claim_citations",
    "source": "discussion_turn_source_citations",
}
_REFERENCE_QUERIES = {
    "question": """SELECT EXISTS(SELECT 1 FROM research_question_versions v
        JOIN research_questions q ON q.id=v.research_question_id
        WHERE v.id=:version AND q.project_id=:project
          AND v.status IN ('FROZEN','SUPERSEDED'))""",
    "claim": """SELECT EXISTS(SELECT 1 FROM claim_versions v
        JOIN claims c ON c.id=v.claim_id
        WHERE v.id=:version AND c.project_id=:project
          AND v.status IN ('FROZEN','SUPERSEDED'))""",
    "source": """SELECT EXISTS(SELECT 1 FROM source_versions v
        JOIN literature_source_project_links l
          ON l.literature_source_id=v.literature_source_id
        WHERE v.id=:version AND l.project_id=:project
          AND v.status IN ('FROZEN','SUPERSEDED'))""",
}


class SqlAlchemyDiscussionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_command(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ) -> None:
        key = f"discussion-receipt:{deployment}:{project}:{actor}:{command}:{request}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def receipt(self, principal, project: UUID, command: str, request: UUID):
        row = self._session.execute(
            text("""SELECT * FROM discussion_command_receipts
                WHERE deployment_id=:deployment AND project_id=:project AND actor_id=:actor
                  AND command_name=:command AND request_id=:request"""),
            {
                "deployment": principal.deployment_id,
                "project": project,
                "actor": principal.actor_id,
                "command": command,
                "request": request,
            },
        ).mappings().first()
        return dict(row) if row else None

    def save_receipt(self, row: dict[str, object]) -> None:
        self._insert("discussion_command_receipts", row)

    def reference_valid(self, kind: str, version: UUID, project: UUID) -> bool:
        return bool(self._session.execute(
            text(_REFERENCE_QUERIES[kind]), {"version": version, "project": project}
        ).scalar_one())

    def session(self, session_id: UUID, project: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        row = self._session.execute(
            text(
                "SELECT * FROM discussion_sessions WHERE id=:id AND project_id=:project" + suffix
            ),
            {"id": session_id, "project": project},
        ).mappings().first()
        return dict(row) if row else None

    def turn(self, turn_id: UUID, session_id: UUID):
        row = self._session.execute(
            text("SELECT * FROM discussion_turns WHERE id=:id AND session_id=:session"),
            {"id": turn_id, "session": session_id},
        ).mappings().first()
        return dict(row) if row else None

    def insert_session(self, row: dict[str, object]) -> None:
        self._insert("discussion_sessions", row)

    def insert_inputs(self, session_id: UUID, kind: str, version_ids: tuple[UUID, ...]) -> None:
        table = _INPUT_TABLES[kind]
        for ordinal, version_id in enumerate(version_ids):
            self._insert(table, {
                "session_id": session_id, "version_id": version_id, "ordinal": ordinal
            })

    def insert_turn(self, row: dict[str, object]) -> None:
        self._insert("discussion_turns", row)

    def insert_citations(self, turn_id: UUID, kind: str, version_ids: tuple[UUID, ...]) -> None:
        table = _CITATION_TABLES[kind]
        for ordinal, version_id in enumerate(version_ids):
            self._insert(table, {
                "turn_id": turn_id, "version_id": version_id, "ordinal": ordinal
            })

    def next_ordinal(self, session_id: UUID) -> int:
        return int(self._session.execute(
            text("SELECT COALESCE(max(ordinal),0)+1 FROM discussion_turns WHERE session_id=:id"),
            {"id": session_id},
        ).scalar_one())

    def close_session(self, session_id: UUID, project: UUID, actor: UUID, at) -> None:
        self._session.execute(
            text("""UPDATE discussion_sessions SET status='CLOSED',closed_by=:actor,
                closed_at=:at,row_version=row_version+1
                WHERE id=:id AND project_id=:project AND status='OPEN'"""),
            {"actor": actor, "at": at, "id": session_id, "project": project},
        )

    def transcript_version(self, version_id: UUID, project: UUID):
        row = self._session.execute(text("""SELECT v.id,v.status,v.frozen_at,v.content_hash,
            v.byte_size,v.media_type,a.artifact_type,a.project_id
            FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
            WHERE v.id=:version AND a.project_id=:project"""),
            {"version": version_id, "project": project}).mappings().first()
        return dict(row) if row else None

    def bind_transcript(self, session_id: UUID, project: UUID, version_id: UUID) -> None:
        self._session.execute(text("""UPDATE discussion_sessions
            SET transcript_artifact_version_id=:version,row_version=row_version+1
            WHERE id=:session AND project_id=:project AND status='CLOSED'
              AND transcript_artifact_version_id IS NULL"""),
            {"version": version_id, "session": session_id, "project": project})

    def input_ids(self, session_id: UUID, kind: str) -> tuple[UUID, ...]:
        table = _INPUT_TABLES[kind]
        return tuple(self._session.execute(
            text(f"SELECT version_id FROM {table} WHERE session_id=:id ORDER BY ordinal"),
            {"id": session_id},
        ).scalars())

    def turn_rows(self, session_id: UUID):
        return [dict(row) for row in self._session.execute(
            text("SELECT * FROM discussion_turns WHERE session_id=:id ORDER BY ordinal"),
            {"id": session_id},
        ).mappings()]

    def citation_ids(self, turn_id: UUID, kind: str) -> tuple[UUID, ...]:
        table = _CITATION_TABLES[kind]
        return tuple(self._session.execute(
            text(f"SELECT version_id FROM {table} WHERE turn_id=:id ORDER BY ordinal"),
            {"id": turn_id},
        ).scalars())

    def _insert(self, table: str, row: dict[str, object]) -> None:
        # Only fixed internal table names and columns reach this helper.
        columns = tuple(row)
        self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(columns)}) "
                f"VALUES ({','.join(':'+column for column in columns)})"
            ),
            row,
        )
