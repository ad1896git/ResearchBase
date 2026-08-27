# PR-04 Schema Summary

Alembic revision `0003_research_question_hypothesis` creates exactly four tables:

| Table | Purpose |
|---|---|
| `research_questions` | Project-scoped ResearchQuestion identity and current version pointer. |
| `research_question_versions` | Parent-local version material, lifecycle status, hash, and row version. |
| `hypotheses` | Project-scoped Hypothesis identity, optional same-project question link, and current pointer. |
| `hypothesis_versions` | Parent-local Hypothesis version material, lifecycle status, hash, and row version. |

All IDs use PostgreSQL UUID; timestamps use timezone-aware timestamps; JSON material uses JSONB; hashes use CHAR(64). Parent/version uniqueness and positive version-number checks are present. All foreign keys use `ON DELETE RESTRICT`, including the current pointers. The cyclic current-pointer foreign keys are added after the identity/version tables are created.

No generic `versions` table and no PR-05 tables were added. Real PostgreSQL schema assertions passed.
