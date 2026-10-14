"""S1 request/Publication/authority snapshot locks and typed relation storage."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.persistence.phase2_identity_repository import SqlAlchemyPhase2IdentityRepository

_SNAPSHOT_TABLES = (
    "actor_subject_bindings",
    "actors",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
)
_RELATIONS = ("authors", "corresponding_authors", "equal_groups", "contributions")


class SqlAlchemyAuthorshipRepository:
    def __init__(self, session: Session):
        self._session = session

    def _one(self, sql, params):
        row = self._session.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    def _many(self, sql, params):
        return [dict(row) for row in self._session.execute(text(sql), params).mappings()]

    def _timeouts(self):
        self._session.execute(text("SET LOCAL lock_timeout = '10s'"))
        self._session.execute(text("SET LOCAL statement_timeout = '30s'"))

    def lock_request(self, identity: UUID) -> None:
        self._timeouts()
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr217:authorship:{identity}"},
        )

    def lock_publication(self, publication_id: UUID, project_id: UUID, *, read=False):
        self._timeouts()
        return self._one(
            "SELECT * FROM publications WHERE id=:id AND project_id=:project FOR "
            + ("SHARE" if read else "UPDATE"),
            {"id": publication_id, "project": project_id},
        )

    def lock_record_publication(self, identity: UUID, project_id: UUID, *, snapshot=False):
        self._timeouts()
        table = "authorship_snapshots" if snapshot else "contribution_records"
        return self._one(
            f"SELECT p.* FROM publications p JOIN {table} r ON r.publication_id=p.id "
            "WHERE r.id=:id AND p.project_id=:project FOR SHARE OF p",
            {"id": identity, "project": project_id},
        )

    def lock_snapshot(self) -> None:
        self._session.execute(text("LOCK TABLE " + ",".join(_SNAPSHOT_TABLES) + " IN SHARE MODE"))

    def lock_project(self, project_id: UUID) -> None:
        SqlAlchemyPhase2IdentityRepository(self._session).lock_project(project_id)

    def lock_actors(self, ids):
        for identity in sorted(set(ids), key=str):
            self._session.execute(
                text("SELECT id FROM actors WHERE id=:id FOR SHARE"), {"id": identity}
            )

    def lock_contributions(self, ids):
        for identity in sorted(ids, key=str):
            self._session.execute(
                text("SELECT id FROM contribution_records WHERE id=:id FOR SHARE"), {"id": identity}
            )

    def at(self):
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one()

    def actor(self, identity):
        return self._one("SELECT * FROM actors WHERE id=:id", {"id": identity})

    def authority(self, principal, project):
        # SHARE table locks already exclude INSERT/UPDATE/DELETE phantoms. No late actor lock.
        return self._many(
            """SELECT a.retired_at,m.status AS membership_status,m.started_at,
          r.role,r.effective_from,r.effective_until,b.status AS binding_status,
          b.bound_at,b.revoked_at,
          p.lifecycle_status FROM actors a JOIN project_memberships m ON m.actor_id=a.id
          JOIN projects p ON p.id=m.project_id
          JOIN project_role_assignments r ON r.membership_id=m.id
            AND r.project_id=m.project_id AND r.actor_id=m.actor_id
          JOIN actor_subject_bindings b ON b.actor_id=a.id
          WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
            AND b.subject_kind=:kind AND b.subject_value=:value
            AND b.subject_credential_id=:credential""",
            {
                "actor": principal.actor_id,
                "project": project,
                "deployment": principal.deployment_id,
                "kind": principal.subject_kind,
                "value": principal.subject_value,
                "credential": principal.credential_id,
            },
        )

    def contribution(self, identity):
        return self._one("SELECT * FROM contribution_records WHERE id=:id", {"id": identity})

    def snapshot(self, identity):
        return self._one("SELECT * FROM authorship_snapshots WHERE id=:id", {"id": identity})

    def publication(self, identity):
        return self._one("SELECT * FROM publications WHERE id=:id", {"id": identity})

    def snapshot_relations(self, identity):
        return {
            kind: self._many(
                f"SELECT * FROM authorship_snapshot_{kind} "
                "WHERE authorship_snapshot_id=:id ORDER BY "
                + ("group_ordinal,ordinal" if kind == "equal_groups" else "ordinal"),
                {"id": identity},
            )
            for kind in _RELATIONS
        }

    def _insert(self, table, row):
        keys = tuple(row)
        self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(keys)}) VALUES ("
                + ",".join(f":{key}" for key in keys)
                + ")"
            ),
            row,
        )

    def insert_contribution(self, row) -> None:
        self._insert("contribution_records", row)

    def insert_snapshot(self, row) -> None:
        self._insert("authorship_snapshots", row)

    def insert_snapshot_relations(self, rows) -> None:
        for kind in _RELATIONS:
            for row in rows[kind]:
                self._insert(f"authorship_snapshot_{kind}", row)
