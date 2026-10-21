"""SQL persistence for the bounded PR2-18 immutable records."""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import text

from researchbase.foundation.canonical_json import canonical_json_text

N = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "audit_findings",
    "claim_versions",
    "claims",
    "correction_records",
    "datasets",
    "experiment_spec_versions",
    "experiment_specs",
    "impact_assessments",
    "impact_targets",
    "literature_evidence",
    "literature_evidence_review_events",
    "literature_search_execution_events",
    "literature_search_executions",
    "literature_search_plan_versions",
    "literature_search_plans",
    "literature_search_provider_attempts",
    "literature_source_project_links",
    "literature_sources",
    "metadata_observations",
    "metric_definition_versions",
    "metric_definitions",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "runs",
    "scientific_conclusions",
    "search_query_records",
    "search_result_records",
    "search_result_resolutions",
    "source_versions",
)
_TABLES = {
    "coverage": "search_coverage",
    "prior_art": "prior_art_relations",
    "novelty": "novelty_assessments",
}


class SqlAlchemyNoveltyRepository:
    def __init__(self, session):
        self._session = session

    def one(self, sql, params):
        row = self._session.execute(text(sql), params).mappings().first()
        if row is None:
            return None
        result = dict(row)
        if result.get("created_at") is not None:
            result["created_at"] = result["created_at"].astimezone(UTC)
        return result

    def many(self, sql, params):
        return [dict(row) for row in self._session.execute(text(sql), params).mappings()]

    def lock_snapshot(self):
        self._session.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))

    def prepare(self, kind, identity, claim=None):
        self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self.lock_snapshot()  # FIRST transaction statement for every scoped write.
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr218:{kind}:{identity}"},
        )
        if kind != "coverage":
            self.one("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE", {"id": claim})

    def repeatable_read(self):
        self._session.connection(execution_options={"isolation_level": "REPEATABLE READ"})

    def force_constraints(self):
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    def at(self):
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one().astimezone(UTC)

    def authority(self, principal, project):
        return self.many(
            """SELECT a.retired_at,m.status AS membership_status,
            r.role,r.effective_from,r.effective_until,b.status AS binding_status,
            b.bound_at,b.revoked_at,p.lifecycle_status FROM actors a
            JOIN project_memberships m ON m.actor_id=a.id
            JOIN projects p ON p.id=m.project_id
            JOIN project_role_assignments r ON r.membership_id=m.id
              AND r.actor_id=m.actor_id AND r.project_id=m.project_id
            JOIN actor_subject_bindings b ON b.actor_id=a.id
            WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
              AND b.subject_kind=:kind AND b.subject_value=:value
              AND b.subject_credential_id=:credential ORDER BY a.id,m.id,r.id,b.id""",
            {
                "actor": principal.actor_id,
                "project": project,
                "deployment": principal.deployment_id,
                "kind": principal.subject_kind,
                "value": principal.subject_value,
                "credential": principal.credential_id,
            },
        )

    def dependency_count(self, identities):
        row = self.one(
            "SELECT count(*) AS n FROM (SELECT * FROM b23_dependencies(:ids) LIMIT 10001) d",
            {"ids": list(identities)},
        )
        assert row is not None
        return row["n"]

    def historical_authority(self, actor, project, at, roles, human):
        row = self.one(
            "SELECT b23_authorized(:actor,:project,:at,:roles,:human) AS allowed",
            {"actor": actor, "project": project, "at": at, "roles": list(roles), "human": human},
        )
        return bool(row and row["allowed"])

    def human(self, identity):
        return self.one("SELECT actor_type FROM actors WHERE id=:id", {"id": identity}) == {
            "actor_type": "HUMAN"
        }

    def committed_assessment(self, identity):
        row = self.one(
            "SELECT xmin IS DISTINCT FROM pg_current_xact_id()::xid AS committed "
            "FROM novelty_assessments WHERE id=:id",
            {"id": identity},
        )
        return bool(row and row["committed"])

    def parent(self, kind, identity):
        table = _TABLES[kind]
        if kind == "coverage":
            return self.one(
                f"""SELECT c.*,p.project_id FROM {table} c
                LEFT JOIN literature_search_plan_versions v ON v.id=c.search_plan_version_id
                LEFT JOIN literature_search_plans p ON p.id=v.plan_id WHERE c.id=:id""",
                {"id": identity},
            )
        return self.one(
            f"""SELECT c.*,p.project_id FROM {table} c
            LEFT JOIN claim_versions v ON v.id=c.claim_version_id
            LEFT JOIN claims p ON p.id=v.claim_id
            WHERE c.id=:id""",
            {"id": identity},
        )

    def executions(self, identity):
        return tuple(
            row["search_execution_id"]
            for row in self.many(
                """SELECT search_execution_id FROM search_coverage_executions
                WHERE search_coverage_id=:id ORDER BY search_execution_id""",
                {"id": identity},
            )
        )

    def resolutions(self, identity):
        return self.many(
            """SELECT r.*,b.resolution_content_hash FROM search_coverage_resolutions b
            LEFT JOIN search_result_resolutions r ON r.id=b.search_result_resolution_id
            WHERE b.search_coverage_id=:id ORDER BY r.search_result_record_id,r.id""",
            {"id": identity},
        )

    def evidence(self, identity):
        return tuple(
            row["literature_evidence_id"]
            for row in self.many(
                """SELECT literature_evidence_id FROM prior_art_evidence_inputs
                WHERE prior_art_relation_id=:id ORDER BY literature_evidence_id""",
                {"id": identity},
            )
        )

    def basis(self, identity):
        return self.many(
            """SELECT prior_art_relation_id,search_result_resolution_id
            FROM novelty_assessment_prior_art_inputs WHERE novelty_assessment_id=:id
            ORDER BY prior_art_relation_id""",
            {"id": identity},
        )

    def resolution(self, identity):
        return self.one(
            """SELECT s.*,q.literature_search_execution_id AS execution_id,e.project_id
            FROM search_result_resolutions s
            JOIN search_result_records r ON r.id=s.search_result_record_id
            JOIN search_query_records q ON q.id=r.search_query_record_id
            JOIN literature_search_executions e ON e.id=q.literature_search_execution_id
            WHERE s.id=:id""",
            {"id": identity},
        )

    def predecessor(self, identity):
        return self.one(
            "SELECT id FROM novelty_assessments WHERE id=:id FOR UPDATE", {"id": identity}
        )

    def successor(self, identity):
        row = self.one(
            "SELECT id FROM novelty_assessments WHERE supersedes_assessment_id=:id",
            {"id": identity},
        )
        return row["id"] if row else None

    def prior_art_predecessor(self, identity):
        return self.one(
            "SELECT id FROM prior_art_relations WHERE id=:id FOR UPDATE", {"id": identity}
        )

    def prior_art_successor(self, identity):
        row = self.one(
            "SELECT id FROM prior_art_relations WHERE supersedes_prior_art_relation_id=:id",
            {"id": identity},
        )
        return row["id"] if row else None

    def prior_art_pair(self, claim, source):
        return self.many(
            """SELECT p.*,c.project_id FROM prior_art_relations p
            LEFT JOIN claim_versions v ON v.id=p.claim_version_id
            LEFT JOIN claims c ON c.id=v.claim_id
            WHERE p.claim_version_id=:claim AND p.source_version_id=:source
            ORDER BY p.id LIMIT 10001""",
            {"claim": claim, "source": source},
        )

    def insert(self, kind, values):
        table = _TABLES[kind]
        values = dict(values)
        columns = tuple(values)
        binds = [
            f"CAST(:{c} AS jsonb)" if c in {"providers", "time_scope"} else f":{c}" for c in columns
        ]
        for c in ("providers", "time_scope"):
            if c in values and values[c] is not None:
                values[c] = canonical_json_text(values[c])
        self._session.execute(
            text(
                f"INSERT INTO {table} (" + ",".join(columns) + ") VALUES (" + ",".join(binds) + ")"
            ),
            values,
        )

    def insert_child(self, kind, values):
        table = {
            "coverage": "search_coverage_executions",
            "coverage_resolution": "search_coverage_resolutions",
            "prior_art": "prior_art_evidence_inputs",
            "novelty": "novelty_assessment_prior_art_inputs",
            "novelty_probe": "novelty_assessment_probes",
            "novelty_screen": "novelty_assessment_screening_results",
        }[kind]
        columns = tuple(values)
        self._session.execute(
            text(
                f"INSERT INTO {table} ("
                + ",".join(columns)
                + ") VALUES ("
                + ",".join(":" + c for c in columns)
                + ")"
            ),
            values,
        )

    def independent_verification(self, identity, author):
        return bool(
            self.one(
                """SELECT e.id FROM literature_evidence_review_events e
            JOIN actors a ON a.id=e.reviewed_by
            WHERE e.id=(SELECT id FROM literature_evidence_review_events
              WHERE literature_evidence_id=:id ORDER BY reviewed_at DESC,id DESC LIMIT 1)
              AND e.new_status='VERIFIED' AND a.actor_type='HUMAN' AND e.reviewed_by<>:author""",
                {"id": identity, "author": author},
            )
        )

    def plan(self, identity):
        return self.one(
            """SELECT v.*,p.project_id FROM literature_search_plan_versions v
            JOIN literature_search_plans p ON p.id=v.plan_id WHERE v.id=:id""",
            {"id": identity},
        )

    def claim(self, identity):
        return self.one(
            """SELECT v.*,c.project_id FROM claim_versions v
            JOIN claims c ON c.id=v.claim_id WHERE v.id=:id""",
            {"id": identity},
        )

    def plan_executions(self, identity):
        rows = self.many(
            "SELECT id FROM literature_search_executions "
            "WHERE search_plan_version_id=:id ORDER BY id LIMIT 101",
            {"id": identity},
        )
        return tuple(x["id"] for x in rows)

    def probes(self, identity):
        return self.many(
            "SELECT * FROM novelty_assessment_probes "
            "WHERE novelty_assessment_id=:id ORDER BY search_execution_id,query_index",
            {"id": identity},
        )

    def screening_results(self, identity):
        return self.many(
            "SELECT * FROM novelty_assessment_screening_results "
            "WHERE novelty_assessment_id=:id ORDER BY search_result_record_id",
            {"id": identity},
        )
