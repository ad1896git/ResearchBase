"""Narrow PostgreSQL adapter for immutable PR2-14 initial reviews."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlAlchemyInternalReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_request(self, identity: UUID) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr214:review:{identity}"},
        )

    def review(self, identity: UUID, project: UUID) -> dict | None:
        row = (
            self._session.execute(
                text("""SELECT * FROM internal_review_records
          WHERE id=:id AND project_id=:project"""),
                {"id": identity, "project": project},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def conclusion_target(self, identity: UUID, project: UUID,
                          *, lock: bool = False) -> dict | None:
        if lock:
            # Lock exact target before the parent; a joined locking query cannot
            # guarantee that order. The subsequent statement rereads after waits.
            self._session.execute(text("""SELECT id FROM scientific_conclusion_versions
              WHERE id=:id FOR UPDATE"""), {"id": identity}).one_or_none()
        suffix = " FOR UPDATE OF c" if lock else ""
        row = self._session.execute(text("""SELECT v.id,v.scientific_conclusion_id,
          v.status,v.frozen_at,v.content_hash,v.created_by
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=:id AND c.project_id=:project""" + suffix),
          {"id": identity, "project": project}).mappings().one_or_none()
        return dict(row) if row else None

    def issues(self, identity: UUID) -> list[dict]:
        rows = (
            self._session.execute(
                text("""SELECT * FROM review_issues
          WHERE review_record_id=:id ORDER BY ordinal,id"""),
                {"id": identity},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def insert_review(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO internal_review_records
          (id,project_id,claim_version_id,scientific_conclusion_version_id,
           target_content_hash,reviewer_actor_id,
           review_type,recommendation,summary,created_at,content_hash,hash_scheme)
          VALUES (:id,:project_id,:claim_version_id,:scientific_conclusion_version_id,
           :target_content_hash,
           :reviewer_actor_id,:review_type,:recommendation,:summary,:created_at,
           :content_hash,:hash_scheme)"""),
            values,
        )

    def insert_issue(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO review_issues
          (id,review_record_id,severity,issue_type,target_locator,description,
           related_claim_version_id,related_source_version_id,related_run_id,
           status,created_at,ordinal)
          VALUES (:id,:review_record_id,:severity,:issue_type,NULL,:description,
            NULL,NULL,NULL,'OPEN',:created_at,:ordinal)"""),
            values,
        )
