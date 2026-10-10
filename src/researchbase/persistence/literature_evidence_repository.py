"""Synchronous repositories for the approved M3 literature aggregate."""

from __future__ import annotations

from sqlalchemy import text

from researchbase.foundation.canonical_json import canonical_json_text

TARGETS = {
    "ClaimVersion": ("claim_version_id", "claim_versions", "claims", "claim_id"),
    "HypothesisVersion": (
        "hypothesis_version_id",
        "hypothesis_versions",
        "hypotheses",
        "hypothesis_id",
    ),
    "ResearchQuestionVersion": (
        "research_question_version_id",
        "research_question_versions",
        "research_questions",
        "research_question_id",
    ),
}


class SqlAlchemyLiteratureEvidenceRepository:
    def __init__(self, session):
        self._session = session

    def _one(self, sql, values):
        row = self._session.execute(text(sql), values).mappings().first()
        return dict(row) if row else None

    def artifact(self, identity, project):
        return self._one(
            """SELECT v.*,a.project_id,a.description,a.name FROM artifact_versions v
            JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=:id AND a.project_id=:project""",
            {"id": identity, "project": project},
        )

    def evidence(self, identity, project):
        return self._one(
            "SELECT * FROM literature_evidence WHERE id=:id AND project_id=:project FOR UPDATE",
            {"id": identity, "project": project},
        )

    def review_event(self, identity):
        return self._one(
            "SELECT * FROM literature_evidence_review_events WHERE id=:id", {"id": identity}
        )

    def events(self, identity):
        return [
            dict(row)
            for row in self._session.execute(
                text("""SELECT * FROM literature_evidence_review_events
            WHERE literature_evidence_id=:id ORDER BY reviewed_at,id"""),
                {"id": identity},
            ).mappings()
        ]

    def target(self, kind, identity, project):
        _, versions, parents, fk = TARGETS[kind]
        return self._one(
            f"""SELECT v.*,p.project_id FROM {versions} v JOIN {parents} p ON p.id=v.{fk}
            WHERE v.id=:id AND p.project_id=:project FOR UPDATE OF p,v""",
            {"id": identity, "project": project},
        )

    def latest(self, kind, identity):
        column = TARGETS[kind][0]
        return self._one(
            f"SELECT * FROM literature_support_snapshots WHERE {column}=:id "
            "ORDER BY snapshot_number DESC LIMIT 1",
            {"id": identity},
        )

    def snapshot(self, identity, project):
        return self._one(
            "SELECT * FROM literature_support_snapshots WHERE id=:id AND project_id=:project",
            {"id": identity, "project": project},
        )

    def relations(self, identity):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM literature_evidence_relations "
                    "WHERE literature_support_snapshot_id=:id "
                    "ORDER BY ordinal,literature_evidence_id"
                ),
                {"id": identity},
            ).mappings()
        ]

    def receipt(self, principal, project, command, request):
        return self._one(
            """SELECT * FROM literature_evidence_command_receipts WHERE deployment_id=:deployment
            AND project_id=:project AND actor_id=:actor
            AND command_name=:command AND request_id=:request""",
            {
                "deployment": principal.deployment_id,
                "project": project,
                "actor": principal.actor_id,
                "command": command,
                "request": request,
            },
        )

    def save_receipt(self, row):
        self._insert("literature_evidence_command_receipts", row)

    def insert_evidence(self, row):
        self._insert("literature_evidence", row, {"locator"})

    def insert_review(self, row):
        self._insert("literature_evidence_review_events", row)

    def insert_snapshot(self, row):
        self._insert("literature_support_snapshots", row)

    def insert_relation(self, row):
        self._insert("literature_evidence_relations", row)

    def _insert(self, table, row, json_fields: set[str] | frozenset[str] = frozenset()):
        # Only internal fixed command projections reach this private helper.
        names = list(row)
        values = {
            key: canonical_json_text(value) if key in json_fields else value
            for key, value in row.items()
        }
        placeholders = [
            f"CAST(:{name} AS jsonb)" if name in json_fields else f":{name}" for name in names
        ]
        self._session.execute(
            text(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join(placeholders)})"),
            values,
        )
