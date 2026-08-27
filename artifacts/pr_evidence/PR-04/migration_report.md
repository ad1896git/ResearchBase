# PR-04 Migration Report

| Operation | Result |
|---|---|
| `0002_actor_project_workspace -> 0003_research_question_hypothesis` | PASS |
| `0003 -> 0002` | PASS; four PR-04 tables removed |
| `0002 -> 0003` after downgrade | PASS |
| final `alembic current` | PASS; `0003_research_question_hypothesis (head)` |

The requested revision identifier is longer than Alembic's default 32-character version column. The migration transactionally widens `alembic_version.version_num` to 64 characters before recording the new revision; this is retained on downgrade so Alembic can first record the shorter `0002` revision safely. This is compatibility plumbing only and does not add a ResearchBase domain table.

The migration is PostgreSQL-only for the required UUID, TIMESTAMPTZ, JSONB, and FK behavior. SQLite was not used.
