"""Typed Decision persistence; callers establish the literal first-SHARE protocol.

Write-only target/advisory helpers are separate from plain historical basis reads.
The legacy snapshot constant remains frozen because B06 imports that inventory.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.foundation.time import to_utc

# Fixed inventory of mutable facts consulted by existing closure/identity readers.
# Frozen Phase1 record/input material has accepted immutable SQL guards; its
# owning identities and version lifecycle rows are included for stable ownership.
_SNAPSHOT_TABLES = tuple(
    sorted(
        {
            "actors",
            "actor_subject_bindings",
            "project_memberships",
            "project_membership_events",
            "project_role_assignments",
            "projects",
            "audit_findings",
            "impact_assessments",
            "impact_targets",
            "correction_records",
            "literature_evidence",
            "literature_evidence_review_events",
            "source_versions",
            "literature_sources",
            "literature_source_project_links",
            "scientific_conclusions",
            "claims",
            "claim_versions",
            "artifacts",
            "artifact_versions",
            "datasets",
            "metric_definitions",
            "metric_definition_versions",
            "experiment_specs",
            "experiment_spec_versions",
            "runs",
        }
    )
)


B11_SNAPSHOT_TABLES = (
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
B11_SHARE_SQL = "LOCK TABLE " + ",".join(B11_SNAPSHOT_TABLES) + " IN SHARE MODE"


class SqlAlchemyDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _one(self, sql, params):
        row = self._session.execute(text(sql), params).mappings().first()
        return (
            {
                key: to_utc(value) if isinstance(value, datetime) else value
                for key, value in row.items()
            }
            if row
            else None
        )

    def _many(self, sql, params):
        return [dict(row) for row in self._session.execute(text(sql), params).mappings()]

    def lock_request(self, identity: UUID) -> None:
        # N SHARE and operational limits are already held by the writer UoW.
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr215:decision:{identity}"},
        )

    def target(self, identity: UUID, project: UUID):
        # Separate statements make the target row exclusion precede parent locks.
        row = self._one(
            """SELECT v.* FROM scientific_conclusion_versions v
            JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
            WHERE v.id=:id AND c.project_id=:project FOR UPDATE OF v""",
            {"id": identity, "project": project},
        )
        return row

    def lock_snapshot(self) -> None:
        # Application UoWs configure isolation before their first statement.
        # Preserve the legacy direct-repository entry point on a fresh Session.
        if not self._session.in_transaction():
            self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self._session.execute(text("LOCK TABLE " + ",".join(_SNAPSHOT_TABLES) + " IN SHARE MODE"))

    def decision(self, identity: UUID, project: UUID):
        return self._one(
            "SELECT * FROM decision_records WHERE id=:id AND project_id=:project",
            {"id": identity, "project": project},
        )

    def decision_exists(self, identity: UUID) -> bool:
        return bool(
            self._session.execute(
                text("SELECT EXISTS(SELECT 1 FROM decision_records WHERE id=:id)"), {"id": identity}
            ).scalar_one()
        )

    def scoped_decision(self, target: UUID, project: UUID):
        return self._one(
            """SELECT d.id FROM decision_records d
            JOIN decision_basis_conclusions b ON b.decision_id=d.id
            WHERE b.scientific_conclusion_version_id=:target AND d.project_id=:project
              AND d.decision_type='INTERNAL_SCIENTIFIC_RELEASE'""",
            {"target": target, "project": project},
        )

    def basis(self, identity: UUID):
        return self._many(
            """SELECT 'ScientificConclusionVersion' AS type,
            b.scientific_conclusion_version_id AS id,v.content_hash,b.ordinal
            FROM decision_basis_conclusions b
            LEFT JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id
            WHERE b.decision_id=:id UNION ALL
            SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash,b.ordinal
            FROM decision_basis_reviews b
            LEFT JOIN internal_review_records r ON r.id=b.internal_review_record_id
            WHERE b.decision_id=:id ORDER BY ordinal""",
            {"id": identity},
        )

    def revision_basis(self, identity: UUID):
        # B07-only query: the release reader also runs at the accepted 0042 checkpoint.
        rows = self.basis(identity)
        rows += self._many(
            """SELECT 'ClaimVersion' AS type,b.claim_version_id AS id,v.content_hash,b.ordinal
            FROM decision_basis_claims b JOIN claim_versions v ON v.id=b.claim_version_id
            WHERE b.decision_id=:id""",
            {"id": identity},
        )
        rows += self._many(
            """SELECT 'ManuscriptVersion' AS type,b.manuscript_version_id AS id,
                v.content_hash,b.ordinal
            FROM decision_basis_manuscripts b
            JOIN manuscript_versions v ON v.id=b.manuscript_version_id
            WHERE b.decision_id=:id""",
            {"id": identity},
        )
        return sorted(rows, key=lambda row: row["ordinal"])

    def reviews(self, target: UUID, project: UUID):
        return self._many(
            """SELECT * FROM internal_review_records
            WHERE scientific_conclusion_version_id=:target AND project_id=:project
            ORDER BY id FOR SHARE""",
            {"target": target, "project": project},
        )

    def review_creation_authorized(self, row) -> bool:
        # Historical intervals/events; present role expiry/retirement is not a rewrite
        # of a valid creation fact. No caller credential is inferred from review IDs.
        return bool(
            self._session.execute(
                text("""SELECT EXISTS (
            SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments r ON r.membership_id=m.id
                AND r.project_id=m.project_id AND r.actor_id=m.actor_id
            WHERE a.id=:actor AND a.actor_type='HUMAN' AND a.created_at<=:at
              AND (a.retired_at IS NULL OR :at<a.retired_at)
              AND m.project_id=:project AND m.started_at<=:at
              AND (SELECT e.new_status FROM project_membership_events e
                  WHERE e.membership_id=m.id AND e.occurred_at<=:at
                  ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
              AND r.role IN ('OWNER','REVIEWER') AND r.effective_from<=:at
              AND (r.effective_until IS NULL OR :at<r.effective_until)
              AND EXISTS (SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                AND b.bound_at<=:at AND (b.revoked_at IS NULL OR :at<b.revoked_at))
            )"""),
                {
                    "actor": row["reviewer_actor_id"],
                    "project": row["project_id"],
                    "at": row["created_at"],
                },
            ).scalar_one()
        )

    def has_blockers(self, target: UUID, project: UUID) -> bool:
        # Historical OPEN-only checkpoints predate B08. Validate terminal
        # projections when present without requiring its SQL function at 0042.
        terminal_ids = (
            self._session.execute(
                text("""SELECT i.id FROM review_issues i
            JOIN internal_review_records r ON r.id=i.review_record_id
            WHERE r.project_id=:project AND r.scientific_conclusion_version_id=:target
              AND i.status<>'OPEN' ORDER BY i.id"""),
                {"target": target, "project": project},
            )
            .scalars()
            .all()
        )
        for identity in terminal_ids:
            self._session.execute(text("SELECT b08_check_history(:id)"), {"id": identity})
        return bool(
            self._session.execute(
                text("""SELECT EXISTS (
            SELECT 1 FROM review_issues i JOIN internal_review_records r
              ON r.id=i.review_record_id WHERE r.project_id=:project
              AND r.scientific_conclusion_version_id=:target
              AND i.status='OPEN' AND i.severity='BLOCKING')"""),
                {"target": target, "project": project},
            ).scalar_one()
        )

    def material_authors(
        self, target: UUID, *, manuscript: bool = False, claim: bool = False, snapshot: bool = False
    ) -> frozenset[UUID]:
        # Fixed typed dependency edges. No live/current substitution is used.
        edges = []
        parents = {
            "scientific_conclusion_versions": (
                "scientific_conclusions",
                "scientific_conclusion_id",
            ),
            "claim_versions": ("claims", "claim_id"),
            "source_versions": ("literature_sources", "literature_source_id"),
            "artifact_versions": ("artifacts", "artifact_id"),
            "dataset_snapshots": ("datasets", "dataset_id"),
            "metric_definition_versions": ("metric_definitions", "metric_definition_id"),
            "experiment_spec_versions": ("experiment_specs", "experiment_spec_id"),
        }
        if manuscript:
            parents["manuscript_versions"] = ("publications", "publication_id")
        for child, (parent, fk) in parents.items():
            edges.append(
                f"SELECT '{child}'::text AS kind,id,'{parent}'::text AS child_kind,"
                f"{fk} AS child_id FROM {child}"
            )
        for table, owner, owner_fk, refs in (
            (
                "scientific_conclusion_claim_inputs",
                "scientific_conclusion_versions",
                "conclusion_version_id",
                (
                    ("claim_versions", "claim_version_id"),
                    ("literature_support_snapshots", "literature_support_snapshot_id"),
                ),
            ),
            (
                "scientific_conclusion_literature_inputs",
                "scientific_conclusion_versions",
                "conclusion_version_id",
                (("literature_evidence", "literature_evidence_id"),),
            ),
            (
                "evidence_relations",
                "claim_versions",
                "claim_version_id",
                (
                    ("measurements", "measurement_id"),
                    ("statistical_results", "statistical_result_id"),
                ),
            ),
            (
                "statistical_result_inputs",
                "statistical_results",
                "statistical_result_id",
                (("measurements", "measurement_id"),),
            ),
            (
                "run_artifact_inputs",
                "runs",
                "run_id",
                (("artifact_versions", "artifact_version_id"),),
            ),
            (
                "run_dataset_inputs",
                "runs",
                "run_id",
                (("dataset_snapshots", "dataset_snapshot_id"),),
            ),
            (
                "literature_evidence_relations",
                "literature_support_snapshots",
                "literature_support_snapshot_id",
                (("literature_evidence", "literature_evidence_id"),),
            ),
        ):
            for child, fk in refs:
                edges.append(
                    f"SELECT '{owner}',{owner_fk},'{child}',{fk} FROM {table} "
                    f"WHERE {fk} IS NOT NULL"
                )
        for table, refs in (
            (
                "measurements",
                (
                    ("runs", "run_id"),
                    ("metric_definition_versions", "metric_definition_version_id"),
                ),
            ),
            ("runs", (("experiment_spec_versions", "experiment_spec_version_id"),)),
            ("literature_evidence", (("source_versions", "source_version_id"),)),
            (
                "literature_support_snapshots",
                (
                    ("claim_versions", "claim_version_id"),
                    ("literature_support_snapshots", "previous_snapshot_id"),
                ),
            ),
            (
                "source_versions",
                (
                    ("artifact_versions", "fulltext_artifact_version_id"),
                    ("source_versions", "predecessor_source_version_id"),
                    ("artifact_versions", "correction_basis_artifact_version_id"),
                ),
            ),
        ):
            for child, fk in refs:
                edges.append(
                    f"SELECT '{table}',id,'{child}',{fk} FROM {table} WHERE {fk} IS NOT NULL"
                )
        tables = (
            set(parents)
            | {x[0] for x in parents.values()}
            | {
                "measurements",
                "runs",
                "statistical_results",
                "literature_evidence",
                "literature_support_snapshots",
            }
        )
        authors = " UNION ALL ".join(
            f"SELECT '{table}'::text AS kind,id,created_by FROM {table}"
            for table in sorted(tables)
            # LiteratureSource is a global identity with explicit actor attribution.
        )
        authors += (
            " UNION ALL SELECT 'claim_versions',claim_version_id,created_by FROM evidence_relations"
        )
        authors += (
            " UNION ALL SELECT 'literature_support_snapshots',"
            "literature_support_snapshot_id,created_by FROM literature_evidence_relations"
        )
        if manuscript:
            edges.append(
                "SELECT 'manuscript_versions',id,'artifact_versions',document_artifact_version_id "
                "FROM manuscript_versions"
            )
            for table, refs in (
                (
                    "manuscript_claim_placements",
                    (
                        ("claim_versions", "claim_version_id"),
                        ("scientific_conclusion_versions", "scientific_conclusion_version_id"),
                    ),
                ),
                ("manuscript_citation_placements", (("source_versions", "source_version_id"),)),
                ("manuscript_artifact_placements", (("artifact_versions", "artifact_version_id"),)),
            ):
                for child, fk in refs:
                    edges.append(
                        f"SELECT 'manuscript_versions',manuscript_version_id,'{child}',{fk} "
                        f"FROM {table} WHERE {fk} IS NOT NULL"
                    )
                authors += (
                    " UNION ALL SELECT 'manuscript_versions',manuscript_version_id,created_by "
                    f"FROM {table}"
                )
        seed = (
            "manuscript_versions"
            if manuscript
            else "claim_versions"
            if claim
            else "literature_support_snapshots"
            if snapshot
            else "scientific_conclusion_versions"
        )
        sql = (
            "WITH RECURSIVE edges AS ("
            + " UNION ALL ".join(edges)
            + """),
          closure(kind,id) AS (SELECT CAST(:seed AS text),CAST(:target AS uuid)
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id), authors AS ("""
            + authors
            + """ )
          SELECT DISTINCT a.created_by FROM authors a JOIN closure c
            ON c.kind=a.kind AND c.id=a.id"""
        )
        return frozenset(
            self._session.execute(text(sql), {"target": target, "seed": seed}).scalars()
        )

    def _insert(self, table, row) -> None:
        keys = tuple(row)
        self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(keys)}) VALUES ("
                + ",".join(f":{key}" for key in keys)
                + ")"
            ),
            row,
        )

    def insert_decision(self, row) -> None:
        self._insert("decision_records", row)

    def insert_conclusion_basis(self, row) -> None:
        self._insert("decision_basis_conclusions", row)

    def insert_review_basis(self, row) -> None:
        self._insert("decision_basis_reviews", row)

    def concern(self, decision):
        return self._one(
            "SELECT * FROM decision_revision_concerns WHERE decision_id=:id", {"id": decision}
        )

    def concern_decision(self, issue):
        return self._one(
            "SELECT decision_id FROM decision_revision_concerns WHERE review_issue_id=:id",
            {"id": issue},
        )

    def manuscript_admission_reviews(self, target, project):
        # Compose the established closure query so predecessor schemas and
        # final-authorization hooks retain their behavior. Only earlier same-
        # Publication blocking concerns are added; they are not affirmative basis.
        rows = self.applicable_manuscript_reviews(target, project)
        earlier = self._many(
            """SELECT r.* FROM internal_review_records r
            JOIN manuscript_versions old ON old.id=r.manuscript_version_id
            JOIN manuscript_versions selected ON selected.publication_id=old.publication_id
            WHERE selected.id=:target AND old.version_number<selected.version_number
              AND r.project_id=:project AND EXISTS (
                SELECT 1 FROM review_issues i WHERE i.review_record_id=r.id
                  AND i.status='OPEN' AND i.severity='BLOCKING')
            ORDER BY r.id""",
            {"target": target, "project": project},
        )
        return sorted({row["id"]: row for row in (*rows, *earlier)}.values(), key=lambda r: r["id"])

    def revision_reviews(self, issue, project, *, lock=False):
        column = (
            "claim_version_id"
            if issue["claim_version_id"] is not None
            else "manuscript_version_id"
            if issue.get("manuscript_version_id") is not None
            else "scientific_conclusion_version_id"
        )
        return self._many(
            "SELECT * FROM internal_review_records WHERE "
            + column
            + "=:target AND project_id=:project ORDER BY id"
            + (" FOR SHARE" if lock else ""),
            {"target": issue[column], "project": project},
        )

    def insert_claim_basis(self, row):
        self._session.execute(
            text(
                "INSERT INTO decision_basis_claims "
                "(decision_id,claim_version_id,ordinal) "
                "VALUES (:decision_id,:claim_version_id,:ordinal)"
            ),
            row,
        )

    def insert_concern(self, decision, issue):
        self._session.execute(
            text(
                "INSERT INTO decision_revision_concerns "
                "(decision_id,review_issue_id) VALUES (:decision,:issue)"
            ),
            {"decision": decision, "issue": issue},
        )

    def force_revision_constraints(self):
        self._session.execute(
            text(
                "SET CONSTRAINTS pr215_complete_decision,b07_complete_decision,b07_complete_claim,"
                "b07_complete_concern,pr215_complete_conclusion,pr215_complete_review,"
                "b11_complete_manuscript IMMEDIATE"
            )
        )

    def revision_creation_authorized(self, row):
        return bool(
            self._session.execute(
                text("SELECT pr216_decision_authorized(d) FROM decision_records d WHERE id=:id"),
                {"id": row["id"]},
            ).scalar_one()
        )

    def prepare_readiness_write(self):
        self._session.execute(text(B11_SHARE_SQL))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def prepare_readiness_read(self):
        self._session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))

    def lock_readiness_request(self, identity: UUID):
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b11:decision:{identity}"},
        )

    def lock_prepare_submission_request(self, identity: UUID):
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b12:decision:{identity}"},
        )

    def prepare_submission_other_basis(self, identity: UUID) -> bool:
        return self.readiness_other_basis(identity) or bool(
            self._session.execute(
                text("""SELECT EXISTS(SELECT 1 FROM decision_basis_approval_decisions
                WHERE decision_id=:id)
                OR EXISTS(SELECT 1 FROM decision_basis_revision_actions WHERE decision_id=:id)"""),
                {"id": identity},
            ).scalar_one()
        )

    def prepare_submission_scope(self, target: UUID, project: UUID):
        return self._one(
            """SELECT d.id FROM decision_records d
            JOIN decision_basis_manuscripts b ON b.decision_id=d.id
            WHERE b.manuscript_version_id=:target AND d.project_id=:project
            AND d.decision_type='PREPARE_SUBMISSION'""",
            {"target": target, "project": project},
        )

    def manuscript_basis(self, identity: UUID):
        return self._many(
            """SELECT 'ManuscriptVersion' AS type,
            b.manuscript_version_id AS id,v.content_hash,b.ordinal
            FROM decision_basis_manuscripts b
            JOIN manuscript_versions v ON v.id=b.manuscript_version_id
            WHERE b.decision_id=:id UNION ALL
            SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash,b.ordinal
            FROM decision_basis_reviews b
            JOIN internal_review_records r ON r.id=b.internal_review_record_id
            WHERE b.decision_id=:id ORDER BY ordinal""",
            {"id": identity},
        )

    def readiness_scope(self, target: UUID, project: UUID):
        return self._one(
            """SELECT d.id FROM decision_records d
            JOIN decision_basis_manuscripts b ON b.decision_id=d.id
            WHERE b.manuscript_version_id=:target AND d.project_id=:project
            AND d.decision_type='READY_FOR_SUBMISSION'""",
            {"target": target, "project": project},
        )

    def readiness_other_basis(self, identity: UUID) -> bool:
        return bool(
            self._session.execute(
                text("""SELECT
            EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=:id) OR
            EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=:id) OR
            EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=:id)"""),
                {"id": identity},
            ).scalar_one()
        )

    def applicable_manuscript_reviews(self, target: UUID, project: UUID):
        return self._many(
            "SELECT * FROM b11_applicable_reviews(:target,:project) ORDER BY id",
            {"target": target, "project": project},
        )

    def insert_manuscript_basis(self, row):
        self._insert("decision_basis_manuscripts", row)

    def force_readiness_constraints(self):
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    def require_readiness_snapshot(self):
        self._session.execute(text("SELECT b11_require_snapshot()"))

    def manuscript_exists(self, identity: UUID) -> bool:
        return (
            self._one("SELECT id FROM manuscript_versions WHERE id=:id", {"id": identity})
            is not None
        )

    def lock_readiness_target(self, identity: UUID):
        self._session.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"), {"id": identity}
        )

    def lock_readiness_project(self, identity: UUID):
        self._session.execute(
            text("SELECT id FROM projects WHERE id=:id FOR SHARE"), {"id": identity}
        )

    def reconsideration_basis(self, identity: UUID):
        return self._many(
            """SELECT 'ScientificConclusionVersion' AS type,
            b.scientific_conclusion_version_id AS id,v.content_hash,b.ordinal
            FROM decision_basis_conclusions b
            JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id
            WHERE b.decision_id=:id UNION ALL
            SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash,b.ordinal
            FROM decision_basis_reviews b
            JOIN internal_review_records r ON r.id=b.internal_review_record_id
            WHERE b.decision_id=:id UNION ALL
            SELECT 'ApprovalDecision',b.approval_decision_id,r.content_hash,b.ordinal
            FROM decision_basis_approval_decisions b JOIN approval_decisions r
              ON r.id=b.approval_decision_id WHERE b.decision_id=:id UNION ALL
            SELECT 'RevisionAction',b.revision_action_id,r.content_hash,b.ordinal
            FROM decision_basis_revision_actions b JOIN revision_actions r
              ON r.id=b.revision_action_id WHERE b.decision_id=:id UNION ALL
            SELECT 'ManuscriptVersion',b.manuscript_version_id,v.content_hash,b.ordinal
            FROM decision_basis_manuscripts b
            JOIN manuscript_versions v ON v.id=b.manuscript_version_id
            WHERE b.decision_id=:id ORDER BY ordinal""",
            {"id": identity},
        )

    def lock_reconsideration(self, identity):
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr215:decision:{identity}"},
        )

    def insert_rejection_basis(self, row):
        self._insert("decision_basis_approval_decisions", row)

    def insert_revision_basis(self, row):
        self._insert("decision_basis_revision_actions", row)

    def lock_conclusion_parent(self, identity):
        self._session.execute(
            text("""SELECT c.id FROM scientific_conclusions c
          JOIN scientific_conclusion_versions v ON v.scientific_conclusion_id=c.id
          WHERE v.id=:id FOR SHARE OF c"""),
            {"id": identity},
        )
