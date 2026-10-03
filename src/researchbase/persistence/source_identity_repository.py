"""Synchronous PostgreSQL adapter for PR2-01 source identity transactions."""

# SQL statement text intentionally follows PostgreSQL grammar inline.
# ruff: noqa: E501

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class SqlAlchemySourceIdentityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def database_time(self) -> datetime:
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one()

    def lock_command(
        self,
        principal: VerifiedPrincipal,
        project_id: UUID,
        command_name: str,
        request_id: UUID,
    ) -> None:
        self._lock_advisory(f"researchbase-project:{project_id}")
        self._session.execute(
            text("SELECT id FROM projects WHERE id=:project_id FOR UPDATE"),
            {"project_id": project_id},
        )
        self._lock_advisory(
            f"literature-receipt:{principal.deployment_id}:{project_id}:"
            f"{principal.actor_id}:{command_name}:{request_id}"
        )

    def lock_identifier(self, identifier_type: str, normalized_value: str) -> None:
        self._lock_advisory(f"literature-identifier:{identifier_type}:{normalized_value}")

    def lock_source(self, source_id: UUID) -> None:
        self._lock_advisory(f"literature-source:{source_id}")
        self._session.execute(
            text("SELECT id FROM literature_sources WHERE id=:id FOR UPDATE"), {"id": source_id}
        )

    def _lock_advisory(self, resource: str) -> None:
        acquired = self._session.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:resource,0))"),
            {"resource": resource},
        ).scalar_one()
        if acquired:
            return
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:resource,0))"),
            {"resource": resource},
        )
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "concurrent source identity transaction requires a fresh retry",
        )

    def authorize(
        self,
        principal: VerifiedPrincipal,
        project_id: UUID,
        at: datetime,
    ) -> tuple[str, str] | None:
        row = self._session.execute(
            text(
                "SELECT a.actor_type, r.role FROM actors a "
                "JOIN project_memberships m ON m.actor_id=a.id AND m.status='ACTIVE' "
                "JOIN project_role_assignments r ON r.membership_id=m.id "
                " AND r.project_id=m.project_id AND r.actor_id=m.actor_id "
                "JOIN actor_subject_bindings b ON b.actor_id=a.id AND b.status='ACTIVE' "
                "WHERE a.id=:actor_id AND a.retired_at IS NULL AND m.project_id=:project_id "
                "AND b.deployment_id=:deployment AND b.subject_kind=:subject_kind "
                "AND b.subject_value=:subject_value AND b.subject_credential_id=:credential_id "
                "AND b.bound_at <= :at AND (b.revoked_at IS NULL OR :at < b.revoked_at) "
                "AND EXISTS (SELECT 1 FROM projects p WHERE p.id=m.project_id AND p.lifecycle_status='ACTIVE') "
                "AND r.effective_from <= :at AND (r.effective_until IS NULL OR :at < r.effective_until) "
                "ORDER BY CASE r.role WHEN 'OWNER' THEN 0 WHEN 'RESEARCHER' THEN 1 "
                "WHEN 'REVIEWER' THEN 2 WHEN 'APPROVER' THEN 3 ELSE 4 END LIMIT 1"
            ),
            {
                "actor_id": principal.actor_id,
                "project_id": project_id,
                "deployment": principal.deployment_id,
                "subject_kind": principal.subject_kind,
                "subject_value": principal.subject_value,
                "credential_id": principal.credential_id,
                "at": at,
            },
        ).first()
        return (str(row.actor_type), str(row.role)) if row else None

    def receipt(
        self, principal: VerifiedPrincipal, project_id: UUID, command_name: str, request_id: UUID
    ) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM literature_command_receipts WHERE deployment_id=:deployment "
                    "AND project_id=:project AND actor_id=:actor AND command_name=:command "
                    "AND request_id=:request_id"
                ),
                {
                    "deployment": principal.deployment_id,
                    "project": project_id,
                    "actor": principal.actor_id,
                    "command": command_name,
                    "request_id": request_id,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_source(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO literature_sources (id,source_kind,canonical_title,lifecycle_status,created_by,created_at,row_version) "
                "VALUES (:id,:kind,:title,'ACTIVE',:actor,:at,1)"
            ),
            values,
        )

    def insert_identifier(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO source_identifiers (id,literature_source_id,identifier_type,identifier_value,normalized_value,normalization_version,binding_basis_artifact_version_id,supersedes_rejected_identifier_id,is_primary,verification_status,created_by,created_at,row_version) "
                "VALUES (:id,:source,:type,:value,:normalized,:normalization_version,:basis,:supersedes,:is_primary,'UNVERIFIED',:actor,:at,1)"
            ),
            values,
        )

    def insert_link(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO literature_source_project_links (id,literature_source_id,project_id,linked_by,linked_at) "
                "VALUES (:id,:source,:project,:actor,:at) ON CONFLICT (literature_source_id,project_id) DO NOTHING"
            ),
            values,
        )

    def source(
        self, source_id: UUID, project_id: UUID, *, lock: bool = False
    ) -> dict[str, object] | None:
        suffix = " FOR UPDATE OF s" if lock else ""
        row = (
            self._session.execute(
                text(
                    "SELECT s.* FROM literature_sources s JOIN literature_source_project_links l "
                    "ON l.literature_source_id=s.id WHERE s.id=:source AND l.project_id=:project"
                    + suffix
                ),
                {"source": source_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def source_by_identifier(
        self, identifier_type: str, normalized_value: str, *, lock: bool = False
    ) -> dict[str, object] | None:
        suffix = " FOR UPDATE OF si" if lock else ""
        row = (
            self._session.execute(
                text(
                    "SELECT si.*, s.source_kind, s.canonical_title FROM source_identifiers si "
                    "JOIN literature_sources s ON s.id=si.literature_source_id "
                    "WHERE si.identifier_type=:type AND si.normalized_value=:normalized "
                    "AND si.verification_status IN ('UNVERIFIED','VERIFIED')" + suffix
                ),
                {"type": identifier_type, "normalized": normalized_value},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def identifier(
        self, identifier_id: UUID, project_id: UUID, *, lock: bool = False
    ) -> dict[str, object] | None:
        suffix = " FOR UPDATE OF si" if lock else ""
        row = (
            self._session.execute(
                text(
                    "SELECT si.* FROM source_identifiers si JOIN literature_source_project_links l "
                    "ON l.literature_source_id=si.literature_source_id WHERE si.id=:id AND l.project_id=:project"
                    + suffix
                ),
                {"id": identifier_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def link_count(self, source_id: UUID) -> int:
        return int(
            self._session.execute(
                text(
                    "SELECT count(*) FROM literature_source_project_links WHERE literature_source_id=:id"
                ),
                {"id": source_id},
            ).scalar_one()
        )

    def has_rejected_identifier(self, identifier_type: str, normalized_value: str) -> bool:
        return bool(
            self._session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM source_identifiers WHERE identifier_type=:type AND normalized_value=:normalized AND verification_status='REJECTED')"
                ),
                {"type": identifier_type, "normalized": normalized_value},
            ).scalar_one()
        )

    def basis_is_frozen(self, artifact_version_id: UUID) -> bool:
        status = self._session.execute(
            text("SELECT status FROM artifact_versions WHERE id=:id FOR SHARE"),
            {"id": artifact_version_id},
        ).scalar_one_or_none()
        return status == "FROZEN"

    def transition_identifier(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "UPDATE source_identifiers SET verification_status=:status,verified_at=:verified_at,verified_by=:verified_by,"
                "verification_basis_artifact_version_id=:basis,row_version=row_version+1 WHERE id=:id"
            ),
            values,
        )

    def insert_verification_event(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO source_identifier_verification_events (id,source_identifier_id,prior_status,new_status,basis_artifact_version_id,verified_by,occurred_at,reason,request_id) "
                "VALUES (:id,:identifier,:prior,:new,:basis,:actor,:at,:reason,:request_id)"
            ),
            values,
        )

    def insert_receipt(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO literature_command_receipts (id,deployment_id,project_id,actor_id,command_name,request_id,input_hash,hash_scheme,result_source_id,result_identifier_id,result_verification_event_id,result_dto_version,result_dto,completed_at) "
                "VALUES (:id,:deployment,:project,:actor,:command,:request_id,:hash,'sha256-cjson-v1',:source,:identifier,:event,1,CAST(:dto AS jsonb),:at)"
            ),
            values,
        )

    def list_identifiers(self, source_id: UUID, project_id: UUID) -> list[dict[str, object]]:
        rows = (
            self._session.execute(
                text(
                    "SELECT si.* FROM source_identifiers si JOIN literature_source_project_links l "
                    "ON l.literature_source_id=si.literature_source_id WHERE si.literature_source_id=:source "
                    "AND l.project_id=:project ORDER BY si.created_at,si.id"
                ),
                {"source": source_id, "project": project_id},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def find_source(
        self, project_id: UUID, identifier_type: str, normalized_value: str
    ) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT resolved.* FROM source_identifiers si "
                    "JOIN literature_sources s ON s.id=si.literature_source_id "
                    "JOIN literature_sources resolved ON resolved.id=CASE "
                    "WHEN s.lifecycle_status='MERGED' THEN s.merged_into_source_id ELSE s.id END "
                    "JOIN literature_source_project_links l ON l.literature_source_id=s.id AND l.project_id=:project "
                    "WHERE si.identifier_type=:type AND si.normalized_value=:normalized "
                    "AND si.verification_status IN ('UNVERIFIED','VERIFIED')"
                ),
                {"project": project_id, "type": identifier_type, "normalized": normalized_value},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def execute_count(self, statement: str, values: dict[str, Any]) -> int:
        return int(self._session.execute(text(statement), values).scalar_one())
