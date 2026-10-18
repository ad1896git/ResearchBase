"""Concrete approval relations; same target/snapshot order as RevisionAction."""

from datetime import datetime

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from researchbase.foundation.time import to_utc
from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
from researchbase.persistence.revision_action_repository import SqlAlchemyRevisionActionRepository

B09_SNAPSHOT_TABLES = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "audit_findings",
    "claim_versions",
    "claims",
    "correction_records",
    "dataset_snapshots",
    "datasets",
    "evidence_relations",
    "experiment_spec_versions",
    "experiment_specs",
    "impact_assessments",
    "impact_targets",
    "internal_review_records",
    "literature_evidence",
    "literature_evidence_relations",
    "literature_evidence_review_events",
    "literature_source_project_links",
    "literature_sources",
    "literature_support_snapshots",
    "manuscript_artifact_placements",
    "manuscript_citation_placements",
    "manuscript_claim_placements",
    "manuscript_versions",
    "measurements",
    "metric_definition_versions",
    "metric_definitions",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "publications",
    "review_issue_events",
    "review_issues",
    "run_artifact_inputs",
    "run_dataset_inputs",
    "runs",
    "scientific_conclusion_claim_inputs",
    "scientific_conclusion_literature_inputs",
    "scientific_conclusion_versions",
    "scientific_conclusions",
    "source_versions",
    "statistical_result_inputs",
    "statistical_results",
)
B09_SHARE_SQL = "LOCK TABLE " + ",".join(B09_SNAPSHOT_TABLES) + " IN SHARE MODE"
B09_DECIDE_SHARE_SQL = (
    "LOCK TABLE "
    + ",".join(t for t in B09_SNAPSHOT_TABLES if t != "publications")
    + " IN SHARE MODE"
)


