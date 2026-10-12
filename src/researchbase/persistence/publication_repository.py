"""Project-confined SQL for the PR2-12 draft publication slice."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlAlchemyPublicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_request(self, key: str) -> None:
        self._session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                              {"key": key})

    def publication(self, identity: UUID, project: UUID, *, lock: bool = False):
        suffix = " FOR UPDATE" if lock else ""
        row = self._session.execute(text("""SELECT * FROM publications
          WHERE id=:id AND project_id=:project""" + suffix),
          {"id": identity, "project": project}).mappings().first()
        return dict(row) if row else None

    def version(self, identity: UUID, publication: UUID):
        row = self._session.execute(text("""SELECT * FROM manuscript_versions
          WHERE id=:id AND publication_id=:publication"""),
          {"id": identity, "publication": publication}).mappings().first()
        return dict(row) if row else None

    def initial_version(self, publication: UUID):
        return self._session.execute(text("""SELECT id FROM manuscript_versions
          WHERE publication_id=:publication AND version_number=1"""),
          {"publication": publication}).scalar_one_or_none()

    def document(self, identity: UUID, project: UUID):
        row = self._session.execute(text("""SELECT v.id,v.status,v.frozen_at,
          v.content_hash,v.byte_size,a.artifact_type,a.project_id
          FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=:id AND a.project_id=:project FOR SHARE OF v,a"""),
          {"id": identity, "project": project}).mappings().first()
        return dict(row) if row else None

    def insert_publication(self, values: dict[str, object]) -> None:
        self._session.execute(text("""INSERT INTO publications
          (id,project_id,publication_type,title,lifecycle_status,
           current_manuscript_version_id,created_by,created_at,row_version)
          VALUES (:id,:project_id,:publication_type,:title,:lifecycle_status,
                  :current_manuscript_version_id,:created_by,:created_at,:row_version)"""), values)

    def insert_initial_event(self, values: dict[str, object]) -> None:
        self._session.execute(text("""INSERT INTO publication_lifecycle_events
          (id,publication_id,prior_status,new_status,actor_id,occurred_at)
          VALUES (:id,:publication_id,NULL,'DRAFTING',:actor_id,:occurred_at)"""), values)

    def insert_version(self, values: dict[str, object]) -> None:
        self._session.execute(text("""INSERT INTO manuscript_versions
          (id,publication_id,version_number,status,document_artifact_version_id,
           title,abstract,semantic_change_class,placement_set_hash,content_hash,hash_scheme,
           created_by,created_at,frozen_at,row_version)
          VALUES (:id,:publication_id,:version_number,:status,:document_artifact_version_id,
                  :title,:abstract,:semantic_change_class,:placement_set_hash,:content_hash,
                  :hash_scheme,
                  :created_by,:created_at,:frozen_at,:row_version)"""), values)

    def citation_source(self, identity: UUID, project: UUID):
        row = self._session.execute(text("""SELECT v.id,v.status,v.frozen_at,v.content_hash
          FROM source_versions v JOIN literature_source_project_links l
            ON l.literature_source_id=v.literature_source_id
          WHERE v.id=:id AND l.project_id=:project FOR SHARE OF v,l"""),
          {"id": identity, "project": project}).mappings().first()
        return dict(row) if row else None

    def insert_citation(self, values: dict[str, object]) -> None:
        self._session.execute(text("""INSERT INTO manuscript_citation_placements
          (id,manuscript_version_id,source_version_id,section_id,locator,
           citation_purpose,ordinal,created_by,created_at,row_version)
          VALUES (:id,:manuscript_version_id,:source_version_id,:section_id,
                  CAST(:locator AS jsonb),:citation_purpose,:ordinal,:created_by,
                  :created_at,:row_version)"""), values)

    def citation(self, identity: UUID, manuscript: UUID):
        row = self._session.execute(text("""SELECT * FROM manuscript_citation_placements
          WHERE id=:id AND manuscript_version_id=:manuscript"""),
          {"id": identity, "manuscript": manuscript}).mappings().first()
        return dict(row) if row else None

    def citations(self, manuscript: UUID):
        rows = self._session.execute(text("""SELECT * FROM manuscript_citation_placements
          WHERE manuscript_version_id=:manuscript ORDER BY section_id,ordinal,id"""),
          {"manuscript": manuscript}).mappings().all()
        return [dict(row) for row in rows]

    def claim_placement_target(self, identity: UUID, project: UUID, *, conclusion: bool):
        if conclusion:
            query = """SELECT v.id,v.status,v.frozen_at,v.content_hash,v.support_set_hash
              FROM scientific_conclusion_versions v JOIN scientific_conclusions c
                ON c.id=v.scientific_conclusion_id
              WHERE v.id=:id AND c.project_id=:project FOR SHARE OF v,c"""
        else:
            query = """SELECT v.id,v.status,v.frozen_at,v.content_hash
              FROM claim_versions v JOIN claims c ON c.id=v.claim_id
              WHERE v.id=:id AND c.project_id=:project FOR SHARE OF v,c"""
        row = self._session.execute(text(query), {"id": identity, "project": project})\
            .mappings().first()
        return dict(row) if row else None

    def insert_claim_placement(self, values: dict[str, object]) -> None:
        self._session.execute(text("""INSERT INTO manuscript_claim_placements
          (id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,
           section_id,locator,rhetorical_strength,ordinal,created_by,created_at,row_version)
          VALUES (:id,:manuscript_version_id,:claim_version_id,
                  :scientific_conclusion_version_id,:section_id,CAST(:locator AS jsonb),
                  :rhetorical_strength,:ordinal,:created_by,:created_at,:row_version)"""),
          values)

    def claim_placement(self, identity: UUID, manuscript: UUID):
        row = self._session.execute(text("""SELECT * FROM manuscript_claim_placements
          WHERE id=:id AND manuscript_version_id=:manuscript"""),
          {"id": identity, "manuscript": manuscript}).mappings().first()
        return dict(row) if row else None

    def claim_placements(self, manuscript: UUID):
        rows = self._session.execute(text("""SELECT * FROM manuscript_claim_placements
          WHERE manuscript_version_id=:manuscript ORDER BY section_id,ordinal,id"""),
          {"manuscript": manuscript}).mappings().all()
        return [dict(row) for row in rows]

    def artifact_placement_target(self, identity: UUID, project: UUID):
        row = self._session.execute(text("""SELECT v.id,v.status,v.frozen_at,v.content_hash,
          a.artifact_type FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=:id AND a.project_id=:project FOR SHARE OF v,a"""),
          {"id": identity, "project": project}).mappings().first()
        return dict(row) if row else None

    def insert_artifact_placement(self, values: dict[str, object]) -> None:
        self._session.execute(text("""INSERT INTO manuscript_artifact_placements
          (id,manuscript_version_id,artifact_version_id,section_id,locator,
           artifact_role,ordinal,created_by,created_at,row_version)
          VALUES (:id,:manuscript_version_id,:artifact_version_id,:section_id,
                  CAST(:locator AS jsonb),:artifact_role,:ordinal,:created_by,
                  :created_at,:row_version)"""), values)

    def artifact_placement(self, identity: UUID, manuscript: UUID):
        row = self._session.execute(text("""SELECT * FROM manuscript_artifact_placements
          WHERE id=:id AND manuscript_version_id=:manuscript"""),
          {"id": identity, "manuscript": manuscript}).mappings().first()
        return dict(row) if row else None

    def artifact_placements(self, manuscript: UUID):
        rows = self._session.execute(text("""SELECT * FROM manuscript_artifact_placements
          WHERE manuscript_version_id=:manuscript ORDER BY section_id,ordinal,id"""),
          {"manuscript": manuscript}).mappings().all()
        return [dict(row) for row in rows]

    def begin_scientific_trace_snapshot(self) -> None:
        """Use one stable PostgreSQL snapshot for authorization and all trace reads."""
        self._session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

    def scientific_trace_placements(self, manuscript: UUID, project: UUID):
        rows = self._session.execute(text("""
          SELECT 'CITATION'::text AS placement_kind,p.id AS placement_id,
            p.source_version_id AS target_id,p.section_id,p.locator,p.ordinal,
            p.citation_purpose AS annotation,v.status AS target_status,
            v.frozen_at AS target_frozen_at,v.content_hash AS target_hash,
            NULL::text AS support_hash,
            EXISTS (SELECT 1 FROM literature_source_project_links l
              WHERE l.literature_source_id=v.literature_source_id
                AND l.project_id=:project) AS project_match
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
        """), {"manuscript": manuscript, "project": project}).mappings().all()
        return [dict(row) for row in rows]

    def scientific_trace_conclusion_claim_inputs(self, manuscript: UUID):
        rows = self._session.execute(text("""
          SELECT p.scientific_conclusion_version_id AS conclusion_version_id,
            i.claim_version_id,i.literature_support_snapshot_id,
            i.relation_type,i.ordinal,v.status AS claim_status,
            v.frozen_at AS claim_frozen_at,v.content_hash AS claim_content_hash,
            c.project_id AS claim_project_id
          FROM manuscript_claim_placements p
          JOIN scientific_conclusion_claim_inputs i
            ON i.conclusion_version_id=p.scientific_conclusion_version_id
          LEFT JOIN claim_versions v ON v.id=i.claim_version_id
          LEFT JOIN claims c ON c.id=v.claim_id
          WHERE p.manuscript_version_id=:manuscript
          ORDER BY p.scientific_conclusion_version_id,i.ordinal,i.claim_version_id
        """), {"manuscript": manuscript}).mappings().all()
        return [dict(row) for row in rows]

    def scientific_trace_claim_experiment_evidence(self, manuscript: UUID):
        rows = self._session.execute(text("""
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
            r.statistical_result_id,
            COALESCE(dm.id,sm.id) AS measurement_id,
            COALESCE(dm.run_id,sm.run_id) AS run_id,
            COALESCE(dr.project_id,sr.project_id) AS run_project_id,
            si.input_role,si.ordinal AS input_ordinal
          FROM trace_claims t JOIN evidence_relations r ON r.claim_version_id=t.id
          LEFT JOIN measurements dm ON dm.id=r.measurement_id
          LEFT JOIN statistical_result_inputs si
            ON si.statistical_result_id=r.statistical_result_id
          LEFT JOIN measurements sm ON sm.id=si.measurement_id
          LEFT JOIN runs dr ON dr.id=dm.run_id
          LEFT JOIN runs sr ON sr.id=sm.run_id
          ORDER BY t.id,r.id,si.ordinal,si.measurement_id
        """), {"manuscript": manuscript}).mappings().all()
        return [dict(row) for row in rows]

    def scientific_trace_literature_evidence(self, manuscript: UUID, project: UUID):
        rows = self._session.execute(text("""
          WITH trace_claims AS (
            SELECT claim_version_id AS id FROM manuscript_claim_placements
              WHERE manuscript_version_id=:manuscript AND claim_version_id IS NOT NULL
            UNION
            SELECT i.claim_version_id AS id FROM manuscript_claim_placements p
              JOIN scientific_conclusion_claim_inputs i
                ON i.conclusion_version_id=p.scientific_conclusion_version_id
              WHERE p.manuscript_version_id=:manuscript
          ), links AS (
            SELECT 'CONCLUSION_INPUT'::text AS link_kind,
              i.conclusion_version_id AS owner_version_id,
              NULL::uuid AS snapshot_id,NULL::uuid AS relation_id,
              NULL::uuid AS snapshot_project_id,
              i.literature_evidence_id AS evidence_id,i.relation_type,i.ordinal
            FROM manuscript_claim_placements p
            JOIN scientific_conclusion_literature_inputs i
              ON i.conclusion_version_id=p.scientific_conclusion_version_id
            WHERE p.manuscript_version_id=:manuscript
            UNION ALL
            SELECT 'CLAIM_SNAPSHOT',s.claim_version_id,s.id,r.id,s.project_id,
              r.literature_evidence_id,r.relation_type,r.ordinal
            FROM trace_claims t
            JOIN literature_support_snapshots s ON s.claim_version_id=t.id
            JOIN literature_evidence_relations r ON r.literature_support_snapshot_id=s.id
          )
          SELECT l.link_kind,l.owner_version_id,l.snapshot_id,l.relation_id,
            l.snapshot_project_id,
            l.evidence_id,l.relation_type,l.ordinal,
            e.project_id AS evidence_project_id,e.source_version_id,
            e.review_status,e.content_hash AS evidence_content_hash,
            v.status AS source_status,v.frozen_at AS source_frozen_at,
            v.content_hash AS source_content_hash,
            EXISTS (SELECT 1 FROM literature_source_project_links pl
              WHERE pl.literature_source_id=v.literature_source_id
                AND pl.project_id=:project) AS source_project_match,
            rev.id AS review_event_id,rev.new_status AS review_event_status
          FROM links l
          LEFT JOIN literature_evidence e ON e.id=l.evidence_id
          LEFT JOIN source_versions v ON v.id=e.source_version_id
          LEFT JOIN LATERAL (
            SELECT id,new_status FROM literature_evidence_review_events
              WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1
          ) rev ON true
          ORDER BY l.link_kind,l.owner_version_id,l.snapshot_id,l.ordinal,l.evidence_id
        """), {"manuscript": manuscript, "project": project}).mappings().all()
        return [dict(row) for row in rows]
