"""Concrete approval relations; same target/snapshot order as RevisionAction."""

from datetime import datetime

from sqlalchemy import text

from researchbase.foundation.time import to_utc
from researchbase.persistence.decision_repository import (
    _SNAPSHOT_TABLES,
    SqlAlchemyDecisionRepository,
)
from researchbase.persistence.revision_action_repository import SqlAlchemyRevisionActionRepository


class SqlAlchemyApprovalRepository(SqlAlchemyRevisionActionRepository):
    def _one(self, sql, params):
        row = super()._one(sql, params)
        if row is not None:
            return {
                key: to_utc(value) if isinstance(value, datetime) else value
                for key, value in row.items()
            }
        return None

    def lock_request(self, identity):
        self._session.execute(text("SET LOCAL lock_timeout = '10s'"))
        self._session.execute(text("SET LOCAL statement_timeout = '30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr216:uuid:{identity}"},
        )

    def lock_snapshot(self):
        # Include insertable input relations so the complete closure has no phantoms.
        tables = sorted(
            (set(_SNAPSHOT_TABLES) - {"claim_versions"})
            | {"run_artifact_inputs", "run_dataset_inputs", "statistical_result_inputs"}
        )
        self._session.execute(text("LOCK TABLE " + ",".join(tables) + " IN SHARE MODE"))

    def lock_scope(self, project):
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr216:scope:{project}:INTERNAL_SCIENTIFIC_RELEASE"},
        )

    def target(self, identity, project):
        return SqlAlchemyDecisionRepository(self._session).target(identity, project)

    def request(self, identity, project):
        return self._one(
            "SELECT * FROM approval_requests WHERE id=:id AND project_id=:project",
            {"id": identity, "project": project},
        )

    def decision(self, identity, project):
        return self._one(
            """SELECT d.* FROM approval_decisions d JOIN approval_requests r
            ON r.id=d.approval_request_id WHERE d.id=:id AND r.project_id=:project""",
            {"id": identity, "project": project},
        )

    def grant(self, identity, project):
        return self._one(
            "SELECT * FROM approval_grants WHERE id=:id AND project_id=:project",
            {"id": identity, "project": project},
        )

    def exists(self, table, identity):
        assert table in {"approval_requests", "approval_decisions", "approval_grants"}
        return self._one(f"SELECT id FROM {table} WHERE id=:id", {"id": identity}) is not None

    def reviews(self, identity):
        return [
            dict(row)
            for row in self._session.execute(
                text("""SELECT v.*
            FROM approval_request_reviews b JOIN internal_review_records v
            ON v.id=b.internal_review_record_id WHERE b.request_id=:id ORDER BY v.id"""),
                {"id": identity},
            ).mappings()
        ]

    def events(self, kind, identity):
        assert kind in {"request", "grant"}
        return tuple(
            self._session.execute(
                text(
                    f"SELECT id FROM approval_{kind}_events WHERE {kind}_id=:id "
                    "ORDER BY occurred_at,id"
                ),
                {"id": identity},
            ).scalars()
        )

    def rejected(self, project):
        return (
            self._one(
                """SELECT d.id FROM approval_decisions d JOIN approval_requests r
            ON r.id=d.approval_request_id WHERE r.project_id=:project AND d.decision='REJECT'
            LIMIT 1""",
                {"project": project},
            )
            is not None
        )

    def newer_target_selected(self, request):
        return (
            self._one(
                """SELECT id FROM approval_requests WHERE project_id=:project
            AND approval_purpose=:purpose AND scientific_conclusion_version_id<>:target
            AND requested_at>:at LIMIT 1""",
                {
                    "project": request["project_id"],
                    "purpose": request["approval_purpose"],
                    "target": request["scientific_conclusion_version_id"],
                    "at": request["requested_at"],
                },
            )
            is not None
        )

    def pending(self, project, target):
        return (
            self._one(
                """SELECT id FROM approval_requests WHERE project_id=:project
            AND scientific_conclusion_version_id=:target AND status='PENDING'""",
                {"project": project, "target": target},
            )
            is not None
        )

    def decision_for_request(self, identity):
        return self._one(
            "SELECT * FROM approval_decisions WHERE approval_request_id=:id", {"id": identity}
        )

    def grant_for_decision(self, identity):
        return self._one(
            "SELECT * FROM approval_grants WHERE approval_decision_id=:id", {"id": identity}
        )

    def decision_creation_authorized(self, identity):
        return self._session.execute(
            text(
                "SELECT public.pr216_decision_authorized(d) FROM decision_records d WHERE d.id=:id"
            ),
            {"id": identity},
        ).scalar_one()

    def human(self, actor):
        return (
            self._one("SELECT id FROM actors WHERE id=:id AND actor_type='HUMAN'", {"id": actor})
            is not None
        )

    def approver_active(self, actor, project):
        return self._session.execute(
            text("SELECT pr216_approver_active(:actor,:project)"),
            {"actor": actor, "project": project},
        ).scalar_one()

    def committed(self, table, identity):
        assert table in {"decision_records", "internal_review_records"}
        return self._session.execute(
            text(
                f"SELECT xmin::text::bigint <> "
                f"pg_current_xact_id()::text::bigint FROM {table} WHERE id=:id"
            ),
            {"id": identity},
        ).scalar_one()

    def insert(self, table, row):
        assert table in {
            "approval_requests",
            "approval_request_reviews",
            "approval_decisions",
            "approval_grants",
        }
        SqlAlchemyDecisionRepository(self._session)._insert(table, row)
