# PR-02 Migration Report

## Revision

- Starting revision: `0002_actor_project_workspace (head)`
- Previous revision: `0001_empty`
- Target revision: `0002_actor_project_workspace (head)`
- PostgreSQL: 18.6 on aarch64 Alpine, healthy `postgres:18-alpine`

## Fresh command results

```text
uv run alembic current
0002_actor_project_workspace (head)

uv run alembic downgrade 0001_empty
Running downgrade 0002_actor_project_workspace -> 0001_empty: PASS

uv run alembic upgrade head
Running upgrade 0001_empty -> 0002_actor_project_workspace: PASS

uv run alembic current
0002_actor_project_workspace (head)
```

The downgrade order removes `workspaces`, then `projects`, then the Actor external-key index and
`actors`, respecting foreign keys. No step was skipped and no irreversible migration note is
required for this revision.
