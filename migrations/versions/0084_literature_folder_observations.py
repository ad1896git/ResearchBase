"""Literature folder observations: append-only scan records for a local PDF/text folder.

Each scan appends one PRESENT row per file it found and one MISSING row per file
that a previous scan saw but this scan did not. Nothing is updated or deleted;
current status and moves are derived by reading the history.
"""

# ruff: noqa: E501
from alembic import op

revision = "0084_literature_folder_observations"
down_revision = "0083_bearing_evaluation_guards"
branch_labels = None
depends_on = None

_UPGRADE = r"""
CREATE TABLE literature_folder_observations (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id),
    scan_id uuid NOT NULL,
    folder_path text NOT NULL CHECK (char_length(folder_path) BETWEEN 1 AND 4096),
    file_path text NOT NULL CHECK (char_length(file_path) BETWEEN 1 AND 4096),
    observation_status text NOT NULL CHECK (observation_status IN ('PRESENT', 'MISSING')),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
    file_mtime timestamptz NOT NULL,
    title text CHECK (title IS NULL OR char_length(title) BETWEEN 1 AND 1024),
    doi text CHECK (doi IS NULL OR char_length(doi) BETWEEN 1 AND 512),
    observed_by uuid NOT NULL REFERENCES actors(id),
    request_id uuid NOT NULL,
    observed_at timestamptz NOT NULL,
    CONSTRAINT uq_literature_folder_scan_file UNIQUE (scan_id, folder_path, file_path)
);
CREATE INDEX ix_literature_folder_project_path_time
    ON literature_folder_observations (project_id, folder_path, file_path, observed_at);
CREATE FUNCTION literature_folder_observations_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'literature folder observations are append-only' USING ERRCODE = 'P17F2';
END $$;
CREATE TRIGGER trg_literature_folder_append_only
    BEFORE UPDATE OR DELETE ON literature_folder_observations
    FOR EACH ROW EXECUTE FUNCTION literature_folder_observations_append_only();
"""

_DOWNGRADE = r"""
DROP TRIGGER trg_literature_folder_append_only ON literature_folder_observations;
DROP FUNCTION literature_folder_observations_append_only();
DROP TABLE literature_folder_observations;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
