"""Project-confined publication drafts and atomic internal lifecycle history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

B14A_SNAPSHOT_TABLES = (
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
B14A_SHARE_SQL = "LOCK TABLE " + ",".join(B14A_SNAPSHOT_TABLES) + " IN SHARE MODE"


class SqlAlchemyPublicationRepository:
    def __init__(self, session: Session, *, protected_reads: bool = False) -> None:
        self._session = session
        self._protected_reads = protected_reads

    def lock_project(self, project: UUID) -> None:
        self._session.execute(
            text("SELECT id FROM projects WHERE id=:id FOR SHARE"), {"id": project}
        )

    def lock_request(self, key: str) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def publication(self, identity: UUID, project: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        row = (
            self._session.execute(
                text(
                    """SELECT * FROM publications
          WHERE id=:id AND project_id=:project"""
                    + suffix
                ),
                {"id": identity, "project": project},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def version(
        self, identity: UUID, publication: UUID, *, lock: bool = False, share: bool = False
    ):
        row = (
            self._session.execute(
                text(
                    """SELECT * FROM manuscript_versions
          WHERE id=:id AND publication_id=:publication"""
                    + (" FOR UPDATE" if lock else " FOR SHARE" if share else "")
                ),
                {"id": identity, "publication": publication},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def next_version(self, publication: UUID) -> int:
        return self._session.execute(
            text(
                "SELECT coalesce(max(version_number)::bigint,0)+1 FROM manuscript_versions "
                "WHERE publication_id=:id"
            ),
            {"id": publication},
        ).scalar_one()

    def has_draft(self, publication: UUID) -> bool:
        return self._session.execute(
            text(
                "SELECT EXISTS(SELECT 1 FROM manuscript_versions WHERE publication_id=:id "
                "AND status='DRAFT')"
            ),
            {"id": publication},
        ).scalar_one()

    def initial_version(self, publication: UUID):
        return self._session.execute(
            text("""SELECT id FROM manuscript_versions
          WHERE publication_id=:publication AND version_number=1"""),
            {"publication": publication},
        ).scalar_one_or_none()

    def document(self, identity: UUID, project: UUID):
        row = (
            self._session.execute(
                text(
                    """SELECT v.id,v.status,v.frozen_at,
          v.content_hash,v.byte_size,a.artifact_type,a.project_id
          FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=:id AND a.project_id=:project"""
                    + ("" if self._protected_reads else " FOR SHARE OF v,a")
                ),
                {"id": identity, "project": project},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_publication(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO publications
          (id,project_id,publication_type,title,lifecycle_status,
           current_manuscript_version_id,created_by,created_at,row_version)
          VALUES (:id,:project_id,:publication_type,:title,:lifecycle_status,
                  :current_manuscript_version_id,:created_by,:created_at,:row_version)"""),
            values,
        )

    def insert_initial_event(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO publication_lifecycle_events
          (id,publication_id,prior_status,new_status,actor_id,occurred_at)
          VALUES (:id,:publication_id,NULL,'DRAFTING',:actor_id,:occurred_at)"""),
            values,
        )

    def insert_version(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO manuscript_versions
          (id,publication_id,version_number,status,document_artifact_version_id,
           title,abstract,semantic_change_class,placement_set_hash,content_hash,hash_scheme,
           created_by,created_at,frozen_at,row_version)
          VALUES (:id,:publication_id,:version_number,:status,:document_artifact_version_id,
                  :title,:abstract,:semantic_change_class,:placement_set_hash,:content_hash,
                  :hash_scheme,
                  :created_by,:created_at,:frozen_at,:row_version)"""),
            values,
        )

    def citation_source(self, identity: UUID, project: UUID):
        row = (
            self._session.execute(
                text(
                    """SELECT v.id,v.status,v.frozen_at,v.content_hash
          FROM source_versions v JOIN literature_source_project_links l
            ON l.literature_source_id=v.literature_source_id
          WHERE v.id=:id AND l.project_id=:project"""
                    + ("" if self._protected_reads else " FOR SHARE OF v,l")
                ),
                {"id": identity, "project": project},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_citation(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO manuscript_citation_placements
          (id,manuscript_version_id,source_version_id,section_id,locator,
           citation_purpose,ordinal,created_by,created_at,row_version)
          VALUES (:id,:manuscript_version_id,:source_version_id,:section_id,
                  CAST(:locator AS jsonb),:citation_purpose,:ordinal,:created_by,
                  :created_at,:row_version)"""),
            values,
        )

    def citation(self, identity: UUID, manuscript: UUID):
        row = (
            self._session.execute(
                text("""SELECT * FROM manuscript_citation_placements
          WHERE id=:id AND manuscript_version_id=:manuscript"""),
                {"id": identity, "manuscript": manuscript},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def citations(self, manuscript: UUID):
        rows = (
            self._session.execute(
                text("""SELECT * FROM manuscript_citation_placements
          WHERE manuscript_version_id=:manuscript ORDER BY section_id,ordinal,id"""),
                {"manuscript": manuscript},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def claim_placement_target(self, identity: UUID, project: UUID, *, conclusion: bool):
        if conclusion:
            query = """SELECT v.id,v.status,v.frozen_at,v.content_hash,v.support_set_hash
              FROM scientific_conclusion_versions v JOIN scientific_conclusions c
                ON c.id=v.scientific_conclusion_id
              WHERE v.id=:id AND c.project_id=:project""" + (
                "" if self._protected_reads else " FOR SHARE OF v,c"
            )
        else:
            query = """SELECT v.id,v.status,v.frozen_at,v.content_hash
              FROM claim_versions v JOIN claims c ON c.id=v.claim_id
              WHERE v.id=:id AND c.project_id=:project""" + (
                "" if self._protected_reads else " FOR SHARE OF v,c"
            )
        row = (
            self._session.execute(text(query), {"id": identity, "project": project})
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_claim_placement(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO manuscript_claim_placements
          (id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,
           section_id,locator,rhetorical_strength,ordinal,created_by,created_at,row_version)
          VALUES (:id,:manuscript_version_id,:claim_version_id,
                  :scientific_conclusion_version_id,:section_id,CAST(:locator AS jsonb),
                  :rhetorical_strength,:ordinal,:created_by,:created_at,:row_version)"""),
            values,
        )

    def claim_placement(self, identity: UUID, manuscript: UUID):
        row = (
            self._session.execute(
                text("""SELECT * FROM manuscript_claim_placements
          WHERE id=:id AND manuscript_version_id=:manuscript"""),
                {"id": identity, "manuscript": manuscript},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def claim_placements(self, manuscript: UUID):
        rows = (
            self._session.execute(
                text("""SELECT * FROM manuscript_claim_placements
          WHERE manuscript_version_id=:manuscript ORDER BY section_id,ordinal,id"""),
                {"manuscript": manuscript},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def artifact_placement_target(self, identity: UUID, project: UUID):
        row = (
            self._session.execute(
                text(
                    """SELECT v.id,v.status,v.frozen_at,v.content_hash,
          a.artifact_type FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=:id AND a.project_id=:project"""
                    + ("" if self._protected_reads else " FOR SHARE OF v,a")
                ),
                {"id": identity, "project": project},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_artifact_placement(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO manuscript_artifact_placements
          (id,manuscript_version_id,artifact_version_id,section_id,locator,
           artifact_role,ordinal,created_by,created_at,row_version)
          VALUES (:id,:manuscript_version_id,:artifact_version_id,:section_id,
                  CAST(:locator AS jsonb),:artifact_role,:ordinal,:created_by,
                  :created_at,:row_version)"""),
            values,
        )

    def artifact_placement(self, identity: UUID, manuscript: UUID):
        row = (
            self._session.execute(
                text("""SELECT * FROM manuscript_artifact_placements
          WHERE id=:id AND manuscript_version_id=:manuscript"""),
                {"id": identity, "manuscript": manuscript},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def artifact_placements(self, manuscript: UUID):
        rows = (
            self._session.execute(
                text("""SELECT * FROM manuscript_artifact_placements
          WHERE manuscript_version_id=:manuscript ORDER BY section_id,ordinal,id"""),
                {"manuscript": manuscript},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def begin_scientific_trace_snapshot(self) -> None:
        """Use one stable PostgreSQL snapshot for authorization and all trace reads."""
        self._session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

    def scientific_trace_placements(self, manuscript: UUID, project: UUID):
        rows = (
            self._session.execute(
                text("""
          SELECT 'CITATION'::text AS placement_kind,p.id AS placement_id,
            p.source_version_id AS target_id,p.section_id,p.locator,p.ordinal,
            p.citation_purpose AS annotation,v.status AS target_status,
            v.frozen_at AS target_frozen_at,v.content_hash AS target_hash,
            NULL::text AS support_hash,
            EXISTS (SELECT 1 FROM literature_source_project_links l
              WHERE l.literature_source_id=v.literature_source_id
                AND l.project_id=:project
                AND EXISTS (SELECT 1 FROM literature_sources ls
                  WHERE ls.id=v.literature_source_id)
                AND (v.fulltext_artifact_version_id IS NULL OR EXISTS (
                  SELECT 1 FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id
                  WHERE av.id=v.fulltext_artifact_version_id))
                AND (v.correction_basis_artifact_version_id IS NULL OR EXISTS (
                  SELECT 1 FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id
                  WHERE av.id=v.correction_basis_artifact_version_id))
                AND (v.predecessor_source_version_id IS NULL OR EXISTS (
                  SELECT 1 FROM source_versions predecessor
                  WHERE predecessor.id=v.predecessor_source_version_id
                    AND predecessor.literature_source_id=v.literature_source_id))) AS project_match
          FROM manuscript_citation_placements p
          LEFT JOIN source_versions v ON v.id=p.source_version_id
          WHERE p.manuscript_version_id=:manuscript
          UNION ALL
          SELECT 'CLAIM',p.id,p.claim_version_id,p.section_id,p.locator,p.ordinal,
            p.rhetorical_strength,v.status,v.frozen_at,v.content_hash,NULL::text,
            (c.project_id=:project)
          FROM manuscript_claim_placements p
          LEFT JOIN claim_versions v ON v.id=p.claim_version_id
          LEFT JOIN claims c ON c.id=v.claim_id
          WHERE p.manuscript_version_id=:manuscript AND p.claim_version_id IS NOT NULL
          UNION ALL
          SELECT 'CONCLUSION',p.id,p.scientific_conclusion_version_id,
            p.section_id,p.locator,p.ordinal,p.rhetorical_strength,
            v.status,v.frozen_at,v.content_hash,v.support_set_hash,
            (c.project_id=:project)
          FROM manuscript_claim_placements p
          LEFT JOIN scientific_conclusion_versions v
            ON v.id=p.scientific_conclusion_version_id
          LEFT JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE p.manuscript_version_id=:manuscript
            AND p.scientific_conclusion_version_id IS NOT NULL
          UNION ALL
          SELECT 'ARTIFACT',p.id,p.artifact_version_id,p.section_id,p.locator,
            p.ordinal,p.artifact_role,v.status,v.frozen_at,v.content_hash,NULL::text,
            (a.project_id=:project)
          FROM manuscript_artifact_placements p
          LEFT JOIN artifact_versions v ON v.id=p.artifact_version_id
          LEFT JOIN artifacts a ON a.id=v.artifact_id
          WHERE p.manuscript_version_id=:manuscript
          ORDER BY placement_kind,section_id,ordinal,placement_id
        """),
                {"manuscript": manuscript, "project": project},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def scientific_trace_conclusion_claim_inputs(self, manuscript: UUID):
        rows = (
            self._session.execute(
                text("""
          SELECT p.scientific_conclusion_version_id AS conclusion_version_id,
            i.claim_version_id,i.literature_support_snapshot_id,
            i.relation_type,i.ordinal,
            s.id AS resolved_snapshot_id,s.project_id AS snapshot_project_id,
            s.claim_version_id AS snapshot_claim_id,s.content_hash AS snapshot_content_hash,
            v.status AS claim_status,
            v.frozen_at AS claim_frozen_at,v.content_hash AS claim_content_hash,
            c.project_id AS claim_project_id
          FROM manuscript_claim_placements p
          JOIN scientific_conclusion_claim_inputs i
            ON i.conclusion_version_id=p.scientific_conclusion_version_id
          LEFT JOIN literature_support_snapshots s ON s.id=i.literature_support_snapshot_id
          LEFT JOIN claim_versions v ON v.id=i.claim_version_id
          LEFT JOIN claims c ON c.id=v.claim_id
          WHERE p.manuscript_version_id=:manuscript
          ORDER BY p.scientific_conclusion_version_id,i.ordinal,i.claim_version_id
        """),
                {"manuscript": manuscript},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def scientific_trace_claim_experiment_evidence(self, manuscript: UUID):
        rows = (
            self._session.execute(
                text("""
          WITH trace_claims AS (
            SELECT claim_version_id AS id FROM manuscript_claim_placements
              WHERE manuscript_version_id=:manuscript AND claim_version_id IS NOT NULL
            UNION
            SELECT i.claim_version_id AS id FROM manuscript_claim_placements p
              JOIN scientific_conclusion_claim_inputs i
                ON i.conclusion_version_id=p.scientific_conclusion_version_id
              WHERE p.manuscript_version_id=:manuscript
          )
          SELECT t.id AS claim_version_id,r.id AS evidence_relation_id,
            r.relation_type,r.measurement_id AS direct_measurement_id,
            r.statistical_result_id, result.id AS resolved_statistical_result_id,
            result.project_id AS result_project_id,
            dm.id AS resolved_direct_measurement_id,
            si.measurement_id AS selected_input_measurement_id,
            sm.id AS resolved_input_measurement_id,
            COALESCE(dm.id,sm.id) AS measurement_id,
            COALESCE(dm.run_id,sm.run_id) AS run_id,
            COALESCE(dr.project_id,sr.project_id) AS run_project_id,
            si.input_role,si.ordinal AS input_ordinal
          FROM trace_claims t JOIN evidence_relations r ON r.claim_version_id=t.id
          LEFT JOIN measurements dm ON dm.id=r.measurement_id
          LEFT JOIN statistical_results result ON result.id=r.statistical_result_id
          LEFT JOIN statistical_result_inputs si
            ON si.statistical_result_id=r.statistical_result_id
          LEFT JOIN measurements sm ON sm.id=si.measurement_id
          LEFT JOIN runs dr ON dr.id=dm.run_id
          LEFT JOIN runs sr ON sr.id=sm.run_id
          ORDER BY t.id,r.id,si.ordinal,si.measurement_id
        """),
                {"manuscript": manuscript},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def scientific_trace_literature_evidence(self, manuscript: UUID, project: UUID):
        rows = (
            self._session.execute(
                text("""
          WITH links AS (
            SELECT 'CONCLUSION_INPUT'::text AS link_kind,
              i.conclusion_version_id AS conclusion_version_id,
              i.conclusion_version_id AS owner_version_id,
              NULL::uuid AS snapshot_id,NULL::uuid AS relation_id,
              NULL::uuid AS snapshot_project_id,
              i.literature_evidence_id AS evidence_id,i.relation_type,i.ordinal
            FROM manuscript_claim_placements p
            JOIN scientific_conclusion_literature_inputs i
              ON i.conclusion_version_id=p.scientific_conclusion_version_id
            WHERE p.manuscript_version_id=:manuscript
            UNION ALL
            SELECT 'CLAIM_SNAPSHOT',i.conclusion_version_id,
              i.claim_version_id,i.literature_support_snapshot_id,r.id,s.project_id,
              r.literature_evidence_id,r.relation_type,r.ordinal
            FROM manuscript_claim_placements p
            JOIN scientific_conclusion_claim_inputs i
              ON i.conclusion_version_id=p.scientific_conclusion_version_id
            LEFT JOIN literature_support_snapshots s
              ON s.id=i.literature_support_snapshot_id
                AND s.claim_version_id=i.claim_version_id
            LEFT JOIN literature_evidence_relations r ON r.literature_support_snapshot_id=s.id
            WHERE p.manuscript_version_id=:manuscript
              AND i.literature_support_snapshot_id IS NOT NULL
          )
          SELECT l.link_kind,l.conclusion_version_id,l.owner_version_id,
            l.snapshot_id,l.relation_id,
            l.snapshot_project_id,
            l.evidence_id,l.relation_type,l.ordinal,
            e.project_id AS evidence_project_id,e.source_version_id,
            e.review_status,e.content_hash AS evidence_content_hash,
            v.status AS source_status,v.frozen_at AS source_frozen_at,
            v.content_hash AS source_content_hash,
            EXISTS (SELECT 1 FROM literature_source_project_links pl
              WHERE pl.literature_source_id=v.literature_source_id
                AND pl.project_id=:project
                AND EXISTS (SELECT 1 FROM literature_sources ls
                  WHERE ls.id=v.literature_source_id)
                AND EXISTS (SELECT 1 FROM artifact_versions av
                  JOIN artifacts a ON a.id=av.artifact_id
                  WHERE av.id=v.fulltext_artifact_version_id AND a.project_id=:project)
                AND (v.correction_basis_artifact_version_id IS NULL OR EXISTS (
                  SELECT 1 FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id
                  WHERE av.id=v.correction_basis_artifact_version_id))
                AND (v.predecessor_source_version_id IS NULL OR EXISTS (
                  SELECT 1 FROM source_versions predecessor
                  WHERE predecessor.id=v.predecessor_source_version_id
                    AND predecessor.literature_source_id=v.literature_source_id))
              ) AS source_project_match,
            rev.id AS review_event_id,rev.new_status AS review_event_status
          FROM links l
          LEFT JOIN literature_evidence e ON e.id=l.evidence_id
          LEFT JOIN source_versions v ON v.id=e.source_version_id
          LEFT JOIN LATERAL (
            SELECT id,new_status FROM literature_evidence_review_events
              WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1
          ) rev ON true
          ORDER BY l.link_kind,l.owner_version_id,l.snapshot_id,l.ordinal,l.evidence_id
        """),
                {"manuscript": manuscript, "project": project},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def scientific_trace_snapshot_closure(self, manuscript: UUID):
        """Retain selected exact snapshots, predecessor edges and empty memberships."""
        return [
            dict(row)
            for row in self._session.execute(
                text("""
          WITH RECURSIVE selected(id) AS (
            SELECT i.literature_support_snapshot_id
            FROM manuscript_claim_placements p
            JOIN scientific_conclusion_claim_inputs i
              ON i.conclusion_version_id=p.scientific_conclusion_version_id
            WHERE p.manuscript_version_id=:manuscript
              AND i.literature_support_snapshot_id IS NOT NULL
            UNION
            SELECT s.previous_snapshot_id FROM selected t
            JOIN literature_support_snapshots s ON s.id=t.id
            WHERE s.previous_snapshot_id IS NOT NULL
          )
          SELECT t.id AS selected_id,s.*,
            cv.content_hash AS target_hash,cv.status AS target_status,
            cv.frozen_at AS target_frozen_at,c.project_id AS target_project,
            r.id AS relation_id,r.literature_evidence_id,r.relation_type,
            r.ordinal,r.qualification,e.content_hash AS evidence_hash,
            e.project_id AS evidence_project,v.id AS source_id,
            ls.id AS source_owner_id,av.id AS source_artifact_id,
            a.project_id AS source_artifact_project,
            v.predecessor_source_version_id AS selected_predecessor_id,
            predecessor.id AS resolved_predecessor_id,
            v.correction_basis_artifact_version_id AS selected_correction_artifact_id,
            correction.id AS resolved_correction_artifact_id,
            correction_owner.id AS correction_artifact_owner_id
          FROM selected t LEFT JOIN literature_support_snapshots s ON s.id=t.id
          LEFT JOIN claim_versions cv ON cv.id=s.claim_version_id
          LEFT JOIN claims c ON c.id=cv.claim_id
          LEFT JOIN literature_evidence_relations r ON r.literature_support_snapshot_id=s.id
          LEFT JOIN literature_evidence e ON e.id=r.literature_evidence_id
          LEFT JOIN source_versions v ON v.id=e.source_version_id
          LEFT JOIN source_versions predecessor
            ON predecessor.id=v.predecessor_source_version_id
              AND predecessor.literature_source_id=v.literature_source_id
          LEFT JOIN artifact_versions correction
            ON correction.id=v.correction_basis_artifact_version_id
          LEFT JOIN artifacts correction_owner ON correction_owner.id=correction.artifact_id
          LEFT JOIN literature_sources ls ON ls.id=v.literature_source_id
          LEFT JOIN artifact_versions av ON av.id=v.fulltext_artifact_version_id
          LEFT JOIN artifacts a ON a.id=av.artifact_id
          ORDER BY t.id,r.ordinal,r.id
        """),
                {"manuscript": manuscript},
            ).mappings()
        ]

    def scientific_trace_conclusions(self, manuscript: UUID):
        return [
            dict(row)
            for row in self._session.execute(
                text("""
            SELECT DISTINCT v.* FROM manuscript_claim_placements p
            JOIN scientific_conclusion_versions v ON v.id=p.scientific_conclusion_version_id
            WHERE p.manuscript_version_id=:manuscript
            ORDER BY v.id
        """),
                {"manuscript": manuscript},
            ).mappings()
        ]

    def prepare_entry_write(self) -> None:
        self._session.execute(text(B14A_SHARE_SQL))
        self._session.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        self._session.execute(
            text(
                "LOCK TABLE "
                "approval_decisions,approval_request_reviews,approval_requests IN SHARE "
                "MODE"
            )
        )
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def lock_entry_target(self, identity: UUID) -> None:
        self._session.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"), {"id": identity}
        )

    def entry_event(self, identity: UUID) -> dict | None:
        row = (
            self._session.execute(
                text(
                    "SELECT e.*,p.project_id FROM publication_lifecycle_events e JOIN "
                    "publications p ON p.id=e.publication_id WHERE e.id=:id"
                ),
                {"id": identity},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def initial_events(self, publication: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM publication_lifecycle_events WHERE publication_id=:id AND "
                    "prior_status IS NULL ORDER BY id"
                ),
                {"id": publication},
            ).mappings()
        ]

    def entry_events(self, publication: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM publication_lifecycle_events WHERE publication_id=:id AND "
                    "new_status='INTERNAL_REVIEW' ORDER BY id"
                ),
                {"id": publication},
            ).mappings()
        ]

    def publication_exists(self, identity: UUID) -> bool:
        return bool(
            self._session.execute(
                text("SELECT EXISTS(SELECT 1 FROM publications WHERE id=:id)"), {"id": identity}
            ).scalar_one()
        )

    def transition_entry(self, parent: dict, values: dict) -> bool:
        changed = self._session.execute(
            text(
                "UPDATE publications SET "
                "lifecycle_status='INTERNAL_REVIEW',row_version=row_version+1 WHERE "
                "id=:id AND row_version=:version AND lifecycle_status='DRAFTING' "
                "RETURNING id"
            ),
            {"id": parent["id"], "version": parent["row_version"]},
        ).scalar_one_or_none()
        if changed is None:
            return False
        self._session.execute(
            text(
                "INSERT INTO publication_lifecycle_events "
                "(id,publication_id,prior_status,new_status,actor_id,occurred_at,manuscri"
                "pt_version_id,basis_decision_id,basis_grant_consumption_id) VALUES "
                "(:id,:publication_id,'DRAFTING','INTERNAL_REVIEW',:actor_id,:occurred_at"
                ",:manuscript_version_id,NULL,NULL)"
            ),
            values,
        )
        return True

    def force_entry_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    def entry_creation_authorized(self, row: dict) -> bool:
        return bool(
            self._session.execute(
                text("""SELECT EXISTS(
          SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
          JOIN project_role_assignments r ON r.membership_id=m.id
           AND r.project_id=m.project_id AND r.actor_id=m.actor_id
          WHERE a.id=:actor AND a.created_at<=:at AND (a.retired_at IS NULL OR :at<a.retired_at)
           AND m.project_id=:project AND m.started_at<=:at
           AND (SELECT e.new_status FROM project_membership_events e
            WHERE e.membership_id=m.id AND e.occurred_at<=:at
            ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
           AND r.role IN ('OWNER','RESEARCHER') AND r.effective_from<=:at
           AND (r.effective_until IS NULL OR :at<r.effective_until)
           AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
            AND b.bound_at<=:at AND (b.revoked_at IS NULL OR :at<b.revoked_at)))"""),
                {"actor": row["actor_id"], "project": row["project_id"], "at": row["occurred_at"]},
            ).scalar_one()
        )

    def ready_event(self, consumption):
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM publication_lifecycle_events "
                    "WHERE basis_grant_consumption_id=:id"
                ),
                {"id": consumption},
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else dict(row)

    def transition_ready(self, publication, values):
        changed = self._session.execute(
            text(
                "UPDATE publications SET lifecycle_status='READY',row_version=row_version+1 "
                "WHERE id=:id AND lifecycle_status='INTERNAL_REVIEW' "
                "AND row_version<2147483647 RETURNING id"
            ),
            {"id": publication},
        ).scalar_one_or_none()
        if changed is None:
            from researchbase.foundation.errors import ErrorCode, ResearchBaseError

            raise ResearchBaseError(ErrorCode.APPROVAL_GATE_FAILED, "publication must be in review")
        self._session.execute(
            text(
                "INSERT INTO publication_lifecycle_events "
                "(id,publication_id,prior_status,new_status,"
                "actor_id,occurred_at,basis_decision_id,basis_grant_consumption_id) "
                "VALUES (:id,:publication_id,'INTERNAL_REVIEW','READY',:actor_id,:occurred_at,"
                ":basis_decision_id,:basis_grant_consumption_id)"
            ),
            values,
        )
