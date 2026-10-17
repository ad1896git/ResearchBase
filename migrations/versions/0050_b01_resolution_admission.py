"""Repeat the existing M2 structural resolution closure at transaction end."""

from alembic import op

revision = "0050_b01_resolution_admission"
down_revision = "0049_b05_manuscript_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE CONSTRAINT TRIGGER b01_resolution_closure_at_commit
    AFTER INSERT ON search_result_resolutions
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION m2_check_closure()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER b01_resolution_closure_at_commit ON search_result_resolutions")
