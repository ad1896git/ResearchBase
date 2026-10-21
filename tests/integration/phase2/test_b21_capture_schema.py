"""Real PostgreSQL sealing, deferred completeness and additive legacy migration."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.novelty import ExactReadQuery, RecordSearchCoverageCommand
from researchbase.persistence.novelty_repository import N


def config(url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_catalog_and_owned_downgrade(novelty_env, phase2_database_url):
    e = novelty_env
    inspector = inspect(e["engine"])
    assert {x["name"] for x in inspector.get_columns("search_coverage_resolutions")} == {
        "id",
        "created_at",
        "created_by",
        "search_coverage_id",
        "search_result_resolution_id",
        "resolution_content_hash",
    }
    fks = inspector.get_foreign_keys("search_coverage_resolutions")
    assert {x["referred_table"] for x in fks} == {
        "actors",
        "search_coverage",
        "search_result_resolutions",
    }
    assert all(x["options"]["ondelete"] == "RESTRICT" for x in fks)
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname IN "
                    "('trg_b21_parent_complete','trg_b21_executions_complete',"
                    "'trg_b21_resolutions_complete') "
                    "AND tgdeferrable AND tginitdeferred"
                )
            ).scalar_one()
            == 3
        )
        tables = set(inspector.get_table_names())
        baseline = conn.execute(
            text("SELECT pg_get_functiondef('pr218_parent_guard()'::regprocedure)")
        ).scalar_one()
    cfg = config(phase2_database_url)
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    assert tables - set(inspect(e["engine"]).get_table_names()) == {
        "search_coverage_resolutions",
        "novelty_assessment_probes",
        "novelty_assessment_screening_results",
        "discussion_hypothesis_admissions",
        "strategy_candidate_captures",
        "strategy_candidate_sources",
        "strategy_question_admissions",
        "strategy_hypothesis_admissions",
    }
    command.upgrade(cfg, "0075_m1_reconsideration")
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT pg_get_functiondef('pr218_parent_guard()'::regprocedure)")
            ).scalar_one()
            == baseline
        )
    e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(uuid4(), e["project"], e["plan"], e["executions"], "Selected"),
    )
    with pytest.raises(DBAPIError, match="cannot downgrade populated B21 history"):
        command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    assert "search_coverage_resolutions" in inspect(e["engine"]).get_table_names()


def test_populated_v1_upgrade_preserves_hash_nested_ref_and_replay(
    novelty_env, phase2_database_url
):
    from researchbase.domain.novelty import (
        HashRef,
        NoveltyOutcome,
        coverage_material,
        novelty_material,
    )
    from researchbase.foundation.hashing import sha256_canonical_json

    e = novelty_env
    cfg = config(phase2_database_url)
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    identity, assessment = uuid4(), uuid4()
    c = RecordSearchCoverageCommand(identity, e["project"], e["plan"], e["executions"], "Legacy")
    with e["factory"]() as uow:
        repo = uow.novelty
        repo.prepare("coverage", identity)
        plan = repo.plan(e["plan"])
        material = coverage_material(
            HashRef("LiteratureSearchPlanVersion", e["plan"], plan["content_hash"]),
            c.search_execution_ids,
            ("test",),
            1,
            2,
            0,
            None,
            "Legacy",
        )
        digest = str(sha256_canonical_json(material))
        at = repo.at()
        repo.insert(
            "coverage",
            dict(
                id=identity,
                created_at=at,
                created_by=e["author"].actor_id,
                search_plan_version_id=e["plan"],
                providers=["test"],
                query_count=1,
                result_count=2,
                resolved_source_count=0,
                time_scope=None,
                coverage_limitations="Legacy",
                content_hash=digest,
                hash_scheme="sha256-cjson-v1",
            ),
        )
        for execution in c.search_execution_ids:
            repo.insert_child(
                "coverage",
                dict(
                    id=uuid4(),
                    created_at=at,
                    created_by=e["author"].actor_id,
                    search_coverage_id=identity,
                    search_execution_id=execution,
                ),
            )
        uow.commit()
    with e["factory"]() as uow:
        repo = uow.novelty
        repo.prepare("novelty", assessment, e["claim"])
        claim = repo.claim(e["claim"])
        novel = novelty_material(
            HashRef("ClaimVersion", e["claim"], claim["content_hash"]),
            HashRef("SearchCoverage", identity, digest),
            NoveltyOutcome.INCONCLUSIVE,
            "Legacy nested",
            None,
            e["author"].actor_id,
        )
        novel_digest = str(sha256_canonical_json(novel))
        repo.insert(
            "novelty",
            dict(
                id=assessment,
                created_at=repo.at(),
                created_by=e["author"].actor_id,
                claim_version_id=e["claim"],
                search_coverage_id=identity,
                assessment="INCONCLUSIVE",
                limitations="Legacy nested",
                assessed_by=e["author"].actor_id,
                supersedes_assessment_id=None,
                content_hash=novel_digest,
                hash_scheme="sha256-cjson-v1",
            ),
        )
        uow.commit()
    command.upgrade(cfg, "0075_m1_reconsideration")
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    add_resolution(e, e["results"][0])
    for value in (
        e["service"].record_search_coverage(e["author"], c),
        e["service"].read_search_coverage(e["author"], ExactReadQuery(e["project"], identity)),
    ):
        assert value.material_version == 1
        assert value.content_hash == digest
        assert value.quality.captured_unresolved_result_count is None
        assert value.quality.current_unresolved_result_count == 1
    value = e["service"].read_novelty_assessment(
        e["author"], ExactReadQuery(e["project"], assessment)
    )
    assert value.content_hash == novel_digest and value.search_coverage.content_hash == digest
    from researchbase.application.novelty import RecordNoveltyAssessmentCommand

    replay = e["service"].record_novelty_assessment(
        e["author"],
        RecordNoveltyAssessmentCommand(
            assessment,
            e["project"],
            e["claim"],
            identity,
            NoveltyOutcome.INCONCLUSIVE,
            "Legacy nested",
        ),
    )
    assert replay.content_hash == novel_digest
    assert replay.search_coverage.material_version == 1
    assert replay.search_coverage.quality.captured_unresolved_result_count is None
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    command.upgrade(cfg, "0075_m1_reconsideration")


def copy_capture(conn, old, new, *, version=2, count=None, children=True, resolutions=True):
    conn.execute(
        text("""INSERT INTO search_coverage
                            (id,created_at,created_by,search_plan_version_id,providers,query_count,
                             result_count,resolved_source_count,time_scope,coverage_limitations,
                             content_hash,hash_scheme,material_version,
                             captured_unresolved_result_count)
        SELECT :new,created_at,created_by,search_plan_version_id,providers,query_count,
        result_count,resolved_source_count,time_scope,coverage_limitations,content_hash,hash_scheme,
        :version,COALESCE(:count,captured_unresolved_result_count)
        FROM search_coverage WHERE id=:old"""),
        {"new": new, "old": old, "version": version, "count": count},
    )
    if children:
        conn.execute(
            text("""INSERT INTO search_coverage_executions
            SELECT gen_random_uuid(),created_at,created_by,:new,search_execution_id
            FROM search_coverage_executions WHERE search_coverage_id=:old"""),
            {"new": new, "old": old},
        )
    if resolutions:
        conn.execute(
            text("""INSERT INTO search_coverage_resolutions
            SELECT gen_random_uuid(),created_at,created_by,:new,search_result_resolution_id,
            resolution_content_hash FROM search_coverage_resolutions
            WHERE search_coverage_id=:old"""),
            {"new": new, "old": old},
        )


@pytest.mark.parametrize("case", ["v1", "count", "omitted", "execution", "prelock", "isolation"])
def test_normal_sql_incomplete_capture_rolls_back(b18_env, novelty_sql_role, case):
    e = b18_env
    identity = uuid4()
    with pytest.raises(DBAPIError) as error:
        with (
            e["engine"]
            .connect()
            .execution_options(
                isolation_level="REPEATABLE READ" if case == "isolation" else "READ COMMITTED"
            ) as conn
        ):
            with conn.begin():
                conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
                if case != "prelock":
                    conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
                copy_capture(
                    conn,
                    e["saved"]["coverage"].id,
                    identity,
                    version=1 if case == "v1" else 2,
                    count=0 if case == "count" else None,
                    children=case != "execution",
                    resolutions=case != "omitted",
                )
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM search_coverage WHERE id=:id"), {"id": identity}
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("case", ["hash", "actor", "time", "duplicate", "foreign", "missing"])
def test_normal_sql_resolution_guard(b18_env, novelty_sql_role, case):
    e = b18_env
    identity = uuid4()
    with e["engine"].connect() as conn:
        row = dict(
            conn.execute(text("SELECT * FROM search_coverage_resolutions LIMIT 1")).mappings().one()
        )
    expected = "23503" if case == "missing" else "23505" if case == "duplicate" else "P17D3"
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            copy_capture(conn, e["saved"]["coverage"].id, identity, resolutions=False)
            row.update(id=uuid4(), search_coverage_id=identity)
            if case == "hash":
                row["resolution_content_hash"] = "b" * 64
            if case == "actor":
                row["created_by"] = e["reviewer"].actor_id
            if case == "time":
                from datetime import timedelta

                row["created_at"] += timedelta(seconds=1)
            if case == "missing":
                row["search_result_resolution_id"] = uuid4()
            if case == "foreign":
                # A valid immutable resolution from another sealed execution.
                from tests.integration.phase2.pr2_18_fixtures import add_resolution

                # Existing baseline execution differs from b18's selected execution.
                result = conn.execute(
                    text(
                        "SELECT r.id FROM search_result_records r "
                        "JOIN search_query_records q ON q.id=r.search_query_record_id "
                        "WHERE q.literature_search_execution_id<>:execution LIMIT 1"
                    ),
                    {"execution": e["executions"][0]},
                ).scalar_one()
                foreign = add_resolution(e, result, connection=conn)
                row["search_result_resolution_id"] = foreign["id"]
                row["resolution_content_hash"] = foreign["content_hash"]
            for _ in range(2 if case == "duplicate" else 1):
                row["id"] = uuid4()
                conn.execute(
                    text(
                        "INSERT INTO search_coverage_resolutions ("
                        + ",".join(row)
                        + ") VALUES ("
                        + ",".join(":" + k for k in row)
                        + ")"
                    ),
                    row,
                )
    assert getattr(error.value.orig, "sqlstate", None) == expected


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "INSERT"])
def test_saved_children_immutable(b18_env, novelty_sql_role, operation):
    e = b18_env
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            if operation == "UPDATE":
                conn.execute(
                    text(
                        "UPDATE search_coverage_resolutions "
                        "SET resolution_content_hash=repeat('a',64)"
                    )
                )
            elif operation == "DELETE":
                conn.execute(text("DELETE FROM search_coverage_resolutions"))
            else:
                conn.execute(
                    text(
                        "INSERT INTO search_coverage_resolutions "
                        "SELECT gen_random_uuid(),created_at,created_by,search_coverage_id,"
                        "search_result_resolution_id,resolution_content_hash "
                        "FROM search_coverage_resolutions"
                    )
                )
    assert getattr(error.value.orig, "sqlstate", None) == "P17D1"


@pytest.mark.parametrize("table", ["search_query_records", "search_result_records"])
def test_terminal_result_closure_remains_sealed(b18_env, novelty_sql_role, table):
    e = b18_env
    columns = [x["name"] for x in inspect(e["engine"]).get_columns(table)]
    selected = ["gen_random_uuid()" if c == "id" else c for c in columns]
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(
                text(
                    f"INSERT INTO {table} ({','.join(columns)}) "
                    f"SELECT {','.join(selected)} FROM {table} LIMIT 1"
                )
            )
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"


@pytest.mark.parametrize("change", ["body", "search_path"])
def test_unexpected_baseline_refuses_upgrade(novelty_env, phase2_database_url, change):
    e = novelty_env
    cfg = config(phase2_database_url)
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    with e["engine"].begin() as conn:
        if change == "body":
            conn.execute(
                text(
                    "CREATE OR REPLACE FUNCTION pr218_immutable() RETURNS trigger "
                    "LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"
                )
            )
        else:
            conn.execute(text("ALTER FUNCTION pr218_immutable() SET search_path TO public"))
    with pytest.raises(DBAPIError, match="unexpected B21 baseline"):
        command.upgrade(cfg, "0075_m1_reconsideration")
    assert "search_coverage_resolutions" not in inspect(e["engine"]).get_table_names()
