"""Empty PR-00 migration proving Alembic connectivity."""

from __future__ import annotations

revision: str = "0001_empty"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
