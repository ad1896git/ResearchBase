"""PostgreSQL adapter for PR2-00 identity and authorization transactions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session


class SqlAlchemyPhase2IdentityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_bound_subject(self, subject: Any) -> dict[str, Any] | None:
        """Resolve one current HUMAN binding without the bootstrap-only join."""
        rows = (
            self._session.execute(
                text(
                    "SELECT b.actor_id, b.bound_at, b.revoked_at, a.retired_at "
                    "FROM actor_subject_bindings b "
                    "JOIN actors a ON a.id=b.actor_id "
                    "WHERE b.deployment_id=:deployment AND b.subject_kind=:kind "
                    "AND b.subject_value=:subject AND b.subject_credential_id=:credential "
                    "AND b.status='ACTIVE' AND a.actor_type='HUMAN'"
                ),
                {
                    "deployment": subject.deployment_id,
                    "kind": subject.subject_kind,
                    "subject": subject.subject_value,
                    "credential": subject.credential_id,
                },
            )
            .mappings()
            .all()
        )
        return dict(rows[0]) if len(rows) == 1 else None

    def resolve_local_binding(self, subject: Any) -> dict[str, Any] | None:
        rows = (
            self._session.execute(
                text(
                    "SELECT b.actor_id, b.bound_at, b.revoked_at, a.retired_at "
                    "FROM actor_subject_bindings b "
                    "JOIN actors a ON a.id=b.actor_id "
                    "JOIN bootstrap_records br ON br.first_actor_id=a.id "
                    "AND br.deployment_id=b.deployment_id "
                    "WHERE b.deployment_id=:deployment AND b.subject_kind='OS_UID' "
                    "AND b.subject_value=:subject AND b.subject_credential_id=:credential "
                    "AND b.status='ACTIVE' AND a.actor_type='HUMAN' "
                    "AND a.external_key=:external_key"
                ),
                {
                    "deployment": subject.deployment_id,
                    "subject": subject.subject_value,
                    "credential": subject.credential_id,
                    "external_key": f"local-os:{subject.deployment_id}:{subject.subject_value}",
                },
            )
            .mappings()
            .all()
        )
        return dict(rows[0]) if len(rows) == 1 else None

    def transaction_isolation(self) -> str:
        return str(self._session.execute(text("SHOW transaction_isolation")).scalar_one())

    def lock_deployment(self, deployment_id: str) -> None:
        self._session.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtextextended('researchbase-deployment:' || :deployment_id, 0))"
            ),
            {"deployment_id": deployment_id},
        )

    def lock_actor_projects(self, actor_id: UUID) -> None:
        project_ids = (
            self._session.execute(
                text(
                    "SELECT DISTINCT project_id FROM project_memberships "
                    "WHERE actor_id = :actor_id ORDER BY project_id"
                ),
                {"actor_id": actor_id},
            )
            .scalars()
            .all()
        )
        for project_id in project_ids:
            self._session.execute(
                text("SELECT rb_phase2_lock_project(:project_id)"),
                {"project_id": project_id},
            )

    def owner_project_ids(
        self, actor_id: UUID, deployment_id: str, subject_kind: str, subject_value: str
    ) -> list[UUID]:
        return list(
            self._session.execute(
                text(
                    "SELECT DISTINCT m.project_id FROM project_memberships m "
                    "JOIN project_role_assignments r ON r.membership_id = m.id "
                    "JOIN actor_subject_bindings b ON b.actor_id = m.actor_id "
                    "WHERE m.actor_id = :actor_id AND m.status = 'ACTIVE' "
                    "AND r.project_id = m.project_id AND r.actor_id = m.actor_id "
                    "AND r.role = 'OWNER' AND b.deployment_id = :deployment_id "
                    "AND b.subject_kind = :subject_kind AND b.subject_value = :subject_value "
                    "AND b.status = 'ACTIVE' ORDER BY m.project_id"
                ),
                {
                    "actor_id": actor_id,
                    "deployment_id": deployment_id,
                    "subject_kind": subject_kind,
                    "subject_value": subject_value,
                },
            )
            .scalars()
            .all()
        )

    def subject_binding_actor_id(self, binding_id: UUID) -> UUID | None:
        return self._session.execute(
            text("SELECT actor_id FROM actor_subject_bindings WHERE id = :id"),
            {"id": binding_id},
        ).scalar_one_or_none()

    def subject_binding_for_update(self, binding_id: UUID) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text("SELECT * FROM actor_subject_bindings WHERE id = :id FOR UPDATE"),
                {"id": binding_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def revoke_subject_binding(self, binding_id: UUID, revoked_at: datetime) -> bool:
        result = self._session.execute(
            text(
                "UPDATE actor_subject_bindings SET status = 'REVOKED', revoked_at = :revoked_at, "
                "row_version = row_version + 1 WHERE id = :id AND status = 'ACTIVE'"
            ),
            {"id": binding_id, "revoked_at": revoked_at},
        )
        return cast(CursorResult[Any], result).rowcount == 1

    def database_time(self) -> datetime:
        value = self._session.execute(text("SELECT clock_timestamp()")).scalar_one()
        if not isinstance(value, datetime):
            raise TypeError("PostgreSQL clock_timestamp() did not return a datetime")
        return value

    def actor_for_update(self, actor_id: UUID) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT id, actor_type, external_key, retired_at "
                    "FROM actors WHERE id = :actor_id FOR UPDATE"
                ),
                {"actor_id": actor_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def has_active_subject_binding(self, actor_id: UUID) -> bool:
        return bool(
            self._session.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM actor_subject_bindings "
                    "WHERE actor_id = :actor_id AND status = 'ACTIVE')"
                ),
                {"actor_id": actor_id},
            ).scalar_one()
        )

    def has_subject_binding(
        self, deployment_id: str, subject_kind: str, subject_value: str
    ) -> bool:
        return bool(
            self._session.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM actor_subject_bindings "
                    "WHERE deployment_id = :deployment_id AND subject_kind = :subject_kind "
                    "AND subject_value = :subject_value AND status = 'ACTIVE')"
                ),
                {
                    "deployment_id": deployment_id,
                    "subject_kind": subject_kind,
                    "subject_value": subject_value,
                },
            ).scalar_one()
        )

    def create_enrollment_challenge(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO actor_enrollment_challenges ("
                "id, deployment_id, actor_id, subject_kind, subject_value, "
                "subject_credential_id, operator_credential_id, nonce_digest, proof_method, "
                "issued_at, expires_at, status, request_id, row_version"
                ") VALUES ("
                ":id, :deployment_id, :actor_id, :subject_kind, :subject_value, "
                ":subject_credential_id, :operator_credential_id, :nonce_digest, :proof_method, "
                ":issued_at, :expires_at, 'ISSUED', :request_id, 1)"
            ),
            values,
        )

    def enrollment_challenge_for_update(self, challenge_id: UUID) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text("SELECT * FROM actor_enrollment_challenges WHERE id = :id FOR UPDATE"),
                {"id": challenge_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def consume_enrollment_challenge(
        self, challenge_id: UUID, binding_id: UUID, consumed_at: datetime
    ) -> bool:
        result = self._session.execute(
            text(
                "UPDATE actor_enrollment_challenges SET status = 'CONSUMED', "
                "consumed_at = :consumed_at, result_binding_id = :binding_id, "
                "row_version = row_version + 1 WHERE id = :id AND status = 'ISSUED'"
            ),
            {"id": challenge_id, "binding_id": binding_id, "consumed_at": consumed_at},
        )
        return cast(CursorResult[Any], result).rowcount == 1

    def create_subject_binding(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO actor_subject_bindings ("
                "id, actor_id, deployment_id, subject_kind, subject_value, status, bound_at, "
                "operator_credential_id, subject_credential_id, proof_sha256, proof_record_ref, "
                "proof_kind, enrollment_challenge_id, created_at, row_version"
                ") VALUES ("
                ":id, :actor_id, :deployment_id, :subject_kind, :subject_value, 'ACTIVE', "
                ":bound_at, :operator_credential_id, :subject_credential_id, :proof_sha256, "
                ":proof_record_ref, :proof_kind, :enrollment_challenge_id, :created_at, 1)"
            ),
            values,
        )

    def create_subject_binding_event(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO actor_subject_binding_events ("
                "id, binding_id, actor_id, event_kind, operator_credential_id, "
                "subject_credential_id, proof_sha256, proof_record_ref, proof_kind, "
                "request_id, reason, occurred_at"
                ") VALUES ("
                ":id, :binding_id, :actor_id, :event_kind, :operator_credential_id, "
                ":subject_credential_id, :proof_sha256, :proof_record_ref, :proof_kind, "
                ":request_id, :reason, :occurred_at)"
            ),
            values,
        )

    def lock_project(self, project_id: UUID) -> None:
        self._session.execute(
            text("SELECT rb_phase2_lock_project(:project_id)"),
            {"project_id": project_id},
        )

    def owner_authorization_facts(
        self,
        actor_id: UUID,
        project_id: UUID,
        deployment_id: str,
        subject_kind: str,
        subject_value: str,
    ) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT a.retired_at, m.status AS membership_status, m.started_at, "
                    "r.effective_from, r.effective_until, b.status AS binding_status, "
                    "b.bound_at, b.revoked_at "
                    "FROM actors a "
                    "JOIN project_memberships m ON m.actor_id = a.id "
                    "JOIN project_role_assignments r ON r.membership_id = m.id "
                    " AND r.project_id = m.project_id AND r.actor_id = m.actor_id "
                    "JOIN actor_subject_bindings b ON b.actor_id = a.id "
                    "WHERE a.id = :actor_id AND m.project_id = :project_id "
                    "AND r.role = 'OWNER' AND b.deployment_id = :deployment_id "
                    "AND b.subject_kind = :subject_kind AND b.subject_value = :subject_value "
                    "AND b.status IN ('ACTIVE', 'REVOKED') "
                    "ORDER BY b.bound_at DESC LIMIT 1 FOR UPDATE OF a, m, r, b"
                ),
                {
                    "actor_id": actor_id,
                    "project_id": project_id,
                    "deployment_id": deployment_id,
                    "subject_kind": subject_kind,
                    "subject_value": subject_value,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def active_membership_for_update(
        self, actor_id: UUID, project_id: UUID
    ) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT m.id AS membership_id, m.status, a.retired_at "
                    "FROM project_memberships m JOIN actors a ON a.id = m.actor_id "
                    "WHERE m.actor_id = :actor_id AND m.project_id = :project_id "
                    "AND m.status = 'ACTIVE' FOR UPDATE OF m, a"
                ),
                {"actor_id": actor_id, "project_id": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def role_assignment_for_update(self, role_assignment_id: UUID) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text("SELECT * FROM project_role_assignments WHERE id = :id FOR UPDATE"),
                {"id": role_assignment_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def close_role_assignment(self, role_assignment_id: UUID, effective_until: datetime) -> bool:
        result = self._session.execute(
            text(
                "UPDATE project_role_assignments SET effective_until = :effective_until, "
                "row_version = row_version + 1 WHERE id = :id AND effective_until IS NULL"
            ),
            {"id": role_assignment_id, "effective_until": effective_until},
        )
        return cast(CursorResult[Any], result).rowcount == 1

    def membership_for_update(self, membership_id: UUID) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text("SELECT * FROM project_memberships WHERE id = :id FOR UPDATE"),
                {"id": membership_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def open_roles_for_membership(self, membership_id: UUID) -> list[dict[str, object]]:
        rows = self._session.execute(
            text(
                "SELECT * FROM project_role_assignments "
                "WHERE membership_id = :id AND effective_until IS NULL ORDER BY id FOR UPDATE"
            ),
            {"id": membership_id},
        ).mappings()
        return [dict(row) for row in rows]

    def close_membership(self, membership_id: UUID, status: str, ended_at: datetime | None) -> bool:
        result = self._session.execute(
            text(
                "UPDATE project_memberships SET status = :status, ended_at = :ended_at, "
                "row_version = row_version + 1 WHERE id = :id AND status = 'ACTIVE'"
            ),
            {"id": membership_id, "status": status, "ended_at": ended_at},
        )
        return cast(CursorResult[Any], result).rowcount == 1

    def latest_membership_for_actor_project(
        self, actor_id: UUID, project_id: UUID
    ) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM project_memberships WHERE actor_id = :actor_id "
                    "AND project_id = :project_id ORDER BY started_at DESC LIMIT 1 FOR UPDATE"
                ),
                {"actor_id": actor_id, "project_id": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def active_binding_for_actor_for_update(self, actor_id: UUID) -> dict[str, object] | None:
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM actor_subject_bindings "
                    "WHERE actor_id = :actor_id AND status = 'ACTIVE' "
                    "ORDER BY bound_at DESC LIMIT 1 FOR UPDATE"
                ),
                {"actor_id": actor_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

    def closed_roles_for_membership(self, membership_id: UUID) -> list[str]:
        return list(
            self._session.execute(
                text(
                    "SELECT r.role FROM project_role_assignments r "
                    "JOIN project_membership_events e ON e.membership_id = r.membership_id "
                    "AND e.occurred_at = r.effective_until "
                    "WHERE r.membership_id = :membership_id AND r.effective_until IS NOT NULL "
                    "AND e.event_kind IN ('SUSPENDED', 'ENDED') ORDER BY r.role"
                ),
                {"membership_id": membership_id},
            )
            .scalars()
            .all()
        )

    def legacy_project_creator_for_update(self, project_id: UUID) -> UUID | None:
        return self._session.execute(
            text("SELECT created_by FROM projects WHERE id = :id FOR UPDATE"),
            {"id": project_id},
        ).scalar_one_or_none()

    def project_has_membership(self, project_id: UUID) -> bool:
        return bool(
            self._session.execute(
                text("SELECT EXISTS (SELECT 1 FROM project_memberships WHERE project_id = :id)"),
                {"id": project_id},
            ).scalar_one()
        )

    def create_role_assignment(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO project_role_assignments ("
                "id, membership_id, project_id, actor_id, role, effective_from, "
                "assigned_by, created_at, row_version"
                ") VALUES ("
                ":id, :membership_id, :project_id, :actor_id, :role, :effective_from, "
                ":assigned_by, :created_at, 1)"
            ),
            values,
        )

    def create_role_event(self, values: dict[str, object]) -> None:
        stored = {**values, "event_kind": values.get("event_kind", "ASSIGNED")}
        self._session.execute(
            text(
                "INSERT INTO project_role_events ("
                "id, role_assignment_id, actor_id, event_kind, occurred_at, reason, request_id"
                ") VALUES ("
                ":id, :role_assignment_id, :actor_id, :event_kind, :occurred_at, "
                ":reason, :request_id)"
            ),
            stored,
        )

    def actors_and_projects_empty(self) -> bool:
        return bool(
            self._session.execute(
                text(
                    "SELECT NOT EXISTS (SELECT 1 FROM actors) "
                    "AND NOT EXISTS (SELECT 1 FROM projects)"
                )
            ).scalar_one()
        )

    def legacy_state_violations(self) -> tuple[str, ...]:
        checks = (
            (
                "PROJECT_CREATOR_ORPHAN",
                "SELECT EXISTS (SELECT 1 FROM projects p LEFT JOIN actors a "
                "ON a.id = p.created_by WHERE a.id IS NULL)",
            ),
            (
                "DUPLICATE_ACTOR_EXTERNAL_KEY",
                "SELECT EXISTS (SELECT 1 FROM actors WHERE external_key IS NOT NULL "
                "GROUP BY external_key HAVING count(*) > 1)",
            ),
            (
                "INVALID_ACTOR_TYPE",
                "SELECT EXISTS (SELECT 1 FROM actors "
                "WHERE actor_type IS NULL "
                "OR actor_type NOT IN ('HUMAN', 'AGENT', 'SERVICE'))",
            ),
            (
                "INVALID_PROJECT_LIFECYCLE",
                "SELECT EXISTS (SELECT 1 FROM projects "
                "WHERE lifecycle_status IS NULL "
                "OR lifecycle_status NOT IN ('ACTIVE', 'ARCHIVED', 'RETIRED'))",
            ),
        )
        return tuple(
            sorted(
                code for code, query in checks if self._session.execute(text(query)).scalar_one()
            )
        )

    def legacy_project_state_violations(self, project_id: UUID) -> tuple[str, ...]:
        project = (
            self._session.execute(
                text(
                    "SELECT created_by, lifecycle_status FROM projects "
                    "WHERE id = :project_id FOR UPDATE"
                ),
                {"project_id": project_id},
            )
            .mappings()
            .first()
        )
        if project is None:
            return ()
        creator_id = project["created_by"]
        violations: list[str] = []
        if project["lifecycle_status"] not in {"ACTIVE", "ARCHIVED", "RETIRED"}:
            violations.append("INVALID_PROJECT_LIFECYCLE")
        if creator_id is None:
            violations.append("PROJECT_CREATOR_ORPHAN")
            return tuple(violations)
        creator = (
            self._session.execute(
                text("SELECT actor_type, external_key FROM actors WHERE id = :actor_id FOR UPDATE"),
                {"actor_id": creator_id},
            )
            .mappings()
            .first()
        )
        if creator is None:
            violations.append("PROJECT_CREATOR_ORPHAN")
            return tuple(violations)
        if creator["actor_type"] not in {"HUMAN", "AGENT", "SERVICE"}:
            violations.append("INVALID_ACTOR_TYPE")
        if (
            creator["external_key"] is not None
            and self._session.execute(
                text("SELECT count(*) > 1 FROM actors WHERE external_key = :external_key"),
                {"external_key": creator["external_key"]},
            ).scalar_one()
        ):
            violations.append("DUPLICATE_ACTOR_EXTERNAL_KEY")
        return tuple(sorted(violations))

    def lock_bootstrap_tables(self) -> None:
        self._session.execute(text("LOCK TABLE actors, projects IN SHARE ROW EXCLUSIVE MODE"))

    def create_actor(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, external_key, "
                "created_at, row_version) "
                "VALUES (:id, 'HUMAN', :display_name, :external_key, :created_at, 1)"
            ),
            values,
        )

    def create_project(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO projects (id, name, description, created_by, created_at, row_version) "
                "VALUES (:id, :name, NULL, :created_by, :created_at, 1)"
            ),
            values,
        )

    def create_membership(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO project_memberships ("
                "id, project_id, actor_id, status, started_at, created_by, created_at, "
                "row_version"
                ") VALUES (:id, :project_id, :actor_id, 'ACTIVE', :started_at, "
                ":created_by, :created_at, 1)"
            ),
            values,
        )

    def create_membership_event(self, values: dict[str, object]) -> None:
        stored = {
            **values,
            "prior_status": values.get("prior_status"),
            "new_status": values.get("new_status", "ACTIVE"),
        }
        self._session.execute(
            text(
                "INSERT INTO project_membership_events ("
                "id, membership_id, event_kind, prior_status, new_status, actor_id, "
                "occurred_at, reason, request_id"
                ") VALUES ("
                ":id, :membership_id, :event_kind, :prior_status, :new_status, :actor_id, "
                ":occurred_at, :reason, :request_id)"
            ),
            stored,
        )

    def create_bootstrap_record(self, values: dict[str, object]) -> None:
        self._session.execute(
            text(
                "INSERT INTO bootstrap_records ("
                "id, deployment_id, request_id, request_fingerprint, operator_credential_id, "
                "secret_digest_id, first_actor_id, first_binding_id, first_project_id, "
                "first_membership_id, first_role_assignment_id, completed_at, "
                "content_hash, hash_scheme"
                ") VALUES ("
                ":id, :deployment_id, :request_id, :request_fingerprint, :operator_credential_id, "
                ":secret_digest_id, :first_actor_id, :first_binding_id, :first_project_id, "
                ":first_membership_id, :first_role_assignment_id, :completed_at, :content_hash, "
                "'sha256-cjson-v1')"
            ),
            values,
        )
