"""Read-only project listings for the terminal record flow.

Rows are ordered by creation time, so a short number (1, 2, 3, ...) is the
record's position in its project and kind. Nothing is stored for it; the
number is recomputed on each read, which is stable because records are never
deleted.
"""

from __future__ import annotations

from sqlalchemy import text

# kind -> SQL returning id, title, status, created_at, and optional extras.
# Titles come from the current version. Every query takes :project.
_QUERIES: dict[str, str] = {
    "question": """
        SELECT r.id, v.question_text AS title, v.status, r.created_at,
               NULL::text AS parent_id
        FROM research_questions r
        LEFT JOIN research_question_versions v ON v.id = r.current_version_id
        WHERE r.project_id = :project
    """,
    "hypothesis": """
        SELECT h.id, v.statement AS title, v.status, h.created_at,
               h.research_question_id::text AS parent_id
        FROM hypotheses h
        LEFT JOIN hypothesis_versions v ON v.id = h.current_version_id
        WHERE h.project_id = :project
    """,
    "experiment": """
        SELECT e.id, v.title AS title, v.status, e.created_at,
               e.hypothesis_id::text AS parent_id
        FROM experiment_specs e
        LEFT JOIN experiment_spec_versions v ON v.id = e.current_version_id
        WHERE e.project_id = :project
    """,
    "run": """
        SELECT r.id, r.run_type AS title, r.status, r.created_at,
               r.experiment_spec_version_id::text AS parent_id
        FROM runs r
        WHERE r.project_id = :project
    """,
    "claim": """
        SELECT c.id, v.statement AS title, v.status, c.created_at,
               c.current_version_id::text AS parent_id
        FROM claims c
        LEFT JOIN claim_versions v ON v.id = c.current_version_id
        WHERE c.project_id = :project
    """,
    "paper": """
        SELECT s.id, s.canonical_title AS title, s.lifecycle_status AS status,
               l.linked_at AS created_at, s.current_version_id::text AS parent_id
        FROM literature_source_project_links l
        JOIN literature_sources s ON s.id = l.literature_source_id
        WHERE l.project_id = :project
    """,
    "evidence": """
        SELECT e.id, e.extracted_statement AS title, e.review_status AS status,
               e.created_at, e.source_version_id::text AS parent_id
        FROM literature_evidence e
        WHERE e.project_id = :project
    """,
}

KINDS = tuple(_QUERIES)


class SqlAlchemyRecordListingRepository:
    def __init__(self, session):
        self._session = session

    def rows(self, kind: str, project) -> list[dict]:
        if kind not in _QUERIES:
            raise ValueError(f"unknown record kind: {kind}")
        result = self._session.execute(
            text(_QUERIES[kind] + " ORDER BY created_at, id"), {"project": project}
        )
        return [dict(row) for row in result.mappings()]

    def paper_detail(self, source_id, project) -> dict | None:
        """Frozen source version and full-text artifact behind a linked paper."""
        row = (
            self._session.execute(
                text(
                    """
                    SELECT sv.id AS source_version_id,
                           sv.fulltext_artifact_version_id AS artifact_version_id
                    FROM literature_sources s
                    JOIN literature_source_project_links l
                      ON l.literature_source_id = s.id AND l.project_id = :project
                    LEFT JOIN source_versions sv ON sv.id = s.current_version_id
                    WHERE s.id = :source
                    """
                ),
                {"source": source_id, "project": project},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None
