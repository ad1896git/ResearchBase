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
               NULL::text AS parent_id, r.current_version_id::text AS version_id,
               r.row_version
        FROM research_questions r
        LEFT JOIN research_question_versions v ON v.id = r.current_version_id
        WHERE r.project_id = :project
    """,
    "hypothesis": """
        SELECT h.id, v.statement AS title, v.status, h.created_at,
               h.research_question_id::text AS parent_id,
               h.current_version_id::text AS version_id, h.row_version
        FROM hypotheses h
        LEFT JOIN hypothesis_versions v ON v.id = h.current_version_id
        WHERE h.project_id = :project
    """,
    "experiment": """
        SELECT e.id, v.title AS title, v.status, e.created_at,
               e.hypothesis_id::text AS parent_id,
               e.current_version_id::text AS version_id, e.row_version
        FROM experiment_specs e
        LEFT JOIN experiment_spec_versions v ON v.id = e.current_version_id
        WHERE e.project_id = :project
    """,
    "run": """
        SELECT r.id, r.run_type AS title, r.status, r.created_at,
               r.experiment_spec_version_id::text AS parent_id,
               NULL::text AS version_id, r.row_version
        FROM runs r
        WHERE r.project_id = :project
    """,
    "metric": """
        SELECT m.id, m.name AS title, v.status, m.created_at,
               NULL::text AS parent_id, m.current_version_id::text AS version_id,
               m.row_version
        FROM metric_definitions m
        LEFT JOIN metric_definition_versions v ON v.id = m.current_version_id
        WHERE m.project_id = :project
    """,
    "result": """
        SELECT ms.id,
               (ms.numeric_value::text || COALESCE(' ' || ms.unit, '')) AS title,
               'RECORDED' AS status, ms.created_at,
               ms.run_id::text AS parent_id,
               ms.metric_definition_version_id::text AS version_id, NULL::int AS row_version
        FROM measurements ms
        JOIN runs r ON r.id = ms.run_id
        WHERE r.project_id = :project
    """,
    "claim": """
        SELECT c.id, v.statement AS title, v.status, c.created_at,
               NULL::text AS parent_id, c.current_version_id::text AS version_id,
               c.row_version, v.row_version AS version_row_version
        FROM claims c
        LEFT JOIN claim_versions v ON v.id = c.current_version_id
        WHERE c.project_id = :project
    """,
    "paper": """
        SELECT s.id, COALESCE(cv.title, s.canonical_title) AS title,
               s.lifecycle_status AS status,
               l.linked_at AS created_at, NULL::text AS parent_id,
               s.current_version_id::text AS version_id, s.row_version
        FROM literature_source_project_links l
        JOIN literature_sources s ON s.id = l.literature_source_id
        LEFT JOIN source_versions cv ON cv.id = s.current_version_id
        WHERE l.project_id = :project
    """,
    # Corrections are appended records; parent_id is "<target_type>:<target id>"
    # so the export can attach each one to the conclusion or result it corrects.
    "correction": """
        SELECT c.id, (c.corrected_assertion #>> '{}') AS title,
               c.correction_type AS status, c.created_at,
               (lower(c.target_type) || ':' || c.target_id::text) AS parent_id,
               NULL::text AS version_id, NULL::int AS row_version,
               c.reason AS reason
        FROM correction_records c
        WHERE c.project_id = :project
    """,
    "evidence": """
        SELECT e.id, e.extracted_statement AS title, e.review_status AS status,
               e.created_at, e.source_version_id::text AS parent_id,
               NULL::text AS version_id, NULL::int AS row_version,
               (SELECT re.reviewed_by = e.created_by
                  FROM literature_evidence_review_events re
                 WHERE re.literature_evidence_id = e.id AND re.new_status = 'VERIFIED'
                 ORDER BY re.reviewed_at DESC, re.id DESC LIMIT 1) AS self_verified
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

    def claim_links(self, project) -> list[dict]:
        """Evidence links on claim versions: measurements, statistical results, literature."""
        result = self._session.execute(
            text(
                """
                SELECT cv.id::text AS claim_version_id, 'measurement' AS kind,
                       er.measurement_id::text AS target_id,
                       er.relation_type, er.qualification
                FROM evidence_relations er
                JOIN claim_versions cv ON cv.id = er.claim_version_id
                JOIN claims c ON c.id = cv.claim_id
                WHERE c.project_id = :project AND er.measurement_id IS NOT NULL
                UNION ALL
                SELECT cv.id::text, 'statistical', er.statistical_result_id::text,
                       er.relation_type, er.qualification
                FROM evidence_relations er
                JOIN claim_versions cv ON cv.id = er.claim_version_id
                JOIN claims c ON c.id = cv.claim_id
                WHERE c.project_id = :project AND er.statistical_result_id IS NOT NULL
                UNION ALL
                SELECT s.claim_version_id::text, 'literature', rel.literature_evidence_id::text,
                       rel.relation_type, rel.qualification
                FROM literature_evidence_relations rel
                JOIN literature_support_snapshots s
                  ON s.id = rel.literature_support_snapshot_id
                WHERE s.project_id = :project
                """
            ),
            {"project": project},
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
