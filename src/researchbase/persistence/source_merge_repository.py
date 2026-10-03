"""PostgreSQL persistence for typed source-merge governance decisions."""

# SQL follows PostgreSQL grammar and uses literal acceptance constraints.
# ruff: noqa: E501

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlAlchemySourceMergeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_project(self, project_id: UUID) -> None:
        self._session.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project_id})
        self._session.execute(
            text("SELECT id FROM projects WHERE id=:id FOR UPDATE"), {"id": project_id}
        )

    def lock_command(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ) -> None:
        key = f"source-merge-receipt:{deployment}:{project}:{actor}:{command}:{request}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def lock_identifier(self, identifier_type: str, normalized_value: str) -> None:
        key = f"literature-identifier:{identifier_type}:{normalized_value}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def lock_source(self, source_id: UUID) -> None:
        key = f"literature-source:{source_id}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )
        self._session.execute(
            text("SELECT id FROM literature_sources WHERE id=:id FOR UPDATE"), {"id": source_id}
        )

    def at(self):
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one()

    def authorize(self, principal, project_id: UUID, at) -> dict[str, Any] | None:
        row = (
            self._session.execute(
                text("""SELECT a.actor_type, a.retired_at, m.id AS membership_id, m.status AS membership_status,
                         r.id AS role_assignment_id, r.role, r.effective_from, r.effective_until,
                         b.id AS binding_id, b.status AS binding_status, b.bound_at, b.revoked_at
                  FROM actors a JOIN project_memberships m ON m.actor_id=a.id
                  JOIN project_role_assignments r ON r.membership_id=m.id AND r.project_id=m.project_id
                    AND r.actor_id=m.actor_id
                  JOIN actor_subject_bindings b ON b.actor_id=a.id
                  WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
                    AND b.subject_kind=:kind AND b.subject_value=:value
                    AND b.subject_credential_id=:credential
                  ORDER BY b.bound_at DESC LIMIT 1
                  FOR UPDATE OF a,m,r,b"""),
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

    def source_exists(self, source_id: UUID) -> bool:
        return bool(
            self._session.execute(
                text("SELECT EXISTS(SELECT 1 FROM literature_sources WHERE id=:id)"),
                {"id": source_id},
            ).scalar_one()
        )

    def project_has_source(self, source_ids: tuple[UUID, UUID], project_id: UUID) -> bool:
        return bool(
            self._session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM literature_source_project_links WHERE project_id=:project AND literature_source_id = ANY(:sources))"
                ),
                {"project": project_id, "sources": list(source_ids)},
            ).scalar_one()
        )

    def link_rows(self, source_ids: tuple[UUID, UUID]) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT id AS link_id, literature_source_id AS source_id, project_id FROM literature_source_project_links WHERE literature_source_id = ANY(:sources) ORDER BY literature_source_id,project_id,id"
                ),
                {"sources": list(source_ids)},
            ).mappings()
        ]

    def identifier_rows(self, source_ids: tuple[UUID, UUID]) -> list[dict[str, Any]]:
        sql = text("""SELECT id AS identifier_id, literature_source_id AS source_id, identifier_type,
                           normalized_value, normalization_version, verification_status, is_primary,
                           binding_basis_artifact_version_id, supersedes_rejected_identifier_id,
                           verification_basis_artifact_version_id, verified_by, verified_at,
                           row_version
                    FROM source_identifiers WHERE literature_source_id = ANY(:sources)
                    ORDER BY identifier_type,normalized_value,id""")
        return [
            dict(row)
            for row in self._session.execute(sql, {"sources": list(source_ids)}).mappings()
        ]

    def lock_basis_rows(self, source_ids: tuple[UUID, UUID]) -> None:
        self._session.execute(
            text(
                "SELECT id FROM literature_source_project_links WHERE literature_source_id = ANY(:ids) ORDER BY project_id,literature_source_id,id FOR UPDATE"
            ),
            {"ids": list(source_ids)},
        ).all()
        self._session.execute(
            text(
                "SELECT id FROM source_identifiers WHERE literature_source_id = ANY(:ids) ORDER BY identifier_type,normalized_value,id FOR UPDATE"
            ),
            {"ids": list(source_ids)},
        ).all()

    def receipt(self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID):
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM source_merge_governance_events WHERE deployment_id=:deployment AND project_id=:project AND actor_id=:actor AND command_name=:command AND request_id=:request"
                ),
                {
                    "deployment": deployment,
                    "project": project,
                    "actor": actor,
                    "command": command,
                    "request": request,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_proposal(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO source_merge_proposals
          (id,deployment_id,source_a_id,source_b_id,canonical_survivor_id,proposed_by_actor_id,
           proposed_in_project_id,rationale,basis_contract_version,identifier_basis_hash,
           source_version_basis_hash,proposal_basis_hash,hash_scheme,request_id,request_hash,
           result_dto_version,result_dto,created_at,supersedes_proposal_id,command_name)
          VALUES (:id,:deployment,:a,:b,:survivor,:actor,:project,:rationale,'source-merge-basis-v1',
           :identifier_hash,:version_hash,:basis_hash,'sha256-cjson-v1',:request,:request_hash,1,
           CAST(:dto AS jsonb),:at,:supersedes,:command)"""),
            values,
        )

    def insert_project_basis(self, proposal_id, rows, at, link_hashes) -> None:
        for row, link_hash in zip(rows, link_hashes, strict=True):
            self._session.execute(
                text(
                    "INSERT INTO source_merge_proposal_projects(proposal_id,project_id,source_a_link_id,source_b_link_id,captured_at,link_basis_hash) VALUES (:proposal,:project,:a,:b,:at,:hash)"
                ),
                {
                    "proposal": proposal_id,
                    "project": row["project_id"],
                    "a": row["a"],
                    "b": row["b"],
                    "at": at,
                    "hash": link_hash,
                },
            )

    def insert_identifier_basis(self, proposal_id, rows) -> None:
        for row in rows:
            row["proposal_id"] = proposal_id
            self._session.execute(
                text("""INSERT INTO source_merge_proposal_identifier_basis
              (proposal_id,identifier_id,source_id,identifier_type,normalized_value,normalization_version,
               verification_status,is_primary,binding_basis_artifact_version_id,supersedes_rejected_identifier_id,
               verification_basis_artifact_version_id,verified_by,verified_at,captured_row_version)
              VALUES (:proposal_id,:identifier_id,:source_id,:identifier_type,:normalized_value,:normalization_version,
               :verification_status,:is_primary,:binding_basis_artifact_version_id,:supersedes_rejected_identifier_id,
               :verification_basis_artifact_version_id,:verified_by,:verified_at,:row_version)"""),
                row,
            )

    def insert_source_basis(self, proposal_id, source_ids, at, state_hash) -> None:
        for source_id in source_ids:
            self._session.execute(
                text(
                    "INSERT INTO source_merge_proposal_source_basis(proposal_id,source_id,current_version_id,current_version_hash,version_state_hash,captured_at) VALUES (:proposal,:source,NULL,NULL,:hash,:at)"
                ),
                {"proposal": proposal_id, "source": source_id, "hash": state_hash, "at": at},
            )

    def frozen_artifact_refs(
        self, artifact_ids: tuple[UUID, ...], project_id: UUID
    ) -> list[dict[str, str]]:
        if not artifact_ids:
            return []
        rows = [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT v.id,v.content_hash FROM artifact_versions v "
                    "JOIN artifacts a ON a.id=v.artifact_id "
                    "WHERE v.id=ANY(:ids) AND v.status='FROZEN' AND a.project_id=:project "
                    "ORDER BY v.id"
                ),
                {"ids": list(artifact_ids), "project": project_id},
            ).mappings()
        ]
        if len(rows) != len(set(artifact_ids)):
            raise ValueError("all evidence artifacts must exist and be frozen")
        return [{"id": str(row["id"]), "content_hash": str(row["content_hash"])} for row in rows]

    def insert_proposal_evidence(self, proposal_id: UUID, refs: list[dict[str, str]]) -> None:
        for ref in refs:
            self._session.execute(
                text(
                    "INSERT INTO source_merge_proposal_evidence"
                    "(proposal_id,artifact_version_id,content_hash) VALUES (:proposal,:artifact,:hash)"
                ),
                {"proposal": proposal_id, "artifact": UUID(ref["id"]), "hash": ref["content_hash"]},
            )

    def proposal_evidence_refs(self, proposal_id: UUID) -> list[dict[str, str]]:
        return [
            {"id": str(row["artifact_version_id"]), "content_hash": str(row["content_hash"])}
            for row in self._session.execute(
                text(
                    "SELECT artifact_version_id,content_hash FROM source_merge_proposal_evidence "
                    "WHERE proposal_id=:proposal ORDER BY artifact_version_id,content_hash"
                ),
                {"proposal": proposal_id},
            ).mappings()
        ]

    def insert_event(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text(
                "INSERT INTO source_merge_governance_events(id,proposal_id,approval_id,project_id,actor_id,event_kind,occurred_at,reason,deployment_id,request_id,request_hash,basis_hash,command_name) VALUES (:id,:proposal,:approval,:project,:actor,:kind,:at,:reason,:deployment,:request,:request_hash,:basis_hash,:command)"
            ),
            values,
        )

    def event_request(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ):
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM source_merge_governance_events WHERE deployment_id=:deployment AND project_id=:project AND actor_id=:actor AND command_name=:command AND request_id=:request"
                ),
                {
                    "deployment": deployment,
                    "project": project,
                    "actor": actor,
                    "command": command,
                    "request": request,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def proposal(self, proposal_id: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        row = (
            self._session.execute(
                text("SELECT * FROM source_merge_proposals WHERE id=:id" + suffix),
                {"id": proposal_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def proposal_request(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ):
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM source_merge_proposals WHERE deployment_id=:deployment AND proposed_in_project_id=:project AND proposed_by_actor_id=:actor AND command_name=:command AND request_id=:request"
                ),
                {
                    "deployment": deployment,
                    "project": project,
                    "actor": actor,
                    "command": command,
                    "request": request,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def decision_request(
        self, deployment: str, project: UUID, actor: UUID, command: str, request: UUID
    ):
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM source_merge_approvals WHERE deployment_id=:deployment AND project_id=:project AND approver_actor_id=:actor AND command_name=:command AND request_id=:request"
                ),
                {
                    "deployment": deployment,
                    "project": project,
                    "actor": actor,
                    "command": command,
                    "request": request,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def project_ids_for_proposal(self, proposal_id: UUID) -> list[UUID]:
        return list(
            self._session.execute(
                text(
                    "SELECT project_id FROM source_merge_proposal_projects WHERE proposal_id=:id ORDER BY project_id"
                ),
                {"id": proposal_id},
            ).scalars()
        )

    def decisions(self, proposal_id: UUID):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM source_merge_approvals WHERE proposal_id=:id ORDER BY project_id"
                ),
                {"id": proposal_id},
            ).mappings()
        ]

    def events(self, proposal_id: UUID):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM source_merge_governance_events WHERE proposal_id=:id ORDER BY occurred_at,id"
                ),
                {"id": proposal_id},
            ).mappings()
        ]

    def project_decision(self, proposal_id: UUID, project_id: UUID):
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM source_merge_approvals WHERE proposal_id=:proposal AND project_id=:project"
                ),
                {"proposal": proposal_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_decision(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO source_merge_approvals
          (id,proposal_id,project_id,decision,decision_reason,decision_payload_hash,approver_actor_id,
           membership_id,owner_role_assignment_id,deployment_id,credential_id,trusted_subject_kind,
           trusted_subject_value,principal_verified_at,decision_basis_hash,request_id,request_hash,
           command_name,result_dto_version,result_dto,decided_at)
          VALUES (:id,:proposal,:project,:decision,:reason,:payload_hash,:actor,:membership,:role,
           :deployment,:credential,:subject_kind,:subject_value,:verified_at,:basis_hash,:request,
           :request_hash,:command,1,CAST(:dto AS jsonb),:at)"""),
            values,
        )
