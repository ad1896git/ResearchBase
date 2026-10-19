"""B22 additive catalog, normal-role guards and populated migration paths."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.novelty_repository import N
from tests.integration.phase2.test_b22_prior_art_correction import record, request

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)
PARENT = "0064_b14_publication_ready"


def config(url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def prelock(conn, role):
    conn.execute(text('SET LOCAL ROLE "' + role + '"'))
    conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))


def insert(conn, e, *, previous=None, identity=None, source=None, version=None, child=True):
    identity = identity or uuid4()
    conn.execute(
        text("""INSERT INTO prior_art_relations
      (id,created_at,created_by,claim_version_id,source_version_id,relation,rationale,
       assessed_by,content_hash,hash_scheme,material_version,supersedes_prior_art_relation_id)
      VALUES (:id,clock_timestamp(),:actor,:claim,:source,'RELATED','SQL guard test',:actor,
              :hash,'sha256-cjson-v1',:version,:previous)"""),
        {
            "id": identity,
            "actor": e["author"].actor_id,
            "claim": e["claim"],
            "source": source or e["source"],
            "hash": "a" * 64,
            "version": version if version is not None else (2 if previous else 1),
            "previous": previous,
        },
    )
    if child:
        conn.execute(
            text("""INSERT INTO prior_art_evidence_inputs
            (id,created_at,created_by,prior_art_relation_id,literature_evidence_id)
            VALUES (:id,clock_timestamp(),:actor,:parent,:evidence)"""),
            {
                "id": uuid4(),
                "actor": e["author"].actor_id,
                "parent": identity,
                "evidence": e["evidence"],
            },
        )
    return identity


def test_catalog_populated_v1_upgrade_and_v2_downgrade_refusal(novelty_env, phase2_database_url):
    e = novelty_env
    root = record(e, request(e))
    cfg = config(phase2_database_url)
    command.downgrade(cfg, PARENT)
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash FROM prior_art_relations WHERE id=:id"), {"id": root.id}
            ).scalar_one()
            == root.content_hash
        )
    command.upgrade(cfg, "head")
    with e["engine"].connect() as conn:
        assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
        columns = dict(
            conn.execute(
                text(
                    "SELECT column_name,data_type FROM information_schema.columns WHERE "
                    "table_name='prior_art_relations'"
                )
            ).all()
        )
        assert columns["material_version"] == "smallint"
        assert columns["supersedes_prior_art_relation_id"] == "uuid"
        assert (
            conn.execute(
                text("SELECT material_version FROM prior_art_relations WHERE id=:id"),
                {"id": root.id},
            ).scalar_one()
            == 1
        )
        constraints = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE "
                    "conrelid='prior_art_relations'::regclass"
                )
            ).scalars()
        )
        assert {
            "uq_b22_prior_art_pair",
            "ck_b22_prior_art_material",
            "ck_b22_prior_art_not_self",
            "fk_b22_prior_art_predecessor",
        } <= constraints
        assert (
            conn.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint WHERE "
                    "conname='fk_b22_prior_art_predecessor'"
                )
            ).scalar_one()
            == "r"
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE indexname IN "
                    "('uq_b22_prior_art_predecessor','ix_b22_prior_art_pair')"
                )
            ).scalar_one()
            == 2
        )
        assert conn.execute(
            text(
                "SELECT tgdeferrable AND tginitdeferred FROM pg_trigger WHERE "
                "tgname='b22_complete_correction'"
            )
        ).scalar_one()
        assert (
            conn.execute(
                text("SELECT count(*) FROM pg_trigger WHERE tgname='b22_prior_art_prelocked'")
            ).scalar_one()
            == 1
        )
    correction = record(e, request(e, supersedes_prior_art_relation_id=root.id))
    with pytest.raises(DBAPIError, match="history prevents downgrade"):
        command.downgrade(cfg, PARENT)
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash FROM prior_art_relations WHERE id=:id"),
                {"id": correction.id},
            ).scalar_one()
            == correction.content_hash
        )


@pytest.mark.parametrize(
    "case,state",
    [
        ("no_prelock", "P17D3"),
        ("same_transaction", "P17D3"),
        ("self", "23514"),
        ("material", "23514"),
        ("missing", "23503"),
        ("empty", "P17D3"),
    ],
)
def test_normal_role_insert_guards(novelty_env, novelty_sql_role, case, state):
    e = novelty_env
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            if case != "no_prelock":
                prelock(conn, novelty_sql_role)
            else:
                conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
            if case == "same_transaction":
                root = insert(conn, e)
                insert(conn, e, previous=root)
            elif case == "self":
                identity = uuid4()
                insert(conn, e, identity=identity, previous=identity)
            elif case == "material":
                insert(conn, e, version=2)
            elif case == "missing":
                insert(conn, e, previous=uuid4())
            else:
                insert(conn, e, child=case != "empty")
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == state
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 0


def test_normal_role_committed_parent_fork_mutation_and_late_evidence(
    novelty_env, novelty_sql_role
):
    e = novelty_env
    root = record(e, request(e))
    with e["engine"].begin() as conn:
        prelock(conn, novelty_sql_role)
        insert(conn, e, previous=root.id)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            prelock(conn, novelty_sql_role)
            insert(conn, e, previous=root.id)
    assert (
        getattr(getattr(error.value.orig, "diag", None), "constraint_name", None)
        == "uq_b22_prior_art_predecessor"
    )
    for sql in [
        "UPDATE prior_art_relations SET rationale='changed' WHERE id=:id",
        "DELETE FROM prior_art_relations WHERE id=:id",
        "INSERT INTO prior_art_evidence_inputs SELECT "
        "gen_random_uuid(),created_at,created_by,prior_art_relation_id,literatu"
        "re_evidence_id FROM prior_art_evidence_inputs WHERE "
        "prior_art_relation_id=:id",
    ]:
        with pytest.raises(DBAPIError) as error:
            with e["engine"].begin() as conn:
                prelock(conn, novelty_sql_role)
                conn.execute(text(sql), {"id": root.id})
        assert getattr(error.value.orig, "sqlstate", None) == "P17D1"


def test_preflight_rejects_unexpected_shared_guard(novelty_env, phase2_database_url):
    e = novelty_env
    cfg = config(phase2_database_url)
    command.downgrade(cfg, PARENT)
    with e["engine"].begin() as conn:
        conn.execute(
            text("""CREATE OR REPLACE FUNCTION pr218_lock_tables() RETURNS void
            LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp
            AS $$ BEGIN RETURN; END $$""")
        )
    with pytest.raises(RuntimeError, match="unexpected shared novelty guard baseline"):
        command.upgrade(cfg, "head")
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PARENT
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name='prior_art_relations' AND column_name='material_version'"
                )
            ).scalar_one()
            == 0
        )


def second_source(e):
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )

    with e["factory"]() as uow:
        material = _material_from_row(uow.source_version, uow.source_version.version(e["source"]))
    service = SourceVersionService(e["factory"], e["credentials"])
    new = service.create(CreateSourceVersion(e["author"], e["project"], material, uuid4()))
    identity = UUID(str(new["source_version_id"]))
    service.freeze(TransitionSourceVersion(e["author"], e["project"], identity, uuid4()))
    return identity


def test_cross_pair_fk_and_application_rejection(novelty_env, novelty_sql_role):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    e = novelty_env
    root = record(e, request(e))
    source = second_source(e)
    with pytest.raises(ResearchBaseError) as error:
        record(e, request(e, source_version_id=source, supersedes_prior_art_relation_id=root.id))
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with pytest.raises(DBAPIError) as sql_error:
        with e["engine"].begin() as conn:
            prelock(conn, novelty_sql_role)
            insert(conn, e, previous=root.id, source=source)
    assert (
        getattr(getattr(sql_error.value.orig, "diag", None), "constraint_name", None)
        == "fk_b22_prior_art_predecessor"
    )
