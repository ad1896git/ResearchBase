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
