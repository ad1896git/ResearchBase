from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    database_engine = create_database_engine()
    try:
        yield database_engine
    finally:
        database_engine.dispose()


def test_claim_schema_has_exact_authorized_columns(engine: Engine) -> None:
    with engine.connect() as connection:
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
            for table in ("claims", "claim_versions", "evidence_relations")
        }

    assert columns["claims"] == {
        "id",
        "project_id",
        "current_version_id",
        "created_by",
        "created_at",
        "row_version",
    }
    assert columns["claim_versions"] == {
        "id",
        "claim_id",
        "version_number",
        "status",
        "statement",
        "scope",
        "qualification",
        "support_set_hash",
        "content_hash",
        "created_by",
        "created_at",
        "frozen_at",
        "row_version",
    }
    assert columns["evidence_relations"] == {
        "id",
        "claim_version_id",
        "measurement_id",
        "statistical_result_id",
        "relation_type",
        "qualification",
        "created_by",
        "created_at",
    }


def test_claim_constraints_indexes_and_fks_are_exact(engine: Engine) -> None:
    with engine.connect() as connection:
        constraints = {
            table: {
                row[0]: row[1]
                for row in connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid=CAST(:table AS regclass) "
                        "AND contype IN ('p','f','u','c')"
                    ),
                    {"table": table},
                )
            }
            for table in ("claims", "claim_versions", "evidence_relations")
        }
        indexes = {
            table: {
                row[0]: row[1]
                for row in connection.execute(
                    text(
                        "SELECT indexname, indexdef FROM pg_indexes "
                        "WHERE schemaname='public' AND tablename=:table"
                    ),
                    {"table": table},
                )
            }
            for table in ("claims", "claim_versions", "evidence_relations")
        }

    assert set(constraints["claims"]) == {
        "claims_pkey",
        "claims_project_id_fkey",
        "claims_created_by_fkey",
        "fk_claim_current_version",
        "fk_claims_current_version_same_parent",
    }
    assert set(constraints["claim_versions"]) == {
        "claim_versions_pkey",
        "claim_versions_claim_id_fkey",
        "claim_versions_created_by_fkey",
        "ck_claim_versions_version_number",
        "ck_claim_versions_status",
        "uq_claim_versions_parent_version",
        "uq_claim_versions_parent_id_id",
    }
    assert set(constraints["evidence_relations"]) == {
        "evidence_relations_pkey",
        "evidence_relations_claim_version_id_fkey",
        "evidence_relations_measurement_id_fkey",
        "evidence_relations_statistical_result_id_fkey",
        "evidence_relations_created_by_fkey",
        "ck_evidence_relations_relation_type",
        "ck_evidence_relations_source_xor",
    }
    assert set(indexes["evidence_relations"]) == {
        "evidence_relations_pkey",
        "uq_evidence_measurement",
        "uq_evidence_stat",
    }
    assert (
        "WHERE (measurement_id IS NOT NULL)"
        in indexes["evidence_relations"]["uq_evidence_measurement"]
    )
    assert (
        "WHERE (statistical_result_id IS NOT NULL)"
        in indexes["evidence_relations"]["uq_evidence_stat"]
    )
    assert all(
        "ON DELETE RESTRICT" in definition
        for table in constraints.values()
        for name, definition in table.items()
        if name.endswith("_fkey") or name == "fk_claim_current_version"
    )


def test_claim_guard_triggers_exist_without_extra_claim_tables(engine: Engine) -> None:
    with engine.connect() as connection:
        triggers = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid IN ('claim_versions'::regclass, 'evidence_relations'::regclass) "
                    "AND NOT tgisinternal"
                )
            )
        }
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename IN ('claims','claim_versions','evidence_relations')"
                )
            )
        }

    assert triggers == {
        "claim_versions_finalized_immutable",
        "evidence_relations_draft_only",
        "pr17d_claim_version_update",
        "pr17d_claim_version_delete",
        "pr17d_evidence_relation_insert",
        "pr17d_evidence_relation_update",
        "pr17d_evidence_relation_delete",
    }
    assert tables == {"claims", "claim_versions", "evidence_relations"}
