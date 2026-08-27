"""Harden PR-09 sealed Run input mutation protection."""

from __future__ import annotations

from alembic import op

revision: str = "0009_run_input_seal_fix"
down_revision: str | None = "0008_run_core"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_FIXED_FUNCTION = """
CREATE OR REPLACE FUNCTION reject_sealed_run_input_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    old_status text;
    old_sealed_at timestamptz;
    new_status text;
    new_sealed_at timestamptz;
BEGIN
    IF TG_OP IN ('DELETE', 'UPDATE') THEN
        SELECT status, inputs_sealed_at INTO old_status, old_sealed_at
        FROM runs WHERE id = OLD.run_id;
        IF old_status IS NULL OR old_status <> 'PLANNED' OR old_sealed_at IS NOT NULL THEN
            RAISE EXCEPTION 'sealed run inputs are immutable' USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status, inputs_sealed_at INTO new_status, new_sealed_at
        FROM runs WHERE id = NEW.run_id;
        IF new_status IS NULL OR new_status <> 'PLANNED' OR new_sealed_at IS NOT NULL THEN
            RAISE EXCEPTION 'sealed run inputs are immutable' USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$
"""

_ORIGINAL_FUNCTION = """
CREATE OR REPLACE FUNCTION reject_sealed_run_input_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE sealed_at timestamptz;
BEGIN
    IF TG_OP = 'DELETE' THEN
        SELECT inputs_sealed_at INTO sealed_at FROM runs WHERE id = OLD.run_id;
    ELSE
        SELECT inputs_sealed_at INTO sealed_at FROM runs WHERE id = NEW.run_id;
    END IF;
    IF sealed_at IS NOT NULL THEN
        RAISE EXCEPTION 'sealed run inputs are immutable' USING ERRCODE = 'check_violation';
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$
"""


def upgrade() -> None:
    op.execute(_FIXED_FUNCTION)


def downgrade() -> None:
    op.execute(_ORIGINAL_FUNCTION)
