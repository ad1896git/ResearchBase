# PR-02 Schema Summary

## Migration

Revision `0002_actor_project_workspace` upgrades from `0001_empty` and creates exactly these
business tables:

### `actors`

- `id UUID PRIMARY KEY`
- `actor_type VARCHAR(16) NOT NULL`
- `display_name VARCHAR(200) NOT NULL`
- `external_key VARCHAR(255) NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `retired_at TIMESTAMPTZ NULL`
- `row_version INTEGER NOT NULL DEFAULT 1`
- CHECK `actor_type IN ('human', 'agent', 'service')`
- partial unique index `uq_actors_external_key (external_key)` where `external_key IS NOT NULL`

### `projects`

- `id UUID PRIMARY KEY`
- `name VARCHAR(255) NOT NULL`
- `description TEXT NULL`
- `lifecycle_status VARCHAR(20) NOT NULL DEFAULT 'active'`
- CHECK `lifecycle_status IN ('active', 'archived', 'retired')`
- `created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT`
- `created_at TIMESTAMPTZ NOT NULL`
- `row_version INTEGER NOT NULL DEFAULT 1`

### `workspaces`

- `id UUID PRIMARY KEY`
- `project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT`
- `name VARCHAR(255) NOT NULL`
- `locator TEXT NULL`
- `lifecycle_status VARCHAR(20) NOT NULL DEFAULT 'active'`
- CHECK `lifecycle_status IN ('active', 'archived', 'retired')`
- `created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT`
- `created_at TIMESTAMPTZ NOT NULL`
- `row_version INTEGER NOT NULL DEFAULT 1`
- unique constraint `uq_workspaces_project_name (project_id, name)`

## Live PostgreSQL verification

The live database contained only `actors`, `projects`, `workspaces`, and `alembic_version` after
the migration round-trip. Information-schema inspection confirmed UUID columns, TIMESTAMPTZ
columns, non-null/default row versions, CHECK constraints, the partial unique index, and
`RESTRICT` foreign-key delete rules.

VERSION TABLES ADDED: NO
SCIENTIFIC DOMAIN TABLES ADDED: NO
ON DELETE CASCADE ON SCIENTIFIC HISTORY: NO
