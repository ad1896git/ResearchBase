from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration

TABLE_COLUMNS = {
    "audit_findings": {
        "id",
        "project_id",
        "finding_type",
        "severity",
        "title",
        "description",
        "target_type",
        "target_id",
        "target_content_hash",
        "status",
        "created_by",
        "created_at",
        "row_version",
    },
    "impact_assessments": {
        "id",
        "project_id",
        "audit_finding_id",
        "assessment_payload",
        "conclusion",
        "created_by",
        "created_at",
        "content_hash",
    },
    "impact_targets": {
        "impact_assessment_id",
        "target_type",
        "target_id",
        "target_content_hash",
        "impact_kind",
    },
    "correction_records": {
        "id",
        "project_id",
        "target_type",
        "target_id",
        "target_content_hash",
        "correction_type",
        "corrected_assertion",
        "reason",
        "created_by",
        "created_at",
        "content_hash",
    },
}


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def test_pr14_has_exactly_four_authorized_governance_tables_and_columns(engine: Engine) -> None:
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND (tablename LIKE 'audit_%' OR tablename LIKE 'impact_%' "
                    "OR tablename LIKE 'correction_%')"
                )
            )
        }
        columns = {
            table: {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name=:table"
                    ),
                    {"table": table},
                )
            }
            for table in TABLE_COLUMNS
        }
    assert tables == set(TABLE_COLUMNS)
    assert columns == TABLE_COLUMNS


def test_pr14_constraints_fks_and_immutability_triggers_are_exact(engine: Engine) -> None:
    with engine.connect() as connection:
        constraints = {
            table: {
                row[0]: row[1]
                for row in connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid=CAST(:table AS regclass) AND contype IN ('p','f','c')"
                    ),
                    {"table": table},
                )
            }
            for table in TABLE_COLUMNS
        }
        triggers = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND "
                    "tgrelid IN ('audit_findings'::regclass, 'impact_assessments'::regclass, "
                    "'impact_targets'::regclass, 'correction_records'::regclass)"
                )
            )
        }

    assert set(constraints["audit_findings"]) == {
        "audit_findings_pkey",
        "audit_findings_project_id_fkey",
        "audit_findings_created_by_fkey",
        "ck_audit_findings_severity",
        "ck_audit_findings_status",
    }
    assert set(constraints["impact_assessments"]) == {
        "impact_assessments_pkey",
        "impact_assessments_project_id_fkey",
        "impact_assessments_audit_finding_id_fkey",
        "impact_assessments_created_by_fkey",
        "ck_impact_assessments_conclusion",
    }
    assert set(constraints["impact_targets"]) == {
        "impact_targets_pkey",
        "impact_targets_impact_assessment_id_fkey",
        "ck_impact_targets_kind",
    }
    assert set(constraints["correction_records"]) == {
        "correction_records_pkey",
        "correction_records_project_id_fkey",
        "correction_records_created_by_fkey",
        "ck_correction_records_type",
    }
    assert all(
        "ON DELETE RESTRICT" in definition
        for values in constraints.values()
        for name, definition in values.items()
        if name.endswith("_fkey")
    )
    assert triggers == {
        "audit_findings_material_immutable",
        "impact_assessments_immutable",
        "impact_targets_insert_guard",
        "impact_targets_immutable",
        "correction_records_immutable",
        "pr17d_audit_finding_update",
        "pr17d_audit_finding_delete",
        "pr17d_audit_finding_transition",
        "pr17d_impact_assessment_update",
        "pr17d_impact_assessment_delete",
        "pr17d_impact_target_update",
        "pr17d_impact_target_delete",
        "pr17d_correction_record_update",
        "pr17d_correction_record_delete",
    }
