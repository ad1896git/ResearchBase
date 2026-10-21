"""Actual catalog, nullable history and deferred AFTER-trigger behavior."""

from dataclasses import asdict
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.domain.search_result_resolution import resolution_hash
from tests.integration.phase2.b01_support import count, record


def test_catalog_preserves_m2_contract_and_adds_deferred_guard(b01_env):
    e = b01_env
    with e["engine"].connect() as conn:
        constraints = dict(
            conn.execute(
                text(
                    "SELECT conname,pg_get_constraintdef(oid) FROM "
                    "pg_constraint WHERE "
                    "conrelid='search_result_resolutions'::regclass"
                )
            ).all()
        )
        assert (
            "UNIQUE NULLS NOT DISTINCT (search_result_record_id, source_id, source_version_id)"
            == constraints["search_result_resolutions_search_result_record_id_source_id_key"]
        )
        assert (
            "FOREIGN KEY (source_id, source_version_id) REFERENCES "
            "source_versions(literature_source_id, id) ON DELETE RESTRICT"
            == constraints["search_result_resolutions_source_id_source_version_id_fkey"]
        )
        triggers = conn.execute(
            text(
                "SELECT "
                "tgname,tgdeferrable,tginitdeferred,pg_get_triggerdef(oid) "
                "FROM pg_trigger WHERE "
                "tgrelid='search_result_resolutions'::regclass AND NOT "
                "tgisinternal"
            )
        ).all()
        names = {r[0] for r in triggers}
        assert names == {
            "m2_resolution_immutable",
            "m2_resolution_closure",
            "b01_resolution_closure_at_commit",
        }
        deferred = next(r for r in triggers if r[0].startswith("b01"))
        assert deferred[1:3] == (True, True)
        assert "AFTER INSERT" in deferred[3] and "m2_check_closure()" in deferred[3]
        cols = conn.execute(
            text(
                "SELECT column_name,data_type,is_nullable FROM "
                "information_schema.columns WHERE "
                "table_name='search_result_resolutions' ORDER BY "
                "ordinal_position"
            )
        ).all()
        assert len(cols) == 9
        assert ("source_version_id", "uuid", "YES") in cols
        indexes = (
            conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='search_result_resolutions'")
            )
            .scalars()
            .all()
        )
        assert {"ix_srr_source_version", "ix_srr_version", "ix_srr_actor"} <= set(indexes)


@pytest.mark.parametrize(
    "operation",
    [
        "UPDATE search_result_resolutions SET basis='changed'",
        "DELETE FROM search_result_resolutions",
    ],
)
def test_raw_history_mutation_denied(b01_env, operation):
    record(b01_env)
    with pytest.raises(DBAPIError) as error, b01_env["engine"].begin() as conn:
        conn.execute(text(operation))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D1"
    assert count(b01_env) == 1


@pytest.mark.parametrize("force", [False, True])
def test_deferred_guard_rechecks_same_transaction_link_closure(b01_env, force):
    e = b01_env
    # Existing owning guards may reject deletion earlier; either path denies commit.
    row = asdict(record(e))
    row.pop("project_id")
    row.update(id=uuid4(), source_version_id=None)
    row["content_hash"] = resolution_hash(row)
    from sqlalchemy.orm import Session

    from researchbase.persistence.metadata_observation_repository import (
        SqlAlchemyMetadataObservationRepository,
    )

    with pytest.raises(DBAPIError), Session(e["engine"]) as session:
        with session.begin():
            SqlAlchemyMetadataObservationRepository(session).insert_resolution(row)
            session.execute(
                text(
                    "DELETE FROM literature_source_project_links WHERE "
                    "literature_source_id=:source AND project_id=:project"
                ),
                {"source": row["source_id"], "project": e["project"]},
            )
            if force:
                session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert count(e) == 1


def test_nullable_legacy_hash_survives_downgrade_and_reupgrade(b01_env):
    e = b01_env
    first = record(e)
    row = asdict(first)
    row.pop("project_id")
    row.update(id=uuid4(), source_version_id=None, basis="Legacy source-only history")
    row["content_hash"] = resolution_hash(row)
    with e["service"]._factory() as uow:
        uow.metadata_observations.insert_resolution(row)
        uow.commit()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", e["engine"].url.render_as_string(hide_password=False))

    def saved():
        with e["engine"].connect() as conn:
            return conn.execute(text("SELECT * FROM search_result_resolutions ORDER BY id")).all()

    before = saved()
    command.downgrade(cfg, "0047_pr2_18_novelty_prior_art")
    assert saved() == before
    command.upgrade(cfg, "head")
    assert saved() == before
    from researchbase.application.search_result_resolution import ExactResolutionQuery

    value = e["service"].get_search_result_resolution(
        e["principal"], ExactResolutionQuery(e["project"], row["id"])
    )
    assert value.source_version_id is None and value.content_hash == row["content_hash"]


def test_direct_sql_concrete_actor_fk_denial(b01_env):
    from sqlalchemy.orm import Session

    from researchbase.persistence.metadata_observation_repository import (
        SqlAlchemyMetadataObservationRepository,
    )

    e = b01_env
    row = asdict(record(e))
    row.pop("project_id")
    row.update(id=uuid4(), source_version_id=None, resolved_by=uuid4())
    row["content_hash"] = resolution_hash(row)
    with pytest.raises(DBAPIError) as error, Session(e["engine"]) as session, session.begin():
        SqlAlchemyMetadataObservationRepository(session).insert_resolution(row)
    assert getattr(error.value.orig, "sqlstate", None) == "23503"
    assert count(e) == 1
