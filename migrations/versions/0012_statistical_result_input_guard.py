"""Enforce at least one input for every StatisticalResult at commit time."""

from __future__ import annotations

from alembic import op

revision: str = "0012_statistical_result_input_guard"
down_revision: str | None = "0011_statistical_result"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION enforce_statistical_result_has_input() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM statistical_result_inputs
                WHERE statistical_result_id = NEW.id
            ) THEN
                RAISE EXCEPTION 'statistical_results require at least one input'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER statistical_result_requires_input
        AFTER INSERT ON statistical_results
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION enforce_statistical_result_has_input()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER statistical_result_requires_input ON statistical_results")
    op.execute("DROP FUNCTION enforce_statistical_result_has_input()")
