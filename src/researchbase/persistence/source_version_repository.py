"""PostgreSQL persistence for immutable LiteratureSource versions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlAlchemySourceVersionRepository:
    def __init__(self, session: Session, *, protected_reads: bool = False) -> None:
        self._session = session
        self._protected_reads = protected_reads

    def prepare_write(self, *, freeze: bool = False) -> None:
        # Reserve the final write modes in SHARE inventory order before any
        # source/authority row lock; freeze writes both version and current pointer.
        tables = "literature_sources,source_versions" if freeze else "source_versions"
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._session.execute(text("LOCK TABLE " + tables + " IN ROW EXCLUSIVE MODE"))

    def lock_project(self, project_id: UUID) -> None:
        self._session.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project_id})
        self._session.execute(
            text("SELECT id FROM projects WHERE id=:id FOR UPDATE"), {"id": project_id}
        )

    def lock_command(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ) -> None:
        key = f"source-version-receipt:{deployment}:{actor}:{project}:{command}:{request}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def lock_source(self, source_id: UUID) -> dict[str, Any] | None:
        row = (
            self._session.execute(
                text("SELECT * FROM literature_sources WHERE id=:id FOR UPDATE"), {"id": source_id}
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def source(
        self, source_id: UUID, project_id: UUID, *, lock: bool = False
    ) -> dict[str, Any] | None:
        suffix = " FOR UPDATE OF s" if lock and not self._protected_reads else ""
        row = (
            self._session.execute(
                text(
                    """SELECT s.* FROM literature_sources s
                    JOIN literature_source_project_links l ON l.literature_source_id=s.id
                   WHERE s.id=:source AND l.project_id=:project"""
                    + suffix
                ),
                {"source": source_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def authorize(self, principal, project_id: UUID, at) -> dict[str, Any] | None:
        row = (
            self._session.execute(
                text("""SELECT a.actor_type, a.retired_at, m.id AS membership_id,
                         m.status AS membership_status, r.id AS role_assignment_id, r.role,
                         r.effective_from, r.effective_until, b.id AS binding_id,
                         b.status AS binding_status, b.bound_at, b.revoked_at
                    FROM actors a JOIN project_memberships m ON m.actor_id=a.id
                    JOIN project_role_assignments r ON r.membership_id=m.id
                      AND r.project_id=m.project_id AND r.actor_id=m.actor_id
                    JOIN actor_subject_bindings b ON b.actor_id=a.id
                   WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
                     AND b.subject_kind=:kind AND b.subject_value=:value
                     AND b.subject_credential_id=:credential
                   ORDER BY b.bound_at DESC LIMIT 1 FOR UPDATE OF a,m,r,b"""),
                {
                    "actor": principal.actor_id,
                    "project": project_id,
                    "deployment": principal.deployment_id,
                    "kind": principal.subject_kind,
                    "value": principal.subject_value,
                    "credential": principal.credential_id,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def at(self):
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one()

    def receipt(self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID):
        row = (
            self._session.execute(
                text("""SELECT * FROM source_version_command_receipts
                   WHERE deployment_id=:deployment AND actor_id=:actor AND project_id=:project
                     AND command_name=:command AND request_id=:request"""),
                {
                    "deployment": deployment,
                    "actor": actor,
                    "project": project,
                    "command": command,
                    "request": request,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def next_version_number(self, source_id: UUID) -> int:
        return int(
            self._session.execute(
                text(
                    "SELECT COALESCE(max(version_number),0)+1 FROM source_versions "
                    "WHERE literature_source_id=:source"
                ),
                {"source": source_id},
            ).scalar_one()
        )

    def insert_draft(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO source_versions
              (id,literature_source_id,version_number,version_kind,predecessor_source_version_id,
               correction_basis_artifact_version_id,title,abstract,authors,publication_date,venue,
               external_version_label,fulltext_artifact_version_id,metadata,status,hash_scheme,
               created_by,created_at)
              VALUES (:id,:source,:number,:kind,:predecessor,:correction_basis,:title,:abstract,
               CAST(:authors AS jsonb),:publication_date,:venue,:external_label,:fulltext,
               CAST(:metadata AS jsonb),'DRAFT','sha256-cjson-v1',:actor,:at)"""),
            values,
        )

    def version(self, version_id: UUID, *, lock: bool = False) -> dict[str, Any] | None:
        suffix = " FOR UPDATE" if lock and not self._protected_reads else ""
        row = (
            self._session.execute(
                text("SELECT * FROM source_versions WHERE id=:id" + suffix), {"id": version_id}
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def versions_for_source(self, source_id: UUID) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                "SELECT * FROM source_versions WHERE literature_source_id=:source "
                "ORDER BY version_number,id"
            ),
            {"source": source_id},
        ).mappings()
        return [dict(row) for row in rows]

    def update_draft(self, version_id: UUID, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""UPDATE source_versions SET version_kind=:kind,
              predecessor_source_version_id=:predecessor,
              correction_basis_artifact_version_id=:correction_basis,title=:title,abstract=:abstract,
              authors=CAST(:authors AS jsonb),publication_date=:publication_date,venue=:venue,
              external_version_label=:external_label,fulltext_artifact_version_id=:fulltext,
              metadata=CAST(:metadata AS jsonb) WHERE id=:id AND status='DRAFT'"""),
            {**values, "id": version_id},
        )

    def artifact_ref(self, artifact_id: UUID | None) -> dict[str, Any] | None:
        if artifact_id is None:
            return None
        row = (
            self._session.execute(
                text("SELECT id,content_hash,status FROM artifact_versions WHERE id=:id"),
                {"id": artifact_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def freeze(self, version_id: UUID, digest: str, at) -> None:
        self._session.execute(
            text(
                "UPDATE source_versions SET status='FROZEN',content_hash=:hash,frozen_at=:at "
                "WHERE id=:id AND status='DRAFT'"
            ),
            {"id": version_id, "hash": digest, "at": at},
        )

    def current_version(self, source_id: UUID) -> dict[str, Any] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT v.* FROM literature_sources s "
                    "JOIN source_versions v ON v.id=s.current_version_id "
                    "WHERE s.id=:source FOR UPDATE OF v"
                ),
                {"source": source_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def set_current(self, source_id: UUID, version_id: UUID) -> None:
        self._session.execute(
            text("UPDATE literature_sources SET current_version_id=:version WHERE id=:source"),
            {"source": source_id, "version": version_id},
        )

    def supersede(self, version_id: UUID) -> None:
        self._session.execute(
            text("UPDATE source_versions SET status='SUPERSEDED' WHERE id=:id AND status='FROZEN'"),
            {"id": version_id},
        )

    def abandon(self, version_id: UUID) -> None:
        self._session.execute(
            text("UPDATE source_versions SET status='ABANDONED' WHERE id=:id AND status='DRAFT'"),
            {"id": version_id},
        )

    def insert_receipt(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO source_version_command_receipts
              (id,deployment_id,project_id,actor_id,command_name,request_id,request_hash,
               hash_scheme,result_source_version_id,result_dto_version,result_dto,completed_at)
              VALUES (:id,:deployment,:project,:actor,:command,:request,:hash,'sha256-cjson-v1',
               :result_id,1,CAST(:dto AS jsonb),:at)"""),
            values,
        )