B13_SNAPSHOT_TABLES = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "audit_findings",
    "claim_versions",
    "claims",
    "correction_records",
    "dataset_snapshots",
    "datasets",
    "evidence_relations",
    "experiment_spec_versions",
    "experiment_specs",
    "impact_assessments",
    "impact_targets",
    "internal_review_records",
    "literature_evidence",
    "literature_evidence_relations",
    "literature_evidence_review_events",
    "literature_source_project_links",
    "literature_sources",
    "literature_support_snapshots",
    "manuscript_artifact_placements",
    "manuscript_citation_placements",
    "manuscript_claim_placements",
    "manuscript_versions",
    "measurements",
    "metric_definition_versions",
    "metric_definitions",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "review_issue_events",
    "review_issues",
    "run_artifact_inputs",
    "run_dataset_inputs",
    "runs",
    "scientific_conclusion_claim_inputs",
    "scientific_conclusion_literature_inputs",
    "scientific_conclusion_versions",
    "scientific_conclusions",
    "source_versions",
    "statistical_result_inputs",
    "statistical_results",
)
B13_APPROVAL_TABLES = ("approval_decisions", "approval_request_reviews", "approval_requests")
B13_SHARE_SQL = "LOCK TABLE " + ",".join(B13_SNAPSHOT_TABLES) + " IN SHARE MODE"
B13_APPROVAL_SQL = "LOCK TABLE " + ",".join(B13_APPROVAL_TABLES) + " IN SHARE MODE"


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
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr216:uuid:{identity}"},
        )

    def lock_snapshot(self, *, deciding=False):
        if deciding:
            self._session.execute(text(B09_DECIDE_SHARE_SQL))
            self._session.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        else:
            self._session.execute(text(B09_SHARE_SQL))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def lock_scope(self, project, purpose):
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr216:scope:{project}:{purpose}"},
        )

    def target(self, identity, project):
        return self._one(
            """SELECT v.* FROM scientific_conclusion_versions v
            JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
            WHERE v.id=:id AND c.project_id=:project""",
            {"id": identity, "project": project},
        )

    def target_reviews(self, identity, project):
        return [
            dict(r)
            for r in self._session.execute(
                text(
                    """SELECT * FROM internal_review_records
                       WHERE scientific_conclusion_version_id=:id AND project_id=:project
                       ORDER BY id"""
                ),
                {"id": identity, "project": project},
            ).mappings()
        ]

    def manuscript_reviews(self, identity, project):
        return [
            dict(r)
            for r in self._session.execute(
                text(
                    """SELECT * FROM internal_review_records
               WHERE manuscript_version_id=:id AND project_id=:project ORDER BY id"""
                ),
                {"id": identity, "project": project},
            ).mappings()
        ]

    def lock_target(self, conclusion, manuscript, project):
        table = (
            "scientific_conclusion_versions" if conclusion is not None else "manuscript_versions"
        )
        identity = conclusion or manuscript
        if identity is None:
            return
        self._session.execute(
            text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
        )
        if manuscript is not None:
            self._session.execute(
                text("""SELECT p.id FROM publications p
                JOIN manuscript_versions v ON v.publication_id=p.id
                WHERE v.id=:id AND p.project_id=:project FOR SHARE OF p"""),
                {"id": manuscript, "project": project},
            )

    def lock_saved_request(self, identity, project):
        return self._one(
            "SELECT * FROM approval_requests WHERE id=:id AND project_id=:project FOR UPDATE",
            {"id": identity, "project": project},
        )

    def lock_affected_grants(self, request, *, reject):
        self._session.execute(
            text("""SELECT g.id FROM approval_grants g
            JOIN approval_decisions d ON d.id=g.approval_decision_id
            JOIN approval_requests r ON r.id=d.approval_request_id
            WHERE r.project_id=:project AND r.approval_purpose=:purpose AND g.status='ACTIVE'
            AND (:reject OR
              coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)<>:target)
            ORDER BY g.id FOR UPDATE OF g"""),
            {
                "project": request["project_id"],
                "purpose": request["approval_purpose"],
                "reject": reject,
                "target": request["scientific_conclusion_version_id"]
                or request.get("manuscript_version_id"),
            },
        )

    def force_constraints(self):
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

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

    def rejected(self, project, purpose, *, exclude_decision=None):
        return (
            self._one(
                """SELECT d.id FROM approval_decisions d JOIN approval_requests r
            ON r.id=d.approval_request_id WHERE r.project_id=:project
            AND r.approval_purpose=:purpose AND d.decision='REJECT'
            AND NOT (d.id IS NOT DISTINCT FROM CAST(:exclude AS uuid)
              AND d.xmin=pg_current_xact_id()::xid)
            LIMIT 1""",
                {"project": project, "purpose": purpose, "exclude": exclude_decision},
            )
            is not None
        )

    def newer_target_selected(self, request):
        return (
            self._one(
                """SELECT id FROM approval_requests WHERE project_id=:project
            AND approval_purpose=:purpose
            AND coalesce(scientific_conclusion_version_id,manuscript_version_id)<>:target
            AND requested_at>:at LIMIT 1""",
                {
                    "project": request["project_id"],
                    "purpose": request["approval_purpose"],
                    "target": request["scientific_conclusion_version_id"]
                    or request.get("manuscript_version_id"),
                    "at": request["requested_at"],
                },
            )
            is not None
        )

    def pending(self, project, target, purpose):
        return (
            self._one(
                """SELECT id FROM approval_requests WHERE project_id=:project
            AND approval_purpose=:purpose
            AND coalesce(scientific_conclusion_version_id,manuscript_version_id)=:target
            AND status='PENDING'""",
                {"project": project, "target": target, "purpose": purpose},
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

    def approver_active(self, actor, project, *, at=None):
        if at is not None:
            return bool(
                self._session.execute(
                    text("""SELECT EXISTS(
                SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
                JOIN project_role_assignments r ON r.membership_id=m.id
                  AND r.project_id=m.project_id AND r.actor_id=m.actor_id
                WHERE a.id=:actor AND a.actor_type='HUMAN' AND a.retired_at IS NULL
                  AND m.project_id=:project AND m.status='ACTIVE' AND r.role='APPROVER'
                  AND r.effective_from<=:at AND (r.effective_until IS NULL OR :at<r.effective_until)
                  AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                    AND b.status='ACTIVE' AND b.bound_at<=:at
                    AND (b.revoked_at IS NULL OR :at<b.revoked_at)))"""),
                    {"actor": actor, "project": project, "at": at},
                ).scalar_one()
            )
        return self._session.execute(
            text("SELECT pr216_approver_active(:actor,:project)"),
            {"actor": actor, "project": project},
        ).scalar_one()

    def committed(self, table, identity):
        assert table in {
            "decision_records",
            "internal_review_records",
            "revision_actions",
            "approval_decisions",
        }
        return bool(
            self._session.execute(
                text(
                    f"SELECT xmin::text::bigint <> "
                    f"pg_current_xact_id()::text::bigint FROM {table} WHERE id=:id"
                ),
                {"id": identity},
            ).scalar_one_or_none()
        )

    def insert(self, table, row):
        assert table in {
            "approval_requests",
            "approval_request_reviews",
            "approval_decisions",
            "approval_grants",
        }
        SqlAlchemyDecisionRepository(self._session)._insert(table, row)

    def rejections(self, project, purpose):
        return [
            {
                key: to_utc(value) if isinstance(value, datetime) else value
                for key, value in row.items()
            }
            for row in self._session.execute(
                text("""
          SELECT d.*,r.id AS request_id,r.project_id,r.approval_purpose,
            r.scientific_conclusion_version_id,r.manuscript_version_id,
            r.target_content_hash,r.requested_by
          FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id
          WHERE r.project_id=:project AND r.approval_purpose=:purpose AND d.decision='REJECT'
          ORDER BY d.id"""),
                {"project": project, "purpose": purpose},
            ).mappings()
        ]

    def successor(self, decision):
        return self._one(
            "SELECT * FROM approval_requests WHERE reconsideration_decision_id=:id",
            {"id": decision},
        )

    def prepare_write(self):
        self._session.execute(text(B13_SHARE_SQL))
        self._session.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        self._session.execute(text(B13_APPROVAL_SQL))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def lock_lifecycle(self, identity, *, consuming=False):
        prefix = "consume" if consuming else "lifecycle"
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b13:{prefix}:{identity}"},
        )

    def lock_grant_chain(self, grant, request):
        self.lock_scope(grant["project_id"], grant["purpose"])
        table = (
            "scientific_conclusion_versions"
            if request["scientific_conclusion_version_id"]
            else "manuscript_versions"
        )
        self._session.execute(
            text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"),
            {
                "id": request["scientific_conclusion_version_id"]
                or request.get("manuscript_version_id")
            },
        )
        if request["scientific_conclusion_version_id"] is not None:
            self._session.execute(
                text(
                    "SELECT c.id FROM scientific_conclusions c "
                    "JOIN scientific_conclusion_versions v "
                    "ON v.scientific_conclusion_id=c.id WHERE v.id=:id FOR SHARE OF c"
                ),
                {"id": request["scientific_conclusion_version_id"]},
            )
        else:
            self._session.execute(
                text(
                    "SELECT p.id FROM publications p JOIN manuscript_versions v "
                    "ON v.publication_id=p.id "
                    "WHERE v.id=:id FOR UPDATE OF p"
                ),
                {"id": request["manuscript_version_id"]},
            )
        self._session.execute(
            text("SELECT id FROM approval_requests WHERE id=:id FOR SHARE"), {"id": request["id"]}
        )
        self._session.execute(
            text("SELECT id FROM approval_grants WHERE id=:id FOR UPDATE"), {"id": grant["id"]}
        )

    def issuer_bindings(self, actor, at):
        return [
            dict(r)
            for r in self._session.execute(
                text(
                    "SELECT * FROM actor_subject_bindings "
                    "WHERE actor_id=:actor AND status='ACTIVE' "
                    "AND bound_at<=:at AND (revoked_at IS NULL OR :at<revoked_at) ORDER BY id"
                ),
                {"actor": actor, "at": at},
            ).mappings()
        ]

    def consumption_by_id(self, identity):
        return self._one("SELECT * FROM approval_grant_consumptions WHERE id=:id", {"id": identity})

    def consumption(self, key):
        return self._one(
            "SELECT * FROM approval_grant_consumptions WHERE command_key=:key", {"key": key}
        )

    def verify_receipt(self, identity):
        self._session.execute(
            text(
                "SELECT b13_verify_receipt(c,true) FROM approval_grant_consumptions c WHERE id=:id"
            ),
            {"id": identity},
        )

    def verify_terminal(self, identity):
        return self._one(
            "SELECT * FROM approval_grant_events WHERE grant_id=:id AND prior_status='ACTIVE'",
            {"id": identity},
        )

    def insert_consumption(self, row):
        keys = tuple(row)
        statement = text(
            "INSERT INTO approval_grant_consumptions ("
            + ",".join(keys)
            + ") VALUES ("
            + ",".join(":" + k for k in keys)
            + ")"
        )
        return self._session.execute(
            text(str(statement) + " RETURNING consumed_at").bindparams(
                bindparam("result_dto", type_=JSONB)
            ),
            row,
        ).scalar_one()

    def lock_grant(self, identity):
        self._session.execute(
            text("SELECT id FROM approval_grants WHERE id=:id FOR UPDATE"), {"id": identity}
        )

    def terminalize(self, grant, actor, status, at, reason):
        self._session.execute(
            text("""INSERT INTO approval_grant_events
          (grant_id,prior_status,new_status,actor_id,occurred_at,reason)
          VALUES(:grant,'ACTIVE',:status,:actor,:at,:reason)"""),
            {"grant": grant, "status": status, "actor": actor, "at": at, "reason": reason},
        )
        self._session.execute(
            text("UPDATE approval_grants SET status=:status WHERE id=:id"),
            {"status": status, "id": grant},
        )

    def request_events(self, identity):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM approval_request_events WHERE request_id=:id "
                    "ORDER BY occurred_at,id"
                ),
                {"id": identity},
            ).mappings()
        ]

    def grant_events(self, identity):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM approval_grant_events WHERE grant_id=:id ORDER BY occurred_at,id"
                ),
                {"id": identity},
            ).mappings()
        ]

    def consumption_for_grant(self, identity):
        # Populated forward-migration tests create legacy grants at their owning
        # revision first. This checks optional receipt availability, never discovers
        # or changes the fixed writer lock inventories.
        if (
            self._session.execute(
                text("SELECT to_regclass('public.approval_grant_consumptions')")
            ).scalar_one()
            is None
        ):
            return None
        return self._one(
            "SELECT * FROM approval_grant_consumptions WHERE grant_id=:id", {"id": identity}
        )
