"""Lock-free gateway keyset query, executed in the caller's formal snapshot."""

from sqlalchemy import text

INVOCATION_PAGE_SQL = """
SELECT * FROM capability_invocations
WHERE project_id=:project AND research_task_id=:task
  AND (CAST(:after_at AS timestamptz) IS NULL OR
       (created_at,id) > (CAST(:after_at AS timestamptz),CAST(:after_id AS uuid)))
ORDER BY created_at,id
LIMIT :fetch_limit
"""


def invocation_page(session, project, task, limit, after_at, after_id):
    return [
        dict(row)
        for row in session.execute(
            text(INVOCATION_PAGE_SQL),
            {
                "project": project,
                "task": task,
                "after_at": after_at,
                "after_id": after_id,
                "fetch_limit": limit + 1,
            },
        ).mappings()
    ]
