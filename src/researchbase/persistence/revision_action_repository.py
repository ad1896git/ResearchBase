"""Concrete immutable revision persistence; Decision-compatible lock ordering."""

from sqlalchemy import text

from researchbase.persistence.decision_repository import _SNAPSHOT_TABLES


class SqlAlchemyRevisionActionRepository:
    def __init__(self, session):
        self._session = session

    def _one(self, sql, params):
        row = self._session.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    def lock_request(self, identity):
        self._session.execute(text("SET LOCAL lock_timeout = '10s'"))
        self._session.execute(text("SET LOCAL statement_timeout = '30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr215:revision:{identity}"},
        )

    def lock_snapshot(self):
        # Frozen version/input material already has immutable SQL guards. Do not
        # table-lock those rows: an INSERT/UPDATE takes ROW EXCLUSIVE before its
        # trigger waits for the old target, which would invert this protocol.
        self._session.execute(
            text(
                "LOCK TABLE "
                + ",".join(table for table in _SNAPSHOT_TABLES if table != "claim_versions")
                + " IN SHARE MODE"
            )
        )

    def authorize(self, principal, project):
        return [
            dict(row)
            for row in self._session.execute(
                text("""
            SELECT a.retired_at,m.status AS membership_status,r.role,r.effective_from,
              r.effective_until,b.status AS binding_status,b.bound_at,b.revoked_at
            FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments r ON r.membership_id=m.id
              AND r.project_id=m.project_id AND r.actor_id=m.actor_id
            JOIN actor_subject_bindings b ON b.actor_id=a.id
            WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
              AND b.subject_kind=:kind AND b.subject_value=:value
              AND b.subject_credential_id=:credential"""),
                {
                    "actor": principal.actor_id,
                    "project": project,
                    "deployment": principal.deployment_id,
                    "kind": principal.subject_kind,
                    "value": principal.subject_value,
                    "credential": principal.credential_id,
                },
            ).mappings()
        ]

    def action(self, identity, project):
        return self._one(
            """SELECT a.* FROM revision_actions a
            JOIN review_issues i ON i.id=a.review_issue_id
            JOIN internal_review_records r ON r.id=i.review_record_id
            WHERE a.id=:id AND r.project_id=:project""",
            {"id": identity, "project": project},
        )

    def exists(self, identity):
        return (
            self._one("SELECT id FROM revision_actions WHERE id=:id", {"id": identity}) is not None
        )

    def issue(self, identity, project):
        return self._one(
            """SELECT i.*,r.claim_version_id,r.scientific_conclusion_version_id
            FROM review_issues i JOIN internal_review_records r ON r.id=i.review_record_id
            WHERE i.id=:id AND r.project_id=:project""",
            {"id": identity, "project": project},
        )

    def target(self, issue, project, *, lock=False):
        if issue["claim_version_id"] is not None:
            table, parent, fk, identity = (
                "claim_versions",
                "claims",
                "claim_id",
                issue["claim_version_id"],
            )
        else:
            table, parent, fk, identity = (
                "scientific_conclusion_versions",
                "scientific_conclusions",
                "scientific_conclusion_id",
                issue["scientific_conclusion_version_id"],
            )
        if lock:
            self._session.execute(
                text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
            )
        return self._one(
            f"""SELECT v.* FROM {table} v JOIN {parent} p ON p.id=v.{fk}
            WHERE v.id=:id AND p.project_id=:project""",
            {"id": identity, "project": project},
        )

    def lock_basis(self, issue):
        self._session.execute(
            text("SELECT id FROM internal_review_records WHERE id=:id FOR SHARE"),
            {"id": issue["review_record_id"]},
        )
        self._session.execute(
            text("SELECT id FROM review_issues WHERE id=:id FOR SHARE"), {"id": issue["id"]}
        )

    def predecessor(self, identity, project):
        return self._one(
            """SELECT a.* FROM revision_actions a
            JOIN review_issues i ON i.id=a.review_issue_id
            JOIN internal_review_records r ON r.id=i.review_record_id
            WHERE a.id=:id AND r.project_id=:project FOR UPDATE OF a""",
            {"id": identity, "project": project},
        )

    def has_successor(self, identity):
        return (
            self._one(
                "SELECT id FROM revision_actions WHERE supersedes_revision_action_id=:id",
                {"id": identity},
            )
            is not None
        )

    def insert(self, row):
        keys = tuple(row)
        self._session.execute(
            text(
                "INSERT INTO revision_actions ("
                + ",".join(keys)
                + ") VALUES ("
                + ",".join(":" + key for key in keys)
                + ")"
            ),
            row,
        )
