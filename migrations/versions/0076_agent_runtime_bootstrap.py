"""PR3-00 empty, forward-only Agent Runtime bootstrap."""

revision = "0076_agent_runtime_bootstrap"
down_revision = "0075_m1_reconsideration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError("forward-only migration; use a reviewed forward repair")
