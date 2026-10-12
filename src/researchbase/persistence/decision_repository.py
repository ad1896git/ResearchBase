"""Typed Decision persistence and protected READ COMMITTED snapshot protocol.

Order: request advisory -> exact version UPDATE -> sorted table SHARE -> parent,
authority and closure rows -> reviews ordered by UUID -> Issue/basis statements.
SHARE conflicts with the ROW EXCLUSIVE PostgreSQL automatically takes for every
INSERT/UPDATE/DELETE, including normal-role SQL. It protects insertion phantoms
in governance validity joins as well as mutable source/review/authority facts.
The coarse locks are confined to this bounded command. A deadlock/serialization
failure aborts the entire UoW; the caller retries a fresh transaction.
The command's first repository operation installs transaction-local operational
limits: 10 seconds per lock wait, 30 seconds per statement. These do not change
scientific policy and cannot leak to the next transaction using this connection.
Lock/query timeouts abort the attempt through the UoW's sanitized failure path;
only deadlock/serialization failures qualify for the existing bounded retry.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

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


class SqlAlchemyDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _one(self, sql, params):
        row = self._session.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    def _many(self, sql, params):
        return [dict(row) for row in self._session.execute(text(sql), params).mappings()]

    def lock_request(self, identity: UUID) -> None:
        # Install bounds before even the first request advisory lock can wait.
        self._session.execute(text("SET LOCAL lock_timeout = '10s'"))
        self._session.execute(text("SET LOCAL statement_timeout = '30s'"))
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
            JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id
            WHERE b.decision_id=:id UNION ALL
            SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash,b.ordinal
            FROM decision_basis_reviews b
            JOIN internal_review_records r ON r.id=b.internal_review_record_id
            WHERE b.decision_id=:id ORDER BY ordinal""",
            {"id": identity},
        )

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

    def material_authors(self, target: UUID) -> frozenset[UUID]:
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
        sql = (
            "WITH RECURSIVE edges AS ("
            + " UNION ALL ".join(edges)
            + """),
          closure(kind,id) AS (SELECT 'scientific_conclusion_versions'::text,CAST(:target AS uuid)
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id), authors AS ("""
            + authors
            + """ )
          SELECT DISTINCT a.created_by FROM authors a JOIN closure c
            ON c.kind=a.kind AND c.id=a.id"""
        )
        return frozenset(self._session.execute(text(sql), {"target": target}).scalars())

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
