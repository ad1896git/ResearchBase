"""Typed, project-confined PostgreSQL operations for R2 ScientificConclusion."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.foundation.canonical_json import canonical_json_text


class SqlAlchemyScientificConclusionRepository:
    def __init__(self, session: Session, *, protected_reads: bool = False) -> None:
        self._session = session
        self._protected_reads = protected_reads

    def lock_command(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ) -> None:
        key = f"scientific-conclusion:{deployment}:{project}:{actor}:{command}:{request}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def receipt(self, principal, project: UUID, command: str, request: UUID):
        return self._one(
            """SELECT * FROM scientific_conclusion_command_receipts
               WHERE deployment_id=:deployment AND project_id=:project AND actor_id=:actor
                 AND command_name=:command AND request_id=:request""",
            {
                "deployment": principal.deployment_id,
                "project": project,
                "actor": principal.actor_id,
                "command": command,
                "request": request,
            },
        )

    def save_receipt(self, row: dict[str, object]) -> None:
        self._insert("scientific_conclusion_command_receipts", row)

    def conclusion(self, identity: UUID, project: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        return self._one(
            "SELECT * FROM scientific_conclusions WHERE id=:id AND project_id=:project" + suffix,
            {"id": identity, "project": project},
        )

    def version(self, identity: UUID, conclusion: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        return self._one(
            """SELECT * FROM scientific_conclusion_versions
               WHERE id=:id AND scientific_conclusion_id=:conclusion"""
            + suffix,
            {"id": identity, "conclusion": conclusion},
        )

    def draft_version(self, conclusion: UUID):
        return self._one(
            """SELECT id FROM scientific_conclusion_versions
               WHERE scientific_conclusion_id=:conclusion AND status='DRAFT'""",
            {"conclusion": conclusion},
        )

    def next_version_number(self, conclusion: UUID) -> int:
        return int(
            self._session.execute(
                text("""SELECT COALESCE(max(version_number),0)+1
           FROM scientific_conclusion_versions WHERE scientific_conclusion_id=:conclusion"""),
                {"conclusion": conclusion},
            ).scalar_one()
        )

    def claim_reference(self, identity: UUID, project: UUID):
        return self._one(
            """SELECT v.id,v.content_hash,v.status,c.project_id FROM claim_versions v
               JOIN claims c ON c.id=v.claim_id
               WHERE v.id=:id AND c.project_id=:project"""
            + ("" if self._protected_reads else " FOR UPDATE OF v,c"),
            {"id": identity, "project": project},
        )

    def snapshot_reference(self, identity: UUID, project: UUID):
        return self._one(
            """SELECT id,project_id,claim_version_id,content_hash
               FROM literature_support_snapshots
               WHERE id=:id AND project_id=:project""",
            {"id": identity, "project": project},
        )

    def evidence_reference(self, identity: UUID, project: UUID):
        return self._one(
            """SELECT id,project_id,content_hash,created_by,review_status
               FROM literature_evidence WHERE id=:id AND project_id=:project""",
            {"id": identity, "project": project},
        )

    def human_actor(self, identity: UUID) -> bool:
        return bool(
            self._session.execute(
                text("""SELECT EXISTS(
           SELECT 1 FROM actors WHERE id=:id AND actor_type='HUMAN')"""),
                {"id": identity},
            ).scalar_one()
        )

    def claim_inputs(self, version: UUID):
        return self._many(
            """SELECT * FROM scientific_conclusion_claim_inputs
               WHERE conclusion_version_id=:version ORDER BY ordinal,claim_version_id""",
            {"version": version},
        )

    def literature_inputs(self, version: UUID):
        return self._many(
            """SELECT * FROM scientific_conclusion_literature_inputs
               WHERE conclusion_version_id=:version ORDER BY ordinal,literature_evidence_id""",
            {"version": version},
        )

    def insert_conclusion(self, row: dict[str, object]) -> None:
        self._insert("scientific_conclusions", row)

    def insert_version(self, row: dict[str, object]) -> None:
        self._insert("scientific_conclusion_versions", row, {"scope"})

    def insert_claim_input(self, row: dict[str, object]) -> None:
        self._insert("scientific_conclusion_claim_inputs", row)

    def insert_literature_input(self, row: dict[str, object]) -> None:
        self._insert("scientific_conclusion_literature_inputs", row)

    def clear_draft_inputs(self, version: UUID) -> None:
        self._session.execute(
            text("""DELETE FROM scientific_conclusion_claim_inputs
           WHERE conclusion_version_id=:version"""),
            {"version": version},
        )
        self._session.execute(
            text("""DELETE FROM scientific_conclusion_literature_inputs
           WHERE conclusion_version_id=:version"""),
            {"version": version},
        )

    def freeze(
        self,
        conclusion: UUID,
        version: UUID,
        actor: UUID,
        at,
        support_hash: str,
        content_hash: str,
        previous: UUID | None,
    ) -> None:
        self._session.execute(
            text("""UPDATE scientific_conclusion_versions
           SET status='FROZEN',support_set_hash=:support,content_hash=:content,
               frozen_at=:at,row_version=row_version+1
           WHERE id=:version AND scientific_conclusion_id=:conclusion AND status='DRAFT'"""),
            {
                "support": support_hash,
                "content": content_hash,
                "at": at,
                "version": version,
                "conclusion": conclusion,
            },
        )
        if previous is not None:
            self._session.execute(
                text("""UPDATE scientific_conclusion_versions
               SET status='SUPERSEDED',row_version=row_version+1
               WHERE id=:previous AND scientific_conclusion_id=:conclusion AND status='FROZEN'"""),
                {"previous": previous, "conclusion": conclusion},
            )
        self._session.execute(
            text("""UPDATE scientific_conclusions
           SET current_version_id=:version,row_version=row_version+1
           WHERE id=:conclusion AND current_version_id IS NOT DISTINCT FROM :previous"""),
            {"version": version, "conclusion": conclusion, "previous": previous},
        )

    def _one(self, sql: str, params: dict[str, object]):
        row = self._session.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    def _many(self, sql: str, params: dict[str, object]):
        return [dict(row) for row in self._session.execute(text(sql), params).mappings()]

    def _insert(
        self,
        table: str,
        row: dict[str, object],
        json_fields: frozenset[str] | set[str] = frozenset(),
    ) -> None:
        # Every table and column originates from fixed internal call sites.
        names = tuple(row)
        values = {
            key: canonical_json_text(value) if key in json_fields else value
            for key, value in row.items()
        }
        placeholders = [
            f"CAST(:{name} AS jsonb)" if name in json_fields else f":{name}" for name in names
        ]
        self._session.execute(
            text(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join(placeholders)})"),
            values,
        )
