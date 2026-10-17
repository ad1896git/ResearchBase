"""PostgreSQL persistence operations for LiteratureSearchPlan commands."""

# SQL statements preserve explicit relational operations and predicates.
# ruff: noqa: E501

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlAlchemyLiteratureSearchPlanRepository:
    def __init__(self, session: Session, *, protected_reads: bool = False) -> None:
        self._session = session
        self._protected_reads = protected_reads

    def lock_project(self, project_id: UUID) -> None:
        if self._protected_reads:
            return
        self._session.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project_id})
        self._session.execute(
            text("SELECT id FROM projects WHERE id=:id FOR UPDATE"), {"id": project_id}
        )

    def project_active(self, project_id: UUID) -> bool:
        status = self._session.execute(
            text("SELECT lifecycle_status FROM projects WHERE id=:id"), {"id": project_id}
        ).scalar_one_or_none()
        return status == "ACTIVE"

    def lock_command(
        self, deployment: str, actor: UUID, project: UUID, command: str, request: UUID
    ) -> None:
        key = f"search-plan-receipt:{deployment}:{actor}:{project}:{command}:{request}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def lock_literature_search_execution_command(
        self, deployment: str, actor: UUID, project: UUID, command: str, request: UUID
    ) -> None:
        key = f"literature-search-execution-receipt:{deployment}:{actor}:{project}:{command}:{request}"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def at(self):
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one()

    def authorize(self, principal, project_id: UUID):
        rows = (
            self._session.execute(
                text(
                    """SELECT a.actor_type, a.retired_at, m.status AS membership_status,
          r.role, r.effective_from, r.effective_until, b.status AS binding_status, b.bound_at, b.revoked_at
          FROM actors a JOIN project_memberships m ON m.actor_id=a.id
          JOIN project_role_assignments r ON r.membership_id=m.id AND r.project_id=m.project_id
            AND r.actor_id=m.actor_id JOIN actor_subject_bindings b ON b.actor_id=a.id
          WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
            AND b.subject_kind=:kind AND b.subject_value=:value AND b.subject_credential_id=:credential
          ORDER BY a.id,m.id,r.id,b.id"""
                    + ("" if self._protected_reads else " FOR UPDATE OF a,m,r,b")
                ),
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
            .all()
        )
        return [dict(row) for row in rows]

    def receipt(self, principal, project: UUID, command: str, request: UUID):
        row = (
            self._session.execute(
                text("""SELECT * FROM literature_search_plan_command_receipts
          WHERE deployment_id=:deployment AND actor_id=:actor AND project_id=:project
            AND command_name=:command AND request_id=:request"""),
                {
                    "deployment": principal.deployment_id,
                    "actor": principal.actor_id,
                    "project": project,
                    "command": command,
                    "request": request,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def plan(self, plan_id: UUID, project_id: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM literature_search_plans WHERE id=:id AND project_id=:project"
                    + suffix
                ),
                {"id": plan_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def version(self, version_id: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        row = (
            self._session.execute(
                text("SELECT * FROM literature_search_plan_versions WHERE id=:id" + suffix),
                {"id": version_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def lock_versions(self, version_ids: list[UUID]) -> None:
        self._session.execute(
            text(
                "SELECT id FROM literature_search_plan_versions WHERE id=ANY(:ids) ORDER BY id FOR UPDATE"
            ),
            {"ids": version_ids},
        ).all()

    def versions(self, plan_id: UUID):
        rows = self._session.execute(
            text(
                "SELECT * FROM literature_search_plan_versions WHERE plan_id=:id ORDER BY version_number,id"
            ),
            {"id": plan_id},
        ).mappings()
        return [dict(row) for row in rows]

    def plans(self, project_id: UUID):
        rows = self._session.execute(
            text(
                "SELECT * FROM literature_search_plans WHERE project_id=:project ORDER BY created_at,id"
            ),
            {"project": project_id},
        ).mappings()
        return [dict(row) for row in rows]

    def question_refs(self, version_id: UUID):
        rows = self._session.execute(
            text("""SELECT q.id AS research_question_id, q.project_id,
          qv.id AS version_id, qv.status, qv.question_text, qv.scope, qv.rationale,
          qv.version_number, qv.content_hash, 'sha256-cjson-v1' AS hash_scheme, qv.frozen_at,
          qv.created_by, qv.created_at, qv.row_version
          FROM search_plan_question_inputs i
          JOIN research_question_versions qv ON qv.id=i.research_question_version_id
          JOIN research_questions q ON q.id=qv.research_question_id
          WHERE i.plan_version_id=:id ORDER BY q.id,qv.id"""),
            {"id": version_id},
        ).mappings()
        return [dict(row) for row in rows]

    def lock_question_inputs(self, version_id: UUID) -> None:
        self._session.execute(
            text("""SELECT i.plan_version_id FROM search_plan_question_inputs i
              JOIN research_question_versions qv ON qv.id=i.research_question_version_id
              JOIN research_questions q ON q.id=qv.research_question_id
              WHERE i.plan_version_id=:id ORDER BY q.id,qv.id FOR UPDATE OF i"""),
            {"id": version_id},
        ).all()

    def question(self, version_id: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE OF q,qv" if lock else ""
        row = (
            self._session.execute(
                text(
                    """SELECT q.id AS research_question_id,q.project_id,
          qv.id AS version_id,qv.status,qv.question_text,qv.scope,qv.rationale,qv.version_number,
          qv.content_hash,'sha256-cjson-v1' AS hash_scheme,qv.frozen_at,qv.created_by,qv.created_at,qv.row_version
          FROM research_question_versions qv JOIN research_questions q ON q.id=qv.research_question_id
          WHERE qv.id=:id"""
                    + suffix
                ),
                {"id": version_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def next_number(self, plan_id: UUID) -> int:
        return int(
            self._session.execute(
                text(
                    "SELECT COALESCE(max(version_number),0)+1 FROM literature_search_plan_versions WHERE plan_id=:id"
                ),
                {"id": plan_id},
            ).scalar_one()
        )

    def insert_plan(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO literature_search_plans (id,project_id,created_by,created_at)
          VALUES (:id,:project,:actor,:at)"""),
            values,
        )

    def insert_version(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO literature_search_plan_versions
          (id,plan_id,version_number,status,objective,source_scope,inclusion_criteria,exclusion_criteria,
           time_range,language_scope,search_strategy,planned_providers,stopping_rule,hash_scheme,created_by,created_at)
          VALUES (:id,:plan,:number,'DRAFT',:objective,:source_scope,CAST(:inclusion AS jsonb),
           CAST(:exclusion AS jsonb),CAST(:time_range AS jsonb),CAST(:language_scope AS jsonb),
           :strategy,CAST(:providers AS jsonb),CAST(:stopping AS jsonb),'sha256-cjson-v1',:actor,:at)"""),
            values,
        )

    def update_draft(self, version_id: UUID, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""UPDATE literature_search_plan_versions SET objective=:objective,
          source_scope=:source_scope,inclusion_criteria=CAST(:inclusion AS jsonb),
          exclusion_criteria=CAST(:exclusion AS jsonb),time_range=CAST(:time_range AS jsonb),
          language_scope=CAST(:language_scope AS jsonb),search_strategy=:strategy,
          planned_providers=CAST(:providers AS jsonb),stopping_rule=CAST(:stopping AS jsonb),
          row_version=row_version+1 WHERE id=:id AND status='DRAFT'"""),
            {**values, "id": version_id},
        )

    def replace_questions(self, version_id: UUID, question_version_ids: list[UUID]) -> None:
        self._session.execute(
            text("DELETE FROM search_plan_question_inputs WHERE plan_version_id=:id"),
            {"id": version_id},
        )
        for ordinal, question_version_id in enumerate(question_version_ids):
            self._session.execute(
                text(
                    "INSERT INTO search_plan_question_inputs (plan_version_id,research_question_version_id,ordinal) VALUES (:plan,:question,:ordinal)"
                ),
                {"plan": version_id, "question": question_version_id, "ordinal": ordinal},
            )

    def add_question(self, version_id: UUID, question_version_id: UUID, ordinal: int) -> None:
        self._session.execute(
            text(
                "INSERT INTO search_plan_question_inputs (plan_version_id,research_question_version_id,ordinal) VALUES (:plan,:question,:ordinal)"
            ),
            {"plan": version_id, "question": question_version_id, "ordinal": ordinal},
        )

    def remove_question(self, version_id: UUID, question_id: UUID) -> bool:
        deleted = self._session.execute(
            text("""DELETE FROM search_plan_question_inputs i USING research_question_versions qv
          WHERE i.plan_version_id=:plan AND i.research_question_version_id=qv.id
            AND qv.research_question_id=:question RETURNING i.research_question_version_id"""),
            {"plan": version_id, "question": question_id},
        )
        if deleted.first() is None:
            return False
        self.canonicalize_questions(version_id)
        return True

    def canonicalize_questions(self, version_id: UUID) -> None:
        question_ids = (
            self._session.execute(
                text("""SELECT i.research_question_version_id FROM search_plan_question_inputs i
              JOIN research_question_versions qv ON qv.id=i.research_question_version_id
              JOIN research_questions q ON q.id=qv.research_question_id
              WHERE i.plan_version_id=:plan ORDER BY qv.id,qv.content_hash"""),
                {"plan": version_id},
            )
            .scalars()
            .all()
        )
        self._session.execute(
            text(
                "UPDATE search_plan_question_inputs SET ordinal=ordinal+1000000 WHERE plan_version_id=:plan"
            ),
            {"plan": version_id},
        )
        for ordinal, question_version_id in enumerate(question_ids):
            self._session.execute(
                text(
                    "UPDATE search_plan_question_inputs SET ordinal=:ordinal WHERE plan_version_id=:plan AND research_question_version_id=:question"
                ),
                {"plan": version_id, "question": question_version_id, "ordinal": ordinal},
            )

    def freeze(self, version_id: UUID, digest: str, at) -> None:
        self._session.execute(
            text(
                "UPDATE literature_search_plan_versions SET status='FROZEN',content_hash=:hash,frozen_at=:at,row_version=row_version+1 WHERE id=:id AND status='DRAFT'"
            ),
            {"id": version_id, "hash": digest, "at": at},
        )

    def supersede(self, version_id: UUID) -> None:
        self._session.execute(
            text(
                "UPDATE literature_search_plan_versions SET status='SUPERSEDED',row_version=row_version+1 WHERE id=:id AND status='FROZEN'"
            ),
            {"id": version_id},
        )

    def set_current(self, plan_id: UUID, version_id: UUID) -> None:
        self._session.execute(
            text(
                "UPDATE literature_search_plans SET current_version_id=:version,row_version=row_version+1 WHERE id=:plan"
            ),
            {"plan": plan_id, "version": version_id},
        )

    def abandon(self, version_id: UUID) -> None:
        self._session.execute(
            text(
                "UPDATE literature_search_plan_versions SET status='ABANDONED',row_version=row_version+1 WHERE id=:id AND status='DRAFT'"
            ),
            {"id": version_id},
        )

    def insert_receipt(self, values: dict[str, Any]) -> None:
        self._session.execute(
            text("""INSERT INTO literature_search_plan_command_receipts
          (id,deployment_id,actor_id,project_id,command_name,request_id,request_hash,hash_scheme,
           result_plan_id,result_plan_version_id,result_dto_version,result_dto,completed_at)
          VALUES (:id,:deployment,:actor,:project,:command,:request,:hash,'sha256-cjson-v1',
           :plan,:version,1,CAST(:dto AS jsonb),:at)"""),
            values,
        )
