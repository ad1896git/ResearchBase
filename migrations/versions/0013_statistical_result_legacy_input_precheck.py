"""Reject legacy zero-input StatisticalResults before accepting the guarded head."""

from __future__ import annotations

from alembic import op

revision: str = "0013_statistical_result_legacy_input_precheck"
down_revision: str | None = "0012_statistical_result_input_guard"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            invalid_result_id uuid;
        BEGIN
            SELECT sr.id
            INTO invalid_result_id
            FROM statistical_results AS sr
            WHERE NOT EXISTS (
                SELECT 1
                FROM statistical_result_inputs AS sri
                WHERE sri.statistical_result_id = sr.id
            )
            LIMIT 1;

            IF invalid_result_id IS NOT NULL THEN
                RAISE EXCEPTION
                    'zero-input StatisticalResult invariant violation for id %; '
                    'manual remediation required before retrying migration',
                    invalid_result_id
                    USING ERRCODE = 'check_violation';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    pass
